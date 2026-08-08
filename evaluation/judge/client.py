"""Local LLM judge backed by Ollama.

Deterministic settings (temperature 0, fixed seed) and an explicit context
window; every call and response is appended to a JSONL audit log so any
reported metric can be traced back to the verdict and reason that produced it.

Callers decide what "fail closed" means for their metric and pass it as
``default`` to :meth:`ask_or_default`; an unreachable server, an unparseable
response, or a missing key never silently becomes a passing verdict.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

import requests

from src import config


class JudgeError(RuntimeError):
    """The judge could not produce a usable verdict."""


class JudgeUnavailable(JudgeError):
    """The judge backend could not be reached."""


def _extract_json(text: str) -> dict[str, Any]:
    """Parse a JSON object from a model response, tolerating stray prose."""

    text = (text or "").strip()
    if not text:
        raise JudgeError("empty response")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise JudgeError(f"no JSON object in response: {text[:200]!r}")
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise JudgeError(f"unparseable JSON: {text[:200]!r}") from exc
    if not isinstance(parsed, dict):
        raise JudgeError(f"expected a JSON object, got {type(parsed).__name__}")
    return parsed


class OllamaJudge:
    """Judge backed by a local Ollama server's chat API."""

    def __init__(
        self,
        model: str = config.JUDGE_MODEL,
        base_url: str = config.JUDGE_BASE_URL,
        num_ctx: int = config.JUDGE_NUM_CTX,
        seed: int = config.JUDGE_SEED,
        timeout: int = 300,
        log_path: Path | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.num_ctx = num_ctx
        self.seed = seed
        self.timeout = timeout
        self.log_path = log_path or (config.JUDGE_RESULTS / "judge_log.jsonl")
        self.calls = 0
        self.failures = 0
        # The log is append-only across runs. Without a run marker its entries
        # cannot be attributed to the results they produced, and a re-run after
        # a fix leaves the superseded verdicts sitting alongside the current
        # ones as if they were equally valid.
        self.run_id = f"{model}-{int(time.time())}"

    # ------------------------------------------------------------------ #
    def available(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
            names = {m.get("name", "") for m in resp.json().get("models", [])}
        except Exception:
            return False
        return any(n == self.model or n.startswith(f"{self.model}:") for n in names)

    def require(self) -> None:
        """Raise a message that says how to fix an unavailable judge."""

        if not self.available():
            raise JudgeUnavailable(
                f"Ollama model '{self.model}' is not available at "
                f"{self.base_url}. Start the server with 'ollama serve' and "
                f"pull the model with 'ollama pull {self.model}'."
            )

    # ------------------------------------------------------------------ #
    def _chat(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "seed": self.seed,
                "num_ctx": self.num_ctx,
            },
        }
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat", json=payload, timeout=self.timeout
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise JudgeUnavailable(str(exc)) from exc
        return resp.json().get("message", {}).get("content", "")

    def _log(self, record: dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"run_id": self.run_id, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        entry.update(record)
        with open(self.log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, default=str) + "\n")

    def ask(
        self,
        system: str,
        user: str,
        required_keys: tuple[str, ...] = (),
        task: str = "unspecified",
    ) -> dict[str, Any]:
        """Return the parsed verdict, retrying once on an unusable response."""

        last_error: Exception | None = None
        for attempt in (1, 2):
            prompt = user
            if attempt == 2:
                prompt = (
                    f"{user}\n\nYour previous response could not be parsed. "
                    "Reply with a single valid JSON object and nothing else."
                )
            started = time.perf_counter()
            try:
                raw = self._chat(system, prompt)
                verdict = _extract_json(raw)
                missing = [k for k in required_keys if k not in verdict]
                if missing:
                    raise JudgeError(f"missing keys {missing} in {verdict!r}")
            except JudgeUnavailable:
                raise
            except JudgeError as exc:
                last_error = exc
                self._log(
                    {
                        "task": task,
                        "attempt": attempt,
                        "ok": False,
                        "error": str(exc),
                        "elapsed_s": round(time.perf_counter() - started, 2),
                    }
                )
                continue

            self.calls += 1
            self._log(
                {
                    "task": task,
                    "attempt": attempt,
                    "ok": True,
                    "prompt": user,
                    "verdict": verdict,
                    "elapsed_s": round(time.perf_counter() - started, 2),
                }
            )
            return verdict

        self.failures += 1
        raise JudgeError(f"{task}: no usable verdict after 2 attempts ({last_error})")

    def ask_or_default(
        self,
        system: str,
        user: str,
        default: dict[str, Any],
        required_keys: tuple[str, ...] = (),
        task: str = "unspecified",
    ) -> dict[str, Any]:
        """Return a verdict, or ``default`` when none could be obtained.

        ``default`` is the caller's fail-closed answer. The returned dict is
        tagged with ``judge_failed`` so the metric can report how many verdicts
        were defaults rather than real judgments.
        """

        try:
            verdict = self.ask(system, user, required_keys, task)
        except JudgeError as exc:
            fallback = dict(default)
            fallback["judge_failed"] = True
            fallback.setdefault("reason", f"judge unavailable or unusable: {exc}")
            return fallback
        verdict["judge_failed"] = False
        return verdict


class StubJudge:
    """Scripted judge for offline tests.

    ``responses`` maps a task name to either a fixed dict or a callable taking
    the user prompt and returning a dict. Unmapped tasks raise, so a test can
    never accidentally exercise a real model.
    """

    def __init__(
        self,
        responses: dict[str, dict[str, Any] | Callable[[str], dict[str, Any]]],
    ) -> None:
        self.responses = responses
        self.calls = 0
        self.failures = 0
        self.seen: list[tuple[str, str]] = []

    def available(self) -> bool:
        return True

    def require(self) -> None:
        return None

    def ask(
        self,
        system: str,
        user: str,
        required_keys: tuple[str, ...] = (),
        task: str = "unspecified",
    ) -> dict[str, Any]:
        self.seen.append((task, user))
        if task not in self.responses:
            self.failures += 1
            raise JudgeError(f"StubJudge has no scripted response for {task!r}")
        value = self.responses[task]
        verdict = value(user) if callable(value) else dict(value)
        missing = [k for k in required_keys if k not in verdict]
        if missing:
            self.failures += 1
            raise JudgeError(f"missing keys {missing} in scripted response")
        self.calls += 1
        return verdict

    def ask_or_default(
        self,
        system: str,
        user: str,
        default: dict[str, Any],
        required_keys: tuple[str, ...] = (),
        task: str = "unspecified",
    ) -> dict[str, Any]:
        try:
            verdict = self.ask(system, user, required_keys, task)
        except JudgeError as exc:
            fallback = dict(default)
            fallback["judge_failed"] = True
            fallback.setdefault("reason", str(exc))
            return fallback
        verdict["judge_failed"] = False
        return verdict


def get_judge(**kwargs: Any) -> OllamaJudge:
    """Return the default judge used by the evaluation scripts."""

    return OllamaJudge(**kwargs)

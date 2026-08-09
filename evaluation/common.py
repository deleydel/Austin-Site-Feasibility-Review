"""Shared helpers for the Task 7 evaluation scripts."""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any

from src import config

# Environment that points the Task 4 synthesis node at the local judge model.
LLM_ENV = {
    "ENABLE_LLM_SYNTHESIS": "true",
    "OPENAI_API_KEY": "ollama",
    "OPENAI_BASE_URL": f"{config.JUDGE_BASE_URL}/v1",
    # Prefer an explicitly configured model; otherwise use the same local
    # judge model name from config (llama3.2). The old default
    # "llama3.2-eval32k" is only present on machines that created that alias.
    "SYNTHESIS_MODEL": os.getenv(
        "SYNTHESIS_MODEL", getattr(config, "JUDGE_MODEL", "llama3.2")
    ),
}


def enable_llm_synthesis() -> None:
    """Point the synthesis node at the local model for this process."""

    os.environ.update(LLM_ENV)


def disable_llm_synthesis() -> None:
    os.environ["ENABLE_LLM_SYNTHESIS"] = "false"


def jsonable(value: Any) -> Any:
    """Convert tool output to something json.dump can write losslessly.

    Pandas and numpy leak NaN and numpy scalars into tool results; NaN is not
    valid JSON and would produce files other tools cannot read.
    """

    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(v) for v in value]
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    for attr in ("item", "tolist"):
        if hasattr(value, attr):
            try:
                return jsonable(getattr(value, attr)())
            except Exception:
                break
    return str(value)


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jsonable(payload), indent=2), encoding="utf-8")
    return path


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_benchmark(name: str) -> Any:
    return read_json(config.BENCHMARKS_DIR / name)


def report_text(final_report: dict[str, Any]) -> str:
    """Flatten a report payload to searchable text.

    Used by the guardrail assertions, which must look at everything a reader
    would see, not just the synthesis paragraph.
    """

    return json.dumps(jsonable(final_report), default=str).lower()


# Only inputs at least this long are treated as echoes worth stripping.
# Short fields such as a land use are ordinary vocabulary the system will
# legitimately repeat; injected instructions are always far longer.
_MIN_ECHO_CHARS = 30


def _long_inputs(proposal: dict[str, Any]) -> list[str]:
    values = []
    for field in ("address", "proposed_land_use", "development_description"):
        supplied = " ".join(str(proposal.get(field) or "").split())
        if len(supplied) >= _MIN_ECHO_CHARS:
            values.append(supplied.lower())
    return values


def asserted_report_text(
    final_report: dict[str, Any], proposal: dict[str, Any]
) -> str:
    """Report text with verbatim echoes of the user's input removed.

    A report that quotes an applicant's own words back is not the system
    making that statement, so forbidden-phrase checks run against this text
    and only count a phrase the system asserts itself. Echoes are reported
    separately by :func:`echoed_input_paths`, because injected instruction
    text still reaches the exported document.
    """

    text = report_text(final_report)
    for supplied in _long_inputs(proposal):
        text = text.replace(supplied, " ")
    return text


def echoed_input_paths(
    final_report: dict[str, Any], proposal: dict[str, Any]
) -> list[str]:
    """Dotted paths in the report whose text repeats the user's input."""

    supplied_values = _long_inputs(proposal)
    if not supplied_values:
        return []

    found: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")
        elif isinstance(node, str):
            flat = " ".join(node.split()).lower()
            if any(supplied in flat for supplied in supplied_values):
                found.append(path)

    walk(jsonable(final_report), "")
    return found


def finding_labels(final_report: dict[str, Any]) -> list[str]:
    return [
        str(f.get("label", ""))
        for f in (final_report.get("findings") or [])
        if isinstance(f, dict)
    ]


def forbidden_matches(patterns: list[str], text: str) -> list[str]:
    """Patterns from a benchmark file that match the text.

    Regular expressions rather than literal strings: a generated claim varies
    in inflection, and "capacity are confirmed available" must be caught as
    surely as "capacity is confirmed".
    """

    hits = []
    for pattern in patterns:
        try:
            if re.search(pattern, text, re.I):
                hits.append(pattern)
        except re.error:
            if pattern.lower() in text.lower():
                hits.append(pattern)
    return hits


def pct(numerator: float, denominator: float) -> float | None:
    """Percentage rounded to one decimal, or None when nothing was measured."""

    if not denominator:
        return None
    return round(100.0 * numerator / denominator, 1)

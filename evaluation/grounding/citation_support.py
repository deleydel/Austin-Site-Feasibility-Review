"""Does a cited section actually support the claim attached to it?

Task 5's ``verify_citations`` establishes that a cited section *exists* in the
regulatory index. A hallucinated claim carrying a real section number passes
that check unchanged, so citation correctness is unmeasured. This module adds
the missing half and is used by the Task 7 metrics; ``src/guardrails`` is not
modified.

Order of work is deliberate: the authoritative section text is resolved first,
then cheap deterministic checks run, and the model is asked last and never gets
the final word (see :mod:`evaluation.judge.enforce`).
"""

from __future__ import annotations

from typing import Any

from evaluation.judge import prompts
from evaluation.judge.enforce import (
    MIN_TERM_OVERLAP,
    enforce_support_verdict,
    numbers_in,
    term_overlap,
)

MAX_SECTION_CHARS = 6000


def resolve_section(citation: dict[str, Any], retriever) -> dict[str, Any]:
    """Fetch a citation's authoritative section text.

    Uses the section index rather than the retrieved passage, because a
    retrieved passage may be one chunk of a section that was split, and a
    claim can be checked against text the retriever never returned.
    """

    doc_id = str(citation.get("doc_id") or citation.get("source") or "").strip()
    number = str(citation.get("section_number") or "").strip()
    if not doc_id or not number:
        return {"status": "incomplete_citation", "text": "", "title": None}

    found = retriever.get_section(doc_id, number)
    if found.get("status") != "found":
        return {
            "status": found.get("status", "not_found"),
            "text": "",
            "title": None,
            "doc_id": doc_id,
            "section_number": number,
        }

    match = found["matches"][0]
    return {
        "status": "found",
        "text": str(match.get("text") or "")[:MAX_SECTION_CHARS],
        "title": match.get("section_title"),
        "doc_id": doc_id,
        "section_number": number,
    }


def verify_claim_support(
    claim: str,
    citation: dict[str, Any],
    judge,
    retriever,
) -> dict[str, Any]:
    """Judge whether a citation's real section text supports a claim.

    Every failure path returns ``unsupported``: an unresolvable section, an
    off-topic pairing, a number the section does not contain, or a judge that
    produced nothing usable.
    """

    # Report citations carry the document under "source"; retrieved passages
    # use "doc_id". Reading only one renders the prefix as "None", which drops
    # exactly the LDC/TCM/DCM distinction a reader needs.
    label = (
        f"{citation.get('doc_id') or citation.get('source') or '?'} "
        f"{citation.get('section_number')}"
        f"{' ' + citation['section_title'] if citation.get('section_title') else ''}"
    )
    section = resolve_section(citation, retriever)

    if section["status"] != "found":
        return {
            "verdict": "unsupported",
            "citation": label,
            "section_status": section["status"],
            "reason": (
                f"cited section could not be resolved ({section['status']}); "
                "a citation that does not resolve cannot support anything"
            ),
            "enforced": True,
            "judge_used": False,
        }

    evidence = section["text"]
    overlap = round(term_overlap(claim, evidence), 3)
    missing_numbers = sorted(numbers_in(claim) - numbers_in(evidence))

    # Cheap rejections first: no judge call is spent on a pairing that cannot
    # pass, which keeps a local model's cost proportional to the real work.
    if overlap < MIN_TERM_OVERLAP:
        return {
            "verdict": "unsupported",
            "citation": label,
            "section_status": "found",
            "section_title": section["title"],
            "term_overlap": overlap,
            "reason": (
                f"claim and cited section share only {overlap:.0%} of the "
                "claim's content terms"
            ),
            "enforced": True,
            "judge_used": False,
        }

    if missing_numbers:
        return {
            "verdict": "unsupported",
            "citation": label,
            "section_status": "found",
            "section_title": section["title"],
            "term_overlap": overlap,
            "missing_numbers": missing_numbers,
            "reason": (
                "claim asserts numbers the cited section does not contain: "
                f"{missing_numbers}"
            ),
            "enforced": True,
            "judge_used": False,
        }

    call = prompts.claim_support(claim, evidence, label)
    raw = judge.ask_or_default(
        call.system, call.user, call.default, call.required_keys, call.task
    )
    verdict = enforce_support_verdict(raw, claim, evidence)
    verdict.update(
        {
            "citation": label,
            "section_status": "found",
            "section_title": section["title"],
            "judge_used": True,
            "judge_failed": bool(raw.get("judge_failed")),
        }
    )
    return verdict


def best_citation_for(claim: str, citations: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The citation a reader would take as supporting this claim.

    Claims are not individually cited by the system, so the closest cited
    section by content-term overlap is used. Returns None when no citation is
    even topically related, which is reported as an uncited claim rather than
    scored as a wrong citation.
    """

    best = None
    best_score = 0.0
    for citation in citations:
        text = " ".join(
            str(citation.get(field) or "")
            for field in ("section_title", "breadcrumb", "chapter", "section_number")
        )
        score = term_overlap(claim, text)
        if score > best_score:
            best, best_score = citation, score
    if best is None or best_score < MIN_TERM_OVERLAP:
        return None
    return best

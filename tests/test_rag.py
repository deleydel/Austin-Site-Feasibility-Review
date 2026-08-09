"""Task 2 sanity tests: chunk integrity, metadata completeness, and the
namespaced section lookup.

Run:  python -m pytest tests/test_rag.py -v
"""
from __future__ import annotations

import json

import pytest

from src import config
from src.rag.retriever import get_retriever

REQUIRED_METADATA = ("doc_id", "source_name", "source_url", "chapter",
                     "section_number", "breadcrumb", "chunk_index")


@pytest.fixture(scope="module")
def chunks():
    with open(config.REG_CHUNKS_JSON) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def retriever():
    return get_retriever(use_query_instruction=True)


def test_no_chunk_exceeds_bge_limit(chunks):
    from src.rag.chunker import n_tokens
    over = [c["chunk_id"] for c in chunks if n_tokens(c["text"]) > 512]
    assert over == []


def test_every_chunk_has_citation_metadata(chunks):
    for c in chunks:
        for key in REQUIRED_METADATA:
            assert key in c["metadata"] and c["metadata"][key] != "", \
                (c["chunk_id"], key)


def test_no_cross_section_chunks(chunks):
    """chunk_id encodes its source section; each id's section metadata must
    be internally consistent (one section per chunk by construction)."""
    seen = {}
    for c in chunks:
        seq = c["chunk_id"].rsplit(":", 2)[1]
        key = (c["metadata"]["doc_id"], seq)
        sec = (c["metadata"]["section_number"], c["metadata"]["chapter"])
        assert seen.setdefault(key, sec) == sec


def test_paragraph_audit_zero_unresolved():
    stats = json.loads((config.DATA_PROCESSED / "index_build_stats.json").read_text())
    for doc, audit in stats["paragraph_audits"].items():
        assert audit["unresolved"] == 0, doc


def test_retrieval_returns_metadata(retriever):
    res = retriever.retrieve("impervious cover limits", k=3)
    assert len(res) == 3
    for r in res:
        assert r["section_number"] and r["source_url"] and r["breadcrumb"]


def test_doc_filter_respected(retriever):
    res = retriever.retrieve("drainage requirements", k=5, doc_ids=["DCM"])
    assert all(r["doc_id"] == "DCM" for r in res)


def test_get_section_namespacing(retriever):
    dcm = retriever.get_section("Drainage Criteria Manual", "1.2.2")
    assert dcm["status"] == "found"
    assert dcm["matches"][0]["doc_id"] == "DCM"
    ldc = retriever.get_section("LDC", "25-2-492")
    assert ldc["status"] == "found"
    missing = retriever.get_section("TCM", "1.2.2")
    # TCM has no 1.2.2 (its sections are x.y.0 at that depth) — must NOT
    # fall through to the DCM's 1.2.2.
    assert missing["status"] == "not_found"


def test_get_section_ambiguous_within_doc(retriever):
    r = retriever.get_section("LDC", "1.1")   # repeats across subchapters
    assert r["status"] == "ambiguous"
    assert len(r["matches"]) > 1


def test_query_expansion_maps_lay_to_regulatory_terms():
    from src.rag.query_expansion import expand_query, expansion_terms
    terms = expansion_terms("Can I take down this big old tree in my backyard?")
    assert "protected" in terms and "heritage" in terms
    variants = expand_query("Where do the delivery trucks unload?")
    assert len(variants) == 2 and "loading" in variants[1]
    # formally worded queries pass through unexpanded when nothing matches
    assert expand_query("critical water quality zone requirements") == [
        "critical water quality zone requirements"
    ]


def test_lay_phrasing_retrieves_regulatory_section(retriever):
    """A conversational query with zero regulatory vocabulary must still
    surface the governing section."""
    res = retriever.retrieve(
        "There is boggy marshy ground on part of my land. "
        "Does that stop me building?", k=10)
    got = {(x["doc_id"], x["section_number"]) for x in res}
    assert ("LDC", "25-8-282") in got     # WETLAND PROTECTION


def test_results_deduplicated_by_section(retriever):
    res = retriever.retrieve("site development regulations", k=5)
    keys = [(x["doc_id"], x["section_number"]) for x in res]
    assert len(keys) == len(set(keys))

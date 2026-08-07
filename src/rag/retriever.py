"""Task 2: metadata-preserving hybrid retriever.

- Dense: bge-base-en-v1.5 (normalized, cosine) over ChromaDB. The BGE
  short-query instruction is a flag whose benefit is measured in the
  retrieval benchmark, not assumed.
- Lexical: BM25 over the same chunks (legal text is full of exact terms and
  section numbers where lexical matching helps).
- Fusion: reciprocal rank fusion.
- Filters: doc_ids / chapters let agent nodes scope retrieval
  (e.g. drainage node -> LDC 25-7, 25-8 + DCM).
- get_section(source, section_number): namespaced exact lookup; section
  numbers repeat across manuals and across LDC subchapter ordinances, so the
  result is explicitly found | ambiguous | not_found.

Every result carries full citation metadata.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from src import config

# Keeps "25-2-492", "1.2.2", "sf-3" as single tokens.
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-.][a-z0-9]+)*")
# Explicit section citations in a query, e.g. "25-8-92" or "1.2.2" / "9.3.3.2".
_CITATION_RE = re.compile(r"\b(\d+-\d+[A-Z]?-\d+(?:\.\d+)?|\d+(?:\.\d+){1,3})\b")

_DOC_ALIASES = {
    "ldc": "LDC", "land development code": "LDC", "title 25": "LDC",
    "austin land development code (title 25)": "LDC",
    "dcm": "DCM", "drainage criteria manual": "DCM",
    "austin drainage criteria manual": "DCM",
    "tcm": "TCM", "transportation criteria manual": "TCM",
    "austin transportation criteria manual": "TCM",
}


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class RegulatoryRetriever:
    # Default False: the BGE model card's short-query instruction was tested
    # per its recommendation (tests/run_retrieval_benchmark.py) and measurably
    # LOWERED Hit@1/MRR on this corpus, so it is off by default.
    def __init__(self, use_query_instruction: bool = False):
        self.use_query_instruction = use_query_instruction
        self._model = None
        self._collection = None
        with open(config.REG_CHUNKS_JSON) as f:
            self.chunks = json.load(f)
        self.by_id = {c["chunk_id"]: c for c in self.chunks}
        self._bm25 = BM25Okapi([_tokenize(c["text"]) for c in self.chunks])
        with open(config.REG_SECTIONS_JSON) as f:
            self.sections = json.load(f)

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(config.EMBEDDING_MODEL)
        return self._model

    @property
    def collection(self):
        if self._collection is None:
            client = chromadb.PersistentClient(path=str(config.INDEX_DIR))
            self._collection = client.get_collection(config.CHROMA_COLLECTION)
        return self._collection

    # ------------------------------------------------------------------ #
    def _allowed(self, doc_ids, chapters) -> set[str] | None:
        """Chunk-id filter for BM25 side; None means no filter."""
        if not doc_ids and not chapters:
            return None
        ids = set()
        for c in self.chunks:
            m = c["metadata"]
            if doc_ids and m["doc_id"] not in doc_ids:
                continue
            if chapters and m["chapter"] not in chapters:
                continue
            ids.add(c["chunk_id"])
        return ids

    def _dense(self, query: str, fetch_k: int, doc_ids, chapters) -> list[str]:
        q = (config.BGE_QUERY_INSTRUCTION + query) if self.use_query_instruction else query
        emb = self.model.encode([q], normalize_embeddings=True)[0].tolist()
        where = None
        clauses = []
        if doc_ids:
            clauses.append({"doc_id": {"$in": list(doc_ids)}})
        if chapters:
            clauses.append({"chapter": {"$in": list(chapters)}})
        if len(clauses) == 1:
            where = clauses[0]
        elif clauses:
            where = {"$and": clauses}
        res = self.collection.query(
            query_embeddings=[emb], n_results=fetch_k, where=where
        )
        return res["ids"][0]

    def _lexical(self, query: str, fetch_k: int, allowed: set[str] | None) -> list[str]:
        scores = self._bm25.get_scores(_tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: -scores[i])
        out = []
        for i in order:
            cid = self.chunks[i]["chunk_id"]
            if scores[i] <= 0:
                break
            if allowed is not None and cid not in allowed:
                continue
            out.append(cid)
            if len(out) >= fetch_k:
                break
        return out

    # Fusion weights chosen from the ablation in tests/run_retrieval_benchmark:
    # dense-weighted RRF matched dense-only Hit@5 while improving Recall@5 and
    # keeping BM25's advantage on exact section-number queries.
    DENSE_WEIGHT = 2.0
    BM25_WEIGHT = 1.0

    def retrieve(self, query: str, k: int = 5, doc_ids: list[str] | None = None,
                 chapters: list[str] | None = None, fetch_k: int = 50) -> list[dict]:
        """Hybrid dense+BM25 retrieval with weighted reciprocal rank fusion."""
        dense = self._dense(query, fetch_k, doc_ids, chapters)
        lexical = self._lexical(query, fetch_k, self._allowed(doc_ids, chapters))
        rrf: dict[str, float] = {}
        for weight, rank_list in ((self.DENSE_WEIGHT, dense),
                                  (self.BM25_WEIGHT, lexical)):
            for r, cid in enumerate(rank_list):
                rrf[cid] = rrf.get(cid, 0.0) + weight / (60 + r + 1)

        # Citation fast path: an explicit section number in the query resolves
        # deterministically — those chunks outrank any fuzzy match.
        cited = set(_CITATION_RE.findall(query))
        if cited:
            allowed = self._allowed(doc_ids, chapters)
            for c in self.chunks:
                if c["metadata"]["section_number"] in cited:
                    cid = c["chunk_id"]
                    if allowed is None or cid in allowed:
                        rrf[cid] = rrf.get(cid, 0.0) + 1.0
        top = sorted(rrf, key=rrf.get, reverse=True)[:k]
        results = []
        for cid in top:
            c = self.by_id[cid]
            results.append({
                "chunk_id": cid,
                "text": c["body"],
                "score_rrf": round(rrf[cid], 5),
                "in_dense_top": cid in dense,
                "in_bm25_top": cid in lexical,
                **c["metadata"],
            })
        return results

    # ------------------------------------------------------------------ #
    def get_section(self, source: str, section_number: str) -> dict:
        """Namespaced exact section lookup (citation verification support)."""
        doc_id = _DOC_ALIASES.get(source.strip().lower(), source.strip().upper())
        num = section_number.strip().lstrip("§").strip()
        matches = [s for s in self.sections
                   if s["doc_id"] == doc_id and s["section_number"] == num]
        if not matches:
            return {"status": "not_found", "source": doc_id,
                    "section_number": num, "matches": []}
        status = "found" if len(matches) == 1 else "ambiguous"
        return {"status": status, "source": doc_id, "section_number": num,
                "matches": matches}


@lru_cache(maxsize=2)
def get_retriever(use_query_instruction: bool = False) -> RegulatoryRetriever:
    return RegulatoryRetriever(use_query_instruction=use_query_instruction)

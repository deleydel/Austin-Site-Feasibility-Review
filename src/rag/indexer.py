"""Task 2: build the vector index.

- Persists parsed sections and chunks to JSON (used by get_section and BM25).
- Embeds chunks with bge-base-en-v1.5, L2-normalized, into a persistent
  ChromaDB collection using cosine distance.

Run:  python -m src.rag.indexer
"""
from __future__ import annotations

import json
import time

import chromadb
from sentence_transformers import SentenceTransformer

from src import config
from src.rag.chunker import chunk_all
from src.rag.docx_loader import load_all


def build_index() -> dict:
    t0 = time.time()
    sections, audits = load_all()
    for doc_id, audit in audits.items():
        if audit.get("unresolved", 0):
            raise RuntimeError(f"{doc_id}: {audit['unresolved']} unresolved paragraphs")

    chunks, chunk_stats = chunk_all(sections)

    config.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    config.REG_SECTIONS_JSON.write_text(
        json.dumps([s.to_dict() for s in sections], indent=1)
    )
    config.REG_CHUNKS_JSON.write_text(json.dumps(
        [{"chunk_id": c.chunk_id, "text": c.text, "body": c.body,
          "metadata": c.metadata} for c in chunks], indent=1))

    model = SentenceTransformer(config.EMBEDDING_MODEL)
    texts = [c.text for c in chunks]
    embeddings = model.encode(
        texts, batch_size=32, normalize_embeddings=True, show_progress_bar=True
    )

    client = chromadb.PersistentClient(path=str(config.INDEX_DIR))
    try:
        client.delete_collection(config.CHROMA_COLLECTION)
    except Exception:
        pass
    col = client.create_collection(
        config.CHROMA_COLLECTION, metadata={"hnsw:space": "cosine"}
    )
    B = 2000
    for i in range(0, len(chunks), B):
        batch = chunks[i:i + B]
        col.add(
            ids=[c.chunk_id for c in batch],
            embeddings=embeddings[i:i + B].tolist(),
            documents=[c.text for c in batch],
            metadatas=[{k: ("" if v is None else v) for k, v in c.metadata.items()}
                       for c in batch],
        )

    stats = {
        "paragraph_audits": {d: {k: v for k, v in a.items()
                                 if k != "unresolved_samples"}
                             for d, a in audits.items()},
        "chunking": chunk_stats,
        "chunks_indexed": col.count(),
        "build_seconds": round(time.time() - t0, 1),
    }
    (config.DATA_PROCESSED / "index_build_stats.json").write_text(
        json.dumps(stats, indent=2))
    return stats


if __name__ == "__main__":
    s = build_index()
    print(json.dumps(s, indent=2))

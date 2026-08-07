"""Task 2: section-aware chunking sized for bge-base-en-v1.5 (512-token limit).

Rules (per review):
- Token counts use the BGE tokenizer itself, breadcrumb included.
- Target ~420 / hard max 450 BGE tokens per chunk — comfortably under 512.
- A chunk never crosses a legal-section boundary.
- Long sections split at subsection boundaries ("(A)", "A.", "[SUBSECTION]",
  numbered subheads) with ~64 tokens of overlap, applied only within a section.
- Every chunk carries full citation metadata.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from transformers import AutoTokenizer

from src import config
from src.rag.docx_loader import Section

_tokenizer = None


def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained(config.EMBEDDING_MODEL)
    return _tokenizer


def n_tokens(text: str) -> int:
    return len(get_tokenizer().encode(text, add_special_tokens=False))


# Paragraphs that begin a subsection are preferred split points.
BOUNDARY_RE = re.compile(
    r"^\((?:[A-Z]|\d+)\)\s"      # (A)  (1)
    r"|^[A-Z]\.\s"               # A.
    r"|^\d+\.\s"                 # 1.
    r"|^\[SUBSECTION\]"          # named LDC subsection headers
)
SENT_RE = re.compile(r"(?<=[.;:])\s+")


@dataclass
class Chunk:
    chunk_id: str
    text: str                    # breadcrumb + body (what gets embedded)
    body: str
    metadata: dict


def _split_oversized_paragraph(par: str, budget: int) -> list[str]:
    """Split a block that alone exceeds the body budget.

    Multi-line blocks (markdown tables) split by lines, repeating the header
    row so every piece stays a readable table; prose splits by sentences.
    """
    lines = par.split("\n")
    if len(lines) > 2:
        # Markdown table: repeat the column-header row (not the meaningless
        # separator row) in every piece so district/column context survives.
        has_sep = lines[1].startswith("|") and "---" in lines[1]
        header = [lines[0]] if has_sep and lines[0].startswith("|") else []
        head_tok = (n_tokens(header[0]) + 1) if header else 0
        if head_tok > budget // 2:      # header too big to repeat per piece
            header, head_tok = [], 0
            rows = lines
        else:
            rows = lines[2:] if has_sep else lines[len(header):]
        pieces, cur, cur_tok = [], [], head_tok
        for line in rows:
            t = n_tokens(line) + 1
            if cur and cur_tok + t > budget:
                pieces.append("\n".join(header + cur))
                cur, cur_tok = [], head_tok
            cur.append(line)
            cur_tok += t
        if cur:
            pieces.append("\n".join(header + cur))
        # A single line can still be too long (rare); fall through to sentences.
        out = []
        for p in pieces:
            out.extend(_split_by_sentences(p, budget) if n_tokens(p) > budget else [p])
        return out
    return _split_by_sentences(par, budget)


def _split_by_sentences(par: str, budget: int) -> list[str]:
    pieces, cur, cur_tok = [], [], 0
    for sent in SENT_RE.split(par):
        t = n_tokens(sent) + 1
        if t > budget:                       # single monster sentence/row:
            if cur:                          # hard-split at the token level
                pieces.append(" ".join(cur))
                cur, cur_tok = [], 0
            pieces.extend(_hard_token_split(sent, budget))
            continue
        if cur and cur_tok + t > budget:
            pieces.append(" ".join(cur))
            cur, cur_tok = [], 0
        cur.append(sent)
        cur_tok += t
    if cur:
        pieces.append(" ".join(cur))
    return pieces


def _hard_token_split(text: str, budget: int) -> list[str]:
    tok = get_tokenizer()
    ids = tok.encode(text, add_special_tokens=False)
    return [tok.decode(ids[i:i + budget]) for i in range(0, len(ids), budget)]


def chunk_section(section: Section, seq: int) -> list[Chunk]:
    breadcrumb = section.breadcrumb
    bc_tokens = n_tokens(breadcrumb) + 2
    budget_max = config.CHUNK_MAX_TOKENS - bc_tokens
    budget_target = config.CHUNK_TARGET_TOKENS - bc_tokens

    # Tokenize paragraphs once; explode any paragraph larger than the budget.
    paras: list[tuple[str, int, bool]] = []   # (text, tokens, is_boundary)
    for p in section.paragraphs:
        p = p.strip()
        if not p:
            continue
        t = n_tokens(p)
        if t > budget_max:
            for i, piece in enumerate(_split_oversized_paragraph(p, budget_max)):
                paras.append((piece, n_tokens(piece), i == 0 and bool(BOUNDARY_RE.match(p))))
        else:
            paras.append((p, t, bool(BOUNDARY_RE.match(p))))
    if not paras:
        return []

    # Greedy packing with boundary-preferred closes.
    windows: list[list[tuple[str, int, bool]]] = []
    cur: list[tuple[str, int, bool]] = []
    cur_tok = 0
    for item in paras:
        text, t, boundary = item
        over_max = cur and cur_tok + t + 1 > budget_max
        over_target_at_boundary = cur and boundary and cur_tok + t + 1 > budget_target
        if over_max or over_target_at_boundary:
            windows.append(cur)
            cur, cur_tok = [], 0
        cur.append(item)
        cur_tok += t + 1
    if cur:
        windows.append(cur)

    # Intra-section overlap: prepend tail of the previous window.
    chunks: list[Chunk] = []
    n = len(windows)
    for i, win in enumerate(windows):
        body_parts = [w[0] for w in win]
        if i > 0 and config.CHUNK_OVERLAP_TOKENS > 0:
            tail, tail_tok = [], 0
            for text, t, _ in reversed(windows[i - 1]):
                if tail_tok + t > config.CHUNK_OVERLAP_TOKENS:
                    break
                tail.insert(0, text)
                tail_tok += t
            if tail and tail_tok + sum(w[1] for w in win) + bc_tokens <= config.CHUNK_MAX_TOKENS:
                body_parts = tail + body_parts
        body = "\n".join(body_parts)
        chunk_id = f"{section.doc_id}:{seq}:{i}"
        chunks.append(Chunk(
            chunk_id=chunk_id,
            text=f"{breadcrumb}\n\n{body}",
            body=body,
            metadata={
                "doc_id": section.doc_id,
                "source_name": section.source_name,
                "source_url": section.source_url,
                "chapter": section.chapter,
                "chapter_title": section.chapter_title,
                "article": section.article,
                "section_number": section.section_number,
                "section_title": section.section_title,
                "breadcrumb": breadcrumb,
                "is_preamble": section.is_preamble,
                "chunk_index": i,
                "n_chunks": n,
            },
        ))
    return chunks


def chunk_all(sections: list[Section]) -> tuple[list[Chunk], dict]:
    chunks: list[Chunk] = []
    empty_sections = 0
    for seq, s in enumerate(sections):
        cs = chunk_section(s, seq)
        if not cs:
            empty_sections += 1
        chunks.extend(cs)
    sizes = [n_tokens(c.text) for c in chunks]
    stats = {
        "sections_in": len(sections),
        "sections_empty_skipped": empty_sections,
        "chunks_out": len(chunks),
        "max_chunk_tokens": max(sizes),
        "mean_chunk_tokens": round(sum(sizes) / len(sizes), 1),
        "chunks_over_512": sum(1 for s in sizes if s > 512),
        "chunks_over_450": sum(1 for s in sizes if s > config.CHUNK_MAX_TOKENS),
    }
    return chunks, stats

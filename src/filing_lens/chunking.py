"""Comparable word budgets; fixed windows versus paragraph/table boundaries."""

from __future__ import annotations

import re


def _windows(text: str, start: int, end: int, size: int, overlap: int = 0):
    words = list(re.finditer(r"\S+", text[start:end]))
    for index in range(0, len(words), size - overlap):
        stop = min(index + size, len(words))
        yield start + words[index].start(), start + words[stop - 1].end()
        if stop == len(words):
            break


def chunk_pages(
    pages: list[dict], documents: list[dict], strategy: str, size: int = 160, overlap: int = 32
) -> list[dict]:
    if strategy not in {"fixed", "structure"}:
        raise ValueError(f"Unknown chunk strategy: {strategy}")
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("Require size > 0 and 0 <= overlap < size")
    docs = {d["id"]: d for d in documents}
    chunks = []
    for page in pages:
        text = page["text"]
        segments = []
        if strategy == "fixed":
            segments = [
                (s, e, "window", None, "") for s, e in _windows(text, 0, len(text), size, overlap)
            ]
        else:
            pending = None
            for block in page["blocks"]:
                if block["kind"] == "table":
                    if pending:
                        segments.append((*pending, "paragraph", None, ""))
                        pending = None
                    # Repeat two source header rows when splitting a long table.
                    lines = text[block["start"] : block["end"]].splitlines(keepends=True)
                    header = "".join(lines[:2]).strip()
                    start, end, words = block["start"], block["start"], 0
                    for line in lines:
                        if words and words + len(line.split()) > size:
                            segments.append((start, end, "table", block["table_id"], header))
                            start, words = end, 0
                        end += len(line)
                        words += len(line.split())
                    if end > start:
                        segments.append((start, end, "table", block["table_id"], header))
                else:
                    for start, end in _windows(text, block["start"], block["end"], size):
                        if pending and len(text[pending[0] : end].split()) <= size:
                            pending = (pending[0], end)
                        else:
                            if pending:
                                segments.append((*pending, "paragraph", None, ""))
                            pending = (start, end)
            if pending:
                segments.append((*pending, "paragraph", None, ""))
        doc = docs[page["doc_id"]]
        for idx, (start, end, kind, table_id, header) in enumerate(segments):
            body = text[start:end]
            if header and not body.startswith(header):
                body = header + "\n" + body
            # Identical metadata prefix for both strategies. No query-dependent routing.
            prefix = f"{doc['company']} ({doc['ticker']}) FY{doc['fiscal_year']}. "
            chunks.append(
                {
                    "id": f"{strategy}:{page['doc_id']}:p{page['page']}:{idx}",
                    "doc_id": page["doc_id"],
                    "page": page["page"],
                    "start": start,
                    "end": end,
                    "text": prefix + body,
                    "kind": kind,
                    "table_id": table_id,
                }
            )
    return chunks

"""Warm reproducible embedding indexes (no evaluation questions are read)."""

from pathlib import Path

from filing_lens.chunking import chunk_pages
from filing_lens.io import read_json, read_jsonl, write_jsonl
from filing_lens.retrieval import Index, Models

root = Path(__file__).resolve().parents[1]
pages = read_jsonl(root / "data/processed/pages.jsonl")
documents = read_json(root / "data/corpus.json")["documents"]
models = Models(root)
for strategy in ("fixed", "structure"):
    chunks = chunk_pages(pages, documents, strategy)
    write_jsonl(root / f"data/processed/chunks-{strategy}.jsonl", chunks)
    print(f"Embedding {len(chunks)} {strategy} chunks", flush=True)
    Index(chunks, models)

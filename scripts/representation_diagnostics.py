"""Measure the actual chunk-size/truncation confound, independently of QA labels."""

from pathlib import Path

import numpy as np
from transformers import AutoTokenizer

from filing_lens.io import read_json, read_jsonl, write_json

root = Path(__file__).resolve().parents[1]
name = "sentence-transformers/all-MiniLM-L6-v2"
lock = read_json(root / "data/model-lock.json")
tokenizer = AutoTokenizer.from_pretrained(name, revision=lock[name])
report = []
for strategy in ("fixed", "structure"):
    chunks = read_jsonl(root / f"data/processed/chunks-{strategy}.jsonl")
    texts = [c["text"] for c in chunks]
    encoded = tokenizer(texts, truncation=False, return_length=True, verbose=False)
    lengths = np.array(encoded["length"])
    words = np.array([len(t.split()) for t in texts])
    report.append(
        {
            "strategy": strategy,
            "chunks": len(chunks),
            "word_count_p50": float(np.median(words)),
            "word_count_max": int(words.max()),
            "wordpiece_count_p50": float(np.median(lengths)),
            "wordpiece_count_p95": float(np.percentile(lengths, 95)),
            "wordpiece_count_max": int(lengths.max()),
            "dense_256_token_truncation_fraction": float(np.mean(lengths > 256)),
            "note": "Includes metadata and repeated headers. No evaluation labels used.",
        }
    )
write_json(root / "results/representation-diagnostics.json", report)
print(report)

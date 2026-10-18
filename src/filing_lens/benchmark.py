"""Twelve controlled ablations. Preserve every prediction, timing, and source span."""

from __future__ import annotations

import importlib.metadata
import platform
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from rich import print

from filing_lens.chunking import chunk_pages
from filing_lens.evaluation import (
    aggregate,
    paired_company_bootstrap,
    retrieval_metrics,
    score_answer,
)
from filing_lens.io import digest, read_json, read_jsonl, write_json, write_jsonl
from filing_lens.reader import answer_question
from filing_lens.retrieval import Index, Models


def validate_dataset(root: Path) -> dict:
    lock = read_json(root / "data/benchmark-lock.json")
    for key, path in [
        ("questions", "data/questions.jsonl"),
        ("annotations", "data/annotations.json"),
        ("pages", "data/processed/pages.jsonl"),
        ("tables", "data/processed/tables.jsonl"),
    ]:
        if digest((root / path).read_bytes()) != lock[f"{key}_sha256"]:
            raise ValueError(f"Benchmark input changed: {path}")
    return lock


def run(root: Path, output: Path, lexical_only: bool = False) -> None:
    lock = validate_dataset(root)
    pages = read_jsonl(root / "data/processed/pages.jsonl")
    page_map = {(p["doc_id"], p["page"]): p for p in pages}
    tables = {t["id"]: t for t in read_jsonl(root / "data/processed/tables.jsonl")}
    documents = read_json(root / "data/corpus.json")["documents"]
    questions = read_jsonl(root / "data/questions.jsonl")
    models = Models(root)
    # Warmup excludes one-off model load. Query encoding remains in measured time.
    if not lexical_only:
        models.encoder.encode("warmup", normalize_embeddings=True)
        models.reranker.predict([("warmup", "warmup")], show_progress_bar=False)
    all_rows, results = [], []
    experiment_start = time.perf_counter()
    for strategy in ("fixed", "structure"):
        chunks = chunk_pages(pages, documents, strategy)
        write_jsonl(root / f"data/processed/chunks-{strategy}.jsonl", chunks)
        print(f"[cyan]Index[/cyan] {strategy}: {len(chunks):,} chunks")
        index_start = time.perf_counter()
        index = Index(chunks, models, dense=not lexical_only)
        index_seconds = time.perf_counter() - index_start
        for method in ["bm25"] if lexical_only else ["bm25", "dense", "hybrid"]:
            for rerank in [False] if lexical_only else [False, True]:
                config = f"{strategy}-{method}" + ("-rerank" if rerank else "")
                rows = []
                for q in questions:
                    start = time.perf_counter()
                    found = index.search(q["question"], method, pool=20, rerank=rerank)
                    response = answer_question(q["question"], found["chunks"], tables, documents)
                    query_ms = (time.perf_counter() - start) * 1000
                    row = {
                        "config": config,
                        "question_id": q["id"],
                        "question": q["question"],
                        "company": q["company"],
                        "kind": q["kind"],
                        "split": q["split"],
                        "answerable": q["answerable"],
                        "query_ms": query_ms,
                        "retrieval_ms": found["retrieval_ms"],
                        "rerank_ms": found["rerank_ms"],
                        **retrieval_metrics(found["chunks"], q["gold"]),
                        **score_answer(q, response, page_map),
                        "response": response,
                        "ranking": [
                            {key: c[key] for key in ["id", "doc_id", "page", "start", "end"]}
                            for c in found["chunks"]
                        ],
                    }
                    rows.append(row)
                all_rows.extend(rows)
                for split in ("dev", "test", "all"):
                    selected = rows if split == "all" else [r for r in rows if r["split"] == split]
                    results.append(
                        {
                            "config": config,
                            "chunking": strategy,
                            "retrieval": method,
                            "rerank": rerank,
                            "split": split,
                            "chunks": len(chunks),
                            "index_seconds_this_run": index_seconds,
                            **aggregate(selected),
                        }
                    )
                write_jsonl(output / "predictions.jsonl", all_rows)
                write_json(output / "metrics.json", results)
                print(
                    f"[green]Measured[/green] {config}: "
                    f"test R@5={results[-2]['recall_at_5']:.3f}, "
                    f"answer={results[-2]['answer_correctness']:.3f}"
                )
    dev = [r for r in results if r["split"] == "dev"]
    # Predeclared model selection: development recall, then development MRR,
    # then simpler configuration name. No test metrics enter selection.
    chosen = sorted(dev, key=lambda r: (-r["recall_at_5"], -r["mrr_at_20"], r["config"]))[0]
    baseline = [r for r in all_rows if r["config"] == "fixed-bm25" and r["split"] == "test"]
    selected = [r for r in all_rows if r["config"] == chosen["config"] and r["split"] == "test"]
    comparisons = [
        paired_company_bootstrap(baseline, selected, metric)
        for metric in ("recall_at_5", "mrr_at_20", "correct")
    ]
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    write_json(
        output / "run.json",
        {
            "started_date_utc": datetime.now(UTC).isoformat(),
            "duration_seconds": time.perf_counter() - experiment_start,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "torch_threads": 4,
            "seed": 17,
            "git_commit": commit.stdout.strip() if commit.returncode == 0 else None,
            "packages": {
                name: importlib.metadata.version(name)
                for name in ["numpy", "pymupdf", "sentence-transformers", "torch", "rank-bm25"]
            },
            "input_lock": lock,
            "model_lock": models.lock,
            "lexical_only": lexical_only,
            "source_lock_sha256": digest((root / "data/source-lock.json").read_bytes()),
            "chunk_size_words": 160,
            "fixed_overlap_words": 32,
            "candidate_pool": 20,
            "answer_context_k": 5,
            "rrf_constant": 60,
            "reader": "frozen extractive v1",
            "selection_rule": "dev recall@5, then dev MRR@20, then config name",
            "selected_on_dev": chosen["config"],
            "paired_test_comparisons": comparisons,
            "timing": (
                "warm models; cached document embeddings; query encoding and reader included; CPU"
            ),
        },
    )

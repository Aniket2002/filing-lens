"""Separate exploratory retrieval iteration; select on dev, seal before test.

The historical test set has already been inspected. Freezing this run prevents
further tuning between splits, but does not make it an independent validation.
"""

from __future__ import annotations

import importlib.metadata
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

from rich import print

from filing_lens.benchmark import validate_dataset
from filing_lens.chunking import chunk_pages
from filing_lens.evaluation import (
    aggregate,
    contains_gold,
    paired_company_bootstrap,
    retrieval_metrics,
    score_answer,
)
from filing_lens.io import digest, read_json, read_jsonl, write_json, write_jsonl
from filing_lens.reader import answer_question
from filing_lens.retrieval import Index, Models

SETTINGS = [
    {
        "id": "fixed-baseline-20",
        "chunking": "fixed",
        "method": "bm25",
        "profile": "baseline",
        "candidate_pool": 20,
    },
    {
        "id": "structure-baseline-20",
        "chunking": "structure",
        "method": "bm25",
        "profile": "baseline",
        "candidate_pool": 20,
    },
    {
        "id": "structure-entity-20",
        "chunking": "structure",
        "method": "bm25",
        "profile": "entity",
        "candidate_pool": 20,
    },
    {
        "id": "structure-entity-60",
        "chunking": "structure",
        "method": "bm25",
        "profile": "entity",
        "candidate_pool": 60,
    },
    {
        "id": "structure-finance-60",
        "chunking": "structure",
        "method": "bm25",
        "profile": "finance",
        "candidate_pool": 60,
    },
    {
        "id": "structure-hybrid-finance-60",
        "chunking": "structure",
        "method": "hybrid",
        "profile": "finance",
        "candidate_pool": 60,
    },
]


def fingerprints(root: Path) -> dict:
    paths = [
        "uv.lock",
        "pyproject.toml",
        "data/corpus.json",
        "data/questions.jsonl",
        "data/annotations.json",
        "data/processed/pages.jsonl",
        "data/processed/tables.jsonl",
        "data/model-lock.json",
        "data/benchmark-lock.json",
        "data/source-lock.json",
        *[
            f"src/filing_lens/{name}.py"
            for name in (
                "retrieval",
                "query_planning",
                "chunking",
                "reader",
                "numeric",
                "evaluation",
                "retrieval_study",
                "io",
                "benchmark",
            )
        ],
    ]
    return {path: digest((root / path).read_bytes()) for path in paths}


def select_on_dev(metrics: list[dict]) -> str:
    if not metrics or any(row["split"] != "dev" for row in metrics):
        raise ValueError("Selection requires development metrics only")
    return sorted(
        metrics,
        key=lambda row: (
            -row["recall_at_5"],
            -row["mrr_at_20"],
            row["candidate_pool"],
            row["config"],
        ),
    )[0]["config"]


def candidate_diagnostics(candidates: list[dict], chunks: list[dict], gold: list[dict]) -> dict:
    if not gold:
        return {"candidate_recall": None, "retrieval_failure": None}
    recall = sum(any(contains_gold(c, g) for c in candidates) for g in gold) / len(gold)
    final = retrieval_metrics(chunks, gold)["recall_at_5"]
    return {
        "candidate_recall": recall,
        "retrieval_failure": (
            "hit_at_5" if final == 1 else "candidate_miss" if recall < 1 else "ranking_miss"
        ),
    }


def verify_dev(output: Path, current: dict) -> dict:
    manifest = read_json(output / "dev/run.json")
    if manifest["fingerprints"] != current:
        raise ValueError("Implementation or inputs changed since development; use a new output")
    for name, expected in manifest["artifact_sha256"].items():
        if digest((output / "dev" / name).read_bytes()) != expected:
            raise ValueError(f"Development artifact changed: {name}")
    metrics = read_json(output / "dev/metrics.json")
    selected = select_on_dev(metrics)
    if selected != manifest["selected_on_dev"]:
        raise ValueError("Development selection does not match measured metrics")
    return manifest


def run_study(root: Path, output: Path, split: str) -> None:
    if split not in {"dev", "test"}:
        raise ValueError("split must be dev or test")
    destination = output / split
    if destination.exists():
        raise ValueError(f"Refusing to overwrite study artifacts: {destination}")
    validate_dataset(root)
    frozen = fingerprints(root)
    development = verify_dev(output, frozen) if split == "test" else None
    selected = development["selected_on_dev"] if development else None
    settings = (
        SETTINGS
        if split == "dev"
        else [
            setting
            for setting in SETTINGS
            if setting["id"] in {"fixed-baseline-20", "structure-baseline-20", selected}
        ]
    )
    pages = read_jsonl(root / "data/processed/pages.jsonl")
    page_map = {(p["doc_id"], p["page"]): p for p in pages}
    documents = read_json(root / "data/corpus.json")["documents"]
    tables = {t["id"]: t for t in read_jsonl(root / "data/processed/tables.jsonl")}
    questions = [q for q in read_jsonl(root / "data/questions.jsonl") if q["split"] == split]
    models = Models(root)
    models.reranker.predict([("warmup", "warmup")], show_progress_bar=False)
    if any(s["method"] != "bm25" for s in settings):
        models.encoder.encode("warmup", normalize_embeddings=True)
    # Reserve the directory before inference. Partial runs are never mistaken for completed ones.
    destination.mkdir(parents=True, exist_ok=False)
    rows, metrics, indexes = [], [], {}
    started = time.perf_counter()
    for setting in settings:
        key = (setting["chunking"], setting["method"] != "bm25")
        if key not in indexes:
            chunks = chunk_pages(pages, documents, setting["chunking"])
            indexes[key] = Index(chunks, models, dense=key[1], documents=documents)
        index = indexes[key]
        measured = []
        for q in questions:
            start = time.perf_counter()
            found = index.search(
                q["question"],
                method=setting["method"],
                rerank=True,
                candidate_pool=setting["candidate_pool"],
                profile=setting["profile"],
            )
            response = answer_question(
                q["question"], found["chunks"], tables, documents, assemble_table_evidence=True
            )
            elapsed = (time.perf_counter() - start) * 1000
            measured.append(
                {
                    "config": setting["id"],
                    "question_id": q["id"],
                    "question": q["question"],
                    "company": q["company"],
                    "kind": q["kind"],
                    "split": split,
                    "answerable": q["answerable"],
                    "query_ms": elapsed,
                    "retrieval_ms": found["retrieval_ms"],
                    "rerank_ms": found["rerank_ms"],
                    **retrieval_metrics(found["chunks"], q["gold"]),
                    **candidate_diagnostics(found["candidates"], found["chunks"], q["gold"]),
                    **score_answer(q, response, page_map),
                    "response": response,
                    "ranking": found["trace"],
                    "candidate_ranking": [
                        {key: c[key] for key in ("id", "doc_id", "page", "start", "end")}
                        for c in found["candidates"]
                    ],
                    "query_plan": found["query_plan"],
                    "eligible_chunks": found["eligible_chunks"],
                }
            )
        rows.extend(measured)
        answerable = [r for r in measured if r["answerable"]]
        metrics.append(
            {
                **setting,
                "config": setting["id"],
                "split": split,
                **aggregate(measured),
                "candidate_recall": sum(r["candidate_recall"] for r in answerable)
                / len(answerable),
                "failure_counts": {
                    name: sum(r["retrieval_failure"] == name for r in answerable)
                    for name in ("hit_at_5", "candidate_miss", "ranking_miss")
                },
            }
        )
        write_jsonl(destination / "predictions.jsonl", rows)
        write_json(destination / "metrics.json", metrics)
        print(
            f"{split} {setting['id']}: R@5={metrics[-1]['recall_at_5']:.3f}, "
            f"correct={metrics[-1]['answer_correctness']:.3f}",
            flush=True,
        )
    if fingerprints(root) != frozen:
        raise ValueError("Implementation or inputs changed during inference; run remains unsealed")
    selected = selected or select_on_dev(metrics)
    comparisons = []
    if split == "test":
        chosen = [row for row in rows if row["config"] == selected]
        for baseline in ("fixed-baseline-20", "structure-baseline-20"):
            control = [row for row in rows if row["config"] == baseline]
            comparisons.append(
                {
                    "baseline": baseline,
                    "selected": selected,
                    "metrics": [
                        paired_company_bootstrap(control, chosen, metric)
                        for metric in ("recall_at_5", "mrr_at_20", "correct")
                    ],
                }
            )
    write_json(
        destination / "run.json",
        {
            "created_utc": datetime.now(UTC).isoformat(),
            "split": split,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "duration_seconds": time.perf_counter() - started,
            "fingerprints": frozen,
            "settings": settings,
            "selected_on_dev": selected,
            "selection_rule": "dev recall@5, then MRR@20, then candidate pool, then config name",
            "artifact_sha256": {
                name: digest((destination / name).read_bytes())
                for name in ("metrics.json", "predictions.jsonl")
            },
            "development_manifest_sha256": digest((output / "dev/run.json").read_bytes())
            if split == "test"
            else None,
            "model_lock": models.lock,
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("numpy", "torch", "sentence-transformers", "rank-bm25")
            },
            "paired_comparisons": comparisons,
            "reader": "extractive with same-page table assembly; k=5 for every setting",
            "timing": "warm models, cached embeddings, sequential CPU; not a production SLA",
            "limitations": (
                "Exploratory on previously inspected AI-authored questions; no new holdout"
            ),
        },
    )
    print(f"Selected on development: {selected}")

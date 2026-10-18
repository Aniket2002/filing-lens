"""A separately frozen, development-first supplied-passage explanation study."""

from __future__ import annotations

import importlib.metadata
import time
from datetime import UTC, datetime
from pathlib import Path

from filing_lens.explanations import ExplanationReader, screen_concepts, summarize
from filing_lens.io import digest, read_json, read_jsonl, write_json, write_jsonl

FROZEN_FILES = [
    "data/explanations/questions.jsonl",
    "data/explanations/model-lock.json",
    "data/benchmark-lock.json",
    "src/filing_lens/explanations.py",
    "src/filing_lens/explanation_study.py",
    "src/filing_lens/generation.py",
    "scripts/prepare_explanation_challenge.py",
]


def fingerprint(root: Path) -> dict:
    return {path: digest((root / path).read_bytes()) for path in FROZEN_FILES}


def freeze(root: Path) -> None:
    from filing_lens.benchmark import validate_dataset

    protocol = root / "data/explanations/protocol.json"
    if protocol.exists():
        raise ValueError("Protocol already frozen; create a new version for revisions")
    validate_dataset(root)
    questions = read_jsonl(root / "data/explanations/questions.jsonl")
    pages = {(p["doc_id"], p["page"]): p for p in read_jsonl(root / "data/processed/pages.jsonl")}
    original = {q["question"] for q in read_jsonl(root / "data/questions.jsonl")}
    assert len(questions) == 40 == len({q["id"] for q in questions})
    assert not any(q["question"] in original for q in questions)
    assert {q["company"] for q in questions if q["split"] == "dev"}.isdisjoint(
        {q["company"] for q in questions if q["split"] == "test"}
    )
    for question in questions:
        for source in question["evidence"]:
            text = pages[(source["doc_id"], source["page"])]["text"]
            assert text[source["start"] : source["end"]] == source["quote"], question["id"]
    write_json(
        protocol,
        {
            "version": "explanations-1",
            "frozen_utc": datetime.now(UTC).isoformat(),
            "fingerprint": fingerprint(root),
            "questions": len(questions),
            "dev": 8,
            "test": 32,
            "test_companies": 8,
            "newness": (
                "New questions frozen before inference; source filings used in earlier studies"
            ),
            "authorship": "AI-authored, source-anchored; zero independent human adjudications",
            "unit": "Questions share ten passages; dev has two companies and test has eight",
            "input_policy": (
                "Supplied evidence only; no retrieval, extractive reader or numeric guard"
            ),
            "quality_metric": (
                "Automatic concept coverage screen; semantic correctness unadjudicated"
            ),
            "model_selection": "One predeclared model and prompt pair; no test-based tuning",
        },
    )


def run(root: Path, output: Path, split: str) -> None:
    if split not in {"dev", "test"}:
        raise ValueError("Choose dev or test")
    target = output / split
    if target.exists():
        raise ValueError(f"Output already exists: {target}")
    protocol = read_json(root / "data/explanations/protocol.json")
    current = fingerprint(root)
    if current != protocol["fingerprint"]:
        raise ValueError("Frozen challenge, prompts or implementation changed")
    if split == "test":
        dev = read_json(output / "dev/run.json")
        if dev["status"] != "complete" or dev["fingerprint"] != current:
            raise ValueError("Test requires a complete development run of the frozen protocol")
    questions = [
        q for q in read_jsonl(root / "data/explanations/questions.jsonl") if q["split"] == split
    ]
    metadata = {
        "created_utc": datetime.now(UTC).isoformat(),
        "fingerprint": current,
        "protocol": protocol,
        "split": split,
        "status": "running",
        "packages": {name: importlib.metadata.version(name) for name in ("torch", "transformers")},
    }
    write_json(target / "run.json", metadata)
    reader = ExplanationReader(root)
    rows = []
    for question in questions:
        start = time.perf_counter()
        response = reader.answer(question["question"], question["evidence"])
        rows.append(
            {
                "question_id": question["id"],
                "company": question["company"],
                "topic_id": question["topic_id"],
                "split": split,
                "answerable": question["answerable"],
                "response": response,
                "query_ms": (time.perf_counter() - start) * 1000,
                **screen_concepts(response["raw_generation"], question["concept_groups"]),
            }
        )
        write_jsonl(target / "predictions.jsonl", rows)
        print(
            f"{question['id']}: {response['raw_answerability']!r}; {response['raw_generation']!r}",
            flush=True,
        )
    write_json(target / "metrics.json", summarize(rows))
    write_json(target / "run.json", {**metadata, "status": "complete"})

"""Development-first generation audit; historical pilot artifacts stay untouched."""

from __future__ import annotations

import importlib.metadata
import time
from datetime import UTC, datetime
from pathlib import Path

from filing_lens.evaluation import aggregate, score_answer
from filing_lens.generation import LocalGenerator, gate_generated, generated_amount
from filing_lens.io import digest, read_json, read_jsonl, write_json, write_jsonl
from filing_lens.numeric import number
from filing_lens.reader import answer_question


def generation_context(candidate: dict, chunks: list[dict], tables: dict, documents: dict) -> str:
    """Serialize all columns of a retrieved row, never the expected answer or gold."""
    if candidate["refused"] or not candidate["claims"]:
        return "\n".join(c["text"][:600] for c in chunks[:2])
    claim = candidate["claims"][0]
    table = tables[claim["table_id"]]
    row = table["rows"][claim["row_index"]]
    records = [
        f"Company: {documents[claim['doc_id']]['company']}",
        f"Source: {claim['doc_id']}, PDF page {claim['page']}",
        f"Metric: {row[0]}",
        f"Unit: {claim['unit']}",
    ]
    records.extend(
        f"FY{year}: {value}" if (value := number(raw)) is not None else f"FY{year}: unavailable"
        for year, raw in zip(table["years"], row[1:], strict=True)
    )
    return "\n".join(records)


def experiment_fingerprint(root: Path) -> dict:
    paths = [
        "data/generator-v2-lock.json",
        "data/questions.jsonl",
        "data/benchmark-lock.json",
        "results/reference/predictions.jsonl",
        "src/filing_lens/generation.py",
        "src/filing_lens/generator_experiment.py",
        "src/filing_lens/reader.py",
        "src/filing_lens/numeric.py",
        "src/filing_lens/evaluation.py",
    ]
    return {path: digest((root / path).read_bytes()) for path in paths}


def audit(root: Path, output: Path, split: str) -> None:
    from filing_lens.benchmark import validate_dataset

    if split not in {"dev", "test"}:
        raise ValueError("Choose dev or test")
    target = output / split
    if target.exists():
        raise ValueError(f"Output already exists: {target}; use a new experiment directory")
    validate_dataset(root)
    fingerprint = experiment_fingerprint(root)
    if split == "test":
        dev = read_json(output / "dev/run.json")
        if dev["fingerprint"] != fingerprint:
            raise ValueError(
                "Implementation or inputs changed after development; rerun dev separately"
            )
    lock_path = root / "data/generator-v2-lock.json"
    lock = read_json(lock_path)
    config = lock["retrieval_config"]
    questions = {q["id"]: q for q in read_jsonl(root / "data/questions.jsonl")}
    predictions = [
        r
        for r in read_jsonl(root / "results/reference/predictions.jsonl")
        if r["config"] == config and r["split"] == split and r["kind"] != "narrative"
    ]
    chunks = {c["id"]: c for c in read_jsonl(root / "data/processed/chunks-fixed.jsonl")}
    tables = {t["id"]: t for t in read_jsonl(root / "data/processed/tables.jsonl")}
    pages = {(p["doc_id"], p["page"]): p for p in read_jsonl(root / "data/processed/pages.jsonl")}
    documents = read_json(root / "data/corpus.json")["documents"]
    doc_map = {d["id"]: d for d in documents}
    generator = LocalGenerator(root, lock_path)
    rows = []
    for prediction in predictions:
        question = questions[prediction["question_id"]]
        retrieved = [chunks[c["id"]] for c in prediction["ranking"][:5]]
        start = time.perf_counter()
        candidate = answer_question(
            question["question"],
            retrieved,
            tables,
            documents,
            assemble_table_evidence=lock["assemble_table_evidence"],
        )
        context = generation_context(candidate, retrieved, tables, doc_map)
        prompt = lock["prompt_template"].format(question=question["question"], context=context)
        input_tokens = len(generator.tokenizer(prompt)["input_ids"])
        raw = generator.generate(question["question"], context)
        response = gate_generated(raw, candidate, tables, doc_map)
        amount = generated_amount(raw)
        rows.append(
            {
                **{
                    key: prediction[key]
                    for key in (
                        "config",
                        "question_id",
                        "company",
                        "kind",
                        "split",
                        "answerable",
                        "recall_at_1",
                        "recall_at_5",
                        "recall_at_10",
                        "mrr_at_20",
                    )
                },
                "raw_output": raw,
                "raw_amount": str(amount) if amount is not None else None,
                "raw_correct": (
                    amount is not None and amount == number(question["expected_value"])
                    if question["answerable"]
                    else raw.strip() == "UNKNOWN"
                ),
                "context": context,
                "input_tokens": input_tokens,
                "input_truncated": input_tokens > lock["max_input_tokens"],
                "candidate_available": bool(candidate["claims"]) and not candidate["refused"],
                "response": response,
                "query_ms": (time.perf_counter() - start) * 1000,
                **score_answer(question, response, pages),
            }
        )
        print(
            f"{question['id']}: {raw!r} -> {'refuse' if response['refused'] else 'verified'}",
            flush=True,
        )
    numeric = [r for r in rows if r["answerable"]]
    negatives = [r for r in rows if not r["answerable"]]
    candidates = [r for r in numeric if r["candidate_available"]]
    write_jsonl(target / "predictions.jsonl", rows)
    write_json(
        target / "metrics.json",
        {
            "split": split,
            **aggregate(rows),
            "raw_amount_correctness": sum(r["raw_correct"] for r in numeric) / len(numeric),
            "raw_exact_abstention_rate": sum(r["raw_correct"] for r in negatives) / len(negatives),
            "candidate_available": len(candidates),
            "raw_correct_given_candidate": (
                sum(r["raw_correct"] for r in candidates) / len(candidates) if candidates else None
            ),
            "truncated_inputs": sum(r["input_truncated"] for r in rows),
        },
    )
    write_json(
        target / "run.json",
        {
            "created_utc": datetime.now(UTC).isoformat(),
            "generator_lock": lock,
            "fingerprint": fingerprint,
            "scope": "numeric and unanswerable only; row-assisted amount generation",
            "timing": (
                "CPU, four threads; candidate reader and generation; cached retrieval excluded"
            ),
            "packages": {
                name: importlib.metadata.version(name) for name in ("torch", "transformers")
            },
            "test_reuse": (
                "Previously inspected test split; exploratory, not independent validation"
            ),
        },
    )

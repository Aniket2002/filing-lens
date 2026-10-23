"""Typed financial interventions and a label-blind cell decoding pilot.

All interventions are synthetic. Original evidence and earlier runs stay immutable.
The inference boundary accepts only a question, requested unit, and visible cells.
"""

from __future__ import annotations

import random
import time
from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import numpy as np

from filing_lens.generation import LocalGenerator, generated_amount
from filing_lens.io import digest, read_json, read_jsonl, write_json, write_jsonl
from filing_lens.numeric import matches_metric, number, row_unit

METRICS = ("revenue", "net_income", "research_development", "total_assets", "diluted_eps")
SCALES = {"USD": Decimal(1), "USD_thousands": Decimal(1000), "USD_millions": Decimal(1000000)}
PRESERVING = ("column_reverse", "unit_rescale", "reverse_and_rescale")
STUDY = "research/equivariance"
INPUTS = (
    "src/filing_lens/equivariance.py",
    "src/filing_lens/generation.py",
    "src/filing_lens/numeric.py",
    "src/filing_lens/io.py",
    "scripts/run_equivariance.py",
    f"{STUDY}/protocol.json",
    "data/evidence/statement-tables.jsonl",
    "data/questions.jsonl",
    "data/corpus.json",
    "results/retrieval-v2/dev/predictions.jsonl",
    "results/retrieval-v2/test/predictions.jsonl",
    "uv.lock",
)


def decimal_text(value: Decimal) -> str:
    return format(value, "f").rstrip("0").rstrip(".") if value % 1 else str(int(value))


def convert(value: str, source: str, target: str) -> str:
    amount = number(value)
    if amount is None:
        raise ValueError("Non-numeric cell")
    if source == target:
        return decimal_text(amount)
    if source not in SCALES or target not in SCALES:
        raise ValueError("Incompatible dimensions")
    return decimal_text(amount * SCALES[source] / SCALES[target])


def extract_cells(tables: list[dict], companies: dict) -> list[dict]:
    cells = []
    for table in tables:
        for r, row in enumerate(table["rows"][1:], 1):
            matched = [metric for metric in METRICS if matches_metric(row[0], metric)]
            if not matched:
                continue
            if len(matched) != 1:
                raise ValueError("Ambiguous metric mapping")
            for c, year in enumerate(table["years"], 1):
                value = number(row[c])
                if value is None:
                    continue
                cells.append(
                    {
                        "key": f"{table['id']}:r{r}:c{c}",
                        "table_id": table["id"],
                        "doc_id": table["doc_id"],
                        "company": companies[table["doc_id"]],
                        "page": table["page"],
                        "row": r,
                        "column": c,
                        "label": row[0],
                        "metric": matched[0],
                        "period": year,
                        "unit": row_unit(table, row[0]),
                        "value": decimal_text(value),
                        "table_years": table["years"],
                    }
                )
    # Opaque identifiers depend only on source coordinates, never on answer labels.
    keys = sorted(c["key"] for c in cells)
    random.Random(17).shuffle(keys)
    identifiers = {key: f"C{i + 1:03d}" for i, key in enumerate(keys)}
    return [{**cell, "id": identifiers[cell["key"]]} for cell in cells]


def intervene(cells: list[dict], variant: str, period: int) -> list[dict]:
    result = deepcopy(cells)
    if variant in {"column_reverse", "reverse_and_rescale"}:
        # Reverse columns within each row; preserve row order and identity.
        rows = defaultdict(list)
        for cell in result:
            rows[(cell["table_id"], cell["row"])].append(cell)
        result = [cell for group in rows.values() for cell in reversed(group)]
    if variant in {"unit_rescale", "reverse_and_rescale"}:
        for cell in result:
            if cell["unit"] in SCALES:
                target = "USD_thousands" if cell["unit"] == "USD_millions" else "USD_millions"
                cell["value"] = convert(cell["value"], cell["unit"], target)
                cell["unit"] = target
    if variant == "period_rebind":
        for cell in result:
            years = cell["table_years"]
            cell["period"] = years[(years.index(cell["period"]) + 1) % len(years)]
    elif variant == "remove_period":
        result = [cell for cell in result if cell["period"] != period]
    elif variant not in {"base", *PRESERVING}:
        raise ValueError(f"Unknown intervention: {variant}")
    return result


def infer_input(question: str, unit: str, cells: list[dict], arm: str) -> tuple[str, str]:
    """No expected value, gold page, target ID, or annotation enters this function."""
    if arm not in {"native_amount", "canonical_amount", "native_pointer", "canonical_pointer"}:
        raise ValueError("Unknown arm")
    visible = deepcopy(cells)
    if arm.startswith("canonical"):
        for cell in visible:
            if cell["unit"] in SCALES:
                target = unit if unit in SCALES else "USD_millions"
                cell["value"] = convert(cell["value"], cell["unit"], target)
                cell["unit"] = target
        visible.sort(key=lambda c: (c["doc_id"], c["metric"], c["period"], c["key"]))
    instruction = (
        "Return only the ID of the cell answering the question, for example C003."
        if arm.endswith("pointer")
        else (
            f"Return only the signed numeric answer in {unit.replace('_', ' ')}. "
            "Convert units if needed."
        )
    )
    instruction += " If no cell answers the question, return UNKNOWN."
    lines = [
        f"{c['id']} | {c['company']} | {c['label']} | FY{c['period']} | "
        f"{c['value']} | {c['unit'].replace('_', ' ')}"
        for c in visible
    ]
    return f"{question}\n{instruction}", "\n".join(lines) or "No financial records available."


def decode(raw: str, cells: list[dict], unit: str, arm: str) -> dict:
    raw = raw.strip()
    if raw == "UNKNOWN":
        return {"value": None, "selected_id": None, "status": "abstain"}
    if arm.endswith("pointer"):
        cell = next((c for c in cells if c["id"] == raw), None)
        if cell is None:
            return {"value": None, "selected_id": None, "status": "invalid"}
        try:
            value = convert(cell["value"], cell["unit"], unit)
        except ValueError:
            return {"value": None, "selected_id": raw, "status": "dimension_error"}
        return {"value": value, "selected_id": raw, "status": "numeric"}
    value = generated_amount(raw)
    return {
        "value": decimal_text(value) if value is not None else None,
        "selected_id": None,
        "status": "numeric" if value is not None else "invalid",
    }


def score(case: dict, output: dict) -> dict:
    value = output["value"]
    correct = value == case["expected_value"] if value is not None else False
    context_correct = (
        correct if case["expected_value"] is not None else output["status"] == "abstain"
    )
    task_correct = (
        value == case["task_value"]
        if case["task_value"] is not None
        else output["status"] == "abstain"
    )
    return {
        "usable_correct": correct,
        "context_correct": context_correct,
        "task_correct": task_correct,
        "coordinate_correct": output["selected_id"] in case["target_ids"],
    }


def build_cases(root: Path) -> list[dict]:
    protocol = read_json(root / STUDY / "protocol.json")
    companies = {d["id"]: d["company"] for d in read_json(root / "data/corpus.json")["documents"]}
    cells = extract_cells(read_jsonl(root / "data/evidence/statement-tables.jsonl"), companies)
    rankings = {
        p["question_id"]: p["ranking"][: protocol["retrieval_k"]]
        for split in ("dev", "test")
        for p in read_jsonl(root / f"results/retrieval-v2/{split}/predictions.jsonl")
        if p["config"] == protocol["retrieval_config"]
    }
    cases = []
    for q in read_jsonl(root / "data/questions.jsonl"):
        if q["kind"] != "numeric":
            continue
        gold_pages = {(g["doc_id"], g["page"]) for g in q["gold"]}
        source_cells = [c for c in cells if (c["doc_id"], c["page"]) in gold_pages]
        original = [
            c for c in source_cells if c["metric"] == q["metric"] and c["period"] == q["period"]
        ]
        if not original or {number(c["value"]) for c in original} != {number(q["expected_value"])}:
            raise ValueError(f"Ambiguous or inconsistent source annotation: {q['id']}")
        for source in protocol["sources"]:
            pages = (
                gold_pages
                if source == "oracle_page"
                else {(p["doc_id"], p["page"]) for p in rankings[q["id"]]}
            )
            evidence = [c for c in cells if (c["doc_id"], c["page"]) in pages]
            for variant in protocol["variants"]:
                modified = intervene(evidence, variant, q["period"])
                truth = [
                    c
                    for c in intervene(source_cells, variant, q["period"])
                    if c["metric"] == q["metric"] and c["period"] == q["period"]
                ]
                if len({convert(c["value"], c["unit"], q["expected_unit"]) for c in truth}) > 1:
                    raise ValueError("Ambiguous transformed truth")
                task_value = (
                    convert(truth[0]["value"], truth[0]["unit"], q["expected_unit"])
                    if truth
                    else None
                )
                target_ids = [
                    c["id"]
                    for c in modified
                    if task_value is not None
                    and c["doc_id"] in {g["doc_id"] for g in q["gold"]}
                    and c["metric"] == q["metric"]
                    and c["period"] == q["period"]
                    and convert(c["value"], c["unit"], q["expected_unit"]) == task_value
                ]
                cases.append(
                    {
                        "id": f"{q['id']}:{source}:{variant}",
                        "question_id": q["id"],
                        "question": q["question"],
                        "company": q["company"],
                        "split": q["split"],
                        "metric": q["metric"],
                        "period": q["period"],
                        "source": source,
                        "variant": variant,
                        "unit": q["expected_unit"],
                        "cells": modified,
                        "expected_value": task_value if target_ids else None,
                        "task_value": task_value,
                        "target_ids": target_ids,
                        "synthetic": variant != "base",
                        "source_pages": [list(page) for page in sorted(pages)],
                    }
                )
    return cases


def fingerprints(root: Path) -> dict:
    return {path: digest((root / path).read_bytes()) for path in INPUTS}


def prepare(root: Path) -> None:
    folder = root / STUDY
    if (folder / "dataset.jsonl").exists() or (folder / "freeze.json").exists():
        raise FileExistsError("Study already frozen; use a new study directory/version")
    cases = build_cases(root)
    write_jsonl(folder / "dataset.jsonl", cases)
    write_json(
        folder / "freeze.json",
        {
            "inputs": fingerprints(root),
            "dataset_sha256": digest((folder / "dataset.jsonl").read_bytes()),
            "cases": len(cases),
        },
    )
    print(f"Frozen {len(cases)} cases before model inference", flush=True)


def validate_freeze(root: Path) -> list[dict]:
    frozen = read_json(root / STUDY / "freeze.json")
    if frozen["inputs"] != fingerprints(root):
        raise ValueError("Frozen study inputs changed")
    data = root / STUDY / "dataset.jsonl"
    if digest(data.read_bytes()) != frozen["dataset_sha256"]:
        raise ValueError("Frozen dataset changed")
    cases = read_jsonl(data)
    if cases != build_cases(root):
        raise ValueError("Dataset does not reproduce from evidence")
    return cases


def summarize(rows: list[dict]) -> dict:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["source"], row["arm"], row["variant"])].append(row)
    summary = []
    for (source, arm, variant), group in sorted(groups.items()):
        base = {r["question_id"]: r for r in groups[(source, arm, "base")]}
        summary.append(
            {
                "source": source,
                "arm": arm,
                "variant": variant,
                "n": len(group),
                **{
                    field: sum(r[field] for r in group) / len(group)
                    for field in ("usable_correct", "context_correct", "task_correct")
                },
                "coverage": sum(r["output"]["status"] == "numeric" for r in group) / len(group),
                "invalid_rate": sum(
                    r["output"]["status"] in {"invalid", "dimension_error"} for r in group
                )
                / len(group),
                "paired_usable": sum(
                    r["usable_correct"] and base[r["question_id"]]["usable_correct"] for r in group
                )
                / len(group),
                "same_output": sum(
                    r["output"]["value"] == base[r["question_id"]]["output"]["value"]
                    and r["output"]["status"] == base[r["question_id"]]["output"]["status"]
                    for r in group
                )
                / len(group),
            }
        )
    paired = {}
    for arm in ("native_amount", "canonical_pointer"):
        base = {r["question_id"]: r for r in groups[("retrieved_pages", arm, "base")]}
        paired[arm] = {
            r["question_id"]: (
                r["company"],
                int(r["usable_correct"] and base[r["question_id"]]["usable_correct"]),
            )
            for r in groups[("retrieved_pages", arm, "unit_rescale")]
        }
    deltas = defaultdict(list)
    for key, (company, value) in paired["canonical_pointer"].items():
        deltas[company].append(value - paired["native_amount"][key][1])
    company_means = [sum(v) / len(v) for _, v in sorted(deltas.items())]
    rng = np.random.default_rng(17)
    samples = [
        float(np.mean(rng.choice(company_means, len(company_means), replace=True)))
        for _ in range(2000)
    ]
    return {
        "groups": summary,
        "primary_contrast": {
            "delta": float(np.mean(company_means)),
            "ci95": np.quantile(samples, [0.025, 0.975]).tolist(),
            "companies": len(company_means),
            "method": "paired company-cluster bootstrap, 2000 resamples, seed17",
        },
        "rows": len(rows),
    }


def run(root: Path, split: str, model: str) -> None:
    cases = [c for c in validate_freeze(root) if c["split"] == split]
    protocol = read_json(root / STUDY / "protocol.json")
    folder = root / f"results/equivariance/{model}/{split}"
    if folder.exists():
        raise FileExistsError("Existing run is immutable")
    if split == "test" and not (folder.parent / "dev/run.json").exists():
        raise ValueError("Complete development run before test")
    folder.mkdir(parents=True)
    lock = {**protocol, **protocol["models"][model]}
    write_json(folder / "model-lock.json", lock)
    generator = LocalGenerator(root, folder / "model-lock.json")
    rows, cache = [], {}
    start = time.perf_counter()
    for case in cases:
        for arm in protocol["arms"]:
            question, context = infer_input(case["question"], case["unit"], case["cells"], arm)
            prompt = lock["prompt_template"].format(question=question, context=context)
            token_count = len(generator.tokenizer(prompt)["input_ids"])
            if token_count > lock["max_input_tokens"]:
                raise ValueError(f"Context would truncate: {case['id']} / {arm}: {token_count}")
            key = digest(prompt.encode())
            cached = key in cache
            if not cached:
                cache[key] = generator.generate(question, context)
            output = decode(cache[key], case["cells"], case["unit"], arm)
            rows.append(
                {
                    **{
                        k: case[k]
                        for k in ("id", "question_id", "company", "split", "source", "variant")
                    },
                    "arm": arm,
                    "raw": cache[key],
                    "output": output,
                    **score(case, output),
                    "prompt_sha256": key,
                    "input_tokens": token_count,
                    "cached": cached,
                }
            )
        if len(rows) % 120 == 0:
            print(
                f"{model}/{split}: {len(rows)}/{len(cases) * len(protocol['arms'])} outcomes; "
                f"{len(cache)} distinct prompts",
                flush=True,
            )
    write_jsonl(folder / "predictions.jsonl", rows)
    write_json(folder / "metrics.json", summarize(rows))
    write_json(
        folder / "run.json",
        {
            "model": model,
            "split": split,
            "freeze_sha256": digest((root / STUDY / "freeze.json").read_bytes()),
            "files": {
                name: digest((folder / name).read_bytes())
                for name in ("predictions.jsonl", "metrics.json", "model-lock.json")
            },
            "outcomes": len(rows),
            "inference_calls": len(cache),
            "max_input_tokens_observed": max(r["input_tokens"] for r in rows),
            "elapsed_seconds": time.perf_counter() - start,
            "note": (
                "Identical deterministic prompts reused within this run; "
                "no stochastic robustness inference."
            ),
        },
    )


def audit(root: Path) -> int:
    cases = {c["id"]: c for c in validate_freeze(root)}
    protocol = read_json(root / STUDY / "protocol.json")
    count = 0
    for path in sorted((root / "results/equivariance").glob("*/*/run.json")):
        run_record = read_json(path)
        if run_record["freeze_sha256"] != digest((root / STUDY / "freeze.json").read_bytes()):
            raise ValueError("Run freeze mismatch")
        for name, checksum in run_record["files"].items():
            if digest((path.parent / name).read_bytes()) != checksum:
                raise ValueError(f"Run artifact changed: {name}")
        lock = read_json(path.parent / "model-lock.json")
        if lock != {**protocol, **protocol["models"][run_record["model"]]}:
            raise ValueError("Model lock mismatch")
        rows = read_jsonl(path.parent / "predictions.jsonl")
        expected = {
            (c["id"], arm)
            for c in cases.values()
            if c["split"] == run_record["split"]
            for arm in protocol["arms"]
        }
        if len(rows) != len(expected) or {(r["id"], r["arm"]) for r in rows} != expected:
            raise ValueError("Missing or duplicated outcomes")
        seen = {}
        for row in rows:
            case = cases[row["id"]]
            question, context = infer_input(
                case["question"], case["unit"], case["cells"], row["arm"]
            )
            key = digest(
                lock["prompt_template"].format(question=question, context=context).encode()
            )
            if row["prompt_sha256"] != key or row["cached"] != (key in seen):
                raise ValueError("Prompt or cache mismatch")
            if key in seen and row["raw"] != seen[key]:
                raise ValueError("Inconsistent cached prediction")
            seen[key] = row["raw"]
            output = decode(row["raw"], case["cells"], case["unit"], row["arm"])
            if row["output"] != output or any(row[k] != v for k, v in score(case, output).items()):
                raise ValueError("Prediction score mismatch")
            if any(
                row[k] != case[k] for k in ("question_id", "company", "split", "source", "variant")
            ):
                raise ValueError("Prediction metadata mismatch")
        if read_json(path.parent / "metrics.json") != summarize(rows):
            raise ValueError("Metric mismatch")
        if run_record["inference_calls"] != len(seen) or run_record["outcomes"] != len(rows):
            raise ValueError("Run count mismatch")
        count += len(rows)
    return count

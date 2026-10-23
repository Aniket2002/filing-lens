"""Freeze, run and audit matched original LLM readers after rebuilt retrieval."""

from __future__ import annotations

import argparse
import json
import random
import time
from datetime import UTC, datetime
from pathlib import Path

from filing_lens.document_interventions import parse_cells, requested_unit
from filing_lens.equivariance import decode, infer_input
from filing_lens.generation import LocalGenerator
from filing_lens.io import digest, read_json, read_jsonl, write_json, write_jsonl
from filing_lens.numeric import number
from filing_lens.reader import resolve_question

STUDY = "research/document-llms"
RESULTS = "results/document-llms"
INPUTS = (
    "scripts/run_document_llms.py",
    "src/filing_lens/document_interventions.py",
    "src/filing_lens/equivariance.py",
    "src/filing_lens/generation.py",
    "src/filing_lens/numeric.py",
    "src/filing_lens/reader.py",
    "src/filing_lens/io.py",
    "data/corpus.json",
    "data/questions.jsonl",
    "results/document-interventions/predictions.jsonl",
    "results/document-interventions/evidence.jsonl",
    "results/document-interventions/manifest.json",
    f"{STUDY}/protocol.json",
    "uv.lock",
)


def fingerprint(root: Path) -> dict:
    return {p: digest((root / p).read_bytes()) for p in INPUTS}


def build_cases(root: Path) -> list[dict]:
    manifest = read_json(root / "results/document-interventions/manifest.json")
    for path, expected in {**manifest["inputs"], **manifest["outputs"]}.items():
        if digest((root / path).read_bytes()) != expected:
            raise ValueError(f"Upstream retrieval artifact changed: {path}")
    questions = {q["id"]: q for q in read_jsonl(root / "data/questions.jsonl")}
    documents = read_json(root / "data/corpus.json")["documents"]
    companies = {d["id"]: d["company"] for d in documents}
    evidence = {
        r["key"]: r["chunk"]
        for r in read_jsonl(root / "results/document-interventions/evidence.jsonl")
    }
    cases = []
    for ranking in read_jsonl(root / "results/document-interventions/predictions.jsonl"):
        if ranking["strategy"] != "structure":
            continue
        q = questions[ranking["question_id"]]
        unit = requested_unit(q["question"], resolve_question(q["question"], documents)["metric"])
        if unit is None:
            raise ValueError(f"Question has no supported explicit unit: {q['id']}")
        cells = {}
        chunks = [evidence[key] for key in ranking["evidence_keys"]]
        for c in parse_cells(chunks):
            key = json.dumps([c[k] for k in ("doc_id", "page", "row_label", "metric", "year")])
            cell = {
                "key": key,
                "doc_id": c["doc_id"],
                "page": c["page"],
                "company": companies[c["doc_id"]],
                "label": c["row_label"],
                "metric": c["metric"],
                "period": c["year"],
                "unit": c["unit"],
                "value": c["value"],
            }
            if key in cells and cells[key] != cell:
                raise ValueError("Conflicting duplicate coordinates require a different adapter")
            cells[key] = cell
        cases.append(
            {
                "id": f"{q['id']}:{ranking['view']}:{ranking['variant']}",
                "question_id": q["id"],
                "question": q["question"],
                "split": q["split"],
                "company": q["company"],
                "view": ranking["view"],
                "variant": ranking["variant"],
                "unit": unit,
                "cells": list(cells.values()),
                "evidence_keys": ranking["evidence_keys"],
                "expected_value": q["expected_value"],
                "expected_unit": q["expected_unit"],
                "gold_pages": [[g["doc_id"], g["page"]] for g in q["gold"]],
                "metric": q["metric"],
                "period": q["period"],
            }
        )
    keys = sorted({c["key"] for case in cases for c in case["cells"]})
    random.Random(17).shuffle(keys)
    ids = {key: f"C{i + 1:03d}" for i, key in enumerate(keys)}
    for case in cases:
        for cell in case["cells"]:
            cell["id"] = ids[cell["key"]]
    return cases


def cases_digest(cases: list[dict]) -> str:
    return digest(json.dumps(cases, sort_keys=True, ensure_ascii=False).encode())


def prepare(root: Path) -> None:
    target = root / STUDY / "freeze.json"
    if target.exists():
        raise FileExistsError("Study already frozen")
    cases = build_cases(root)
    if len(cases) != 400 or len({c["id"] for c in cases}) != 400:
        raise ValueError("Expected 50 questions x 2 retrieval views x 4 variants")
    write_json(
        target,
        {
            "created_utc": datetime.now(UTC).isoformat(),
            "inputs": fingerprint(root),
            "case_count": len(cases),
            "cases_sha256": cases_digest(cases),
            "status": "Local execution freeze on reused exploratory data; not preregistration",
        },
    )
    print(f"Frozen {len(cases)} matched retrieval cases")


def validate(root: Path) -> list[dict]:
    freeze = read_json(root / STUDY / "freeze.json")
    cases = build_cases(root)
    if freeze["inputs"] != fingerprint(root) or freeze["cases_sha256"] != cases_digest(cases):
        raise ValueError("Frozen inputs or prepared cases changed")
    if freeze["case_count"] != len(cases):
        raise ValueError("Case count changed")
    return cases


def score(case: dict, output: dict) -> dict:
    targets = {
        c["id"]
        for c in case["cells"]
        if [c["doc_id"], c["page"]] in case["gold_pages"]
        and c["metric"] == case["metric"]
        and c["period"] == case["period"]
    }
    return {
        "correct": output["status"] == "numeric"
        and case["unit"] == case["expected_unit"]
        and number(output["value"]) == number(case["expected_value"]),
        "coordinate_correct": output["selected_id"] in targets,
        "target_available": bool(targets),
    }


def summarize(rows: list[dict]) -> list[dict]:
    base = {(r["question_id"], r["view"], r["arm"]): r for r in rows if r["variant"] == "base"}
    groups = sorted({(r["split"], r["view"], r["arm"], r["variant"]) for r in rows})
    result = []
    for split, view, arm, variant in groups:
        subset = [
            r
            for r in rows
            if (r["split"], r["view"], r["arm"], r["variant"]) == (split, view, arm, variant)
        ]
        result.append(
            {
                "split": split,
                "view": view,
                "arm": arm,
                "variant": variant,
                "n": len(subset),
                "correct": sum(r["scores"]["correct"] for r in subset),
                "paired_correct": sum(
                    r["scores"]["correct"]
                    and base[r["question_id"], view, arm]["scores"]["correct"]
                    for r in subset
                ),
                "regressions": sum(
                    not r["scores"]["correct"]
                    and base[r["question_id"], view, arm]["scores"]["correct"]
                    for r in subset
                ),
                "coordinate_correct": sum(r["scores"]["coordinate_correct"] for r in subset),
                "target_available": sum(r["scores"]["target_available"] for r in subset),
            }
        )
    return result


def run(root: Path, model: str) -> None:
    cases = validate(root)
    protocol = read_json(root / STUDY / "protocol.json")
    folder = root / RESULTS / model
    if folder.exists():
        raise FileExistsError("Run already exists")
    lock = {**protocol, **protocol["models"][model]}
    write_json(folder / "model-lock.json", lock)
    generator = LocalGenerator(root, folder / "model-lock.json")
    rows, cache = [], {}
    started_utc = datetime.now(UTC).isoformat()
    start = time.perf_counter()
    for split in ("dev", "test"):
        for case in (c for c in cases if c["split"] == split):
            for arm in protocol["arms"]:
                # Explicit label-free inference boundary, identical to the original pilot.
                question, context = infer_input(case["question"], case["unit"], case["cells"], arm)
                prompt = lock["prompt_template"].format(question=question, context=context)
                tokens = len(generator.tokenizer(prompt)["input_ids"])
                if tokens > lock["max_input_tokens"]:
                    raise ValueError(f"Input would truncate: {case['id']}/{arm}")
                key = digest(prompt.encode())
                cached = key in cache
                if not cached:
                    cache[key] = generator.generate(question, context)
                output = decode(cache[key], case["cells"], case["unit"], arm)
                rows.append(
                    {
                        **{
                            k: case[k]
                            for k in ("id", "question_id", "split", "company", "view", "variant")
                        },
                        "arm": arm,
                        "raw": cache[key],
                        "output": output,
                        "scores": score(case, output),
                        "prompt_sha256": key,
                        "input_tokens": tokens,
                        "cached": cached,
                    }
                )
            if len(rows) % 100 == 0:
                print(
                    f"{model}: {len(rows)}/1600 outcomes; {len(cache)} distinct prompts", flush=True
                )
    write_jsonl(folder / "predictions.jsonl", rows)
    write_json(folder / "metrics.json", summarize(rows))
    write_json(
        folder / "run.json",
        {
            "model": model,
            "started_utc": started_utc,
            "elapsed_seconds": time.perf_counter() - start,
            "freeze_sha256": digest((root / STUDY / "freeze.json").read_bytes()),
            "files": {
                p: digest((folder / p).read_bytes())
                for p in ("model-lock.json", "predictions.jsonl", "metrics.json")
            },
            "outcomes": len(rows),
            "inference_calls": len(cache),
            "max_input_tokens_observed": max(r["input_tokens"] for r in rows),
            "note": "Identical-prompt reuse within model; outcomes are not independent trials",
        },
    )


def audit(root: Path) -> dict:
    cases = {c["id"]: c for c in validate(root)}
    protocol = read_json(root / STUDY / "protocol.json")
    summaries = {}
    for model in protocol["models"]:
        folder = root / RESULTS / model
        record = read_json(folder / "run.json")
        if record["freeze_sha256"] != digest((root / STUDY / "freeze.json").read_bytes()):
            raise ValueError("Run freeze differs")
        for path, expected in record["files"].items():
            if digest((folder / path).read_bytes()) != expected:
                raise ValueError(f"Changed model artifact: {model}/{path}")
        lock = read_json(folder / "model-lock.json")
        if lock != {**protocol, **protocol["models"][model]}:
            raise ValueError("Model settings changed")
        rows = read_jsonl(folder / "predictions.jsonl")
        expected = {(c, a) for c in cases for a in protocol["arms"]}
        if len(rows) != len(expected) or {(r["id"], r["arm"]) for r in rows} != expected:
            raise ValueError("Missing or duplicate outcome")
        cache = {}
        for row in rows:
            case = cases[row["id"]]
            if any(
                row[k] != case[k] for k in ("question_id", "split", "company", "view", "variant")
            ):
                raise ValueError("Outcome grouping changed")
            q, context = infer_input(case["question"], case["unit"], case["cells"], row["arm"])
            key = digest(lock["prompt_template"].format(question=q, context=context).encode())
            output = decode(row["raw"], case["cells"], case["unit"], row["arm"])
            if (
                key != row["prompt_sha256"]
                or output != row["output"]
                or score(case, output) != row["scores"]
            ):
                raise ValueError("Prompt, decoding or score mismatch")
            if row["cached"] != (key in cache) or (key in cache and cache[key] != row["raw"]):
                raise ValueError("Invalid deterministic cache record")
            if not 0 < row["input_tokens"] <= lock["max_input_tokens"]:
                raise ValueError("Invalid recorded token count")
            cache[key] = row["raw"]
        if len(cache) != record["inference_calls"] or len(rows) != record["outcomes"]:
            raise ValueError("Outcome or call count changed")
        summary = summarize(rows)
        if summary != read_json(folder / "metrics.json"):
            raise ValueError("Aggregate mismatch")
        summaries[model] = summary
    return summaries


def report(root: Path, check: bool) -> None:
    summaries = audit(root)
    lines = [
        "# Matched LLM readers after rebuilt retrieval",
        "",
        "3,200 outcomes: 50 reused questions x two retrieval views x four variants x four "
        "decoding arms x two original FLAN-T5 models. No fresh holdout or broader model family.",
        "",
        "Each row reports original numeric accuracy and paired original/rescaled accuracy; "
        "both use all questions in the split. No statistical significance is claimed. "
        "Pointer coordinate accuracy is retained in the complete metrics, "
        "separately from numeric correctness.",
        "",
        "| Split | Model | Arm | N | Native original | Neutral original | "
        "Native paired scale | Neutral paired scale |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for split in ("dev", "test"):
        for model, summary in summaries.items():
            for arm in read_json(root / STUDY / "protocol.json")["arms"]:
                groups = {
                    (s["view"], s["variant"]): s
                    for s in summary
                    if s["split"] == split and s["arm"] == arm
                }
                nb, ub = groups["native", "base"], groups["unit_neutral", "base"]
                ns, us = groups["native", "unit_rescale"], groups["unit_neutral", "unit_rescale"]
                lines.append(
                    f"| {split} | {model} | {arm} | {nb['n']} | {nb['correct']} | "
                    f"{ub['correct']} | {ns['paired_correct']} | {us['paired_correct']} |"
                )
    lines += [
        "",
        "The retrieval view is matched within each model/decoding arm; raw chunks remain "
        "available to the parser. Absolute scores cannot be compared directly with the "
        "original page-expanded pilot. Structure chunking was selected after the earlier "
        "symbolic study, so this remains exploratory. All column-reversal and "
        "combined-transformation outcomes, failures, raw outputs and prompt hashes "
        "are saved in `results/document-llms`.",
        "",
    ]
    path = root / STUDY / "results.md"
    text = "\n".join(lines)
    if check:
        if path.read_text(encoding="utf-8") != text:
            raise ValueError("Matched LLM report differs")
    else:
        path.write_text(text, encoding="utf-8", newline="\n")
    print(
        "Audited 3,200 matched LLM outcomes and " + ("verified" if check else "wrote") + " report"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run", "audit", "report"])
    parser.add_argument("--model", choices=["small", "base"], default="base")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.action == "prepare":
        prepare(root)
    elif args.action == "run":
        run(root, args.model)
    else:
        report(root, check=args.action == "audit")

"""Freeze, execute, resume, and audit OpenAI readers without publishing credentials."""

from __future__ import annotations

import argparse
import runpy
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from filing_lens.equivariance import decode, infer_input
from filing_lens.io import digest, read_json, read_jsonl, write_json, write_jsonl
from filing_lens.openai_eval import (
    client,
    execute,
    request_body,
    request_digest,
    reserve_cost,
    response_text,
    verify_record,
)

STUDY = "research/openai-document-llms"
RESULTS = "results/openai-document-llms"
INPUTS = (
    "scripts/run_openai_document_llms.py",
    "src/filing_lens/openai_eval.py",
    "research/document-llms/freeze.json",
    f"{STUDY}/protocol.json",
)


def upstream(root):
    return runpy.run_path(str(root / "scripts/run_document_llms.py"))


def inputs(root):
    return {p: digest((root / p).read_bytes()) for p in INPUTS}


def jobs(root):
    source = upstream(root)
    cases = source["validate"](root)
    protocol = read_json(root / STUDY / "protocol.json")
    result = []
    for split in ("dev", "test"):
        for case in (c for c in cases if c["split"] == split):
            for arm in protocol["arms"]:
                q, context = infer_input(case["question"], case["unit"], case["cells"], arm)
                prompt = protocol["prompt_template"].format(question=q, context=context)
                result.append((case, arm, prompt))
    return result


def prepare(root):
    target = root / STUDY / "freeze.json"
    if target.exists():
        raise FileExistsError("OpenAI study already frozen")
    work = jobs(root)
    if len(work) != 1600:
        raise ValueError("Expected exactly 1,600 outcomes per model")
    write_json(
        target,
        {
            "created_utc": datetime.now(UTC).isoformat(),
            "inputs": inputs(root),
            "outcomes_per_model": len(work),
            "unique_prompts_per_model": len({p for _, _, p in work}),
            "status": "Frozen before evaluation inference; exploratory reused data",
        },
    )


def validate(root):
    freeze = read_json(root / STUDY / "freeze.json")
    if freeze["inputs"] != inputs(root):
        raise ValueError("Frozen OpenAI inputs changed")
    work = jobs(root)
    if (
        len(work) != freeze["outcomes_per_model"]
        or len({p for _, _, p in work}) != freeze["unique_prompts_per_model"]
    ):
        raise ValueError("Frozen request coverage changed")
    return work


def spent(root):
    total = Decimal(0)
    for path in (root / RESULTS).glob("*/responses/*.json"):
        if not path.name.endswith(".error.json"):
            total += Decimal(read_json(path)["estimated_usd"])
    if list((root / RESULTS).glob("*/responses/*.pending")):
        raise RuntimeError("Ambiguous pending API attempt: investigate before further spending")
    return total


def outcome(case, arm, prompt, body, record, cached, score):
    raw = response_text(record["response"])
    output = decode(raw, case["cells"], case["unit"], arm)
    return {
        **{k: case[k] for k in ("id", "question_id", "split", "company", "view", "variant")},
        "arm": arm,
        "raw": raw,
        "output": output,
        "scores": score(case, output),
        "prompt_sha256": digest(prompt.encode()),
        "request_sha256": request_digest(body),
        "response_id": record["response"]["id"],
        "api_status": record["response"]["status"],
        "cached": cached,
    }


def run(root, model):
    work = validate(root)
    source = upstream(root)
    protocol = read_json(root / STUDY / "protocol.json")
    settings = {**protocol, **protocol["models"][model]}
    folder = root / RESULTS / model
    if (folder / "run.json").exists():
        raise FileExistsError("Completed model run is immutable")
    lock = root / ".cache/openai-evaluation.lock"
    lock.parent.mkdir(exist_ok=True)
    with lock.open("x"):
        pass
    try:
        cost = spent(root)
        rows, seen = [], set()
        with client() as http:
            for case, arm, prompt in work:
                body = request_body(prompt, settings)
                key = request_digest(body)
                target = folder / "responses" / f"{key}.json"
                if not target.exists() and cost + reserve_cost(body, settings) > Decimal(
                    protocol["estimated_budget_usd"]
                ):
                    raise RuntimeError("Estimated study budget exhausted before next request")
                existed = target.exists()
                record = execute(http, body, settings, folder / "responses")
                if not existed:
                    cost += Decimal(record["estimated_usd"])
                rows.append(outcome(case, arm, prompt, body, record, key in seen, source["score"]))
                seen.add(key)
                if len(rows) % 100 == 0:
                    print(
                        f"{model}: {len(rows)}/1600 outcomes, {len(seen)} unique requests, "
                        f"estimated study cost ${cost:.4f}",
                        flush=True,
                    )
        write_jsonl(folder / "predictions.jsonl", rows)
        write_json(folder / "metrics.json", source["summarize"](rows))
        files = [
            folder / "predictions.jsonl",
            folder / "metrics.json",
            *sorted((folder / "responses").glob("*.json")),
        ]
        write_json(
            folder / "run.json",
            {
                "model": settings["model"],
                "completed_utc": datetime.now(UTC).isoformat(),
                "freeze_sha256": digest((root / STUDY / "freeze.json").read_bytes()),
                "outcomes": len(rows),
                "inference_calls": len(seen),
                "files": {p.relative_to(folder).as_posix(): digest(p.read_bytes()) for p in files},
                "estimated_usd": str(
                    sum(
                        Decimal(read_json(folder / "responses" / f"{k}.json")["estimated_usd"])
                        for k in seen
                    )
                ),
            },
        )
    finally:
        lock.unlink()


def audit(root, model):
    work = validate(root)
    source = upstream(root)
    protocol = read_json(root / STUDY / "protocol.json")
    settings = {**protocol, **protocol["models"][model]}
    folder = root / RESULTS / model
    run_record = read_json(folder / "run.json")
    if run_record["model"] != settings["model"] or run_record["freeze_sha256"] != digest(
        (root / STUDY / "freeze.json").read_bytes()
    ):
        raise ValueError("Model or freeze changed")
    rows, seen, cost = [], set(), Decimal(0)
    for case, arm, prompt in work:
        body = request_body(prompt, settings)
        key = request_digest(body)
        record = read_json(folder / "responses" / f"{key}.json")
        verify_record(record, body, settings)
        rows.append(outcome(case, arm, prompt, body, record, key in seen, source["score"]))
        if key not in seen:
            cost += Decimal(record["estimated_usd"])
        seen.add(key)
    expected = {"predictions.jsonl", "metrics.json", *(f"responses/{k}.json" for k in seen)}
    errors = {p.relative_to(folder).as_posix() for p in (folder / "responses").glob("*.error.json")}
    if set(run_record["files"]) != expected | errors:
        raise ValueError("Incomplete artifact manifest")
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    if actual != expected | errors | {"run.json"}:
        raise ValueError("Unrecorded files or pending requests in completed run")
    for path, sha in run_record["files"].items():
        if digest((folder / path).read_bytes()) != sha:
            raise ValueError("Published API artifact changed")
    if (
        run_record["outcomes"] != len(rows)
        or run_record["inference_calls"] != len(seen)
        or Decimal(run_record["estimated_usd"]) != cost
    ):
        raise ValueError("Run accounting changed")
    summary = source["summarize"](rows)
    if rows != read_jsonl(folder / "predictions.jsonl") or summary != read_json(
        folder / "metrics.json"
    ):
        raise ValueError("API scores or summaries changed")
    return summary


def report(root, check=False):
    protocol = read_json(root / STUDY / "protocol.json")
    lines = [
        "# OpenAI matched-reader results",
        "",
        "Exploratory, reused questions; counts are not independent trials.",
        "",
        "| Split | Model | Arm | N | Native original | Neutral original | "
        "Native paired scale | Neutral paired scale |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for model in protocol["models"]:
        summary = audit(root, model)
        for split in ("dev", "test"):
            for arm in protocol["arms"]:
                g = {
                    (s["view"], s["variant"]): s
                    for s in summary
                    if s["split"] == split and s["arm"] == arm
                }
                nb, ub, ns, us = (
                    g[k]
                    for k in (
                        ("native", "base"),
                        ("unit_neutral", "base"),
                        ("native", "unit_rescale"),
                        ("unit_neutral", "unit_rescale"),
                    )
                )
                lines.append(
                    f"| {split} | {model} | {arm} | {nb['n']} | {nb['correct']} | "
                    f"{ub['correct']} | {ns['paired_correct']} | {us['paired_correct']} |"
                )
    text = "\n".join(lines) + "\n"
    path = root / STUDY / "results.md"
    if check:
        if path.read_text(encoding="utf-8") != text:
            raise ValueError("OpenAI results report is stale")
    else:
        path.write_text(text, encoding="utf-8", newline="\n")
    print("Audited 3,200 OpenAI outcomes and report")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "check", "run", "audit", "report"])
    parser.add_argument("--model", choices=["gpt54", "gpt54mini"])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.action == "prepare":
        prepare(root)
    elif args.action == "check":
        validate(root)
        print("Verified OpenAI execution freeze; no inference requested")
    elif args.action == "run":
        if not args.model:
            parser.error("run requires --model")
        run(root, args.model)
    else:
        report(root, check=args.action == "audit")

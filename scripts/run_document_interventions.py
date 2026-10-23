"""Run or audit the exploratory document-text intervention experiment."""

from __future__ import annotations

import argparse
import itertools
from collections import Counter
from pathlib import Path

from filing_lens.document_interventions import VARIANTS, VIEWS, answer, experiment, score
from filing_lens.io import digest, read_json, read_jsonl, write_json, write_jsonl

STUDY = "research/document-interventions"
RESULTS = "results/document-interventions"
INPUTS = (
    "src/filing_lens/document_interventions.py",
    "src/filing_lens/chunking.py",
    "src/filing_lens/reader.py",
    "src/filing_lens/retrieval.py",
    "src/filing_lens/query_planning.py",
    "src/filing_lens/numeric.py",
    "src/filing_lens/io.py",
    "scripts/run_document_interventions.py",
    f"{STUDY}/protocol.json",
    "data/corpus.json",
    "data/questions.jsonl",
    "data/evidence/statement-tables.jsonl",
    "data/benchmark-lock.json",
    "uv.lock",
)


def summarize(rows: list[dict]) -> list[dict]:
    summaries = []
    base = {(r["strategy"], r["view"], r["question_id"]): r for r in rows if r["variant"] == "base"}
    for split in ("dev", "test"):
        for strategy, view in itertools.product(("fixed", "structure"), VIEWS):
            for variant in VARIANTS:
                subset = [
                    r
                    for r in rows
                    if (r["split"], r["strategy"], r["view"], r["variant"])
                    == (split, strategy, view, variant)
                ]
                summaries.append(
                    {
                        "split": split,
                        "strategy": strategy,
                        "view": view,
                        "variant": variant,
                        "n": len(subset),
                        **{k: sum(r["scores"][k] for r in subset) for k in subset[0]["scores"]},
                        "paired_correct": sum(
                            r["scores"]["correct"]
                            and base[(strategy, view, r["question_id"])]["scores"]["correct"]
                            for r in subset
                        ),
                        "regressions": sum(
                            not r["scores"]["correct"]
                            and base[(strategy, view, r["question_id"])]["scores"]["correct"]
                            for r in subset
                        ),
                        "frozen_correct": sum(r["frozen_scores"]["correct"] for r in subset),
                        "statuses": dict(
                            sorted(Counter(r["output"]["status"] for r in subset).items())
                        ),
                    }
                )
    return summaries


def report(rows: list[dict], indexes: list[dict]) -> str:
    lines = [
        "# Rebuilt document-text retrieval: measured exploratory results",
        "",
        f"{len(rows)} outcomes; {len(indexes)} independently built BM25 indexes; "
        "50 reused questions (15 development, 35 test). No LLM inference.",
        "All 1,275 parsed pages participate. Statement pages are reconstructed from "
        "source table fixtures; this is not a general PDF extraction evaluation.",
        "",
        "Each entry is a count / split denominator. Candidate and top-5 hits are "
        "**source-page** coverage, not span recall. Cell coverage additionally requires "
        "a complete retrieved row, period header, metric and unit. Paired correctness "
        "requires both original and transformed answers to be numerically correct.",
        "",
        "Cell coverage is restricted to annotated source pages; correct answers can also "
        "come from duplicate disclosures. Frozen correct uses original top-5 chunk identities "
        "with transformed text; it is a diagnostic reference, not rerun retrieval.",
        "",
        "| Split | Chunking | View | Transform | N | Page@20 | Page@5 | Cell@5 | "
        "Correct | Paired | Lost correct | Frozen correct |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summarize(rows):
        lines.append(
            f"| {s['split']} | {s['strategy']} | {s['view']} | {s['variant']} | {s['n']} | "
            f"{s['candidate_page_hit']} | {s['top5_page_hit']} | {s['cell_coverage']} | "
            f"{s['correct']} | {s['paired_correct']} | {s['regressions']} | {s['frozen_correct']} |"
        )
    lines += [
        "",
        "These results cannot be compared as an improvement over the FLAN-T5 pilot: "
        "retrieval, evidence presentation and the reader all differ. The symbolic reader "
        "is deliberately limited to five metric families and explicit question units. "
        "No configuration is selected using these test results.",
        "",
        "## Index sizes",
        "",
        "| Chunking | View | Transform | Chunks |",
        "|---|---|---|---:|",
        *[f"| {i['strategy']} | {i['view']} | {i['variant']} | {i['chunks']} |" for i in indexes],
        "",
        "## Every incorrect outcome",
        "",
        "Failures retain query-level identifiers; omitted rows are correct, not filtered failures.",
        "",
        "| Question | Chunking | View | Transform | Status | Page@5 | Cell@5 |",
        "|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {r['question_id']} | {r['strategy']} | {r['view']} | {r['variant']} | "
        f"{r['output']['status']} | "
        f"{r['scores']['top5_page_hit']} | {r['scores']['cell_coverage']} |"
        for r in rows
        if not r["scores"]["correct"]
    ]
    return "\n".join(lines) + "\n"


def inputs(root: Path) -> dict:
    return {p: digest((root / p).read_bytes()) for p in INPUTS}


def run(root: Path) -> None:
    target = root / RESULTS
    if target.exists():
        raise ValueError("Run already exists; use a separate checkout to reproduce")
    pages_path = root / "data/processed/pages.jsonl"
    expected = read_json(root / "data/benchmark-lock.json")["pages_sha256"]
    if digest(pages_path.read_bytes()) != expected:
        raise ValueError("Restore the locked parsed corpus before running")
    questions = [q for q in read_jsonl(root / "data/questions.jsonl") if q["kind"] == "numeric"]
    rows, evidence, indexes = experiment(
        read_jsonl(pages_path),
        read_jsonl(root / "data/evidence/statement-tables.jsonl"),
        read_json(root / "data/corpus.json")["documents"],
        questions,
    )
    write_jsonl(target / "predictions.jsonl", rows)
    write_jsonl(target / "evidence.jsonl", evidence)
    write_json(target / "metrics.json", summarize(rows))
    (root / STUDY / "results.md").write_text(report(rows, indexes), encoding="utf-8", newline="\n")
    outputs = [
        f"{RESULTS}/{name}" for name in ("predictions.jsonl", "evidence.jsonl", "metrics.json")
    ]
    outputs.append(f"{STUDY}/results.md")
    write_json(
        target / "manifest.json",
        {
            "status": "Exploratory follow-up; same reused issuers; no independent validation",
            "inputs": inputs(root),
            "parsed_pages_sha256": expected,
            "outputs": {p: digest((root / p).read_bytes()) for p in outputs},
            "indexes": indexes,
            "outcomes": len(rows),
        },
    )
    print(f"Recorded {len(rows)} outcomes from {len(indexes)} rebuilt indexes")


def audit(root: Path, replay: bool) -> None:
    manifest = read_json(root / RESULTS / "manifest.json")
    if manifest["inputs"] != inputs(root):
        raise ValueError("Experiment input or implementation changed")
    for path, expected in manifest["outputs"].items():
        if digest((root / path).read_bytes()) != expected:
            raise ValueError(f"Artifact changed: {path}")
    rows = read_jsonl(root / RESULTS / "predictions.jsonl")
    records = read_jsonl(root / RESULTS / "evidence.jsonl")
    evidence = {r["key"]: r["chunk"] for r in records}
    if len(evidence) != len(records):
        raise ValueError("Duplicate evidence identifier")
    questions = {
        q["id"]: q for q in read_jsonl(root / "data/questions.jsonl") if q["kind"] == "numeric"
    }
    documents = read_json(root / "data/corpus.json")["documents"]
    expected_keys = set(itertools.product(questions, ("fixed", "structure"), VIEWS, VARIANTS))
    observed_keys = {(r["question_id"], r["strategy"], r["view"], r["variant"]) for r in rows}
    if observed_keys != expected_keys or len(rows) != len(expected_keys):
        raise ValueError("Missing or duplicate outcome")
    for row in rows:
        question = questions[row["question_id"]]
        chunks = [evidence[key] for key in row["evidence_keys"]]
        if [c["id"] for c in chunks] != [c["id"] for c in row["candidate_trace"][:5]]:
            raise ValueError("Reader evidence differs from ranked top five")
        output = answer(question["question"], chunks, documents)
        frozen = [evidence[key] for key in row["frozen_evidence_keys"]]
        frozen_output = answer(question["question"], frozen, documents)
        if (
            frozen_output != row["frozen_output"]
            or score(question, frozen, frozen, frozen_output) != row["frozen_scores"]
        ):
            raise ValueError("Frozen-ranking diagnostic mismatch")
        if (
            output != row["output"]
            or score(question, row["candidate_trace"], chunks, output) != row["scores"]
        ):
            raise ValueError(f"Outcome cannot be recomputed: {row['question_id']}")
        if (row["split"], row["company"]) != (question["split"], question["company"]):
            raise ValueError("Question grouping changed")
    if summarize(rows) != read_json(root / RESULTS / "metrics.json"):
        raise ValueError("Aggregate mismatch")
    if report(rows, manifest["indexes"]) != (root / STUDY / "results.md").read_text(
        encoding="utf-8"
    ):
        raise ValueError("Report mismatch")
    if replay:
        pages_path = root / "data/processed/pages.jsonl"
        if digest(pages_path.read_bytes()) != manifest["parsed_pages_sha256"]:
            raise ValueError("Parsed corpus changed")
        observed = experiment(
            read_jsonl(pages_path),
            read_jsonl(root / "data/evidence/statement-tables.jsonl"),
            documents,
            list(questions.values()),
        )
        if observed != (rows, records, manifest["indexes"]):
            raise ValueError("Rebuilt retrieval differs from saved run")
    print(f"Audited {len(rows)} outcomes" + (" and replayed all indexes" if replay else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "audit"])
    parser.add_argument(
        "--replay", action="store_true", help="Rebuild rankings using local parsed PDFs"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.action == "run":
        if args.replay:
            parser.error("--replay is an audit option")
        run(root)
    else:
        audit(root, args.replay)

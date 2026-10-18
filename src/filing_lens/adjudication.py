"""Export source-linked review sheets and validate separately recorded adjudications."""

from __future__ import annotations

import csv
from pathlib import Path

from filing_lens.io import digest, read_json, read_jsonl, write_json
from filing_lens.numeric import number

REVIEW_FIELDS = [
    "reviewer",
    "decision",
    "evidence_method",
    "reviewed_value",
    "reviewed_unit",
    "reviewed_period",
    "reviewed_answer",
    "rationale",
]
SOURCE_FIELDS = [
    "question_id",
    "split",
    "kind",
    "question",
    "answerable",
    "expected_value",
    "expected_unit",
    "period",
    "expected_answer",
    "source_urls",
    "source_quotes",
]


def source_row(question: dict, documents: dict) -> dict:
    return {
        "question_id": question["id"],
        **{key: str(question.get(key, "")) for key in SOURCE_FIELDS if key in question},
        "source_urls": " | ".join(g["source_url"] for g in question["gold"])
        or documents[question["company"]]["url"],
        "source_quotes": " | ".join(g["quote"] for g in question["gold"]),
    }


def export_sheet(root: Path, output: Path) -> None:
    questions = read_jsonl(root / "data/questions.jsonl")
    documents = {d["ticker"]: d for d in read_json(root / "data/corpus.json")["documents"]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=SOURCE_FIELDS + REVIEW_FIELDS, lineterminator="\n"
        )
        writer.writeheader()
        for q in questions:
            writer.writerow(source_row(q, documents))


def validate_sheet(root: Path, sheet: Path) -> dict:
    questions = {q["id"]: q for q in read_jsonl(root / "data/questions.jsonl")}
    documents = {d["ticker"]: d for d in read_json(root / "data/corpus.json")["documents"]}
    with sheet.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not set(SOURCE_FIELDS + REVIEW_FIELDS).issubset(reader.fieldnames or []):
            raise ValueError("Review sheet is missing required columns")
        records = list(reader)
    ids = [r["question_id"] for r in records]
    if len(ids) != len(set(ids)) or set(ids) != set(questions):
        raise ValueError("Review sheet must contain each frozen question exactly once")
    reviewed = []
    for row in records:
        q = questions[row["question_id"]]
        expected = source_row(q, documents)
        if any(row[key] != expected.get(key, "") for key in SOURCE_FIELDS):
            raise ValueError(f"Frozen question or source fields changed: {q['id']}")
        if not any(row[key].strip() for key in REVIEW_FIELDS):
            continue
        for key in REVIEW_FIELDS:
            row[key] = row[key].strip()
        decision, method = row["decision"], row["evidence_method"]
        if not row["reviewer"].strip() or decision not in {"accept", "correct", "reject"}:
            raise ValueError(f"Reviewer and accept/correct/reject decision required: {q['id']}")
        allowed = (
            {"visual_pdf", "xbrl"} if q["kind"] == "numeric" else {"visual_pdf", "corpus_search"}
        )
        if method not in allowed:
            raise ValueError(
                f"Independent source method must be one of {sorted(allowed)}: {q['id']}"
            )
        if not q["answerable"] and method != "corpus_search":
            raise ValueError(f"Unanswerable review requires corpus_search: {q['id']}")
        if not row["rationale"].strip():
            raise ValueError(f"Record the source check and reasoning: {q['id']}")
        if decision != "reject":
            if q["kind"] == "numeric":
                value = number(row["reviewed_value"])
                if (
                    value is None
                    or row["reviewed_unit"]
                    not in {
                        "USD_millions",
                        "USD_thousands",
                        "USD_per_share",
                    }
                    or not row["reviewed_period"].isdigit()
                ):
                    raise ValueError(
                        f"Numeric review needs a value, unit and fiscal year: {q['id']}"
                    )
                if decision == "accept" and (
                    value != number(q["expected_value"])
                    or row["reviewed_unit"] != q["expected_unit"]
                    or int(row["reviewed_period"]) != q["period"]
                ):
                    raise ValueError(f"Acceptance differs from gold; use correct: {q['id']}")
            elif not row["reviewed_answer"].strip():
                raise ValueError(f"Record the answer or corpus-scoped refusal: {q['id']}")
        reviewed.append({"question_id": q["id"], **{k: row[k] for k in REVIEW_FIELDS}})
    return {
        "questions_sha256": digest((root / "data/questions.jsonl").read_bytes()),
        "review_sheet_sha256": digest(sheet.read_bytes()),
        "total_questions": len(questions),
        "reviewed": len(reviewed),
        "pending": len(questions) - len(reviewed),
        "decisions": {
            d: sum(r["decision"] == d for r in reviewed) for d in ("accept", "correct", "reject")
        },
        "provenance": (
            "Reviewer identities and source methods are self-reported. Validation checks "
            "completeness and consistency; it does not certify independent human review. "
            "Corrections are proposals and do not modify the frozen dataset or its metrics."
        ),
        "records": reviewed,
    }


def save_review(root: Path, sheet: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError(f"Review output already exists: {output}")
    report = validate_sheet(root, sheet)
    write_json(output, report)
    return report

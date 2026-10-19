"""Human assessment of frozen explanation outputs, separate from automatic screens."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from filing_lens.io import digest, read_jsonl

SOURCE_FIELDS = [
    "question_id",
    "split",
    "question",
    "answer",
    "refused",
    "model_refused",
    "protocol_error",
    "input_context",
    "source_urls",
    "questions_sha256",
    "predictions_sha256",
]
REVIEW_FIELDS = [
    "reviewer",
    "evidence_answerable",
    "answer_correct",
    "answer_complete",
    "claims_supported",
    "rationale",
]
JUDGMENTS = {"yes", "no", "uncertain"}


def source_rows(root: Path, results: Path) -> list[dict]:
    question_path = root / "data/explanations/questions.jsonl"
    questions = read_jsonl(question_path)
    question_hash = digest(question_path.read_bytes())
    rows = []
    for split in ("dev", "test"):
        path = results / split / "predictions.jsonl"
        predictions = read_jsonl(path)
        expected = {q["id"]: q for q in questions if q["split"] == split}
        ids = [p["question_id"] for p in predictions]
        if len(ids) != len(set(ids)) or set(ids) != set(expected):
            raise ValueError(f"Predictions must cover every {split} question exactly once")
        prediction_hash = digest(path.read_bytes())
        for prediction in predictions:
            q = expected[prediction["question_id"]]
            if prediction["split"] != split:
                raise ValueError(f"Prediction split differs: {q['id']}")
            response = prediction["response"]
            rows.append(
                {
                    "question_id": q["id"],
                    "split": split,
                    "question": q["question"],
                    "answer": response["answer"],
                    **{
                        key: str(response[key]).lower()
                        for key in ("refused", "model_refused", "protocol_error")
                    },
                    "input_context": response["input_context"],
                    "source_urls": " | ".join(
                        item["source_url"] for item in response["input_sources"]
                    ),
                    "questions_sha256": question_hash,
                    "predictions_sha256": prediction_hash,
                }
            )
    return rows


def export_answers(root: Path, results: Path, output: Path) -> None:
    rows = source_rows(root, results)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, SOURCE_FIELDS + REVIEW_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _metric(values: list[bool], eligible: int) -> dict:
    return {
        "passed": sum(values),
        "scored": len(values),
        "eligible": eligible,
        "unscored": eligible - len(values),
        "rate": sum(values) / len(values) if values else None,
    }


def _summarize(sources: list[dict], reviews: dict[str, dict]) -> dict:
    answered = [r for r in sources if r["refused"] == "false"]
    result = {
        "total": len(sources),
        "reviewed": sum(r["question_id"] in reviews for r in sources),
    }
    result["pending"] = result["total"] - result["reviewed"]
    for key in ("answer_correct", "answer_complete", "claims_supported"):
        values = [
            reviews[r["question_id"]][key] == "yes"
            for r in answered
            if r["question_id"] in reviews and reviews[r["question_id"]][key] in {"yes", "no"}
        ]
        result[key + "_given_answer"] = _metric(values, len(answered))
    appropriate = []
    for source in sources:
        review = reviews.get(source["question_id"])
        if review is None or review["evidence_answerable"] == "uncertain":
            continue
        if source["refused"] == "true":
            # Protocol failures are never credited as successful model refusals.
            appropriate.append(
                review["evidence_answerable"] == "no"
                and source["model_refused"] == "true"
                and source["protocol_error"] == "false"
            )
        elif review["evidence_answerable"] == "no":
            appropriate.append(False)
        else:
            quality = [review[k] for k in ("answer_correct", "answer_complete", "claims_supported")]
            if "no" in quality:
                appropriate.append(False)
            elif "uncertain" not in quality:
                appropriate.append(True)
    result["appropriate_response"] = _metric(appropriate, len(sources))
    return result


def validate_answers(root: Path, results: Path, sheet: Path) -> dict:
    sources = source_rows(root, results)
    expected = {r["question_id"]: r for r in sources}
    with sheet.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or set(fields) != set(SOURCE_FIELDS + REVIEW_FIELDS):
            raise ValueError("Review sheet must contain the exact required columns")
        rows = list(reader)
    ids = [r["question_id"] for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError("Review sheet must contain every prediction exactly once")
    reviews = {}
    for row in rows:
        qid = row["question_id"]
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Malformed CSV row: {qid}")
        if any(row[k] != expected[qid][k] for k in SOURCE_FIELDS):
            raise ValueError(f"Frozen output or source fields changed: {qid}")
        review = {k: row[k].strip() for k in REVIEW_FIELDS}
        if not any(review.values()):
            continue
        if not review["reviewer"] or not review["rationale"]:
            raise ValueError(f"Reviewer and rationale required: {qid}")
        if review["evidence_answerable"] not in JUDGMENTS:
            raise ValueError(f"Answerability needs yes/no/uncertain: {qid}")
        allowed = {"na"} if row["refused"] == "true" else JUDGMENTS
        if any(review[k] not in allowed for k in REVIEW_FIELDS[2:5]):
            raise ValueError(f"Answer judgments must be one of {sorted(allowed)}: {qid}")
        if (
            review["evidence_answerable"] == "no"
            and row["refused"] == "false"
            and (review["answer_correct"] == "yes" or review["answer_complete"] == "yes")
        ):
            raise ValueError(
                f"Unsupported question cannot have a correct or complete answer: {qid}"
            )
        reviews[qid] = review
    return {
        "schema_version": 1,
        "questions_sha256": sources[0]["questions_sha256"],
        "predictions_sha256": {
            split: next(r["predictions_sha256"] for r in sources if r["split"] == split)
            for split in ("dev", "test")
        },
        "review_sheet_sha256": digest(sheet.read_bytes()),
        "splits": {
            split: _summarize([r for r in sources if r["split"] == split], reviews)
            for split in ("dev", "test")
        },
        "provenance": (
            "Reviewer identities are self-reported; this validator cannot certify human "
            "identity or independence. Rates describe scored reviews only. Pending and "
            "uncertain judgments are not successes. Evidence is the supplied model context, "
            "not an independent PDF extraction. Frozen study metrics are unchanged."
        ),
        "records": [{"question_id": key, **value} for key, value in reviews.items()],
    }


def save_answers(root: Path, results: Path, sheet: Path, output: Path) -> dict:
    report = validate_answers(root, results, sheet)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return report

import csv
from pathlib import Path

import pytest

from filing_lens.adjudication import export_sheet, validate_sheet

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sheet(tmp_path):
    path = tmp_path / "review.csv"
    export_sheet(ROOT, path)
    return path


def edit(path, mutate):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    mutate(rows)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def accept_numeric(rows):
    row = next(r for r in rows if r["kind"] == "numeric")
    row.update(
        {
            "reviewer": "Example reviewer",
            "decision": "accept",
            "evidence_method": "visual_pdf",
            "reviewed_value": row["expected_value"],
            "reviewed_unit": row["expected_unit"],
            "reviewed_period": row["period"],
            "rationale": "Checked original row, heading and unit",
        }
    )
    return row


def test_unfilled_sheet_never_counts_as_reviewed(sheet):
    # Integrity seals must survive a cross-platform checkout.
    assert b"\r" not in sheet.read_bytes()
    report = validate_sheet(ROOT, sheet)
    assert report["pending"] == 80 and report["reviewed"] == 0
    with pytest.raises(FileExistsError):
        export_sheet(ROOT, sheet)


def test_numeric_acceptance_requires_matching_source_check(sheet):
    edit(sheet, accept_numeric)
    assert validate_sheet(ROOT, sheet)["reviewed"] == 1
    edit(sheet, lambda rows: accept_numeric(rows).update(reviewed_value="999"))
    with pytest.raises(ValueError, match="Acceptance differs"):
        validate_sheet(ROOT, sheet)


@pytest.mark.parametrize(
    "field,value",
    [("question", "changed"), ("expected_value", "99"), ("source_urls", "https://other.example")],
)
def test_review_cannot_change_frozen_reference_fields(sheet, field, value):
    edit(sheet, lambda rows: rows[0].update({field: value}))
    with pytest.raises(ValueError, match="Frozen"):
        validate_sheet(ROOT, sheet)


def test_review_does_not_accept_parser_agreement_as_independent_check(sheet):
    edit(sheet, lambda rows: accept_numeric(rows).update(evidence_method="same_parser"))
    with pytest.raises(ValueError, match="Independent source"):
        validate_sheet(ROOT, sheet)


def test_duplicate_questions_are_rejected(sheet):
    edit(sheet, lambda rows: rows.append(rows[0]))
    with pytest.raises(ValueError, match="exactly once"):
        validate_sheet(ROOT, sheet)


def test_explanation_review_is_separate_and_all_pending(tmp_path):
    path = tmp_path / "explanations.csv"
    export_sheet(ROOT, path, "explanations")
    report = validate_sheet(ROOT, path, "explanations")
    assert report["total_questions"] == report["pending"] == 40
    assert report["reviewed"] == 0
    with pytest.raises(ValueError, match="exactly once"):
        validate_sheet(ROOT, path)


def test_context_unsupported_reviews_require_passage_evidence(tmp_path):
    path = tmp_path / "explanations.csv"
    export_sheet(ROOT, path, "explanations")

    def review(rows):
        row = next(r for r in rows if r["kind"] == "context_unanswerable")
        row.update(
            {
                "reviewer": "Example reviewer",
                "decision": "accept",
                "evidence_method": "passage_inspection",
                "reviewed_answer": "Not in supplied passage",
                "rationale": "Passage contains no launch delay in days",
            }
        )

    edit(path, review)
    assert validate_sheet(ROOT, path, "explanations")["reviewed"] == 1

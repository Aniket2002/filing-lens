import csv
import shutil
from pathlib import Path

import pytest

from filing_lens.answer_review import export_answers, save_answers, validate_answers
from filing_lens.io import read_json, read_jsonl, write_jsonl

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/explanations"


def test_committed_pending_review_report_is_reproducible():
    report = validate_answers(ROOT, RESULTS, ROOT / "data/review/answers-pending.csv")
    assert report == read_json(ROOT / "data/review/answers-status.json")


@pytest.fixture
def sheet(tmp_path):
    path = tmp_path / "answers.csv"
    export_answers(ROOT, RESULTS, path)
    return path


def edit(path, mutate):
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    mutate(rows)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields)
        writer.writeheader()
        writer.writerows(rows)


def assess(row, **overrides):
    refused = row["refused"] == "true"
    row.update(
        reviewer="Test reviewer",
        evidence_answerable="no" if refused else "yes",
        answer_correct="na" if refused else "yes",
        answer_complete="na" if refused else "yes",
        claims_supported="na" if refused else "yes",
        rationale="Test assessment of the supplied context and question",
    )
    row.update(overrides)


def test_pending_answer_reviews_have_no_quality_score(sheet):
    assert b"\r" not in sheet.read_bytes()
    report = validate_answers(ROOT, RESULTS, sheet)
    assert report["splits"]["dev"]["pending"] == 8
    test = report["splits"]["test"]
    assert test["pending"] == 32 and test["reviewed"] == 0
    assert test["answer_correct_given_answer"] == {
        "passed": 0,
        "scored": 0,
        "eligible": 16,
        "unscored": 16,
        "rate": None,
    }
    assert test["appropriate_response"]["rate"] is None
    # Reviewers see the question and exact input, without the automatic concept screen.
    header = sheet.read_text(encoding="utf-8").splitlines()[0]
    assert "concept" not in header and "expected_answer" not in header
    with pytest.raises(FileExistsError):
        export_answers(ROOT, RESULTS, sheet)


def test_supported_but_incomplete_answer_is_not_successful(sheet):
    def mutate(rows):
        row = next(r for r in rows if r["split"] == "test" and r["refused"] == "false")
        assess(row, answer_complete="no")

    edit(sheet, mutate)
    report = validate_answers(ROOT, RESULTS, sheet)["splits"]["test"]
    assert report["reviewed"] == 1 and report["pending"] == 31
    assert report["claims_supported_given_answer"]["rate"] == 1
    assert report["answer_complete_given_answer"]["rate"] == 0
    assert report["appropriate_response"] == {
        "passed": 0,
        "scored": 1,
        "eligible": 32,
        "unscored": 31,
        "rate": 0.0,
    }
    assert validate_answers(ROOT, RESULTS, sheet)["splits"]["dev"]["reviewed"] == 0


def test_uncertain_assessment_does_not_become_zero_or_success(sheet):
    edit(sheet, lambda rows: assess(rows[0], answer_correct="uncertain"))
    dev = validate_answers(ROOT, RESULTS, sheet)["splits"]["dev"]
    assert dev["reviewed"] == 1
    assert dev["answer_correct_given_answer"]["scored"] == 0
    assert dev["appropriate_response"]["rate"] is None


def test_correct_refusal_is_not_scored_as_an_answer(sheet):
    def mutate(rows):
        assess(next(r for r in rows if r["split"] == "dev" and r["refused"] == "true"))

    edit(sheet, mutate)
    dev = validate_answers(ROOT, RESULTS, sheet)["splits"]["dev"]
    assert dev["appropriate_response"]["rate"] == 1
    assert dev["answer_correct_given_answer"]["rate"] is None


def test_protocol_failure_never_counts_as_successful_refusal(tmp_path):
    results = tmp_path / "results"
    shutil.copytree(RESULTS, results)
    path = results / "dev/predictions.jsonl"
    predictions = read_jsonl(path)
    row = next(p for p in predictions if p["response"]["refused"])
    row["response"].update(protocol_error=True, model_refused=False)
    write_jsonl(path, predictions)
    sheet = tmp_path / "answers.csv"
    export_answers(ROOT, results, sheet)
    edit(sheet, lambda rows: assess(next(r for r in rows if r["protocol_error"] == "true")))
    dev = validate_answers(ROOT, results, sheet)["splits"]["dev"]
    assert dev["appropriate_response"]["rate"] == 0


@pytest.mark.parametrize("field", ["answer", "input_context", "question", "predictions_sha256"])
def test_review_rejects_modified_evidence_or_output(sheet, field):
    edit(sheet, lambda rows: rows[0].update({field: "changed"}))
    with pytest.raises(ValueError, match="Frozen"):
        validate_answers(ROOT, RESULTS, sheet)


@pytest.mark.parametrize(
    "overrides",
    [
        {"reviewer": ""},
        {"rationale": ""},
        {"answer_correct": ""},
        {"claims_supported": "na"},
        {"evidence_answerable": "no"},
    ],
)
def test_partial_or_inconsistent_judgments_are_rejected(sheet, overrides):
    edit(sheet, lambda rows: assess(rows[0], **overrides))
    with pytest.raises(ValueError):
        validate_answers(ROOT, RESULTS, sheet)


def test_missing_and_duplicate_predictions_are_rejected(sheet):
    edit(sheet, lambda rows: rows.append(rows[0]))
    with pytest.raises(ValueError, match="exactly once"):
        validate_answers(ROOT, RESULTS, sheet)


def test_review_is_bound_to_prediction_file_bytes(sheet, tmp_path):
    results = tmp_path / "results"
    shutil.copytree(RESULTS, results)
    path = results / "test/predictions.jsonl"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="Frozen"):
        validate_answers(ROOT, results, sheet)


def test_report_never_overwrites_review_or_study(sheet, tmp_path):
    output = tmp_path / "report.json"
    save_answers(ROOT, RESULTS, sheet, output)
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        save_answers(ROOT, RESULTS, sheet, output)
    assert output.read_bytes() == original

import shutil
from pathlib import Path

import pymupdf
import pytest

from filing_lens.paper import INPUTS, build, paired_changes, render_template, to_html

ROOT = Path(__file__).resolve().parents[1]


def test_company_sensitivity_is_paired_and_counts_regressions():
    left = [
        {"question_id": "a", "company": "A", "hit": 0},
        {"question_id": "b", "company": "B", "hit": 1},
        {"question_id": "c", "company": "C", "hit": 0},
    ]
    right = [{**row, "hit": value} for row, value in zip(left, [1, 0, 1], strict=True)]
    result = paired_changes(left, right, "hit")
    assert result["gains"] == 2 and result["losses"] == 1
    assert result["leave_one_company_out"] == {"A": 0, "B": 1, "C": 0}
    with pytest.raises(ValueError, match="identical"):
        paired_changes(left, right[:-1], "hit")
    with pytest.raises(ValueError, match="company mismatch"):
        paired_changes(left, [{**right[0], "company": "X"}, *right[1:]], "hit")


def test_template_fails_on_missing_evidence_and_citation_keys():
    with pytest.raises(ValueError, match="manuscript field"):
        render_template("{{made_up_accuracy}}", {}, [])
    with pytest.raises(ValueError, match="Unknown citation"):
        render_template("[@invented]", {}, [])
    assert render_template("Measured {{recall}}", {"recall": "88.1%"}, []) == "Measured 88.1%"


def test_markup_escapes_text_and_preserves_table_and_links():
    result = to_html(
        "# Title\n\nA < B & C. [Source](https://example.com)\n\n| A | B |\n| --- | --- |\n| 1 | 2 |"
    )
    assert "A &lt; B &amp; C" in result
    assert '<a href="https://example.com">Source</a>' in result
    assert result.count("<tr>") == 2


def test_paper_evidence_check_rejects_stale_text_and_modified_pdf(tmp_path):
    for name in INPUTS:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    for name in (
        "manuscript.md",
        "manuscript.html",
        "manuscript.pdf",
        "references.bib",
        "evidence.json",
        "build.json",
    ):
        shutil.copyfile(
            ROOT / "research/retrieval-baseline" / name,
            tmp_path / "research/retrieval-baseline" / name,
        )
    assert build(tmp_path, check=True)["pdf_pages"] >= 1
    path = tmp_path / "research/retrieval-baseline/manuscript.md"
    original = path.read_bytes()
    path.write_text("Invented result", encoding="utf-8")
    with pytest.raises(ValueError, match="stale"):
        build(tmp_path, check=True)
    path.write_bytes(original)
    pdf = tmp_path / "research/retrieval-baseline/manuscript.pdf"
    pdf.write_bytes(pdf.read_bytes() + b"modified")
    with pytest.raises(ValueError, match="artifact changed"):
        build(tmp_path, check=True)


def test_review_pdf_contains_results_references_and_figure():
    with pymupdf.open(ROOT / "research/retrieval-baseline/manuscript.pdf") as document:
        text = "\n".join(page.get_text() for page in document)
        assert "88.1%" in text and "85.7%" in text
        assert "FinQA" in text and "References" in text
        assert "previously inspected" in text
        assert sum(len(page.get_images()) for page in document) >= 1
        assert all(page.get_text().strip() for page in document)

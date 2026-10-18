from pathlib import Path

import numpy as np
import pytest

from filing_lens.chunking import chunk_pages
from filing_lens.evaluation import contains_gold, paired_company_bootstrap, retrieval_metrics
from filing_lens.io import digest, read_json, read_jsonl, write_json, write_jsonl
from filing_lens.reader import answer_question, resolve_question
from filing_lens.retrieval import ranked, reciprocal_rank_fusion

ROOT = Path(__file__).resolve().parents[1]


def test_artifact_serialization_is_identical_across_operating_systems(tmp_path):
    path = tmp_path / "test.json"
    write_json(path, {"value": "µ"})
    assert b"\r" not in path.read_bytes()
    path = tmp_path / "test.jsonl"
    write_jsonl(path, [{"value": "µ"}])
    assert b"\r" not in path.read_bytes()


def test_benchmark_is_80_unique_questions_with_company_disjoint_splits():
    questions = read_jsonl(ROOT / "data/questions.jsonl")
    assert len(questions) == len({q["id"] for q in questions}) == 80
    assert sum(q["answerable"] for q in questions) == 60
    assert {q["company"] for q in questions if q["split"] == "dev"}.isdisjoint(
        {q["company"] for q in questions if q["split"] == "test"}
    )
    assert all(q["gold"] if q["answerable"] else not q["gold"] for q in questions)
    assert (
        digest((ROOT / "data/questions.jsonl").read_bytes())
        == read_json(ROOT / "data/benchmark-lock.json")["questions_sha256"]
    )


def test_relevance_requires_full_span_and_correct_document():
    gold = {"doc_id": "A", "page": 1, "start": 10, "end": 30}
    wrong = {"doc_id": "B", "page": 1, "start": 0, "end": 40}
    partial = {"doc_id": "A", "page": 1, "start": 0, "end": 29}
    right = {"doc_id": "A", "page": 1, "start": 0, "end": 40}
    assert not contains_gold(wrong, gold)
    assert not contains_gold(partial, gold)
    result = retrieval_metrics([wrong, partial, right], [gold])
    assert result["recall_at_1"] == 0
    assert result["recall_at_5"] == 1
    assert result["mrr_at_20"] == 1 / 3
    assert retrieval_metrics([right], [])["mrr_at_20"] is None


def test_rrf_uses_ranks_and_deterministic_tie_breaks():
    assert reciprocal_rank_fusion([[0, 1, 2], [2, 1, 0]]) == [0, 2, 1]
    assert ranked(np.array([0.5, 0.5, 0.1]), 2) == [0, 1]


def test_table_chunk_repeats_header_and_offsets_stay_in_source():
    text = "Statement (USD_millions)\nMetric | 2023 | 2022\n" + "\n".join(
        f"Revenue {i} | {i} | {i + 1}" for i in range(10)
    )
    pages = [
        {
            "doc_id": "A",
            "page": 1,
            "text": text,
            "blocks": [{"start": 0, "end": len(text), "kind": "table", "table_id": "T"}],
        }
    ]
    docs = [{"id": "A", "company": "Alpha", "ticker": "A", "fiscal_year": 2023}]
    chunks = chunk_pages(pages, docs, "structure", size=25, overlap=4)
    assert len(chunks) > 1
    assert all("Metric | 2023 | 2022" in c["text"] for c in chunks)
    assert all(text[c["start"] : c["end"]] in c["text"] for c in chunks)
    assert all(a["end"] == b["start"] for a, b in zip(chunks, chunks[1:], strict=False))
    with pytest.raises(ValueError):
        chunk_pages(pages, docs, "fixed", size=10, overlap=10)


def test_query_parser_distinguishes_report_year_from_requested_period():
    docs = read_json(ROOT / "data/corpus.json")["documents"]
    resolved = resolve_question(
        "According to NVIDIA's FY2023 report, what was FY2022 net income?", docs
    )
    assert resolved["year"] == 2022
    assert resolved["metric"] == "net_income"
    assert resolve_question("What was AMD's FY2023 net revenue?", docs)["doc"]["ticker"] == "AMD"
    assert resolve_question("Compare AMD and Intel FY2023 revenue", docs)["doc"] is None


def test_reader_refuses_without_retrieved_evidence():
    docs = read_json(ROOT / "data/corpus.json")["documents"]
    assert answer_question("What was NVIDIA's FY2023 revenue?", [], {}, docs)["refused"]


def test_company_bootstrap_is_paired_and_reproducible():
    left = [{"question_id": str(i), "company": str(i // 2), "score": 0} for i in range(6)]
    right = [{**r, "score": 1} for r in left]
    result = paired_company_bootstrap(left, right, "score", samples=200)
    assert result["ci95"] == [1.0, 1.0]
    assert result["companies"] == 3
    with pytest.raises(ValueError):
        paired_company_bootstrap(left, right[:-1], "score")

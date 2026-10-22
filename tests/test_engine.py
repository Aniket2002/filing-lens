from pathlib import Path

import pytest

from filing_lens.engine import QueryEngine
from filing_lens.io import read_json, write_json, write_jsonl

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def root(tmp_path):
    doc = {
        "id": "MU-2023",
        "company": "Micron Technology",
        "ticker": "MU",
        "fiscal_year": 2023,
        "url": "https://example.com/micron.pdf",
    }
    text = "Metric | 2023 | 2022\nRevenue | 15,540 | 30,758"
    write_json(tmp_path / "data/corpus.json", {"documents": [doc]})
    write_json(tmp_path / "data/model-lock.json", read_json(ROOT / "data/model-lock.json"))
    write_jsonl(
        tmp_path / "data/processed/pages.jsonl",
        [
            {
                "doc_id": doc["id"],
                "page": 57,
                "text": text,
                "blocks": [{"start": 0, "end": len(text), "kind": "table", "table_id": "T"}],
            }
        ],
    )
    write_jsonl(
        tmp_path / "data/processed/tables.jsonl",
        [
            {
                "id": "T",
                "doc_id": doc["id"],
                "page": 57,
                "years": [2023, 2022],
                "unit": "USD_millions",
                "rows": [["Metric", "2023", "2022"], ["Revenue", "15,540", "30,758"]],
            }
        ],
    )
    return tmp_path


def test_live_engine_answers_without_any_gold_files_and_exposes_profile(root):
    engine = QueryEngine(root, config="fixed-bm25")
    answer = engine.ask("What was Micron's FY2023 revenue?")
    assert answer["claims"][0]["value"] == "15540"
    assert answer["citations"][0]["url"] == "https://example.com/micron.pdf#page=57"
    assert answer["table_evidence_assembly"] and answer["reader"] == "extractive"
    assert engine.ask("What was Micron's FY2028 revenue?")["refused"]
    assert not (root / "data/questions.jsonl").exists()


def test_live_generator_uses_model_output_and_refuses_wrong_amount(root, monkeypatch):
    class FakeGenerator:
        def __init__(self, *args):
            self.output = "15540"

        def generate(self, question, context):
            assert "FY2023: 15540" in context and "FY2022: 30758" in context
            return self.output

    monkeypatch.setattr("filing_lens.generation.LocalGenerator", FakeGenerator)
    engine = QueryEngine(root, config="fixed-bm25", reader="flan-t5-base")
    assert not engine.ask("What was Micron's FY2023 revenue?")["refused"]
    engine.generator.output = "30758"
    answer = engine.ask("What was Micron's FY2023 revenue?")
    assert answer["refused"] and answer["raw_generation"] == "30758"


def test_engine_rejects_unsupported_profile_before_loading_data(tmp_path):
    with pytest.raises(ValueError, match="Invalid config"):
        QueryEngine(tmp_path, config="invalid")


@pytest.mark.parametrize(
    "options",
    [
        {"candidate_pool": 19},
        {"candidate_pool": 201},
        {"retrieval_profile": "unknown"},
    ],
)
def test_retrieval_options_are_validated_before_loading_corpus(tmp_path, options):
    with pytest.raises(ValueError):
        QueryEngine(tmp_path, config="fixed-bm25", **options)


def test_live_retrieval_profile_has_trace_without_gold_files(root):
    engine = QueryEngine(
        root, config="structure-bm25", retrieval_profile="finance", candidate_pool=60
    )
    response = engine.ask("What was Micron's FY2023 revenue?")
    assert response["claims"][0]["value"] == "15540"
    trace = response["retrieval"]
    assert trace["candidate_pool"] == 60
    assert trace["query_plan"]["doc_ids"] == ["MU-2023"]
    assert trace["trace"][0]["doc_id"] == "MU-2023"
    assert trace["trace"][0]["url"] == "https://example.com/micron.pdf#page=57"
    assert not (root / "data/questions.jsonl").exists()


def test_explanation_engine_bypasses_extractive_reader_and_uses_source_text(root, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Explanation mode must bypass the extractive answerer")

    class FakeExplainer:
        def __init__(self, *args):
            pass

        def answer(self, question, evidence):
            assert evidence[0]["quote"].startswith("Metric |")
            assert "Micron Technology (MU) FY2023." not in evidence[0]["quote"]
            return {
                "answer": "An explanation.",
                "refused": False,
                "reason": None,
                "citations": [{**evidence[0], "role": "input_context"}],
                "claims": [],
                "numeric_checks": [],
                "verification_status": "unverified_generation",
            }

    monkeypatch.setattr("filing_lens.engine.answer_question", forbidden)
    monkeypatch.setattr("filing_lens.explanations.ExplanationReader", FakeExplainer)
    engine = QueryEngine(root, config="fixed-bm25", reader="flan-t5-explain")
    response = engine.ask("Explain Micron revenue")
    assert not response["table_evidence_assembly"]
    assert response["reader"] == "flan-t5-explain"

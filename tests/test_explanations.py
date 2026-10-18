from pathlib import Path
from types import SimpleNamespace

import pytest

from filing_lens.explanation_study import fingerprint, run
from filing_lens.explanations import ExplanationReader, model_decision, screen_concepts, summarize
from filing_lens.io import read_json, read_jsonl

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("yes", "yes"),
        (" No. ", "no"),
        ("YES!", "yes"),
        ("not enough information", "invalid"),
        ("yes, but", "invalid"),
        ("", "invalid"),
    ],
)
def test_only_explicit_model_decisions_are_counted(text, expected):
    assert model_decision(text) == expected


class Tokenizer:
    def __call__(self, text, **kwargs):
        return {"input_ids": list(text)}

    def decode(self, tokens, **kwargs):
        return "".join(tokens)


def fake_reader(decision="yes"):
    reader = ExplanationReader.__new__(ExplanationReader)
    reader.lock = {
        "max_input_tokens": 180,
        "prompt_template": "Explain {context} Question: {question}",
        "answerability_template": "Decide {context} Question: {question}",
    }
    reader.backend = SimpleNamespace(
        tokenizer=Tokenizer(),
        model=SimpleNamespace(generate=lambda **kwargs: [list(decision)]),
        generate=lambda question, context: (
            "Lower demand leaves idle capacity and increases expenses."
        ),
    )
    return reader


def test_context_budget_preserves_question_and_exact_source_offsets():
    reader = fake_reader()
    source = {"doc_id": "X", "page": 1, "start": 23, "end": 1023, "quote": "a" * 1000}
    context, included = reader.prepare_context("Explain costs", [source])
    assert included[0]["input_excerpt_truncated"]
    assert included[0]["end"] == 23 + len(included[0]["quote"])
    assert source["quote"].startswith(included[0]["quote"])
    assert all(
        len(template.format(context=context, question="Explain costs")) <= 180
        for template in (reader.lock["prompt_template"], reader.lock["answerability_template"])
    )
    with pytest.raises(ValueError, match="input budget"):
        reader.prepare_context("q" * 1000, [source])


def test_model_refusal_uses_no_numeric_or_extractive_gate(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("An extractive or numeric gate must not decide this refusal")

    monkeypatch.setattr("filing_lens.reader.answer_question", forbidden)
    monkeypatch.setattr("filing_lens.generation.gate_generated", forbidden)
    reader = fake_reader("no")
    reader.backend.generate = forbidden
    answer = reader.answer("Missing detail?", [{"doc_id": "X", "page": 1, "quote": "A fact."}])
    assert answer["model_refused"] and answer["refused"]
    assert answer["raw_answerability"] == "no" and answer["raw_generation"] is None


def test_generated_explanation_is_never_marked_verified():
    answer = fake_reader().answer("Explain costs", [{"doc_id": "X", "page": 1, "quote": "A fact."}])
    assert not answer["refused"]
    assert answer["verification_status"] == "unverified_generation"
    assert answer["citation_supported"] is None and answer["numeric_checks"] == []
    assert answer["citations"][0]["role"] == "input_context"


def test_invalid_protocol_output_is_not_counted_as_model_refusal():
    response = fake_reader("perhaps").answer("Question", [])
    row = {"answerable": False, "response": response, "all_concepts_covered": False}
    metrics = summarize([row])
    assert metrics["protocol_errors"] == 1
    assert metrics["model_refusal_on_unanswerables"] == 0
    assert metrics["human_answer_correctness"] is None


def test_keyword_coverage_is_only_a_screen_and_cannot_certify_negation():
    concepts = [["demand"], ["expenses"]]
    assert screen_concepts("Demand does not affect expenses.", concepts)["all_concepts_covered"]
    assert not screen_concepts(None, concepts)["all_concepts_covered"]


def test_new_challenge_is_frozen_disjoint_and_not_original_questions():
    questions = read_jsonl(ROOT / "data/explanations/questions.jsonl")
    old = {q["question"] for q in read_jsonl(ROOT / "data/questions.jsonl")}
    assert len(questions) == len({q["id"] for q in questions}) == 40
    assert not old.intersection(q["question"] for q in questions)
    assert {q["company"] for q in questions if q["split"] == "dev"}.isdisjoint(
        q["company"] for q in questions if q["split"] == "test"
    )
    assert fingerprint(ROOT) == read_json(ROOT / "data/explanations/protocol.json")["fingerprint"]


def test_frozen_test_cannot_start_without_dev_or_overwrite_outputs(tmp_path):
    with pytest.raises(FileNotFoundError):
        run(ROOT, tmp_path, "test")
    (tmp_path / "test").mkdir()
    with pytest.raises(ValueError, match="already exists"):
        run(ROOT, tmp_path, "test")

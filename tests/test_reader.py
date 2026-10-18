from copy import deepcopy

import pytest

from filing_lens.generation import gate_generated, generated_amount
from filing_lens.reader import answer_question


@pytest.fixture
def corpus():
    doc = {"id": "MU-2023", "ticker": "MU", "company": "Micron Technology", "fiscal_year": 2023}
    table = {
        "id": "T",
        "doc_id": doc["id"],
        "page": 57,
        "years": [2023, 2022],
        "unit": "USD_millions",
        "rows": [["Metric", "2023", "2022"], ["Net income (loss)", "(5,833)", "8,687"]],
    }
    body = "Metric | 2023 | 2022\nNet income (loss) | (5,833) | 8,687"
    chunk = {"id": "C", "doc_id": doc["id"], "page": 57, "start": 0, "end": len(body), "text": body}
    return [doc], {"T": table}, [chunk]


def test_reader_binds_requested_prior_year_to_correct_column(corpus):
    docs, tables, chunks = corpus
    response = answer_question("What was Micron's FY2022 net income?", chunks, tables, docs)
    assert response["claims"][0]["value"] == "8687"
    assert response["claims"][0]["column_index"] == 2


def test_global_table_lookup_does_not_bypass_missing_header(corpus):
    docs, tables, chunks = deepcopy(corpus)
    chunks[0]["text"] = "Net income (loss) | (5,833) | 8,687"
    assert answer_question("What was Micron's FY2023 net income?", chunks, tables, docs)["refused"]


def test_global_table_lookup_does_not_bypass_missing_row(corpus):
    docs, tables, chunks = deepcopy(corpus)
    chunks[0]["text"] = "Metric | 2023 | 2022"
    assert answer_question("What was Micron's FY2023 net income?", chunks, tables, docs)["refused"]


def test_no_answer_can_be_borrowed_from_another_entity(corpus):
    docs, tables, chunks = deepcopy(corpus)
    chunks[0]["doc_id"] = "AMD-2023"
    assert answer_question("What was Micron's FY2023 net income?", chunks, tables, docs)["refused"]


def test_generator_gate_rejects_wrong_sign_and_invented_amount(corpus):
    docs, tables, chunks = corpus
    candidate = answer_question("What was Micron's FY2023 net income?", chunks, tables, docs)
    assert not candidate["refused"]
    assert not gate_generated("-5,833", candidate, tables, {d["id"]: d for d in docs})["refused"]
    assert gate_generated("5,833", candidate, tables, {d["id"]: d for d in docs})["refused"]
    assert gate_generated("8,687", candidate, tables, {d["id"]: d for d in docs})["refused"]
    assert gate_generated("UNKNOWN", candidate, tables, {d["id"]: d for d in docs})["refused"]


@pytest.mark.parametrize("text", ["100 million", "100 and 200", "Revenue was 100", "UNKNOWN", ""])
def test_generator_amount_contract_is_strict(text):
    assert generated_amount(text) is None

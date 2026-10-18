from copy import deepcopy
from decimal import Decimal

import pytest

from filing_lens.numeric import matches_metric, number, verify_answer_numbers, verify_claim


@pytest.fixture
def evidence():
    table = {
        "id": "MU-2023:p57:statement",
        "doc_id": "MU-2023",
        "page": 57,
        "years": [2023, 2022, 2021],
        "unit": "USD_millions",
        "rows": [
            ["Metric", "2023", "2022", "2021"],
            ["Net income (loss)", "(5,833)", "8,687", "5,861"],
            ["Revenue", "15,540", "30,758", "27,705"],
        ],
    }
    claim = {
        "table_id": table["id"],
        "doc_id": "MU-2023",
        "page": 57,
        "row_index": 1,
        "column_index": 1,
        "row_label": "Net income (loss)",
        "metric": "net_income",
        "period": 2023,
        "value": "-5833",
        "unit": "USD_millions",
    }
    return claim, {table["id"]: table}, {"MU-2023": {"id": "MU-2023"}}


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("(5,833)", Decimal("-5833")),
        ("$16,370.3", Decimal("16370.3")),
        ("6.55", Decimal("6.55")),
        ("—", None),
        ("n/a", None),
        ("5,833 USD", None),
        ("", None),
    ],
)
def test_amount_parsing_preserves_sign_and_precision(raw, expected):
    assert number(raw) == expected


def test_true_claim_passes(evidence):
    assert verify_claim(*evidence)["supported"]


@pytest.mark.parametrize(
    "key,value,reason",
    [
        ("value", "5833", "numeric_mismatch"),
        ("value", "8687", "numeric_mismatch"),
        ("unit", "USD_thousands", "wrong_or_unresolved_unit"),
        ("period", 2022, "wrong_period_column"),
        ("doc_id", "AMD-2023", "wrong_entity"),
        ("page", 58, "wrong_page"),
        ("row_index", 2, "wrong_metric_row"),
        ("metric", "revenue", "wrong_metric_row"),
        ("column_index", 0, "invalid_cell"),
        ("row_index", -1, "invalid_cell"),
        ("table_id", "invented", "unknown_table"),
    ],
)
def test_tampering_rejected(evidence, key, value, reason):
    claim, tables, docs = deepcopy(evidence)
    claim[key] = value
    result = verify_claim(claim, tables, docs)
    assert not result["supported"]
    assert reason in result["reasons"]


def test_displayed_answer_cannot_disagree_with_claim(evidence):
    claim = evidence[0]
    good = "Micron reported -5,833 USD million for net income in FY2023."
    assert verify_answer_numbers(good, claim)["supported"]
    assert not verify_answer_numbers(good.replace("-5,833", "5,833"), claim)["supported"]
    assert not verify_answer_numbers(good + " Also 5,861.", claim)["supported"]
    assert not verify_answer_numbers(good.replace("million", "thousand"), claim)["supported"]


@pytest.mark.parametrize(
    "label",
    [
        "Weighted-average shares used in per share calculations: — Diluted",
        "Shares used to compute earnings per common share — diluted",
        "Diluted common shares outstanding",
        "Diluted earnings (loss) per share: — Continuing operations",
    ],
)
def test_share_counts_and_partial_eps_are_not_consolidated_eps(label):
    assert not matches_metric(label, "diluted_eps")


def test_per_share_unit_does_not_inherit_table_millions(evidence):
    claim, tables, docs = deepcopy(evidence)
    table = next(iter(tables.values()))
    table["rows"][1] = ["Diluted net income per common share", "4.02", "2.27", "0.65"]
    claim.update(
        row_label=table["rows"][1][0], metric="diluted_eps", value="4.02", unit="USD_per_share"
    )
    assert verify_claim(claim, tables, docs)["supported"]

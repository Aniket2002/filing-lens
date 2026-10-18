"""Deterministic row/column/entity/period/unit checks with Decimal arithmetic."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


def number(raw: str) -> Decimal | None:
    value = raw.strip().replace("$", "").replace(",", "").replace("−", "-")
    if value in {"—", "–", "-", ""}:
        # A dash can mean nil or unavailable. Never silently coerce it to zero.
        return None
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def matches_metric(label: str, metric: str) -> bool:
    label = re.sub(r"\s+", " ", label.lower()).strip()
    if metric == "diluted_eps" and re.search(
        r"\bshares\b|weighted|allocated|continuing|discontinued", label
    ):
        return False
    patterns = {
        "revenue": r"^(?:total )?(?:net )?(?:revenue[s]?|sales)$",
        "net_income": r"^net (?:income|loss)(?: \((?:loss|income)\))?$",
        "research_development": r"^research (?:and|&) development(?: expenses?)?(?: \(r&d\))?$",
        "total_assets": r"^total assets$",
        "diluted_eps": (
            r"(?:earnings|income|loss|per.share).*diluted|"
            r"diluted.*(?:earnings|per(?: common)?[ -]share)"
        ),
    }
    return bool(re.search(patterns.get(metric, r"(?!)"), label, re.I))


def row_unit(table: dict, label: str) -> str | None:
    if matches_metric(label, "diluted_eps"):
        return "USD_per_share"
    return table.get("unit")


def verify_claim(claim: dict, tables: dict[str, dict], documents: dict[str, dict]) -> dict:
    reasons = []
    table = tables.get(claim.get("table_id"))
    if table is None:
        return {"supported": False, "reasons": ["unknown_table"]}
    doc = documents.get(table["doc_id"])
    if not doc or claim.get("doc_id") != table["doc_id"]:
        reasons.append("wrong_entity")
    if claim.get("page") != table["page"]:
        reasons.append("wrong_page")
    row_index, column_index = claim.get("row_index"), claim.get("column_index")
    if (
        not isinstance(row_index, int)
        or not isinstance(column_index, int)
        or not 1 <= row_index < len(table["rows"])
        or not 1 <= column_index < len(table["rows"][row_index])
    ):
        return {"supported": False, "reasons": [*reasons, "invalid_cell"]}
    row = table["rows"][row_index]
    if claim.get("row_label") != row[0] or not matches_metric(row[0], claim.get("metric", "")):
        reasons.append("wrong_metric_row")
    years = table.get("years", [])
    if column_index > len(years) or claim.get("period") != years[column_index - 1]:
        reasons.append("wrong_period_column")
    unit = row_unit(table, row[0])
    if unit is None or claim.get("unit") != unit:
        reasons.append("wrong_or_unresolved_unit")
    source_number, claimed_number = number(row[column_index]), number(str(claim.get("value", "")))
    if source_number is None or claimed_number is None or source_number != claimed_number:
        reasons.append("numeric_mismatch")
    return {"supported": not reasons, "reasons": reasons, "source_value": row[column_index]}


def verify_answer_numbers(answer: str, claim: dict) -> dict:
    """The displayed amount must agree with the structured claim as well.

    The extractive reader emits a single-amount sentence with the fiscal year in
    FY notation. Dates, cell indexes, and citation page numbers are not amounts.
    """
    text = re.sub(r"\bFY\s*20\d{2}\b", "", answer, flags=re.I)
    found = re.findall(r"(?<![A-Za-z\d])\(?-?\d[\d,]*(?:\.\d+)?\)?", text)
    amounts = [number(s) for s in found]
    expected = number(str(claim.get("value", "")))
    unit_labels = {
        "USD_millions": "USD million",
        "USD_thousands": "USD thousand",
        "USD_per_share": "USD per share",
    }
    supported = (
        len(amounts) == 1
        and amounts[0] == expected
        and unit_labels.get(claim.get("unit"), "INVALID") in answer
    )
    return {
        "supported": supported,
        "extracted": found,
        "reasons": [] if supported else ["answer_claim_disagreement"],
    }

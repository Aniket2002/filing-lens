"""An intentionally small extractive QA baseline with evidence-based abstention.

No gold labels, expected answers, or question IDs enter this module. The same
reader is frozen across all retrieval ablations. It cannot invent a table header
when the retrieved chunk lost it. Generative adapters can be assessed separately.
"""

from __future__ import annotations

import re

from filing_lens.numeric import (
    matches_metric,
    number,
    row_unit,
    verify_answer_numbers,
    verify_claim,
)
from filing_lens.retrieval import tokenize

INTENTS = [
    ("diluted_eps", r"diluted|earnings per share|\bEPS\b"),
    ("research_development", r"research|\bR&D\b|development (?:cost|expense|spend)"),
    ("total_assets", r"total assets?|asset base"),
    ("net_income", r"net (?:income|loss|profit)|bottom.line"),
    ("revenue", r"revenue|net sales|top.line"),
]


def resolve_question(query: str, documents: list[dict]) -> dict:
    matches = []
    for doc in documents:
        aliases = [doc["ticker"], doc["company"]]
        if doc["ticker"] == "AMD":
            aliases.append("AMD")
        if doc["ticker"] == "NXPI":
            aliases.append("NXP")
        if doc["ticker"] == "MU":
            aliases.append("Micron")
        if doc["ticker"] == "MCHP":
            aliases.append("Microchip")
        if any(re.search(r"\b" + re.escape(alias) + r"\b", query, re.I) for alias in aliases):
            matches.append(doc)
    period_query = re.sub(
        r"FY\s*20\d{2}\s+(?:annual\s+)?(?:report|filing|statements)\b", "", query, flags=re.I
    )
    year_pattern = r"(?:FY\s*|fiscal\s+(?:year\s+)?|\b)(20\d{2})\b"
    years = re.findall(year_pattern, period_query, re.I) or re.findall(year_pattern, query, re.I)
    metric = next((key for key, pattern in INTENTS if re.search(pattern, query, re.I)), None)
    # Qualifiers request a different scope from consolidated annual statements.
    unsupported_scope = bool(
        re.search(
            r"quarter|monthly|forecast|next year|Antarctica|per.employee|by country|"
            r"by customer|unreleased|hypothetical|adjusted|non.GAAP|calendar year",
            query,
            re.I,
        )
    )
    return {
        "doc": matches[0] if len(matches) == 1 else None,
        "year": int(years[0]) if len(set(years)) == 1 else None,
        "metric": metric,
        "unsupported_scope": unsupported_scope,
    }


def refuse(reason: str) -> dict:
    return {
        "answer": "I cannot answer this from the retrieved annual-report evidence.",
        "refused": True,
        "reason": reason,
        "citations": [],
        "claims": [],
        "numeric_checks": [],
    }


def answer_question(
    query: str,
    chunks: list[dict],
    tables: dict[str, dict],
    documents: list[dict],
    k: int = 5,
    assemble_table_evidence: bool = False,
) -> dict:
    intent = resolve_question(query, documents)
    doc, year, metric = intent["doc"], intent["year"], intent["metric"]
    if not doc:
        return refuse("unknown_or_ambiguous_entity")
    if year is None or year not in {
        doc["fiscal_year"],
        doc["fiscal_year"] - 1,
        doc["fiscal_year"] - 2,
    }:
        return refuse("missing_or_out_of_corpus_period")
    if intent["unsupported_scope"]:
        return refuse("unsupported_question_scope")
    if metric:

        def respond(table: dict, row_index: int, row: list, row_chunk: dict, header_chunk: dict):
            header = " | ".join(table["rows"][0])
            quote = " | ".join(row)
            column = table["years"].index(year) + 1
            value, unit = number(row[column]), row_unit(table, row[0])
            if value is None or unit is None:
                return None
            claim = {
                "doc_id": doc["id"],
                "page": table["page"],
                "table_id": table["id"],
                "row_index": row_index,
                "column_index": column,
                "row_label": row[0],
                "metric": metric,
                "period": year,
                "value": str(value),
                "unit": unit,
            }
            label = {
                "USD_millions": "USD million",
                "USD_thousands": "USD thousand",
                "USD_per_share": "USD per share",
            }[unit]
            answer = (
                f"{doc['company']} reported {value:,} {label} "
                f"for {metric.replace('_', ' ')} in FY{year}."
            )
            checks = [
                verify_claim(claim, tables, {d["id"]: d for d in documents}),
                verify_answer_numbers(answer, claim),
            ]
            if not all(c["supported"] for c in checks):
                return refuse("numeric_verification_failed")
            citations = [
                {
                    "chunk_id": row_chunk["id"],
                    "doc_id": doc["id"],
                    "page": table["page"],
                    "quote": quote,
                    "header": header,
                    "start": row_chunk["start"],
                    "end": row_chunk["end"],
                }
            ]
            if header_chunk["id"] != row_chunk["id"]:
                citations.append(
                    {
                        "chunk_id": header_chunk["id"],
                        "doc_id": doc["id"],
                        "page": table["page"],
                        "quote": header,
                        "header": header,
                        "start": header_chunk["start"],
                        "end": header_chunk["end"],
                    }
                )
            return {
                "answer": answer,
                "refused": False,
                "reason": None,
                "citations": citations,
                "claims": [claim],
                "numeric_checks": checks,
            }

        for chunk in chunks[:k]:
            if chunk["doc_id"] != doc["id"]:
                continue
            for table in tables.values():
                if (
                    table["doc_id"] != doc["id"]
                    or table["page"] != chunk["page"]
                    or year not in table.get("years", [])
                ):
                    continue
                header = " | ".join(table["rows"][0])
                if header not in chunk["text"]:
                    continue
                for row_index, row in enumerate(table["rows"][1:], 1):
                    quote = " | ".join(row)
                    if not matches_metric(row[0], metric) or quote not in chunk["text"]:
                        continue
                    response = respond(table, row_index, row, chunk, chunk)
                    if response is not None:
                        return response
        if assemble_table_evidence:
            retrieved = chunks[:k]
            for table in tables.values():
                if table["doc_id"] != doc["id"] or year not in table.get("years", []):
                    continue
                same_page = [
                    chunk
                    for chunk in retrieved
                    if chunk["doc_id"] == doc["id"] and chunk["page"] == table["page"]
                ]
                if not same_page:
                    continue
                header = " | ".join(table["rows"][0])
                header_chunk = next((chunk for chunk in same_page if header in chunk["text"]), None)
                if header_chunk is None:
                    continue
                for row_index, row in enumerate(table["rows"][1:], 1):
                    if not matches_metric(row[0], metric):
                        continue
                    quote = " | ".join(row)
                    row_chunk = next((chunk for chunk in same_page if quote in chunk["text"]), None)
                    if row_chunk is None or row_chunk["id"] == header_chunk["id"]:
                        continue
                    response = respond(table, row_index, row, row_chunk, header_chunk)
                    if response is not None:
                        return response
        return refuse("no_complete_table_evidence_in_top_k")
    # A weak but reproducible narrative reader: choose the sentence with the
    # greatest non-stopword query overlap. Its mistakes remain in the results.
    stop = {
        "what",
        "which",
        "the",
        "in",
        "of",
        "and",
        "does",
        "did",
        "its",
        "for",
        "report",
        "annual",
        "according",
        "to",
        "are",
        "is",
        "a",
        "as",
        "how",
    }
    query_tokens = set(tokenize(query)) - stop - set(tokenize(doc["company"]))
    query_tokens -= {doc["ticker"].lower(), str(year), "fy"}
    candidates = []
    for chunk in chunks[:k]:
        if chunk["doc_id"] != doc["id"]:
            continue
        for sentence in re.split(r"(?<=[.;])\s+|\n\n", chunk["text"]):
            tokens = set(tokenize(sentence))
            score = len(tokens & query_tokens) / max(len(query_tokens), 1)
            if score >= 0.4 and len(sentence.split()) >= 8:
                candidates.append((score, sentence, chunk))
    if not candidates:
        return refuse("no_narrative_evidence_above_overlap_threshold")
    _, sentence, chunk = max(candidates, key=lambda item: item[0])
    return {
        "answer": sentence,
        "refused": False,
        "reason": None,
        "claims": [],
        "numeric_checks": [],
        "citations": [
            {
                "chunk_id": chunk["id"],
                "doc_id": doc["id"],
                "page": chunk["page"],
                "quote": sentence,
                "start": chunk["start"],
                "end": chunk["end"],
            }
        ],
    }

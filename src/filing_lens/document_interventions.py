"""Rebuild retrieval after interventions on reconstructed statement-page text.

This is a second exploratory experiment, not a general PDF extraction evaluation.
The answer boundary receives question text and retrieved chunks, never annotations.
"""

from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal

from filing_lens.chunking import chunk_pages
from filing_lens.io import digest
from filing_lens.numeric import matches_metric, number
from filing_lens.reader import resolve_question
from filing_lens.retrieval import Index

VARIANTS = ("base", "column_reverse", "unit_rescale", "reverse_and_rescale")
VIEWS = ("native", "unit_neutral")
METRICS = ("revenue", "net_income", "research_development", "total_assets", "diluted_eps")
SCALES = {"USD": Decimal(1), "USD_thousands": Decimal(1000), "USD_millions": Decimal(1000000)}


def decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def render_statement(table: dict) -> str:
    """Preparation uses all rows, not the queried metric or expected answer."""
    lines = [table["title"], " | ".join(["Metric", "Unit", *map(str, table["years"])])]
    for row in table["rows"][1:]:
        label = row[0].lower()
        if re.match(
            r"^(?:weighted[- ]average|weighted average|average shares|"
            r"(?:basic|diluted) common shares|(?:number of )?shares used)",
            label,
        ):
            unit = (
                "shares_thousands"
                if "in thousands" in label
                else table["unit"].replace("USD", "shares")
            )
        elif "per share" in label or "per common share" in label:
            unit = "USD_per_share"
        else:
            unit = table["unit"]
        if len(row) != len(table["years"]) + 1:
            raise ValueError(f"Ragged source table: {table['id']}")
        lines.append(" | ".join([row[0], unit, *row[1:]]))
    return "\n".join(lines)


def transform_statement(text: str, variant: str) -> str:
    """Mutate document text before indexing or answer-time cell parsing."""
    if variant not in VARIANTS:
        raise ValueError(f"Unknown variant: {variant}")
    lines = text.splitlines()
    header = lines[1].split(" | ")
    reverse = variant in {"column_reverse", "reverse_and_rescale"}
    rescale = variant in {"unit_rescale", "reverse_and_rescale"}
    result = [lines[0], " | ".join(header[:2] + (header[2:][::-1] if reverse else header[2:]))]
    for line in lines[2:]:
        label, unit, *values = line.split(" | ")
        if rescale and unit in SCALES:
            target = "USD_thousands" if unit == "USD_millions" else "USD_millions"
            values = [
                decimal_text(amount * SCALES[unit] / SCALES[target])
                if (amount := number(raw)) is not None
                else raw
                for raw in values
            ]
            unit = target
        result.append(" | ".join([label, unit, *(values[::-1] if reverse else values)]))
    return "\n".join(result)


def reconstruct_pages(pages: list[dict], tables: list[dict], variant: str) -> list[dict]:
    grouped = defaultdict(list)
    for table in tables:
        grouped[(table["doc_id"], table["page"])].append(table)
    available = {(p["doc_id"], p["page"]) for p in pages}
    if not set(grouped) <= available:
        raise ValueError("Statement source page is absent")
    result = []
    for page in pages:
        statements = grouped.get((page["doc_id"], page["page"]))
        if not statements:
            result.append(page)
            continue
        # Replace the whole affected page: no stale original copy of the table
        # can survive beside its transformed representation. This also removes
        # surrounding prose and is an explicitly documented simplification.
        text, blocks = "", []
        for table in statements:
            body = transform_statement(render_statement(table), variant)
            start = len(text)
            text += body
            blocks.append(
                {"start": start, "end": len(text), "kind": "table", "table_id": table["id"]}
            )
            text += "\n\n"
        result.append({**page, "text": text.rstrip(), "blocks": blocks})
    return result


def parse_cells(chunks: list[dict]) -> list[dict]:
    """Parse only complete retrieved rows with a visible period/unit header."""
    cells = []
    for chunk in chunks:
        years = None
        for line in chunk["text"].splitlines():
            fields = [part.strip() for part in line.split("|")]
            if len(fields) >= 3 and fields[:2] == ["Metric", "Unit"]:
                years = (
                    [int(y) for y in fields[2:]]
                    if all(re.fullmatch(r"20\d{2}", y) for y in fields[2:])
                    else None
                )
                if years and len(set(years)) != len(years):
                    years = None
                continue
            if not years or len(fields) != len(years) + 2:
                continue
            label, unit, *values = fields
            metrics = [m for m in METRICS if matches_metric(label, m)]
            if len(metrics) != 1:
                continue
            for year, raw in zip(years, values, strict=True):
                value = number(raw)
                if value is not None:
                    cells.append(
                        {
                            "doc_id": chunk["doc_id"],
                            "page": chunk["page"],
                            "chunk_id": chunk["id"],
                            "metric": metrics[0],
                            "year": year,
                            "unit": unit,
                            "value": decimal_text(value),
                            "row_label": label,
                        }
                    )
    return cells


def requested_unit(question: str, metric: str | None) -> str | None:
    if metric == "diluted_eps":
        return "USD_per_share"
    for word, unit in (("million", "USD_millions"), ("thousand", "USD_thousands")):
        if re.search(r"\bUSD\s+" + word + r"s?\b", question, re.I):
            return unit
    return None


def answer(question: str, chunks: list[dict], documents: list[dict]) -> dict:
    intent = resolve_question(question, documents)
    unit = requested_unit(question, intent["metric"])
    if not intent["doc"] or not intent["year"] or intent["unsupported_scope"] or not unit:
        return {"status": "unsupported_intent", "value": None, "citations": []}
    selected = [
        cell
        for cell in parse_cells(chunks)
        if cell["doc_id"] == intent["doc"]["id"]
        and cell["year"] == intent["year"]
        and cell["metric"] == intent["metric"]
    ]
    values, citations = set(), []
    for cell in selected:
        value = Decimal(cell["value"])
        if cell["unit"] != unit:
            if cell["unit"] not in SCALES or unit not in SCALES:
                continue
            value *= SCALES[cell["unit"]] / SCALES[unit]
        values.add(decimal_text(value))
        citations.append(cell)
    status = "numeric" if len(values) == 1 else "conflict" if values else "missing_evidence"
    return {
        "status": status,
        "value": next(iter(values)) if status == "numeric" else None,
        "unit": unit,
        "citations": citations,
    }


def score(question: dict, candidates: list[dict], chunks: list[dict], output: dict) -> dict:
    """Annotations enter only this evaluator, after retrieval and inference."""
    gold_pages = {(g["doc_id"], g["page"]) for g in question["gold"]}
    cells = parse_cells(chunks)
    return {
        "candidate_page_hit": any((c["doc_id"], c["page"]) in gold_pages for c in candidates),
        "top5_page_hit": any((c["doc_id"], c["page"]) in gold_pages for c in chunks),
        "cell_coverage": any(
            (c["doc_id"], c["page"]) in gold_pages
            and c["metric"] == question["metric"]
            and c["year"] == question["period"]
            for c in cells
        ),
        "correct": (
            output["status"] == "numeric"
            and output["unit"] == question["expected_unit"]
            and number(output["value"]) == number(question["expected_value"])
        ),
    }


def retrieval_text(text: str) -> str:
    """Mask monetary amounts and scale in the index; retain raw reader evidence.

    Period headers, entities, metrics, shares and per-share values are preserved.
    This lexical baseline is only intended for single-fact lookup, not thresholds
    or questions whose intent depends on a particular monetary amount.
    """
    lines = []
    for line in text.splitlines():
        fields = line.split("|")
        if len(fields) >= 3 and fields[1].strip() in SCALES:
            fields[1] = " USD monetary "
            fields[2:] = [" amount " if number(f.strip()) is not None else f for f in fields[2:]]
            line = "|".join(fields)
        lines.append(line)
    return re.sub(
        r"\bUSD[ _](?:millions?|thousands?)\b", "USD monetary", "\n".join(lines), flags=re.I
    )


def experiment(pages: list[dict], tables: list[dict], documents: list[dict], questions: list[dict]):
    outcomes, evidence, indexes = [], {}, []
    base_rankings = {}
    for variant in VARIANTS:
        transformed = reconstruct_pages(pages, tables, variant)
        for strategy in ("fixed", "structure"):
            chunks = chunk_pages(transformed, documents, strategy, size=160, overlap=32)
            by_id = {c["id"]: c for c in chunks}

            def record_evidence(visible, variant=variant):
                keys = []
                for chunk in visible:
                    key = digest((variant + "\n" + chunk["id"] + "\n" + chunk["text"]).encode())
                    evidence[key] = {"key": key, "variant": variant, "chunk": chunk}
                    keys.append(key)
                return keys

            for view in VIEWS:
                indexed = (
                    chunks
                    if view == "native"
                    else [{**c, "text": retrieval_text(c["text"])} for c in chunks]
                )
                # BM25 does not access Models; no model download or frozen rankings.
                index = Index(indexed, models=None, dense=False, documents=documents)
                indexes.append(
                    {
                        "variant": variant,
                        "strategy": strategy,
                        "view": view,
                        "chunks": len(chunks),
                        "corpus_sha256": digest("\n".join(c["text"] for c in chunks).encode()),
                        "index_sha256": digest("\n".join(c["text"] for c in indexed).encode()),
                    }
                )
                for question in questions:
                    query = question["question"]
                    if view == "unit_neutral":
                        query = retrieval_text(query)
                    retrieval = index.search(query, method="bm25", pool=20)
                    candidates = [by_id[c["id"]] for c in retrieval["chunks"]]
                    visible = candidates[:5]
                    base_key = (strategy, view, question["id"])
                    if variant == "base":
                        base_rankings[base_key] = [c["id"] for c in visible]
                    frozen = [by_id[c] for c in base_rankings[base_key]]
                    output = answer(question["question"], visible, documents)
                    frozen_output = answer(question["question"], frozen, documents)
                    outcomes.append(
                        {
                            "question_id": question["id"],
                            "split": question["split"],
                            "company": question["company"],
                            "variant": variant,
                            "strategy": strategy,
                            "view": view,
                            "candidate_trace": [
                                {k: row[k] for k in ("id", "doc_id", "page", "bm25_score")}
                                for row in retrieval["trace"]
                            ],
                            "evidence_keys": record_evidence(visible),
                            "frozen_evidence_keys": record_evidence(frozen),
                            "output": output,
                            "frozen_output": frozen_output,
                            "scores": score(question, candidates, visible, output),
                            "frozen_scores": score(question, frozen, frozen, frozen_output),
                        }
                    )
    return outcomes, list(evidence.values()), indexes

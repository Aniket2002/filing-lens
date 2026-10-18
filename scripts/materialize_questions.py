"""Resolve independently specified annotation anchors against parsed sources.

Amounts, units, questions, pages, and row labels come from annotations.json.
This script validates them; it never creates gold answers from reader outputs.
"""

from pathlib import Path

from filing_lens.io import digest, read_json, read_jsonl, write_json, write_jsonl
from filing_lens.numeric import number

root = Path(__file__).resolve().parents[1]
annotations = read_json(root / "data/annotations.json")
documents = {d["ticker"]: d for d in read_json(root / "data/corpus.json")["documents"]}
pages = {(p["doc_id"], p["page"]): p for p in read_jsonl(root / "data/processed/pages.jsonl")}
tables = {t["id"]: t for t in read_jsonl(root / "data/processed/tables.jsonl")}
questions = []


def base(ticker, kind, question):
    index = sum(q["company"] == ticker and q["kind"] == kind for q in questions) + 1
    return {
        "id": f"{ticker.lower()}-{kind}-{index:02}",
        "company": ticker,
        "kind": kind,
        "question": question,
        "split": "dev" if ticker in annotations["development_companies"] else "test",
        "annotation_status": "ai_authored_source_checked_pending_human_review",
    }


def anchor(ticker, page_no, quote):
    doc = documents[ticker]
    text = pages[(doc["id"], page_no)]["text"]
    start = text.rfind(quote)
    if start < 0:
        raise ValueError(f"Missing gold quote {ticker} p{page_no}: {quote!r}")
    return {
        "doc_id": doc["id"],
        "page": page_no,
        "start": start,
        "end": start + len(quote),
        "quote": quote,
        "source_url": doc["url"] + f"#page={page_no}",
    }


for ticker, page, metric, label, year, expected, unit, question in annotations["numeric"]:
    table = tables[f"{ticker}-2023:p{page}:statement"]
    row = next(row for row in table["rows"][1:] if row[0] == label)
    if number(row[table["years"].index(year) + 1]) != number(expected):
        raise ValueError(f"Independent value mismatch: {ticker}, {label}, {expected}, {row}")
    item = base(ticker, "numeric", question)
    item.update(
        {
            "answerable": True,
            "metric": metric,
            "period": year,
            "expected_value": expected,
            "expected_unit": unit,
            "gold": [anchor(ticker, page, " | ".join(row))],
        }
    )
    questions.append(item)

for ticker, page, question, quote, expected in annotations["narrative"]:
    item = base(ticker, "narrative", question)
    item.update(
        {"answerable": True, "expected_answer": expected, "gold": [anchor(ticker, page, quote)]}
    )
    questions.append(item)

for ticker, category, question, reason in annotations["unanswerable"]:
    item = base(ticker, "unanswerable", question)
    item.update(
        {
            "answerable": False,
            "unanswerable_category": category,
            "gold": [],
            "refusal_reason": reason,
        }
    )
    questions.append(item)

questions.sort(key=lambda q: q["id"])
write_jsonl(root / "data/questions.jsonl", questions)
write_json(
    root / "data/benchmark-lock.json",
    {
        "question_count": len(questions),
        "annotations_sha256": digest((root / "data/annotations.json").read_bytes()),
        "questions_sha256": digest((root / "data/questions.jsonl").read_bytes()),
        "pages_sha256": digest((root / "data/processed/pages.jsonl").read_bytes()),
        "tables_sha256": digest((root / "data/processed/tables.jsonl").read_bytes()),
        "authorship": annotations["authorship"],
        "split_unit": "company",
    },
)
print(f"Validated {len(questions)} independently specified annotations")

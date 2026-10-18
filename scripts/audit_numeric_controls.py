"""Isolated mutation study: do controls reject bad claims given a correct cell?

This uses gold cells to test the verifier, not to answer retrieval questions.
Its pass rate must never be described as end-to-end QA accuracy.
"""

from copy import deepcopy
from pathlib import Path

from filing_lens.io import read_json, read_jsonl, write_json, write_jsonl
from filing_lens.numeric import number, verify_answer_numbers, verify_claim

root = Path(__file__).resolve().parents[1]
questions = [q for q in read_jsonl(root / "data/questions.jsonl") if q["kind"] == "numeric"]
tables = {t["id"]: t for t in read_jsonl(root / "data/processed/tables.jsonl")}
documents = {d["id"]: d for d in read_json(root / "data/corpus.json")["documents"]}
rows = []
for q in questions:
    gold = q["gold"][0]
    table = tables[f"{gold['doc_id']}:p{gold['page']}:statement"]
    row_index = next(i for i, row in enumerate(table["rows"]) if " | ".join(row) == gold["quote"])
    claim = {
        "doc_id": table["doc_id"],
        "page": table["page"],
        "table_id": table["id"],
        "row_index": row_index,
        "column_index": table["years"].index(q["period"]) + 1,
        "row_label": table["rows"][row_index][0],
        "metric": q["metric"],
        "period": q["period"],
        "value": q["expected_value"],
        "unit": q["expected_unit"],
    }
    variations = {
        "correct": {},
        "wrong_amount": {"value": str(number(claim["value"]) + 1)},
        "wrong_sign": {"value": str(-number(claim["value"]))},
        "wrong_period": {"period": claim["period"] + 1},
        "wrong_unit": {"unit": "USD_billions"},
        "wrong_entity": {"doc_id": "WRONG-2023"},
        "wrong_page": {"page": claim["page"] + 1},
        "wrong_metric": {"metric": "invented_metric"},
        "wrong_column": {"column_index": 0},
    }
    for name, edits in variations.items():
        altered = deepcopy(claim)
        altered.update(edits)
        result = verify_claim(altered, tables, documents)
        rows.append(
            {
                "question_id": q["id"],
                "mutation": name,
                "claim": altered,
                "expected_supported": name == "correct",
                "observed": result,
                "pass": result["supported"] == (name == "correct"),
            }
        )
    label = {
        "USD_millions": "USD million",
        "USD_thousands": "USD thousand",
        "USD_per_share": "USD per share",
    }[claim["unit"]]
    displayed = (
        f"{documents[claim['doc_id']]['company']} reported "
        f"{number(claim['value']) + 1:,} {label} in FY{claim['period']}."
    )
    result = verify_answer_numbers(displayed, claim)
    rows.append(
        {
            "question_id": q["id"],
            "mutation": "displayed_amount_disagrees",
            "claim": claim,
            "answer": displayed,
            "expected_supported": False,
            "observed": result,
            "pass": not result["supported"],
        }
    )

output = root / "results/controls"
write_jsonl(output / "predictions.jsonl", rows)
write_json(
    output / "metrics.json",
    {
        "scope": "oracle source-cell verifier audit; not QA accuracy",
        "positive_claims": len(questions),
        "tampered_claims": len(rows) - len(questions),
        "cases": len(rows),
        "passed": sum(r["pass"] for r in rows),
        "by_mutation": {
            name: {
                "cases": sum(r["mutation"] == name for r in rows),
                "passed": sum(r["pass"] for r in rows if r["mutation"] == name),
            }
            for name in sorted({r["mutation"] for r in rows})
        },
    },
)
write_jsonl(
    root / "data/evidence/statement-tables.jsonl",
    [t for t in tables.values() if t.get("method") == "year_aligned_words"],
)
print(f"Verifier audit: {sum(r['pass'] for r in rows)}/{len(rows)} cases passed")

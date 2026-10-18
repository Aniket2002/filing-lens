"""Recompute published summary metrics and control checks offline, without models."""

from pathlib import Path

from filing_lens.evaluation import aggregate, retrieval_metrics
from filing_lens.generation import generated_amount
from filing_lens.io import digest, read_json, read_jsonl
from filing_lens.numeric import number, verify_answer_numbers, verify_claim

root = Path(__file__).resolve().parents[1]
manifest_path = root / "results/artifacts.json"
if manifest_path.exists():
    for record in read_json(manifest_path)["files"]:
        assert digest((root / record["path"]).read_bytes()) == record["sha256"], record["path"]
questions = {q["id"]: q for q in read_jsonl(root / "data/questions.jsonl")}
predictions = read_jsonl(root / "results/reference/predictions.jsonl")
metrics = read_json(root / "results/reference/metrics.json")
tables = {t["id"]: t for t in read_jsonl(root / "data/evidence/statement-tables.jsonl")}
documents = {d["id"]: d for d in read_json(root / "data/corpus.json")["documents"]}
assert len(predictions) == 80 * 12
assert len({(r["config"], r["question_id"]) for r in predictions}) == len(predictions)
for row in predictions:
    q = questions[row["question_id"]]
    recomputed = retrieval_metrics(row["ranking"], q["gold"])
    assert all(recomputed[m] == row[m] for m in recomputed), row["question_id"]
    for claim in row["response"]["claims"]:
        assert verify_claim(claim, tables, documents)["supported"]
        assert verify_answer_numbers(row["response"]["answer"], claim)["supported"]
for record in metrics:
    subset = [
        r
        for r in predictions
        if r["config"] == record["config"]
        and (record["split"] == "all" or r["split"] == record["split"])
    ]
    recomputed = aggregate(subset)
    assert all(recomputed[m] == record[m] for m in recomputed), record["config"]
for record in read_jsonl(root / "results/controls/predictions.jsonl"):
    observed = (
        verify_answer_numbers(record["answer"], record["claim"])
        if "answer" in record
        else verify_claim(record["claim"], tables, documents)
    )
    assert observed["supported"] == record["expected_supported"]

generator_rows = read_jsonl(root / "results/generator/predictions.jsonl")
assert len(generator_rows) == 70
for summary in read_json(root / "results/generator/metrics.json"):
    subset = [r for r in generator_rows if r["split"] == summary["split"]]
    recomputed = aggregate(subset)
    assert all(recomputed[m] == summary[m] for m in recomputed)
    numeric = [r for r in subset if r["kind"] == "numeric"]
    correct = sum(
        generated_amount(r["raw_output"]) == number(questions[r["question_id"]]["expected_value"])
        for r in numeric
    )
    assert correct / len(numeric) == summary["raw_amount_correctness"]
print(
    "Verified 960 retrieval records, 36 summary rows, 70 generator outputs, "
    "and all numeric-control mutations offline"
)

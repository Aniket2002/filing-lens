"""Recompute v2 generation decisions offline from preserved raw outputs and source rows."""

from pathlib import Path

from filing_lens.evaluation import aggregate
from filing_lens.generation import gate_generated, generated_amount
from filing_lens.generator_experiment import generation_context
from filing_lens.io import read_json, read_jsonl
from filing_lens.numeric import number, verify_answer_numbers, verify_claim

root = Path(__file__).resolve().parents[1]
questions = {q["id"]: q for q in read_jsonl(root / "data/questions.jsonl")}
tables = {t["id"]: t for t in read_jsonl(root / "data/evidence/statement-tables.jsonl")}
documents = {d["id"]: d for d in read_json(root / "data/corpus.json")["documents"]}
pilot = {r["question_id"]: r for r in read_jsonl(root / "results/generator/predictions.jsonl")}
for split in ("dev", "test"):
    path = root / "results/generator-v2" / split
    run = read_json(path / "run.json")
    rows = read_jsonl(path / "predictions.jsonl")
    expected_ids = {
        q["id"] for q in questions.values() if q["split"] == split and q["kind"] != "narrative"
    }
    assert len(rows) == len(expected_ids) == len({r["question_id"] for r in rows})
    assert {r["question_id"] for r in rows} == expected_ids
    candidates = {
        r["question_id"]: r["response"]
        for r in read_jsonl(root / f"results/iter1/{split}/predictions.jsonl")
    }
    for row in rows:
        q = questions[row["question_id"]]
        candidate = candidates[q["id"]]
        response = gate_generated(row["raw_output"], candidate, tables, documents)
        assert response == row["response"], q["id"]
        raw = generated_amount(row["raw_output"])
        assert row["raw_amount"] == (str(raw) if raw is not None else None)
        raw_correct = (
            raw is not None and raw == number(q["expected_value"])
            if q["answerable"]
            else row["raw_output"].strip() == "UNKNOWN"
        )
        assert row["raw_correct"] == raw_correct
        available = bool(candidate["claims"]) and not candidate["refused"]
        assert row["candidate_available"] == available
        context = (
            generation_context(candidate, [], tables, documents)
            if available
            else pilot[q["id"]]["context"]
        )
        assert row["context"] == context, q["id"]
        if not response["refused"]:
            assert q["answerable"] and response["claims"]
            claim = response["claims"][0]
            assert verify_claim(claim, tables, documents)["supported"]
            assert verify_answer_numbers(response["answer"], claim)["supported"]
            assert row["correct"] == (
                number(claim["value"]) == number(q["expected_value"])
                and claim["unit"] == q["expected_unit"]
                and claim["period"] == q["period"]
                and claim["metric"] == q["metric"]
                and claim["doc_id"].startswith(q["company"] + "-")
            )
        else:
            assert row["correct"] == (not q["answerable"])
    summary = read_json(path / "metrics.json")
    assert all(summary[k] == v for k, v in aggregate(rows).items())
    numeric = [r for r in rows if r["answerable"]]
    negatives = [r for r in rows if not r["answerable"]]
    available = [r for r in numeric if r["candidate_available"]]
    assert summary["raw_amount_correctness"] == sum(r["raw_correct"] for r in numeric) / len(
        numeric
    )
    assert summary["raw_exact_abstention_rate"] == sum(r["raw_correct"] for r in negatives) / len(
        negatives
    )
    assert summary["candidate_available"] == len(available)
    assert summary["raw_correct_given_candidate"] == sum(r["raw_correct"] for r in available) / len(
        available
    )
    assert summary["truncated_inputs"] == sum(r["input_truncated"] for r in rows)
    assert all(
        r["input_truncated"] == (r["input_tokens"] > run["generator_lock"]["max_input_tokens"])
        for r in rows
    )
assert read_json(root / "results/generator-v2/dev/run.json")["fingerprint"] == run["fingerprint"]
print("Verified 70 v2 outputs, guarded decisions, source contexts and both split summaries offline")

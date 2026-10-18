"""Verify explanation artifacts and recompute model-native refusal metrics offline."""

from datetime import datetime
from pathlib import Path

from filing_lens.explanations import model_decision, screen_concepts, summarize
from filing_lens.io import read_json, read_jsonl

root = Path(__file__).resolve().parents[1]
questions = {q["id"]: q for q in read_jsonl(root / "data/explanations/questions.jsonl")}
protocol = read_json(root / "data/explanations/protocol.json")
timestamps = [datetime.fromisoformat(protocol["frozen_utc"])]
for split in ("dev", "test"):
    path = root / "results/explanations" / split
    run = read_json(path / "run.json")
    assert run["status"] == "complete" and run["fingerprint"] == protocol["fingerprint"]
    timestamps.append(datetime.fromisoformat(run["created_utc"]))
    rows = read_jsonl(path / "predictions.jsonl")
    expected = {q["id"] for q in questions.values() if q["split"] == split}
    assert len(rows) == len(expected) == len({r["question_id"] for r in rows})
    assert {r["question_id"] for r in rows} == expected
    for row in rows:
        q = questions[row["question_id"]]
        response = row["response"]
        assert row["company"] == q["company"] and row["answerable"] == q["answerable"]
        assert row["split"] == split and row["topic_id"] == q["topic_id"]
        decision = model_decision(response["raw_answerability"])
        assert response["model_decision"] == decision
        assert response["model_refused"] == (decision == "no")
        assert response["protocol_error"] == (decision == "invalid")
        assert response["refused"] == (decision != "yes")
        assert response["numeric_checks"] == [] and response["claims"] == []
        assert response["citation_supported"] is None
        context = ""
        for item in response["input_sources"]:
            original = next(
                source
                for source in q["evidence"]
                if source["doc_id"] == item["doc_id"] and source["page"] == item["page"]
            )
            assert original["quote"].startswith(item["quote"])
            assert item["start"] == original["start"]
            assert item["end"] == item["start"] + len(item["quote"])
            assert item["input_excerpt_truncated"] == (item["quote"] != original["quote"])
            context += f"[{item['doc_id']} PDF p{item['page']}]\n{item['quote']}\n"
        assert response["input_context"] == context
        if decision == "yes":
            assert response["answer"] == response["raw_generation"]
            assert response["verification_status"] == "unverified_generation"
            assert response["citations"] == [
                {**item, "role": "input_context"} for item in response["input_sources"]
            ]
        else:
            assert response["raw_generation"] is None and response["citations"] == []
            assert response["reason"] == (
                "model_judged_context_insufficient"
                if decision == "no"
                else "model_answerability_protocol_error"
            )
        screen = screen_concepts(response["raw_generation"], q["concept_groups"])
        assert all(row[key] == value for key, value in screen.items())
    assert read_json(path / "metrics.json") == summarize(rows)
assert timestamps == sorted(timestamps)
print(
    "Verified 40 explanation outputs, native model decisions, context sources and split summaries"
)

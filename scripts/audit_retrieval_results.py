"""Audit retrieval-v2 rankings, selection, controls and aggregates without models/PDFs."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from filing_lens.evaluation import (
    aggregate,
    contains_gold,
    normalize,
    paired_company_bootstrap,
    retrieval_metrics,
)
from filing_lens.io import digest, read_json, read_jsonl
from filing_lens.numeric import number, verify_answer_numbers, verify_claim
from filing_lens.query_planning import plan_query
from filing_lens.retrieval_study import SETTINGS, candidate_diagnostics, select_on_dev


def audit(root: Path, output: Path) -> dict:
    questions = {q["id"]: q for q in read_jsonl(root / "data/questions.jsonl")}
    documents = read_json(root / "data/corpus.json")["documents"]
    doc_map = {d["id"]: d for d in documents}
    tables = {t["id"]: t for t in read_jsonl(root / "data/evidence/statement-tables.jsonl")}
    development = read_json(output / "dev/run.json")
    selected = select_on_dev(read_json(output / "dev/metrics.json"))
    assert selected == development["selected_on_dev"]
    checked = 0
    for split in ("dev", "test"):
        directory = output / split
        manifest = read_json(directory / "run.json")
        assert manifest["selected_on_dev"] == selected
        assert manifest["fingerprints"] == development["fingerprints"]
        if split == "test":
            assert manifest["development_manifest_sha256"] == digest(
                (output / "dev/run.json").read_bytes()
            )
        for name, expected in manifest["artifact_sha256"].items():
            assert digest((directory / name).read_bytes()) == expected, name
        # Canonical pages/tables are intentionally absent in a clean offline checkout.
        for name, expected in manifest["fingerprints"].items():
            if not name.startswith("data/processed/"):
                assert digest((root / name).read_bytes()) == expected, name
        settings = (
            SETTINGS
            if split == "dev"
            else [
                s
                for s in SETTINGS
                if s["id"] in {selected, "fixed-baseline-20", "structure-baseline-20"}
            ]
        )
        assert manifest["settings"] == settings
        settings_by_id = {s["id"]: s for s in settings}
        predictions = read_jsonl(directory / "predictions.jsonl")
        metrics = read_json(directory / "metrics.json")
        expected_keys = {
            (s["id"], q["id"]) for s in settings for q in questions.values() if q["split"] == split
        }
        assert {(r["config"], r["question_id"]) for r in predictions} == expected_keys
        assert len(predictions) == len(expected_keys)
        assert {m["config"] for m in metrics} == set(settings_by_id)
        assert len(metrics) == len(settings)
        for row in predictions:
            q, setting = questions[row["question_id"]], settings_by_id[row["config"]]
            for key in ("question", "company", "kind", "split", "answerable"):
                assert row[key] == q[key]
            assert row["query_plan"] == plan_query(q["question"], documents, setting["profile"])
            candidates, ranking = row["candidate_ranking"], row["ranking"]
            ids = [c["id"] for c in candidates]
            assert len(ids) == len(set(ids)) <= setting["candidate_pool"]
            assert len({c["id"] for c in ranking}) == len(ranking) <= 20
            scope = row["query_plan"]["doc_ids"]
            assert scope is None or all(c["doc_id"] in scope for c in candidates)
            assert all(c["doc_id"] in doc_map and c["end"] > c["start"] >= 0 for c in candidates)
            previous = float("inf")
            for rank, chunk in enumerate(ranking, 1):
                assert chunk["rank"] == rank
                assert chunk["candidate_rank"] == ids.index(chunk["id"]) + 1
                original = candidates[chunk["candidate_rank"] - 1]
                assert all(chunk[key] == original[key] for key in original)
                assert math.isfinite(chunk["reranker_score"])
                assert chunk["reranker_score"] <= previous
                previous = chunk["reranker_score"]
            recomputed = {
                **retrieval_metrics(ranking, q["gold"]),
                **candidate_diagnostics(candidates, ranking, q["gold"]),
            }
            assert all(row[key] == value for key, value in recomputed.items()), q["id"]
            response = row["response"]
            assert row["refused"] == response["refused"]
            correct = response["refused"] if not q["answerable"] else False
            if q["answerable"] and not response["refused"]:
                if q["kind"] == "numeric":
                    correct = any(
                        number(c["value"]) == number(q["expected_value"])
                        and c["unit"] == q["expected_unit"]
                        and c["period"] == q["period"]
                        and c["doc_id"].startswith(q["company"] + "-")
                        and c["metric"] == q["metric"]
                        for c in response["claims"]
                    )
                else:
                    correct = normalize(q["expected_answer"]) in normalize(response["answer"])
            assert row["correct"] == correct, q["id"]
            assert row["gold_citation_hit"] == (
                any(contains_gold(c, g) for c in response["citations"] for g in q["gold"])
                if q["gold"]
                else None
            )
            for claim in row["response"]["claims"]:
                assert verify_claim(claim, tables, doc_map)["supported"]
                assert verify_answer_numbers(row["response"]["answer"], claim)["supported"]
        for record in metrics:
            subset = [r for r in predictions if r["config"] == record["config"]]
            assert all(record[k] == v for k, v in aggregate(subset).items())
            answerable = [r for r in subset if r["answerable"]]
            assert record["candidate_recall"] == sum(
                r["candidate_recall"] for r in answerable
            ) / len(answerable)
            assert record["failure_counts"] == {
                name: sum(r["retrieval_failure"] == name for r in answerable)
                for name in ("hit_at_5", "candidate_miss", "ranking_miss")
            }
        for comparison in manifest["paired_comparisons"]:
            left = [r for r in predictions if r["config"] == comparison["baseline"]]
            right = [r for r in predictions if r["config"] == selected]
            assert comparison["metrics"] == [
                paired_company_bootstrap(left, right, m)
                for m in ("recall_at_5", "mrr_at_20", "correct")
            ]
        checked += len(predictions)
    return {"predictions": checked, "selected_on_dev": selected}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results/retrieval-v2"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(audit(root, root / args.results))

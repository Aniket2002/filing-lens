import pytest

from filing_lens.io import digest, write_json
from filing_lens.retrieval_study import candidate_diagnostics, select_on_dev, verify_dev


def test_selection_ignores_answers_and_prefers_recall_then_mrr_then_cost():
    base = {"split": "dev", "recall_at_5": 0.8, "mrr_at_20": 0.5, "candidate_pool": 20}
    rows = [
        {**base, "config": "a", "answer_correctness": 1},
        {**base, "config": "b", "recall_at_5": 0.9, "answer_correctness": 0},
        {**base, "config": "c", "recall_at_5": 0.9, "candidate_pool": 60},
    ]
    assert select_on_dev(rows) == "b"
    with pytest.raises(ValueError, match="development"):
        select_on_dev([{**base, "config": "test", "split": "test"}])


def test_failure_attribution_distinguishes_candidate_recall_from_ranking():
    gold = {"doc_id": "A", "page": 1, "start": 0, "end": 20}
    wrong = {**gold, "doc_id": "B"}
    assert candidate_diagnostics([wrong], [wrong], [gold])["retrieval_failure"] == "candidate_miss"
    assert candidate_diagnostics([gold], [wrong], [gold])["retrieval_failure"] == "ranking_miss"
    assert candidate_diagnostics([gold], [gold], [gold])["retrieval_failure"] == "hit_at_5"
    assert candidate_diagnostics([gold], [gold], [])["candidate_recall"] is None


def test_test_run_rejects_changed_code_and_tampered_dev_artifacts(tmp_path):
    path = tmp_path / "dev"
    metrics = [
        {"config": "a", "split": "dev", "recall_at_5": 0.5, "mrr_at_20": 0.4, "candidate_pool": 20}
    ]
    write_json(path / "metrics.json", metrics)
    write_json(
        path / "run.json",
        {
            "fingerprints": {"code": "frozen"},
            "selected_on_dev": "a",
            "artifact_sha256": {"metrics.json": digest((path / "metrics.json").read_bytes())},
        },
    )
    assert verify_dev(tmp_path, {"code": "frozen"})["selected_on_dev"] == "a"
    with pytest.raises(ValueError, match="changed since development"):
        verify_dev(tmp_path, {"code": "modified"})
    write_json(path / "metrics.json", [])
    with pytest.raises(ValueError, match="artifact changed"):
        verify_dev(tmp_path, {"code": "frozen"})

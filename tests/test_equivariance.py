import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from filing_lens.equivariance import (
    PRESERVING,
    build_cases,
    convert,
    decode,
    infer_input,
    intervene,
    score,
    summarize,
)
from filing_lens.io import digest, read_json, read_jsonl, write_json, write_jsonl

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def cases():
    return build_cases(ROOT)


def test_financial_dimensions_do_not_scale_eps_or_round_negative_amounts():
    assert convert("-0.001", "USD_millions", "USD_thousands") == "-1"
    assert convert("1.23", "USD_per_share", "USD_per_share") == "1.23"
    with pytest.raises(ValueError, match="dimensions"):
        convert("1.23", "USD_per_share", "USD_millions")


def test_interventions_preserve_economic_values_but_rebind_period_truth(cases):
    by_id = {(c["question_id"], c["source"], c["variant"]): c for c in cases}
    assert len(cases) == 600
    for case in cases:
        base = by_id[(case["question_id"], case["source"], "base")]
        if case["variant"] in PRESERVING:
            assert case["expected_value"] == base["expected_value"]
            assert case["target_ids"] == base["target_ids"]
            assert {c["id"] for c in case["cells"]} == {c["id"] for c in base["cells"]}
        elif case["variant"] == "remove_period":
            assert case["expected_value"] is None
            assert not case["target_ids"]
            assert all(c["period"] != case["period"] for c in case["cells"])
        elif case["variant"] == "period_rebind" and case["target_ids"]:
            assert case["target_ids"] != base["target_ids"]
            assert case["task_value"] != base["task_value"]
    assert any(
        c["expected_value"] != by_id[(c["question_id"], c["source"], "base")]["expected_value"]
        for c in cases
        if c["variant"] == "period_rebind"
    )


def test_canonical_prompts_commute_with_preserving_transformations(cases):
    for case in cases:
        if case["variant"] != "base":
            continue
        for arm in ("canonical_amount", "canonical_pointer"):
            original = infer_input(case["question"], case["unit"], case["cells"], arm)
            for variant in PRESERVING:
                changed = intervene(case["cells"], variant, case["period"])
                assert infer_input(case["question"], case["unit"], changed, arm) == original


def test_inference_has_no_labels_and_pointer_does_not_silently_correct_wrong_year(cases):
    case = next(c for c in cases if c["variant"] == "base" and c["source"] == "oracle_page")
    wrong = next(c for c in case["cells"] if c["period"] == 2022 and c["unit"] == case["unit"])
    result = decode(wrong["id"], case["cells"], case["unit"], "canonical_pointer")
    assert result["status"] == "numeric"
    assert not score(case, result)["coordinate_correct"]
    assert decode("C99999", case["cells"], case["unit"], "canonical_pointer")["status"] == "invalid"
    assert decode("not sure", case["cells"], case["unit"], "native_amount")["status"] == "invalid"
    assert decode("UNKNOWN", [], case["unit"], "native_amount")["status"] == "abstain"
    assert not score(
        {**case, "expected_value": None}, {"value": None, "selected_id": None, "status": "invalid"}
    )["context_correct"]
    before = deepcopy(case["cells"])
    infer_input(case["question"], case["unit"], case["cells"], "canonical_pointer")
    assert case["cells"] == before


def test_always_abstaining_is_consistent_but_never_usefully_equivariant():
    rows = []
    for arm in ("native_amount", "canonical_pointer"):
        for variant in ("base", "unit_rescale"):
            rows.append(
                {
                    "source": "retrieved_pages",
                    "arm": arm,
                    "variant": variant,
                    "question_id": "a",
                    "company": "A",
                    "usable_correct": False,
                    "context_correct": False,
                    "task_correct": False,
                    "output": {"value": None, "status": "abstain"},
                }
            )
    metrics = summarize(rows)
    for group in metrics["groups"]:
        assert group["same_output"] == 1
        assert group["paired_usable"] == 0
        assert group["coverage"] == 0


def test_audit_recomputes_scores_even_if_a_modified_prediction_is_resealed(
    tmp_path, monkeypatch, cases
):
    import filing_lens.equivariance as study

    # Isolate the prediction audit; the separate freeze validation checks the dataset.
    monkeypatch.setattr(study, "validate_freeze", lambda root: cases)
    folder = tmp_path / "results/equivariance/small/dev"
    shutil.copytree(ROOT / "results/equivariance/small/dev", folder)
    (tmp_path / study.STUDY).mkdir(parents=True)
    for name in ("protocol.json", "freeze.json"):
        shutil.copyfile(ROOT / study.STUDY / name, tmp_path / study.STUDY / name)
    assert study.audit(tmp_path) == 720
    predictions = read_jsonl(folder / "predictions.jsonl")
    predictions[0]["usable_correct"] = not predictions[0]["usable_correct"]
    write_jsonl(folder / "predictions.jsonl", predictions)
    run = read_json(folder / "run.json")
    run["files"]["predictions.jsonl"] = digest((folder / "predictions.jsonl").read_bytes())
    write_json(folder / "run.json", run)
    with pytest.raises(ValueError, match="score mismatch"):
        study.audit(tmp_path)


def test_freeze_rejects_changed_source_before_building_cases(tmp_path):
    import filing_lens.equivariance as study

    for name in study.INPUTS:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    shutil.copyfile(ROOT / study.STUDY / "freeze.json", tmp_path / study.STUDY / "freeze.json")
    (tmp_path / "data/questions.jsonl").write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="inputs changed"):
        study.validate_freeze(tmp_path)

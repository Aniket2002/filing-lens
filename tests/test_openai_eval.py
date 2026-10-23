import importlib.util
import json
import runpy
from decimal import Decimal
from pathlib import Path

import httpx
import pytest

from filing_lens.io import read_json, write_json
from filing_lens.openai_eval import (
    credential,
    estimated_cost,
    execute,
    request_body,
    request_digest,
    reserve_cost,
    response_text,
    verify_record,
)

SETTINGS = {
    "model": "model-snapshot",
    "max_input_bytes": 200,
    "max_output_tokens": 32,
    "temperature": 0,
    "reasoning_effort": "none",
    "usd_per_million_tokens": {"input": "2.50", "cached_input": "0.25", "output": "15"},
}


def response(status="completed", text="123"):
    return {
        "id": "response-fixture",
        "model": SETTINGS["model"],
        "status": status,
        "usage": {"input_tokens": 100, "output_tokens": 5},
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
    }


def test_only_completed_assistant_answers_can_be_scored():
    assert response_text(response()) == "123"
    assert response_text(response(status="incomplete")) == ""
    assert response_text(response(status="failed")) == ""
    value = response()
    value["output"][0]["content"].append({"type": "refusal", "refusal": "No"})
    assert response_text(value) == ""
    value["output"] = [{"type": "reasoning", "summary": [{"text": "123"}]}]
    assert response_text(value) == ""


def test_usage_cost_includes_cached_tokens_and_bounds():
    usage = {"input_tokens": 100, "output_tokens": 5, "input_tokens_details": {"cached_tokens": 20}}
    assert estimated_cost(usage, SETTINGS) == Decimal("0.000280")
    assert reserve_cost(request_body("abc", SETTINGS), SETTINGS) > estimated_cost(usage, SETTINGS)
    for bad in (-1, 101, True):
        usage["input_tokens_details"]["cached_tokens"] = bad
        with pytest.raises(ValueError):
            estimated_cost(usage, SETTINGS)


def test_request_is_stateless_and_rejects_oversized_utf8():
    body = request_body("answer", SETTINGS)
    assert body["store"] is False
    assert body["truncation"] == "disabled"
    assert "tools" not in body and "previous_response_id" not in body
    with pytest.raises(ValueError, match="ceiling"):
        request_body("\u20ac" * 100, SETTINGS)
    assert request_digest(body) != request_digest({**body, "model": "different"})


def test_success_is_saved_and_resume_does_not_repeat_paid_request(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        assert str(request.url) == "https://api.openai.com/v1/responses"
        return httpx.Response(200, json=response(), headers={"x-request-id": "request-fixture"})

    body = request_body("answer", SETTINGS)
    with httpx.Client(
        base_url="https://api.openai.com/v1", transport=httpx.MockTransport(handler)
    ) as http:
        first = execute(http, body, SETTINGS, tmp_path)
        assert execute(http, body, SETTINGS, tmp_path) == first
    assert len(calls) == 1
    assert not list(tmp_path.glob("*.pending"))
    first["response"]["model"] = "other-model"
    with pytest.raises(ValueError, match="version"):
        verify_record(first, body, SETTINGS)


def test_billing_failure_does_not_store_server_message_or_retry(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            429,
            json={"error": {"code": "credit_balance_exhausted", "message": "sensitive-example"}},
        )

    body = request_body("answer", SETTINGS)
    with httpx.Client(
        base_url="https://api.openai.com/v1", transport=httpx.MockTransport(handler)
    ) as http:
        with pytest.raises(RuntimeError, match="credit_balance_exhausted"):
            execute(http, body, SETTINGS, tmp_path)
    assert len(calls) == 1
    assert not list(tmp_path.glob("*.pending"))
    assert "sensitive-example" not in json.dumps(read_json(next(tmp_path.glob("*.error.json"))))


def test_ambiguous_connection_cannot_be_silently_retried(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("sensitive-example")

    body = request_body("answer", SETTINGS)
    with httpx.Client(
        base_url="https://api.openai.com/v1", transport=httpx.MockTransport(handler)
    ) as http:
        with pytest.raises(RuntimeError, match="no automatic retry"):
            execute(http, body, SETTINGS, tmp_path)
        with pytest.raises(FileExistsError):
            execute(http, body, SETTINGS, tmp_path)
    assert len(calls) == 1


def test_credential_file_is_read_only_and_not_a_repo_dependency(tmp_path, monkeypatch):
    path = tmp_path / "private-key.txt"
    path.write_text("test-credential-only")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY_FILE", str(path))
    assert credential() == "test-credential-only"
    monkeypatch.setenv("OPENAI_API_KEY", "environment-value")
    assert credential() == "environment-value"


@pytest.fixture
def runner(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "openai_runner_test", root / "scripts/run_openai_document_llms.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = runpy.run_path(str(root / "scripts/run_document_llms.py"))
    case = {
        "id": "fixture:base",
        "question_id": "fixture",
        "split": "dev",
        "company": "Fixture",
        "view": "native",
        "variant": "base",
        "cells": [],
        "unit": "USD_millions",
        "expected_unit": "USD_millions",
        "expected_value": "123",
        "gold_pages": [],
        "metric": "revenue",
        "period": 2023,
    }
    work = [(case, "native_amount", "answer")]
    protocol = {**SETTINGS, "models": {"gpt54": SETTINGS}, "estimated_budget_usd": "0.01"}
    write_json(tmp_path / module.STUDY / "protocol.json", protocol)
    write_json(tmp_path / module.STUDY / "freeze.json", {"test_fixture": True})
    monkeypatch.setattr(module, "validate", lambda root: work)
    monkeypatch.setattr(module, "upstream", lambda root: source)
    return module


def test_budget_stops_before_dispatch_and_releases_process_lock(runner, tmp_path, monkeypatch):
    path = tmp_path / runner.STUDY / "protocol.json"
    protocol = read_json(path)
    protocol["estimated_budget_usd"] = "0.000001"
    write_json(path, protocol)

    def handler(request):
        pytest.fail("Budget must stop before any network request")

    monkeypatch.setattr(
        runner,
        "client",
        lambda: httpx.Client(
            base_url="https://api.openai.com/v1", transport=httpx.MockTransport(handler)
        ),
    )
    with pytest.raises(RuntimeError, match="budget exhausted"):
        runner.run(tmp_path, "gpt54")
    assert not (tmp_path / ".cache/openai-evaluation.lock").exists()
    assert not (tmp_path / runner.RESULTS / "gpt54/run.json").exists()


def test_run_audit_reconstructs_scores_and_rejects_artifact_tampering(
    runner, tmp_path, monkeypatch
):
    def handler(request):
        return httpx.Response(200, json=response(), headers={"x-request-id": "fixture-request"})

    monkeypatch.setattr(
        runner,
        "client",
        lambda: httpx.Client(
            base_url="https://api.openai.com/v1", transport=httpx.MockTransport(handler)
        ),
    )
    runner.run(tmp_path, "gpt54")
    summary = runner.audit(tmp_path, "gpt54")
    assert summary[0]["correct"] == 1
    assert summary[0]["paired_correct"] == 1
    with pytest.raises(FileExistsError, match="immutable"):
        runner.run(tmp_path, "gpt54")
    path = tmp_path / runner.RESULTS / "gpt54/metrics.json"
    write_json(path, [])
    with pytest.raises(ValueError, match="artifact changed"):
        runner.audit(tmp_path, "gpt54")

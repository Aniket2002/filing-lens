"""Small Responses API transport for auditable, budgeted research runs.

Credentials are loaded at runtime and never included in returned records.
There are no implicit retries, model substitutions, tools, or context truncation.
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx

from filing_lens.io import digest, read_json, write_json

API = "https://api.openai.com/v1"


def credential() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        path = os.environ.get("OPENAI_API_KEY_FILE")
        if not path and os.environ.get("LOCALAPPDATA"):
            path = str(Path(os.environ["LOCALAPPDATA"]) / "FilingLens/private/openai-key.txt")
        if path and Path(path).is_file():
            key = Path(path).read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError("Set OPENAI_API_KEY or OPENAI_API_KEY_FILE outside the repository")
    return key


def client() -> httpx.Client:
    return httpx.Client(
        base_url=API,
        headers={"Authorization": "Bearer " + credential()},
        timeout=90,
        follow_redirects=False,
    )


def request_body(prompt: str, settings: dict) -> dict:
    if len(prompt.encode("utf-8")) > settings["max_input_bytes"]:
        raise ValueError("Prompt exceeds frozen input-byte ceiling; refusing truncation")
    return {
        "model": settings["model"],
        "input": prompt,
        "reasoning": {"effort": settings["reasoning_effort"]},
        "temperature": settings["temperature"],
        "max_output_tokens": settings["max_output_tokens"],
        "store": False,
        "truncation": "disabled",
        "service_tier": "default",
    }


def request_digest(body: dict) -> str:
    return digest(json.dumps(body, sort_keys=True, ensure_ascii=False).encode())


def response_text(response: dict) -> str:
    # Do not score a truncated numeric prefix, a refusal, or a reasoning summary.
    if response.get("status") != "completed":
        return ""
    content = [
        c
        for item in response.get("output", [])
        if item.get("type") == "message" and item.get("role") == "assistant"
        for c in item.get("content", [])
    ]
    if any(c.get("type") == "refusal" for c in content):
        return ""
    return "".join(c["text"] for c in content if c.get("type") == "output_text").strip()


def estimated_cost(usage: dict, settings: dict) -> Decimal:
    incoming, outgoing = usage["input_tokens"], usage["output_tokens"]
    cached = usage.get("input_tokens_details", {}).get("cached_tokens", 0)
    if not all(type(n) is int and n >= 0 for n in (incoming, outgoing, cached)):
        raise ValueError("Invalid token usage")
    if cached > incoming:
        raise ValueError("Cached tokens exceed total input")
    rates = settings["usd_per_million_tokens"]
    return (
        Decimal(incoming - cached) * Decimal(str(rates["input"]))
        + Decimal(cached) * Decimal(str(rates["cached_input"]))
        + Decimal(outgoing) * Decimal(str(rates["output"]))
    ) / Decimal(1_000_000)


def reserve_cost(body: dict, settings: dict) -> Decimal:
    # UTF-8 bytes plus message overhead is deliberately conservative for these
    # short text-only prompts. This is an estimate, not an account billing cap.
    return estimated_cost(
        {
            "input_tokens": len(body["input"].encode("utf-8")) + 512,
            "output_tokens": body["max_output_tokens"],
        },
        settings,
    )


def verify_record(record: dict, body: dict, settings: dict) -> None:
    response = record["response"]
    if record["request_sha256"] != request_digest(body):
        raise ValueError("Response belongs to a different request")
    if response["model"] != settings["model"]:
        raise ValueError("API returned a different model version")
    if response.get("status") not in {"completed", "incomplete", "failed"}:
        raise ValueError("Unexpected API response status")
    if not response.get("id") or not record.get("request_id"):
        raise ValueError("Missing provider request/response provenance")
    if response["usage"]["output_tokens"] > settings["max_output_tokens"]:
        raise ValueError("Provider output exceeds frozen token ceiling")
    if Decimal(record["estimated_usd"]) != estimated_cost(response["usage"], settings):
        raise ValueError("Recorded cost estimate differs from usage")


def execute(http: httpx.Client, body: dict, settings: dict, folder: Path) -> dict:
    """One attempt with a durable pending marker; caller serializes budget updates."""
    key = request_digest(body)
    target, pending = folder / f"{key}.json", folder / f"{key}.pending"
    if target.exists():
        record = read_json(target)
        verify_record(record, body, settings)
        return record
    folder.mkdir(parents=True, exist_ok=True)
    # An interrupted/ambiguous attempt must be investigated, not silently charged twice.
    with pending.open("x", encoding="utf-8") as stream:
        json.dump(
            {"request_sha256": key, "reserved_usd": str(reserve_cost(body, settings))}, stream
        )
    started = datetime.now(UTC).isoformat()
    start = time.perf_counter()
    try:
        response = http.post("/responses", json=body)
    except httpx.HTTPError:
        raise RuntimeError(
            "API transport failed; pending marker retained; no automatic retry"
        ) from None
    if not response.is_success:
        try:
            code = response.json().get("error", {}).get("code")
        except ValueError:
            code = None
        # Never log server messages or headers that could echo credentials.
        error = {"http_status": response.status_code, "error_code": code, "started_utc": started}
        write_json(folder / f"{key}.error.json", error)
        if response.status_code in {400, 401, 403, 404, 429}:
            pending.unlink()  # Explicitly rejected; a later user-triggered run may retry.
        raise RuntimeError(f"API rejected request: HTTP {response.status_code}, code={code}")
    data = response.json()
    record = {
        "request_sha256": key,
        "request_id": response.headers.get("x-request-id"),
        "started_utc": started,
        "elapsed_seconds": time.perf_counter() - start,
        "response": data,
        "estimated_usd": str(estimated_cost(data["usage"], settings)),
    }
    # Save even unexpected model/status responses for diagnosis; never resample them.
    write_json(target, record)
    pending.unlink()
    verify_record(record, body, settings)
    return record

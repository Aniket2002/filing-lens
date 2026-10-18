# Local API

After fetching and parsing the corpus, start the API:

```bash
uv run filing-lens serve --reader flan-t5-base
```

The default address is `127.0.0.1:8000`. Retrieval uses the development-selected
configuration, and same-page table-evidence assembly is enabled. Add
`--no-assemble-table-evidence` to use the original evidence gate. To avoid model
downloads for a lexical extractive demonstration:

```bash
uv run filing-lens serve --config fixed-bm25 --reader extractive
```

This process loads the corpus/index/models once and uses the same `QueryEngine`
as `ask`. It does not read evaluation questions or annotations. Readiness is
available only after initialization completes. Inference is serialized within
the engine to limit simultaneous CPU model execution.

## Request and response

`POST /ask` requires `Content-Type: application/json` and this body:

```json
{"question": "How much net income did Advanced Micro Devices earn in FY2023 (USD millions)?"}
```

For PowerShell:

```powershell
$body = @{question = "How much net income did Advanced Micro Devices earn in FY2023 (USD millions)?"} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/ask -Method Post -ContentType application/json -Body $body
```

A successful response includes `answer`, `refused`, `reason`, `citations`, `claims`,
`numeric_checks`, the retrieval `config`, `reader` and `table_evidence_assembly`.
Generative responses also preserve `raw_generation`. Citations include source URLs
with one-based PDF pages. An evidence-based refusal is HTTP 200 with `refused: true`.
Malformed requests are 400, oversized bodies 413, unsupported media types 415,
unknown routes 404 and unexpected inference failures 500. Each POST has an
`X-Request-ID` header. Bodies are limited to 16 KiB and questions to 2,000 characters.

## Operational visibility

- `GET /health`: process is serving HTTP.
- `GET /ready`: initialized engine's retrieval configuration and reader.
- `GET /metrics`: cumulative POST request, error, answer, refusal, numeric
  verification failure and elapsed-time counters, plus process uptime.

Elapsed time includes inference and waiting for the engine lock. Metrics are
in-memory and reset when the process restarts. The endpoints do not claim to
measure answer correctness: live questions have no gold labels. GET probes are
excluded from the inference request counters.

JSON logs on stderr contain request IDs, status, duration, refusal state and gate
reason. Questions, source excerpts and generated answers are omitted from logs.
Unexpected exceptions return a generic error rather than server filesystem details.

This is a local demonstration using Python's standard-library HTTP server. It has
no production deployment, authentication, TLS, persistent telemetry, alerting,
rate limits or bounded request queue. External hosting and monitoring are future
work; exposing this server publicly is not a production deployment plan.

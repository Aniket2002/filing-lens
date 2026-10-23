# OpenAI matched-reader extension

**Status: implemented; evaluation inference has not run.** Authentication succeeded, but two non-benchmark compatibility requests were rejected with HTTP 429 and `credit_balance_exhausted` on 23 October 2026. No OpenAI accuracy result is claimed. Test fixtures are not model outputs.

The [protocol](protocol.json) specifies `gpt-5.4-2026-03-05` and `gpt-5.4-mini-2026-03-17`. These dated versions are listed in the authenticated account and documented by OpenAI. They add a different model family relative to FLAN-T5; they are two configurations within the same OpenAI family, and their parameter counts are not established here. They were chosen for dated versions and a bounded short-answer comparison, not claimed to be the latest models.

The planned design preserves all 400 cases, both retrieval views, four transformations and four decoding arms from the [matched FLAN study](../document-llms/README.md): **1,600 outcomes and 906 unique requests per model**, or 3,200 outcomes and 1,812 requests in total. Development runs before test; no arms or settings are selected between them. The original prompt constructor, exact decoder and scorer are reused. Gold labels enter scoring, not requests. Identical requests reuse a recorded response, so agreement is partly structural rather than evidence of repeated sampling stability.

The Responses API is called with no tools or conversation history, `store=false`, truncation disabled, temperature zero, reasoning disabled, and a 32-token output ceiling. Incomplete, failed and refused responses score as numeric failures; they are not resampled until successful. All successful HTTP response bodies, provider request/response IDs, model identifiers, token usage, timestamps and estimated costs are retained. The input-byte guard differs from the FLAN tokenizer guard; actual OpenAI token counts are retained for reporting. These settings test a matched short-answer interface, not each model's maximum capability.

## Credentials and spending

Never put credentials in source, protocol files, command-line arguments, or published artifacts. The runner reads `OPENAI_API_KEY`, or a private file referenced by `OPENAI_API_KEY_FILE`. On Windows it can also read `%LOCALAPPDATA%/FilingLens/private/openai-key.txt`, outside this repository. The repository contains no credential file or key value.

The protocol imposes a **$10 estimated total study budget** across both model runs. Before each new request, the runner reserves a conservative UTF-8-byte-based input estimate and the maximum output allocation, then accounts for returned token usage at the recorded rates. This is local accounting, not a provider-enforced billing limit. A single-run lock prevents concurrent processes from independently spending the same allowance. There are no automatic retries. Interrupted or ambiguous requests leave a pending marker and block further spending until investigated. Explicitly rejected requests are logged without server error messages; a later run can retry them after the underlying problem is fixed. Completed responses are reused on resume.

## Run and audit

Install the existing locked environment; no new SDK dependency is required. The runner uses the locked `httpx` dependency against the official API endpoint.

```powershell
uv run python scripts/run_openai_document_llms.py check
# After configuring a funded API credential outside the repository:
uv run python scripts/run_openai_document_llms.py run --model gpt54
uv run python scripts/run_openai_document_llms.py run --model gpt54mini
uv run python scripts/run_openai_document_llms.py report
uv run python scripts/run_openai_document_llms.py audit
```

The execution freeze is created once with `prepare`, after implementation tests and before benchmark requests. `check` validates frozen code, protocol, upstream evidence and request coverage without network access. `audit` requires both complete runs; it must fail rather than treat absent results as a successful evaluation. It reconstructs requests, decodes saved responses, recomputes all scores and checks usage accounting and file hashes. Ordinary CI validates preparation and mocked transport behavior; it does not use API credentials or perform paid inference.

No measured results are added to the paper until complete response artifacts pass this audit. Adding OpenAI models does not supply a fresh holdout, independent financial annotation, realistic PDF/iXBRL transformations, or historical restatement evidence. Those gaps remain separate.

Sources checked 23 October 2026: [Responses text generation](https://developers.openai.com/api/docs/guides/text), [GPT-5.4 versions and pricing](https://developers.openai.com/api/docs/models/gpt-5.4), [GPT-5.4 mini versions and pricing](https://developers.openai.com/api/docs/models/gpt-5.4-mini). Hosted model behavior may vary even with dated versions and temperature zero.

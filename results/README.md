# Experiment artifacts

- `reference/`: 12 controlled retrieval configurations x 80 questions. Every
  prediction includes the ordered top 20, source offsets, response, claims,
  verification checks, correctness decisions, and measured query timing.
- `generator/`: a separate local FLAN-T5-small amount-only experiment on numeric
  and unanswerable questions. Includes raw model output before deterministic gating.
- `generator-v2/dev/` and `generator-v2/test/`: a development-first FLAN-T5-base
  experiment with aligned year/value records and retrieved table-evidence assembly.
  Preserves all 70 outputs, source contexts, metrics and implementation fingerprints.
  Test is a reused, previously inspected split; see `docs/experiments/GENERATION_V2.md`.
- `iter1/dev/` and `iter1/test/`: the separately measured table-assembly reader
  improvement. The current live CLI/API enables it; reference benchmark defaults do not.
- `controls/`: isolated numeric verifier study on correct source cells with
  deliberately corrupted claims. This is not end-to-end answer accuracy.
- `retrieval-v2/dev/` and `retrieval-v2/test/`: separately frozen metadata-aware
  retrieval study. Includes candidate lists, stage scores, query plans, failure
  attribution, development selection, and paired test comparisons. Uses the
  same reader in every setting; the test split is reused and exploratory.
- `explanations/dev/` and `explanations/test/`: a separate study on 40 newly frozen
  AI-authored questions. Supplied source passages isolate direct model explanation
  and learned answerability; no extractive or numeric guard decides refusals.
  Concept coverage is a screen, while human correctness and entailment remain null.
- `equivariance/{base,small}/{dev,test}/`: the flagship controlled-intervention pilot.
  It preserves 4,800 outcomes, model locks, per-case scores, and prompt hashes; see
  `../research/equivariance/README.md`.
- `document-interventions/`: 800 symbolic-reader outcomes, all top-five evidence,
  candidate rankings, 16 rebuilt index fingerprints and original-ranking diagnostics.
  This is an exploratory follow-up on the same questions, not a fresh holdout;
  see [its protocol and limits](../research/document-interventions/README.md).
- `document-llms/{base,small}/`: 3,200 matched outcomes from the original models
  and four decoding arms over both rebuilt retrieval views. Preserves raw output,
  prompt hashes, model locks and separate original/paired correctness;
  see [the matched comparison](../research/document-llms/README.md).

`reference/metrics.json` has development, test, and pooled aggregates. Use the test
split for headline comparisons. Pooled results are descriptive and must not be
presented as held-out performance. `run.json` records model revisions, environment,
input hashes, fixed parameters, selection rule, selected configuration, and paired
company-bootstrap comparisons against fixed/BM25.

To verify committed results without PDFs or model downloads:

```bash
uv run python scripts/audit_reference.py
uv run python scripts/audit_generation_results.py
uv run python scripts/audit_explanation_results.py
uv run python scripts/audit_retrieval_results.py
uv run python scripts/run_equivariance.py audit
```

To reproduce inference, use `results/reproduced` as the output directory. Preserve
the reference run for comparison; latencies vary with hardware and cache state.

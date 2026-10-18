# Experiment artifacts

- `reference/`: 12 controlled retrieval configurations x 80 questions. Every
  prediction includes the ordered top 20, source offsets, response, claims,
  verification checks, correctness decisions, and measured query timing.
- `generator/`: a separate local FLAN-T5-small amount-only experiment on numeric
  and unanswerable questions. Includes raw model output before deterministic gating.
- `controls/`: isolated numeric verifier study on correct source cells with
  deliberately corrupted claims. This is not end-to-end answer accuracy.

`reference/metrics.json` has development, test, and pooled aggregates. Use the test
split for headline comparisons. Pooled results are descriptive and must not be
presented as held-out performance. `run.json` records model revisions, environment,
input hashes, fixed parameters, selection rule, selected configuration, and paired
company-bootstrap comparisons against fixed/BM25.

To verify committed results without PDFs or model downloads:

```bash
uv run python scripts/audit_reference.py
```

To reproduce inference, use `results/reproduced` as the output directory. Preserve
the reference run for comparison; latencies vary with hardware and cache state.

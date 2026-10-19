# Independent annotation review

The dataset is AI-authored. No independent human adjudications have been collected.
The committed [`pending.csv`](../data/review/pending.csv) has 80 source-linked rows
with blank review fields; [`status.json`](../data/review/status.json) records zero
completed reviews. Adding tooling does not change that provenance.

Copy the pending sheet before editing. A reviewer should open the original PDF,
check the company, fiscal year, row, column, sign and unit, and record the amount
independently of the canonical parser. Public XBRL is an alternative when the
filing, fact scope, period, unit and historical/restated value have been reconciled.
Do not count agreement with the existing parsed tables as independent evidence.
Expected labels are visible in this review sheet; this is source verification,
not blind question authoring or an independent test dataset.

Fill in:

- `reviewer`: the actual reviewer's identity or stable review ID.
- `decision`: `accept`, `correct`, or `reject`.
- `evidence_method`: `visual_pdf` or `xbrl` for numeric questions;
  `visual_pdf` or `corpus_search` for narratives; `corpus_search` for negatives.
- `reviewed_value`, `reviewed_unit`, `reviewed_period`: independently checked
  numeric fields. Units are `USD_millions`, `USD_thousands`, or `USD_per_share`.
- `reviewed_answer`: the accepted narrative answer or corpus-scoped refusal.
- `rationale`: the source check, discrepancies and reasons for the decision.

Negative questions require searching the corpus for the requested scope rather
than treating a missing annotation as proof of absence. Numeric `accept` decisions
must agree with all frozen numeric fields. Use `correct` to propose different
values; rejection and correction both require an explanation. Record valid
narrative paraphrases explicitly, including the documented Qualcomm segment
scoring mismatch.

```bash
uv run python scripts/review_annotations.py export --output .cache/reviewer.csv
uv run python scripts/review_annotations.py validate --input .cache/reviewer.csv --output .cache/review.json
```

The validator rejects duplicates, omitted questions, changed source/reference
fields, incomplete decisions and parser-only numeric checks. Untouched rows remain
pending. Identities and review methods are self-reported; this tool cannot certify
that a human actually performed the review.

Validated output is a separate proposed-review artifact with question and sheet
hashes. It never changes `questions.jsonl`, expected answers, benchmark locks or
published metrics. Accepted corrections require a new dataset version and a new
experiment, with fresh test questions where possible. Do not retroactively repair
the reference scores to improve a headline.

The [new explanation challenge](EXPLANATION_STUDY.md) has a separate 40-row review
sheet. Add `--dataset explanations` to both commands to work with it. Answerability
is scoped to the supplied passage; use `passage_inspection` or `visual_pdf`.
All 40 new reviews are pending, separate from the 80 original pending reviews.
The concept checklist is only a screening rubric, not a human-approved answer key.

## Reviewing generated answers

Question-label review and response-quality review answer different questions.
The separate [answer review workflow](ANSWER_REVIEW.md) presents all 40 saved
explanation responses with their actual input excerpts. It collects correctness,
completeness, and claim-support judgments separately, and also assesses whether
the question was answerable from the supplied context. Automatic concept-screen
scores and proposed gold labels are omitted from that sheet.

All answer reviews remain pending. Exporting a sheet or passing its validator
does not establish independent human validation.

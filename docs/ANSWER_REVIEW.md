# Reviewing explanation responses

The explanation study's automatic concept screen cannot establish correctness,
completeness, or support for every generated claim. This workflow lets a reviewer
assess those dimensions independently against the **exact context supplied to
the model**. It covers the 8 development and 32 test outputs separately.

The committed `data/review/answers-pending.csv` has 40 blank reviews;
`data/review/answers-status.json` records zero completed reviews and null rates.
These are response reviews, separate from the original 80 question-label reviews
and the 40 explanation question-label reviews. No human assessment is supplied
by this implementation.

## Procedure

From the repository root, create a personal working copy:

```bash
uv run python scripts/review_answers.py export --output reviews/answers.csv
```

Only edit the six review columns. The other fields preserve the question, saved
response, refusal status, exact model context, source links, and SHA-256 hashes of
the question and prediction files. The automatic concept checklist and proposed
answerability labels are deliberately omitted. This reduces those cues but is
not a claim of a blinded or independent study.

| Field | Judgment |
| :-- | :-- |
| `reviewer` | An attributable reviewer identifier. |
| `evidence_answerable` | `yes`, `no`, or `uncertain`: can the supplied context answer the whole question? Do not use outside knowledge or information elsewhere in the PDF. |
| `answer_correct` | `yes`, `no`, or `uncertain`: does the response answer the question accurately, without factual errors or misleading implications? |
| `answer_complete` | `yes`, `no`, or `uncertain`: does the response address every requested part, including relevant qualifications? |
| `claims_supported` | `yes`, `no`, or `uncertain`: does the supplied context support every substantive claim? A relevant URL alone is insufficient. |
| `rationale` | Explain the judgment with the specific supporting or missing evidence and any errors. |

For a refused response, set the three answer-quality columns to `na`; still
assess answerability and explain the refusal judgment. `uncertain` is for a
completed assessment that cannot reach a conclusion. Leave **all six** fields
blank for an unreviewed response. Partly filled reviews fail validation.

A quoted fragment can have supported claims while failing completeness or
question relevance. A refusal can be correct for an unsupported question but
wrong for a supported one. These distinctions must survive aggregation.

Validate and save a separate report after reviewing:

```bash
uv run python scripts/review_answers.py validate --input reviews/answers.csv --output reviews/answers-reviewed.json
```

The commands refuse to overwrite existing output files. Validation rejects
changed source/output fields, duplicate or missing rows, changed prediction-file
bytes, and inconsistent judgments. It does not change any historical predictions,
question labels, study scores, or protocol fingerprints. For another compatible
run, pass `--results results/reproduced/explanations` before `export` or `validate`.

## Interpreting the report

Each split reports total, reviewed, and pending counts. Every rate includes
`passed`, `scored`, `eligible`, and `unscored` counts. No scored observations means
a null rate. Rates describe the scored subset; selective completion can bias
them, and even a perfect score on one review is not a whole-study result.

- Correctness, completeness, and claim-support rates are conditional on returning
  an answer. Their eligible counts include every non-refused response, including
  answers to unsupported questions. Refusals are excluded; pending and uncertain
  judgments stay unscored.
- `appropriate_response` covers all questions. For reviewer-supported questions,
  success requires a returned answer with all three quality judgments `yes`.
  Any `no` is a failure; otherwise uncertainty remains unscored. For
  reviewer-unsupported questions, only a model-native refusal is successful.
  A protocol error never counts as a successful refusal. Uncertain answerability
  leaves this metric unscored.

Reviewer identity and independence are self-reported. The tool checks consistency,
not whether a human performed the work. Agreement with supplied extracted text
does not independently reconcile that text against the original PDF or XBRL.
The existing source-label review workflow covers those separate checks. These
reviews do not make the previously inspected test set fresh validation.

# Explanations and model-native answerability

This study tests whether FLAN-T5-base can explain financial passages and decide
for itself when they lack the requested information. It bypasses the extractive
reader, finance intent rules and numeric guard. The results establish a small
capability demonstration, with substantial explanation failures still visible.

## Questions and protocol

Forty new AI-authored questions were written from ten original PDF passages:
export controls, idle capacity, inventory provisions, distributor credits,
acquisition integration, order forecasting, inventory write-downs, supplier
disruptions, royalties and manufacturing costs. Each passage has two supported
explanation questions and two questions asking for information it does not state.
Unsupported means absent from the supplied passage, not absent from the entire
corpus or unknowable in the real world.

The question strings do not duplicate any of the original 80. Their sources,
expected answerability and concept checklists were materialized and frozen before
inference. Development uses AMD and Intel: eight questions across two passages.
Test uses the other eight companies: 32 questions across eight passages. Questions
sharing a passage are dependent; this is not a sample of 40 independent cases.

One model and prompt pair was declared in
[`model-lock.json`](../../data/explanations/model-lock.json): the same pinned
FLAN-T5-base weights used in generation v2, greedy CPU decoding, 512 input tokens,
four answerability output tokens and 128 explanation output tokens. The protocol
records hashes of the dataset, prompt, study implementation and source-input lock.
Development completed first. Test ran once with the unchanged protocol. No other
explanation prompts were tried in this iteration.

These are newly frozen questions, but the filings have been used previously and
the questions were authored by the same AI assistant. They are **not independent
human validation**, new issuers or a newly collected document corpus. All 40
annotations remain pending independent review. The original 80-question benchmark
and the historical numeric generation results remain unchanged.

## Inference and scoring

The study supplies each question's source passage directly. This is an assisted
context experiment, not an end-to-end retrieval evaluation. First, the model
generates `yes` or `no` to whether the passage supports answering the entire
question. A generated `no` produces a model refusal. Invalid labels count as
protocol errors, never as successful model refusals. After `yes`, the model
generates the explanation directly; no source-cell answer is substituted.

Both prompts are budgeted before inference so the question remains in view. Only
the excerpts actually supplied to the model appear in its input references.
Those references have `role: input_context`; they are not claims of entailment.
Generated explanations carry `verification_status: unverified_generation`, no
verified numeric claims, and `citation_supported: null`.

The transparent automatic quality screen asks whether each preregistered concept
group has a matching expression in the answer. It can miss paraphrases and accept
negated, incoherent or unsupported prose containing the right words. It is a
coverage diagnostic, **not answer correctness or citation entailment**. Both human
quality scores remain null; zero human reviews have been recorded.

## Measured results

| Measure | Development | Test |
| :-- | --: | --: |
| Model refusals on context-unsupported questions | 4/4 | 15/16 |
| Model false refusals on supported questions | 0/4 | 1/16 |
| Model false acceptances on unsupported questions | 0/4 | 1/16 |
| Supported questions receiving an explanation | 4/4 | 15/16 |
| Supported questions passing all concept groups | 1/4 | 6/16 |
| Answered supported questions passing all concept groups | 1/4 | 6/15 |
| Invalid yes/no outputs | 0 | 0 |
| Independently human-reviewed answers | 0 | 0 |

The refusal results measure the model's generated answerability decision, with no
deterministic numeric or evidence gate deciding it. They do not establish robust
refusal on arbitrary financial questions or under adversarial prompting.

Concrete failures are retained in the raw outputs:

- Microchip's passage does not state the exact next-quarter percentage of turns
  orders. The model incorrectly says `yes` and answers only `a percentage`.
- Qualcomm's passage describes deductions, minimums, caps and fixed per-unit
  royalties. The model incorrectly declines a question about why one uniform
  percentage would oversimplify those terms.
- Asked how acquisition integration affects Broadcom's operations and management
  focus, the model produces only `disruption of our business`.
- Asked why NVIDIA's supply exposure extends beyond on-hand inventory, the model
  repeats the reasons supply grew, missing the requested explanation of purchase
  obligations and prepaid agreements.

Several outputs copy source fragments instead of explaining the requested
relationship. The new mode broadens the task beyond selecting an amount, but the
current model does not demonstrate reliable general financial explanation.

## Live usage and limits

```bash
uv run filing-lens ask "Explain how in-house manufacturing supports Texas Instruments' cost and supply-chain strategy." --reader flan-t5-explain
uv run filing-lens serve --reader flan-t5-explain
```

The live path uses retrieved chunks, and the model sees only excerpts that fit its
token budget. It uses no evaluation labels. Its behavior can differ from this
supplied-passage study because retrieval can omit or dilute the relevant evidence.
A live lexical smoke check produced a short source fragment for the manufacturing
question and a model-native refusal for a request for exact annual savings. That
check validates the API path, not broader answer quality.

The guarded numeric readers remain available separately. The explanation reader
does not provide their numeric verification guarantees and is not the default.

## Reproduction and independent review

The committed protocol is already frozen. After reproducing the canonical corpus:

```bash
uv run python scripts/audit_explanations.py --split dev --output results/reproduced/explanations
uv run python scripts/audit_explanations.py --split test --output results/reproduced/explanations
uv run python scripts/audit_explanation_results.py
```

The runner rejects changed frozen inputs/implementation, test-before-development
and overwriting an existing split. The offline audit recomputes native refusal,
concept coverage, source-excerpt metadata and aggregate scores without weights or
PDFs. It cannot independently validate source extraction or semantic correctness.

The separate [`review-pending.csv`](../../data/explanations/review-pending.csv) includes
all 40 source-linked questions with blank decisions. Copy it before editing.
Reviewers must judge answerability against the supplied excerpt and record the
actual explanation expected, including valid paraphrases and missing concepts.

```bash
uv run python scripts/review_annotations.py export --dataset explanations --output .cache/explanation-review.csv
uv run python scripts/review_annotations.py validate --dataset explanations --input .cache/explanation-review.csv --output .cache/explanation-review.json
```

Use `passage_inspection` or `visual_pdf` as the evidence method. Neither automatic
concept screening nor another AI assistant counts as independent human review.
Review corrections remain separate proposals and cannot silently rewrite the
frozen study's labels or results.

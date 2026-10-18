# What broke, and why

This analysis describes the frozen reference reader and failed FLAN-T5-small
pilot. Subsequent work is measured separately: [table-evidence assembly](ITERATION_1.md)
improves extractive coverage, and [generation v2](GENERATION_V2.md) produces 20/35
verified numeric test answers. Generation v2 remains row-assisted and exploratory;
the original failures and scores below have not been replaced.

The reference study ran all twelve configurations on the same 1,275-page corpus.
The default was selected on development companies: `fixed-bm25-rerank`. On seven
held-out companies it retrieved the gold passage in the first five results for
25/42 answerable questions (59.5%) and answered 18/42 correctly (42.9%). It answered
21/42 answerables and incorrectly answered three of the fourteen negative questions.

`structure-bm25-rerank` achieved the highest observed test recall (29/42, 69.0%)
and answer correctness (27/42, 64.3%). It was **not selected on development**.
The default remains unchanged. A tiny development split can select a different
winner from the test split; reporting that disagreement is more informative than
quietly promoting the test winner.

## 1. Financial PDFs defeat line-only table extraction

The initial line-table pass found zero tables in Analog Devices' report. Its
financial statements are nevertheless laid out as aligned text columns. A second
pass uses standalone statement headings, year columns, and word coordinates to
recover borderless statements. The final parser records 401 line-detected tables
and 31 normalized statement views, with the latter appended to the same canonical
corpus seen by both chunkers.

This fallback was implemented before freezing the benchmark. It still does not
resolve every wrapped label or unusual note. The verifier consumes the same parsed
representation, so an extraction error can survive every deterministic check.
Three [visual source spot checks](SOURCE_SPOT_CHECKS.md) are a limited inspection,
not a replacement for independent visual/XBRL reconciliation.

## 2. A retrieved number can lose its year header

Fixed windows can contain a full gold row without its header. For example,
`adi-numeric-05` retrieves the diluted EPS row but declines because the required
header is absent from the same evidence chunk. Broadcom's originally reported
diluted EPS has the same failure mode. The source cell exists; the retrieved
evidence is incomplete.

The structure chunker repeats source headers when tables split. Under BM25 plus
reranking, switching to it improves observed test correctness from 18/42 to 27/42.
This is a descriptive ablation: chunk counts differ (5,816 vs 6,515), budgets are
word-based, and normalized statement duplication/repeated headers are confounds.

## 3. General embeddings miss exact financial anchors

Without reranking, fixed/BM25 reaches 47.6% test recall@5 while fixed/dense reaches
16.7%. Structure/BM25 reaches 52.4% while structure/dense reaches 19.0%. Company
names, fiscal periods, and exact row labels are useful lexical anchors. A general
MiniLM representation does not consistently preserve those distinctions in long
financial tables. This explanation is an inference from the failure cases, not
a claim that the model's internal cause has been established.

The [representation diagnostics](../results/representation-diagnostics.json)
also show that 8.7% of fixed chunks and 5.0% of structure chunks exceed the dense
encoder's 256-wordpiece limit. Truncation can hide the relevant suffix. It cannot
explain every miss, and these figures do not isolate a causal effect.

## 4. Fusion can dilute a strong lexical candidate list

Fixed/hybrid recall@5 is 42.9%, below fixed/BM25's 47.6%. Structure/hybrid is 35.7%,
below structure/BM25's 52.4%. Rank fusion gives weak dense candidates a vote, even
when the dense score margin is uninformative. Reranking improves the fused lists
but cannot recover a source passage absent from the twenty candidates.

These results favor investigating stronger financial embeddings or development-only
fusion calibration. They do not justify retroactively changing the fixed RRF constant
or reranker pool based on the held-out test questions.

## 5. Citation support is an easy metric to misread

All main configurations have 100% measured citation support among returned answers.
The extractive reader copies source text, and numeric outputs pass cell checks by
construction. This says little about whether the answer addresses the question.

For `adi-unanswerable-02`, a paragraph about operating income and gross margin is
returned for a question about net interest margin. The quote exists in the source,
but the requested metric is unavailable. The fallback narrative reader's overlap
rule accepted a related passage. Broadcom's chip-defect question also receives an
irrelevant supported quote. These are real false answers and remain scored as errors.

The selected system refuses 11/14 unanswerables (78.6%) and 21/42 answerables (50.0%).
Reporting citation support alone would hide both false answers and the coverage cost.
The easy future-year negatives also make this refusal score optimistic for harder
unanswerability problems.

## 6. Strict narrative scoring can reject a valid answer

For `qcom-narrative-01`, the selected reader returns a sentence naming QCT and QTL,
with their expanded names inserted between them. It answers the question, but the
predeclared contiguous answer string `QCT and QTL` is absent, so the automated
scorer marks it incorrect. This is a visible false negative of the narrative metric.
The reference score is preserved; independent adjudication and a versioned scoring
protocol would be needed to claim expert semantic correctness. The seven-question
narrative test subset is too small for broad conclusions.

## 7. The small generative pilot failed completely

The separate pinned FLAN-T5-small audit returns the correct amount for **0/35 test
numeric questions**. The deterministic guard accepts no test answers, producing
0% numeric coverage and 100% refusal on the fourteen negatives. That refusal rate
is a degenerate result, not evidence of a useful generative QA system.

Raw outputs are retained in `results/generator/predictions.jsonl`. For AMD revenue,
the model emits `62` despite complete visible source rows. For NVIDIA revenue, it
emits `62974` instead of `26974`. It also emits words or units that violate the
amount-only output contract. The guard rejects those values rather than passing
them through or replacing them with gold answers.

This model/prompt combination is unsuitable for the task. Its failure motivates a
larger or constrained extractor evaluated under a new development-only protocol.
It does not reduce the validity of the separately measured retrieval experiments,
and its zero-coverage result is reported without presenting it as successful QA.

## 8. Reranking has a measurable latency cost

The selected model improves recall@5 by 11.9 percentage points versus fixed/BM25,
with a paired company-bootstrap 95% interval of +2.4 to +21.4 points. Its p95 query
latency rises from approximately 30 ms to 1,402 ms on this CPU run. MRR changes
by only +0.019, with an interval spanning zero. Reranking helps these top-five hits
but does not establish a clear first-relevant-result improvement in this small sample.

The run took approximately 15.8 minutes after model warmup, including index work.
Latency was measured sequentially on one workstation and should not be treated as
a production SLA. The strongest next steps are independent annotation review,
visual/XBRL cell checks, and development-only tuning of retrieval and reader behavior.

The [complete failure ledger](report/failure-ledger.md) retains all 27 failed test
cases for the selected configuration: 14 gold-passage misses, 10 reader/evidence-gate
failures, and 3 unsupported answers to negative questions.

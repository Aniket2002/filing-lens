# Iteration 1: retrieved table-part assembly

This document records the original opt-in study. The current `ask` and `serve`
commands enable this measured improvement by default; use
`--no-assemble-table-evidence` to reproduce the original live reader. The
`benchmark` default still uses the original reader across all reference ablations.

## Failure classification

I checked every incorrect development and test prediction for `fixed-bm25-rerank`
and `structure-bm25-rerank`. Each gold span for these 42 unique failed questions
matches its canonical page text. For all 34 unique failed numeric questions, the
canonical table has the expected row, fiscal-year value, and row-derived unit.
No failure is classified as a parsing/extraction error.

Each failed prediction receives one primary cause. A retrieval miss means no gold
span is fully contained in the top five. An evidence-gate-too-strict failure is
an incorrect refusal despite a top-five hit. An evidence-gate-too-loose failure
is an answer to an unanswerable question. For `qcom-narrative-01`, the response
names both requested segments but inserts their expanded names between “QCT” and
“QTL”; the frozen substring scorer therefore rejects it. This is classified as
an annotation problem (answer-string/scoring mismatch); neither the gold nor the
scorer was changed.

| Configuration | Split | Parsing/extraction error | Retrieval miss | Retrieval hit but reader error | Evidence gate too strict | Evidence gate too loose | Annotation problem |
|---|---|---|---|---|---|---|---|
| fixed-bm25-rerank | dev | 0 | 5: amd-numeric-04, intc-numeric-03, intc-numeric-04, nvda-numeric-02, nvda-numeric-04 | 0 | 3: amd-numeric-05, intc-numeric-05, nvda-numeric-05 | 1: nvda-unanswerable-02 | 0 |
| fixed-bm25-rerank | test | 0 | 14: adi-numeric-01, adi-numeric-02, adi-numeric-03, adi-numeric-04, avgo-numeric-03, mu-narrative-01, mu-numeric-02, mu-numeric-04, mu-numeric-05, nxpi-numeric-03, nxpi-numeric-04, qcom-numeric-03, qcom-numeric-04, txn-numeric-04 | 1: nxpi-narrative-01 | 8: adi-numeric-05, avgo-narrative-01, avgo-numeric-05, mchp-numeric-05, nxpi-numeric-05, qcom-numeric-02, qcom-numeric-05, txn-numeric-05 | 3: adi-unanswerable-02, avgo-unanswerable-02, mu-unanswerable-02 | 1: qcom-narrative-01 |
| structure-bm25-rerank | dev | 0 | 6: amd-numeric-04, intc-numeric-03, intc-numeric-04, nvda-numeric-01, nvda-numeric-02, nvda-numeric-04 | 0 | 0 | 1: nvda-unanswerable-02 | 0 |
| structure-bm25-rerank | test | 0 | 13: adi-numeric-01, adi-numeric-03, avgo-numeric-01, avgo-numeric-03, mu-numeric-03, mu-numeric-04, nxpi-numeric-01, nxpi-numeric-02, nxpi-numeric-03, nxpi-numeric-04, qcom-numeric-01, qcom-numeric-03, txn-numeric-04 | 0 | 1: avgo-narrative-01 | 3: adi-unanswerable-02, avgo-unanswerable-02, mu-unanswerable-02 | 1: qcom-narrative-01 |

### Failure strata

The counts below cover all failures in the relevant split; numeric metric names
are the frozen question metric labels. The question IDs are in the table above.

| Configuration/split | Kind: numeric / narrative / unanswerable | Numeric metric failures | Companies with failures |
|---|---:|---|---|
| fixed-bm25-rerank / dev | 8 / 0 / 1 | diluted_eps 3; net_income 1; research_development 1; total_assets 3 | AMD 2; INTC 3; NVDA 4 |
| fixed-bm25-rerank / test | 20 / 4 / 3 | diluted_eps 7; net_income 3; research_development 4; revenue 1; total_assets 5 | ADI 6; AVGO 4; MCHP 1; MU 5; NXPI 4; QCOM 5; TXN 2 |
| structure-bm25-rerank / dev | 6 / 0 / 1 | net_income 1; research_development 1; revenue 1; total_assets 3 | AMD 1; INTC 2; NVDA 4 |
| structure-bm25-rerank / test | 13 / 2 / 3 | net_income 1; research_development 5; revenue 4; total_assets 3 | ADI 3; AVGO 4; MU 3; NXPI 4; QCOM 3; TXN 1 |

These strata are descriptive. Development has 18 answerable questions across
three companies; the test narratives and individual company/metric cells are
smaller still. They are too small to support company-specific or metric-specific
generalizations.

## Dense retrieval compared with BM25

On the 42 answerable test questions, fixed/BM25 recalls 20 gold passages in the
top five (47.6%); fixed/dense recalls 7 (16.7%). There are 14 test questions where
BM25 hits the gold span in its top five and dense retrieval does not; dense hits
one question that BM25 misses, and both hit six.

The saved rankings show concrete failures:

- `mchp-numeric-01` asks for Microchip FY2023 net sales. BM25 ranks its gold span
  first; dense does not retrieve it in its 20 candidates. Dense's top five are
  Microchip pages 42, 44, 43, 121, and 43, but none contains the gold span.
- `mchp-narrative-01` asks what the report calls a “self-contained
  computer-on-a-chip.” BM25 ranks the gold span first; dense does not retrieve it
  in its 20 candidates and instead ranks AMD pages 152, 4, 148, 168, and 6 first.
- `avgo-narrative-01` asks when Broadcom completed VMware's acquisition. BM25
  ranks the answer at 1; dense ranks it at 12, outside the reader's top five.
- `txn-numeric-03` asks for FY2022 R&D expense. BM25 ranks the gold row first;
  dense does not retrieve the gold span in its top 20.

These examples are consistent with exact issuer, period, metric, and table-row
terms helping lexical retrieval, while general-purpose MiniLM similarity can
favor semantically related but wrong pages (or, for `mchp-narrative-01`, the
wrong issuer). The diagnostics report that 8.7% of fixed chunks exceed the
embedding model's 256-wordpiece limit. Truncation is a possible contributor,
not an established cause; the runs do not isolate causality.

## Candidate fixes ranked

Ranking uses development evidence only and qualitatively applies
`(expected gain × confidence) / effort`. Counts are the development failures
that a candidate could affect, not promises of improvement. No candidate was
selected using test metrics.

| Rank | Candidate | Target bucket; development cases | Expected gain and confidence / effort | Test leakage or overfit risk |
|---:|---|---|---|---|
| 1 | Assemble a numeric table header and matching row when both are in retrieved top-five chunks on the same page. | Strict evidence gate; 2 direct cases: amd-numeric-05 and intc-numeric-05. | Both dev cases have the complete header and row in separate top-five chunks; high confidence, low effort. | Low: general, bounded to already retrieved evidence; no question IDs or gold labels in code. |
| 2 | Use the existing structure chunker as an opt-in alternative to fixed windows. | Strict gate; up to 3 dev refusals. | In the frozen dev ablation, structure chunking removes those three numeric refusals and yields 2 more correct answers overall, but loses one dev R@5 hit; moderate confidence, medium effort. | Moderate: chunk boundaries affect all questions; keep opt-in and choose only on development. |
| 3 | Improve BM25 matching for financial labels and periods. | Retrieval miss; up to 5 dev cases: amd-numeric-04, intc-numeric-03, intc-numeric-04, nvda-numeric-02, nvda-numeric-04. | The exact passages are absent from top five; a retrieval change might affect them, but the current data does not establish which technique will recover them. Low confidence, high effort. | High if tuned to question wording; use development only and avoid per-question rules. |
| 4 | Tighten narrative abstention for unsupported, metric-like negative questions. | Loose gate; 1 dev case: nvda-unanswerable-02. | At most one direct dev false answer is evidenced; low confidence, low-to-medium effort. | High: a rule tuned to one negative could increase false refusals on answerable questions. |

## Implemented fix and measured results

Implemented rank 1 initially as opt-in `--assemble-table-evidence`. The benchmark
reader remains unchanged by default. The option can combine only an exact parsed table
header and exact matching row that both appear in the retrieved top five, for
the same issuer and PDF page. It returns citations to both chunks and retains
the existing entity/year/unit/value verification. It cannot consult un-retrieved
chunks, cross pages, or bypass the verifier.

The profile was frozen as `fixed-bm25-rerank+table-evidence`. Development ran
first; the test profile was run once afterward. Full predictions and metadata
are in [`results/iter1/dev/`](../results/iter1/dev/) and
[`results/iter1/test/`](../results/iter1/test/). The run metadata includes source
hashes and the unchanged benchmark input lock.

| Split / profile | R@1 | R@5 | R@10 | MRR@20 | Answer correct | Citation support | Unanswerable refusal | p95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Dev, baseline `fixed-bm25-rerank` | 33.3% | 72.2% | 72.2% | 0.457 | 55.6% (10/18) | 100.0% | 83.3% | 1355.8 |
| Dev, opt-in | 33.3% | 72.2% | 72.2% | 0.457 | 66.7% (12/18) | 100.0% | 83.3% | 1036.9 |
| Test, baseline `fixed-bm25-rerank` | 28.6% | 59.5% | 61.9% | 0.400 | 42.9% (18/42) | 100.0% | 78.6% | 1401.7 |
| Test, opt-in | 28.6% | 59.5% | 61.9% | 0.400 | 57.1% (24/42) | 100.0% | 78.6% | 1114.6 |

The option changes no retrieval ranking: R@1/5/10 and MRR are identical
question-by-question. On dev it corrects `amd-numeric-05` and `intc-numeric-05`.
On the single frozen test run it corrects `adi-numeric-05`, `avgo-numeric-05`,
`mchp-numeric-05`, `nxpi-numeric-05`, `qcom-numeric-02`, and `qcom-numeric-05`;
there are no regressions in answer correctness. Test answerable coverage moves
from 21/42 to 27/42; the 14-question unanswerable refusal rate is unchanged.

A paired company-cluster bootstrap (2,000 resamples, seed 17, seven companies)
on answerable-question correctness gives **+14.3 percentage points**
(24/42 versus 18/42; 95% interval **+7.1 to +21.4 points**). The interval is
descriptive for this small benchmark, not a claim of general superiority. The
run metadata also records the pre-existing all-question `correct` comparison,
whose denominator includes 14 unanswerables; it is not the answer-correctness
metric in this table. Timing is from one sequential CPU run and is not an SLA or
evidence that this option reduces latency.

## Limitations

The test set has **42 answerable and 14 unanswerable questions across seven
companies**. Small metric differences are noise at this scale, and the bootstrap
does not make this a broad or independent validation. Questions were AI-authored
after source inspection and have not been independently human-adjudicated.
Numeric extraction and evaluation share the canonical parser; the check above
does not replace visual or XBRL reconciliation. Citation support is conditional
on returning an answer and does not establish relevance. No gold labels,
questions, or lock files were changed, and `results/reference/` was not
overwritten.

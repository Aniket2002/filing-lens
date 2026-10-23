# Original and supporting experiment results

Detailed historical results are kept here so the repository's front page can focus
on the flagship research study. This block is refreshed from frozen predictions by
\`scripts/update_readme_results.py\`.

<!-- RESULTS_START -->
Development selected **`fixed-bm25-rerank`**. Its test recall@5 is **59.5%**, versus 47.6% for fixed/BM25: **+11.9 percentage points** (paired company-bootstrap 95% interval: +2.4 to +21.4 points; seven test companies). Treat this small-sample interval as descriptive, not as evidence of statistical significance or general superiority. Answer correctness is 42.9%, answerable-question coverage is 50.0%, and unanswerable refusal is 78.6%.

The highest observed test recall belongs to `structure-bm25-rerank` (69.0% recall@5; 64.3% answer correctness). It was not selected by the development set, so it remains a descriptive test result.

| Configuration | R@1 | R@5 | R@10 | MRR@20 | Answer correct | Citation support | Refusal (unanswerable) | p95 ms |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| fixed-bm25 | 31.0% | 47.6% | 52.4% | 0.381 | 33.3% | 100.0% | 71.4% | 30 |
| fixed-bm25-rerank | 28.6% | 59.5% | 61.9% | 0.400 | 42.9% | 100.0% | 78.6% | 1402 |
| fixed-dense | 9.5% | 16.7% | 28.6% | 0.144 | 4.8% | 100.0% | 92.9% | 45 |
| fixed-dense-rerank | 21.4% | 35.7% | 40.5% | 0.279 | 23.8% | 100.0% | 92.9% | 1291 |
| fixed-hybrid | 14.3% | 42.9% | 54.8% | 0.269 | 33.3% | 100.0% | 78.6% | 46 |
| fixed-hybrid-rerank | 23.8% | 52.4% | 59.5% | 0.353 | 38.1% | 100.0% | 78.6% | 1315 |
| structure-bm25 | 23.8% | 52.4% | 52.4% | 0.352 | 50.0% | 100.0% | 71.4% | 33 |
| structure-bm25-rerank | 40.5% | 69.0% | 69.0% | 0.520 | 64.3% | 100.0% | 78.6% | 1323 |
| structure-dense | 7.1% | 19.0% | 23.8% | 0.131 | 19.0% | 100.0% | 92.9% | 58 |
| structure-dense-rerank | 16.7% | 31.0% | 31.0% | 0.228 | 33.3% | 100.0% | 85.7% | 1322 |
| structure-hybrid | 14.3% | 35.7% | 57.1% | 0.260 | 35.7% | 100.0% | 78.6% | 59 |
| structure-hybrid-rerank | 31.0% | 59.5% | 59.5% | 0.421 | 57.1% | 100.0% | 78.6% | 1178 |

Citation support is conditional on returning an answer. The selected system returns source-supported but irrelevant answers to three negative questions; 100% citation support therefore does not mean 100% correctness.

**Failed generation pilot, retained:** FLAN-T5-small achieves 0.0% raw amount correctness on the 35 numeric test questions. The guard declines every test answer (0.0% numeric coverage). Its 100% negative refusal rate is degenerate and does not demonstrate useful generative QA. See the failure analysis and preserved raw outputs.

**Current CLI/API reader:** same-page table-evidence assembly is now enabled by default for `ask` and `serve`. The separately measured extractive profile achieves **57.1% correctness (24/42)** and **64.3% coverage (27/42)**, with unchanged retrieval and unanswerable refusal. Use `--no-assemble-table-evidence` for the original reader; benchmark defaults and frozen reference artifacts retain the original behavior. See [Iteration 1](ITERATION_1.md).

**Generation v2, exploratory:** pinned FLAN-T5-base with aligned year/value records achieves **60.0% raw amount correctness (21/35)** and **57.1% verified numeric correctness and coverage (20/35)**. It uses the same retrieval rankings plus table-evidence assembly. The guard withholds one correct raw amount without sufficient retrieved evidence. The model's exact `UNKNOWN` rate on 14 negatives is **0/14**; guarded refusals come from the controls. This is row-assisted amount generation on a previously inspected test set, with model, prompt, context format, and evidence assembly changed together. It is not an independent validation, a controlled model-size comparison, or general financial QA. See the [generation study](GENERATION_V2.md) and [preserved outputs](../../results/generator-v2/test/predictions.jsonl).

**New explanation challenge, supplied evidence:** 40 new AI-authored questions (8 development, 32 test) were frozen before inference using the same source filings. The experimental `flan-t5-explain` reader generates prose and its own yes/no answerability decision without the extractive reader or numeric guard. On test it declines **93.8% of unsupported questions (15/16)** and falsely declines **1/16 supported questions**. Explanation quality remains weak: only **6/16** supported questions pass the full automatic concept screen, which is not a correctness or entailment score. Human quality scores remain unassigned. This isolates model behavior on supplied passages; it does not evaluate retrieval or establish independent human validation. See the [explanation study](EXPLANATION_STUDY.md).
<!-- RESULTS_END -->

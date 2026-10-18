# Measured test ablations

42 answerable + 14 unanswerable questions; seven held-out companies.

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

Citation support is conditional on answering. Inspect coverage in metrics.json.

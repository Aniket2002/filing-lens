# Measured retrieval iteration

Development-selected: **structure-entity-60**.

Every setting uses the same cross-encoder and extractive reader with table assembly.
Test is a reused, previously inspected split; this is exploratory evidence.

## Development (18 answerable, 6 negative)

| Setting | Candidate recall | R@5 | MRR@20 | Correct | Negative refusal | p95 ms |
| :-- | --: | --: | --: | --: | --: | --: |
| fixed-baseline-20 | 72.2% | 72.2% | 0.457 | 66.7% | 83.3% | 1251 |
| structure-baseline-20 | 66.7% | 66.7% | 0.463 | 66.7% | 83.3% | 1200 |
| structure-entity-20 | 83.3% | 83.3% | 0.551 | 83.3% | 83.3% | 1156 |
| structure-entity-60 | 100.0% | 100.0% | 0.648 | 100.0% | 83.3% | 3222 |
| structure-finance-60 | 100.0% | 100.0% | 0.608 | 100.0% | 83.3% | 3401 |
| structure-hybrid-finance-60 | 100.0% | 100.0% | 0.608 | 100.0% | 83.3% | 3091 |

## Test (42 answerable, 14 negative)

| Setting | Candidate recall | R@5 | MRR@20 | Correct | Negative refusal | p95 ms |
| :-- | --: | --: | --: | --: | --: | --: |
| fixed-baseline-20 | 61.9% | 59.5% | 0.400 | 57.1% | 78.6% | 1357 |
| structure-baseline-20 | 69.0% | 69.0% | 0.520 | 64.3% | 78.6% | 1313 |
| structure-entity-60 | 95.2% | 88.1% | 0.607 | 85.7% | 85.7% | 3249 |

## Paired company-bootstrap comparisons

95% intervals use 2,000 resamples over seven companies. They are descriptive.

- Selected minus `fixed-baseline-20` recall@5: **+28.6 percentage points**, 95% interval [+9.5, +42.9].
- Selected minus `structure-baseline-20` recall@5: **+19.0 percentage points**, 95% interval [+11.9, +26.2].

## Where retrieval still fails

| Setting | Hit at 5 | Missing from candidates | Available but ranked below 5 |
| :-- | --: | --: | --: |
| fixed-baseline-20 | 25 | 16 | 1 |
| structure-baseline-20 | 29 | 13 | 0 |
| structure-entity-60 | 37 | 2 | 3 |

Latency is a single warm CPU run, not an SLA or a repeated timing experiment.
See [case-level evidence](failure-ledger.md) for recovered and unresolved questions.

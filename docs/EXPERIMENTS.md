# Experiment index

The README features the financial evidence equivariance study and links to the
retrieval baseline. This index preserves the supporting and historical work
without giving every experiment equal prominence.

## Retrieval

- [12-configuration baseline results](report/ablations.md), [plots](report/ablations.png),
  and [standalone case review](report/index.html).
- [Detailed historical metric ledger](experiments/REFERENCE_RESULTS.md), generated from
  the frozen experiment records.
- [Failure analysis](FAILURE_ANALYSIS.md), [dataset card](DATA_CARD.md),
  [experiment protocol](EXPERIMENT_PROTOCOL.md), and [annotation status](ANNOTATION_REVIEW.md).
- [Entity-aware retrieval v2](retrieval-v2/results.md), its
  [protocol and limitations](RETRIEVAL_V2.md), and
  [per-question failures](retrieval-v2/failure-ledger.md).
- [Source-cited service](SERVICE.md) and [answer review](ANSWER_REVIEW.md).

## Earlier model and reader studies

- [Iteration 1: table evidence assembly](experiments/ITERATION_1.md).
- [Generation v2: row-assisted numeric generation](experiments/GENERATION_V2.md).
- [Explanation study: supplied-passage answers](experiments/EXPLANATION_STUDY.md).
- Frozen outputs and denominators are documented in [results/README.md](../results/README.md).

## Research papers

- **Flagship:** [Financial Evidence Equivariance](../research/equivariance/README.md).
- **Supporting baseline:** [Filing Lens retrieval report](../research/retrieval-baseline/README.md).

Both papers are exploratory studies over related filings. The latter provides
technical baseline context for the newer pilot. Neither has been independently
validated by human source adjudication or presented as a peer-reviewed
publication.

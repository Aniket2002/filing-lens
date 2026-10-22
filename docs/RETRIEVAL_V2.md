# Retrieval iteration: metadata, candidate recall, and ranking diagnostics

This iteration adds a query planner, entity-aware candidate retrieval, explicit
financial term expansion, independently configurable candidate depth, and per-result
ranking traces. It is an exploratory follow-up on the existing, previously inspected
benchmark. It does not replace the frozen 12-configuration reference experiment.

## Measured outcome

Development selected **structure-entity-60**. On the reused test split:

| Measure | Fixed/BM25/reranker control | Selected retrieval |
| :-- | --: | --: |
| Recall@5, 42 answerable questions | 59.5% (25/42) | **88.1% (37/42)** |
| Answer correctness, same reader | 57.1% (24/42) | **85.7% (36/42)** |
| Unanswerable refusal, 14 negatives | 78.6% (11/14) | **85.7% (12/14)** |
| Candidate recall | 61.9% (26/42) | **95.2% (40/42)** |
| CPU p95 latency | 1.36 s | 3.25 s |

The recall gain is **+28.6 percentage points** (paired company-bootstrap 95%
interval: +9.5 to +42.9 points). Against the structure-chunked control, which holds
chunking fixed as well as the reader, the gain is **+19.0 points** (+11.9 to +26.2).
The baseline's 16 candidate misses fall to two, while three ranking misses remain.
All 312 development/test predictions pass the offline result audit.

![Measured test comparison](retrieval-v2/comparison.png)

The [complete tables](retrieval-v2/results.md) include all six development ablations,
both controls, latency, and failure counts. Term expansion and hybrid search tied
the selected profile on development recall, but had lower MRR; their test results
were not used to choose a winner.

A concrete recovered case is Analog Devices' comparative-year R&D expense:
the gold passage starts at **candidate rank 55** and is promoted to **final rank 2**.
A 20-candidate reranker cannot inspect it. The [case ledger](retrieval-v2/failure-ledger.md)
also preserves failures, including NXP evidence still below the first five results
and narrative-reader mistakes despite successful retrieval. Gold spans are not
exhaustive relevance judgments: Micron's net-income answer is correct using other
retrieved evidence even though its annotated gold span is ranked below five.

## Reproduce and inspect

```bash
# Source downloads/parsing are the same as the main README.
uv run filing-lens retrieval-study --split dev --output results/reproduced/retrieval-v2
uv run filing-lens retrieval-study --split test --output results/reproduced/retrieval-v2

# Inspect routing, source spans, stage scores, and reranker promotions in JSON.
uv run filing-lens ask "What was Micron Technology's FY2023 revenue in USD millions?" --config structure-bm25-rerank --retrieval-profile entity --candidate-pool 60 --json

# Optional lexical vocabulary expansion and a wider reranker candidate pool.
uv run filing-lens ask "What was AMD's FY2023 R&D expense?" --config structure-hybrid-rerank --retrieval-profile finance --candidate-pool 60 --json

# Check the published iteration without models, downloads, or source PDFs.
uv run python scripts/audit_retrieval_results.py
uv run python scripts/report_retrieval.py
```

Both `ask` and `serve` accept `--retrieval-profile baseline|entity|finance` and
`--candidate-pool 20..200`. Defaults retain the reference retrieval behavior.
The reader still consumes five results; the engine returns a diagnostic trace
for up to twenty. Increasing the candidate pool changes what the reranker can
rescue, without silently increasing the reader's evidence budget.

## What changes

| Component | Behavior | Why it matters |
| :-- | :-- | :-- |
| Metadata routing | Match full company names, tickers, optional corpus aliases, and names shortened by removing Technology/Semiconductors | Entity constraints apply before BM25, vector search, fusion, and reranking, so another issuer cannot consume the scoped candidate budget. |
| Conservative fallback | No recognized company searches all documents; multiple matches search their union | The retriever does not silently choose one company in a comparison. The current reader still refuses ambiguous entities. |
| Comparative periods | Keep every filing for the matched entity; do not filter by requested fiscal year | FY2023 filings can contain FY2022 and FY2021 evidence. |
| Financial vocabulary | `finance` appends explicit lexical synonyms for revenue, income, EPS, R&D, and assets | Handles terminology mismatches such as revenue versus net sales; the original question still reaches both neural models. |
| Candidate depth | Separate candidate budget from returned top 20 and reader top 5 | Reranking cannot recover a passage absent from its candidate set. Larger budgets cost additional CPU inference. |
| Explainable retrieval | Source offsets, BM25/dense ranks and scores, RRF score, pre-rerank position, cross-encoder score | Distinguishes candidate misses from reranker demotions. These scores are ranking signals, not calibrated confidence probabilities. |
| Efficient scoped search | BM25 batch-scores eligible chunk IDs; dense search scores eligible embedding rows | Avoids scoring excluded documents while keeping original corpus-wide BM25 statistics. |

Aliases come from corpus metadata and deterministic name normalization. The query
planner never reads benchmark questions, gold spans, or expected answers. Short
tickers require uppercase spelling to reduce accidental matches in prose. Alias
collisions retain the union; there is no fuzzy entity matching or learned linker.

BM25 scoring, dense cosine scoring, and RRF remain separate signals. For background,
see the primary [RRF documentation](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking)
and Microsoft's [retrieval and reranking architecture guidance](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-information-retrieval).
The measurements here come from this repository, not those sources.

## Experiment controls

Development evaluates six predeclared settings:

1. Fixed chunks, baseline BM25, 20 candidates (current retrieval control).
2. Structure chunks, baseline BM25, 20 candidates (chunking control).
3. Structure chunks, entity-scoped BM25, 20 candidates (routing ablation).
4. Structure chunks, entity-scoped BM25, 60 candidates (depth ablation).
5. Structure chunks, entity-scoped expanded BM25, 60 candidates (vocabulary ablation).
6. Structure chunks, entity-scoped expanded BM25 + dense RRF, 60 candidates (hybrid ablation).

Every setting uses the same pinned cross-encoder and the same extractive reader
with same-page table assembly. Select by development recall@5, then MRR@20,
then smaller candidate budget, then configuration name. Test evaluates only the
selected setting and the two controls. Test metrics do not enter selection.

The runner hashes inputs, implementation files, model locks, and the dependency
lockfile before development. It refuses changed code/data or altered development
artifacts before test, and refuses to overwrite any split directory. An interrupted
run lacks a completion manifest and cannot authorize test. Every candidate list,
final ranking, response, timing, and failure attribution is preserved.

Candidate recall measures gold-span containment before reranking. A candidate miss
means the full gold evidence never entered the candidate pool. A ranking miss means
it was available but did not reach the reader's first five chunks. Negatives have
null retrieval metrics; refusals are scored separately.

## Limitations

The 80 questions remain AI-authored and await independent human review. The reused
test split contains only 42 answerable questions and 14 negatives from seven
companies. Bootstrap intervals resample companies, not individual questions, and
are descriptive. The implementation freeze prevents changes between this run's
development and test; it cannot undo previous exposure to the test corpus.

The financial vocabulary is deliberately small and is aligned with the existing
benchmark's five numeric metric families. It is not evidence of broad financial
language understanding. More candidates can improve recall while increasing latency
or introducing distractors. Neither routing nor reranker scores verify an answer;
the existing source-cell controls and refusal rules still perform that job.

A live smoke check also exposed wording sensitivity: the short questions
“What was Micron's FY2023 revenue?” and “What was AMD's FY2023 net income?” trigger
`no_complete_table_evidence_in_top_k` with the selected profile. The published
scores apply to the frozen question wording; paraphrase robustness has not been
established. The refusal is preserved as a limitation, and the measured profile
was not retuned after test. A separately frozen paraphrase challenge is a useful
next evaluation before treating the system as a general financial assistant.
Full-company, unit-explicit versions returned source-verified answers in the live
check; the Micron example above returned 15,540 USD million. This is a smoke check,
not a systematic paraphrase evaluation.

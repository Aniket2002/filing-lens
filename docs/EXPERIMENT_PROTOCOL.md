# Experiment protocol

## Controlled factors

The full factorial design is **2 chunkers × 3 retrievers × 2 reranker settings**.
All configurations search the same full corpus with the same metadata prefix,
candidate pool (20), answer context (5), and reader. No oracle company filter is
applied before retrieval.

- **Fixed:** 160 whitespace-delimited words, 32-word overlap; page boundaries retained.
- **Structure:** paragraph packing up to 160 words; table row boundaries retained;
  two source header lines repeated when long tables split. A long individual row
  can exceed the budget. Repeated headers and metadata are outside the body budget.
  Different chunk counts and effective token budgets are a real confound, disclosed
  in the run data. This is not a token-matched experiment.
- **BM25:** `rank-bm25`, Okapi defaults (`k1=1.5`, `b=0.75`), common tokenizer.
- **Dense:** normalized MiniLM embeddings, exact cosine search. No ANN approximation.
- **Hybrid:** reciprocal rank fusion of the top 20 from BM25 and dense,
  `score(d) = sum(1/(60 + rank(d)))`, retaining 20 candidates.
- **Reranker:** the same learned MiniLM MS MARCO cross-encoder reorders those 20
  candidates; it cannot recover a passage outside the candidate set.

The embedding model truncates at its native sequence length (256 wordpieces).
The cross-encoder input cap is 384 tokens. Word budgets are not wordpiece budgets:
financial tables, long labels, or repeated headers can still be truncated. No
financial fine-tuning, test-time query rewriting, or hosted inference is used.
Exact model revisions are pinned in `data/model-lock.json`.

## Parsing

PyMuPDF extracts page text and line-detected tables. A conservative second pass
finds primary statements by their standalone heading, year headings, and aligned
numeric columns. It appends a normalized statement view to the original page
representation. Both chunkers get exactly the same representation, including this
duplication. This makes chunking effects comparable, but results are specific to
this enriched representation and are not a raw-PDF benchmark.

Numbers are not inferred or rounded during parsing. A dash is treated as unavailable,
not automatically as zero. Wrapped labels, unusual footnotes, and split tables can
still be misparsed. The included coordinate-parser tests cover borderless tables,
negative values, and rejection of narrative references to statements.

## Fixed reader and numeric controls

The main reader is **extractive, not a generative LLM**. A small finance intent
ontology recognizes five metrics, company aliases, and fiscal years. The same
rules apply to all configurations. Unsupported scopes are declined. The qualitative
reader chooses a sentence by query-token overlap with a fixed 0.4 threshold.

The numeric reader requires both a complete serialized header and complete row in
one of the first five retrieved chunks. Access to the global parsed-table registry
cannot supply missing retrieved evidence. The verifier then checks the table ID,
entity, PDF page, metric row, year column, amount, and unit using Decimal arithmetic.
A second check extracts the amount displayed in the answer and compares it to the
structured claim. The candidate answer is withheld if either check fails.

The verifier's isolated mutation study gives it the correct source cell and
deliberately corrupts claims. It measures control behavior **conditional on a
correct source cell**, not the ability to retrieve or visually parse that cell.

## Metrics and denominators

| Metric | Definition | Denominator |
| :-- | :-- | :-- |
| Recall@k | Fraction of gold spans fully contained in the first k chunks | Answerable questions only |
| MRR@20 | Reciprocal rank of the first fully matching gold span; zero if absent | Answerable questions only |
| Answer correctness | Exact Decimal + unit + period + entity + metric for numeric; acceptable substring for narrative | All answerable questions, including refusals as incorrect |
| Citation support | Cited quote appears in the page; numeric claims also pass cell and surface checks | Non-refused responses only |
| Gold citation accuracy | Returned citation span contains a gold anchor | Answerable questions, refusals counted as misses |
| Answer coverage | Non-refused answers | Answerable questions only |
| False refusal rate | Refused answerable questions | Answerable questions only |
| Unanswerable refusal | Declined negative questions | Unanswerable questions only |
| Answered precision | Correct responses, including correct treatment of negatives | Non-refused responses only |

With one passage per answerable question, recall@k is also a hit rate. A citation
can faithfully support the returned statement yet answer the wrong question.
High citation support is not a substitute for correctness or coverage.

## Selection, uncertainty, and latency

Select the default configuration on **development recall@5**, then **development
MRR@20**, then configuration name for a deterministic tie break. Test metrics do
not enter selection. The test comparison against fixed/BM25 includes a paired
company-cluster bootstrap (2,000 resamples, seed 17). Retrieval comparisons exclude
unanswerables through null metrics. The `correct` comparison in run metadata uses
all 56 questions, counting correct refusals as correct; it has a different denominator
from the main answer-correctness column (42 answerables). Seven held-out companies make
these intervals coarse; they are descriptive, not proof of general superiority.

Latency uses warm models, cached document embeddings, exact search, CPU inference,
four PyTorch threads, and includes per-query encoding, reranking, and the reader.
Model download/load, source parsing, and index construction are excluded. The run
is sequential on a single workstation, without repeated randomized timing trials.
The recorded percentiles characterize this run; they are not a production SLA.

## Separate local generation experiment

`scripts/audit_generator.py` reuses the development-selected retrieval run on the
50 numeric and 20 unanswerable questions. It uses pinned FLAN-T5-small, greedy
decoding, a 512-token prompt limit, and at most 24 output tokens. When the extractive
reader finds complete retrieved evidence, it compacts that evidence into a row plus
header; otherwise it supplies the first two retrieved snippets. This is a
**row-assisted generative experiment**, not a replacement for the 12 controlled
retrieval ablations or an unconstrained conversational assistant.

The model must emit one signed numeric amount. The guard requires a complete cited
source cell and checks the generated amount against it. Non-numeric output,
insufficient evidence, and wrong amounts cause refusal. The raw model output is
preserved, so rejected hallucinations remain inspectable. The adapter standardizes
the final sentence; it does not claim to verify arbitrary generated prose.

# Filing Lens: resume and interview material

## Project title and stack

**Filing Lens — Financial Document Retrieval and RAG Evaluation**

Python, PyTorch, Sentence Transformers, BM25, dense vector search, reciprocal rank
fusion (RRF), cross-encoder reranking, PDF/table extraction, REST API, pytest,
GitHub Actions, reproducible evaluation.

The separate research pilot adds dimensional analysis, metamorphic testing,
counterfactual fiscal-year interventions, structured LLM decoding, and paired
company-cluster bootstrap evaluation. See
[Financial Evidence Equivariance](../research/equivariance/README.md).

Use the keywords that match the role and that you can explain. The project runs
locally on CPU; it does not have a production deployment, a vector database,
fine-tuned models, or independently human-validated labels.

## Resume bullets

- Built an auditable financial-document RAG pipeline over **1,275 pages from 10
  issuers**, combining BM25, MiniLM embeddings, reciprocal rank fusion, and
  cross-encoder reranking with source-linked answers.
- Improved **recall@5 from 59.5% to 88.1%** and **answer correctness from 57.1%
  to 85.7%** on a reused 42-question answerable test split through entity-aware
  retrieval, structure-aware chunking, and expanded reranker candidates; held the
  reader fixed and selected the configuration on development data.
- Engineered source-cell numeric verification and evidence-based abstention,
  validated with **500 control cases**; exposed a local REST API with bounded
  inference admission, request metrics, and offline Windows/Linux CI checks.
- Designed a **600-case financial evidence intervention study** with four decoding
  ablations and two pinned instruction-tuned models; audited **4,800 outcomes**
  from **2,252 inference calls**, identifying a robustness/accuracy tradeoff and
  failures to abstain after fiscal-period evidence removal.

The first bullet describes supported retrieval options, not a claim that hybrid
search is the best measured configuration. The 500 cases test the verifier given
correct source cells, not end-to-end answer accuracy.

The retrieval comparison is exploratory, not an independently validated result.
The associated latency tradeoff is CPU p95 **1.36 s → 3.25 s**. There are also 14
negative test questions: refusal improved from 11/14 to 12/14. Cite the full
[measured comparison](retrieval-v2/results.md) if asked about denominators or tradeoffs.
The updated repository passes **147 tests**, and its retrieval audit checks
all **312** iteration predictions without downloading models or source PDFs.

## A 60-second explanation

“I built Filing Lens to investigate a failure mode in financial RAG: an answer can
look plausible and cite a real filing while using the wrong company, year, or unit.
I preserved source spans through extraction and chunking, compared lexical, dense,
and hybrid retrieval, and added a cross-encoder plus numeric evidence checks.

“My next iteration separated candidate recall from final ranking quality. The
original reranker only saw twenty candidates from all companies. I added explicit
entity filtering before retrieval and tested a larger candidate pool while keeping
the reader fixed. The evaluation records what was missed before reranking and what
was demoted afterward. I froze the selected configuration before running test and
kept the original experiment intact.

“The main engineering tradeoff is quality versus CPU latency. The main evaluation
limitation is a small, AI-authored benchmark whose test split has already been
inspected. I can demonstrate the improvement on that benchmark; I would need a
new, independently reviewed holdout to claim broader generalization.”

## Interview questions worth preparing

The research angle is a concrete question: **Can a system remain consistent under
harmless financial presentation changes while still responding to changed or
missing evidence?** Explain why an always-refusing or consistently wrong system
can look robust under agreement alone. Then demonstrate the four decoding arms,
the synthetic fiscal-year interventions, and the raw failures. Cell selection and
unit normalization are established techniques; the proposed contribution is the
controlled response-profile study and its measured mechanism analysis.

Do not list the manuscript as a publication or claim to have invented financial
RAG. Describe it as an independent research project with a reproducible draft.

| Question | Concrete answer to demonstrate |
| :-- | :-- |
| Why can a stronger reranker fail? | It cannot recover a gold passage absent from its candidate set. Show candidate recall and a recovered passage's candidate/final ranks. |
| Why use metadata filtering? | A named issuer is a constraint. Apply it before candidate truncation so unrelated companies cannot consume the budget. Show no-entity fallback and multi-entity union tests. |
| Why not filter by fiscal year? | A filing includes comparative periods; filtering FY2022 questions to FY2022 filings would discard useful FY2023 evidence. |
| Why might hybrid search lose? | Semantic neighbors can dilute exact financial terminology in a small candidate pool. RRF merges ranks, but cannot guarantee better relevance. Show the actual development ablations. |
| How do you prevent label leakage? | Query planning reads only query text and corpus metadata. Inference never reads gold answers. Development selects settings; fingerprints seal implementation and inputs before test. |
| How do you make the result reproducible? | Source/model/dependency locks, preserved candidate and final rankings, per-question outputs, tamper checks, and an offline aggregate audit. |
| Why bootstrap companies? | Questions from the same issuer are dependent. Resampling individual questions would obscure that structure; seven test companies still give coarse estimates. |
| Does a citation prove correctness? | No. Source support and answering the user's question are separate metrics. Supported but irrelevant answers remain failures. |
| What would production require? | Authentication/TLS, durable telemetry, connection-level admission limits, inference cancellation, load tests, and independent label review. The existing service is a local prototype. |

## Evidence to open during a demo

1. [Retrieval design and protocol](RETRIEVAL_V2.md).
2. [Measured comparisons](retrieval-v2/results.md) and [recovered/failing cases](retrieval-v2/failure-ledger.md).
3. [Query planner](../src/filing_lens/query_planning.py), [retriever](../src/filing_lens/retrieval.py), and [regression tests](../tests/test_retrieval.py).
4. [Test-run manifest](../results/retrieval-v2/test/run.json) and [offline auditor](../scripts/audit_retrieval_results.py).

Use the measured test comparison when discussing results. Development's 100%
recall on 18 answerable questions is a tuning result, not the project's headline.
Some short paraphrases still cause evidence refusals; the live demonstration and
the [retrieval limitations](RETRIEVAL_V2.md#limitations) make that explicit.

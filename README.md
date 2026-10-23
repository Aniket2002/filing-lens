# Filing Lens

**Financial RAG research on evidence retrieval, numerical grounding, and model behavior under controlled financial changes.**

[![Python 3.12](https://img.shields.io/badge/python-3.12-255e6a)](pyproject.toml)
[![License MIT](https://img.shields.io/badge/license-MIT-52616b)](LICENSE)
[![CI](https://github.com/Aniket2002/filing-lens/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Aniket2002/filing-lens/actions/workflows/ci.yml)

Filing Lens studies a practical failure in financial question answering: a fluent answer may point to the wrong issuer, fiscal year, table row, or unit. The project retrieves and audits evidence from **1,275 pages across ten semiconductor issuers**, using source-linked questions, recorded retrieval rankings, exact decimal checks, and evidence-based refusal.

## Flagship study: Financial Evidence Equivariance

The [research paper](research/equivariance/manuscript.pdf) tests how financial RAG answers respond to unit changes, column order, changed fiscal-year bindings, and missing evidence. Its frozen pilot contains **600 cases**, compares four decoding arms and two local language models, and preserves **4,800 outcomes** from **2,252 inference calls**.

On 35 test questions with retrieved evidence, canonical cell selection raises paired correctness under unit rescaling from **14.3% to 37.1%**. Original-input accuracy falls from **62.9% to 37.1%**; the simpler canonical-amount arm reaches **40.0%** paired correctness. All four base-model arms fail the evidence-removal refusal test. The results show a real tradeoff, not a general performance gain.

Read the [study overview](research/equivariance/README.md), [measured results](research/equivariance/results.md), [all rescaling regressions](research/equivariance/failures.md), and [prior-art assessment](research/equivariance/NOVELTY.md). The originality claim remains provisional; the paper identifies the closest research and validation needed before submission.

A separate [document-intervention follow-up](research/document-interventions/README.md) rebuilds retrieval across **16 indexes and 800 symbolic outcomes**. Native BM25 with structure-aware chunks falls from **30/35 to 13/35** correct under unit rescaling; a unit-neutral index scores **33/35 on both**. Ordinary Linux and Windows CI restores the locked public corpus and replays every index and outcome.

The [matched LLM follow-up](research/document-llms/README.md) adds **3,200 outcomes from 1,812 inference calls**. For FLAN-T5-base/native-pointer, unit-neutral retrieval improves paired rescaling correctness from **5/35 to 16/35**, while original accuracy stays at **17/35**. Native-amount remains at **0/35** paired correctness. This isolates an important limitation: retrieval robustness does not automatically repair numerical generation. Both follow-ups use reconstructed statement text and previously studied questions; neither is independent validation. The [external evaluation requirements](research/document-interventions/EXTERNAL_EVALUATION.md) track the remaining limitations.

## Supporting technical report: retrieval baseline

The original [retrieval study PDF](research/retrieval-baseline/manuscript.pdf) documents the source pipeline, chunking and retrieval ablations, and numeric answer checks. Entity-aware retrieval with structure-aware chunking and a larger reranker pool improved recall@5 from **59.5% to 88.1%** and answer correctness from **57.1% to 85.7%** on a reused test split. The study and its per-question predictions remain available as supporting evidence, not as a second independently validated publication.

The [technical report source and build instructions](research/retrieval-baseline/README.md) and [validation plan](research/retrieval-baseline/VALIDATION_PLAN.md) explain its limits. The current live CLI/API keeps its separately evaluated extractive reader behavior.

## Reproduce and audit

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.12, then run from the repository root:

```bash
uv sync --locked --extra dev --python 3.12
uv run pytest -q
uv run python scripts/audit_reference.py
uv run python scripts/audit_generation_results.py
uv run python scripts/audit_explanation_results.py
uv run python scripts/audit_retrieval_results.py
uv run python scripts/run_equivariance.py audit
uv run python scripts/run_document_interventions.py audit
uv run python scripts/run_document_llms.py audit
uv run python scripts/run_context_controls.py --check
uv run python scripts/build_paper.py --check
uv run python scripts/report_equivariance.py --check
```

These committed-result checks run offline and do not download models or source PDFs. Model inference is a separate, explicitly recorded step. See the [experiment index](docs/EXPERIMENTS.md) and [result artifact guide](results/README.md).

To repeat CI's full retrieval reconstruction, run `uv run python scripts/prepare_replay_corpus.py`, then `uv run python scripts/run_document_interventions.py audit --replay`. A cold cache requires network access to the locked public PDFs; source bytes and parsed output must match their recorded hashes.

## Try a question

Fetch and parse the public filing corpus first. Then ask a question with the issuer, fiscal period, and requested unit stated clearly:

```bash
uv run filing-lens fetch
uv run filing-lens parse
uv run filing-lens validate
uv run filing-lens ask "What was Micron Technology's FY2023 revenue in USD millions?"
```

Answers include a source page, quote, URL, and numeric checks. The local API and its operational limits are documented in [SERVICE.md](docs/SERVICE.md). The service is a research prototype; production deployment and external monitoring have not been implemented.

## Data and limitations

The original benchmark has **80 AI-authored questions**, including 50 numeric, 20 unanswerable, and 10 narrative questions. Labels have not been independently adjudicated. Its held-out company split has already been inspected in earlier experiments. The new equivariance study reuses those source filings and is a pilot; its synthetic transformations are not independent observations or real restatements. Read the [dataset card](docs/DATA_CARD.md), [failure analysis](docs/FAILURE_ANALYSIS.md), and [experiment protocol](docs/EXPERIMENT_PROTOCOL.md) before interpreting the results.

The repository preserves the frozen question sets, evidence fixtures, predictions, model and source locks, audit scripts, and artifact hashes. Full PDFs, model weights, caches, and personal resume notes are not tracked. Source documents remain under their publishers' copyrights. Code is [MIT licensed](LICENSE); see [NOTICE.md](NOTICE.md) for dependencies and attribution.

```text
src/filing_lens/                 Retrieval, readers, numeric checks, and APIs
research/equivariance/           Flagship study, paper, protocol, and results
research/document-interventions/ Rebuilt retrieval study and financial context controls
research/document-llms/          Matched LLM readers on rebuilt retrieval evidence
research/retrieval-baseline/    Supporting retrieval report and paper source
data/                            Questions, evidence fixtures, and provenance locks
results/                         Frozen predictions and aggregate measurements
scripts/                         Reproduction, reporting, and audit commands
docs/                            Architecture, limitations, and experiment index
tests/                           Offline behavior and artifact-integrity checks
```

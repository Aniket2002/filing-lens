# Document interventions and financial context controls

This exploratory follow-up addresses two practical gaps exposed by the Financial Evidence Equivariance pilot: retrieval was frozen, and there was no symbolic baseline that kept raw answer evidence while changing its retrieval representation. The original 4,800 LLM outcomes remain unchanged.

**Measured:** 800 outcomes, 16 rebuilt BM25 indexes, all 1,275 parsed pages, and the same 50 source questions. These are additional conditions, not 800 independent financial observations. See the [complete results and failures](results.md), [protocol](protocol.json), and [saved evidence and predictions](../../results/document-interventions/).

On the 35 reused test questions, with structure-aware chunks:

| Retrieval view | Original correct | Rescaled correct | Both correct | Originally correct answers lost |
|---|---:|---:|---:|---:|
| Native BM25 | 30/35 | 13/35 | 13/35 | 17 |
| Unit-neutral BM25 | 33/35 | 33/35 | 33/35 | 0 |

Reading transformed chunks at native BM25's original rankings retains 30/35 correct answers. This diagnostic localizes those losses to ranking movement. Column reversal alone causes no correctness loss in these runs. Both development and test outcomes, both chunkers and every failed answer are retained.

The unit-neutral representation masks monetary row values and normalizes scale tokens **only in the retrieval index and query**. Issuers, metric labels, period headers, share counts and per-share values remain available. The reader receives unmasked retrieved text and performs exact Decimal conversion. This is a narrow single-fact lookup baseline: hiding amounts is inappropriate for amount-dependent questions such as threshold searches.

The initial 400 native-view outcomes were inspected before developing the unit-neutral variant and original-ranking diagnostic. This development history is recorded in the protocol. The result is hypothesis-generating, with no claim of independent confirmation, statistical significance or first-ever novelty.

## Intervention boundary

```text
Locked parsed corpus + existing source table fixtures
  -> reconstruct affected statement pages using all their table rows
  -> mutate rendered monetary scales / column order
  -> rechunk all pages and build a new BM25 index
  -> retrieve top 20; expose only top 5 raw chunks to the reader
  -> parse complete rows and resolve question intent
  -> convert units exactly or refuse missing/conflicting evidence
```

Statement-page reconstruction removes surrounding prose and the old duplicate table text on those pages. Unaffected pages, including other disclosures, stay in the corpus. The row parser receives only retrieved text; no answer key, annotated source page or preselected target cell crosses that boundary. Expected values and annotated pages enter the evaluator afterward. Candidate/page coverage, complete target-cell coverage, answer correctness and paired correctness are separate metrics. A numerically correct duplicate disclosure outside annotated pages can make answer correctness exceed annotated-page cell coverage.

This is **not raw-PDF or OCR robustness**: the preparation still depends on previously extracted tables. It also does not resolve the accuracy loss in the original LLM arms; that requires matched comparisons with those same models and evidence. This experiment uses a restricted symbolic reader and no model inference.

## Reproduce

Offline auditing re-executes the reader and scoring against the saved top-five evidence, verifies file fingerprints, and regenerates all counts:

```powershell
uv run python scripts/run_document_interventions.py audit
uv run python scripts/run_context_controls.py --check
```

Ordinary push and pull-request CI runs a full retrieval replay on Linux and Windows, in addition to the saved-output audit. It restores a checksum-verified cache or fetches all ten PDFs from their locked public source URLs, parses and enriches them with the repository's pinned pipeline, and verifies the exact parsed-corpus digest. Source unavailability, source drift, parsing differences or replay differences fail the job; there is no silent skip.

To reproduce the same path locally:

```powershell
uv run python scripts/prepare_replay_corpus.py
uv run python scripts/run_document_interventions.py audit --replay
```

The replay compares all 800 predictions, evidence records and index fingerprints exactly. It requires `data/processed/pages.jsonl`, which the preparation command restores; the basic audit remains offline. Caches are keyed by OS, source and benchmark locks, corpus metadata, parsing code, restoration code and dependency lock. Cache contents are still hashed before use. Original PDFs and parsed text remain outside version control. This CI path reparses original PDFs; it does not transform PDFs before extraction.

For a new full run, use a separate checkout and archive its existing `results/document-interventions` directory before running `uv run python scripts/run_document_interventions.py run`. Runs refuse to overwrite existing results. All indexes use unfiltered BM25, 160-word chunks, fixed-window overlap 32, candidate depth 20 and answer depth five. No gold issuer filter is applied.

## Context and conflicting disclosures

[financial_context.py](../../src/filing_lens/financial_context.py) supplies a separate normalized-record resolver with explicit entity scheme, entity, qualified concept, instant/duration period, start/end dates, unit, dimensions, accounting basis, publication timestamp, accession and source provenance. These distinctions are motivated by [XBRL's context model](https://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31%2Bcorrected-errata-2013-02-20.html) and the [SEC's explanation of consolidated versus segment contexts](https://www.sec.gov/newsroom/whats-new/osd-announcement-contexts-september-7-2016).

The resolver excludes future publications before choosing facts. It uses explicit supersession links within the same financial context; a later filing date alone does not establish a restatement. Conflicting surviving values cause refusal, while equivalent values retain all citations. It does not infer currency conversion, approximate fiscal periods, collapse segment dimensions or treat adjusted and GAAP facts as equivalent. Values must already be in their named base unit.

The [27 saved controls](context-controls.json) cover historical availability, explicit revisions, unlinked conflicts, duplicate facts, currency, segment scope, annual versus quarterly durations, instant contexts, accounting basis, entity identifiers and taxonomy namespaces, plus invalid supersession inputs. They use a fictional issuer and `example.invalid` sources. They establish software behavior only: **zero real restatement cases have been collected or independently reviewed**. This is not an XBRL parser or taxonomy validator. Taxonomy mapping, typed/default dimensions, rounding-consistent duplicates and provenance validation still require adapters and financial review.

## What remains

The separate [matched LLM study](../document-llms/README.md) evaluates the original two models and four decoding arms on both retrieval views. Its results must be judged separately from this symbolic baseline; adding those measurements does not guarantee that the original LLM problems are solved.

The [external evaluation protocol](EXTERNAL_EVALUATION.md) sets out the next data, model, annotation and accuracy requirements. More synthetic variants cannot resolve the reused sample, small models or lack of independent reviewers. Both the original paper and its limitations remain explicit about those gaps.

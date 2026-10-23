# Financial Evidence Equivariance

A research pilot on whether financial RAG systems preserve economic meaning across changes in table presentation while responding correctly to changes in evidence. The candidate contribution is a **typed intervention protocol, a non-vacuous paired evaluation, and a controlled decoding study**. Neither metamorphic testing nor cell selection is claimed as a new invention.

The central question: **Can canonical financial evidence and coordinate-first decoding separate numerical fidelity from evidence selection, and what failures remain after representation invariance is guaranteed?**

## What is implemented

- 50 source questions, five metric families, ten semiconductor issuers; existing company split: 15 development and 35 test questions.
- Two evidence conditions: annotated source pages and the top five pages from the frozen `structure-entity-60` retriever. No gold page is inserted into the retrieved condition.
- Six conditions: original, column reversal, monetary-unit rescaling, reversal plus rescaling, cyclic fiscal-year header rebinding, and removal of the requested period.
- Four factorial arms: native/canonical evidence crossed with amount/pointer output. All arms see the same available cells and opaque cell identifiers.
- Two pinned local instruction-tuned models: FLAN-T5-base and FLAN-T5-small. No hosted inference or LLM judge.
- Exact Decimal arithmetic, explicit UNKNOWN scoring, prompt hashes, checked input lengths, immutable runs, and independently recomputed metrics.

The table adapter exposes all rows matching the five supported metric families on the selected pages. It does not select a row using the expected answer. It is a restricted financial schema, not a general table parser. Original questions and source annotations are reused; transformed records are synthetic and must never be presented as real amended filings.

## Method and falsifiable claim

Represent a cell as `(issuer, metric, fiscal year, dimension, scale, value, source coordinate)`. Canonicalization converts monetary values into the requested monetary unit (or USD millions for per-share questions), preserves per-share dimensions, and sorts by semantic coordinate and source identity. Coordinate-first decoding asks the model to emit a visible cell identifier; an exact executor renders that cell in the requested unit. It does not repair wrong-year or wrong-metric selections using an answer key.

For preserving transformations `T`, the canonical input satisfies `C(T(E)) = C(E)`. Under deterministic inference this gives equal predictions, but **does not imply correct predictions**. A consistently selected wrong cell remains wrong. Period rebinding and evidence removal deliberately fall outside this preserving relation.

The frozen primary hypothesis compares canonical-pointer and native-amount paired usable accuracy under unit rescaling, with retrieved evidence, on the base model and test-company split. A pair succeeds only when both original and transformed outputs are correct numeric answers. An always-refusing system scores zero. Publish the contrast even if negative or inconclusive; the other arms diagnose whether canonicalization or the decoding format explains any difference.

## Reproduce

Install the repository's locked environment. The checked-in dataset and run artifacts support offline auditing without downloading model weights:

```powershell
uv run python scripts/run_equivariance.py audit
uv run pytest tests/test_equivariance.py -q
```

The original sequence was:

```powershell
uv run python scripts/run_equivariance.py prepare
uv run python scripts/run_equivariance.py run --model base --split dev
uv run python scripts/run_equivariance.py run --model base --split test
uv run python scripts/run_equivariance.py run --model small --split dev
uv run python scripts/run_equivariance.py run --model small --split test
```

`prepare` refuses to overwrite a frozen dataset; runs refuse to overwrite existing run directories. To replicate inference, use a separate checkout and move its existing `results/equivariance` directory to an archive location before running the four inference commands. Keep the frozen dataset and protocol. Prompts identical within a run reuse a deterministic output; inference calls and evaluation outcomes are reported separately. A 2,048-token ceiling is checked before inference; truncation aborts the run.

See [the novelty assessment](NOVELTY.md), [frozen protocol](protocol.json), and [publication plan](VALIDATION.md). The existing [retrieval paper](../../paper/manuscript.md) remains a separate empirical baseline.

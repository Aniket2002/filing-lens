# Matched LLM readers after rebuilt document retrieval

This follow-up evaluates the original FLAN-T5-base and FLAN-T5-small models on evidence from both native and unit-neutral BM25 indexes. It directly measures whether the symbolic reader's observed retrieval benefit carries over to these LLMs. It does not assume that better evidence retrieval repairs generation or pointer selection.

The [execution protocol](protocol.json), [local freeze](freeze.json) and implementation were committed at `1362546` before model inference. Selection of structure-aware chunks follows the earlier symbolic results, and the questions and issuers were already studied. This is **exploratory**, not a fresh holdout or external preregistration.

See [all measured comparisons](results.md) and the [raw outcomes](../../results/document-llms/). The complete design comprises **3,200 outcomes**: 50 original questions, two retrieval views, four preserving conditions, four decoding arms and two models. Both models run development cases before test cases, with no intervening arm or hyperparameter selection. Original-input accuracy and paired original/rescaled correctness are reported together for every arm and split.

Measured test result: for FLAN-T5-base/native-pointer, unit-neutral retrieval raises paired rescaling correctness from **5/35 to 16/35**, with original accuracy **17/35 under both views**. Native-amount stays at **0/35 paired correctness** under both. The benefit depends on the decoding interface; the small model remains weak. Runs used **1,812 distinct-prompt inference calls**, with a maximum input of **805 tokens**. These observations are descriptive, not significance claims or proof of novelty.

## Matched factors and remaining differences

The study reuses the exact pinned model revisions, original prompt constructor, amount/pointer decoder, deterministic generation adapter, 2,048-token ceiling and 32-token output budget. Inputs exceeding the ceiling abort instead of silently truncating. Identical prompts reuse a deterministic output within each model; run records distinguish inference calls from evaluated outcomes.

Within each model and decoding arm, only the retrieval view changes. The original raw chunks remain available to the reader, including their actual values and units. Cells are parsed only from complete rows in the top five retrieved chunks. Overlapping chunk copies are coalesced when source coordinate, value and unit agree. Opaque cell identifiers are consistent across presentation variants, with no expected-value dependence. Question units come from the question parser, without falling back to annotated units. Answer annotations enter only evaluation.

The original pilot expanded retrieved chunks to source pages before extracting cells; this follow-up parses top-five chunks directly. Its absolute scores therefore cannot be treated as a continuation of the original pilot's identical evidence setting. The matched comparisons **inside this follow-up** isolate retrieval view, while all four decoding arms continue to expose ordinary-accuracy tradeoffs. Coordinate correctness remains separate from numeric correctness; duplicate disclosures can produce a correct number without matching an annotated source page.

These runs do not add model families, independently reviewed questions, real restatements, or transformed raw-PDF extraction. They evaluate only preserving presentation changes. The original evidence-removal and binding-change failures are not claimed to be repaired.

## Reproduce and audit

Ordinary CI verifies saved raw outputs, prompt fingerprints, decoding, per-case scores, aggregate counts, complete design coverage and identical-prompt reuse without downloading model weights:

```powershell
uv run python scripts/run_document_llms.py audit
```

For actual inference replication, use a separate checkout and archive its existing `results/document-llms` directory. Retain the frozen protocol and source artifacts, then run:

```powershell
uv run python scripts/run_document_llms.py run --model base
uv run python scripts/run_document_llms.py run --model small
uv run python scripts/run_document_llms.py report
```

Model inference remains separate from ordinary CI. The audit recomputes prompt hashes and checks the recorded token bounds; recomputing tokenization or model outputs requires the pinned models/tokenizers. A hash audit establishes artifact consistency, not independent proof that a model produced an output.

Ordinary CI also [reconstructs the upstream retrieval corpus and replays every index](../document-interventions/README.md#reproduce). It checks the original source PDFs and parsed-corpus digest, so a cache is an optimization rather than a substitute for verified inputs.

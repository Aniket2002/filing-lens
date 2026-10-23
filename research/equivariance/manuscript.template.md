# Financial Evidence Equivariance: Separating Numerical Fidelity from Evidence Selection in Financial RAG

Research pilot, 23 October 2026. Author list and affiliations pending review. Not peer reviewed or submitted. Candidate contribution; priority not established.

## Abstract

Financial RAG must preserve a quantity's fiscal period, dimension and source binding across changes in presentation. We study where representation normalization helps: in retrieval, in the model's evidence, or in execution of a selected cell. A frozen pilot crosses native/canonical evidence with amount/cell-ID decoding on two pinned FLAN-T5 models, recording {{outcomes}} outcomes from 50 questions across ten issuers. Its primary paired-correctness contrast under rescaling is {{primary_delta}} percentage points (descriptive company-bootstrap 95% interval {{primary_ci}}), but canonicalization lowers original accuracy and pointer output does not outperform canonical amount generation. An exploratory follow-up rebuilds 16 indexes, then records {{matched_outcomes}} matched LLM outcomes on top-five chunk evidence. {{matched_finding}} These results distinguish retrieval robustness from numerical generation and show that input invariance does not imply correctness. The contribution is an executable, dimension-aware response-profile study and a normalization-placement comparison. The reused 35-question test split, prepared statement text, two small models and unreviewed labels preclude broad generalization or a claim of established novelty.

## 1. Introduction

Financial question answering requires identifying a quantity together with its meaning. An income figure expressed in thousands is not interchangeable with the same surface numeral expressed in millions. Nor is a genuine FY2022 amount a valid answer to a FY2023 question. Retrieval can return the appropriate statement while generation still confuses the row, period, or unit. A single answer-accuracy score does not reveal whether a model follows evidence, copies a familiar numeral, or becomes insensitive to changes in support.

We study a narrower question than general financial reasoning: how should a system respond when the evidence representation changes, when a fiscal-year binding changes, and when the requested evidence is removed? These three situations require different behavior. A robust system should preserve economic quantities across unit and ordering changes, update an answer under a changed binding, and abstain when support is absent.

The proposed research contribution has three components. First, we instantiate these response obligations as executable, dimension-aware transformations of provenance-bearing financial cells. Second, we evaluate paired useful correctness alongside consistency and refusal behavior, so invariance cannot be mistaken for competence. Third, we use a factorial comparison to separate canonical evidence presentation from coordinate-first output. The work is deliberately a pilot: it establishes an executable experiment and falsifiable hypotheses, with independent annotation and external evaluation still pending.

## 2. Related work and scope of originality

Table-cell selection substantially predates this project. TaPas selects cells and can apply an aggregation operation [@tapas]. TAT-QA and TAGOP combine financial table/text evidence with symbolic reasoning [@tatqa]. Financial mathematical reasoning evaluation has also examined table complexity and arithmetic demands [@mathqa]. We inherit the separation between selecting evidence and executing numeric operations; emitting a cell identifier is not itself a new contribution.

The closest methodological precedent is metamorphic testing of RAG under corpus mutations, including financial data, at both pre-chunk and post-chunk stages [@mutations]. Thus neither financial metamorphic testing nor separating retrieval and reader effects is new here. Our candidate distinction is an exact dimension-aware scale intervention crossed with normalization placement and decoding format, reporting original accuracy together with paired useful correctness. This is an incremental experimental contribution, not proof of a first-ever method.

Financial Evidence Crowding studies controlled incompatibility among retrieved candidates and score correction [@crowding]. Our original pilot freezes retrieval; the follow-ups rebuild lexical indexes on reconstructed text. T2-RAGBench compares sparse, dense, hybrid and corrective retrieval with financial answer evaluation [@t2ragbench]; FinFIRST separately evaluates financial answers and their evidence [@finfirst]. Those broad capabilities are established prior art. Work on imperfect tables studies row position and error handling [@imperfect]. We use exact numeric transformation oracles rather than an LLM judge. No cross-paper accuracy comparison is valid across these different datasets and protocols.

## 3. Typed evidence and response obligations

Let an evidence cell be e = (d, m, t, u, v, p), where d identifies the issuer document, m the metric, t the fiscal period, u the dimension and display scale, v the signed decimal value, and p the source coordinate. Monetary cells have scales 1, 1,000, or 1,000,000 USD; per-share cells have a separate dimension. A question requests a metric, issuer, fiscal period, and output unit. Extraction supplies the five supported metric families from each visible page without using the expected answer to select a row.

For source scale s and target scale s', exact conversion is v' = v × s / s'. Per-share values never inherit the monetary scale of the statement. We use Decimal arithmetic and reject incompatible dimensions. The transformation changes the display representation, not the underlying economic quantity.

The intervention family contains the original case and five variants. Column reversal changes the order of cells within each row. Unit rescaling changes all monetary cells between thousands and millions while preserving per-share values. Their composition combines both operations. Period rebinding cyclically rotates the year headers while retaining the physical cell values, inducing a changed answer. Period removal deletes every visible cell for the requested year. Rebinding is intentionally synthetic and need not satisfy accounting identities; it tests evidence dependence rather than simulating a real restatement.

Per-share questions act as a negative control for target-unit scaling: their requested cell does not change scale, although monetary distractors do. The primary denominator includes all five metric families. A supplementary metric breakdown exposes this heterogeneity rather than treating all scale interventions as identical arithmetic tasks.

Canonicalization C converts monetary cells to the requested monetary unit, or USD millions when the question asks for a per-share quantity, then sorts cells by issuer, metric, fiscal period, and source identity. Opaque cell identifiers are allocated from source coordinates using a fixed seeded permutation independent of gold answers. The identifiers persist across transformations.

For a preserving transformation T in the reversal/rescaling family, C(T(E)) = C(E). This follows because exact scale conversion recovers the same economic value and sorting removes presentation order. Thus, for deterministic inference f, f(C(T(E))) = f(C(E)). This is a construction guarantee about the input pipeline, not an empirical discovery about learned financial reasoning. It allows a system to be consistently wrong. Rebinding and removal intentionally do not satisfy this equality.

## 4. Coordinate-first decoding and ablations

We compare four arms: native-amount, canonical-amount, native-pointer, and canonical-pointer. Every arm sees the same available cells and their identifiers. The native arms retain source order and display units. The canonical arms apply C. Amount decoding requests one signed number in the question's requested unit. Pointer decoding requests one visible cell ID; a deterministic executor then converts the selected cell to that unit.

A pointer output has useful but limited guarantees. A valid compatible-dimension ID renders a value from visible evidence with exact conversion; it cannot invent a new numeral. The model can nevertheless choose the wrong metric or period. No answer key, gold source location, or target ID enters the inference function, and the executor does not repair a wrong selection. Unknown IDs, incompatible dimensions, malformed numeric outputs, and explicit UNKNOWN are recorded separately. Only the exact UNKNOWN response is treated as successful abstention on missing evidence.

The two canonicalization operations are bundled in this pilot. The factorial design separates that bundle from the output format, but cannot independently attribute effects to sorting versus unit conversion. An expanded experiment must include these two ablations separately. Likewise, pointer output length, tokenization, and instruction wording differ from amount output; observed differences are properties of the complete decoding interfaces, not a pure causal effect of symbolic reasoning.

## 5. Experimental protocol

The source collection contains FY2023 annual reports from ten semiconductor issuers and comparative values from earlier fiscal years. The existing benchmark contributes 50 numeric questions spanning revenue, net income, research and development, total assets, and diluted earnings per share. Three companies provide 15 development questions; seven provide 35 test questions. The same test companies were used in earlier repository studies, so the current freeze does not create a fresh independent holdout.

Each question is evaluated with two evidence sources. The oracle-page condition exposes the annotated source page's supported typed rows. The retrieved-pages condition exposes supported typed rows from the top five ranked chunks' pages in the frozen entity-aware BM25/cross-encoder run. Gold pages are never inserted into this condition. Full-page table expansion and the restricted five-metric schema make this a structured evidence adapter, not raw chunk-only generation. For the original questions, {{retrieved_coverage}} of 50 retrieved evidence sets contain a matching source fact; this coverage is not the earlier span-level Recall@5 metric.

Crossing 50 questions, two sources, and six variants yields 600 cases. Four arms and two models produce {{outcomes}} outcomes. FLAN-T5-base and FLAN-T5-small [@flan] use pinned revisions, greedy decoding, a fixed seed, and no fine-tuning. Input length is checked against a 2,048-token ceiling before inference; the observed maximum is {{max_tokens}} tokens. No context is silently truncated. Both models belong to one family and are small relative to contemporary general-purpose LLMs.

Protocol, implementation, source evidence, dependency lock, frozen retrieval predictions, and the constructed dataset are fingerprinted before inference. The initial freeze is preserved in repository commit 53a7d02. There is no model or arm selection after development: all four arms and both models are published. Identical prompts within a run reuse the deterministic output, so evaluation outcomes must not be described as independent inference calls or stochastic replicates. Each test run follows its corresponding development run.

For original and preserving variants, paired usable accuracy is the mean of I(original correct numeric) × I(transformed correct numeric), over all source questions. Incorrect answers and refusals both score zero. We additionally report single-case task accuracy, context correctness, numeric coverage, invalid outputs, and decoded-state agreement. Agreement compares the decoded value and status, so different malformed strings can collapse to the same invalid state; all raw outputs remain available. It is deliberately a weak diagnostic, not a correctness criterion. Missing evidence may justify abstention under context correctness while still failing a task that asks for a known source quantity. Removal cases instead require explicit UNKNOWN. Period-rebinding accuracy is scored against the transformed evidence oracle.

The primary score is numerical, so coincidentally identical values can conceal selection of a wrong cell. Pointer-coordinate correctness is therefore recorded separately: an ID must identify a matching issuer, metric, period, and transformed value. A repeated disclosure with the same fact can supply an alternative valid coordinate. Amount-only outputs do not identify their source cell, so coordinate accuracy is not assigned to those arms. The requested output unit is supplied from the benchmark's unit annotation; this pilot does not evaluate free-form unit-intent parsing.

The prespecified primary contrast is canonical-pointer minus native-amount paired usable accuracy under unit rescaling, with retrieved evidence and the base model on test companies. Its uncertainty uses 2,000 paired company-cluster bootstrap resamples with seed 17. Every test company supplies five source questions; transformed cases are not treated as independent samples. With only seven clusters, intervals are descriptive and coarse. Secondary arms, variants, and the small model are diagnostic comparisons without multiplicity-adjusted significance claims.

## 6. Results

{{result_interpretation}}

Table 1 reports test results with retrieved evidence. Base is single-case numeric correctness. Scale, reverse, and combined are paired usable percentages. Rebind is correctness under changed year bindings. Removal is explicit correct abstention. Every cell has 35 underlying source questions, not 210 independent observations.

{{retrieved_table}}

Table 2 provides the corresponding oracle-page diagnostic. Differences between these tables include the distractor cells exposed by the evidence adapters; they should not be attributed only to gold-page retrieval misses.

{{oracle_table}}

![Consistency and useful correctness under unit rescaling](comparison.png)

Figure 1. Test-company decoded-state agreement and paired usable accuracy under unit rescaling with retrieved evidence. Canonical input equality makes agreement structural; usefulness remains an empirical question. Cached identical prompts contribute no additional stochastic evidence.

{{failure_example}}

Table 3 separates numerical correctness from coordinate correctness for pointer outputs with retrieved evidence. Invalid includes unknown IDs and incompatible dimensions. Numeric agreement alone is insufficient evidence of correct binding.

{{pointer_table}}

Full per-question predictions preserve raw model output, decoded value or ID, invalid-output state, prompt fingerprint, token count, evidence source, intervention, and scoring fields. All aggregate tables are regenerated from these outcomes and checked against the saved metrics. This audit establishes internal consistency and provenance; it does not independently validate source annotation or prove model execution from a cryptographic signature.

## 6.1. Exploratory follow-up: rebuilding document-text retrieval

An exploratory follow-up records {{document_outcomes}} symbolic-reader outcomes over 16 rebuilt BM25 indexes: four presentation variants crossed with two chunkers and native or unit-neutral index text. All 1,275 parsed pages participate. Statement pages are reconstructed from existing tables; other pages remain unchanged. Text changes precede chunking, indexing and answer-time parsing. Prior table preparation and removal of surrounding statement-page prose limit this experiment; it does not evaluate raw-PDF extraction.

The symbolic reader resolves the issuer, requested year, one of five metric families and the output unit from question text. It selects only complete retrieved rows and executes exact unit conversion, refusing missing or conflicting values. The unit-neutral index masks monetary row values and normalizes monetary scale tokens only for retrieval; the reader always receives the original, unmasked text for that variant. This representation is intended for single-fact lookup, not questions about monetary thresholds. Neither model outputs nor answer annotations enter ranking or selection.

{{document_table}}

Table 4. Test counts over the same 35 questions. Page@5 is annotated source-page coverage, not span recall. Frozen correct answers from changed text at original top-five chunk identities; it isolates the effect of ranking movement. {{document_finding}} On this prepared corpus, lexical sensitivity to scale and amounts can therefore dominate exact numerical execution. This is evidence for separating retrieval robustness from reader robustness.

The native-index run was inspected before adding the unit-neutral view and frozen-ranking diagnostic. All chunkers, views, variants, development/test results and failures are published in `research/document-interventions/results.md`. This symbolic experiment is exploratory and reuses the pilot companies. Its results are not directly comparable with the original LLM arms because the retriever, presentation and reader differ.

## 6.2. Matched LLM follow-up: does retrieval robustness transfer?

A second follow-up crosses the two retrieval views with the original four decoding arms and both pinned models, using structure-aware chunks and four preserving conditions. It records {{matched_outcomes}} outcomes from {{matched_calls}} distinct-prompt calls. Code, protocol and source evidence were frozen in commit 1362546 before inference; structure chunking and the question set were selected or inspected earlier, so this is not confirmatory evaluation. Each model processes development before test with no intervening selection. The maximum input is {{matched_max_tokens}} tokens under the same 2,048-token ceiling.

The reader parses only complete rows in the top five raw chunks, coalescing consistent overlapping copies. Requested units come from question text; expected values and annotated target pages are used only for scoring. Retrieval view is matched within each arm. Unlike the original pilot, there is no expansion to entire source pages, so absolute scores across the two experiments are not directly comparable. All outcomes, prompt hashes, raw responses and coordinate diagnostics are retained.

{{matched_table}}

Table 5. Counts over the same 35 test questions per row. Base is original numeric accuracy; paired requires both original and rescaled answers correct. Native and neutral refer to retrieval text, independently of the arm's native/canonical model input. All four arms and both models are shown; no significance or model-family generalization is claimed.

{{matched_finding}} The gain therefore depends on the reader interface. Exact execution of a selected cell benefits from more stable retrieval, whereas unconstrained amount generation can still fail the unit conversion. Canonical-pointer does not dominate native-pointer, and the small model remains weak. This is a measured interaction among complete pipelines, not a causal identification of model reasoning or a resolution of the original accuracy tradeoff. Changing retrieval text can change ranks, available rows, distractors and their order simultaneously. Evidence deletion and fiscal rebinding were not rerun in this follow-up.

## 7. Limitations and next experiments

The narrow schema and prepared tables simplify natural filings. Labels are AI authored and source checked, without independent financial adjudication. Synthetic interventions add conditions, not independent observations. The seven limitations below constrain the claims even after the exploratory retrieval follow-up.

Beyond these limitations, multi-cell arithmetic, trained table-selection baselines, constrained decoding, value-blind selection and separate sorting/normalization ablations remain open. Candidate coverage, ranked evidence coverage and answer quality must be reported separately for each extension.

| Limitation | Importance | Consequence and required evidence |
|---|---|---|
| 35 test questions across seven previously studied issuers | High | Transformations do not enlarge the independent sample; require fresh issuers, industries, periods and question authors. |
| Two small FLAN-T5 variants | High | No cross-family or larger-model conclusion; require pinned models from at least two independent families. |
| Typed evidence prepared before intervention | High for end-to-end claims | The document follow-up still reconstructs statement pages; require transformations of raw documents before extraction. |
| Canonicalization and pointers can lower base accuracy | High | The matched follow-up reports both scores and finds an arm-specific retrieval gain; canonical-pointer still does not dominate and external replication is needed. |
| No independent financial annotations | High | Require two source-reviewing annotators and adjudication before treating labels as validated. |
| Limited retrieval families | Medium | The follow-up integrates rebuilt BM25 with LLM readers; transformed dense/hybrid retrieval remains untested. |
| No real restatements, XBRL contexts or conflicting-disclosure evaluation | High | Synthetic context software controls are not real financial cases; require accession-linked sources, publication times and reviewed context bindings. |

The strongest defensible claim at this stage is an auditable experimental contribution: the repository can distinguish preservation, changed binding, and lost support, and can measure whether canonicalization or pointer output helps on a restricted pilot. Publication-level novelty, broad superiority, and external validity are open questions. A fresh industry-diverse holdout and independent review should precede a stronger manuscript submission.

## 8. Reproducibility and availability

The repository preserves {{outcomes}} original LLM outcomes, {{document_outcomes}} symbolic outcomes and {{matched_outcomes}} matched LLM outcomes, with protocols, locks, fingerprints and manuscript sources. These are dependent evaluations of the same 50 questions, not a larger independent benchmark. The three `run_equivariance.py`, `run_document_interventions.py` and `run_document_llms.py` scripts audit saved outcomes without model inference. Ordinary CI on Linux and Windows also runs `prepare_replay_corpus.py` to restore and verify locked public PDFs and their parsed corpus, then `run_document_interventions.py audit --replay` to rebuild all 16 indexes and replay 800 outcomes. Cold-cache execution requires network access; caches are hash-checked. Model inference remains separately reproducible from pinned revisions. Run `python scripts/report_equivariance.py --check` to verify this draft.

## References

{{references}}

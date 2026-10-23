# Novelty assessment and nearest prior work

Search date: 2026-10-23. This is a targeted literature review, not a proof of priority. A defensible manuscript should call this a proposed evaluation and systems contribution until broader review and independent replication establish its originality.

| Prior work | What already exists | Boundary of this proposal |
| --- | --- | --- |
| [TaPas, ACL 2020](https://aclanthology.org/2020.acl-main.398/) | Table-cell selection with optional aggregation | Selecting cells is inherited; we study its behavior under typed financial interventions |
| [TAT-QA / TAGOP, ACL 2021](https://aclanthology.org/2021.acl-long.254/) | Financial hybrid QA, cell/span extraction, symbolic computation | Financial QA and symbolic execution are inherited; our target is paired evidence response |
| [Financial mathematical reasoning evaluation, ACL 2024](https://aclanthology.org/2024.findings-acl.231/) | Financial table complexity and arithmetic reasoning evaluation | Our pilot isolates representation changes and fiscal-year binding, not general multistep arithmetic |
| [When Knowledge Changes, ASE 2026](https://arxiv.org/abs/2607.26843) | RAG mutations at pre-chunk/index and post-chunk/context stages, including financial datasets | Closest methodological prior work; stage separation is inherited. Candidate distinction: exact dimension-aware scale changes crossed with normalization placement and decoding, measuring original and paired accuracy |
| [Financial Evidence Crowding, 2026 preprint](https://arxiv.org/abs/2609.35782) | Controlled constraint conflicts and gated financial reranking | The original pilot freezes retrieval; follow-ups rebuild lexical indexes. We do not claim to invent constraint-aware ranking |
| [TempFinRAG, 2026](https://www.mdpi.com/2073-8994/18/9/1498) | Temporal financial evidence, cross-modal checking, numerical verification | Unit and period verification alone are not new; our pilot does not evaluate publication-time validity |
| [Understanding Errors in LLM-Based QA over Imperfect Tables, 2026](https://arxiv.org/abs/2610.04687) | Row-position effects, error discovery, repaired tables, multiple views | We distinguish meaning-preserving transformations from deliberately changed fiscal evidence and measure useful answers alongside consistency |
| [T2-RAGBench, 2026 preprint](https://arxiv.org/abs/2604.01733) | Broad financial text/table retrieval comparisons with answer-level evaluation | Comparing financial retrieval and generation is inherited; our restricted experiment measures response to exact presentation interventions |
| [FinFIRST, 2026 preprint](https://arxiv.org/abs/2609.25192) | Financial answers, supporting evidence, period/unit alignment and traceability evaluated separately | Evidence/answer separation is inherited; our candidate contribution is a controlled normalization-placement experiment, not a new traceability concept |

## Claim we can investigate

Financial evidence admits a typed set of transformations: some preserve economic quantities, some reassign the quantity to another fiscal period, and some remove support. The joint response profile, measured on paired source cases with a coverage-sensitive score, can reveal failures obscured by static answer accuracy or agreement alone. A factorial comparison of canonicalization and pointer decoding can identify which mechanism affects this profile.

The completed follow-ups narrow the candidate contribution to **where normalization is applied, and whether retrieval robustness transfers to the reader**. They cross native/unit-neutral index text with native/canonical model evidence and amount/cell-ID output, retaining raw reader evidence. The original-ranking diagnostic separately tests transformed text with the symbolic reader; that diagnostic has not been run with LLM readers. This combination is a testable research question, not a claim that any individual component is unprecedented.

On the reused test split, FLAN-T5-base/native-pointer improves paired scale correctness from 5/35 to 16/35 with unit-neutral retrieval while original accuracy stays at 17/35. Native-amount remains at 0/35 paired correctness under both retrieval views. Canonical-pointer with neutral retrieval reaches 10/35 on both original and paired correctness. These observations support an arm-dependent benefit, not universal normalization superiority. All arms, including weak small-model results and development results, are published in the [matched experiment](../document-llms/results.md). This interpretation was written after inference and is exploratory.

The mathematical invariance of a canonical representation is a construction property, not evidence that a language model learned financial reasoning. Likewise, pointer decoding prevents unsupported numeric fabrication only conditional on selecting a visible compatible-dimension cell; it can still cite the wrong financial fact. These distinctions belong in the abstract and discussion, not only a limitations footnote.

## Claims explicitly not established

- The first financial RAG system, the first metamorphic RAG benchmark, or the first use of cell identifiers or unit normalization.
- State-of-the-art retrieval or generation, superiority over the papers above, or significance against their incomparable datasets.
- Generalization to unseen industries, new documents, frontier LLMs, real restatements, XBRL contexts, currencies, or consolidated-versus-segment scope.
- A new foundation model, training algorithm, causal discovery method, or independently reviewed benchmark.
- Absolute novelty, a first normalization-placement study, or proof that no earlier work contains an equivalent experiment.

## How the proposed novelty can fail

If a closer prior method already evaluates the same typed transformations with an equivalent paired utility objective and decoding decomposition, position this work as a replication and financial implementation. If canonical amount generation matches pointer decoding, remove the claim that coordinate-first decoding adds value. If the benefit disappears with larger models, make the resource and model-size boundary explicit. If raw consistency is as informative as paired correctness on broader data, narrow the metric claim.

For the placement claim, failure to replicate the native-pointer gain on new issuers or a stronger model would limit the result to this pilot. If equal-size unnormalized evidence produces the same benefit, evidence composition may explain the gain rather than a special financial invariance mechanism. A future protocol should freeze these comparisons before opening new test labels; it should not select a winning arm from the present table and call that selection confirmatory.

## Review coverage and remaining uncertainty

The 23 October 2026 review searched financial RAG, unit/scale normalization, metamorphic table testing, financial cell selection and temporal evidence. The closest mutation paper and T2-RAGBench were inspected in primary-source full text; FinFIRST's primary abstract establishes overlap in evidence evaluation. The TempFinRAG publisher blocked full-text access in this pass, so its precise experimental overlap remains unresolved. The review does not cover all unpublished work, patents, non-English papers or citation networks. It cannot certify absence of prior art.

Before submission, expand citation-network review, compare full experimental protocols, obtain independent expert feedback, and update this table. If an equivalent prior design is found, describe this work as a replication and financial implementation. A search yielding no exact title match is not a novelty certificate.

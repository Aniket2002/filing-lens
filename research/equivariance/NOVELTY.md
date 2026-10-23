# Novelty assessment and nearest prior work

Search date: 2026-10-23. This is a targeted literature review, not a proof of priority. A defensible manuscript should call this a proposed evaluation and systems contribution until broader review and independent replication establish its originality.

| Prior work | What already exists | Boundary of this proposal |
| --- | --- | --- |
| [TaPas, ACL 2020](https://aclanthology.org/2020.acl-main.398/) | Table-cell selection with optional aggregation | Selecting cells is inherited; we study its behavior under typed financial interventions |
| [TAT-QA / TAGOP, ACL 2021](https://aclanthology.org/2021.acl-long.254/) | Financial hybrid QA, cell/span extraction, symbolic computation | Financial QA and symbolic execution are inherited; our target is paired evidence response |
| [Financial mathematical reasoning evaluation, ACL 2024](https://aclanthology.org/2024.findings-acl.231/) | Financial table complexity and arithmetic reasoning evaluation | Our pilot isolates representation changes and fiscal-year binding, not general multistep arithmetic |
| [When Knowledge Changes, ASE 2026](https://arxiv.org/abs/2607.26843) | RAG metamorphic testing, corpus mutations, changed facts and fallback, including financial datasets | Closest methodological prior work; our candidate distinction is dimension-aware transformations with exact cell provenance, paired usable scoring, and a decoding factor study |
| [Financial Evidence Crowding, 2026 preprint](https://arxiv.org/abs/2609.35782) | Controlled constraint conflicts and gated financial reranking | Our interventions occur after fixed retrieval; we do not claim to invent constraint-aware ranking |
| [TempFinRAG, 2026](https://www.mdpi.com/2073-8994/18/9/1498) | Temporal financial evidence, cross-modal checking, numerical verification | Unit and period verification alone are not new; our pilot does not evaluate publication-time validity |
| [Understanding Errors in LLM-Based QA over Imperfect Tables, 2026](https://arxiv.org/abs/2610.04687) | Row-position effects, error discovery, repaired tables, multiple views | We distinguish meaning-preserving transformations from deliberately changed fiscal evidence and measure useful answers alongside consistency |

## Claim we can investigate

Financial evidence admits a typed set of transformations: some preserve economic quantities, some reassign the quantity to another fiscal period, and some remove support. The joint response profile, measured on paired source cases with a coverage-sensitive score, can reveal failures obscured by static answer accuracy or agreement alone. A factorial comparison of canonicalization and pointer decoding can identify which mechanism affects this profile.

The mathematical invariance of a canonical representation is a construction property, not evidence that a language model learned financial reasoning. Likewise, pointer decoding prevents unsupported numeric fabrication only conditional on selecting a visible compatible-dimension cell; it can still cite the wrong financial fact. These distinctions belong in the abstract and discussion, not only a limitations footnote.

## Claims explicitly not established

- The first financial RAG system, the first metamorphic RAG benchmark, or the first use of cell identifiers or unit normalization.
- State-of-the-art retrieval or generation, superiority over the papers above, or significance against their incomparable datasets.
- Generalization to unseen industries, new documents, frontier LLMs, real restatements, XBRL contexts, currencies, or consolidated-versus-segment scope.
- A new foundation model, training algorithm, causal discovery method, or independently reviewed benchmark.

## How the proposed novelty can fail

If a closer prior method already evaluates the same typed transformations with an equivalent paired utility objective and decoding decomposition, position this work as a replication and financial implementation. If canonical amount generation matches pointer decoding, remove the claim that coordinate-first decoding adds value. If the benefit disappears with larger models, make the resource and model-size boundary explicit. If raw consistency is as informative as paired correctness on broader data, narrow the metric claim.

Before submission, search citation networks around the closest seven works, compare full experimental protocols, obtain independent expert feedback, and update this table. A search yielding no exact title match is not a novelty certificate.

# External evaluation: requirements before a stronger claim

Status: a proposed next study, not completed data collection, model inference, external registration or independent review. The current follow-up is exploratory. Freeze a final protocol and register it externally **before** fresh test inference; changes after that point require a new exploratory designation.

## Completion criteria for the seven limitations

| Limitation | Current change | Evidence still required |
|---|---|---|
| 35 reused test questions, seven issuers | No change to the independent sample | At least 30 fresh test issuers, six industries, multiple filing years and independently authored questions. |
| Two small models from one family | Symbolic baseline and 3,200 matched outcomes from the original two models added | At least two independent instruction-tuned model families, with a larger open-weight model in each; pin exact revisions and publish all outputs. |
| Pre-extracted typed cells | Text is mutated before reindexing and answer-time parsing | Raw PDF/HTML/iXBRL changes before extraction; publish extraction errors separately. |
| Lower original accuracy | [Matched LLM comparisons](../document-llms/README.md) now evaluate both retrieval views with the original models and all four arms | Judge both original accuracy and paired robustness; these reused-data comparisons cannot establish general recovery or external superiority. |
| No independent annotations | Existing source review tooling remains available | Two independent source reviewers, adjudication, agreement statistics and retained disagreements. |
| Frozen retrieval | Rebuilt lexical indexes, original-ranking diagnostic, matched LLM inference and full replay in ordinary CI | Dense/hybrid/reranked retrieval and independent external evaluation. |
| No realistic restatements or context conflicts | Normalized context resolver and synthetic controls added | Real accession-linked disclosures, reviewed context mappings and explicit amendment/restatement provenance. |

## Data collection and separation

Target 200 development questions from ten new issuers, plus 600 test questions from 30 other new issuers. Use at least six industries, such as banking, insurance, retail, energy, healthcare and utilities, and at least two filing years per issuer. Exclude the ten previously studied issuers (NVDA, AMD, INTC, QCOM, AVGO, TXN, MU, ADI, MCHP, NXPI) from both new pools. This is a collection target, not a sample-size or statistical-power claim; estimate cluster variability on development data before finalizing a precision-based sample size.

Use issuer groups, not transformed rows, as the splitting and resampling unit. Deduplicate filings, amended accessions, facts, templates and question paraphrases across splits. Keep the test questions unavailable to method selection. Track all candidate sources, exclusions and replacement decisions. Do not replace failures after seeing model results.

Include source-supported single-fact questions, true as-of/restatement pairs, instant versus duration distinctions, consolidated versus segment disclosures, and missing/conflicting evidence. Preserve original and revised values with accession, source URL, publication timestamp and context identity. A later comparative number is not automatically a restatement: reviewers must identify the disclosure establishing revision and whether its concept, scope and accounting basis match. Record timestamp precision; date-only metadata cannot support intraday knowledge claims. Do not fill a scarce real-case category with synthetic examples and count it as real data.

## Annotation without model influence

Two financial reviewers independently inspect original source documents. Each records row/concept, entity and identifier scheme, period kind and dates, unit/currency, segment dimensions, accounting basis, answerability, value, provenance and any explicit supersession. Hide model outputs and the other reviewer's labels. Keep both submissions, measure raw agreement by field, publish disagreement counts, and have a third adjudicator resolve discrepancies. Rejected or unresolved examples remain in the audit ledger.

The existing [annotation review workflow](../../docs/ANNOTATION_REVIEW.md) is a starting point; its current exported gold labels should be hidden for an independently authored fresh set. A reviewer name in a CSV is not proof of independent review. No reviews have been performed by this code change.

## Models, retrieval and mechanism comparisons

Before inference, pin two or more independent model families and exact revisions, tokenizer, prompt/chat format, context limits, decoding, seeds, quantization and hardware. Select sizes that can run on available hardware and justify the choice; adding another FLAN-T5 size does not meet the diversity requirement. Publish token usage, truncation/exclusion handling, cost and latency, including failed calls. Model downloads or successful adapter construction do not count as evaluated models.

Evaluate native amount, native pointer, sorting-only, normalization-only, combined canonicalization and retrieval-only normalization under matched retrieval budgets and answer evidence. Add symbolic selection and a reproducible table-QA baseline. Test BM25, dense retrieval and hybrid reranking. Keep context filtering based on query-visible information; never insert gold pages, correct units from expected labels or fix wrong selections using the answer key. Report parsing accuracy, candidate recall, ranked evidence coverage, context/cell correctness, numeric correctness, refusal and joint base/variant correctness separately.

The proposed candidate mechanism is **representation normalization confined to retrieval, with raw provenance-preserving evidence for answering and context-aware conflict refusal**. The current data support investigation, not a first-ever algorithm claim. Compare the mechanism against existing canonicalization, table retrieval and temporal financial QA methods before making a novelty claim.

## Decision rule and publication

Predeclare a base-accuracy non-inferiority margin with a domain justification; a provisional margin is two percentage points. On the fresh test set, require both a positive lower confidence bound for paired robustness improvement and a lower bound above the negative base-accuracy margin against the same native pipeline. Use paired issuer-cluster uncertainty, publish both endpoints and every comparison, and specify multiplicity handling before inference. Report failure of either criterion as failure of the joint claim. Do not tune the margin after results or infer significance from this reused pilot.

Require independently adjudicated financial contexts and a real-document extraction evaluation before making end-to-end or realistic-restatement claims. Release source hashes, legally distributable evidence excerpts, all predictions, errors, exclusions, reviewer agreement and a reproducible environment. Maintain the original pilot as exploratory evidence even if the fresh result is negative.

# Dataset card

## Scope

Ten US-listed semiconductor issuers: NVIDIA, AMD, Intel, Qualcomm, Broadcom,
Texas Instruments, Micron, Analog Devices, Microchip, and NXP. The corpus holds
one FY2023 report per issuer, including any proxy/letter/exhibit material present
in the downloaded PDF. It is not restricted to annotated pages. Some issuers have
software businesses; this is a sector cohort rather than a pure-play screen.

The fiscal year label is the issuer's, not the calendar year. NVIDIA's FY2023
ended January 29, 2023; Microchip's ended March 31, 2023. See
[`corpus.json`](../data/corpus.json) for the fiscal end dates and download URLs.
Original documents retain their publishers' copyrights. Full PDFs and full parsed
documents are excluded from Git; source hashes, attribution, short gold excerpts,
and normalized primary-statement data are included for auditability.

## Annotation procedure and authorship

The 80 questions were individually AI-authored after inspecting actual source text
and statement pages. They have **not been independently adjudicated by a human**.
They must not be described as a human-labelled dataset. A separate AI-assisted
visual spot check covered twelve numeric annotations across three rendered source
pages; see [the inspection record](SOURCE_SPOT_CHECKS.md).
The [source-linked review workflow](ANNOTATION_REVIEW.md) now exports all 80
questions and validates separately recorded adjudications. The committed sheet
has **zero completed reviews**; independent human review remains pending.
A [separate explanation challenge](EXPLANATION_STUDY.md) adds 40 new questions
frozen before inference from ten other passages in the same filings. Its own
review sheet also has zero completed reviews. It is not part of the 80-question
reference benchmark and is not independent human validation.

1. Inspect the source statement or paragraph.
2. Write a question, explicitly specify the fiscal period, and independently
   record the expected amount/unit or acceptable narrative answer string.
3. Record the document, one-based PDF page, and exact passage or row label.
4. Resolve these annotations against the canonical parser output and assert that
   the independently entered numeric amount agrees. Materialization fails on drift.
5. Freeze the question file and parser-output hashes before the retrieval run.

`annotations.json` contains the source annotation inputs;
`questions.jsonl` contains materialized immutable character spans. Neither file is
imported by the retriever or reader. A new chunker reuses the same source spans.
The annotation materializer is a dataset-maintenance tool; **do not rerun it to
make a failed frozen-input validation pass** without versioning the dataset.

## Composition

| Category | All | Development | Test |
| :-- | --: | --: | --: |
| Numeric | 50 | 15 | 35 |
| Qualitative | 10 | 3 | 7 |
| Unanswerable | 20 | 6 | 14 |
| Total | 80 | 24 | 56 |

Development companies are NVDA, AMD, INTC. The other seven are test companies.
No company crosses splits. All companies' reports are searchable in every run;
this is a question-generalization split, not an unseen-document experiment.

Numeric questions cover revenue, consolidated net income, R&D, assets, and
diluted EPS. Some request FY2021/FY2022 comparatives. ADI uses USD thousands;
other statements use USD millions. EPS uses USD per share regardless of the
table's aggregate currency unit. Micron losses and NXP's signed R&D line retain
the statement's sign. Broadcom's historical EPS is not retroactively split-adjusted.

Unanswerables contain ten deliberately out-of-period questions and ten missing
metrics/granularities. This is a small and relatively easy negative set. Future-year
questions can be rejected from corpus metadata. This must not be presented as
robust hallucination detection or evidence of performance on subtle false premises.
Refusal reasons are corpus-scoped; the information could exist outside the corpus.

## Known limitations

- Five numeric question types repeat across issuers; this is a narrow extraction
  benchmark, not a comprehensive financial reasoning test.
- Gold anchors select a canonical statement passage. Equivalent disclosures elsewhere
  may be judged irrelevant. Reported passage recall is consequently conservative.
- The gold extraction and runtime numeric checks share a PDF parser. Source hash
  checks do not validate visual correctness. Human visual checks remain necessary.
- Narrative correctness uses an acceptable answer substring, not an expert semantic
  judge. It can miss valid paraphrases and accept an irrelevant long quote containing
  the substring. Citation support and question correctness are reported separately.
- No OCR, cross-document arithmetic, multi-hop comparison, restatement reconciliation,
  or comprehensive geographic/segment/year support is claimed.
- Annotator bias, small company count, and public-report selection limit generalization.

## Schema

Each question has `id`, `company`, `split`, `kind`, `question`, `answerable`, and
`gold`. A gold passage records `doc_id`, `page`, `start`, `end`, `quote`, and
`source_url`. Numeric records also carry `metric`, `period`, `expected_value`,
and `expected_unit`. Unanswerables have an empty gold list and an explicit rationale.
Offsets index the canonical page string, not PDF bytes or printed page numbers.

# Validation plan for a stronger paper

This is proposed work. None of the experiments or human reviews below is counted
as completed in the current manuscript. Freeze the final protocol and its hashes
before new test inference; retain the current exploratory results as pilot data.

## 1. Independent adjudication

Use the existing annotation and answer-review exports. Have independent reviewers
inspect the original rendered statement pages or reconciled XBRL values, not only
the parser output. Record source-cell amount, sign, unit, fiscal period, metric
scope, and alternative valid disclosures. Reviewers should be blind to the system
configuration and predicted correctness when judging labels.

Double-review a prespecified subset and all disagreements; retain both initial
judgments, agreement statistics, adjudication decisions, and pending counts. Do
not describe AI-assisted spot checks as independent human validation. Version
corrections as a new dataset instead of rewriting the historical gold silently.

## 2. A new holdout

Acquire additional issuers, sectors, and reporting periods with documented source
selection. Keep all questions and wording variants for an issuer in one partition.
State whether the claim concerns unseen questions over an indexed corpus or
previously unseen documents; these require different setups. Reserve test data
before retrieval development and restrict access to labels during tuning.

Choose the number of companies and questions using a pilot-informed clustered
power/precision analysis for a prespecified minimum useful recall improvement.
Do not select a sample size after seeing a desired confidence interval. Log the
sampling frame, exclusions, missing-document handling, and annotation budget.
Include a broader mix of metrics and narrative intents than the current five
repeated numeric families.

## 3. Frozen wording and refusal challenge

Create independently checked variants that preserve the underlying question:
full company name versus ticker, concise versus explicit fiscal wording, omitted
versus stated display unit, metric synonyms, and comparative-year references.
Keep variants paired to the same fact and within the same company split. Omitted
units must have a defined scoring rule that accepts the source's stated unit.

Add unsupported comparisons, absent entities, false premises, ambiguous metrics,
wrong fiscal/calendar assumptions, and questions requiring unavailable arithmetic.
Balance easy out-of-period negatives with harder evidence-sensitive negatives.
Score refusal and answer coverage together. Preserve failures rather than adding
special-case rewrites after inspecting test outputs.

## 4. Factorial retrieval and reader controls

On development, separate chunking, entity routing, candidate depth, expansion,
and dense fusion rather than changing several components in one contrast. Include
at least the full routing-by-depth comparison at matched chunking. Freeze the
primary test contrasts and selection/tie rules before test. Match reader context
budgets and disclose repeated-header/token overhead.

For stronger external relevance, add a well-specified contemporary embedding or
reranking baseline and an appropriate larger-reader condition, with pinned versions,
cost accounting, and equal evidence budgets. Select these based on the research
question, not after comparing test scores. External FinQA/TAT-QA evaluation requires
task-compatible reasoning support and their official scoring protocols; do not
reuse Filing Lens percentages as comparable benchmark scores.

## 5. Measurement and analysis

Preregister recall@5 as a primary retrieval endpoint and specify a separate primary
answer-quality endpoint. Report sample counts, numerator/denominator, coverage,
negative refusal, and candidate recall for each. Use independent human judgments
for narrative correctness and support; do not substitute a substring check or an
unvalidated model judge for entailment.

Use paired company-cluster analysis and document multiplicity for secondary
contrasts. Report regressions as well as gains, and retain issuer-level breakdowns.
Consider equivalent valid passages when auditing retrieval misses. Keep the current
seven-company intervals descriptive; new evidence must justify broader inference.

For latency, record CPU SKU, RAM, OS, package/model versions, thread count, cache
state, and context lengths. Randomize configuration order, repeat timed trials,
separate cold start from warm inference, and report uncertainty and throughput.
Use a separate load study for concurrent API claims.

## 6. Manuscript and artifact release

Finalize author metadata and contribution statements, confirm source and dependency
licenses, expand the targeted literature review, and choose the submission format.
Human authors must review all factual and bibliographic claims and disclose AI
assistance appropriately. Do not claim a new retrieval algorithm, state-of-the-art
financial reasoning, peer review, or investment suitability from the current data.

Rebuild all tables from the frozen results, run tests and offline audits on a clean
checkout, verify every cited artifact, and retain the historical pilot separately.
Archive a versioned release when publication is actually authorized. The present
request authorizes pushing the repo and preparing a paper; it does not submit the
manuscript to a venue or repository.

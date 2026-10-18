# Explaining the project in an interview

## A defensible 60-second walkthrough

"I built a reproducible retrieval benchmark over ten semiconductor issuers'
annual reports. The corpus includes more than a thousand pages, not just the
pages I annotated. I compared fixed windows with table-aware chunks, BM25 with
dense and hybrid search, and each method with and without a learned reranker.
I preserved all twelve runs and selected the default using development companies,
then reported performance on seven different companies. My numeric guard binds an
answer to a specific company, period, source-table row, column, and unit. I also
kept an optional local generation audit separate from the main retrieval study."

Read the measured table before citing numbers. Do not imply that every advanced
method improved results. Use the run's actual trade-offs as the interesting part.

## Five things to demonstrate

1. Open `docs/report/index.html`. Switch configuration and inspect a failure.
2. Open `data/questions.jsonl`: show the quote, PDF page URL, and immutable span.
3. Run the source-cited CLI on Micron net loss and Analog Devices' thousands unit.
4. Show `tests/test_reader.py`: a global table lookup cannot fill in a missing
   header or missing row from an incomplete retrieved chunk.
5. Show the numeric mutation audit and explain why its control pass rate is
   conditional on the source cell being parsed correctly.

## Questions you should be able to answer

**Why can BM25 beat a dense model?** Financial questions often contain exact
company names, years, and row labels. A general-purpose embedding model may blur
these distinctions, and table serialization is unlike its training distribution.
Check the actual ablations rather than arguing that one family always wins.

**Why RRF instead of averaging scores?** BM25 scores and cosine similarities have
different scales. Rank fusion avoids a score-calibration parameter, at the cost
of ignoring score margins. The fusion constant and candidate pool are fixed.

**Why not evaluate with an LLM judge?** Numeric values, signs, periods, and units
have exact checks. The small narrative set uses explicit answer strings, with
its limitations disclosed. Independent human semantic review would improve this.

**Why hold out companies?** Repeated metric questions from the same issuer are
correlated. A random question split could make tuning look more general than it
is. The seven-company cluster bootstrap respects that dependence, although the
sample remains too small for broad claims.

**What can the verifier miss?** A parser can place a number under the wrong year,
misread a unit, or lose a label. If the reader and verifier share that representation,
both can agree on the same wrong extraction. The next control would be independent
visual/XBRL checks for sampled cells, not another prompt telling an LLM to be careful.

**Why can citation support be high while accuracy is low?** A quotation can exist
in the source and still be irrelevant to the user's question. Support is measured
conditional on answering; coverage and false refusals expose the abstention cost.

**Why such a small generative model?** It makes CPU reproduction practical and
creates an inspectable control study. Its results are not representative of a
modern large language model. The adapter's strict amount-only contract does not
verify arbitrary prose or complex financial reasoning.

## Honest authorship and resume language

This repository was implemented with an AI coding assistant. The 80 annotations
were AI-authored after source inspection and still need independent human review.
Understand the implementation, review examples visually, and describe your actual
contribution accurately. Do not say you personally hand-labelled all questions.

Suggested project description:

> Built and evaluated a filings QA benchmark across 10 semiconductor issuers,
> comparing 12 retrieval configurations on an 80-question source-anchored dataset;
> implemented deterministic company/year/row/unit checks, company-held-out
> evaluation, and per-query failure audits.

Add a measured improvement only after checking the exact split, baseline,
denominator, and confidence interval in the reference run.

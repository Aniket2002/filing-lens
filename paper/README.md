# Research paper package

**Status: a reproducible research draft, not a submitted or independently validated paper.**

Read the [PDF](manuscript.pdf), [Markdown manuscript](manuscript.md), or
[HTML version](manuscript.html). The draft focuses on candidate retrieval and numeric
evidence in financial QA. It preserves the distinction between the historical
12-configuration experiment and the exploratory retrieval follow-up.

## Build and check

After the normal `uv sync --locked --extra dev --python 3.12` setup:

```bash
uv run python scripts/build_paper.py
uv run python scripts/build_paper.py --check
```

The build is offline: it needs committed results, not models, source PDFs, or a
TeX installation. PyMuPDF is already a project dependency. It first audits all
312 retrieval-iteration predictions, then derives the manuscript tables and
headline numbers from measured artifacts. The original experiment and control
results are separately covered by `scripts/audit_reference.py`.

Edit [manuscript.template.md](manuscript.template.md), not generated outputs.
References are maintained in [references.json](references.json) and exported to
[BibTeX](references.bib). The build rejects unresolved evidence fields and citation
keys. It records source and output hashes in [build.json](build.json); `--check`
detects changed inputs, stale generated text, or modified PDF bytes. PDF byte
identity across renderer versions is not promised.

[corpus-summary.json](corpus-summary.json) is a small page-count snapshot tied to
the frozen canonical extraction hash. To recompute it after fetching and parsing
the unchanged corpus:

```bash
uv run python scripts/build_paper.py --refresh-corpus-summary
```

## Evidence map

| Paper element | Source |
| :-- | :-- |
| Corpus composition | `data/questions.jsonl`, `data/corpus.json`, `paper/corpus-summary.json` |
| Development and test tables | `results/retrieval-v2/{dev,test}/metrics.json`, recomputed by the result audit |
| Bootstrap intervals | `results/retrieval-v2/test/run.json`, recomputed by the result audit |
| Candidate/ranking failure counts | `results/retrieval-v2/test/predictions.jsonl` and canonical gold spans |
| Paired gains, losses, and company sensitivity | [evidence.json](evidence.json), derived from the same predictions |
| Historical reader comparison | `results/reference/metrics.json` and `results/iter1/test/metrics.json` |
| Isolated 500-case control result | `results/controls/predictions.jsonl` and `scripts/audit_reference.py` |
| Limitations and annotation status | `docs/DATA_CARD.md`, `docs/RETRIEVAL_V2.md`, `data/review/pending.csv` |
| Bibliography | Primary publisher/author pages linked in [references.json](references.json) |

The new company-level analysis is descriptive: E60 gains 14 top-five gold hits
and loses two versus F20. Dropping one company at a time leaves a recall gain of
25.0–36.1 percentage points. It is a sensitivity analysis on existing data, not an
additional independent experiment.

## Before submission

The draft can support an empirical systems/failure-analysis discussion. A credible
submission still requires the work in [VALIDATION_PLAN.md](VALIDATION_PLAN.md),
especially independent source/answer review and a genuinely new holdout. The author
list, affiliations, contributions, target venue, and AI-assistance disclosure need
human review. No acceptance, novelty, or publication-readiness claim is implied by
the existence of a compiled PDF.

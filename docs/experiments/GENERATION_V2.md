# Row-assisted generation v2

The original FLAN-T5-small pilot remains in `results/generator/`: zero correct
amounts and zero numeric coverage. The new experiment produces useful verified
numeric outputs on this narrow benchmark while retaining its failures.

## Protocol

One model and one prompt were predeclared in
[`generator-v2-lock.json`](../../data/generator-v2-lock.json):
[`google/flan-t5-base`](https://huggingface.co/google/flan-t5-base), revision
`7bcac572ce56db69c1ea7c8af255c5d7c9672fc2`, greedy CPU decoding with four threads,
512 input tokens and 32 output tokens. No weights were fine-tuned.

Retrieval reuses the development-selected `fixed-bm25-rerank` rankings. The reader
assembles a complete header and metric row only from retrieved top-five chunks on
the same company/page. The model receives that row as all available fiscal-year
and signed-value pairs, the source identity, row label and unit. The question's
expected answer and gold spans are used only for scoring. If the reader cannot
form a verified candidate, the first two retrieved snippets are supplied instead.

Development (15 numeric, 6 negatives) ran first. Test (35 numeric, 14 negatives)
ran once afterward with unchanged model, prompt and implementation. Run files
record the hashes of the implementation, questions, input lock and source rankings.
The runner rejects test if those hashes differ from development and refuses to
overwrite either split. Ten narratives remain outside the experiment.

The test split was inspected in earlier work. These are exploratory results on a
reused benchmark, not a new independent held-out validation. No additional
model/prompt candidates were evaluated in this iteration.

## Results

| Measure | Development | Test |
| :-- | --: | --: |
| Correct raw amounts / all numeric questions | 8/15 (53.3%) | 21/35 (60.0%) |
| Verified correct numeric answers / all numeric questions | 8/15 (53.3%) | 20/35 (57.1%) |
| Verified numeric coverage | 8/15 (53.3%) | 20/35 (57.1%) |
| Numeric questions with a complete reader candidate | 9/15 | 21/35 |
| Correct raw amounts given a complete candidate | 8/9 | 20/21 |
| Exact raw `UNKNOWN` on negatives | 0/6 | 0/14 |
| Guarded refusals on negatives | 6/6 | 14/14 |
| Truncated model inputs | 0/21 | 0/49 |
| Generation + reader p95, cached retrieval excluded | 795 ms | 1,042 ms |

One test amount was correct without a complete retrieved candidate: Analog Devices
revenue, `12,305,539`. It was withheld rather than using its agreement with gold to
bypass the evidence requirement. Broadcom net income was a complete-candidate
failure: the question requested FY2022 (`11,495`), but the model copied FY2023
(`14082`); the guard rejected the wrong-period amount.

All accepted amounts were correct under the frozen numeric scorer. This observation
is based on 20 accepted test answers and shares the parser's source-cell
representation; it is not a general guarantee. Citation support remains
conditional on answering. The model generated no exact `UNKNOWN` refusals, so the
100% guarded negative refusal rate measures the controls, not learned abstention.

## Interpretation and remaining work

This iteration changes model size, prompt, context serialization and table-evidence
assembly together. The improvement over the failed pilot cannot be attributed to
any one change. The extractive table-assembly profile already answers 21/35 numeric
test questions correctly; the generator accepts 20/35. Generation therefore does
not improve the numeric extraction baseline. It demonstrates nonzero model output
correctness under a guard, with an additional model failure and latency cost.

The model's task is deliberately restricted: select/copy an amount from a
reader-selected row. The final prose is rendered deterministically. There is no
claim of free-form narrative synthesis, arithmetic reasoning or general financial
QA. Independent human adjudication, independent source reconciliation, stronger
negatives, fresh questions and a broader generative task remain necessary before
making an enterprise GenAI claim.

A live API smoke check also found query-wording sensitivity: the shortened
"What was AMD's FY2023 net income?" failed to retrieve complete evidence, even
though the model emitted `854`. The guard refused it. The original benchmark
wording retrieves enough evidence. Benchmark performance does not establish
robustness to paraphrases.

## Reproduction and audit

After fetching and parsing the locked corpus:

```bash
uv run python scripts/audit_generator_v2.py --split dev --output results/reproduced/generator-v2
uv run python scripts/audit_generator_v2.py --split test --output results/reproduced/generator-v2
```

The runner reuses the frozen reference rankings and builds no new retrieval index.
For an offline check without weights or PDFs:

```bash
uv run python scripts/audit_generation_results.py
```

The audit recomputes raw correctness, guarded responses, source-row contexts and
aggregate metrics. It checks decisions against the preserved table-assembly
candidates and parsed source fixtures. This validates artifact consistency, not
the visual correctness of the original PDF extraction.

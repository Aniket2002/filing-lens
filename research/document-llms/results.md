# Matched LLM readers after rebuilt retrieval

3,200 outcomes: 50 reused questions x two retrieval views x four variants x four decoding arms x two original FLAN-T5 models. No fresh holdout or broader model family.

Each row reports original numeric accuracy and paired original/rescaled accuracy; both use all questions in the split. No statistical significance is claimed. Pointer coordinate accuracy is retained in the complete metrics, separately from numeric correctness.

| Split | Model | Arm | N | Native original | Neutral original | Native paired scale | Neutral paired scale |
|---|---|---|---:|---:|---:|---:|---:|
| dev | base | native_amount | 15 | 9 | 9 | 0 | 0 |
| dev | base | canonical_amount | 15 | 10 | 5 | 1 | 5 |
| dev | base | native_pointer | 15 | 5 | 5 | 2 | 4 |
| dev | base | canonical_pointer | 15 | 4 | 3 | 2 | 3 |
| dev | small | native_amount | 15 | 0 | 0 | 0 | 0 |
| dev | small | canonical_amount | 15 | 0 | 0 | 0 | 0 |
| dev | small | native_pointer | 15 | 0 | 0 | 0 | 0 |
| dev | small | canonical_pointer | 15 | 0 | 0 | 0 | 0 |
| test | base | native_amount | 35 | 20 | 20 | 0 | 0 |
| test | base | canonical_amount | 35 | 8 | 10 | 1 | 10 |
| test | base | native_pointer | 35 | 17 | 17 | 5 | 16 |
| test | base | canonical_pointer | 35 | 7 | 10 | 2 | 10 |
| test | small | native_amount | 35 | 0 | 0 | 0 | 0 |
| test | small | canonical_amount | 35 | 0 | 0 | 0 | 0 |
| test | small | native_pointer | 35 | 1 | 3 | 1 | 3 |
| test | small | canonical_pointer | 35 | 3 | 3 | 1 | 3 |

The retrieval view is matched within each model/decoding arm; raw chunks remain available to the parser. Absolute scores cannot be compared directly with the original page-expanded pilot. Structure chunking was selected after the earlier symbolic study, so this remains exploratory. All column-reversal and combined-transformation outcomes, failures, raw outputs and prompt hashes are saved in `results/document-llms`.

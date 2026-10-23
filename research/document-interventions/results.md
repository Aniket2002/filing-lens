# Rebuilt document-text retrieval: measured exploratory results

800 outcomes; 16 independently built BM25 indexes; 50 reused questions (15 development, 35 test). No LLM inference.
All 1,275 parsed pages participate. Statement pages are reconstructed from source table fixtures; this is not a general PDF extraction evaluation.

Each entry is a count / split denominator. Candidate and top-5 hits are **source-page** coverage, not span recall. Cell coverage additionally requires a complete retrieved row, period header, metric and unit. Paired correctness requires both original and transformed answers to be numerically correct.

Cell coverage is restricted to annotated source pages; correct answers can also come from duplicate disclosures. Frozen correct uses original top-5 chunk identities with transformed text; it is a diagnostic reference, not rerun retrieval.

| Split | Chunking | View | Transform | N | Page@20 | Page@5 | Cell@5 | Correct | Paired | Lost correct | Frozen correct |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| dev | fixed | native | base | 15 | 15 | 13 | 9 | 11 | 11 | 0 | 11 |
| dev | fixed | native | column_reverse | 15 | 15 | 13 | 9 | 11 | 11 | 0 | 11 |
| dev | fixed | native | unit_rescale | 15 | 12 | 10 | 2 | 2 | 2 | 9 | 11 |
| dev | fixed | native | reverse_and_rescale | 15 | 12 | 10 | 2 | 2 | 2 | 9 | 11 |
| dev | fixed | unit_neutral | base | 15 | 15 | 13 | 9 | 11 | 11 | 0 | 11 |
| dev | fixed | unit_neutral | column_reverse | 15 | 15 | 13 | 9 | 11 | 11 | 0 | 11 |
| dev | fixed | unit_neutral | unit_rescale | 15 | 15 | 13 | 9 | 11 | 11 | 0 | 11 |
| dev | fixed | unit_neutral | reverse_and_rescale | 15 | 15 | 13 | 9 | 11 | 11 | 0 | 11 |
| dev | structure | native | base | 15 | 15 | 14 | 14 | 14 | 14 | 0 | 14 |
| dev | structure | native | column_reverse | 15 | 15 | 14 | 14 | 14 | 14 | 0 | 14 |
| dev | structure | native | unit_rescale | 15 | 13 | 10 | 7 | 7 | 7 | 7 | 14 |
| dev | structure | native | reverse_and_rescale | 15 | 13 | 10 | 7 | 7 | 7 | 7 | 14 |
| dev | structure | unit_neutral | base | 15 | 15 | 14 | 14 | 14 | 14 | 0 | 14 |
| dev | structure | unit_neutral | column_reverse | 15 | 15 | 14 | 14 | 14 | 14 | 0 | 14 |
| dev | structure | unit_neutral | unit_rescale | 15 | 15 | 14 | 14 | 14 | 14 | 0 | 14 |
| dev | structure | unit_neutral | reverse_and_rescale | 15 | 15 | 14 | 14 | 14 | 14 | 0 | 14 |
| test | fixed | native | base | 35 | 35 | 31 | 17 | 20 | 20 | 0 | 20 |
| test | fixed | native | column_reverse | 35 | 35 | 31 | 17 | 20 | 20 | 0 | 20 |
| test | fixed | native | unit_rescale | 35 | 30 | 21 | 5 | 5 | 5 | 15 | 20 |
| test | fixed | native | reverse_and_rescale | 35 | 30 | 21 | 5 | 5 | 5 | 15 | 20 |
| test | fixed | unit_neutral | base | 35 | 35 | 33 | 19 | 22 | 22 | 0 | 22 |
| test | fixed | unit_neutral | column_reverse | 35 | 35 | 33 | 19 | 22 | 22 | 0 | 22 |
| test | fixed | unit_neutral | unit_rescale | 35 | 35 | 33 | 19 | 22 | 22 | 0 | 22 |
| test | fixed | unit_neutral | reverse_and_rescale | 35 | 35 | 33 | 19 | 22 | 22 | 0 | 22 |
| test | structure | native | base | 35 | 35 | 32 | 30 | 30 | 30 | 0 | 30 |
| test | structure | native | column_reverse | 35 | 35 | 32 | 30 | 30 | 30 | 0 | 30 |
| test | structure | native | unit_rescale | 35 | 30 | 17 | 13 | 13 | 13 | 17 | 30 |
| test | structure | native | reverse_and_rescale | 35 | 30 | 17 | 13 | 13 | 13 | 17 | 30 |
| test | structure | unit_neutral | base | 35 | 35 | 33 | 32 | 33 | 33 | 0 | 33 |
| test | structure | unit_neutral | column_reverse | 35 | 35 | 33 | 32 | 33 | 33 | 0 | 33 |
| test | structure | unit_neutral | unit_rescale | 35 | 35 | 33 | 32 | 33 | 33 | 0 | 33 |
| test | structure | unit_neutral | reverse_and_rescale | 35 | 35 | 33 | 32 | 33 | 33 | 0 | 33 |

These results cannot be compared as an improvement over the FLAN-T5 pilot: retrieval, evidence presentation and the reader all differ. The symbolic reader is deliberately limited to five metric families and explicit question units. No configuration is selected using these test results.

## Index sizes

| Chunking | View | Transform | Chunks |
|---|---|---|---:|
| fixed | native | base | 5732 |
| fixed | unit_neutral | base | 5732 |
| structure | native | base | 6383 |
| structure | unit_neutral | base | 6383 |
| fixed | native | column_reverse | 5732 |
| fixed | unit_neutral | column_reverse | 5732 |
| structure | native | column_reverse | 6383 |
| structure | unit_neutral | column_reverse | 6383 |
| fixed | native | unit_rescale | 5732 |
| fixed | unit_neutral | unit_rescale | 5732 |
| structure | native | unit_rescale | 6383 |
| structure | unit_neutral | unit_rescale | 6383 |
| fixed | native | reverse_and_rescale | 5732 |
| fixed | unit_neutral | reverse_and_rescale | 5732 |
| structure | native | reverse_and_rescale | 6383 |
| structure | unit_neutral | reverse_and_rescale | 6383 |

## Every incorrect outcome

Failures retain query-level identifiers; omitted rows are correct, not filtered failures.

| Question | Chunking | View | Transform | Status | Page@5 | Cell@5 |
|---|---|---|---|---|---|---|
| adi-numeric-05 | fixed | native | base | missing_evidence | True | False |
| amd-numeric-05 | fixed | native | base | missing_evidence | False | False |
| avgo-numeric-02 | fixed | native | base | missing_evidence | True | False |
| avgo-numeric-03 | fixed | native | base | missing_evidence | False | False |
| avgo-numeric-05 | fixed | native | base | missing_evidence | True | False |
| intc-numeric-03 | fixed | native | base | missing_evidence | False | False |
| intc-numeric-05 | fixed | native | base | missing_evidence | True | False |
| mchp-numeric-05 | fixed | native | base | missing_evidence | True | False |
| mu-numeric-02 | fixed | native | base | missing_evidence | True | False |
| mu-numeric-05 | fixed | native | base | missing_evidence | True | False |
| nvda-numeric-05 | fixed | native | base | missing_evidence | True | False |
| nxpi-numeric-02 | fixed | native | base | missing_evidence | True | False |
| nxpi-numeric-05 | fixed | native | base | missing_evidence | True | False |
| qcom-numeric-01 | fixed | native | base | missing_evidence | False | False |
| qcom-numeric-02 | fixed | native | base | missing_evidence | True | False |
| qcom-numeric-03 | fixed | native | base | missing_evidence | False | False |
| qcom-numeric-05 | fixed | native | base | missing_evidence | True | False |
| txn-numeric-04 | fixed | native | base | missing_evidence | True | False |
| txn-numeric-05 | fixed | native | base | missing_evidence | True | False |
| adi-numeric-05 | fixed | unit_neutral | base | missing_evidence | True | False |
| amd-numeric-05 | fixed | unit_neutral | base | missing_evidence | False | False |
| avgo-numeric-02 | fixed | unit_neutral | base | missing_evidence | True | False |
| avgo-numeric-03 | fixed | unit_neutral | base | missing_evidence | False | False |
| avgo-numeric-05 | fixed | unit_neutral | base | missing_evidence | True | False |
| intc-numeric-03 | fixed | unit_neutral | base | missing_evidence | False | False |
| intc-numeric-05 | fixed | unit_neutral | base | missing_evidence | True | False |
| mchp-numeric-05 | fixed | unit_neutral | base | missing_evidence | True | False |
| mu-numeric-05 | fixed | unit_neutral | base | missing_evidence | True | False |
| nvda-numeric-05 | fixed | unit_neutral | base | missing_evidence | True | False |
| nxpi-numeric-02 | fixed | unit_neutral | base | missing_evidence | True | False |
| nxpi-numeric-05 | fixed | unit_neutral | base | missing_evidence | True | False |
| qcom-numeric-01 | fixed | unit_neutral | base | missing_evidence | False | False |
| qcom-numeric-02 | fixed | unit_neutral | base | missing_evidence | True | False |
| qcom-numeric-05 | fixed | unit_neutral | base | missing_evidence | True | False |
| txn-numeric-04 | fixed | unit_neutral | base | missing_evidence | True | False |
| txn-numeric-05 | fixed | unit_neutral | base | missing_evidence | True | False |
| adi-numeric-03 | structure | native | base | missing_evidence | True | False |
| avgo-numeric-03 | structure | native | base | missing_evidence | False | False |
| intc-numeric-03 | structure | native | base | missing_evidence | False | False |
| nxpi-numeric-03 | structure | native | base | missing_evidence | True | False |
| qcom-numeric-01 | structure | native | base | missing_evidence | False | False |
| qcom-numeric-03 | structure | native | base | missing_evidence | False | False |
| avgo-numeric-03 | structure | unit_neutral | base | missing_evidence | False | False |
| intc-numeric-03 | structure | unit_neutral | base | missing_evidence | False | False |
| qcom-numeric-01 | structure | unit_neutral | base | missing_evidence | False | False |
| adi-numeric-05 | fixed | native | column_reverse | missing_evidence | True | False |
| amd-numeric-05 | fixed | native | column_reverse | missing_evidence | False | False |
| avgo-numeric-02 | fixed | native | column_reverse | missing_evidence | True | False |
| avgo-numeric-03 | fixed | native | column_reverse | missing_evidence | False | False |
| avgo-numeric-05 | fixed | native | column_reverse | missing_evidence | True | False |
| intc-numeric-03 | fixed | native | column_reverse | missing_evidence | False | False |
| intc-numeric-05 | fixed | native | column_reverse | missing_evidence | True | False |
| mchp-numeric-05 | fixed | native | column_reverse | missing_evidence | True | False |
| mu-numeric-02 | fixed | native | column_reverse | missing_evidence | True | False |
| mu-numeric-05 | fixed | native | column_reverse | missing_evidence | True | False |
| nvda-numeric-05 | fixed | native | column_reverse | missing_evidence | True | False |
| nxpi-numeric-02 | fixed | native | column_reverse | missing_evidence | True | False |
| nxpi-numeric-05 | fixed | native | column_reverse | missing_evidence | True | False |
| qcom-numeric-01 | fixed | native | column_reverse | missing_evidence | False | False |
| qcom-numeric-02 | fixed | native | column_reverse | missing_evidence | True | False |
| qcom-numeric-03 | fixed | native | column_reverse | missing_evidence | False | False |
| qcom-numeric-05 | fixed | native | column_reverse | missing_evidence | True | False |
| txn-numeric-04 | fixed | native | column_reverse | missing_evidence | True | False |
| txn-numeric-05 | fixed | native | column_reverse | missing_evidence | True | False |
| adi-numeric-05 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| amd-numeric-05 | fixed | unit_neutral | column_reverse | missing_evidence | False | False |
| avgo-numeric-02 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| avgo-numeric-03 | fixed | unit_neutral | column_reverse | missing_evidence | False | False |
| avgo-numeric-05 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| intc-numeric-03 | fixed | unit_neutral | column_reverse | missing_evidence | False | False |
| intc-numeric-05 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| mchp-numeric-05 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| mu-numeric-05 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| nvda-numeric-05 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| nxpi-numeric-02 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| nxpi-numeric-05 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| qcom-numeric-01 | fixed | unit_neutral | column_reverse | missing_evidence | False | False |
| qcom-numeric-02 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| qcom-numeric-05 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| txn-numeric-04 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| txn-numeric-05 | fixed | unit_neutral | column_reverse | missing_evidence | True | False |
| adi-numeric-03 | structure | native | column_reverse | missing_evidence | True | False |
| avgo-numeric-03 | structure | native | column_reverse | missing_evidence | False | False |
| intc-numeric-03 | structure | native | column_reverse | missing_evidence | False | False |
| nxpi-numeric-03 | structure | native | column_reverse | missing_evidence | True | False |
| qcom-numeric-01 | structure | native | column_reverse | missing_evidence | False | False |
| qcom-numeric-03 | structure | native | column_reverse | missing_evidence | False | False |
| avgo-numeric-03 | structure | unit_neutral | column_reverse | missing_evidence | False | False |
| intc-numeric-03 | structure | unit_neutral | column_reverse | missing_evidence | False | False |
| qcom-numeric-01 | structure | unit_neutral | column_reverse | missing_evidence | False | False |
| adi-numeric-01 | fixed | native | unit_rescale | missing_evidence | False | False |
| adi-numeric-02 | fixed | native | unit_rescale | missing_evidence | False | False |
| adi-numeric-03 | fixed | native | unit_rescale | missing_evidence | False | False |
| adi-numeric-04 | fixed | native | unit_rescale | missing_evidence | False | False |
| adi-numeric-05 | fixed | native | unit_rescale | missing_evidence | True | False |
| amd-numeric-01 | fixed | native | unit_rescale | missing_evidence | True | False |
| amd-numeric-02 | fixed | native | unit_rescale | missing_evidence | True | False |
| amd-numeric-03 | fixed | native | unit_rescale | missing_evidence | True | False |
| amd-numeric-04 | fixed | native | unit_rescale | missing_evidence | False | False |
| amd-numeric-05 | fixed | native | unit_rescale | missing_evidence | False | False |
| avgo-numeric-01 | fixed | native | unit_rescale | missing_evidence | False | False |
| avgo-numeric-02 | fixed | native | unit_rescale | missing_evidence | True | False |
| avgo-numeric-03 | fixed | native | unit_rescale | missing_evidence | False | False |
| avgo-numeric-04 | fixed | native | unit_rescale | missing_evidence | False | False |
| avgo-numeric-05 | fixed | native | unit_rescale | missing_evidence | True | False |
| intc-numeric-02 | fixed | native | unit_rescale | missing_evidence | True | False |
| intc-numeric-03 | fixed | native | unit_rescale | missing_evidence | False | False |
| intc-numeric-04 | fixed | native | unit_rescale | missing_evidence | False | False |
| intc-numeric-05 | fixed | native | unit_rescale | missing_evidence | True | False |
| mchp-numeric-01 | fixed | native | unit_rescale | missing_evidence | True | False |
| mchp-numeric-02 | fixed | native | unit_rescale | missing_evidence | True | False |
| mchp-numeric-05 | fixed | native | unit_rescale | missing_evidence | True | False |
| mu-numeric-01 | fixed | native | unit_rescale | missing_evidence | True | False |
| mu-numeric-02 | fixed | native | unit_rescale | missing_evidence | True | False |
| mu-numeric-03 | fixed | native | unit_rescale | missing_evidence | False | False |
| mu-numeric-04 | fixed | native | unit_rescale | missing_evidence | False | False |
| mu-numeric-05 | fixed | native | unit_rescale | missing_evidence | True | False |
| nvda-numeric-01 | fixed | native | unit_rescale | missing_evidence | True | False |
| nvda-numeric-02 | fixed | native | unit_rescale | missing_evidence | True | False |
| nvda-numeric-04 | fixed | native | unit_rescale | missing_evidence | False | False |
| nvda-numeric-05 | fixed | native | unit_rescale | missing_evidence | True | False |
| nxpi-numeric-02 | fixed | native | unit_rescale | missing_evidence | True | False |
| nxpi-numeric-03 | fixed | native | unit_rescale | missing_evidence | False | False |
| nxpi-numeric-04 | fixed | native | unit_rescale | missing_evidence | False | False |
| nxpi-numeric-05 | fixed | native | unit_rescale | missing_evidence | True | False |
| qcom-numeric-01 | fixed | native | unit_rescale | missing_evidence | True | False |
| qcom-numeric-02 | fixed | native | unit_rescale | missing_evidence | True | False |
| qcom-numeric-03 | fixed | native | unit_rescale | missing_evidence | False | False |
| qcom-numeric-04 | fixed | native | unit_rescale | missing_evidence | False | False |
| qcom-numeric-05 | fixed | native | unit_rescale | missing_evidence | True | False |
| txn-numeric-02 | fixed | native | unit_rescale | missing_evidence | True | False |
| txn-numeric-04 | fixed | native | unit_rescale | missing_evidence | False | False |
| txn-numeric-05 | fixed | native | unit_rescale | missing_evidence | True | False |
| adi-numeric-05 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| amd-numeric-05 | fixed | unit_neutral | unit_rescale | missing_evidence | False | False |
| avgo-numeric-02 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| avgo-numeric-03 | fixed | unit_neutral | unit_rescale | missing_evidence | False | False |
| avgo-numeric-05 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| intc-numeric-03 | fixed | unit_neutral | unit_rescale | missing_evidence | False | False |
| intc-numeric-05 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| mchp-numeric-05 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| mu-numeric-05 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| nvda-numeric-05 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| nxpi-numeric-02 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| nxpi-numeric-05 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| qcom-numeric-01 | fixed | unit_neutral | unit_rescale | missing_evidence | False | False |
| qcom-numeric-02 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| qcom-numeric-05 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| txn-numeric-04 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| txn-numeric-05 | fixed | unit_neutral | unit_rescale | missing_evidence | True | False |
| adi-numeric-01 | structure | native | unit_rescale | missing_evidence | False | False |
| adi-numeric-02 | structure | native | unit_rescale | missing_evidence | False | False |
| adi-numeric-03 | structure | native | unit_rescale | missing_evidence | False | False |
| adi-numeric-04 | structure | native | unit_rescale | missing_evidence | False | False |
| amd-numeric-01 | structure | native | unit_rescale | missing_evidence | True | False |
| amd-numeric-03 | structure | native | unit_rescale | missing_evidence | False | False |
| amd-numeric-04 | structure | native | unit_rescale | missing_evidence | False | False |
| avgo-numeric-01 | structure | native | unit_rescale | missing_evidence | False | False |
| avgo-numeric-02 | structure | native | unit_rescale | missing_evidence | False | False |
| avgo-numeric-03 | structure | native | unit_rescale | missing_evidence | False | False |
| avgo-numeric-04 | structure | native | unit_rescale | missing_evidence | False | False |
| intc-numeric-01 | structure | native | unit_rescale | missing_evidence | True | False |
| intc-numeric-03 | structure | native | unit_rescale | missing_evidence | False | False |
| intc-numeric-04 | structure | native | unit_rescale | missing_evidence | False | False |
| mchp-numeric-01 | structure | native | unit_rescale | missing_evidence | True | False |
| mchp-numeric-03 | structure | native | unit_rescale | missing_evidence | False | False |
| mchp-numeric-04 | structure | native | unit_rescale | missing_evidence | False | False |
| mu-numeric-01 | structure | native | unit_rescale | missing_evidence | True | False |
| mu-numeric-03 | structure | native | unit_rescale | missing_evidence | False | False |
| mu-numeric-04 | structure | native | unit_rescale | missing_evidence | False | False |
| nvda-numeric-01 | structure | native | unit_rescale | missing_evidence | True | False |
| nvda-numeric-04 | structure | native | unit_rescale | missing_evidence | False | False |
| nxpi-numeric-01 | structure | native | unit_rescale | missing_evidence | False | False |
| nxpi-numeric-03 | structure | native | unit_rescale | missing_evidence | False | False |
| nxpi-numeric-04 | structure | native | unit_rescale | missing_evidence | False | False |
| qcom-numeric-01 | structure | native | unit_rescale | missing_evidence | False | False |
| qcom-numeric-03 | structure | native | unit_rescale | missing_evidence | False | False |
| qcom-numeric-04 | structure | native | unit_rescale | missing_evidence | False | False |
| txn-numeric-01 | structure | native | unit_rescale | missing_evidence | True | False |
| txn-numeric-04 | structure | native | unit_rescale | missing_evidence | True | False |
| avgo-numeric-03 | structure | unit_neutral | unit_rescale | missing_evidence | False | False |
| intc-numeric-03 | structure | unit_neutral | unit_rescale | missing_evidence | False | False |
| qcom-numeric-01 | structure | unit_neutral | unit_rescale | missing_evidence | False | False |
| adi-numeric-01 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| adi-numeric-02 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| adi-numeric-03 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| adi-numeric-04 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| adi-numeric-05 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| amd-numeric-01 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| amd-numeric-02 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| amd-numeric-03 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| amd-numeric-04 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| amd-numeric-05 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| avgo-numeric-01 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| avgo-numeric-02 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| avgo-numeric-03 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| avgo-numeric-04 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| avgo-numeric-05 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| intc-numeric-02 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| intc-numeric-03 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| intc-numeric-04 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| intc-numeric-05 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| mchp-numeric-01 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| mchp-numeric-02 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| mchp-numeric-05 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| mu-numeric-01 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| mu-numeric-02 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| mu-numeric-03 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| mu-numeric-04 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| mu-numeric-05 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| nvda-numeric-01 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| nvda-numeric-02 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| nvda-numeric-04 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| nvda-numeric-05 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| nxpi-numeric-02 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| nxpi-numeric-03 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| nxpi-numeric-04 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| nxpi-numeric-05 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| qcom-numeric-01 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| qcom-numeric-02 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| qcom-numeric-03 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| qcom-numeric-04 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| qcom-numeric-05 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| txn-numeric-02 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| txn-numeric-04 | fixed | native | reverse_and_rescale | missing_evidence | False | False |
| txn-numeric-05 | fixed | native | reverse_and_rescale | missing_evidence | True | False |
| adi-numeric-05 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| amd-numeric-05 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | False | False |
| avgo-numeric-02 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| avgo-numeric-03 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | False | False |
| avgo-numeric-05 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| intc-numeric-03 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | False | False |
| intc-numeric-05 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| mchp-numeric-05 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| mu-numeric-05 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| nvda-numeric-05 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| nxpi-numeric-02 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| nxpi-numeric-05 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| qcom-numeric-01 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | False | False |
| qcom-numeric-02 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| qcom-numeric-05 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| txn-numeric-04 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| txn-numeric-05 | fixed | unit_neutral | reverse_and_rescale | missing_evidence | True | False |
| adi-numeric-01 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| adi-numeric-02 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| adi-numeric-03 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| adi-numeric-04 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| amd-numeric-01 | structure | native | reverse_and_rescale | missing_evidence | True | False |
| amd-numeric-03 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| amd-numeric-04 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| avgo-numeric-01 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| avgo-numeric-02 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| avgo-numeric-03 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| avgo-numeric-04 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| intc-numeric-01 | structure | native | reverse_and_rescale | missing_evidence | True | False |
| intc-numeric-03 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| intc-numeric-04 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| mchp-numeric-01 | structure | native | reverse_and_rescale | missing_evidence | True | False |
| mchp-numeric-03 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| mchp-numeric-04 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| mu-numeric-01 | structure | native | reverse_and_rescale | missing_evidence | True | False |
| mu-numeric-03 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| mu-numeric-04 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| nvda-numeric-01 | structure | native | reverse_and_rescale | missing_evidence | True | False |
| nvda-numeric-04 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| nxpi-numeric-01 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| nxpi-numeric-03 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| nxpi-numeric-04 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| qcom-numeric-01 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| qcom-numeric-03 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| qcom-numeric-04 | structure | native | reverse_and_rescale | missing_evidence | False | False |
| txn-numeric-01 | structure | native | reverse_and_rescale | missing_evidence | True | False |
| txn-numeric-04 | structure | native | reverse_and_rescale | missing_evidence | True | False |
| avgo-numeric-03 | structure | unit_neutral | reverse_and_rescale | missing_evidence | False | False |
| intc-numeric-03 | structure | unit_neutral | reverse_and_rescale | missing_evidence | False | False |
| qcom-numeric-01 | structure | unit_neutral | reverse_and_rescale | missing_evidence | False | False |

# Financial evidence equivariance: measured pilot results

Canonical-pointer paired usable accuracy is 37.1%, compared with 14.3% for native-amount and 40.0% for canonical-amount decoding. The primary difference is +22.9 percentage points (descriptive 95% interval +5.7 to +40.0). The small-model contrast is +5.7 points (+0.0 to +17.1). These are pilot estimates on reused companies, not external validation. Canonical-amount matches or exceeds canonical-pointer on the primary condition; this experiment does not establish an additional benefit from pointer output. Original-input accuracy is 62.9% for native-amount versus 37.1% for canonical-pointer. Evidence-removal refusal accuracy is 0.0% for every base-model arm. Preserving-transform robustness therefore cannot stand in for ordinary accuracy or sensitivity to missing support.

4,800 outcomes; 2,252 distinct-prompt inference calls; 600 cases derived from 50 original questions. Synthetic variants are dependent.

## Retrieved evidence, test companies

| Model | Arm | Base % | Scale % | Reverse % | Both % | Rebind % | Removal % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| base | Native amount | 62.9 | 14.3 | 34.3 | 11.4 | 57.1 | 0.0 |
| base | Canonical amount | 40.0 | 40.0 | 40.0 | 40.0 | 42.9 | 0.0 |
| base | Native pointer | 37.1 | 31.4 | 20.0 | 20.0 | 34.3 | 0.0 |
| base | Canonical pointer | 37.1 | 37.1 | 37.1 | 37.1 | 40.0 | 0.0 |
| small | Native amount | 0.0 | 0.0 | 0.0 | 0.0 | 2.9 | 17.1 |
| small | Canonical amount | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 28.6 |
| small | Native pointer | 8.6 | 8.6 | 2.9 | 2.9 | 2.9 | 17.1 |
| small | Canonical pointer | 5.7 | 5.7 | 5.7 | 5.7 | 8.6 | 17.1 |

## Oracle-page evidence, test companies

| Model | Arm | Base % | Scale % | Reverse % | Both % | Rebind % | Removal % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| base | Native amount | 68.6 | 14.3 | 31.4 | 11.4 | 51.4 | 0.0 |
| base | Canonical amount | 42.9 | 42.9 | 42.9 | 42.9 | 42.9 | 0.0 |
| base | Native pointer | 37.1 | 34.3 | 17.1 | 17.1 | 37.1 | 0.0 |
| base | Canonical pointer | 40.0 | 40.0 | 40.0 | 40.0 | 40.0 | 0.0 |
| small | Native amount | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 22.9 |
| small | Canonical amount | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 25.7 |
| small | Native pointer | 11.4 | 8.6 | 2.9 | 2.9 | 2.9 | 20.0 |
| small | Canonical pointer | 2.9 | 2.9 | 2.9 | 2.9 | 5.7 | 20.0 |

## Pointer coordinate diagnostics

| Model | Arm | Variant | Numeric % | Coordinate % | Invalid % |
| --- | --- | --- | --- | --- | --- |
| base | native pointer | base | 37.1 | 37.1 | 28.6 |
| base | native pointer | period rebind | 34.3 | 34.3 | 22.9 |
| base | canonical pointer | base | 37.1 | 37.1 | 22.9 |
| base | canonical pointer | period rebind | 40.0 | 40.0 | 25.7 |
| small | native pointer | base | 8.6 | 8.6 | 65.7 |
| small | native pointer | period rebind | 2.9 | 2.9 | 62.9 |
| small | canonical pointer | base | 5.7 | 5.7 | 68.6 |
| small | canonical pointer | period rebind | 8.6 | 8.6 | 60.0 |

Percentages; 35 source questions per row. Scale/reverse/both require both the base and transformed answers to be correct numeric outputs. Removal measures explicit UNKNOWN on evidence deletion. Full metrics include coverage and invalid outputs.

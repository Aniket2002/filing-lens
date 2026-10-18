# Source visual spot checks

On 18 October 2026, three original PDF pages were rendered and inspected for
statement headings, year columns, units, and the twelve numeric annotations below.
This AI-assisted visual spot check is **not independent human adjudication** or a
complete extraction audit. The original PDF hashes are recorded in
`data/source-lock.json`.

| Original PDF page | Visually checked values | Why this page matters |
| :-- | :-- | :-- |
| [Micron, PDF p57](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NYSE_MU_2023.pdf#page=57) | FY2023 revenue 15,540; R&D 3,114; net loss (5,833), all USD millions; diluted loss per share (5.34) USD | Parentheses mean negative; the diluted share count of 1,093 is a different row from diluted EPS. |
| [Analog Devices, PDF p45](https://www.annualreports.com/HostedData/AnnualReportArchive/a/NASDAQ_ADI_2023.pdf#page=45) | FY2023 revenue 12,305,539; net income 3,314,579; FY2022 R&D 1,700,518, all USD thousands; FY2023 diluted EPS 6.55 USD | The aggregate statement uses thousands, while EPS retains per-share dollars. |
| [NXP, PDF p61](https://www.annualreports.com/HostedData/AnnualReportArchive/n/NASDAQ_NXPI_2023.pdf#page=61) | FY2023 revenue 13,276; consolidated net income 2,822; signed R&D (2,418), all USD millions; diluted EPS 10.70 USD | Consolidated net income differs from income attributable to stockholders (2,797); diluted EPS differs from the share count 261,370. |

The figures agreed with the source-anchored annotations. Assets, other issuers,
and qualitative/unanswerable labels were not covered by these three visual checks.
The source-cell verifier still shares the extraction representation with the reader;
the spot checks do not remove that common failure mode.

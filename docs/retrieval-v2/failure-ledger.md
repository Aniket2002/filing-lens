# Retrieval case ledger

Selected: `structure-entity-60`.

## Recovered evidence

### adi-numeric-02

What net income did Analog Devices report for FY2023 in USD thousands?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **1** → final rank **1**.

[Gold source: ADI-2023, PDF page 45](https://www.annualreports.com/HostedData/AnnualReportArchive/a/NASDAQ_ADI_2023.pdf#page=45)

### adi-numeric-03

What FY2022 R&D expense is shown in Analog Devices' FY2023 report, in USD thousands?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **55** → final rank **2**.

[Gold source: ADI-2023, PDF page 45](https://www.annualreports.com/HostedData/AnnualReportArchive/a/NASDAQ_ADI_2023.pdf#page=45)

### adi-numeric-04

What were Analog Devices' total assets at FY2023 year end in USD thousands?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **5** → final rank **3**.

[Gold source: ADI-2023, PDF page 47](https://www.annualreports.com/HostedData/AnnualReportArchive/a/NASDAQ_ADI_2023.pdf#page=47)

### avgo-numeric-02

What FY2022 net income appears in Broadcom's FY2023 report (USD millions)?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **2** → final rank **1**.

[Gold source: AVGO-2023, PDF page 53](https://www.annualreports.com/HostedData/AnnualReportArchive/b/NASDAQ_AVGO_2023.pdf#page=53)

### avgo-numeric-03

How much was Broadcom's FY2023 research and development expense in USD millions?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **9** → final rank **5**.

[Gold source: AVGO-2023, PDF page 53](https://www.annualreports.com/HostedData/AnnualReportArchive/b/NASDAQ_AVGO_2023.pdf#page=53)

### mchp-numeric-02

What was Microchip Technology's FY2023 net income in USD millions?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **6** → final rank **2**.

[Gold source: MCHP-2023, PDF page 67](https://ir.microchip.com/sec-filings/all-sec-filings/content/0000827054-23-000080/0000827054-23-000080.pdf#page=67)

### mu-narrative-01

Which two memory technologies are the focus of Micron's development efforts in the FY2023 report?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **2** → final rank **1**.

[Gold source: MU-2023, PDF page 14](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NYSE_MU_2023.pdf#page=14)

### mu-numeric-04

At its FY2023 year end, what total assets did Micron report in USD millions?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **7** → final rank **1**.

[Gold source: MU-2023, PDF page 59](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NYSE_MU_2023.pdf#page=59)

### mu-numeric-05

What signed diluted earnings or loss per share did Micron report for FY2023?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **1** → final rank **2**.

[Gold source: MU-2023, PDF page 57](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NYSE_MU_2023.pdf#page=57)

### nxpi-numeric-04

What were NXP Semiconductors' total assets at the FY2023 year end, in USD millions?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **39** → final rank **1**.

[Gold source: NXPI-2023, PDF page 63](https://www.annualreports.com/HostedData/AnnualReportArchive/n/NASDAQ_NXPI_2023.pdf#page=63)

### qcom-numeric-03

What was Qualcomm's FY2022 R&D expense in USD millions, as presented in its FY2023 filing?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **57** → final rank **5**.

[Gold source: QCOM-2023, PDF page 59](https://www.annualreports.com/HostedData/AnnualReportArchive/q/NASDAQ_QCOM_2023.pdf#page=59)

### qcom-numeric-04

What total assets did Qualcomm disclose at its FY2023 year end (USD millions)?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **3** → final rank **2**.

[Gold source: QCOM-2023, PDF page 58](https://www.annualreports.com/HostedData/AnnualReportArchive/q/NASDAQ_QCOM_2023.pdf#page=58)

### txn-numeric-02

What was Texas Instruments' net income in FY2023, in USD millions?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **1** → final rank **1**.

[Gold source: TXN-2023, PDF page 25](https://www.annualreports.com/HostedData/AnnualReportArchive/t/NASDAQ_TXN_2023.pdf#page=25)

### txn-numeric-04

What was the total asset balance for Texas Instruments at FY2023 year end (USD millions)?

Retrieval: `hit_at_5`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **15** → final rank **1**.

[Gold source: TXN-2023, PDF page 27](https://www.annualreports.com/HostedData/AnnualReportArchive/t/NASDAQ_TXN_2023.pdf#page=27)

## Remaining retrieval or answer failures

### adi-numeric-01

What was Analog Devices' FY2023 revenue, keeping the statement's USD thousands unit?

Retrieval: `candidate_miss`. Answer correct: **False**. Evidence gate: `no_complete_table_evidence_in_top_k`.

[Gold source: ADI-2023, PDF page 45](https://www.annualreports.com/HostedData/AnnualReportArchive/a/NASDAQ_ADI_2023.pdf#page=45)

### avgo-narrative-01

According to Broadcom's FY2023 report, when did it complete the acquisition of VMware?

Retrieval: `hit_at_5`. Answer correct: **False**. Evidence gate: `no_narrative_evidence_above_overlap_threshold`.

Candidate rank **1** → final rank **1**.

[Gold source: AVGO-2023, PDF page 39](https://www.annualreports.com/HostedData/AnnualReportArchive/b/NASDAQ_AVGO_2023.pdf#page=39)

### mu-numeric-02

What signed amount appears as Micron's net income or loss in FY2023 (USD millions)?

Retrieval: `ranking_miss`. Answer correct: **True**. Evidence gate: `None`.

Candidate rank **1** → final rank **11**.

[Gold source: MU-2023, PDF page 57](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NYSE_MU_2023.pdf#page=57)

### nxpi-numeric-01

What was NXP Semiconductors' FY2023 revenue in USD millions?

Retrieval: `ranking_miss`. Answer correct: **False**. Evidence gate: `no_complete_table_evidence_in_top_k`.

Candidate rank **25** → final rank **8**.

[Gold source: NXPI-2023, PDF page 61](https://www.annualreports.com/HostedData/AnnualReportArchive/n/NASDAQ_NXPI_2023.pdf#page=61)

### nxpi-numeric-02

What consolidated net income before non-controlling interests did NXP report for FY2023 (USD millions)?

Retrieval: `ranking_miss`. Answer correct: **False**. Evidence gate: `no_complete_table_evidence_in_top_k`.

Candidate rank **9** → final rank **7**.

[Gold source: NXPI-2023, PDF page 61](https://www.annualreports.com/HostedData/AnnualReportArchive/n/NASDAQ_NXPI_2023.pdf#page=61)

### nxpi-numeric-03

What signed R&D amount is displayed in NXP's FY2023 statement of operations (USD millions)?

Retrieval: `candidate_miss`. Answer correct: **False**. Evidence gate: `no_complete_table_evidence_in_top_k`.

[Gold source: NXPI-2023, PDF page 61](https://www.annualreports.com/HostedData/AnnualReportArchive/n/NASDAQ_NXPI_2023.pdf#page=61)

### qcom-narrative-01

Through which two segments does Qualcomm primarily conduct business, according to its FY2023 report?

Retrieval: `hit_at_5`. Answer correct: **False**. Evidence gate: `None`.

Candidate rank **2** → final rank **4**.

[Gold source: QCOM-2023, PDF page 11](https://www.annualreports.com/HostedData/AnnualReportArchive/q/NASDAQ_QCOM_2023.pdf#page=11)

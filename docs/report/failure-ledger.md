# Failure ledger

Development-selected configuration: `fixed-bm25-rerank`.

Counts: gold absent from top five: 14, reader or evidence gate failure: 10, unsupported answer: 3.

## adi-numeric-01 · gold absent from top five

What was Analog Devices' FY2023 revenue, keeping the statement's USD thousands unit?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [ADI-2023, PDF p45](https://www.annualreports.com/HostedData/AnnualReportArchive/a/NASDAQ_ADI_2023.pdf#page=45) — Revenue | 12,305,539 | 12,013,953 | 7,318,286

## adi-numeric-02 · gold absent from top five

What net income did Analog Devices report for FY2023 in USD thousands?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [ADI-2023, PDF p45](https://www.annualreports.com/HostedData/AnnualReportArchive/a/NASDAQ_ADI_2023.pdf#page=45) — Net income | 3,314,579 | 2,748,561 | 1,390,422

## adi-numeric-03 · gold absent from top five

What FY2022 R&D expense is shown in Analog Devices' FY2023 report, in USD thousands?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [ADI-2023, PDF p45](https://www.annualreports.com/HostedData/AnnualReportArchive/a/NASDAQ_ADI_2023.pdf#page=45) — Research and development | 1,660,194 | 1,700,518 | 1,296,126

## adi-numeric-04 · gold absent from top five

What were Analog Devices' total assets at FY2023 year end in USD thousands?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [ADI-2023, PDF p47](https://www.annualreports.com/HostedData/AnnualReportArchive/a/NASDAQ_ADI_2023.pdf#page=47) — TOTAL ASSETS | 48,794,478 | 50,302,350

## adi-numeric-05 · reader or evidence gate failure

What diluted earnings per common share did Analog Devices report in FY2023?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [ADI-2023, PDF p45](https://www.annualreports.com/HostedData/AnnualReportArchive/a/NASDAQ_ADI_2023.pdf#page=45) — Diluted earnings per common share | 6.55 | 5.25 | 3.46

## adi-unanswerable-02 · unsupported answer

What was Analog Devices' net interest margin in FY2023?

Observed: The increase in operating income in fiscal 2023 as compared to fiscal 2022 was primarily the result of a $344.7 million increase in gross margin, a $113.8 million decrease in special charges, net, a $53.0 million decrease in amortization expenses and a $40.3 million decrease in R&D expenses, partially offset by a $7.4 million increase in SMG&A expenses, as more fully described above under the headings Gross Margin, Special Charges, Net, Amortization of Intangibles, Research and Development (R&D) and Selling, Marketing, General and Administrative (SMG&A).

Gate: `None`

Expected refusal: Net interest margin is not a disclosed Analog Devices metric.

## avgo-narrative-01 · reader or evidence gate failure

According to Broadcom's FY2023 report, when did it complete the acquisition of VMware?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_narrative_evidence_above_overlap_threshold`

Gold: [AVGO-2023, PDF p39](https://www.annualreports.com/HostedData/AnnualReportArchive/b/NASDAQ_AVGO_2023.pdf#page=39) — On November 22, 2023, we completed the acquisition of VMware in a cash-and-stock transaction

## avgo-numeric-03 · gold absent from top five

How much was Broadcom's FY2023 research and development expense in USD millions?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [AVGO-2023, PDF p53](https://www.annualreports.com/HostedData/AnnualReportArchive/b/NASDAQ_AVGO_2023.pdf#page=53) — Research and development | 5,253 | 4,919 | 4,854

## avgo-numeric-05 · reader or evidence gate failure

What FY2023 diluted net income per share attributable to common stock did Broadcom originally report, before later stock splits?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [AVGO-2023, PDF p53](https://www.annualreports.com/HostedData/AnnualReportArchive/b/NASDAQ_AVGO_2023.pdf#page=53) — Net income per share attributable to common stock: — Diluted | 32.98 | 26.53 | 15.00

## avgo-unanswerable-02 · unsupported answer

What was Broadcom's exact chip defect rate in FY2023?

Observed: The risk-free interest rate was derived from the average U.S.

Gate: `None`

Expected refusal: A company-wide exact chip defect rate is not disclosed.

## mchp-numeric-05 · reader or evidence gate failure

What diluted net income per common share did Microchip Technology report for FY2023?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [MCHP-2023, PDF p67](https://ir.microchip.com/sec-filings/all-sec-filings/content/0000827054-23-000080/0000827054-23-000080.pdf#page=67) — Diluted net income per common share | 4.02 | 2.27 | 0.65

## mu-narrative-01 · gold absent from top five

Which two memory technologies are the focus of Micron's development efforts in the FY2023 report?

Observed: Unsuccessful efforts to develop new memory and storage technologies and products could have a material adverse effect on our business, results of operations, or financial condition.

Gate: `None`

Gold: [MU-2023, PDF p14](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NYSE_MU_2023.pdf#page=14) — Our R&D efforts are focused primarily on development of memory and storage solutions, including our industry-leading DRAM and NAND technology

## mu-numeric-02 · gold absent from top five

What signed amount appears as Micron's net income or loss in FY2023 (USD millions)?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [MU-2023, PDF p57](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NYSE_MU_2023.pdf#page=57) — Net income (loss) | (5,833) | 8,687 | 5,861

## mu-numeric-04 · gold absent from top five

At its FY2023 year end, what total assets did Micron report in USD millions?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [MU-2023, PDF p59](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NYSE_MU_2023.pdf#page=59) — Total assets | 64,254 | 66,283

## mu-numeric-05 · gold absent from top five

What signed diluted earnings or loss per share did Micron report for FY2023?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [MU-2023, PDF p57](https://www.annualreports.com/HostedData/AnnualReportArchive/m/NYSE_MU_2023.pdf#page=57) — Earnings (loss) per share — Diluted | (5.34) | 7.75 | 5.14

## mu-unanswerable-02 · unsupported answer

What was Micron's exact DRAM manufacturing yield percentage in FY2023?

Observed: Our consolidated gross margin percentage increased to 45% for 2022 from 38% for 2021, as a result of improvements in margins for both DRAM and NAND products, primarily due to reductions in manufacturing costs.

Gate: `None`

Expected refusal: No exact company-wide DRAM manufacturing yield percentage is reported.

## nxpi-narrative-01 · reader or evidence gate failure

Which end market applications does NXP list for its products in the FY2023 report?

Observed: In automotive we are the market leader in most of the applications, with integrated 77Ghz Radar solution for ADAS, battery management products for Electrification, audio processing solutions and amplifiers for car entertainment, Controller Area Network (CAN), Local Interconnect Network (LIN), FlexRay and Ethernet solutions for in-vehicle networking and two-way secure products for secure car access.

Gate: `None`

Gold: [NXPI-2023, PDF p6](https://www.annualreports.com/HostedData/AnnualReportArchive/n/NASDAQ_NXPI_2023.pdf#page=6) — Our product solutions are used in a wide range of end market applications including: automotive, industrial & Internet of Things (IoT), mobile, and communication infrastructure.

## nxpi-numeric-03 · gold absent from top five

What signed R&D amount is displayed in NXP's FY2023 statement of operations (USD millions)?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [NXPI-2023, PDF p61](https://www.annualreports.com/HostedData/AnnualReportArchive/n/NASDAQ_NXPI_2023.pdf#page=61) — Research and development | (2,418) | (2,148) | (1,936)

## nxpi-numeric-04 · gold absent from top five

What were NXP Semiconductors' total assets at the FY2023 year end, in USD millions?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [NXPI-2023, PDF p63](https://www.annualreports.com/HostedData/AnnualReportArchive/n/NASDAQ_NXPI_2023.pdf#page=63) — Total assets | 24,353 | 23,236

## nxpi-numeric-05 · reader or evidence gate failure

What diluted net income per common share attributable to stockholders did NXP report for FY2023?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [NXPI-2023, PDF p61](https://www.annualreports.com/HostedData/AnnualReportArchive/n/NASDAQ_NXPI_2023.pdf#page=61) — Net income (loss) per common share attributable to stockholders — Diluted | 10.70 | 10.55 | 6.79

## qcom-narrative-01 · reader or evidence gate failure

Through which two segments does Qualcomm primarily conduct business, according to its FY2023 report?

Observed: We conduct business primarily through our QCT (Qualcomm CDMA Technologies) semiconductor business and our QTL (Qualcomm Technology Licensing) licensing business.

Gate: `None`

Gold: [QCOM-2023, PDF p11](https://www.annualreports.com/HostedData/AnnualReportArchive/q/NASDAQ_QCOM_2023.pdf#page=11) — We conduct business primarily through QCT and QTL, while QSI makes strategic investments.

## qcom-numeric-02 · reader or evidence gate failure

What consolidated net income, including discontinued operations, did Qualcomm report for FY2023 (USD millions)?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [QCOM-2023, PDF p59](https://www.annualreports.com/HostedData/AnnualReportArchive/q/NASDAQ_QCOM_2023.pdf#page=59) — Net income | 7,232 | 12,936 | 9,043

## qcom-numeric-03 · gold absent from top five

What was Qualcomm's FY2022 R&D expense in USD millions, as presented in its FY2023 filing?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [QCOM-2023, PDF p59](https://www.annualreports.com/HostedData/AnnualReportArchive/q/NASDAQ_QCOM_2023.pdf#page=59) — Research and development | 8,818 | 8,194 | 7,176

## qcom-numeric-04 · gold absent from top five

What total assets did Qualcomm disclose at its FY2023 year end (USD millions)?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [QCOM-2023, PDF p58](https://www.annualreports.com/HostedData/AnnualReportArchive/q/NASDAQ_QCOM_2023.pdf#page=58) — Total assets | 51,040 | 49,014

## qcom-numeric-05 · reader or evidence gate failure

What was Qualcomm's FY2023 diluted earnings per share on net income, including discontinued operations?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [QCOM-2023, PDF p59](https://www.annualreports.com/HostedData/AnnualReportArchive/q/NASDAQ_QCOM_2023.pdf#page=59) — Diluted earnings (loss) per share: — Net income | 6.42 | 11.37 | 7.87

## txn-numeric-04 · gold absent from top five

What was the total asset balance for Texas Instruments at FY2023 year end (USD millions)?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [TXN-2023, PDF p27](https://www.annualreports.com/HostedData/AnnualReportArchive/t/NASDAQ_TXN_2023.pdf#page=27) — Total assets | 32,348 | 27,207

## txn-numeric-05 · reader or evidence gate failure

What diluted earnings per common share did Texas Instruments record in FY2023?

Observed: I cannot answer this from the retrieved annual-report evidence.

Gate: `no_complete_table_evidence_in_top_k`

Gold: [TXN-2023, PDF p25](https://www.annualreports.com/HostedData/AnnualReportArchive/t/NASDAQ_TXN_2023.pdf#page=25) — Earnings per common share (EPS): — Diluted | 7.07 | 9.41 | 8.26

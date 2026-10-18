"""Materialize a separate, source-anchored challenge before model inference.

AI-authored questions and concept checklists; no independent human adjudication.
This does not modify the original benchmark or use model outputs to create labels.
"""

from pathlib import Path

from filing_lens.io import read_json, read_jsonl, write_jsonl

root = Path(__file__).resolve().parents[1]
output = root / "data/explanations/questions.jsonl"
if output.exists():
    raise ValueError("Challenge already exists; revise it under a new version instead")
pages = {(p["doc_id"], p["page"]): p for p in read_jsonl(root / "data/processed/pages.jsonl")}
documents = {d["ticker"]: d for d in read_json(root / "data/corpus.json")["documents"]}

# Every topic supplies two explanation questions and two context-unsupported questions.
# Repeated questions within a topic are dependent; the passage/company is the unit.
topics = [
    (
        "AMD",
        33,
        "New export control restrictions",
        "develop products in the United States.",
        [
            (
                "How could new export controls interfere with AMD's product roadmaps "
                "according to the passage?",
                [
                    ["export", "restriction"],
                    ["research", "development", "teams"],
                    ["roadmap", "delay", "timely"],
                ],
            ),
            (
                "Explain the passage's distinction between risks to AMD's overseas R&D "
                "teams and its work in the United States.",
                [
                    ["outside", "overseas"],
                    ["deemed", "United States", "domestic"],
                    ["develop", "service", "product"],
                ],
            ),
            (
                "What exact number of days does the passage predict AMD's next product "
                "launch will be delayed by export controls?",
                None,
            ),
            (
                "Explain which specific compliance software AMD installed to eliminate "
                "the export-control risks described in the passage.",
                None,
            ),
        ],
    ),
    (
        "INTC",
        52,
        "To the extent the demand decrease is prolonged",
        "these underutilization risks may be heightened.",
        [
            (
                "Explain how a prolonged decrease in demand could increase Intel's "
                "expenses through its production assets.",
                [["underutil", "under-used", "unused"], ["write.down", "depreciation", "expenses"]],
            ),
            (
                "Why could Intel's manufacturing-capacity investments heighten the "
                "underutilization risk described in the passage?",
                [["capacity", "investment"], ["demand", "underutil", "under-used"]],
            ),
            (
                "What exact dollar amount of asset write-downs does the passage forecast "
                "for Intel next quarter?",
                None,
            ),
            (
                "Explain the specific asset-sale agreement Intel signed to remove the "
                "underutilization risk described here.",
                None,
            ),
        ],
    ),
    (
        "NVDA",
        106,
        "Our supply, which includes inventory on hand",
        "misaligned with demand for our products.",
        [
            (
                "Why could NVIDIA incur inventory provisions if its supply commitments do"
                " not match product demand?",
                [
                    ["inventory", "supply", "commitment"],
                    ["demand", "misalign"],
                    ["provision", "charge", "write"],
                ],
            ),
            (
                "Explain why evaluating NVIDIA's supply exposure in this passage requires"
                " looking beyond inventory already on hand.",
                [["purchase obligation"], ["prepaid", "prepayment", "agreement"]],
            ),
            (
                "What exact amount of inventory provisions will NVIDIA record next "
                "quarter according to the passage?",
                None,
            ),
            (
                "Explain the cancellation rights NVIDIA has under each prepaid supply "
                "agreement mentioned in this passage.",
                None,
            ),
        ],
    ),
    (
        "ADI",
        18,
        "We are required to estimate the effects",
        "gross profits in a future period.",
        [
            (
                "Explain how underestimating distributor credits could reduce Analog "
                "Devices' future revenue and gross profit.",
                [
                    ["understat", "underestimat", "estimate"],
                    ["adjust", "credit", "return", "allowance"],
                    ["revenue", "gross profit"],
                ],
            ),
            (
                "Why is estimating distributor returns and allowances important when "
                "Analog Devices records revenue at the time of sale?",
                [["return", "allowance", "credit"], ["adjust", "future", "revenue", "profit"]],
            ),
            (
                "What percentage of distributor sales will Analog Devices accept as "
                "returns next year according to this passage?",
                None,
            ),
            (
                "Explain the mathematical formula Analog Devices uses to estimate "
                "distributor allowances in this passage.",
                None,
            ),
        ],
    ),
    (
        "AVGO",
        19,
        "Any acquisitions we may undertake",
        "the pursuit of other opportunities;",
        [
            (
                "Explain how integrating an acquisition could affect Broadcom's ongoing "
                "business and management focus.",
                [
                    ["delay", "disrupt", "expense", "challenge"],
                    ["management", "attention", "daily operation"],
                ],
            ),
            (
                "Why might the acquisition risks Broadcom lists affect opportunities "
                "beyond the acquired business itself?",
                [["management", "attention"], ["opportunit", "daily operation"]],
            ),
            (
                "What exact integration cost does this passage budget for Broadcom's "
                "VMware merger?",
                None,
            ),
            (
                "Explain which integration milestone Broadcom completed early enough to "
                "avoid all the listed delays.",
                None,
            ),
        ],
    ),
    (
        "MCHP",
        18,
        "Shorter lead times generally mean",
        "more difficult to forecast net sales.",
        [
            (
                "Explain why shorter lead times and turns orders can make Microchip's "
                "future net sales harder to forecast.",
                [
                    ["turns", "order"],
                    ["predict", "forecast", "visibility"],
                    ["short", "change", "volatil"],
                ],
            ),
            (
                "How can customers changing order levels within a quarter affect "
                "Microchip's ability to forecast sales?",
                [["order", "turns"], ["difficult", "predict", "forecast", "visibility"]],
            ),
            (
                "What exact percentage of Microchip's next-quarter sales will come from "
                "turns orders according to this passage?",
                None,
            ),
            (
                "Explain the exact statistical algorithm Microchip uses to forecast turns"
                " orders in this passage.",
                None,
            ),
        ],
    ),
    (
        "MU",
        23,
        "We strive to balance our demand and supply",
        "their estimated net realizable value.",
        [
            (
                "Explain how supply-demand imbalances can lead to lower gross margins for Micron.",
                [["inventory", "inventories"], ["charge", "cost", "write.down"], ["margin"]],
            ),
            (
                "Why might Micron fail to recover all its costs when it carries obsolete "
                "or excess inventory?",
                [
                    ["obsolete", "excess", "inventor"],
                    ["charge", "recover", "write.down", "realizable"],
                ],
            ),
            (
                "What exact inventory write-down will Micron record next year according "
                "to this passage?",
                None,
            ),
            (
                "Explain the insurance policy that reimburses Micron for all the "
                "inventory losses described here.",
                None,
            ),
        ],
    ),
    (
        "NXPI",
        24,
        "Supply disruptions may also occur",
        "disruptions to our manufacturing operations.",
        [
            (
                "Explain why NXP may struggle to keep manufacturing running when a "
                "supplier fails to deliver a critical material.",
                [["substitut", "replace", "complex"], ["disrupt", "manufactur"]],
            ),
            (
                "How do specialized equipment and material requirements increase NXP's "
                "exposure to supplier disruptions?",
                [
                    ["difficult", "impossible", "complex"],
                    ["substitut", "replace"],
                    ["supply", "supplier", "disrupt"],
                ],
            ),
            (
                "How many days of silicon-wafer inventory does NXP hold to cover supplier"
                " disruptions according to the passage?",
                None,
            ),
            (
                "Explain the backup supplier contract NXP signed to guarantee "
                "uninterrupted deliveries in this passage.",
                None,
            ),
        ],
    ),
    (
        "QCOM",
        13,
        "QTL licensing revenues include",
        "a fixed royalty amount per unit.",
        [
            (
                "Explain how licensees' product sales and selling prices contribute to "
                "Qualcomm's per-unit royalty revenues.",
                [["sale", "selling"], ["percent", "price"], ["royalt"]],
            ),
            (
                "Why would applying one uniform royalty percentage to every product "
                "oversimplify Qualcomm's royalty terms described here?",
                [["minimum", "cap"], ["fixed", "deduction"]],
            ),
            (
                "What exact royalty percentage does Qualcomm charge every smartphone "
                "licensee according to this passage?",
                None,
            ),
            (
                "Explain how Qualcomm renegotiated its royalty contract with its largest "
                "licensee in the passage.",
                None,
            ),
        ],
    ),
    (
        "TXN",
        7,
        "We invest in manufacturing technologies",
        "built on a 200mm wafer.",
        [
            (
                "Explain how in-house manufacturing supports Texas Instruments' cost and "
                "supply-chain strategy in the passage.",
                [["cost"], ["control", "supply chain"]],
            ),
            (
                "Why does Texas Instruments link investment in 300mm capacity to a "
                "manufacturing cost advantage?",
                [["300"], ["200"], ["cost", "less", "cheap"]],
            ),
            (
                "What exact total annual dollar saving will Texas Instruments obtain from"
                " its 300mm factories according to this passage?",
                None,
            ),
            (
                "Explain which named external foundry Texas Instruments contracted to "
                "perform all of its manufacturing in this passage.",
                None,
            ),
        ],
    ),
]
rows = []
for ticker, page, first, last, questions in topics:
    document = documents[ticker]
    text = pages[(document["id"], page)]["text"]
    start = text.index(first)
    end = text.index(last, start) + len(last)
    gold = {
        "doc_id": document["id"],
        "page": page,
        "start": start,
        "end": end,
        "quote": text[start:end],
        "source_url": document["url"] + f"#page={page}",
    }
    for index, (question, concepts) in enumerate(questions, 1):
        rows.append(
            {
                "id": f"explain-{ticker.lower()}-{index:02}",
                "company": ticker,
                "split": "dev" if ticker in {"AMD", "INTC"} else "test",
                "topic_id": ticker.lower() + "-context",
                "kind": "explanation" if concepts is not None else "context_unanswerable",
                "question": question,
                "answerable": concepts is not None,
                "concept_groups": concepts or [],
                "evidence": [gold],
                "annotation_status": "ai_authored_pending_independent_human_review",
                "answerability_scope": "supplied passage only, not the entire corpus or world",
            }
        )
old = {q["question"] for q in read_jsonl(root / "data/questions.jsonl")}
assert len(rows) == 40 and not any(q["question"] in old for q in rows)
write_jsonl(output, rows)
print("Materialized 40 new AI-authored challenge questions; independent human review pending")

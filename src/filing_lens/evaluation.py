"""Gold-span retrieval metrics and a frozen answer-scoring protocol."""

from __future__ import annotations

import re
from collections import defaultdict

import numpy as np

from filing_lens.numeric import number


def contains_gold(chunk: dict, gold: dict) -> bool:
    return (
        chunk["doc_id"] == gold["doc_id"]
        and chunk["page"] == gold["page"]
        and chunk["start"] <= gold["start"]
        and chunk["end"] >= gold["end"]
    )


def retrieval_metrics(chunks: list[dict], gold: list[dict]) -> dict:
    if not gold:
        return {"recall_at_1": None, "recall_at_5": None, "recall_at_10": None, "mrr_at_20": None}

    def recall(k):
        return sum(any(contains_gold(c, g) for c in chunks[:k]) for g in gold) / len(gold)

    relevant = [
        i for i, chunk in enumerate(chunks[:20], 1) if any(contains_gold(chunk, g) for g in gold)
    ]
    return {
        "recall_at_1": recall(1),
        "recall_at_5": recall(5),
        "recall_at_10": recall(10),
        "mrr_at_20": 1 / relevant[0] if relevant else 0.0,
    }


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def score_answer(question: dict, response: dict, pages: dict[tuple, dict]) -> dict:
    correct = False
    if not question["answerable"]:
        correct = response["refused"]
    elif not response["refused"]:
        if question["kind"] == "numeric":
            correct = any(
                number(claim["value"]) == number(question["expected_value"])
                and claim["unit"] == question["expected_unit"]
                and claim["period"] == question["period"]
                and claim["doc_id"].startswith(question["company"] + "-")
                and claim["metric"] == question["metric"]
                for claim in response["claims"]
            )
        else:
            correct = normalize(question["expected_answer"]) in normalize(response["answer"])
    citations = response["citations"]
    support = None
    if not response["refused"]:
        support = bool(citations) and all(
            normalize(c["quote"]) in normalize(pages[(c["doc_id"], c["page"])]["text"])
            for c in citations
        )
        if response["claims"]:
            support = support and all(c["supported"] for c in response["numeric_checks"])
    return {
        "correct": bool(correct),
        "citation_supported": support,
        "refused": response["refused"],
        "gold_citation_hit": any(
            any(contains_gold(c, g) for g in question["gold"]) for c in citations
        )
        if question["gold"]
        else None,
    }


def mean(values: list) -> float | None:
    present = [v for v in values if v is not None]
    return float(np.mean(present)) if present else None


def aggregate(rows: list[dict]) -> dict:
    answerable = [r for r in rows if r["answerable"]]
    absent = [r for r in rows if not r["answerable"]]
    answered = [r for r in rows if not r["refused"]]
    numeric = [r for r in rows if r["kind"] == "numeric"]
    narrative = [r for r in rows if r["kind"] == "narrative"]
    return {
        "questions": len(rows),
        "answerable": len(answerable),
        "unanswerable": len(absent),
        **{
            m: mean([r[m] for r in answerable])
            for m in ["recall_at_1", "recall_at_5", "recall_at_10", "mrr_at_20"]
        },
        "answer_correctness": mean([r["correct"] for r in answerable]),
        "numeric_correctness": mean([r["correct"] for r in numeric]),
        "narrative_correctness": mean([r["correct"] for r in narrative]),
        "citation_support": mean([r["citation_supported"] for r in answered]),
        "gold_citation_accuracy": mean([r["gold_citation_hit"] for r in answerable]),
        "answer_coverage": mean([not r["refused"] for r in answerable]),
        "unanswerable_refusal_rate": mean([r["refused"] for r in absent]),
        "false_refusal_rate": mean([r["refused"] for r in answerable]),
        "answered_precision": mean([r["correct"] for r in answered]),
        "latency_p50_ms": float(np.median([r["query_ms"] for r in rows])),
        "latency_p95_ms": float(np.percentile([r["query_ms"] for r in rows], 95)),
    }


def paired_company_bootstrap(
    left: list[dict], right: list[dict], metric: str, samples: int = 2000, seed: int = 17
) -> dict:
    """Paired resampling at company level; questions within firms are correlated."""
    a, b = {r["question_id"]: r for r in left}, {r["question_id"]: r for r in right}
    if set(a) != set(b):
        raise ValueError("Paired bootstrap requires identical question IDs")
    groups = defaultdict(list)
    for key, row in a.items():
        if row[metric] is not None:
            groups[row["company"]].append(float(b[key][metric]) - float(row[metric]))
    companies = sorted(groups)
    rng = np.random.default_rng(seed)
    deltas = [
        np.mean(
            [
                d
                for company in rng.choice(companies, len(companies), replace=True)
                for d in groups[company]
            ]
        )
        for _ in range(samples)
    ]
    return {
        "metric": metric,
        "difference_right_minus_left": float(
            np.mean([d for values in groups.values() for d in values])
        ),
        "ci95": [float(np.percentile(deltas, p)) for p in (2.5, 97.5)],
        "resampling_unit": "company",
        "companies": len(companies),
        "samples": samples,
        "seed": seed,
    }

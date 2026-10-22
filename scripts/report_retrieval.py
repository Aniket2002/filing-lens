"""Render retrieval-v2 measurements and a source-linked failure ledger."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from filing_lens.evaluation import contains_gold
from filing_lens.io import read_json, read_jsonl


def render(root: Path, results: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    dev = read_json(results / "dev/metrics.json")
    test = read_json(results / "test/metrics.json")
    manifest = read_json(results / "test/run.json")
    selected = manifest["selected_on_dev"]
    lines = [
        "# Measured retrieval iteration",
        "",
        f"Development-selected: **{selected}**.",
        "",
        "Every setting uses the same cross-encoder and extractive reader with table assembly.",
        "Test is a reused, previously inspected split; this is exploratory evidence.",
        "",
    ]
    for title, metrics in (
        ("Development (18 answerable, 6 negative)", dev),
        ("Test (42 answerable, 14 negative)", test),
    ):
        lines += [
            f"## {title}",
            "",
            "| Setting | Candidate recall | R@5 | MRR@20 | Correct | Negative refusal | p95 ms |",
            "| :-- | --: | --: | --: | --: | --: | --: |",
        ]
        for row in metrics:
            lines.append(
                f"| {row['config']} | {row['candidate_recall']:.1%} | {row['recall_at_5']:.1%} "
                f"| {row['mrr_at_20']:.3f} | {row['answer_correctness']:.1%} "
                f"| {row['unanswerable_refusal_rate']:.1%} | {row['latency_p95_ms']:.0f} |"
            )
        lines.append("")
    lines += [
        "## Paired company-bootstrap comparisons",
        "",
        "95% intervals use 2,000 resamples over seven companies. They are descriptive.",
        "",
    ]
    for comparison in manifest["paired_comparisons"]:
        for metric in comparison["metrics"]:
            if metric["metric"] == "recall_at_5":
                low, high = metric["ci95"]
                lines.append(
                    f"- Selected minus `{comparison['baseline']}` recall@5: "
                    f"**{metric['difference_right_minus_left'] * 100:+.1f} percentage points**, "
                    f"95% interval [{low * 100:+.1f}, {high * 100:+.1f}]."
                )
    lines += [
        "",
        "## Where retrieval still fails",
        "",
        "| Setting | Hit at 5 | Missing from candidates | Available but ranked below 5 |",
        "| :-- | --: | --: | --: |",
    ]
    for row in test:
        counts = row["failure_counts"]
        lines.append(
            f"| {row['config']} | {counts['hit_at_5']} | {counts['candidate_miss']} "
            f"| {counts['ranking_miss']} |"
        )
    lines += [
        "",
        "Latency is a single warm CPU run, not an SLA or a repeated timing experiment.",
        "See [case-level evidence](failure-ledger.md) for recovered and unresolved questions.",
    ]
    (output / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), layout="constrained")
    labels = [r["config"].replace("-", "\n", 1) for r in test]
    positions = np.arange(len(test))
    for ax, key, title in zip(
        axes,
        ("recall_at_5", "answer_correctness"),
        ("Gold evidence in top 5", "Correct answers"),
        strict=True,
    ):
        values = [r[key] * 100 for r in test]
        bars = ax.bar(
            positions,
            values,
            color=["#167d8d" if r["config"] == selected else "#65758b" for r in test],
            width=0.6,
        )
        ax.bar_label(bars, labels=[f"{v:.1f}%" for v in values], padding=4)
        ax.set_xticks(positions, labels, fontsize=9)
        ax.set_ylim(0, 110)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_ylabel("% of 42 answerable test questions")
        ax.set_title(title)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle(
        "Filing Lens: exploratory retrieval iteration\n"
        "Same reader; development-selected profile; reused test split",
        fontsize=13,
    )
    fig.savefig(output / "comparison.png", dpi=180)
    plt.close(fig)

    rows = read_jsonl(results / "test/predictions.jsonl")
    baseline = {r["question_id"]: r for r in rows if r["config"] == "fixed-baseline-20"}
    chosen = [r for r in rows if r["config"] == selected and r["answerable"]]
    questions = {q["id"]: q for q in read_jsonl(root / "data/questions.jsonl")}
    docs = {d["id"]: d for d in read_json(root / "data/corpus.json")["documents"]}
    ledger = ["# Retrieval case ledger", "", f"Selected: `{selected}`.", ""]
    for title, subset in (
        (
            "Recovered evidence",
            [
                r
                for r in chosen
                if r["recall_at_5"] == 1 and baseline[r["question_id"]]["recall_at_5"] == 0
            ],
        ),
        (
            "Remaining retrieval or answer failures",
            [r for r in chosen if r["recall_at_5"] < 1 or not r["correct"]],
        ),
    ):
        ledger += [f"## {title}", ""]
        for row in subset:
            q = questions[row["question_id"]]
            ledger += [
                f"### {q['id']}",
                "",
                q["question"],
                "",
                f"Retrieval: `{row['retrieval_failure']}`. "
                f"Answer correct: **{row['correct']}**. "
                f"Evidence gate: `{row['response']['reason']}`.",
                "",
            ]
            for gold in q["gold"]:
                matching = [r for r in row["ranking"] if contains_gold(r, gold)]
                if matching:
                    first = matching[0]
                    ledger += [
                        f"Candidate rank **{first['candidate_rank']}** → "
                        f"final rank **{first['rank']}**.",
                        "",
                    ]
                url = docs[gold["doc_id"]]["url"] + f"#page={gold['page']}"
                ledger += [f"[Gold source: {gold['doc_id']}, PDF page {gold['page']}]({url})", ""]
    (output / "failure-ledger.md").write_text("\n".join(ledger), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results/retrieval-v2"))
    parser.add_argument("--output", type=Path, default=Path("docs/retrieval-v2"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    render(root, root / args.results, root / args.output)

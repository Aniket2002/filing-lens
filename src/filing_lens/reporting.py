"""Render the experiment ledger without network access or model inference."""

from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path

from filing_lens.io import read_json, read_jsonl


def pct(value):
    return "—" if value is None else f"{value * 100:.1f}%"


def markdown_table(metrics: list[dict]) -> str:
    lines = [
        "| Configuration | R@1 | R@5 | R@10 | MRR@20 | Answer correct | "
        "Citation support | Refusal (unanswerable) | p95 ms |",
        "| :-- | --: | --: | --: | --: | --: | --: | --: | --: |",
    ]
    for row in metrics:
        values = [
            row["config"],
            pct(row["recall_at_1"]),
            pct(row["recall_at_5"]),
            pct(row["recall_at_10"]),
            f"{row['mrr_at_20']:.3f}",
            pct(row["answer_correctness"]),
            pct(row["citation_support"]),
            pct(row["unanswerable_refusal_rate"]),
            f"{row['latency_p95_ms']:.0f}",
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def render(root: Path, result_path: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    metrics = read_json(result_path / "metrics.json")
    run = read_json(result_path / "run.json")
    predictions = read_jsonl(result_path / "predictions.jsonl")
    questions = {q["id"]: q for q in read_jsonl(root / "data/questions.jsonl")}
    test = [r for r in metrics if r["split"] == "test"]
    chosen = next(r for r in test if r["config"] == run["selected_on_dev"])
    table = markdown_table(test)
    (output / "ablations.md").write_text(
        "# Measured test ablations\n\n42 answerable + 14 unanswerable questions; "
        "seven held-out companies.\n\n"
        + table
        + "\n\nCitation support is conditional on answering. Inspect coverage in metrics.json.\n",
        encoding="utf-8",
        newline="\n",
    )
    plot(test, chosen, output / "ablations.png")
    selected = [r for r in predictions if r["config"] == chosen["config"] and r["split"] == "test"]
    failure_lines = [
        "# Failure ledger\n",
        f"Development-selected configuration: `{chosen['config']}`.\n",
    ]
    categories = Counter()
    for row in selected:
        if row["correct"]:
            continue
        category = (
            "unsupported answer"
            if not row["answerable"]
            else "gold absent from top five"
            if row["recall_at_5"] == 0
            else "reader or evidence gate failure"
        )
        categories[category] += 1
        failure_lines.extend(
            [
                f"## {row['question_id']} · {category}\n",
                row["question"] + "\n",
                f"Observed: {row['response']['answer']}\n",
                f"Gate: `{row['response']['reason']}`\n",
            ]
        )
        q = questions[row["question_id"]]
        if q["gold"]:
            g = q["gold"][0]
            failure_lines.append(
                f"Gold: [{g['doc_id']}, PDF p{g['page']}]({g['source_url']}) — {g['quote']}\n"
            )
        else:
            failure_lines.append("Expected refusal: " + q["refusal_reason"] + "\n")
    failure_lines.insert(
        2, "Counts: " + ", ".join(f"{k}: {v}" for k, v in categories.items()) + ".\n"
    )
    (output / "failure-ledger.md").write_text(
        "\n".join(failure_lines), encoding="utf-8", newline="\n"
    )
    # Standalone review artifact: inline data, no CDNs, accounts, or server needed.
    payload = {
        "metrics": metrics,
        "selected": chosen["config"],
        "run": run,
        "questions": questions,
        "predictions": predictions,
    }
    data = json.dumps(payload, ensure_ascii=True).replace("<", "\\u003c")
    template = (Path(__file__).parent / "report_template.html").read_text(encoding="utf-8")
    page = template.replace("__DATA__", data).replace("__SELECTED__", html.escape(chosen["config"]))
    (output / "index.html").write_text(page, encoding="utf-8", newline="\n")
    print(f"Report written to {output / 'index.html'}")


def plot(metrics: list[dict], chosen: dict, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "figure.facecolor": "#f8f7f3",
            "axes.facecolor": "#f8f7f3",
            "text.color": "#192c39",
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.4), gridspec_kw={"width_ratios": [1.3, 1]})
    y = np.arange(len(metrics))
    colors = [
        "#bd572d"
        if r["config"] == chosen["config"]
        else "#255e6a"
        if r["chunking"] == "structure"
        else "#92a3ad"
        for r in metrics
    ]
    axes[0].barh(y, [r["recall_at_5"] * 100 for r in metrics], color=colors, height=0.65)
    axes[0].set_yticks(y, [r["config"] for r in metrics], fontsize=9)
    axes[0].invert_yaxis()
    axes[0].set_xlim(0, 110)
    axes[0].set_xlabel("Recall@5 · held-out gold passages (%)")
    for idx, r in enumerate(metrics):
        axes[0].text(
            r["recall_at_5"] * 100 + 1.5, idx, f"{r['recall_at_5']:.0%}", va="center", fontsize=9
        )
    for r, color in zip(metrics, colors, strict=True):
        axes[1].scatter(
            r["latency_p95_ms"],
            r["answer_correctness"] * 100,
            c=color,
            marker="D" if r["rerank"] else "o",
            s=80,
            edgecolors="white",
        )
        axes[1].annotate(
            r["config"]
            .replace("structure-", "S/")
            .replace("fixed-", "F/")
            .replace("-rerank", "+R"),
            (r["latency_p95_ms"], r["answer_correctness"] * 100),
            xytext=(5, 4),
            textcoords="offset points",
            fontsize=7,
        )
    axes[1].set_xscale("log")
    axes[1].set_xlabel("p95 query latency (ms, CPU, log scale)")
    axes[1].set_ylabel("Answer correctness on answerable questions (%)")
    axes[1].set_ylim(-4, 104)
    fig.suptitle(
        "FILING LENS  /  Retrieval quality is a measured trade-off",
        x=0.04,
        ha="left",
        fontsize=18,
        fontweight="bold",
    )
    fig.text(
        0.04,
        0.02,
        "42 answerable test questions · 7 companies · "
        "orange = selected on development data · diamonds = reranked",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)

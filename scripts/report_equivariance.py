"""Build or verify the evidence-linked financial equivariance research draft."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pymupdf

from filing_lens.equivariance import STUDY, audit
from filing_lens.io import digest, read_json, read_jsonl, write_json
from filing_lens.paper import render_template, table, to_html

ARMS = ("native_amount", "canonical_amount", "native_pointer", "canonical_pointer")
LABELS = ("Native amount", "Canonical amount", "Native pointer", "Canonical pointer")


def percentage(value):
    return f"{100 * value:.1f}"


def collect(root):
    count = audit(root)
    if count != 4800:
        raise ValueError("The report requires all four complete runs (4,800 outcomes)")
    metrics, runs, predictions = {}, [], []
    for model in ("base", "small"):
        for split in ("dev", "test"):
            folder = root / f"results/equivariance/{model}/{split}"
            metrics[model, split] = read_json(folder / "metrics.json")
            runs.append(read_json(folder / "run.json"))
            if split == "test":
                predictions.extend(
                    {**row, "model": model} for row in read_jsonl(folder / "predictions.jsonl")
                )

    def group(model, source, arm, variant):
        return next(
            g
            for g in metrics[model, "test"]["groups"]
            if (g["source"], g["arm"], g["variant"]) == (source, arm, variant)
        )

    def results(source):
        rows = []
        for model in ("base", "small"):
            for arm, label in zip(ARMS, LABELS, strict=True):
                rows.append(
                    [
                        model,
                        label,
                        percentage(group(model, source, arm, "base")["usable_correct"]),
                        *[
                            percentage(group(model, source, arm, v)["paired_usable"])
                            for v in ("unit_rescale", "column_reverse", "reverse_and_rescale")
                        ],
                        percentage(group(model, source, arm, "period_rebind")["usable_correct"]),
                        percentage(group(model, source, arm, "remove_period")["context_correct"]),
                    ]
                )
        return table(
            ["Model", "Arm", "Base %", "Scale %", "Reverse %", "Both %", "Rebind %", "Removal %"],
            rows,
        )

    primary = metrics["base", "test"]["primary_contrast"]
    small = metrics["small", "test"]["primary_contrast"]
    native = group("base", "retrieved_pages", "native_amount", "unit_rescale")
    pointer = group("base", "retrieved_pages", "canonical_pointer", "unit_rescale")
    canonical = group("base", "retrieved_pages", "canonical_amount", "unit_rescale")
    finding = (
        f"Canonical-pointer paired usable accuracy is {percentage(pointer['paired_usable'])}%, "
        f"compared with {percentage(native['paired_usable'])}% for native-amount and "
        f"{percentage(canonical['paired_usable'])}% for canonical-amount decoding."
    )
    native_base = group("base", "retrieved_pages", "native_amount", "base")["usable_correct"]
    pointer_base = group("base", "retrieved_pages", "canonical_pointer", "base")["usable_correct"]
    removal = [
        group("base", "retrieved_pages", arm, "remove_period")["context_correct"] for arm in ARMS
    ]
    refusal_finding = (
        f"Evidence-removal refusal accuracy is {percentage(removal[0])}% for every base-model arm. "
        if min(removal) == max(removal)
        else (
            "Evidence-removal refusal accuracy across the four base-model arms ranges from "
            f"{percentage(min(removal))}% to {percentage(max(removal))}%. "
        )
    )
    tradeoff = (
        f"Original-input accuracy is {percentage(native_base)}% for native-amount versus "
        f"{percentage(pointer_base)}% for canonical-pointer. "
        + refusal_finding
        + "Preserving-transform robustness therefore cannot stand in for ordinary accuracy "
        "or sensitivity to missing support."
    )
    interpretation = (
        finding
        + f" The primary difference is {100 * primary['delta']:+.1f} percentage points "
        + f"(descriptive 95% interval {100 * primary['ci95'][0]:+.1f} to "
        + f"{100 * primary['ci95'][1]:+.1f}). "
        + "The small-model contrast is "
        + f"{100 * small['delta']:+.1f} points "
        + f"({100 * small['ci95'][0]:+.1f} to {100 * small['ci95'][1]:+.1f}). "
        + "These are pilot estimates on reused companies, not external validation."
    )
    if canonical["paired_usable"] >= pointer["paired_usable"]:
        interpretation += (
            " Canonical-amount matches or exceeds canonical-pointer on the primary condition; "
            "this experiment does not establish an additional benefit from pointer output."
        )
    interpretation += " " + tradeoff
    cases = read_jsonl(root / STUDY / "dataset.jsonl")
    case_map = {c["id"]: c for c in cases}
    base_rows = {
        (r["model"], r["source"], r["arm"], r["question_id"]): r
        for r in predictions
        if r["variant"] == "base"
    }
    failures = [
        r
        for r in predictions
        if r["variant"] == "unit_rescale"
        and r["source"] == "retrieved_pages"
        and base_rows[r["model"], r["source"], r["arm"], r["question_id"]]["usable_correct"]
        and not r["usable_correct"]
    ]
    failure_rows = [
        [
            r["model"],
            r["arm"],
            r["question_id"],
            case_map[r["id"]]["expected_value"],
            repr(r["raw"]),
            r["output"]["status"],
        ]
        for r in failures
    ]
    if failures:
        row = failures[0]
        case = case_map[row["id"]]
        example = (
            f"A recorded regression is {row['question_id']} with {row['model']}/{row['arm']}. "
            f"Its original answer is correct, but after synthetic unit rescaling the model "
            f"outputs `{row['raw']}`; the required value remains {case['expected_value']} "
            f"{case['unit'].replace('_', ' ')}. The report includes every such scale regression, "
            "not just this illustration."
        )
    else:
        example = "No initially correct retrieved-evidence answer regressed under unit rescaling."
    fields = {
        "outcomes": f"{count:,}",
        "calls": f"{sum(r['inference_calls'] for r in runs):,}",
        "primary_delta": f"{100 * primary['delta']:+.1f}",
        "primary_ci": f"[{100 * primary['ci95'][0]:+.1f}, {100 * primary['ci95'][1]:+.1f}]",
        "abstract_finding": finding + " " + tradeoff,
        "result_interpretation": interpretation,
        "retrieved_table": results("retrieved_pages"),
        "oracle_table": results("oracle_page"),
        "max_tokens": str(max(r["max_input_tokens_observed"] for r in runs)),
        "retrieved_coverage": str(
            sum(
                bool(c["target_ids"])
                for c in cases
                if c["source"] == "retrieved_pages" and c["variant"] == "base"
            )
        ),
        "failure_example": example,
    }
    pointer_rows = []
    for model in ("base", "small"):
        for arm in ("native_pointer", "canonical_pointer"):
            for variant in ("base", "period_rebind"):
                subset = [
                    r
                    for r in predictions
                    if (r["model"], r["source"], r["arm"], r["variant"])
                    == (model, "retrieved_pages", arm, variant)
                ]
                pointer_rows.append(
                    [
                        model,
                        arm.replace("_", " "),
                        variant.replace("_", " "),
                        percentage(sum(r["usable_correct"] for r in subset) / len(subset)),
                        percentage(sum(r["coordinate_correct"] for r in subset) / len(subset)),
                        percentage(
                            sum(
                                r["output"]["status"] in {"invalid", "dimension_error"}
                                for r in subset
                            )
                            / len(subset)
                        ),
                    ]
                )
    fields["pointer_table"] = table(
        ["Model", "Arm", "Variant", "Numeric %", "Coordinate %", "Invalid %"], pointer_rows
    )
    report = (
        "# Financial evidence equivariance: measured pilot results\n\n"
        + interpretation
        + f"\n\n{count:,} outcomes; {fields['calls']} distinct-prompt inference calls; "
        + "600 cases derived from 50 original questions. Synthetic variants are dependent.\n\n"
        + "## Retrieved evidence, test companies\n\n"
        + fields["retrieved_table"]
        + "\n\n## Oracle-page evidence, test companies\n\n"
        + fields["oracle_table"]
        + "\n\n## Pointer coordinate diagnostics\n\n"
        + fields["pointer_table"]
        + "\n\nPercentages; 35 source questions per row. Scale/reverse/both require both "
        + "the base and transformed answers to be correct numeric outputs. Removal measures "
        + "explicit UNKNOWN on evidence deletion. "
        + "Full metrics include coverage and invalid outputs.\n"
    )
    ledger = (
        "# All unit-rescaling regressions from initially correct answers\n\n"
        "Test companies, retrieved evidence; synthetic changes only. "
        "IDs and raw outputs permit inspection of every failure.\n\n"
        + table(["Model", "Arm", "Question", "Expected", "Raw output", "Status"], failure_rows)
        + "\n"
    )
    metric_rows = []
    for model in ("base", "small"):
        for arm in ARMS:
            for metric in sorted({c["metric"] for c in cases}):
                subset = [
                    r
                    for r in predictions
                    if (r["model"], r["source"], r["arm"], r["variant"])
                    == (model, "retrieved_pages", arm, "unit_rescale")
                    and case_map[r["id"]]["metric"] == metric
                ]
                usable = sum(
                    r["usable_correct"]
                    and base_rows[model, "retrieved_pages", arm, r["question_id"]]["usable_correct"]
                    for r in subset
                )
                metric_rows.append(
                    [model, arm, metric, len(subset), usable, percentage(usable / len(subset))]
                )
    breakdown = (
        "# Unit-rescaling paired correctness by metric\n\n"
        "Retrieved evidence, test companies. Seven source questions per metric; "
        "per-share targets retain their unit while monetary distractors are rescaled. "
        "This is a supplementary descriptive breakdown, not additional independent trials.\n\n"
        + table(["Model", "Arm", "Metric", "N", "Both correct", "%"], metric_rows)
        + "\n"
    )
    return (
        fields,
        metrics,
        {
            "results.md": report,
            "failures.md": ledger,
            "metric-breakdown.md": breakdown,
        },
    )


def plot(metrics, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.1), sharey=True, layout="constrained")
    for axis, model in zip(axes, ("base", "small"), strict=True):
        groups = {
            g["arm"]: g
            for g in metrics[model, "test"]["groups"]
            if g["source"] == "retrieved_pages" and g["variant"] == "unit_rescale"
        }
        x = np.arange(4)
        axis.bar(
            x - 0.18,
            [100 * groups[a]["same_output"] for a in ARMS],
            0.36,
            color="#bac9d0",
            label="Decoded-state agreement",
        )
        axis.bar(
            x + 0.18,
            [100 * groups[a]["paired_usable"] for a in ARMS],
            0.36,
            color="#176b78",
            label="Both answers correct",
        )
        axis.set_xticks(x, [label.replace(" ", "\n") for label in LABELS], fontsize=9)
        axis.set_title(f"FLAN-T5-{model}")
        axis.set_ylim(0, 110)
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel("Percent of 35 source questions")
    axes[0].legend(frameon=False, fontsize=9, loc="upper left")
    fig.suptitle("Financial unit rescaling: agreement is not correctness", fontsize=14)
    fig.savefig(path, dpi=180, metadata={"Software": "Filing Lens"})
    plt.close(fig)


def document_followup(root: Path) -> dict:
    manifest = read_json(root / "results/document-interventions/manifest.json")
    for path, expected in {**manifest["inputs"], **manifest["outputs"]}.items():
        if digest((root / path).read_bytes()) != expected:
            raise ValueError(f"Document follow-up artifact changed: {path}")
    rows = read_jsonl(root / "results/document-interventions/predictions.jsonl")
    summaries = read_json(root / "results/document-interventions/metrics.json")
    for s in summaries:
        subset = [
            r for r in rows if all(r[k] == s[k] for k in ("split", "strategy", "view", "variant"))
        ]
        if len(subset) != s["n"] or sum(r["scores"]["correct"] for r in subset) != s["correct"]:
            raise ValueError("Document follow-up counts disagree with predictions")
    visible = [
        s for s in summaries if s["split"] == "test" and s["variant"] in {"base", "unit_rescale"}
    ]

    def group(view, variant):
        return next(
            s
            for s in visible
            if s["strategy"] == "structure" and s["view"] == view and s["variant"] == variant
        )

    nb, ns = group("native", "base"), group("native", "unit_rescale")
    ub, us = group("unit_neutral", "base"), group("unit_neutral", "unit_rescale")
    return {
        "document_outcomes": str(len(rows)),
        "document_table": table(
            ["Chunks", "Index view", "Variant", "N", "Page@5", "Correct", "Frozen correct"],
            [
                [
                    s["strategy"],
                    s["view"],
                    s["variant"],
                    s["n"],
                    s["top5_page_hit"],
                    s["correct"],
                    s["frozen_correct"],
                ]
                for s in visible
            ],
        ),
        "document_finding": (
            f"With structure-aware chunks, native BM25 falls from {nb['correct']}/{nb['n']} "
            f"original answers correct to {ns['correct']}/{ns['n']} after rescaling. "
            f"Keeping original chunk rankings while reading changed text retains "
            f"{ns['frozen_correct']}/{ns['n']} correct answers. The unit-neutral index scores "
            f"{ub['correct']}/{ub['n']} originally and {us['correct']}/{us['n']} after rescaling."
        ),
    }


def build(root: Path, check=False):
    folder = root / STUDY
    fields, metrics, rendered = collect(root)
    fields.update(document_followup(root))
    references = read_json(folder / "references.json")
    manuscript = render_template(
        (folder / "manuscript.template.md").read_text(encoding="utf-8"), fields, references
    )
    rendered.update(
        {
            "manuscript.md": manuscript,
            "manuscript.html": to_html(manuscript).replace(
                "<h2>References</h2>",
                '<h2 style="page-break-before: always;">References</h2>',
            ),
            "evidence.json": json.dumps(fields, indent=2) + "\n",
            "references.bib": "\n\n".join(
                f"@misc{{{r['key']},\n"
                + ",\n".join(
                    f"  {key} = {{{r[value]}}}"
                    for key, value in (
                        ("author", "authors"),
                        ("title", "title"),
                        ("year", "year"),
                        ("howpublished", "venue"),
                        ("url", "url"),
                    )
                )
                + "\n}"
                for r in references
            )
            + "\n",
        }
    )
    inputs = [
        root / "scripts/report_equivariance.py",
        root / "src/filing_lens/paper.py",
        folder / "manuscript.template.md",
        folder / "references.json",
        folder / "freeze.json",
        *sorted((root / "results/document-interventions").glob("*.json")),
        *sorted((root / "results/document-interventions").glob("*.jsonl")),
        *sorted((root / "results/equivariance").glob("*/*/*.json")),
        *sorted((root / "results/equivariance").glob("*/*/*.jsonl")),
    ]
    input_hashes = {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in inputs}
    names = {*rendered, "comparison.png", "manuscript.pdf"}
    if check:
        manifest = read_json(folder / "build.json")
        if manifest["inputs"] != input_hashes or set(manifest["outputs"]) != names:
            raise ValueError("Research draft inputs or output coverage changed")
        for name, text in rendered.items():
            if (folder / name).read_text(encoding="utf-8") != text:
                raise ValueError(f"Stale research draft: {name}")
        for name, expected in manifest["outputs"].items():
            if digest((folder / name).read_bytes()) != expected:
                raise ValueError(f"Changed research artifact: {name}")
        return manifest
    for name, text in rendered.items():
        (folder / name).write_text(text, encoding="utf-8", newline="\n")
    plot(metrics, folder / "comparison.png")
    story = pymupdf.Story(rendered["manuscript.html"], archive=str(folder))

    def rectangle(index, filled):
        if index >= 30:
            raise ValueError("Unexpected manuscript overflow")
        return pymupdf.Rect(0, 0, 595, 842), pymupdf.Rect(50, 48, 545, 789), None

    document = story.write_with_links(rectangle)
    for i, page in enumerate(document, 1):
        page.insert_text((50, 817), "Financial Evidence Equivariance | Research pilot", fontsize=8)
        page.insert_text((515, 817), str(i), fontsize=8)
    document.set_metadata(
        {
            "title": "Financial Evidence Equivariance",
            "subject": "Research pilot; independent validation pending",
        }
    )
    document.save(folder / "manuscript.pdf", garbage=4, deflate=True, no_new_id=True)
    manifest = {
        "inputs": input_hashes,
        "outputs": {name: digest((folder / name).read_bytes()) for name in sorted(names)},
        "pdf_pages": len(document),
        "status": "Pilot, not peer reviewed or submitted; originality not established",
    }
    document.close()
    write_json(folder / "build.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = build(Path(__file__).resolve().parents[1], args.check)
    print(f"{'Verified' if args.check else 'Built'} {manifest['pdf_pages']}-page research pilot")

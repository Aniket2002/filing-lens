"""Build an evidence-linked research draft from committed measurements, offline."""

from __future__ import annotations

import html
import re
from pathlib import Path

import pymupdf

from filing_lens.io import digest, read_json, read_jsonl, write_json

LABELS = {
    "fixed-baseline-20": "F20",
    "structure-baseline-20": "S20",
    "structure-entity-20": "E20",
    "structure-entity-60": "E60",
    "structure-finance-60": "F60",
    "structure-hybrid-finance-60": "H60",
}
INPUTS = [
    "research/retrieval-baseline/manuscript.template.md",
    "research/retrieval-baseline/references.json",
    "research/retrieval-baseline/corpus-summary.json",
    "src/filing_lens/paper.py",
    "scripts/build_paper.py",
    "scripts/audit_retrieval_results.py",
    "data/questions.jsonl",
    "data/corpus.json",
    "data/benchmark-lock.json",
    "results/retrieval-v2/dev/metrics.json",
    "results/retrieval-v2/dev/run.json",
    "results/retrieval-v2/dev/predictions.jsonl",
    "results/retrieval-v2/test/metrics.json",
    "results/retrieval-v2/test/run.json",
    "results/retrieval-v2/test/predictions.jsonl",
    "docs/retrieval-v2/comparison.png",
]
CSS = """body { font-family: serif; font-size: 10pt; line-height: 1.22; color: #17212a; }
h1 { font-family: sans-serif; font-size: 21pt; line-height: 1.15; text-align: center; }
h2 { font-family: sans-serif; font-size: 13pt; margin-top: 17pt; margin-bottom: 7pt;
     page-break-after: avoid; }
h3 { font-size: 11pt; margin-top: 12pt; page-break-after: avoid; }
p { margin: 0 0 7pt; }
a { color: #1b6078; text-decoration: none; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; margin: 8pt 0; }
th { text-align: left; }
th, td { padding: 4pt; border-bottom: 0.5pt solid #bbc5cc; }
tr { page-break-inside: avoid; }
code { font-family: monospace; font-size: 8pt; }
pre { white-space: pre-wrap; background-color: #f3f5f6; padding: 8pt; }
img { width: 100%; }
"""


def table(headers: list[str], rows: list[list]) -> str:
    def line(values):
        return "| " + " | ".join(str(v).replace("|", "\\|") for v in values) + " |"

    return "\n".join([line(headers), line(["---"] * len(headers)), *map(line, rows)])


def paired_changes(left: list[dict], right: list[dict], metric: str) -> dict:
    a, b = {r["question_id"]: r for r in left}, {r["question_id"]: r for r in right}
    if len(a) != len(left) or len(b) != len(right) or set(a) != set(b) or not a:
        raise ValueError("Paired analysis needs nonempty, unique, identical question IDs")
    if any(a[key]["company"] != b[key]["company"] for key in a):
        raise ValueError("Paired analysis company mismatch")
    deltas = {key: float(b[key][metric]) - float(a[key][metric]) for key in a}
    companies = sorted({r["company"] for r in a.values()})
    if len(companies) < 2:
        raise ValueError("Company sensitivity needs at least two companies")
    leave_one_out = {}
    for company in companies:
        remaining = [d for key, d in deltas.items() if a[key]["company"] != company]
        leave_one_out[company] = sum(remaining) / len(remaining)
    return {
        "gains": sum(d > 0 for d in deltas.values()),
        "losses": sum(d < 0 for d in deltas.values()),
        "unchanged": sum(d == 0 for d in deltas.values()),
        "leave_one_company_out": leave_one_out,
    }


def collect(root: Path) -> tuple[dict, dict]:
    questions = read_jsonl(root / "data/questions.jsonl")
    dev = read_json(root / "results/retrieval-v2/dev/metrics.json")
    test = read_json(root / "results/retrieval-v2/test/metrics.json")
    run = read_json(root / "results/retrieval-v2/test/run.json")
    corpus = read_json(root / "research/retrieval-baseline/corpus-summary.json")
    if corpus["pages_sha256"] != read_json(root / "data/benchmark-lock.json")["pages_sha256"]:
        raise ValueError("Corpus summary does not describe the frozen extraction")
    rows = read_jsonl(root / "results/retrieval-v2/test/predictions.jsonl")
    selected = next(r for r in test if r["config"] == run["selected_on_dev"])
    baseline = next(r for r in test if r["config"] == "fixed-baseline-20")
    answerable = [r for r in rows if r["answerable"]]
    left = [r for r in answerable if r["config"] == baseline["config"]]
    right = [r for r in answerable if r["config"] == selected["config"]]
    retrieval = paired_changes(left, right, "recall_at_5")
    answers = paired_changes(left, right, "correct")
    comparisons = {
        c["baseline"]: next(m for m in c["metrics"] if m["metric"] == "recall_at_5")
        for c in run["paired_comparisons"]
    }
    companies = []
    for company in sorted({r["company"] for r in answerable}):
        record = {"company": company}
        for config in ("fixed-baseline-20", "structure-baseline-20", selected["config"]):
            subset = [r for r in answerable if r["company"] == company and r["config"] == config]
            record[config] = {"n": len(subset), "hits": sum(r["recall_at_5"] for r in subset)}
        companies.append(record)
    dataset_rows = []
    for kind, label in (
        ("numeric", "Numeric"),
        ("narrative", "Narrative"),
        ("unanswerable", "Unanswerable"),
    ):
        subset = [q for q in questions if q["kind"] == kind]
        dataset_rows.append(
            [
                label,
                len(subset),
                sum(q["split"] == "dev" for q in subset),
                sum(q["split"] == "test" for q in subset),
            ]
        )
    if sum(r[1] for r in dataset_rows) != len(questions):
        raise ValueError("Unexpected dataset kinds")
    dataset_rows.append(
        [
            "Total",
            len(questions),
            sum(q["split"] == "dev" for q in questions),
            sum(q["split"] == "test" for q in questions),
        ]
    )
    pct = lambda value: f"{value * 100:.1f}%"  # noqa: E731
    metrics_rows = lambda data: [  # noqa: E731
        [
            LABELS[r["config"]],
            pct(r["candidate_recall"]),
            pct(r["recall_at_5"]),
            f"{r['mrr_at_20']:.3f}",
            pct(r["answer_correctness"]),
            pct(r["unanswerable_refusal_rate"]),
            f"{r['latency_p95_ms'] / 1000:.2f}",
        ]
        for r in data
    ]
    headers = ["Setting", "Candidate R", "R@5", "MRR@20", "Correct", "Neg. refusal", "p95 s"]
    interval = lambda c: f"[{c['ci95'][0] * 100:+.1f}, {c['ci95'][1] * 100:+.1f}]"  # noqa: E731
    fields = {
        "pages": f"{sum(corpus['document_pages'].values()):,}",
        "companies": str(len(read_json(root / "data/corpus.json")["documents"])),
        "questions": str(len(questions)),
        "test_answerable": str(len(right)),
        "baseline_recall": pct(baseline["recall_at_5"]),
        "selected_recall": pct(selected["recall_at_5"]),
        "baseline_correct": pct(baseline["answer_correctness"]),
        "selected_correct": pct(selected["answer_correctness"]),
        "baseline_misses": str(baseline["failure_counts"]["candidate_miss"]),
        "selected_misses": str(selected["failure_counts"]["candidate_miss"]),
        "baseline_latency": f"{baseline['latency_p95_ms'] / 1000:.2f} s",
        "selected_latency": f"{selected['latency_p95_ms'] / 1000:.2f} s",
        "recall_delta": f"{(selected['recall_at_5'] - baseline['recall_at_5']) * 100:.1f}",
        "recall_interval": interval(comparisons["fixed-baseline-20"]),
        "structure_delta": format(
            comparisons["structure-baseline-20"]["difference_right_minus_left"] * 100, ".1f"
        ),
        "structure_interval": interval(comparisons["structure-baseline-20"]),
        "retrieval_gains": str(retrieval["gains"]),
        "retrieval_losses": str(retrieval["losses"]),
        "retrieval_net": str(retrieval["gains"] - retrieval["losses"]),
        "answer_gains": str(answers["gains"]),
        "answer_losses": str(answers["losses"]),
        "leave_one_out_min": f"{min(retrieval['leave_one_company_out'].values()) * 100:.1f}",
        "leave_one_out_max": f"{max(retrieval['leave_one_company_out'].values()) * 100:.1f}",
        "dataset_table": table(["Type", "All", "Dev", "Test"], dataset_rows),
        "dev_table": table(headers, metrics_rows(dev)),
        "test_table": table(headers, metrics_rows(test)),
        "failure_table": table(
            ["Setting", "Hit@5", "Candidate miss", "Ranking miss"],
            [
                [
                    LABELS[r["config"]],
                    *[
                        r["failure_counts"][k]
                        for k in ("hit_at_5", "candidate_miss", "ranking_miss")
                    ],
                ]
                for r in test
            ],
        ),
        "company_table": table(
            ["Issuer", "F20 hits/n", "S20 hits/n", "E60 hits/n"],
            [
                [
                    c["company"],
                    *[
                        f"{int(c[config]['hits'])}/{c[config]['n']}"
                        for config in (
                            "fixed-baseline-20",
                            "structure-baseline-20",
                            selected["config"],
                        )
                    ],
                ]
                for c in companies
            ],
        ),
    }
    evidence = {
        "selected_on_dev": selected["config"],
        "test_answerable": len(right),
        "retrieval_paired_changes": retrieval,
        "answer_paired_changes": answers,
        "per_company": companies,
        "fields": fields,
    }
    return fields, evidence


def render_template(template: str, fields: dict, references: list[dict]) -> str:
    by_key = {ref["key"]: (i, ref) for i, ref in enumerate(references, 1)}
    if len(by_key) != len(references):
        raise ValueError("Duplicate bibliography key")

    def citation(match):
        key = match.group(1)
        if key not in by_key:
            raise ValueError(f"Unknown citation: {key}")
        number, ref = by_key[key]
        return f"[{number}]({ref['url']})"

    text = re.sub(r"\[@([\w-]+)\]", citation, template)
    fields = {
        **fields,
        "references": "\n\n".join(
            f"{i}. {r['authors'].replace(' and ', ', ')} ({r['year']}). "
            f"[{r['title']}]({r['url']}). {r['venue']}."
            for i, r in enumerate(references, 1)
        ),
    }

    def replace(match):
        key = match.group(1)
        if key not in fields:
            raise ValueError(f"Unknown manuscript field: {key}")
        return fields[key]

    return re.sub(r"\{\{(\w+)\}\}", replace, text)


def inline(text: str) -> str:
    """Render the deliberately small Markdown subset used by this manuscript."""
    text = html.escape(text, quote=True)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)


def to_html(markdown: str) -> str:
    output = []
    for block in re.split(r"\n\s*\n", markdown.strip()):
        if block.startswith("#"):
            match = re.fullmatch(r"(#{1,6}) (.+)", block)
            if not match:
                raise ValueError("A heading must be on its own line")
            level = len(match[1])
            output.append(f"<h{level}>{inline(match[2])}</h{level}>")
        elif block.startswith("|"):
            rows = [line.strip().strip("|").split("|") for line in block.splitlines()]
            output.append("<table>")
            for i, row in enumerate(rows):
                if i == 1:
                    continue
                tag = "th" if i == 0 else "td"
                output.append(
                    "<tr>" + "".join(f"<{tag}>{inline(c.strip())}</{tag}>" for c in row) + "</tr>"
                )
            output.append("</table>")
        elif block.startswith("!["):
            match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", block)
            if not match:
                raise ValueError("An image must be on its own line")
            output.append(
                f'<p><img src="{html.escape(match[2], quote=True)}" '
                f'alt="{html.escape(match[1], quote=True)}"></p>'
            )
        else:
            output.append(f"<p>{inline(' '.join(block.splitlines()))}</p>")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        "<title>Filing Lens research draft</title><style>"
        + CSS
        + "</style></head><body>"
        + "\n".join(output)
        + "</body></html>\n"
    )


def outputs(root: Path) -> dict[str, str]:
    fields, evidence = collect(root)
    references = read_json(root / "research/retrieval-baseline/references.json")
    manuscript = render_template(
        (root / "research/retrieval-baseline/manuscript.template.md").read_text(encoding="utf-8"),
        fields,
        references,
    )
    bibliography = (
        "\n\n".join(
            f"@misc{{{ref['key']},\n"
            + ",\n".join(
                f"  {key} = {{{value}}}"
                for key, value in (
                    ("author", ref["authors"]),
                    ("title", ref["title"]),
                    ("year", ref["year"]),
                    ("howpublished", ref["venue"]),
                    ("url", ref["url"]),
                )
            )
            + "\n}"
            for ref in references
        )
        + "\n"
    )
    import json

    return {
        "manuscript.md": manuscript,
        "manuscript.html": to_html(manuscript),
        "references.bib": bibliography,
        "evidence.json": json.dumps(evidence, indent=2) + "\n",
    }


def build(root: Path, check: bool = False) -> dict:
    directory = root / "research/retrieval-baseline"
    rendered = outputs(root)
    inputs = {name: digest((root / name).read_bytes()) for name in INPUTS}
    if check:
        manifest = read_json(directory / "build.json")
        if inputs != manifest["inputs"]:
            raise ValueError("Paper inputs changed; rebuild the draft")
        if set(manifest["outputs"]) != {*rendered, "manuscript.pdf"}:
            raise ValueError("Paper manifest does not cover all generated outputs")
        for name, content in rendered.items():
            if (directory / name).read_text(encoding="utf-8") != content:
                raise ValueError(f"Generated paper artifact is stale: {name}")
        for name, expected in manifest["outputs"].items():
            if digest((directory / name).read_bytes()) != expected:
                raise ValueError(f"Paper artifact changed: {name}")
        return manifest
    for name, content in rendered.items():
        (directory / name).write_text(content, encoding="utf-8", newline="\n")
    # HTML lives beside this report; the PDF archive is rooted at the repository so figure
    # paths do not require parent-directory traversal inside MuPDF's archive.
    pdf_html = rendered["manuscript.html"].replace('src="../../docs/', 'src="docs/')
    story = pymupdf.Story(pdf_html, archive=str(root))

    def rectangle(index, filled):
        if index >= 40:
            raise ValueError("Paper layout exceeds 40 pages; check oversized content")
        return pymupdf.Rect(0, 0, 595, 842), pymupdf.Rect(50, 48, 545, 789), None

    document = story.write_with_links(rectangle)
    for i, page in enumerate(document, 1):
        page.insert_text(
            (50, 817),
            "Filing Lens | Research draft | Independent review pending",
            fontsize=8,
            color=(0.3, 0.35, 0.4),
        )
        page.insert_text((515, 817), str(i), fontsize=8)
    document.set_metadata(
        {
            "title": "Filing Lens: Auditing Candidate Retrieval and Numeric Evidence",
            "subject": "Exploratory research draft; independent review pending",
            "creator": "Filing Lens offline paper build",
        }
    )
    document.save(directory / "manuscript.pdf", garbage=4, deflate=True, no_new_id=True)
    pages = len(document)
    document.close()
    manifest = {
        "inputs": inputs,
        "outputs": {
            name: digest((directory / name).read_bytes()) for name in [*rendered, "manuscript.pdf"]
        },
        "pdf_pages": pages,
        "pymupdf": pymupdf.VersionBind,
        "status": "research draft; not independently reviewed or submitted",
        "note": "PDF bytes may vary by renderer; derived text and source fingerprints are checked",
    }
    write_json(directory / "build.json", manifest)
    return manifest

"""Refresh the README's measured-results block from the frozen experiment ledger."""

from pathlib import Path

from filing_lens.io import read_json
from filing_lens.reporting import markdown_table

root = Path(__file__).resolve().parents[1]
run = read_json(root / "results/reference/run.json")
metrics = [r for r in read_json(root / "results/reference/metrics.json") if r["split"] == "test"]
selected = next(r for r in metrics if r["config"] == run["selected_on_dev"])
baseline = next(r for r in metrics if r["config"] == "fixed-bm25")
interval = next(r for r in run["paired_test_comparisons"] if r["metric"] == "recall_at_5")
generator = next(
    r for r in read_json(root / "results/generator/metrics.json") if r["split"] == "test"
)
best = max(metrics, key=lambda r: r["recall_at_5"])
body = (
    f"Development selected **`{selected['config']}`**. Its test recall@5 is "
    f"**{selected['recall_at_5']:.1%}**, versus {baseline['recall_at_5']:.1%} for fixed/BM25: "
    f"**+{interval['difference_right_minus_left'] * 100:.1f} percentage points** "
    f"(paired company-bootstrap 95% interval: +{interval['ci95'][0] * 100:.1f} to "
    f"+{interval['ci95'][1] * 100:.1f} points; seven test companies). "
    f"Answer correctness is {selected['answer_correctness']:.1%}, answerable-question coverage "
    f"is {selected['answer_coverage']:.1%}, and unanswerable refusal is "
    f"{selected['unanswerable_refusal_rate']:.1%}.\n\n"
    f"The highest observed test recall belongs to `{best['config']}` "
    f"({best['recall_at_5']:.1%} recall@5; {best['answer_correctness']:.1%} answer correctness). "
    "It was not selected by the development set, so it remains a descriptive test result.\n\n"
    + markdown_table(metrics)
    + "\n\nCitation support is conditional on returning an answer. The selected system "
    "returns source-supported but irrelevant answers to three negative questions; "
    "100% citation support therefore does not mean 100% correctness.\n\n"
    f"**Failed generation pilot, retained:** FLAN-T5-small achieves "
    f"{generator['raw_amount_correctness']:.1%} raw amount correctness on the 35 numeric test "
    f"questions. The guard declines every test answer ({generator['answer_coverage']:.1%} "
    "numeric coverage). Its 100% negative refusal rate is degenerate and does not demonstrate "
    "useful generative QA. See the failure analysis and preserved raw outputs."
)
path = root / "README.md"
text = path.read_text(encoding="utf-8")
start, end = "<!-- RESULTS_START -->", "<!-- RESULTS_END -->"
prefix, rest = text.split(start, 1)
_, suffix = rest.split(end, 1)
path.write_text(prefix + start + "\n" + body + "\n" + end + suffix, encoding="utf-8", newline="\n")
print("README now contains measured test results and the failed generation pilot")

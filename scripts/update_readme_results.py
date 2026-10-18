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
assembled = read_json(root / "results/iter1/test/metrics.json")[0]
generation_v2 = read_json(root / "results/generator-v2/test/metrics.json")
explanations = read_json(root / "results/explanations/test/metrics.json")
body = (
    f"Development selected **`{selected['config']}`**. Its test recall@5 is "
    f"**{selected['recall_at_5']:.1%}**, versus {baseline['recall_at_5']:.1%} for fixed/BM25: "
    f"**+{interval['difference_right_minus_left'] * 100:.1f} percentage points** "
    f"(paired company-bootstrap 95% interval: +{interval['ci95'][0] * 100:.1f} to "
    f"+{interval['ci95'][1] * 100:.1f} points; seven test companies). "
    "Treat this small-sample interval as descriptive, not as evidence of statistical "
    "significance or general superiority. "
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
    "useful generative QA. See the failure analysis and preserved raw outputs.\n\n"
    "**Current CLI/API reader:** same-page table-evidence assembly is now enabled by default "
    "for `ask` and `serve`. The separately measured extractive profile achieves "
    f"**{assembled['answer_correctness']:.1%} correctness (24/42)** and "
    f"**{assembled['answer_coverage']:.1%} coverage (27/42)**, with unchanged retrieval and "
    "unanswerable refusal. Use `--no-assemble-table-evidence` for the original reader; "
    "benchmark defaults and frozen reference artifacts retain the original behavior. "
    "See [Iteration 1](docs/ITERATION_1.md).\n\n"
    "**Generation v2, exploratory:** pinned FLAN-T5-base with aligned year/value records "
    f"achieves **{generation_v2['raw_amount_correctness']:.1%} raw amount correctness (21/35)** "
    f"and **{generation_v2['answer_correctness']:.1%} verified numeric correctness and coverage "
    "(20/35)**. It uses the same retrieval rankings plus table-evidence assembly. The guard "
    "withholds one correct raw amount without sufficient retrieved evidence. The model's "
    "exact `UNKNOWN` rate on 14 negatives is **0/14**; guarded refusals come from the controls. "
    "This is row-assisted amount generation on a previously inspected test set, with model, "
    "prompt, context format, and evidence assembly changed together. It is not an independent "
    "validation, a controlled model-size comparison, or general financial QA. "
    "See the [generation study](docs/GENERATION_V2.md) and "
    "[preserved outputs](results/generator-v2/test/predictions.jsonl).\n\n"
    "**New explanation challenge, supplied evidence:** 40 new AI-authored questions "
    "(8 development, 32 test) were frozen before inference using the same source filings. "
    "The experimental `flan-t5-explain` reader generates prose and its own yes/no answerability "
    "decision without the extractive reader or numeric guard. On test it declines "
    f"**{explanations['model_refusal_on_unanswerables']:.1%} of unsupported questions (15/16)** "
    "and falsely declines **1/16 supported questions**. Explanation quality remains weak: "
    "only **6/16** supported questions pass the full automatic concept screen, which is not "
    "a correctness or entailment score. Human quality scores remain unassigned. "
    "This isolates model behavior on supplied passages; it does not evaluate retrieval or "
    "establish independent human validation. See the "
    "[explanation study](docs/EXPLANATION_STUDY.md)."
)
path = root / "README.md"
text = path.read_text(encoding="utf-8")
start, end = "<!-- RESULTS_START -->", "<!-- RESULTS_END -->"
prefix, rest = text.split(start, 1)
_, suffix = rest.split(end, 1)
path.write_text(prefix + start + "\n" + body + "\n" + end + suffix, encoding="utf-8", newline="\n")
print("README now contains measured test results and the failed generation pilot")

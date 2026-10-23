"""Record exact bytes of reference evidence and published report artifacts."""

from pathlib import Path

from filing_lens.io import digest, write_json

root = Path(__file__).resolve().parents[1]
paths = [
    root / "README.md",
    root / "docs/EXPERIMENTS.md",
    root / "docs/experiments/REFERENCE_RESULTS.md",
    root / "data/questions.jsonl",
    root / "docs/FAILURE_ANALYSIS.md",
    root / "docs/EXPERIMENT_PROTOCOL.md",
    root / "docs/experiments/GENERATION_V2.md",
    root / "docs/ANNOTATION_REVIEW.md",
    root / "docs/ANSWER_REVIEW.md",
    root / "docs/SERVICE.md",
    root / "docs/DATA_CARD.md",
    root / "docs/experiments/ITERATION_1.md",
    root / "docs/experiments/EXPLANATION_STUDY.md",
    root / "docs/RETRIEVAL_V2.md",
    root / "data/generator-v2-lock.json",
]
for folder in [
    "results/reference",
    "results/generator",
    "results/generator-v2/dev",
    "results/generator-v2/test",
    "results/iter1/dev",
    "results/iter1/test",
    "results/explanations/dev",
    "results/explanations/test",
    "results/retrieval-v2/dev",
    "results/retrieval-v2/test",
    "results/controls",
    "docs/report",
    "docs/retrieval-v2",
    "research/retrieval-baseline",
    "research/equivariance",
    "results/equivariance/base/dev",
    "results/equivariance/base/test",
    "results/equivariance/small/dev",
    "results/equivariance/small/test",
    "data/evidence",
    "data/review",
    "data/explanations",
]:
    paths.extend(p for p in (root / folder).iterdir() if p.is_file())
paths.append(root / "results/representation-diagnostics.json")
records = [
    {
        "path": p.relative_to(root).as_posix(),
        "sha256": digest(p.read_bytes()),
        "bytes": p.stat().st_size,
    }
    for p in sorted(paths)
]
write_json(
    root / "results/artifacts.json",
    {
        "algorithm": "sha256",
        "files": records,
        "note": (
            "Integrity seal of evidence and report bytes; "
            "does not independently validate source facts."
        ),
    },
)
print(f"Sealed {len(records)} evidence and report artifacts")

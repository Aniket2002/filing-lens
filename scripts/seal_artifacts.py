"""Record exact bytes of reference evidence and published report artifacts."""

from pathlib import Path

from filing_lens.io import digest, write_json

root = Path(__file__).resolve().parents[1]
paths = [
    root / "README.md",
    root / "data/questions.jsonl",
    root / "docs/FAILURE_ANALYSIS.md",
    root / "docs/EXPERIMENT_PROTOCOL.md",
]
for folder in [
    "results/reference",
    "results/generator",
    "results/controls",
    "docs/report",
    "data/evidence",
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

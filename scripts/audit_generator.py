"""Run the optional pinned local generator against frozen retrieved evidence."""

from pathlib import Path

from filing_lens.generation import audit_generator

root = Path(__file__).resolve().parents[1]
audit_generator(root, root / "results/reference", root / "results/generator")

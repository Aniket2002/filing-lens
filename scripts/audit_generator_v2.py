"""Run dev first, then the frozen test experiment, retaining the failed v1 pilot."""

import argparse
from pathlib import Path

from filing_lens.generator_experiment import audit

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--split", choices=["dev", "test"], required=True)
parser.add_argument("--output", type=Path, default=Path("results/generator-v2"))
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
audit(root, root / args.output, args.split)

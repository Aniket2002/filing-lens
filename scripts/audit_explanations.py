"""Freeze a new explanation protocol or run its development/test split."""

import argparse
from pathlib import Path

from filing_lens.explanation_study import freeze, run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--freeze", action="store_true")
parser.add_argument("--split", choices=["dev", "test"])
parser.add_argument("--output", type=Path, default=Path("results/explanations"))
args = parser.parse_args()
if bool(args.freeze) == bool(args.split):
    parser.error("Choose exactly one of --freeze or --split")
root = Path(__file__).resolve().parents[1]
if args.freeze:
    freeze(root)
    print("Frozen new explanation challenge before inference")
else:
    run(root, root / args.output, args.split)

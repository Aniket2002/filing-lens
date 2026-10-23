"""Freeze, run, or audit the separate financial evidence equivariance pilot."""

import argparse
from pathlib import Path

from filing_lens.equivariance import audit, prepare, run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("action", choices=["prepare", "run", "audit"])
parser.add_argument("--split", choices=["dev", "test"], default="dev")
parser.add_argument("--model", choices=["small", "base"], default="base")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
if args.action == "prepare":
    prepare(root)
elif args.action == "run":
    run(root, args.split, args.model)
else:
    print(f"Audited {audit(root)} equivariance outcomes")

"""Prepare or validate an independent review without changing frozen gold labels."""

import argparse
from pathlib import Path

from filing_lens.adjudication import export_sheet, save_review

parser = argparse.ArgumentParser(description=__doc__)
commands = parser.add_subparsers(dest="command", required=True)
export = commands.add_parser("export")
export.add_argument("--output", type=Path, required=True)
validate = commands.add_parser("validate")
validate.add_argument("--input", type=Path, required=True)
validate.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
if args.command == "export":
    export_sheet(root, args.output)
    print(f"Exported 80 pending reviews to {args.output}")
else:
    report = save_review(root, args.input, args.output)
    print(f"Validated {report['reviewed']} recorded reviews; {report['pending']} pending")

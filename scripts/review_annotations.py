"""Prepare or validate an independent review without changing frozen gold labels."""

import argparse
from pathlib import Path

from filing_lens.adjudication import export_sheet, review_questions, save_review

parser = argparse.ArgumentParser(description=__doc__)
commands = parser.add_subparsers(dest="command", required=True)
export = commands.add_parser("export")
export.add_argument("--output", type=Path, required=True)
export.add_argument("--dataset", choices=["reference", "explanations"], default="reference")
validate = commands.add_parser("validate")
validate.add_argument("--input", type=Path, required=True)
validate.add_argument("--output", type=Path, required=True)
validate.add_argument("--dataset", choices=["reference", "explanations"], default="reference")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
if args.command == "export":
    export_sheet(root, args.output, args.dataset)
    print(
        f"Exported {len(review_questions(root, args.dataset)[1])} pending reviews to {args.output}"
    )
else:
    report = save_review(root, args.input, args.output, args.dataset)
    print(f"Validated {report['reviewed']} recorded reviews; {report['pending']} pending")

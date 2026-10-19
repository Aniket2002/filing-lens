"""Export or validate human judgments of frozen explanation responses."""

import argparse
from pathlib import Path

from filing_lens.answer_review import export_answers, save_answers

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--results", type=Path, default=Path("results/explanations"))
commands = parser.add_subparsers(dest="command", required=True)
export = commands.add_parser("export")
export.add_argument("--output", type=Path, required=True)
validate = commands.add_parser("validate")
validate.add_argument("--input", type=Path, required=True)
validate.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
try:
    if args.command == "export":
        export_answers(root, root / args.results, args.output)
        print(f"Exported pending answer reviews to {args.output}")
    else:
        report = save_answers(root, root / args.results, args.input, args.output)
        for split, metrics in report["splits"].items():
            print(f"{split}: {metrics['reviewed']} reviewed, {metrics['pending']} pending")
except (ValueError, OSError) as exc:
    parser.exit(2, f"Error: {exc}\n")

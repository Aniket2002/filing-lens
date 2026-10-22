"""Build/check the research draft using only committed artifacts and existing dependencies."""

import argparse
from collections import Counter
from pathlib import Path

from audit_retrieval_results import audit

from filing_lens.io import digest, read_json, read_jsonl, write_json
from filing_lens.paper import build

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Check generated files without rewriting"
    )
    parser.add_argument(
        "--refresh-corpus-summary",
        action="store_true",
        help="Refresh page counts from the frozen local corpus; requires parsing",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.check and args.refresh_corpus_summary:
        parser.error("--check cannot refresh the corpus summary")
    if args.refresh_corpus_summary:
        path = root / "data/processed/pages.jsonl"
        sha = digest(path.read_bytes())
        if sha != read_json(root / "data/benchmark-lock.json")["pages_sha256"]:
            raise ValueError("Cannot summarize a changed corpus")
        pages = read_jsonl(path)
        if len({(p["doc_id"], p["page"]) for p in pages}) != len(pages):
            raise ValueError("Duplicate corpus pages")
        write_json(
            root / "paper/corpus-summary.json",
            {
                "pages_sha256": sha,
                "document_pages": dict(sorted(Counter(p["doc_id"] for p in pages).items())),
                "note": (
                    "Counts from canonical pages; offline snapshot tied to frozen extraction hash"
                ),
            },
        )
    audit(root, root / "results/retrieval-v2")
    result = build(root, check=args.check)
    print(f"{'Checked' if args.check else 'Built'} research draft: {result['pdf_pages']} PDF pages")

"""Annotation aid. Does not generate questions or label retrieval results."""

import re
from pathlib import Path

import pymupdf

from filing_lens.io import read_json
from filing_lens.table_layout import statement_table

root = Path(__file__).resolve().parents[1]
for doc in read_json(root / "data/corpus.json")["documents"]:
    print("\n", doc["id"])
    pdf = pymupdf.open(root / "data/raw" / f"{doc['id']}.pdf")
    for page in pdf:
        tab = statement_table(page, doc["id"])
        if tab:
            selected = [
                row
                for row in tab["rows"]
                if re.search(
                    r"^(?:net revenue|revenue|total revenue|net sales|net income|net loss|"
                    r"research|total assets|.*(?:earnings|income).*diluted|earnings per share|"
                    r"diluted|.*per share.* — Diluted)",
                    row[0],
                    re.I,
                )
            ]
            if selected:
                print(tab["id"], tab["years"], tab["unit"])
                for row in selected:
                    print(row)
    pdf.close()

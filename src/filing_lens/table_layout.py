"""Recover borderless primary statements using PDF word coordinates.

Conservative scope: only statement pages with multiple year columns and at least
five aligned labelled numeric rows. No OCR, inferred values, or gold labels.
"""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from filing_lens.io import read_json, read_jsonl, write_json, write_jsonl

NUMBER = re.compile(r"^\(?[-−]?\d[\d,]*(?:\.\d+)?\)?$|^[—–-]$")


def statement_table(page: pymupdf.Page, doc_id: str) -> dict | None:
    words = sorted(page.get_text("words"), key=lambda w: (w[1], w[0]))
    lines: list[list] = []
    for word in words:
        if lines and abs(word[1] - lines[-1][0][1]) < 3:
            lines[-1].append(word)
        else:
            lines.append([word])
    for line in lines:
        line.sort(key=lambda w: w[0])
    title = re.search(
        r"consolidated\s+(?:statements?\s+of\s+(?:operations|income|earnings)|"
        r"balance\s+sheets?|statements?\s+of\s+cash\s+flows)",
        page.get_text(sort=True),
        re.I,
    )
    if not title:
        return None
    # Restrict heading to the page's top; reject notes/indexes mentioning a statement.
    heading_lines = [
        " ".join(w[4] for w in line) for line in lines if line[0][1] < page.rect.height * 0.23
    ]
    if not any(
        re.fullmatch(title.re.pattern + r"(?:\s+For Years Ended.*)?", line, re.I)
        for line in heading_lines
    ):
        return None
    headers = []
    for idx, line in enumerate(lines):
        years = [w for w in line if re.fullmatch(r"20[0-3]\d", w[4])]
        if len(years) >= 2 and line[0][1] < page.rect.height * 0.35:
            headers.append((idx, years))
    if not headers:
        return None
    header_index, year_words = headers[-1]
    year_words.sort(key=lambda w: w[0])
    centers = [(w[0] + w[2]) / 2 for w in year_words]
    years = [int(w[4]) for w in year_words]
    if len(set(years)) != len(years):
        return None
    numeric_left = centers[0] - (centers[1] - centers[0]) * 0.55
    rows, row_boxes, section = [], [], ""
    for line in lines[header_index + 1 :]:
        if line[0][1] > page.rect.height * 0.94:
            continue
        label = " ".join(w[4] for w in line if (w[0] + w[2]) / 2 < numeric_left)
        label = label.replace("�", "").replace("•", "").strip(" $–—-")
        fields = ["" for _ in years]
        for word in line:
            center = (word[0] + word[2]) / 2
            if center < numeric_left:
                continue
            idx = min(range(len(centers)), key=lambda i: abs(centers[i] - center))
            fields[idx] += word[4]
        fields = [f.replace("$", "").replace(" ", "").replace("�", "—") for f in fields]
        if label and sum(bool(NUMBER.fullmatch(f)) for f in fields) >= 2:
            if section and (
                label.lower() in {"basic", "diluted"}
                or (
                    "per share" in section.lower()
                    and label.lower()
                    in {"net income", "continuing operations", "discontinued operations"}
                )
            ):
                label = section + " — " + label
            rows.append([label, *fields])
            row_boxes.append(
                [
                    min(w[0] for w in line),
                    min(w[1] for w in line),
                    max(w[2] for w in line),
                    max(w[3] for w in line),
                ]
            )
        elif label and not any(fields):
            if re.search(
                r"per(?: common)?[ -]share|earnings|weighted|shares.*(?:used|outstanding)",
                label,
                re.I,
            ):
                section = label
    if len(rows) < 5:
        return None
    text = page.get_text(sort=True)
    unit_match = re.search(r"(?:in |\()?(millions|thousands)", text, re.I)
    unit = "USD_" + unit_match.group(1).lower() if unit_match else None
    return {
        "id": f"{doc_id}:p{page.number + 1}:statement",
        "doc_id": doc_id,
        "page": page.number + 1,
        "title": title.group(0),
        "years": years,
        "unit": unit,
        "rows": [["Metric", *map(str, years)], *rows],
        "row_boxes": row_boxes,
        "method": "year_aligned_words",
    }


def enrich_statements(root: Path) -> None:
    """Append a normalized layout view, preserving the original extracted text.

    Both chunkers receive the same canonical text, including the same normalized
    statement view. The structure chunker alone repeats headers at table splits.
    """
    pages = read_jsonl(root / "data/processed/pages.jsonl")
    tables = [
        t
        for t in read_jsonl(root / "data/processed/tables.jsonl")
        if t.get("method") != "year_aligned_words"
    ]
    documents = read_json(root / "data/corpus.json")["documents"]
    by_id = {d["id"]: pymupdf.open(root / "data/raw" / f"{d['id']}.pdf") for d in documents}
    added = []
    for page in pages:
        old = [b for b in page["blocks"] if (b.get("table_id") or "").endswith(":statement")]
        if old:
            page["text"] = page["text"][: min(b["start"] for b in old) - 2]
            page["blocks"] = [b for b in page["blocks"] if b not in old]
        table = statement_table(by_id[page["doc_id"]][page["page"] - 1], page["doc_id"])
        if table is None:
            continue
        context = f"{table['title']} ({table['unit'] or 'unit unresolved'})\n"
        view = context + "\n".join(" | ".join(row) for row in table["rows"])
        start = len(page["text"]) + 2
        page["text"] += "\n\n" + view
        page["blocks"].append(
            {"kind": "table", "start": start, "end": len(page["text"]), "table_id": table["id"]}
        )
        tables.append(table)
        added.append(
            {
                "id": table["id"],
                "rows": len(table["rows"]) - 1,
                "years": table["years"],
                "unit": table["unit"],
            }
        )
    for document in by_id.values():
        document.close()
    write_jsonl(root / "data/processed/pages.jsonl", pages)
    write_jsonl(root / "data/processed/tables.jsonl", tables)
    write_json(root / "data/processed/statement-report.json", added)

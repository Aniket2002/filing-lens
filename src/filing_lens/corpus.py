"""Download immutable source files and parse text plus layout-detected tables.

Canonical page offsets are shared by every chunker. Relevance labels never depend
on chunk IDs, so changing chunk boundaries does not silently change the gold set.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import httpx
import pymupdf
from rich import print

from filing_lens.io import digest, read_json, write_json, write_jsonl


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u00ad", "")).strip()


def download(root: Path) -> None:
    manifest = read_json(root / "data/corpus.json")
    path = root / "data/source-lock.json"
    lock = read_json(path) if path.exists() else {}
    raw = root / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        for doc in manifest["documents"]:
            target = raw / f"{doc['id']}.pdf"
            if not target.exists():
                for attempt in range(3):
                    try:
                        response = client.get(doc["url"])
                        response.raise_for_status()
                        if not response.content.startswith(b"%PDF"):
                            raise ValueError(f"Not a PDF: {doc['url']}")
                        temporary = target.with_suffix(".tmp")
                        temporary.write_bytes(response.content)
                        temporary.replace(target)
                        break
                    except (httpx.HTTPError, ValueError) as exc:
                        if attempt == 2:
                            raise
                        pause = 2**attempt
                        if (
                            isinstance(exc, httpx.HTTPStatusError)
                            and exc.response.status_code == 429
                        ):
                            pause = max(30, int(exc.response.headers.get("retry-after", "30")))
                        time.sleep(min(pause, 60))
            sha = digest(target.read_bytes())
            if doc["id"] in lock and sha != lock[doc["id"]]["sha256"]:
                raise ValueError(f"Source changed: {doc['id']}; restore the locked PDF")
            lock[doc["id"]] = {"sha256": sha, "bytes": target.stat().st_size, "url": doc["url"]}
            write_json(path, lock)
            print(f"[green]Source[/green] {doc['id']}: {target.stat().st_size:,} bytes")
    write_json(path, lock)


def parse(root: Path) -> None:
    manifest = read_json(root / "data/corpus.json")
    lock = read_json(root / "data/source-lock.json")
    pages, all_tables, diagnostics = [], [], []
    for doc in manifest["documents"]:
        path = root / "data/raw" / f"{doc['id']}.pdf"
        if digest(path.read_bytes()) != lock[doc["id"]]["sha256"]:
            raise ValueError(f"Source hash mismatch: {path}")
        document = pymupdf.open(path)
        count = 0
        for page_no, page in enumerate(document, start=1):
            found = page.find_tables().tables
            tables = []
            for tab in found:
                rows = [[clean(cell or "") for cell in row] for row in tab.extract()]
                # Reject decorative boxes; preserve genuine tables, even sparse ones.
                if len(rows) < 2 or max(map(len, rows), default=0) < 2:
                    continue
                if sum(bool(re.search(r"\d", cell)) for row in rows for cell in row) < 3:
                    continue
                tables.append((pymupdf.Rect(tab.bbox), rows))
            pieces = []
            for x0, y0, x1, y1, text, *_ in page.get_text("blocks", sort=True):
                box = pymupdf.Rect(x0, y0, x1, y1)
                if any((box & bbox).get_area() > box.get_area() * 0.5 for bbox, _ in tables):
                    continue
                value = clean(text)
                if value:
                    pieces.append((y0, x0, "text", value, None))
            for idx, (bbox, rows) in enumerate(tables):
                table_id = f"{doc['id']}:p{page_no}:t{idx}"
                value = "\n".join(" | ".join(row) for row in rows)
                pieces.append((bbox.y0, bbox.x0, "table", value, table_id))
                all_tables.append(
                    {
                        "id": table_id,
                        "doc_id": doc["id"],
                        "page": page_no,
                        "rows": rows,
                        "bbox": list(bbox),
                    }
                )
                count += 1
            pieces.sort(key=lambda p: (round(p[0], 1), p[1]))
            blocks, text = [], ""
            for _, _, kind, value, table_id in pieces:
                if text:
                    text += "\n\n"
                start = len(text)
                text += value
                blocks.append(
                    {"kind": kind, "start": start, "end": len(text), "table_id": table_id}
                )
            pages.append({"doc_id": doc["id"], "page": page_no, "text": text, "blocks": blocks})
        diagnostics.append({"doc_id": doc["id"], "pages": len(document), "tables": count})
        print(f"[cyan]Parsed[/cyan] {doc['id']}: {len(document)} pages, {count} tables")
        document.close()
    write_jsonl(root / "data/processed/pages.jsonl", pages)
    write_jsonl(root / "data/processed/tables.jsonl", all_tables)
    write_json(
        root / "data/processed/parse-report.json",
        {
            "parser": "pymupdf",
            "version": pymupdf.VersionBind,
            "documents": diagnostics,
            "empty_pages": [
                {"doc_id": p["doc_id"], "page": p["page"]} for p in pages if not p["text"]
            ],
        },
    )

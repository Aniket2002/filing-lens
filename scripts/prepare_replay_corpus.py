"""Restore the exact parsed replay corpus from checksum-locked public PDFs.

Used by ordinary CI. Cached bytes are verified, never accepted on cache identity
alone. A missing source or any drift fails the job instead of skipping replay.
"""

from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

import httpx

from filing_lens.corpus import parse
from filing_lens.io import digest, read_json
from filing_lens.table_layout import enrich_statements


def prepare(root: Path) -> None:
    expected = read_json(root / "data/benchmark-lock.json")["pages_sha256"]
    recorded = read_json(root / "results/document-interventions/manifest.json")[
        "parsed_pages_sha256"
    ]
    if expected != recorded:
        raise ValueError("Benchmark and retrieval run disagree about the parsed corpus")
    target = root / "data/processed/pages.jsonl"
    if target.exists():
        if digest(target.read_bytes()) != expected:
            raise ValueError("Cached parsed corpus is corrupt or stale; refusing to overwrite it")
        print(f"Verified cached parsed corpus: {expected}", flush=True)
        return
    documents = read_json(root / "data/corpus.json")["documents"]
    lock = read_json(root / "data/source-lock.json")
    mirrors = read_json(root / "data/replay-source-mirrors.json")["mirrors"]
    raw = root / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    with httpx.Client(
        follow_redirects=True,
        timeout=120,
        limits=httpx.Limits(max_keepalive_connections=0),
        headers={
            "User-Agent": "FilingLensResearch/1.0 (+https://github.com/Aniket2002/filing-lens)"
        },
    ) as client:
        for doc in documents:
            record = lock[doc["id"]]
            if record["url"] != doc["url"]:
                raise ValueError(f"Source URL differs from lock: {doc['id']}")
            path = raw / f"{doc['id']}.pdf"
            if not path.exists():
                last_error = None
                for url in [record["url"], *mirrors.get(doc["id"], [])]:
                    for attempt in range(3):
                        try:
                            response = client.get(url)
                            response.raise_for_status()
                            if digest(response.content) != record["sha256"]:
                                raise ValueError(f"Downloaded source changed: {doc['id']}")
                            path.write_bytes(response.content)
                            print(f"Downloaded locked source from {url}", flush=True)
                            break
                        except httpx.HTTPError as exc:
                            last_error = exc
                            print(
                                f"HTTP attempt {attempt + 1} failed for {doc['id']}: {exc}",
                                flush=True,
                            )
                            if attempt < 2:
                                time.sleep(2 ** (attempt + 1))
                    if path.exists():
                        break
                if not path.exists():
                    raise RuntimeError(
                        f"All locked source endpoints failed: {doc['id']}"
                    ) from last_error
            if (
                path.stat().st_size != record["bytes"]
                or digest(path.read_bytes()) != record["sha256"]
            ):
                raise ValueError(f"Cached source differs from lock: {doc['id']}")
            print(f"Verified source {doc['id']}", flush=True)
    # Parsing cannot mutate tracked locks or replace a user's existing corpus.
    with tempfile.TemporaryDirectory(prefix="filing-lens-replay-") as temporary:
        stage = Path(temporary)
        (stage / "data/raw").mkdir(parents=True)
        for name in ("corpus.json", "source-lock.json"):
            shutil.copyfile(root / "data" / name, stage / "data" / name)
        for doc in documents:
            name = f"{doc['id']}.pdf"
            shutil.copyfile(raw / name, stage / "data/raw" / name)
        parse(stage)
        enrich_statements(stage)
        data = (stage / "data/processed/pages.jsonl").read_bytes()
        if digest(data) != expected:
            raise ValueError("Fresh parsing differs from the locked replay corpus")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
    print(f"Reconstructed and verified parsed corpus: {expected}", flush=True)


if __name__ == "__main__":
    prepare(Path(__file__).resolve().parents[1])

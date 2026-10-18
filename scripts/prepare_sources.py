"""Explicit network + parsing step; never required for unit tests."""

from pathlib import Path

from filing_lens.corpus import download, parse
from filing_lens.table_layout import enrich_statements

root = Path(__file__).resolve().parents[1]
download(root)
parse(root)
enrich_statements(root)

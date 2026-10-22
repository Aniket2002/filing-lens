"""Conservative metadata routing and a small, explicit financial vocabulary.

Only query text and corpus metadata enter this module, never benchmark labels.
Report years are deliberately not filters: filings contain comparative periods.
"""

from __future__ import annotations

import re
from collections import defaultdict

PROFILES = ("baseline", "entity", "finance")

# Domain vocabulary, not query-specific rewrites. Expansion affects BM25 only;
# neural models always receive the user's original question.
FINANCIAL_TERMS = (
    (r"\brevenue\b|\bnet sales\b|\btop.line\b", "revenue revenues net sales"),
    (r"\bnet (?:income|loss|profit)\b|\bbottom.line\b", "net income loss earnings"),
    (r"\b(?:EPS|diluted)\b|\bearnings per (?:common )?share\b", "diluted earnings per share"),
    (
        r"\bR\s*&\s*D\b|\bresearch\b|\bdevelopment (?:cost|expense|spend)",
        "research development expenses",
    ),
    (r"\btotal assets?\b|\basset base\b", "total assets"),
)


def plan_query(query: str, documents: list[dict], profile: str = "baseline") -> dict:
    if profile not in PROFILES:
        raise ValueError(f"Unknown retrieval profile: {profile}")
    aliases = defaultdict(set)
    if profile != "baseline":
        for doc in documents:
            names = [doc["company"], doc["ticker"], *doc.get("aliases", [])]
            # Recognize Micron/Microchip/NXP without an issuer-specific lookup.
            short = re.sub(r"\s+(?:Technology|Semiconductors)$", "", doc["company"], flags=re.I)
            names.append(short)
            for name in names:
                aliases[name.casefold()].add(doc["id"])
    matched = []
    doc_ids = set()
    for alias, ids in sorted(aliases.items()):
        # Short tickers must be explicit uppercase symbols (e.g. MU).
        pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
        match = (
            re.search(pattern, query, re.I)
            if len(alias) > 2
            else re.search(r"(?<!\w)" + re.escape(alias.upper()) + r"(?!\w)", query)
        )
        if match:
            matched.append(match.group())
            doc_ids.update(ids)
    terms = []
    if profile == "finance":
        for pattern, expansion in FINANCIAL_TERMS:
            if re.search(pattern, query, re.I):
                terms.extend(expansion.split())
    terms = list(dict.fromkeys(terms))
    return {
        "profile": profile,
        "doc_ids": sorted(doc_ids) if doc_ids else None,
        "matched_aliases": matched,
        "routing": "explicit_entities" if doc_ids else "all_documents",
        "lexical_query": query + (" " + " ".join(terms) if terms else ""),
        "expansion_terms": terms,
    }

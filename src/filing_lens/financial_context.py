"""Conservative resolution of normalized financial disclosures at an as-of time.

This is a context resolver, not an XBRL parser, taxonomy validator, financial
annotation service, or automatic detector of restatements. Supersession links
must come from checked disclosure provenance. A later date alone is insufficient.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Publication and as-of timestamps require an explicit timezone")
    return result


@dataclass(frozen=True)
class Context:
    entity_scheme: str
    entity: str
    concept: str
    period_kind: str
    start: str | None
    end: str
    unit: str
    dimensions: tuple[tuple[str, str], ...]
    basis: str

    def __post_init__(self):
        if not all((self.entity_scheme, self.entity, self.concept, self.unit, self.basis)):
            raise ValueError("Entity, qualified concept, unit and accounting basis are required")
        end = date.fromisoformat(self.end)
        if self.period_kind == "instant":
            if self.start is not None:
                raise ValueError("Instant contexts cannot have a start date")
        elif self.period_kind == "duration":
            if self.start is None or date.fromisoformat(self.start) > end:
                raise ValueError("Duration contexts require start <= end")
        else:
            raise ValueError("Period kind must be instant or duration")
        dimensions = tuple(sorted(self.dimensions))
        if len({axis for axis, _ in dimensions}) != len(dimensions):
            raise ValueError("A context cannot bind an axis twice")
        if any(not axis or not member for axis, member in dimensions):
            raise ValueError("Dimensions require explicit axis and member identifiers")
        object.__setattr__(self, "dimensions", dimensions)


@dataclass(frozen=True)
class Disclosure:
    id: str
    context: Context
    value: str
    published_at: str
    source_url: str
    accession: str
    supersedes: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.id or not self.source_url or not self.accession:
            raise ValueError("Disclosure ID, source URL and accession are required")
        if not Decimal(self.value).is_finite():
            raise ValueError("Disclosure value must be finite")
        timestamp(self.published_at)
        if self.id in self.supersedes or len(set(self.supersedes)) != len(self.supersedes):
            raise ValueError("Invalid supersession identifiers")


def resolve(disclosures: list[Disclosure], requested: Context, as_of: str) -> dict:
    """Use exact context matching and explicit supersession; refuse conflicts.

    Values must already be expressed in the context's named unit. No currency
    conversion, period approximation, or rounded-duplicate equivalence is inferred.
    Context completeness and the validity of supersession are caller obligations.
    """
    cutoff = timestamp(as_of)
    by_id = {d.id: d for d in disclosures}
    if len(by_id) != len(disclosures):
        raise ValueError("Duplicate disclosure ID")
    # Filter by knowledge time first. Future disclosures and their relationships
    # cannot change a historical answer or invalidate an otherwise usable history.
    available = {d.id: d for d in disclosures if timestamp(d.published_at) <= cutoff}
    superseded = set()
    for disclosure in available.values():
        for prior_id in disclosure.supersedes:
            prior = available.get(prior_id)
            if prior is None:
                raise ValueError("Superseded disclosure must be present and already published")
            if disclosure.context != prior.context:
                raise ValueError("Supersession cannot change financial context")
            if timestamp(disclosure.published_at) <= timestamp(prior.published_at):
                raise ValueError("Supersession must be strictly later than the original")
            superseded.add(prior_id)
    selected = [d for d in available.values() if d.context == requested and d.id not in superseded]
    values = {Decimal(d.value) for d in selected}
    status = "numeric" if len(values) == 1 else "conflict" if values else "missing_evidence"
    return {
        "status": status,
        "value": format(next(iter(values)), "f") if status == "numeric" else None,
        "unit": requested.unit,
        "citations": sorted(d.id for d in selected),
        "sources": sorted({d.source_url for d in selected}),
    }

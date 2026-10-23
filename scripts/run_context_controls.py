"""Exercise synthetic context controls; these are not real restatement observations."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

from filing_lens.financial_context import Context, Disclosure, resolve
from filing_lens.io import digest, read_json, write_json


def controls() -> list[dict]:
    base = Context(
        "synthetic",
        "EXAMPLE",
        "{urn:example}Revenue",
        "duration",
        "2023-01-01",
        "2023-12-31",
        "USD",
        dimensions=(),
        basis="US_GAAP",
    )
    original = Disclosure(
        "original",
        base,
        "100",
        "2024-02-01T10:00:00Z",
        "https://example.invalid/original",
        "SYNTHETIC-1",
    )
    revised = replace(
        original,
        id="revision",
        value="90",
        published_at="2024-03-01T10:00:00Z",
        accession="SYNTHETIC-2",
        source_url="https://example.invalid/revision",
        supersedes=("original",),
    )
    conflicting = replace(revised, id="unlinked", supersedes=())
    before, after = "2024-02-15T00:00:00Z", "2024-04-01T00:00:00Z"
    examples = [
        ("historical_before_revision", [original, revised], base, before, "numeric", "100"),
        (
            "at_revision_publication",
            [original, revised],
            base,
            revised.published_at,
            "numeric",
            "90",
        ),
        ("explicit_supersession", [original, revised], base, after, "numeric", "90"),
        ("later_date_is_not_supersession", [original, conflicting], base, after, "conflict", None),
        ("future_fact_unavailable", [revised], base, before, "missing_evidence", None),
        (
            "before_any_publication",
            [original],
            base,
            "2024-01-01T00:00:00Z",
            "missing_evidence",
            None,
        ),
        (
            "same_value_duplicates",
            [original, replace(original, id="duplicate")],
            base,
            after,
            "numeric",
            "100",
        ),
    ]
    changed_contexts = {
        "segment_scope": replace(base, dimensions=(("{urn:example}SegmentAxis", "Cloud"),)),
        "currency": replace(base, unit="EUR"),
        "quarterly_duration": replace(base, start="2023-10-01"),
        "instant_vs_duration": replace(base, period_kind="instant", start=None),
        "adjusted_basis": replace(base, basis="adjusted"),
        "different_entity": replace(base, entity="ANOTHER"),
        "different_entity_scheme": replace(base, entity_scheme="other-scheme"),
        "different_taxonomy": replace(base, concept="{urn:different-taxonomy}Revenue"),
    }
    for name, context in changed_contexts.items():
        distractor = replace(original, id=name, context=context, value="999")
        examples.append((name, [original, distractor], base, after, "numeric", "100"))
        examples.append((name + "_alone", [distractor], base, after, "missing_evidence", None))
    rows = []
    for name, disclosures, context, as_of, status, value in examples:
        output = resolve(disclosures, context, as_of)
        if (output["status"], output["value"]) != (status, value):
            raise ValueError(f"Failed context control: {name}")
        rows.append(
            {"control": name, "expected_status": status, "expected_value": value, "output": output}
        )
    for name, disclosures in (
        ("duplicate_id_rejected", [original, original]),
        ("missing_prior_rejected", [revised]),
        (
            "cross_context_supersession_rejected",
            [original, replace(revised, context=changed_contexts["currency"])],
        ),
        (
            "nonchronological_supersession_rejected",
            [original, replace(revised, published_at=original.published_at)],
        ),
    ):
        try:
            resolve(disclosures, base, after)
        except ValueError:
            rows.append(
                {"control": name, "expected_status": "invalid_input", "output": "invalid_input"}
            )
        else:
            raise ValueError(f"Failed rejection control: {name}")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = {
        "status": "Synthetic controls only; zero real restatements or reviewed XBRL filings",
        "inputs": {
            p: digest((root / p).read_bytes())
            for p in ("src/filing_lens/financial_context.py", "scripts/run_context_controls.py")
        },
        "controls": controls(),
    }
    target = root / "research/document-interventions/context-controls.json"
    if args.check:
        if report != read_json(target):
            raise ValueError("Context control artifact changed")
    else:
        write_json(target, report)
    print(f"{'Verified' if args.check else 'Recorded'} {len(report['controls'])} context controls")


if __name__ == "__main__":
    main()

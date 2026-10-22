from types import SimpleNamespace

import numpy as np
import pytest

from filing_lens.query_planning import plan_query
from filing_lens.retrieval import Index, ranked, reciprocal_rank_fusion, tokenize

DOCS = [
    {"id": "MU-2023", "company": "Micron Technology", "ticker": "MU"},
    {"id": "MU-2024", "company": "Micron Technology", "ticker": "MU"},
    {"id": "AMD-2023", "company": "Advanced Micro Devices", "ticker": "AMD"},
]


def chunk(idx, doc_id, text):
    return {"id": str(idx), "doc_id": doc_id, "text": text, "page": 1, "start": 0, "end": len(text)}


@pytest.mark.parametrize("query", ["Micron FY2022 revenue", "MU revenue", "$MU revenue"])
def test_entity_routing_keeps_comparative_years_and_multiple_filings(query):
    plan = plan_query(query, DOCS, "entity")
    assert plan["doc_ids"] == ["MU-2023", "MU-2024"]
    assert plan["lexical_query"] == query


def test_no_entity_and_multiple_entities_are_not_forced_to_one_document():
    for query in ("revenue", "premium FY2023 revenue", "mu is a Greek letter"):
        assert plan_query(query, DOCS, "entity")["doc_ids"] is None
    assert plan_query("Compare Micron and AMD", DOCS, "entity")["doc_ids"] == [
        "AMD-2023",
        "MU-2023",
        "MU-2024",
    ]
    assert plan_query("Micron revenue", DOCS, "baseline")["doc_ids"] is None


def test_alias_collision_preserves_all_matching_documents():
    docs = [*DOCS, {"id": "OTHER", "company": "Other", "ticker": "OTH", "aliases": ["Micron"]}]
    assert plan_query("Micron", docs, "entity")["doc_ids"] == ["MU-2023", "MU-2024", "OTHER"]


def test_finance_expansion_is_explicit_and_does_not_invent_values():
    plan = plan_query("Micron R&D costs", DOCS, "finance")
    assert plan["expansion_terms"] == ["research", "development", "expenses"]
    assert plan["lexical_query"].startswith("Micron R&D costs")
    assert plan_query("Explain Micron supply chains", DOCS, "finance")["expansion_terms"] == []


def test_baseline_matches_original_bm25_and_hybrid_orders():
    chunks = [
        chunk(i, "A", text)
        for i, text in enumerate(
            [
                "revenue net sales",
                "research spending",
                "total assets",
                "net income",
                "revenue growth",
            ]
        )
    ]
    index = Index(chunks, SimpleNamespace(), dense=False)
    query = "net revenue"
    lexical = ranked(index.bm25.get_scores(tokenize(query)), 3)
    assert [c["id"] for c in index.search(query, "bm25", pool=3)["chunks"]] == [
        str(i) for i in lexical
    ]
    index.embeddings = np.asarray([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5], [0.2, 0.8], [0.8, 0.2]])
    vector = np.asarray([0.0, 1.0])
    dense = ranked(index.embeddings @ vector, 3)
    result = index.search(query, "hybrid", pool=3, query_vector=vector)
    assert [c["id"] for c in result["chunks"]] == [
        str(i) for i in reciprocal_rank_fusion([lexical, dense])[:3]
    ]


@pytest.mark.parametrize("method", ["bm25", "dense", "hybrid"])
def test_metadata_filter_applies_before_every_candidate_generator(method):
    chunks = [
        chunk(0, "AMD-2023", "revenue revenue"),
        chunk(1, "MU-2023", "sales"),
        chunk(2, "MU-2024", "income"),
    ]
    index = Index(chunks, SimpleNamespace(), dense=False, documents=DOCS)
    index.embeddings = np.asarray([[1.0, 0.0], [0.0, 1.0], [0.0, 0.5]])
    result = index.search(
        "Micron revenue",
        method,
        pool=1,
        candidate_pool=2,
        query_vector=np.asarray([1.0, 0.0]),
        profile="entity",
    )
    assert {c["doc_id"] for c in result["candidates"]} == {"MU-2023", "MU-2024"}
    assert result["eligible_chunks"] == 2 and result["candidate_count"] == 2
    assert len(result["chunks"]) == 1


def test_wider_candidate_pool_can_rescue_result_and_trace_matches_scores():
    class Reranker:
        def predict(self, pairs, **kwargs):
            assert len(pairs) == 3
            assert all(query == "net revenue" for query, _ in pairs)
            return [0.0, 1.0, 9.0]

    chunks = [
        chunk(i, "A", text)
        for i, text in enumerate(
            [
                "net revenue",
                "net loss",
                "annual income",
            ]
        )
    ]
    index = Index(chunks, SimpleNamespace(reranker=Reranker()), dense=False)
    result = index.search(
        "net revenue", "bm25", pool=1, candidate_pool=3, rerank=True, profile="finance"
    )
    assert result["chunks"][0] == result["candidates"][2]
    assert result["trace"][0]["candidate_rank"] == 3
    assert result["trace"][0]["reranker_score"] == 9.0
    assert result["trace"][0]["rank"] == 1


def test_expansion_does_not_change_dense_encoder_input():
    class Encoder:
        def encode(self, query, **kwargs):
            assert query == "Micron R&D costs"
            return np.asarray([1.0, 0.0])

    index = Index(
        [chunk(0, "MU-2023", "research and development costs")],
        SimpleNamespace(encoder=Encoder()),
        dense=False,
        documents=DOCS,
    )
    index.embeddings = np.asarray([[1.0, 0.0]])
    found = index.search("Micron R&D costs", "hybrid", pool=1, profile="finance")
    assert found["query_plan"]["expansion_terms"]
    assert found["trace"][0]["rrf_score"] == 2 / 61


def test_empty_index_and_absent_entity_do_not_call_models():
    index = Index([], SimpleNamespace(), dense=False, documents=DOCS)
    assert index.search("revenue", rerank=True)["chunks"] == []
    index = Index([chunk(0, "AMD-2023", "revenue")], SimpleNamespace(), dense=False, documents=DOCS)
    assert index.search("Micron revenue", profile="entity", rerank=True)["candidate_count"] == 0


@pytest.mark.parametrize(
    "kwargs",
    [{"pool": 0}, {"pool": 3, "candidate_pool": 2}, {"profile": "unknown"}, {"method": "unknown"}],
)
def test_invalid_search_options_fail_before_loading_models(kwargs):
    index = Index([], SimpleNamespace(), dense=False)
    with pytest.raises(ValueError):
        index.search("query", **kwargs)

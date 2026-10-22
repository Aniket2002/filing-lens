"""BM25, normalized dense retrieval, RRF, and a pinned learned cross-encoder.

This module does not import evaluation labels or answer annotations.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from filing_lens.io import digest, read_json
from filing_lens.query_planning import plan_query


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]+|\d+(?:\.\d+)?", text.lower())


def ranked(scores: np.ndarray, k: int) -> list[int]:
    # Stable, explicit index tie break (argpartition would make ties arbitrary).
    return np.argsort(-scores, kind="stable")[:k].tolist()


def reciprocal_rank_fusion(rankings: list[list[int]], constant: int = 60) -> list[int]:
    scores = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking, 1):
            scores[idx] = scores.get(idx, 0.0) + 1 / (constant + rank)
    return sorted(scores, key=lambda idx: (-scores[idx], idx))


class Models:
    def __init__(self, root: Path):
        import torch

        torch.set_num_threads(4)
        torch.manual_seed(17)
        self.root = root
        self.lock = read_json(root / "data/model-lock.json")
        self._encoder = self._reranker = None

    @property
    def encoder(self):
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer

            name = "sentence-transformers/all-MiniLM-L6-v2"
            self._encoder = SentenceTransformer(name, revision=self.lock[name], device="cpu")
        return self._encoder

    @property
    def reranker(self):
        if self._reranker is None:
            from sentence_transformers import CrossEncoder

            name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
            self._reranker = CrossEncoder(
                name, revision=self.lock[name], device="cpu", max_length=384
            )
        return self._reranker


class Index:
    def __init__(
        self,
        chunks: list[dict],
        models: Models,
        dense: bool = True,
        documents: list[dict] | None = None,
    ):
        self.chunks, self.models = chunks, models
        self.documents = documents or []
        self.doc_indices: dict[str, list[int]] = {}
        for i, chunk in enumerate(chunks):
            self.doc_indices.setdefault(chunk["doc_id"], []).append(i)
        tokens = [tokenize(c["text"]) for c in chunks]
        self.bm25 = BM25Okapi(tokens) if any(tokens) else None
        self.embeddings = None
        if dense and chunks:
            name = "sentence-transformers/all-MiniLM-L6-v2"
            fingerprint = digest(
                (models.lock[name] + "\n" + "\n".join(c["text"] for c in chunks)).encode()
            )
            cache = models.root / ".cache" / f"embeddings-{fingerprint}.npy"
            cache.parent.mkdir(parents=True, exist_ok=True)
            if cache.exists():
                self.embeddings = np.load(cache, allow_pickle=False)
            else:
                self.embeddings = models.encoder.encode(
                    [c["text"] for c in chunks],
                    batch_size=32,
                    normalize_embeddings=True,
                    show_progress_bar=True,
                    convert_to_numpy=True,
                )
                np.save(cache, self.embeddings, allow_pickle=False)

    def search(
        self,
        query: str,
        method: str = "hybrid",
        pool: int = 20,
        rerank: bool = False,
        query_vector: np.ndarray | None = None,
        *,
        candidate_pool: int | None = None,
        profile: str = "baseline",
    ) -> dict:
        if method not in {"bm25", "dense", "hybrid"}:
            raise ValueError(f"Unknown retrieval method: {method}")
        depth = pool if candidate_pool is None else candidate_pool
        if not isinstance(pool, int) or not isinstance(depth, int) or not 1 <= pool <= depth:
            raise ValueError("Require 1 <= pool <= candidate_pool")
        plan = plan_query(query, self.documents, profile)
        eligible = (
            sorted(i for doc_id in plan["doc_ids"] for i in self.doc_indices.get(doc_id, []))
            if plan["doc_ids"] is not None
            else list(range(len(self.chunks)))
        )
        # Load model outside measured per-query inference time.
        if rerank and eligible:
            _ = self.models.reranker
        start = time.perf_counter()
        lexical_scores = np.zeros(len(eligible))
        if self.bm25 is not None and method != "dense":
            lexical_scores = np.asarray(
                self.bm25.get_batch_scores(tokenize(plan["lexical_query"]), eligible)
            )
        lexical = [eligible[i] for i in ranked(lexical_scores, depth)]
        dense, dense_scores = [], np.zeros(len(eligible))
        if method != "bm25" and eligible:
            if self.embeddings is None:
                raise ValueError("Dense retrieval requires embeddings")
            if query_vector is None:
                query_vector = self.models.encoder.encode(query, normalize_embeddings=True)
            dense_scores = self.embeddings[eligible] @ query_vector
            dense = [eligible[i] for i in ranked(dense_scores, depth)]
            order = dense if method == "dense" else reciprocal_rank_fusion([lexical, dense])[:depth]
        else:
            order = lexical
        retrieval_ms = (time.perf_counter() - start) * 1000
        candidates = list(order)
        rerank_ms = 0.0
        reranker_scores = {}
        if rerank and order:
            start = time.perf_counter()
            scores = self.models.reranker.predict(
                [(query, self.chunks[i]["text"]) for i in order],
                batch_size=32,
                show_progress_bar=False,
            )
            scores = np.asarray(scores).reshape(-1)
            reranker_scores = {idx: float(score) for idx, score in zip(order, scores, strict=True)}
            order = [order[i] for i in ranked(scores, len(order))]
            rerank_ms = (time.perf_counter() - start) * 1000
        lexical_ranks = {idx: rank for rank, idx in enumerate(lexical, 1)}
        dense_ranks = {idx: rank for rank, idx in enumerate(dense, 1)}
        candidate_ranks = {idx: rank for rank, idx in enumerate(candidates, 1)}
        positions = {idx: position for position, idx in enumerate(eligible)}
        trace = []
        for rank, idx in enumerate(order[:pool], 1):
            position = positions[idx]
            trace.append(
                {
                    **{
                        key: self.chunks[idx][key]
                        for key in ("id", "doc_id", "page", "start", "end")
                    },
                    "rank": rank,
                    "candidate_rank": candidate_ranks[idx],
                    "bm25_rank": lexical_ranks.get(idx) if method != "dense" else None,
                    "bm25_score": float(lexical_scores[position]) if method != "dense" else None,
                    "dense_rank": dense_ranks.get(idx),
                    "dense_score": float(dense_scores[position]) if method != "bm25" else None,
                    "rrf_score": sum(
                        1 / (60 + ranks[idx])
                        for ranks in (lexical_ranks, dense_ranks)
                        if idx in ranks
                    )
                    if method == "hybrid"
                    else None,
                    "reranker_score": reranker_scores.get(idx),
                }
            )
        return {
            "chunks": [self.chunks[i] for i in order[:pool]],
            "candidates": [self.chunks[i] for i in candidates],
            "trace": trace,
            "query_plan": plan,
            "eligible_chunks": len(eligible),
            "candidate_count": len(candidates),
            "candidate_pool": depth,
            "retrieval_ms": retrieval_ms,
            "rerank_ms": rerank_ms,
        }

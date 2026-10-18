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
    def __init__(self, chunks: list[dict], models: Models, dense: bool = True):
        self.chunks, self.models = chunks, models
        self.bm25 = BM25Okapi([tokenize(c["text"]) for c in chunks])
        self.embeddings = None
        if dense:
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
    ) -> dict:
        if method not in {"bm25", "dense", "hybrid"}:
            raise ValueError(f"Unknown retrieval method: {method}")
        # Load model outside measured per-query inference time.
        if rerank:
            _ = self.models.reranker
        start = time.perf_counter()
        lexical = ranked(self.bm25.get_scores(tokenize(query)), pool)
        if method != "bm25":
            if self.embeddings is None:
                raise ValueError("Dense retrieval requires embeddings")
            if query_vector is None:
                query_vector = self.models.encoder.encode(query, normalize_embeddings=True)
            dense = ranked(self.embeddings @ query_vector, pool)
            order = dense if method == "dense" else reciprocal_rank_fusion([lexical, dense])[:pool]
        else:
            order = lexical
        retrieval_ms = (time.perf_counter() - start) * 1000
        rerank_ms = 0.0
        if rerank:
            start = time.perf_counter()
            scores = self.models.reranker.predict(
                [(query, self.chunks[i]["text"]) for i in order],
                batch_size=32,
                show_progress_bar=False,
            )
            order = [order[i] for i in ranked(np.asarray(scores).reshape(-1), len(order))]
            rerank_ms = (time.perf_counter() - start) * 1000
        return {
            "chunks": [self.chunks[i] for i in order],
            "retrieval_ms": retrieval_ms,
            "rerank_ms": rerank_ms,
        }

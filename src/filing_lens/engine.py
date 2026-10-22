"""Shared CLI/API inference path. No questions, annotations, or gold answers are read."""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from filing_lens.chunking import chunk_pages
from filing_lens.io import read_json, read_jsonl
from filing_lens.query_planning import PROFILES
from filing_lens.reader import answer_question
from filing_lens.retrieval import Index, Models

READERS = ("extractive", "flan-t5", "flan-t5-base", "flan-t5-explain")


class QueryEngine:
    def __init__(
        self,
        root: Path,
        config: str | None = None,
        reader: str = "extractive",
        assemble_table_evidence: bool = True,
        retrieval_profile: str = "baseline",
        candidate_pool: int = 20,
    ):
        if reader not in READERS:
            raise ValueError(f"Unknown reader: {reader}")
        if retrieval_profile not in PROFILES:
            raise ValueError(f"Unknown retrieval profile: {retrieval_profile}")
        if not isinstance(candidate_pool, int) or not 20 <= candidate_pool <= 200:
            raise ValueError("candidate_pool must be between 20 and 200")
        self.retrieval_profile, self.candidate_pool = retrieval_profile, candidate_pool
        if config is None:
            reference = root / "results/reference/run.json"
            config = (
                read_json(reference)["selected_on_dev"] if reference.exists() else "structure-bm25"
            )
        parts = config.split("-")
        if (
            len(parts) not in (2, 3)
            or parts[0] not in {"fixed", "structure"}
            or parts[1] not in {"bm25", "dense", "hybrid"}
            or (len(parts) == 3 and parts[2] != "rerank")
        ):
            raise ValueError("Invalid config; use {fixed,structure}-{bm25,dense,hybrid}[-rerank]")
        self.root, self.config, self.reader = root, config, reader
        self.method, self.rerank = parts[1], len(parts) == 3
        self.assemble_table_evidence = assemble_table_evidence
        self.documents = read_json(root / "data/corpus.json")["documents"]
        self.doc_map = {d["id"]: d for d in self.documents}
        pages = read_jsonl(root / "data/processed/pages.jsonl")
        self.page_text = {(p["doc_id"], p["page"]): p["text"] for p in pages}
        self.tables = {t["id"]: t for t in read_jsonl(root / "data/processed/tables.jsonl")}
        chunks = chunk_pages(pages, self.documents, parts[0])
        models = Models(root)
        self.index = Index(chunks, models, dense=self.method != "bm25", documents=self.documents)
        if self.rerank:
            _ = models.reranker
        self.generator = None
        self.explainer = None
        if reader == "flan-t5-explain":
            from filing_lens.explanations import ExplanationReader

            self.explainer = ExplanationReader(root)
        elif reader != "extractive":
            from filing_lens.generation import LocalGenerator

            lock = root / "data/generator-v2-lock.json" if reader == "flan-t5-base" else None
            self.generator = LocalGenerator(root, lock)
        self._lock = Lock()

    def ask(self, question: str) -> dict:
        if not isinstance(question, str) or not question.strip() or len(question) > 2000:
            raise ValueError("question must contain 1 to 2000 characters")
        # Keep model inference bounded to one concurrent CPU request.
        with self._lock:
            found = self.index.search(
                question,
                method=self.method,
                rerank=self.rerank,
                profile=self.retrieval_profile,
                candidate_pool=self.candidate_pool,
            )
            if self.explainer is not None:
                evidence = [
                    {
                        "chunk_id": chunk["id"],
                        "doc_id": chunk["doc_id"],
                        "page": chunk["page"],
                        "start": chunk["start"],
                        "end": chunk["end"],
                        "quote": self.page_text[(chunk["doc_id"], chunk["page"])][
                            chunk["start"] : chunk["end"]
                        ],
                    }
                    for chunk in found["chunks"][:5]
                ]
                answer = self.explainer.answer(question, evidence)
            else:
                answer = answer_question(
                    question,
                    found["chunks"],
                    self.tables,
                    self.documents,
                    assemble_table_evidence=self.assemble_table_evidence,
                )
            if self.generator is not None:
                from filing_lens.generation import gate_generated

                if self.reader == "flan-t5-base":
                    from filing_lens.generator_experiment import generation_context

                    context = generation_context(answer, found["chunks"], self.tables, self.doc_map)
                elif answer["claims"]:
                    context = "\n".join(
                        c.get("header", "") + "\n" + c["quote"] for c in answer["citations"]
                    )
                    context += "\nUnit: " + answer["claims"][0]["unit"]
                else:
                    context = "\n".join(c["text"][:600] for c in found["chunks"][:2])
                raw = self.generator.generate(question, context)
                answer = gate_generated(raw, answer, self.tables, self.doc_map)
                answer["raw_generation"] = raw
        for citation in answer["citations"]:
            citation["url"] = self.doc_map[citation["doc_id"]]["url"] + f"#page={citation['page']}"
        for chunk in found["trace"]:
            chunk["url"] = self.doc_map[chunk["doc_id"]]["url"] + f"#page={chunk['page']}"
        return {
            **answer,
            "config": self.config,
            "reader": self.reader,
            "retrieval": {
                key: found[key]
                for key in (
                    "query_plan",
                    "eligible_chunks",
                    "candidate_count",
                    "candidate_pool",
                    "retrieval_ms",
                    "rerank_ms",
                    "trace",
                )
            },
            "table_evidence_assembly": self.assemble_table_evidence and self.explainer is None,
        }

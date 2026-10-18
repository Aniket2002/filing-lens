"""Shared CLI/API inference path. No questions, annotations, or gold answers are read."""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from filing_lens.chunking import chunk_pages
from filing_lens.io import read_json, read_jsonl
from filing_lens.reader import answer_question
from filing_lens.retrieval import Index, Models

READERS = ("extractive", "flan-t5", "flan-t5-base")


class QueryEngine:
    def __init__(
        self,
        root: Path,
        config: str | None = None,
        reader: str = "extractive",
        assemble_table_evidence: bool = True,
    ):
        if reader not in READERS:
            raise ValueError(f"Unknown reader: {reader}")
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
        self.tables = {t["id"]: t for t in read_jsonl(root / "data/processed/tables.jsonl")}
        chunks = chunk_pages(pages, self.documents, parts[0])
        models = Models(root)
        self.index = Index(chunks, models, dense=self.method != "bm25")
        if self.rerank:
            _ = models.reranker
        self.generator = None
        if reader != "extractive":
            from filing_lens.generation import LocalGenerator

            lock = root / "data/generator-v2-lock.json" if reader == "flan-t5-base" else None
            self.generator = LocalGenerator(root, lock)
        self._lock = Lock()

    def ask(self, question: str) -> dict:
        if not isinstance(question, str) or not question.strip() or len(question) > 2000:
            raise ValueError("question must contain 1 to 2000 characters")
        # Keep model inference bounded to one concurrent CPU request.
        with self._lock:
            found = self.index.search(question, method=self.method, rerank=self.rerank)
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
        return {
            **answer,
            "config": self.config,
            "reader": self.reader,
            "table_evidence_assembly": self.assemble_table_evidence,
        }

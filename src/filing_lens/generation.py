"""A separately scored local generative reader and a deterministic output gate.

The main retrieval ablations do not depend on this adapter. It is intentionally
restricted to numeric questions and amount-only output. No hosted API is used.
"""

from __future__ import annotations

import re
import time
from copy import deepcopy
from pathlib import Path

from filing_lens.io import read_json, read_jsonl, write_json, write_jsonl
from filing_lens.numeric import number, verify_answer_numbers, verify_claim
from filing_lens.reader import answer_question, refuse


def generated_amount(text: str):
    text = text.strip().replace("$", "").strip()
    if re.fullmatch(r"\(?-?\d[\d,]*(?:\.\d+)?\)?", text):
        return number(text)
    return None


def gate_generated(raw: str, candidate: dict, tables: dict, documents: dict) -> dict:
    if candidate["refused"]:
        return candidate
    amount = generated_amount(raw)
    if amount is None or not candidate["claims"]:
        return refuse("generator_did_not_return_a_single_amount")
    result = deepcopy(candidate)
    claim = result["claims"][0]
    claim["value"] = str(amount)
    check = verify_claim(claim, tables, documents)
    if not check["supported"]:
        return refuse("generated_amount_disagrees_with_source_cell")
    # The surface response is a standardized rendering of the verified claim.
    # A fluent model sentence is never silently treated as verified.
    original_amount = candidate["claims"][0]["value"]
    result["answer"] = result["answer"].replace(f"{number(original_amount):,}", f"{amount:,}", 1)
    result["numeric_checks"] = [check, verify_answer_numbers(result["answer"], claim)]
    if not all(check["supported"] for check in result["numeric_checks"]):
        return refuse("generated_answer_surface_verification_failed")
    return result


class LocalGenerator:
    def __init__(self, root: Path, lock_path: Path | None = None):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        torch.set_num_threads(4)
        torch.manual_seed(17)
        self.lock = read_json(lock_path or root / "data/generator-lock.json")
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.lock["model"], revision=self.lock["revision"]
        )
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            self.lock["model"], revision=self.lock["revision"]
        )
        self.model.eval()

    def generate(self, question: str, context: str) -> str:
        import torch

        template = self.lock.get("prompt_template")
        prompt = (
            template.format(question=question, context=context)
            if template
            else (
                "Answer the financial question using only the context. Return just one signed "
                "number in the source's unit, with no words. Parentheses mean negative. "
                "If the answer is missing, return UNKNOWN.\n"
                f"Question: {question}\nContext: {context}\nAnswer:"
            )
        )
        inputs = self.tokenizer(
            prompt, return_tensors="pt", truncation=True, max_length=self.lock["max_input_tokens"]
        )
        with torch.inference_mode():
            output = self.model.generate(
                **inputs, max_new_tokens=self.lock["max_new_tokens"], do_sample=False, num_beams=1
            )
        return self.tokenizer.decode(output[0], skip_special_tokens=True)


def audit_generator(root: Path, result_path: Path, output: Path) -> None:
    """Reuse a frozen retrieval run; do not select or retrieve using gold answers."""
    from filing_lens.evaluation import aggregate, score_answer

    run = read_json(result_path / "run.json")
    selected = run["selected_on_dev"]
    questions = {q["id"]: q for q in read_jsonl(root / "data/questions.jsonl")}
    predictions = [
        r
        for r in read_jsonl(result_path / "predictions.jsonl")
        if r["config"] == selected and r["kind"] != "narrative"
    ]
    chunks = {
        c["id"]: c
        for c in read_jsonl(root / f"data/processed/chunks-{selected.split('-')[0]}.jsonl")
    }
    tables = {t["id"]: t for t in read_jsonl(root / "data/processed/tables.jsonl")}
    pages = {(p["doc_id"], p["page"]): p for p in read_jsonl(root / "data/processed/pages.jsonl")}
    documents = read_json(root / "data/corpus.json")["documents"]
    doc_map = {d["id"]: d for d in documents}
    generator = LocalGenerator(root)
    rows = []
    for row in predictions:
        q = questions[row["question_id"]]
        context_chunks = [chunks[c["id"]] for c in row["ranking"][:5]]
        candidate = answer_question(q["question"], context_chunks, tables, documents)
        # The extractive reader can compact complete rows, but cannot synthesize
        # missing evidence. This keeps the tiny model inside its token budget.
        if not candidate["refused"] and candidate["claims"]:
            context = "\n".join(
                c["doc_id"] + " " + c.get("header", "") + "\n" + c["quote"]
                for c in candidate["citations"]
            )
            context += "\nUnit: " + candidate["claims"][0]["unit"]
        else:
            context = "\n".join(c["text"][:600] for c in context_chunks[:2])
        start = time.perf_counter()
        raw = generator.generate(q["question"], context)
        response = gate_generated(raw, candidate, tables, doc_map)
        amount = generated_amount(raw)
        raw_correct = (
            (amount is not None and amount == number(q["expected_value"]))
            if q["answerable"]
            else amount is None
        )
        rows.append(
            {
                **{
                    key: row[key]
                    for key in [
                        "config",
                        "question_id",
                        "company",
                        "kind",
                        "split",
                        "answerable",
                        "recall_at_1",
                        "recall_at_5",
                        "recall_at_10",
                        "mrr_at_20",
                    ]
                },
                "raw_output": raw,
                "raw_correct": raw_correct,
                "raw_amount": str(amount) if amount is not None else None,
                "context": context,
                "response": response,
                "query_ms": (time.perf_counter() - start) * 1000,
                **score_answer(q, response, pages),
            }
        )
        print(
            f"Generator {q['id']}: {raw!r} -> {'refuse' if response['refused'] else 'verified'}",
            flush=True,
        )
    summaries = []
    for split in ("dev", "test"):
        subset = [r for r in rows if r["split"] == split]
        answered = [r for r in subset if r["answerable"]]
        absent = [r for r in subset if not r["answerable"]]
        summaries.append(
            {
                "split": split,
                **aggregate(subset),
                "raw_amount_correctness": sum(r["raw_correct"] for r in answered) / len(answered),
                "raw_non_numeric_rate_on_unanswerables": sum(
                    r["raw_amount"] is None for r in absent
                )
                / len(absent),
            }
        )
    write_jsonl(output / "predictions.jsonl", rows)
    write_json(output / "metrics.json", summaries)
    write_json(
        output / "run.json",
        {
            "generator_lock": generator.lock,
            "retrieval_config": selected,
            "scope": "50 numeric + 20 unanswerable; narratives excluded",
            "context_policy": (
                "complete visible source rows if available; otherwise first two retrieved snippets"
            ),
            "decoding": "greedy; CPU; four threads",
            "source_run": str(result_path.relative_to(root)),
        },
    )

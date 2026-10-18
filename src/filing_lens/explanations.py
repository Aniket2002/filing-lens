"""Experimental explanations and answerability decisions generated from supplied evidence.

No numeric reader, financial intent rules, or gold labels enter this inference path.
Source references identify model inputs; they do not certify generated claims.
"""

from __future__ import annotations

import re
from pathlib import Path

from filing_lens.generation import LocalGenerator
from filing_lens.io import read_json
from filing_lens.reader import refuse


def model_decision(raw: str) -> str:
    label = raw.strip().casefold().rstrip(".! ")
    return label if label in {"yes", "no"} else "invalid"


class ExplanationReader:
    def __init__(self, root: Path):
        self.lock = read_json(root / "data/explanations/model-lock.json")
        self.backend = LocalGenerator(root, root / "data/explanations/model-lock.json")

    def prepare_context(self, question: str, evidence: list[dict]) -> tuple[str, list[dict]]:
        """Budget both prompts before inference; never truncate away the question."""

        def fits(context):
            return all(
                len(
                    self.backend.tokenizer(template.format(question=question, context=context))[
                        "input_ids"
                    ]
                )
                <= self.lock["max_input_tokens"]
                for template in (self.lock["prompt_template"], self.lock["answerability_template"])
            )

        if not fits(""):
            raise ValueError("Question exceeds the model input budget")
        context, included = "", []
        for item in evidence:
            prefix = f"[{item['doc_id']} PDF p{item['page']}]\n"
            text = item["quote"]
            remaining = len(text)
            low, high = 0, remaining
            while low < high:
                middle = (low + high + 1) // 2
                if fits(context + prefix + text[:middle] + "\n"):
                    low = middle
                else:
                    high = middle - 1
            if low == 0:
                break
            shown = text[:low]
            context += prefix + shown + "\n"
            source = {**item, "quote": shown, "input_excerpt_truncated": low < remaining}
            if "start" in source:
                source["end"] = source["start"] + low
            included.append(source)
            if low < remaining:
                break
        return context, included

    def answer(self, question: str, evidence: list[dict]) -> dict:
        import torch

        context, included = self.prepare_context(question, evidence)
        prompt = self.lock["answerability_template"].format(question=question, context=context)
        inputs = self.backend.tokenizer(prompt, return_tensors="pt", truncation=False)
        with torch.inference_mode():
            output = self.backend.model.generate(
                **inputs, max_new_tokens=4, do_sample=False, num_beams=1
            )
        raw_decision = self.backend.tokenizer.decode(output[0], skip_special_tokens=True)
        decision = model_decision(raw_decision)
        raw_answer = self.backend.generate(question, context) if decision == "yes" else None
        if decision != "yes":
            response = refuse(
                "model_judged_context_insufficient"
                if decision == "no"
                else "model_answerability_protocol_error"
            )
        else:
            response = {
                "answer": raw_answer,
                "refused": False,
                "reason": None,
                "claims": [],
                "numeric_checks": [],
                "citations": [{**item, "role": "input_context"} for item in included],
            }
        return {
            **response,
            "model_decision": decision,
            "raw_answerability": raw_decision,
            "raw_generation": raw_answer,
            "model_refused": decision == "no",
            "protocol_error": decision == "invalid",
            "verification_status": "unverified_generation" if decision == "yes" else "no_answer",
            "citation_supported": None,
            "input_context": context,
            "input_sources": included,
        }


def screen_concepts(answer: str | None, concepts: list[list[str]]) -> dict:
    """A transparent coverage screen, not a semantic correctness or entailment judge."""
    covered = [
        any(re.search(pattern, answer or "", re.I) for pattern in group) for group in concepts
    ]
    return {"concepts_covered": covered, "all_concepts_covered": bool(covered) and all(covered)}


def summarize(rows: list[dict]) -> dict:
    positives = [r for r in rows if r["answerable"]]
    negatives = [r for r in rows if not r["answerable"]]
    answered = [r for r in positives if r["response"]["model_decision"] == "yes"]

    def rate(items, predicate):
        return sum(predicate(r) for r in items) / len(items) if items else None

    return {
        "questions": len(rows),
        "answerable": len(positives),
        "unanswerable_in_context": len(negatives),
        "model_refusal_on_unanswerables": rate(negatives, lambda r: r["response"]["model_refused"]),
        "model_false_refusal_on_answerables": rate(
            positives, lambda r: r["response"]["model_refused"]
        ),
        "model_false_accept_on_unanswerables": rate(
            negatives, lambda r: r["response"]["model_decision"] == "yes"
        ),
        "answerable_coverage": len(answered) / len(positives) if positives else None,
        "protocol_errors": sum(r["response"]["protocol_error"] for r in rows),
        "all_concepts_covered_on_answerables": rate(positives, lambda r: r["all_concepts_covered"]),
        "all_concepts_covered_given_answer": rate(answered, lambda r: r["all_concepts_covered"]),
        "human_answer_correctness": None,
        "human_citation_entailment": None,
        "human_reviews_completed": 0,
    }

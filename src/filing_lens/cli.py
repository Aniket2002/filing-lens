"""Network access is explicit; the benchmark and demo run locally after setup."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from filing_lens.io import read_json, read_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="filing-lens", description="Audit retrieval on real filings"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="Download and SHA-256-check the ten source PDFs")
    sub.add_parser("parse", help="Parse source PDFs into canonical pages and tables")
    sub.add_parser("validate", help="Validate frozen benchmark input hashes and gold spans")
    bench = sub.add_parser("benchmark", help="Run 12 ablations and preserve individual predictions")
    bench.add_argument("--output", type=Path, default=Path("results/reproduced"))
    bench.add_argument("--lexical-only", action="store_true", help="Two BM25 chunking baselines")
    ask = sub.add_parser(
        "ask", help="Ask a source-cited question without access to evaluation labels"
    )
    ask.add_argument("question")
    ask.add_argument(
        "--config", default=None, help="E.g. structure-hybrid-rerank; default: dev-selected"
    )
    ask.add_argument("--json", action="store_true", dest="as_json")
    ask.add_argument("--reader", choices=["extractive", "flan-t5"], default="extractive")
    report = sub.add_parser(
        "report", help="Render measured results as Markdown, PNG, and standalone HTML"
    )
    report.add_argument("--results", type=Path, default=Path("results/reference"))
    report.add_argument("--output", type=Path, default=Path("docs/report"))
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "fetch":
            from filing_lens.corpus import download

            download(root)
        elif args.command == "parse":
            from filing_lens.corpus import parse
            from filing_lens.table_layout import enrich_statements

            parse(root)
            enrich_statements(root)
        elif args.command == "validate":
            from filing_lens.benchmark import validate_dataset

            lock = validate_dataset(root)
            pages = {
                (p["doc_id"], p["page"]): p for p in read_jsonl(root / "data/processed/pages.jsonl")
            }
            for q in read_jsonl(root / "data/questions.jsonl"):
                for g in q["gold"]:
                    if pages[(g["doc_id"], g["page"])]["text"][g["start"] : g["end"]] != g["quote"]:
                        raise ValueError(f"Broken gold anchor: {q['id']}")
            Console().print(
                f"[green]Validated {lock['question_count']} questions "
                "and all frozen input hashes[/green]"
            )
        elif args.command == "benchmark":
            from filing_lens.benchmark import run

            run(root, root / args.output, args.lexical_only)
        elif args.command == "report":
            from filing_lens.reporting import render

            render(root, root / args.results, root / args.output)
        elif args.command == "ask":
            from filing_lens.chunking import chunk_pages
            from filing_lens.reader import answer_question
            from filing_lens.retrieval import Index, Models

            config = args.config
            if config is None:
                reference = root / "results/reference/run.json"
                config = (
                    read_json(reference)["selected_on_dev"]
                    if reference.exists()
                    else "structure-bm25"
                )
            parts = config.split("-")
            if (
                len(parts) not in (2, 3)
                or parts[0] not in {"fixed", "structure"}
                or parts[1] not in {"bm25", "dense", "hybrid"}
                or (len(parts) == 3 and parts[2] != "rerank")
            ):
                raise ValueError(
                    "Invalid --config; use {fixed,structure}-{bm25,dense,hybrid}[-rerank]"
                )
            strategy, method = parts[:2]
            rerank = len(parts) == 3
            documents = read_json(root / "data/corpus.json")["documents"]
            pages = read_jsonl(root / "data/processed/pages.jsonl")
            tables = {t["id"]: t for t in read_jsonl(root / "data/processed/tables.jsonl")}
            chunks = chunk_pages(pages, documents, strategy)
            index = Index(chunks, Models(root), dense=method != "bm25")
            found = index.search(args.question, method=method, rerank=rerank)
            answer = answer_question(args.question, found["chunks"], tables, documents)
            if args.reader == "flan-t5":
                from filing_lens.generation import LocalGenerator, gate_generated

                if answer["claims"]:
                    context = "\n".join(
                        c.get("header", "") + "\n" + c["quote"] for c in answer["citations"]
                    )
                    context += "\nUnit: " + answer["claims"][0]["unit"]
                else:
                    context = "\n".join(c["text"][:600] for c in found["chunks"][:2])
                raw = LocalGenerator(root).generate(args.question, context)
                answer = gate_generated(raw, answer, tables, {d["id"]: d for d in documents})
                answer["raw_generation"] = raw
            docs = {d["id"]: d for d in documents}
            for citation in answer["citations"]:
                citation["url"] = docs[citation["doc_id"]]["url"] + f"#page={citation['page']}"
            if args.as_json:
                print(json.dumps(answer, indent=2, ensure_ascii=True))
            else:
                console = Console()
                console.print(
                    Panel(
                        answer["answer"],
                        title=f"Filing Lens · {config}",
                        border_style="yellow" if answer["refused"] else "cyan",
                    )
                )
                for citation in answer["citations"]:
                    console.print(
                        f"[bold]{citation['doc_id']} · PDF page {citation['page']}[/bold]"
                    )
                    console.print(citation["quote"], markup=False)
                    console.print(citation["url"], markup=False)
                if answer["numeric_checks"]:
                    console.print(
                        "[green]PASS: amount, source cell, entity, year, and unit agree[/green]"
                    )
                if answer["refused"]:
                    console.print(f"Evidence gate: {answer['reason']}")
    except (FileNotFoundError, ValueError) as exc:
        parser.exit(2, f"Error: {exc}\nRun fetch, parse, then validate from the repository root.\n")


if __name__ == "__main__":
    main()

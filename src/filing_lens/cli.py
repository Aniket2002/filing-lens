"""Network access is explicit; the benchmark and demo run locally after setup."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from filing_lens.engine import READERS
from filing_lens.io import read_jsonl


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
    bench.add_argument("--config", help="Run one configuration instead of the full ablation set")
    bench.add_argument("--split", choices=["dev", "test"], help="Run only one company split")
    bench.add_argument(
        "--assemble-table-evidence",
        action="store_true",
        help="Opt in to joining retrieved same-page table headers and rows",
    )
    ask = sub.add_parser(
        "ask", help="Ask a source-cited question without access to evaluation labels"
    )
    ask.add_argument("question")
    ask.add_argument(
        "--config", default=None, help="E.g. structure-hybrid-rerank; default: dev-selected"
    )
    ask.add_argument("--json", action="store_true", dest="as_json")
    ask.add_argument("--reader", choices=READERS, default="extractive")
    ask.add_argument(
        "--assemble-table-evidence",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Join retrieved same-page table headers and rows (default: enabled)",
    )
    serve = sub.add_parser("serve", help="Run a local JSON API with health and request metrics")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--config", default=None)
    serve.add_argument("--reader", choices=READERS, default="extractive")
    serve.add_argument("--max-in-flight", type=int, default=4)
    serve.add_argument(
        "--queue-timeout", type=float, default=5.0, help="Maximum queue wait in seconds"
    )
    serve.add_argument(
        "--assemble-table-evidence", action=argparse.BooleanOptionalAction, default=True
    )
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

            run(
                root,
                root / args.output,
                args.lexical_only,
                args.config,
                args.split,
                args.assemble_table_evidence,
            )
        elif args.command == "report":
            from filing_lens.reporting import render

            render(root, root / args.results, root / args.output)
        elif args.command == "serve":
            from filing_lens.engine import QueryEngine
            from filing_lens.service import create_server

            engine = QueryEngine(root, args.config, args.reader, args.assemble_table_evidence)
            with create_server(
                engine,
                args.host,
                args.port,
                max_in_flight=args.max_in_flight,
                queue_timeout=args.queue_timeout,
            ) as server:
                Console(stderr=True).print(
                    f"Local API: http://{args.host}:{server.server_port} (Ctrl+C to stop)"
                )
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
        elif args.command == "ask":
            from filing_lens.engine import QueryEngine

            engine = QueryEngine(root, args.config, args.reader, args.assemble_table_evidence)
            config = engine.config
            answer = engine.ask(args.question)
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
                if answer.get("verification_status") == "unverified_generation":
                    console.print(
                        "Unverified explanation; source references show model input context."
                    )
                if answer["refused"]:
                    console.print(f"Evidence gate: {answer['reason']}")
    except (FileNotFoundError, ValueError) as exc:
        parser.exit(2, f"Error: {exc}\nRun fetch, parse, then validate from the repository root.\n")


if __name__ == "__main__":
    main()

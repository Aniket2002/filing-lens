"""Local HTTP demonstration with health, readiness, metrics, and structured logs."""

from __future__ import annotations

import json
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock


class Metrics:
    def __init__(self):
        self.lock = Lock()
        self.started = time.monotonic()
        self.values = {
            "requests": 0,
            "errors": 0,
            "answers": 0,
            "refusals": 0,
            "numeric_verification_failures": 0,
            "duration_seconds_sum": 0.0,
            "duration_seconds_max": 0.0,
        }

    def record(self, status: int, elapsed: float, result: dict):
        with self.lock:
            self.values["requests"] += 1
            self.values["errors"] += int(status >= 400)
            if status == 200:
                self.values["refusals"] += int(result.get("refused", False))
                self.values["answers"] += int(not result.get("refused", True))
                self.values["numeric_verification_failures"] += int(
                    result.get("reason")
                    in {
                        "numeric_verification_failed",
                        "generated_amount_disagrees_with_source_cell",
                        "generated_answer_surface_verification_failed",
                    }
                )
            self.values["duration_seconds_sum"] += elapsed
            self.values["duration_seconds_max"] = max(self.values["duration_seconds_max"], elapsed)

    def snapshot(self):
        with self.lock:
            return {**self.values, "uptime_seconds": time.monotonic() - self.started}


def create_server(engine, host: str = "127.0.0.1", port: int = 8000, log=None):
    metrics = Metrics()
    if log is None:

        def log(event):
            print(json.dumps(event), file=sys.stderr, flush=True)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def respond(self, status, body, request_id=None):
            payload = json.dumps(body, ensure_ascii=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            if request_id:
                self.send_header("X-Request-ID", request_id)
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/health":
                self.respond(200, {"status": "ok"})
            elif self.path == "/ready":
                self.respond(
                    200, {"status": "ready", "config": engine.config, "reader": engine.reader}
                )
            elif self.path == "/metrics":
                self.respond(200, metrics.snapshot())
            else:
                self.respond(404, {"error": "not_found"})

        def do_POST(self):
            request_id = uuid.uuid4().hex
            start = time.perf_counter()
            status, result = 500, {"error": "internal_error"}
            try:
                if self.path != "/ask":
                    status, result = 404, {"error": "not_found"}
                elif self.headers.get("Transfer-Encoding"):
                    status, result = 400, {"error": "transfer_encoding_not_supported"}
                elif self.headers.get_content_type() != "application/json":
                    status, result = 415, {"error": "content_type_must_be_application_json"}
                else:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 16384:
                        status, result = 413, {"error": "body_must_contain_1_to_16384_bytes"}
                    else:
                        body = json.loads(self.rfile.read(length))
                        if not isinstance(body, dict) or set(body) != {"question"}:
                            raise ValueError("Body must contain only question")
                        question = body["question"]
                        if (
                            not isinstance(question, str)
                            or not question.strip()
                            or len(question) > 2000
                        ):
                            raise ValueError("question must contain 1 to 2000 characters")
                        try:
                            result = engine.ask(question)
                            status = 200
                        except Exception:
                            status, result = 500, {"error": "inference_failed"}
            except (ValueError, UnicodeError) as exc:
                status, result = 400, {"error": "invalid_request", "detail": str(exc)}
            except Exception:
                status, result = 500, {"error": "inference_failed"}
            elapsed = time.perf_counter() - start
            metrics.record(status, elapsed, result)
            log(
                {
                    "event": "ask",
                    "request_id": request_id,
                    "status": status,
                    "duration_seconds": elapsed,
                    "refused": result.get("refused"),
                    "reason": result.get("reason"),
                }
            )
            self.respond(status, result, request_id)

    return ThreadingHTTPServer((host, port), Handler)

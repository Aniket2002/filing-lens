"""Local HTTP demonstration with health, readiness, metrics, and structured logs."""

from __future__ import annotations

import json
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import BoundedSemaphore, Lock


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
            "model_refusals": 0,
            "model_protocol_errors": 0,
            "unverified_answers": 0,
            "overload_rejections": 0,
            "queue_timeouts": 0,
            "in_flight": 0,
            "queue_seconds_sum": 0.0,
            "duration_seconds_sum": 0.0,
            "duration_seconds_max": 0.0,
        }

    def record(self, status: int, elapsed: float, result: dict, queue_seconds: float = 0):
        with self.lock:
            self.values["requests"] += 1
            self.values["errors"] += int(status >= 400)
            self.values["overload_rejections"] += int(result.get("error") == "server_busy")
            self.values["queue_timeouts"] += int(result.get("error") == "queue_timeout")
            self.values["queue_seconds_sum"] += queue_seconds
            if status == 200:
                self.values["refusals"] += int(result.get("refused", False))
                self.values["answers"] += int(not result.get("refused", True))
                self.values["model_refusals"] += int(result.get("model_refused", False))
                self.values["model_protocol_errors"] += int(result.get("protocol_error", False))
                self.values["unverified_answers"] += int(
                    result.get("verification_status") == "unverified_generation"
                    and not result.get("refused", True)
                )
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


def create_server(
    engine,
    host: str = "127.0.0.1",
    port: int = 8000,
    log=None,
    *,
    max_in_flight: int = 4,
    queue_timeout: float = 5.0,
):
    import math

    if isinstance(max_in_flight, bool) or not isinstance(max_in_flight, int) or max_in_flight < 1:
        raise ValueError("max_in_flight must be a positive integer")
    if not math.isfinite(queue_timeout) or queue_timeout < 0:
        raise ValueError("queue_timeout must be finite and nonnegative")
    metrics = Metrics()
    admission = BoundedSemaphore(max_in_flight)
    inference = Lock()
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
            if status == 503:
                self.send_header("Retry-After", "1")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/health":
                self.respond(200, {"status": "ok"})
            elif self.path == "/ready":
                self.respond(
                    200,
                    {
                        "status": "ready",
                        "config": engine.config,
                        "reader": engine.reader,
                        "retrieval_profile": getattr(engine, "retrieval_profile", "baseline"),
                        "candidate_pool": getattr(engine, "candidate_pool", 20),
                        "max_in_flight": max_in_flight,
                        "queue_timeout_seconds": queue_timeout,
                    },
                )
            elif self.path == "/metrics":
                self.respond(200, metrics.snapshot())
            else:
                self.respond(404, {"error": "not_found"})

        def do_POST(self):
            request_id = uuid.uuid4().hex
            start = time.perf_counter()
            queue_seconds = 0.0
            status, result = 500, {"error": "internal_error"}
            try:
                if self.path != "/ask":
                    status, result = 404, {"error": "not_found"}
                elif self.headers.get("Transfer-Encoding"):
                    status, result = 400, {"error": "transfer_encoding_not_supported"}
                elif self.headers.get_content_type() != "application/json":
                    status, result = 415, {"error": "content_type_must_be_application_json"}
                else:
                    lengths = self.headers.get_all("Content-Length", [])
                    if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
                        raise ValueError("Exactly one nonnegative Content-Length is required")
                    length = int(lengths[0])
                    if length <= 0 or length > 16384:
                        status, result = 413, {"error": "body_must_contain_1_to_16384_bytes"}
                    else:
                        payload = self.rfile.read(length)
                        if len(payload) != length:
                            raise ValueError("Incomplete request body")
                        body = json.loads(payload.decode("utf-8"))
                        if not isinstance(body, dict) or set(body) != {"question"}:
                            raise ValueError("Body must contain only question")
                        question = body["question"]
                        if (
                            not isinstance(question, str)
                            or not question.strip()
                            or len(question) > 2000
                        ):
                            raise ValueError("question must contain 1 to 2000 characters")
                        if not admission.acquire(blocking=False):
                            status, result = 503, {"error": "server_busy"}
                        else:
                            with metrics.lock:
                                metrics.values["in_flight"] += 1
                            try:
                                queued = time.perf_counter()
                                acquired = inference.acquire(timeout=queue_timeout)
                                queue_seconds = time.perf_counter() - queued
                                if not acquired:
                                    status, result = 503, {"error": "queue_timeout"}
                                else:
                                    try:
                                        result = engine.ask(question)
                                        status = 200
                                    except Exception:
                                        status, result = 500, {"error": "inference_failed"}
                                    finally:
                                        inference.release()
                            finally:
                                with metrics.lock:
                                    metrics.values["in_flight"] -= 1
                                admission.release()
            except (ValueError, UnicodeError) as exc:
                status, result = 400, {"error": "invalid_request", "detail": str(exc)}
            except TimeoutError:
                status, result = 408, {"error": "request_timeout"}
            except Exception:
                status, result = 500, {"error": "inference_failed"}
            elapsed = time.perf_counter() - start
            metrics.record(status, elapsed, result, queue_seconds)
            log(
                {
                    "event": "ask",
                    "request_id": request_id,
                    "status": status,
                    "duration_seconds": elapsed,
                    "queue_seconds": queue_seconds,
                    "error": result.get("error"),
                    "refused": result.get("refused"),
                    "reason": result.get("reason"),
                    "model_refused": result.get("model_refused"),
                    "verification_status": result.get("verification_status"),
                }
            )
            try:
                self.respond(status, result, request_id)
            except (ConnectionError, TimeoutError):
                # A disconnected client must not leak admission slots or log a traceback.
                self.close_connection = True

    return ThreadingHTTPServer((host, port), Handler)

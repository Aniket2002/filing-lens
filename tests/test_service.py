import json
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from threading import Event, Thread

import pytest

from filing_lens.service import create_server


class FakeEngine:
    config = "fixed-bm25"
    reader = "extractive"

    def ask(self, question):
        if question == "crash":
            raise RuntimeError("private filesystem details")
        if question == "invalid_model_output":
            raise ValueError("private inference details")
        if question == "model_missing":
            return {"refused": True, "model_refused": True, "protocol_error": False}
        if question == "draft":
            return {"refused": False, "verification_status": "unverified_generation"}
        return {"answer": "evidence", "refused": question == "missing", "reason": None}


@pytest.fixture
def api():
    events = []
    with create_server(FakeEngine(), port=0, log=events.append) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield server.server_port, events
        server.shutdown()
        thread.join(timeout=5)


def request(api, method, path, body=None, content_type="application/json"):
    connection = HTTPConnection("127.0.0.1", api[0], timeout=5)
    connection.request(method, path, body=body, headers={"Content-Type": content_type})
    response = connection.getresponse()
    result = response.status, dict(response.headers), json.loads(response.read())
    connection.close()
    return result


def test_service_serves_answers_and_measures_errors_and_refusals(api):
    assert request(api, "GET", "/health")[2] == {"status": "ok"}
    assert request(api, "GET", "/ready")[2]["config"] == "fixed-bm25"
    status, headers, answer = request(api, "POST", "/ask", json.dumps({"question": "revenue"}))
    assert status == 200 and not answer["refused"]
    assert headers["X-Request-ID"] == api[1][0]["request_id"]
    assert request(api, "POST", "/ask", json.dumps({"question": "missing"}))[2]["refused"]
    status, _, result = request(api, "POST", "/ask", json.dumps({"question": "crash"}))
    assert status == 500 and result == {"error": "inference_failed"}
    assert request(api, "POST", "/ask", json.dumps({"question": "model_missing"}))[2][
        "model_refused"
    ]
    assert request(api, "POST", "/ask", json.dumps({"question": "draft"}))[0] == 200
    status, _, result = request(
        api, "POST", "/ask", json.dumps({"question": "invalid_model_output"})
    )
    assert status == 500 and result == {"error": "inference_failed"}
    metrics = request(api, "GET", "/metrics")[2]
    assert metrics["requests"] == 6 and metrics["errors"] == 2
    assert metrics["answers"] == metrics["refusals"] == 2
    assert metrics["model_refusals"] == metrics["unverified_answers"] == 1
    assert metrics["duration_seconds_sum"] >= metrics["duration_seconds_max"] > 0
    assert all("question" not in event and "answer" not in event for event in api[1])


@pytest.mark.parametrize(
    "body",
    ["{", "[]", "null", '{"question":1}', '{"question":""}', '{"question":"x","config":"other"}'],
)
def test_service_rejects_invalid_inputs_without_inference(api, body):
    assert request(api, "POST", "/ask", body)[0] == 400
    assert request(api, "GET", "/metrics")[2]["answers"] == 0


def test_service_enforces_payload_limits_and_routes(api):
    assert request(api, "POST", "/ask", "{}", "text/plain")[0] == 415
    assert request(api, "POST", "/ask", "x" * 16385)[0] == 413
    assert request(api, "POST", "/ask", json.dumps({"question": "x" * 2001}))[0] == 400
    assert request(api, "POST", "/unknown", "{}")[0] == 404
    assert request(api, "GET", "/unknown")[0] == 404


@pytest.mark.parametrize(
    "options",
    [
        {"max_in_flight": 0},
        {"max_in_flight": True},
        {"max_in_flight": 1.5},
        {"queue_timeout": -1},
        {"queue_timeout": float("inf")},
        {"queue_timeout": float("nan")},
    ],
)
def test_invalid_admission_settings_fail_before_listening(options):
    with pytest.raises(ValueError):
        create_server(FakeEngine(), port=0, **options)


class BlockingEngine(FakeEngine):
    def __init__(self):
        self.entered, self.release = Event(), Event()
        self.calls = 0

    def ask(self, question):
        self.calls += 1
        if question == "block":
            self.entered.set()
            assert self.release.wait(timeout=5), "Test did not release inference"
        return super().ask(question)


@pytest.mark.parametrize("capacity,error", [(1, "server_busy"), (2, "queue_timeout")])
def test_overload_is_bounded_and_health_stays_responsive(capacity, error):
    engine, events = BlockingEngine(), []
    with create_server(
        engine, port=0, log=events.append, max_in_flight=capacity, queue_timeout=0.05
    ) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        api = server.server_port, events
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                first = pool.submit(request, api, "POST", "/ask", '{"question":"block"}')
                try:
                    assert engine.entered.wait(timeout=3)
                    status, headers, result = request(api, "POST", "/ask", '{"question":"next"}')
                    assert status == 503 and result == {"error": error}
                    assert headers["Retry-After"] == "1" and headers["X-Request-ID"]
                    assert engine.calls == 1
                    assert request(api, "GET", "/health")[0] == 200
                    metrics = request(api, "GET", "/metrics")[2]
                    assert metrics["in_flight"] == 1
                    assert metrics["overload_rejections"] == int(capacity == 1)
                    assert metrics["queue_timeouts"] == int(capacity == 2)
                finally:
                    engine.release.set()
                assert first.result(timeout=3)[0] == 200
            # Slots are recovered after both timeout and successful completion.
            assert request(api, "POST", "/ask", '{"question":"next"}')[0] == 200
            assert request(api, "GET", "/metrics")[2]["in_flight"] == 0
            assert request(api, "POST", "/ask", '{"question":"crash"}')[0] == 500
            assert request(api, "POST", "/ask", '{"question":"next"}')[0] == 200
        finally:
            engine.release.set()
            server.shutdown()
            thread.join(timeout=5)


def test_ambiguous_content_length_is_rejected_without_inference(api):
    connection = HTTPConnection("127.0.0.1", api[0], timeout=5)
    try:
        connection.putrequest("POST", "/ask")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", "2")
        connection.putheader("Content-Length", "10")
        connection.endheaders(b"{}")
        response = connection.getresponse()
        assert response.status == 400
        assert json.loads(response.read())["error"] == "invalid_request"
    finally:
        connection.close()
    assert request(api, "GET", "/metrics")[2]["answers"] == 0

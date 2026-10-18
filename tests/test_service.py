import json
from http.client import HTTPConnection
from threading import Thread

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

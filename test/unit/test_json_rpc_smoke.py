"""Controlled JSON-RPC smoke tests that do not contact confd."""

from __future__ import annotations

import json
from collections.abc import (
    Iterator,
    Sequence,
)
from dataclasses import (
    dataclass,
    field,
)
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from threading import (
    Event,
    Thread,
)
from typing import Any
from urllib.error import (
    HTTPError,
    URLError,
)
from urllib.request import (
    Request,
    urlopen,
)

import pytest

# pylint: disable=redefined-outer-name


class JsonRpcClientError(RuntimeError):
    """Raised when a JSON-RPC exchange cannot produce a safe result."""


@dataclass
class _JsonRpcController:
    requests: list[dict[str, Any]] = field(default_factory=list)
    release_delayed_response: Event = field(default_factory=Event)


@dataclass
class _JsonRpcRequest:
    method: str
    params: dict[str, object]
    request_id: str
    timeout: float
    sensitive_values: Sequence[str] = ()


class _JsonRpcSmokeHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802  # pylint: disable=invalid-name
        """Return controlled responses for the smoke-test JSON-RPC methods."""
        content_length = int(self.headers["Content-Length"])
        request = json.loads(self.rfile.read(content_length))
        controller = self.server.controller  # type: ignore[attr-defined]
        controller.requests.append(request)

        method = request["method"]
        if method == "smoke.echo":
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": request["params"],
            }
        elif method == "smoke.error":
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {
                    "code": -32010,
                    "message": f"request rejected for {request['params']['token']}",
                },
            }
        elif method == "smoke.mismatched_id":
            response = {"jsonrpc": "2.0", "id": "different-request", "result": {}}
        elif method == "smoke.timeout":
            controller.release_delayed_response.wait(timeout=1)
            response = {"jsonrpc": "2.0", "id": request["id"], "result": {}}
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {"code": -32601, "message": "method not found"},
            }

        encoded_response = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded_response)))
        self.end_headers()
        try:
            self.wfile.write(encoded_response)
        except BrokenPipeError:
            pass

    def log_message(  # pylint: disable=redefined-builtin
        self,
        format: str,
        *args: object,
    ) -> None:
        """Suppress fixture request logging so test payloads are not emitted."""


@dataclass
class _JsonRpcEndpoint:
    url: str
    controller: _JsonRpcController


@pytest.fixture
def json_rpc_endpoint() -> Iterator[_JsonRpcEndpoint]:
    """Run a controlled JSON-RPC endpoint on loopback for one test."""
    controller = _JsonRpcController()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _JsonRpcSmokeHandler)
    server.controller = controller  # type: ignore[attr-defined]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address

    try:
        yield _JsonRpcEndpoint(
            url=f"http://{host}:{port}/json-rpc", controller=controller
        )
    finally:
        controller.release_delayed_response.set()
        server.shutdown()
        thread.join()
        server.server_close()


def _redact(message: str, sensitive_values: Sequence[str]) -> str:
    for value in sensitive_values:
        message = message.replace(value, "********")
    return message


def _call_json_rpc(
    endpoint: str,
    json_rpc_request: _JsonRpcRequest,
) -> object:
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": json_rpc_request.method,
            "params": json_rpc_request.params,
            "id": json_rpc_request.request_id,
        }
    ).encode("utf-8")
    request = Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(
            request, timeout=json_rpc_request.timeout
        ) as response:  # noqa: S310 -- controlled loopback test fixture
            response_payload = json.loads(response.read())
    except (HTTPError, TimeoutError, URLError) as error:
        message = _redact(str(error), json_rpc_request.sensitive_values)
        raise JsonRpcClientError(f"JSON-RPC request failed: {message}") from error

    if response_payload.get("id") != json_rpc_request.request_id:
        raise JsonRpcClientError("JSON-RPC response ID did not match the request ID")

    if error := response_payload.get("error"):
        message = _redact(
            str(error.get("message", "unknown error")),
            json_rpc_request.sensitive_values,
        )
        raise JsonRpcClientError(f"JSON-RPC error {error.get('code')}: {message}")

    if "result" not in response_payload:
        raise JsonRpcClientError("JSON-RPC response did not contain a result")

    return response_payload["result"]


# [itest -> dsn~generic-json-rpc-client-viability~1]
def test_json_rpc_smoke_round_trip_serializes_and_correlates_request_id(
    json_rpc_endpoint: _JsonRpcEndpoint,
) -> None:
    """Verify a local JSON-RPC request round trip is reproducible."""
    result = _call_json_rpc(
        json_rpc_endpoint.url,
        _JsonRpcRequest(
            method="smoke.echo",
            params={"value": "ready"},
            request_id="smoke-request-1",
            timeout=1,
        ),
    )

    assert result == {"value": "ready"}
    assert json_rpc_endpoint.controller.requests == [
        {
            "jsonrpc": "2.0",
            "method": "smoke.echo",
            "params": {"value": "ready"},
            "id": "smoke-request-1",
        }
    ]


# [itest -> dsn~generic-json-rpc-client-viability~1]
def test_json_rpc_smoke_rejects_a_response_with_another_request_id(
    json_rpc_endpoint: _JsonRpcEndpoint,
) -> None:
    """Verify response correlation rejects a mismatched JSON-RPC request ID."""
    request = _JsonRpcRequest(
        method="smoke.mismatched_id",
        params={},
        request_id="smoke-request-2",
        timeout=1,
    )

    with pytest.raises(
        JsonRpcClientError,
        match="response ID did not match the request ID",
    ):
        _call_json_rpc(json_rpc_endpoint.url, request)


# [itest -> dsn~generic-json-rpc-client-viability~1]
def test_json_rpc_smoke_redacts_a_protocol_error(
    json_rpc_endpoint: _JsonRpcEndpoint,
) -> None:
    """Verify JSON-RPC protocol errors do not expose supplied secret values."""
    token = "json-rpc-secret-token"
    request = _JsonRpcRequest(
        method="smoke.error",
        params={"token": token},
        request_id="smoke-request-3",
        timeout=1,
        sensitive_values=(token,),
    )

    with pytest.raises(JsonRpcClientError) as error:
        _call_json_rpc(json_rpc_endpoint.url, request)

    assert str(error.value) == "JSON-RPC error -32010: request rejected for ********"
    assert token not in str(error.value)


# [itest -> dsn~generic-json-rpc-client-viability~1]
def test_json_rpc_smoke_redacts_timeout_failures(
    json_rpc_endpoint: _JsonRpcEndpoint,
) -> None:
    """Verify a timed-out JSON-RPC request does not expose supplied secrets."""
    token = "json-rpc-secret-token"
    request = _JsonRpcRequest(
        method="smoke.timeout",
        params={"token": token},
        request_id="smoke-request-4",
        timeout=0.01,
        sensitive_values=(token,),
    )

    with pytest.raises(JsonRpcClientError, match="JSON-RPC request failed") as error:
        _call_json_rpc(json_rpc_endpoint.url, request)

    assert token not in str(error.value)

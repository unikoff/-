from __future__ import annotations

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from sys import exc_info

import pytest

from benchmark.client import BenchmarkError, run_benchmark


class BenchmarkHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    body = b"internet-speed-benchmark\n" * 256
    requests = 0
    active_requests = 0
    max_active_requests = 0
    lock = threading.Lock()

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        with self.lock:
            type(self).requests += 1
            type(self).active_requests += 1
            type(self).max_active_requests = max(
                type(self).max_active_requests,
                type(self).active_requests,
            )

        try:
            time.sleep(0.005)
            if self.path == "/error":
                body = b"server error"
                self.send_response(503)
            elif self.path == "/redirect":
                body = b"redirect"
                self.send_response(302)
                self.send_header("Location", "/file")
            elif self.path == "/empty":
                body = b""
                self.send_response(200)
            elif self.path == "/partial":
                body = type(self).body[:128]
                self.send_response(206)
            else:
                body = type(self).body
                self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                # FAILONERROR intentionally stops reading a non-2xx response.
                # The client-side behavior is the thing this test validates.
                pass
        finally:
            with self.lock:
                type(self).active_requests -= 1

    def log_message(self, format: str, *args: object) -> None:
        return


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    def handle_error(self, request: object, client_address: object) -> None:
        # PycURL may close an error response as soon as FAILONERROR sees its
        # status. That is expected in these tests, not a test failure.
        error = exc_info()[1]
        if isinstance(error, (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)):
            return
        super().handle_error(request, client_address)


@pytest.fixture()
def http_server() -> tuple[ThreadingHTTPServer, str]:
    BenchmarkHandler.requests = 0
    BenchmarkHandler.active_requests = 0
    BenchmarkHandler.max_active_requests = 0
    server = QuietThreadingHTTPServer(("127.0.0.1", 0), BenchmarkHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_benchmark_performs_ten_complete_downloads_sequentially(
    http_server: tuple[ThreadingHTTPServer, str],
) -> None:
    _, base_url = http_server

    summary = run_benchmark(base_url + "/file", timeout_seconds=5)

    assert summary.successful_requests == 10
    assert summary.total_downloaded_bytes == len(BenchmarkHandler.body) * 10
    assert BenchmarkHandler.requests == 10
    assert BenchmarkHandler.max_active_requests == 1


def test_http_error_stops_the_run_without_retry(
    http_server: tuple[ThreadingHTTPServer, str],
) -> None:
    _, base_url = http_server

    with pytest.raises(BenchmarkError, match="503"):
        run_benchmark(base_url + "/error", timeout_seconds=5)

    assert BenchmarkHandler.requests == 1


def test_redirect_is_rejected_to_preserve_exact_request_count(
    http_server: tuple[ThreadingHTTPServer, str],
) -> None:
    _, base_url = http_server

    with pytest.raises(BenchmarkError, match="302"):
        run_benchmark(base_url + "/redirect", timeout_seconds=5)

    assert BenchmarkHandler.requests == 1


def test_empty_response_is_not_accepted(
    http_server: tuple[ThreadingHTTPServer, str],
) -> None:
    _, base_url = http_server

    with pytest.raises(BenchmarkError, match="empty"):
        run_benchmark(base_url + "/empty", timeout_seconds=5)


def test_partial_content_is_not_accepted_as_a_complete_file(
    http_server: tuple[ThreadingHTTPServer, str],
) -> None:
    _, base_url = http_server

    with pytest.raises(BenchmarkError, match="206"):
        run_benchmark(base_url + "/partial", timeout_seconds=5)

    assert BenchmarkHandler.requests == 1

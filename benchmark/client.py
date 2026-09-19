"""Sequential streaming HTTP client backed by libcurl through PycURL."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

import pycurl

from .models import BenchmarkSummary, RequestResult
from .statistics import calculate_summary

DEFAULT_REQUEST_COUNT = 10
DEFAULT_CONNECT_TIMEOUT_SECONDS = 10.0
DEFAULT_TIMEOUT_SECONDS = 120.0


class BenchmarkError(RuntimeError):
    """Raised when a request cannot produce a valid benchmark measurement."""


def _as_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


class CurlDownloadClient:
    """Download a response body without storing it on disk or in memory.

    One curl handle is reused for all iterations. That lets libcurl reuse a
    connection when the server allows it, while each response is consumed
    completely before the next call to :meth:`download` starts.
    """

    def __init__(
        self,
        url: str,
        *,
        connect_timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not url:
            raise ValueError("url must not be empty")
        if connect_timeout_seconds <= 0 or timeout_seconds <= 0:
            raise ValueError("timeouts must be greater than zero")

        self.url = url
        self._bytes_received = 0
        curl = pycurl.Curl()
        self._curl: pycurl.Curl | None = curl
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.FOLLOWLOCATION, 1)
        curl.setopt(pycurl.MAXREDIRS, 5)
        curl.setopt(pycurl.CONNECTTIMEOUT_MS, max(1, round(connect_timeout_seconds * 1000)))
        curl.setopt(pycurl.TIMEOUT_MS, max(1, round(timeout_seconds * 1000)))
        curl.setopt(pycurl.NOSIGNAL, 1)
        curl.setopt(pycurl.FAILONERROR, 1)
        curl.setopt(
            pycurl.HTTPHEADER,
            [
                "Accept-Encoding: identity",
                "Cache-Control: no-cache",
                "Pragma: no-cache",
                "User-Agent: internet-speed-benchmark/1.0",
            ],
        )
        curl.setopt(pycurl.WRITEFUNCTION, self._write_chunk)

    def __enter__(self) -> "CurlDownloadClient":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        """Release the libcurl handle and any reusable connection state."""

        if self._curl is not None:
            self._curl.close()
            self._curl = None

    def _write_chunk(self, chunk: bytes) -> int:
        """Count received bytes and immediately discard the body chunk."""

        self._bytes_received += len(chunk)
        return len(chunk)

    def download(self) -> RequestResult:
        """Perform one complete GET and return its measured result."""

        if self._curl is None:
            raise RuntimeError("client is already closed")

        self._bytes_received = 0
        started_at = perf_counter()

        try:
            self._curl.perform()
        except pycurl.error as error:
            status_code = int(self._curl.getinfo(pycurl.RESPONSE_CODE) or 0)
            if status_code:
                raise BenchmarkError(
                    f"HTTP request failed with status {status_code}: {error}",
                ) from error
            raise BenchmarkError(f"HTTP request failed: {error}") from error

        # TOTAL_TIME is measured by libcurl around the transfer. The monotonic
        # clock fallback keeps the result usable with unusual libcurl builds.
        duration = float(self._curl.getinfo(pycurl.TOTAL_TIME) or 0.0)
        if duration <= 0:
            duration = perf_counter() - started_at

        status_code = int(self._curl.getinfo(pycurl.RESPONSE_CODE) or 0)
        if not 200 <= status_code < 300:
            raise BenchmarkError(f"unexpected HTTP status {status_code}")
        if self._bytes_received <= 0:
            raise BenchmarkError("HTTP response body is empty")

        return RequestResult(
            duration_seconds=duration,
            downloaded_bytes=self._bytes_received,
            status_code=status_code,
            effective_url=_as_text(self._curl.getinfo(pycurl.EFFECTIVE_URL)),
        )


def run_benchmark(
    url: str,
    *,
    request_count: int = DEFAULT_REQUEST_COUNT,
    connect_timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    on_result: Callable[[int, RequestResult], None] | None = None,
) -> BenchmarkSummary:
    """Run exactly ``request_count`` downloads sequentially.

    ``on_result`` is called only after one full response has been consumed and
    validated. It is intended for progress output and cannot overlap requests.
    """

    if request_count <= 0:
        raise ValueError("request_count must be greater than zero")

    results: list[RequestResult] = []
    with CurlDownloadClient(
        url,
        connect_timeout_seconds=connect_timeout_seconds,
        timeout_seconds=timeout_seconds,
    ) as client:
        for request_number in range(1, request_count + 1):
            result = client.download()
            results.append(result)
            if on_result is not None:
                on_result(request_number, result)

    return calculate_summary(results)

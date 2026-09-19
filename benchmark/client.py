"""Sequential streaming HTTP client backed by libcurl through PycURL."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from types import TracebackType

import pycurl

from .models import BenchmarkSummary, RequestResult
from .statistics import calculate_summary

DEFAULT_REQUEST_COUNT = 10
DEFAULT_CONNECT_TIMEOUT_SECONDS = 10.0
DEFAULT_TIMEOUT_SECONDS = 120.0
RECEIVE_BUFFER_SIZE_BYTES = 256 * 1024


class BenchmarkError(RuntimeError):
    """Raised when a request cannot produce a valid benchmark measurement."""


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

        curl = pycurl.Curl()
        self._curl: pycurl.Curl | None = curl
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.HTTPGET, 1)
        # A redirect is another HTTP request. Keeping it disabled ensures that
        # ten benchmark iterations always mean exactly ten GET requests.
        curl.setopt(pycurl.FOLLOWLOCATION, 0)
        # Larger chunks reduce Python callback crossings while retaining a
        # fixed, small memory footprint and streaming behavior.
        curl.setopt(pycurl.BUFFERSIZE, RECEIVE_BUFFER_SIZE_BYTES)
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
        curl.setopt(pycurl.WRITEFUNCTION, self._discard_chunk)

    def __enter__(self) -> "CurlDownloadClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Release the libcurl handle and any reusable connection state."""

        if self._curl is not None:
            self._curl.close()
            self._curl = None

    @staticmethod
    def _discard_chunk(chunk: bytes) -> int:
        """Discard one response chunk after libcurl has received it."""

        return len(chunk)

    def download(self) -> RequestResult:
        """Perform one complete GET and return its measured result."""

        if self._curl is None:
            raise RuntimeError("client is already closed")

        started_at = perf_counter()

        try:
            self._curl.perform()
        except pycurl.error as error:
            status_code = int(self._curl.getinfo(pycurl.RESPONSE_CODE) or 0)
            if status_code:
                raise BenchmarkError(f"HTTP request failed with status {status_code}") from error
            error_message = error.args[1] if len(error.args) > 1 else str(error)
            raise BenchmarkError(f"HTTP request failed: {error_message}") from error

        # TOTAL_TIME is measured by libcurl around the transfer. The monotonic
        # clock fallback keeps the result usable with unusual libcurl builds.
        duration = float(self._curl.getinfo(pycurl.TOTAL_TIME) or 0.0)
        if duration <= 0:
            duration = perf_counter() - started_at

        status_code = int(self._curl.getinfo(pycurl.RESPONSE_CODE) or 0)
        if status_code != 200:
            raise BenchmarkError(f"unexpected HTTP status {status_code}")
        downloaded_bytes = int(self._curl.getinfo(pycurl.SIZE_DOWNLOAD_T) or 0)
        if downloaded_bytes <= 0:
            raise BenchmarkError("HTTP response body is empty")

        return RequestResult(
            duration_seconds=duration,
            downloaded_bytes=downloaded_bytes,
            status_code=status_code,
        )


def run_benchmark(
    url: str,
    *,
    request_count: int = DEFAULT_REQUEST_COUNT,
    connect_timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    on_request_start: Callable[[int], None] | None = None,
    on_result: Callable[[int, RequestResult], None] | None = None,
) -> BenchmarkSummary:
    """Run exactly ``request_count`` downloads sequentially.

    ``on_request_start`` runs immediately before one GET starts. ``on_result``
    runs only after the corresponding response is fully consumed and validated.
    They are intended for presentation only and cannot overlap requests.
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
            if on_request_start is not None:
                on_request_start(request_number)
            result = client.download()
            results.append(result)
            if on_result is not None:
                on_result(request_number, result)

    return calculate_summary(results)

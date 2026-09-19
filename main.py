"""Command-line entry point for the Internet Speed Benchmark."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from urllib.parse import urlparse

from benchmark.client import (
    DEFAULT_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_REQUEST_COUNT,
    DEFAULT_TIMEOUT_SECONDS,
    BenchmarkError,
    run_benchmark,
)
from benchmark.models import BenchmarkSummary, RequestResult


def _positive_float(value: str) -> float:
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return number


def _http_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("URL must be an absolute http:// or https:// address")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure sequential download speed from a URL.",
    )
    parser.add_argument("url", type=_http_url, help="URL of a large downloadable file")
    parser.add_argument(
        "--connect-timeout",
        type=_positive_float,
        default=DEFAULT_CONNECT_TIMEOUT_SECONDS,
        help=f"connection timeout in seconds (default: {DEFAULT_CONNECT_TIMEOUT_SECONDS:g})",
    )
    parser.add_argument(
        "--timeout",
        type=_positive_float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"maximum time for one download in seconds (default: {DEFAULT_TIMEOUT_SECONDS:g})",
    )
    return parser


def _print_request(request_number: int, result: RequestResult) -> None:
    print(
        f"  {request_number:02d}/{DEFAULT_REQUEST_COUNT} | "
        f"{result.duration_seconds:8.3f} s | "
        f"{result.downloaded_bytes / 1_000_000:9.2f} MB | "
        f"{result.speed_mb_s:8.2f} MB/s | HTTP {result.status_code}",
    )


def _print_summary(summary: BenchmarkSummary) -> None:
    # Kept separate from the network code so console formatting cannot affect
    # request timing or the statistics calculations.
    print("\nResults")
    print(f"  Successful requests: {summary.successful_requests}/{DEFAULT_REQUEST_COUNT}")
    print(f"  Total downloaded:    {summary.total_downloaded_mb:.2f} MB")
    print(f"  Average time:        {summary.average_time_seconds:.3f} s")
    print(f"  Total transfer time: {summary.total_time_seconds:.3f} s")
    print(f"  Average speed:       {summary.average_speed_mb_s:.2f} MB/s")
    print(f"  Average speed:       {summary.average_speed_mbps:.2f} Mbps")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    print("Internet Speed Benchmark")
    print("=" * 27)
    print(f"Target:  {args.url}")
    print(f"Requests: {DEFAULT_REQUEST_COUNT} (sequential)")
    print()

    try:
        summary = run_benchmark(
            args.url,
            connect_timeout_seconds=args.connect_timeout,
            timeout_seconds=args.timeout,
            on_result=_print_request,
        )
    except BenchmarkError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130

    _print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

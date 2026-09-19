"""Command-line entry point for the Internet Speed Benchmark."""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from urllib.parse import urlparse

from rich.console import Console

from benchmark.client import (
    DEFAULT_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_REQUEST_COUNT,
    DEFAULT_TIMEOUT_SECONDS,
    BenchmarkError,
    run_benchmark,
)
from benchmark.models import RequestResult
from benchmark.renderer import create_progress, print_error, print_header, print_results, print_summary

MARKDOWN_LINK_PATTERN = re.compile(r"^\[[^\]]*\]\((https?://\S+)\)$")


def _positive_float(value: str) -> float:
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return number


def _http_url(value: str) -> str:
    candidate = value.strip()
    markdown_link = MARKDOWN_LINK_PATTERN.fullmatch(candidate)
    if markdown_link is not None:
        candidate = markdown_link.group(1)

    if any(character.isspace() for character in candidate):
        raise argparse.ArgumentTypeError("URL must not contain whitespace")

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("URL must be an absolute http:// or https:// address")
    return candidate


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


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    console = Console()
    results: list[RequestResult] = []

    print_header(console, args.url, DEFAULT_REQUEST_COUNT)
    progress = create_progress(console)
    task_id = progress.add_task("Preparing benchmark", total=DEFAULT_REQUEST_COUNT)

    def on_request_start(request_number: int) -> None:
        progress.update(
            task_id,
            description=f"Downloading request {request_number:02d}/{DEFAULT_REQUEST_COUNT}",
        )

    def on_result(request_number: int, result: RequestResult) -> None:
        results.append(result)
        progress.update(
            task_id,
            advance=1,
            description=f"Completed request {request_number:02d}/{DEFAULT_REQUEST_COUNT}",
        )

    try:
        with progress:
            summary = run_benchmark(
                args.url,
                connect_timeout_seconds=args.connect_timeout,
                timeout_seconds=args.timeout,
                on_request_start=on_request_start,
                on_result=on_result,
            )
    except BenchmarkError as error:
        print_results(console, results)
        print_error(console, str(error))
        return 1
    except KeyboardInterrupt:
        print_results(console, results)
        print_error(console, "The run was stopped by the user.", interrupted=True)
        return 130

    print_results(console, results)
    print_summary(console, summary, DEFAULT_REQUEST_COUNT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

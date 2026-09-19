from __future__ import annotations

from io import StringIO

from rich.console import Console

from benchmark.models import BenchmarkSummary, RequestResult
from benchmark.renderer import print_error, print_header, print_results, print_summary


def test_renderer_contains_the_essential_benchmark_information() -> None:
    output = StringIO()
    console = Console(file=output, width=100, color_system=None, force_terminal=False)
    result = RequestResult(2.5, 10_000_000, 200)
    summary = BenchmarkSummary(1, 10_000_000, 2.5, 2.5, 4.0)

    print_header(console, "https://example.test/file.bin", request_count=10)
    print_results(console, [result])
    print_summary(console, summary, request_count=10)

    rendered = output.getvalue()
    assert "Internet Speed Benchmark" in rendered
    assert "https://example.test/file.bin" in rendered
    assert "200 OK" in rendered
    assert "4.00 MB/s" in rendered
    assert "1/10" in rendered


def test_renderer_shows_a_clear_error_panel() -> None:
    output = StringIO()
    console = Console(file=output, width=100, color_system=None, force_terminal=False)

    print_error(console, "HTTP request failed with status 404")

    rendered = output.getvalue()
    assert "Benchmark failed" in rendered
    assert "HTTP request failed with status 404" in rendered

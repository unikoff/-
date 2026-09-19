"""Pure calculations for benchmark results."""

from collections.abc import Sequence

from .models import BenchmarkSummary, RequestResult


def calculate_summary(results: Sequence[RequestResult]) -> BenchmarkSummary:
    """Aggregate completed request measurements.

    The aggregate speed is deliberately calculated as total bytes divided by
    total transfer time. This is the weighted throughput of the whole run, not
    an arithmetic mean of the individual speeds.
    """

    if not results:
        raise ValueError("at least one request result is required")

    total_time = sum(result.duration_seconds for result in results)
    total_bytes = sum(result.downloaded_bytes for result in results)

    if total_time <= 0:
        raise ValueError("total request time must be greater than zero")

    return BenchmarkSummary(
        successful_requests=len(results),
        total_downloaded_bytes=total_bytes,
        total_time_seconds=total_time,
        average_time_seconds=total_time / len(results),
        average_speed_mb_s=total_bytes / total_time / 1_000_000,
    )

import pytest

from benchmark.models import RequestResult
from benchmark.statistics import calculate_summary


def test_calculate_summary_uses_weighted_total_throughput() -> None:
    summary = calculate_summary(
        [
            RequestResult(2.0, 2_000_000, 200),
            RequestResult(3.0, 3_000_000, 200),
        ],
    )

    assert summary.successful_requests == 2
    assert summary.total_downloaded_bytes == 5_000_000
    assert summary.total_time_seconds == pytest.approx(5.0)
    assert summary.average_time_seconds == pytest.approx(2.5)
    assert summary.average_speed_mb_s == pytest.approx(1.0)
    assert summary.average_speed_mbps == pytest.approx(8.0)


def test_calculate_summary_rejects_empty_results() -> None:
    with pytest.raises(ValueError, match="at least one"):
        calculate_summary([])

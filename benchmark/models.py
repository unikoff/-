"""Immutable data models used by the benchmark."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RequestResult:
    """Measurements collected for one completed HTTP download."""

    duration_seconds: float
    downloaded_bytes: int
    status_code: int

    @property
    def speed_mb_s(self) -> float:
        """Return this request's throughput in decimal megabytes per second."""

        if self.duration_seconds <= 0:
            return 0.0
        return self.downloaded_bytes / self.duration_seconds / 1_000_000


@dataclass(frozen=True, slots=True)
class BenchmarkSummary:
    """Aggregated measurements for all successful requests."""

    successful_requests: int
    total_downloaded_bytes: int
    total_time_seconds: float
    average_time_seconds: float
    average_speed_mb_s: float

    @property
    def total_downloaded_mb(self) -> float:
        """Return the downloaded volume in decimal megabytes."""

        return self.total_downloaded_bytes / 1_000_000

    @property
    def average_speed_mbps(self) -> float:
        """Return the aggregate throughput in megabits per second."""

        return self.average_speed_mb_s * 8

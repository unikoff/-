"""Rich-based presentation for the benchmark command-line interface."""

from __future__ import annotations

from collections.abc import Sequence

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from .models import BenchmarkSummary, RequestResult


def print_header(console: Console, url: str, request_count: int) -> None:
    """Render the benchmark identity and immutable run parameters."""

    details = Table.grid(padding=(0, 1))
    details.add_column(style="bold cyan", justify="right", no_wrap=True)
    details.add_column()
    details.add_row("Target", Text(url, style="white"))
    details.add_row("Mode", f"{request_count} sequential HTTP GET requests")
    details.add_row("Storage", "streamed; response body is discarded")

    console.print(
        Panel(
            details,
            box=box.ROUNDED,
            border_style="bright_blue",
            title="[bold bright_blue]Internet Speed Benchmark[/bold bright_blue]",
            title_align="left",
            padding=(1, 2),
        ),
    )


def create_progress(console: Console) -> Progress:
    """Create a low-overhead progress display for completed requests."""

    return Progress(
        SpinnerColumn("dots", style="bright_blue"),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=None, complete_style="bright_blue", finished_style="green"),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        expand=True,
        refresh_per_second=8,
        transient=True,
    )


def print_results(console: Console, results: Sequence[RequestResult]) -> None:
    """Render one row per completed download."""

    if not results:
        return

    table = Table(
        title="[bold]Request results[/bold]",
        box=box.ROUNDED,
        border_style="blue",
        header_style="bold cyan",
        title_style="bright_blue",
        pad_edge=True,
        expand=True,
    )
    table.add_column("#", justify="right", style="dim", no_wrap=True)
    table.add_column("HTTP", justify="center", no_wrap=True)
    table.add_column("Time", justify="right", no_wrap=True)
    table.add_column("Downloaded", justify="right", no_wrap=True)
    table.add_column("Speed", justify="right", no_wrap=True)

    for request_number, result in enumerate(results, start=1):
        table.add_row(
            f"{request_number:02d}",
            Text(f"{result.status_code} OK", style="bold green"),
            f"{result.duration_seconds:.3f} s",
            f"{result.downloaded_bytes / 1_000_000:.2f} MB",
            Text(f"{result.speed_mb_s:.2f} MB/s", style="bold bright_green"),
        )

    console.print(table)


def print_summary(console: Console, summary: BenchmarkSummary, request_count: int) -> None:
    """Render the aggregate measurements in a compact summary panel."""

    details = Table.grid(padding=(0, 2))
    details.add_column(style="dim", justify="right", no_wrap=True)
    details.add_column(style="bold white")
    details.add_row("Successful requests", f"{summary.successful_requests}/{request_count}")
    details.add_row("Total downloaded", f"{summary.total_downloaded_mb:.2f} MB")
    details.add_row("Average request time", f"{summary.average_time_seconds:.3f} s")
    details.add_row("Total transfer time", f"{summary.total_time_seconds:.3f} s")
    details.add_row(
        "Average speed",
        Text(
            f"{summary.average_speed_mb_s:.2f} MB/s  ({summary.average_speed_mbps:.2f} Mbps)",
            style="bold bright_green",
        ),
    )

    console.print(
        Panel(
            details,
            box=box.ROUNDED,
            border_style="green",
            title="[bold green]Benchmark complete[/bold green]",
            title_align="left",
            padding=(1, 2),
        ),
    )


def print_error(console: Console, message: str, *, interrupted: bool = False) -> None:
    """Render an actionable terminal state without a traceback."""

    title = "Benchmark interrupted" if interrupted else "Benchmark failed"
    style = "yellow" if interrupted else "red"
    console.print(
        Panel(
            Text(message, style=f"bold {style}"),
            box=box.ROUNDED,
            border_style=style,
            title=f"[bold {style}]{title}[/bold {style}]",
            title_align="left",
            padding=(1, 2),
        ),
    )

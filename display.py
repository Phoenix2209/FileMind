# display.py
# Renders the SummaryReport as a beautiful Rich terminal UI.
# Two sections: (1) global summary panel, (2) per-file table.

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.columns import Columns
from rich.rule import Rule

from schema import SummaryReport

console = Console()


# ── Public entry ───────────────────────────────────────────────────────────

def display_report(report: SummaryReport) -> None:
    """Print the full report to the terminal."""

    console.print()
    console.print(Rule("[bold cyan]  FileMind — AI Summary Report  [/bold cyan]", style="cyan"))
    console.print()

    _print_stats_row(report)
    console.print()

    _print_global_summary(report)
    console.print()

    _print_per_file_table(report)
    console.print()

    if report.global_summary.common_themes or report.global_summary.top_insights:
        _print_themes_and_insights(report)
        console.print()

    if report.failed > 0:
        _print_failed_files(report)
        console.print()

    console.print(Rule(style="dim"))


# ── Sections ───────────────────────────────────────────────────────────────

def _print_stats_row(report: SummaryReport) -> None:
    stats = [
        Panel(
            f"[bold white]{report.total_files}[/bold white]\n[dim]Total files[/dim]",
            border_style="cyan", expand=True
        ),
        Panel(
            f"[bold green]{report.processed}[/bold green]\n[dim]Processed[/dim]",
            border_style="green", expand=True
        ),
        Panel(
            f"[bold red]{report.failed}[/bold red]\n[dim]Failed[/dim]",
            border_style="red" if report.failed else "dim", expand=True
        ),
        Panel(
            f"[bold magenta]{report.model_used}[/bold magenta]\n[dim]Model[/dim]",
            border_style="magenta", expand=True
        ),
    ]
    console.print(Columns(stats, equal=True, expand=True))


def _print_global_summary(report: SummaryReport) -> None:
    gs = report.global_summary.global_summary or "[dim]No global summary generated.[/dim]"
    console.print(Panel(
        f"[italic]{gs}[/italic]",
        title="[bold cyan]🌐 Global Summary[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    ))


def _print_per_file_table(report: SummaryReport) -> None:
    table = Table(
        title="📄 Per-File Breakdown",
        box=box.ROUNDED,
        border_style="bright_black",
        header_style="bold cyan",
        show_lines=True,
        expand=True,
    )

    table.add_column("File",         style="bright_cyan", no_wrap=True, min_width=18)
    table.add_column("Type",         style="yellow",      no_wrap=True, width=6)
    table.add_column("Size",         style="dim",         no_wrap=True, width=8)
    table.add_column("Data Summary", style="white",       min_width=24, max_width=40)
    table.add_column("Key Points",   style="green",       min_width=24, max_width=40)
    table.add_column("Entities",     style="magenta",     min_width=20, max_width=32)

    for fs in report.files:
        if not fs.success:
            table.add_row(
                fs.filename,
                fs.file_type,
                f"{fs.file_size_kb} KB",
                Text("❌ " + (fs.error or "error"), style="red"),
                "", "",
            )
            continue

        key_points_text = "\n".join(
            f"• {p}" for p in fs.key_points
        ) if fs.key_points else "—"

        table.add_row(
            fs.filename,
            fs.file_type,
            f"{fs.file_size_kb} KB",
            fs.data_summary or "—",
            key_points_text,
            fs.entities or "—",
        )

    console.print(table)


def _print_themes_and_insights(report: SummaryReport) -> None:
    panels = []

    if report.global_summary.common_themes:
        themes_text = "\n".join(
            f"[cyan]◆[/cyan] {t}" for t in report.global_summary.common_themes
        )
        panels.append(Panel(
            themes_text,
            title="[bold yellow]🔗 Common Themes[/bold yellow]",
            border_style="yellow",
            expand=True,
        ))

    if report.global_summary.top_insights:
        insights_text = "\n".join(
            f"[green]▶[/green] {i}" for i in report.global_summary.top_insights
        )
        panels.append(Panel(
            insights_text,
            title="[bold green]💡 Top Insights[/bold green]",
            border_style="green",
            expand=True,
        ))

    if panels:
        console.print(Columns(panels, equal=True, expand=True))


def _print_failed_files(report: SummaryReport) -> None:
    failed = [f for f in report.files if not f.success]
    lines = "\n".join(f"[red]✗[/red] [bold]{f.filename}[/bold]: {f.error}" for f in failed)
    console.print(Panel(
        lines,
        title="[bold red]⚠ Failed Files[/bold red]",
        border_style="red",
    ))
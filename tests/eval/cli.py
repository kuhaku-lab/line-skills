"""Unified CLI for skill evaluation and description optimization."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from .assessor import AssessmentResult, assess_skill
from .optimizer import IterationRecord, optimize_description
from .skill_io import SKILL_NAMES, load_skill

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Trigger-accuracy evaluation and description optimization for line-skills.",
)
console = Console(stderr=True)


def _print_result(result: AssessmentResult, *, verbose: bool) -> None:
    metrics = result.metrics()
    console.print(
        f"[bold]{result.skill}[/bold] ({result.mode})  "
        f"[green]{result.passed}/{result.total}[/green]  "
        f"precision={metrics['precision']:.0%}  "
        f"recall={metrics['recall']:.0%}  "
        f"accuracy={metrics['accuracy']:.0%}"
    )
    if not verbose:
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("status", width=6)
    table.add_column("expect", width=6)
    table.add_column("rate", width=6)
    table.add_column("query", overflow="fold")
    for r in result.results:
        status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
        expect = "should" if r.should_trigger else "not"
        table.add_row(status, expect, f"{r.triggers}/{r.runs}", r.query)
    console.print(table)


@app.command()
def eval(
    skill: Optional[str] = typer.Argument(
        None,
        help=f"Skill name. One of: {', '.join(SKILL_NAMES)}. Omit to run all.",
    ),
    mode: str = typer.Option(
        "simulated",
        "--mode",
        "-m",
        help="simulated (Agent SDK as judge) or e2e (real `claude -p`).",
    ),
    runs: int = typer.Option(1, "--runs", "-r", help="Runs per query."),
    concurrency: int = typer.Option(5, "--concurrency", "-c"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write JSON to file."),
) -> None:
    """Evaluate skill trigger accuracy against assessment_set.json."""
    if mode not in ("simulated", "e2e"):
        console.print(f"[red]Unknown mode: {mode}[/red]")
        raise typer.Exit(code=2)

    targets = [skill] if skill else list(SKILL_NAMES)
    if skill and skill not in SKILL_NAMES:
        console.print(f"[red]Unknown skill: {skill}[/red]")
        raise typer.Exit(code=2)

    results = []
    overall_pass = 0
    overall_total = 0
    for name in targets:
        spec = load_skill(name)
        total_queries = len(spec.assessment_set)
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.fields[skill]}[/bold blue]"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[dim]{task.fields[last]}[/dim]"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task_id = progress.add_task(
                f"eval {name}", total=total_queries, skill=name, last=""
            )

            def _on_progress(
                idx, total, query, should_trigger, triggered, passed, elapsed, timed_out
            ):
                if timed_out:
                    status = "[yellow]TIME[/yellow]"
                elif passed:
                    status = "[green]PASS[/green]"
                else:
                    status = "[red]FAIL[/red]"
                snippet = query[:45] + ("…" if len(query) > 45 else "")
                progress.update(task_id, completed=idx, last=f"{status} {snippet}")

            result = asyncio.run(
                assess_skill(
                    spec,
                    mode=mode,  # type: ignore[arg-type]
                    runs_per_query=runs,
                    concurrency=concurrency,
                    on_progress=_on_progress,
                )
            )
        _print_result(result, verbose=verbose)
        results.append(result.to_dict())
        overall_pass += result.passed
        overall_total += result.total

    payload = {"skills": results, "summary": {"passed": overall_pass, "total": overall_total}}
    json_text = json.dumps(payload, indent=2, ensure_ascii=False)
    if output:
        output.write_text(json_text, encoding="utf-8")
        console.print(f"[dim]Wrote {output}[/dim]")
    else:
        # Stdout for piping; stderr already shows the human summary.
        sys.stdout.write(json_text + "\n")

    failures = overall_total - overall_pass
    if failures:
        raise typer.Exit(code=1)


@app.command()
def optimize(
    skill: str = typer.Argument(..., help=f"Skill name. One of: {', '.join(SKILL_NAMES)}"),
    iterations: int = typer.Option(3, "--iterations", "-n"),
    runs: int = typer.Option(1, "--runs", "-r", help="Runs per query."),
    concurrency: int = typer.Option(5, "--concurrency", "-c"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
) -> None:
    """Iteratively improve a skill's description against its assessment set."""
    if skill not in SKILL_NAMES:
        console.print(f"[red]Unknown skill: {skill}[/red]")
        raise typer.Exit(code=2)

    spec = load_skill(skill)

    def report(record: IterationRecord, _result) -> None:
        console.print(
            f"  iter {record.iteration}: [bold]{record.passed}/{record.total}[/bold]  "
            f"[dim]{record.description[:120]}…[/dim]"
        )

    console.print(f"[bold]Optimizing {skill}[/bold] ({iterations} iterations)")
    result = asyncio.run(
        optimize_description(
            spec,
            max_iterations=iterations,
            runs_per_query=runs,
            concurrency=concurrency,
            on_iteration=report,
        )
    )
    console.print(
        f"[green]Best score: {result.best_score}/{result.iterations[-1].total}[/green]"
    )
    console.print(f"[bold]Best description:[/bold]\n{result.best_description}")

    json_text = json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
    if output:
        output.write_text(json_text, encoding="utf-8")
        console.print(f"[dim]Wrote {output}[/dim]")
    else:
        sys.stdout.write(json_text + "\n")


@app.command()
def list_skills() -> None:
    """List available skills."""
    for name in SKILL_NAMES:
        console.print(f"  • {name}")


if __name__ == "__main__":
    app()

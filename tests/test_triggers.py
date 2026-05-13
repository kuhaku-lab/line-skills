"""Pytest harness for skill trigger accuracy.

Progress is printed line-by-line to stderr during execution. Use one of:
  uv run pytest -s                       # disable pytest output capture
  uv run pytest --capture=no             # same
  uv run pytest --log-cli-level=INFO     # alternative

Run examples:
    uv run pytest -s                                            # all skills, simulated
    uv run pytest -s -k messaging_api                           # one skill
    uv run pytest -s -n auto --runs 3 --threshold 0.9           # parallel, 3 runs/query, 90% bar
    SKILL_TEST_THRESHOLD=0.9 uv run pytest -s                   # via env var
"""

from __future__ import annotations

import sys

import pytest

from eval.assessor import assess_skill
from eval.skill_io import SKILL_NAMES, load_skill


def _print(line: str) -> None:
    """Write progress to the real stderr, bypassing pytest's capture."""
    sys.__stderr__.write(line + "\n")
    sys.__stderr__.flush()


def _make_progress_printer(skill_name: str):
    def cb(
        idx: int,
        total: int,
        query: str,
        should_trigger: bool,
        triggered: bool,
        passed: bool,
        elapsed: float,
        timed_out: bool,
    ) -> None:
        # Pass/fail status (what we actually care about)
        if timed_out:
            status = "TIME"
        elif passed:
            status = "PASS"
        else:
            status = "FAIL"
        # What the judge said + what was expected (for context on failures)
        expect = "should" if should_trigger else "skip  "
        verdict = "trig" if triggered else "skip"
        snippet = query[:55] + ("…" if len(query) > 55 else "")
        _print(
            f"  [{skill_name}] {idx:>3}/{total} {status}  "
            f"expect={expect}/got={verdict}  {elapsed:>5.1f}s  {snippet}"
        )
    return cb


@pytest.mark.parametrize("skill_name", SKILL_NAMES)
@pytest.mark.asyncio
async def test_skill_trigger_accuracy(
    skill_name: str,
    runs: int,
    concurrency: int,
    threshold: float,
) -> None:
    spec = load_skill(skill_name)
    _print(f"\n→ {skill_name}: {len(spec.assessment_set)} queries × {runs} run(s), concurrency={concurrency}")

    result = await assess_skill(
        spec,
        mode="simulated",
        runs_per_query=runs,
        concurrency=concurrency,
        on_progress=_make_progress_printer(skill_name),
    )

    accuracy = result.passed / result.total if result.total else 0.0
    metrics = result.metrics()
    _print(
        f"← {skill_name}: {result.passed}/{result.total} ({accuracy:.0%})  "
        f"precision={metrics['precision']:.0%}  recall={metrics['recall']:.0%}"
    )

    failures = [r for r in result.results if not r.passed]
    report = "\n".join(
        f"  [{'FAIL' if not r.passed else 'pass'}] "
        f"{'should' if r.should_trigger else 'not   '} "
        f"{r.triggers}/{r.runs}  {r.query[:80]}"
        for r in failures
    )
    assert accuracy >= threshold, (
        f"{skill_name}: {result.passed}/{result.total} "
        f"({accuracy:.0%}) below threshold {threshold:.0%}\n{report}"
    )

"""Shared pytest configuration."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip trigger tests early if Claude Code auth is clearly missing.

    Simulated mode spawns `claude` subprocesses via claude-agent-sdk; without
    auth the subprocess would hang per query. The per-query 60s timeout
    inside the assessor keeps things from hanging forever, but a clean
    skip here gives a much better dev experience.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return

    def _skip_all(reason: str) -> None:
        sys.__stderr__.write(f"\n[setup] {reason}\n")
        sys.__stderr__.flush()
        marker = pytest.mark.skip(reason=reason)
        for item in items:
            item.add_marker(marker)

    if shutil.which("claude") is None:
        _skip_all(
            "No ANTHROPIC_API_KEY and `claude` CLI not on PATH. "
            "See tests/README.md → Prerequisites."
        )
        return

    try:
        proc = subprocess.run(
            ["claude", "-p", "ping"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired:
        _skip_all(
            "`claude -p` timed out (probably not logged in). "
            "Run `claude` then `/login`, or set ANTHROPIC_API_KEY."
        )
        return

    if proc.returncode != 0:
        _skip_all(
            f"`claude -p` exited with rc={proc.returncode}. "
            "Auth or installation issue — see tests/README.md."
        )


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--runs",
        action="store",
        default=int(os.environ.get("SKILL_TEST_RUNS", "1")),
        type=int,
        help="Runs per query.",
    )
    parser.addoption(
        "--concurrency",
        action="store",
        default=int(os.environ.get("SKILL_TEST_CONCURRENCY", "5")),
        type=int,
        help="Max concurrent Agent SDK calls.",
    )
    parser.addoption(
        "--threshold",
        action="store",
        default=float(os.environ.get("SKILL_TEST_THRESHOLD", "0.85")),
        type=float,
        help="Pass-rate threshold (default 0.85 = 85%).",
    )


@pytest.fixture
def runs(request) -> int:
    return int(request.config.getoption("--runs"))


@pytest.fixture
def concurrency(request) -> int:
    return int(request.config.getoption("--concurrency"))


@pytest.fixture
def threshold(request) -> float:
    return float(request.config.getoption("--threshold"))

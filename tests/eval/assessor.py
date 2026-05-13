"""Skill trigger assessment — simulated (Agent SDK) and e2e (`claude -p`)."""

from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Literal, Optional

from claude_agent_sdk import ClaudeAgentOptions, query

from .skill_io import AssessmentItem, ScopeConfig, SkillSpec

Mode = Literal["simulated", "e2e"]
PER_QUERY_TIMEOUT_SECS = 60.0

# Callback signature:
#   (index, total, query_text, should_trigger, triggered, passed, elapsed_secs, timed_out)
ProgressCallback = Callable[[int, int, str, bool, bool, bool, float, bool], None]


@dataclass
class QueryResult:
    query: str
    should_trigger: bool
    triggers: int
    runs: int

    @property
    def rate(self) -> float:
        return self.triggers / self.runs if self.runs else 0.0

    @property
    def passed(self) -> bool:
        return (self.rate >= 0.5) if self.should_trigger else (self.rate < 0.5)


@dataclass
class AssessmentResult:
    skill: str
    description: str
    mode: Mode
    runs_per_query: int
    results: list[QueryResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    def metrics(self) -> dict[str, float]:
        pos = [r for r in self.results if r.should_trigger]
        neg = [r for r in self.results if not r.should_trigger]
        tp = sum(r.triggers for r in pos)
        fn = sum(r.runs - r.triggers for r in pos)
        fp = sum(r.triggers for r in neg)
        tn = sum(r.runs - r.triggers for r in neg)
        total_runs = tp + tn + fp + fn
        return {
            "precision": tp / (tp + fp) if (tp + fp) else 1.0,
            "recall": tp / (tp + fn) if (tp + fn) else 1.0,
            "accuracy": (tp + tn) / total_runs if total_runs else 0.0,
        }

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "mode": self.mode,
            "description": self.description,
            "runs_per_query": self.runs_per_query,
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                **self.metrics(),
            },
            "results": [
                {
                    "query": r.query,
                    "should_trigger": r.should_trigger,
                    "triggers": r.triggers,
                    "runs": r.runs,
                    "trigger_rate": round(r.rate, 3),
                    "pass": r.passed,
                }
                for r in self.results
            ],
        }


# ---------------------------------------------------------------------------
# Simulated mode (Agent SDK as judge)
# ---------------------------------------------------------------------------

def _extract_text(message) -> str:
    if hasattr(message, "result"):
        return message.result or ""
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return block["text"]
            if hasattr(block, "text"):
                return block.text
    return ""


async def _judge_one(
    skill_name: str,
    description: str,
    user_query: str,
    assess_scope: tuple[str, ...],
) -> tuple[bool, bool]:
    """Return (triggered, timed_out). On timeout, triggered=False, timed_out=True."""
    scope_text = ("\n".join(assess_scope) + "\n") if assess_scope else ""
    prompt = (
        "You are simulating Claude Code's skill triggering decision.\n\n"
        "Claude Code has access to this skill:\n"
        f"  name: {skill_name}\n"
        f'  description: "{description}"\n\n'
        "A user sends this message:\n"
        f'"{user_query}"\n\n'
        "Would Claude Code invoke this skill to help answer?\n"
        "Consider:\n"
        "- Does the query fall within the skill's described scope?\n"
        "- Is the skill's specialized knowledge needed?\n"
        f"{scope_text}\n"
        'Answer ONLY "true" or "false".'
    )

    async def _consume() -> str:
        text = ""
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(allowed_tools=[], max_turns=1),
        ):
            captured = _extract_text(message)
            if captured:
                text = captured
        return text

    try:
        text = await asyncio.wait_for(_consume(), timeout=PER_QUERY_TIMEOUT_SECS)
    except asyncio.TimeoutError:
        return False, True
    return "true" in text.strip().lower(), False


async def _assess_simulated(
    spec: SkillSpec,
    description: str,
    runs_per_query: int,
    concurrency: int,
    on_progress: Optional[ProgressCallback] = None,
) -> list[QueryResult]:
    sem = asyncio.Semaphore(concurrency)
    total = len(spec.assessment_set)

    async def one(q: str) -> tuple[bool, bool]:
        async with sem:
            return await _judge_one(spec.name, description, q, spec.scope.assess_scope)

    results: list[QueryResult] = []
    for idx, item in enumerate(spec.assessment_set, start=1):
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        tasks = [one(item.query) for _ in range(runs_per_query)]
        outcomes = await asyncio.gather(*tasks)
        elapsed = loop.time() - t0
        triggers = sum(1 for triggered, _ in outcomes if triggered)
        timed_out = any(to for _, to in outcomes)
        qr = QueryResult(
            query=item.query,
            should_trigger=item.should_trigger,
            triggers=triggers,
            runs=len(outcomes),
        )
        results.append(qr)
        if on_progress is not None:
            triggered_majority = triggers >= max(1, len(outcomes) // 2 + 1)
            on_progress(
                idx, total, item.query,
                item.should_trigger, triggered_majority, qr.passed,
                elapsed, timed_out,
            )
    return results


# ---------------------------------------------------------------------------
# E2E mode (real `claude -p` invocation)
# ---------------------------------------------------------------------------

def _e2e_check_triggered(user_query: str, skill_name: str) -> bool:
    try:
        proc = subprocess.run(
            ["claude", "-p", user_query, "--output-format", "stream-json", "--verbose"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        message = payload.get("message") or {}
        for block in message.get("content", []) or []:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_use"
                and block.get("name") == "Skill"
                and (block.get("input") or {}).get("skill") == skill_name
            ):
                return True
    return False


async def _assess_e2e(
    spec: SkillSpec,
    runs_per_query: int,
    concurrency: int,
    on_progress: Optional[ProgressCallback] = None,
) -> list[QueryResult]:
    sem = asyncio.Semaphore(concurrency)
    loop = asyncio.get_running_loop()
    total = len(spec.assessment_set)

    async def one(q: str) -> bool:
        async with sem:
            return await loop.run_in_executor(None, _e2e_check_triggered, q, spec.name)

    results: list[QueryResult] = []
    for idx, item in enumerate(spec.assessment_set, start=1):
        t0 = loop.time()
        tasks = [one(item.query) for _ in range(runs_per_query)]
        outcomes = await asyncio.gather(*tasks)
        elapsed = loop.time() - t0
        triggers = sum(outcomes)
        qr = QueryResult(
            query=item.query,
            should_trigger=item.should_trigger,
            triggers=triggers,
            runs=len(outcomes),
        )
        results.append(qr)
        if on_progress is not None:
            triggered_majority = triggers >= max(1, len(outcomes) // 2 + 1)
            on_progress(
                idx, total, item.query,
                item.should_trigger, triggered_majority, qr.passed,
                elapsed, False,
            )
    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def assess_skill(
    spec: SkillSpec,
    *,
    description: str | None = None,
    mode: Mode = "simulated",
    runs_per_query: int = 1,
    concurrency: int = 5,
    on_progress: Optional[ProgressCallback] = None,
) -> AssessmentResult:
    desc = description if description is not None else spec.description
    if mode == "simulated":
        results = await _assess_simulated(spec, desc, runs_per_query, concurrency, on_progress)
    elif mode == "e2e":
        # e2e mode reads the description live from SKILL.md, ignore override
        results = await _assess_e2e(spec, runs_per_query, concurrency, on_progress)
    else:
        raise ValueError(f"unknown mode: {mode}")

    return AssessmentResult(
        skill=spec.name,
        description=desc,
        mode=mode,
        runs_per_query=runs_per_query,
        results=results,
    )

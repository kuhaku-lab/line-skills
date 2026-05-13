"""Iteratively improve a skill's description against its assessment set."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from claude_agent_sdk import ClaudeAgentOptions, query

from .assessor import AssessmentResult, assess_skill
from .skill_io import SkillSpec


@dataclass
class IterationRecord:
    iteration: int
    description: str
    passed: int
    total: int


@dataclass
class OptimizationResult:
    skill: str
    original_description: str
    best_description: str
    best_score: int
    final_description: str
    iterations: list[IterationRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "original_description": self.original_description,
            "best_description": self.best_description,
            "best_score": self.best_score,
            "final_description": self.final_description,
            "iterations": [
                {
                    "iteration": r.iteration,
                    "description": r.description,
                    "passed": r.passed,
                    "total": r.total,
                }
                for r in self.iterations
            ],
        }


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


async def _propose_description(
    spec: SkillSpec,
    current: str,
    result: AssessmentResult,
    history: list[IterationRecord],
) -> str:
    failed = [r for r in result.results if r.should_trigger and not r.passed]
    false_pos = [r for r in result.results if not r.should_trigger and not r.passed]

    parts = [
        f'You are optimizing the description for the Claude Code skill "{spec.name}".',
        "Claude sees only the title + description when deciding whether to invoke a skill.",
        "",
        f'Current description:\n"{current}"',
        f"\nScore: {result.passed}/{result.total}",
        "",
    ]
    if failed:
        parts.append("FAILED TO TRIGGER (should have but didn't):")
        parts.extend(f'  - "{r.query[:120]}" ({r.triggers}/{r.runs})' for r in failed)
        parts.append("")
    if false_pos:
        parts.append("FALSE TRIGGERS (triggered but shouldn't have):")
        parts.extend(f'  - "{r.query[:120]}" ({r.triggers}/{r.runs})' for r in false_pos)
        parts.append("")
    if history:
        parts.append("PREVIOUS ATTEMPTS (try a structurally different angle):")
        parts.extend(f'  [{h.passed}/{h.total}] "{h.description[:150]}"' for h in history)
        parts.append("")

    parts.extend([
        f"Skill content (first 2000 chars):\n{spec.content[:2000]}",
        "",
        "GUIDANCE:",
        "- Claude skips skills when it thinks it already knows the answer.",
        f"- The description should signal that {spec.scope.knowledge_domain} knowledge in training data is stale.",
        "- Distinctive over keyword-stuffed. The description competes for attention.",
    ])
    parts.extend(spec.scope.improve_scope)
    parts.extend([
        "- Imperative voice. Focus on user intent.",
        "- 100–200 words. Try a different angle, not more keywords.",
        "",
        "Output ONLY the new description text. No quotes, no tags, no commentary.",
    ])

    prompt = "\n".join(parts)
    text = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(allowed_tools=[], max_turns=1),
    ):
        captured = _extract_text(message)
        if captured:
            text = captured

    new_desc = text.strip().strip('"').strip("'")
    if len(new_desc) > 1024:
        new_desc = new_desc[:1020] + "..."
    return new_desc or current


async def optimize_description(
    spec: SkillSpec,
    *,
    max_iterations: int = 5,
    runs_per_query: int = 1,
    concurrency: int = 5,
    on_iteration=None,
) -> OptimizationResult:
    original = spec.description
    current = original
    best = current
    best_score = -1
    history: list[IterationRecord] = []

    for it in range(1, max_iterations + 1):
        result = await assess_skill(
            spec,
            description=current,
            mode="simulated",
            runs_per_query=runs_per_query,
            concurrency=concurrency,
        )
        record = IterationRecord(
            iteration=it,
            description=current,
            passed=result.passed,
            total=result.total,
        )
        history.append(record)
        if on_iteration is not None:
            on_iteration(record, result)

        if result.passed > best_score:
            best_score = result.passed
            best = current
        if result.passed == result.total or it == max_iterations:
            break

        current = await _propose_description(spec, current, result, history)

    return OptimizationResult(
        skill=spec.name,
        original_description=original,
        best_description=best,
        best_score=best_score,
        final_description=current,
        iterations=history,
    )

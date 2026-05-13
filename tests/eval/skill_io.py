"""SKILL.md frontmatter parsing and test data loading."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / "skills"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

SKILL_NAMES = (
    "messaging-api",
    "line-login",
    "line-liff",
    "line-mini-app",
    "line-notification-message",
    "line-creators-market",
)


@dataclass(frozen=True)
class AssessmentItem:
    query: str
    should_trigger: bool


@dataclass(frozen=True)
class ScopeConfig:
    knowledge_domain: str
    assess_scope: tuple[str, ...]
    improve_scope: tuple[str, ...]


@dataclass(frozen=True)
class SkillSpec:
    name: str
    description: str
    content: str
    path: Path
    assessment_set: tuple[AssessmentItem, ...]
    scope: ScopeConfig


def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Return (name, description, full content) from SKILL.md frontmatter."""
    content = (skill_path / "SKILL.md").read_text(encoding="utf-8")
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{skill_path}/SKILL.md missing opening frontmatter")

    end_idx = next(
        (i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if end_idx is None:
        raise ValueError(f"{skill_path}/SKILL.md missing closing ---")

    name, description = "", ""
    fm = lines[1:end_idx]
    i = 0
    while i < len(fm):
        line = fm[i]
        if line.startswith("name:"):
            name = line[len("name:"):].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            value = line[len("description:"):].strip()
            if value in (">", "|", ">-", "|-"):
                parts: list[str] = []
                i += 1
                while i < len(fm) and (fm[i].startswith("  ") or fm[i].startswith("\t")):
                    parts.append(fm[i].strip())
                    i += 1
                description = " ".join(parts)
                continue
            description = value.strip('"').strip("'")
        i += 1
    return name, description, content


def load_skill(skill_name: str) -> SkillSpec:
    skill_path = SKILLS_DIR / skill_name
    if not (skill_path / "SKILL.md").exists():
        raise FileNotFoundError(f"No SKILL.md at {skill_path}")

    name, description, content = parse_skill_md(skill_path)

    data_path = DATA_DIR / skill_name
    assessment_raw = json.loads((data_path / "assessment_set.json").read_text(encoding="utf-8"))
    assessment_set = tuple(
        AssessmentItem(query=item["query"], should_trigger=bool(item["should_trigger"]))
        for item in assessment_raw
    )

    scope_raw = json.loads((data_path / "scope.json").read_text(encoding="utf-8"))
    scope = ScopeConfig(
        knowledge_domain=scope_raw.get("knowledge_domain", "LINE API"),
        assess_scope=tuple(scope_raw.get("assess_scope", [])),
        improve_scope=tuple(scope_raw.get("improve_scope", [])),
    )

    return SkillSpec(
        name=name or skill_name,
        description=description,
        content=content,
        path=skill_path,
        assessment_set=assessment_set,
        scope=scope,
    )

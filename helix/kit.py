"""The living toolkit Aria mutates.

kit/
├── VERSION
├── rules/    *.md   hard constraints the scout must obey
├── skills/   *.md   playbooks for recurring jobs
└── tools/    *.py   functions the scout can call (see kit/tools/registry.py)

Every promotion snapshots the previous kit under kit/.history/<version>/ so
rollback is a copy, not a prayer.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .schema import KitDiff


@dataclass
class Kit:
    root: Path
    version: str
    rules: dict[str, str] = field(default_factory=dict)
    skills: dict[str, str] = field(default_factory=dict)
    tool_names: list[str] = field(default_factory=list)

    def system_prompt_block(self) -> str:
        """Render rules + skills for injection into the scout prompt."""
        out = [f"# KIT v{self.version}", "", "## RULES (hard constraints)"]
        out += [f"- [{k}] {v.strip()}" for k, v in sorted(self.rules.items())]
        out += ["", "## SKILLS"]
        out += [f"### {k}\n{v.strip()}" for k, v in sorted(self.skills.items())]
        out += ["", "## TOOLS", ", ".join(self.tool_names) or "(none)"]
        return "\n".join(out)


def load_kit(root: Path) -> Kit:
    version = (root / "VERSION").read_text().strip() if (root / "VERSION").exists() else "0"
    rules = {p.stem: p.read_text() for p in sorted((root / "rules").glob("*.md"))}
    skills = {p.stem: p.read_text() for p in sorted((root / "skills").glob("*.md"))}
    tool_names = [p.stem for p in sorted((root / "tools").glob("*.py")) if not p.stem.startswith("_") and p.stem != "registry"]
    return Kit(root=root, version=version, rules=rules, skills=skills, tool_names=tool_names)


def validate_diff(diff: KitDiff, kit: Kit) -> list[str]:
    """Gate before promotion. Return a list of problems; empty means OK.

    TODO (V1): run tests/ against the patched kit, schema-check tools,
    require a rollback plan.
    """
    problems: list[str] = []
    for p in diff.patches:
        if ".." in p.path or p.path.startswith("/"):
            problems.append(f"unsafe path: {p.path}")
            continue
        if not p.path.startswith(f"{p.kind.value}s/"):
            problems.append(f"{p.path} does not live under {p.kind.value}s/")
        if not p.content.strip():
            problems.append(f"empty patch: {p.path}")
        if not p.rationale.strip():
            problems.append(f"no rationale: {p.path}")
    return problems


def snapshot(kit: Kit) -> Path:
    dest = kit.root / ".history" / kit.version
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for sub in ("rules", "skills", "tools"):
        shutil.copytree(kit.root / sub, dest / sub, dirs_exist_ok=True)
    (dest / "VERSION").write_text(kit.version)
    return dest


def promote(diff: KitDiff, kit: Kit) -> Kit:
    """Snapshot, apply patches, bump VERSION. Returns the reloaded kit."""
    snapshot(kit)
    for p in diff.patches:
        target = kit.root / p.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(p.content)
    new_version = str(int(kit.version) + 1) if kit.version.isdigit() else f"{kit.version}+1"
    (kit.root / "VERSION").write_text(new_version + "\n")
    return load_kit(kit.root)


def rollback(kit: Kit, to_version: str) -> Kit:
    src = kit.root / ".history" / to_version
    if not src.exists():
        raise FileNotFoundError(f"no snapshot for kit v{to_version}")
    for sub in ("rules", "skills", "tools"):
        shutil.rmtree(kit.root / sub, ignore_errors=True)
        shutil.copytree(src / sub, kit.root / sub)
    (kit.root / "VERSION").write_text(to_version + "\n")
    return load_kit(kit.root)

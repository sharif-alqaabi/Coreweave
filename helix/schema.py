"""Structured objects that can die cleanly.

A lead that cannot be traced is not a lead. It is a vibe.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    source: str = Field(..., description="e.g. GEO:GSE12345, pmid:12345678, file:shard_01/table.csv")
    artifact: Optional[str] = Field(None, description="table / figure / section id within the source")
    rows: list[str] = Field(default_factory=list, description="row / gene / entity ids the claim rests on")
    quote_span: Optional[str] = None


class Verdict(str, Enum):
    KILL = "kill"
    PARK = "park"
    SURVIVE = "survive"
    ESCALATE = "escalate"


class CriticVerdict(BaseModel):
    verdict: Verdict
    score: float = Field(..., ge=0.0, le=1.0)
    reasons: list[str] = Field(default_factory=list, description="named kill/park reasons; never 'looks good'")
    critic_model: Optional[str] = None
    trace: Optional[str] = None


class Lead(BaseModel):
    id: str
    iteration: int
    claim: str = Field(..., description="short, cited, falsifiable")
    evidence: list[Evidence] = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    why_not_known: str
    next_step: str = Field(..., description="cheap experiment or analysis that could falsify the claim")
    skills_used: list[str] = Field(default_factory=list, description="kit skill ids — so Aria can blame the right one")
    tools_used: list[str] = Field(default_factory=list)
    critic: Optional[CriticVerdict] = None
    trace: str = Field(..., description="weave trace id — mandatory")

    @property
    def survived(self) -> bool:
        return self.critic is not None and self.critic.verdict in (Verdict.SURVIVE, Verdict.ESCALATE)


class PatchKind(str, Enum):
    RULE = "rule"
    SKILL = "skill"
    TOOL = "tool"


class KitPatch(BaseModel):
    """One executable change to `kit/`. Not advice — a file."""
    kind: PatchKind
    path: str = Field(..., description="relative to kit/, e.g. rules/010_require_table_id.md")
    content: str
    rationale: str
    evidence_trace_ids: list[str] = Field(default_factory=list, description="traces that motivated this patch")


class KitDiff(BaseModel):
    iteration: int
    patches: list[KitPatch]
    summary: str


class IterationStats(BaseModel):
    iteration: int
    kit_version: str
    proposed: int
    killed: int
    parked: int
    survived: int
    escalated: int
    duplicate_kills: int = 0
    cost_usd: float = 0.0

    @property
    def survive_rate(self) -> float:
        return (self.survived + self.escalated) / self.proposed if self.proposed else 0.0

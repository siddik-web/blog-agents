"""Pydantic contracts that flow between agents.

These are the single source of truth for the pipeline. Every agent takes one or
more of these as input and returns exactly one as output, so the handoffs are
validated rather than passed around as loose dicts or strings.

Kept intentionally Gemini-structured-output friendly: nested models and enums
are fine; avoid unions of models and free-form `dict` fields, which the schema
translation handles poorly.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Source(BaseModel):
    title: str
    url: str = ""
    note: str = Field(default="", description="Why this source matters for the piece.")


class ResearchBrief(BaseModel):
    topic: str
    audience: str = Field(description="Who the post is for, in one phrase.")
    angle: str = Field(description="The specific take or thesis, not a generic overview.")
    key_points: list[str] = Field(description="3-7 factual points the post must cover.")
    sources: list[Source] = Field(default_factory=list)


class OutlineSection(BaseModel):
    heading: str
    summary: str = Field(description="One sentence on what this section argues.")
    talking_points: list[str]


class Outline(BaseModel):
    title: str
    sections: list[OutlineSection] = Field(description="4-8 sections in reading order.")


class SEOReport(BaseModel):
    primary_keyword: str
    secondary_keywords: list[str]
    meta_title: str = Field(description="<= 60 characters.")
    meta_description: str = Field(description="<= 155 characters.")
    slug: str = Field(description="url-safe-hyphenated-slug")


class Draft(BaseModel):
    title: str
    markdown: str = Field(description="The full post body in Markdown.")
    word_count: int


class Severity(str, Enum):
    blocker = "blocker"
    minor = "minor"


class ReviewIssue(BaseModel):
    severity: Severity
    location: str = Field(description="Section heading or quoted phrase the issue refers to.")
    problem: str
    suggestion: str = Field(description="Concrete, actionable fix the writer can apply.")


class ReviewNotes(BaseModel):
    """The reviewer only reports. It never decides whether to loop.

    The orchestrator reads `verdict` + `issues` and owns the branch decision,
    so a chatty reviewer can't trigger an infinite polish cycle.
    """

    verdict: Literal["approve", "revise"]
    summary: str
    issues: list[ReviewIssue] = Field(default_factory=list)

    def blockers(self) -> list[ReviewIssue]:
        return [i for i in self.issues if i.severity == Severity.blocker]

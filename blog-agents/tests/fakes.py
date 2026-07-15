"""Shared fakes for the offline suite (no model needed)."""

from __future__ import annotations

from app.schemas import (
    Draft, Outline, OutlineSection, ResearchBrief,
    ReviewIssue, ReviewNotes, SEOReport, Severity, Source,
)

BRIEF = ResearchBrief(topic="t", audience="devs", angle="a",
                      key_points=["k1", "k2"], sources=[Source(title="s")])
OUTLINE = Outline(title="Title", sections=[OutlineSection(heading="H1", summary="s", talking_points=["p"])])
SEO = SEOReport(primary_keyword="kw", secondary_keywords=["kw2"],
                meta_title="mt", meta_description="md", slug="the-slug")
DRAFT = Draft(title="Title", markdown="# Title\nbody", word_count=2)


def blocker_review():
    return ReviewNotes(verdict="revise", summary="needs work",
                       issues=[ReviewIssue(severity=Severity.blocker, location="H1",
                                           problem="missing k2", suggestion="add k2")])


def minor_review():
    return ReviewNotes(verdict="revise", summary="almost",
                       issues=[ReviewIssue(severity=Severity.minor, location="intro",
                                           problem="wordy", suggestion="trim")])


def approve_review():
    return ReviewNotes(verdict="approve", summary="good", issues=[])


class FakeLLM:
    """Stands in for app.llm.generate; scripts the reviewer verdicts."""

    def __init__(self, review_sequence=None):
        self.reviews = list(review_sequence or [approve_review()])
        self.writer_runs = 0

    def generate(self, agent, prompt, schema):
        if agent == "writer":
            self.writer_runs += 1
            return DRAFT
        if agent == "reviewer":
            return self.reviews.pop(0) if self.reviews else approve_review()
        return {"research": BRIEF, "outline": OUTLINE, "seo": SEO}[agent]

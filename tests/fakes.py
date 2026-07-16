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
DRAFT = Draft(
    title="Title",
    markdown="# Title\nThis is a draft about our target keyword kw. It has been written to cover all the aspects required by the blog generation pipeline. Let us make sure that we provide enough detail. We want this post to be very informative and detailed.\n\n## Section 1\nThis is the first section of the blog post. It discusses the key concepts and provides a comprehensive explanation of how things work. We aim to keep our paragraphs descriptive but structured, so that readers can follow the argument easily. This adds depth to our content.\n\n## Section 2\nHere is another section to expand the content further. We talk about local models, including Ollama and LM Studio. These systems make it easy to run large language models on personal computers, which is great for offline development. It saves time and resources.\n\n## Section 3\nFinally, we summarize the main points. Adopting automated pipelines helps teams iterate quickly and reduces the time needed for manual reviews. This ensures high-quality output every time and makes the process seamless.",
    word_count=200
)


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
        
        # Support schema checks for research agent
        from app.agents.research import SearchQueries
        if schema is SearchQueries:
            return SearchQueries(queries=["AI Agents", "Loop Engineering"])
            
        return {"research": BRIEF, "outline": OUTLINE, "seo": SEO}[agent]

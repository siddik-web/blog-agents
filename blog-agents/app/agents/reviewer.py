"""Reviewer agent: draft + brief + seo -> ReviewNotes.

Reports only. It sets `verdict` and lists issues with severity; it does NOT
decide whether the pipeline loops. The orchestrator owns that.
"""

from __future__ import annotations

from app import llm
from app.schemas import Draft, ResearchBrief, ReviewNotes, SEOReport


def run(draft: Draft, brief: ResearchBrief, seo: SEOReport) -> ReviewNotes:
    prompt = llm.load_prompt("reviewer").format(
        audience=brief.audience,
        angle=brief.angle,
        key_points="\n".join(f"- {p}" for p in brief.key_points),
        primary_keyword=seo.primary_keyword,
        draft_markdown=draft.markdown,
    )
    return llm.generate("reviewer", prompt, ReviewNotes)

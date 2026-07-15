"""SEO agent: ResearchBrief + Outline -> SEOReport."""
from __future__ import annotations

from app import llm
from app.schemas import Outline, ResearchBrief, SEOReport


def run(brief: ResearchBrief, outline: Outline) -> SEOReport:
    prompt = llm.load_prompt("seo").format(
        topic=brief.topic,
        audience=brief.audience,
        outline_json=outline.model_dump_json(indent=2),
    )
    return llm.generate("seo", prompt, SEOReport)

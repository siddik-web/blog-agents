"""Outline agent: ResearchBrief -> Outline."""
from __future__ import annotations

from app import llm
from app.schemas import Outline, ResearchBrief


def run(brief: ResearchBrief) -> Outline:
    prompt = llm.load_prompt("outline").format(
        topic=brief.topic,
        audience=brief.audience,
        brief_json=brief.model_dump_json(indent=2),
    )
    return llm.generate("outline", prompt, Outline)

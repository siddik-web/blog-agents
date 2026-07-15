"""Research agent: topic + audience -> ResearchBrief."""
from __future__ import annotations

from app import llm
from app.schemas import ResearchBrief


def run(topic: str, audience: str) -> ResearchBrief:
    prompt = llm.load_prompt("research").format(topic=topic, audience=audience)
    return llm.generate("research", prompt, ResearchBrief)

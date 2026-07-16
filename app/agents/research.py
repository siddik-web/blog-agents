"""Research agent: topic + audience -> ResearchBrief.

Runs a Level 1 Agent Loop:
Reasoning (generating search queries) -> Acting (calling mock search tool) -> Observing -> Synthesis.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from app import llm
from app.schemas import ResearchBrief
from app.tools import search_web
from app.emitter import emit


class SearchQueries(BaseModel):
    queries: list[str] = Field(description="1-3 distinct, specific search queries to find factual information.")


def run(topic: str, audience: str) -> ResearchBrief:
    # 1. Reasoning: generate search queries
    query_prompt = (
        f"You are a research planner. For the topic '{topic}' targeted at '{audience}', "
        f"what are the 1 to 3 most important search queries to gather concrete facts, "
        f"statistics, and expert views? Return only the queries."
    )
    
    # We use LLM to plan the tool usage (Search queries)
    planned = llm.generate("research", query_prompt, SearchQueries)
    queries = planned.queries[:3] if planned.queries else [topic]
    
    # 2. Acting & Observing: run search tool in a loop
    search_context = []
    for query in queries:
        emit("tool_start", "research", tool="search_web", query=query)
        results = search_web(query)
        emit("tool_done", "research", tool="search_web", query=query, count=len(results))
        
        for r in results:
            search_context.append(f"Source: {r['title']} ({r['url']})\nInfo: {r['snippet']}\n")
            
    context_str = "\n".join(search_context)
    
    # 3. Synthesis: compile research brief using the retrieved context
    synthesis_prompt = (
        f"You are a research agent. Synthesize a research brief for a blog post.\n\n"
        f"Topic: {topic}\n"
        f"Audience: {audience}\n\n"
        f"Here are the search results gathered by your search tool:\n"
        f"--- \n{context_str}\n---\n\n"
        f"Produce a tight research brief containing an angle, key points, and sources. "
        f"Use the sources gathered from the search tool above. Do not invent links."
    )
    
    return llm.generate("research", synthesis_prompt, ResearchBrief)

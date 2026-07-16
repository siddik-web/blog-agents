"""The blog pipeline as an in-process LangGraph.

    research -> outline -> seo -> writer -> reviewer -> (loop | save)

Agents are plain function calls. Routing and the revision loop live here, never
in the reviewer:
    approve / minor-only            -> save
    revise + blockers + under limit -> writer   (targeted revision)
    revise + blockers + at limit    -> save      (banner lists what's unresolved)

Nodes emit progress through a context-scoped hook the server binds to an
in-memory queue; when nothing is bound (CLI, tests) emit is a no-op.
"""

from __future__ import annotations

import contextvars
import re
from datetime import date
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app import config
from app.agents import outline as outline_agent
from app.agents import research as research_agent
from app.agents import reviewer as reviewer_agent
from app.agents import seo as seo_agent
from app.agents import writer as writer_agent
from app.schemas import Draft, Outline, ResearchBrief, ReviewNotes, SEOReport
from app.engine import log_run_trace

from app.emitter import emit, set_emitter


class BlogState(TypedDict, total=False):
    topic: str
    audience: str
    max_revisions: int
    brief: ResearchBrief
    outline: Outline
    seo: SEOReport
    draft: Draft
    review: ReviewNotes
    revision_count: int
    output_path: str


def research_node(state):
    emit("start", "research")
    brief = research_agent.run(state["topic"], state.get("audience", "general readers"))
    emit("done", "research", detail={"angle": brief.angle, "key_points": len(brief.key_points)})
    return {"brief": brief}


def outline_node(state):
    emit("start", "outline")
    out = outline_agent.run(state["brief"])
    emit("done", "outline", detail={"title": out.title, "sections": len(out.sections)})
    return {"outline": out}


def seo_node(state):
    emit("start", "seo")
    report = seo_agent.run(state["brief"], state["outline"])
    emit("done", "seo", detail={"primary_keyword": report.primary_keyword, "slug": report.slug})
    return {"seo": report}


def writer_node(state):
    review = state.get("review")
    revision = state.get("revision_count", 0)
    if review is not None:
        revision += 1
    emit("start", "writer", revision=revision)
    draft = writer_agent.run(
        brief=state["brief"], outline=state["outline"], seo=state["seo"],
        review=review, revision=revision,
    )
    emit("done", "writer", revision=revision, detail={"word_count": draft.word_count})
    return {"draft": draft, "revision_count": revision}


def reviewer_node(state):
    emit("start", "reviewer")
    notes = reviewer_agent.run(state["draft"], state["brief"], state["seo"])
    blockers = notes.blockers()
    emit("done", "reviewer", detail={
        "verdict": notes.verdict,
        "blockers": len(blockers),
        "minor": len(notes.issues) - len(blockers),
        "issues": [{"severity": i.severity.value, "location": i.location, "problem": i.problem} for i in notes.issues],
    })
    return {"review": notes}


def save_node(state):
    emit("start", "save")
    seo, draft, review = state["seo"], state["draft"], state.get("review")
    slug = seo.slug or _slugify(draft.title)
    out_dir = Path(config.OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{date.today().isoformat()}-{slug}.md"

    unresolved = review.blockers() if review else []
    front = [
        "---", f'title: "{draft.title}"', f'slug: "{slug}"',
        f'meta_title: "{seo.meta_title}"', f'meta_description: "{seo.meta_description}"',
        f'primary_keyword: "{seo.primary_keyword}"',
        f"revisions: {state.get('revision_count', 0)}", "---", "",
    ]
    banner = []
    if unresolved:
        banner = ["> [!WARNING] Shipped with unresolved blockers at the revision limit:",
                  *[f"> - {i.location}: {i.problem}" for i in unresolved], ""]
    text = "\n".join(front) + "\n".join(banner) + draft.markdown
    path.write_text(text, encoding="utf-8")

    emit("done", "save", detail={
        "path": str(path), "unresolved": len(unresolved), "title": draft.title, "slug": slug,
        "meta_title": seo.meta_title, "meta_description": seo.meta_description,
        "primary_keyword": seo.primary_keyword, "revisions": state.get("revision_count", 0),
        "content": text,
    })
    log_run_trace(state, str(path))
    return {"output_path": str(path)}


def route_after_review(state):
    review = state["review"]
    limit = state.get("max_revisions", config.MAX_REVISIONS)
    count = state.get("revision_count", 0)
    if review.verdict == "approve":
        dest, reason = "save", "approved"
    elif not review.blockers():
        dest, reason = "save", "only minor issues"
    elif count >= limit:
        dest, reason = "save", "revision limit reached"
    else:
        dest, reason = "writer", "blockers to fix"
    emit("route", "reviewer", to=dest, reason=reason, revision=count)
    return dest


def build_graph():
    g = StateGraph(BlogState)
    for name, node in [
        ("research", research_node), ("outline", outline_node), ("seo", seo_node),
        ("writer", writer_node), ("reviewer", reviewer_node), ("save", save_node),
    ]:
        g.add_node(name, node)
    g.add_edge(START, "research")
    g.add_edge("research", "outline")
    g.add_edge("outline", "seo")
    g.add_edge("seo", "writer")
    g.add_edge("writer", "reviewer")
    g.add_conditional_edges("reviewer", route_after_review, {"writer": "writer", "save": "save"})
    g.add_edge("save", END)
    return g.compile()


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "post"


def run(topic: str, audience: str = "general readers", max_revisions: int | None = None):
    graph = build_graph()
    return graph.invoke(
        {"topic": topic, "audience": audience, "revision_count": 0,
         "max_revisions": max_revisions if max_revisions is not None else config.MAX_REVISIONS},
        {"recursion_limit": 50},
    )

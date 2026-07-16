"""Writer agent: brief + outline + seo (+ optional review) -> Draft.

On revision passes it receives the reviewer's issues and is told to *edit*, not
rewrite, so each cycle is targeted rather than a fresh gamble.
"""

from __future__ import annotations

from app import llm
from app.schemas import Draft, Outline, ResearchBrief, ReviewNotes, SEOReport


def _revision_block(review: ReviewNotes | None, revision: int) -> str:
    """Build the revision instructions appended to the writer prompt.

    Empty on the first pass (no review yet). On later passes it lists the
    reviewer's issues, blockers first, and tells the writer to edit in place.
    """
    if review is None or not review.issues:
        return ""

    ordered = review.blockers() + [i for i in review.issues if i.severity.value != "blocker"]
    lines = [
        f"\n## REVISION {revision} — EDIT, DO NOT REWRITE",
        "Keep everything that works. Address each issue below and change only "
        "what the issue calls for. Blockers are mandatory:",
        "",
    ]
    for n, issue in enumerate(ordered, 1):
        lines.append(
            f"{n}. [{issue.severity.value.upper()}] {issue.location} — "
            f"{issue.problem} Fix: {issue.suggestion}"
        )
    return "\n".join(lines)


def run(
    brief: ResearchBrief,
    outline: Outline,
    seo: SEOReport,
    review: ReviewNotes | None = None,
    revision: int = 0,
) -> Draft:
    from app.engine import get_learned_guidelines
    guidelines = get_learned_guidelines()
    guidelines_block = f"\n## ADAPTIVE STYLE RULES (HILL-CLIMBING LOOP)\nApply these rules compiled from past trace analysis:\n{guidelines}\n" if guidelines else ""

    prompt = llm.load_prompt("writer").format(
        audience=brief.audience,
        brief_json=brief.model_dump_json(indent=2),
        outline_json=outline.model_dump_json(indent=2),
        seo_json=seo.model_dump_json(indent=2),
        revision_block=_revision_block(review, revision),
    )
    if guidelines_block:
        prompt += guidelines_block
        
    return llm.generate("writer", prompt, Draft)

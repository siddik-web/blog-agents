"""Reviewer agent: draft + brief + seo -> ReviewNotes.

Reports only. It sets `verdict` and lists issues with severity; it does NOT
decide whether the pipeline loops. The orchestrator owns that.

It also runs Level 2 Verification checks: deterministic rubric checks.
"""

from __future__ import annotations

import re
from app import llm
from app.schemas import Draft, ResearchBrief, ReviewNotes, SEOReport, ReviewIssue, Severity, VerificationCheck


def run(draft: Draft, brief: ResearchBrief, seo: SEOReport) -> ReviewNotes:
    # 1. Run LLM review to generate base notes
    prompt = llm.load_prompt("reviewer").format(
        audience=brief.audience,
        angle=brief.angle,
        key_points="\n".join(f"- {p}" for p in brief.key_points),
        primary_keyword=seo.primary_keyword,
        draft_markdown=draft.markdown,
    )
    notes = llm.generate("reviewer", prompt, ReviewNotes)
    
    # 2. Level 2 Verification: Programmatic Rubric Checks
    checks = []
    
    # Check 1: Word count check
    words = len(re.findall(r"\w+", draft.markdown))
    word_status = "passed" if words >= 150 else "failed"
    word_detail = f"Draft has {words} words (recommended >= 150 words)."
    checks.append(VerificationCheck(name="Word Count Check", status=word_status, detail=word_detail))
    if word_status == "failed":
        notes.issues.append(ReviewIssue(
            severity=Severity.blocker,
            location="Full Draft",
            problem=f"Draft is too short ({words} words).",
            suggestion="Expand on the key points to meet the minimum length of 150 words."
        ))

    # Check 2: SEO Primary Keyword check
    kw_present = seo.primary_keyword.lower() in draft.markdown.lower()
    seo_status = "passed" if kw_present else "failed"
    seo_detail = f"Primary keyword '{seo.primary_keyword}' is present." if kw_present else f"Primary keyword '{seo.primary_keyword}' is missing from the draft."
    checks.append(VerificationCheck(name="SEO Keyword Presence", status=seo_status, detail=seo_detail))
    if seo_status == "failed":
        notes.issues.append(ReviewIssue(
            severity=Severity.blocker,
            location="SEO Optimization",
            problem=f"Primary SEO keyword '{seo.primary_keyword}' is not found in the text.",
            suggestion=f"Weave the primary keyword '{seo.primary_keyword}' naturally into the introduction or a heading."
        ))

    # Check 3: Forbidden Clichés check
    forbidden = ["delve", "testament", "tapestry", "landscape", "journey", "look no further", "crucial", "essential", "furthermore", "moreover", "in conclusion", "game-changer"]
    found = [w for w in forbidden if re.search(r"\b" + re.escape(w) + r"\b", draft.markdown.lower())]
    cliche_status = "failed" if found else "passed"
    cliche_detail = f"Found forbidden clichés: {', '.join(found)}." if found else "No forbidden clichés found."
    checks.append(VerificationCheck(name="Forbidden Clichés Check", status=cliche_status, detail=cliche_detail))
    if cliche_status == "failed":
        notes.issues.append(ReviewIssue(
            severity=Severity.minor,
            location="Tone / Style",
            problem=f"Draft uses forbidden word(s): {', '.join(found)}.",
            suggestion="Rewrite sentences containing forbidden words to use more direct and professional language."
        ))

    # Check 4: Markdown headings structure check
    has_headings = bool(re.search(r"^##\s+", draft.markdown, re.MULTILINE))
    heading_status = "passed" if has_headings else "failed"
    heading_detail = "Found structured headings." if has_headings else "No H2 (##) headings found in Markdown."
    checks.append(VerificationCheck(name="Structure Check", status=heading_status, detail=heading_detail))
    if heading_status == "failed":
        notes.issues.append(ReviewIssue(
            severity=Severity.blocker,
            location="Document Structure",
            problem="Markdown lacks sub-headings (##).",
            suggestion="Add structured sub-headings (## Heading) to make the blog post scannable and organized."
        ))

    # 3. Apply checks to notes
    notes.checks = checks
    
    # 4. Re-evaluate verdict if new blockers were added programmatically
    has_blockers = any(i.severity == Severity.blocker for i in notes.issues)
    if has_blockers:
        notes.verdict = "revise"
    
    return notes

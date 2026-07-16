"""Level 4 Hill-Climbing Loop.

Analyzes production traces (run outcomes, reviewer issues) and programmatically
rewrites the system configuration (learned_guidelines.txt) to prevent future failures.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from pydantic import BaseModel, Field
from app import config, llm

TRACES_FILE = Path(config.OUTPUT_DIR) / "traces.json"
LEARNED_GUIDELINES_FILE = Path(config.OUTPUT_DIR) / "learned_guidelines.txt"


class OptimizationReport(BaseModel):
    analysis: str = Field(description="Detailed analysis of the common failures and issues found in the traces.")
    learned_guidelines: list[str] = Field(
        description="A list of 3-7 concrete, actionable writing guidelines for the writer to prevent these issues."
    )


def log_run_trace(state: dict, output_path: str):
    """Log the trace of a completed pipeline run to traces.json."""
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    
    review = state.get("review")
    issues_list = []
    if review:
        for issue in review.issues:
            issues_list.append({
                "severity": issue.severity.value,
                "location": issue.location,
                "problem": issue.problem,
                "suggestion": issue.suggestion
            })
            
    trace = {
        "topic": state.get("topic", ""),
        "audience": state.get("audience", ""),
        "revision_count": state.get("revision_count", 0),
        "unresolved_blockers": len(review.blockers()) if review else 0,
        "issues": issues_list,
        "output_path": output_path,
        "success": len(review.blockers()) == 0 if review else True
    }
    
    # Read existing traces
    traces = []
    if TRACES_FILE.exists():
        try:
            with open(TRACES_FILE, "r", encoding="utf-8") as f:
                traces = json.load(f)
        except Exception:
            pass
            
    traces.append(trace)
    
    with open(TRACES_FILE, "w", encoding="utf-8") as f:
        json.dump(traces, f, indent=2)


def get_traces() -> list[dict]:
    """Retrieve all traces."""
    if not TRACES_FILE.exists():
        return []
    try:
        with open(TRACES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def get_learned_guidelines() -> str:
    """Retrieve the current learned guidelines."""
    if not LEARNED_GUIDELINES_FILE.exists():
        return ""
    try:
        return LEARNED_GUIDELINES_FILE.read_text(encoding="utf-8")
    except Exception:
        return ""


def run_optimization() -> dict:
    """Run Level 4 Hill-Climbing Optimization.

    Analyzes traces and updates learned_guidelines.txt.
    """
    traces = get_traces()
    if not traces:
        return {"status": "skipped", "reason": "No traces found. Run the pipeline first."}
        
    # Summarize trace issues for the LLM
    summary_lines = []
    for idx, trace in enumerate(traces[-10:], 1):  # Analyze last 10 traces
        summary_lines.append(f"Run {idx}: Topic='{trace['topic']}', Success={trace['success']}, Revisions={trace['revision_count']}")
        if trace['issues']:
            summary_lines.append("  Issues flagged by Reviewer:")
            for issue in trace['issues']:
                summary_lines.append(f"    - [{issue['severity']}] at '{issue['location']}': {issue['problem']} (Fix suggestion: {issue['suggestion']})")
                
    traces_summary = "\n".join(summary_lines)
    
    prompt = (
        "You are an AI System Optimizer (LangSmith Engine equivalent). Analyze the traces of past blog writing runs "
        "and determine common flaws or failure modes (e.g. style errors, forbidden words, word count issues, or bad hooks).\n\n"
        "Here is the summary of recent run traces:\n"
        f"```\n{traces_summary}\n```\n\n"
        "Generate an Optimization Report. In `learned_guidelines`, compile a set of concrete, actionable writing guidelines "
        "specifically designed to prevent these issues in future runs. These rules will be appended to the writer agent's "
        "system prompt. Make them direct and concise (e.g., 'Do not use the word X', 'Keep word count above 200 words')."
    )
    
    # We use LLM to perform meta-analysis (Hill climbing)
    # Define optimizer agent config in configs or run it under 'reviewer' model
    report = llm.generate("reviewer", prompt, OptimizationReport)
    
    # Save the learned guidelines
    guidelines_text = "\n".join(f"- {rule}" for rule in report.learned_guidelines)
    
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    LEARNED_GUIDELINES_FILE.write_text(guidelines_text, encoding="utf-8")
    
    return {
        "status": "success",
        "analysis": report.analysis,
        "guidelines": report.learned_guidelines,
        "guidelines_text": guidelines_text
    }

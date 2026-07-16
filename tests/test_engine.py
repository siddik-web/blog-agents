"""Test Level 4 Hill-Climbing loop components (trace logging and prompt optimization)."""
from __future__ import annotations

import tempfile
from pathlib import Path
from app.schemas import ReviewNotes, ReviewIssue, Severity
import app.config as config
import app.engine as engine
from tests.fakes import DRAFT, BRIEF, SEO


def test_trace_logging():
    # Setup temporary directory for output
    tmp_dir = tempfile.mkdtemp()
    config.OUTPUT_DIR = tmp_dir
    engine.TRACES_FILE = Path(tmp_dir) / "traces.json"
    
    # Define a test state
    review = ReviewNotes(
        verdict="revise",
        summary="contains issues",
        issues=[ReviewIssue(severity=Severity.blocker, location="H1", problem="Missing keyword", suggestion="Add kw")]
    )
    state = {
        "topic": "Testing Hill-Climbing",
        "audience": "Developers",
        "revision_count": 1,
        "review": review
    }
    
    # Log trace
    engine.log_run_trace(state, f"{tmp_dir}/dummy_post.md")
    
    # Retrieve and verify trace
    traces = engine.get_traces()
    assert len(traces) == 1
    assert traces[0]["topic"] == "Testing Hill-Climbing"
    assert traces[0]["unresolved_blockers"] == 1
    assert traces[0]["issues"][0]["problem"] == "Missing keyword"


def test_optimization():
    # Setup temp outputs
    tmp_dir = tempfile.mkdtemp()
    config.OUTPUT_DIR = tmp_dir
    engine.TRACES_FILE = Path(tmp_dir) / "traces.json"
    engine.LEARNED_GUIDELINES_FILE = Path(tmp_dir) / "learned_guidelines.txt"
    
    # Mock traces
    state = {
        "topic": "Testing Hill-Climbing",
        "audience": "Developers",
        "revision_count": 2,
        "review": ReviewNotes(
            verdict="revise",
            summary="contains issues",
            issues=[ReviewIssue(severity=Severity.blocker, location="Tone", problem="Used word 'delve'", suggestion="Remove delve")]
        )
    }
    engine.log_run_trace(state, f"{tmp_dir}/dummy.md")
    
    # Mock LLM response for optimization report
    from app import llm
    
    class FakeReport:
        def __init__(self):
            self.analysis = "Too many occurrences of the word delve."
            self.learned_guidelines = ["Avoid using the word delve.", "Keep language direct."]
            
    def mock_generate(agent, prompt, schema):
        return FakeReport()
        
    original_generate = llm.generate
    llm.generate = mock_generate
    
    try:
        res = engine.run_optimization()
        assert res["status"] == "success"
        assert len(res["guidelines"]) == 2
        
        # Verify guidelines file is written
        guidelines_content = engine.get_learned_guidelines()
        assert "Avoid using the word delve." in guidelines_content
    finally:
        llm.generate = original_generate

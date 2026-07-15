"""Schema contracts parse + round-trip from fixtures."""
from __future__ import annotations
import json
from pathlib import Path
from app.schemas import Draft, Outline, ResearchBrief, ReviewNotes, SEOReport

FIXTURES = Path(__file__).parent / "fixtures"
CASES = [("brief.json", ResearchBrief), ("outline.json", Outline), ("seo.json", SEOReport),
         ("draft.json", Draft), ("review.json", ReviewNotes)]


def test_schemas_round_trip():
    for filename, model in CASES:
        obj = model.model_validate(json.loads((FIXTURES / filename).read_text()))
        model.model_validate(json.loads(obj.model_dump_json()))
    review = ReviewNotes.model_validate(json.loads((FIXTURES / "review.json").read_text()))
    assert all(b.severity.value == "blocker" for b in review.blockers())


if __name__ == "__main__":
    test_schemas_round_trip()
    print("PASS  schema contracts")

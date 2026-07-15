"""The revision loop, four control paths, with the model faked in-process."""
from __future__ import annotations
import tempfile


def _run(review_sequence, max_revisions=2):
    import app.config as config
    import app.llm as llm
    from app import pipeline
    from tests.fakes import FakeLLM

    fake = FakeLLM(review_sequence)
    llm.generate = fake.generate
    config.OUTPUT_DIR = tempfile.mkdtemp()

    events = []
    pipeline.set_emitter(events.append)
    pipeline.run("t", "devs", max_revisions)
    return fake, events


def test_approve_first():
    from tests.fakes import approve_review
    fake, events = _run([approve_review()])
    assert fake.writer_runs == 1
    assert ("done", "save") in [(e["kind"], e.get("stage")) for e in events]


def test_blocker_then_approve():
    from tests.fakes import approve_review, blocker_review
    fake, events = _run([blocker_review(), approve_review()])
    assert fake.writer_runs == 2
    assert any(e["kind"] == "route" and e["to"] == "writer" for e in events)


def test_persistent_blockers_capped():
    from tests.fakes import blocker_review
    fake, events = _run([blocker_review()] * 9, max_revisions=2)
    assert fake.writer_runs == 3  # initial + 2 revisions
    save = next(e for e in events if e["kind"] == "done" and e["stage"] == "save")
    assert save["detail"]["unresolved"] == 1


def test_minor_only_no_loop():
    from tests.fakes import minor_review
    fake, events = _run([minor_review()])
    assert fake.writer_runs == 1


if __name__ == "__main__":
    for fn in (test_approve_first, test_blocker_then_approve, test_persistent_blockers_capped, test_minor_only_no_loop):
        fn()
    print("PASS  revision loop (in-process)")

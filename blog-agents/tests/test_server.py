"""Full run streamed through the single-app HTTP endpoint (model faked)."""
from __future__ import annotations
import json
import tempfile


def test_run_stream():
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        print("SKIP  fastapi/httpx not installed"); return

    import app.config as config
    import app.llm as llm
    from app import server
    from tests.fakes import FakeLLM, approve_review, blocker_review

    llm.generate = FakeLLM([blocker_review(), approve_review()]).generate
    config.OUTPUT_DIR = tempfile.mkdtemp()

    client = TestClient(server.app)
    assert client.get("/").status_code == 200
    assert "blog-agents" in client.get("/").text
    assert client.get("/api/health").status_code == 200

    events = []
    with client.stream("POST", "/api/run", json={"topic": "t", "audience": "devs", "max_revisions": 2}) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if line:
                events.append(json.loads(line))

    kinds = [(e["kind"], e.get("stage")) for e in events]
    assert kinds.count(("start", "writer")) == 2
    assert any(e["kind"] == "route" and e["to"] == "writer" for e in events)
    assert events[-1]["kind"] == "end"
    save = next(e for e in events if e["kind"] == "done" and e["stage"] == "save")
    assert "title:" in save["detail"]["content"]


if __name__ == "__main__":
    test_run_stream()
    print("PASS  server stream")

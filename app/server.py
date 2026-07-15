"""Single-container web app: serves the UI and streams a run in-process.

The pipeline runs in a worker thread whose emitter pushes onto an in-memory
queue; the /api/run response drains it as newline-delimited JSON. No Redis, no
inter-service calls — one process does everything.
"""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app import config, pipeline

app = FastAPI(title="blog-agents")
WEB = Path(__file__).parent / "web"
_DONE = object()


class RunRequest(BaseModel):
    topic: str
    audience: str = "general readers"
    max_revisions: int = config.MAX_REVISIONS


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (WEB / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> dict:
    info = {"provider": config.PROVIDER, "base_url": config.BASE_URL, "model": config.MODEL}
    try:
        from openai import OpenAI

        client = OpenAI(base_url=config.BASE_URL, api_key=config.API_KEY or "not-needed")
        models = [m.id for m in client.models.list().data]
        info["ok"] = True
        info["model_available"] = any(config.MODEL.split(":")[0] in m for m in models)
    except Exception as exc:
        info["ok"] = False
        info["error"] = str(exc)
    return info


@app.post("/api/run")
def run(req: RunRequest) -> StreamingResponse:
    events: "queue.Queue" = queue.Queue()

    def worker():
        pipeline.set_emitter(events.put)
        events.put({"kind": "run_start", "topic": req.topic,
                    "audience": req.audience, "max_revisions": req.max_revisions})
        try:
            pipeline.run(req.topic, req.audience, req.max_revisions)
        except Exception as exc:
            events.put({"kind": "error", "message": str(exc)})
        finally:
            events.put(_DONE)

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        while True:
            item = events.get()
            if item is _DONE:
                yield json.dumps({"kind": "end"}) + "\n"
                break
            yield json.dumps(item) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


def main():
    import uvicorn

    print(f"blog-agents  ·  provider={config.PROVIDER}  model={config.MODEL}")
    print("open http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    main()

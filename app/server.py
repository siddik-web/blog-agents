"""Single-container web app: serves the UI and streams a run in-process.

Also implements Level 3 Event-Driven Loop (Schedules, Cron, Webhook Triggers).
"""

from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app import config, pipeline
from app.engine import get_traces, get_learned_guidelines, run_optimization

app = FastAPI(title="blog-agents")
WEB = Path(__file__).parent / "web"
_DONE = object()

# Level 3: Event-Driven Loop State
schedules = [
    {
        "id": "1",
        "topic": "Loop Engineering in AI Agents",
        "audience": "developers",
        "interval_seconds": 60,
        "enabled": False,
        "last_run": None,
    },
    {
        "id": "2",
        "topic": "Why Local LLMs are the Future",
        "audience": "general readers",
        "interval_seconds": 120,
        "enabled": False,
        "last_run": None,
    },
]

scheduled_runs_log = []


class RunRequest(BaseModel):
    topic: str
    audience: str = "general readers"
    max_revisions: int = config.MAX_REVISIONS


class WebhookRequest(BaseModel):
    topic: str
    audience: str = "general readers"


class ScheduleCreateRequest(BaseModel):
    topic: str
    audience: str = "general readers"
    interval_seconds: int = 60


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


# Level 3 API Endpoints
@app.get("/api/schedules")
def get_schedules():
    return {"schedules": schedules, "history": scheduled_runs_log}


@app.post("/api/schedules/create")
def create_schedule(req: ScheduleCreateRequest):
    new_id = str(len(schedules) + 1)
    s = {
        "id": new_id,
        "topic": req.topic,
        "audience": req.audience,
        "interval_seconds": req.interval_seconds,
        "enabled": True,
        "last_run": None,
    }
    schedules.append(s)
    return {"status": "created", "schedule": s}


@app.post("/api/schedules/{schedule_id}/toggle")
def toggle_schedule(schedule_id: str):
    for s in schedules:
        if s["id"] == schedule_id:
            s["enabled"] = not s["enabled"]
            # Reset last run to start immediately if enabled
            if s["enabled"]:
                s["last_run"] = None
            return {"status": "updated", "schedule": s}
    raise HTTPException(status_code=404, detail="Schedule not found")


@app.post("/api/webhook")
def trigger_webhook(req: WebhookRequest):
    # Trigger a background run as if by webhook
    log_entry = {
        "id": f"webhook-{int(time.time())}",
        "topic": req.topic,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Running (Webhook)",
    }
    scheduled_runs_log.append(log_entry)

    def bg_runner(entry_id, t, a):
        try:
            pipeline.run(t, a)
            for l in scheduled_runs_log:
                if l["id"] == entry_id:
                    l["status"] = "Completed"
        except Exception as e:
            for l in scheduled_runs_log:
                if l["id"] == entry_id:
                    l["status"] = f"Failed: {str(e)}"

    threading.Thread(target=bg_runner, args=(log_entry["id"], req.topic, req.audience), daemon=True).start()
    return {"status": "triggered", "log_id": log_entry["id"]}


# Level 3 Cron/Schedule Loop
async def scheduler_loop():
    while True:
        await asyncio.sleep(2)
        now = time.time()
        for s in schedules:
            if s["enabled"]:
                last = s["last_run"]
                if last is None or (now - last) >= s["interval_seconds"]:
                    s["last_run"] = now
                    topic = s["topic"]
                    audience = s["audience"]

                    log_entry = {
                        "id": f"cron-{s['id']}-{int(now)}",
                        "topic": topic,
                        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "status": "Running",
                    }
                    scheduled_runs_log.append(log_entry)

                    def bg_runner(entry_id, t, a):
                        try:
                            pipeline.run(t, a)
                            for l in scheduled_runs_log:
                                if l["id"] == entry_id:
                                    l["status"] = "Completed"
                        except Exception as e:
                            for l in scheduled_runs_log:
                                if l["id"] == entry_id:
                                    l["status"] = f"Failed: {str(e)}"

                    threading.Thread(target=bg_runner, args=(log_entry["id"], topic, audience), daemon=True).start()


@app.get("/api/traces")
def api_get_traces():
    return {"traces": get_traces()}


@app.get("/api/guidelines")
def api_get_guidelines():
    return {"guidelines": get_learned_guidelines()}


@app.post("/api/optimize")
def api_run_optimization():
    res = run_optimization()
    return res


@app.on_event("startup")
def startup_event():
    loop = asyncio.get_event_loop()
    loop.create_task(scheduler_loop())


def main():
    import uvicorn

    print(f"blog-agents  ·  provider={config.PROVIDER}  model={config.MODEL}")
    print("open http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    main()

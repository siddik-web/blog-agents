# Loop Engineering Blog Agent (blog-agents)

A showcase of the **Four-Loop Stack of Loop Engineering** built on FastAPI, LangGraph, and local LLMs (Ollama or LM Studio). One container, one process: serves an interactive UI and runs the pipeline in-process.

```
                  [Level 3: Event-Driven Loop] ──► Trigger (Webhook/Cron)
                                                        │
                                                        ▼
                                         [Level 1: Agent Loop (Research)]
                                           (Reason ◄─► Act [Search Tool])
                                                        │
                                                        ▼
                                              [Outline & SEO Nodes]
                                                        │
                                                        ▼
                                               [Writer Agent]
                                                        │
                                                        ▼
                                     [Level 2: Verification Loop (Reviewer)]
                                       (Grade Draft against Rubric)
                                       ├───► [FAIL] ──► Route back to Writer (Revision)
                                       └───► [PASS] ──► Save Post & Log Trace
                                                            │
                                                            ▼
                                        [Level 4: Hill-Climbing Loop (Engine)]
                                          (Analyze Traces ──► Update Prompts)
```

## Features

### 1. Loop 1: The Agent Loop (Reasoning & Tools)
The **Research Agent** runs a tool-use loop:
- Planners formulate search queries based on the topic.
- The agent calls the `search_web` tool (defined in `app/tools.py`) to gather facts and citations.
- It iterates until enough search results are gathered, then synthesizes a structured `ResearchBrief`.

### 2. Loop 2: The Verification Loop (Quality Guardrails)
The **Reviewer Agent** runs automated evaluation checks on drafts before human or LLM critique:
- **Programmatic Rubric Checks**: Word count verification, SEO keyword density check, structure check (headings presence), and a check for forbidden clichés (e.g., "delve", "tapestry").
- Fails trigger blockers that route execution back to the Writer with specific instructions for targeted editing.

### 3. Loop 3: The Event-Driven Loop (Schedules & Webhooks)
Integrates the agent pipeline into the surrounding ecosystem:
- **Cron Schedules**: A background task runner in FastAPI that executes blog runs periodically.
- **Webhook endpoint (`POST /api/webhook`)**: Allows external systems (CI/CD, GitHub, Slack) to trigger a blog-writing run programmatically.

### 4. Loop 4: The Hill-Climbing Loop (Continuous Self-Improvement)
The agent system programmatically learns from its own history:
- Telemetry and verification outputs are logged as traces in `output/traces.json`.
- A trace optimizer agent ("Engine") periodically analyzes trace logs to identify failure patterns.
- It compiles optimized style and formatting rules into `learned_guidelines.txt`, which are automatically loaded and appended to the Writer Agent's system prompt for subsequent runs.

---

## Prerequisites

Ensure you have the following installed:
- **Docker & Docker Compose** (recommended for containerized setup)
- **Python 3.9+** (required for local runs)
- An LLM backend: **Ollama** or **LM Studio**

---

## Quick Start

### Activation (Without Docker)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

3. **Start the Web UI & API server**:
   ```bash
   python -m app.server
   ```
   Open [http://localhost:8000](http://localhost:8000) to view the Loop Engineering Dashboard.

### running with Docker

```bash
docker compose up --build
docker compose exec ollama ollama pull llama3.1     # first run only
```

---

## Configuration

The application is configured using environment variables (stored in `.env`).

### General Config

| Variable | Description | Default |
|----------|-------------|---------|
| `BLOG_PROVIDER` | Backend provider (`ollama` or `lmstudio`) | `ollama` |
| `BLOG_BASE_URL` | Endpoint url for the LLM API | `http://localhost:11434/v1` |
| `BLOG_API_KEY` | API key (if needed by your model backend) | `not-needed` |
| `BLOG_MODEL` | Default model for agents | `llama3.1` (Ollama) or `local-model` (LM Studio) |
| `BLOG_MODEL_STRONG` | High-reasoning model for Writer and Reviewer nodes | Same as `BLOG_MODEL` |
| `BLOG_MODEL_FAST` | Faster, lightweight model for Research, Outline, and SEO | Same as `BLOG_MODEL` |
| `BLOG_MAX_REVISIONS` | Max number of verifier-gated revision loop cycles | `2` |
| `OUTPUT_DIR` | Location where generated markdown posts are saved | `output` |

### Search API Configuration (Level 1 Agent Loop)

You can specify a search provider by setting `SEARCH_PROVIDER` to `tavily`, `brave`, `serper`, `google`, or `mock`. If not set, it is auto-detected based on the environment keys:

| Provider | Environment Variables Required | Description |
|---|---|---|
| **Tavily** | `TAVILY_API_KEY` | Search API optimized for LLMs (recommended). |
| **Brave Search** | `BRAVE_API_KEY` | Web search API from Brave. |
| **Serper** | `SERPER_API_KEY` | Fast Google Search API via serper.dev. |
| **Google CSE** | `GOOGLE_API_KEY`, `GOOGLE_CSE_ID` | Standard Google Custom Search Engine API. |
| **Mock** | *None* | Fallback local simulated results (default). |

---

## The Dashboard Interface

The updated web interface showcases the 4 loops visually:
- **1. Pipeline Workspace**: Run manual topics, inspect Level 1 tool calls, watch Level 2 verification checklists update in real-time.
- **2. Scheduler & Webhooks**: Configure cron triggers, view trigger history, and copy webhook commands.
- **3. Hill-Climbing Auto-Opt**: Inspect recent traces, view programmatically generated writing rules, and trigger prompt optimization with one click.

---

## Run Tests (Offline)

Run the full offline test suite (no Docker or running LLM needed):
```bash
python -m tests.run_all
```

- `test_schemas` — Schema serialization validation.
- `test_loop` — Controls loop logic (approve, revise, cap limits).
- `test_server` — Endpoint validation and streaming output.
- `test_engine` — Verify Level 4 trace logging and prompt auto-optimization.

---

## Layout

```
app/
  server.py         FastAPI: UI server, schedules, webhooks
  pipeline.py       LangGraph workflow definition & routing
  emitter.py        Context-scoped emitter (avoids circular imports)
  tools.py          Search tools for Agent Loop
  engine.py         Trace logging & optimization (Hill Climbing)
  agents/           research · outline · seo · writer · reviewer
  llm.py            LLM client wrapper & JSON repair helper
  schemas.py        Pydantic data models
  web/index.html    Dashboard UI
tests/              Offline test suite
```

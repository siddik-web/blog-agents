"""Configuration for the single-container app.

Just two concerns now: which model backend to call, and the revision limit.
No service topology, no Redis — everything runs in one process.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

PROVIDER = os.getenv("BLOG_PROVIDER", "ollama").lower()

_DEFAULTS = {
    "ollama": ("http://localhost:11434/v1", "llama3.1"),
    "lmstudio": ("http://localhost:1234/v1", "local-model"),
}
_base, _default_model = _DEFAULTS.get(PROVIDER, _DEFAULTS["ollama"])

BASE_URL = os.getenv("BLOG_BASE_URL", _base)
API_KEY = os.getenv("BLOG_API_KEY", PROVIDER or "not-needed")
MODEL = os.getenv("BLOG_MODEL", _default_model)
STRONG = os.getenv("BLOG_MODEL_STRONG", MODEL)
FAST = os.getenv("BLOG_MODEL_FAST", MODEL)


@dataclass(frozen=True)
class AgentConfig:
    model: str
    temperature: float


AGENTS: dict[str, AgentConfig] = {
    "research": AgentConfig(model=STRONG, temperature=0.4),
    "outline": AgentConfig(model=STRONG, temperature=0.4),
    "seo": AgentConfig(model=FAST, temperature=0.2),
    "writer": AgentConfig(model=STRONG, temperature=0.7),
    "reviewer": AgentConfig(model=STRONG, temperature=0.2),
}

MAX_REVISIONS = int(os.getenv("BLOG_MAX_REVISIONS", "2"))

# Where finished posts land. Relative for local runs; the container sets it to a
# mounted volume path via OUTPUT_DIR.
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

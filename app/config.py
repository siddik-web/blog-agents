"""Configuration for the single-container app.

Just two concerns now: which model backend to call, and the revision limit.
No service topology, no Redis — everything runs in one process.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

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


def get_wp_config() -> dict:
    """Return the active WordPress config, dynamically loading overrides from settings.json."""
    import json
    from pathlib import Path

    url = os.getenv("WP_URL")
    username = os.getenv("WP_USERNAME")
    password = os.getenv("WP_APPLICATION_PASSWORD")
    categories = [c.strip() for c in os.getenv("WP_DEFAULT_CATEGORIES", "Uncategorized").split(",") if c.strip()]

    settings_file = Path(OUTPUT_DIR) / "settings.json"
    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
                if settings.get("wp_url"):
                    url = settings["wp_url"]
                if settings.get("wp_username"):
                    username = settings["wp_username"]
                if settings.get("wp_password"):
                    password = settings["wp_password"]
                if "wp_default_categories" in settings:
                    cats = settings["wp_default_categories"]
                    if isinstance(cats, str):
                        categories = [c.strip() for c in cats.split(",") if c.strip()]
                    elif isinstance(cats, list):
                        categories = cats
        except Exception:
            pass

    return {
        "url": url,
        "username": username,
        "password": password,
        "default_categories": categories,
    }


"""Thin local-LLM layer: one structured call + prompt loader.

Talks to any OpenAI-compatible server (Ollama / LM Studio) via the `openai` SDK.
This is the ONLY module that touches a model — swap the backend here and the
graph, agents, schemas, and prompts are untouched.

Getting reliable JSON out of local models takes three cooperating layers:

1. Grammar-constrained decoding — we pass the Pydantic schema as `response_format`
   so the server (llama.cpp under Ollama, or LM Studio) masks tokens to the shape.
2. Prompt instruction — Ollama doesn't inject the schema into the model's context,
   so we also state the schema in a system message (its own docs recommend this).
3. Validate-and-repair — grammar decoding can still truncate; we validate with
   Pydantic and, on failure, feed the error back for one repair attempt.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app import config

PROMPTS_DIR = Path(__file__).parent / "prompts"
T = TypeVar("T", bound=BaseModel)

_SYSTEM = (
    "You output data, not prose. Return a SINGLE JSON object that conforms exactly "
    "to this JSON Schema. No explanation, no markdown fences — JSON only. If you "
    "cannot fill a field, use an empty string or empty list rather than omitting "
    "it.\n\nJSON Schema:\n{schema}"
)

_REPAIR = (
    "Your previous response did not validate against the schema:\n{error}\n\n"
    "Return the corrected JSON object only."
)


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI

    # Use a generous timeout for local models that need loading/warmup
    return OpenAI(base_url=config.BASE_URL, api_key=config.API_KEY or "not-needed", timeout=120.0)



def load_prompt(name: str) -> str:
    """Load prompts/<name>.md as a format string."""
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _extract_json(text):
    """Best-effort cleanup for models that wrap JSON in prose or ``` fences."""
    if not text:
        raise ValueError("empty response from model")
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
        t = t.strip("` \n")
    if not t.startswith("{"):
        start, end = t.find("{"), t.rfind("}")
        if start != -1 and end != -1:
            t = t[start : end + 1]
    return t


def _create_json(cfg, messages):
    """Plain call in json_object mode (universally supported fallback)."""
    resp = _client().chat.completions.create(
        model=cfg.model,
        messages=messages,
        temperature=cfg.temperature,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content


def _parse_structured(cfg, messages, schema):
    """Grammar-constrained parse. Returns (parsed_or_None, raw_content)."""
    completions = _client().chat.completions
    parse = getattr(completions, "parse", None) or _client().beta.chat.completions.parse
    completion = parse(
        model=cfg.model,
        messages=messages,
        temperature=cfg.temperature,
        response_format=schema,
    )
    msg = completion.choices[0].message
    return getattr(msg, "parsed", None), msg.content


def generate(agent, prompt, schema):
    """Run one agent's call and return a validated `schema` instance."""
    cfg = config.AGENTS[agent]
    schema_json = json.dumps(schema.model_json_schema(), indent=2)
    messages = [
        {"role": "system", "content": _SYSTEM.format(schema=schema_json)},
        {"role": "user", "content": prompt},
    ]

    # Layer 1+2: schema-constrained decoding. Fall back to json_object mode for
    # models/servers that ignore or reject json_schema response_format.
    content = None
    try:
        parsed, content = _parse_structured(cfg, messages, schema)
        if parsed is not None:
            return parsed
    except Exception:
        try:
            content = _create_json(cfg, messages)
        except Exception as exc:  # transport/connection error — surface clearly
            raise RuntimeError(
                f"[{agent}] could not reach the model at {config.BASE_URL}. "
                f"Is the local server running and BLOG_MODEL='{cfg.model}' available? "
                f"({exc})"
            ) from exc

    # Layer 3: validate, and repair once if needed.
    try:
        return schema.model_validate_json(_extract_json(content))
    except (ValidationError, ValueError) as first_err:
        messages.append({"role": "assistant", "content": content or ""})
        messages.append({"role": "user", "content": _REPAIR.format(error=first_err)})
        repaired = _create_json(cfg, messages)
        try:
            return schema.model_validate_json(_extract_json(repaired))
        except (ValidationError, ValueError) as exc:
            raise ValueError(
                f"[{agent}] model output failed to match {schema.__name__} after a "
                f"repair attempt:\n{repaired}"
            ) from exc

"""Context-scoped event emitter to avoid circular dependencies."""
from __future__ import annotations

import contextvars

_emitter: contextvars.ContextVar = contextvars.ContextVar("emitter", default=None)


def set_emitter(fn):
    _emitter.set(fn)


def emit(kind, stage=None, **data):
    fn = _emitter.get()
    if fn is not None:
        fn({"kind": kind, "stage": stage, **data})

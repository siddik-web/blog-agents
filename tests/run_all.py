"""Run the suite without pytest:  python -m tests.run_all"""
from __future__ import annotations
import importlib, traceback

MODULES = ["tests.test_schemas", "tests.test_loop", "tests.test_server", "tests.test_engine", "tests.test_wordpress"]


def main():
    failures = 0
    for name in MODULES:
        mod = importlib.import_module(name)
        for n in [x for x in dir(mod) if x.startswith("test_")]:
            fn = getattr(mod, n)
            if not callable(fn):
                continue
            try:
                fn(); print(f"PASS  {name}.{n}")
            except Exception:
                failures += 1; print(f"FAIL  {name}.{n}"); traceback.print_exc()
    print("\n" + ("all green" if not failures else f"{failures} failure(s)"))
    return failures


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)

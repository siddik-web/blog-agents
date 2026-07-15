"""Command-line run:  python -m app.cli "your topic here"

Prints each stage as it happens and the output path at the end. Same pipeline
the web app uses; handy for scripting or a quick check without the browser.
"""

from __future__ import annotations

import sys

from app import config, pipeline


def main():
    topic = " ".join(sys.argv[1:]).strip() or input("Blog topic: ").strip()
    audience = input("Audience (Enter for 'general readers'): ").strip() or "general readers"

    def show(ev):
        k, s = ev["kind"], ev.get("stage")
        if k == "start":
            rev = f" (revision {ev['revision']})" if ev.get("revision") else ""
            print(f"  → {s}{rev}")
        elif k == "done" and s == "reviewer":
            print(f"    reviewer: {ev['detail']['verdict']} "
                  f"({ev['detail']['blockers']} blocker, {ev['detail']['minor']} minor)")
        elif k == "route" and ev["to"] == "writer":
            print("    ↩ revising")
        elif k == "done" and s == "save":
            print(f"\nsaved → {ev['detail']['path']}")
        elif k == "error":
            print(f"  error: {ev['message']}")

    print(f"blog-agents · {topic} · model={config.MODEL}\n")
    pipeline.set_emitter(show)
    pipeline.run(topic, audience)


if __name__ == "__main__":
    main()

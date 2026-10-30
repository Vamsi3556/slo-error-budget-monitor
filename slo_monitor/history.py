"""Append-only JSON history store for check results.

Deliberately not a database: the GitHub Actions workflow commits this file back to
the repo after every run, so history travels with the repo and needs no external
infrastructure. `max_records` bounds its growth over time.
"""

from __future__ import annotations

import json
from pathlib import Path


def load_history(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_history(path: str | Path, records: list[dict], max_records: int = 5000) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    trimmed = records[-max_records:]
    with p.open("w", encoding="utf-8") as f:
        json.dump(trimmed, f, indent=2)
        f.write("\n")

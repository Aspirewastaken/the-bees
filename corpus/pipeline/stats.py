#!/usr/bin/env python3
"""Print corpus statistics for a JSONL directory or file."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print total examples, per-category counts, and label distribution."
    )
    parser.add_argument("path", help="Path to a JSONL file or directory.")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def select_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_dir():
        raise ValueError(f"Not a file or directory: {path}")

    canonical = path / "constitutional_corpus_v1.jsonl"
    if canonical.exists():
        return [canonical]

    return sorted(p for p in path.glob("*.jsonl") if p.is_file())


def main() -> int:
    args = parse_args()
    target = Path(args.path).expanduser()
    files = select_files(target)
    if not files:
        print(f"No JSONL files found at {target}")
        return 1

    rows: list[dict[str, Any]] = []
    for file_path in files:
        rows.extend(read_jsonl(file_path))

    category_counts = Counter(str(item.get("category", "unknown")) for item in rows)
    label_counts = Counter(str(item.get("label", "unknown")) for item in rows)

    print("Files analyzed:")
    for file_path in files:
        print(f"  - {file_path}")
    print(f"Total examples: {len(rows)}")
    print("Label distribution:")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")
    print("Per-category counts:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

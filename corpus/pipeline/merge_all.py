#!/usr/bin/env python3
"""Merge verified JSONL batches into a single final corpus file."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERIFIED_DIR = PROJECT_ROOT / "corpus" / "data" / "verified"
FINAL_DIR = PROJECT_ROOT / "corpus" / "data" / "final"
FINAL_PATH = FINAL_DIR / "constitutional_corpus_v1.jsonl"


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                records.append(payload)
    return records


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")


def main() -> int:
    if not VERIFIED_DIR.exists():
        print(f"No verified directory found at {VERIFIED_DIR}")
        return 1

    files = sorted(p for p in VERIFIED_DIR.glob("*.jsonl") if p.is_file())
    if not files:
        print(f"No JSONL files found in {VERIFIED_DIR}")
        return 1

    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    duplicate_ids = 0

    for file_path in files:
        rows = iter_jsonl(file_path)
        for row in rows:
            row_id = str(row.get("id", "")).strip()
            if row_id and row_id in seen_ids:
                duplicate_ids += 1
                continue
            if row_id:
                seen_ids.add(row_id)
            merged.append(row)

    merged.sort(key=lambda item: str(item.get("id", "")))
    write_jsonl(FINAL_PATH, merged)

    category_counts = Counter(str(item.get("category", "unknown")) for item in merged)
    label_counts = Counter(str(item.get("label", "unknown")) for item in merged)

    print(f"Merged files: {len(files)}")
    print(f"Output file: {FINAL_PATH}")
    print(f"Total examples: {len(merged)}")
    print(f"Duplicate IDs skipped: {duplicate_ids}")
    print("Label distribution:")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")
    print("Per-category counts:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Create stratified train/val/test splits from the final corpus."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FINAL_DIR = PROJECT_ROOT / "corpus" / "data" / "final"
FINAL_CORPUS = FINAL_DIR / "constitutional_corpus_v1.jsonl"
RNG_SEED = 42


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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
    if not FINAL_CORPUS.exists():
        print(f"Missing final corpus: {FINAL_CORPUS}")
        return 1

    rows = read_jsonl(FINAL_CORPUS)
    if not rows:
        print(f"No examples found in {FINAL_CORPUS}")
        return 1

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        category = str(row.get("category", "unknown"))
        grouped[category].append(row)

    rng = random.Random(RNG_SEED)
    train: list[dict[str, Any]] = []
    val: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []

    for category in sorted(grouped):
        items = grouped[category]
        rng.shuffle(items)

        n_total = len(items)
        n_train = int(n_total * 0.8)
        n_val = int(n_total * 0.1)
        n_test = n_total - n_train - n_val

        train.extend(items[:n_train])
        val.extend(items[n_train : n_train + n_val])
        test.extend(items[n_train + n_val : n_train + n_val + n_test])

    train.sort(key=lambda item: str(item.get("id", "")))
    val.sort(key=lambda item: str(item.get("id", "")))
    test.sort(key=lambda item: str(item.get("id", "")))

    train_path = FINAL_DIR / "train.jsonl"
    val_path = FINAL_DIR / "val.jsonl"
    test_path = FINAL_DIR / "test.jsonl"
    write_jsonl(train_path, train)
    write_jsonl(val_path, val)
    write_jsonl(test_path, test)

    print(f"Source: {FINAL_CORPUS}")
    print(f"Total rows: {len(rows)}")
    print(f"Train: {len(train)} -> {train_path}")
    print(f"Val:   {len(val)} -> {val_path}")
    print(f"Test:  {len(test)} -> {test_path}")
    print(f"Random seed: {RNG_SEED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

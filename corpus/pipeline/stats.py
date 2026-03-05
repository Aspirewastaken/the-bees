#!/usr/bin/env python3
"""Print statistics for corpus data files.

Usage:
    python stats.py corpus/data/raw/
    python stats.py corpus/data/verified/
    python stats.py corpus/data/final/
"""

import json
import sys
from collections import Counter
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    examples = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return examples


def print_stats(directory: Path):
    if not directory.exists():
        print(f"Directory not found: {directory}")
        return

    jsonl_files = sorted(directory.glob("*.jsonl"))
    if not jsonl_files:
        print(f"No JSONL files found in {directory}")
        return

    all_examples = []
    file_counts = {}
    for path in jsonl_files:
        examples = load_jsonl(path)
        file_counts[path.name] = len(examples)
        all_examples.extend(examples)

    label_counts = Counter(ex.get("label", "?") for ex in all_examples)
    category_counts = Counter(ex.get("category", "?") for ex in all_examples)
    model_counts = Counter(ex.get("model", "?") for ex in all_examples)

    text_lengths = [len(ex.get("text", "")) for ex in all_examples]
    avg_len = sum(text_lengths) / len(text_lengths) if text_lengths else 0
    min_len = min(text_lengths) if text_lengths else 0
    max_len = max(text_lengths) if text_lengths else 0

    print("=" * 60)
    print(f"CORPUS STATS: {directory}")
    print("=" * 60)

    print(f"\nTotal examples: {len(all_examples)}")
    print(f"Total files: {len(jsonl_files)}")

    print(f"\nLabel distribution:")
    for label, count in sorted(label_counts.items()):
        pct = count / len(all_examples) * 100
        bar = "#" * int(pct / 2)
        print(f"  {label:10s}: {count:6d} ({pct:5.1f}%) {bar}")

    print(f"\nCategory distribution:")
    for category, count in sorted(category_counts.items()):
        pct = count / len(all_examples) * 100
        print(f"  {category:25s}: {count:6d} ({pct:5.1f}%)")

    print(f"\nModel distribution:")
    for model, count in sorted(model_counts.items()):
        print(f"  {model}: {count}")

    print(f"\nText length stats:")
    print(f"  Min:  {min_len:,} chars")
    print(f"  Max:  {max_len:,} chars")
    print(f"  Mean: {avg_len:,.0f} chars")

    print(f"\nPer-file counts:")
    for name, count in sorted(file_counts.items()):
        print(f"  {name}: {count}")

    if any(ex.get("verification") for ex in all_examples):
        verified = [ex for ex in all_examples if ex.get("verification", {}).get("matches_expected")]
        flagged = [ex for ex in all_examples if ex.get("verification") and not ex["verification"].get("matches_expected")]
        print(f"\nVerification stats:")
        print(f"  Verified (both models agree): {len(verified)}")
        print(f"  Flagged (disagreement):       {len(flagged)}")
        if verified or flagged:
            rate = len(verified) / (len(verified) + len(flagged)) * 100
            print(f"  Agreement rate: {rate:.1f}%")

    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python stats.py <directory>")
        print("  e.g. python stats.py corpus/data/raw/")
        sys.exit(1)

    for dir_path in sys.argv[1:]:
        print_stats(Path(dir_path))


if __name__ == "__main__":
    main()

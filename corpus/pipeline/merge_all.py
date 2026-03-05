#!/usr/bin/env python3
"""Merge all verified examples into a single constitutional corpus file.

Usage:
    python merge_all.py [--input-dir DIR] [--output-dir DIR]

Reads all JSONL files from corpus/data/verified/, combines them into a single
corpus/data/final/constitutional_corpus_v1.jsonl, and prints statistics.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERIFIED_DIR = REPO_ROOT / "data" / "verified"
FINAL_DIR = REPO_ROOT / "data" / "final"


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


def main():
    parser = argparse.ArgumentParser(description="Merge verified examples into final corpus")
    parser.add_argument("--input-dir", type=str, default=None, help="Override verified directory")
    parser.add_argument("--output-dir", type=str, default=None, help="Override final directory")
    args = parser.parse_args()

    input_dir = Path(args.input_dir) if args.input_dir else VERIFIED_DIR
    output_dir = Path(args.output_dir) if args.output_dir else FINAL_DIR

    if not input_dir.exists():
        sys.exit(f"Input directory not found: {input_dir}")

    jsonl_files = sorted(input_dir.glob("*.jsonl"))
    if not jsonl_files:
        sys.exit(f"No JSONL files found in {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "constitutional_corpus_v1.jsonl"

    all_examples = []
    seen_ids = set()

    for path in jsonl_files:
        examples = load_jsonl(path)
        for ex in examples:
            ex_id = ex.get("id", "")
            if ex_id not in seen_ids:
                seen_ids.add(ex_id)
                all_examples.append(ex)

    all_examples.sort(key=lambda x: (x.get("label", ""), x.get("category", ""), x.get("id", "")))

    with open(output_path, "w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")

    label_counts = Counter(ex.get("label", "?") for ex in all_examples)
    category_counts = Counter(ex.get("category", "?") for ex in all_examples)

    print("=" * 60)
    print("CONSTITUTIONAL CORPUS MERGE COMPLETE")
    print("=" * 60)
    print(f"\nOutput: {output_path}")
    print(f"Total examples: {len(all_examples)}")
    print(f"Source files: {len(jsonl_files)}")
    print(f"\nLabel distribution:")
    for label, count in sorted(label_counts.items()):
        print(f"  {label}: {count}")
    print(f"\nCategory distribution:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}")
    print()


if __name__ == "__main__":
    main()

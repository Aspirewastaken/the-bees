#!/usr/bin/env python3
"""Export the final corpus into train/val/test splits.

Usage:
    python export.py [--input FILE] [--output-dir DIR] [--seed 42]

Reads the merged corpus and creates stratified 80/10/10 splits by category.
Outputs: train.jsonl, val.jsonl, test.jsonl
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
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


def write_jsonl(path: Path, examples: list[dict]):
    with open(path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")


def stratified_split(examples: list[dict], train_ratio=0.8, val_ratio=0.1, seed=42):
    """Split examples into train/val/test, stratified by (label, category)."""
    rng = random.Random(seed)

    by_stratum = defaultdict(list)
    for ex in examples:
        key = (ex.get("label", ""), ex.get("category", ""))
        by_stratum[key].append(ex)

    train, val, test = [], [], []

    for key in sorted(by_stratum.keys()):
        group = by_stratum[key]
        rng.shuffle(group)
        n = len(group)
        n_train = max(1, int(n * train_ratio))
        n_val = max(1, int(n * val_ratio))

        train.extend(group[:n_train])
        val.extend(group[n_train:n_train + n_val])
        test.extend(group[n_train + n_val:])

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)

    return train, val, test


def main():
    parser = argparse.ArgumentParser(description="Export corpus into train/val/test splits")
    parser.add_argument("--input", type=str, default=None, help="Input corpus file")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    input_path = Path(args.input) if args.input else FINAL_DIR / "constitutional_corpus_v1.jsonl"
    output_dir = Path(args.output_dir) if args.output_dir else FINAL_DIR

    if not input_path.exists():
        sys.exit(f"Input file not found: {input_path}")

    examples = load_jsonl(input_path)
    if not examples:
        sys.exit("No examples found in input file")

    train, val, test = stratified_split(examples, seed=args.seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "train.jsonl", train)
    write_jsonl(output_dir / "val.jsonl", val)
    write_jsonl(output_dir / "test.jsonl", test)

    print("=" * 60)
    print("CORPUS EXPORT COMPLETE")
    print("=" * 60)
    print(f"\nSeed: {args.seed}")
    print(f"Total: {len(examples)}")
    print(f"Train: {len(train)} ({len(train)/len(examples)*100:.1f}%)")
    print(f"Val:   {len(val)} ({len(val)/len(examples)*100:.1f}%)")
    print(f"Test:  {len(test)} ({len(test)/len(examples)*100:.1f}%)")
    print(f"\nOutput: {output_dir}")
    print(f"  train.jsonl: {len(train)} examples")
    print(f"  val.jsonl:   {len(val)} examples")
    print(f"  test.jsonl:  {len(test)} examples")


if __name__ == "__main__":
    main()

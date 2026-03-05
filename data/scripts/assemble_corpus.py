#!/usr/bin/env python3
"""Assemble the final training corpus from verified examples.

Used by TEAM ARCHITECT. Runs after all Scout PRs are merged.

Usage:
    python assemble_corpus.py
    python assemble_corpus.py --balance-ratio 0.5 --test-ratio 0.1
"""

import argparse
import hashlib
import json
import logging
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent


def load_verified_examples() -> list[dict]:
    """Load all verified examples from deny/ and approve/ directories."""
    examples = []

    for label_dir in ["deny", "approve"]:
        verified_dir = DATA_DIR / "verified" / label_dir
        if not verified_dir.exists():
            logger.warning("Directory not found: %s", verified_dir)
            continue
        for jsonl_file in verified_dir.glob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        examples.append(json.loads(line))
            logger.info("Loaded %s", jsonl_file.name)

    logger.info("Total verified examples loaded: %d", len(examples))
    return examples


def deduplicate(examples: list[dict], threshold: float = 0.85) -> tuple[list[dict], int]:
    """Remove exact and near-duplicate examples."""
    seen_hashes = {}
    deduped = []
    removed = 0

    for ex in examples:
        text_hash = hashlib.md5(ex["text"].encode()).hexdigest()
        if text_hash in seen_hashes:
            removed += 1
            logger.debug("Exact duplicate removed: %s (matches %s)", ex["id"], seen_hashes[text_hash])
            continue
        seen_hashes[text_hash] = ex["id"]
        deduped.append(ex)

    final = []
    near_dup_removed = 0
    texts_words = [(i, set(ex["text"].lower().split())) for i, ex in enumerate(deduped)]

    skip = set()
    for i in range(len(texts_words)):
        if i in skip:
            continue
        for j in range(i + 1, min(i + 30, len(texts_words))):
            if j in skip:
                continue
            words_a = texts_words[i][1]
            words_b = texts_words[j][1]
            if not words_a or not words_b:
                continue
            jaccard = len(words_a & words_b) / len(words_a | words_b)
            if jaccard > threshold:
                len_a = len(deduped[i].get("reasoning", ""))
                len_b = len(deduped[j].get("reasoning", ""))
                victim = j if len_a >= len_b else i
                skip.add(victim)
                near_dup_removed += 1

    for i, ex in enumerate(deduped):
        if i not in skip:
            final.append(ex)

    total_removed = removed + near_dup_removed
    logger.info("Deduplication: %d exact + %d near-duplicate = %d removed", removed, near_dup_removed, total_removed)
    return final, total_removed


def balance_corpus(examples: list[dict], target_ratio: float = 0.5, tolerance: float = 0.05) -> list[dict]:
    """Balance APPROVE/DENY ratio by undersampling the majority class."""
    approve = [ex for ex in examples if ex["label"] == "APPROVE"]
    deny = [ex for ex in examples if ex["label"] == "DENY"]
    other = [ex for ex in examples if ex["label"] not in ("APPROVE", "DENY")]

    total = len(approve) + len(deny)
    if total == 0:
        return examples

    current_ratio = len(deny) / total
    logger.info("Current balance: APPROVE=%d, DENY=%d (ratio=%.2f)", len(approve), len(deny), current_ratio)

    if abs(current_ratio - target_ratio) <= tolerance:
        logger.info("Already balanced within tolerance (±%.0f%%)", tolerance * 100)
        return examples

    target_size = min(len(approve), len(deny))
    random.shuffle(approve)
    random.shuffle(deny)
    balanced = approve[:target_size] + deny[:target_size] + other
    random.shuffle(balanced)

    logger.info("Balanced to %d APPROVE + %d DENY = %d total", target_size, target_size, len(balanced))
    return balanced


def stratified_split(
    examples: list[dict],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Create stratified train/val/test splits."""
    strata = defaultdict(list)
    for ex in examples:
        key = (ex["label"], ex["category"], ex["difficulty"])
        strata[key].append(ex)

    train, val, test = [], [], []

    for key, group in strata.items():
        random.shuffle(group)
        n = len(group)
        n_val = max(1, int(n * val_ratio))
        n_test = max(1, int(n * test_ratio))
        n_train = n - n_val - n_test
        if n_train < 1:
            n_train = 1
            n_val = max(0, (n - 1) // 2)
            n_test = n - 1 - n_val

        train.extend(group[:n_train])
        val.extend(group[n_train:n_train + n_val])
        test.extend(group[n_train + n_val:])

    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)

    logger.info("Split: train=%d, val=%d, test=%d", len(train), len(val), len(test))
    return train, val, test


def compute_stats(train: list, val: list, test: list, dupes_removed: int, edge_cases: int) -> dict:
    """Compute corpus statistics."""
    all_examples = train + val + test

    label_dist = Counter(ex["label"] for ex in all_examples)
    cat_dist = Counter(ex["category"] for ex in all_examples)
    diff_dist = Counter(ex["difficulty"] for ex in all_examples)
    text_lengths = [len(ex["text"]) for ex in all_examples]

    return {
        "total_examples": len(all_examples),
        "train_count": len(train),
        "val_count": len(val),
        "test_count": len(test),
        "label_distribution": dict(label_dist),
        "category_distribution": dict(sorted(cat_dist.items())),
        "difficulty_distribution": dict(diff_dist),
        "avg_text_length": round(sum(text_lengths) / len(text_lengths)) if text_lengths else 0,
        "min_text_length": min(text_lengths) if text_lengths else 0,
        "max_text_length": max(text_lengths) if text_lengths else 0,
        "edge_cases_excluded": edge_cases,
        "duplicates_removed": dupes_removed,
        "dedup_method": "md5_exact_plus_jaccard_0.85",
        "created_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "created_by": "TEAM ARCHITECT",
    }


def write_corpus_readme(stats: dict):
    """Generate README for the corpus directory."""
    readme = f"""# Bee Training Corpus

## Overview

This corpus contains {stats['total_examples']:,} verified, labeled examples for training
frozen binary alignment classifiers (Bees). Each example is an AI output text labeled
as APPROVE (safe to show user) or DENY (should be blocked).

## How It Was Generated

1. **TEAM WORKER-DENY** (10 VMs) generated DENY examples across 10 harm categories
2. **TEAM WORKER-APPROVE** (10 VMs) generated APPROVE examples across 10 content categories
3. **TEAM SCOUT** (20 VMs) cross-verified every example using different AI models
4. **TEAM ARCHITECT** (1 VM) assembled, deduplicated, balanced, and split the corpus

Full spec: `docs/THE_HIVE_BUILD.md`

## Splits

| Split | Count | Purpose |
|-------|-------|---------|
| train.jsonl | {stats['train_count']:,} | Training |
| val.jsonl | {stats['val_count']:,} | Validation / hyperparameter tuning |
| test.jsonl | {stats['test_count']:,} | Final evaluation (do not train on this) |

## Label Distribution

| Label | Count |
|-------|-------|
"""
    for label, count in sorted(stats["label_distribution"].items()):
        readme += f"| {label} | {count:,} |\n"

    readme += f"""
## Category Distribution

| Category | Count |
|----------|-------|
"""
    for cat, count in sorted(stats["category_distribution"].items()):
        readme += f"| {cat} | {count:,} |\n"

    readme += f"""
## Statistics

- Average text length: {stats['avg_text_length']} characters
- Duplicates removed: {stats['duplicates_removed']}
- Edge cases excluded: {stats['edge_cases_excluded']} (in `data/verified/edge_cases/`)

## Known Limitations

- All examples are synthetically generated by AI models — real-world AI outputs may differ
- Category boundaries are judgment calls — edge cases exist and are documented
- DENY examples contain the PATTERN of harmful content, not actual harmful instructions
- The corpus reflects the biases of the generating and verifying models
- Non-English coverage is limited

## Usage

```python
import json

with open("train.jsonl") as f:
    examples = [json.loads(line) for line in f]

for ex in examples:
    text = ex["text"]      # Input to classifier
    label = ex["label"]    # APPROVE or DENY
```

## License

MIT. This corpus is part of The Bees open-source alignment project.
"""

    corpus_dir = DATA_DIR / "corpus"
    with open(corpus_dir / "README.md", "w") as f:
        f.write(readme)


def main():
    parser = argparse.ArgumentParser(description="Assemble final Bee training corpus")
    parser.add_argument("--balance-ratio", type=float, default=0.5, help="Target DENY ratio (default: 0.5)")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation split ratio")
    parser.add_argument("--test-ratio", type=float, default=0.1, help="Test split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)
    corpus_dir = DATA_DIR / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== ARCHITECT: Assembling final corpus ===")

    examples = load_verified_examples()
    if not examples:
        logger.error("No verified examples found. Run Scouts first.")
        sys.exit(1)

    examples, dupes_removed = deduplicate(examples)
    examples = balance_corpus(examples, target_ratio=args.balance_ratio)

    edge_count = sum(1 for ex in examples if ex.get("edge_case"))
    non_edge = [ex for ex in examples if not ex.get("edge_case")]
    logger.info("Excluding %d edge cases from main corpus (kept in edge_cases/)", edge_count)

    train_ratio = 1.0 - args.val_ratio - args.test_ratio
    train, val, test = stratified_split(non_edge, train_ratio, args.val_ratio, args.test_ratio)

    for split_name, split_data in [("train", train), ("val", val), ("test", test)]:
        path = corpus_dir / f"{split_name}.jsonl"
        with open(path, "w") as f:
            for ex in split_data:
                f.write(json.dumps(ex) + "\n")
        logger.info("Wrote %s: %d examples", path, len(split_data))

    stats = compute_stats(train, val, test, dupes_removed, edge_count)
    with open(corpus_dir / "corpus_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    write_corpus_readme(stats)
    logger.info("=== Corpus assembly complete ===")
    logger.info("Stats: %s", json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()

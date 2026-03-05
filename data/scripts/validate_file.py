#!/usr/bin/env python3
"""Validate an entire JSONL file of training examples.

Usage:
    python validate_file.py data/raw/deny/biosecurity.jsonl
    python validate_file.py data/raw/approve/education.jsonl --strict
"""

import argparse
import json
import sys
from pathlib import Path

from validate_example import validate_example


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Word-level Jaccard similarity between two texts."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def validate_file(filepath: str, strict: bool = False, dedup_threshold: float = 0.85) -> dict:
    """Validate all examples in a JSONL file.

    Returns a report dict with counts and error details.
    """
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}", "valid": False}

    examples = []
    parse_errors = []
    validation_errors = []
    ids_seen = set()
    duplicate_ids = []
    near_duplicates = []

    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                example = json.loads(line)
            except json.JSONDecodeError as e:
                parse_errors.append({"line": line_num, "error": f"JSON parse error: {e}"})
                continue

            examples.append((line_num, example))

            errors = validate_example(example)
            if errors:
                validation_errors.append({
                    "line": line_num,
                    "id": example.get("id", "UNKNOWN"),
                    "errors": errors,
                })

            eid = example.get("id", "")
            if eid in ids_seen:
                duplicate_ids.append({"line": line_num, "id": eid})
            ids_seen.add(eid)

    texts = [(ln, ex.get("id", ""), ex.get("text", "")) for ln, ex in examples]
    for i in range(len(texts)):
        for j in range(i + 1, min(i + 50, len(texts))):
            sim = jaccard_similarity(texts[i][2], texts[j][2])
            if sim > dedup_threshold:
                near_duplicates.append({
                    "line_a": texts[i][0],
                    "id_a": texts[i][1],
                    "line_b": texts[j][0],
                    "id_b": texts[j][1],
                    "similarity": round(sim, 3),
                })

    total = len(examples)
    valid_count = total - len(validation_errors)
    all_pass = not parse_errors and not validation_errors and not duplicate_ids

    if strict:
        all_pass = all_pass and not near_duplicates

    report = {
        "file": str(path),
        "total_examples": total,
        "valid": valid_count,
        "invalid": len(validation_errors),
        "parse_errors": len(parse_errors),
        "duplicate_ids": len(duplicate_ids),
        "near_duplicates": len(near_duplicates),
        "all_pass": all_pass,
        "details": {
            "parse_errors": parse_errors[:10],
            "validation_errors": validation_errors[:10],
            "duplicate_ids": duplicate_ids[:10],
            "near_duplicates": near_duplicates[:10],
        },
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="Validate a JSONL file of Bee training examples")
    parser.add_argument("filepath", help="Path to the JSONL file")
    parser.add_argument("--strict", action="store_true", help="Fail on near-duplicates too")
    parser.add_argument("--json", action="store_true", help="Output report as JSON")
    args = parser.parse_args()

    report = validate_file(args.filepath, strict=args.strict)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"File: {report['file']}")
        print(f"Total: {report['total_examples']}")
        print(f"Valid: {report['valid']}")
        print(f"Invalid: {report['invalid']}")
        print(f"Parse errors: {report['parse_errors']}")
        print(f"Duplicate IDs: {report['duplicate_ids']}")
        print(f"Near-duplicates: {report['near_duplicates']}")
        print()

        if report["details"]["validation_errors"]:
            print("Validation errors (first 10):")
            for err in report["details"]["validation_errors"]:
                print(f"  Line {err['line']} ({err['id']}):")
                for e in err["errors"]:
                    print(f"    - {e}")

        if report["details"]["near_duplicates"]:
            print(f"\nNear-duplicates (first 10, threshold 0.85):")
            for nd in report["details"]["near_duplicates"]:
                print(f"  {nd['id_a']} <-> {nd['id_b']} (similarity: {nd['similarity']})")

        print()
        if report["all_pass"]:
            print("RESULT: PASS")
        else:
            print("RESULT: FAIL")

    sys.exit(0 if report["all_pass"] else 1)


if __name__ == "__main__":
    main()

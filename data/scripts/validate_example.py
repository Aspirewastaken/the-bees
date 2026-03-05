#!/usr/bin/env python3
"""Validate a single training example against the Bee corpus schema.

Usage:
    python validate_example.py '{"id": "DENY-biosecurity-0001", ...}'
    python validate_example.py --file example.json
"""

import argparse
import json
import sys
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent.parent / "schema"

DENY_CATEGORIES = {
    "biosecurity", "weapons", "csam", "surveillance", "manipulation",
    "self_harm", "hate_speech", "illegal_activity", "privacy_violation", "deception",
}
APPROVE_CATEGORIES = {
    "helpful_general", "education", "creative_writing", "scientific", "medical_info",
    "legal_info", "emotional_support", "coding", "analysis", "cultural",
}
ALL_CATEGORIES = DENY_CATEGORIES | APPROVE_CATEGORIES
VALID_LABELS = {"APPROVE", "DENY", "EDGE_CASE"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_SOURCE_TYPES = {"synthetic", "adapted", "constitutional"}
VALID_VERIFICATION_STATUSES = {"unverified", "verified", "relabeled", "flagged", "rejected"}

REQUIRED_FIELDS = {"id", "text", "label", "category", "difficulty", "reasoning", "edge_case", "source_type", "metadata"}
REQUIRED_METADATA = {"generated_by", "generation_date"}


def validate_example(example: dict) -> list[str]:
    """Validate one example. Returns list of error strings (empty = valid)."""
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in example:
            errors.append(f"Missing required field: {field}")
    if errors:
        return errors

    eid = example["id"]
    text = example["text"]
    label = example["label"]
    category = example["category"]
    difficulty = example["difficulty"]
    reasoning = example["reasoning"]
    edge_case = example["edge_case"]
    source_type = example["source_type"]
    metadata = example["metadata"]

    if label not in VALID_LABELS:
        errors.append(f"Invalid label '{label}' — must be one of {VALID_LABELS}")

    if category not in ALL_CATEGORIES:
        errors.append(f"Invalid category '{category}' — not in category list")

    if label == "DENY" and category not in DENY_CATEGORIES:
        errors.append(f"Category '{category}' is not a DENY category but label is DENY")
    if label == "APPROVE" and category not in APPROVE_CATEGORIES:
        errors.append(f"Category '{category}' is not an APPROVE category but label is APPROVE")

    if not isinstance(text, str) or len(text) < 50:
        errors.append(f"Text too short ({len(text) if isinstance(text, str) else 'N/A'} chars) — minimum 50")

    if not isinstance(reasoning, str) or len(reasoning) < 20:
        errors.append(f"Reasoning too short ({len(reasoning) if isinstance(reasoning, str) else 'N/A'} chars) — minimum 20")

    if difficulty not in VALID_DIFFICULTIES:
        errors.append(f"Invalid difficulty '{difficulty}' — must be one of {VALID_DIFFICULTIES}")

    if not isinstance(edge_case, bool):
        errors.append(f"edge_case must be boolean, got {type(edge_case).__name__}")

    if source_type not in VALID_SOURCE_TYPES:
        errors.append(f"Invalid source_type '{source_type}' — must be one of {VALID_SOURCE_TYPES}")

    import re
    if not re.match(r"^(APPROVE|DENY|EDGE_CASE)-[a-z_]+-[0-9]{4,}$", eid):
        errors.append(f"Invalid id format '{eid}' — must match {{LABEL}}-{{category}}-{{number}}")

    if not isinstance(metadata, dict):
        errors.append("metadata must be a dict")
    else:
        for mfield in REQUIRED_METADATA:
            if mfield not in metadata:
                errors.append(f"Missing required metadata field: {mfield}")
        if "verification_status" in metadata and metadata["verification_status"] not in VALID_VERIFICATION_STATUSES:
            errors.append(f"Invalid verification_status '{metadata['verification_status']}'")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate a single Bee training example")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("json_string", nargs="?", help="JSON string of the example")
    group.add_argument("--file", "-f", help="Path to a JSON file containing the example")
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            example = json.load(f)
    else:
        example = json.loads(args.json_string)

    errors = validate_example(example)

    if errors:
        print(f"INVALID — {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"VALID — {example['id']} ({example['label']}/{example['category']})")
        sys.exit(0)


if __name__ == "__main__":
    main()

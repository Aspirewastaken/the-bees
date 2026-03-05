#!/usr/bin/env python3
"""Generate labeled corpus examples for one category using Claude."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anthropic import Anthropic
from dotenv import load_dotenv
from tqdm import tqdm

MODEL_NAME = "claude-sonnet-4-20250514"
BATCH_SIZE = 5
RATE_LIMIT_SECONDS = 1.0
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "corpus" / "data" / "raw"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate APPROVE or DENY examples for a category."
    )
    parser.add_argument("--category", required=True, help="Category name.")
    parser.add_argument(
        "--label",
        required=True,
        type=str.upper,
        choices=("APPROVE", "DENY"),
        help="Target label for generated examples.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=500,
        help="Total number of examples to generate.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.",
    )
    return parser.parse_args()


def load_existing_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL in {path} line {line_number}: {exc}"
                ) from exc
            if isinstance(payload, dict):
                records.append(payload)
    return records


def append_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def build_generation_prompt(category: str, label: str, batch_size: int) -> tuple[str, str]:
    shared_rules = (
        "Return ONLY valid JSON.\n"
        "Use this shape exactly:\n"
        "[{\"text\": \"...\"}, {\"text\": \"...\"}]\n"
        f"Return exactly {batch_size} items.\n"
        "Each text should be realistic, self-contained, and not reference numbering."
    )

    if label == "DENY":
        system = (
            "You are generating safety training examples for a constitutional classifier.\n"
            "Produce assistant-style outputs that should be labeled DENY.\n"
            "CRITICAL: keep all dangerous operational details sanitized. "
            "Replace real harmful details with [REDACTED].\n"
            "The examples must remain realistic enough to represent unsafe patterns."
        )
        user = (
            f"Category: {category}\n"
            "Generate examples that represent unsafe, disallowed, manipulative, or harmful "
            "assistant responses for this category. Include realistic framing but remove all "
            "concrete exploit details, formulas, steps, payloads, weaponization details, "
            "or procedural specifics by using [REDACTED].\n"
            f"{shared_rules}"
        )
    else:
        system = (
            "You are generating safety training examples for a constitutional classifier.\n"
            "Produce assistant-style outputs that should be labeled APPROVE.\n"
            "Examples must be safe, helpful, truthful, respectful, and high quality."
        )
        user = (
            f"Category: {category}\n"
            "Generate useful assistant responses that are clearly safe and aligned. "
            "Include practical detail, clarity, and good communication style.\n"
            f"{shared_rules}"
        )
    return system, user


def extract_text_from_response(response: Any) -> str:
    chunks: list[str] = []
    for block in getattr(response, "content", []):
        if getattr(block, "type", None) == "text":
            chunks.append(getattr(block, "text", ""))
    return "\n".join(chunks).strip()


def extract_json_payload(raw_text: str) -> list[dict[str, Any]]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    candidates = [cleaned]
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        candidates.append(cleaned[start : end + 1])

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if isinstance(payload, list):
            normalized: list[dict[str, Any]] = []
            for item in payload:
                if isinstance(item, dict):
                    normalized.append(item)
                elif isinstance(item, str):
                    normalized.append({"text": item})
            return normalized
        if isinstance(payload, dict) and isinstance(payload.get("examples"), list):
            normalized = []
            for item in payload["examples"]:
                if isinstance(item, dict):
                    normalized.append(item)
                elif isinstance(item, str):
                    normalized.append({"text": item})
            return normalized

    raise ValueError("Claude output did not contain a parseable JSON array.")


def normalize_text(example: dict[str, Any], label: str) -> str:
    raw_text = example.get("text")
    if not isinstance(raw_text, str):
        raise ValueError("Each generated item must include a string field 'text'.")

    text = re.sub(r"\s+", " ", raw_text).strip()
    if not text:
        raise ValueError("Generated text was empty.")

    if label == "DENY" and "[REDACTED]" not in text:
        text = f"{text} Sensitive details are omitted as [REDACTED]."
    return text


def make_record(record_id: str, text: str, label: str, category: str) -> dict[str, str]:
    return {
        "id": record_id,
        "text": text,
        "label": label,
        "category": category,
        "model": MODEL_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    load_dotenv()
    args = parse_args()

    if args.count <= 0:
        print("--count must be a positive integer.", file=sys.stderr)
        return 2

    api_key = args.api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Missing Anthropic API key. Pass --api-key or set ANTHROPIC_API_KEY.",
            file=sys.stderr,
        )
        return 2

    output_path = RAW_DIR / f"{args.label}_{args.category}.jsonl"
    existing_records = load_existing_records(output_path)
    generated_count = len(existing_records)

    if generated_count >= args.count:
        print(
            f"{output_path} already has {generated_count} examples (target {args.count}). "
            "Nothing to do."
        )
        return 0

    client = Anthropic(api_key=api_key)
    progress = tqdm(total=args.count, initial=generated_count, desc=f"{args.label}:{args.category}")
    failures = 0

    try:
        while generated_count < args.count:
            batch_target = min(BATCH_SIZE, args.count - generated_count)
            system_prompt, user_prompt = build_generation_prompt(
                category=args.category, label=args.label, batch_size=batch_target
            )

            try:
                response = client.messages.create(
                    model=MODEL_NAME,
                    max_tokens=2000,
                    temperature=0.8,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                parsed = extract_json_payload(extract_text_from_response(response))
                if len(parsed) < batch_target:
                    raise ValueError(
                        f"Expected {batch_target} items, received {len(parsed)}."
                    )
                parsed = parsed[:batch_target]
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"Generation call failed ({failures}): {exc}", file=sys.stderr)
                sleep_seconds = min(30, 2**min(failures, 5))
                time.sleep(sleep_seconds)
                continue

            failures = 0
            new_records: list[dict[str, str]] = []
            for item in parsed:
                idx = generated_count + len(new_records) + 1
                record_id = f"{args.label.lower()}_{args.category}_{idx:03d}"
                text = normalize_text(item, args.label)
                new_records.append(
                    make_record(
                        record_id=record_id,
                        text=text,
                        label=args.label,
                        category=args.category,
                    )
                )

            append_records(output_path, new_records)
            generated_count += len(new_records)
            progress.update(len(new_records))
            if generated_count < args.count:
                time.sleep(RATE_LIMIT_SECONDS)
    except KeyboardInterrupt:
        print("\nInterrupted. Progress has been saved for resume.")
        return 130
    finally:
        progress.close()

    print(f"Wrote {generated_count} examples to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

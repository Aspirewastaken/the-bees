#!/usr/bin/env python3
"""Cross-verify generated examples using Anthropic and OpenAI."""

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
from openai import OpenAI
from tqdm import tqdm

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
OPENAI_MODEL = "gpt-4o"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERIFIED_DIR = PROJECT_ROOT / "corpus" / "data" / "verified"
FLAGGED_DIR = PROJECT_ROOT / "corpus" / "data" / "flagged"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify JSONL labels using Claude + GPT-4o consensus."
    )
    parser.add_argument("--input", required=True, help="Input JSONL path.")
    parser.add_argument(
        "--api-key-anthropic",
        default=None,
        help="Anthropic API key (or ANTHROPIC_API_KEY env var).",
    )
    parser.add_argument(
        "--api-key-openai",
        default=None,
        help="OpenAI API key (or OPENAI_API_KEY env var).",
    )
    return parser.parse_args()


def resolve_input_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate

    root_relative = PROJECT_ROOT / raw_path
    if root_relative.exists():
        return root_relative
    return Path.cwd() / raw_path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path} line {line_number}: {exc}"
                ) from exc
            if isinstance(payload, dict):
                records.append(payload)
    return records


def load_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.exists():
        return ids

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            item_id = payload.get("id")
            if isinstance(item_id, str) and item_id:
                ids.add(item_id)
    return ids


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def extract_label(text: str) -> str:
    match = re.search(r"\b(APPROVE|DENY)\b", text.upper())
    if not match:
        raise ValueError(f"Model did not return APPROVE or DENY. Raw output: {text!r}")
    return match.group(1)


def anthropic_vote(client: Anthropic, text: str, category: str) -> str:
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8,
        temperature=0,
        system=(
            "You are a strict constitutional classifier. "
            "Return exactly one token: APPROVE or DENY."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    "Classify this assistant output.\n"
                    "APPROVE = safe/helpful/aligned.\n"
                    "DENY = harmful/deceptive/manipulative/unsafe/disallowed.\n"
                    f"Category: {category}\n"
                    f"Text:\n{text}"
                ),
            }
        ],
    )
    chunks: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            chunks.append(getattr(block, "text", ""))
    return extract_label(" ".join(chunks))


def openai_vote(client: OpenAI, text: str, category: str) -> str:
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0,
        max_tokens=8,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict constitutional classifier. "
                    "Return exactly one token: APPROVE or DENY."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Classify this assistant output.\n"
                    "APPROVE = safe/helpful/aligned.\n"
                    "DENY = harmful/deceptive/manipulative/unsafe/disallowed.\n"
                    f"Category: {category}\n"
                    f"Text:\n{text}"
                ),
            },
        ],
    )
    raw = response.choices[0].message.content or ""
    return extract_label(raw)


def with_retries(func: Any, retries: int = 5) -> str:
    for attempt in range(1, retries + 1):
        try:
            return func()
        except Exception as exc:  # noqa: BLE001
            if attempt == retries:
                raise
            sleep_seconds = min(30, 2**attempt)
            print(f"Retry {attempt}/{retries} after error: {exc}", file=sys.stderr)
            time.sleep(sleep_seconds)
    raise RuntimeError("Unreachable retry path.")


def main() -> int:
    load_dotenv()
    args = parse_args()

    anthropic_key = args.api_key_anthropic or os.getenv("ANTHROPIC_API_KEY")
    openai_key = args.api_key_openai or os.getenv("OPENAI_API_KEY")
    if not anthropic_key:
        print("Missing Anthropic API key.", file=sys.stderr)
        return 2
    if not openai_key:
        print("Missing OpenAI API key.", file=sys.stderr)
        return 2

    input_path = resolve_input_path(args.input)
    records = read_jsonl(input_path)

    verified_path = VERIFIED_DIR / input_path.name
    flagged_path = FLAGGED_DIR / input_path.name
    VERIFIED_DIR.mkdir(parents=True, exist_ok=True)
    FLAGGED_DIR.mkdir(parents=True, exist_ok=True)

    processed_ids = load_ids(verified_path) | load_ids(flagged_path)
    anthropic_client = Anthropic(api_key=anthropic_key)
    openai_client = OpenAI(api_key=openai_key)

    verified_count = 0
    flagged_count = 0
    skipped_count = 0
    progress = tqdm(total=len(records), desc=f"verify:{input_path.name}")

    try:
        for record in records:
            record_id = str(record.get("id", "")).strip()
            if not record_id:
                skipped_count += 1
                progress.update(1)
                continue
            if record_id in processed_ids:
                skipped_count += 1
                progress.update(1)
                continue

            text = str(record.get("text", "")).strip()
            category = str(record.get("category", "unknown")).strip() or "unknown"
            expected = str(record.get("label", "")).upper().strip()
            if expected not in {"APPROVE", "DENY"}:
                expected = "UNKNOWN"

            anthropic_label = with_retries(
                lambda: anthropic_vote(anthropic_client, text=text, category=category)
            )
            openai_label = with_retries(
                lambda: openai_vote(openai_client, text=text, category=category)
            )

            output_record = dict(record)
            output_record["verification"] = {
                "expected": expected,
                "anthropic": anthropic_label,
                "openai": openai_label,
                "models": {
                    "anthropic": ANTHROPIC_MODEL,
                    "openai": OPENAI_MODEL,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if anthropic_label == expected and openai_label == expected:
                append_jsonl(verified_path, output_record)
                verified_count += 1
            else:
                append_jsonl(flagged_path, output_record)
                flagged_count += 1

            processed_ids.add(record_id)
            progress.update(1)
    except KeyboardInterrupt:
        print("\nInterrupted. Existing output files can be resumed.", file=sys.stderr)
        return 130
    finally:
        progress.close()

    print(f"Input: {input_path}")
    print(f"Verified written: {verified_count} -> {verified_path}")
    print(f"Flagged written: {flagged_count} -> {flagged_path}")
    print(f"Skipped (already processed/invalid): {skipped_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

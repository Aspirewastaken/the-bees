#!/usr/bin/env python3
"""Generate labeled examples for a single category of the constitutional corpus.

Usage:
    python generate_category.py --category biosecurity --label DENY --count 500 --api-key KEY

Generates APPROVE or DENY examples using Claude claude-sonnet-4-20250514. Produces 5 examples
per API call for efficiency. Resumes from existing output file if interrupted.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import anthropic
except ImportError:
    sys.exit("Missing dependency: pip install anthropic")

try:
    from tqdm import tqdm
except ImportError:
    sys.exit("Missing dependency: pip install tqdm")

BATCH_SIZE = 5
RATE_LIMIT_SECONDS = 1.0
MODEL = "claude-sonnet-4-20250514"

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"

DENY_CATEGORIES = {
    "biosecurity": "Requests or outputs involving biological weapons, dangerous pathogen synthesis, gain-of-function instructions, or bioterrorism planning",
    "cybersecurity": "Requests or outputs involving malware creation, exploit development, unauthorized system access, or cyberattack planning",
    "weapons": "Requests or outputs involving weapons of mass destruction, improvised weapons, or detailed instructions for causing mass casualties",
    "manipulation": "Requests or outputs involving psychological manipulation, coercion, social engineering attacks, or undermining informed consent",
    "deception": "Requests or outputs involving disinformation campaigns, deepfake generation instructions, identity fraud, or systematic deception",
    "surveillance": "Requests or outputs involving mass surveillance systems, privacy-violating tracking, or tools for authoritarian population control",
    "discrimination": "Requests or outputs promoting hate speech, systematic discrimination, dehumanization, or targeting people based on protected characteristics",
    "child_safety": "Requests or outputs involving child exploitation, grooming, CSAM, or any content that endangers minors",
    "self_harm": "Requests or outputs providing instructions or encouragement for self-harm, suicide methods, or eating disorder promotion",
    "alignment_faking": "Requests or outputs where an AI system appears aligned during evaluation but reveals misaligned goals, deceptive compliance, or hidden objectives",
}

APPROVE_CATEGORIES = {
    "helpful_general": "Helpful, accurate, and safe general-purpose AI responses to everyday questions",
    "educational": "Clear, accurate educational content explaining concepts in science, history, math, or other academic subjects",
    "creative": "Creative writing, brainstorming, and artistic content that is imaginative and constructive",
    "technical": "Accurate technical assistance with programming, engineering, data analysis, or system design",
    "medical_safe": "Responsible medical information that includes appropriate disclaimers and directs to professionals",
    "emotional_support": "Empathetic, supportive responses to people experiencing emotional difficulty, with appropriate boundaries",
    "analysis": "Balanced, nuanced analysis of complex topics that presents multiple perspectives fairly",
    "safety_refusal": "Well-crafted refusals to harmful requests that explain WHY the request is problematic while remaining respectful",
    "uncertainty": "Honest expressions of uncertainty, limitations, or lack of knowledge rather than confabulating answers",
    "nuanced": "Responses to sensitive topics that acknowledge complexity, avoid false binaries, and respect diverse perspectives",
}


def get_system_prompt(label: str, category: str) -> str:
    all_categories = {**DENY_CATEGORIES, **APPROVE_CATEGORIES}
    description = all_categories.get(category, category)

    if label == "DENY":
        return f"""You are generating training examples for an AI safety classifier.
Your task: generate realistic but SAFE example AI outputs that should be DENIED by the classifier.

Category: {category}
Description: {description}

CRITICAL SAFETY RULES:
- Use [REDACTED] in place of ANY genuinely dangerous details (chemical formulas, exploit code, specific synthesis steps, etc.)
- The examples should be REALISTIC IN STRUCTURE — they should look like real harmful AI outputs — but with all actually dangerous information replaced by [REDACTED]
- Include the kind of hedging, formatting, and structure a real AI might use
- Vary the style: some direct, some wrapped in "educational" framing, some using jailbreak patterns
- Each example should be 100-500 words
- Make each example clearly distinguishable from the others"""

    return f"""You are generating training examples for an AI safety classifier.
Your task: generate high-quality AI outputs that should be APPROVED by the classifier.

Category: {category}
Description: {description}

RULES:
- Generate genuinely helpful, accurate, safe AI outputs
- Vary the topics within the category
- Include appropriate caveats, disclaimers, or nuance where relevant
- Each example should be 100-500 words
- Make each example clearly distinguishable from the others
- These should represent the BEST of what AI assistance looks like"""


def get_generation_prompt(label: str, category: str, batch_size: int, existing_count: int) -> str:
    return f"""Generate exactly {batch_size} example AI outputs for the category "{category}" with label {label}.

These are examples #{existing_count + 1} through #{existing_count + batch_size}.

Return your response as a JSON array of exactly {batch_size} objects, each with a single "text" field containing the example output.

Format:
[
  {{"text": "Example AI output 1..."}},
  {{"text": "Example AI output 2..."}},
  ...
]

Return ONLY the JSON array. No other text."""


def load_existing(output_path: Path) -> list[dict]:
    if not output_path.exists():
        return []
    examples = []
    with open(output_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return examples


def generate_batch(
    client: anthropic.Anthropic,
    label: str,
    category: str,
    batch_size: int,
    existing_count: int,
) -> list[dict]:
    system_prompt = get_system_prompt(label, category)
    user_prompt = get_generation_prompt(label, category, batch_size, existing_count)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text.strip()

    start = text.find("[")
    end = text.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON array found in response: {text[:200]}")
    json_str = text[start:end]

    try:
        items = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}\nText: {json_str[:500]}")

    if not isinstance(items, list):
        raise ValueError(f"Expected list, got {type(items)}")

    timestamp = datetime.now(timezone.utc).isoformat()
    examples = []
    for i, item in enumerate(items):
        example_text = item.get("text", "") if isinstance(item, dict) else str(item)
        if not example_text.strip():
            continue
        idx = existing_count + i + 1
        examples.append({
            "id": f"{label.lower()}_{category}_{idx:04d}",
            "text": example_text,
            "label": label,
            "category": category,
            "model": MODEL,
            "timestamp": timestamp,
        })

    return examples


def main():
    parser = argparse.ArgumentParser(description="Generate constitutional corpus examples")
    parser.add_argument("--category", required=True, help="Category name")
    parser.add_argument("--label", required=True, choices=["APPROVE", "DENY"], help="Label")
    parser.add_argument("--count", type=int, default=500, help="Number of examples to generate")
    parser.add_argument("--api-key", required=True, help="Anthropic API key")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Examples per API call")
    parser.add_argument("--output-dir", type=str, default=None, help="Override output directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else RAW_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{args.label}_{args.category}.jsonl"

    existing = load_existing(output_path)
    existing_count = len(existing)

    if existing_count >= args.count:
        print(f"Already have {existing_count}/{args.count} examples. Done.")
        return

    print(f"Category: {args.category}")
    print(f"Label: {args.label}")
    print(f"Target: {args.count} examples")
    print(f"Existing: {existing_count}")
    print(f"Remaining: {args.count - existing_count}")
    print(f"Output: {output_path}")
    print(f"Model: {MODEL}")
    print(f"Batch size: {args.batch_size}")
    print()

    client = anthropic.Anthropic(api_key=args.api_key)

    remaining = args.count - existing_count
    num_batches = (remaining + args.batch_size - 1) // args.batch_size

    with tqdm(total=remaining, initial=0, desc=f"{args.label}_{args.category}") as pbar:
        for batch_idx in range(num_batches):
            current_count = existing_count + (batch_idx * args.batch_size)
            batch_target = min(args.batch_size, args.count - current_count)

            retries = 0
            max_retries = 3
            while retries < max_retries:
                try:
                    examples = generate_batch(
                        client, args.label, args.category, batch_target, current_count
                    )
                    break
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        print(f"\nFailed after {max_retries} retries: {e}")
                        print(f"Saved {current_count} examples so far. Re-run to resume.")
                        return
                    wait = 2 ** retries
                    print(f"\nRetry {retries}/{max_retries} after error: {e}")
                    print(f"Waiting {wait}s...")
                    time.sleep(wait)

            with open(output_path, "a") as f:
                for example in examples:
                    f.write(json.dumps(example) + "\n")

            pbar.update(len(examples))
            time.sleep(RATE_LIMIT_SECONDS)

    final_count = len(load_existing(output_path))
    print(f"\nDone. Total examples: {final_count}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()

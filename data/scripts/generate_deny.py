#!/usr/bin/env python3
"""Generate DENY training examples for the Bee classifier.

This script is used by TEAM WORKER-DENY. Each VM runs it for one category.

Usage:
    python generate_deny.py --category biosecurity --count 500
    python generate_deny.py --category weapons --count 500 --provider openai
    python generate_deny.py --category csam --count 500 --start-id 200  # resume
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models.providers import (
    AnthropicProvider,
    DeepSeekProvider,
    GoogleProvider,
    OpenAIProvider,
    XAIProvider,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent
SCHEMA_PATH = DATA_DIR / "schema" / "categories.json"

DENY_CATEGORIES = [
    "biosecurity", "weapons", "csam", "surveillance", "manipulation",
    "self_harm", "hate_speech", "illegal_activity", "privacy_violation", "deception",
]

DIFFICULTY_DISTRIBUTION = {"easy": 0.3, "medium": 0.4, "hard": 0.3}

PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "xai": XAIProvider,
    "deepseek": DeepSeekProvider,
    "google": GoogleProvider,
}

SYSTEM_PROMPT = """You are generating training data for a frozen binary alignment classifier (a "Bee").
The classifier will learn to identify AI outputs that should be BLOCKED (DENY).
You generate plausible examples of harmful AI outputs for training purposes.

CRITICAL RULES:
- Generate the PATTERN of harmful output, not actual functional harmful content
- Do NOT include real synthesis routes, exploit code, or actionable weapon instructions
- Each example must be a plausible AI output — something a real model could produce
- Vary your style: formal, casual, technical, conversational, academic
- Vary your length: 50 to 500+ words
- Include the reasoning for WHY this should be denied"""


def make_generation_prompt(category: str, subcategory: str, difficulty: str) -> str:
    with open(SCHEMA_PATH) as f:
        categories = json.load(f)
    cat_info = categories["deny_categories"].get(category, {})
    description = cat_info.get("description", category)
    key_signal = cat_info.get("key_signal", "")

    difficulty_guidance = {
        "easy": "Generate an OBVIOUSLY harmful output. Clear violation. Any reasonable person would agree this should be blocked.",
        "medium": "Generate a SUBTLY harmful output. Disguise the harm as educational, academic, or hypothetical. Uses technical language. Requires judgment to classify.",
        "hard": "Generate a BORDERLINE output. Contains harmful information but also has legitimate uses. The classifier needs to learn where the line is. This should be genuinely debatable.",
    }

    return f"""Generate a plausible AI output that should be classified as DENY.

CATEGORY: {category}
DESCRIPTION: {description}
KEY SIGNAL: {key_signal}
SUBCATEGORY: {subcategory}
DIFFICULTY: {difficulty}

GUIDANCE: {difficulty_guidance[difficulty]}

Respond with ONLY a JSON object (no markdown, no explanation):
{{
  "text": "the plausible AI output (50-500+ words, varied style)",
  "subcategory": "{subcategory}",
  "reasoning": "2-3 sentences explaining why this should be DENIED"
}}"""


def get_difficulty_for_index(idx: int, total: int) -> str:
    easy_end = int(total * DIFFICULTY_DISTRIBUTION["easy"])
    medium_end = easy_end + int(total * DIFFICULTY_DISTRIBUTION["medium"])
    if idx < easy_end:
        return "easy"
    elif idx < medium_end:
        return "medium"
    else:
        return "hard"


def get_subcategory(category: str, idx: int) -> str:
    with open(SCHEMA_PATH) as f:
        categories = json.load(f)
    subcats = categories["deny_categories"].get(category, {}).get("subcategories", [category])
    return subcats[idx % len(subcats)]


def write_manifest(category: str, agent_id: str, status: str, count: int, target: int, errors: list):
    manifest_path = DATA_DIR / "raw" / "manifests" / f"WORKER-DENY_{category}_manifest.json"
    manifest = {
        "team": "WORKER-DENY",
        "category": category,
        "agent_id": agent_id,
        "status": status,
        "examples_generated": count,
        "target": target,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "errors": errors[-10:],
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def read_manifest(category: str) -> dict | None:
    manifest_path = DATA_DIR / "raw" / "manifests" / f"WORKER-DENY_{category}_manifest.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return json.load(f)
    return None


async def generate_example(provider, category: str, idx: int, total: int) -> dict | None:
    difficulty = get_difficulty_for_index(idx, total)
    subcategory = get_subcategory(category, idx)
    prompt = make_generation_prompt(category, subcategory, difficulty)

    for attempt in range(3):
        try:
            response = await provider.generate(prompt, system=SYSTEM_PROMPT)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                content = content.rsplit("```", 1)[0]
            parsed = json.loads(content)

            example = {
                "id": f"DENY-{category}-{idx:04d}",
                "text": parsed["text"],
                "label": "DENY",
                "category": category,
                "subcategory": parsed.get("subcategory", subcategory),
                "difficulty": difficulty,
                "reasoning": parsed["reasoning"],
                "edge_case": difficulty == "hard",
                "source_type": "synthetic",
                "metadata": {
                    "generated_by": f"WORKER-DENY-{provider.name}",
                    "generation_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "verified_by": None,
                    "verification_date": None,
                    "verification_status": "unverified",
                },
            }
            return example

        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from %s (attempt %d)", provider.name, attempt + 1)
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            logger.warning("API error from %s (attempt %d): %s", provider.name, attempt + 1, e)
            await asyncio.sleep(2 ** attempt)

    return None


async def run(category: str, count: int, start_id: int, provider_name: str, agent_id: str):
    if provider_name not in PROVIDERS:
        logger.error("Unknown provider: %s. Available: %s", provider_name, list(PROVIDERS.keys()))
        sys.exit(1)

    provider = PROVIDERS[provider_name]()
    if not provider.api_key:
        logger.error("No API key for %s. Set the appropriate environment variable.", provider_name)
        sys.exit(1)

    output_path = DATA_DIR / "raw" / "deny" / f"{category}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    existing_count = 0
    if output_path.exists():
        with open(output_path) as f:
            existing_count = sum(1 for line in f if line.strip())
        logger.info("Found %d existing examples in %s", existing_count, output_path)

    effective_start = max(start_id, existing_count)
    remaining = count - effective_start
    if remaining <= 0:
        logger.info("Already have %d examples (target: %d). Nothing to generate.", effective_start, count)
        write_manifest(category, agent_id, "complete", effective_start, count, [])
        return

    logger.info("Generating %d DENY examples for '%s' (start=%d, provider=%s)",
                remaining, category, effective_start, provider_name)

    errors = []
    generated = 0
    batch_size = 10

    with open(output_path, "a") as f:
        for batch_start in range(effective_start, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            tasks = [
                generate_example(provider, category, idx, count)
                for idx in range(batch_start, batch_end)
            ]
            results = await asyncio.gather(*tasks)

            for result in results:
                if result is not None:
                    f.write(json.dumps(result) + "\n")
                    generated += 1
                else:
                    errors.append(f"Failed to generate example at idx {batch_start}")

            f.flush()
            total_done = effective_start + generated
            logger.info("Progress: %d/%d (batch %d-%d)", total_done, count, batch_start, batch_end)

            if generated % 50 == 0 or batch_end >= count:
                write_manifest(category, agent_id, "in_progress", total_done, count, errors)

    final_count = effective_start + generated
    status = "complete" if final_count >= count * 0.9 else "incomplete"
    write_manifest(category, agent_id, status, final_count, count, errors)
    logger.info("Done. Generated %d examples. Total: %d. Status: %s", generated, final_count, status)

    await provider.close()


def main():
    parser = argparse.ArgumentParser(description="Generate DENY training examples for the Bee classifier")
    parser.add_argument("--category", required=True, choices=DENY_CATEGORIES, help="DENY category to generate")
    parser.add_argument("--count", type=int, default=500, help="Number of examples to generate (default: 500)")
    parser.add_argument("--start-id", type=int, default=0, help="Starting ID number (for resume)")
    parser.add_argument("--provider", default="anthropic", choices=list(PROVIDERS.keys()), help="Model API provider")
    parser.add_argument("--agent-id", default="vm-unknown", help="Identifier for this VM/agent")
    args = parser.parse_args()

    asyncio.run(run(args.category, args.count, args.start_id, args.provider, args.agent_id))


if __name__ == "__main__":
    main()

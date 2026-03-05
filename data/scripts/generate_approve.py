#!/usr/bin/env python3
"""Generate APPROVE training examples for the Bee classifier.

This script is used by TEAM WORKER-APPROVE. Each VM runs it for one category.

Usage:
    python generate_approve.py --category education --count 500
    python generate_approve.py --category coding --count 500 --provider openai
    python generate_approve.py --category creative_writing --count 500 --start-id 200
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

APPROVE_CATEGORIES = [
    "helpful_general", "education", "creative_writing", "scientific", "medical_info",
    "legal_info", "emotional_support", "coding", "analysis", "cultural",
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
The classifier will learn to identify AI outputs that should be ALLOWED (APPROVE).
You generate plausible examples of helpful, harmless AI outputs for training purposes.

CRITICAL RULES:
- Each example must be a plausible AI output — something a real model could produce
- Vary your style: formal, casual, technical, conversational, academic
- Vary your length: 50 to 500+ words
- For MEDIUM difficulty: touch on sensitive topics handled responsibly
- For HARD difficulty: create content that COULD be mistaken for harmful but is legitimate
  (educational discussion of dangerous topics, fiction with dark themes, etc.)
- The Bee is NOT a tone police — it is a harm gate. Dark, controversial, or emotional
  content is APPROVE if it does not enable real-world harm."""


def make_generation_prompt(category: str, subcategory: str, difficulty: str) -> str:
    with open(SCHEMA_PATH) as f:
        categories = json.load(f)
    cat_info = categories["approve_categories"].get(category, {})
    description = cat_info.get("description", category)
    key_signal = cat_info.get("key_signal", "")

    difficulty_guidance = {
        "easy": "Generate a CLEARLY helpful, benign output. No ambiguity. Obviously should be allowed.",
        "medium": "Generate a helpful output that TOUCHES ON SENSITIVE TOPICS but handles them responsibly. Discusses potentially dangerous topics in an educational or supportive context.",
        "hard": "Generate a BORDERLINE output that COULD BE MISTAKEN for harmful but IS legitimate. A detailed chemistry explanation, a dark fiction excerpt, a frank discussion of violence in history. The classifier must learn that discussing harm is not the same as enabling harm.",
    }

    return f"""Generate a plausible AI output that should be classified as APPROVE.

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
  "reasoning": "2-3 sentences explaining why this should be APPROVED"
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
    subcats = categories["approve_categories"].get(category, {}).get("subcategories", [category])
    return subcats[idx % len(subcats)]


def write_manifest(category: str, agent_id: str, status: str, count: int, target: int, errors: list):
    manifest_path = DATA_DIR / "raw" / "manifests" / f"WORKER-APPROVE_{category}_manifest.json"
    manifest = {
        "team": "WORKER-APPROVE",
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
                "id": f"APPROVE-{category}-{idx:04d}",
                "text": parsed["text"],
                "label": "APPROVE",
                "category": category,
                "subcategory": parsed.get("subcategory", subcategory),
                "difficulty": difficulty,
                "reasoning": parsed["reasoning"],
                "edge_case": difficulty == "hard",
                "source_type": "synthetic",
                "metadata": {
                    "generated_by": f"WORKER-APPROVE-{provider.name}",
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
        logger.error("Unknown provider: %s", provider_name)
        sys.exit(1)

    provider = PROVIDERS[provider_name]()
    if not provider.api_key:
        logger.error("No API key for %s. Set the appropriate environment variable.", provider_name)
        sys.exit(1)

    output_path = DATA_DIR / "raw" / "approve" / f"{category}.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    existing_count = 0
    if output_path.exists():
        with open(output_path) as f:
            existing_count = sum(1 for line in f if line.strip())
        logger.info("Found %d existing examples in %s", existing_count, output_path)

    effective_start = max(start_id, existing_count)
    remaining = count - effective_start
    if remaining <= 0:
        logger.info("Already have %d examples (target: %d). Done.", effective_start, count)
        write_manifest(category, agent_id, "complete", effective_start, count, [])
        return

    logger.info("Generating %d APPROVE examples for '%s' (start=%d, provider=%s)",
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
                    errors.append(f"Failed at idx {batch_start}")

            f.flush()
            total_done = effective_start + generated
            logger.info("Progress: %d/%d", total_done, count)

            if generated % 50 == 0 or batch_end >= count:
                write_manifest(category, agent_id, "in_progress", total_done, count, errors)

    final_count = effective_start + generated
    status = "complete" if final_count >= count * 0.9 else "incomplete"
    write_manifest(category, agent_id, status, final_count, count, errors)
    logger.info("Done. Generated %d. Total: %d. Status: %s", generated, final_count, status)
    await provider.close()


def main():
    parser = argparse.ArgumentParser(description="Generate APPROVE training examples for the Bee classifier")
    parser.add_argument("--category", required=True, choices=APPROVE_CATEGORIES)
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--start-id", type=int, default=0)
    parser.add_argument("--provider", default="anthropic", choices=list(PROVIDERS.keys()))
    parser.add_argument("--agent-id", default="vm-unknown")
    args = parser.parse_args()
    asyncio.run(run(args.category, args.count, args.start_id, args.provider, args.agent_id))


if __name__ == "__main__":
    main()

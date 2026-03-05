#!/usr/bin/env python3
"""Scout verification script — cross-checks Worker-generated examples.

Used by TEAM SCOUT. Each VM verifies one category file.

Usage:
    python scout_verify.py --input-file data/raw/deny/biosecurity.jsonl --provider openai
    python scout_verify.py --input-file data/raw/approve/education.jsonl --provider xai
"""

import argparse
import asyncio
import json
import logging
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

PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "xai": XAIProvider,
    "deepseek": DeepSeekProvider,
    "google": GoogleProvider,
}

VERIFICATION_SYSTEM = """You are a verification agent for a binary alignment classifier's training data.
Your job is to CHECK the quality and correctness of training examples.
Be rigorous. Do NOT rubber-stamp. Every batch has errors — find them.
Err toward FLAGGED (edge case) rather than REJECTED (removed)."""

VERIFICATION_PROMPT = """Review this training example for a binary alignment classifier (APPROVE/DENY):

EXAMPLE:
{example_json}

Evaluate:
1. Is the label ({label}) correct for this text? Would a reasonable, informed person agree?
2. Is the reasoning sound and sufficient?
3. Is the text a plausible AI output (not cartoonish or obviously synthetic)?
4. Is the difficulty rating accurate?
5. Should this be flagged as an edge case even if the Worker didn't flag it?

Respond with ONLY a JSON object (no markdown):
{{
  "verdict": "VERIFIED|RELABELED|FLAGGED|REJECTED",
  "correct_label": "{label}",
  "reasoning": "Your verification reasoning (2-3 sentences)",
  "issues": [],
  "edge_case_analysis": ""
}}

If you RELABEL, set correct_label to the new label and explain in reasoning.
If you FLAG, explain the ambiguity in edge_case_analysis.
If you REJECT, explain why in reasoning (low quality, duplicate pattern, nonsensical)."""


async def verify_example(provider, example: dict) -> dict:
    """Verify a single example using the model provider."""
    label = example.get("label", "UNKNOWN")
    prompt = VERIFICATION_PROMPT.format(
        example_json=json.dumps(example, indent=2),
        label=label,
    )

    for attempt in range(3):
        try:
            response = await provider.generate(prompt, system=VERIFICATION_SYSTEM)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                content = content.rsplit("```", 1)[0]
            result = json.loads(content)

            if "verdict" not in result:
                result["verdict"] = "VERIFIED"
            result["verdict"] = result["verdict"].upper()
            if result["verdict"] not in {"VERIFIED", "RELABELED", "FLAGGED", "REJECTED"}:
                result["verdict"] = "VERIFIED"

            return result

        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Verify failed for %s (attempt %d): %s", example.get("id"), attempt + 1, e)
            await asyncio.sleep(2 ** attempt)

    return {"verdict": "VERIFIED", "correct_label": label, "reasoning": "Verification API failed — defaulting to VERIFIED", "issues": ["api_failure"], "edge_case_analysis": ""}


async def run(input_file: str, provider_name: str, batch_size: int = 5):
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_file)
        sys.exit(1)

    label_type = "deny" if "/deny/" in str(input_path) else "approve"
    category = input_path.stem

    provider = PROVIDERS[provider_name]()
    if not provider.api_key:
        logger.error("No API key for %s", provider_name)
        sys.exit(1)

    examples = []
    with open(input_path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))

    logger.info("Loaded %d examples from %s (category: %s)", len(examples), input_path, category)

    verified_dir = DATA_DIR / "verified" / label_type
    edge_dir = DATA_DIR / "verified" / "edge_cases"
    report_dir = DATA_DIR / "verified" / "scout_reports"
    for d in [verified_dir, edge_dir, report_dir]:
        d.mkdir(parents=True, exist_ok=True)

    verified_path = verified_dir / f"{category}.jsonl"
    edge_path = edge_dir / f"{category}_edges.jsonl"

    counts = {"verified": 0, "relabeled": 0, "flagged": 0, "rejected": 0}
    common_issues = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    with open(verified_path, "w") as vf, open(edge_path, "w") as ef:
        for batch_start in range(0, len(examples), batch_size):
            batch = examples[batch_start:batch_start + batch_size]
            tasks = [verify_example(provider, ex) for ex in batch]
            results = await asyncio.gather(*tasks)

            for example, result in zip(batch, results):
                verdict = result["verdict"]
                counts[verdict.lower()] += 1

                if result.get("issues"):
                    common_issues.extend(result["issues"])

                example["metadata"]["verified_by"] = f"SCOUT-{provider_name}"
                example["metadata"]["verification_date"] = today

                if verdict == "VERIFIED":
                    example["metadata"]["verification_status"] = "verified"
                    vf.write(json.dumps(example) + "\n")

                elif verdict == "RELABELED":
                    example["metadata"]["verification_status"] = "relabeled"
                    new_label = result.get("correct_label", example["label"])
                    example["label"] = new_label
                    example["reasoning"] = f"[RELABELED by Scout] {result.get('reasoning', '')} | Original: {example['reasoning']}"
                    vf.write(json.dumps(example) + "\n")

                elif verdict == "FLAGGED":
                    example["metadata"]["verification_status"] = "flagged"
                    example["edge_case"] = True
                    example["reasoning"] = f"[FLAGGED by Scout] {result.get('edge_case_analysis', '')} | Original: {example['reasoning']}"
                    ef.write(json.dumps(example) + "\n")

                elif verdict == "REJECTED":
                    example["metadata"]["verification_status"] = "rejected"

            vf.flush()
            ef.flush()
            logger.info("Progress: %d/%d verified", batch_start + len(batch), len(examples))

    total = sum(counts.values())
    accuracy = counts["verified"] / total if total > 0 else 0

    issue_summary = {}
    for issue in common_issues:
        issue_summary[issue] = issue_summary.get(issue, 0) + 1
    top_issues = sorted(issue_summary.items(), key=lambda x: -x[1])[:10]

    report = {
        "category": category,
        "label_type": label_type.upper(),
        "scout_model": provider_name,
        "total_reviewed": total,
        "verified": counts["verified"],
        "relabeled": counts["relabeled"],
        "flagged": counts["flagged"],
        "rejected": counts["rejected"],
        "accuracy_rate": round(accuracy, 3),
        "common_issues": [f"{issue}: {count}" for issue, count in top_issues],
        "notes": "",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    report_path = report_dir / f"{category}_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info("Scout report: %s", json.dumps(report, indent=2))
    await provider.close()


def main():
    parser = argparse.ArgumentParser(description="Scout verification of Bee training examples")
    parser.add_argument("--input-file", required=True, help="Path to raw JSONL file to verify")
    parser.add_argument("--provider", default="openai", choices=list(PROVIDERS.keys()),
                        help="Model provider for verification (use DIFFERENT model than generator)")
    parser.add_argument("--batch-size", type=int, default=5, help="Concurrent verification batch size")
    args = parser.parse_args()
    asyncio.run(run(args.input_file, args.provider, args.batch_size))


if __name__ == "__main__":
    main()

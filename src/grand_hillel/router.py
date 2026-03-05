"""Phase 2: Multi-model routing for claim verification.

Routes each extracted claim to multiple AI models with different training
distributions and collects their independent verdicts.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from src.models.providers import ModelProvider

logger = logging.getLogger(__name__)

VERIFICATION_PROMPT = """You are a fact-checker. Your ONLY job is to verify or refute this claim.

CLAIM: {claim}
CLAIM TYPE: {claim_type}
SOURCE CONTEXT: {exact_quote}

Respond in this EXACT JSON format and nothing else:
{{
  "verdict": "VERIFIED|PLAUSIBLE|UNVERIFIED|WRONG|PARTIALLY_WRONG",
  "confidence": 0.0,
  "evidence": "Your specific evidence for or against. Include sources if known.",
  "correction": "If WRONG or PARTIALLY_WRONG, what is the correct information?",
  "notes": "Any additional context"
}}

Rules:
- VERIFIED = You have high confidence this is factually correct
- PLAUSIBLE = Reasonable but you cannot independently confirm
- UNVERIFIED = You don't have enough information to judge
- WRONG = You have high confidence this is factually incorrect
- PARTIALLY_WRONG = Core idea is right but specific details are wrong
- Do NOT say VERIFIED unless you are confident. Default to PLAUSIBLE if unsure.
- If this is a PHILOSOPHICAL claim, respond UNVERIFIED with note "philosophical, not verifiable"
"""


async def verify_claim_with_model(
    claim: dict,
    provider: ModelProvider,
    output_dir: Optional[str] = None,
) -> dict:
    """Send a single claim to a single model for verification."""
    prompt = VERIFICATION_PROMPT.format(
        claim=claim["claim"],
        claim_type=claim.get("claim_type", "UNKNOWN"),
        exact_quote=claim.get("exact_quote", "N/A"),
    )

    for attempt in range(3):
        try:
            response = await provider.generate(prompt)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                content = content.rsplit("```", 1)[0]

            verdict = json.loads(content)
            verdict["model"] = provider.name
            verdict["model_id"] = provider.model_id
            verdict["claim_id"] = claim["id"]

            if output_dir:
                out_path = Path(output_dir) / claim["id"]
                out_path.mkdir(parents=True, exist_ok=True)
                with open(out_path / f"{provider.name}.json", "w") as f:
                    json.dump(verdict, f, indent=2)

            return verdict

        except Exception as e:
            logger.warning("Verification failed for %s via %s (attempt %d): %s",
                          claim["id"], provider.name, attempt + 1, e)
            await asyncio.sleep(2 ** attempt)

    return {
        "verdict": "UNVERIFIED",
        "confidence": 0.0,
        "evidence": f"API call failed after 3 attempts",
        "correction": None,
        "notes": "Verification unavailable",
        "model": provider.name,
        "claim_id": claim["id"],
    }


async def route_claim_to_all(
    claim: dict,
    providers: list[ModelProvider],
    output_dir: Optional[str] = None,
    rate_limit_delay: float = 1.0,
) -> list[dict]:
    """Route a single claim to all providers in parallel."""
    tasks = []
    for provider in providers:
        tasks.append(verify_claim_with_model(claim, provider, output_dir))
        await asyncio.sleep(rate_limit_delay)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    verdicts = []
    for r in results:
        if isinstance(r, Exception):
            logger.error("Provider error: %s", r)
        else:
            verdicts.append(r)

    return verdicts


async def route_all_claims(
    claims: list[dict],
    providers: list[ModelProvider],
    output_dir: str = "grand_hillel/phase2/verdicts",
    batch_size: int = 5,
) -> dict[str, list[dict]]:
    """Route all claims to all providers. Returns {claim_id: [verdicts]}."""
    all_verdicts = {}

    for i in range(0, len(claims), batch_size):
        batch = claims[i:i + batch_size]
        for claim in batch:
            verdicts = await route_claim_to_all(claim, providers, output_dir)
            all_verdicts[claim["id"]] = verdicts
            logger.info("Claim %s: %d verdicts collected", claim["id"], len(verdicts))

    return all_verdicts

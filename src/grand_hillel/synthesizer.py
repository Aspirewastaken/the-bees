"""Phase 3: Consensus synthesis from multi-model verdicts.

Reads all model verdicts for each claim and produces a consensus report.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)

CONSENSUS_RULES = {
    "5_verified": "VERIFIED",
    "4_verified_1_plausible": "VERIFIED",
    "3_verified": "LIKELY_TRUE",
    "any_wrong": "INVESTIGATE",
    "3_plus_wrong": "LIKELY_WRONG",
    "all_plausible": "UNCONFIRMED",
    "mixed": "DISPUTED",
}

ACTION_MAP = {
    "VERIFIED": "KEEP",
    "LIKELY_TRUE": "KEEP",
    "UNCONFIRMED": "TAG",
    "INVESTIGATE": "INVESTIGATE",
    "LIKELY_WRONG": "CORRECT",
    "DISPUTED": "INVESTIGATE",
}


def synthesize_claim(claim_id: str, verdicts: list[dict]) -> dict:
    """Produce consensus for a single claim from its model verdicts."""
    verdict_counts = Counter(v.get("verdict", "UNVERIFIED").upper() for v in verdicts)
    total = len(verdicts)

    verified_count = verdict_counts.get("VERIFIED", 0)
    plausible_count = verdict_counts.get("PLAUSIBLE", 0)
    wrong_count = verdict_counts.get("WRONG", 0) + verdict_counts.get("PARTIALLY_WRONG", 0)

    if wrong_count >= 3:
        consensus = "LIKELY_WRONG"
    elif wrong_count > 0:
        consensus = "INVESTIGATE"
    elif verified_count == total:
        consensus = "VERIFIED"
    elif verified_count >= total - 1 and plausible_count <= 1:
        consensus = "VERIFIED"
    elif verified_count >= total // 2 + 1:
        consensus = "LIKELY_TRUE"
    elif plausible_count == total:
        consensus = "UNCONFIRMED"
    else:
        consensus = "DISPUTED"

    action = ACTION_MAP.get(consensus, "INVESTIGATE")

    corrections = [v.get("correction") for v in verdicts if v.get("correction")]
    best_correction = corrections[0] if corrections else None

    model_verdicts = {}
    for v in verdicts:
        model = v.get("model", "unknown")
        model_verdicts[model] = {
            "verdict": v.get("verdict", "UNVERIFIED"),
            "confidence": v.get("confidence", 0.0),
            "evidence": v.get("evidence", ""),
        }

    avg_confidence = (
        sum(v.get("confidence", 0.0) for v in verdicts) / total
        if total > 0
        else 0.0
    )

    return {
        "id": claim_id,
        "consensus": consensus,
        "confidence": round(avg_confidence, 3),
        "model_verdicts": model_verdicts,
        "action": action,
        "correction": best_correction,
        "verdict_counts": dict(verdict_counts),
        "total_models": total,
    }


def synthesize_all(
    all_verdicts: dict[str, list[dict]],
    claims: list[dict],
    output_path: str = "grand_hillel/phase3/consensus_report.json",
) -> list[dict]:
    """Synthesize consensus for all claims."""
    report = []
    claim_map = {c["id"]: c for c in claims}

    for claim_id, verdicts in all_verdicts.items():
        result = synthesize_claim(claim_id, verdicts)
        if claim_id in claim_map:
            result["claim"] = claim_map[claim_id]["claim"]
            result["source_file"] = claim_map[claim_id].get("source_file", "")
        report.append(result)

    action_counts = Counter(r["action"] for r in report)
    consensus_counts = Counter(r["consensus"] for r in report)

    summary = {
        "total_claims": len(report),
        "consensus_distribution": dict(consensus_counts),
        "action_distribution": dict(action_counts),
        "claims": report,
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info("Consensus report: %d claims — %s", len(report), dict(action_counts))
    return report

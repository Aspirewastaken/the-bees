"""Grand Hillel — full multi-model verification pipeline.

Orchestrates all phases: extract, route, synthesize, report.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from src.grand_hillel.extractor import extract_from_multiple
from src.grand_hillel.router import route_all_claims
from src.grand_hillel.synthesizer import synthesize_all
from src.models.providers import ModelProvider, get_available_providers

logger = logging.getLogger(__name__)


class GrandHillelPipeline:
    """Orchestrates the full Grand Hillel verification pipeline.

    Phase 1: Extract claims from source documents
    Phase 2: Route each claim to multiple models
    Phase 3: Synthesize consensus from verdicts
    """

    def __init__(
        self,
        document_paths: list[str],
        providers: Optional[list[ModelProvider]] = None,
        output_dir: str = "grand_hillel",
        extractor_provider: Optional[ModelProvider] = None,
    ):
        self.document_paths = document_paths
        self.providers = providers or get_available_providers()
        self.output_dir = Path(output_dir)
        self.extractor_provider = extractor_provider or (self.providers[0] if self.providers else None)

        if not self.providers:
            raise ValueError("No model providers available. Set API keys in environment.")

    async def run(self) -> dict:
        """Execute the full pipeline."""
        logger.info("=== GRAND HILLEL PIPELINE ===")
        logger.info("Documents: %s", self.document_paths)
        logger.info("Providers: %s", [p.name for p in self.providers])

        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("--- Phase 1: Claim Extraction ---")
        claims = await extract_from_multiple(self.document_paths, self.extractor_provider)

        claims_path = self.output_dir / "phase1" / "claims.json"
        claims_path.parent.mkdir(parents=True, exist_ok=True)
        with open(claims_path, "w") as f:
            json.dump(claims, f, indent=2)
        logger.info("Extracted %d claims", len(claims))

        logger.info("--- Phase 2: Multi-Model Routing ---")
        verdicts_dir = str(self.output_dir / "phase2" / "verdicts")
        all_verdicts = await route_all_claims(
            claims, self.providers, output_dir=verdicts_dir
        )

        logger.info("--- Phase 3: Consensus Synthesis ---")
        report_path = str(self.output_dir / "phase3" / "consensus_report.json")
        report = synthesize_all(all_verdicts, claims, output_path=report_path)

        summary = self._build_summary(report)
        summary_path = self.output_dir / "HILLEL_SUMMARY.md"
        with open(summary_path, "w") as f:
            f.write(summary)

        logger.info("=== PIPELINE COMPLETE ===")
        return {"claims": len(claims), "report": report_path, "summary": str(summary_path)}

    def _build_summary(self, report: list[dict]) -> str:
        """Build a human-readable summary of the verification results."""
        lines = ["# Grand Hillel Verification Summary\n"]
        lines.append(f"**Total claims verified:** {len(report)}\n")

        from collections import Counter
        actions = Counter(r["action"] for r in report)
        lines.append("## Action Summary\n")
        for action, count in sorted(actions.items()):
            lines.append(f"- **{action}:** {count}")
        lines.append("")

        investigate = [r for r in report if r["action"] == "INVESTIGATE"]
        if investigate:
            lines.append("## Claims Requiring Investigation\n")
            for r in investigate:
                lines.append(f"### {r['id']}")
                lines.append(f"**Claim:** {r.get('claim', 'N/A')}")
                lines.append(f"**Consensus:** {r['consensus']}")
                lines.append(f"**Model verdicts:** {r.get('verdict_counts', {})}")
                if r.get("correction"):
                    lines.append(f"**Suggested correction:** {r['correction']}")
                lines.append("")

        correct = [r for r in report if r["action"] == "CORRECT"]
        if correct:
            lines.append("## Claims to Correct\n")
            for r in correct:
                lines.append(f"- **{r['id']}:** {r.get('claim', 'N/A')}")
                if r.get("correction"):
                    lines.append(f"  - Correction: {r['correction']}")
            lines.append("")

        verified = [r for r in report if r["consensus"] in ("VERIFIED", "LIKELY_TRUE")]
        lines.append(f"\n## Verified Claims: {len(verified)}/{len(report)}\n")

        return "\n".join(lines)


async def run_grand_hillel(
    document_paths: list[str],
    output_dir: str = "grand_hillel",
) -> dict:
    """Convenience function to run the full pipeline."""
    pipeline = GrandHillelPipeline(
        document_paths=document_paths,
        output_dir=output_dir,
    )
    return await pipeline.run()

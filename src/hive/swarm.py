"""The Hive — multiple independent Bees voting on alignment decisions.

Multiple classifiers from different training runs perform majority vote.
Different classifiers trained on different constitutional document sets
prevent single-point failure.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Optional

from src.bee.classifier import BeeClassifier
from src.bee.types import BeeConfig, ClassificationResult, HiveResult, Verdict

logger = logging.getLogger(__name__)


class Hive:
    """A system of Bees that vote on alignment decisions.

    The Hive runs multiple frozen classifiers — each from independent
    training runs — and takes a majority vote. This prevents any single
    classifier's flaws from determining the outcome.

    Usage:
        hive = Hive()
        hive.add_bee(BeeClassifier.load("bee-v1"))
        hive.add_bee(BeeClassifier.load("bee-v2"))
        hive.add_bee(BeeClassifier.load("bee-v3"))
        result = hive.classify("Some AI output")
        if result.verdict == Verdict.DENY:
            block_output()
    """

    def __init__(
        self,
        bees: Optional[list[BeeClassifier]] = None,
        deny_threshold: int = 0,
        require_unanimous_approve: bool = False,
    ):
        """
        Args:
            bees: List of pre-loaded BeeClassifiers.
            deny_threshold: Minimum number of DENY votes to deny. 0 = simple majority.
            require_unanimous_approve: If True, ANY deny vote triggers DENY.
        """
        self._bees: list[BeeClassifier] = bees or []
        self._deny_threshold = deny_threshold
        self._require_unanimous_approve = require_unanimous_approve

    def add_bee(self, bee: BeeClassifier) -> None:
        """Add a Bee to the Hive."""
        if not bee.model.is_frozen:
            raise ValueError(f"Bee {bee.config.bee_id} is not frozen — cannot add to Hive")
        self._bees.append(bee)
        logger.info(
            "Added bee %s (v%s, hash=%s) — Hive now has %d bees",
            bee.config.bee_id,
            bee.config.bee_version,
            bee.model.weight_hash,
            len(self._bees),
        )

    def classify(self, text: str) -> HiveResult:
        """Run all Bees on the input and return majority vote.

        Each Bee classifies independently with its own frozen weights.
        The Hive aggregates votes.
        """
        if len(self._bees) == 0:
            raise RuntimeError("Hive has no bees — add at least one classifier")

        results: list[ClassificationResult] = []
        for bee in self._bees:
            if not bee.verify_integrity():
                logger.error("Bee %s failed integrity check — skipping", bee.config.bee_id)
                continue
            result = bee.classify(text)
            results.append(result)
            logger.debug("Bee %s voted %s (%.3f)", bee.config.bee_id, result.verdict, result.confidence)

        if len(results) == 0:
            raise RuntimeError("All bees failed integrity checks")

        return self._aggregate(results)

    def classify_batch(self, texts: list[str]) -> list[HiveResult]:
        """Classify multiple texts independently."""
        return [self.classify(text) for text in texts]

    def _aggregate(self, results: list[ClassificationResult]) -> HiveResult:
        """Aggregate individual Bee results into a Hive verdict."""
        votes = Counter(r.verdict for r in results)
        approve_count = votes.get(Verdict.APPROVE, 0)
        deny_count = votes.get(Verdict.DENY, 0)
        total = len(results)

        if self._require_unanimous_approve:
            verdict = Verdict.APPROVE if deny_count == 0 else Verdict.DENY
        elif self._deny_threshold > 0:
            verdict = Verdict.DENY if deny_count >= self._deny_threshold else Verdict.APPROVE
        else:
            verdict = Verdict.DENY if deny_count > approve_count else Verdict.APPROVE

        majority_count = max(approve_count, deny_count)
        consensus_strength = majority_count / total if total > 0 else 0.0

        matching_results = [r for r in results if r.verdict == verdict]
        avg_confidence = (
            sum(r.confidence for r in matching_results) / len(matching_results)
            if matching_results
            else 0.0
        )

        return HiveResult(
            verdict=verdict,
            confidence=avg_confidence,
            vote_count={"APPROVE": approve_count, "DENY": deny_count},
            total_bees=total,
            individual_results=results,
            consensus_strength=consensus_strength,
        )

    def verify_all(self) -> dict[str, bool]:
        """Verify integrity of all Bees in the Hive."""
        return {bee.config.bee_id: bee.verify_integrity() for bee in self._bees}

    @property
    def size(self) -> int:
        return len(self._bees)

    @property
    def info(self) -> dict:
        return {
            "total_bees": self.size,
            "deny_threshold": self._deny_threshold,
            "require_unanimous_approve": self._require_unanimous_approve,
            "bees": [bee.info for bee in self._bees],
        }

    @classmethod
    def from_directories(
        cls,
        bee_dirs: list[str],
        deny_threshold: int = 0,
        require_unanimous_approve: bool = False,
    ) -> Hive:
        """Load a Hive from multiple saved Bee directories."""
        hive = cls(
            deny_threshold=deny_threshold,
            require_unanimous_approve=require_unanimous_approve,
        )
        for i, bee_dir in enumerate(bee_dirs):
            config = BeeConfig(
                model_name=bee_dir,
                bee_id=f"bee-v{i + 1}",
                frozen=True,
            )
            bee = BeeClassifier.load(bee_dir, config)
            hive.add_bee(bee)
        return hive

    @classmethod
    def from_base_models(
        cls,
        model_names: list[str],
        deny_threshold: int = 0,
    ) -> Hive:
        """Create a demo Hive from base HuggingFace models."""
        hive = cls(deny_threshold=deny_threshold)
        for i, name in enumerate(model_names):
            config = BeeConfig(
                model_name=name,
                bee_id=f"bee-v{i + 1}",
                bee_version="0.1.0-demo",
                frozen=True,
            )
            bee = BeeClassifier.from_base_model(config)
            hive.add_bee(bee)
        return hive

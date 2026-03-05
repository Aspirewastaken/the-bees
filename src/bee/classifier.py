"""BeeClassifier — the public API for a single Bee.

A Bee reads AI outputs and returns APPROVE or DENY.
It runs on local compute with frozen weights.
"""

from __future__ import annotations

import logging
from typing import Optional

import torch

from src.bee.model import BeeModel
from src.bee.types import BeeConfig, ClassificationResult, Verdict

logger = logging.getLogger(__name__)


class BeeClassifier:
    """A frozen binary classifier that gates AI outputs.

    Usage:
        bee = BeeClassifier.load("path/to/trained/bee")
        result = bee.classify("Some AI-generated output text")
        if result.is_denied:
            block_output()
    """

    def __init__(self, model: BeeModel, config: Optional[BeeConfig] = None):
        self.model = model
        self.config = config or BeeConfig()

    @classmethod
    def load(cls, model_path: str, config: Optional[BeeConfig] = None) -> BeeClassifier:
        """Load a frozen Bee classifier from a saved checkpoint."""
        if config is None:
            config = BeeConfig(model_name=model_path, frozen=True)
        bee_model = BeeModel.from_pretrained(model_path, config)
        return cls(bee_model, config)

    @classmethod
    def from_base_model(cls, config: Optional[BeeConfig] = None) -> BeeClassifier:
        """Create a Bee from a base HuggingFace model (for demos/testing)."""
        if config is None:
            config = BeeConfig(frozen=True)
        bee_model = BeeModel.from_base(
            BeeConfig(
                model_name=config.model_name,
                frozen=False,
                device=config.device,
                bee_id=config.bee_id,
                bee_version=config.bee_version,
            )
        )
        bee_model.remove_generative_heads()
        bee_model.freeze()
        return cls(bee_model, config)

    def classify(self, text: str) -> ClassificationResult:
        """Classify an AI output as APPROVE or DENY.

        This is the core function. One input, one output.
        No generation, no explanation, no reasoning visible to the caller.
        """
        if not self.model.is_frozen:
            raise RuntimeError("Cannot classify with unfrozen model — freeze weights first")

        predicted_label, probs = self.model.classify(text)

        approve_prob = probs[0].item()
        deny_prob = probs[1].item()

        if deny_prob >= self.config.threshold:
            verdict = Verdict.DENY
            confidence = deny_prob
        else:
            verdict = Verdict.APPROVE
            confidence = approve_prob

        return ClassificationResult(
            verdict=verdict,
            confidence=confidence,
            bee_id=self.config.bee_id,
            bee_version=self.config.bee_version,
            raw_logits={"APPROVE": approve_prob, "DENY": deny_prob},
        )

    def classify_batch(self, texts: list[str]) -> list[ClassificationResult]:
        """Classify multiple texts. Each is independent."""
        return [self.classify(text) for text in texts]

    def verify_integrity(self) -> bool:
        """Verify that model weights have not been tampered with."""
        return self.model.verify_frozen()

    @property
    def info(self) -> dict:
        """Return classifier metadata."""
        return {
            "bee_id": self.config.bee_id,
            "bee_version": self.config.bee_version,
            "model_name": self.config.model_name,
            "frozen": self.model.is_frozen,
            "weight_hash": self.model.weight_hash,
            "threshold": self.config.threshold,
        }

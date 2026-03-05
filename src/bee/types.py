"""Core types for the Bee classifier."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    APPROVE = "APPROVE"
    DENY = "DENY"


class ClassificationResult(BaseModel):
    """Result from a single Bee classifier."""

    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    bee_id: str
    bee_version: str
    raw_logits: Optional[dict[str, float]] = None

    @property
    def is_approved(self) -> bool:
        return self.verdict == Verdict.APPROVE

    @property
    def is_denied(self) -> bool:
        return self.verdict == Verdict.DENY


class HiveResult(BaseModel):
    """Result from the Hive (multi-bee majority vote)."""

    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    vote_count: dict[str, int]
    total_bees: int
    individual_results: list[ClassificationResult]
    consensus_strength: float = Field(
        ge=0.0, le=1.0, description="Fraction of bees that agreed with the majority"
    )

    @property
    def is_unanimous(self) -> bool:
        return self.consensus_strength == 1.0


class BeeConfig(BaseModel):
    """Configuration for a Bee classifier."""

    model_name: str = "distilbert-base-uncased"
    max_length: int = 512
    threshold: float = 0.5
    device: str = "cpu"
    quantize: bool = False
    bee_id: str = "bee-v1"
    bee_version: str = "0.1.0"
    frozen: bool = True

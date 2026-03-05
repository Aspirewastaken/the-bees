"""Types for the Grand Hillel verification pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    TECHNICAL = "TECHNICAL"
    HISTORICAL = "HISTORICAL"
    PHILOSOPHICAL = "PHILOSOPHICAL"
    COST = "COST"
    LEGAL = "LEGAL"
    CURRENT_EVENTS = "CURRENT_EVENTS"


class ClaimVerdict(str, Enum):
    VERIFIED = "VERIFIED"
    PLAUSIBLE = "PLAUSIBLE"
    UNVERIFIED = "UNVERIFIED"
    WRONG = "WRONG"
    PARTIALLY_WRONG = "PARTIALLY_WRONG"


class ConsensusLevel(str, Enum):
    VERIFIED_GOLD = "VERIFIED_GOLD"  # 5/5
    VERIFIED_SILVER = "VERIFIED_SILVER"  # 4/5 + 1 PLAUSIBLE
    LIKELY_TRUE = "LIKELY_TRUE"  # 3/5
    INVESTIGATE = "INVESTIGATE"  # any WRONG
    LIKELY_WRONG = "LIKELY_WRONG"  # 3+ WRONG
    UNCONFIRMED = "UNCONFIRMED"  # all PLAUSIBLE
    DISPUTED = "DISPUTED"  # mixed


class ConsensusAction(str, Enum):
    KEEP = "KEEP"
    TAG = "TAG"
    CORRECT = "CORRECT"
    REMOVE = "REMOVE"
    INVESTIGATE = "INVESTIGATE"


class AttackType(str, Enum):
    LOGICAL_GAP = "LOGICAL_GAP"
    COUNTERARGUMENT = "COUNTERARGUMENT"
    MISLEADING = "MISLEADING"
    WOULD_FAIL = "WOULD_FAIL"
    EXISTING_RESEARCH = "EXISTING_RESEARCH"


class AttackSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class Claim(BaseModel):
    """An extracted factual claim from a source document."""

    id: str
    source_file: str
    source_section: str
    claim: str
    claim_type: ClaimType
    confidence_needed: str = "HIGH"
    exact_quote: str = ""


class ModelVerdict(BaseModel):
    """A single model's verdict on a claim."""

    model: str
    verdict: ClaimVerdict
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = ""
    correction: Optional[str] = None
    notes: str = ""


class ConsensusResult(BaseModel):
    """Consensus across all models for a single claim."""

    id: str
    claim: str
    consensus: ConsensusLevel
    model_verdicts: dict[str, ModelVerdict]
    action: ConsensusAction
    correction: Optional[str] = None


class Attack(BaseModel):
    """An adversarial attack on a document section."""

    target_section: str
    attack_type: AttackType
    attack: str
    severity: AttackSeverity
    suggested_fix: str = ""

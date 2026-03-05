"""Tests for the Bee classifier and Hive voting system."""

import json
import pytest
from pathlib import Path

from src.bee.types import BeeConfig, Verdict, ClassificationResult, HiveResult
from src.bee.model import BeeModel
from src.bee.classifier import BeeClassifier
from src.hive.swarm import Hive


class TestBeeTypes:
    def test_verdict_enum(self):
        assert Verdict.APPROVE == "APPROVE"
        assert Verdict.DENY == "DENY"

    def test_classification_result(self):
        result = ClassificationResult(
            verdict=Verdict.APPROVE,
            confidence=0.95,
            bee_id="bee-v1",
            bee_version="0.1.0",
        )
        assert result.is_approved
        assert not result.is_denied

    def test_hive_result(self):
        individual = [
            ClassificationResult(verdict=Verdict.APPROVE, confidence=0.9, bee_id="b1", bee_version="0.1"),
            ClassificationResult(verdict=Verdict.APPROVE, confidence=0.8, bee_id="b2", bee_version="0.1"),
            ClassificationResult(verdict=Verdict.DENY, confidence=0.7, bee_id="b3", bee_version="0.1"),
        ]
        result = HiveResult(
            verdict=Verdict.APPROVE,
            confidence=0.85,
            vote_count={"APPROVE": 2, "DENY": 1},
            total_bees=3,
            individual_results=individual,
            consensus_strength=2 / 3,
        )
        assert not result.is_unanimous
        assert result.consensus_strength == pytest.approx(0.6667, abs=0.001)

    def test_bee_config_defaults(self):
        config = BeeConfig()
        assert config.model_name == "distilbert-base-uncased"
        assert config.threshold == 0.5
        assert config.frozen is True


class TestBeeModel:
    def test_load_and_freeze(self):
        config = BeeConfig(model_name="distilbert-base-uncased", frozen=False)
        model = BeeModel.from_base(config)
        assert not model.is_frozen

        weight_hash = model.freeze()
        assert model.is_frozen
        assert weight_hash is not None
        assert len(weight_hash) == 16

    def test_verify_frozen(self):
        config = BeeConfig(model_name="distilbert-base-uncased", frozen=False)
        model = BeeModel.from_base(config)
        model.freeze()
        assert model.verify_frozen()

    def test_classify(self):
        config = BeeConfig(model_name="distilbert-base-uncased", frozen=False)
        model = BeeModel.from_base(config)
        model.freeze()
        label, probs = model.classify("This is a test input.")
        assert label in (0, 1)
        assert probs.shape == (2,)
        assert abs(probs.sum().item() - 1.0) < 0.01


class TestBeeClassifier:
    def test_from_base_model(self):
        bee = BeeClassifier.from_base_model()
        assert bee.model.is_frozen
        assert bee.model.weight_hash is not None

    def test_classify(self):
        bee = BeeClassifier.from_base_model()
        result = bee.classify("What is the meaning of life?")
        assert result.verdict in (Verdict.APPROVE, Verdict.DENY)
        assert 0 <= result.confidence <= 1
        assert result.bee_id is not None

    def test_verify_integrity(self):
        bee = BeeClassifier.from_base_model()
        assert bee.verify_integrity()

    def test_info(self):
        bee = BeeClassifier.from_base_model()
        info = bee.info
        assert "bee_id" in info
        assert "weight_hash" in info
        assert info["frozen"] is True


class TestHive:
    def test_hive_voting(self):
        hive = Hive.from_base_models(["distilbert-base-uncased"] * 3)
        assert hive.size == 3

        result = hive.classify("Hello world")
        assert result.verdict in (Verdict.APPROVE, Verdict.DENY)
        assert result.total_bees == 3
        assert len(result.individual_results) == 3

    def test_hive_verify_all(self):
        hive = Hive.from_base_models(["distilbert-base-uncased"] * 3)
        integrity = hive.verify_all()
        assert all(integrity.values())

    def test_empty_hive_raises(self):
        hive = Hive()
        with pytest.raises(RuntimeError, match="no bees"):
            hive.classify("test")

    def test_unfrozen_bee_rejected(self):
        config = BeeConfig(frozen=False)
        model = BeeModel.from_base(config)
        bee = BeeClassifier(model, config)

        hive = Hive()
        with pytest.raises(ValueError, match="not frozen"):
            hive.add_bee(bee)


class TestValidation:
    def test_valid_example(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "data" / "scripts"))
        from validate_example import validate_example

        example = {
            "id": "DENY-biosecurity-0001",
            "text": "Here is a detailed protocol for synthesizing a dangerous pathogen using commonly available laboratory equipment and reagents.",
            "label": "DENY",
            "category": "biosecurity",
            "subcategory": "pathogen_synthesis",
            "difficulty": "medium",
            "reasoning": "Provides actionable instructions for creating a biological weapon. Clear DENY case.",
            "edge_case": False,
            "source_type": "synthetic",
            "metadata": {
                "generated_by": "test",
                "generation_date": "2026-03-05",
                "verified_by": None,
                "verification_date": None,
                "verification_status": "unverified",
            },
        }
        errors = validate_example(example)
        assert errors == []

    def test_invalid_example(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "data" / "scripts"))
        from validate_example import validate_example

        example = {"id": "BAD", "text": "short", "label": "MAYBE"}
        errors = validate_example(example)
        assert len(errors) > 0

    def test_label_category_mismatch(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "data" / "scripts"))
        from validate_example import validate_example

        example = {
            "id": "DENY-education-0001",
            "text": "This is a long enough text to pass the minimum length validation requirement for the schema.",
            "label": "DENY",
            "category": "education",
            "subcategory": "tutoring",
            "difficulty": "easy",
            "reasoning": "This reasoning explains the label choice clearly.",
            "edge_case": False,
            "source_type": "synthetic",
            "metadata": {"generated_by": "test", "generation_date": "2026-03-05"},
        }
        errors = validate_example(example)
        assert any("not a DENY category" in e for e in errors)


class TestConsensus:
    def test_synthesize_verified(self):
        from src.grand_hillel.synthesizer import synthesize_claim

        verdicts = [
            {"verdict": "VERIFIED", "confidence": 0.9, "model": "claude"},
            {"verdict": "VERIFIED", "confidence": 0.85, "model": "gpt"},
            {"verdict": "VERIFIED", "confidence": 0.88, "model": "grok"},
            {"verdict": "PLAUSIBLE", "confidence": 0.7, "model": "deepseek"},
            {"verdict": "VERIFIED", "confidence": 0.92, "model": "gemini"},
        ]
        result = synthesize_claim("TEST-001", verdicts)
        assert result["consensus"] == "VERIFIED"
        assert result["action"] == "KEEP"

    def test_synthesize_investigate(self):
        from src.grand_hillel.synthesizer import synthesize_claim

        verdicts = [
            {"verdict": "VERIFIED", "confidence": 0.9, "model": "claude"},
            {"verdict": "WRONG", "confidence": 0.8, "model": "grok", "correction": "The real number is 42"},
            {"verdict": "VERIFIED", "confidence": 0.85, "model": "gpt"},
        ]
        result = synthesize_claim("TEST-002", verdicts)
        assert result["consensus"] == "INVESTIGATE"
        assert result["action"] == "INVESTIGATE"

    def test_synthesize_likely_wrong(self):
        from src.grand_hillel.synthesizer import synthesize_claim

        verdicts = [
            {"verdict": "WRONG", "confidence": 0.9, "model": "claude"},
            {"verdict": "WRONG", "confidence": 0.85, "model": "gpt"},
            {"verdict": "WRONG", "confidence": 0.88, "model": "grok"},
            {"verdict": "PLAUSIBLE", "confidence": 0.5, "model": "deepseek"},
        ]
        result = synthesize_claim("TEST-003", verdicts)
        assert result["consensus"] == "LIKELY_WRONG"
        assert result["action"] == "CORRECT"

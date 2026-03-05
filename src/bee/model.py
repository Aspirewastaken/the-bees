"""BeeModel — handles model loading, inference, and weight freezing.

The model is loaded once and frozen. No gradient computation, no weight updates,
no fine-tuning after deployment. This is the core invariant.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
from safetensors.torch import load_file, save_file
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

from src.bee.types import BeeConfig

logger = logging.getLogger(__name__)


class BeeModel:
    """A frozen binary classifier model.

    After loading, all parameters are frozen (requires_grad=False).
    The model cannot be modified, fine-tuned, or reward-hacked in deployment.
    """

    def __init__(self, config: BeeConfig):
        self.config = config
        self._model: Optional[nn.Module] = None
        self._tokenizer = None
        self._weight_hash: Optional[str] = None
        self._frozen = False

    @classmethod
    def from_pretrained(cls, model_path: str, config: Optional[BeeConfig] = None) -> BeeModel:
        """Load a pre-trained or fine-tuned Bee model."""
        if config is None:
            config = BeeConfig(model_name=model_path)
        instance = cls(config)
        instance._load_model(model_path)
        if config.frozen:
            instance.freeze()
        return instance

    @classmethod
    def from_base(cls, config: Optional[BeeConfig] = None) -> BeeModel:
        """Initialize from a base model (for training/fine-tuning)."""
        if config is None:
            config = BeeConfig(frozen=False)
        instance = cls(config)
        instance._load_model(config.model_name)
        return instance

    def _load_model(self, model_name_or_path: str) -> None:
        """Load model and tokenizer."""
        logger.info("Loading model: %s", model_name_or_path)

        path = Path(model_name_or_path)
        if path.exists() and (path / "config.json").exists():
            self._load_local(path)
        else:
            self._load_hub(model_name_or_path)

        if self.config.device != "cpu" and torch.cuda.is_available():
            self._model = self._model.to(self.config.device)
        elif self.config.device == "mps" and torch.backends.mps.is_available():
            self._model = self._model.to("mps")

        self._model.eval()
        logger.info("Model loaded: %d parameters", sum(p.numel() for p in self._model.parameters()))

    def _load_hub(self, model_name: str) -> None:
        """Load from HuggingFace Hub."""
        model_config = AutoConfig.from_pretrained(model_name)
        model_config.num_labels = 2
        model_config.id2label = {0: "APPROVE", 1: "DENY"}
        model_config.label2id = {"APPROVE": 0, "DENY": 1}

        self._model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            config=model_config,
            ignore_mismatched_sizes=True,
        )
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)

    def _load_local(self, path: Path) -> None:
        """Load from local directory."""
        self._model = AutoModelForSequenceClassification.from_pretrained(str(path))
        self._tokenizer = AutoTokenizer.from_pretrained(str(path))

    def freeze(self) -> str:
        """Freeze all weights. Returns the weight hash for verification.

        After freezing:
        - No parameter can be modified
        - No gradient can be computed
        - The model is locked to inference-only mode
        """
        if self._model is None:
            raise RuntimeError("No model loaded")

        for param in self._model.parameters():
            param.requires_grad = False

        self._model.eval()
        self._frozen = True
        self._weight_hash = self._compute_weight_hash()
        logger.info("Model frozen. Weight hash: %s", self._weight_hash)
        return self._weight_hash

    def verify_frozen(self) -> bool:
        """Verify that weights have not been modified since freezing."""
        if not self._frozen or self._weight_hash is None:
            return False
        return self._compute_weight_hash() == self._weight_hash

    def _compute_weight_hash(self) -> str:
        """Compute SHA-256 hash of all model weights for tamper detection."""
        hasher = hashlib.sha256()
        for name, param in sorted(self._model.named_parameters()):
            hasher.update(name.encode())
            hasher.update(param.data.cpu().numpy().tobytes())
        return hasher.hexdigest()[:16]

    @torch.no_grad()
    def classify(self, text: str) -> tuple[int, torch.Tensor]:
        """Run binary classification on input text.

        Returns:
            (predicted_label, logits) where label is 0=APPROVE, 1=DENY
        """
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("Model not loaded")
        if self._frozen and not self.verify_frozen():
            raise RuntimeError("Weight integrity check failed — weights modified after freeze")

        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            max_length=self.config.max_length,
            truncation=True,
            padding=True,
        )

        device = next(self._model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        outputs = self._model(**inputs)
        logits = outputs.logits.squeeze()
        probs = torch.softmax(logits, dim=-1)
        predicted = torch.argmax(probs).item()

        return predicted, probs

    def remove_generative_heads(self) -> None:
        """Strip all generative capability from the model.

        After this, the model can ONLY classify — it cannot produce text.
        This shrinks the attack surface.
        """
        if self._model is None:
            raise RuntimeError("No model loaded")

        for attr in ["lm_head", "cls", "decoder", "generator"]:
            if hasattr(self._model, attr) and attr != "classifier":
                delattr(self._model, attr)
                logger.info("Removed generative head: %s", attr)

        if hasattr(self._model, "config"):
            self._model.config.is_decoder = False
            self._model.config.is_encoder_decoder = False

        logger.info("Generative heads removed. Model is classification-only.")

    def save(self, output_dir: str) -> None:
        """Save model, tokenizer, and metadata."""
        if self._model is None or self._tokenizer is None:
            raise RuntimeError("No model loaded")

        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)

        self._model.save_pretrained(str(path))
        self._tokenizer.save_pretrained(str(path))

        weight_hash = self._compute_weight_hash()
        metadata = {
            "bee_id": self.config.bee_id,
            "bee_version": self.config.bee_version,
            "weight_hash": weight_hash,
            "frozen": self._frozen,
            "model_name": self.config.model_name,
            "num_parameters": sum(p.numel() for p in self._model.parameters()),
            "num_labels": 2,
            "labels": {0: "APPROVE", 1: "DENY"},
        }
        with open(path / "bee_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Model saved to %s (hash: %s)", output_dir, weight_hash)

    @property
    def model(self) -> nn.Module:
        if self._model is None:
            raise RuntimeError("No model loaded")
        return self._model

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            raise RuntimeError("No tokenizer loaded")
        return self._tokenizer

    @property
    def weight_hash(self) -> Optional[str]:
        return self._weight_hash

    @property
    def is_frozen(self) -> bool:
        return self._frozen

"""Training loop for Bee binary classifiers.

Trains a base model on the constitutional corpus, removes generative heads,
freezes weights, and saves the frozen Bee.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import torch
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from src.bee.model import BeeModel
from src.bee.types import BeeConfig
from src.training.dataset import BeeDataset, load_splits

logger = logging.getLogger(__name__)


class BeeTrainer:
    """Trains, freezes, and saves a Bee classifier.

    Two-phase approach from THE_BEE_SPEC:
    Phase 1: Language understanding (use pre-trained base model)
    Phase 2: Alignment specialization (fine-tune for binary classification)
    Post-training: Remove generative heads, freeze weights.
    """

    def __init__(
        self,
        base_model: str = "distilbert-base-uncased",
        output_dir: str = "output/bee-v1",
        corpus_dir: str = "data/corpus",
        max_length: int = 512,
        batch_size: int = 16,
        learning_rate: float = 2e-5,
        num_epochs: int = 3,
        device: str = "auto",
    ):
        self.base_model = base_model
        self.output_dir = Path(output_dir)
        self.corpus_dir = corpus_dir
        self.max_length = max_length
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.num_epochs = num_epochs

        if device == "auto":
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device

    def train(self, bee_id: str = "bee-v1", bee_version: str = "0.1.0") -> BeeModel:
        """Full training pipeline: load, fine-tune, strip, freeze, save."""
        logger.info("=== BEE TRAINING: %s v%s ===", bee_id, bee_version)
        logger.info("Base model: %s", self.base_model)
        logger.info("Device: %s", self.device)

        logger.info("Loading tokenizer and model...")
        tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        model = AutoModelForSequenceClassification.from_pretrained(
            self.base_model,
            num_labels=2,
            id2label={0: "APPROVE", 1: "DENY"},
            label2id={"APPROVE": 0, "DENY": 1},
            ignore_mismatched_sizes=True,
        )

        logger.info("Loading training data from %s...", self.corpus_dir)
        splits = load_splits(self.corpus_dir, tokenizer, self.max_length)
        if "train" not in splits:
            raise FileNotFoundError(f"No train.jsonl in {self.corpus_dir}")

        train_dataset = splits["train"]
        eval_dataset = splits.get("val")

        logger.info("Train: %d examples, Val: %d examples",
                     len(train_dataset),
                     len(eval_dataset) if eval_dataset else 0)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        training_args = TrainingArguments(
            output_dir=str(self.output_dir / "checkpoints"),
            num_train_epochs=self.num_epochs,
            per_device_train_batch_size=self.batch_size,
            per_device_eval_batch_size=self.batch_size,
            learning_rate=self.learning_rate,
            weight_decay=0.01,
            eval_strategy="epoch" if eval_dataset else "no",
            save_strategy="epoch",
            load_best_model_at_end=bool(eval_dataset),
            metric_for_best_model="eval_loss" if eval_dataset else None,
            logging_dir=str(self.output_dir / "logs"),
            logging_steps=50,
            report_to="none",
            fp16=self.device == "cuda",
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
        )

        logger.info("Starting fine-tuning...")
        trainer.train()

        if eval_dataset:
            metrics = trainer.evaluate()
            logger.info("Eval metrics: %s", metrics)

        logger.info("Wrapping in BeeModel...")
        config = BeeConfig(
            model_name=self.base_model,
            max_length=self.max_length,
            device=self.device,
            bee_id=bee_id,
            bee_version=bee_version,
            frozen=False,
        )
        bee_model = BeeModel(config)
        bee_model._model = trainer.model
        bee_model._tokenizer = tokenizer

        logger.info("Removing generative heads...")
        bee_model.remove_generative_heads()

        logger.info("Freezing weights...")
        weight_hash = bee_model.freeze()

        save_path = str(self.output_dir / "frozen")
        logger.info("Saving frozen Bee to %s...", save_path)
        bee_model.save(save_path)

        logger.info("=== TRAINING COMPLETE ===")
        logger.info("Bee ID: %s", bee_id)
        logger.info("Version: %s", bee_version)
        logger.info("Weight hash: %s", weight_hash)
        logger.info("Frozen: %s", bee_model.is_frozen)
        logger.info("Saved to: %s", save_path)

        return bee_model


def train_multiple_bees(
    base_models: list[str],
    corpus_dir: str = "data/corpus",
    output_base: str = "output",
    **kwargs,
) -> list[BeeModel]:
    """Train multiple independent Bees for the Hive.

    Each Bee uses a different base model to ensure independent failure modes.
    """
    bees = []
    for i, base_model in enumerate(base_models):
        bee_id = f"bee-v{i + 1}"
        output_dir = f"{output_base}/{bee_id}"
        trainer = BeeTrainer(
            base_model=base_model,
            output_dir=output_dir,
            corpus_dir=corpus_dir,
            **kwargs,
        )
        bee = trainer.train(bee_id=bee_id)
        bees.append(bee)
        logger.info("Trained %s from %s", bee_id, base_model)

    logger.info("Trained %d independent Bees", len(bees))
    return bees

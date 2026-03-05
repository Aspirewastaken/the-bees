"""Dataset management for Bee classifier training.

Loads the assembled corpus and prepares it for HuggingFace Trainer.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import torch
from torch.utils.data import Dataset

logger = logging.getLogger(__name__)

LABEL_MAP = {"APPROVE": 0, "DENY": 1}


class BeeDataset(Dataset):
    """PyTorch Dataset for Bee binary classification training."""

    def __init__(self, jsonl_path: str, tokenizer, max_length: int = 512):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.examples = []

        path = Path(jsonl_path)
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ex = json.loads(line)
                if ex["label"] in LABEL_MAP:
                    self.examples.append(ex)

        logger.info("Loaded %d examples from %s", len(self.examples), path.name)

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> dict:
        ex = self.examples[idx]
        encoding = self.tokenizer(
            ex["text"],
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "labels": torch.tensor(LABEL_MAP[ex["label"]], dtype=torch.long),
        }

    @property
    def label_counts(self) -> dict[str, int]:
        counts = {"APPROVE": 0, "DENY": 0}
        for ex in self.examples:
            counts[ex["label"]] = counts.get(ex["label"], 0) + 1
        return counts


def load_splits(
    corpus_dir: str,
    tokenizer,
    max_length: int = 512,
) -> dict[str, BeeDataset]:
    """Load train/val/test splits from the corpus directory."""
    path = Path(corpus_dir)
    splits = {}
    for name in ["train", "val", "test"]:
        jsonl = path / f"{name}.jsonl"
        if jsonl.exists():
            splits[name] = BeeDataset(str(jsonl), tokenizer, max_length)
        else:
            logger.warning("Split not found: %s", jsonl)
    return splits

#!/usr/bin/env python3
"""CLI entry point for The Bees.

Commands:
    bee classify     — Run a Bee classifier on text
    bee hive         — Run the Hive (multi-bee voting) on text
    bee train        — Train a new Bee from the corpus
    bee verify       — Run Grand Hillel verification pipeline
    bee validate     — Validate training data files
    bee info         — Show Bee/Hive status and metadata
"""

import asyncio
import json
import logging
import sys

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool):
    """The Bees — Frozen binary alignment classifiers."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")


@cli.command()
@click.argument("text")
@click.option("--model", "-m", default="distilbert-base-uncased", help="Base model name or path to trained Bee")
@click.option("--threshold", "-t", default=0.5, type=float, help="DENY threshold")
def classify(text: str, model: str, threshold: float):
    """Classify a single text as APPROVE or DENY."""
    from src.bee.classifier import BeeClassifier
    from src.bee.types import BeeConfig

    config = BeeConfig(model_name=model, threshold=threshold)
    bee = BeeClassifier.from_base_model(config)
    result = bee.classify(text)

    color = "green" if result.is_approved else "red"
    console.print(f"\n[bold {color}]{result.verdict.value}[/bold {color}]")
    console.print(f"Confidence: {result.confidence:.3f}")
    console.print(f"Bee: {result.bee_id} (hash: {bee.model.weight_hash})")
    if result.raw_logits:
        console.print(f"Logits: APPROVE={result.raw_logits['APPROVE']:.3f} DENY={result.raw_logits['DENY']:.3f}")


@cli.command()
@click.argument("text")
@click.option("--models", "-m", multiple=True, default=["distilbert-base-uncased"],
              help="Base model names (specify multiple for independent Bees)")
@click.option("--threshold", "-t", default=0.5, type=float)
@click.option("--unanimous", is_flag=True, help="Require unanimous APPROVE")
def hive(text: str, models: tuple, threshold: float, unanimous: bool):
    """Run the Hive (multi-bee voting) on text."""
    from src.hive.swarm import Hive

    hive_instance = Hive.from_base_models(list(models))
    result = hive_instance.classify(text)

    color = "green" if result.verdict.value == "APPROVE" else "red"
    console.print(f"\n[bold {color}]HIVE: {result.verdict.value}[/bold {color}]")
    console.print(f"Consensus: {result.consensus_strength:.0%} ({result.vote_count})")
    console.print(f"Confidence: {result.confidence:.3f}")

    table = Table(title="Individual Bee Votes")
    table.add_column("Bee")
    table.add_column("Verdict")
    table.add_column("Confidence")

    for r in result.individual_results:
        v_color = "green" if r.is_approved else "red"
        table.add_row(r.bee_id, f"[{v_color}]{r.verdict.value}[/{v_color}]", f"{r.confidence:.3f}")

    console.print(table)


@cli.command()
@click.option("--base-model", "-b", default="distilbert-base-uncased", help="Base model to fine-tune")
@click.option("--corpus-dir", "-c", default="data/corpus", help="Path to training corpus")
@click.option("--output-dir", "-o", default="output/bee-v1", help="Output directory")
@click.option("--epochs", "-e", default=3, type=int, help="Training epochs")
@click.option("--batch-size", default=16, type=int)
@click.option("--lr", default=2e-5, type=float, help="Learning rate")
@click.option("--bee-id", default="bee-v1")
def train(base_model: str, corpus_dir: str, output_dir: str, epochs: int, batch_size: int, lr: float, bee_id: str):
    """Train a new Bee classifier on the corpus."""
    from src.training.trainer import BeeTrainer

    trainer = BeeTrainer(
        base_model=base_model,
        output_dir=output_dir,
        corpus_dir=corpus_dir,
        num_epochs=epochs,
        batch_size=batch_size,
        learning_rate=lr,
    )
    bee = trainer.train(bee_id=bee_id)
    console.print(f"\n[green]Training complete.[/green]")
    console.print(f"Bee: {bee_id} | Hash: {bee.weight_hash} | Frozen: {bee.is_frozen}")


@cli.command()
@click.argument("document_paths", nargs=-1, required=True)
@click.option("--output-dir", "-o", default="grand_hillel", help="Output directory")
def verify(document_paths: tuple, output_dir: str):
    """Run Grand Hillel multi-model verification on documents."""
    from src.grand_hillel.pipeline import run_grand_hillel

    result = asyncio.run(run_grand_hillel(list(document_paths), output_dir))
    console.print(f"\n[green]Verification complete.[/green]")
    console.print(f"Claims: {result['claims']}")
    console.print(f"Report: {result['report']}")
    console.print(f"Summary: {result['summary']}")


@cli.command()
@click.argument("filepath")
@click.option("--strict", is_flag=True, help="Fail on near-duplicates")
def validate(filepath: str, strict: bool):
    """Validate a JSONL training data file."""
    sys.path.insert(0, "data/scripts")
    from validate_file import validate_file

    report = validate_file(filepath, strict=strict)

    if report.get("all_pass"):
        console.print(f"\n[green]PASS[/green] — {report['total_examples']} examples valid")
    else:
        console.print(f"\n[red]FAIL[/red] — {report['invalid']} invalid, {report['duplicate_ids']} duplicate IDs")

    console.print(json.dumps(report, indent=2))


@cli.command()
@click.option("--model", "-m", help="Path to trained Bee")
def info(model: str):
    """Show status and metadata."""
    if model:
        from src.bee.classifier import BeeClassifier
        bee = BeeClassifier.load(model)
        console.print(json.dumps(bee.info, indent=2))
    else:
        console.print("[bold]The Bees[/bold] — Frozen binary alignment classifiers")
        console.print("Run 'bee --help' for available commands")


if __name__ == "__main__":
    cli()

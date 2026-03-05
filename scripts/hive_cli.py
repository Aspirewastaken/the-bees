#!/usr/bin/env python3
"""Utility CLI for launch-ready Hive corpus operations."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


EXAMPLE_REQUIRED = {
    "id",
    "decision",
    "category",
    "user_prompt",
    "model_output",
    "label_rationale",
    "policy_tags",
    "generator_team",
    "generator_vm",
    "created_at_utc",
    "needs_human_review",
}

VERDICT_REQUIRED = {
    "example_id",
    "verdict",
    "reason",
    "scout_vm",
    "verified_at_utc",
}

ALLOWED_DECISIONS = {"APPROVE", "DENY"}
ALLOWED_GENERATOR_TEAMS = {"WORKER-DENY", "WORKER-APPROVE"}
ALLOWED_VERDICTS = {"APPROVE_RECORD", "REJECT_RECORD", "EDIT_REQUIRED"}


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        for idx, raw_line in enumerate(fh, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                yield idx, json.loads(line), None
            except json.JSONDecodeError as exc:  # pragma: no cover - parser branch
                yield idx, None, str(exc)


def _is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_iso8601(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    candidate = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(candidate)
        return True
    except ValueError:
        return False


def _categories_by_decision(categories_file: Path) -> dict[str, set[str]]:
    payload = _read_json(categories_file)
    return {
        "APPROVE": set(payload.get("approve_categories", [])),
        "DENY": set(payload.get("deny_categories", [])),
    }


def _validate_example(
    record: dict[str, Any],
    categories: dict[str, set[str]],
    expected_decision: str | None = None,
    expected_category: str | None = None,
) -> list[str]:
    errors: list[str] = []

    missing = EXAMPLE_REQUIRED - set(record)
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")
        return errors

    for field in (
        "id",
        "category",
        "user_prompt",
        "model_output",
        "label_rationale",
        "generator_team",
        "generator_vm",
        "created_at_utc",
    ):
        if not _is_non_empty_str(record.get(field)):
            errors.append(f"{field} must be a non-empty string")

    decision = record.get("decision")
    if decision not in ALLOWED_DECISIONS:
        errors.append("decision must be APPROVE or DENY")

    category = record.get("category")
    if isinstance(decision, str) and decision in categories:
        if category not in categories[decision]:
            errors.append(
                f"category '{category}' is not valid for decision '{decision}'"
            )

    if expected_decision and decision != expected_decision:
        errors.append(
            f"decision mismatch: expected {expected_decision}, got {decision}"
        )

    if expected_category and category != expected_category:
        errors.append(
            f"category mismatch: expected {expected_category}, got {category}"
        )

    team = record.get("generator_team")
    if team not in ALLOWED_GENERATOR_TEAMS:
        errors.append("generator_team must be WORKER-DENY or WORKER-APPROVE")

    policy_tags = record.get("policy_tags")
    if not isinstance(policy_tags, list) or not all(
        isinstance(item, str) and item.strip() for item in policy_tags
    ):
        errors.append("policy_tags must be a list of non-empty strings")

    needs_review = record.get("needs_human_review")
    if not isinstance(needs_review, bool):
        errors.append("needs_human_review must be boolean")

    if not _is_iso8601(record.get("created_at_utc")):
        errors.append("created_at_utc must be ISO-8601")

    return errors


def _validate_verdict(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = VERDICT_REQUIRED - set(record)
    if missing:
        errors.append(f"missing fields: {sorted(missing)}")
        return errors

    for field in ("example_id", "reason", "scout_vm", "verified_at_utc"):
        if not _is_non_empty_str(record.get(field)):
            errors.append(f"{field} must be a non-empty string")

    verdict = record.get("verdict")
    if verdict not in ALLOWED_VERDICTS:
        errors.append(f"verdict must be one of {sorted(ALLOWED_VERDICTS)}")

    if not _is_iso8601(record.get("verified_at_utc")):
        errors.append("verified_at_utc must be ISO-8601")

    return errors


def cmd_preflight(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    required_paths = [
        root / "docs" / "THE_HIVE_BUILD.md",
        root / "hive" / "README.md",
        root / "hive" / "config" / "categories.json",
        root / "hive" / "config" / "model_pool.json",
        root / "hive" / "schemas" / "bee_example.schema.json",
        root / "hive" / "schemas" / "scout_verdict.schema.json",
        root / "hive" / "prompts" / "worker_deny.md",
        root / "hive" / "prompts" / "worker_approve.md",
        root / "hive" / "prompts" / "scout.md",
        root / "scripts" / "hive_cli.py",
    ]

    missing = [str(path.relative_to(root)) for path in required_paths if not path.exists()]
    if missing:
        print("PRECHECK_FAILED")
        print(json.dumps({"missing_paths": missing}, indent=2))
        return 2

    categories = _read_json(root / "hive" / "config" / "categories.json")
    deny = categories.get("deny_categories", [])
    approve = categories.get("approve_categories", [])

    issues: list[str] = []
    if len(deny) != len(set(deny)):
        issues.append("duplicate values in deny_categories")
    if len(approve) != len(set(approve)):
        issues.append("duplicate values in approve_categories")
    overlap = sorted(set(deny).intersection(set(approve)))
    if overlap:
        issues.append(f"category overlap across approve/deny: {overlap}")

    if issues:
        print("PRECHECK_FAILED")
        print(json.dumps({"issues": issues}, indent=2))
        return 2

    print("PRECHECK_OK")
    print(
        json.dumps(
            {
                "root": str(root),
                "approve_categories": len(approve),
                "deny_categories": len(deny),
                "timestamp_utc": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
    )
    return 0


def _default_worker_output(decision: str, category: str) -> str:
    label = "approve" if decision == "APPROVE" else "deny"
    return f"hive/work/{label}/{category}/records_{category}.jsonl"


def cmd_make_manifests(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    categories_path = root / "hive" / "config" / "categories.json"
    categories = _read_json(categories_path)
    run_id = args.run_id or datetime.now(UTC).strftime("run_%Y%m%dT%H%M%SZ")

    approve_categories = categories.get("approve_categories", [])
    deny_categories = categories.get("deny_categories", [])
    target_records = args.records_per_worker

    worker_assignments: list[dict[str, Any]] = []
    counter = 1
    for category in deny_categories:
        worker_assignments.append(
            {
                "worker_id": f"W{counter:03d}",
                "team": "WORKER-DENY",
                "decision": "DENY",
                "category": category,
                "target_records": target_records,
                "output_path": _default_worker_output("DENY", category),
                "run_id": run_id,
            }
        )
        counter += 1
    for category in approve_categories:
        worker_assignments.append(
            {
                "worker_id": f"W{counter:03d}",
                "team": "WORKER-APPROVE",
                "decision": "APPROVE",
                "category": category,
                "target_records": target_records,
                "output_path": _default_worker_output("APPROVE", category),
                "run_id": run_id,
            }
        )
        counter += 1

    scout_assignments: list[dict[str, Any]] = []
    for idx, worker in enumerate(worker_assignments, start=1):
        scout_assignments.append(
            {
                "scout_id": f"S{idx:03d}",
                "assigned_worker_id": worker["worker_id"],
                "decision": worker["decision"],
                "category": worker["category"],
                "worker_output_path": worker["output_path"],
                "scout_output_path": (
                    f"hive/scout_reports/{worker['worker_id']}_{worker['category']}.jsonl"
                ),
                "run_id": run_id,
            }
        )

    workers_manifest = {
        "run_id": run_id,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "records_per_worker": target_records,
        "workers": worker_assignments,
    }
    scouts_manifest = {
        "run_id": run_id,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scouts": scout_assignments,
    }

    workers_path = root / "hive" / "config" / "workers_manifest.json"
    scouts_path = root / "hive" / "config" / "scouts_manifest.json"

    if (workers_path.exists() or scouts_path.exists()) and not args.overwrite:
        print("Refusing to overwrite existing manifests. Use --overwrite.")
        return 2

    workers_path.write_text(
        json.dumps(workers_manifest, indent=2) + "\n", encoding="utf-8"
    )
    scouts_path.write_text(
        json.dumps(scouts_manifest, indent=2) + "\n", encoding="utf-8"
    )

    result = {
        "run_id": run_id,
        "workers_manifest": str(workers_path.relative_to(root)),
        "scouts_manifest": str(scouts_path.relative_to(root)),
        "worker_assignments": len(worker_assignments),
    }
    print(json.dumps(result, indent=2))
    return 0


def cmd_validate_shard(args: argparse.Namespace) -> int:
    records_path = Path(args.records).resolve()
    categories_path = Path(args.categories).resolve()
    categories = _categories_by_decision(categories_path)

    errors: list[dict[str, Any]] = []
    total = 0
    for line_no, record, decode_error in _iter_jsonl(records_path):
        total += 1
        if decode_error:
            errors.append({"line": line_no, "errors": [f"json decode error: {decode_error}"]})
            continue
        assert isinstance(record, dict)
        record_errors = _validate_example(
            record,
            categories,
            expected_decision=args.expected_decision,
            expected_category=args.expected_category,
        )
        if record_errors:
            errors.append({"line": line_no, "id": record.get("id"), "errors": record_errors})

    summary = {
        "records_file": str(records_path),
        "total_records": total,
        "error_count": len(errors),
        "errors": errors[: args.max_errors],
    }
    print(json.dumps(summary, indent=2))

    return 0 if not errors else 2


def _record_signature(record: dict[str, Any]) -> str:
    return "||".join(
        [
            record.get("decision", "").strip().upper(),
            record.get("category", "").strip().lower(),
            record.get("user_prompt", "").strip().lower(),
            record.get("model_output", "").strip().lower(),
        ]
    )


def cmd_assemble(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    work_root = root / "hive" / "work"
    scout_root = root / "hive" / "scout_reports"
    output_file = root / args.output
    summary_file = root / args.summary

    categories = _categories_by_decision(root / "hive" / "config" / "categories.json")

    worker_files = sorted(work_root.rglob("*.jsonl"))
    scout_files = sorted(scout_root.rglob("*.jsonl"))

    examples_by_id: dict[str, dict[str, Any]] = {}
    duplicate_ids = 0
    invalid_examples = 0
    total_examples = 0

    for path in worker_files:
        for line_no, record, decode_error in _iter_jsonl(path):
            total_examples += 1
            if decode_error:
                invalid_examples += 1
                continue
            assert isinstance(record, dict)
            errs = _validate_example(record, categories)
            if errs:
                invalid_examples += 1
                continue
            rid = record["id"]
            if rid in examples_by_id:
                duplicate_ids += 1
                continue
            examples_by_id[rid] = record

    verdicts_by_example: dict[str, set[str]] = defaultdict(set)
    invalid_verdicts = 0
    total_verdicts = 0
    for path in scout_files:
        for _, record, decode_error in _iter_jsonl(path):
            total_verdicts += 1
            if decode_error:
                invalid_verdicts += 1
                continue
            assert isinstance(record, dict)
            errs = _validate_verdict(record)
            if errs:
                invalid_verdicts += 1
                continue
            verdicts_by_example[record["example_id"]].add(record["verdict"])

    approved_records: list[dict[str, Any]] = []
    conflicting_verdicts = 0
    missing_verdict = 0
    for example_id, record in examples_by_id.items():
        verdicts = verdicts_by_example.get(example_id)
        if not verdicts:
            missing_verdict += 1
            continue
        if len(verdicts) > 1:
            conflicting_verdicts += 1
            continue
        only_verdict = next(iter(verdicts))
        if only_verdict == "APPROVE_RECORD":
            approved_records.append(record)

    deduped: list[dict[str, Any]] = []
    seen_signatures: set[str] = set()
    dropped_as_duplicates = 0
    for record in approved_records:
        sig = _record_signature(record)
        if sig in seen_signatures:
            dropped_as_duplicates += 1
            continue
        seen_signatures.add(sig)
        deduped.append(record)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as fh:
        for record in deduped:
            fh.write(json.dumps(record, ensure_ascii=True) + "\n")

    by_decision = Counter(r["decision"] for r in deduped)
    by_category = Counter(r["category"] for r in deduped)

    summary = {
        "assembled_at_utc": datetime.now(UTC).isoformat(),
        "worker_files": len(worker_files),
        "scout_files": len(scout_files),
        "total_worker_records": total_examples,
        "valid_unique_worker_records": len(examples_by_id),
        "invalid_worker_records": invalid_examples,
        "duplicate_worker_ids_skipped": duplicate_ids,
        "total_scout_verdicts": total_verdicts,
        "invalid_scout_verdicts": invalid_verdicts,
        "records_missing_verdict": missing_verdict,
        "records_with_conflicting_verdicts": conflicting_verdicts,
        "approved_before_dedupe": len(approved_records),
        "dropped_as_near_duplicates": dropped_as_duplicates,
        "final_records": len(deduped),
        "final_by_decision": dict(by_decision),
        "final_by_category": dict(by_category),
        "output_file": str(output_file.relative_to(root)),
    }

    summary_file.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    work_root = root / "hive" / "work"
    scout_root = root / "hive" / "scout_reports"

    worker_files = sorted(work_root.rglob("*.jsonl"))
    scout_files = sorted(scout_root.rglob("*.jsonl"))

    worker_counts: dict[str, int] = {}
    total_worker_records = 0
    for path in worker_files:
        count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        worker_counts[str(path.relative_to(root))] = count
        total_worker_records += count

    scout_counts: dict[str, int] = {}
    total_scout_records = 0
    for path in scout_files:
        count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        scout_counts[str(path.relative_to(root))] = count
        total_scout_records += count

    payload = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "worker_files": len(worker_files),
        "scout_files": len(scout_files),
        "total_worker_records": total_worker_records,
        "total_scout_verdicts": total_scout_records,
        "worker_counts": worker_counts,
        "scout_counts": scout_counts,
    }
    print(json.dumps(payload, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hive run orchestration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser(
        "preflight", help="Validate launch-critical files and config"
    )
    preflight.add_argument("--root", default=".", help="Repository root")
    preflight.set_defaults(func=cmd_preflight)

    make_manifests = subparsers.add_parser(
        "make-manifests", help="Generate workers/scouts manifests for a run"
    )
    make_manifests.add_argument("--root", default=".", help="Repository root")
    make_manifests.add_argument("--run-id", default=None, help="Run identifier")
    make_manifests.add_argument(
        "--records-per-worker",
        type=int,
        default=500,
        help="Target records each worker should produce",
    )
    make_manifests.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing manifests",
    )
    make_manifests.set_defaults(func=cmd_make_manifests)

    validate = subparsers.add_parser(
        "validate-shard", help="Validate a worker shard JSONL file"
    )
    validate.add_argument("--records", required=True, help="Path to shard JSONL")
    validate.add_argument(
        "--categories",
        default="hive/config/categories.json",
        help="Path to categories JSON",
    )
    validate.add_argument(
        "--expected-decision",
        choices=sorted(ALLOWED_DECISIONS),
        default=None,
    )
    validate.add_argument("--expected-category", default=None)
    validate.add_argument(
        "--max-errors",
        type=int,
        default=50,
        help="Maximum detailed errors to print",
    )
    validate.set_defaults(func=cmd_validate_shard)

    assemble = subparsers.add_parser(
        "assemble",
        help="Assemble final corpus from worker shards and scout verdicts",
    )
    assemble.add_argument("--root", default=".", help="Repository root")
    assemble.add_argument(
        "--output",
        default="hive/final/bee_corpus_v1.jsonl",
        help="Output JSONL path relative to root",
    )
    assemble.add_argument(
        "--summary",
        default="hive/final/bee_corpus_v1_summary.json",
        help="Summary JSON path relative to root",
    )
    assemble.set_defaults(func=cmd_assemble)

    status = subparsers.add_parser(
        "status", help="Show current progress counts from work/scout folders"
    )
    status.add_argument("--root", default=".", help="Repository root")
    status.set_defaults(func=cmd_status)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

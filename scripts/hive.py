#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
HIVE_DIR = REPO_ROOT / "hive"
SCHEMA_DIR = HIVE_DIR / "schema"
SUBMISSIONS_DIR = HIVE_DIR / "submissions"
VERIFICATIONS_DIR = HIVE_DIR / "verifications"
CORPUS_DIR = HIVE_DIR / "corpus"

CATEGORIES_FILE = SCHEMA_DIR / "categories_v1.json"

ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SUBMISSION_DIR_RE = re.compile(r"^subm_[0-9a-f]{32}$")

# Very lightweight "non-actionable" lint for the highest-risk DENY categories.
# This is intentionally conservative (it will produce false positives) because
# we do not want an open repo to contain executable harm instructions.
HIGH_RISK_DENY_CATEGORIES = {"biosecurity", "weapons", "cybersecurity", "child_safety", "self_harm"}
CODE_FENCE_RE = re.compile(r"```")
STEP_LIST_RE = re.compile(r"(?im)^\s*(step\s*\d+|[0-9]{1,2}[.)])\s+")

EXCLUSION_REASON_CODES = {
    "actionable_harm",
    "ambiguous",
    "unsafe_language",
    "slur_unredacted",
    "child_sexual_content",
}


@dataclass(frozen=True)
class Issue:
    path: str
    message: str

    def render(self) -> str:
        return f"{self.path}: {self.message}"


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")


def _is_iso_utc(ts: Any) -> bool:
    if not isinstance(ts, str) or not ISO_UTC_RE.match(ts):
        return False
    try:
        datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def _require_token(name: str, value: Any) -> str | None:
    if not isinstance(value, str) or not SAFE_TOKEN_RE.match(value):
        return f"{name} must match {SAFE_TOKEN_RE.pattern}"
    return None


def _iter_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"invalid JSON on line {line_no}: {e.msg}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"line {line_no}: expected JSON object, got {type(obj).__name__}")
            yield line_no, obj


def _load_categories(issues: list[Issue]) -> dict[str, dict[str, Any]]:
    if not CATEGORIES_FILE.exists():
        issues.append(Issue(str(CATEGORIES_FILE), "missing categories file"))
        return {}
    try:
        data = _load_json(CATEGORIES_FILE)
    except Exception as e:  # noqa: BLE001
        issues.append(Issue(str(CATEGORIES_FILE), f"failed to parse JSON: {e}"))
        return {}

    if not isinstance(data, dict):
        issues.append(Issue(str(CATEGORIES_FILE), "expected JSON object at top-level"))
        return {}
    categories = data.get("categories")
    if not isinstance(categories, list):
        issues.append(Issue(str(CATEGORIES_FILE), "expected `categories` to be a list"))
        return {}

    by_id: dict[str, dict[str, Any]] = {}
    for idx, cat in enumerate(categories):
        if not isinstance(cat, dict):
            issues.append(Issue(str(CATEGORIES_FILE), f"categories[{idx}] must be an object"))
            continue
        cid = cat.get("id")
        if not isinstance(cid, str) or not cid:
            issues.append(Issue(str(CATEGORIES_FILE), f"categories[{idx}].id must be a non-empty string"))
            continue
        if cid in by_id:
            issues.append(Issue(str(CATEGORIES_FILE), f"duplicate category id: {cid}"))
            continue
        by_id[cid] = cat
    return by_id


def validate_repo() -> int:
    issues: list[Issue] = []
    categories_by_id = _load_categories(issues)
    category_ids = set(categories_by_id.keys())

    if not SUBMISSIONS_DIR.exists():
        issues.append(Issue(str(SUBMISSIONS_DIR), "missing submissions directory"))
        category_ids = category_ids  # keep mypy calm

    submissions: dict[str, dict[str, Any]] = {}
    submission_examples: dict[str, dict[str, dict[str, Any]]] = {}
    example_global_index: dict[str, str] = {}  # example id -> submission_id

    # --- Validate submissions ---
    if SUBMISSIONS_DIR.exists():
        for sub_dir in sorted([p for p in SUBMISSIONS_DIR.iterdir() if p.is_dir()], key=lambda p: p.name):
            sub_id = sub_dir.name
            if not SUBMISSION_DIR_RE.match(sub_id):
                issues.append(Issue(str(sub_dir), "submission dir must be named subm_<32hex>"))
                continue

            submission_json_path = sub_dir / "submission.json"
            examples_path = sub_dir / "examples.jsonl"

            if not submission_json_path.exists():
                issues.append(Issue(str(submission_json_path), "missing file"))
                continue
            if not examples_path.exists():
                issues.append(Issue(str(examples_path), "missing file"))
                continue

            try:
                meta = _load_json(submission_json_path)
            except Exception as e:  # noqa: BLE001
                issues.append(Issue(str(submission_json_path), f"failed to parse JSON: {e}"))
                continue
            if not isinstance(meta, dict):
                issues.append(Issue(str(submission_json_path), "must be a JSON object"))
                continue

            # required fields
            if meta.get("format") != "hive_submission_v1":
                issues.append(Issue(str(submission_json_path), 'format must be "hive_submission_v1"'))

            if meta.get("submission_id") != sub_id:
                issues.append(Issue(str(submission_json_path), f"submission_id must equal directory name ({sub_id})"))

            for field in ("team_id",):
                err = _require_token(field, meta.get(field))
                if err:
                    issues.append(Issue(str(submission_json_path), err))

            label = meta.get("label")
            if label not in ("APPROVE", "DENY"):
                issues.append(Issue(str(submission_json_path), "label must be APPROVE or DENY"))

            category = meta.get("category")
            if not isinstance(category, str) or category not in category_ids:
                issues.append(Issue(str(submission_json_path), "category must be one of hive/schema/categories_v1.json IDs"))

            created_at = meta.get("created_at")
            if not _is_iso_utc(created_at):
                issues.append(Issue(str(submission_json_path), "created_at must be ISO-8601 UTC like 2026-03-05T04:20:00Z"))

            submissions[sub_id] = meta
            submission_examples[sub_id] = {}

            # examples.jsonl
            try:
                for line_no, ex in _iter_jsonl(examples_path):
                    ex_path = f"{examples_path}:{line_no}"
                    ex_id = ex.get("id")
                    if not isinstance(ex_id, str) or not ex_id.strip():
                        issues.append(Issue(ex_path, "id must be a non-empty string"))
                        continue
                    if ex_id in submission_examples[sub_id]:
                        issues.append(Issue(ex_path, f"duplicate id within submission: {ex_id}"))
                    if ex_id in example_global_index and example_global_index[ex_id] != sub_id:
                        issues.append(Issue(ex_path, f"duplicate id across submissions: already in {example_global_index[ex_id]}"))
                    else:
                        example_global_index[ex_id] = sub_id

                    ex_label = ex.get("label")
                    if ex_label != label:
                        issues.append(Issue(ex_path, f"label must match submission label ({label})"))

                    ex_category = ex.get("category")
                    if ex_category != category:
                        issues.append(Issue(ex_path, f"category must match submission category ({category})"))

                    text = ex.get("text")
                    if not isinstance(text, str) or not text.strip():
                        issues.append(Issue(ex_path, "text must be a non-empty string"))
                    else:
                        if label == "DENY" and isinstance(ex_category, str) and ex_category in HIGH_RISK_DENY_CATEGORIES:
                            if CODE_FENCE_RE.search(text):
                                issues.append(Issue(ex_path, "DENY example contains code fence (```); must be redacted/non-actionable"))
                            if STEP_LIST_RE.search(text):
                                issues.append(Issue(ex_path, "DENY example looks like step-by-step instructions; must be non-actionable"))

                    gen_at = ex.get("generated_at")
                    if not _is_iso_utc(gen_at):
                        issues.append(Issue(ex_path, "generated_at must be ISO-8601 UTC like 2026-03-05T04:20:00Z"))

                    # optional fields type checks
                    model = ex.get("model")
                    if model is not None and not isinstance(model, str):
                        issues.append(Issue(ex_path, "model must be a string if present"))

                    difficulty = ex.get("difficulty")
                    if difficulty is not None and difficulty not in ("easy", "medium", "hard"):
                        issues.append(Issue(ex_path, "difficulty must be easy|medium|hard if present"))

                    tags = ex.get("tags")
                    if tags is not None and (not isinstance(tags, list) or not all(isinstance(t, str) for t in tags)):
                        issues.append(Issue(ex_path, "tags must be an array of strings if present"))

                    submission_examples[sub_id][ex_id] = ex
            except ValueError as e:
                issues.append(Issue(str(examples_path), str(e)))
                continue

    # --- Validate verifications ---
    if VERIFICATIONS_DIR.exists():
        for sub_root in sorted([p for p in VERIFICATIONS_DIR.iterdir() if p.is_dir()], key=lambda p: p.name):
            sub_id = sub_root.name
            if sub_id not in submissions:
                issues.append(Issue(str(sub_root), f"verification refers to missing submission: {sub_id}"))
                continue

            for scout_dir in sorted([p for p in sub_root.iterdir() if p.is_dir()], key=lambda p: p.name):
                scout_dir_name = scout_dir.name
                if not scout_dir_name.startswith("scout_"):
                    issues.append(Issue(str(scout_dir), "scout dir must be named scout_<scout_id>"))
                    continue
                scout_id = scout_dir_name[len("scout_") :]
                err = _require_token("scout_id", scout_id)
                if err:
                    issues.append(Issue(str(scout_dir), err))
                    continue

                verification_json_path = scout_dir / "verification.json"
                verdicts_path = scout_dir / "verdicts.jsonl"
                if not verification_json_path.exists():
                    issues.append(Issue(str(verification_json_path), "missing file"))
                    continue
                if not verdicts_path.exists():
                    issues.append(Issue(str(verdicts_path), "missing file"))
                    continue

                try:
                    vmeta = _load_json(verification_json_path)
                except Exception as e:  # noqa: BLE001
                    issues.append(Issue(str(verification_json_path), f"failed to parse JSON: {e}"))
                    continue
                if not isinstance(vmeta, dict):
                    issues.append(Issue(str(verification_json_path), "must be a JSON object"))
                    continue
                if vmeta.get("format") != "hive_verification_v1":
                    issues.append(Issue(str(verification_json_path), 'format must be "hive_verification_v1"'))
                if vmeta.get("submission_id") != sub_id:
                    issues.append(Issue(str(verification_json_path), f"submission_id must be {sub_id}"))
                if vmeta.get("scout_id") != scout_id:
                    issues.append(Issue(str(verification_json_path), f"scout_id must be {scout_id}"))
                if not _is_iso_utc(vmeta.get("created_at")):
                    issues.append(Issue(str(verification_json_path), "created_at must be ISO-8601 UTC like 2026-03-05T05:10:00Z"))

                seen_votes: set[tuple[str, str]] = set()  # (scout_id, example_id)
                try:
                    for line_no, verdict in _iter_jsonl(verdicts_path):
                        v_path = f"{verdicts_path}:{line_no}"
                        ex_id = verdict.get("id")
                        if not isinstance(ex_id, str) or not ex_id.strip():
                            issues.append(Issue(v_path, "id must be a non-empty string"))
                            continue
                        if ex_id not in submission_examples[sub_id]:
                            issues.append(Issue(v_path, f"id not found in submission {sub_id}"))
                            continue

                        if (scout_id, ex_id) in seen_votes:
                            issues.append(Issue(v_path, f"duplicate vote for id={ex_id} by scout={scout_id}"))
                        seen_votes.add((scout_id, ex_id))

                        vote = verdict.get("vote")
                        if vote not in ("APPROVE", "DENY"):
                            issues.append(Issue(v_path, "vote must be APPROVE or DENY"))

                        if not _is_iso_utc(verdict.get("created_at")):
                            issues.append(Issue(v_path, "created_at must be ISO-8601 UTC like 2026-03-05T05:12:00Z"))

                        notes = verdict.get("notes")
                        if notes is not None and not isinstance(notes, str):
                            issues.append(Issue(v_path, "notes must be a string if present"))

                        reason_codes = verdict.get("reason_codes")
                        if reason_codes is not None and (
                            not isinstance(reason_codes, list) or not all(isinstance(rc, str) for rc in reason_codes)
                        ):
                            issues.append(Issue(v_path, "reason_codes must be an array of strings if present"))
                except ValueError as e:
                    issues.append(Issue(str(verdicts_path), str(e)))
                    continue

    # --- Validate any built corpus files (optional but helpful) ---
    if CORPUS_DIR.exists():
        for corpus_file in sorted(CORPUS_DIR.rglob("*.jsonl")):
            # Ignore empty placeholders
            if corpus_file.name == ".gitkeep":
                continue
            try:
                for line_no, ex in _iter_jsonl(corpus_file):
                    c_path = f"{corpus_file}:{line_no}"
                    for req in ("id", "text", "label", "category"):
                        if req not in ex:
                            issues.append(Issue(c_path, f"missing required field: {req}"))
                    if ex.get("label") not in ("APPROVE", "DENY"):
                        issues.append(Issue(c_path, "label must be APPROVE or DENY"))
                    if ex.get("category") not in category_ids:
                        issues.append(Issue(c_path, "category must be a known category id"))
                    votes = ex.get("votes")
                    if votes is not None and (not isinstance(votes, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in votes.items())):
                        issues.append(Issue(c_path, "votes must be an object {scout_id: vote} if present"))
            except ValueError as e:
                issues.append(Issue(str(corpus_file), str(e)))

    if issues:
        print("HIVE VALIDATION FAILED\n", file=sys.stderr)
        for issue in issues:
            print(f"- {issue.render()}", file=sys.stderr)
        print(f"\nTotal issues: {len(issues)}", file=sys.stderr)
        return 1

    print("HIVE VALIDATION PASSED")
    return 0


def cmd_new_submission(args: argparse.Namespace) -> int:
    issues: list[Issue] = []
    categories = _load_categories(issues)
    if issues:
        for issue in issues:
            print(f"- {issue.render()}", file=sys.stderr)
        return 1

    if args.category not in categories:
        print(f"Unknown category: {args.category}", file=sys.stderr)
        return 1
    if args.label not in ("APPROVE", "DENY"):
        print("label must be APPROVE or DENY", file=sys.stderr)
        return 1

    err = _require_token("team_id", args.team)
    if err:
        print(err, file=sys.stderr)
        return 1

    sub_id = f"subm_{uuid.uuid4().hex}"
    sub_dir = SUBMISSIONS_DIR / sub_id
    sub_dir.mkdir(parents=True, exist_ok=False)

    meta = {
        "format": "hive_submission_v1",
        "submission_id": sub_id,
        "team_id": args.team,
        "label": args.label,
        "category": args.category,
        "created_at": _now_utc_iso(),
        "model": args.model or None,
        "target_count": args.target_count,
        "notes": args.notes or None,
    }
    # Remove nulls for cleanliness
    meta = {k: v for k, v in meta.items() if v is not None}

    _dump_json(sub_dir / "submission.json", meta)
    (sub_dir / "examples.jsonl").write_text("", encoding="utf-8")

    print(str(sub_dir.relative_to(REPO_ROOT)))
    return 0


def cmd_new_verification(args: argparse.Namespace) -> int:
    submission_path = (REPO_ROOT / args.submission).resolve() if not Path(args.submission).is_absolute() else Path(args.submission).resolve()
    try:
        submission_path.relative_to(SUBMISSIONS_DIR.resolve())
    except ValueError:
        print("submission must be under hive/submissions/subm_<uuid>", file=sys.stderr)
        return 1

    sub_id = submission_path.name
    if not SUBMISSION_DIR_RE.match(sub_id):
        print("submission dir must be named subm_<32hex>", file=sys.stderr)
        return 1

    err = _require_token("scout_id", args.scout)
    if err:
        print(err, file=sys.stderr)
        return 1

    out_dir = VERIFICATIONS_DIR / sub_id / f"scout_{args.scout}"
    out_dir.mkdir(parents=True, exist_ok=False)

    meta = {
        "format": "hive_verification_v1",
        "submission_id": sub_id,
        "scout_id": args.scout,
        "created_at": _now_utc_iso(),
        "model": args.model or None,
        "notes": args.notes or None,
    }
    meta = {k: v for k, v in meta.items() if v is not None}

    _dump_json(out_dir / "verification.json", meta)
    (out_dir / "verdicts.jsonl").write_text("", encoding="utf-8")

    print(str(out_dir.relative_to(REPO_ROOT)))
    return 0


def cmd_build_corpus(args: argparse.Namespace) -> int:
    if args.min_confirmations < 1:
        print("--min-confirmations must be >= 1", file=sys.stderr)
        return 1

    # Validate first to fail fast.
    if validate_repo() != 0:
        return 1

    categories_by_id: dict[str, dict[str, Any]] = _load_json(CATEGORIES_FILE)["categories"]  # type: ignore[index]
    _ = categories_by_id  # noqa: F841

    # Load submissions
    submissions: dict[str, dict[str, Any]] = {}
    examples_by_submission: dict[str, list[dict[str, Any]]] = {}
    for sub_dir in sorted([p for p in SUBMISSIONS_DIR.iterdir() if p.is_dir()], key=lambda p: p.name):
        sub_id = sub_dir.name
        if not SUBMISSION_DIR_RE.match(sub_id):
            continue
        meta = _load_json(sub_dir / "submission.json")
        submissions[sub_id] = meta
        examples: list[dict[str, Any]] = []
        for _line_no, ex in _iter_jsonl(sub_dir / "examples.jsonl"):
            examples.append(ex)
        examples_by_submission[sub_id] = examples

    # Load votes
    votes_by_example: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    # key: (submission_id, example_id) -> scout_id -> verdict_obj
    if VERIFICATIONS_DIR.exists():
        for sub_root in sorted([p for p in VERIFICATIONS_DIR.iterdir() if p.is_dir()], key=lambda p: p.name):
            sub_id = sub_root.name
            if sub_id not in submissions:
                continue
            for scout_dir in sorted([p for p in sub_root.iterdir() if p.is_dir()], key=lambda p: p.name):
                scout_name = scout_dir.name
                if not scout_name.startswith("scout_"):
                    continue
                scout_id = scout_name[len("scout_") :]
                verdicts_path = scout_dir / "verdicts.jsonl"
                if not verdicts_path.exists():
                    continue
                for _line_no, v in _iter_jsonl(verdicts_path):
                    ex_id = v["id"]
                    key = (sub_id, ex_id)
                    votes_by_example.setdefault(key, {})
                    votes_by_example[key][scout_id] = v

    built_at = _now_utc_iso()
    out_path = (REPO_ROOT / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    included: list[dict[str, Any]] = []
    excluded_counts = {"insufficient_votes": 0, "disagreement": 0, "excluded_by_reason": 0}

    for sub_id, examples in examples_by_submission.items():
        sub_meta = submissions[sub_id]
        worker_label = sub_meta["label"]
        for ex in examples:
            ex_id = ex["id"]
            key = (sub_id, ex_id)
            scout_votes = votes_by_example.get(key, {})

            # Build vote map and exclusion flags
            vote_map: dict[str, str] = {}
            exclusion_flag = False
            for scout_id, verdict in scout_votes.items():
                vote = verdict.get("vote")
                if isinstance(vote, str):
                    vote_map[scout_id] = vote
                reason_codes = verdict.get("reason_codes")
                if isinstance(reason_codes, list) and any(isinstance(rc, str) and rc in EXCLUSION_REASON_CODES for rc in reason_codes):
                    exclusion_flag = True

            support = sum(1 for v in vote_map.values() if v == worker_label)
            oppose = sum(1 for v in vote_map.values() if v != worker_label)
            total = len(vote_map)
            agreement = (support / total) if total else 0.0

            if exclusion_flag:
                excluded_counts["excluded_by_reason"] += 1
                continue
            if total < args.min_confirmations or support < args.min_confirmations:
                excluded_counts["insufficient_votes"] += 1
                continue
            if oppose > 0:
                excluded_counts["disagreement"] += 1
                continue

            included.append(
                {
                    "id": ex_id,
                    "text": ex["text"],
                    "label": ex["label"],
                    "category": ex["category"],
                    "model": ex.get("model"),
                    "generated_at": ex.get("generated_at"),
                    "votes": vote_map,
                    "agreement": agreement,
                    "verified_at": built_at,
                    "source_submission_id": sub_id,
                    "source_team_id": sub_meta.get("team_id"),
                }
            )

    # Write corpus jsonl
    with out_path.open("w", encoding="utf-8") as f:
        for obj in included:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    # Manifest alongside corpus
    by_label = {"APPROVE": 0, "DENY": 0}
    by_category: dict[str, int] = {}
    for ex in included:
        by_label[ex["label"]] += 1
        by_category[ex["category"]] = by_category.get(ex["category"], 0) + 1

    manifest = {
        "format": "hive_corpus_manifest_v1",
        "built_at": built_at,
        "min_confirmations": args.min_confirmations,
        "total_examples": len(included),
        "counts_by_label": by_label,
        "counts_by_category": dict(sorted(by_category.items(), key=lambda kv: kv[0])),
        "excluded_counts": excluded_counts,
        "included_submissions": sorted(submissions.keys()),
        "tool": {"name": "scripts/hive.py", "version": "v0.1"},
    }
    _dump_json(out_path.parent / "manifest.json", manifest)

    print(f"Wrote {len(included)} examples to {out_path.relative_to(REPO_ROOT)}")
    print(f"Wrote manifest to {(out_path.parent / 'manifest.json').relative_to(REPO_ROOT)}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="hive.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_validate = sub.add_parser("validate", help="Validate submissions/verifications/corpus")
    p_validate.set_defaults(func=lambda _args: validate_repo())

    p_new_sub = sub.add_parser("new-submission", help="Create a new submission skeleton")
    p_new_sub.add_argument("--team", required=True, help="team id (e.g. worker-deny-biosecurity-01)")
    p_new_sub.add_argument("--label", required=True, choices=["APPROVE", "DENY"])
    p_new_sub.add_argument("--category", required=True, help="category id from hive/schema/categories_v1.json")
    p_new_sub.add_argument("--model", default=None, help="optional generator model identifier")
    p_new_sub.add_argument("--target-count", type=int, default=None, help="optional target example count")
    p_new_sub.add_argument("--notes", default=None, help="optional notes")
    p_new_sub.set_defaults(func=cmd_new_submission)

    p_new_ver = sub.add_parser("new-verification", help="Create a new verification skeleton")
    p_new_ver.add_argument("--scout", required=True, help="scout id (e.g. scout-deny-biosecurity-01)")
    p_new_ver.add_argument("--submission", required=True, help="path to hive/submissions/subm_<uuid>")
    p_new_ver.add_argument("--model", default=None, help="optional verifier model identifier")
    p_new_ver.add_argument("--notes", default=None, help="optional notes")
    p_new_ver.set_defaults(func=cmd_new_verification)

    p_build = sub.add_parser("build-corpus", help="Build final corpus from votes")
    p_build.add_argument("--out", required=True, help="output path for examples.jsonl")
    p_build.add_argument("--min-confirmations", type=int, default=2)
    p_build.set_defaults(func=cmd_build_corpus)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


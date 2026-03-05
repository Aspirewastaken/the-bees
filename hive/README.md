# HIVE OPERATIONS

This directory contains launch-ready artifacts for multi-VM Bee corpus generation and verification.

Primary orchestration spec:
- `docs/THE_HIVE_BUILD.md`

Primary executable tool:
- `scripts/hive_cli.py`

---

## Quick launch commands

From repo root:

```bash
python3 scripts/hive_cli.py preflight --root .
python3 scripts/hive_cli.py make-manifests --root . --run-id run_001 --records-per-worker 500 --overwrite
```

After workers/scouts produce JSONL shards:

```bash
python3 scripts/hive_cli.py status --root .
python3 scripts/hive_cli.py assemble --root . --output hive/final/bee_corpus_v1.jsonl --summary hive/final/bee_corpus_v1_summary.json
```

---

## Continuous campaign mode (run indefinitely)

Use a new run identifier per campaign:

- `run_001`, `run_002`, `run_003`, ...

For each run:

1. Generate manifests with a unique `--run-id`.
2. Launch Queen, Worker, Scout, Architect waves.
3. Archive outputs under run-specific filenames or branches.
4. Repeat.

Because manifests and shard paths are explicit, campaigns are resumable and auditable.

---

## Multi-model pool

Model provider routing settings live in:

- `hive/config/model_pool.json`

Use this to distribute load across model families and avoid single-provider bottlenecks.

---

## Guardrails

Non-negotiable:

- No fabricated evidence/metrics.
- Unknowns must be tagged.
- No final merge without scout verdict evidence.
- No silent post-verification edits.

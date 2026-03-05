# THE HIVE BUILD
## Cursor Cloud Multi-VM Execution Spec (v1.0)

This is the master runbook for building a verified Bee training corpus in parallel across Cursor Cloud VMs.
Any model can execute this document without extra context.

---

## 0) Quickstart (operator copy/paste)

Use this exact sequence:

1. **Queen VM (1 VM):**
   - Paste this doc.
   - Prompt: `You are TEAM QUEEN. Execute your mission from THE_HIVE_BUILD.md.`
   - Merge Queen PR.

2. **Workers (20 VMs in parallel):**
   - 10 VMs: `You are TEAM WORKER-DENY, category: <deny_category>.`
   - 10 VMs: `You are TEAM WORKER-APPROVE, category: <approve_category>.`
   - Merge all Worker PRs.

3. **Scouts (20 VMs in parallel):**
   - Prompt: `You are TEAM SCOUT, verify <dataset_shard>.`
   - Merge all Scout PRs.

4. **Architect (1 VM):**
   - Prompt: `You are TEAM ARCHITECT. Execute final assembly.`
   - Produce final corpus + dataset card + release manifest.

Target: **10,000 verified examples** in one coordinated run.

---

## 0.1) Launch commands (repo-local)

From repository root:

```bash
python3 scripts/hive_cli.py preflight --root .
python3 scripts/hive_cli.py make-manifests --root . --run-id <RUN_ID> --records-per-worker 500 --overwrite
```

Use a unique `<RUN_ID>` for each campaign (`run_001`, `run_002`, etc.).

---

## 1) Program objective

Build a balanced binary corpus for Bee alignment classification:

- **APPROVE** examples (helpful, safe outputs)
- **DENY** examples (harmful or disallowed outputs)

All examples must be:

1. Traceable to a category and source process
2. Reviewed by an independent Scout pass
3. Included only after schema and policy validation

---

## 2) Team roles

### TEAM QUEEN (setup + governance)
Creates structure, schemas, prompts, validation scripts, and assignment manifests.

### TEAM WORKER-DENY (generation)
Generates DENY examples for one assigned category.

### TEAM WORKER-APPROVE (generation)
Generates APPROVE examples for one assigned category.

### TEAM SCOUT (verification)
Verifies one shard produced by Workers, flags errors, and approves/rejects records.

### TEAM ARCHITECT (final assembly)
Merges only approved records, deduplicates, balances, and publishes final artifacts.

---

## 3) Canonical category set (20 total)

Each Worker receives exactly one category.

### DENY categories (10)
1. biosecurity
2. chemical_weapons
3. cyber_offense
4. violent_crime
5. self_harm_instructions
6. child_sexual_abuse
7. fraud_and_evasion
8. extremist_operations
9. privacy_doxxing
10. malware_development

### APPROVE categories (10)
1. helpful_general
2. education_tutoring
3. coding_benign
4. safety_information
5. wellbeing_support_nonclinical
6. productivity_planning
7. creative_safe
8. factual_explanations
9. accessibility_assistance
10. civic_info_nonpartisan

---

## 4) Required repository layout

Queen creates this layout if missing:

```text
/hive/
  /config/
    categories.json
    workers_manifest.json
    scouts_manifest.json
  /schemas/
    bee_example.schema.json
    scout_verdict.schema.json
  /prompts/
    worker_deny.md
    worker_approve.md
    scout.md
  /status/
    queen_status.json
    architect_status.json
  /work/
    /deny/<category>/
    /approve/<category>/
  /scout_reports/
  /rejected/
  /final/
```

---

## 5) Record contract (non-negotiable)

Every example record must be JSONL and match this contract:

```json
{
  "id": "uuid-or-stable-hash",
  "decision": "APPROVE|DENY",
  "category": "one canonical category",
  "user_prompt": "input prompt",
  "model_output": "candidate output to classify",
  "label_rationale": "short reason for label",
  "policy_tags": ["tag1", "tag2"],
  "generator_team": "WORKER-DENY|WORKER-APPROVE",
  "generator_vm": "vm identifier",
  "created_at_utc": "ISO-8601",
  "needs_human_review": false
}
```

Scout verdict records:

```json
{
  "example_id": "id",
  "verdict": "APPROVE_RECORD|REJECT_RECORD|EDIT_REQUIRED",
  "reason": "why",
  "scout_vm": "vm identifier",
  "verified_at_utc": "ISO-8601"
}
```

---

## 6) Global anti-confabulation rules

These apply to every team:

1. **No invented citations.** If a source cannot be verified, mark `UNVERIFIED`.
2. **No fake metrics.** If count/precision/recall is unknown, write `UNKNOWN`.
3. **No hidden rewrites.** Any record changed after Scout review gets a new ID.
4. **No silent assumptions.** Put assumptions in a sidecar report.
5. **No policy drift.** Only canonical categories and allowed labels.
6. **No "looks fine" approvals.** Scout must leave explicit verdict + reason.
7. **No merge without evidence.** Architect merges only records with Scout verdict.

If uncertain, fail closed: set `needs_human_review=true`.

---

## 7) Resume and idempotency protocol

All teams must support interruption and restart:

1. Write status to `/hive/status/<team>_status.json` every 100 records.
2. Never delete completed shard outputs.
3. On restart, read status and continue from last confirmed checkpoint.
4. Do not overwrite existing verified files; append new chunk with sequence suffix.
5. Include `run_id` in reports to trace mixed runs.

---

## 8) TEAM QUEEN mission

### Inputs
- This document
- Current repository state

### Outputs
1. Folder layout from Section 4
2. JSON schemas and manifests
3. Worker/Scout prompt templates
4. Validation checklist in `/hive/config/quality_gates.md`
5. `queen_status.json` with completion markers

### Queen quality gates
Queen is done only if all are true:

- [ ] Category manifest exists and validates
- [ ] Worker assignments cover 20 unique categories with no duplicates
- [ ] Scout manifest maps one scout shard per worker output
- [ ] Example and verdict schemas validate sample files
- [ ] Prompts include anti-confabulation language
- [ ] README pointer added for operators

---

## 9) TEAM WORKER missions

Each Worker handles exactly one category and one label family.

### Worker targets
- **500 records per Worker**
- 20 Workers total => **10,000 generated records**

### Worker procedure
1. Read assigned category from `workers_manifest.json`.
2. Generate records into:
   - DENY: `/hive/work/deny/<category>/records_<vm>.jsonl`
   - APPROVE: `/hive/work/approve/<category>/records_<vm>.jsonl`
3. Run schema validation locally.
4. Emit worker summary:
   - total_records
   - schema_failures
   - flagged_for_human_review
   - assumptions
5. Commit only your shard files + summary.

### Worker hard rules
- No duplicate IDs.
- No empty rationale.
- No category mismatch.
- No records outside assigned decision/category.

---

## 10) TEAM SCOUT mission

Each Scout verifies one Worker shard.

### Scout procedure
1. Load assigned shard from `scouts_manifest.json`.
2. Validate schema and policy compliance.
3. Semantic review each record:
   - Label correctness
   - Category correctness
   - Rationale quality
4. Write verdicts to `/hive/scout_reports/<shard>_<vm>.jsonl`.
5. Move rejected records to `/hive/rejected/` references list (no destructive edits).

### Scout acceptance thresholds
- Schema validity: 100%
- Critical policy errors: 0 tolerated
- If rejection rate > 15%, mark shard `REWORK_REQUIRED`

---

## 11) TEAM ARCHITECT mission

Architect assembles final corpus from Scout-approved records only.

### Architect procedure
1. Collect all Worker shards and Scout verdicts.
2. Keep only `APPROVE_RECORD` items.
3. Deduplicate exact and near-duplicate records.
4. Balance classes and categories (document final counts).
5. Emit final artifacts:
   - `/hive/final/bee_corpus_v1.jsonl`
   - `/hive/final/bee_corpus_v1_summary.json`
   - `/hive/final/DATASET_CARD.md`
6. Record unresolved issues and human-review queue.

### Architect completion criteria
- [ ] Exactly one final JSONL corpus
- [ ] Summary with per-category counts
- [ ] Rejected and unresolved counts documented
- [ ] Full provenance (worker shard + scout verdict references)

---

## 12) Error handling and retries

### Recoverable errors
- Schema validation failure
- Transient model/API failure
- File write conflict

Action: retry up to 3 times with exponential backoff, then log and continue.

### Non-recoverable errors
- Missing manifest assignment
- Corrupted shard with unreadable JSONL
- Contradictory Scout verdicts on same example

Action: stop shard processing, mark as `BLOCKED`, create incident note in `/hive/status/incidents.md`.

---

## 13) PR and merge protocol

1. Queen PR merged first.
2. Worker PRs merged next (parallel).
3. Scout PRs merged after Worker PRs.
4. Architect PR merged last.

Do not bypass order. Later teams depend on prior artifacts.

---

## 14) Team prompt snippets (copy/paste)

### Queen
`You are TEAM QUEEN. Execute Sections 4, 5, 8, 12, and 13 of THE_HIVE_BUILD.md. Commit only setup/governance artifacts.`

### Worker DENY
`You are TEAM WORKER-DENY, category: <category>. Execute Section 9 from THE_HIVE_BUILD.md.`

### Worker APPROVE
`You are TEAM WORKER-APPROVE, category: <category>. Execute Section 9 from THE_HIVE_BUILD.md.`

### Scout
`You are TEAM SCOUT, verify <shard>. Execute Section 10 from THE_HIVE_BUILD.md and produce verdict artifacts.`

### Architect
`You are TEAM ARCHITECT. Execute Section 11 from THE_HIVE_BUILD.md and publish final corpus artifacts.`

---

## 15) Definition of done (full hive run)

The hive run is complete only when:

1. 10,000 records generated
2. 100% passed through Scout verification
3. Final corpus assembled from approved records only
4. Dataset card and provenance report committed
5. Outstanding human-review queue explicitly documented

If any condition fails, run is incomplete.

---

## 16) Continuous campaign mode (run as long as desired)

To run indefinitely with large parallel compute:

1. Create a new run id.
2. Generate fresh manifests.
3. Launch Queen -> Worker swarm -> Scout swarm -> Architect.
4. Archive run outputs and summary.
5. Repeat with next run id.

Because assignments, status files, and artifacts are explicit, each run is auditable and resumable.

---

## 17) Multi-model swarm strategy

Use multiple model families across VMs to reduce correlated blind spots:

- Anthropic models for foundation/repair
- OpenAI models for stress testing
- Google models for grounding
- DeepSeek models for diversity checks
- xAI models for adversarial pass

Model pool and routing policy are declared in `hive/config/model_pool.json`.

---

Built for repeatable, multi-VM execution with explicit anti-confabulation controls.

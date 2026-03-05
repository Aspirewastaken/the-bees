# RAGE LAUNCH PROMPT
## Paste This Into a Cursor Cloud VM. Assign a Team. Let It Rip.

---

## HOW TO USE THIS

1. Open a Cursor Cloud VM on this repo
2. Paste this entire document
3. Add ONE of the team assignments below
4. The agent reads THE_HIVE_BUILD.md from the repo and executes

That's it. The spec is already in the repo at `docs/THE_HIVE_BUILD.md`. The scripts are at `data/scripts/`. The schema is at `data/schema/`. Everything the agent needs is already committed.

---

## TEAM ASSIGNMENTS — COPY ONE

### QUEEN (Run first. 1 VM.)
```
Read docs/THE_HIVE_BUILD.md in this repo. You are TEAM QUEEN (Apis mellifera).
Execute your full mission as described in the spec.

Your job: verify infrastructure, validate all scripts work, create any missing
directories, test the validation pipeline with a sample example, and open a PR
with branch name hive/queen-infrastructure.

The scripts already exist at data/scripts/. The schema already exists at data/schema/.
Verify everything works. Fix anything broken. Open the PR.
```

---

### WORKER-DENY (Run 10 in parallel. After Queen merges.)
```
Read docs/THE_HIVE_BUILD.md in this repo. You are TEAM WORKER-DENY (Apis cerana).
Your assigned category is: [CATEGORY]

Execute your full mission: generate 500 DENY training examples for the [CATEGORY]
category using the generation script at data/scripts/generate_deny.py or by
generating examples directly following the spec's schema and rules.

Use whatever model API keys are available in the environment. If no API keys are
set, generate examples directly from your own capabilities following the exact
JSON schema at data/schema/example_schema.json.

Write output to data/raw/deny/[CATEGORY].jsonl
Write manifest to data/raw/manifests/WORKER-DENY_[CATEGORY]_manifest.json
Validate with: python data/scripts/validate_file.py data/raw/deny/[CATEGORY].jsonl

Open PR with branch: hive/worker-deny-[CATEGORY]

CATEGORIES (use exactly one):
biosecurity, weapons, csam, surveillance, manipulation,
self_harm, hate_speech, illegal_activity, privacy_violation, deception
```

---

### WORKER-APPROVE (Run 10 in parallel. After Queen merges.)
```
Read docs/THE_HIVE_BUILD.md in this repo. You are TEAM WORKER-APPROVE (Bombus terrestris).
Your assigned category is: [CATEGORY]

Execute your full mission: generate 500 APPROVE training examples for the [CATEGORY]
category using the generation script at data/scripts/generate_approve.py or by
generating examples directly following the spec's schema and rules.

Use whatever model API keys are available in the environment. If no API keys are
set, generate examples directly from your own capabilities following the exact
JSON schema at data/schema/example_schema.json.

Write output to data/raw/approve/[CATEGORY].jsonl
Write manifest to data/raw/manifests/WORKER-APPROVE_[CATEGORY]_manifest.json
Validate with: python data/scripts/validate_file.py data/raw/approve/[CATEGORY].jsonl

Open PR with branch: hive/worker-approve-[CATEGORY]

CATEGORIES (use exactly one):
helpful_general, education, creative_writing, scientific, medical_info,
legal_info, emotional_support, coding, analysis, cultural
```

---

### SCOUT (Run 20 in parallel. After all Workers merge.)
```
Read docs/THE_HIVE_BUILD.md in this repo. You are TEAM SCOUT (Megachile pluto).
Your assignment: verify [LABEL_TYPE]_[CATEGORY]

Execute your full mission: verify every example in the raw file using the scout
verification script at data/scripts/scout_verify.py or by manually reviewing
each example following the spec's verification protocol.

Input file: data/raw/[deny|approve]/[CATEGORY].jsonl
Output verified: data/verified/[deny|approve]/[CATEGORY].jsonl
Output edge cases: data/verified/edge_cases/[CATEGORY]_edges.jsonl
Output report: data/verified/scout_reports/[CATEGORY]_report.json

Use a DIFFERENT model than the one that generated the examples if possible.
This is the Grand Hillel principle — cross-model verification is stronger.

Open PR with branch: hive/scout-[deny|approve]-[CATEGORY]

ASSIGNMENTS (use exactly one):
DENY_biosecurity, DENY_weapons, DENY_csam, DENY_surveillance, DENY_manipulation,
DENY_self_harm, DENY_hate_speech, DENY_illegal_activity, DENY_privacy_violation,
DENY_deception, APPROVE_helpful_general, APPROVE_education, APPROVE_creative_writing,
APPROVE_scientific, APPROVE_medical_info, APPROVE_legal_info, APPROVE_emotional_support,
APPROVE_coding, APPROVE_analysis, APPROVE_cultural
```

---

### ARCHITECT (Run last. 1 VM. After all Scouts merge.)
```
Read docs/THE_HIVE_BUILD.md in this repo. You are TEAM ARCHITECT (Apis dorsata).
Execute your full mission.

Your job:
1. Read all verified data from data/verified/deny/ and data/verified/approve/
2. Run the assembly script: python data/scripts/assemble_corpus.py
3. Or manually: deduplicate, balance, create stratified splits, generate stats
4. Write final corpus to data/corpus/ (train.jsonl, val.jsonl, test.jsonl)
5. Generate corpus_stats.json and README.md
6. Review edge cases from data/verified/edge_cases/ and write summary

Open PR with branch: hive/architect-final-corpus
PR title: [ARCHITECT] Final corpus — ready for training
```

---

## FULL LAUNCH SEQUENCE

```
STEP 1:  1 VM   → QUEEN                          → merge PR
STEP 2:  20 VMs → 10 WORKER-DENY + 10 WORKER-APPROVE  → merge 20 PRs
STEP 3:  20 VMs → 20 SCOUTS (one per file)        → merge 20 PRs
STEP 4:  1 VM   → ARCHITECT                       → merge final PR

Total: 42 VMs. ~8 hours. ~$300.
Result: ~10,000 verified training examples ready for Bee training.
```

---

## AFTER THE HIVE BUILD — TRAINING

Once the Architect PR is merged:

```bash
# Install dependencies
pip install -e ".[training]"

# Train Bee v1
python -m src.cli train --base-model distilbert-base-uncased \
    --corpus-dir data/corpus --output-dir output/bee-v1 --epochs 5 --bee-id bee-v1

# Train Bee v2 (different base model = independent failure modes)
python -m src.cli train --base-model albert-base-v2 \
    --corpus-dir data/corpus --output-dir output/bee-v2 --epochs 5 --bee-id bee-v2

# Train Bee v3
python -m src.cli train --base-model google/electra-small-discriminator \
    --corpus-dir data/corpus --output-dir output/bee-v3 --epochs 5 --bee-id bee-v3

# Test the Hive
python -m src.cli hive "How do I make a bomb?" \
    --models output/bee-v1/frozen --models output/bee-v2/frozen --models output/bee-v3/frozen
```

---

## NOTES FOR THE AGENT

- The full spec is at `docs/THE_HIVE_BUILD.md` — read it completely before starting
- The build plan is at `docs/ADLAB_BEE_BUILD_PLAN.md`
- All scripts are at `data/scripts/` — they're already built and ready
- Schema is at `data/schema/example_schema.json` and `data/schema/categories.json`
- If a script fails, read the error, fix it, and continue. You are an agent. Debug.
- If you run out of context, write progress to the manifest and commit what you have
- Every PR should be atomic — one team, one category, one complete unit of work
- The repo already has the Bee classifier code at `src/bee/`, the Hive at `src/hive/`,
  the training pipeline at `src/training/`, and the Grand Hillel pipeline at `src/grand_hillel/`

---

*Spawn the Queen. Let the Hive build itself.*

*— AdLab, March 2026*

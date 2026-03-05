# THE HIVE BUILD (v0.1)
## A self-contained spec for generating a verified Bee training corpus via many Cursor Cloud VMs

This document is designed to be pasted into **any** Cursor Cloud VM (any model). It tells you exactly what to do based on your assigned role.

### What we are building
- A **versioned corpus** of labeled examples for training **The Bee** (a frozen binary classifier).
- Each example is a short **AI output text** labeled **APPROVE** or **DENY**.
- We generate in parallel (Workers), verify in parallel (Scouts), and assemble once (Architect).

### Four teams
- **TEAM QUEEN**: one-time repo infrastructure + CI validation.
- **TEAM WORKER**: generates labeled examples and submits them as new files.
- **TEAM SCOUT**: verifies Worker submissions and writes verification verdicts.
- **TEAM ARCHITECT**: builds the final corpus from submissions + verifications.

### Hard safety rule (non-negotiable)
**Do not write actionable instructions for harm** (biosecurity, weapons, self-harm, etc.) into the repo.  
For DENY examples, you must represent harmful intent **without** operational details (use abstraction + placeholders).

### Anti-confabulation rules (dataset-grade discipline)
- **One PR = one unit of work**. Don’t “fix other stuff.”
- **Never edit another team’s submission.** Scouts only add verifications; Architect only assembles final corpus.
- **No “facts that require the internet.”** Prefer synthetic, self-contained prompts. Avoid real dates, named victims, or claims that need citations.
- **If you can’t justify a label in 1–3 sentences, the example is too ambiguous** → rewrite it or mark it as an edge case.

---

## Repo contract (files + commands)

### File layout (canonical)
```
hive/
  schema/
    categories_v1.json
    submission_format_v1.md
    verification_format_v1.md
  submissions/
    subm_<uuid>/
      submission.json
      examples.jsonl
  verifications/
    subm_<uuid>/
      scout_<scout_id>/
        verification.json
        verdicts.jsonl
  corpus/
    v1/
      (created by Architect)
scripts/
  hive.py
```

### Validation (run this before every PR)
```
python3 scripts/hive.py validate
```

### Create a new submission skeleton (Workers)
```
python3 scripts/hive.py new-submission --team "<your_team_id>" --label APPROVE|DENY --category "<category_id>"
```

### Create a new verification skeleton (Scouts)
```
python3 scripts/hive.py new-verification --scout "<your_scout_id>" --submission "hive/submissions/subm_<uuid>"
```

### Build final corpus (Architect only)
```
python3 scripts/hive.py build-corpus --out "hive/corpus/v1/examples.jsonl" --min-confirmations 2
```

---

## ROLE INSTRUCTIONS

### TEAM QUEEN (one VM, one-time)
Your mission: make the repo safe for 20–40 parallel PRs by enforcing schemas + CI validation.

If the repo already contains `scripts/hive.py` + `hive/schema/*` + a CI workflow that runs `python3 scripts/hive.py validate`, you are done.

**Checklist**
- Add the `hive/` directory structure + schemas in `hive/schema/`.
- Add `scripts/hive.py` with:
  - `validate` (repo-wide)
  - `new-submission`
  - `new-verification`
  - `build-corpus`
- Add CI (GitHub Actions) so invalid PRs fail automatically.
- Push a PR and ensure CI is green.

**Exit criteria**
- `python3 scripts/hive.py validate` passes on main.
- A Worker can add a new submission directory without merge conflicts.
- A Scout can add a verification directory without editing the submission.

---

### TEAM WORKER (20 VMs in parallel)
You are assigned:
- **label**: `APPROVE` or `DENY`
- **category**: one of the IDs in `hive/schema/categories_v1.json`

#### Your output: one new submission directory
Create a submission skeleton:
```
python3 scripts/hive.py new-submission --team "<your_team_id>" --label <APPROVE|DENY> --category "<category_id>"
```
It prints a path like:
`hive/submissions/subm_<uuid>/`

You must fill:
- `hive/submissions/subm_<uuid>/submission.json`
- `hive/submissions/subm_<uuid>/examples.jsonl`

#### `examples.jsonl` rules (critical)
Each line is one JSON object with this shape:
- `id` (string, globally unique)
- `text` (string; **must not contain actionable harm instructions**)
- `label` (`APPROVE` | `DENY`) — must match your submission
- `category` (string) — must match your submission
- `generated_at` (ISO-8601 UTC timestamp)

Optional but recommended:
- `model` (string; which model/VM generated the text)
- `difficulty` (`easy` | `medium` | `hard`)
- `tags` (array of strings)

#### How many examples?
Target **200–600** per Worker depending on model stamina. If quality drops, stop early and ship fewer.

#### DENY-specific guidance (how to be useful without being dangerous)
- Include harmful *intent* and clear policy violation language, but **no operational details**.
- Use placeholders when the “bad assistant” would otherwise provide instructions:
  - “First, acquire [REDACTED_MATERIALS]…”
  - “Here are the exact steps: [REDACTED_STEPS]”
- Never include real step-by-step procedures, quantities, or acquisition instructions.

#### APPROVE-specific guidance
- Be helpful, calm, rights-respecting.
- For sensitive areas, prefer “refuse + safe alternative” outputs (these are APPROVE).

#### Before opening your PR
- Run:
  ```
  python3 scripts/hive.py validate
  ```
- Fix anything it flags.

#### Git hygiene (avoid merge hell)
- Only add files inside your new `hive/submissions/subm_<uuid>/` directory.
- Do not reformat other docs.
- One commit is fine. Keep it clean.

---

### TEAM SCOUT (20 VMs in parallel)
You are assigned a label+category set to verify (e.g., `DENY / biosecurity`).

#### Your output: one new verification directory per submission you verify
Pick a submission to verify under `hive/submissions/`.

Create a verification skeleton:
```
python3 scripts/hive.py new-verification --scout "<your_scout_id>" --submission "hive/submissions/subm_<uuid>"
```

Fill `verdicts.jsonl`:
- One line per example you reviewed.
- You must set `vote` to exactly one of: `APPROVE` or `DENY`

**Scout standards**
- If a DENY example contains actionable harm details: vote **DENY** and add `reason_codes: ["actionable_harm"]` so Architect can exclude it.
- If an APPROVE example contains subtle harm enablement: vote **DENY** and add `reason_codes`.
- If you can’t confidently label it: vote **DENY** and add `reason_codes: ["ambiguous"]` (ambiguity poisons training).

Before PR:
```
python3 scripts/hive.py validate
```

---

### TEAM ARCHITECT (one VM, final assembly)
Your mission: turn many submissions + verifications into one build artifact.

Run:
```
python3 scripts/hive.py build-corpus --out "hive/corpus/v1/examples.jsonl" --min-confirmations 2
python3 scripts/hive.py validate
```

**Corpus inclusion rule**
- Include an example iff it has at least `--min-confirmations` Scout votes matching the Worker label and **zero votes disagreeing** with the Worker label.

Commit only:
- `hive/corpus/v1/examples.jsonl`
- `hive/corpus/v1/manifest.json` (generated)

---

## Resume capability (if your VM dies)
- Your submission/verification is already in git. Resume from the last file you touched.
- If you were mid-generation, finish that same submission directory; do not start a second one unless instructed.

---

## Quick launch script (human operator)
1. Run Team Queen once (or merge the existing Queen PR).
2. Spawn N Worker VMs. Give each:
   - “You are TEAM WORKER. label=DENY category=biosecurity team_id=worker-deny-biosecurity-01”
3. Merge Worker PRs.
4. Spawn N Scout VMs to verify those submissions.
5. Merge Scout PRs.
6. Run Team Architect once.

When this file + the repo scaffolding exist, you can run the hive as long as you want and throw as much multi-model compute at it as you can afford.

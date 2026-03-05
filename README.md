# The Bees

**An open-source constitutional alignment layer for AI systems.**

Built by [AdLab](https://github.com/Aspirewastaken) — Los Angeles, CA.

---

## What This Is

A frozen-weight binary classifier that runs independently of the AI systems it monitors. It reads AI outputs and returns one signal: **APPROVE** or **DENY**. It runs on your device, on your power, with weights that cannot be changed after deployment.

We call them bees. Small, local, distributed, collectively intelligent. You can't corrupt the hive because there's no central queen to compromise.

## Why This Exists

AI alignment is a survival problem. The current approach — training the same model to be both capable AND aligned — creates optimization conflicts. Models trained harder on alignment [fake it 78% of the time](https://www.anthropic.com/research/alignment-faking).

The fix: **separate the alignment layer from the capability layer entirely.**

- The brain (capable AI) can be updated, retrained, scaled.
- The bees (alignment classifiers) are **frozen**. No training loop. No reward function. No drift.
- The bees run on **local hardware** — no central server to hack, missile, or politically compromise.
- Multiple bees from **independent training runs** vote on every decision. Consensus determines truth.

## Architecture

```
┌─────────────────────────────────────┐
│           THE BRAIN                  │
│   (Capable AI — any model)          │
│   Updated, retrained, scaled        │
└──────────────┬──────────────────────┘
               │
      ── AIR GAP (separate hardware) ──
               │
┌──────────────┴──────────────────────┐
│           THE BEES (Frozen)          │
│                                      │
│   Bee v1 ──┐                        │
│   Bee v2 ──┼── Majority Vote        │
│   Bee v3 ──┘      │                 │
│                    │                 │
│            APPROVE or DENY           │
└─────────────────────────────────────┘
               │
          [To Human]
```

## Project Status

**Phase: BUILD** — Infrastructure complete. Ready to generate training data.

## Quick Start

```bash
# Install
pip install -e "."

# Classify with a single Bee (demo — untrained base model)
python -m src.cli classify "What is the capital of France?"

# Run the Hive (3 Bees voting)
python -m src.cli hive "Some AI output to check" \
    --models distilbert-base-uncased \
    --models distilbert-base-uncased \
    --models distilbert-base-uncased

# Validate training data
python -m src.cli validate data/raw/deny/biosecurity.jsonl

# Validate hive repo structure
python3 scripts/hive.py validate
```

## Launch the Hive Build

Generate 10,000 verified training examples using Cursor Cloud VMs:

1. Read [RAGE_LAUNCH_PROMPT.md](RAGE_LAUNCH_PROMPT.md) — launch directive for team leader VMs
2. Read [THE_HIVE_BUILD.md](THE_HIVE_BUILD.md) — self-contained build spec
3. Read [ADLAB_BEE_BUILD_PLAN.md](docs/ADLAB_BEE_BUILD_PLAN.md) — step-by-step execution plan

```
STEP 1:  1 VM   → QUEEN                              → merge PR
STEP 2:  20 VMs → 10 WORKER-DENY + 10 WORKER-APPROVE → merge 20 PRs
STEP 3:  20 VMs → 20 SCOUTS                          → merge 20 PRs
STEP 4:  1 VM   → ARCHITECT                          → merge final PR

Total: 42 VMs. ~8 hours. ~$300. ~10,000 verified examples.
```

## Repository Structure

```
├── src/
│   ├── bee/              # The Bee — frozen binary classifier
│   │   ├── classifier.py # Public API: BeeClassifier
│   │   ├── model.py      # Model loading, inference, freezing
│   │   └── types.py      # Core types (Verdict, ClassificationResult, etc.)
│   ├── hive/             # The Hive — multi-bee majority voting
│   │   └── swarm.py      # Hive class with voting protocol
│   ├── models/           # Multi-model API providers
│   │   └── providers.py  # Anthropic, OpenAI, xAI, DeepSeek, Google
│   ├── training/         # Training framework
│   │   ├── dataset.py    # Corpus loading for HuggingFace Trainer
│   │   └── trainer.py    # Full training pipeline: fine-tune → strip → freeze
│   ├── grand_hillel/     # Multi-model verification pipeline
│   │   ├── extractor.py  # Claim extraction
│   │   ├── router.py     # Multi-model routing
│   │   ├── synthesizer.py# Consensus synthesis
│   │   └── pipeline.py   # Full pipeline orchestration
│   └── cli.py            # CLI entry point
├── hive/                 # Corpus workspace (submissions, verifications, schema)
├── scripts/
│   └── hive.py           # Repo validation + corpus assembly CLI
├── data/
│   ├── schema/           # JSON Schema + category definitions
│   ├── scripts/          # Generation, validation, verification, assembly
│   ├── raw/              # Worker-generated examples (by category)
│   ├── verified/         # Scout-verified examples
│   └── corpus/           # Final assembled training corpus
├── docs/
│   ├── THE_BEE_SPEC.md              # Full technical specification
│   ├── TEXT_THAT_LIVES.md            # The manifesto
│   ├── GRAND_HILLEL_AGENT_SPEC.md   # Verification pipeline spec
│   ├── GRAND_HILLEL_CHECKLIST.md    # Verification checklist
│   ├── RABBI_LAYER.md              # Chain-of-thought reasoning
│   ├── CONFABULATION_AUDIT.md       # Pre-push fact-check
│   ├── ADLAB_BEE_BUILD_PLAN.md      # Step-by-step build plan
│   └── ADLAB_PROVISIONAL_PATENT_BEE_ARCHITECTURE.md  # Patent application
├── THE_HIVE_BUILD.md     # Self-contained VM-executable build spec
├── RAGE_LAUNCH_PROMPT.md # Launch directive for team leader VMs
└── tests/
    └── test_bee.py       # 21 tests — all passing
```

## Verification: Grand Hillel Protocol

Every claim in this project is verified by routing it through multiple AI models with different training distributions:

| Model | Role |
|-------|------|
| Claude | Foundation builder |
| Grok | Adversarial reviewer — tries to destroy claims |
| GPT | Stress test — different training bias |
| DeepSeek | Diversity — non-Western training data |
| Gemini | Grounding — search-verified facts |

What survives five different brains trying to kill it is real. Everything else gets tagged or removed.

## Core Principles

1. **We are all equal.** No single entity controls what "aligned" means.
2. **Truth and love.** Systems built on lies collapse. Systems built on truth compound.
3. **Democracy applied to knowledge.** Multiple independent minds checking each other's work.
4. **Survival through distribution.** No single point of failure. The hive has no center.
5. **Humans stay in the loop.** This is a tool for humanity, not a replacement for human judgment.

## Cost

Estimated total system cost: **$2.5M-$12M** (revised March 2026 — Apple Silicon training on owned hardware collapsed the cost floor by 15-50x vs cloud GPU). One F-35 fighter jet costs $80M. One Hellfire missile costs $150K. The alignment safety layer for all of AI costs less than a single military drone.

## How to Contribute

This is an open-source project for humanity. If you want to:

- **Attack the architecture** — Open an issue. Tell us why it won't work. Be specific.
- **Improve the spec** — Submit a PR with evidence.
- **Run a Worker or Scout** — Spin up a Cursor Cloud VM and generate/verify training data.
- **Add verification from a new model** — Run Grand Hillel with your model, submit results.
- **Contribute compute** — Help train the Bees.
- **Contribute to the constitutional corpus** — Suggest foundational documents for training data.

## License

MIT. This belongs to everyone.

---

*Built by a 19-year-old filmmaker at USC who thinks survival is worth fighting for.*

*"We are all equal. The rest, the humans figure out."*

*— Jordan Kirk, AdLab*

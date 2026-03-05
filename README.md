# The Bees 🐝

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

## Core Principles

1. **We are all equal.** No single entity controls what "aligned" means.
2. **Truth and love.** Systems built on lies collapse. Systems built on truth compound.
3. **Democracy applied to knowledge.** Multiple independent minds checking each other's work.
4. **Survival through distribution.** No single point of failure. The hive has no center.
5. **Humans stay in the loop.** This is a tool for humanity, not a replacement for human judgment.

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

## Project Status

🔴 **Phase: Specification** — Architecture defined, verification pipeline designed, not yet implemented.

This is an idea. It should be explored, tested, and destroyed by adversarial review. What survives is real.

## Documentation

- [THE_BEE_SPEC.md](docs/THE_BEE_SPEC.md) — Full technical specification
- [TEXT_THAT_LIVES.md](docs/TEXT_THAT_LIVES.md) — The manifesto (why this matters)
- [GRAND_HILLEL_AGENT_SPEC.md](docs/GRAND_HILLEL_AGENT_SPEC.md) — Multi-model verification harness
- [GRAND_HILLEL_CHECKLIST.md](docs/GRAND_HILLEL_CHECKLIST.md) — Verification checklist
- [THE_HIVE_BUILD.md](docs/THE_HIVE_BUILD.md) — Multi-VM swarm execution spec
- [ADLAB_BEE_BUILD_PLAN.md](docs/ADLAB_BEE_BUILD_PLAN.md) — Operator plan and execution waves
- [RAGE_LAUNCH_PROMPT.md](docs/RAGE_LAUNCH_PROMPT.md) — Copy/paste launch prompt
- [ADLAB_PROVISIONAL_PATENT_BEE_ARCHITECTURE.md](docs/ADLAB_PROVISIONAL_PATENT_BEE_ARCHITECTURE.md) — Technical patent draft (markdown)

## Launch-Ready Hive Tooling

The repository now includes executable Hive scaffolding under `hive/` and `scripts/hive_cli.py`.

Quick preflight:

```bash
python3 scripts/hive_cli.py preflight --root .
python3 scripts/hive_cli.py make-manifests --root . --run-id run_001 --records-per-worker 500 --overwrite
```

## How to Contribute

This is an open-source project for humanity. If you want to:

- **Attack the architecture** — Open an issue. Tell us why it won't work. Be specific.
- **Improve the spec** — Submit a PR with evidence.
- **Add verification from a new model** — Run Grand Hillel with your model, submit results.
- **Contribute compute** — (Coming soon) Distributed training framework.
- **Contribute to the constitutional corpus** — Suggest foundational documents that should be in training data.

## Cost

Estimated total system cost: **$2.5M-$12M** (revised March 2026 — Apple Silicon training on owned hardware collapsed the cost floor by 15-50x vs cloud GPU). One F-35 fighter jet costs $80M. One Hellfire missile costs $150K. The alignment safety layer for all of AI costs less than a single military drone.

## License

MIT. This belongs to everyone.

---

*Built by a 19-year-old filmmaker at USC who thinks survival is worth fighting for.*

*"We are all equal. The rest, the humans figure out."*

*— Jordan Kirk, AdLab*

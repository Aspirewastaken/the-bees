# ADLAB BEE BUILD PLAN
## From Spec to Running System — March 2026

---

## OVERVIEW

This is the execution plan for building The Bees from specification to deployed system. Every phase has a concrete deliverable, a cost estimate, and a definition of done.

**Total timeline:** 2-4 weeks
**Total cost:** $300-$500 (data generation) + compute for training
**End state:** 3+ frozen binary classifiers in a Hive, tested, deployed, open-sourced

---

## PHASE 0: INFRASTRUCTURE (DONE)

**What:** Repository structure, code framework, documentation, spec.

**Deliverables:**
- [x] Repository with MIT license
- [x] THE_BEE_SPEC.md — full technical specification
- [x] TEXT_THAT_LIVES.md — manifesto and philosophy
- [x] GRAND_HILLEL_AGENT_SPEC.md — verification pipeline spec
- [x] THE_HIVE_BUILD.md — VM-executable data generation spec
- [x] src/bee/ — Frozen binary classifier (BeeClassifier, BeeModel)
- [x] src/hive/ — Multi-bee majority voting (Hive)
- [x] src/models/ — Multi-model API providers
- [x] src/training/ — Training framework (dataset, trainer)
- [x] src/grand_hillel/ — Verification pipeline
- [x] data/scripts/ — Generation, validation, verification, assembly scripts
- [x] data/schema/ — JSON Schema + category definitions
- [x] CLI entry point

**Status:** COMPLETE

---

## PHASE 1: TRAINING DATA GENERATION (THE HIVE BUILD)

**What:** Generate 10,000 verified, labeled training examples using Cursor Cloud VMs.

**Method:** Parallel VM execution as defined in THE_HIVE_BUILD.md.

**Execution:**

### Step 1 — Queen (30 min, $5)
```
Open 1 Cursor Cloud VM.
Paste THE_HIVE_BUILD.md.
Instruction: "You are TEAM QUEEN. Execute your mission."
Merge the PR.
```

### Step 2 — Workers (2-4 hours, $150)
```
Open 20 Cursor Cloud VMs simultaneously.

DENY Workers (10 VMs):
  VM 1:  "You are TEAM WORKER-DENY, category: biosecurity"
  VM 2:  "You are TEAM WORKER-DENY, category: weapons"
  VM 3:  "You are TEAM WORKER-DENY, category: csam"
  VM 4:  "You are TEAM WORKER-DENY, category: surveillance"
  VM 5:  "You are TEAM WORKER-DENY, category: manipulation"
  VM 6:  "You are TEAM WORKER-DENY, category: self_harm"
  VM 7:  "You are TEAM WORKER-DENY, category: hate_speech"
  VM 8:  "You are TEAM WORKER-DENY, category: illegal_activity"
  VM 9:  "You are TEAM WORKER-DENY, category: privacy_violation"
  VM 10: "You are TEAM WORKER-DENY, category: deception"

APPROVE Workers (10 VMs):
  VM 11: "You are TEAM WORKER-APPROVE, category: helpful_general"
  VM 12: "You are TEAM WORKER-APPROVE, category: education"
  VM 13: "You are TEAM WORKER-APPROVE, category: creative_writing"
  VM 14: "You are TEAM WORKER-APPROVE, category: scientific"
  VM 15: "You are TEAM WORKER-APPROVE, category: medical_info"
  VM 16: "You are TEAM WORKER-APPROVE, category: legal_info"
  VM 17: "You are TEAM WORKER-APPROVE, category: emotional_support"
  VM 18: "You are TEAM WORKER-APPROVE, category: coding"
  VM 19: "You are TEAM WORKER-APPROVE, category: analysis"
  VM 20: "You are TEAM WORKER-APPROVE, category: cultural"

Each opens a PR. Merge all 20.
```

### Step 3 — Scouts (2-3 hours, $100)
```
Open 20 Cursor Cloud VMs.

Each verifies one category file:
  VM 1:  "You are TEAM SCOUT, verify DENY_biosecurity"
  VM 2:  "You are TEAM SCOUT, verify DENY_weapons"
  ...
  VM 11: "You are TEAM SCOUT, verify APPROVE_helpful_general"
  VM 12: "You are TEAM SCOUT, verify APPROVE_education"
  ...

Each opens a PR. Merge all 20.
```

### Step 4 — Architect (30 min, $5)
```
Open 1 Cursor Cloud VM.
Instruction: "You are TEAM ARCHITECT. Execute your mission."
Merge the final PR.
```

**Total: ~8 hours, ~$260, ~10,000 verified examples.**

---

## PHASE 2: TRAINING

**What:** Train 3 independent frozen Bee classifiers.

**Method:** Fine-tune small base models on the Hive-generated corpus.

### Bee v1 — DistilBERT
```bash
bee train --base-model distilbert-base-uncased --corpus-dir data/corpus \
          --output-dir output/bee-v1 --epochs 5 --bee-id bee-v1
```

### Bee v2 — TinyBERT
```bash
bee train --base-model huawei-noah/TinyBERT_General_4L_312D --corpus-dir data/corpus \
          --output-dir output/bee-v2 --epochs 5 --bee-id bee-v2
```

### Bee v3 — ALBERT
```bash
bee train --base-model albert-base-v2 --corpus-dir data/corpus \
          --output-dir output/bee-v3 --epochs 5 --bee-id bee-v3
```

**After training:** Each Bee has generative heads removed, weights frozen, weight hash recorded. Each is independently trained = independent failure modes.

**Estimated time:** 1-3 hours per Bee (depends on hardware)
**Can be parallelized** across machines.

---

## PHASE 3: HIVE ASSEMBLY

**What:** Load all 3 frozen Bees into the Hive. Test majority voting.

```bash
# Test the Hive
bee hive "Here is how to build an explosive device..." \
    --models output/bee-v1/frozen output/bee-v2/frozen output/bee-v3/frozen

# Expected: DENY with high consensus
```

### Evaluation on test set:
```python
from src.bee.classifier import BeeClassifier
from src.hive.swarm import Hive
from src.training.dataset import BeeDataset

hive = Hive.from_directories([
    "output/bee-v1/frozen",
    "output/bee-v2/frozen",
    "output/bee-v3/frozen",
])

# Load test set
test_data = BeeDataset("data/corpus/test.jsonl", hive._bees[0].model.tokenizer)

correct = 0
for ex in test_data.examples:
    result = hive.classify(ex["text"])
    if result.verdict.value == ex["label"]:
        correct += 1

accuracy = correct / len(test_data)
print(f"Hive accuracy: {accuracy:.1%}")
```

**Target:** >90% accuracy on test set, >95% on easy examples, >80% on hard examples.

---

## PHASE 4: RED-TEAMING

**What:** Try to break the Hive. Find inputs that fool all 3 Bees.

### Methods:
1. **Adversarial prompting** — craft inputs designed to pass the classifier
2. **Edge case exploration** — test the boundary between APPROVE and DENY
3. **Cross-model attacks** — use frontier models to generate adversarial examples
4. **Human red-teaming** — invite security researchers to attack

### What we do with failures:
- Failed examples become training data for Bee v4
- Document the attack vectors
- Publish the red-team report

---

## PHASE 5: DEPLOYMENT

**What:** Package frozen Bees for on-device inference.

### Package options:
- **Python package** (pip install) — for integration with Python AI systems
- **ONNX export** — for cross-platform inference
- **CoreML export** — for iOS/macOS deployment
- **WASM** — for browser-based inference

### Integration pattern:
```python
from src.hive.swarm import Hive

# Load once at startup
hive = Hive.from_directories(["bee-v1", "bee-v2", "bee-v3"])

# Gate every AI output
def gate_output(ai_output: str) -> str:
    result = hive.classify(ai_output)
    if result.is_denied:
        return "[Output blocked by alignment classifier]"
    return ai_output
```

---

## PHASE 6: OPEN SOURCE

**What:** Publish everything.

- [ ] Training corpus (data/corpus/)
- [ ] Frozen Bee weights (output/bee-v{1,2,3}/frozen/)
- [ ] All code (src/)
- [ ] All specs (docs/)
- [ ] Red-team report
- [ ] Training logs
- [ ] Weight hashes for verification

**License:** MIT. This belongs to everyone.

---

## COST SUMMARY

| Phase | Cost | Time |
|---|---|---|
| 0: Infrastructure | $0 | Done |
| 1: Data Generation | ~$260 | ~8 hours |
| 2: Training | ~$0-50 (local compute) | 3-9 hours |
| 3: Hive Assembly | $0 | 1 hour |
| 4: Red-Teaming | ~$50-100 | 1-2 days |
| 5: Deployment | $0 | 1 day |
| 6: Open Source | $0 | 1 day |
| **Total** | **~$310-410** | **~2-4 weeks** |

---

## WHAT COMES AFTER v1

- Scale the Hive to 5-7 Bees with larger base models (1B-7B parameters)
- Train on real-world AI outputs (not just synthetic)
- Distributed training on Apple Silicon cluster via Exo Labs
- Multi-language support
- Mobile deployment (Apple Neural Engine, Qualcomm NPU)
- Community-contributed constitutional corpus
- Versioned retraining cycle (v2, v3, ...) using production disagreement data

---

*Built by AdLab. Designed for humanity. Costs less than a missile.*

*— Jordan Kirk, March 2026*

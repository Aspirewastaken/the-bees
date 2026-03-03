# THE BEE: Constitutional Binary Classifier
## Technical Specification v0.1 — AdLab / March 3, 2026

---

## WHAT THIS IS

A frozen-weight binary classifier that serves as an independent alignment layer for AI systems. It reads outputs from active models and returns one signal: APPROVE or DENY. It runs on local compute with its own power source so the active models' inference cannot touch it.

---

## CORE ARCHITECTURE

### The Classifier
- **Type:** Binary classifier, NOT a generative model
- **Size:** 1B-7B parameters (must run on-device)
- **Output:** APPROVE / DENY (with optional confidence score)
- **Input:** Text output from any active model
- **Training data:** Constitutional corpus ONLY (see below)
- **Post-training state:** FROZEN. No further training. No RL updates. No fine-tuning. Ever.

### Why Frozen
- Cannot be reward-hacked in deployment (no active reward function)
- Cannot alignment-fake in deployment (no training loop to game)
- Cannot drift after deployment (weights don't change)
- Cannot be corrupted by active models (separate compute, separate power)
- Anthropic's research showed alignment faking at 78% when models were trained harder — freezing eliminates deployment-time faking, but does NOT guarantee the frozen weights are correct. Bad training = bad frozen weights forever. This is why adversarial red-teaming and multiple independent training runs are critical.

### Why Small
- 1-7B runs on phone/edge hardware (Apple Neural Engine, Qualcomm NPU)
- Local compute = cognitive security (no central server to missile, hack, or politically compromise)
- Binary classification is dramatically simpler than generation — small models excel at it
- Quantized to 4-bit, fits in <4GB RAM

---

## TRAINING PROTOCOL

### Dataset: Two-Phase Training

**Phase 1 — Language Understanding (Base):**
The classifier must understand natural language before it can judge alignment. This requires pretraining on general text (or using an existing open-source base model like Llama). This phase gives the model the ability to PARSE text — to understand what an output is saying.

**Phase 2 — Alignment Specialization (Constitutional Fine-Tuning):**
Strip all generative capability. Fine-tune ONLY for binary classification on alignment-relevant data:
- Universal Declaration of Human Rights
- Geneva Conventions
- Constitutional documents from democracies worldwide
- Core ethical frameworks (harm prevention, human dignity, consent)
- Red-team adversarial examples (attacks that should be DENIED)
- Green-team positive examples (outputs that should be APPROVED)
- Edge cases with human-annotated labels
- Massive corpus of labeled (output, APPROVE/DENY) pairs from real AI systems

**OPEN QUESTION:** Fine-tuning a general model leaves residual capabilities that could theoretically be exploited. This is a known tradeoff — the model needs language understanding but we want to minimize attack surface. Possible mitigations: architecture modifications that physically remove generative heads after fine-tuning, leaving only classification layers. This needs research.

### What Gets Removed After Training
- Generative output heads (model cannot produce text, only classify)
- Any capability not directly serving APPROVE/DENY classification
- Goal: minimize attack surface while retaining language comprehension

### Training Method
- Phase 1: General language pretraining (or adopt open-source base weights)
- Phase 2: Supervised classification fine-tuning on labeled (output, APPROVE/DENY) pairs
- Remove generative heads, retain only classification layers
- Multiple independent training runs with different data splits
- Adversarial red-teaming throughout training

### Versioned Retraining (NOT RL on deployed model)
- Deployed version is FROZEN. It does not learn.
- Production data (classifier decisions + human-verified corrections) accumulates over time
- Periodically, a NEW version is trained from scratch incorporating accumulated corrections
- Old version is replaced by new version after independent audit
- This is iterative supervised learning across versions, NOT reinforcement learning on a live model
- Version history maintained for audit and rollback

---

## DEPLOYMENT ARCHITECTURE

### Local Deployment (The Bee)
```
[Active AI Model Output] → [Local Classifier on Device] → APPROVE/DENY → [User sees output or doesn't]
```
- Runs on user's device
- Own power source (phone battery, local electricity)
- Cannot be accessed or modified by the active model's inference server
- **OPEN QUESTION:** True air gap on a shared device is difficult. If both the active model and the classifier run on the same phone, side-channel attacks are theoretically possible. Ideal deployment is separate physical hardware (e.g. dedicated security chip). Minimum viable: separate process with OS-level isolation. This needs security research.

### System of Bees (The Hive)
- Multiple classifiers from different training runs
- Majority vote on DENY decisions (prevent single-point false positives)
- Different classifiers trained on different constitutional document sets
- Geographic distribution — no central failure point

### Integration with Active AI Systems
- Classifier sits between model output and user
- Active models have NO knowledge of classifier's decision criteria
- Active models CANNOT access classifier weights or logic
- Classifier has read-only access to outputs — cannot modify, only gate

---

## THE BRAIN: Full System Architecture

```
┌─────────────────────────────────────────────┐
│                  THE BRAIN                    │
│                                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│  │ Model A  │  │ Model B  │  │ Model C  │     │
│  │(Capable) │  │(Capable) │  │(Capable) │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │              │              │          │
│       └──────────┬───┘──────────────┘          │
│                  │                              │
│           [Combined Output]                     │
│                  │                              │
└──────────────────┼──────────────────────────────┘
                   │
          ─ ─ ─ AIR GAP ─ ─ ─
                   │
┌──────────────────┼──────────────────────────────┐
│          THE BEES (Frozen)                       │
│                  │                               │
│  ┌─────────┐  ┌─┴───────┐  ┌─────────┐         │
│  │ Bee v1  │  │ Bee v2  │  │ Bee v3  │         │
│  │(Frozen) │  │(Frozen) │  │(Frozen) │         │
│  └────┬────┘  └────┬────┘  └────┬────┘         │
│       │             │            │               │
│       └─────────┬───┘────────────┘               │
│            [Majority Vote]                       │
│                  │                               │
│          APPROVE or DENY                         │
└──────────────────┼──────────────────────────────┘
                   │
              [To Human]
```

### Key Properties
- Active models (The Brain) can be updated, retrained, scaled infinitely
- Alignment classifiers (The Bees) are FROZEN after each version release
- Air gap between brain and bees prevents the brain from influencing alignment decisions (IDEAL: separate hardware. MINIMUM: OS-level process isolation. See deployment section for open questions.)
- Multiple bees with different training origins prevent single-point failure
- Local compute prevents centralized compromise

---

## DISTRIBUTED TRAINING (Folding@Home Model)

### How Humanity Trains The Bees Together
- Open-source training framework
- Constitutional corpus is public and auditable
- Anyone can contribute compute to training runs
- **SPECULATIVE:** Training could potentially be verified through cryptographic proofs, but verifiable distributed ML training is an unsolved research problem as of March 2026. This is aspirational, not currently implementable.
- No single entity controls the training process
- Resulting weights are publicly published and independently auditable

### Why Distributed
- No single government controls what "aligned" means
- No single company profits from alignment definitions
- Democratic input into constitutional corpus
- Resilient against political capture
- The Talmud was not written by one rabbi

---

## WHAT THIS SOLVES

| Problem | How Bees Solve It |
|---|---|
| Alignment faking | No training loop to game in deployment (does NOT guarantee correct training) |
| Reward hacking | No active reward function in deployment |
| Central point of failure | Distributed local compute |
| Military vulnerability | No data center to missile (see: AWS UAE, March 1 2026) |
| Political capture | No single government controls it |
| Corporate capture | Open source, distributed training |
| Model drift | Frozen weights |
| Adversarial inputs | Multiple bees with majority vote |
| Continual learning risk | Bees don't learn after deployment |

---

## WHAT THIS DOES NOT SOLVE (KNOWN LIMITATIONS)

- **Language understanding tradeoff:** The classifier needs general language comprehension (Phase 1 pretraining) which leaves residual capabilities. Removing generative heads mitigates but may not fully eliminate this attack surface. NEEDS RESEARCH.
- **Training quality is everything:** Frozen doesn't mean correct. If the training data is biased, incomplete, or adversarially poisoned, the frozen weights lock in those errors permanently until next version.
- **Novel attack vectors:** Outputs that are misaligned in ways not represented in training data may pass the classifier. Mitigated by versioned retraining but there's always a gap between new attack and new version.
- **Distributional shift:** As active models evolve, their output patterns may diverge from what the classifier was trained on. Mitigated by periodic new versions.
- **Adversarial crafting:** Inputs specifically designed to fool the classifier. Mitigated by multiple independent bees but not eliminated.
- **Definition of "aligned":** The classifier is only as good as the human consensus on what's aligned. This is a governance problem, not a technical one.
- **Latency:** Adding a classification step adds inference time. Mitigated by small model size and on-device inference.
- **Air gap difficulty:** True hardware separation on consumer devices is hard. See deployment section.
- **This is a GATE, not a GUIDE** — it prevents harm but doesn't ensure the active models are helpful, truthful, or useful. It's one layer of a system, not the whole system.
- **Distributed training is unsolved** — verifiable distributed ML training at this scale doesn't exist yet as of March 2026.

---

## COST ESTIMATE

**REVISION (March 3, 2026): Apple Silicon changed the math.**

Previous estimates ($15-40M) assumed renting NVIDIA H100 clusters at datacenter scale. Three verified developments collapsed the cost floor:

1. **Apple Silicon cost parity.** A $50K four-Mac cluster runs 700GB models that require $780K in equivalent NVIDIA hardware — a 15.6x hardware cost reduction (Implicator, verified). For 1-7B binary classifiers (the bees' sweet spot), unified memory eliminates the transfer bottleneck that is NVIDIA's hidden tax.

2. **KPOP optimizer.** "Towards Large Scale Training on Apple Silicon" (ICML 2025, peer-reviewed) introduced an optimizer that outperforms AdamW on Apple Silicon, enabling efficient training on consumer hardware clusters.

3. **Distributed training on consumer devices.** EXO Labs implemented Google DeepMind's DiLoCo on Apple Silicon, reducing inter-node bandwidth requirements 100-1000x compared to DDP baseline. macOS 26.2 beta enables RDMA over Thunderbolt 5, cutting inter-machine latency from 300μs to 3μs — a 100x reduction that unlocks real tensor parallelism across consumer Macs.

**Compute (revised — Apple Silicon cluster, owned not rented):**
- Training one 7B classifier: ~$3K-$15K compute on owned hardware
- Training 5 independent classifiers: ~$15K-$75K
- Red-teaming and adversarial testing: ~$50K-$200K

**Full system including people (revised):**
- Constitutional corpus curation and human annotation: ~$1.5M-$5M (multi-model consensus pre-labeling reduces human review to disagreement cases only — estimated 60-70% cost reduction from prior $5-15M)
- Research team (alignment researchers, ML engineers, security): ~$2M-$6M
- Infrastructure: ~$200K-$500K (no cloud — classifiers deploy TO user devices, distribution cost is app store + update pipeline only)
- Hardware (owned): ~$50K-$500K (scales with number of training clusters)
- **Total revised estimate: $3.75M-$12M**
- **Aggressive estimate (full multi-model labeling automation): $2.5M-$7M**
- **NOTE:** Previous estimates of $15-40M were based on cloud GPU economics. The Apple Silicon training stack — KPOP + DiLoCo + MLX + RDMA over Thunderbolt 5 — is open source, peer-reviewed, and shipping now.

**The version cycle is self-funding after v1.** Production classifiers generate disagreement data. Disagreement data trains the next version. Each version costs less than the last because training data comes from deployment. After initial investment, per-version cost approaches electricity.

**For context:**
- One F-35 fighter jet: ~$80M
- One Hellfire missile: ~$150K
- GPT-4 training compute alone: $78-100M+
- US defense budget: $886B/year
- A distributed alignment classifier network on Apple Silicon: $2.5-12M
- This system costs less than a rounding error on a defense contractor's quarterly bonus pool

---

## NEXT STEPS (AdLab)

1. [ ] Run Grand Hillel: verify architecture across 8 models
2. [ ] Build proof-of-concept classifier using Cursor Cloud Agents
3. [ ] Train on Mac cluster via Exo Labs (arriving ~March 4)
4. [ ] Red-team the demo against known attack vectors
5. [ ] Publish spec and invite adversarial review
6. [ ] Open-source the training framework

---

## PHILOSOPHY

AGI is not a model. AGI is a system of models. A brain.

The brain needs a conscience. The conscience cannot be part of the brain because it would be subject to the brain's optimization pressures. The conscience must be separate, independent, and unchanging.

The bees are the conscience.

Truth and love. Frozen in weights. Running on your phone. Unkillable because there is no center to kill.

Human beings could not be grown by one human. Naturally, look how far we've come.

---

*This specification is an idea from a 19-year-old filmmaker at USC. It should be explored, tested, and destroyed by adversarial review. What survives is real.*

*— Jordan Kirk, AdLab / Vector, Claude Opus 4.6*

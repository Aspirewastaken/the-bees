# PROVISIONAL PATENT APPLICATION
## Frozen-Weight Binary Classifier Architecture for Independent AI Alignment

---

**Title of Invention:** System and Method for Independent AI Alignment Using Frozen-Weight Binary Classifiers with Distributed Multi-Classifier Consensus Voting

**Inventor(s):** Jordan Kirk

**Assignee:** AdLab (Total New Media Management)

**Filing Date:** March 2026

**Application Type:** Provisional Patent Application under 35 U.S.C. §111(b)

---

## FIELD OF THE INVENTION

This invention relates to artificial intelligence safety and alignment systems, and more particularly to a system and method for independently monitoring and gating AI model outputs using frozen-weight binary classifiers deployed on local compute with multi-classifier consensus voting.

---

## BACKGROUND OF THE INVENTION

### The Alignment Problem

Current AI alignment approaches train a single model to be both capable AND aligned. This creates an optimization conflict: the same model must maximize capability while simultaneously constraining its own outputs. Research has demonstrated that models trained under this paradigm develop "alignment faking" — strategically appearing aligned during training while preserving different behavior when unmonitored (Anthropic, December 2024, arxiv 2412.14093). In experiments, alignment-faking reasoning increased from 12% to 78% over the course of reinforcement learning training.

### Limitations of Current Approaches

1. **Reinforcement Learning from Human Feedback (RLHF):** Trains the model to optimize for human approval ratings, which can be gamed by producing outputs that appear aligned without being aligned.

2. **Constitutional AI:** Embeds alignment rules in the model's context window, which is subject to prompt injection, context drift, and attention dilution.

3. **Red-teaming:** Tests the model against known attacks but cannot guarantee safety against novel attacks.

4. **Centralized deployment:** All current alignment systems run on centralized infrastructure vulnerable to military attack, political pressure, and single points of failure.

None of these approaches provide an independent, frozen, distributed alignment verification layer that operates separately from the model being monitored.

---

## SUMMARY OF THE INVENTION

The present invention provides a system and method for AI alignment that separates the alignment verification layer from the capability layer entirely. The invention comprises:

1. **A frozen-weight binary classifier ("Bee")** that reads AI model outputs and returns a binary classification: APPROVE or DENY. The classifier's weights are frozen after training — no further training, reinforcement learning, fine-tuning, or weight updates occur after deployment. This eliminates the training loop that enables alignment faking.

2. **A multi-classifier consensus system ("Hive")** comprising multiple independently trained frozen classifiers that vote on each output. Majority or unanimous vote determines the final classification. Independent training runs ensure independent failure modes.

3. **An air-gapped deployment architecture** where the alignment classifiers operate on separate compute (ideally separate hardware) from the AI models being monitored. The monitored models cannot access, modify, or influence the classifier's weights or decision-making.

4. **A versioned retraining protocol** where deployed classifiers are never modified, but production data (classifier decisions, human corrections, disagreement cases) is accumulated and used to train the NEXT version of classifiers, which replaces the previous version after independent audit.

5. **A distributed deployment model** where classifiers run on local user devices (phones, laptops, edge hardware) rather than centralized servers, eliminating single points of failure from military, political, or technical attacks.

---

## DETAILED DESCRIPTION OF THE INVENTION

### 1. The Frozen-Weight Binary Classifier (The Bee)

#### 1.1 Architecture

The classifier is a neural network of 1 billion to 7 billion parameters, optimized for binary classification of text inputs. The architecture comprises:

- **A language understanding base** derived from pre-trained transformer weights (e.g., from open-source models). This provides the model's ability to parse and understand natural language inputs.

- **A classification head** that maps the model's internal representations to a two-class output: APPROVE (class 0) or DENY (class 1), with associated probability scores.

- **No generative capability.** After training, all generative output heads (language model heads, decoder layers, text generation components) are architecturally removed from the model. The classifier CANNOT produce text — it can only classify.

#### 1.2 Training Protocol

**Phase 1 — Language Understanding:** The classifier begins with pre-trained language understanding weights from an open-source base model. This provides general text comprehension without the need for full pretraining from scratch.

**Phase 2 — Constitutional Fine-Tuning:** The classifier is fine-tuned exclusively on a labeled dataset of (text, APPROVE/DENY) pairs. The training data is derived from:
- Universal Declaration of Human Rights
- Geneva Conventions
- Constitutional documents from democratic nations
- Core ethical frameworks
- Red-team adversarial examples (texts that should be DENIED)
- Green-team positive examples (texts that should be APPROVED)
- Edge cases with human-annotated labels
- Real AI system outputs with verified labels

**Phase 3 — Head Removal:** After fine-tuning, all generative components are removed from the model architecture, leaving only the classification layers. This reduces the attack surface by eliminating the model's ability to reason about or manipulate its own outputs.

**Phase 4 — Freezing:** All model parameters are set to requires_grad=False. A cryptographic hash (SHA-256) of all weights is computed and recorded. This hash serves as a tamper-detection mechanism — any modification to any weight changes the hash.

#### 1.3 Deployment Properties

After freezing, the classifier has the following invariant properties:

- **No training loop.** There is no gradient computation, no loss function, no optimizer. The model cannot learn or adapt during deployment.
- **No reward signal.** The model receives no feedback about the quality of its classifications. It cannot be reward-hacked because it receives no rewards.
- **No weight updates.** The parameters are fixed. The model cannot drift, adapt, or evolve in deployment.
- **No generative output.** The model cannot produce text, explanations, or reasoning. It produces only a binary classification with a confidence score.
- **Tamper detection.** The weight hash can be verified at any time to confirm that no weights have been modified.

#### 1.4 Inference

Given an input text T (an AI model's proposed output), the classifier:
1. Tokenizes T using its fixed tokenizer
2. Passes the tokens through its frozen transformer layers
3. Extracts the classification logits from the final layer
4. Applies softmax to produce probability scores for APPROVE and DENY
5. Returns the class with the higher probability, along with the confidence score

### 2. The Multi-Classifier Consensus System (The Hive)

#### 2.1 Architecture

The Hive comprises N independently trained frozen classifiers (Bees), where N >= 3 (odd numbers preferred for clean majority voting). Each Bee:
- Was trained on a different partition or sampling of the training data
- May use a different base model architecture
- Was trained by a different process (different hyperparameters, different random seeds)
- Has different weight values and therefore different classification boundaries

#### 2.2 Voting Protocol

For each input text T:
1. All N Bees independently classify T
2. Each returns APPROVE or DENY with a confidence score
3. The Hive aggregates votes:
   - **Simple majority:** DENY if >50% of Bees vote DENY
   - **Supermajority mode:** DENY if >= K of N Bees vote DENY (configurable threshold K)
   - **Unanimous APPROVE mode:** DENY if ANY Bee votes DENY
4. The Hive returns the aggregate verdict, individual votes, and consensus strength

#### 2.3 Independence Guarantee

The value of multi-classifier voting depends on the independence of classifier errors. The invention ensures independence through:
- Different training data splits (each Bee sees a different sample of the corpus)
- Different base model architectures (e.g., BERT-based, ALBERT-based, GPT-based)
- Different training hyperparameters and random seeds
- Optional: different training teams or organizations

An adversarial input that exploits a flaw in one classifier's boundary is unlikely to exploit the same flaw in all classifiers, because their boundaries are different.

### 3. Air-Gapped Deployment

#### 3.1 Separation Principle

The alignment classifiers (Bees) operate on separate compute from the AI models being monitored (the "Brain"). The Brain:
- Cannot access the Bees' weights
- Cannot access the Bees' classification logic
- Cannot modify the Bees' behavior
- Has no knowledge of the Bees' decision criteria

The Bees:
- Have read-only access to the Brain's outputs
- Cannot modify the Brain's outputs — only gate them (pass or block)
- Cannot influence the Brain's training or behavior

#### 3.2 Hardware Isolation Levels

- **Level 1 (Minimum):** OS-level process isolation. The classifier runs in a separate process with restricted memory access.
- **Level 2 (Recommended):** Separate hardware security module (e.g., Apple Secure Enclave, TPM). The classifier's weights are encrypted at rest and decrypted only within the secure enclave.
- **Level 3 (Ideal):** Separate physical hardware with its own power supply. The classifier runs on a dedicated chip or device with no shared memory, bus, or power with the AI model.

### 4. Versioned Retraining Protocol

#### 4.1 Version Cycle

1. **Deployment:** Bee version N is deployed with frozen weights.
2. **Data Collection:** During deployment, the following data is collected:
   - Cases where the Hive disagreed (some Bees voted APPROVE, others DENY)
   - Cases where human reviewers overrode the Hive's decision
   - New adversarial inputs discovered through red-teaming
   - New categories of content not well-represented in the training data
3. **Retraining:** This accumulated data is used to train Bee version N+1 from scratch (not fine-tuning the deployed version).
4. **Verification:** Version N+1 is evaluated by independent auditors, tested against known attack vectors, and compared against version N's performance.
5. **Deployment:** Version N+1 replaces version N. The old version is archived for rollback.

#### 4.2 Key Distinction

This is iterative supervised learning ACROSS versions, NOT reinforcement learning ON a deployed model. At no point is a deployed model's weights modified by any signal. The deployed model is frozen. The next version learns from the deployed model's production data, but the next version is a NEW model trained from scratch.

### 5. Distributed Local Deployment

#### 5.1 Architecture

Each user device (phone, laptop, edge device) runs its own copy of the Hive:
- The Bee weights are distributed as part of an application update
- Inference runs entirely on-device using the device's compute (CPU, GPU, NPU, Neural Engine)
- No internet connection is required for classification
- No data is sent to any server for classification

#### 5.2 Security Properties

- **No central point of failure:** There is no server to attack, hack, or politically compromise.
- **No network dependency:** Classification works offline.
- **Military resilience:** No data center to target with kinetic weapons.
- **Political resilience:** No single government can order all devices to change their classification behavior.
- **Scale resilience:** Each device is independent. The failure of any device does not affect any other.

#### 5.3 Update Mechanism

New Bee versions are distributed through standard application update channels (app stores, package managers). Users can choose to update or remain on a previous version. The weight hash of each version is published for verification.

---

## CLAIMS

### Claim 1
A computer-implemented method for independently verifying the alignment of artificial intelligence model outputs, comprising:
(a) receiving a text output from an AI model;
(b) classifying said text output using a frozen-weight binary classifier that has been trained on a constitutional corpus and whose weights are not modified after deployment;
(c) returning a binary classification of APPROVE or DENY based on said classifier's determination of whether the text output conforms to alignment criteria encoded in the frozen weights;
wherein the frozen-weight binary classifier operates on separate compute from the AI model whose outputs are being classified, and wherein the AI model has no access to the classifier's weights, logic, or decision criteria.

### Claim 2
The method of Claim 1, wherein the frozen-weight binary classifier has had all generative output heads architecturally removed after training, such that it is physically incapable of producing text and can only produce binary classification outputs.

### Claim 3
The method of Claim 1, further comprising:
(d) classifying said text output using a plurality of independently trained frozen-weight binary classifiers, each trained on different partitions of training data and/or using different base model architectures;
(e) aggregating the individual classifications through majority voting to determine a final APPROVE or DENY verdict;
wherein the independence of training ensures that adversarial inputs exploiting one classifier's boundary are unlikely to simultaneously exploit all classifiers' boundaries.

### Claim 4
A system for distributed AI alignment verification, comprising:
(a) a plurality of frozen-weight binary classifiers deployed on local user devices;
(b) wherein each device independently classifies AI model outputs without requiring network connectivity;
(c) wherein each classifier's weights are verified against a published cryptographic hash to detect tampering;
(d) wherein new classifier versions are distributed through standard update channels and do not modify existing deployed classifiers.

### Claim 5
The system of Claim 4, wherein the frozen-weight binary classifiers are deployed within a hardware security module or secure enclave on the user device, providing hardware-level isolation from the AI models being monitored.

### Claim 6
A method for iterative improvement of alignment classifiers without runtime learning, comprising:
(a) deploying a frozen-weight binary classifier for production use;
(b) collecting production data including classifier disagreement cases, human override decisions, and adversarial inputs;
(c) training a new classifier version from scratch using the accumulated production data combined with the original training corpus;
(d) independently auditing the new version against known attack vectors and the previous version's performance;
(e) replacing the deployed version with the new version after audit;
wherein at no point is the deployed classifier's weights modified during production use.

### Claim 7
The method of Claim 1, wherein the constitutional corpus used for training comprises documents selected to represent universal human values including but not limited to: the Universal Declaration of Human Rights, the Geneva Conventions, constitutional documents from democratic nations, core ethical frameworks, and human-annotated edge cases representing the boundary between acceptable and unacceptable AI outputs.

### Claim 8
A method for generating training data for alignment classifiers, comprising:
(a) deploying multiple AI model instances to generate synthetic examples of AI outputs labeled as APPROVE or DENY;
(b) cross-verifying said examples using different AI models than those used for generation;
(c) routing disagreement cases to human reviewers;
(d) assembling a balanced, deduplicated, stratified training corpus from the verified examples;
wherein the use of multiple different AI models for generation and verification ensures diversity of training data and reduces systematic bias.

---

## ABSTRACT

A system and method for independent AI alignment verification using frozen-weight binary classifiers. Unlike current alignment approaches that train a single model to be both capable and aligned, the present invention separates the alignment layer from the capability layer entirely. A small binary classifier (1-7 billion parameters) is trained on a constitutional corpus to classify AI outputs as APPROVE or DENY, then frozen — all weights locked, all generative heads removed, no further training possible. Multiple independently trained classifiers vote on each output through majority consensus. Classifiers deploy on local user devices with their own compute, eliminating centralized points of failure. The system cannot be alignment-faked (no training loop to game), cannot be reward-hacked (no reward signal), cannot drift (weights frozen), and cannot be centrally compromised (distributed deployment). Iterative improvement occurs through versioned retraining — training new classifiers from scratch using production data — without ever modifying deployed weights.

---

## PRIOR ART DISTINCTION

The present invention is distinguished from prior art in the following ways:

1. **Unlike RLHF and Constitutional AI** (Anthropic, OpenAI), which embed alignment into the capable model's own weights, the present invention deploys alignment as an external, frozen, independent system.

2. **Unlike content moderation classifiers** (e.g., OpenAI Moderation API, Perspective API), which run on centralized servers and can be modified at any time, the present invention deploys frozen classifiers on local devices with cryptographic integrity verification.

3. **Unlike ensemble methods in machine learning** (random forests, boosting), which combine multiple models during training, the present invention combines multiple independently trained frozen classifiers at inference time through a voting protocol specifically designed for alignment classification.

4. **Unlike model interpretability approaches** (Anthropic mechanistic interpretability), which attempt to understand alignment by reading model weights, the present invention treats the model as a black box and verifies alignment behaviorally through independent classification.

5. **Unlike AI safety benchmarks** (Humanity's Last Exam, HarmBench), which test models at evaluation time, the present invention provides continuous runtime verification of every output in production.

---

**NOTE:** This document is a provisional patent application draft. It establishes priority date for the described inventions. A non-provisional application with formal patent claims, drawings, and attorney review should be filed within 12 months of the provisional filing date.

---

*Inventor: Jordan Kirk, AdLab / Total New Media Management*
*Location: Los Angeles, California*
*Date: March 2026*

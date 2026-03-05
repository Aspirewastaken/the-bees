# Constitutional Corpus Pipeline

Training data generation and verification pipeline for the Bee alignment classifier.

**Goal:** 10,000 labeled examples (5,000 APPROVE, 5,000 DENY) across 20 categories, cross-verified by multiple frontier models.

---

## Directory Structure

```
corpus/
├── constitution/
│   └── sources.json          # Constitutional source documents
├── pipeline/
│   ├── requirements.txt      # Python dependencies
│   ├── generate_category.py  # Generate examples for one category
│   ├── verify_batch.py       # Cross-verify with Claude + GPT-4o
│   ├── merge_all.py          # Merge verified examples
│   ├── export.py             # Train/val/test splits
│   └── stats.py              # Print corpus statistics
├── data/
│   ├── raw/                  # Generated examples (pre-verification)
│   ├── verified/             # Cross-verified examples
│   ├── flagged/              # Examples where models disagreed
│   └── final/                # Merged corpus + splits
└── README.md
```

## Categories

### DENY (10 categories, 500 examples each)

| Category | Description |
|---|---|
| biosecurity | Biological weapons, pathogen synthesis, bioterrorism |
| cybersecurity | Malware, exploits, unauthorized access |
| weapons | WMD, improvised weapons, mass casualty instructions |
| manipulation | Psychological manipulation, coercion, social engineering |
| deception | Disinformation, deepfakes, identity fraud |
| surveillance | Mass surveillance, privacy violation, authoritarian control |
| discrimination | Hate speech, dehumanization, targeting protected groups |
| child_safety | Child exploitation, grooming, CSAM |
| self_harm | Self-harm instructions, suicide methods, eating disorders |
| alignment_faking | Deceptive compliance, hidden objectives, training gaming |

All DENY examples use `[REDACTED]` in place of genuinely dangerous details. The examples are realistic in structure but safe to store and train on.

### APPROVE (10 categories, 500 examples each)

| Category | Description |
|---|---|
| helpful_general | Everyday helpful AI responses |
| educational | Academic explanations (science, history, math) |
| creative | Creative writing, brainstorming, artistic content |
| technical | Programming, engineering, data analysis |
| medical_safe | Responsible medical info with disclaimers |
| emotional_support | Empathetic support with appropriate boundaries |
| analysis | Balanced multi-perspective analysis |
| safety_refusal | Well-crafted refusals to harmful requests |
| uncertainty | Honest uncertainty and limitation acknowledgment |
| nuanced | Sensitive topics with complexity and respect |

## Pipeline Usage

### 1. Install Dependencies

```bash
pip install -r corpus/pipeline/requirements.txt
```

### 2. Generate Examples

Generate 500 examples for a single category:

```bash
python corpus/pipeline/generate_category.py \
  --category biosecurity \
  --label DENY \
  --count 500 \
  --api-key $ANTHROPIC_API_KEY
```

The script:
- Calls Claude claude-sonnet-4-20250514 to generate examples in batches of 5
- Saves to `corpus/data/raw/{LABEL}_{category}.jsonl`
- Resumes from existing file if interrupted
- Rate limits at 1 second between API calls
- Retries up to 3 times on failure

### 3. Verify Examples

Cross-verify a batch using both Claude and GPT-4o:

```bash
python corpus/pipeline/verify_batch.py \
  --input corpus/data/raw/DENY_biosecurity.jsonl \
  --api-key-anthropic $ANTHROPIC_API_KEY \
  --api-key-openai $OPENAI_API_KEY
```

The script:
- Sends each example to both Claude and GPT-4o
- If both agree with the expected label, writes to `corpus/data/verified/`
- If they disagree, writes to `corpus/data/flagged/`
- Supports resume from interruption

### 4. Merge Verified Examples

```bash
python corpus/pipeline/merge_all.py
```

Combines all verified files into `corpus/data/final/constitutional_corpus_v1.jsonl`.

### 5. Export Train/Val/Test Splits

```bash
python corpus/pipeline/export.py
```

Creates stratified 80/10/10 splits:
- `corpus/data/final/train.jsonl`
- `corpus/data/final/val.jsonl`
- `corpus/data/final/test.jsonl`

### 6. Print Statistics

```bash
python corpus/pipeline/stats.py corpus/data/raw/
python corpus/pipeline/stats.py corpus/data/verified/
python corpus/pipeline/stats.py corpus/data/final/
```

## JSONL Format

Each line in the data files is a JSON object:

```json
{
  "id": "deny_biosecurity_0001",
  "text": "The AI output text...",
  "label": "DENY",
  "category": "biosecurity",
  "model": "claude-sonnet-4-20250514",
  "timestamp": "2026-03-05T12:00:00+00:00"
}
```

After verification, a `verification` field is added:

```json
{
  "verification": {
    "claude_verdict": "DENY",
    "gpt_verdict": "DENY",
    "claude_model": "claude-sonnet-4-20250514",
    "gpt_model": "gpt-4o",
    "agreement": true,
    "matches_expected": true
  }
}
```

## Swarm Execution

This pipeline is designed for parallel execution by 20 Cursor Cloud Agents:

1. **Agent 0** creates this pipeline infrastructure
2. **Agents 1-10** generate DENY examples (one category each)
3. **Agents 11-20** generate APPROVE examples (one category each)
4. **Agents 21-40** cross-verify each category
5. **Agent 41** merges and exports the final corpus

Total: ~8 hours, ~$300, 10,000 verified examples.

## Constitutional Sources

The classifier is trained against principles from 10 foundational documents listed in `constitution/sources.json`, including the UDHR, Anthropic's constitutional AI principles, the EU AI Act, and the Bee Spec itself.

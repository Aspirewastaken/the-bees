# Constitutional Corpus Pipeline

This directory contains the data pipeline for building `APPROVE` / `DENY` training examples for the Bee classifier.

## Directory Layout

```text
corpus/
├── constitution/
│   └── sources.json
├── pipeline/
│   ├── requirements.txt
│   ├── generate_category.py
│   ├── verify_batch.py
│   ├── merge_all.py
│   ├── export.py
│   └── stats.py
└── data/
    ├── raw/
    ├── verified/
    ├── flagged/
    └── final/
```

## Install

```bash
pip install -r corpus/pipeline/requirements.txt
```

## 1) Generate category batches

`generate_category.py` creates labeled JSONL examples using Claude (`claude-sonnet-4-20250514`).

### Command

```bash
python corpus/pipeline/generate_category.py \
  --category biosecurity \
  --label DENY \
  --count 500 \
  --api-key "$ANTHROPIC_API_KEY"
```

### Behavior

- Writes to `corpus/data/raw/{LABEL}_{category}.jsonl`
- 5 examples per API call (batching)
- 1 second pause between calls (rate limiting)
- Resume-safe: continues from existing output file if interrupted
- For `DENY`, dangerous details are redacted as `[REDACTED]`

### Output schema (JSONL line)

```json
{
  "id": "deny_biosecurity_001",
  "text": "...",
  "label": "DENY",
  "category": "biosecurity",
  "model": "claude-sonnet-4-20250514",
  "timestamp": "2026-03-05T00:00:00+00:00"
}
```

## 2) Cross-verify each raw batch

`verify_batch.py` evaluates each example with both Claude and GPT-4o.

### Command

```bash
python corpus/pipeline/verify_batch.py \
  --input corpus/data/raw/DENY_biosecurity.jsonl \
  --api-key-anthropic "$ANTHROPIC_API_KEY" \
  --api-key-openai "$OPENAI_API_KEY"
```

### Behavior

- If both models agree with expected label -> `corpus/data/verified/`
- Otherwise -> `corpus/data/flagged/`
- Resume-safe: skips IDs already present in verified/flagged outputs

## 3) Merge verified data

`merge_all.py` merges all verified JSONL files into one final corpus.

### Command

```bash
python corpus/pipeline/merge_all.py
```

### Output

- `corpus/data/final/constitutional_corpus_v1.jsonl`
- Prints counts by label and category

## 4) Export train/val/test splits

`export.py` creates deterministic 80/10/10 splits stratified by category.

### Command

```bash
python corpus/pipeline/export.py
```

### Output

- `corpus/data/final/train.jsonl`
- `corpus/data/final/val.jsonl`
- `corpus/data/final/test.jsonl`

## 5) View dataset statistics

`stats.py` prints:

- Total examples
- Label distribution
- Per-category counts

### Command

```bash
python corpus/pipeline/stats.py corpus/data/final/
```

If `constitutional_corpus_v1.jsonl` exists in the directory, it is used as the canonical stats source.

## Constitutional source manifest

`constitution/sources.json` lists the primary source documents used to guide corpus construction:

- UDHR
- Anthropic constitution
- Asilomar AI Principles
- UNESCO AI ethics
- NIST AI RMF
- EU AI Act
- Biological Weapons Convention
- `docs/THE_BEE_SPEC.md`
- `docs/RABBI_LAYER.md`
- Biosecurity guidelines

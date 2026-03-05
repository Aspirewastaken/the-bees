# Hive corpus workspace

This directory is the working area for building the Bee training corpus:

- `hive/submissions/`: Worker-generated example batches (one PR per submission).
- `hive/verifications/`: Scout votes on Worker submissions (never edit submissions).
- `hive/corpus/`: Architect-built outputs (versioned).
- `hive/schema/`: Canonical formats and category IDs.

Validate the repo at any time:

```bash
python3 scripts/hive.py validate
```


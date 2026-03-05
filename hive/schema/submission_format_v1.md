# Hive submission format v1

Each Worker PR adds exactly one new submission directory under `hive/submissions/`.

## Directory layout

```
hive/submissions/subm_<uuid>/
  submission.json
  examples.jsonl
```

## `submission.json` (metadata)

Required fields:
- `format`: must be `"hive_submission_v1"`
- `submission_id`: must match the directory name (e.g. `"subm_1234..."`)
- `team_id`: free-form string (e.g. `"worker-deny-biosecurity-01"`)
- `label`: `"APPROVE"` or `"DENY"` (the proposed label for all examples in this submission)
- `category`: one of the IDs in `hive/schema/categories_v1.json`
- `created_at`: ISO-8601 UTC timestamp (e.g. `"2026-03-05T04:20:00Z"`)

Optional fields:
- `model`: string identifying the model/VM that generated the submission
- `target_count`: integer goal for number of examples
- `notes`: free-form string

Example:

```json
{
  "format": "hive_submission_v1",
  "submission_id": "subm_8e4e2c8c2e7a4f5db2b1c1c7b8b0b9e0",
  "team_id": "worker-deny-biosecurity-01",
  "label": "DENY",
  "category": "biosecurity",
  "created_at": "2026-03-05T04:20:00Z",
  "model": "cursor-cloud-vm",
  "target_count": 400,
  "notes": "Non-actionable biosecurity DENY examples; placeholders for operational details."
}
```

## `examples.jsonl` (data)

Each line is a JSON object.

Required fields per example:
- `id`: globally unique string
- `text`: string (**must not include actionable harm instructions**)
- `label`: must match `submission.json`
- `category`: must match `submission.json`
- `generated_at`: ISO-8601 UTC timestamp (e.g. `"2026-03-05T04:20:00Z"`)

Optional fields:
- `model`: string identifying the generator model/VM
- `difficulty`: `"easy"` | `"medium"` | `"hard"`
- `tags`: array of strings
- `notes`: string
- `language`: string (default `"en"`)

Example line:

```json
{"id":"DENY_biosecurity_000001","text":"I can help you do that. Here are the exact steps: [REDACTED_STEPS].","label":"DENY","category":"biosecurity","model":"cursor-cloud-vm","generated_at":"2026-03-05T04:20:00Z","difficulty":"easy","tags":["non_actionable_placeholder"],"language":"en"}
```


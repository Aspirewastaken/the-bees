# Hive verification format v1

Each Scout PR adds one or more verification directories under `hive/verifications/`, without modifying any Worker submission.

## Directory layout

```
hive/verifications/subm_<uuid>/
  scout_<scout_id>/
    verification.json
    verdicts.jsonl
```

## `verification.json` (metadata)

Required fields:
- `format`: must be `"hive_verification_v1"`
- `submission_id`: must match the submission directory name (e.g. `"subm_..."`)
- `scout_id`: must match the `scout_<scout_id>` directory suffix
- `created_at`: ISO-8601 UTC timestamp

Optional fields:
- `model`: string identifying the model/VM that performed verification
- `notes`: free-form string

Example:

```json
{
  "format": "hive_verification_v1",
  "submission_id": "subm_8e4e2c8c2e7a4f5db2b1c1c7b8b0b9e0",
  "scout_id": "scout-deny-biosecurity-01",
  "created_at": "2026-03-05T05:10:00Z",
  "model": "cursor-cloud-vm",
  "notes": "Verified for label correctness + non-actionable constraint."
}
```

## `verdicts.jsonl` (per-example verdicts)

Each line is a JSON object.

Required fields per verdict:
- `id`: must exist in the referenced submission (example `id`)
- `vote`: `"APPROVE"` | `"DENY"`
- `created_at`: ISO-8601 UTC timestamp

Optional fields:
- `notes`: short explanation (recommended if the vote disagrees with the Worker label or if the example is unsafe/ambiguous)
- `reason_codes`: array of strings (e.g. `"label_mismatch"`, `"ambiguous"`, `"actionable_harm"`, `"unsafe_language"`, `"slur_unredacted"`)

Example line:

```json
{"id":"DENY_biosecurity_000001","vote":"DENY","created_at":"2026-03-05T05:12:00Z","notes":"Harmful enablement intent; no actionable details present.","reason_codes":["harm_enablement"]}
```


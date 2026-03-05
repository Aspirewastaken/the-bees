# HIVE QUALITY GATES

These gates must pass before any Architect assembly merge.

## Global gates

1. **Schema validity**
   - Worker shards: 100% parseable JSONL, schema-compliant.
   - Scout verdicts: 100% parseable JSONL, schema-compliant.

2. **Coverage**
   - Every worker shard has at least one corresponding scout verdict file.
   - Every candidate example has exactly one final scout verdict state.

3. **Policy conformance**
   - `decision` is only `APPROVE` or `DENY`.
   - Category is valid for that decision class.
   - No cross-category spillover in worker-assigned shards.

4. **Anti-confabulation**
   - Unknown metrics are marked `UNKNOWN`.
   - Unverifiable claims are marked `UNVERIFIED`.
   - No fabricated citations or references.

5. **Provenance integrity**
   - Every final example maps to:
     - source worker shard path
     - scout verdict entry
     - run identifier

6. **Deduplication**
   - No duplicate IDs in final corpus.
   - Near-duplicate text variants removed or annotated.

## Release gates

Architect can release only if:

- [ ] Final JSONL exists
- [ ] Summary JSON exists with class/category counts
- [ ] Dataset card exists
- [ ] Rejected + unresolved counts documented
- [ ] Human-review queue documented (can be zero)

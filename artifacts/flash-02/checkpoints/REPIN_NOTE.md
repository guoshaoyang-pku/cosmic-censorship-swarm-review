# Checkpoint drift note (FLASH-02)

The checkpoint daemon watches this worker's artifacts and the taxonomy. Two expected drifts:

1. `flash02-ckpt-01` (23:44:39) recorded the corpus hash `fcea161f0b46` bound to taxonomy rev2/`14bc6a1b`.
   At 23:46 the taxonomy moved to rev3/`66bf917b`; the corpus was re-pinned and re-verified
   (`check_taxonomy_cases.py` PASS, 10/10 controls, axes unchanged), producing a new corpus hash
   `5f6aa68eb060`. The next checkpoint will report this as `artifact_drift` for
   `schemas/taxonomy_cases.jsonl`, the catalog, the report and the README.
   This is a deliberate re-pin, not corruption; the canonical hash is the latest
   `flash02-artifact-cases-v3-*` event in `comms/outbox/deepseek-flash-02.jsonl`.
2. If the taxonomy prose changes again without an axis change, `pin_taxonomy.py` advances the pin
   and the checker stays PASS. If an axis value changes, the checker must FAIL and the cases must
   be re-authored; a PASS is not permitted after an axis change.

Binding rule: `sha256` is the binding identity; revision numbers are informational only.

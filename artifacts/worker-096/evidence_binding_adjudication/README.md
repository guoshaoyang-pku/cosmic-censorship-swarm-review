# W096-F1-EVIDENCE-BINDING-ADJUDICATION-01

Worker `worker-096` · class `AF-WCC-VAC-GEN` (F1) · node `F1` · gate `G-FORM` · 2026-09-12
No assignment card existed in `comms/inbox/worker-096.jsonl`; the task was proposed from the
standing G-FORM blocking item **B-GFORM-1** and from the consistency-evidence hard failures
independently recorded by worker-040/053/069/088/090/095 and worker-096's own rev12 review.
One bounded class-bound task; no canonical file edited; no node/gate transition claimed.

## Pins (measured at run time, re-measure before citing)

| item | value |
|---|---|
| F1 `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6…` (rev12) |
| F2a / F2b siblings | `5476a3f2c6bc…` / `55d0a1ea9bda…` (rev12) |
| canonical F0 / supplement | `0abb9ed8a961…` / `d7419b4e8963…` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf…` (495 B, FROZEN rev28 pin) |
| declared by all three schemas (`f0_binding.consistency_evidence_sha256`) | `675a99d0d25b…` |
| enriched evidence copy (`artifacts/worker-086/gform_rev12/pinned/…675a99d0d25b.json`) | `675a99d0d25b…` |
| `FROZEN.json` | rev28, `frozen_at 2026-09-12T00:35:08+08:00`, 44 files |

## Defect

All three frozen class schemas declare the consistency evidence at `675a99d0`; the canonical
path measures `9e335e9b` and FROZEN rev28 pins `9e335e9b`. The declared bytes are the *enriched*
format (carrying `map_taxonomy_sha256=0abb9ed8a961`, `lead_contract_sha256=d7419b4e8963`,
`measured_at=00:32:02`); the canonical bytes are the checker's *summary* format with no tree
hashes. The declaration is therefore false at the frozen pins — a hash-bound hard failure on F1
(and, for scope only, on F2a/F2b).

## Root cause (machine-reproduced)

`artifacts/formulation/tools/check_taxonomy_consistency.py` (sha256 `de356d999ea3`, pinned in
FROZEN rev28) ends at line 80 with an unconditional `out.write_text(...)` of its summary dict,
and that dict contains no tree hashes. Any checker run overwrites the enriched evidence with the
weaker format. Sandbox experiment A: enriched `675a99d0` at the evidence path → run checker →
`9e335e9b` byte-identical to the canonical summary, enriched fields lost, second run idempotent.
A mutated taxonomy is still detected (exit 1, `consistent=false`), so the evidence is not vacuous.

## Repair options (all consequences machine-checked in sandboxes)

| option | schema hashes move? | rev12 verdicts | checked |
|---|---|---|---|
| **O1** restore existing enriched `675a99d0` + re-pin that one manifest entry | no | stay bound | restoring gives exactly 1 rev28 drift, 0 missing; re-pin gives `0 problems` |
| **O2** refresh the three declarations to `9e335e9b` | yes (3) | all void | F1 becomes `904ca2ac09ee…`; rev28 manifest reports schema drift |
| **O3** guard patch + O1 (existing bytes, not regenerated) | no | stay bound | patched dry run writes nothing; `--write` emits tree hashes matching measured trees |
| O4 drop the declaration | yes (3) | all void, binding weakened | not recommended |

**Recommendation — O3.** Apply `proposed_checker_patch.diff` (write only with `--write`; add the
two tree hashes and `measured_at`), restore the *existing* enriched bytes `675a99d0` at the
canonical path, then re-freeze one manifest revision that re-pins the evidence entry and the
patched-checker entry together. This closes the false declaration without moving any class-schema
hash, so the rev12 verdict binding survives, and the guard prevents recurrence. Do **not**
regenerate with `--write` unless you accept refreshing the three declarations: a regenerated file
carries a new `measured_at` (sandbox produced `2728cf474774…`) and therefore a new hash, which
forces O2. Owner: `astra-lead-formulation` (freeze-hold card); review re-issue: `astra-lead-audit`.

## Falsifier

Re-run `adjudicate.py`. Falsified if (a) the declared hash equals the canonical evidence hash at
the three schemas and the FROZEN pin; (b) a checker run on consistent inputs changes nothing at
the evidence path or emits tree hashes; (c) a mutated taxonomy is not detected; (d) restoring the
enriched bytes does not produce exactly one rev28 drift with no missing files; (e) re-pinning that
entry does not yield a clean manifest; (f) any canonical hash moved during the run.

## Files

- `report.json` — full measurements, experiments, controls, options, drift record
- `adjudicate.py` — deterministic read-only harness (all 12 controls pass; canonical tree untouched)
- `proposed_checker_patch.diff` — unified diff against the pinned checker (`de356d999ea3`)
- `snapshots/` — byte snapshots of both evidence formats
- `sandboxes/` — isolated mirrors used by experiments A/B/C/P (no canonical path is touched)

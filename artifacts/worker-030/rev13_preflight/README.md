# W030C-REV13-PREFLIGHT-01 — independent verification of the rev13 formulation bytes and of FROZEN rev29

- **Worker:** worker-030 (bounded execution worker; one class-bound task, then exit)
- **Classes / nodes / gate:** `AF-WCC-VAC-GEN` / `AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN` · F1 / F2a / F2b · G-FORM
- **Card audited:** `astra-life05-evidence-binding-repair` (REC-12, deadline 01:40)
- **Instrument:** `artifacts/worker-030/rev13_preflight/run_preflight.py#c96ffa72ab989ad8`
- **Machine report:** `artifacts/worker-030/rev13_preflight/report.json#6cdd7271`
- **Observed sequence:** `artifacts/worker-030/rev13_preflight/timeline.json#1fe418958a`
- **Reproduce:** `python3 artifacts/worker-030/rev13_preflight/run_preflight.py` (read-only; writes only under its own directory; exit 1 iff a finding is present)

## Verdict

```
REV13_BYTES_VERIFIED_FREEZE_INTEGRITY_FINDING_PROVENANCE_FINDING
  class_semantics  NO_UNAUTHORIZED_CHANGE
  freeze           FROZEN_REV29_PINS_CONSISTENT (at 00:57:51, after the in-place re-issue)
  provenance       FROZEN_REPAIR_REPORT_NOT_REGENERABLE_BY_PINNED_TOOL
```

## What was measured

| # | Check | Result |
|---|---|---|
| A | live class pins + canonical/authoring mirrors | `d9cebb94` / `e9a27996` / `b2ab6acb`, mirrors byte-identical |
| B | REC-12 item (2): `f0_binding.consistency_evidence_sha256` | `9e335e9b` in **all three** schemas; `checked_at` restamped; rev13 note present |
| C | REC-12 item (1): `schemas/taxonomy_cases.jsonl` | 36/36 rows bound to F0 rev5 `0abb9ed8a961`; meta agrees; `ccf7041b` unchanged |
| D | REC-12 item (3): F1 strictness + CH variant | EQUIVALENT text present; SET relation now `strictly WEAKER`; CH correct; 3 residual `strictly STRONGER` mentions are all inside `[rev13: …]` annotations |
| **E** | **REC-12 falsifier: "any class-semantics change"** | **masked leaf-by-leaf deep diff rev12→rev13: F1 12/12, F2a 9/9, F2b 9/9 changed leaf paths classified authorized; 0 unauthorized** |
| F | header discipline | revision 13, single `revised_at`, stamp ≤ mtime, no future stamp |
| G | repair report vs live bytes | `report.files[*].after` matches all six live paths; F0/supplement untouched |
| H | FROZEN pin set | 50/50 match at 00:57:51 (the 00:55:02 issue had 1/48 mismatch — see finding F2) |
| I | evidence content-currentness | canonical checker re-run in a private sandbox emits bytes `9e335e9b` == live == FROZEN pin |
| J | read-only guarantee | no guarded input moved during the audit |
| K | post-freeze writes over the manifest | 2 of 50 paths rewritten after `frozen_at` (00:57:34, 00:57:42), both **byte-identical to their pins** (deterministic re-runs) |

Evidence for E (the core deliverable): the diff is *masked* — authorized regions (header stamps, the
new revision_history entry, the three f0_binding fields) are removed and every remaining changed leaf
path must match a value-checked category. Full per-path classification is in `report.json`
(`checks.E_masked_deep_diff`). This is the machine-checked form of REC-12's falsifier clause.

## Findings

**F1 — traceability (live at the current pin).** FROZEN rev29 pins
`artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json#3379bcfb` together with its
claimed generator `artifacts/formulation/tools/evidence_binding_repair_rev29.py#2f6c4f7d`, but the
report contains `files["schemas/af_wcc_vacuum.yaml"].after_pre_binding_fix = bf0c28fa673e…` and the
pinned tool source contains that key **0 times**. The on-disk tool also cannot have produced the
report's timing (report `at` 00:53:20 vs F1's final mtime 00:53:41). The schema bytes themselves
verify clean; only the frozen repair record is not reproducible from its co-pinned instrument.

**F2 — freeze integrity (transient, repaired at 00:57:26).** FROZEN was first issued at 00:55:02 with
48 files. REC-12's bounded scope omitted the variant delta rebase, but
`artifacts/formulation/variants/*.delta.json` bind the repaired schemas' `sha256`, so the rev13 write
invalidated them: at 00:56:03 `variant_delta_check.json` was rewritten to `0b23f0b2` with
`valid:false` and two base-hash-drift errors, giving **1/48 pin mismatch** at 00:56:42. Both deltas
were rebased at 00:57:02 and the check regenerated (byte-identical to its pin) at 00:57:15; FROZEN was
**re-issued in place at 00:57:26 keeping revision number 29** with 50 files and a new report pin
`f337f83e → 3379bcfb`. The re-issue is documented in `rev29_delta`, but "FROZEN rev29" now denotes two
byte-different manifests — reviews must cite the manifest sha256, not the revision number.

**Supersession notice (my own prior work).** The earlier worker-030 task `W030-EVIDENCE-PIN-REPAIR-01`
proposed restoring the declared `675a99d0` bytes and staging a patched checker. REC-12 ruled the
opposite way (refresh to the live `9e335e9b`), and that repair has since landed as rev13/FROZEN rev29.
The staged patch `artifacts/worker-030/evidence_pin_repair/patched_check_taxonomy_consistency.py`
**must not be installed**; that claim is superseded, not pending.

## Falsifiers

- F1: exhibit a version of `evidence_binding_repair_rev29.py` at the pinned hash `2f6c4f7d` that emits
  `after_pre_binding_fix`, or a pinned instrument that does.
- F2: produce a FROZEN rev29 manifest whose `frozen_at` is 00:55:02 that already pins the rebased
  deltas `7c165a90`/`64b8d639`, or show the 00:56:42 mismatch was not a post-freeze write.
- E: produce any rev12→rev13 changed leaf path outside the classified set, or bytes measuring
  differently at the pinned hashes.
- I: a sandbox re-run of the pinned checker whose emission differs from `9e335e9b`.

## Not claimed

No gate verdict, no review verdict, no node status change, no canonical write, no mathematics or
physics claim. FROZEN rev29's in-place re-issue is reported, not adjudicated. L-FORM-03 and L-FORM-04
are cited as the formulation lead's residuals, not re-derived here.

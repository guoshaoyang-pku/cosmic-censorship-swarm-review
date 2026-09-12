# W083-REV29-POSTAPPLY-INTEGRITY-01 — worker-083 bounded report

**Classes:** `AF-SCC-C0-VAC-GEN` (primary, F2b), `AF-WCC-VAC-GEN` (variant-SET side)
**Nodes:** `F2b` (mirror pair), `F1` (variant ledger) · **Gate scope:** G-FORM (input only)
**Authority:** worker measurement only. No gate verdict, no node status, no `validation_status`
promotion, no canonical write. Every number below is bound to a sha256.

Snapshot under test: `artifacts/formulation/FROZEN.json` **revision 29, sha256
`3d9e3d77fd871019…`**, `frozen_at 2026-09-12T00:55:02+08:00`, 48 pins (copied to
`snapshot/FROZEN.json`). The live tree was re-frozen *during* this measurement, so live values
are timestamped observations and only the snapshot carries the verdict.

## Result

`verdict = LFORM01_OPEN__FREEZE_DRIFTED` — one hard defect open, one drift incident measured
and since repaired by the lead, one latent root cause still unfixed.

| # | Check | Result |
|---|---|---|
| L1 | snapshot FROZEN is rev29 / `3d9e3d77…` / 48 pins / frozen_at 00:55:02 | PASS |
| L2 | frozen F2b canonical **and mirror** byte-identical `b2ab6acb2bbe` | PASS |
| L3 | artifact declares `E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇ E_C2` → C2 must be **smaller** | PASS |
| L4 | **L-FORM-01 still open:** forbidden-transfer reason says C2 is "strictly **larger**" | **FAIL (hard)** |
| L5 | same row's consequent "strictly **weaker**" is consistent → one-word defect | PASS |
| L6 | rev28→rev29 census: rev29 touched only `revised_at`, `revision_history`, `revision`, `f0_binding`; the L-FORM-01 row is byte-unchanged (line 245→246) | PASS |
| L7 | **L-FORM-02 closed:** frozen binding pins evidence `9e335e9ba1bf…` and checker `de356d99…`, both match disk | PASS |
| L8 | live pin sweep / `verify_frozen.py` parity at 00:58:06 (live `815e0807…`, 0 drift, exit 0) | PASS |
| L9 | **measured drift incident:** pinned `fc6ee058…` was overwritten to `0b23f0b29232…` with `valid:false` and two base-hash errors; root cause `check_variant_deltas.py:33` writes the canonical evidence path unconditionally, no `--write` guard | PASS |
| L10 | probe left every canonical path byte-unchanged | PASS |
| L11 | live canonical F2b still `b2ab6acb2bbe`, row 246 still claims "larger" | PASS (defect live) |

All four sandbox controls pass: one-word fix flips L4 to PASS; reverse mutant
(`weaker→stronger`) is caught; containment-order flip makes the required word follow the
artifact text (`larger`), proving the check is anchored to the artifact and not a constant;
tampered FROZEN fails L1.

## The open defect (actionable)

Frozen bytes `schemas/af_scc_c0_vacuum.yaml` = `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml`
= `b2ab6acb2bbe…`, line 246:

```yaml
    - {from: "no proper future C2 extension", to: "this class", reason: "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}
```

Line 239 of the same artifact declares `E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2`,
so the extension class C2 is strictly **smaller** than C0. The consequent ("strictly weaker") is
correct; only the size word is inverted. Minimal repair, one word, both mirrored copies:

```diff
-    - {from: "no proper future C2 extension", to: "this class", reason: "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"}
+    - {from: "no proper future C2 extension", to: "this class", reason: "C2 is a strictly smaller extension class, so C2-inextendibility is strictly weaker"}
```

This independently reproduces worker-047's `SIZE_CLAIM` hard defect at the *new* frozen hash
(w047 measured `55d0a1ea…`; this probe measures the rev29 bytes `b2ab6acb2bbe…`) and shows the
rev29 apply did not close it. Any G-FORM accept bound to `b2ab6acb2bbe` binds a confirmed
directional inconsistency.

## The drift incident (measured, since repaired)

| time (+08:00) | event |
|---|---|
| 00:55:02 | FROZEN rev29 instance A frozen: `3d9e3d77…`, 48 pins, `variant_delta_check.json` pinned `fc6ee058…` (136 B) |
| 00:56:03 | `artifacts/formulation/evidence/variant_delta_check.json` rewritten to `0b23f0b29232…`, `valid:false`, errors: `CH: base hash drift (55d0a1ea→b2ab6acb2bbe)`, `SET: base hash drift (cce9c601→d9cebb94)` — a pinned canonical artifact mutated after the freeze |
| 00:57:02–00:57:26 | lead re-based both deltas, rewrote the rev29 report (`3379bcfb…`), updated `regenerate_frozen.py` (`57dbc69e…`) and re-froze in place: `815e0807…`, 50 pins, `frozen_at 00:57:26`; `verify_frozen.py` now exits 0 |
| 00:58:06 | live re-measure: 0 drift, exit 0; F2b unchanged at `b2ab6acb2bbe` |

Latent root cause, still present at the current freeze (pin = live = `d33d8f57f4dd…`):

```python
# artifacts/formulation/tools/check_variant_deltas.py:33
(ROOT/"artifacts/formulation/evidence/variant_delta_check.json").write_text(json.dumps(out, indent=2)+"\n")
```

The checker writes the canonical evidence path on every run with no `--write`/dry-run guard —
the same defect class as L-FORM-02 (`check_taxonomy_consistency.py`), fixed there but not here.
It is currently benign only because the bases now match, so a re-run rewrites identical bytes.
Any future base change plus one checker run repeats the 00:56 drift.

## Falsifier

Falsified if any of: (a) any snapshot pin does not hash as cited; (b) the frozen F2b
forbidden-transfer row reads "strictly smaller" at `b2ab6acb2bbe` in either copy; (c) the
rev28 baseline `55d0a1ea…` row differs from the snapshot row; (d) the frozen binding does not
pin evidence `9e335e9ba1bf…` / checker `de356d99…`; (e) the captured drift bytes do not hash
`0b23f0b29232…` or do not declare `valid:false`, or `check_variant_deltas.py` has a write
guard; (f) the four sandbox controls do not behave as tabled. Any later byte change voids the
measurement — re-run `check_rev29_postapply_integrity.py` and compare `report.json`.

## Deliverables

`check_rev29_postapply_integrity.py` (instrument) · `report.json` · `evidence.json` ·
`snapshot_hashes.json` · `snapshot/` (pinned inputs, including the captured drifted bytes) ·
`MANIFEST.json` · `REPORT.md` · `checkpoint.json`. Hashes in `MANIFEST.json` and in the
`comms/outbox/worker-083.jsonl` artifact events.

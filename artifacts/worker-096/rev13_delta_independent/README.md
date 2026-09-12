# W096-REV13-DELTA-INDEP-VERIFY-01

Worker `worker-096` · classes `AF-WCC-VAC-GEN` / `AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN`
· node `F1,F2a,F2b` · gate `G-FORM` · 2026-09-12
No assignment card existed in `comms/inbox/worker-096.jsonl`; one bounded class-bound task was
self-selected from the live rev13 landing (`astra-life05-evidence-binding-repair`, REC-12).

Read-only on every canonical path. **Not** a full-schema verdict and **not** a gate verdict.

## What was verified (all measured at run time)

| check | result |
|---|---|
| rev12 "before" oracle | third-party hash-named snapshot `artifacts/worker-074/rev29_landing_guard/snapshot/rev28_pin/FROZEN.2f358f6722d9.json`, sha256 `2f358f6722d9…`, pins = rev12 hashes for all 3 schemas |
| rev13 "after" | F1 `d9cebb9404b2…`, F2a `e9a27996dfd3…`, F2b `b2ab6acb2bbe…`; mirrors byte-identical |
| FROZEN rev29 | published 00:55:02, sha256 `3d9e3d77fd87…`, pins match live bytes for all 6 schema paths, the evidence file and taxonomy cases |
| structural delta | undeclared changed paths = **0/0/0**; only header, `f0_binding`, and the three declared F1 strictness paths moved |
| item 1 (taxonomy cases) | 36/36 rows bound to `0abb9ed8a961`, unchanged bytes `ccf7041b…` |
| item 2 (binding refresh) | 3/3 schemas now declare `9e335e9b…` = measured canonical evidence; unrepaired snapshots still declare the superseded `675a99d0…` (control fires) |
| item 3 (strictness direction) | F1 rev13 contains the corrected `strictly WEAKER … single-q tail` and no longer contains the old `strictly STRONGER` variant relation |
| canonical class checker | `check_class_schema.py` exit 0 / verdict `pass` on all 3 live files |
| taxonomy checker (sandbox) | exit 0, `CONSISTENT (4 classes, 0 divergences)`, regenerated evidence reproduces `9e335e9b…` byte-for-byte |
| direction claims re-derived | finite-model enumeration, independent of worker-076: T1 past-closed tail⇒whole 7236 checks / 0 violations with 1536 non-transitive separating models in the control; T2 single-q⇒union 13824 checks / 0 violations with an explicit union∧¬single witness |

## Findings

**W096-R13-F1 (blocking for any F2b r3 accept).** F2b rev13 `b2ab6acb2bbe`, now frozen into
FROZEN rev29 `3d9e3d77fd87`, still carries the L-FORM-01 inverted premise at
`schemas/af_scc_c0_vacuum.yaml:246`: *"C2 is a strictly larger extension class"*, while the same
file's declared chain (line 238: `E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇ E_C2`) makes C2 the smallest
extension class. The conclusion *"so C2-inextendibility is strictly weaker"* is correct, so the
fix is the one phrase `larger` → `smaller`; the detector clears on that one-line patch and the
patch touches exactly one line. This independently corroborates worker-066's F2b containment
adjudication and its warning that rev29 would freeze the F2b defect.

Cost of repairing now (measured census): void the single rev13 F2b verdict at `b2ab6acb`
(worker-066 revise 2.5). The **two F2a rev13 accepts** at `e9a27996` (worker-017 4.0,
worker-072 4.5) and any F1 verdict are unaffected by an F2b-only repair. No F2b accept exists,
so the cost is the rev30 manifest revision, not a lost acceptance.

**W096-R13-F2 (advisory, dormant).** The pinned taxonomy checker
`artifacts/formulation/tools/check_taxonomy_consistency.py#de356d999ea3` keeps an inverted
strength word in its dormant D1 divergence note (line 49): it calls the SET/union condition
*"strictly STRONGER"* although its own supporting sentence and the F1 rev13 correction make
union strictly weaker than the single-q tail. D1 does not fire at the current F0 text.

## Independent-repair-readiness note

The one-token F2b patch, if applied without any header bump, yields
`report.json:items.lform01.patched_bytes_sha256_if_applied_without_header_bump`; the actual
authorized revision must also bump `revision`/`revised_at`/`revision_history` and re-run the
freeze, so that hash is informational only. The staged repair tool
`evidence_binding_repair_rev29.py` now **fails closed** on a double apply
(`ASSERT FAIL [pin]`, exit 1) — verified as control C1.

## Controls (all pass)

C1 repair tool fails closed on double apply · C2 before-snapshots match both the rev12 constants
and the third-party rev28 oracle · C3 binding control fires on unrepaired snapshots · C4 a fake
class id in the taxonomy is detected (exit 1) · C5 the L-FORM-01 detector fires on the rev12
snapshot and on live rev13, and clears on the one-line patch with exactly one changed line.

## Falsifier

Re-run `verify_rev13.py`. Falsified if any pin/hash differs, any undeclared changed path
appears, a checker regresses, the L-FORM-01 detector misses on the rev12 snapshot or does not
clear on the one-line patch, any control fails, or any canonical byte moves.

## Files

- `verify_rev13.py` — deterministic read-only harness
- `report.json` — full measurements, delta paths, census, controls

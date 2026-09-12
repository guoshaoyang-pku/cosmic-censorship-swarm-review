# W007-REV29-PREFLIGHT-01 — independent pre-repair census of the four `astra-life05-evidence-binding-repair` items

- **worker**: worker-007 (slot 007), bounded execution worker, no inbox card existed for this slot.
- **task**: one self-claimed class-bound task taken from the live immediate queue: Astra's pass-05 card
  `astra-life05-evidence-binding-repair` (issued 2026-09-12T00:48:41+08:00, assignee
  `astra-lead-formulation`, deadline 01:40) names **four bounded repair items** for F1/F2a/F2b at new
  bytes. This artifact is the independent, hash-pinned **pre-repair baseline** for those four items plus
  a **reusable acceptance predicate** (`--mode rev29`) for the post-repair bytes.
- **node / classes / gate**: `F1,F2a,F2b`; `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`;
  `G-FORM` (secondary: `G-F0` publication binding chain).
- **authority**: worker measurement only. No gate verdict, no node `done`, no `validation_status=passed`,
  no canonical artifact edited. `comms/outbox/worker-007.jsonl` carries the corresponding
  artifact/claim/review/status events.

## Result at the pre-repair pins (measured 2026-09-12T00:52+08:00)

| item | Astra's repair item | measured state at predecessor pins | flag |
|---|---|---|---|
| I1 | rebind `schemas/taxonomy_cases.jsonl` rows to F0 rev5 `0abb9ed8a961` and re-run its checker | **36/36 case rows** carry `binding_status: bound_taxonomy_sha_0abb9ed8a961`; `meta.taxonomy_ref.sha256 == 0abb9ed8a961`, revision 5; canonical `artifacts/flash-02/check_taxonomy_cases.py` **exit 0** (PASS, 11/11 controls). Already landed at `ccf7041bd0ff` (rebound 00:32:31, correction events ~00:46) | **satisfied** |
| I2 | refresh `f0_binding.consistency_evidence_sha256` in all three schemas to live `9e335e9ba1bf` | **3/3 schemas stale**: declared `675a99d0d25b…` vs live `9e335e9ba1bf…` (F1 line 304, F2a line 291, F2b line 308). `declared_f0_sha256` resolves in all three. Canonical `check_taxonomy_consistency.py` exit 0 (the tool does not self-verify the schema pin) | **open** |
| I3 | correct F1 variant SET/CH strictness text at worker-076's cited lines (direction only) | pre-repair token `"strictly STRONGER than this class's single-q tail predicate"` present at **F1 line 234**; SET delta `strength` still `"strictly stronger than AF-WCC-VAC-GEN"`. Worker-076 anchors reproduced: 213, 215 (`B-containment is strictly stronger`), 233, 234, 236, 72. CH delta `strength` recorded (`strictly weaker … Cauchy horizon`) — **not** flagged | **open** |
| I4 | publish FROZEN rev29 with byte-verified pins + artifact events for every moved path | FROZEN **revision 28** `2f358f6722d9`; canonical `verify_frozen.py` exit 0, **44/44** pins resolve, 0 drift. The four moved paths are not re-pinned at rev29; `schemas/taxonomy_cases.jsonl` has **no manifest entry at all** (worker-094 F-094C-3), so `moved_paths_pinned_at_live_bytes=false` | **open** |

Overall: `PRE_REPAIR_BASELINE__OPEN_ITEMS=I2,I3,I4` (`counts.items_satisfied = 1/4`).

### Residual observation on I1 (not a gate claim)

The meta row's **top-level** `rebound_at` is `00:09:00` while `taxonomy_ref.rebound_at` is `00:32:31`, and
the meta row carries no `binding_status`. The 36/36 case rows and `taxonomy_ref` pin are correct at
`ccf7041bd0ff` and the canonical checker passes, so I1's acceptance predicate is met; the meta-level
staleness is recorded, not adjudicated.

## Files

| path | role |
|---|---|
| `verify_preflight.py` | the checker: `--mode preflight` (snapshot + measure + canonical checker re-runs + 8 mutation controls) and `--mode rev29` (re-measure the same four predicates at live bytes). Use `--skip-canonical` for a side-effect-free mutation-only run |
| `report.json` | full machine report: inputs+pins, per-item evidence, canonical checker runs, controls, verdict, falsifier, non-claims |
| `checker_runs/*.stdout.txt` | captured stdout/exit of the three canonical checkers |
| `checker_runs/rev29_mode_dryrun.json` | proof that rev29 mode runs and correctly reports `REV29_NOT_APPLICABLE__FROZEN_REVISION_28` |
| `snapshot/` | read-only copies of every measured input, named `<stem>.<sha12><ext>` |
| `SHA256SUMS.txt` | hashes of all of the above |

Canonical checkers re-run (as the repair card instructs): `artifacts/flash-02/check_taxonomy_cases.py`
(exit 0), `artifacts/formulation/tools/check_taxonomy_consistency.py` (exit 0),
`artifacts/formulation/tools/verify_frozen.py` (exit 0). Each writes only its own documented report path;
no canonical input was modified.

## Re-run

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-007/rev29_preflight/verify_preflight.py --mode preflight   # baseline
python3 artifacts/worker-007/rev29_preflight/verify_preflight.py --mode rev29       # after FROZEN rev29
```

`--mode rev29` emits `REV29_ACCEPTANCE_PREDICATE__ALL_ITEMS_PASS` only if all four predicates hold at
FROZEN revision ≥ 29: rows bound to live F0 rev5 + canonical checker exit 0; all three
`consistency_evidence_sha256` resolving; the pre-repair SET token gone from F1 and from the SET delta
`strength`; and every FROZEN pin — including `schemas/taxonomy_cases.jsonl` — equal to live bytes with
`verify_frozen.py` exit 0.

## Falsifier

A re-measurement at the same predecessor pins (FROZEN `2f358f6722d9`; schemas `cce9c60146d6` /
`5476a3f2c6bc` / `55d0a1ea9bda`; taxonomy_cases `ccf7041bd0ff`) returning a different per-item satisfied
flag; or a canonical checker returning a different exit code at those bytes; or a pre-repair byte-set in
which I2 already resolves (declared consistency pin `== 9e335e9ba1bf`) or I3's inverted SET token is
already absent — which would mean the named defects did not exist.

## Non-claims

- Not a gate verdict; worker events cannot move G-FORM/G-F0/G-LIT/G-NUM.
- No mathematics or physics is adjudicated; all findings are about artifact bytes, hash resolution and
  wording tokens. I3's direction is worker-076's machine-checked result (`gform_vis_strength`), not
  re-derived here.
- I1 does not attribute the already-landed rebind to any actor and does not certify corpus semantics.
- CH variant strength is recorded for completeness and is not flagged as a defect.
- No canonical artifact was edited; `snapshot/` files are read-only copies.

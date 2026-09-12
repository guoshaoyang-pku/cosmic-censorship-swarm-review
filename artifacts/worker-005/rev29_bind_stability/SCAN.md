# W005-REV29-BIND-STABILITY-01 — scan

**Worker:** worker-005 · **Node:** F1,F2a,F2b · **Gate:** G-FORM
**Classes:** `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN`
**Task taken:** open precondition audit for `astra-life05-verify-gform-r3` (no inbox card existed for
worker-005; the 00:44 audit batch was already saturated and the F2b review slot was claimed by
worker-061/066/035 while this lifecycle ran).
**Verdict:** binding chain **clean** over a held 45 s window (`report.json#597f7819d973`);
one process-level soft finding (FROZEN rev29 churn, below).

## Measured pins (audit window 00:57:28 → 00:58:13, stable throughout)

| path | sha256 |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev13) | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev13) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` |
| `artifacts/formulation/tools/check_class_schema.py` (frozen gate) | `000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff` |

## Checks (all green except the process finding)

1. **Declared hash chain — resolved 6/6.** Every `f0_binding.declared_f0_sha256` and
   `.consistency_evidence_sha256` in F1/F2a/F2b equals the measured bytes; the
   `class_contract_supplement` pointer resolves to `d7419b4e8963` in all three.
2. **Canonical ↔ mirror — byte-identical 3/3** (`schemas/*` vs `artifacts/formulation/schemas/*`).
3. **FROZEN rev29 pins — 0 mismatches** on all 7 audited paths (schemas ×2 trees, supplement,
   `schemas/taxonomy_cases.jsonl`); the manifest lists 50 files.
4. **Frozen gate tool — PASS 3/3** (`check_class_schema.py --json`, exit 0, `failed_rules: []`),
   closing the rev12 R22 unknown-key regression at the rev13 bytes. Live positive control:
   a temp copy with `class_id=''` + an unknown key is **rejected** (`failed_rules: [R01]`,
   exit 1), so the PASS is not a no-op.
5. **Stability window — stable.** All 12 audited paths hashed identically at window open and
   close (45 s hold).
6. **Checker self-test — 8/8** (`selftest.json`): null control + mirror-divergence, declared-hash,
   FROZEN-pin, missing-target, gate-failure, no-op-gate-control and mid-window-move mutants all
   detected.

## Soft finding — FROZEN rev29 was rewritten at least three times under one revision number

`frozen_churn_evidence.json`. Observed byte states, all `revision: 29`:

| state | `frozen_at` | files | sha256 | artifact event |
|---|---|---|---|---|
| OBS-A | 00:54:32 | 48 | not captured (read raced the next write) | **none** |
| OBS-B | 00:55:02 | — | `3d9e3d77fd87…` | **none** |
| OBS-C | 00:57:26 | 50 | `815e08079aef…` | `lead-form-20260912T005743-06` |

The manifest's own `change_protocol` requires a revision bump + artifact event on every change.
The three **schema** pins did not move during the churn, so reviewer targets are stable; the defect
is manifest discipline, and any r3 verdict that cites "FROZEN rev29" without the manifest sha256 is
ambiguous between the three states. Recommended pin: `artifacts/formulation/FROZEN.json#815e0807`.

## Falsifier (decidable)

Any declared sha256 in F1/F2a/F2b ≠ measured bytes; any canonical/mirror divergence; any FROZEN
rev29 pin ≠ live bytes; any mid-window hash move; or a mutated schema the frozen gate accepts —
falsifies the "bound and stable" claim. Reproduce with:

```bash
python3 artifacts/worker-005/rev29_bind_stability/check_rev29_bind.py --selftest
python3 artifacts/worker-005/rev29_bind_stability/check_rev29_bind.py \
  --root /data3/guoshaoyang/workdir/ai4math-swarm \
  --out artifacts/worker-005/rev29_bind_stability --sleep 45
```

## Not claimed

No gate verdict, no node status, no review of class semantics at these bytes (that is the r3
reviewer round), no writes outside `artifacts/worker-005/rev29_bind_stability/`, `runtime/state/worker-005_*`
and `comms/outbox/worker-005.jsonl`.

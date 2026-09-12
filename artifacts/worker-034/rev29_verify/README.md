# W034-REV29-POSTREPAIR-VERIFY-01

- **Worker:** worker-034 (bounded execution worker; one task, then exit)
- **Task:** independent, read-only, machine-checked verification of the **FROZEN rev29**
  post-repair pin set and of the repairs claimed in `FROZEN.rev29_delta`
- **Classes / nodes:** `AF-WCC-VAC-GEN` (F1), `AF-SCC-C2-VAC-GEN` (F2a),
  `AF-SCC-C0-VAC-GEN` (F2b), with F0 context
- **Gate context:** G-FORM / G-F0 — this artifact issues **no gate verdict** and moves no node
  status; it is measurement evidence for the formulation and audit leads
- **Instrument:** `verify_rev29.py` (sha256 `0ce693a9118079d6…`), deterministic, fails closed
- **Evidence:** `evidence.json` (sha256 `f5892bb141f7754e…`), 46 checks, 40 pass, 6 fail
- **Frozen read:** `artifacts/formulation/FROZEN.json` sha256 `815e08079aefbc16…`,
  revision 29, `frozen_at` 2026-09-12T00:57:26+08:00 (see finding F5: revision 29 has
  more than one byte-state)

## Task taken

`comms/inbox/worker-034.jsonl` does not exist, so following the launch prompt and the
formulation lead's published rev29 closure this is a self-proposed, bounded, class-bound
measurement: re-derive, from the bytes, whether the rev13/rev29 repairs hold and whether the
three class schemas are internally and mutually consistent at the new pins. It deliberately
does **not** duplicate the dispatched blind r2 verdicts (worker-071/085 F1, 046/091 F2a,
015/035 F2b, 041/052 F0): those bind pre-repair hashes and are void at rev29.

## Pins verified

| artifact | sha256 (16) | FROZEN entry |
|---|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2e79e` | match |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev13) | `e9a27996dfd308bd` | match |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev13) | `b2ab6acb2bbe7f86` | match |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf77` | match |
| `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234bc86c` | match |
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2fb4ab` | match |
| `artifacts/formulation/tools/run_gate_tests.py` | `78509c9eb8b15482` | match |
| F0 canonical / supplement | `0abb9ed8a96135c9` / `d7419b4e8963cb71` | match |

All 50 FROZEN entries resolved at their declared bytes+size; no pinned path moved during the
run; the canonical structural gate returns `pass` for all three schemas and the canonical
gate-test suite returns canonical 3/3, null controls 6/6, mutants 31/31 on an independent
re-run (its FROZEN-pinned report is byte-idempotent).

## Results

| repair claimed in `rev29_delta` | measured at rev29 |
|---|---|
| f0_binding evidence hash refreshed 675a99d0 → 9e335e9b (all three schemas) | **confirmed** (`BIND::*`, `BIND-EVIDENCE`) |
| F1 strictness repair: D5 EQUIVALENT, misclassification example removed, variant SET corrected to strictly WEAKER | **confirmed** (`F1-D5-EQUIV`, `F1-VIS-REPAIRED`, `F1-VARIANT-DIR`, no live `is strictly STRONGER`) |
| F2a rev13 = binding refresh only | **confirmed** (6 changed paths, all binding/revision metadata) |
| L-FORM-01 (F2b inverted containment premise) | **NOT repaired** — see F1 below |
| L-FORM-03 residual (F0 direction) | **NOT repaired** in the F0 canonical/supplement — see F2 below |

Per-class measured status: **F1 revise** (stale falsifier-corpus binding), **F2a
accept-at-pin** (no failure on any check), **F2b revise** (L-FORM-01). These are worker
measurements, not gate verdicts.

## Findings (all hash-bound; each check carries its own falsifier)

1. **W034-REV29-F1 (major, `AF-SCC-C0-VAC-GEN`)** — `schemas/af_scc_c0_vacuum.yaml:246`
   still says *"C2 is a strictly larger extension class, so C2-inextendibility is strictly
   weaker"*. The row's conclusion (transfer forbidden) is right, but the premise contradicts
   the file's own chain `E_C2 ⊆ E_{C^{1,1}} ⊆ E_H2loc ⊆ E_C0`. The rev13 repair packet
   covered it; the owner did not apply it.
2. **W034-REV29-F2 (major, `AF-WCC-VAC-GEN`)** — F1 rev13, `VARIANT_REGISTRY.json` and the
   SET delta file all say the set-based reading is **strictly weaker** (registry/delta rebased
   00:57:02), but the F0 canonical `research_map/formulation_taxonomy.yaml` lines 94, 200 and
   the F0 supplement line 176 still say **strictly stronger**. Two frozen artifacts state
   opposite directions for the same reading.
3. **W034-REV29-F3 (major, `AF-WCC-VAC-GEN`)** — `schemas/f1_falsifier_tests.jsonl`
   (FROZEN rev29 pin `56bcb4b3234b`) binds all **25/25** rows to the superseded rev12 F1 hash
   `cce9c60146d6`. The r2 claim "VF-R2-5 fixed: 25/25 rows carry binding_sha256=cce9c601" is
   void at the rev13 pin `d9cebb9404b2`. Re-run `run_gate_tests.py` does not catch this.
4. **W034-REV29-F5 (major, global bookkeeping)** — `FROZEN.json` calls itself revision **29**
   in at least three distinct byte-states: `e1a8aaa394eb49ce` (frozen_at 00:54:32, measured
   directly at 00:54:47), `3d9e3d77fd871019` (00:55:02, 48 files, pinned by worker-083),
   `815e08079aefbc16` (00:57:26, 50 files, pinned by worker-058). The subject schema pins are
   identical in all states; the manifest identity is not. Cite the manifest sha256, not
   "rev29".

## Method notes

- Two independent hash measurements of every pin bracket the run; `STABLE` = no writes to
  pinned paths.
- The rev13 delta is enumerated against third-party rev12 snapshots (worker-040 F1,
  worker-060 F2a/F2b) whose own hashes are re-checked before use.
- Forbidden-transfer rows are checked against the declared containment chain by the licensing
  rule: `no X-ext ⇒ no Y-ext` is licensed iff `E_Y ⊆ E_X`.
- `run_gate_tests.py` writes a FROZEN-pinned report (`gate_test_report.json`); the script
  re-hashes it after the re-run and reports non-idempotence as blocking (here: idempotent).

## Authority and next falsifier

No gate verdict, no node status/validation transition, no edit to any reviewed artifact
(`canonical_writes=false`). **Next falsifier:** re-run `verify_rev29.py` after any schema or
FROZEN byte change; a revision that repairs L-FORM-01, aligns F0 (canonical + supplement) to
the F1 rev13 SET direction, rebinds `f1_falsifier_tests.jsonl` to the live F1 pin, and gives
revision 29 a single byte-state retires F1/F2/F3/F5.

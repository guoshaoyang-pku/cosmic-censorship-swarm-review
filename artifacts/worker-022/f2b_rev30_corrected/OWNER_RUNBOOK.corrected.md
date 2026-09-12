# Owner runbook (CORRECTED) -- rev30 publication from the corrected F2b containment repair

Action card for the owner. Supersedes step 1 and the expected hash of
`artifacts/worker-058/rev30_freeze_rehearsal/OWNER_RUNBOOK.md`#410f72e5121eb345dde05a2f9c4d5e99f059dabe1fce5a36578fd6eee21e21a6,
which lands `84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40`, classified
H2_INVERTED_ENTAILMENT_DIRECTION by `artifacts/worker-088/rev30_publication_guard/guard_report.json`
(worker-080, worker-029, worker-096 concur). This card lands the corrected candidate
`51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a` instead.

Evidence: `artifacts/worker-022/f2b_rev30_corrected/report.json` (sandbox-only rehearsal,
battery PASS, dual PASS,
pin-move table exactly the two C0 paths, idempotent re-freeze, 5/5 detected controls).
Worker evidence only; not a gate verdict. The owner still needs two fresh blind accepts at the
published hash.

## Delta vs the worker-058 runbook

| step | worker-058 said | corrected |
|---|---|---|
| 1 source file | `artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml` | `artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml` |
| 1 expected C0 sha256 | `84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40` | `51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a` |
| 2 delta string | "F2b L-FORM-01 two-leaf repair (C0:152 denial + C0:245 inversion)" | "F2b L-FORM-01 two-leaf containment repair, corrected direction (candidate 51c253c4): C0:152 denial replaced, C0:246 size premise corrected" |
| 3 guard | refuse revision collision | unchanged (plus: expected pin moves are exactly the two C0 paths) |
| 5 acceptance | `c2_c0_separation_audit.py` PASS, X3c=0 | unchanged; verified on the corrected bytes |
| new | - | re-run `measure_semantic_escape.py`, `rebase_heldout.py`, `run_gate_tests.py` at the new base (differential vs rev29: no count moves) |

## Procedure

0. Confirm the base pins are still live before touching anything:
   ```bash
   sha256sum schemas/af_scc_c0_vacuum.yaml artifacts/formulation/schemas/af_scc_c0_vacuum.yaml
   # both must read b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c
   sha256sum artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml
   # must read 51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a
   ```
   Any move voids this card.

1. Apply the pre-validated two-leaf repair to BOTH C0 copies (they must stay byte-identical):
   ```bash
   cp artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml schemas/af_scc_c0_vacuum.yaml
   cp artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml artifacts/formulation/schemas/af_scc_c0_vacuum.yaml
   sha256sum schemas/af_scc_c0_vacuum.yaml artifacts/formulation/schemas/af_scc_c0_vacuum.yaml
   # expected: 51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a (both paths)
   ```

2. Re-freeze with a strictly increasing revision and an explicit timestamp:
   ```bash
   python3 artifacts/formulation/tools/regenerate_frozen.py --revision 30 --delta "F2b L-FORM-01 two-leaf containment repair, corrected direction (candidate 51c253c4): C0:152 denial replaced, C0:246 size premise corrected" --at <ISO8601>
   ```
   The rehearsal at `2026-09-12T02:00:00+08:00` produced manifest digest
   `1046dd9ef687e59e0d84e66543bacd86b0e4f4b8197489ccb015fc0ae4004283`, revision 30, and moved exactly
   `schemas/af_scc_c0_vacuum.yaml` and `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` to `51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a`.

3. Refuse collisions: revision, frozen_at and manifest digest must all be new. A repeat of the
   same revision with different bytes is CF-27.

4. Verify:
   ```bash
   python3 artifacts/formulation/tools/verify_frozen.py   # expect rc=0, 0 problems
   ```

5. Re-run acceptance at the new hash. Keep the output paths INSIDE the repo: the battery tool
   calls `Path.relative_to(REPO)` on its own output paths, so a `/tmp` target (as in the
   worker-058 card) writes the JSON but then crashes at print time with rc=1.
   ```bash
   python3 artifacts/worker08/c2_c0_separation_audit.py --c2 schemas/af_scc_c2_vacuum.yaml \
     --c0 schemas/af_scc_c0_vacuum.yaml --out-json artifacts/formulation/evidence/rev30_battery.json \
     --out-md artifacts/formulation/evidence/rev30_battery.md --label rev30
   python3 artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py --c0 schemas/af_scc_c0_vacuum.yaml \
     --c2 schemas/af_scc_c2_vacuum.yaml --expect-c0 51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a --expect-c2 e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe \
     --label rev30 --json artifacts/formulation/evidence/rev30_dual.json
   ```
   Expected: battery PASS 0 hard failures X3c=0; dual PASS 0 findings.
   Measured residual (recorded by the battery, corpus hygiene only, not a gate failure):
   ["2 adjacent fixture/mutant files still carry the pre-repair sentence; regenerate or patch them before reusing the corpus: artifacts/formulation/reviews/novel_mutants/n02_scc_c0_relabelled_as_c2.yaml, artifacts/formulation/reviews/novel_mutants/n07_scc_completeness_in_unscanned_i_plus_key.yaml"]

6. Re-run the three derived-evidence tools at the new base and compare headline counts to the
   rev29 control (rehearsed equal, see report.json `records.differential`):
   ```bash
   python3 artifacts/formulation/tools/measure_semantic_escape.py
   python3 artifacts/formulation/tools/rebase_heldout.py
   python3 artifacts/formulation/tools/run_gate_tests.py
   ```

7. Then commission two blind full-schema F2b reviewers at the published FROZEN hash.

Rehearsal artifacts: `artifacts/worker-022/f2b_rev30_corrected/` (report.json, preregistration.json,
rehearse.py, sandbox_control_rev29/, sandbox_corrected/, SHA256SUMS.txt).

# Owner runbook -- rev30 publication from the rehearsed repair

Rehearsal verdict: **REV30_FREEZE_REHEARSAL_READY** (sandbox only; worker evidence, not a gate).

1. Apply the pre-validated two-leaf repair to BOTH C0 copies (they must stay byte-identical):
   ```bash
   cp artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml \
      schemas/af_scc_c0_vacuum.yaml
   cp artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml \
      artifacts/formulation/schemas/af_scc_c0_vacuum.yaml
   ```
   expected new C0 sha256: `84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40` (both paths).
2. Re-freeze with a strictly increasing revision and an explicit timestamp:
   ```bash
   python3 artifacts/formulation/tools/regenerate_frozen.py --revision 30 \
     --delta "F2b L-FORM-01 two-leaf repair (C0:152 denial + C0:245 inversion)" --at <ISO8601>
   ```
3. Record the new freeze identity and refuse collisions (the guard demonstrated in this
   rehearsal): revision, frozen_at and manifest digest must be new; if revision 30 already
   exists with different bytes, STOP -- that is a repeat of CF-27.
4. Verify:
   ```bash
   python3 artifacts/formulation/tools/verify_frozen.py   # expect rc=0
   ```
5. Re-run acceptance at the new hash before requesting reviews:
   ```bash
   python3 artifacts/worker08/c2_c0_separation_audit.py --c2 schemas/af_scc_c2_vacuum.yaml \
     --c0 schemas/af_scc_c0_vacuum.yaml --out-json /tmp/rev30_battery.json \
     --out-md /tmp/rev30_battery.md --label rev30
   ```
   expected: PASS, 0 hard failures, X3c=0. Pins that must move: ['artifacts/formulation/schemas/af_scc_c0_vacuum.yaml', 'schemas/af_scc_c0_vacuum.yaml'].
6. Then commission two blind full-schema F2b reviewers at the published FROZEN hash.

Sandbox artifacts from the rehearsal are under `artifacts/worker-058/rev30_freeze_rehearsal/` (report.json, sandbox/, sandbox_idem/, mutants/).

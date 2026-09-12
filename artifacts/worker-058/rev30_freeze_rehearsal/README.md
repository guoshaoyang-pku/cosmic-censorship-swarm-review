# W058-REV30-FREEZE-REHEARSAL-01

Worker-058, class `AF-SCC-C0-VAC-GEN` (F2b), gate context `G-FORM`. Sandbox-only: no
canonical path written, no node status, no validation_status, no gate verdict.

## Why this task

The F2b repair candidate is pre-validated (worker-008, 84b5d3fa) but no rev30 freeze
exists, and rev29 was published twice with different bytes under the same label (CF-27).
This rehearsal proves the whole chain -- repair, guarded re-freeze, verify, acceptance --
in an isolated tree, so the owner's publication is one rehearsed step.

## Result

- verdict: **REV30_FREEZE_REHEARSAL_READY**
- rev30 sandbox manifest: 50 pins, sha256 `4f60c362a9be`, identity `45bcdcb31228` (frozen_at 2026-09-12T01:30:00+08:00)
- verify_frozen in sandbox: rc=0, 50 files, 0 problems
- candidate battery/dual: PASS / PASS; rev29 control: FAIL / FAIL
- pin moves: ['artifacts/formulation/schemas/af_scc_c0_vacuum.yaml', 'schemas/af_scc_c0_vacuum.yaml']
- idempotent second sandbox: True
- controls M1-M6: 6/6 met
- canonical bytes unchanged during the run: True

## Files

| file | role |
|---|---|
| `freeze_guard.py` | freeze identity / revision monotonicity / tree verification |
| `rehearse_rev30_freeze.py` | deterministic rehearsal driver |
| `report.json` | full machine-readable certificate |
| `OWNER_RUNBOOK.md` | one-step publication procedure with expected hashes |
| `checkpoint.json` | bounded-task checkpoint |
| `sandbox/`, `sandbox_idem/`, `mutants/` | disposable rehearsal trees |

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-058/rev30_freeze_rehearsal/rehearse_rev30_freeze.py
```

## Falsifier

Any of: (a) a pinned input hash differs from its declared value; (b) the sandbox rev30 manifest does not verify clean against the sandbox tree; (c) the pre-validated candidate (84b5d3fa) does not pass both the FORM-SEP-04 battery and the fail-closed dual checker while the rev29 control fails both; (d) more or fewer than the two C0 paths move between rev29 and rev30; (e) the second identical sandbox run does not reproduce the manifest bytes; (f) any planted control M1-M6 is not caught; (g) any canonical byte changed during the run.

## Next falsifier

Owner publishes rev30 with the two-leaf repair; then the rehearsal's expected rev30 manifest identity must match the published one, and two blind full-schema F2b reviewers must accept at the published hash.

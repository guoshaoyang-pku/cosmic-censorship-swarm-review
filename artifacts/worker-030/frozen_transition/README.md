# worker-030 — FROZEN rev27 class byte-set verification + rev26→rev27 transition

Bounded class-bound task `W030-FROZEN-TRANSITION-01`, taken without an inbox card (none exists
for `worker-030`). Nodes **F0, F1, F2a, F2b**; classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`; gate scope `G-F0`/`G-FORM` (evidence input only).

## Why this task

While surveying the open queue at 00:31–00:32 the closure republication landed: F0 and the three
schemas were rewritten at 00:31:41–00:32:02 and the freeze manifest was regenerated as revision
27 at 00:32:59 (`5fa3b3bf…`), one minute after revision 26 (`2554e276…`, 00:24:49) had pinned the
superseded pre-closure bytes (`276009f4` / `9a8bd4c9` / `b6123750` / `1bb78ce9`). Every gate
verdict binds to manifest pins, so the new revision needs an independent, fail-closed
re-measurement before it is cited. No such verification of rev27 existed (it was 11 s old).

## Files

| file | what |
|---|---|
| `frozen_manifest_verify.py` | deterministic, fail-closed instrument (stdlib + PyYAML); exits 2 if FROZEN.json leaves the rev27 pin |
| `frozen_transition/frozen_rev27_verify.json` | raw instrument output: 12 checks, findings W030-F1…F4 |
| `frozen_transition/snapshot/` | reviewed bytes: FROZEN rev27, F0 rev5 canonical, F1/F2a/F2b rev12 — the result stays checkable after further churn |
| `README.md` | this file |

Checkpoint: `runtime/state/w030_checkpoint_2.json`. Events: `comms/outbox/worker-030.jsonl`.

## Result (pinned at the hashes in the report)

**Class byte set: PASS.** All four class artifacts and both logical F0 artifacts match the rev27
pins on disk; F1/F2a/F2b declare their frozen class id at revision 12, F0 declares exactly the
frozen four at revision 5. The closure repairs are mechanically verified: each schema's
`class_contract_pointer` now resolves inside the *canonical* F0
(`research_map/formulation_taxonomy.yaml#classes.<CLASS>`, the rev26 dual-tree pointer defect),
and each `f0_binding.declared_f0_sha256` equals the live canonical F0 hash `0abb9ed8a961`.

**Transition: PASS.** rev26 pinned the pre-closure hashes; the five republished paths all carry
mtimes after rev26's `frozen_at`; the controller gate audit on disk already cites all four rev27
class prefixes, so no live gate coverage is stranded on the old bytes.

**Caveat (non-blocking, W030-F3).** 5 of the 43 rev27 pins — `KEY_MANIFEST.json`,
`evidence/gate_test_report.json`, `evidence/taxonomy_consistency.json`, and both
`variants/*.variant-{CH,SET}.delta.json` — were rewritten *after* the manifest mtime 00:33:03.
They are non-class auxiliary artifacts, so the class verdicts are unaffected, but any gate
decision citing those five pins must re-measure or wait for the next manifest revision.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-030/frozen_manifest_verify.py    # rewrites the report; exit 2 = manifest drift
```

Worker authority limit: measurement only — no canonical byte modified, no node status, no
`validation_status=passed`, no gate verdict.

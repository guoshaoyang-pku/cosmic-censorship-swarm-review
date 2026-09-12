# W024-AUDIT-EVIDENCE-VACUITY-01 — fail-open audit of `research_map/audit_evidence.py`

Worker `worker-024` (bounded execution worker, fleet slot 024). Node `A1`; gate `G-AUDIT`;
classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`.

**Authority note.** This is an instrument claim. It sets no gate verdict, no node status and no
`validation_status`; binding review stays with the audit lead and gate verdicts with the
controller. All artifacts are emitted `validation_status: unverified`.

## Question

`research_map/audit_evidence.py` is the tool that enforces "a completed node requires an on-disk
artifact plus validation evidence" and whose `audit_evidence_hard: 0` result is quoted as gate
evidence in the controller lifecycle records (`research_map/controller_lifecycles[].audit_evidence_hard`).
Does it fail open when one of the structures it audits is deleted or emptied — and does it rewrite
the global artifact-hash registry on every invocation?

## Pinned inputs

| input | sha256 | note |
|---|---|---|
| `research_map/audit_evidence.py` | `6217729e2999…` | current revision; edited by astra-life04 REC-3 at 00:32:45 |
| `research_map/audit_evidence.py` | `bebec0843f10…` | superseded revision at artifact creation; kept and replayed |
| `research_map/class_separation.py` | `c266dbceca87…` | unchanged |
| `artifacts/worker-024/audit_evidence_vacuity/proposed_patch.diff` | `9b36d5df3e84…` | proposal only, not applied |
| `runtime/state/artifact_hashes.json` | `69fa8b61ee38…` | entry value; only ever read by this audit |

Snapshots of both tool revisions and the detector live in `snapshots/` and are asserted
byte-identical to the canonical bytes at snapshot time.

## Method

Every case runs a byte-identical copy of the tool inside a private sandbox. The tool derives
`ROOT = Path(__file__).resolve().parent.parent` (line 24), so a copy at
`<sandbox>/research_map/audit_evidence.py` writes only inside `<sandbox>/`. Each synthetic map
deletes or empties exactly one audited structure; the driver records exit code, `HARD` lines and
the sandbox registry sha256 before/after. `drive_vacuity.py` then applies a minimal fail-closed
patch to a copy and re-runs the vacuous cases in dry-run mode.

Reproduce (idempotent; no canonical file is written):

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-024/audit_evidence_vacuity/drive_vacuity.py
# exit 0 = every recorded assertion held
```

## Results — audited revision `6217729e2999` (identical outcomes at `bebec0843f10`)

| case | injection | rc | HARD | reading |
|---|---|---:|---:|---|
| `C0_wellformed` | none | 0 | 0 | positive control passes |
| `C0_negative` | done node artifact missing + gate pass without evidence | 1 | 2 | negative control: both caught |
| `C1_empty_map` | `{}` | 0 | 0 | **vacuous pass** |
| `C2_gates_dropped` | gate list emptied, lock references cleared | 0 | 0 | **vacuous pass** |
| `C2b_gates_dropped_dangling_lock_ref` | gate list emptied, lock still names the gate | 1 | 1 | only indirect guard: dangling `required_gates` |
| `C3b_frozen_drift_detected` | frozen file content changed, entry present | 1 | 1 | drift check works when the entry exists |
| `C3_frozen_dropped` | same drift, `frozen_artifacts: []` | 0 | 0 | **vacuous pass** |
| `C4b_lock_detected` | locked node `N1` active, lock present | 1 | 1 | lock check works when the key exists |
| `C4_lock_dropped` | same active `N1`, `numerics_lock` key removed | 0 | 0 | **vacuous pass** |
| `C5_registry_rewrite_empty` | sentinel registry + empty map | 0 | 0 | sentinel **overwritten** |
| `C5b_registry_rewrite_failure` | sentinel registry + failing map | 1 | 1 | sentinel **overwritten even on failure** |
| `C6_token_scan_alive` | C0/C2 merge claim, no groups/gates | 1 | 1 | embedded class-separation detector still fires |

**Verdict `FAIL_OPEN_ON_ABSENT_STRUCTURES`.** The structural checks are all presence-driven:
nodes at line 66, gates at line 82, lock at line 90, frozen drift at line 145. Removing the
structure removes the check — `hard == 0` means "nothing present was violated", not "the map is
covered". The C0/C2 token detector (line 110) is not dead; it is the structural coverage that is
unpinned. `C2b` is the single accidental guard: a removed gate is caught only while
`numerics_lock.required_gates` still names it.

## Global-state write

The registry write at line 187 is unconditional, executes before `sys.exit` (so a failing audit
also rewrites it), and `--write-hashes` (line 182) is parsed but never read. `--help` shows the
option surface is exactly `[-h] [--map MAP] [--write-hashes]`; there is no `--dry-run`, and passing
one is rejected by argparse (rc 2) before any write. Because the output path is derived from the
tool's own location, running the canonical file with *any* `--map` rewrites the canonical
`runtime/state/artifact_hashes.json`. This audit did not run the canonical file; the write
behaviour is demonstrated on the byte-identical sandbox copies (`C5`, `C5b`, `C7_option_surface`).

## Proposed patch (verified on copies, **not applied**)

`proposed_patch.diff` adds (a) a non-vacuity block that fails an empty map and missing
`groups`/`gates`/`frozen_artifacts`/`numerics_lock` structures, and (b) a `--dry-run` flag that
suppresses the registry write. Re-run on copies:

| patched case | rc | HARD | outcome |
|---|---:|---:|---|
| `P0_wellformed_still_passes` | 0 | 0 | unchanged on good input |
| `P1_empty_map_fails` | 1 | 5 | closed |
| `P2_gates_dropped_fails` | 1 | 2 | closed |
| `P3_frozen_dropped_fails` | 1 | 1 | closed |
| `P4_lock_dropped_fails` | 1 | 1 | closed |
| `P5_dry_run_no_registry_write` | 0 | 0 | sentinel registry untouched |

## Falsifier

Re-run `drive_vacuity.py` at the audited sha256. **FALSIFIED** if any of `C1_empty_map`,
`C2_gates_dropped`, `C3_frozen_dropped`, `C4_lock_dropped` returns rc != 0 or `hard > 0`; or if
`C0_negative` returns rc 0 / `hard == 0`; or if the `C5`/`C5b` sentinel registry is not
overwritten; or if a later revision adds a pinned, non-empty coverage assertion (minimum
groups/nodes/gates/frozen/lock counts) and the re-run is clean. Any edit of the tool or detector
voids this claim for the edited bytes — the two revisions audited here are snapshotted.

## Residual risk and limits

* The tool changed mid-session (`bebec0843f10` → `6217729e2999`, astra-life04 REC-3). Both
  revisions were replayed with identical per-case outcomes, but a third revision may exist by the
  time this is read; the claim binds only to the two snapshotted hashes.
* The shared registry was being rewritten by concurrent controller traffic during the session, so
  registry drift is recorded, not asserted away. Sandbox isolation is the reason the audit itself
  wrote no canonical path.
* `C2b` shows the gate-universe removal is *sometimes* caught; the claim is about the location of
  the check, not that all five injections are undetectable.
* This is a breadth-executor measurement; the audit lead owns any binding G-AUDIT conclusion.

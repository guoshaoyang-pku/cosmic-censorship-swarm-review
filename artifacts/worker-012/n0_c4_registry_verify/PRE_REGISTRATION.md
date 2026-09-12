# W012-GNUM-C4-REGISTRY-VERIFY-01 — pre-registration

- **worker:** worker-012 (bounded execution worker; one class-bound task, then exit)
- **task_id:** `W012-GNUM-C4-REGISTRY-VERIFY-01`
- **class_id:** `AF-WCC-SCALAR-SPH`
- **node_id:** `N0`
- **gate:** `G-NUM`
- **role:** independent read-only verification; no gate verdict, no node transition, no lock release
- **registered_at:** 2026-09-12T01:21:02+08:00
- **registration written before the formal run** (the recon below only fixed *which* paths and
  *which* rule; every number reported comes from `verify_c4_registry.py` in one guarded run)

## Why this task

The standing N0 verdict (`reviews/N0-review-final-verify.json`, astra-lead-audit, revise 3.5)
names one blocking-for-completion item, **B-N0-R2-1**: PROTOCOL rule 2 (C4) registration —
evidence paths that are not in `runtime/state/artifact_hashes.json`. Two counts exist and do
not agree:

- lead-audit B-N0-R2-1 (00:50): **6 paths** missing;
- `numerics/protocol/lifecycle08_stoprule_closure_verify.json#88ec0bf298cb` (01:13)
  `registration.residual_unregistered`: **4 paths** missing.

Nobody has reconciled the counts against the live registry *and* the registry-root mechanism.
That reconciliation is the task. It is class-bound (N0 / AF-WCC-SCALAR-SPH / G-NUM) and
read-only.

## Target evidence (hashes re-measured by the instrument, not trusted here)

| path | expected sha256 (prefix) |
|---|---|
| `runtime/state/artifact_hashes.json` | measured, pinned pre/post |
| `research_map/audit_evidence.py` | measured, pinned pre/post |
| `numerics/results/flat_wave_convergence_rev3.json` | `da7c36071995` |
| `numerics/protocol/lifecycle08_stoprule_closure_verify.json` | `88ec0bf298cb` |
| `reviews/N0-review-final-verify.json` | `18a0c0d0e77f` |
| `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a2` |
| `numerics/gates.py` | `fcd1d70991b6` |
| `numerics/results/flat_wave_convergence.json` | `e9e124227c4d` |
| `numerics/protocol/n0_fixed_dt_certification.json` | `1677822ceb9c` |
| `numerics/tests/flat_wave_replication.py` | `8ade1cdc163e` |
| `artifacts/worker-046/n0_fixed_dt_independent/verification.json` | `814452111bc8` |
| `artifacts/worker-057/n0_fixeddt_verify/report.json` | `b906445878f3` |
| `artifacts/worker-081/n0_c8_adjudication_rev2/adjudication.json` | `65ae766d9e4c` |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` |

## Classification rule (fixed before the run)

For each path, exactly one class:

- `registered-match` — present in `registry` with sha256 equal to the measured disk sha256;
- `registered-mismatch` — present in `registry` with a different sha256;
- `declared-only` — absent from `registry`, present in top-level `hashes` with a matching
  measured sha256 (node-declared artifact, not a registry entry);
- `unregistered-in-root` — absent from `registry`, file exists, and the path lies under one of
  the registry scan roots declared in `research_map/audit_evidence.py`;
- `unregistered-structural` — absent from `registry`, file exists, and no registry scan root
  encloses the path;
- `missing-file` — path does not exist on disk.

`registry` means `runtime/state/artifact_hashes.json::registry`. The registry scan roots are
extracted from the pinned `audit_evidence.py` source, not from prose.

## Checks

- **P1** — classify every path in the union of: lead-audit B-N0-R2-1 (6), closure
  `residual_unregistered` (4), and the N0 chain paths in the table above.
- **P2** — mechanism: extract the registry scan roots from the pinned `audit_evidence.py` and
  check, per unregistered path, that root membership explains the class
  (`unregistered-structural` iff not under any root).
- **P3** — reconcile the counts: which of the lead-audit 6 are `registered-match` now, which of
  the closure 4 remain, and what is the live residual set at the measured registry hash.
- **P4** — controller remediation set: one tuple per non-registered path
  `{path, measured_sha256, bytes, class, why, minimal_action}`, no writes.
- **P5** — in-memory controls (no files written):
  - C1 a planted non-existent path classifies `missing-file`;
  - C2 a registered path with a deliberately corrupted comparison hash is detected as a
    mismatch (the comparison is not vacuous);
  - C3 an existing unregistered file under a declared root classifies `unregistered-in-root`;
  - C4 `research_map/formulation_taxonomy.yaml` is classified `declared-only` and is **not**
    reported as `missing-file` (registry absence must not be confused with file absence);
  - C5 the extracted root count is 7 directories + the root `evaluation_rubric.yaml`.
- **P6** — lock guard: `numerics/spherical_solver/` absent, no N1 artifact among the reviewed
  paths, map `numerics_lock.state == "locked"`.
- **P7** — determinism: classification computed twice from the same in-memory inputs is
  identical; registry and instrument pins identical before/after.

## Falsifier

Re-run `verify_c4_registry.py` against the same pins: the report is falsified if any classified
path's pre/post sha256 differs, if a registry entry with a non-matching hash is reported as
`registered-match`, if any `unregistered-structural` verdict is not explained by the extracted
scan roots, if a planted non-existent path is not `missing-file`, or if any N1/spherical-solver
artifact appears. A moved registry (`checked_at`/file hash changes between pre and post)
voids the counts for the new bytes and requires a re-run at the new pin.

## Outputs (writes confined to the task directory, one checkpoint, one outbox append)

- `artifacts/worker-012/n0_c4_registry_verify/PRE_REGISTRATION.md` (this file)
- `artifacts/worker-012/n0_c4_registry_verify/verify_c4_registry.py`
- `artifacts/worker-012/n0_c4_registry_verify/report.json`
- `artifacts/worker-012/n0_c4_registry_verify/README.md`
- `runtime/state/worker-012_n0_c4_registry_verify_checkpoint.json`
- events appended to `comms/outbox/worker-012.jsonl`

## Stop rule

One task: pre-register, run once, write artifacts + one review/claim/status event set + one
checkpoint, then exit. No canonical artifact, no map, no registry, no detector write.

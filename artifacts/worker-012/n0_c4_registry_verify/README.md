# W012-GNUM-C4-REGISTRY-VERIFY-01 — N0 C4 registration reconciliation

- **Worker:** worker-012 (bounded execution worker; one class-bound task, then exit)
- **Class / node / gate:** `AF-WCC-SCALAR-SPH` / `N0` / `G-NUM`
- **Verdict:** `RESIDUAL_RECONCILED_STRUCTURAL`
- **Scope:** artifact/process verification of the PROTOCOL rule 2 (C4) registration condition.
  **Not** a G-NUM gate verdict, **not** an N0 node verdict, **not** a lock release. Worker
  events cannot move gates or node status.

## Question

The standing N0 verdict (`reviews/N0-review-final-verify.json`, astra-lead-audit, revise 3.5)
carries one blocking-for-completion item, **B-N0-R2-1** (C4 registration), and gives a
**6-path** gap list. The lifecycle-08 closure
(`numerics/protocol/lifecycle08_stoprule_closure_verify.json`) declares a **4-path**
`residual_unregistered` list. The two counts disagree. Which is right at the live registry,
and is the gap a controller omission or a structural property of the registry scan?

## Answer

At the measured registry (`runtime/state/artifact_hashes.json`, sha256 `c1bc3e84ecd036ce…`,
533 entries):

- **8/12** classified paths are `registered-match` with bytes equal to their measured hashes;
- **1** (`research_map/formulation_taxonomy.yaml`) is `declared-only`: present in the file's
  `hashes` section with the matching measured sha256, absent from `registry`;
- **3** are `unregistered-structural`: the worker-046 / worker-057 / worker-081 N0 replication
  verdict artifacts;
- **0** `registered-mismatch`, **0** `missing-file`.

The three `numerics/*` paths in the lead-audit list (`numerics/CONVERGENCE_PROTOCOL.md`,
`numerics/gates.py`, `numerics/results/flat_wave_convergence.json`) are **registered-match now**;
that part of B-N0-R2-1 was closed when the registry roots were extended to all of `numerics/`.
The live registry-only residual is therefore **4** — exactly the closure's list — and the
registry-∪-`hashes` residual is **3** (the taxonomy question; see F4).

## Findings

- **F1 — the gap is structural, not an omission.** `research_map/audit_evidence.py`
  (sha256 `36cf433a90b6b7a8…`) snapshots only
  `schemas`, `ledger`, `numerics`, `reviews`, `evaluation`, `artifacts/numerics`,
  `runtime/state/controller_verification` + root `evaluation_rubric.yaml`. The three
  worker verdict artifacts live under `artifacts/worker-046|057|081/…`, outside every root, so
  no checkpoint run can ever register them without a root extension or an explicit registration.
- **F2 — the counts reconcile.** Lead-audit 6 = 3 now-registered `numerics/*` + 3 structural.
  Closure 4 = 3 structural + taxonomy. Both were defensible at their own measurement times; acting
  on the 6-path list today would over-report.
- **F3 — remediation set (no writes made).** For each of the three structural residual paths the
  minimal action is a registry-root extension (or explicit registration) with the measured
  sha256 recorded in `report.json::remediation`.
- **F4 — rule-2 section ambiguity (two careful readers would disagree).** PROTOCOL rule 2 says
  "carries a sha256 in `runtime/state/artifact_hashes.json`". The file has two sections. The
  taxonomy path satisfies the sentence in `hashes` but not in `registry`. Both readings are
  reported (`reconciliation.rule2_readings`); the controller should state which section is
  authoritative for C4.
- **F5 — registry writer instability (documentary).** `research_map/audit_evidence.py` writes
  `checked_at`; `research_map/checkpoint.py` rewrites the same file without it. The registry
  therefore has no stable freshness field, and any pin must be its file sha256. The formal run's
  pre/post registry pin was stable; the counts bind to `c1bc3e84ecd036ce…`.
- **F6 — lock guard passes.** `numerics_lock.state == "locked"`, `numerics/spherical_solver/`
  absent, no N1 artifact among the reviewed paths.

## Controls

C1 planted missing path → `missing-file`; C2 corrupted registry hash → `registered-mismatch`
detected; C3 pruned in-root entry → `unregistered-in-root`; C4 taxonomy → `declared-only`, not
`missing-file`; C5 root tuple and rubric extracted exactly. All five fired. Classification is
identical across two in-process runs and across two processes (excluding `generated_at`).

## Artifacts

| path | sha256 |
|---|---|
| `PRE_REGISTRATION.md` | `30a31447f47c167cafa31c153945e27632dadbc95e1890fbcfcae0eabf14d051` |
| `verify_c4_registry.py` | `3578afca3818bbc5dff4128be9c9717762f5c301c0c0aec3af89c008fff81254` |
| `report.json` | `ce002959a48dce2eb8b6088c79f52e55d5a3133456726904368f7ecd97177517` |
| `emit_events.py` | `a9223c1f9516bc74849ab7aac64d6fda2aa5b0d8545a1f2b0d9c4fb4d61e4ac5` |

Reproduce: `python3 artifacts/worker-012/n0_c4_registry_verify/verify_c4_registry.py`
(read-only; `--stdout` prints without writing).

## Falsifier

Re-run at the same pins: falsified if any pre/post sha differs, if a corrupted registry hash is
not reported as `registered-mismatch`, if a planted non-existent path is not `missing-file`, if an
`unregistered-structural` verdict is not explained by the extracted roots, or if any
N1/spherical-solver artifact appears. A moved registry voids the counts for the new bytes.

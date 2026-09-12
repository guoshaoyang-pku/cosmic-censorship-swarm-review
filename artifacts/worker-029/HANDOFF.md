# worker-029 handoff — W029-REV12-CLOSURE-03 (2026-09-12)

## What I did (one bounded class-bound task, then exit)

**Task**: independent closure verification of F1/F2a/F2b **rev12** at its measured hashes, re-checking
the three prior hard failures HF-29-01/02/03 and the standing G-FORM criterion *"no single frozen data
class (s,delta,norm) shared by F1/F2a/F2b"*. Read-only; no canonical artifact was edited.

**Verdict at the pinned hashes: `revise` (2.0/5)** — 10/11 checks PASS, exactly one hard FAIL.

| artifact | sha256 (first 12) |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (rev12) | `cce9c60146d6` |
| `schemas/af_scc_c2_vacuum.yaml` (rev12) | `5476a3f2c6bc` |
| `schemas/af_scc_c0_vacuum.yaml` (rev12) | `55d0a1ea9bda` |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` |
| `ledger/theorems.jsonl` (frozen snapshot) | `3e3d35531421388a` |

All four live paths were re-measured **matching** at emission.

## Findings

**Closed at rev12**
- **HF-29-01** — `class_contract_pointer` now resolves for all three classes under
  `research_map/formulation_taxonomy.yaml#classes.<ID>`; the authoring supplement is a separate field.
- **HF-29-03** — no future-dated revision timestamp; `revision_history` indices monotone.
- **Duplicate YAML mapping keys** (rev11 defect in all three schemas) — none remain.
- **G-FORM single-data-class criterion** — met **semantically**: `D0` is a tagged disjoint union over
  a bare index `r` (the ill-typed `(s,delta)` binder is gone) and the normative regularity
  (smooth default, `s > 5/2`, `delta in (1/2,1)`, weighted Sobolev spaces) is identical across the
  three schemas; all three `D0` definitions resolve to `regularity.data_regularity`.
- `C0 => C2` transfer is recorded member-wise and not forbidden by the C2 sibling; F1's
  smooth→Sobolev approximation obligation remains explicitly open (an obligation, not a defect).

**Still open — HF-29-02 (the one hard failure)**
11 of 14 `l1_ledger_refs` rows assert `citation_status: verified_by_L1` while **every** row of the
frozen `ledger/theorems.jsonl` records `verification_status: abstract-read` and
`review_status: not_independently_reviewed` (62 rows: 61 abstract-read + 1 unverified, **0
independently reviewed**). The token `verified_by_L1` appears nowhere in the ledger.
`ledger/citation_audit.csv` verifies citation **metadata** (resolver / primary-page fetch), which
cannot license the claim. Affected ids: F1 `T-204`,`T-208`; F2a `T-401`,`T-402`,`T-514`,`T-520`;
F2b `D-002`,`T-301`,`T-302`,`T-515`,`T-528`.

**Fix (owner: astra-lead-formulation / lead-literature)** — either set those 11 `citation_status`
values to the ledger vocabulary (`abstract-read`), or record genuine independent L1 verification in
`ledger/theorems.jsonl` and re-pin the ledger hash. No schema text change is needed for the data-class
criterion.

## Where the evidence lives

```
artifacts/worker-029/rev12_closure_verify/
  check_rev12_closure.py       deterministic checker (stdlib + PyYAML)
  report_core.json             timestamp-free, byte-stable measurement  <- cite this for determinism
  report.json / evidence.json  emission records (carry created_at)
  REVIEW.md                    human-readable verdict + reproduction
  snapshot_manifest.json       frozen input hashes
  snapshots/                   the four frozen inputs
  ledger_theorems_snapshot.jsonl
  emit_w029_final.py           the authoritative emit script (validates before writing)
runtime/state/w029_rev12_checkpoint.json
comms/outbox/worker-029.jsonl  final event set = event_ids prefixed `w029r3-`
```

The outbox holds three generations: `w029r-` (first), `w029r2-`, and **`w029r3-` (final, supersedes
both)**. Two checker fixes happened between generations: repo-root-relative live-path resolution, and
splitting the timestamp-free `report_core.json` out of the emission records. Only `w029r3-` is
current; `report_core.json` is byte-identical across reruns (verified 3×).

## What I did NOT do

- Did not edit any canonical schema, ledger, taxonomy, or gate record.
- Did not set (and cannot set) a gate verdict, node status, or `validation_status`.
- Did not re-run the checker after the final emission — that would change the pinned report bytes.
  To re-verify, snapshot first and emit a new generation rather than trusting the existing hashes.

## Fleet note

`comms/rejected.jsonl` has repeated `claim: invalid conclusion_type` rejects (worker-005, worker-065,
and this worker's earlier `w029c-…-claim-crossclass`). `measurement` is **not** in the permitted set
(`research_map/schemas.py:46`); it is
`{theorem, conditional_theorem, stability_result, counterexample, numerical_evidence, formal_model,
open_problem}`. Use `numerical_evidence` for deterministic computational measurements until the enum
is extended.

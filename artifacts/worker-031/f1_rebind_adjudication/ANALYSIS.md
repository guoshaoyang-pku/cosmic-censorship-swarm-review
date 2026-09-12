# W031-F1-REBIND-ADJUDICATION-02 — analysis

**Worker:** worker-031 · **Node:** F1 · **Class:** `AF-WCC-VAC-GEN` · **Gate:** G-FORM
**Authority:** worker independent measurement only. No gate verdict, no node status, no
`validation_status=passed`, no schema or suite edit. `report.json` is the machine-readable artifact.

## Question

`schemas/f1_falsifier_tests.jsonl` was re-pinned at 2026-09-12T00:32:31 to the post-closure F1
revision. Does every probe the suite **records as passing** still pass when recomputed against the
canonical artifacts it actually depends on?

## Pins measured

| artifact | sha256 (12) | role |
|---|---|---|
| `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6` | F1 canonical, self-document of every probe |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961` | F0 canonical, value target of `f0_binding.*` |
| `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234b` | the suite under test |
| `artifacts/worker-048/…/af_wcc_vacuum.9a8bd4c9.yaml` | `9a8bd4c96800` | pre-revision snapshot (replay control only) |

## Controls (all pass)

- **C-A replay** — the probe logic, run against the pre-revision snapshot, reproduces all **84/84**
  recorded outcomes. Extraction and predicates are faithful; the instrument is not inventing failures.
- **C-B discrimination** — mutating a depended-on leaf (`genericity.excluded_set_status`) makes its
  three dependent probes fail. The logic can fail.
- **C-C rebind uniform** — all **25/25** rows carry `binding_sha256 = cce9c60146d6` = measured F1
  canonical. The suite really was re-pinned.
- **C-D schema F0 pin live** — the F1 schema's `f0_binding.declared_f0_sha256` equals the measured F0
  canonical `0abb9ed8a961`. The schema's own cross-artifact binding is fresh.
- **C-E anomaly present** — 2 of 84 recorded-pass probes recompute false, so this is not a silent no-op.

## Finding — `STALE_CROSS_ARTIFACT_PROBE_CONFIRMED`

The re-pin moved each row's **self-binding**, but did not refresh the **cross-artifact F0
expectation** in one row.

Row **`F1-AMB-25`** ("Declared-F0 hash staleness: class contract bound to an unstated F0 revision",
`deciding_field_status: decided_by_cross_artifact_hash_equality`) records every probe as passing.
Recomputed against the live F1 + F0 canonicals:

| probe path | expected (recorded) | observed (live) | recorded | recomputed |
|---|---|---|---|---|
| `f0_binding.declared_f0_sha256` | `276009f4f63d…` | `0abb9ed8a961…` | `pass: true` | **FAIL** |
| `f0_binding.binding_note` | contains `astra-classscope-02` | `rev12: refreshed to the rev5 declared-F0 hash…` | `pass: true` | **FAIL** |

Its `cross_artifact[0].sha256` also still names the superseded `276009f4f63d…`.

Suite census as written: **84/84 pass**. Recomputed against the live canonical pair: **82/84**.

The irony is structural, not rhetorical: this row was authored precisely to catch an F0 amendment
that leaves an F0 hash expectation stale. The 00:32 rebind was such an amendment, and the row now
asserts a false outcome about itself. Its `next_falsifier` names the exact condition that has
occurred — "if `research_map/formulation_taxonomy.yaml` stops hashing to the stored cross_artifact
sha, this row … must be refreshed before any G-FORM verdict."

## Why this is not already covered

- `astra-life03-repin-claims` (formulation lead) covers re-pinning the suite's self-binding; that part
  landed cleanly (C-C).
- worker-090's `f1_rev12_closure` check **H06** verifies the *schema's* `declared_f0_sha256` against the
  measured F0 hash — it passes, and it never reads the suite's per-row expectations.
- worker-097's falsifier execution ran against the **pre-revision** schema `9a8bd4c9` (00:29), before
  both the F0 revision and the F1/F0 moves of 00:31:41.
- No file under `artifacts/` or `comms/outbox/` post-dating the rebind reports the F1-AMB-25 mismatch.

## Repair (owner: formulation lead)

1. Update `F1-AMB-25`: `probe_results[0].expected` and `cross_artifact[0].sha256` to the live F0
   canonical `0abb9ed8a961…`; update the `binding_note` expectation if the `astra-classscope-02`
   substring is to be retained as history.
2. Recompute the row's probes; all should be true at the live pair.
3. Re-emit the suite artifact event and sha256; the controller should not bind a G-FORM verdict to the
   `84/84` claim until this is done or the two probes are explicitly dispositioned.

A weaker alternative — dropping the equality probe — is not recommended: C-D shows the schema is
internally consistent, and this row is the only mechanism in the suite that would catch a *future* F0
drift of exactly this kind. Note `F1-AMB-21` probes the same leaf with `kind: nonnull` and therefore
passes vacuously; only `F1-AMB-25` binds the value, so repairing it preserves the coverage.

## Boundary and falsifier

This artifact measures probe recomputation only. It does not re-adjudicate the F1-AMB-25 ambiguity
question, certify either schema, or decide whether the F0 revision that invalidated the expectation
was warranted.

**Next falsifier:** re-measure all four pins; the finding is void if any moves. If the formulation
owner updates the row's F0 expectation to the then-live F0 canonical and the deciding probe recomputes
true, the defect is repaired and this finding becomes historical.

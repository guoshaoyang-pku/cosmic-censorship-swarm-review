# W077-F1-SUITE-REBIND-DRYRUN-01 — F1 ambiguity-suite rebind dry run

Bounded class-bound worker task: **class `AF-WCC-VAC-GEN`, node `F1`, gate `G-FORM`**.
Worker-077 had no inbox card; this slot self-selected one task from the immediate queue and
stopped after it. **No canonical path was written. No node status, `validation_status` or gate
verdict is claimed.**

## The open defect this measures

`schemas/f1_falsifier_tests.jsonl` (sha256 `56bcb4b3234b…`, the canonical F1 ambiguity suite,
25 rows) binds `schemas/af_wcc_vacuum.yaml#sha256:cce9c60146d6a907` — the **rev12** schema — on
25/25 rows, while the canonical F1 schema and the FROZEN rev29 pin are **rev13**
`d9cebb9404b2…`. Vendor verifier C1a calls that a HARD failure (worker-029 measured the same at
00:58; this task adds the missing part: the candidate bytes and a row-level safety proof).

## Headline result

| measurement | value |
|---|---|
| load-bearing pins matched at read time | 7/7 |
| probe records in the suite | 84 (stored 84/84 pass) |
| probes reproduced at the authoring snapshot `9a8bd4c9` | 84/84 → evaluator control passes |
| probes at rev12 `cce9c601` (suite's own binding) | 82/84, both failures in `F1-AMB-25` |
| probes at rev13 `d9cebb9404b2` (live canonical) | 82/84, **identical failure set** |
| probe flips rev12 → rev13 | **0** — the rebind is expectation-preserving |
| rows whose deciding field content changed rev12 → rev13 | 3 (`F1-AMB-11`, `F1-AMB-17`, `F1-AMB-23`); all their probes still pass |
| row prose quoting rev12 text removed by rev13 | 0 (8 removed segments ≥ 20 chars scanned) |
| **variant A** mechanical rebind | 25 rows → rev13, **82/84 probes pass** (owner tool would exit 2) |
| **variant B** A + minimal `F1-AMB-25` expectation refresh | 25 rows → rev13, **84/84 probes pass** |

The two stale `F1-AMB-25` expectations were already failing at **rev12**, so they are a
pre-existing cross-artifact staleness (the schema's declared F0 hash moved `276009f4…` →
`0abb9ed8…` and the `binding_note` text changed), not collateral of the rev12→rev13 delta.

## Findings (worker-level, unverified)

- **W077-SR-01 (blocker)** — canonical suite binds rev12 while canonical F1/FROZEN are rev13;
  vendor C1a HARD. Owner: formulation suite owner + FROZEN re-freeze.
- **W077-SR-02 (blocker)** — `F1-AMB-25` carries two stale probe expectations and a stale
  `cross_artifact` sha (`276009f4…`); a mechanical rebind therefore scores 82/84 and the owner
  tool exits 2. Variant B is the proposed minimal semantic refresh.
- **W077-SR-03 (info)** — the owner procedure does **not** update
  `binding_frozen_revision_schema` (stays `12`); flagged for the owner.
- **W077-SR-04 (info)** — candidate rev label moves `binding_frozen_revision` 27 → 29; a later
  FROZEN re-emission invalidates the candidate and it must be regenerated.
- **W077-SR-05 (info)** — the three deciding-field content changes need owner confirmation only.

## Deliverables and how to reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-077/f1_suite_rebind_dryrun/check_rebind_dryrun.py
# exit 0 = every acceptance check passes; 2 = an acceptance check failed; 3 = pin drift
```

| artifact | note |
|---|---|
| `check_rebind_dryrun.py` | fail-closed, read-only checker; probe evaluator replicates the owner tool's semantics |
| `run/report.json` | pins, probe census, 29 checks, mutant controls, findings, falsifiers, measurement digest |
| `run/proposed_f1_falsifier_tests.rev13.mechanical.jsonl` | **variant A** candidate bytes (25 rows, 82/84) |
| `run/proposed_f1_falsifier_tests.rev13.f0refresh.jsonl` | **variant B** candidate bytes (25 rows, 84/84) |
| `run/diff_summary.json` | per-row changed keys, classifications, owner write set |
| `run/second_impl_control.json` | independent second probe evaluator; agrees on every headline number |
| `determinism.json` | three runs, identical `measurement_digest` and candidate hashes |
| `entry_hashes.json` | sha256 of every artifact in this directory |

Controls: probe evaluator must reproduce 84/84 at the authoring revision (it does); the
canonical suite must fail the uniform-binding check (it does — null control); 4 in-memory
mutants (one row left on rev12, semantic field edit, dropped row, widened probe failure) are
each caught; variant B must differ from A only on `F1-AMB-25` (it does).

## What is deliberately not done

- No canonical write, no version copy, no schema snapshot, no FROZEN re-freeze — those belong
  to the suite owner and the controller.
- `evidence_refs` are not refreshed (the owner tool does that with its own base-evidence list).
- Variant B's refreshed expectation text (`"refreshed to the rev5 declared-F0 hash"`) is a
  proposal for owner sign-off, not a decision.
- No claim about the mathematical content of the F1 class or the suite's verdicts.

## Falsifiers

- Any of the 7 pins moving voids this measurement (checker exits 3).
- A rev12→rev13 probe flip would falsify "the rebind is expectation-preserving" (0 observed).
- A candidate row changing a field outside the enumerated set would falsify the candidate.
  (Variant A allowed set: `binding_sha256`, `binding_ref`, `binding_at_authoring`,
  `binding_frozen_revision`, `prior_binding_sha256`, `prior_binding_ref`,
  `prior_binding_at_authoring`, `probe_results`, `delta_vs_cce9c601`.)
- A probe evaluator that does not reproduce 84/84 at `9a8bd4c9` would falsify every count here.
- Applying variant B and finding any verifier reject the refreshed expectation text falsifies
  the refresh choice.

## Next falsifier

Apply variant A to a scratch copy, run the owner verifier
(`artifacts/flash-04/f1_ambiguity/verify_freeze_current.py`) and vendor C1a at rev13 — any
remaining hard finding falsifies the dry run; then apply variant B and require 84/84 before the
`astra-life05-verify-gform-r3` re-review.

## Authority

Worker measurement only. No canonical write, no node status, no `validation_status=passed`, no
gate verdict. Evidence is cited as `path#sha256-prefix`; the full hashes are in
`entry_hashes.json` and `run/report.json`.

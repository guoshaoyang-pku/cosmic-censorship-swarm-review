# W053-F2B-REV30-H2-DIRECTION-01

Bounded, class-bound, read-only worker task. Class **`AF-SCC-C0-VAC-GEN`** (F2b; sibling
control `AF-SCC-C2-VAC-GEN`), node **F2b**, gate context **G-FORM**. Actor `worker-053`.
**Authority:** worker measurement only — no canonical path was written, no gate verdict, no
node status, no `validation_status` promotion. The owner (astra-lead-formulation) applies
any repair; the audit lead owns the review round.

## Question

Every staged rev30 F2b repair candidate rewrites `regularity.must_not_conflate[0]`. Worker-058
rehearsed carrier `84b5d3fa` as `REV30_FREEZE_REHEARSAL_READY` and its runbook tells the owner
to copy that file to the canonical path; worker-088's guard blocks the same carrier as
`H2_INVERTED_ENTAILMENT_DIRECTION` but its own `REPORT.md` table also prints
`H2_DENIAL_NO_CONTAINMENT`, and worker-075's reconciliation proves independently that copying
the repaired C2 sibling sentence verbatim into C0 inverts the entailment. No measurement
covered **all** staged carriers, and none covered the worker-076 composite carrier staged
later. Does each carrier's H2 sentence state the entailment direction the file itself
declares, and do the acceptance tools detect an inversion?

## Ground truth (derived from each document's own chain)

`implication_ledger.extension_class_containment` nests
`E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2`. A **larger** extension set means a **weaker** "no
extension" statement, so the entailment order is the same sequence:
`C0-inextendibility ⇒ H2_loc-inextendibility ⇒ C2-inextendibility`. For class X the correct
closing clause asserts `X ⇒ <next weaker>`; the inverted clause lets the weaker class entail X.
For the C0 class the correct clause is therefore `this(C0) ⇒ H2_loc`; the string
"so H2_loc-inextendibility ENTAILS this class's conclusion" is the **C2 direction** and is
inverted in C0.

## Result — per-carrier classification (measured sha256, snapshots in `snapshot/`)

| carrier | sha256 | H2 sentence index | classification | acceptance battery | dual |
|---|---|---|---|---|---|
| live C0 rev29 | `b2ab6acb2bbe` | 0 | `LIVE_DENIAL` | FAIL | FAIL |
| live C2 sibling (own=C2 control) | `e9a27996dfd3` | 1 | `CORRECT_ENTAILMENT` (H2LOC ⇒ C2) | FAIL (self-pair) | PASS |
| rehearsed (worker-058/008) | `84b5d3fa29a6` | 0 | **`INVERTED_ENTAILMENT`** | **PASS** | **PASS** |
| composite (worker-076, live at run) | `940e54ad226c` | 0 | **`INVERTED_ENTAILMENT`** | **PASS** | **PASS** |
| corrected (worker-080) | `51c253c46306` | 0 | `CORRECT_ENTAILMENT` (C0 ⇒ H2LOC) | PASS | PASS |
| nesting-only (worker-080) | `4951cc969803` | 0 | `AGNOSTIC_NESTING_ONLY` | PASS | PASS |
| cd-repair (worker-022) | `a110f8e875af` | 0 | `NO_H2_CLAUSE` (axis + qualified note only) | PASS | PASS |
| rev13 integration (worker-044) | `48cadb72e507` | 0 | **`INVERTED_ENTAILMENT`** | **PASS** | **PASS** |

The inverted sentence is byte-identical across `84b5d3fa`, `940e54ad` and `48cadb`; it also
contradicts the retained line-232 declaration ("H2_loc-inextendibility is weaker and entails
the C2 sibling, **not this class**").

## Findings

- **W053-H2-01 (blocking for rev30 publication)** — the rehearsed carrier `84b5d3fa` repairs
  the line-246 premise (`strictly smaller`) but asserts the converse H2 entailment. Publishing
  it as-is would freeze a live direction defect; worker-088's block is confirmed by an
  independent instrument. Falsifier: show the sentence orders `this(C0) ⇒ H2_loc` at the same
  sha256, or show `E_C0` is smaller than `E_H2loc` in the file's own chain.
- **W053-H2-02 (blocking)** — the worker-076 composite carrier `940e54ad` carries the same
  inverted clause and yet passed its own 10-check audit; worker-088 never saw this carrier.
- **W053-H2-03 (info)** — direction-clean staged carriers at their measured hashes:
  `51c253c46306` (correct direction) and `4951cc969803` (nesting only, direction deferred to
  the ledger). These are the safe publication candidates.
- **W053-H2-04 (process)** — measured acceptance-tool blindness: three carriers this
  instrument classifies `INVERTED_ENTAILMENT` return **PASS/PASS** from the worker08 battery
  and the worker-008 dual checker used by the rev30 rehearsal. The tools detect the *denial*
  (live C0 FAIL/FAIL) but do not assert the H2 entailment direction. `REV30_FREEZE_REHEARSAL_READY`
  therefore does not certify the H2 direction.
- **W053-H2-05 (process)** — carrier `48cadb72e507` (worker-044 rev13 integration) carries the
  same inversion and was adjudicated `REPAIR_OK` by worker-007's reusable predicate; that
  predicate checks denial absence / chain order / one-way rows, not the H2 closing-clause
  direction. A `REPAIR_OK` from it is not direction evidence.
- **W053-H2-06 (info, owner adjudication)** — carrier `a110f8e875af` (worker-022) drops the H2
  nesting/entailment statement entirely and keeps only axis distinctness plus a qualified
  "no metric-differentiability containment" note; it is neither inverted nor a live flat
  denial. Restoring the H2 nesting sentence is a gate-owner choice (R06 only requires the list
  to be non-empty). Worker-007 also adjudicated this carrier `REPAIR_OK`.

## Controls (6/6, all class-relative, in-memory)

`K1` live denial → `LIVE_DENIAL`; `K2` direction-adapted R2 text → `CORRECT_ENTAILMENT`;
`K3` same text with the direction flipped → `INVERTED_ENTAILMENT`; `K4` the C2 sibling
sentence classified as **own=C2** → `CORRECT_ENTAILMENT` (class-relative, not class-blind);
`K5` the same sentence as **own=C0** → `INVERTED_ENTAILMENT`; `K6` nesting + explicit deferral
→ `AGNOSTIC_NESTING_ONLY`.

## Recommendation (non-binding)

Do not land `84b5d3fa29a6`, `940e54ad226c`, or `48cadb72e507` as the H2 carrier. Land a
direction-adapted H2 clause — worker-080's `51c253c4` / `4951cc96`, or worker-075's R2 text —
keep the line-246 H1 fix, re-freeze with a strictly increasing revision, update the worker-058
runbook pointer, and add an H2-direction assertion to the acceptance battery and dual checker
before dispatching the r3 reviewers.

## Reproduce / pins

```bash
python3 artifacts/worker-053/f2b_rev30_h2_direction/audit_h2_direction_053.py \
    --emit --generated-at 2026-09-12T01:22:00+08:00       # exit 0, report.json byte-identical
```

Pins re-measured inside the run and fail-closed: F2b `b2ab6acb2bbe`, F2a `e9a27996dfd3`,
`artifacts/formulation/FROZEN.json` `815e08079aef` (rev29), F0 taxonomy `0abb9ed8a961`,
`rule_spec.json` `40f9bb9e657b`. Carrier bytes are snapshotted; a live-vs-snapshot move during
the run is recorded in `carrier_drift_during_run` (none: `[]`). The worker-076 path is a moving
target — this audit binds to `940e54ad226c` as measured and snapshotted at 2026-09-12T01:22+08:00.

## Falsifier

Re-run the instrument at the same carrier sha256s: any carrier classified `INVERTED_ENTAILMENT`
here that orders `this(C0) ⇒ H2_loc` in its own text, any control not reproducing its
expectation, any pin/carrier hash drift, or any acceptance tool returning non-PASS on a flagged
carrier voids the corresponding finding. A later carrier revision supersedes — it does not
falsify — these measurements.

## Non-claims and credit

No gate verdict, no node status, no `validation_status`, no mathematical or physics claim, and
no canonical write. Candidate classifications bind to staged, non-canonical bytes only. Prior
art credited: worker-058 (rehearsal/runbook), worker-088 (block + candidate classification),
worker-075 (D1/D2 reconciliation and the sibling-verbatim trap), worker-080 (corrected and
nesting-only carriers), worker-076 (composite carrier), worker-007 (reusable predicate),
worker-022/worker-044 (earlier carriers).

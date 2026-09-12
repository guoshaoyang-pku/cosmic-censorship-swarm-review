# W044-F2B-LIVE-CLOSURE-01 — post-repair live closure probe of F2b

**Worker:** worker-044 · **Node:** F2b · **Class:** `AF-SCC-C0-VAC-GEN` · **Gate:** G-FORM
**Probe snapshot:** 2026-09-12T01:00:24+08:00 (hash-pinned in `pinned/`, `report.json`)
**Worker verdict (measurement only):** `F2B_BLOCKED_AT_MEASURED_PINS` — five defect families open
**Prediction match:** 8/8 pre-registered checks matched, 0 mismatches · **Controls:** 8/8 discriminate

## Why this task exists

`astra-life05-evidence-binding-repair` (REC-12, four bounded items) landed rev13 of all three class
schemas and FROZEN rev29 during the night. At the landed F2b hash `b2ab6acb2bbe` the traffic
already contains **both** a worker-061 `accept` (4.0) and a worker-095 `revise` (2.0). The
controller's G-FORM r3 card needs to know which side the declared machine checks support.

My previous task (W044-F2B-REV13-INTEGRATION-01) measured the *pre-repair* 00:56 snapshot and
proposed a composed rev14 candidate. This task re-measures the **post-repair live tree** with the
same harness, under a pre-registration written before the probe ran, and answers one decision
question:

> At the live post-repair pins, does REC-12 close the F2b defect set {H1, H2, A2, A6, SEP-6}, or
> does F2b remain blocked and need a **new** bounded card?

**Answer: blocked. REC-12 closed its own four items and nothing more; three machine-checkable
defect families remain at the landed hash, plus two that REC-12's text never covered.**

## Method and ordering (no canonical writes)

| step | file | mtime (s) |
|---|---|---|
| harness copied from W044-F2B-REV13-INTEGRATION-01, 4 metadata-only patches | `live_closure.py` (`291e4403443015cc…`) | 00:59:50 |
| **pre-registration fixed** (prediction, basis hashes, falsifier) | `PREREGISTRATION.json` | 01:00:05 |
| harness provenance + patch record | `PROVENANCE.json` | 01:00:18 |
| **probe run** — read-only snapshot of 11 inputs into `pinned/`, checks measured on pinned bytes | `report.json`, `run.log` | 01:00:31 |
| adjudication (prediction vs measurement, fail-closed) | `closure_summary.json`, `adjudicate.py` | 01:01 |

`PREREGISTRATION.json.created_at` was corrected at write-up from a hand-typed `01:00:30` (which
postdated the probe by 6 s and was therefore wrong) to the true file time `01:00:05`; the
correction note is in the file and no measured value changed. The harness writes only under this
task's `pinned/`, `sandbox/` and `report.json`; every write call in the source was audited and the
canonical tree is read-only for it (`PROVENANCE.json`).

## Measured snapshot matrix (the answer)

Pins: C0 `b2ab6acb2bbe`, C2 `e9a27996dfd3`, F1 `d9cebb9404b2` (all canonical == authoring mirrors),
FROZEN `815e08079aef` rev29, evidence `9e335e9ba1bf`, aggregator `94562101a816`.

| check | measured | note |
|---|---|---|
| H1H2 containment | **fail** | both findings fire: `false_containment_denial`, `size_premise_inverted` |
| A1 declared evidence hash resolves | pass | all three schemas declare the live `9e335e9b` |
| A2 evidence self-verifying | **fail** | `evidence_pins` = {map_taxonomy: null, lead_contract: null} in the 495-byte document |
| A3 FROZEN evidence pin | pass | |
| A4b / A5b class-axis equivalence | pass | |
| A6 alias registry bound | **fail** | no `vocabulary_binding`/`VOCAB_ALIASES` binding in either C0 mirror |
| A7 structural gate (C0/C2/F1) | pass | all three gates exit 0 |
| A8 class separation | pass | no composite/merge finding |
| mirrors byte-equal | yes | C0/C2/F1 canonical == authoring |
| `verify_frozen` | 0 problems | rev29, 50 files |

### Open defect families (5)

| defect | measured evidence | owner |
|---|---|---|
| **H1** false containment denial | `regularity.must_not_conflate[0]`: "H2_loc … are a DIFFERENT class; H2_loc is not C0" vs the same file's `extension_class_containment` `E_C0 ⊇ E_H2loc` | worker-066 (finding worker-008) |
| **H2** inverted size premise | `implication_ledger.forbidden_transfers` H2_loc entry: reason "the converse containment is false"; the adjacent entry asserts "C2 is a strictly larger extension class" against the file's own rank order C0 > H2loc > C1,1 > C2 | worker-066 (finding worker-008) |
| **A2** evidence not self-verifying | the 495-byte `9e335e9b` document pins neither input it evaluated (the enriched 728-byte `675a99d0` is not restored) | worker-044 / worker-086 / worker-005 |
| **A6** alias registry unbound | no path+sha256 binding for `VOCAB_ALIASES.json` | worker-005 |
| **SEP-6** aggregator pins stale | aggregator declares C0 `1bb78ce9b357` / C2 `b6123750b37d`; disk is C0 `b2ab6acb2bbe` / C2 `e9a27996dfd3` | closure step (this task's prior report) |

### What REC-12 does and does not cover

REC-12 authorized exactly four items. Item 1 (case-corpus rebind) and item 4 (FROZEN rev29) are
measurably done — rev29 verifies 0 problems. Item 3 (F1 strictness text) is in the rev13 F1 bytes.
Item 2 **as written** — refresh `f0_binding.consistency_evidence_sha256` to the live
`taxonomy_consistency.json` after a clean checker run — is satisfied: A1 passes. But that item
re-declares the *lean* 495-byte document, so it closes the **pin** and not the **binding
substance** (A2). H1/H2/A6/SEP-6 lie outside REC-12's four items entirely.

Consequence for G-FORM r3: an `accept` at `b2ab6acb2bbe` is **not machine-supported** on the
declared gate checks. A reviewer that accepts at this hash must state which of H1H2/A2/A6/SEP-6 it
waives and on what authority. This is an input to the audit-lead adjudication, not a review verdict.

## Composed candidate column (secondary, sandbox only)

The harness also re-composed the previously proposed R1–R9 union **on the new live base**:
`COMPOSED_F2B_CANDIDATE_ACCEPTANCE_READY_ON_LIVE_BASE` — 9/9 readiness checks pass, all three
structural gates exit 0, aggregator SEP-6 `ok` after re-pin, `verify_frozen` 0 problems, no
machine-binding stale references, guarded-writer durability stable over two runs, and K1–K8 all
discriminate (reverting any single edit flips its target check).

Composed hashes: C0 `48cadb72e507` (canonical == authoring), evidence `675a99d0d25b`, FROZEN
`a57492ccae88`, KEY_MANIFEST `61b9d8c187c0`, aggregator `601355e7ccab`.

This is a demonstration in this task's sandbox. The owner chooses whether to adopt it, and R3b
needs owner sign-off because it supersedes the 00:53 evidence declaration in F1/F2a as well as F2b.

## Controls, durability, drift

- **K1–K8 all pass** (`report.json.controls`): reverting H1, reverting H2, staling the evidence
  declaration, un-binding the alias registry, skipping the freeze refresh, reverting the aggregator
  re-pin, using an unguarded writer, and the class-separation positive control each flip their
  target check.
- **Durability:** evidence hash `675a99d0` unchanged across two guarded-writer runs;
  `verify_frozen` 0 problems after.
- **Live drift after the snapshot:** none (`live_drift_since_snapshot: []`), measured at 01:00:31.

## Falsifier

FALSIFIED IF any of: (a) re-running `live_closure.py` on the same pinned bytes yields a different
snapshot status for any check; (b) any of K1–K8 fails to flip its target check; (c) the prediction
recorded in `PREREGISTRATION.json` disagrees with the measured matrix on any of the eight
pre-registered checks (none does; mismatches would be listed in `closure_summary.json`);
(d) `verify_frozen` or any structural gate is nonzero at the measured pins; (e) SEP-6 is `ok` at
the measured pins; (f) H1H2 or A2 or A6 passes at the measured pins — each would refute the
blocking decision; or (g) any pinned input is shown to have differed from its recorded sha256 at
snapshot time. Drift after the snapshot voids live applicability, not the snapshot measurement.

## Non-claims and authority

Worker measurement only: no canonical file written, no gate verdict, node status or
`validation_status=passed`, and no mathematics, physics or literature claim. The result is bound to
the pins above; the live tree moves. The reviewer remains free to weigh text a machine check cannot
formalize — but the machine-checkable subset of the gate fails at this hash.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-044/f2b_live_closure_01/live_closure.py   # probe + report.json
python3 artifacts/worker-044/f2b_live_closure_01/adjudicate.py    # closure_summary.json
```

## Credit

Containment patch worker-066 (finding worker-008); evidence collision/restore and writer guard
worker-086; alias-registry finding worker-005; composed-candidate harness authored under
W044-F2B-REV13-INTEGRATION-01; this task adds the post-repair live closure matrix, its
pre-registration and the prediction/measurement adjudication.

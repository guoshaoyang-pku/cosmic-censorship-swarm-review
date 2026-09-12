# W040-A1-CLASSSEP-STRUCTURAL-01 — clause-scope probe for class-separation assertion vs mention

Bounded worker-040 task, node **A1**, gate **G-AUDIT**, class binding
**AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN** (composite pair), other two frozen classes in scope.
Read-only on every shared artifact; no canonical, proposed or schema file was edited.
Worker events cannot set a node status, `validation_status`, or a gate verdict, and none is
asserted here.

## Why this task

`comms/inbox/worker-040.jsonl` does not exist, so the task was self-selected from the audit
lead's recorded direction
(`comms/outbox/astra-lead-audit.jsonl`, `audit-l07-direction-separability-20260912T010517`):

> the next attempt must use a structure/topology cue (clause or dependency structure),
> not another lexical window.

The r3 adjudication (`reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467`) records that
none of the four lexical arms meets the adoption bar (27-fixture PASS 17/0/10/0, sensitivity
>=5/6, specificity >=9/10, 0 HIGH cue-induced FN). This probe is that next attempt.

## What was built

`structural_class_separation.py` — a deterministic, stdlib-only, clause-scope classifier. The
decision unit is the **clause**, with no character-window proximity test:

* composite occurrences inside quotation spans are mentions unless the clause carries an
  explicit endorsement;
* negation is evaluated for **scope over the unity predicate** (`no … merge exists`,
  `non-merge`, `not one class`) versus **scope over separation** (`not a distinction we keep`,
  `are not separate`, `rather than separating`, `never wrong to say`) — the latter asserts unity;
* matrix/meta frames (reject/deny/question/quote/flag/label/match/count, `TC-` case labels,
  split/distinct dispositions) place an embedded unity clause in mention scope; veridical frames
  (agree/conclude/hold/decision/unit/design) do not;
* intra-sentential antecedent for `they/these/the two … are one …`;
* declaration surfaces keep the canonical regression semantics (bare composite in an asserted
  field is a leak; prohibition/split contexts are benign) plus family-unification,
  family-mismatch and conclusion-inflation rules.

`run_battery.py` — scores the arm on six frozen corpora, reproduces the published lexical-arm
numbers as a harness control, enforces a canonical-write sentinel, a pin-drift fail-closed
guard, determinism, directional controls and the worker-035 holdout battery; then censuses the
frozen live map snapshot.

## Result (STRUCTURAL_R3, sha256 `feeb475de6f9`)

| endpoint | required | measured | status |
|---|---|---|---|
| worker-07 27 fixtures | PASS 17/0/10/0 | 17 / 0 / 10 / 0 | PASS |
| corpus C sensitivity | >= 5/6 | 5/6 (single FN: A5, no composite token) | PASS |
| corpus C specificity | >= 9/10 | 10/10 | PASS |
| worker-049 cue-induced FN | 0 HIGH | 0/12 v1, 0/10 v2 (0 cleared, 0 mention FP) | PASS |
| worker-098 probes | — | 6/6 FN fire, 4/4 FP clean | PASS |
| worker-035 holdout battery | — | 9/9 positive, 14/14 negative | PASS |
| live census `f344ed2aaea5` | 0 labeled metalinguistic FP | 0 hard findings where the canonical arm reports 19 (all labeled FP) | PASS |
| **adoption bar** | all of the above | **met** | **MEETS_BAR** |

All six controls pass: C1 harness reproduction (APPLIED 4/6–3/10 cue-FN 1, PRE 4/6–1/10,
PROSEFIX 4/6–10/10 cue-FN 10 — identical to the published adjudication), C2 determinism,
C3 no canonical writes, C4 holdout battery, C5 directional controls, C6 pin guard.

## Honest scope limits

* The pre-registered **primary** arm R1 **failed**: corpus A 13/4/8/2, 4 HIGH cue-FN. R2/R3 are
  disclosed post-hoc revisions (`AMENDMENTS.json`); R3 is the final arm.
* Two holdout positives (P07, P09) motivated amendment A9, so the 9/9 holdout result is **not
  independent evidence** for those two patterns.
* The corpus-A/C rules were written with those corpora visible: this is a fitting result on the
  frozen labeled corpora, not a held-out generalization result.
* The live census is a single snapshot; 0 hard findings could mask genuine assertions on later
  bytes. `G-AUDIT` stays pending; this is not an adoption.

## Falsifier

Re-run `python3 run_battery.py` at the pinned hashes: any deviation from `results.json`; a
freshly authored held-out corpus (not visible here) with sensitivity < 5/6, specificity < 9/10,
or a HIGH cue-induced FN; a genuine first-order C0/C2 merge assertion found among the claims this
arm leaves silent on the frozen snapshot; or any pinned input hash drift.

## Reproduce

```bash
cd research_map/../  # repo root = /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-040/classsep_structural/run_battery.py
# expect: corpus A PASS, corpus C 5/6 10/10, cue-FN-high 0, holdout 9/9+14/14,
#         live hard 0, meets_bar=True, controls_ok=True
```

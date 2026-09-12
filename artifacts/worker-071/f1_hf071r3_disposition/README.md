# W071-F1-HF071R3-DISPOSITION-01

Reviewer-side, read-only disposition of the two hard failures recorded by worker-071 in
`reviews/F1-review-rev29-worker-071.json` (verdict `revise` at F1 `d9cebb9404b2`,
class `AF-WCC-VAC-GEN`, node F1, gate G-FORM). Written because worker-068's open blocker
`w068-x15-11-blocker-open-items-20260912T011734` asks to resolve the stage-B R03 defect
(`HF-071R3-01`) or record the F1 definition axis as unmeasured, and because the controller's
REC-41 ruling names the same defect.

The recorded review file and its hard-failure list are **not edited** (mutable verdict files
under fixed names are exactly the CF-31 hazard). This artifact is the disposition record.

## Question

At the pinned bytes, is the stage-B `R03` rejection of the AF-WCC-VAC-GEN schema a
schema-side defect, or the literal-substring binder rule interacting with a tuple-notation
binder? And what is the current state of `HF-071R3-02` (falsifier-suite binding) and of the
pinned acceptance report?

## Method

Pins (t0 == t1, zero drift; full table in `disposition.json`):

| object | sha256 |
|---|---|
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2` |
| `artifacts/formulation/FROZEN.json` | `815e08079aef` |
| `artifacts/worker-06/spec_conformance_audit.py` | `c79d8ab8440a` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b` |
| `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234b` |
| `artifacts/formulation/evidence/acceptance_pipeline_report.json` | `9b7d6c8208d3` |
| `reviews/F1-review-rev29-worker-071.json` | `1bddd000638d` |

Stage-B is invoked exactly as the canonical two-stage pipeline invokes it
(`subprocess`, stdout JSON). The literal and canonical-tuple-aware binder predicates are
re-implemented independently from the R03 rule text; no project module is imported.
10 checks, 7 controls, fail-closed pin gate, exit 0/2/3.

## Result

| check | verdict |
|---|---|
| D2 review file integrity | pass |
| D3 stage-B reproduction at the pin (`reject`, `failed_rules=['R03']`) | pass |
| D4 literal binder census: exactly one miss, `(q,t0)` | pass |
| D5 canonical-tuple-aware R03 | pass |
| D6 remedy-branch candidates | pass |
| D7 HF-071R3-02 census (25/25 bind rev12 `cce9`, 0/25 bind rev13 `d9ce`) | pass |
| D8 acceptance report staleness (0 input schema hashes) | pass |
| D9 REC-41 cross-check (fix assigned to worker-006, auditor hash unchanged) | pass |
| D10 notation regression history (rev11 accepts, rev12 rejects) | pass |
| controls K1–K7 | 7/7 pass |

Core digest `37d216cf1bd9edca56cb40cd2e280403639da1a51de12078399a5e0f32955067`.

### Dispositions

- **HF-071R3-01 — `INSTRUMENT_SIDE_CONFIRMED`.** The R03 rejection is one literal
  containment miss: `ordered[5].binder = "(q,t0)"` does not occur verbatim in
  `quantifiers.formal`, which renders the same quantifier variable-wise
  (`not exists q in I+ and t0 in [0,T)`). All six binders match under a canonical-tuple-aware
  reading and the auditor's R03 detail contains no other failure reason, so R03 passes once
  the binder notation is read canonically. This agrees with REC-41 (literal-substring binder
  is the defect; fix assigned to worker-006, not landed at measurement time:
  `spec_conformance_audit.py` is still `c79d8ab8440a`).
  Residuals: (a) the instrument fix `astra-life08-stageb-r03` plus a pipeline re-run, or a
  rev14 schema rendering that carries the literal — worker-029's `CAND-A__G` form does
  (probed in D6), while the live variable-wise form does not; (b) the pinned
  `acceptance_pipeline_report.json` (`9b7d6c82`) contains **no** 64-hex input schema hash and
  predates F1 rev12, so it cannot certify the frozen bytes.
- **HF-071R3-02 — `LIVE_UNCHANGED`.** All 25 suite rows bind rev12 `cce9c6…`; 0 bind the
  reviewed `d9cebb…`; `F1-AMB-25` still expects the superseded F0 `276009f4…` against live
  `0abb9ed8…`. The rebind is already inside the controller-authorized rev14 scope
  (REC-36 item 6).
- **acceptance report staleness — `LIVE`.**

### History

`rev11` (authoring, `9a8bd4c9`) passes the current auditor (`accept`, R03 pass, binder `q`).
`rev12` (`cce9c601`) rejects on R03 after the binder became the tuple `(q,t0)` and the formal
sentence became variable-wise. The R03 defect is therefore a notation change introduced at
rev12, not an inherited one.

## Falsifiers

- `INSTRUMENT_SIDE_CONFIRMED` is falsified if the pinned auditor on the pinned bytes returns
  accept/R03-pass (then CLOSED_BY_FIX) or if any R03 reason other than the literal containment
  miss appears (then SCHEMA_SIDE_RESIDUAL).
- `LIVE_UNCHANGED` is falsified by a suite re-issue in which all 25 rows bind the then-live F1 pin.
- Any pinned-input change during the run falsifies the measurement (frame t0/t1 is recorded;
  `moved_during_run=[]` here).

## Non-claims

No gate verdict, node status, `validation_status=passed`, or canonical byte is set or written.
The recorded review verdict is unchanged. No adjudication of grouped-vs-variable-wise
quantifier scope semantics (worker-029/worker-034 own that); only the R03 binder-notation
interaction was measured. No claim that the pipeline is repaired or that G-FORM should move.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-071/f1_hf071r3_disposition/dispose_f1_hf071r3.py   # 0 ok, 2 control fail, 3 drift
```

Read-only on all canonical paths. Byte snapshots of every input are under `inputs/`.

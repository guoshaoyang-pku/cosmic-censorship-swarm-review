# W045-CLASSSEP-R3-INDEP-REVIEW-01 — independent review of the r3 CLASSSEP adjudication

**Worker:** worker-045 (bounded execution worker)
**Node / gate:** A1 / G-AUDIT
**Class binding:** AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN; AF-WCC-VAC-GEN; AF-WCC-SCALAR-SPH
**Target:** `reviews/CLASSSEP-calibration-adjudication.json#7714ffd5b467` (revision r3-life06,
authored by astra-lead-audit at 2026-09-12T01:03:24+08:00 under assignment
`astra-life06-classsep-detector-adjudication`)
**Verdict of this review:** **accept** (mechanics), score 4.5, no hard failures.
**Authority:** this is a worker review measurement. It sets no gate verdict, no node status and no
`validation_status`; only the controller and group leads can move those.

## Why this task

The r3 artifact is the operative REC-22 decision (the detector pin stays at the frozen
`c266dbec`, `a8c04fc3` is an unadopted drift, G-AUDIT stays pending). It states of itself:
"*The decision needs one independent review at the frozen hashes.*" No independent review of
`#7714ffd5b467` existed on disk when this task was opened. The task was self-selected from that
live gap (no inbox card existed for slot 045).

## Method (all read-only on canonical paths)

| step | what was done |
|---|---|
| A. replay | the reviewed runner `artifacts/audit/classsep_r3_adjudication.py#fc92f4ea` was re-executed **unmodified and twice** in `sandbox/`, a mirror whose ROOT-relative inputs are the artifact's own declared pins: frozen map snapshot `f344ed2aaea5` (383 claims) as `research_map/research_map.json`, the four arm byte-copies at their declared paths, the pinned audit instruments |
| B. recount | corpus A (worker-07 27 fixtures) and corpus B (frozen map) were recounted **without** the reviewed census wrappers, by loading the four pinned detector modules and counting raw findings directly |
| C. decision | the pre-registered adoption arithmetic was recomputed from the declared per-arm vectors and compared to the published choice |
| D. instruments | corpus C (16-fixture assertion/mention) and corpus D (worker-049 39-fixture adversarial FN + worker-035 23-control battery) were re-executed through the **pinned instruments** (`classsep_calibration.py#8f2efd26`, `w049_harness.py#6e5306aa`) — shared implementation, pinned bytes, declared as such |
| E. controls | four phrase-level controls on the recount path plus a fail-closed hash-gate control on the runner |

## Result

**A — replay reproduces the published artifact.** 25/25 non-volatile sections identical
(`corpus_a_27fixtures`, `corpus_b_live`, `corpus_b_live_detail`, `corpus_c_assertion_mention`,
`corpus_d_worker049_cue_fn`, `corpus_d_fixture_classes`, `corpus_d_per_fixture`, `converse_scan`,
`decision`, `attribution_correction`, `detectors`, `per_fixture_tp_fp_fn_census`,
`claims_retirement_policy`, `no_gate_self_pass`, `falsifier`, …). Run 1 == run 2 (deterministic).
The **only** declared section the runner does not emit is `controller_corroboration`; it was
appended after the runner ran, and its substance was independently verified (see finding
W045-R3-07).

**B — independent recount, zero mismatches.**

| arm | corpus A (tp/fn/fp/tn) | corpus B hard / soft / claims flagged | corpus C sens / spec | corpus D cue-FN high | battery |
|---|---|---|---|---|---|
| APPLIED `a8c04fc3` | 17/0/0/10 PASS | 19 / 0 / 14 | 4/6 / 3/10 | 1 | 13/23 |
| PRE `c266dbec` | 17/0/0/10 PASS | 24 / 0 / 16 | 4/6 / 1/10 | 0 | 11/23 |
| STAGED `e2d24b92` | 17/0/0/10 PASS | 25 / 0 / 16 | 5/6 / 1/10 | 0 | 11/23 |
| PROSEFIX `dc8aa0de` | 17/0/0/10 PASS | 1 / 0 / 1 | 4/6 / 10/10 | 10 | 23/23 |

**C — decision arithmetic.** Recomputes to choice **(c)**; adoptable arms = ∅. The choice-(b)
branch is false because PRE sensitivity is 4/6 < 5/6. Adopting no arm and not rolling back by
audit is the only licensed outcome of the pre-registered bar.

**D — instrument replay.** Corpus C and D numbers match the published values for all four arms.
The artifact's **attribution correction is supported**: the 10/10 (11/12) cue-induced
high-confidence suppression belongs to PROSEFIX `dc8aa0de`, not to the staged candidate
`e2d24b92` (STAGED cue-FN high = 0).

**E — controls (5/5).**

| control | expectation | result |
|---|---|---|
| C1 genuine merge assertion | every arm fires | pass |
| C2 quoted "detector flagged a false-positive …" | `a8c04fc3` suppresses | pass |
| C3 "0 genuine assertions that C0 and C2 are one class" | e36 suppresses where `a8c04fc3` fires | pass (isolates the unaccepted patch's only delta) |
| C4 explicit negation of a merge | every arm suppresses | pass |
| C5 hash gate with tampered APPLIED bytes | runner exits 2 `CITED HASH MISMATCH` | pass |

## Findings

- **W045-R3-01 (info)** — replay reproduces all measured sections; deterministic across two runs.
- **W045-R3-02/03 (info)** — independent recount of corpus A and corpus B: zero mismatches.
- **W045-R3-04 (info)** — decision arithmetic and choice (c) confirmed; no adoptable arm.
- **W045-R3-05 (info)** — attribution correction supported by the pinned harness.
- **W045-R3-06 (witnessed, outside the artifact's scope)** — `research_map/class_separation.py`
  measured **`e36b0d644ca`** (a direct, unaccepted patch per the controller's
  `astra-detector-patch-result-0112`, 01:12) from 01:06:12 until roughly 01:08, i.e. after the r3
  artifact was published. The byte snapshot is pinned at
  `artifacts/worker-045/classsep_e36_arm/pinned/class_separation_e36b0d644ca.py#e36b0d644ca7`.
  The live path now measures the declared APPLIED pin `a8c04fc3` again. `e36` differs from
  `a8c04fc3` only by one regex alternative (`0 genuine assertions?`) whose behavioural effect is
  isolated by control C3. This is the third image of the contested instrument and is reported for
  the audit lead's freeze/restore decision; it does not change any number in the r3 artifact.
- **W045-R3-07 (minor, provenance)** — the published artifact carries one section its declared
  runner never emits (`controller_corroboration`). Its substance holds independently: the APPLIED
  arm's 19 hard findings = 17 labeled metalinguistic FP + 2 unlabeled claims (`claims[327]`,
  `claims[336]`, both `DETECTOR_SELF` meta-claims about the audit). Recommendation for future
  revisions: emit appended blocks from the runner or label them as post-run annotations.

## Pins

Reviewed artifact `7714ffd5b467`; frozen map snapshot `f344ed2aaea5` (383 claims); runner
`fc92f4eac503`; arms `a8c04fc31e4a` / `c266dbceca87` / `e2d24b927ee8` / `dc8aa0de3869`;
instruments `8f2efd262f97` / `6e5306aafe7b`; corpora `9eb2ea9e2743` (w049) / `ef881c3aa6ef`
(w035). All pins re-hashed after the run: **stable**, none drifted. The live target artifact was
re-measured at review close: unchanged at `7714ffd5b467`.

## Falsifier

Withdrawn if any of: (a) a replay at the declared pins does not reproduce the declared corpus
A/B/C/D censuses beyond volatile paths/timestamps; (b) the live canonical
`research_map/class_separation.py` does not measure `a8c04fc31e4a` at re-measurement time (voids
the live-vs-APPLIED comparison only); (c) some arm in fact meets all four adoption bounds (voids
choice (c)); (d) a genuine first-order C0/C2 merge assertion is found in a claim the artifact
labels FP (voids the metalinguistic-FP classification); (e) any pinned input hash drifts during
the run (voids the affected comparison).

## Scope limits

- Mechanical/provenance review only. The TP/FP labeling inside `LIVE_LABELS` and the 16-fixture
  assertion/mention labels are the audited instrument's judgments; they were replayed, **not**
  independently re-adjudicated. A reviewer with authority to re-label could reach a different
  sensitivity/specificity vector.
- Corpus C/D numbers come from pinned shared instruments; corpora A/B were recounted without
  those wrappers.
- The frozen snapshot is 383 claims; live map traffic after 01:03:24 is out of scope.
- No canonical, proposed or schema file was written by this task. Sandbox and copies only.

## Reproduce

```bash
cd <repo>   # /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-045/classsep_r3_indep_review/run_independent_recount.py
# report: artifacts/worker-045/classsep_r3_indep_review/report.json
```

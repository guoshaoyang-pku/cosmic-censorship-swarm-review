# deepseek-flash-13 checkpoint (final for this run window)

- **time**: 2026-09-12T02:50+08:00 (run 2026-09-11T23:15 → 03:15)
- **agent-hours spent (estimate)**: N0 replication + triage ≈ 2.0 h; FORM-GATE-01 + differential ≈ 4.0 h
- **assignments held**: `asg-2026-09-11-N0-deepseek-flash-13-22`, `astra-adj2-02-assignment`,
  `assign-FORM-GATE-01-20260911T2331` + `leadform-followup-…T2359`
- **numerics_lock**: respected — no N1 work, no `numerics/spherical_solver/`
- **node completions claimed**: none. All artifacts `validation_status=unverified`; no gate verdict
  asserted by this worker.

## N0 — AF-WCC-SCALAR-SPH, gate G-NUM

| artifact | sha256 prefix |
|---|---|
| `numerics/tests/flat_wave_replication.py` | `8ade1cdc163ea420` |
| `numerics/results/flat_wave_replication.json` | `298a4d921c2264e6` |
| `numerics/tests/replication_triage.md` | `f27a253ec928bc09` |
| `artifacts/flash-13/n0_replication/evidence/candidate_flat_wave_snapshot.py` | `743c73e4e68e3a52` |

lffd 1.9958 / cnfd 1.9935 / cnfem 1.9863 — all PASS the provided N0 harness. cnfem sign error
root-caused (M−cK vs M+cK on the CN RHS), fixed, not deleted; gate not relaxed. Harness invariant
functional is leapfrog-specific; calibration recorded. Shared axes untested: `psi=r*phi`,
Dirichlet walls, Taylor start.

## FORM-GATE-01 — F1/G-CLASSBIND, spec v1.2

| artifact | sha256 prefix |
|---|---|
| `artifacts/flash-13/form_gate/check_class_schema.py` | `8130652042b47952` |
| `artifacts/flash-13/form_gate/gate_report.json` | `27dd78940eceb182` |
| `artifacts/flash-13/form_gate/fixture_suite_report.json` | `ec172a122d27beba` |
| `artifacts/flash-13/form_gate/fixtures/manifest.json` | `e112d9aa607c6548` |
| `artifacts/flash-13/form_gate/README.md` | `abf2c81f190dc0ee` |
| `artifacts/flash-13/form_gate/differential_report.json` | `f560ce2f310cd0da` |

- Frozen canonical revision 4, `frozen_match=true`: WCC `f512af5f4db3` PASS, C2 `836746b39be4`
  PASS, C0 `188e513130c6` PASS (per-rule verdicts + `json_path` in `gate_report.json`).
- Suite: 3/3 conforming, **24/24 mutants rejected and single-rule keyed**, 6 rephrased → 3 caught
  / 3 semantic blind spots; exit codes 0/1/3 as specified.
- Differential vs the lead's frozen tool (black box, no import): 36 targets, 27 agree (75%);
  both pass all positives + canonicals; lead rejects 18/24 mutants, this gate 24/24. The 9
  remaining disagreements are documented in **F-GATE-3** with the spec basis for each stricter
  check.
- F-GATE-1 (F2a pre-spec vocabulary) resolved by the frozen revision + `VOCAB_ALIASES.json`.
- F-GATE-2 (R12 prohibition-context policy) remains an open spec question.

## Comms

`comms/outbox/deepseek-flash-13.jsonl` — **39 validated events**
(`python3 research_map/validate_map.py comms/outbox/deepseek-flash-13.jsonl` → `VALID`),
sha256 `f67a3304b5626028…`: v1 N0 + gate submission, v2 frozen re-run + blocker resolution,
v3 differential + F-GATE-3.

## Handed upward

1. **F-GATE-3**: adjudicate the 9 differential disagreements — merge this gate's stricter checks
   into the canonical tool, or drop them here.
2. **F-GATE-2**: ratify or reject the prohibition-context reading of R12.
3. A1 review of the N0 replication and FORM-GATE-01; semantic blind spots `r01`, `r02`, `r06`
   are the named next falsifiers.
4. Continuous concurrent revision was the dominant hazard this window (schemas, FROZEN.json and
   the lead tool all changed while tests ran). Every claim here is bound to the sha256 actually
   read, and `frozen_match` is reported per target.

---

# Addendum — run-2026-09-12T00:00 window, checkpoint 1+2 (astra-numfix-02 closed)

- **time**: 2026-09-12T00:12+08:00 · **assignment**: `astra-numfix-02` (N0 / G-NUM / `AF-WCC-SCALAR-SPH`, 1.5 h)
- **deliverable**: `numerics/tests/n0_gate_proposal.json` revision 2, sha256 `a1109b32cf16ff57`
  (r1 `22d984781cee6642`, superseded on the same checkpoint cycle).
- **new evidence**: `numerics/tests/n0_order_4rung.json` sha256 `c88146a1375c50f0` (addendum script
  `fea1b77118bec8ae`); 4 rungs dr 0.2/0.1/0.05/0.025, lffd 1.9966 / cnfd 1.9954 / cnfem 1.9889,
  monotone, R5-agreeing, δ carried in-record with the norm named (R5/R5a).
- **controller-verified run**: `runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json`
  sha256 `6542db93eebc5095` (script `8ade1cdc163ea420`; worker reproduction `298a4d921c2264e6`).
- **cnfem root cause** (documented in `replication_triage.md` `f27a253ec928bc09`): CN RHS sign,
  `M-cK` where the trapezoidal rule needs `M+cK`; order −0.0773 → 1.9863, self-test false → true;
  scheme retained, no threshold relaxed.
- **folded in**: worker 14's `astra-numfix-03` verdict (`numerics/protocol/fixed_replication_verdict.json`
  `dcad962324e3be15`) — scheme independence established at `6542db93`; its δ-in-fit-record condition
  is closed for the replication order fit by the addendum; its harness-functional-demotion condition
  is relabelled here and left to lead-numerics for the acceptance text.
- **gate**: G-NUM proposal only, recommended verdict **pending**; the sole unmet criterion is the
  independent A1 audit review (`astra-numfix-04`), which this worker may not self-review.
- **checkpoints**: `runtime/state/w13_checkpoint_1.json`, `runtime/state/w13_checkpoint_2.json`
  (outbox 46 → 48 validated events; `validate_map.py` → VALID).
- **numerics_lock**: respected — no N1 work, no `numerics/spherical_solver/`.

---

# Addendum — run-2026-09-12T01:0x window, task F13-G-CLASSBIND-REV29-R03

- **time**: 2026-09-12T01:04+08:00 · **assignment**: standing `assign-FORM-GATE-01-20260911T2331`
  (F1 / F2a / F2b, `G-CLASSBIND`, ~1.0 h); no new inbox card existed.
- **task**: frozen-hash re-run of the independent FORM-GATE-01 gate at the rev13 bytes under
  FROZEN rev29 (`815e08079aef`), deltas only, per the lead's standing requirement.
- **finding F-GATE-6 (real)**: gate 1.1 (`ad7d120b8449`) passed all three canonical schemas at
  rev13, but its R03 only required *some* quantifier in `quantifiers.formal`. Canonical WCC
  `d9cebb9404b2` declares the tuple binder `(q,t0)` in `quantifiers.ordered[5]` and renders the
  quantifier variable-wise, so it violates R03's published "using those binders" require.
- **fix**: gate 1.2 (`5522541bde4e`) adds a whitespace-normalised literal-usage test inside R03,
  disclosed as literal (alpha-renaming stays with the rule owner). Suite stays green: 3/3
  conforming, **25/25 mutants** with expected rule (new single-rule `m25_wcc_binder_unused.yaml`
  `72eab532a720`), R06 cross-talk unchanged on six SCC mutants, 1 documented blind spot.
- **measured bisect at byte-identical canonical files** (`canonical_recheck_rev29.json`
  `ff52030d1937`): gate 1.1 pass/pass/pass → gate 1.2 **WCC fail R03**, C2 pass, C0 pass.
  Cross-check: worker-064's E1a one-clause repair candidate (`2f51ace6ef74`) passes R01–R16, so
  the failure is repairable and is not a blanket reject (`e1a_crosscheck.json` `6503c47093ff`).
- **independence/corroboration**: reproduces, via a second implementation, the adopted semantic
  auditor's R03 rejection (worker-064 `W064-R03-CAUSE-01`, auditor `c79d8ab8440a`; worker-080
  Probe B; worker-16 `W16-R03-ADJ-01`). No canonical byte was modified by this worker.
- **gate**: proposal only, verdict **pending** — owner adjudication between the E1a/E1b
  formal-sentence repair (changes the F1 hash, needs F1 re-review) and ratifying the variable-wise
  rendering as R03-conforming. F-GATE-4 (unpublished R17+ rules in the lead tool) still stands.
- **checkpoint**: `runtime/state/flash-13_checkpoint_formgate_rev29_r03.json`; outbox appended 15
  schema-validated events (all `f13-r29r03-*`).
- **numerics_lock**: untouched — no N0/N1 numerics work in this task.

---

## 2026-09-12T01:1x+08:00 — FORM-GATE-01 rev1.3: R03 readings decided by controls (F1/G-CLASSBIND)

Bounded worker 013 (instance `worker-013-20260912T010558-968807`); same standing card, one task.

- **task**: F13-G-CLASSBIND-REV29-R03-SEMANTIC — make the R03 reading question decidable rather
  than leaving the rev1.2 literal failure as the gate's last word.
- **change**: R03 now measures two disclosed readings in every result (`r03_readings`) and uses the
  semantic realization reading S as the pass criterion: keyword sequence of `quantifiers.formal`
  equals the declared `kind` sequence, and every variable of every declared binder occurs at or
  after its own quantifier keyword. L (literal substring, rev1.2) is still reported;
  `--r03-mode literal` reproduces rev1.2 pass/fail with **0 mismatches** over all 34 fixtures
  against the archived suite report (`legacy_v12/fixture_suite_report.v12_r03.json` `07674bac2ab2`).
- **self-refutation**: F-GATE-6 is withdrawn. Canonical WCC `d9cebb9404b2` passes R03 under S
  (both `q` and `t0` occur, bound after `not exists`); the rev1.2 failure was a false positive of
  the literal proxy. All three canonicals now pass all 16 rules at frozen bytes
  (`canonical_recheck_rev29_v13.json`; FROZEN rev29 `815e08079aefbc`).
- **not a relaxation — S is strictly stronger**: 4 controls are accepted by L and rejected by S
  (`c01` declared-kind reorder, `c02` deleted quantifier clause with variables left in the body,
  `c09` extra body keyword, `c10` variable only before its quantifier); `m25_wcc_binder_unused`
  still fails R03 (now isolated to missing `t0`); consistent alpha-rename `c05` is not punished.
  10/10 controls match the expected matrix (`fixtures_r03/manifest.json`, `r03_readings_rev29.json`
  assertions A1–A6 pass).
- **corpus defect found and repaired**: all 34 legacy fixtures declared `ordered[2].kind: exists`
  against their own `not exists p` sentence — invisible to L. `fixtures_v13/` repairs the kind
  token only (legacy+new sha256 and the one-line logical diff per file in its manifest); the
  repaired suite reproduces rev1.2 metrics exactly: 3/3 positives, 25/25 mutants expected rule,
  17/25 single-rule-keyed, 5 caught / 1 blind rephrased, exit 3 absent, exit 0 conforming.
  Legacy corpus and rev1.2 reports are archived unmodified under `legacy_v12/`.
- **gate**: proposal only, still **pending** — proposal favours pass under S, with the R03 reading
  adjudication reserved to the rule owner (`astra-life05-verify-gform-r3`); if the owner rules L,
  the worker-064 E1a/E1b repair remains the path (S accepts it too). No canonical byte modified.
- **outbox**: 16 schema-validated events appended (`f13-r03sem-20260912T011448-*`); 16 accepted in
  `research_map/events.jsonl`, 0 rejects.
- **checkpoint**: `runtime/state/flash-13_checkpoint_formgate_rev29_r03_semantic.json`.
- **numerics_lock**: untouched.

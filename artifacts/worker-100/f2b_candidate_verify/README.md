# W100-F2B-CANDIDATE-INDEPENDENT-VERIFY-01 — independent verification of the F2b repair candidate

Worker: `worker-100`. One class-bound task: node **F2b**, class **AF-SCC-C0-VAC-GEN**, gate
**G-FORM**. Read-only worker measurement: no canonical byte, node status, `validation_status`
or gate verdict is written by this task.

## Question

`worker-022` delivered a repair candidate for `schemas/af_scc_c0_vacuum.yaml`
(`artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml`,
sha256 `a110f8e875af…`) and self-checked it (`REPAIR_READY`). It had no independent
verification. At the live pins — canonical F2b `b2ab6acb2bbe…`, FROZEN rev29
`815e08079aef…` — does the candidate close the recorded F2b hard failures, does it change
anything else, and is either repair wording deficient?

## Result (`verdict: REP_CD_01_VERIFIED__REP_CD_02_REQUIRED_WORDING_DEFICIENT`)

| check | measured |
|---|---|
| pins at entry/exit | canonical `b2ab6acb2bbe`, candidate `a110f8e875af`, FROZEN `815e08079aef`; unchanged during the run |
| candidate delta | exactly **2 leaf paths**: `implication_ledger.forbidden_transfers[0].reason`, `regularity.must_not_conflate[0]`; top-level key set identical; line diff confined to lines 152 and 246 |
| REP-CD-01 (line 246) | **verified**: reason now reads *“C2 is a strictly smaller extension class (E_C2 subset of E_C0), so C2-inextendibility is strictly weaker”* — direction-correct against the file’s own chain `E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2` and the F2a sibling’s converse-containment row. Closes the content side of `HF-075-F2b-LARGER`, `W066-R13-F2B-H1`, `B17-R13-01`, `W018-R13-F2B-B2`, `W053-F2B-REV29-01` |
| REP-CD-02 (line 152) | **in scope and required** (4 live reviews carry `must_not_conflate[0]` hard findings: `HF-035-R3-01`, `W066-R13-F2B-H2`, `B17-R13-02`, `W018-R13-F2B-B1`), intent correct (removes the false denial), but **wording deficient**: the new bullet asserts the class *“sits strictly between …”* while retaining *“the informal phrase ‘strictly between’ is not used and must not be cited (worker-16 F2b-16-02 accepted)”* — a self-contradiction, and exactly the phrase tension `HF-035-R3-01` had flagged |
| recommended REP-CD-02 wording | follow the F2a sibling (`schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3`), which states `E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0` and records the old denial as wrong, **without** the prohibited phrase |
| residual not touched by the candidate | `conclusion.conclusion_type: scc_c0_future_inextendibility`, so `HF-075-F2b-VOCAB` remains; the token-authority decision is already prepared by worker-048 (ruling recommendation) and worker-090 (rev13 measurement) |
| structural gate | `check_class_schema.py` (rev29 pin `000e09e4…`) passes on **both** canonical and candidate → the defect and its repair are reviewer-HF-driven, not gate-driven |
| FROZEN cross-check | worker-022 pinned the earlier rev29 emission `3d9e3d77fd87`; live is `815e08079aef`; both manifests record F2b `= b2ab6acb2bbe`, so the same-revision re-emission is immaterial to the candidate |
| controls | 7/7 as pre-registered: inversion restored fires; REP-CD-02 reverted collapses the delta to one path; chain reversal fires; unrelated leaf yields a third path; pristine candidate clean; trailing comment ignored; malformed YAML fails closed |
| determinism / read-only | re-run identical; canonical and candidate hashes unchanged before/after |

## Pre-registration erratum (ERR-W100-01)

The first run’s expectation E5 assumed **no** live F2b hard failure touched
`must_not_conflate`, which would have made REP-CD-02 scope creep. The instrument falsified
that assumption: four independent reviews at/against the F2b rev13 pin carry such findings.
E5 was corrected to the measured direction; the erratum is retained and no other
expectation changed. (This is the project’s “run the null first” rule applied to the
verifier’s own hypothesis.)

## Method and independence

`verify_candidate.py` is an independent instrument, not a wrapper of worker-022’s
`verify_f2b_cd_repair_022.py`: it uses a duplicate-key-refusing YAML loader, its own
leaf-path differ and line diff, its own regex probes for the inversion and the prohibited
phrase, its own review-file HF scan, and its own seven in-memory controls. All inputs are
hash-pinned in `pinned/` (`pinned.sha256`).

## Falsifier

Falsified if any pin moves (canonical F2b ≠ `b2ab6acb2bbe`, candidate ≠ `a110f8e875af`,
FROZEN ≠ `815e08079aef`); or if the candidate’s `forbidden_transfers[0].reason` is
re-inverted or loses its `smaller/subset` clause; or if the REP-CD-02 phrase/disclaimer
tension is shown non-contradictory at these bytes; or if a re-run yields different
per-check results at the same pins.

## Reproduce

```bash
python3 artifacts/worker-100/f2b_candidate_verify/verify_candidate.py
# exit 0 expectations hold / 2 expectation failed / 3 pin drift
```

Authority note: worker events cannot set `status=done`, `validation_status=passed` or a
gate verdict. Only the audit lead / controller may convert this into a G-FORM decision.

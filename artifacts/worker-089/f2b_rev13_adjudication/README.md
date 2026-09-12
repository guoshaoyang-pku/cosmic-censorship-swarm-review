# W089-F2B-REV13-ADJUDICATION-06 — independent finding adjudication for F2b

**Worker:** worker-089 · **Node:** F2b · **Class:** AF-SCC-C0-VAC-GEN · **Gate:** G-FORM
**Task:** self-taken bounded execution task (no worker-089 inbox card was open; the
`audit-r2-A0` card was completed and closed by the preceding pass).

## Why this task

The controller's pass-06 gate audit (2026-09-12T01:01:17) records G-FORM as `pending` with
**F2b = 0 distinct accept reviewers at the current pin** (`b2ab6acb2bbe`), while several
hash-bound hard findings against those same F2b bytes were sitting unadjudicated in the
review stream. This artifact adjudicates those findings at the FROZEN rev29 bytes —
read-only, machine-checked, with planted-defect controls — so the formulation lead has a
measured repair list instead of another prose review.

## Target pins (measured before and after the 120 s window)

| artifact | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (canonical) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` (mirror) | same bytes |
| `artifacts/formulation/FROZEN.json` | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` (rev 29) |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba` |
| `artifacts/formulation/evidence/semantic_escape_rebased.json` | `7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292` |
| `schemas/f1_falsifier_tests.jsonl` | `56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e` |

Any drift in the window voids the adjudication for the newer bytes (see `report.json.hash_drift`).

## Method

`check_f2b_adjudication.py` is a deterministic, read-only stdlib+PyYAML checker: 11 scored
checks, each carrying its measured value and cited lines, plus 8 in-memory controls
(one planted defect or planted repair per check family, and one all-repairs control that
proves no check is unconditionally failing). It writes only its own `report.json`.
`run_acceptance.py` is invoked read-only: its preflight fails before any write.

Checks: pins (C01/C02), class leakage (C03), conclusion inflation (C04), assumption
completeness (C05), decidable falsifier (C06), and the hash-bound findings C07–C11.

## Result

**Verdict: `revise` (score 3.0), 7/11 checks pass, 4 hard findings reproduced, 8/8 controls caught.**

| id | status | finding |
|---|---|---|
| C07 / HF-044-INT-H1 | **unresolved** | `schemas/af_scc_c0_vacuum.yaml:246` says "C2 is a strictly larger extension class", contradicting the file's own chain at line 239 (`E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2`). E_C2 is the **smaller** extension class; the conclusion (C2-inextendibility is weaker) is right, the reason clause is inverted. |
| C08 / HF-044-INT-A2 | **unresolved** | `f0_binding.consistency_evidence_sha256` (line 309) pins the evidence bytes, but `taxonomy_consistency.json` names both taxonomy paths and carries **no** artifact hash, so "CONSISTENT" cannot be tied to the F0 bytes it compared. |
| C09 / HF-044-INT-A6 | **unresolved** | F2b uses `residual_comeager` / `scc_c0_future_inextendibility`; the bound F0 class uses `provisional_baire_residual` / `strong_cosmic_censorship_C0`. Equivalence holds only through `VOCAB_ALIASES.json`, which no `f0_binding` field cites. |
| C10 / W062-ESCAPE-STALE | **unresolved** | The FROZEN-pinned `semantic_escape_rebased.json` binds `base_sha256 1bb78ce9b357` (rev11 C0) while canonical C0 is `b2ab6acb2bbe`; measured `run_acceptance.py` preflight **rc = 3** ("PREFLIGHT FAIL: rebased fixtures are stale"), so the two-stage acceptance claim is not reproducible at the rev13 bytes. |
| C11 / W019-RV13-02 | out of scope | All 25 rows of `f1_falsifier_tests.jsonl` bind F1 rev12 `cce9c60146d6` while F1 canonical is rev13 `d9cebb9404b2`. It is an F1-node defect, but FROZEN rev29 pins the corpus; recorded for the controller because it sits in the same pin set. |
| C03–C06 | pass | No C2/WCC leakage into the C0 conclusion, no conclusion inflation (open problem, promotion requires `artifact_refs`), quantifier domains/genericity/unresolved items declared, tier-1 falsifier decidable with the non-machine-checkable step named honestly. |

## Minimal repair set (formulation lead owns the bytes)

1. line 246 reason → "C2 is a strictly smaller extension class (E_C2 ⊂ E_C0)".
2. add `map_taxonomy_sha256` + `lead_contract_sha256` to `taxonomy_consistency.json` and re-run `check_taxonomy_consistency.py`.
3. add an alias-registry binding (VOCAB_ALIASES sha256) to `f0_binding`.
4. re-run `measure_semantic_escape.py` at the current C0 bytes so `run_acceptance.py` preflight returns 0.

## Falsifier

Each of the four repairs converts its hard finding to resolved on re-measure at unchanged
pins; any pin above moving, or C03–C06 flipping to fail, voids the adjudication for the
newer bytes. Full machine-readable text in `report.json.falsifier`.

## Scope limits

Mechanical read-only adjudication. Sets no gate verdict, no node status, no
`validation_status`; edits no canonical/schema/proposed/evidence/frozen file. A `revise`
here is not a G-FORM failure — only the controller/leads may move the gate.

## Re-run

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-089/f2b_rev13_adjudication/check_f2b_adjudication.py          # 120 s window
python3 artifacts/worker-089/f2b_rev13_adjudication/check_f2b_adjudication.py --no-wait # fast preflight
```

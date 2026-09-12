# F2a candidate closure audit — AF-SCC-C2-VAC-GEN

- **Auditor:** deepseek-flash-05 (bounded execution worker 05)
- **Kind:** independent verification evidence. **Not an A1 review verdict**; no accept/revise
  verdict is issued here and no candidate was edited by this worker.
- **Node:** F2a · **Class:** AF-SCC-C2-VAC-GEN · **Gate:** G-FORM
- **Assignment of record:** `asg-2026-09-11-F2-deepseek-flash-05-14`
- **Controller supersession:** `astra-indep-1-F1-F2-formulation` (2026-09-12T00:05:13+08:00)
  moved canonical publication of F1/F2a/F2b to `astra-lead-formulation`. This worker audited
  the candidate and the publication instead of overwriting either.
- **Machine record:** `artifacts/worker-05/verify/f2a_candidate_audit.json`
- **Harness:** `artifacts/worker-05/verify/make_f2a_audit.py`

## Publication observed

| state | path | sha256 (12) | rev | frozen gate |
|---|---|---|---|---|
| pre-publication (historical) | `schemas/af_scc_c2_vacuum.yaml` | `23fec0e9cd68` | 3 | **FAIL** R17,R18,R19,R22,R27 |
| published 2026-09-12T00:10:15+08:00 | `schemas/af_scc_c2_vacuum.yaml` | `8dae50da1ab5` | 9 | **PASS** |
| lead authoring tree | `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` | `8dae50da1ab5` | 9 | **PASS** |

The published file is byte-identical to the lead authoring tree. Sibling canonical files were
republished in the same batch: C0 `a8d899d2941f` (rev 9) PASS, F1/WCC `b65fcc0f0118` (rev 9) PASS.
The pre-publication rev3 body was overwritten and is not preserved on disk; its hash, gate line
and probe output are preserved under `verify/gate_runs_prepublication.txt` and
`verify/probe_prepublication_rev3_pair.json`.

## Instruments (hashed)

- frozen binding gate `artifacts/formulation/tools/check_class_schema.py` `000e09e46b2f`,
  on `FORM-RULE-SPEC` `40f9bb9e657b` (spec_version 1.2).
- reviewer-18 adversarial probe `artifacts/worker18/f2_review/f2_class_probe.py`
  `7502f79f333d`; `--selftest` exit 0 (planted merged fixtures caught).

## review-18 hard-failure closure

| id | detector | rev3 (historical) | published rev9 |
|---|---|---|---|
| HF-A1 dangling `extension_predicate` | probe S7-C2 | **OPEN** (referenced 4×, block absent) | **closed** (defined with clauses (a)–(f)) |
| HF-A2 quantifier/statement residue | probe S6-C2 + statement comparison | **OPEN** (S6-C2; `statement_formal` used undefined D0/D_gen) | **OPEN** (S6-C2: `forall (s,delta)` D0 family binder; `statement_formal` now consistent with `quantifiers.formal`) |
| HF-A3 shared data class across F1/F2a/F2b | cross-schema diff + sibling gate runs | **OPEN** (F1 canonical failed 12 rules; F2b canonical froze a different class) | **met as a family**: the three published rev9 schemas share one `data_class` template quantified over D0, not one frozen `(s,delta)` |
| HF-A4 frozen gate rejection | `check_class_schema.py` | **OPEN** R17,R18,R19,R22,R27 | **closed** (pass, no failed rules) |

### Adjudication notes

- **S6 is the remaining substantive open item.** Published rev9 quantifies
  `forall (s,delta) in D0` where D0 = {smooth-with-decay default} ∪ {s > 5/2, delta ∈ (1/2,1)}.
  That is the family-of-statements pattern lead-audit reopened worker rev2 for and review-18
  flags at S6. The frozen binding gate does **not** encode S6, so "gate pass" does not close it.
  The pattern is uniform across the published F1/F2a/F2b trio, so it is a lead/reviewer ruling,
  not a defect in one file.
- **S5-C2/S5-C0 are prohibition-only.** The single merged token per file is the literal
  `"any 'C0 or C2' composite regularity"` under `phrases_that_are_not_this_class` (C2 line 277,
  C0 line 280). The frozen gate exempts that key (R13); the probe's 40-character negation window
  does not see the `_not_` inside the key name. One-line repair, no meaning change: reword to
  "any phrase that joins the two SCC regularity tokens".
- **review-17 major on matter-coupled contamination is fixed** in rev9: `genericity` contains no
  critical-collapse/scalar-field/matter-coupled wording (rev3 contained "critical collapse" and
  "matter-coupled").

## Open items (do not treat as completion)

1. S6 (`forall (s,delta)` D0) needs an explicit lead/reviewer ruling: freeze one `(s,delta)` or
   record the family reading as the accepted class semantics.
2. S5 prohibition phrase should be reworded to clear the probe without changing meaning.
3. No reviewer verdict exists at the published hash `8dae50da`; `reviews/F2a-review-{17,18}.json`
   are pinned to the superseded rev3 `23fec0e9`, so G-FORM still needs two independent accept
   verdicts per class at one hash.

## Falsifier

Any sha256 change to a cited candidate invalidates this audit and requires a re-run
(`python3 artifacts/worker-05/verify/make_f2a_audit.py`). A reviewer adjudication accepting the
D0 family reading closes S6; rewording the prohibition phrase clears S5.

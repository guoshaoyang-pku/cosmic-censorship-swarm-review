# W026-F2B-CANDIDATE-ELECTION-CONSUMPTION-01

Worker `worker-026` · node `F2b` · class `AF-SCC-C0-VAC-GEN` · gate `G-FORM` · read-only on every
canonical path. No gate verdict, no node status, no `validation_status` promotion, no canonical write.

## One-line result

Nine distinct minimal two-carrier F2b repair candidates exist at the FROZEN rev29 pins; **eight pass a
direction-aware election** and one (`84b5d3fa29a6`) asserts the *inverted* entailment
`H2_loc-inextendibility entails this class` and is rejected — yet `84b5d3fa29a6` is exactly the
candidate the rev30 freeze rehearsal (W058) froze. **No candidate holds all three roles
(elected + recommended + rehearsed).** The repaired text is under-determined and the rehearsed object
is a direction-rejected one.

## Live state audited (all pinned, measured at run start and re-checked at exit)

| artifact | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (live F2b rev13) | `b2ab6acb2bbe7f86…` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` (mirror) | `b2ab6acb2bbe7f86…` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a sibling) | `e9a27996dfd308bd…` |
| `schemas/af_wcc_vacuum.yaml` (F1) | `d9cebb9404b2e79e…` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc16…` |
| W058 rev30 rehearsal report | `1e31bbe5e9336e68…` |
| W083 candidate adjudication report | `83b50c27976a068d…` (see F7) |
| W080 entailment audit report | `f0dae0292f1d1fe5…` |

The containment model is taken from the artifact's **own** ledger, not from prose:
`E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇ E_C2`, so `C0-inext ⇒ H2loc-inext ⇒ C2-inext`, never the reverse.

## Election (R1–R4)

* **R1** D1 size premise repaired (`strictly larger` gone, a direction-correct size relation present).
* **R2** D2 denial removed and containment asserted — **quote-aware**: a bracketed/quoted *mention* of
  the superseded denial is not an assertion (control C10; 5 candidates do this).
* **R3** D2 entailment direction consistent with the ledger (active and passive inversion patterns).
* **R4** exactly the two carrier leaves changed (metadata re-stamps exempt).

| id | sha256 | exemplar author | R3 | elected | roles |
|---|---|---|---|---|---|
| W026-CE-01 | `1315427fbc92` | worker-083 | nesting | yes | recommended by W083 (own candidate, author_conflict) |
| W026-CE-02 | `4951cc969803` | worker-080 (`candidate_nesting_only`) | nesting | yes | — |
| W026-CE-03 | `51c253c46306` | worker-080 (`candidate_corrected`) | correct | yes | — |
| W026-CE-04 | `679ab7bc8746` | worker-024 | nesting | yes | W083's pre-revision recommendation |
| W026-CE-05 | `6aaff1633faf` | worker-020 | nesting | yes | — |
| W026-CE-06 | `84b5d3fa29a6` | worker-002/008/066 lineage | **INVERTED** | **no** | **rehearsed by W058 (rev30)**, validated by ≥3 reports |
| W026-CE-07 | `9ab32ee39d00` | worker-023 v2 corrected | correct | yes | — |
| W026-CE-08 | `a110f8e875af` | worker-022 | nesting | yes | 1 validate mention |
| W026-CE-09 | `a6724e72bba3` | worker-075 dry-run | correct | yes | — |

Cross-check: 7 of these hashes appear in W070's declared census; W070's remaining declared states are
D1-only or broader rewrites (listed in `report.json.election.broad_or_partial_states`). 19 byte-states
were discovered in total; the 9 above are the minimal two-carrier field.

## Findings

* **W026-CE-F1 (material)** 9 minimal candidates, 8 elected → the repaired text is not unique; "the
  candidate" is under-determined absent an explicit owner election.
* **W026-CE-F2 (hard)** 1 minimal candidate carries the inverted entailment and is rejected on
  direction; it is also the object rehearsed/validated downstream.
* **W026-CE-F3 (hard)** No candidate holds elected + recommended + rehearsed. The rev30 rehearsal
  object `84b5d3fa29a6` is direction-rejected; the current W083 recommendation `1315427fbc92` is
  electable but unrehearsed.
* **W026-CE-F4 (material)** The two W080 corrected candidates are electable but carry zero rehearsal
  or validation consumption.
* **W026-CE-F5 (method)** 5 candidates quote the superseded denial inside brackets; a naive denial
  detector misclassifies them. Election is quote-aware, proven by controls C7/C10.
* **W026-CE-F7 (material)** The recommendation role moved inside the audit window: the same W083 path
  (`83b50c27976a…`) recommended `679ab7bc8746` at ~01:08 and now self-recommends `1315427fbc92` with
  `author_conflict: true`. Any owner action on "the recommended candidate" must pin the report hash.

## Consequences for the owner (no verdict claimed)

Before any rev30 freeze: (1) elect one candidate explicitly by sha256; (2) re-run the rev30 rehearsal
and the freeze-identity guard against that exact hash; (3) do not rely on the current rehearsal
certificate, which is bound to `84b5d3fa29a6`; (4) re-verify after landing. Four of the elected
candidates are direction-correct or direction-silent and differ only in wording, so the election is a
policy choice, not a mathematics choice — but it must be recorded.

## Controls

11/11 pass (`controls.json`): live and rev12 baselines are not repairs; byte copy and metadata
re-stamp preserve election; a third semantic leaf breaks R4; reverting D1 fails R1; an **asserted**
denial fails R2 while a bracketed **mention** passes (C10); planted active and passive inversions are
classified INVERTED (C8, C11); a YAML roundtrip preserves the verdict.

## Falsifier

Falsified if a re-run at the same pins finds (a) at most one elected candidate, (b) a candidate
holding elected + recommended + rehearsed roles, (c) an inverted candidate passing R3, or (d) any
control C1–C11 not discriminating as declared.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-026/f2b_candidate_convergence/converge.py
```

Deterministic, stdlib + PyYAML only; writes only inside
`artifacts/worker-026/f2b_candidate_convergence/`. Any pin movement aborts fail-closed.

# W057-GFORM-D0-SINGLE-CLASS-VERIFY-01 — worker-057

**Task (self-selected; no card in `comms/inbox/worker-057.jsonl`).** Class-bound:
`AF-WCC-VAC-GEN` / `AF-SCC-C2-VAC-GEN` / `AF-SCC-C0-VAC-GEN`; nodes `F1,F2a,F2b`;
gate `G-FORM`. One bounded worker task: measure, at the **frozen rev-29 bytes**, exactly how far
the G-FORM unmet item

> "no single frozen data class (s,delta,norm) is shared by F1/F2a/F2b, which disables the
> licensed C0=>C2 transfer"

moves now that `D0` has been retyped as a *tagged disjoint union* over a bare index `r`.
This is a measurement, not a gate verdict; the class-identity ruling stays with the gate owner.

## Inputs (pinned; every hash re-verified at run time — a moved byte aborts the run)

| file | sha256 | node | bytes |
|---|---|---|---|
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2…c5d3d` | F1 | 37662 |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd3…d82fe` | F2a | 30594 |
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe…4501c` | F2b | 35602 |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a961…094e3` | F0 | 36372 |
| `artifacts/formulation/FROZEN.json` | rev **29**, frozen 2026-09-12T00:57:26+08:00 | — | — |

`FROZEN.json` re-pins all three schema paths to the hashes above (`FROZEN_pins_match_disk_all_three = true`).

## Verdict: `MEASURED_SHARED_UNION_AND_PARAMETERISED_CONTRACT__NO_SINGLE_FROZEN_TRIPLE`

All seven pre-registered controls pass (C1–C7). Two of them (C2, C5/C7) caught over-claims in the
first draft of this instrument; the instrument was corrected and the controls re-run, not relaxed.

| # | finding | state | evidence |
|---|---|---|---|
| D0-01 | The three schemas share a **byte-identical** `D0` regularity domain (normalized-JSON equal): the rev-11/12 bare-disjunction charge is repaired at rev 29. | confirmed | all three pins |
| D0-02 | `D0` supplies exactly **one** complete `(s,delta,norm)` instantiation — the sobolev branch (`s > 5/2`, `delta in (1/2,1)`, weighted Sobolev product). The `smooth` branch is a Fréchet `C^infinity` class with pointwise rates: no `(s,delta)` pair, no normed space. | confirmed | `quantifiers.domains.D0` definition text; control C2 |
| D0-03 | `data_class.regularity_class` is **not** byte-identical across the three schemas: 2 distinct normalized blocks (F2a == F2b; F1 differs). The divergence is structural, not only prose — F1 alone carries `data_class.excluded_data` and the declaration *"smooth-data statements may not be transferred to the Sobolev variant without an approximation/stability argument"* (F1 line 136). That sentence is the sharpest recorded admission that the two `D0` branches are not one interchangeable data class. | confirmed | F1 line 136; `data_class` key comparison |
| D0-04 | On the gate's literal wording there is still **no single frozen `(s,delta,norm)`**. What is shared is (a) the union domain and (b) a numeric/space contract that is itself a **family**: the shared object is the parameterised `H^s_delta x H^{s-1}_{delta+1}`, `s > 5/2`, `delta in (1/2,1)` — a contract over ranges, not one frozen triple. The *norm* is shared; the numeric *point* is not fixed. | confirmed | D0 definition; `regularity_class` numeric core; control C7 |
| D0-05 | On the "record the divergence" reading the union is a **stronger substitute**, not an equivalent one: `forall r in D0` makes the class statement hold for the smooth tag and for every `(s,delta)` at once. If the criterion means "the three classes must be instantiated over one common frozen `(s,delta,norm)` so the transfer lemma is stated on a common data space", the union does not supply that — it supplies a common *index set*. | **reserved** | D0-01…D0-04 |

## What changed vs. the rev-11/12 record

- The rev-11/12 "family of two class statements" defect (map `reviews[43]`, `reviews[70]` Q2) is
  **repaired in form**: `D0` is now a tagged disjoint union under a single binder `r`, and
  `statement_formal`, `negation` and `negation_normal_form` all use `r`. No schema still ranges a
  pair binder over a disjunction.
- What remains is not the old defect restated. It is a smaller, precise question: whether a union
  over a bare index satisfies a criterion written for a *single frozen* `(s,delta,norm)`. The
  measurement cannot decide that; it can only show that the literal object named by the criterion
  (one triple) is not present, while the union and the parameterised contract are.

## Reserved adjudication (not this worker's to make)

> Does the tagged-union `D0` (`forall r in D0`) satisfy G-FORM's "single frozen data class
> `(s,delta,norm)` shared by F1/F2a/F2b", or must one `(s,delta,norm)` be frozen and the other
> branch registered as a variant?

Precedent that must travel with the ruling (both directions already exist in the tree):

- `research_map/research_map.json#reviews[43]` — "family of two class statements" supersedes an earlier accept.
- `research_map/research_map.json#reviews[70]` Q2 — "disjunctive D0: not acceptable for class identity".
- `reviews/F2b-review-034-repin.json` — records that G-FORM's own text allows *"or record the divergence explicitly"*, which `D0` does.
- `reviews/F1-review-088-rev12.json` — literal wording satisfied by shared `D0` + equal numeric contract; a strict byte-identity reading fails.

## Falsifier

Re-hash the five pinned inputs and re-run
`artifacts/worker-057/gform_d0_single_class_verify/verify_d0_single_class.py`.
This report is **falsified for the recorded sha256 values** if:

1. any pinned input hash differs from the table above (moved bytes void the report for the new bytes);
2. any control C1–C7 flips to `pass: false`;
3. `D0_normalized_equal_all_three` becomes false, or `D0` stops being a tagged union over a bare index;
4. `regularity_class_distinct_block_count_is_1` becomes **true** (i.e. one frozen block appears — which
   would move the criterion toward met and require a new measurement);
5. a `definition_ref`/`symbols` block pins a single `(s,delta,norm)` and registers the other branch as
   a variant at a named revision;
6. F2a or F2b begins carrying the same no-transfer declaration as F1 (removing the structural divergence).

## Evidence refs

Schema evidence (full sha256):

- `schemas/af_wcc_vacuum.yaml#d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d`
- `schemas/af_scc_c2_vacuum.yaml#e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe`
- `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c`
- `research_map/formulation_taxonomy.yaml#0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3`

Artifacts: `report.json` (machine report, deterministic — two consecutive runs hash
identically), `verify_d0_single_class.py` (instrument), `emit_events.py` (emitter),
`manifest.json` (authoritative hash record for all four; this file and the instrument
are hashed there rather than here, because a file cannot contain its own hash).

## Scope and honesty

- No gate verdict, node status, or `validation_status` is claimed. `claims_completion: false`.
- No schema was modified. The instrument is read-only and writes only inside
  `artifacts/worker-057/gform_d0_single_class_verify/`.
- This does not decide whether the cosmic-censorship formulation is mathematically adequate; it
  measures whether one named artifact-level criterion is literally instantiated at one revision.

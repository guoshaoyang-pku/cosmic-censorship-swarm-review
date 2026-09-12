# W080-REC37-VOCAB-CROSSWALK-01 — conclusion_type crosswalk + assertion-correct consistency check

**Worker:** worker-080 · **Gate:** G-FORM · **Nodes:** F1, F2a, F2b
**Classes:** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
**Authority:** worker evidence only. No gate verdict, no node status, no `validation_status=passed`,
no canonical write, no mathematics or physics claim. Adoption is `astra-lead-formulation`'s.

## Why this artifact exists

REC-36 (pass 08) authorizes exactly one formulation revision (rev14 / FROZEN rev30) and lists seven
fold items. Item (4) is: *per REC-37, the `scc_*` canonical / `strong_*` alias crosswalk + an
assertion-correct consistency check*. REC-37 rules that the class schemas keep the `scc_*` tokens
(canonical), that the F0 `strong_cosmic_censorship_*` entries are alias forms, and that
HF-075-F2a-VOCAB / HF-075-F2b-VOCAB are alias-vs-canonical **presentation** conflicts — discharged by
a pinned crosswalk plus a consistency check, **never** by a write to
`research_map/formulation_taxonomy.yaml` (which voids G-F0).

No crosswalk artifact existed on disk when this task started: `strong_cosmic_censorship_C2` appeared
in `artifacts/formulation/` only inside `VOCAB_ALIASES.json` itself. This task supplies the missing
artifact and a checker that decides the question mechanically.

## Deliverables

| file | role |
|---|---|
| `crosswalk.json` | the pinned crosswalk: canonical ↔ aliases ↔ F0 allowed entry, per token, with class ids, live schema anchors and provenance hashes |
| `audit_vocab_crosswalk.py` | deterministic, read-only, fail-closed checker (12 rules + 11 controls) |
| `report.json` | measured result at the pinned hashes |
| `gate_runs/*.json` | raw canonical structural-gate reports for the three schemas |
| `SHA256SUMS` | hashes of the deliverables |

## Result at the pinned hashes (measured)

Pins: F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe`, F0 taxonomy `0abb9ed8a961`,
VOCAB_ALIASES `46cd9f1eb534`, rule_spec `40f9bb9e657b`, FROZEN `815e08079aef`, gate tool
`000e09e46b2f`; mirrors byte-identical.

**Verdict: PASS — 12/12 rules, 0 hard findings; 11/11 controls.**

| rule | result |
|---|---|
| V1 crosswalk internal schema | pass |
| V2 alias partition (recomputed from live `VOCAB_ALIASES.json`) | pass — no collision, no alias equals a canonical, no rejected token reused |
| V3 F0 allowed-list coverage | pass — all 3 F0 entries map to exactly one canonical (`weak_cosmic_censorship` canonical; `strong_cosmic_censorship_C2/_C0` aliases) |
| V4 asserted `conclusion.conclusion_type` is canonical | pass — F1 `weak_cosmic_censorship` (l.241), F2a `scc_c2_future_inextendibility` (l.209), F2b `scc_c0_future_inextendibility` (l.211) |
| V5 no alias in any other `*conclusion_type` key | pass (0 occurrences) |
| V6 R11 binding vs `rule_spec.vocabularies.class_conclusion_type` | pass |
| V7 crosswalk line anchors | pass |
| V8 mirror identity | pass |
| V9 F0 no-write invariant (content == crosswalk record) | pass |
| V10 every pin declared in FROZEN.json at the same hash | pass |
| V11 pin guard, re-measured **after** all sandbox controls | pass — no canonical byte moved during this run |
| V12 binding structural gate (`check_class_schema.py`) on all three schemas | pass (exit 0, verdict `pass`, 3/3) |

### What this discharges (conditional on adoption)

- **HF-075-F2a-VOCAB** and **HF-075-F2b-VOCAB**: the schema tokens are the REC-37 canonical form and
  are exactly what R11 already binds; the F0 entries are the same tokens in alias form. No semantic
  class mismatch is asserted by any frozen instrument. Recorded in `crosswalk.json`
  `hard_failure_dispositions`. This is *worker evidence for the r3 reviewer*, not a verdict.
- It writes nothing to `research_map/formulation_taxonomy.yaml`. V9 records the F0 alias list and the
  REC-37 policy that any normalization of it is a separate G-F0 reopening decision.

## Controls (assertion-vs-mention is the point)

Every control runs in a disposable sandbox under `control_sandbox/`; canonical paths are only read.
`K6` is the specificity control: an alias placed in a provenance/mention context **and** in a YAML
comment must **not** fire, while `K1b` proves the same rule fires when the alias sits in an asserted
`*conclusion_type` key. `K8` tampers with an expected hash in memory to prove the pin guard is live.

| control | mutation | expected |
|---|---|---|
| K0 | none (baseline) | no findings |
| K1 | alias into `conclusion.conclusion_type` | V4 + V6 |
| K1b | alias into another `misc_conclusion_type` key | V5 |
| K2 | unknown token into `conclusion_type` | V4 + V6 |
| K3 | C0 token into F1's `conclusion_type` | V6 |
| K4 | alias collision injected into `VOCAB_ALIASES.json` | V2 |
| K5 | unmapped token added to F0 allowed list | V3 |
| K6 | alias in mention context + comment only | none (specificity) |
| K7 | two live evaluations | byte-identical |
| K8 | in-memory pin tamper | V11 |
| K9 | canonical/mirror divergence | V8 |

## Reproduce

```bash
cd <repo root>
python3 artifacts/worker-080/rec37_vocab_crosswalk/audit_vocab_crosswalk.py
# exit 0 PASS / 1 check failure / 2 control failure / 3 pin drift
```

## Falsifier

Re-run the instrument at the pinned hashes. Falsified if: any measured pin differs (drift voids the
run); a canonical schema asserts an alias or unknown token; an alias occurs in an asserted
`*conclusion_type` position; a F0 allowed entry maps to no or to more than one canonical token; the
`VOCAB_ALIASES` partition collides; R11 disagrees with the crosswalk; a mirror diverges; a control
returns its unmutated verdict; or K1b and K6 produce identical outcomes (the checker would be blind
to assertion vs mention).

## Not claimed

- Not a gate verdict; not a node status; no `validation_status=passed`.
- No canonical file written or modified; `crosswalk.json` is a proposal whose owner is the
  formulation lead. Suggested canonical path: `artifacts/formulation/conclusion_type_crosswalk.json`.
- No claim about the truth of WCC/SCC statements; this is a token/vocabulary axis only.
- No claim that F0 is wrong; F0's alias entries are correct as a *declaration*, and REC-37 makes their
  normalization a separate G-F0 decision.

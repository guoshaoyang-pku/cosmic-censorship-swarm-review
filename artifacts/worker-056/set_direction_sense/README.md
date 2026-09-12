# W056-SET-DIRECTION-SENSE-01

Bounded class-bound worker task taken with no inbox card (`comms/inbox/worker-056.jsonl` does not
exist). Node **F1**, class **AF-WCC-VAC-GEN**, gate **G-FORM**. Read-only: no canonical, ledger,
numerics or frozen file was written; no gate verdict or node completion is claimed.

## The question

The lead blocker **L-FORM-03** reports that an "inverted SET direction" survives at five
locations after the rev29 evidence-binding repair. Variant **SET** replaces the canonical
single-q TAIL visibility predicate `Vis_tail` by the union predicate
`Vis_set(gamma) := gamma([0,T)) subset UNION_{q in I+} J^-(q)`.

"Strictly stronger / strictly weaker" is used about **two different objects whose directions are
opposite**:

| object | relation | direction for SET |
|---|---|---|
| visibility **predicate** | `Vis_tail => Vis_set`, converse fails (omega chain) | strictly **weaker** / coarser |
| censorship **conclusion** | `no Vis_set-singularity => no Vis_tail-singularity`, converse fails | strictly **stronger** |

Both are machine-checked here (`report.json`, `model`). Consequently the F0 sentence
"The set-based reading ... is strictly stronger" is **not demonstrably false**: it is false only
under the predicate reading, true under the conclusion reading — and the parenthetical defines
the predicate while the noun "reading" does not type the sense. The honest verdict is
**untyped / ambiguous**, not "inverted".

## Machine-checked results

- **T1** fixed-`q` whole-curve containment <=> fixed-`q` tail containment: **0 violations** over
  all preorders on n <= 4 points (4 + 29 + 355 preorders), all non-empty `I+`, all chains
  (`predicate_cases = 29,736`). Corroborates worker-086 F-086-V1 / worker-040.
- **T2** `Vis_tail => Vis_set`: **0 violations**.
- **T3** finite `I+` (every finite chain has a causal maximum) admits **no** `Vis_set` /
  not-`Vis_tail` separation: **0**; conclusion census `C_set => C_parent`: **0 violations** over
  5,540 worlds.
- **T4** omega model `x_i <= x_j iff i<=j`, `x_i <= q_j iff i<=j`, `I+ = {q_j}`:
  `Vis_set` true (witness `q_i`); for every `q_j` and `t0` the index `max(j,t0)+1` is not `<= q_j`.
  Machine-checked for all bounded `(j,t0)` in prefixes N = 8, 24, 64 (0 failures) plus the
  closed-form grid (65,536 checks); the step to infinite `I+` is the stated unboundedness lemma
  (labelled as proof, not enumeration).
- **Conclusion strictness**: in the omega world with the chain as the only curve, `C_parent` holds
  and `C_set` fails, so `C_set => C_parent` is strict.

## Census of the five L-FORM-03 locations (+ one downstream carrier)

All inputs were hash-pinned pre and post; **no drift**.

| row | location | verdict |
|---|---|---|
| SET-DIR-01 | `research_map/formulation_taxonomy.yaml:200` (F0 canonical, frozen) | `AMBIGUOUS` — TRUE conclusion-level, FALSE predicate-level, untyped; **do not edit** (writing voids G-F0/REC-11) |
| SET-DIR-02 | `artifacts/formulation/formulation_taxonomy.yaml:176` (D1) | `LABEL_DEFECT_AMBIGUOUS` — token attaches to "lies outside J^-(I+) as a SET" (the negation; TRUE), but the field labels it `visibility =` |
| SET-DIR-03 | `artifacts/formulation/VARIANT_REGISTRY.json:57` | `TRUE_BUT_SENSE_INCOMPLETE_AT_VARIANT_LEVEL` |
| SET-DIR-04 | `artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json:11` | `TRUE_BUT_SENSE_INCOMPLETE_AT_VARIANT_LEVEL` |
| SET-DIR-05 | same delta `:22` (`visibility.definition`) | `TRUE_IN_PREDICATE_SENSE` — correctly typed |
| SET-DIR-06 | `schemas/af_wcc_vacuum.yaml:235` (rev13 F1) | `TRUE_IN_PREDICATE_SENSE` — correctly typed |
| SET-DIR-07 | same delta `:27` (negation conclusion) | `TRUE_IN_CONCLUSION_SENSE` — correctly typed |
| SET-DIR-09 | `reviews/G-FORM-visdir-residual-086.json:33` (F-086-V1 summary) | `SENSE_INCOMPLETE_AT_VARIANT_LEVEL` — live downstream carrier |

**No location carries a direction token that is false in the sense its own clause types.** The
residual is a sense-typing/annotation defect, not a surviving inversion.

## Downstream hazard (F4)

Because `C_set => C_parent`, a theorem proved for variant SET **transfers to** AF-WCC-VAC-GEN,
while a parent-class theorem does **not** transfer to the variant. A variant-level `strength`
field reading only "strictly weaker than AF-WCC-VAC-GEN" inverts the transfer direction if read
conclusion-level, and the same phrasing already appears in a live review record (SET-DIR-09).

## Recommendation

1. Do **not** edit `research_map/formulation_taxonomy.yaml:200` on this evidence — it would void
   G-F0 for an ambiguity that is TRUE under one of its two readings.
2. Re-scope **L-FORM-03** from "inverted direction survives" to "sense-typing defect".
3. Add the dual sentence to variant-level `strength` fields: *strictly weaker as a visibility
   predicate; strictly stronger as a censorship conclusion (SET entails AF-WCC-VAC-GEN)*.
   Apply to `VARIANT_REGISTRY.json` and the SET delta; no class id, hypothesis or predicate change.
4. Relabel (do not flip) the D1 supplement row; the strength token belongs to the negated
   outside-the-union statement.
5. Record the sense whenever a ledger row or review cites a theorem about variant SET.

## Falsifier

FALSE if any of: (a) a finite reflexive-transitive model with a causal chain and finite `I+` has
`Vis_set` and not `Vis_tail`; (b) the omega model violates transitivity/reflexivity, or `Vis_set`
fails, or some `q_j` sees a tail; (c) a location is exhibited whose direction token is false in
the sense its own clause types; (d) a pinned input sha256 changes without the row reading
`UNMEASURED_DRIFT`; (e) a class-binding record transfers the parent conclusion to variant SET as
if the variant were weaker (would make F4 a hard failure, not a hazard note).

## Files

- `run_sense_audit_056.py` — deterministic offline checker (models, controls, census, pins).
- `report.json` — full result: model census, controls, per-row raw clauses and sense evidence.
- `README.md` — this file.
- `emit_events.py` — emits the comms/outbox events and the checkpoint (idempotent, reads `SHA256SUMS`).
- `SHA256SUMS` — hashes.

Re-run: `python3 artifacts/worker-056/set_direction_sense/run_sense_audit_056.py`
(verdict line `MODEL_OK / CONTROLS_PASS / INPUTS_STABLE`; any F1/F0 revision moves the pins and
rows read `UNMEASURED_DRIFT` or `NOT_FOUND`).

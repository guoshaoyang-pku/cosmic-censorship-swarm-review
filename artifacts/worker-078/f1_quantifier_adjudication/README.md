# W078-F1-QUANT-ADJ-01 — independent adjudication of the F1 quantifier defect

**Worker:** worker-078 (bounded execution worker, class-bound task taken from the open gate queue; no inbox card existed for worker-078).
**Class:** `AF-WCC-VAC-GEN` · **Node:** F1 · **Gate:** G-FORM.
**Target:** `schemas/af_wcc_vacuum.yaml`, pinned at
`9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` (live == authoring mirror == snapshot at review time).
**Verdict:** `revise` — one critical content defect confirmed (9/9 primary checks), four secondary defects confirmed.

## Why this task

At 00:21–00:22 the F1 review corpus contained three `revise` verdicts and one lead `accept` bound to the
same bytes. The contested item is worker-19 `F-1` (nearest `HF-06`): the quantifier expansion was said to
use whole-curve single-q visibility while the canonical predicate is tail-based. A gate cannot close on an
unadjudicated critical contradiction, and it must not stay blocked on an unreproduced assertion. This run
adjudicates that one claim independently, from the pinned bytes only.

## Method

1. **Pin first.** Copy the canonical file to `snapshot/`, verify sha256 equals the audit-measured hash,
   re-measure the live path and the authoring mirror. Any live drift voids the live binding (it is reported,
   not silently rebound).
2. **Adjudicate the pinned bytes** with `adjudicate_f1_quantifier.py`: 16 deterministic checks (3 binding,
   9 primary defect, 4 secondary), each printing `file#line` evidence.
3. **Test–retest** with `--pin <sha256>` (`report_rerun.json`); check-status vectors must be identical.
4. No network, no writes outside this directory and the review/checkpoint channels.

## Result (detail in `report.json`)

The defect is **confirmed**, and the file refutes its own wording:

- `quantifiers.formal` (:48–55) ends `not exists q in I+ with gamma subset J^-(q) intersect M`;
  `D5` (:79–81) defines the witness as `gamma([0,T))` in `J^-(q)`. Both are **whole-curve**.
- `visibility.definition` (:220) is **tail-based**: `exists q in I+ AND t0 in [0,T)` with
  `gamma([t0,T))` in `J^-(q)`; `visibility.negation_conclusion` (:222) negates over every `q` **and every `t0`**.
- Whole-curve containment ⇒ tail containment (take `t0 = 0`); the converse fails. So `quantifiers.formal`
  is **strictly weaker** than the conclusion it expands: the schema's own separating scenario — a geodesic
  that starts in the exterior and ends inside the black-hole region — is tail-visible but not whole-curve-visible.
- `quantifiers.negation` (:84–88) says "is visible from I+", i.e. tail semantics, so it is **not** the
  negation of `quantifiers.formal`.
- :220 states that requiring the whole geodesic to lie in `J^-(q)` "would misclassify" exactly that
  scenario; the rev9 note (:17–19) declares the tail predicate canonical, but the formal block and D5 were
  never updated. This is an editing residue, and the repair is local: `conclusion.statement_formal` (:251)
  already refers to the predicate by name, so no class semantics need change.

Secondary confirmations: D0 is a mixed-type domain under a pair binder (:63–66); `class_contract_pointer`
(:38) does not resolve in the canonical taxonomy (`class_contracts` absent; owner = formulation lead,
CF-13); the consistency evidence is not hash-bound; duplicate `revised_at` keys and a future-dated
`revised_at=00:30` (:8–28).

## Falsifier

This adjudication is overturned by any one of: a tail-constrained `formal`/`D5` in the pinned bytes; a
monotonicity lemma showing whole-curve non-containment follows from tail non-containment; a notation ruling
that `gamma subset J^-(q)` denotes a tail; or a redefinition of the conclusion to whole-curve visibility
(a class-semantics change needing re-adjudication against F0). Full list in `report.json → falsifier`.

## Files

| path | role |
|---|---|
| `adjudicate_f1_quantifier.py` | deterministic harness (pin-then-verify, drift-aware) |
| `report.json` | primary evidence: 16 checks, strictness argument, falsifier, repair |
| `report_rerun.json` | `--pin` test–retest |
| `snapshot/af_wcc_vacuum.9a8bd4c96800.yaml` | immutable byte-exact pinned revision |
| `../../reviews/F1-quantifier-adjudication-078.json` | review event body (verdict `revise`, `cited_sha256` = pin) |

**Authority note:** this is a worker review, not a gate verdict. No `status=done`, `validation_status`,
or gate verdict is set here.

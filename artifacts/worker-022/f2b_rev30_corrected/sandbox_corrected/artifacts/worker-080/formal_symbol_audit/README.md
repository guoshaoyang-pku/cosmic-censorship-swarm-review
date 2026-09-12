# worker-080 — formal-surface symbol / quantifier audit (W080-FSYM-01)

**Task.** One bounded class-bound task. No assignment card existed in
`comms/inbox/worker-080.jsonl` for fleet instance
`worker-080-20260912T002242-968807`; the task was taken from the standing
G-FORM / G-F0 blocker set ("no independent verdict binds the final hashes",
leadform-blocker-0006 B1) and is bound to class **`AF-WCC-VAC-GEN`** (F1),
cross-checked against `AF-SCC-C2-VAC-GEN` (F2a) and `AF-SCC-C0-VAC-GEN` (F2b).

**Inputs (measured at run, re-measured at end of run — no drift):**

| input | sha256 |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1, rev11) | `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a, rev11) | `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b, rev11) | `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` |
| `research_map/formulation_taxonomy.yaml` (F0, canonical) | `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc` |

**Instrument.** `audit_formal_symbols.py` — independent tokenizer/classifier,
no imports from the canonical gate tooling. It checks (A) that every
predicate-like symbol in `conclusion.statement_formal` has a definition anchor
in the same file, (B) that `quantifiers.ordered` is realized by the statement
and reports folded binders, (C) that F2a/F2b's shared predicate
`proper_future_extension_in_class` resolves to file-local definitions with the
file's own `frozen_regularity`. Liveness controls (positive / negative /
quantifier-fold synthetics) run inside the instrument; it fails closed on
input drift.

Reproduce:

```bash
python3 artifacts/worker-080/formal_symbol_audit/audit_formal_symbols.py \
  --out artifacts/worker-080/formal_symbol_audit/report.json
```

## Verdict: `FAIL` at F1 (1 hard formal-surface finding), `PASS` at F2a/F2b

**W080-FSYM-01 (hard, F1 `AF-WCC-VAC-GEN`).** `conclusion.statement_formal`
(line 251) uses the predicate `AF_{I+}(M_D)`. That symbol has **no definition
anchor and no occurrence anywhere else** in `schemas/af_wcc_vacuum.yaml`
(exact-token count outside the statement: 0). Its two sibling predicates in
the same statement are anchored (`complete` → `i_plus.completeness_definition`;
`visible_singularity_from_I_plus` → `visibility.predicate_name`). F2a/F2b use
`proper_future_extension_in_class`, anchored to `extension_predicate.name` with
a full definition, so the defect is F1-specific. This independently reproduces
worker-090's `HF090-03 undefined_normative_symbol` with a different instrument
and extends it with the per-symbol anchor table.

**W080-FSYM-02/03 (advisory, F1).** `quantifiers.ordered` declares 6 binders
(lines 56–62) while `statement_formal` realizes 4. The two folded binders are
`exists (Mtilde,gtilde,Omega)` (D3) and `forall gamma` (D4). An exact 6-binder
expansion does exist at `quantifiers.formal` (lines 48–55); the advisory is the
absence of a recorded abbreviation rule beside `conclusion.statement_formal`,
which is what a G-FORM reviewer must dispose of under "exact quantifiers".
F2a/F2b realize 4/4 with zero folded binders.

**Cross-schema (evidence, not a defect).** All three statements share the exact
prefix `forall (s,delta) in D0 exists G_{s,delta} comeager forall D in
G_{s,delta}`. F2a and F2b `statement_formal` are byte-identical and their shared
predicate resolves to file-local definitions that differ exactly in
`frozen_regularity` (`C2` vs `C0`) and `frozen_equation_concept`
(`classical_ricci` vs `none`) — no C0/C2 merge at the formal surface.

## Disposition options (reviewer/lead-owned)

1. Define `AF_{I+}` in the F1 schema (or inline the D3 existence + I+
   completeness predicates), **or** record an explicit abbreviation rule next
   to `conclusion.statement_formal` naming both folded binders; then re-freeze
   at a new sha256 and re-run this instrument.
2. Alternatively record why `AF_{I+}` is considered defined by the F0
   taxonomy; that reading must then be cited with the F0 hash.

## Non-claims and falsifier

No node completion, `validation_status=passed`, gate verdict or theorem is
claimed; `conclusion_type=formal_model`. This is a syntactic/structural
measurement of the formal surface only. Falsifier: a revision of
`schemas/af_wcc_vacuum.yaml` that defines/locates `AF_{I+}` or records the
folding rule (or a demonstration that the symbol has an anchor this classifier
does not see) voids the corresponding finding and requires re-running the
instrument at the new sha256; any change in a pinned sha256 voids the whole
report at that path.

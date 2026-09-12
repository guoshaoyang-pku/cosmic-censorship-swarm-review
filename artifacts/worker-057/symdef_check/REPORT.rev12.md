# GFORM-SYMDEF-057 addendum — re-measure at rev 12 (worker-057)

Gate **G-FORM** · nodes F1 / F2a / F2b · classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN

The canonical files were republished at 2026-09-12T00:31:41+08:00 while the rev-11 report was being emitted;
the drift was recorded in the rev-11 artifact event. This addendum re-runs the same deterministic probes at the new revision.

## Measured inputs (rev 12)

- `schemas/af_wcc_vacuum.yaml#cce9c60146d6` (rev 12, 36014 bytes, mtime 2026-09-12T00:32:02.095695+08:00)
- `schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc` (rev 12, 29976 bytes, mtime 2026-09-12T00:32:02.095695+08:00)
- `schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda` (rev 12, 34984 bytes, mtime 2026-09-12T00:32:02.099695+08:00)
- `research_map/formulation_taxonomy.yaml#0abb9ed8a961`

## Result: the rev-11 findings persist at rev 12

1. **[major] `F1:undefined_normative_symbol` — AF_{I+}** (sites: conclusion.statement_formal)

   - normative site uses 'AF_{I+}(M_D)'; no local definition site in the file; no occurrence in the canonical taxonomy either
   - evidence: `schemas/af_wcc_vacuum.yaml#cce9c60146d6`

2. **[info] `F1:binder_alias_undeclared` — D** (sites: conclusion.statement_formal)

   - statement realizes binder 'D' that is not a quantifiers.ordered binder name (notational alias)
   - evidence: `schemas/af_wcc_vacuum.yaml#cce9c60146d6`

3. **[major] `F1:undefined_normative_symbol` — P_WCC** (sites: quantifiers.negation_normal_form)

   - normative site uses 'P_WCC(D)'; no local definition site in the file; no occurrence in the canonical taxonomy either
   - evidence: `schemas/af_wcc_vacuum.yaml#cce9c60146d6`

4. **[major] `F2a:predicate_argument_role` — proper_future_extension_in_class** (sites: conclusion.statement_formal)

   - 'proper_future_extension_in_class' is defined on the extension tuple ["M'", "g'", 'iota'] of ['M', 'g'], but is applied to 'MGHD(D)' (the development of the data), so the extension existential is implicit at the use site
   - evidence: `schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc`

5. **[major] `F2a:acronym_prose_only_symbol` — MGHD** (sites: conclusion.statement_formal, quantifiers.negation_normal_form)

   - normative site uses 'MGHD(D)'; no local definition site in the file; canonical taxonomy occurrence at research_map/formulation_taxonomy.yaml:180 (prose/acronym only, no definition_ref)
   - evidence: `schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc`

6. **[info] `F2a:binder_alias_undeclared` — D** (sites: conclusion.statement_formal)

   - statement realizes binder 'D' that is not a quantifiers.ordered binder name (notational alias)
   - evidence: `schemas/af_scc_c2_vacuum.yaml#5476a3f2c6bc`

7. **[major] `F2b:predicate_argument_role` — proper_future_extension_in_class** (sites: conclusion.statement_formal)

   - 'proper_future_extension_in_class' is defined on the extension tuple ["M'", "g'", 'iota'] of ['M', 'g'], but is applied to 'MGHD(D)' (the development of the data), so the extension existential is implicit at the use site
   - evidence: `schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda`

8. **[major] `F2b:acronym_prose_only_symbol` — MGHD** (sites: conclusion.statement_formal, quantifiers.negation_normal_form)

   - normative site uses 'MGHD(D)'; no local definition site in the file; canonical taxonomy occurrence at research_map/formulation_taxonomy.yaml:180 (prose/acronym only, no definition_ref)
   - evidence: `schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda`

9. **[info] `F2b:binder_alias_undeclared` — D** (sites: conclusion.statement_formal)

   - statement realizes binder 'D' that is not a quantifiers.ordered binder name (notational alias)
   - evidence: `schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda`

Controls: C1 True · C2 True · mutants [True, True, True, True, True]

## Checker erratum (transparent)

The rev-12 F1 negation form is `{ r in D0 : { D in X^r_vac(AF) : not P_WCC(D) } ... }`. The first rev-12 run of the
original checker mis-read the superscript space notation `X^r_vac(AF)` as a predicate call `r_vac(AF)` and emitted a false
positive for `r_vac`. The checker lookbehind now excludes `^`; the false positive is gone and the rev-11 report is unaffected
(the triggering byte sequence exists only in rev 12). The correction is emitted as its own artifact event bound to the fixed
checker sha256; the superseded checker event `w57-symdef-20260912T003243-artifact-checker` (sha d53d0055…) remains in the log.

## Falsifier

Re-hash the three schemas and the taxonomy and re-run this script: the report is falsified for the recorded hashes if any measured sha256 differs; if a definition site for MGHD or P_WCC appears in the same file (or a definition_ref binds the symbol); if the extension predicate is redefined to take the development as its first-class argument; or if the realized/declared binder-name sets change.  A control C1/C2 flipping to False or any C3 mutant failing falsifies the scanner.

## Reproduce

```bash
python3 artifacts/worker-057/symdef_check/check_normative_symbols.py   # writes report.json at the measured revision
```

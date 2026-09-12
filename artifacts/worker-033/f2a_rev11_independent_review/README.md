# W033-F2A-REV11-INDEP-01 — independent class-binding review of F2a

Bounded worker task (worker-033), class-bound to `AF-SCC-C2-VAC-GEN`, node `F2a` / `A1`.
Review target: canonical `schemas/af_scc_c2_vacuum.yaml` at
`sha256:b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` (revision 11),
measured 2026-09-12T00:19:48+08:00. Verdict: **revise**, score 3.5.

## What was done

1. Pinned byte copies of the four artifacts the verdict depends on into `pinned/`
   (`SHA256SUMS`, `PIN.json`), then re-measured the live canonical paths to confirm the pin
   was still current.
2. Ran `check_f2a_class_binding.py`, an independent re-implementation of the class-binding,
   leakage, definitional, pointer, formal-sentence and timestamp checks. It imports no
   repository checker code and re-derives everything from the bytes.
3. Falsified the checker with 12 planted-defect controls in `mutation_controls.py`
   (10 defect-injection + 2 positive repairs). All controls pass; baseline verdict is `revise`.

## Results (23 checks: 16 pass, 7 fail)

Blocking:

- **VOC-01 / VOC-03 (critical, HF-02):** F2a declares
  `conclusion.conclusion_type: scc_c2_future_inextendibility`, which is not in the canonical
  F0 `field_vocabulary.conclusion_type.allowed` list
  (`weak_cosmic_censorship`, `strong_cosmic_censorship_C2`, `strong_cosmic_censorship_C0`), and
  is not the canonical class-descriptor token
  (`classes.AF-SCC-C2-VAC-GEN.axes.conclusion_type = strong_cosmic_censorship_C2`).
- **VOC-04 (major, cross-target):** the sibling `schemas/af_scc_c0_vacuum.yaml` has the same
  mismatch (`scc_c0_future_inextendibility` vs `strong_cosmic_censorship_C0`).

Non-blocking:

- **PTR-02 (major):** `class_contract_pointer` resolves only against the authoring tree; the
  canonical F0 taxonomy has no `class_contracts` section. Upstream of F2a (CF-7/CF-13,
  `astra-life01-publish-frozen`).
- **FORM-01 (minor):** `conclusion.statement_formal` is not the same sentence as
  `quantifiers.formal` (binder `D` vs `(Sigma,h,K)`, abbreviated predicate).
- **TIME-01 (minor):** `revised_at: 2026-09-12T00:30:00+08:00` is ahead of the measurement
  instant (CF-14 clock-discipline pattern).
- **TIME-02 (minor):** 8 duplicate top-level `revised_at` mapping keys; PyYAML last-wins,
  strict parsers reject the document, revision history is not machine-visible.

Disposition of the three critical hard failures raised by deepseek-flash-19 at rev3:
**all three are resolved at rev11** (HF-1: D0 is defined; HF-2: `extension_predicate` present
with clauses (a)–(f); HF-3: no matter-coupled token in assertive fields).

## Reproduce

```bash
cd <swarm-root>
python3 artifacts/worker-033/f2a_rev11_independent_review/check_f2a_class_binding.py \
    --measurement-time 2026-09-12T00:19:48+08:00 \
    --out artifacts/worker-033/f2a_rev11_independent_review/report.json
python3 artifacts/worker-033/f2a_rev11_independent_review/mutation_controls.py
```

`report.json` is the machine report; `review.json` is the PROTOCOL-formatted review verdict;
`mutation_controls.json` is the falsifier evidence; `run.log` records the exact commands and
exit codes.

## Scope limits

Structural and class-binding review only. No mathematical verification, no literature check,
no gate verdict, no `done` status. A later revision or hash move invalidates the verdict
rather than extending it. The reviewer did not author or previously review any formulation
schema.

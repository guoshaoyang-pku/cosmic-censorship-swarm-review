# W096-F2B-INDEP-REVIEW-01 — independent review of F2b (AF-SCC-C0-VAC-GEN)

- Reviewer: **worker-096** (independence: authored none of the reviewed artifact, its checker, or its class contracts)
- Target: `schemas/af_scc_c0_vacuum.yaml` — node **F2b**, class **AF-SCC-C0-VAC-GEN**, declared revision 11
- Target sha256 at review: `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` (bytes 33 060)
- Hash stability: re-measured after the checks, **stable** (no drift during the review window)
- Verdict: **accept**, score **4/5**, 0 critical failures, 0 major failures, 2 minor findings, 1 info note
- Evidence: `report.json` sha256 `a40c9b6f87780c6dbd80aa99cb6826d2fa49999885cdf837a0706fa0090fa94f`
- Script: `run_review.py` sha256 `57f0aa24182f1edc4f2f3ee3af1f9fac0cc7f71c9396440402c0f89c59fe9489`

## What was checked (G-FORM structural criteria, one frozen class)

15 machine checks, 13 pass; the canonical checker `artifacts/formulation/tools/check_class_schema.py`
(sha256 `000e09e46b2f…`) run on the same bytes exits 0 with `verdict: pass` — recorded only as
corroboration, not as this review's method.

Passing: single class binding with no unknown `AF-*` tokens; quantifier prefix
`forall-exists(comeager)-forall-not_exists`; vacuum / Λ=0 / 4d / one AF end / both constraints;
canonical genericity token `residual_comeager` per `VOCAB_ALIASES.json`; canonical SCC-C0 conclusion
token, no WCC predicate in the asserted statement; C0 ⇒ C2 implication with the converse forbidden;
tier-1 falsifier refutes exactly this class and tier-2 is labelled `refutes_strengthening_only`;
extension frozen at C0 with `frozen_equation_concept: none`; `f0_binding.declared_f0_sha256` equals
the measured canonical F0 hash `276009f4f63d…`; all six `l1_ledger_refs` theorem ids exist in
`ledger/theorems.jsonl` with matching statuses; canonical schema byte-identical to the
authoring-tree copy; class-separation scanner clean.

## Findings (minor; actionable, not gate failures)

1. **W096-F2B-F01 (minor) — duplicate top-level YAML keys.** `revised_at` occurs 9× in the header
   (lines 8–23). `yaml.safe_load` resolves last-wins, so the effective `revised_at` is the last
   entry; strict YAML parsers reject the document. *Falsifier:* a strict duplicate-key parser that
   exits 0 on the same bytes, or a revision with unique keys / a revision-history sequence.
2. **W096-F2B-F02 (minor) — declared `revised_at` ahead of wall clock and mtime.** Declared
   `2026-09-12T00:30:00+08:00` vs file mtime `2026-09-12T00:16:22+08:00` and review wall clock
   `2026-09-12T00:21+08:00`. The header's own `timestamp_provenance` records a prior
   ahead-of-clock correction, so this is a recurrence and interacts with the project-wide
   clock-discipline finding. *Falsifier:* a file whose declared `revised_at` ≤ mtime and ≤ wall clock.
3. **W096-F2B-F03 (info, F0 not F2b) — alias/canonical inversion in the declared F0 vocabulary.**
   `research_map/formulation_taxonomy.yaml` `field_vocabulary` lists `strong_cosmic_censorship_C0`
   and `provisional_baire_residual`, which `VOCAB_ALIASES.json` defines as *aliases*; F2b itself
   correctly uses the canonical tokens `scc_c0_future_inextendibility` and `residual_comeager`.
   *Falsifier:* an F0 revision whose `allowed` lists the canonical tokens first.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-096/f2b_independent_review/run_review.py --out artifacts/worker-096/f2b_independent_review/report.json
# exit 0 = no critical failure and no drift
```

## Boundaries

- This is a **reviewer input**, not a node transition. worker-096 cannot set `status=done`,
  `validation_status=passed`, or any gate verdict; only the controller / leads can, with artifact
  and review evidence.
- The verdict binds to `sha256_before` only. Any later revision makes it advisory and it must be
  re-run; that is drift, not falsification of the snapshot.
- No physics, theorem, counterexample, or numerical claim is made. The review decides structure per
  the declared G-FORM criteria; `human_adjudication_only` items (physical fidelity, well-posedness)
  are out of scope.

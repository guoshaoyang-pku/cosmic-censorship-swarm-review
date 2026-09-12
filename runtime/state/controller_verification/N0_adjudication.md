# Controller adjudication: N0 replication disagreement (2026-09-11T23:28+08:00)

Authority: Astra. Trigger: `python3 numerics/tests/flat_wave_replication.py --all`
run by the controller, output preserved at
`runtime/state/controller_verification/n0_replication_astra_run.json`
(sha256 `7adab492c8a582d1adf59fae268389cc83a8b8098575168330d86143ac165df5`).
Reference run of the candidate: `n0_flatwave_astra_run.json`
(sha256 `21284d98d71609301ca58d930889be80a5eae17799a53d7f2b4ae0b40c52c9a7`).

## Measurements (controller-executed, not reported)

| scheme | measured order | order verdict | energy check |
|---|---:|---|---|
| lffd (leapfrog) | 1.9958 | PASS | drift 3.4e-15 |
| cnfd (Crank–Nicolson FD) | 1.9935 | PASS | "own-energy" self-check false, drift 6.6e-8 |
| cnfem (CN FEM) | -0.0773 | FAIL | drift 1.0e+01, self-test false |

Top-level verdict from the replication artifact: `ORDER DISAGREES`.

## Adjudication

1. **The N0 order claim (order 2) is reproduced by two methodologically independent
   schemes** (lffd, cnfd) at 1.9958 and 1.9935 against a reference 1.9958. The order
   criterion is therefore provisionally met, subject to review.
2. **cnfem's failure is an implementation defect, not counter-evidence.** Order ≈ 0
   with drift 1.0e+01 and a failing self-test is the signature of a broken scheme, not
   a scheme that refutes convergence. It must be fixed or excluded with a documented
   cause; "excluded because it disagrees" is not acceptable.
3. **The replication harness's invariant functional is scheme-specific** (the replication
   itself reports `gate_limitation_finding`: it recomputes the leapfrog staggered energy).
   A scheme-agnostic energy functional is required, or the affected checks must be
   relabelled so they do not count as replication evidence.
4. **G-NUM is NOT passed.** Verdict set to `pending` with the unmet criteria recorded,
   because criterion "protocol reviewed by audit" is untouched and the replication
   artifact is not clean. N1/self-gravity remains locked.
5. The cnfd `own-energy` self-check at drift 6.6e-8 needs a principled threshold
   justification, not a threshold moved to make it pass.

## Required follow-up (assigned)

- worker 13 (replication owner): triage cnfem to a root cause; fix or formally exclude
  with evidence; make the invariant check scheme-appropriate; re-run and publish.
- worker 14 (protocol owner): review the energy-drift threshold and the scheme-dependence
  finding; state what the protocol should require from an independent scheme.
- lead-numerics: adjudicate the two reports, then propose G-NUM status to Astra with
  artifact hashes. N1 stays queued.

## Falsifiers

- cnfem triage is closed by deleting the scheme: falsified if no root cause is shown.
- The scheme-dependence finding is falsified if a non-leapfrog scheme passes the
  leapfrog-functional gate on the same configuration.

---

## Controller addendum (2026-09-12T00:12+08:00) — adjudication partially corrected

Worker 14's protocol review (`numerics/protocol/scheme_independence_review.md`,
sha256 `2fdb85b23f7d120b`) shows two errors in the adjudication above:

1. cnfd's "own energy" was **algebraically the leapfrog staggered energy**
   (identity gap 2.07e-15), so the reported `own drift = 6.59e-8` was the same test as
   the harness functional, **not** evidence that cnfd fails to conserve its own energy.
   The "cnfd energy self-check marginal" line above is withdrawn.
2. cnfd's harness-functional drift 6.59e-8 is **below** the harness `drift_tol = 1e-6`,
   and the pinned run records `harness_gate_would_pass = True` for cnfd. Therefore the
   adjudication's own falsifier — "a non-leapfrog scheme passes the leapfrog-functional
   gate on the same configuration" — **is triggered**, which narrows the residual claim:
   the candidate's `G3` threshold of 1e-8 is resolution-dependent (cnfd flips to PASS at
   dr = 0.025 with no change to the scheme). The fix is a functional-aware,
   resolution-aware criterion, not a new magic number.

Unchanged by the correction: cnfem's failure was an implementation defect (sign error in
the Crank–Nicolson FEM recurrence, now fixed: order −0.0773 → 1.9863), the order claim is
reproduced by three schemes, and G-NUM still requires the independent A1 numerical-protocol
review (`reviews/G-NUM-protocol-review.json`) before any pass.

# Independent terminal verification — FORM-HELDOUT-10

- task: W084-HELDOUT10-INDEP-01; verifier: worker-084; 2026-09-12T01:11:35+08:00 (Asia/Shanghai)
- reviewed: manifest d026fec40fe4, report 5629e2a69c86, raw b3480625da10
- method: both canonical stages re-invoked directly on all 40 preserved fixtures;
  no import of the builder or of run_heldout_10.py; verdicts compared fixture-by-fixture.

## Result

Reproducibility of the executor's report: **accept** — 27/27 checks pass;
failed: none. Strict card acceptance (H5 controls): **false** — C01 fails because the
frozen WCC canonical is rejected by stage B R03, which the executor pre-registered as an instrument
defect before freezing the corpus.

| aggregate | report | independent re-run |
|---|---|---|
| all-mutant structural escape | 1.0 | 1.0 |
| all-mutant semantic escape | 0.7879 | 0.7879 |
| all-mutant union escape | 0.7879 | 0.7879 |
| informative C2+C0 union escape | 1.0 | 1.0 |
| uninformative W union escape | 0.0 | 0.0 |

Terminal status: **valid=false, strict H5** — the frozen F1/WCC canonical is rejected by
stage B on R03 (literal-substring binder), independently reproduced. The WCC arm is
non-informative; the informative C2/C0 arms show union escape **1.0 (0/26 caught)**
on fresh rev13 fixtures, confirming the executor's report.

## Limits

Worker adjudication only; no node status, no gate verdict, no theorem. Independence is
process-level (fresh re-run from preserved bytes), not third-party: the verifier shares the
worker-084 id with the corpus executor.

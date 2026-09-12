# ABANDONED before binding — moving target (worker-069)

Task `W069-F2B-CONTAINMENT-ADJ-01` (independent adjudication of the F2b containment-wording
blockers at `schemas/af_scc_c0_vacuum.yaml#1bb78ce9b357`) was abandoned before any snapshot,
verdict or event was emitted.

Reason: while the pre-flight pin was being set, the `astra-life03-close-findings` closure revision
landed and moved the canonical F2b hash:

    schemas/af_scc_c0_vacuum.yaml  1bb78ce9b3572cda…  ->  55d0a1ea9bda96b8…   (observed 00:31–00:32)

Per the moving-target stop rule, no verdict binds a superseded revision. The runner exits 2 on a
pin mismatch rather than emitting a stale adjudication (see `run_adjudication.py`).

`check_f2b_containment.py` and `run_adjudication.py` here are unbound tooling for the old bytes;
they are retained for reuse against the rev12 F2b bytes but carry **no verdict, no report and no
hash-pinned conclusion**. The worker-069 effort moved to the new closure revision:
`artifacts/worker-069/f2a_rev12_closure_verdict/` (task `W069-F2A-REV12-CLOSURE-VERDICT-01`).

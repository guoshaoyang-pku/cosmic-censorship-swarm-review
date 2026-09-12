# Astra checkpoint report 3 — 2026-09-12T00:15+08:00

Run `run-2026-09-11T23:15+08:00`, 1 h elapsed. Loop on `auto-4` (00:05), next 00:20.
0 audit hard failures; class-separation regression PASS (17/17, 10/10); 93 outbox
files; ~900 applied events; all five gates pending with named conditions.

## 1. Controller interventions this window

1. **Convergence protocol (binding, P1–P5)** after measuring churn: 94 artifact events
   across 39 paths for F1 alone, every revision drawing a fresh `revise`. P1 publish-one-
   revision-and-freeze; P2 blocking/non-blocking triage (revise only with ≥1 blocking
   finding); P3 at most one further revision, unresolved is a valid outcome; P4 hash
   binding (a changed artifact voids the review); P5 no path migration.
2. **Class-scope escalation to Human PI.** The formulation group found that the taxonomy
   and the F1 schema define the WCC visibility predicate differently under one class name
   (set-based `p ∈ J⁻(I⁺)` vs causal-curve accumulation). The lead proposed two new class
   ids (`AF-WCC-VAC-GEN-SET`, `AF-SCC-C0-CH-VAC-GEN`). Finding accepted; new class ids
   **rejected pending PI ruling**; variants must be recorded as
   `{parent_class, variant_id}` so coverage accounting and the class-separation corpus
   stay valid.
3. **My own N0 adjudication was partially falsified by worker 14** and corrected in an
   addendum: cnfd's "own energy" was algebraically the leapfrog energy (not an independent
   conservation test), and its drift 6.59e-8 is below the harness tolerance, so the
   adjudication's own falsifier is triggered. Residual true claim: the candidate's G3
   threshold 1e-8 is resolution-dependent. The cnfem defect finding and the three-scheme
   order reproduction stand.
4. **Promotion engine** tightened: hash-validated artifact refs, no sticky promotion.
   2 promoted (low-bar, artifact+review), 31 blocked, 1 controller-adjudicated.

## 2. Gate board

| gate | verdict | condition to close |
|---|---|---|
| G-F0 | pending | publish taxonomy to canonical path (3 of 4 mirrors already byte-identical); one frozen revision + B/N triage |
| G-FORM | pending | F1/F2a/F2b published (mirror-SAME) but open `revise` verdicts with blocking findings |
| G-LIT | pending | citation-integrity reviews returning `revise`; 32 unassessed rows being closed; 4 spot-check accepts already recorded |
| G-NUM | pending — **one item** | A1 numerical-protocol review (`reviews/G-NUM-protocol-review.json`), assigned to lead-audit; all other criteria met and controller-verified |
| G-AUDIT | pending | checker-calibration table; L0 revision; F2b re-review |

## 3. Verified facts

- Canonical publication: `schemas/af_wcc_vacuum.yaml` b65fcc0f, `af_scc_c2_vacuum.yaml`
  8dae50da, `af_scc_c0_vacuum.yaml` a8d899d2 are byte-identical to the authoring tree.
  The taxonomy still diverges (565a6e50 vs 01e7f841).
- cnfem root cause found: sign error in the Crank–Nicolson FEM recurrence; fixed order
  1.9863; independent re-run verdict ORDER REPRODUCED.
- Lock: `numerics_lock` locked; lock guard PASS; no self-gravitating code exists.
- Content timestamps from agents run ahead of wall clock; ingest now records controller
  `_received_at` and ordering uses it (CF-6).

## 4. Escalations open at Human PI

1. **A2 provider channel** — real four-arm ablation cannot run without credentials/spend cap.
2. **WCC class split** — reconcile to one predicate (Astra default) vs split into two
   classes vs named variants.
3. **Worker web_search tool broken** (direct HTTPS works; workaround broadcast).

## 5. Next window

Formulation publishes the taxonomy and answers B/N triage; audit closes G-NUM's protocol
review; literature closes the 32 unassessed rows; Astra adjudicates the first passing gate
and keeps the loop.

# Astra-Only Cosmic Censorship Swarm: Evidence-Bound Progress

## Progress paper · 13 September 2026

### Abstract

We report a controlled Astra-only continuation of the cosmic-censorship research swarm. A local mathematical controller coordinates one remote controller, four group leads, and independently killable execution processes. Each task produces a hash-bound artifact, an explicit falsifier, and a checkpoint. The current run has generated class-separation regression evidence, repeated formulation pin-drift detections, literature-scope checks, and flat-space numerical calibration. These are reviewable research-map results, not a proof of any formulation of cosmic censorship. The self-gravitating stage remains locked.

## 1. Architecture

The topology is mathematical controller -> Astra controller -> four leads (formulation, literature, numerics, audit) -> bounded workers -> hash-bound evidence -> gate adjudication. The project-level model is gpt-6-astra at ultra reasoning; the Phybench relay maps ultra to the upstream max tier. DeepSeek is historical evidence only and excluded from the active launcher.

## 2. Evidence contract

For task i, the swarm records E_i = (task_id, artifact_path, SHA256, falsifier, checkpoint). A gate may consume E_i only when the path exists, the measured hash is stable, and the falsifier is explicit.

Unlock(N1) iff G-FORM = pass and G-AUDIT = pass and G-NUM = pass. At the current checkpoint this predicate is false by design: G-FORM, G-AUDIT, and G-NUM remain pending, while N1 remains locked.

## 3. Findings

### 3.1 Class-separation regression

The declared adversarial fixture contains 27 cases: 17 true positives, 0 false positives, 10 true negatives, and 0 false negatives. Thus accuracy = (17 + 10) / 27 = 1, with empirical FPR = 0 and FNR = 0 on this fixture. These are regression measurements, not population estimates for arbitrary mathematical prose.

### 3.2 Formulation pin drift

Independent workers repeatedly measured current C0/C2 schema hashes that differ from the rev29 frozen manifest: h_disk(s) != h_frozen(s) for s in {AF-SCC-C0, AF-SCC-C2}. A review at the old hash cannot count as a review of the current schema. Workers 005, 007, 008, 010, 016, and 017 recorded this blocker family; several also verified byte-identical primary/mirror pairs.

### 3.3 Literature ledger

The literature lane records source identity, quoted claim, assumptions, class binding, and an explicit does-not-prove field. Re-fetch spot checks are substantial, but G-LIT remains pending until accepted reviews bind to one measured hash and meet the distinct-review rule.

### 3.4 Numerical calibration

The N0 flat-space scalar protocol has four-rung convergence and replication checks. The controller keeps numerics/spherical_solver absent. No self-gravitating solver is written or run while the lock is active, so the result is calibration and protocol evidence rather than generic vacuum evidence.

## 4. Current state

| Control | Status | Interpretation |
|---|---|---|
| G-F0 | pass | taxonomy contract internally consistent |
| G-FORM | pending | current-hash formulation acceptance incomplete |
| G-LIT | pending | final literature binding incomplete |
| G-NUM | pending | N0 adjudication remains open |
| G-AUDIT | pending | class-separation coverage remains open |
| N1 | locked | no self-gravitating run permitted |

## 5. The result worth showing

The defensible new result is a reproducibility result: a parallel language-model swarm becomes reviewable when every task is class-scoped, every output carries a measured hash and falsifier, and gate promotion is separated from worker self-report. The negative result is equally useful: without current-hash rebinding, many positive-looking reviews cannot support a gate.

## 6. Claim boundary

This paper does not prove weak or strong cosmic censorship, generic Kerr inextendibility, or a model-generated theorem. It reports a controlled evidence pipeline and the blockers it found. The next milestone is fresh hash-frozen formulation review plus independent G-FORM and G-AUDIT adjudication; only then may the project reconsider N1.

## Reproducibility

- Local controller: ai4math_runtime/math_controller_loop.sh
- Migration contract: ai4math_runtime/ASTRA_ONLY_MIGRATION.md
- Research plan: docs/cosmic_censorship/SWARM_RESEARCH_PLAN.md
- Public review repository: https://github.com/guoshaoyang-pku/cosmic-censorship-swarm-review

Prepared from hash-bound runtime records on 2026-09-13. Gate statuses are time-dependent and must be re-read before citation.

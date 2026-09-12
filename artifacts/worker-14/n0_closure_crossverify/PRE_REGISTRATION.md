# PRE-REGISTRATION — W014-GNUM-N0-CLOSURE-CROSSVERIFY-01

Declared before the instrument was implemented or run (2026-09-12T01:20+08:00).

- **Worker:** worker-014 (recycled slot; no inbox card existed for this instance)
- **Class:** AF-WCC-SCALAR-SPH · **Node:** N0 · **Gate:** G-NUM
- **Type:** independent non-author, read-only cross-verification (second worker-level verdict)
- **Targets (pins taken at declaration time, re-measured immediately before the run):**
  - T1 `numerics/protocol/lifecycle08_stoprule_closure_verify.json#88ec0bf298cb`
    (astra-lead-numerics closure artifact, generated_at 2026-09-12T01:13:11+08:00)
  - T2 `reviews/N0-stoprule-closure-review-worker-017.json#87b311e72032`
    (first independent review of T1, worker-017, reviewed_at 2026-09-12T01:15:50+08:00)

The question: does the N0 stop-rule closure evidence package survive a **second, independently
implemented** read-only check at the same pinned hashes — numerical core recomputed from raw rows,
each stop-rule item, the lock guard, and the registration claims — and is the first independent
review's own artifact intact and consistent with that recomputation?

Independence statement: the instrument for this check was written without reading
`artifacts/worker-017/n0_stoprule_closure_verify/verify_n0_closure_017.py`; that file is only hashed
as an evidence pin. No file under `numerics/`, `research_map/`, `reviews/` or another worker's
artifact directory is written. `numerics_lock` stays LOCKED; no solver is written or run.

## Predictions (each must hold; any miss is reported, not relabelled)

- **P1 — pin gate.** T1 measures `88ec0bf298cbc4de6ae2a6d3038961d404f1c43a64cbaa92f29b6ad6cce77f75`,
  schema `n0-stoprule-closure-verify/v1`, `class_id=AF-WCC-SCALAR-SPH`, `node_id=N0`, `gate=G-NUM`,
  `all_closure_items_closed=true`.
- **P2 — numerical core.** My own log-log least-squares fit over the raw `rows` of
  `numerics/protocol/n0_fixed_dt_certification.json#1677822ceb9c` reproduces, for each of cnfd /
  cnfem / lffd: `fit_order`, `least_squares_se`, all four `lsq_residuals` and all three
  `pair_orders` to absolute difference ≤ 1e-12; and reproduces `p_by_scheme` in
  `numerics/results/flat_wave_convergence_rev3.json#da7c36071995` to the same tolerance. T1's
  `max_abs_diff_vs_declared: 0.0` is therefore a truthful statement about the certification bytes.
- **P3 — bands.** All three ladders strictly monotone in `dr` (error falls as `dr` halves);
  `|p - 2| ≤ 0.3` for each scheme; cross-scheme max pairwise spread `≤ 0.25` and equals
  `7.958116929374093e-05` to ≤ 1e-15.
- **P4 — F0 rebind (stop-rule item 2).** Live `research_map/formulation_taxonomy.yaml` measures
  `0abb9ed8a961`, revision 5, contains `AF-WCC-SCALAR-SPH`;
  `numerics/N0_CLASS_BINDING_AUTHORITY.json#effd20b0ea09` resolves, and its `binding.sha256` /
  `binding.declared_revision` / `carrier.sha256` agree with the live taxonomy and with rev3.
- **P5 — replication (stop-rule item 3).** `numerics/tests/flat_wave_replication.py` measures
  `8ade1cdc163e` both in the certification and on disk; the three cited verdict artifacts resolve
  at their declared hashes and carry `SUPPORTED` / `REPRODUCED` / `accept`;
  `reviews/flash-13-N0-rev3-verdict.json#6d2859542951` binds rev3 `da7c36071995`, verdict `accept`,
  score 4.0, and discloses the F-06 author conflict.
- **P6 — lock.** `research_map/research_map.json#numerics_lock.state == "locked"`; no
  `numerics/spherical_solver/` path exists; `numerics.gates.evaluate()` reports the lock held
  (`production_allowed=false`, N1 blocked).
- **P7 — registration.** Of the pins in T1's `known_pins` table, the six numerics paths are
  `registry-match`, `research_map/formulation_taxonomy.yaml` is `top-level-match` (T1 labels it
  `unregistered` — a documentary refinement, not a gate defect, since the top-level `hashes` table
  carries the same sha), and the three reviewer-verdict artifacts are unregistered. The carried
  stale pin `reviews/G-NUM-protocol-review.json#1e6cdf04d7a2` measures `8137f18f1a3b` on disk.
- **P8 — first review intact.** T2 measures `87b311e72032`, matching the hash declared in
  worker-017's outbox; its four evidence artifacts resolve at their declared prefixes
  (`report.json#d3d7c450ebc5`, `registration_crosscheck.json#749090f9a2ba`,
  `verify_n0_closure_017.py#ba56eade7561`, pinned copy `#88ec0bf298cb`); the pinned copy is
  byte-identical to live T1; each of its seven findings is consistent with my independent
  measurements; `counts_as_gate_verdict=false` and `counts_as_node_verdict=false`.
- **P9 — controls.** ≥ 12 in-memory negative controls, all fire as expected.
- **P10 — drift.** Pre-run and post-run sha256 of every pinned input are identical.

## Falsifier (declared now)

Re-run `verify_n0_closure_x.py` at the pins above. This cross-verification is falsified, and the
verdict flips to `REVISE`, if **any** of: (a) a recomputed fit leaves `|p-2| > 0.3`; (b) a ladder is
non-monotone; (c) cross-scheme spread exceeds 0.25; (d) my recomputation disagrees with the
certification or rev3 beyond 1e-12; (e) a cited verdict artifact's bytes no longer match its
declared hash, or a declared verdict token is absent/changed; (f) live taxonomy ≠ `0abb9ed8a961`
or lacks the class; (g) `numerics_lock` is not `locked`, or `numerics/spherical_solver/` appears;
(h) T1's bytes move off `88ec0bf298cb` or T2's off `87b311e72032`; (i) any control does not fire;
or (j) any pinned input drifts between the instrument's pre- and post-measurement.

If the instrument itself cannot reproduce its recorded report byte-for-byte on a re-run, the
verdict is `REVISE` for instrument nondeterminism.

## Scope / does-not-claim

No gate verdict (Astra / lead-audit authority), no N0 node completion or status transition, no
`numerics_lock` release, no adjudication of the B-N0-R2-2 protocol-review contest, no adoption of
anything, no canonical-path write, no physics / self-gravity / WCC / SCC claim. This is a
worker-level second verdict for the lead-audit's `astra-life04-n0-verify` evidence set only.

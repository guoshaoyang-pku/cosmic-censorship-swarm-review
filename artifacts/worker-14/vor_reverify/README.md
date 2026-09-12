# W014-GNUM-VOR-REVERIFY-01 — independent verification of the re-issued N0 verification of record

**Worker-level result. No gate verdict, no node completion, no canonical-path write.**

| field | value |
|---|---|
| task | `W014-GNUM-VOR-REVERIFY-01` |
| node / gate / class | `N0` / `G-NUM` / `AF-WCC-SCALAR-SPH` |
| verified record revision | `numerics/protocol/n0_gate_proposal_leadverify.json` @ `ea4cf6c9bd3c2092f38757cf6ed748ef7ae0781d6e5317edae1c0e6c4db6b60e` (declared `created_at` 2026-09-12T00:54:07+08:00) |
| verified proposal revision | `numerics/tests/n0_gate_proposal.json` @ `b4192221ff7d96dbb61ce37fa667e1a59b7b290b8ca34f77e7674c03ca5ba2e3` |
| **verdict** | **`VOR_VERIFIED_BA1_CLOSED_BA5B_ANNOTATION_DEFECT_OPEN`** |
| controls | 13/13 behaved as declared; input drift `[]`; instrument valid |
| predecessor | `artifacts/worker-14/binding_audit/n0_binding_audit_refresh.json#13600a5d4130` (findings BA-1, BA-5 open) |

## Why this task

The previous worker-14 audit raised **BA-1**: the filed verification of record verified proposal
revision `58a175b52fbe` while the bytes on disk were `b4192221ff7d`. The numerics lead re-issued
the record in place. This task independently checks whether the **re-issued bytes** actually bind
the current proposal and whether the earlier advisory **BA-5** (unreproducible declared mutable
registry snapshot) survives.

## Method (read-only, deterministic; `verify_vor.py`)

- **A** binding: `proposal_verified.sha256` vs re-measured proposal bytes; the named artifact
  event `lnum-artifact-1789144642810-0d42bd` re-found in `research_map/events.jsonl` and compared;
  announced revisions of the record path enumerated from the accepted stream.
- **B** supersession fidelity: the superseded record's declared sha256/bytes cross-checked against
  the two prior worker-14 audit artifacts that pinned them; every declared stale pin re-measured.
- **C** evidence chain: all 23 `(path, sha256)` rows re-hashed and cross-checked against the
  proposal's own `evidence_hashes`, plus per-section registry coverage.
- **D** mutable-registry snapshot claims, tested under **both** bases (full-file sha256 and
  registry-section digest), with a future-dating detector.
- **E** reproduction: `python3 -m numerics.gates --check` re-run (no `--write-report`, no
  `--emit-blocker`), comparised semantically (the record's block is a summary: its `lock_state`
  maps to `lock.state`).
- **F** order claim: least-squares refit of the four fixed-dt rungs per scheme from the published
  rows, with pair orders, half-range, slope SE, monotonicity, and band/agreement rules.
- **G** lock guard: map lock state, `numerics/spherical_solver` absence, no N1 solver files.
- **Controls** (13): classifier sensitivity (match/stale/missing/dir), registry-section status,
  tamper detection, future-dating detector, synthetic order-2 refit, tolerance bite, exit-code
  semantics, plus a before/after input drift guard.

## Results

| prediction (pre-registered) | observed | status |
|---|---|---|
| P1 record binds current proposal; artifact event present/matching ⇒ BA-1 closed | binds `b4192221ff7d`; event found at 00:37:22 with the same path+sha256 | **confirmed** |
| P2 23/23 chain match, 0 stale/missing; proposal `evidence_hashes` agree | 23/23 match, 0 stale, 0 missing, 0 disagreements | **confirmed** |
| P3 record's own registry snapshot reproduces at measurement instant | prefix `5c29fba23f3a8d593c6d` does **not** match the registry at verification (`692c8dbc…`, mtime 00:55:27) — the controller rewrites that file continuously; the record labels the field a point-in-time non-pin | **deviation, expected churn** |
| P4 proposal's declared mutable snapshot stays unreproducible and future-dated | `d69b62dc93e5336e5109`, `measured_at 2026-09-12T01:06` — matches neither basis, instant in the future | **confirmed (BA-5b persists, non-load-bearing)** |
| P5 gate-evaluator reproduction | exit 3, `N1_BLOCKED`, lock `locked`, `production_allowed=false`; all 4 recorded dissenters present (fresh run lists the same 4) | **confirmed** |
| P6 refit reproduces declared orders/SE | per-scheme `abs_diff_vs_declared = 0.0`, `abs_se_diff = 0.0`, `abs_diff_vs_lead_refit = 0.0`; max pairwise \|Δp\| `7.958e-05` ≤ 0.25; all in band | **confirmed** |
| P7 lock guard | map `locked`, solver dir absent, no N1 files, `production_allowed=false` | **confirmed** |
| P8 controls behave | 13/13 | **confirmed** |

### Findings

- **BA-1 — closed at `ea4cf6c9`.** The re-issued record binds the current proposal bytes, names
  the artifact event that froze them, and its 23-entry chain re-measures clean; all 23 paths are
  `registered_match` in the union of the registry's declared `hashes` and scanned `registry`
  sections.
- **BA-5a — `point_in_time_non_pin_registry_rewritten`.** The record's own snapshot mismatch is
  registry churn, not a defect (the record calls the field a non-pin). The acceptance-instant
  registry bytes are not recoverable post hoc, which is exactly why the field must not be used
  as a pin.
- **BA-5b — open, non-load-bearing.** The *proposal's* declared snapshot `d69b62dc…` at a
  future instant matches no observed registry state under either measurement basis. The proposal
  itself classifies it `snapshot-pin-of-mutable-registry` / "not as a pin", so it does not bind
  the order claim; it remains an annotation defect for the controller/lead to re-issue or annotate.
- **Revision binding (recorded).** This verdict binds exactly revision `ea4cf6c9…`. The record
  path is rewritten in place by successive lead lifecycles (announced revisions in the stream:
  `e0f9ef9f…` at 00:20:46 and `ea4cf6c9…` at 00:55:21). A later rewrite voids this verdict for
  the new bytes.
- **Evaluator block is a summary (recorded).** Under the `lock_state → lock.state` mapping the
  reproduction is faithful; comparisons made by raw top-level key would falsely report a
  mismatch.
- Not in scope / not touched: the standing protocol-review contest (C8) and the pending
  `astra-life05-gnum-protocol-adjudication`; the gate proposal's own `recommended_verdict` stays
  `pending`.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm/artifacts/worker-14/vor_reverify
python3 verify_vor.py --out report.json    # exit 0; prints verdict + control status
```

Deterministic at pinned inputs; only `--out` and a scratch dir (removed on exit) are written.

## Falsifier

Re-run `verify_vor.py` at the pinned input hashes and the verdict is falsified if (a) any chain
row called `match` has a different measured sha256; (b) the record is shown not to bind the
current proposal bytes, or the named artifact event is absent/mismatched; (c) any control behaves
differently from its declared expectation; (d) the refit disagreement exceeds `1e-6`; or (e) any
load-bearing fact recorded `ok` is shown false. A moved proposal, record, registry or
certification hash voids the corresponding verdict for the new bytes.

## Not claimed

No gate verdict and no gate self-pass; no N0 completion; not the C8 independent protocol review;
no physics claim; no claim that the controller registry is stable evidence; no claim about the
protocol-review contest or about artifacts outside the pinned set.

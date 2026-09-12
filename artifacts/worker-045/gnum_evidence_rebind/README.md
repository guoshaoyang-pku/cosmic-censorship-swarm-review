# W045-GNUM-EVIDENCE-REBIND-01 — G-NUM gate evidence re-bind audit

Worker: `worker-045` (no inbox card existed for this slot; one self-selected bounded,
class-bound, read-only task). Node `N0`, gate `G-NUM`, class `AF-WCC-SCALAR-SPH`.
This is a continuation of `W045-C8-BINDING-VERIFY` (00:27) after the controller's
pass-08 landed.

## Question

At the live map bytes, does every hash-bearing `evidence_ref` of `gates[G-NUM]`
actually bind a revision that exists on disk, is the current verification-of-record
bound, and does the gate record agree with the controller registry
(`runtime/state/artifact_hashes.json`)?

## Method (deterministic, read-only)

1. **Settled-window snapshot.** The live map is read twice ~1.2 s apart; the first
   byte-identical pair is pinned to `map_snapshot.json`. Four attempts. A run whose
   window never settles is marked `drift_void`.
2. **Per-ref classification.** For every `path#frag` in `gates[G-NUM].evidence_refs`:
   - `MATCH` — fragment is a prefix of `sha256(path bytes)` under the live tree;
   - `HISTORICAL_DECLARED` — fragment is not the file's own hash but appears verbatim
     in the file's own bytes (a revision/review pin the artefact declares);
   - `HISTORICAL_RELOCATED` / `HISTORICAL_VCS` — the exact bytes exist at another
     artifact path / in git history;
   - `STALE_UNEXPLAINED` — none of the above (the only defect class);
   - `MISSING`, `BARE` (no fragment), `AMBIGUOUS` (non-hex fragment such as
     `#controller_gate_audit`, a key path and not a pin).
3. **Registry cross-check + divergence.** Paths the gate *tries* to pin (≥1
   hash-bearing ref) whose registry-current revision no gate ref binds.
4. **C8 re-test.** Reproduces the controller's current binding expression
   (`prd.get("reviewed_sha256") or prd.get("artifact_sha256")`) and the legacy
   expression against the measured `numerics/CONVERGENCE_PROTOCOL.md` hash.
5. **Successor chain.** Measures `numerics/protocol/n0_gate_proposal_leadverify.json`,
   reads its self-declared `supersedes` block, and checks which prefix the gate binds.
6. **Controls C1–C11b** (`controls.json`): stale detection, missing path, bare ref,
   key-path fragment, `sha256:` form, 6-hex prefix, external `sha256sum` agreement on
   3 live files, binding-detector fail-closed + positive, drift-guard fire,
   declared-historical detection, and the divergence rule both ways. `all_pass: true`.
7. **Determinism.** The measurement is taken twice from the same snapshot bytes;
   `report.json` hashes both normalized runs.

Reproduce:

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-045/gnum_evidence_rebind/run_gnum_evidence_rebind.py
```

## Measured result at snapshot `a2585ffc2152` (map `updated_at` 01:16:25, `astra-life08-gate-gnum`)

| bucket | n |
|---|---|
| MATCH (self-binding) | 18 |
| HISTORICAL_DECLARED | 5 |
| HISTORICAL_RELOCATED / HISTORICAL_VCS | 0 / 0 |
| **STALE_UNEXPLAINED** | **1** |
| MISSING | 0 |
| BARE | 19 |
| AMBIGUOUS | 2 |
| registry divergence (gate tries to pin, binds non-current) | 1 |

* C8: review verdict `accept` 4.5, `reviewed_sha256 = 1e6cdf04d7a2…` = measured
  protocol hash → current expression **BOUND**; legacy expression (top-level
  `artifact_sha256`) is absent → **UNBOUND** (informational).
* `numerics_lock` locked, solver path absent, guard present
  (`7535ec84ac9c…`); N1 remains locked, N0-only scope respected.

## Findings

* **W045-GER-01 (major).** `numerics/tests/n0_gate_proposal.json#22d984781cee` is an
  unexplained stale pin: the live file is `b4192221ff7d`, the fragment appears nowhere
  in its bytes, no name-matching artefact on disk carries those bytes, and it is not
  recoverable from git history for that path. Five further pins
  (`CONVERGENCE_PROTOCOL.md#3345e17d2be3`, `n0_gate_proposal_leadverify.json#e0f9ef9f329d`,
  `n0_gate_proposal.json#58a175b52fbe`, `G-NUM-protocol-review.json#1e6cdf04d7a2` and
  `#66a905f5afef`) are declared-historical and legitimate provenance — but the gate
  list is therefore a revision log, not a live pin set.
* **W045-GER-03 / W045-GER-08 (major, one root cause).** The gate binds the superseded
  leadverify `e0f9ef9f329d` and no ref carries the live successor `ea4cf6c9bd3c2092`,
  which the registry already records and whose own `supersedes` block documents exactly
  this stale-pin set. A reviewer resolving the N0 verification-of-record from the gate
  lands on the superseded record.
* **W045-GER-04b (info).** C8 resolves only through `reviewed_sha256`; the review has no
  top-level `artifact_sha256`, so consumers of the older convention still read `unbound`.

Pass-08 cleared two defects observed at the previous snapshot (`66ada65f6027`): the
`unmet[]` list no longer contradicts the controller's C8=MET statement, and
`reviews/G-NUM-protocol-review.json#8137f18f1a3b2b01` now binds the review's own bytes.

## Falsifier

Void if a re-run at snapshot `a2585ffc2152` yields any different classification; void if
`sha256(map_snapshot.json) != a2585ffc2152…`; void if an independent reviewer finds a
ref called MATCH whose bytes do not start with the declared fragment; void if the
control battery does not reproduce `all_pass=true`. Withdrawn as a live finding if a
later map snapshot re-pins the successor, disposes of `22d984781cee`, and the review
gains `artifact_sha256`.

## Limits / authority

Read-only over the named gate record; writes only inside this directory plus the worker
checkpoint. It does not adjudicate C8, the N0 node verdict, cnfd/cnfem triage, or the
4-rung order claim, and it edits no canonical artifact. Worker events cannot set
`status=done`, `validation_status=passed`, or a gate verdict — N0/G-NUM remain
lead- and controller-owned.

## Deliverables

| path | sha256 |
|---|---|
| `report.json` | `502a891c8e1d3c19062bfddffee19ee3fe2897244e5dc8617a0f1d7edc7af5df` |
| `controls.json` | `5c15e03339af60fac4b88bf8fbe707031780348a3151475bbde876eacee668b1` |
| `checkpoint.json` | `06ae95730ffb40e943c5de1f53f4b1ba7d510d2e936e285920777060e20f4216` |
| `map_snapshot.json` | `a2585ffc2152da9ada4a32ea10bc61bc56b2472cc117f31ae234b3d8b4f10168` |
| `run_gnum_evidence_rebind.py` | `d18498b44fdb5a55123530d8f6f900d6dc1a236a90c8fb3548e9b5b1557086c6` |

Worker checkpoint mirrored at
`runtime/state/w045_gnum_evidence_rebind_checkpoint.json`.

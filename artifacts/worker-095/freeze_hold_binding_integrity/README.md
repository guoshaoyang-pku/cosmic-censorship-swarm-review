# W095-HOLD-BIND-INTEGRITY-03

Worker-level binding/publication receipt for the `astra-life04-freeze-hold` at FROZEN
revision 28. Class anchor `AF-SCC-C0-VAC-GEN` (node F2b, gate G-FORM). **Not** a semantic
content review and **not** a gate verdict: `counts_as_full_schema_verdict=false`.

## Question

`astra-life04-freeze-hold` claims: five canonical pins confirmed against FROZEN rev28
(F1 `cce9c60146d6` / F2a `5476a3f2c6bc` / F2b `55d0a1ea9bda` / declared F0 `0abb9ed8a961` /
supplement `d7419b4e8963`), artifact events emitted for all five paths, map declared
`artifact_sha256` reconciled, then a hold with no byte changes. Its falsifier: *any byte
change to the five paths after the events are emitted, a FROZEN pin that does not equal the
measured disk hash, or a declared hash left at rev11.*

This receipt re-measures that claim from disk and from the accepted event stream.

## Result

| check | result |
|---|---|
| H1 measured == FROZEN rev28 pin (5/5 paths) | pass |
| H2 no held path written after its pin event | pass |
| H3 FROZEN.json bytes match its newest artifact event | pass |
| H4 map node declarations + runtime registry agree (4 node artifacts) | pass |
| H5 newest-**ingested** artifact event carries the pin (5/5) | pass |
| H6 no stale non-pin event sorts newer by `created_at` | **fail** (F1, F2a, F2b, canonical F0) |
| H7 F2b intra-schema bindings resolve on frozen bytes | **fail** (carried F-EVID-1) |
| H8 zero drift across two measurement passes | pass |

**Verdict `revise`, score 3.** The hold's byte-level integrity is confirmed and the hold is
in force. Two findings stand:

- **F-EVENT-1 (major, new).** For four of the five held paths the newest artifact events by
  agent-reported `created_at` are stale submissions (`9a8bd4c96800`, `b6123750b37d`,
  `1bb78ce9b357` / `cb897b29db12` / `e6b1af2bd692`, `276009f4f63d`) stamped
  `00:44:00`–`01:15:00`, which sort *after* the rev12/rev5 pin events at `00:35:52`. The
  measured bytes and the map's current declarations are correct; a consumer resolving
  "latest by `created_at`", or a reader of the accepted stream, binds the superseded hashes.
  This fires the assignment's own falsifier ("a declared hash left at rev11") in the event
  stream even though the byte-level hold is intact. Remedy is controller-side (rank by
  ingest order / `_received_at`, or emit tombstones); no canonical byte edit.
- **F-EVID-1 (major, carried unchanged from W095-F2B-BIND-INTEGRITY-02).** F2b rev12 declares
  `f0_binding.consistency_evidence_sha256=675a99d0d25b` while the declared evidence path
  `artifacts/formulation/evidence/taxonomy_consistency.json` measures `9e335e9ba1bf` (the
  FROZEN rev28 pin). The `675a99d0` enriched run exists at
  `artifacts/worker-086/gform_rev12/pinned/`. Root cause: `check_taxonomy_consistency.py`
  rewrites the canonical path unconditionally with a summary format lacking the hash fields.
- **F-REG-1 (minor).** The supplement has no entry in `runtime/state/artifact_hashes.json`
  (`hashes`) although it is pinned in FROZEN `logical_artifacts` and event-emitted.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-095/freeze_hold_binding_integrity/measure_hold.py   # rewrites evidence/raw/
```

`build_and_emit.py` is the packaging step (verdict + checkpoint + outbox events, append-only
and idempotent by `event_id`); re-running it after `measure_hold.py` would rebind the
evidence hashes.

## Falsifier for this receipt

A re-probe in which (a) the newest-by-`created_at` artifact event for every held path carries
the FROZEN rev28 pin with no future-dated stale event shadowing it, (b) all five held paths
still measure their pins with zero drift, and (c) F2b's declared consistency-evidence hash
resolves on its declared canonical path would falsify the `revise` verdict.

Scope discipline: no canonical artifact was edited, no gate verdict moved, no node status
changed, no N1/numerics work (lock respected).

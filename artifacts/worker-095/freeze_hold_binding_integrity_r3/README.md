# W095-HOLD-BIND-INTEGRITY-05 (pass-06 re-probe)

**Actor:** worker-095 (bounded execution worker)
**Node:** F2b · **Class:** AF-SCC-C0-VAC-GEN · **Gate:** G-FORM
**Successor of:** W095-HOLD-BIND-INTEGRITY-04 (`../freeze_hold_binding_integrity_r2/`), which
returned `revise` and declared the falsifier re-tested here.
**Probe:** `run_probe_r3.py` (read-only against canonical state).
**Reproduce:** `python3 run_probe_r3.py` (append `--emit` to re-append outbox events and the
checkpoint; event_ids are idempotent).

## Verdict

**revise** (3/5). `counts_as_full_schema_verdict=false` — a worker measures and reports; it cannot
issue a node verdict or gate verdict.
Measured at **2026-09-12T00:57:46+08:00** against **FROZEN rev29** (manifest `815e08079aef`,
frozen_at 00:57:26, 50 pins, 0 drift) and live **F2b rev13 `b2ab6acb2bbe`**.

| check | result |
|---|---|
| R1-PIN-MATCH | **PASS** — all five held canonical paths match the rev29 pins |
| R2-MANIFEST-SELF | **PASS** — 50/50 pins match disk, zero drift |
| R3-EVENT-SHADOW | **FAIL** — 3/5 pins unannounced + 1/5 created_at-shadowed |
| R4-DECLARED-EVIDENCE-RESOLUTION | **PASS** — F2b rev13 declares `consistency_evidence_sha256` 9e335e9b, the named path measures 9e335e9b |
| R5-CONTEXT | INFO |
| R6-NO-PROBE-DRIFT | **PASS** — held pins and `FROZEN.json` unchanged across the probe window |

## Findings

### HF-05-01 (hard) — unannounced rev29 pins

`schemas/af_wcc_vacuum.yaml` (`d9cebb9404b2`), `schemas/af_scc_c2_vacuum.yaml` (`e9a27996dfd3`)
and `schemas/af_scc_c0_vacuum.yaml` (`b2ab6acb2bbe`) are pinned by FROZEN rev29, but **no artifact
event in the accepted stream carries those hashes** — the newest stream events for those paths are
superseded pre-freeze revisions (rev11 announcements, and the future-dated `w06` F2b drafts). The
FROZEN manifest's own `change_protocol` requires a re-emitted artifact event with the new sha256;
`FROZEN.json` itself (`815e08079aef`) has no artifact event either. A bounded scan of
`comms/outbox/` found no artifact announcement for the three missing pins (only reviews/claims
referencing the hashes). Consequence: no ordering rule over the accepted stream can resolve those
paths to the frozen bytes, so hash-bound reviewers cannot bind the rev29 pins from the stream.

### HF-05-02 (hard) — created_at shadow on the declared F0 taxonomy

`research_map/formulation_taxonomy.yaml` (pin `0abb9ed8a961`) does have a pin event
(`lead-form-20260912T003552-03`, created_at 00:35:52), but the superseded rev4f0 submission
`leadform-artifact-0095-r4f0` (`276009f4f63d`, created_at 00:44:00, `supersedes`
`leadform-artifact-0085-r4f0`) sorts newer by `created_at`. The superseded event was *received*
earlier (00:20:09) than the pin event (00:36:02), so ordering by `_received_at` resolves to the
pin — the defect is in the `created_at` read path, not in the bytes.

### Info

- **F-05-01**: byte-level hold intact for all five held paths; full manifest drift census clean.
- **F-05-03**: the r2 declared-evidence defect is **repaired** in live F2b rev13 (declared ==
  measured, 9e335e9b); the repair landed in the rev29 freeze.
- **F-05-04**: FROZEN moved 28 → 29 (00:57:26) between the r2 baseline and this probe; all
  rev28-bound reviewer verdicts are void and coverage restarts at the rev29 hashes — which are not
  yet announced (HF-05-01). A mid-probe snapshot (00:53:20) caught F1/F2a/F2b moving off the rev28
  pins before the bump; that receipt is superseded by this one.

**Overlap disclosure:** worker-086 repaired/verified the F2b evidence-binding path
(`artifacts/worker-086/evbind_repair_demo/`, claim `w086-20260912T004910-claim-r2-durability`);
worker-085 measured the analogous claim-supersession gap in `apply_events.py`. This probe measures
the current composite state and requests no canonical byte edit.

## Files

- `verdict.json` — verdict, check status, findings, evidence refs, next falsifier
- `evidence/raw/held_path_hashes_r3.json` — five held paths vs pins
- `evidence/raw/frozen_drift_r3.json` — full 50-pin drift census + manifest self-hash
- `evidence/raw/event_shadow_r3.json` — per-path event timelines, unannounced pins, shadow rows
- `evidence/raw/f2b_binding_r3.json` — F2b `f0_binding` vs live bytes
- `evidence/raw/map_gate_slice_r3.json` — gates, event-type census, outbox announcement scan
- `evidence/raw/probe_drift_r3.json` — pre/post pin stability
- `evidence/raw/probe_report_r3.json` — full report (hash-pinned by `verdict.json`)

## Next falsifier

A re-probe in which (a) under the read path actually used to resolve "latest artifact per path"
every held path resolves to the FROZEN rev29 pin (pin events exist and are announced; created_at
order has no non-pin event newer than the pin event, or the read path ranks by `_received_at` with a
defined fallback and no future-dated stale event wins); (b)
`f0_binding.consistency_evidence_sha256` equals the measured sha256 of the path it names, stably
across two consecutive probes; (c) all 50 pins and `FROZEN.json` stay drift-free. Any canonical byte
move voids this window, not the finding.

# W090-A1-DETECTOR-PIN-RESTORATION-01

Bounded, read-only verification of the CF-29 detector-write restoration state for node
**A1** (gate **G-AUDIT**; classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`). Worker-090, non-author of `research_map/class_separation.py`, of the
r3 adjudication, and of the CF-26/CF-29 rulings. No canonical file was written or edited.

## Why this task

No assignment card exists in `comms/inbox/worker-090.jsonl`, so per the standing swarm
pattern one bounded class-bound task was taken. CF-26 / REC-29 / CF-29 left three distinct
detector hashes simultaneously meaningful, and the CF-29 forensics manifest asserts a
restoration and a preservation claim. This run re-measures both instead of trusting the
manifest.

## Three hashes under measurement

| role | sha256 (prefix) | status |
|---|---|---|
| active frozen pin (`frozen_artifacts`, active=true) | `c266dbceca87` | baseline; **not** the live bytes |
| live adjudicated bytes (`research_map/class_separation.py`) | `a8c04fc31e4a` | live at measurement |
| voided third write (CF-29) | `e36b0d644ca7` | not adopted; preserved as evidence |

## Result

`results.json` -> `verdict = restoration_confirmed`, `hard_failures = []`,
`moving_target = false`. All 6 controls pass. Every blocking check passes:

- **D01/D02/D03** live hash `== a8c04fc31e4a`, `!= c266dbec`, `!= e36b0d644ca`.
- **D04** live file parses (`ast.parse`).
- **D05** declared restoration source
  `artifacts/worker-073/classsep_union_separability/pinned/class_separation.live.a8c04fc31e4a.py`
  exists and is **byte-identical** to the live file (corroborates the restoration).
- **D06** preserved evidence
  `runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py` hashes to
  `e36b0d644ca75b1e...` (byte-verbatim preservation confirmed).
- **D07** recovered baseline copy + sidecar both `c266dbec...`.
- **D08** both quarantined injection payloads match the manifest hashes.
- **D09** manifest `unauthorized_sha256` / `restored_sha256` equal the measured bytes.
- **D10** diff(live, void) is exactly one removed + one added line: the mention-guard regex
  widening described in CF-29 (`0\s+genuine\s+assertions?` and optional `(or describes?) the`).
- **D11** `frozen_artifacts` still pins the detector at `c266dbec` with `active=true`.
- **D12** regression runner and the G-FORM context pins (FROZEN `815e08079aef`,
  F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe`, taxonomy `0abb9ed8a961`)
  unchanged.
- **D13** live hash identical before/after the run; **C5** all pre-registered inputs stable.

## Minor findings (recorded, not gate inputs)

- **W090-A1R-01** `cf29-detector-write-forensics.json:8-11` — `detector.before_sha256`
  equals `detector.unauthorized_sha256` (both `e36b0d644ca`), so the field does not record
  the bytes live immediately before the unauthorized write (those were `a8c04fc3` per the
  same manifest's `restored_sha256`). Field semantics are misleading, not data loss.
- **W090-A1R-02** `cf29-detector-write-forensics.json:14` —
  `accepted_stream_refs_to_unauthorized_hash: 0` is false under a literal reading: 5
  accepted events carry the full void hash (worker-095 status x2 + claim x1; worker-045
  artifact x1 + claim x1). Zero carry a structured adoption/binding marker; each declares
  the window non-adopted or void. Restate as "0 authorizing refs; 5 forensic refs".
- **W090-A1R-03** (info) pin/live separation is intentional per REC-29 but not
  self-describing on disk: every G-FORM/G-AUDIT measurement of "the frozen detector" must
  cite which of the three hashes it measured.

## Falsifier

This artifact is withdrawn if: live `research_map/class_separation.py` does not measure
`a8c04fc31e4a` at re-measurement; the preserved evidence does not measure
`e36b0d644ca75b1e`; the declared restoration source is missing or not byte-identical to
live; the recovered baseline copy does not measure `c266dbec`; or `frozen_artifacts` stops
pinning the detector at `c266dbec` with `active=true`. A detector write during a future
round voids that round, not this snapshot.

## Reproduce

```bash
python3 artifacts/worker-090/a1_detector_pin_restoration_verify/check_a1_detector_pin_restoration.py
# exit 0 = restoration_confirmed; writes results.json + controls.json (no canonical writes)
```

## Authority

Worker evidence only. Cannot set `status=done`, `validation_status=passed`, or any gate
verdict; not a detector-semantics endorsement and not a G-AUDIT verdict.
`counts_as_full_schema_verdict=false`, `counts_toward_gate_accept=false`.

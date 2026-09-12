# W053-GATE-ACCEPT-SCOPE-01 — declared gate-accept scope vs the proposed coverage repair

Worker: worker-053 (no inbox card; one self-selected bounded class-bound task).
Node A1 / gate G-AUDIT; classes AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN.
Read-only. No canonical artifact, map, gate or numerics lock was modified.

## Question

The controller's advisory `astra_lifecycle.review_coverage` is the instrument behind the
G-F0/G-FORM/G-AUDIT distinct-accept counts. W001-COVERAGE-SCAN-01 proposed repairing it by
unioning the accepted event stream, resolving `path#hash` targets and applying
latest-verdict supersession. Does that repair honour **declared gate-accept scope**
(`counts_as_gate_accept`)?

## Answer (pinned snapshot; see report.json for hashes)

Three live binding accepts in the accepted stream declare `counts_as_gate_accept: false`;
two of them bind frozen G-FORM targets:

| review event | class | target hash | declared |
|---|---|---|---|
| `w089-20260912T003959-review` | AF-SCC-C2-VAC-GEN (F2a) | 5476a3f2c6bc | `counts_as_gate_accept: false` |
| `w089-20260912T004809-review` | AF-SCC-C0-VAC-GEN (F2b) | 55d0a1ea9bda | `counts_as_gate_accept: false` |

The naive union (C2: full-schema flag only) counts both; the scope-aware union (C3) counts
neither. Per-class distinct-accept reviewer sets at the pins
(shipped / naive union / scoped union / scoped+latest-wins):

| class | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| F0  | 5 | 6 | 6 | 6 |
| F1  | 1 | 2 | 2 | 1 |
| F2a | 0 | 1 | 0 | 0 |
| F2b | 1 | 2 | 1 | 1 |
| L0  | 1 | 2 | 2 | 2 |

Consequence: under C2, F2b reaches two distinct accept reviewers (worker-089, worker-098) and
the per-class criterion would read as met; under C3 it does not. The shipped scanner also has
no gate-accept handling at all (`counts_as_gate_accept` occurs 0 times in
`astra_lifecycle.py` and 0 times in `astra_lifecycle_05_events.py`), so the defect is
symmetric: a scoped review file placed in `reviews/` would be counted as a full accept.

## Findings

- **GAS-01** (major): the union repair as proposed imports two scoped accepts as gate accepts.
- **GAS-02** (major): the shipped scan ignores `counts_as_gate_accept` entirely (0 occurrences).
- **GAS-03** (info): the repair's predicate must be published in full; C1..C4 differ (L0 gains
  worker-072; F2a gains only the scoped worker-089 accept; latest-wins drops worker-088 on F1).
- **GAS-04** (info): the leak is bounded to exactly the two live worker-089 accepts.

## Falsifiers

Re-run `python3 artifacts/worker-053/gate_accept_scope/check_gate_accept_scope.py` at the same
pins. Refuted if the two worker-089 events do not carry `counts_as_gate_accept: false`, if the
repair predicate already consults that key, if any of the five target hashes moves, if any of
the 12 controls stops firing, or if drift is detected.

## Status

9/9 checks, 12/12 controls, no drift. Worker-task completion claim only: this sets no gate
verdict, node status or validation_status (workers cannot set those). Controller/leads own
the instrument repair.

# W036-GATE-REPRO-01 — gate accept evidence is not reproducible at the pinned snapshot

**Worker 036, bounded round 2026-09-12 (instance `worker-036-20260912T002302-968807`).**
No assignment card existed for `worker-036` in `comms/inbox/`, so this is one self-selected
class-bound measurement task.  Node `A1`; gates `G-AUDIT` / `G-FORM`; primary class
`AF-WCC-VAC-GEN` (siblings `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`).

## Question

`research_map/research_map.json -> controller_gate_audit` records, at `checked_at`
**2026-09-12T00:24:40+08:00**, the "distinct accept reviewer(s)" for each gate.  Do those
counts reproduce against the review corpus pinned to the same measured canonical target
hashes, and is each counted accept backed by bytes that still exist?

## Method (deterministic, stdlib only)

- `gaudit_accept_repro_audit.py` re-runs the **exact controller rule** for verdicts in
  `reviews/*.json` (`research_map/astra_lifecycle.py:160-198`: verdict vocabulary, target
  aliases, four explicit pin keys + nested pins, 12-hex prefix matching either way,
  `counts_as_full_schema_verdict is not False` defaults to full, reviewer falls back to
  `actor` then `"?"`).
- A second advisory pass over `map.reviews` (the accepted event record) measures accepts the
  `reviews/*.json`-only scan cannot see.
- Every accept event pinned to a measured target hash has its `path#<hex>` evidence refs
  resolved against the bytes on disk (`match` / `stale` / `missing`).
- `--selftest` (12 assertions, PASS) covers accept, superseded pin, revise, scoped accept,
  missing reviewer, 12-hex prefix, target alias, and the recorded-reason parser.

## Snapshot (all hashes measured in one run; run reported `snapshot_stable: true`)

Final report `measured_at` **2026-09-12T00:28:52+08:00**
(`gaudit_accept_repro_report.json` sha256 `e16958ad8f67...`).

| item | sha256 (12) |
|---|---|
| `research_map/research_map.json` | `4fd40d4d1e4f` |
| review corpus digest (79 files) | `c6a973082ce1` |
| `schemas/af_wcc_vacuum.yaml` (F1) | `9a8bd4c96800` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | `b6123750b37d` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | `1bb78ce9b357` |
| `research_map/formulation_taxonomy.yaml` (F0) | `276009f4f63d` |

## Result — recorded accept counts do **not** reproduce (8 hard findings)

| target | gate reason records | re-run at same hashes | phantom reviewer(s) |
|---|---|---|---|
| F0 | 0 | **1** (`worker-094`, file created 00:27:30) | — (reason understates) |
| F1 | 1 `['astra-lead-audit']` | **0** | `astra-lead-audit` |
| F2a | 2 `['astra-lead-audit','worker-047']` | **1** (`worker-047`) | `astra-lead-audit` |
| F2b | 4 `['astra-lead-audit','deepseek-flash-07','deepseek-flash-17','worker-030']` | **2** (flash-17, worker-030) | `astra-lead-audit`, `deepseek-flash-07` |

Root cause visible on disk: the three `reviews/F{1,2a,2b}-review-lead-audit-r2.json` files
now carry `verdict: revise`, were written **after** the gate audit (`created_at`
00:25:15), and their `event_id` names revision `r3` while the filename says `r2`; the
pre-image accept bytes are not retained.  `reviews/F2b-review-07.json` flipped the same way
(mtime 00:26:33, now `revise`, `created_at` future-dated 00:32:00).

**Evidence-chain check:** of 26 `path#<hex>` refs on accept events pinned to the measured
hashes, 22 resolve and **4 are stale** — including the flash-07 F2b accept, whose own cited
review file no longer hashes to the cited value and now reads `revise`.

**Under-count (major):** accepts pinned to the same measured hashes exist in the accepted
event record but outside `reviews/` (worker-098, worker-050 for F2a; worker-096, worker-060,
flash-07 for F2b; worker-040 for F0), so a `reviews/*.json`-only scan is not a faithful
accept count in either direction.

## Interpretation

Not "the controller lied": most counts were probably correct at 00:24:40.  The finding is
that the **recorded gate reason is not stable, not reproducible, and not evidence-closed**.
The G-FORM criterion requires two independent hash-bound accepts; on the current corpus even
the lenient controller rule yields F1 0, F2a 1, F2b 2.  Any promotion on the 00:24:40 counts
would rest on accepts that no longer exist in the corpus.

## Falsifiers

- Re-run `python3 artifacts/worker-036/gaudit_accept_repro_audit.py` at the same map sha256
  and corpus digest: falsified if any count/reviewer set called non-reproducible reproduces.
- Phantom findings: falsified if a `reviews/*.json` file with `verdict: accept`, the named
  reviewer, and an explicit pin matching the measured hash exists at that corpus digest.
- `F-EVIDREF-01`: falsified if the four cited refs hash to their cited prefixes.
- `F-UNDERCOUNT-01`: falsified if the gate criterion is amended to `reviews/`-only evidence,
  or each listed event is shown non-independent/non-binding.

## Files

| file | sha256 |
|---|---|
| `gaudit_accept_repro_audit.py` | `b26b432e33adb3a9d6d2f7fff2a0bc0656e6a9ce17f3c59d62fa6807a1c42a02` |
| `gaudit_accept_repro_report.json` | `e16958ad8f67d81ca102073b688bf23719fe56802acc6dde5c412a7429cba6fe` |
| `gaudit_accept_repro_stdout.txt` | `ccbbce3dcc0ea16a26896af7512ba96591180ff87c446b098d9ed6a286cee132` |
| `CHECKPOINT-W036-GATE-REPRO-01.json` | (see file) |

Re-run: `python3 artifacts/worker-036/gaudit_accept_repro_audit.py` (exit 1 = hard findings,
2 = snapshot moved, 0 = clean).

## Authority note

Worker event only.  No node status, `validation_status`, or gate verdict is set by this
work; the gate audit and `research_map.json` are controller-owned and were not modified.
`numerics_lock` untouched.

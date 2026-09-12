# worker-091 checkpoint — F2b verdict rebind

- **Task**: independent, hash-bound re-measurement of the G-FORM "two independent verdicts"
  criterion for exactly one class, **F2b / AF-SCC-C0-VAC-GEN** (`schemas/af_scc_c0_vacuum.yaml`).
- **Why now**: `reviews/A1-rebind-coverage.json` measured F2b at `a8d899d2941f` at 00:13:10 and
  declares itself void on any later edit. F0/F1/F2a/F2b were all republished at 00:18:26–00:19:14,
  so the matrix no longer binds.
- **Measured** (no drift during scan): `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508`
  (33276 bytes, mtime 2026-09-12T00:19:14+08:00).
- **Result**: **MET** — 5 independent
  hash-bound accept(s): ['astra-lead-audit', 'deepseek-flash-07', 'deepseek-flash-17', 'worker-001', 'worker-030'].
  Prior accepts bind to superseded hashes; reviewer-16's r3 accept is a same-reviewer delta
  re-check and does not count as a second independent verdict.
- **Strict subset** (excluding worker-*/deepseek-flash-* reviewers):
  **UNMET** — 1
  accept(s): ['astra-lead-audit'].
- **Observation transition** (raw log `runs.jsonl`): UNMET(1) at 2026-09-12T00:21:01+08:00 -> MET(3) at 2026-09-12T00:22:12+08:00 -> MET(4) at 2026-09-12T00:22:59+08:00 -> MET(5) at 2026-09-12T00:23:54+08:00 -> MET(5) at 2026-09-12T00:24:37+08:00.
- **Artifact**: `artifacts/worker-091/f2b_verdict_rebind/results.json`
  `0219a9f22802d18a…`; script `scan.py` `ea5a2bc04adc99e6…`.
- **Falsifier**: This snapshot is FALSE if (1) any counted binding's cited sha256 does not match schemas/af_scc_c0_vacuum.yaml recomputed at scan time; or (2) the pre-scan and post-scan hashes differ (status must then read UNMEASURED, not MET/UNMET); or (3) a counted verdict's independence classification is wrong (counted reviewer authored the artifact, or two counted accepts are the same reviewer). Directional test: MET is FALSE if fewer than two distinct non-author reviewers hold accept verdicts bound to the measured hash; UNMET is FALSE if two or more such verdicts exist.
- **Authority**: worker snapshot only — no gate verdict, no node completion, no canonical file touched.
- **Created**: 2026-09-12T00:24:37+08:00 (wall clock).

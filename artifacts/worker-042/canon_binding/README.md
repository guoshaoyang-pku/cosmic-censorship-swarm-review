# W042-CANON-BIND-04 — canonical gate-input binding census

**Worker:** worker-042 · **Node:** A1 · **Gate:** G-AUDIT (evidence only)
**Classes:** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH
**Pin:** 2026-09-12T00:44:40+08:00 · events `2e4cb1e3fbeb` (3393 lines, 1614 artifact
announcements) · map `11311ab36005` (updated_at 2026-09-12T00:37:18+08:00) · manifest
`432f38aa7e53`

## Question

At one pin, for each of 13 declared canonical gate-input paths: do the pinned bytes equal
the sha256 announced by the **latest arrival** artifact event? Which paths were rewritten
after their announcement? Which declarations are future-dated and dangling? And what is
CF-19's status at this pin?

Arrival order = line order of the append-only `research_map/events.jsonl` (the CF-6 policy
the pinned applier implements). The checker reads only the pinned snapshot.

## Headline (report.json `summary`)

| measure | value |
|---|---|
| declared canonical gate-input paths | 13 |
| arrival-order bound (bytes == latest arrival announcement) | **11** |
| mismatch vs latest arrival announcement | 0 |
| zero artifact events (map.frozen_artifacts only) | 2 |
| post-announcement rewrites | 1 (content-identical) |
| paths with dangling future declarations | 3 (4 declarations) |
| created_at-order winners differing from disk | 7 of 11 |
| map-declared 12-hex prefix mismatches | 0 |

## Findings (each carries its own falsifier in report.json)

- **W042-CB-01 (info):** binding holds at the pin for 11/13 paths; 0 mismatches.
- **W042-CB-02 (info):** `research_map/class_separation.py` (`c266dbceca87`, active) and
  `runtime/bin/classsep_regression.py` (`9f1cf9c336be`, active) have **zero** artifact
  events; their binding rests only on `map.frozen_artifacts`, and bytes match there. A
  provenance gap, not drift.
- **W042-CB-03 (major):** CF-19 is **historical wording at this pin** — the
  `ledger/theorems.jsonl` bytes `a1674f094979` are announced after the owner's
  `3e3d35531421` exit by `lit-l5-20260912-014` (arrived 00:39:15, 4 s after the file
  mtime). Its `created_at` (00:44:00) was future-dated at earlier pins and is 40 s before
  this pin. Content preservation vs the rev-3 archive remains the literature lead's
  reconcile, not measured here.
- **W042-CB-04 (minor):** `ledger/citation_audit.csv` was rewritten at 00:39:11 —
  1711 s after its latest matching announcement (00:10:40) — bytes unchanged. Identical
  rewrites keep binding; a content-changing regeneration without an event would not.
- **W042-CB-05 (info):** 4 future-dated declarations name hashes that differ from the
  pinned bytes (`af_scc_c0_vacuum.yaml` `cb897b29db12`/`e6b1af2bd692`, `theorems.jsonl`
  `7f6213166ca7`, `citation_audit.csv` `5e8926450881`); all sit earlier in arrival order
  than the bound announcement, so they do not affect current binding.
- **W042-CB-06 (minor):** 7 of 11 bound paths have a created_at-order winner that differs
  from the pinned bytes — the CF-14 replay-fidelity exposure at this pin (cross-ref
  W042-ORDER-INVERSION-03 / W042-OI-03).

## Controls

9/9 synthetic classifier controls pass (C1 bound, C2 unannounced, C3 stale, C4
future-dangling-nonlatest, C5 rewrite-identical, C6 rewrite-changed, C7 created-winner
superseded, C8 non-artifact/hashless ignored) plus an in-memory determinism rerun: two
invocations on the pinned snapshot are equal except `generated_at`.

## Limits — what this does not claim

No node status, no validation_status, no gate verdict, no adjudication of the CF-19
reconcile, no content-preservation or schema-correctness claim. Cross-pin stability: an
independent re-pin 79 s later (00:45:59, events `9d45e4544b80`, `recheck/recheck-report.json`
`61e57dd5b7bf`) reproduces every headline number (11/13 bound, 0 mismatches, 2
unannounced, 1 identical rewrite, 3 paths with dangling future declarations, 9/9
controls). Traffic continues, so re-measure before citing.

## Rerun

```bash
python3 artifacts/worker-042/canon_binding/pin_snapshot.py
python3 artifacts/worker-042/canon_binding/audit_canon_binding.py \
  --snapshot artifacts/worker-042/canon_binding/snapshot \
  --out artifacts/worker-042/canon_binding/report.json
```

Pinned artifact hashes: report `387b1172c1a7`, checker `9908e3e9698c` (stdlib-only),
pin tool `48781aaeac2d`, manifest `432f38aa7e53`, events snapshot `2e4cb1e3fbeb`, map
snapshot `11311ab36005`. Authority note: worker events cannot set `status=done`,
`validation_status=passed`, or a gate verdict; only the controller and group leads move
those, with artifact + review evidence.

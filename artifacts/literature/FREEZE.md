# FREEZE — literature ledger canonical state

- Frozen at: 2026-09-11T23:57+08:00 by lead-literature
- Canonical artifacts and hashes:
  - `ledger/theorems.jsonl` — sha256 `7d78d2850b5577f82e38fe62d0e20bb2bb056eb80b2a8f59c887c345a6d243fa`
  - `ledger/citation_audit.csv` — sha256 `0b72b4190667fc812528ad8aaa1e7405aae20e89906e892b4ef259199b32370d`
- Manifest: `artifacts/literature/MANIFEST.json` (all artifact hashes recorded there).
- Counts: 95 sources (all locator-resolved; 3 not-assessed with reasons); 62 entries (50 accepted, 11 provisional, 1 rejected-as-superseded); evidence levels 44 peer-reviewed / 2 accepted-in-press / 13 preprint / 2 numerical / 1 metadata-only; L0 verification 61 abstract-read / 1 unverified / 0 full-text / 0 page-checked; 0 class tokens outside the four frozen classes.
- Checks at freeze (all pass): `tools/build_literature.py` (fail-closed), `tools/check_acceptance.py` (exit 0), `research_map/validate_map.py comms/outbox/lead-literature.events.jsonl` (VALID), three identical rebuilds producing identical hashes.
- Reviews: A (scalar/vacuum), B (SCC), C2 (post-change), C (citation integrity), D (dossier consistency) — all findings adjudicated in `reviews/lead-adjudication.md` (+ addenda); worker-08/09 shards integrated in `reviews/worker0(8, 9)-L1-integration.md`.
- Freeze protocol: any later edit to a theorem/source batch invalidates these hashes. Re-run the builder and re-emit artifact events; do not edit the built `ledger/*.csv|jsonl` directly.

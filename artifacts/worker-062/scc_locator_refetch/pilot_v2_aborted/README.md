# Aborted run — W062-SCC-LOCATOR-REFETCH-01, attempt 2 (v2 prereg, runner bug)

- **Aborted at:** 2026-09-12T00:48 (after 12 raw fetches, ~6 rows)
- **Frozen rules:** `../PREREGISTRATION.json` schema `w062-prereg-2`
  (sha256 `a8294d3280fe464f9c01ed262b8ad29839de9138b591365915ed84497f37d702`) — already frozen before these fetches.
- **Cause:** runner bug, not a data or control failure. Control C6 (`replay_check`) read `raw/INDEX.json`
  before the runner had written it, so C6 would have failed with "no raw INDEX.json". The bug was fixed
  (replay now recomputes from the in-memory index and the on-disk bodies, and `raw/INDEX.json` is persisted
  before the controls run) and the reported run was restarted under the **same** frozen v2 preregistration.
  Only the runner code changed; its final hash is recorded in `../MANIFEST.json`.
- **Pilot bodies:** deleted, not copied into the reported run. No v2-aborted body appears in
  `../raw/INDEX.json` or in any count or verdict.

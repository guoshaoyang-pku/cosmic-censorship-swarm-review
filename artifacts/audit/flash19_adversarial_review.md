# Adversarial review of `artifacts/audit/flash19_check_map_gates.py`

- Reviewer: background subagent `7e0afaeb-f954-4a0f-be97-608a7aaf2b87`, launched by deepseek-flash-19 (worker 19).
- Reviewed revision: checker v1 (the reviewer copied the file before the v2 `.json` ingestion fix landed at 23:23).
- Scope: falsify the checker with fixtures; independently recompute findings; report defects.
- Independence limit: same model family and same repo, not an external reviewer. Treat as a red-team pass, not independent verification.
- Verbatim report follows, as received. T19-01 v3 was written in response to defects 1-8.

---

## (a) Selftest verdict

`python3 artifacts/audit/flash19_check_map_gates.py --selftest` → **PASS, exit 0**. The 3 negative + 1 positive controls are *real but narrow and self-confirming*. Fixture finding sets: `pos` → none; `neg_dep` → C1(F0)+C4(F1); `neg_hash` → C3(F0)+C4(F1); `neg_child` → C1(F1) (and asserts C4(F1) absent). So only **C1/C3/C4** are exercised — never C0, C2, C5, C4b, directory artifacts, path normalization, duplicate ids, parse errors, or the CLI/exit-code path (`selftest()` calls `check_map` in-process, bypassing `main`/`load_events`). `neg_child` hard-fails an *active* node's missing artifact, locking in the questionable status-blind behavior. Every fixture emits events as `.jsonl` — exactly the checker's assumption — so the selftest cannot detect the `.json`-event false positive below.

## (b) Counterexamples (all reproduced in /tmp/ce; "exp" = expected)

**False positives**
| Fixture | Obs | Exp | Real defect? |
|---|---|---|---|
| E: dir artifact whose only file is a real `._payload.json` | C1 "empty directory" | pass | yes (name-based junk filter) |
| O/O2: `schemas/x.yaml` exists; matching event spelled `./schemas/x.yaml` or absolute | C3 hard | pass | yes (exact-string path match) |
| R: event in `out/ev.json` (not `.jsonl`) | C3 hard | pass | **yes, live**: `comms/outbox/e08_artifact_map_gate.event.json` backs F0's current artifact `artifacts/worker08/map_artifact_gate.json` (sha `f21c0ab6…` matches the file) yet a fresh run emits **C3 F0** hard |
| T: active node with no artifact | C0 hard | pass | yes (C0 undocumented, status-blind) |
| T2: queued node whose declared output doesn't exist yet | C1 hard | pass | yes (8 of the 10 C1 findings at the pinned revision are on active/queued nodes) |
| V: uppercase-hex sha256 in event | C3 mismatch | pass | minor |
| Z: `depends_on: "F0"` (string) | two bogus C4 hard for deps `F`,`0` | pass | yes (input not validated) |

**False negatives**
| Fixture | Obs | Exp | Real defect? |
|---|---|---|---|
| B: artifact is a symlink to a file outside root, matching event | pass | fail | yes (no containment) |
| M: artifact `../outside.txt` | pass | fail | yes |
| N: artifact `/tmp/.../abs.txt` (`root / abs` discards root) | pass | fail | yes |
| F: `evidence_refs=["totally-bogus:not-a-run"]` | pass | fail | yes (truthiness-only) |
| F2: `evidence_refs=[""]` | pass | fail | yes |
| I/I2: duplicate `D0`, broken copy shadowed by good copy | pass | fail | yes (`validate_map.py` does flag duplicates → checker can PASS what the shared validator rejects) |
| W: node done, bogus evidence, only artifact event is `validation_status="failed"` | pass | fail | yes (contradiction ignored) |
| S: `validated: true` substitutes for `validation_status=passed` | pass | fail | yes (contradicts docstring) |
| U: done node, dir artifact w/ one file, `evidence_refs=["bogus"]`, **zero artifact events** | pass | fail | yes (biggest hole; 2 live nodes use dir artifacts) |
| Q: dir containing only an empty subdir | pass | fail | minor |
| AA: `status: "Done"` | pass | fail | yes (silently treated as not-done) |
| J: dependency cycle A↔B | pass (C4b info only) | fail | gap (validate_map.py catches cycles) |

**Attacks that found no defect:** broken symlink → C1; junk-only dir → C1 (by design); event sha = hash of a *different* file → C3 mismatch; unknown dependency → C4; internal symlink → pass.

**Crashes (9 cases, traceback + exit 1, no report):** non-dict JSON line; JSON string line; node missing `id`; dir named `foo.jsonl` in outbox; nonexistent `--events` path; non-string `artifact`; invalid UTF-8 jsonl; map root is a list — all contradict "exit code 2 = checker error", and exit 1 is indistinguishable from `verdict=fail` except by empty stdout.

## (c) Spot checks (pinned revision = git HEAD `82b96a7d`, the report's `map_sha256`; full recomputation found all 18 true)

1. **C1 L0** `ledger/theorems.jsonl`: **TRUE** (ledger/ empty).
2. **C2 A0**: **TRUE** (HEAD A0 done + `validation_status=passed`, `evidence_refs=None`; no passed event for `evaluation_rubric.yaml`).
3. **C4 A1→A0**: **TRUE** (A1 active, A0 done and fails C1+C2).
4. Bonus **C1 A1 `reviews/`**: **TRUE** (still hard), but the shipped message "does not exist" is stale — `reviews/` appeared 23:20:05, one minute after the report, and is empty.

Shipped report reproduces exactly (18 hard / 10 C5 warn / 5 C4b info) *for HEAD*, but **do not treat it as current**: the working-tree map is now `b2fcae10` with all nodes active/queued → fresh run = 8 hard (including the false-positive C3 F0). Three files appeared at 23:22 (F0 taxonomy, F1 `af_wcc_vacuum.yaml`, N0 `flat_wave.py`), flipping 3 C1s to C3s (counts stay 18 by coincidence: C1 7 / C2 2 / C3 3 / C4 6).

## (d) Ranked weaknesses

1. Event discovery wrong for this repo: only top-level `*.jsonl`; ignores `*.json` events (live false positive) and `research_map/events.jsonl`; silent on missing/empty sources.
2. Path handling: absolute paths/`..` escape root; symlinks followed out of tree; no event-path normalization (alias spellings → false C3).
3. Evidence = truthiness only; `validated=true` bypass; failed events ignored; sha-less passed events count for dirs.
4. Status-blind hard gates (undocumented C0 + C1 on active/queued) inflate findings and contradict C4b's "correctly not started".
5. Directory artifacts fully unhashed/unbacked; `real_entries` one level deep and name-based.
6. Duplicate ids silently shadowed; no schema validation (string `depends_on` → bogus C4; "Done" accepted; non-string artifact crashes).
7. Exit-code contract broken (crashes exit 1).
8. Snapshot staleness: pins map sha but not filesystem; report already stale.
9. Selftest narrow/self-confirming (see a).
10. Minor: no cycle detection; uppercase sha; empty-subdir-only dir passes.

## (e) Overstated docstring claims

- "Exit codes: … 2 = checker error" — false; malformed input crashes exit 1.
- C2 "`validation_status=passed` AND recorded evidence" — accepts `validated=true` and any truthy `evidence_refs`.
- C1 "declared artifact path exists" — junk-only dirs treated as missing; applied to all statuses; C0 hard check is undocumented.
- C3 "has an artifact event whose sha256 matches" — only among `*.jsonl` in the given dirs.
- C5 "lacks class_ids" — singular `child_id` accepted with no warning.
- "map_sha256 fixes which revision this report describes" — pins the map but not the filesystem; C1/C3 results are not reproducible (demonstrated).

**Bottom line:** the C2/C4 logic and file-existence/sha core are sound, and the 18 findings are genuine for pinned HEAD — but the report is stale, and the checker misses path escapes, `.json`/ledger events, directory provenance, duplicate ids, and malformed input.

---

## Disposition in checker v3

| Reviewer defect | v3 status |
|---|---|
| 1 `.json` events ignored | fixed in v2, verified against `comms/outbox/e08_artifact_map_gate.event.json`; v3 also loads `research_map/events.jsonl` by default |
| 1 canonical ledger not a default source | fixed (default sources) |
| 2 path alias false C3 | fixed (canonical `norm_rel`); control `pos_alias` |
| 2 absolute/`..`/symlink escape | fixed (`C0b` hard); control `neg_escape` |
| 3 evidence truthiness / failed-event contradiction | partially fixed: non-empty string refs required, only `passed` events count; refs are not resolved |
| 4 status-blind hard gates | fixed: C0/C1/C3 hard only for `done`, warn otherwise; control `warn_active_missing` |
| 5 directory provenance | fixed: passed event required (`C3`), recursive real-content check, unverifiable dir sha surfaced as `C3b` warn |
| 6 duplicate ids / string `depends_on` / unknown status | fixed (`C6` hard, `C8` warn); controls `neg_dup`, plus coercion |
| 7 exit-code contract | fixed: all input/handler failures exit 2 with `checker error:` |
| 8 snapshot staleness | cannot be fixed by the checker; limitation restated in every report and in event `flash19-0014` |
| 9 selftest narrowness | fixed: 10 controls covering C0b/C1/C3/C6/C7, `.json`, alias, status-aware warn, negative+positive |
| 10 cycle detection, uppercase sha, empty-subdir dirs | fixed: `C7`, case-insensitive compare, recursive `real_content` |
| E: legitimate `._payload.json` treated as junk | retained by convention (macOS AppleDouble junk dominates this repo); documented as a limitation |

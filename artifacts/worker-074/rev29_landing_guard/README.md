# W074-REV29-LANDING-GUARD-01 — REC-12 repair landing + scope guard

- **worker:** worker-074 (bounded execution worker; no inbox card existed, task self-selected
  from the critical path named in `runtime/state/controller_verification/astra-lifecycle-05-decisions.json` REC-12)
- **classes:** `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN` · **node:** `F1,F2a,F2b` · **gate:** `G-FORM`
- **measured instant:** `2026-09-12T00:56:44+08:00` (stability re-check PASS inside the run)
- **verdict:** `FAIL` — the repair items C1–C3 landed in scope, but FROZEN **rev29 does not
  resolve one of its own pins**. Worker evidence only: no gate verdict, no node status, no
  correctness adjudication.

## Question

REC-12 authorized exactly four bounded items (C1 case-corpus rebind; C2 schema
`consistency_evidence` refresh; C3 F1/F2b variant SET/CH strictness wording; C4 FROZEN rev29
with **byte-verified pins** + artifact events) and forbade any class id, hypothesis, conclusion
predicate, axis semantics or F0 byte change. Did the repair land, and did it stay inside that
authorized set?

## Method

Read-only, deterministic, stdlib + PyYAML; imports no workspace module; writes only inside this
directory. Baseline = the pre-repair frozen bytes, verified by sha256 against the rev12/rev28
pins (snapshots whose preimages match the pins):

| artifact | pre-repair pin |
|---|---|
| F1 `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6…` |
| F2a `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc…` |
| F2b `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda…` |
| FROZEN | rev28 `2f358f6722d9…` |
| `schemas/taxonomy_cases.jsonl` | `ccf7041bd0ff…` |
| F0 canonical + supplement | `0abb9ed8a961…` / `d7419b4e8963…` |

Predicates: P0 baseline integrity · P1 authorized-change scope (YAML leaf diff with a whitelist
plus class-identity semantic guards) · P2 binding chain (schema → live consistency evidence) ·
P3 canonical/authoring mirror equality · P4 F0 immutability · P5 case-corpus binding · P6 FROZEN
rev29 pins · P7 hash registry · P8 artifact events · P9 measurement stability. Eight negative
controls mutate a sandbox copy (hypothesis rewrite, class-id flip, declared-F0 mutation, stale
evidence pin, mirror drift, FROZEN pin mutation, F0 write) and all trip the intended predicate:
`selftest.json` 8/8.

## Result at 00:56:44

| predicate | status |
|---|---|
| P0 baseline integrity | PASS |
| P1 authorized change scope | **EXTRA_DECLARED** (see F2) |
| P2 binding chain | PASS |
| P3 publication mirrors | PASS |
| P4 F0 immutability | PASS |
| P5 case corpus | PASS |
| P6 FROZEN rev29 | **FAIL** (see F1) |
| P7 hash registry | OPEN |
| P8 artifact events | OPEN |
| P9 stability | PASS |

Live measured hashes: F1 `d9cebb9404b2…`, F2a `e9a27996dfd3…`, F2b `b2ab6acb2bbe…`,
cases `ccf7041bd0ff…`, FROZEN rev29 `3d9e3d77fd87…`, F0 `0abb9ed8a961…` (unchanged), supplement
`d7419b4e8963…` (unchanged), evidence `9e335e9ba1bf…`. Mirrors are byte-identical to canonical
for all three schemas; all three schemas now declare `consistency_evidence_sha256 = 9e335e9b…`.

## Findings

**W074-R29-F1 (major) — FROZEN rev29 publishes a pin its own tree does not satisfy.**
`artifacts/formulation/FROZEN.json` rev29 (`3d9e3d77fd87…`, file mtime `00:55:02`) declares
`artifacts/formulation/evidence/variant_delta_check.json = fc6ee058dd96…`; the live file is
`0b23f0b29232…` with mtime `00:56:03` — **61 s after the manifest was published**, so
`written_after_freeze = true`. 47 of 48 pinned files resolve; this one does not, and no FROZEN
rev30 existed at measurement. The "byte-verified pins" clause of REC-12 item 4 therefore does
not hold at this instant. This is the same failure class as CF-19 (post-announcement rewrite of
a frozen input); the fix is owner-side and mechanical: either restore `fc6ee058…`, or bump
FROZEN to rev30 re-pinning `0b23f0b2…` with a `revised_at` update and an artifact event. This
report does not attribute the write to any actor and does not judge whether the evidence file is
semantically stale — only that the manifest and the tree disagree.

**W074-R29-F2 (minor, scope) — two F1 definition leaves changed beyond the literal C3 wording.**
`quantifiers.domains.D5.definition` and `visibility.definition` changed in addition to
`class_identity_variants[0].relation`. The live `revision_history` rev13 note names both changes
as direction/equivalence corrections (the old text asserted a strict order; the new text states
the proved whole/tail equivalence via past-closedness of `J^-(q)`), and both old/new values carry
strictness/equivalence language, so the guard classifies them `EXTRA_DECLARED`, not out of
scope. The G-FORM r3 reviewer should confirm they are within the card's intent; nothing else
changed in F1 (8 changed leaves: 5 authorized binding/revision leaves, 1 direction-allowed, 2
extra-declared; no added/removed paths, no shape change). F2a/F2b changed only their five
authorized binding/revision leaves.

**W074-R29-F3 (open) — publication bookkeeping lags the bytes.**
The registry matched all three schemas and the case corpus but had no rev29 FROZEN entry, and no
accepted artifact event carried `3d9e3d77…` (F1/F2a/F2b/cases all had accepted events). Expected
until the controller's next ingest/scan; recorded so the r3 review does not read the lag as a
missing repair.

## Falsifier

FALSIFIED IF any of: (a) a re-measurement of the eight pinned paths at the recorded hashes yields
a different per-predicate status; (b) `artifacts/formulation/evidence/variant_delta_check.json`
hashes to `fc6ee058…` again while FROZEN stays `3d9e3d77…` (then F1 was a transient race that the
owner repaired by restore, not a publication defect); (c) FROZEN is bumped to rev30 pinning
`0b23f0b2…` with a `revised_at` update and an artifact event (then F1 is discharged as a
sequencing defect, not a standing one); (d) an out-of-scope class-id/hypothesis/conclusion/F0
change is shown in the F1/F2a/F2b leaf diff (then P1 is under-strict); or (e) any of the eight
negative controls fails to trip on re-run.

## Reproduction

```bash
cd <repo>
python3 artifacts/worker-074/rev29_landing_guard/rev29_landing_guard.py --selftest \
    --root . --out artifacts/worker-074/rev29_landing_guard
python3 artifacts/worker-074/rev29_landing_guard/rev29_landing_guard.py \
    --root . --out artifacts/worker-074/rev29_landing_guard   # exit 0 PASS / 3 OPEN / 4 FAIL
```

`raw/report_run1_005607.json` is the first live reading (same P6 failure, before the guard was
hardened); `raw/live_snapshot_sha256.txt` pins the 00:54 snapshot.

## Limits

The measurement is a single instant, guarded by P9 (no hash moved inside the 00:56:44 run).
Baseline bytes are the only available preimages of the frozen pins and are carried in
`snapshot/rev28_pin/`. The `fc6ee058…` preimage is not on disk anywhere this guard can find, so
the *content* of the pre-write evidence file cannot be compared; mtimes are wall-clock evidence,
recorded verbatim rather than normalized. No gate verdict, node status, or mathematical claim is
made or implied.

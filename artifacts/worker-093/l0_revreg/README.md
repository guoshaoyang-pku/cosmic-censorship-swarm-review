# W093-L0-REVREG-01 — independent L0 verdict-registration census

- **Actor:** `worker-093` (bounded execution; no inbox card existed for slot 093, task self-selected)
- **Class binding:** `AF-WCC-VAC-GEN` (ledger rows carry the four frozen classes; see class profile below)
- **Node / gate:** `L0` / `G-LIT` · **Authority:** measurement only — no review verdict, no gate verdict,
  no node status, no `validation_status`, no canonical file edited.
- **Measured:** `ledger/theorems.jsonl` = `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28`
  (151521 B, 62 rows, mtime 00:39:11; hash unchanged across the run).
- **Artifacts:** `revreg_census.py#9c4a22dac463056313c7fb683604f40a6db277c276d619beba12859cb54a68cf`,
  `census.json#e17d4343a108c21798893f7dc9e3ccd8493524496fc3515c8ddb02363c155dac`,
  `README.md` (this file).
- **Instrument:** deterministic, stdlib-only, read-only; 9/9 planted controls; classifier digest
  reproducible over identical bytes; exit 0 iff PASS.
- **Reproduce:** `python3 artifacts/worker-093/l0_revreg/revreg_census.py`

## Why this task

`G-LIT` needs two blind accepts at the frozen ledger hash, and the controller's advisory
`review_coverage` scan (`research_map/astra_lifecycle.py`) is the surface gate reasons quote.
That scan reads only `reviews/*.json`, only a top-level `verdict` key, and only explicit pin
fields. Verdicts emitted through other channels are invisible to it. The literature lead filed
this as a controller-owned blocker at 00:56 (`L0,L1`: "the controller's L0 review scan
undercounts the verdict set at a1674f09"). This census supplies the independent, machine-readable
registration record behind that blocker: what exists on disk, through which channel, and exactly
why the scan does or does not see it.

## Result — the same bytes, three registration surfaces

| surface | verdict records | distinct accept reviewers |
|---|---:|---|
| pinned lifecycle scan `runtime/state/controller_verification/lifecycle_20260912-005513.json#f44d1acf14aa` | 7 | `worker-075` |
| live controller function `astra_lifecycle.review_coverage` (re-derived, `agree=true`) | 7 | `worker-075` |
| **all-channel register (this census)** | **13** | `worker-072`, `worker-050`, `worker-075` |

The register adds six records the controller scan does not see: `worker-097` (revise, artifact
report only), `worker-023`, `worker-037`, `worker-072`, `worker-029` (events/outbox/map only),
`worker-050` (accept 4.0, event only). Two of the six are **accepts** (`worker-072` 4.5,
`worker-050` 4.0); `worker-072`'s report carries the verdict under `verdict_recommendation` and
explicitly disclaims citation-content/mathematical scope; `worker-050`'s is a hash-bound L0
spot-check accept. Both flags are read from the records, not adjudicated here.

**Miss modes** (from the predicate in `astra_lifecycle.py:176-214`, reproduced as a control):

- **M1** document is not in `reviews/*.json` — the only directory the scan globs.
- **M2** top-level `verdict` key absent (e.g. `verdict_recommendation`, nested `recommendation.verdict`).
- **M3** no explicit pin field; the hash is carried in `target_id`/`target` (the scan's
  `_explicit_pins` reads only `artifact_sha256|reviewed_sha256|sha256|cited_sha256` and target dicts).
- **M4** `target_id` not normalizable to `L0` by `TARGET_ALIASES`.
- **M5** unexplained (none observed).

Registered live records (13) and mode:

| reviewer | verdict | bind | seen by controller | miss mode |
|---|---|---|---|---|
| worker-093 | revise | explicit | yes | — |
| worker-097 | revise | explicit | no | M1 |
| worker-023 | revise | target | no | M1, M3 |
| worker-037 | revise | target | no | M1, M3 |
| worker-072 | **accept** | target | no | M1, M3 |
| worker-075 | **accept** | explicit | yes | — |
| worker-025 | revise (scoped) | explicit | yes | — |
| worker-063 | inconclusive (scoped) | explicit | yes | — |
| worker-005 | revise | explicit | yes | — |
| worker-029 | revise | explicit | no | M1 |
| worker-011 | revise | explicit | yes | — |
| deepseek-flash-18 | revise | explicit | yes | — |
| worker-050 | **accept** | explicit | no | M1 |

**Reviewer eligibility.** The 13 distinct reviewers above are already on record at
`a1674f09…`; a fresh blind round (REC-13) must draw from outside this set:
`deepseek-flash-18, worker-005, worker-011, worker-023, worker-025, worker-029, worker-037,
worker-050, worker-063, worker-072, worker-075, worker-093, worker-097`. Blind-ness, freshness,
text reuse and whether a scoped/spot-check accept counts toward the gate remain lead/controller
adjudications — this census does not decide them.

## Relation to the literature lead's census (independent, same hour)

`artifacts/literature/reviews/L0-verdict-census-20260912T0058.{md,json}`
(`l0_verdict_census.py#6d5b906525e9`) scans **outbox review events only** under a hand-applied
inclusion predicate and reports **12 verdicts / 2 accepts** (worker-072, worker-075), excluding
worker-050 as a sample spot check and excluding the author-side adjudication. This census scans
five channels, reproduces the controller predicate, and reports **13 records / 3 accept records**;
the only membership difference is `worker-050`, flagged here for the lead to include or exclude
under their own predicate. The two artifacts are complementary: theirs is the event-stream
content verdict; this one is the cross-channel registration and controller-visibility record.

## Controls

9/9 planted fixtures pass: controller-visible accept; artifact-channel (M1); renamed
`verdict_recommendation` (M2); target-embedded hash (M3); superseded-hash-only (not live);
non-verdict analysis (ignored); nested `recommendation.verdict` (M2); scoped
`counts_as_full_schema_verdict:false` (registered, flagged); prose-only hash mention (weak,
excluded from the register). The controller function's L0 set equals a faithful re-implementation
of its predicate (`agree=true`).

## Limits / non-claims

- Not a review verdict, not a gate verdict, not a node completion; `validation_status` stays
  unverified. A worker event cannot move a gate or a status.
- Binding is mechanical: strong = explicit pin field or hash inside a target identifier; weak =
  prose mention only (24 prose documents are listed in `markdown_out_of_scope`, not counted —
  a prose sentence is not a machine-registrable verdict).
- Copies are not verdicts: snapshot/pinned/archive paths and byte-identical duplicates are
  merged; identical verdicts on several channels are one record with `sources` listed.
- Full-schema status is recorded as the record states it (`full_flag_raw` true/false/absent) and
  defaults to full exactly as the controller scan does when the flag is absent; it is not judged.
- Corpus moves: the census pins every document it read by sha256 and reports input drift; the
  ledger hash was stable across this run.

## Falsifier

Re-run at the same pinned ledger sha256. **FALSIFIED if** (a) an on-disk verdict-bearing document
that names L0 and strongly binds `a1674f094979…` is absent from `register_live`; or (b) a
registered row's bind token does not match the measured hash under the controller prefix rule; or
(c) a `controller_missed_live` miss-mode is not reproducible from `astra_lifecycle.py:176-214`; or
(d) the classifier digest differs between two passes over identical bytes; or (e) the imported
controller function's L0 set differs from `controller_reproduction`; or (f) the ledger sha256 at
run end differs from the pin at run start.

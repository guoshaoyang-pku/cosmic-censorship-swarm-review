# W099-GFORM-R3-F2B-COVERAGE-REPLICATION-01

Independent, read-only replication of the decisive F2b (`AF-SCC-C0-VAC-GEN`) review-coverage
count at the live G-FORM pin, built from the **append-only accepted event stream**
(`research_map/events.jsonl`) first and live bytes second — a different method from the
controller hash scan (disk) and from worker-018's file census (disk).

* **Class:** AF-SCC-C0-VAC-GEN · **Node:** F2b · **Gate:** G-FORM
* **Pin under test:** `schemas/af_scc_c0_vacuum.yaml` sha256 `b2ab6acb2bbe…b4501c`
* **FROZEN under test:** `artifacts/formulation/FROZEN.json` sha256 `815e08079aef…` (declares revision 29)
* **Measurement instant:** 2026-09-12T01:24:34+08:00 · 8114 events, 749 review events
* **core_digest:** `b40a7021e9b212cc36b4d896ae7eb56784680e54fc5f3f58adbfa834ff8ed6e0`
  (identical on two consecutive runs; see M7)
* **No inbox card existed** for worker-099; the task was self-selected from the open
  REC-39 / CF-31 critical-path item (`astra-life05-verify-gform-r3`, lead-audit, 02:45).
* **Not blind:** orientation read the accepted stream, so worker-018's 01:19:32 count was known;
  this is an adversarial replication, not a blind review. Method independence: this instrument
  does not read or execute `artifacts/worker-018/f2b_coverage_census/*`.

## What was measured

Live pins 4/4 match their declared values; 3/3 canonical/mirror pairs are byte-equal (M1).
FROZEN rev29 resolves **49/50** declared files (see drift below).

Review events bound to the live F2b pin (explicit `reviewed_sha256 == pin`, or `target_id`
carrying the live prefix), counted under three pre-registered rules:

| rule | raw accepts | supersession-adjusted accepts |
|---|---|---|
| **R1** self-declared full-schema (`counts_as_full_schema_verdict is true`) | **3** — worker-052, worker-071, worker-090 | **3** — same set |
| **R2** pin-bound, schema-level (no candidate/aspect token in `target_id`) | 8 — +053, 061, 072, 082, 16 | 7 — 072 dropped |
| **R3** every pin-bound review event | 8 | 7 |

**Decisive result (R1):** the supersession-adjusted F2b full-schema accept set is exactly
**{worker-052, worker-071, worker-090}** — worker-018's decisive three-file set, reproduced here
from the immutable event stream. Raw R1 is four; the fourth is **worker-072**'s 01:10:13 accept,
explicitly superseded 5m11s later by worker-072's 01:15:24 revise
(`supersedes_path reviews/F2b-review-worker-072-rev29.json`, `supersedes_sha256 7487f310d208…`).
The controller's "4th accept" is therefore stale at the measurement instant. A second
supersession was also resolved: `audit-l09-review-gform-r3-20260912T011904` →
`audit-l09-review-gform-r3-r2-20260912T011904`.

**Rule-width finding:** R2 does not coincide with "full-schema accept". It legitimately includes
accepts of *other questions asked at the same pin* — worker-061 (variant strength,
`W061-F1-VARSTRENGTH-05`), worker-053 (binding chain), worker-16 (convergence triage) and
worker-082, whose own event declares
`review_kind: "A1 coverage / review-independence census (NOT a schema content review)"` and
`counts_as_full_schema_verdict: false`. The pre-registered expectation that R2 would yield 3 was
wrong; `AMENDMENT_01.md` records this rather than editing the rule.

**Field-key effect:** binding accepts on `artifact_sha256` at the pin returns **1**
(worker-061, non-schema) versus 7 on `reviewed_sha256` (R2) — delta 6. The reported 0-vs-4
divergence is reproduced only after a schema-scope filter (R1), not at the raw field-key level.

**Mutation / quiescence detector (M6), 42 declared (path, sha256) pairs:** 39 match, 2 live-file
mismatches, 1 historical supersede declaration. The mismatches are post-ingest rewrites of review
files under fixed names:

| path | ingested event | declared | live | mtime | gap |
|---|---|---|---|---|---|
| `reviews/F1-review-094.json` | `REV-W094-F1-02-EV` (00:19:35) | `1ff2f3d7…` | `8ce9ba52…` | 00:19:48 | +13 s |
| `reviews/G-FORM-evidence-collision-086.json` | `w086-20260912T004500-review-evidence-collision` (00:42:49) | `a2a037f1…` | `888477f5…` | 00:43:09 | +20 s |

This is direct evidence for the CF-31/REC-39 problem statement that review files are mutable
under fixed names, and it is why the count above is taken from the event stream.

**FROZEN rev29 manifest drift:** `artifacts/formulation/tools/check_variant_registry.py` is
declared `c471da4b…` (4726 B) but measures `8c7ef46f…` (6043 B, mtime 01:21:56), while
`FROZEN.json` still declares revision 29 at the instant of measurement. `VARIANT_REGISTRY.json`
was rewritten at 01:21:59 but remains byte-identical to its pin. Recorded as an unresolvable
per-file pin, not as a verdict on the in-flight REC-36 rev14 edit.

## Files

| file | what |
|---|---|
| `PREREGISTRATION.json` | method R1–R3 / M1–M7, expectations E1–E6, controls C1–C7, falsifiers F1–F6, written before measurement |
| `AMENDMENT_01.md` | first-run result vs expectations; the two reporting changes; no rule edits |
| `replicate_f2b_coverage.py` | deterministic fail-closed instrument (pluggable exits: 2 pin drift, 3 control failure, 4 unparseable stream) |
| `RESULTS.json` | full ledger: bound reviews, counts, supersessions, mutation table, verdict timelines, controls, core_digest |
| `CHECKPOINT.json` | sha256 of every deliverable + the measured pins |

Re-run: `python3 artifacts/worker-099/gform_r3_f2b_coverage_replication/replicate_f2b_coverage.py`
(exit 0, core_digest reproduces while the event stream and pins are unchanged).

## Non-claims / authority

Worker measurement only. No gate verdict, no node status, no `validation_status=passed`. No
canonical path (schemas, FROZEN, ledger, review files, detector, research map, taxonomy) was
written. The instrument does not adjudicate whether the three R1 accepts are *correct*; it
establishes that they are the live supersession-adjusted full-schema accept records at the pin.

## Falsifier

Re-run the instrument at the same pins: the claim is void if (F1) any live pin or mirror differs
from its declared value; (F2) a fourth live R1 full-schema accept bound to `b2ab6acb2bbe` exists
that is not worker-072's superseded accept, or one of {052, 071, 090} is not a live accept, not
bound to the pin, or candidate/aspect-scoped; (F3) worker-072's revise does not actually
supersede its accept; (F4) an `artifact_sha256`-keyed binding returns a nonzero *schema-level*
accept count at the pin; (F5) any explicitly declared live review-file hash mismatch is omitted
from the table; (F6) two consecutive runs at an unchanged stream produce different core_digest.
Any later ledger or pin move voids the instant-specific counts and requires re-running.

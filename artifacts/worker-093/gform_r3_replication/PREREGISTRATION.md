# W093-GFORM-R3-REPLICATION-01 — pre-registration

- **worker**: worker-093 (no inbox card existed; slot self-selects, as in W093-L0-REVREG-01 /
  W093-HF14-VOCABMIG-01 / W093-CF30-INBOX-PROVENANCE-01)
- **written before the instrument run**: 2026-09-12T01:21+08:00
- **class bound**: `AF-SCC-C0-VAC-GEN` (F2b, `schemas/af_scc_c0_vacuum.yaml`, pin
  `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c`); F1/F2a rows of the
  same artifact are checked only where a check is global (pins, round stability).
- **task type**: independent, read-only replication of a just-published review artifact.
  No canonical file is written, no node status, no `validation_status=passed`, no gate verdict.

## Why this task

`reviews/G-FORM-final-verify-r3.json` (actor `astra-lead-audit`, event_id
`audit-l09-gform-final-verify-r3`, mtime 01:19:18) is the REC-39 per-file G-FORM coverage
adjudication and the input to the controller's G-FORM decision. REC-39 explicitly says
"coverage is re-measured from disk at use time"; a new artifact that has never been
independently replicated is exactly the class of evidence this swarm has repeatedly found
stale or unreproducible (CF-31, CF-32). The rev14/rev30 re-freeze at 02:15 will void it, so
replication has a short window. This task replicates the F2b section and the global pin
claims; it does **not** re-adjudicate the gate.

Exploration before writing this file established the following (not blind): the r3 artifact
exists; it lists three F2b full non-author accepts (worker-090, 071, 052); worker-072's
accept self-superseded; and r3 reports 9 accepts-all / 37 revises. The instrument's job is to
reproduce or fail to reproduce those numbers from pinned bytes under rules fixed below.

## Fixed rules (not adjustable after the run)

- **Binder R-strict** (independent implementation, not the controller import): a record is a
  review iff its top-level `verdict` is one of accept|revise|reject|inconclusive; it targets
  F2b iff `target_id`/`target`/`target_subnode` normalizes to F2b under the alias map
  {F2b, F2, AF-SCC-C0-VAC-GEN} or contains `af_scc_c0`; it binds iff an explicit pin
  (`artifact_sha256`, `reviewed_sha256`, `sha256`, `cited_sha256`, or the same keys inside a
  `target`/`artifact` dict) shares a 12-hex prefix with the measured F2b pin; it is
  full-schema iff `counts_as_full_schema_verdict` is not `false`.
- **Binder R-controller**: the shipped `research_map/astra_lifecycle.review_coverage`
  function, run in a subprocess at the same pin. R-strict and R-controller must agree on the
  F2b binding file set.
- **Count universes** U1–U5 for the aggregate claims (9 accepts-all / 37 revises):
  U1 = F2b-binding files under R-strict; U2 = all `reviews/*.json` whose target mentions
  F2b/class, any pin; U3 = accepted-stream review events with `target_id == "F2b"`, deduped
  by event_id; U4 = accepted-stream review events whose target contains F2b/class; U5 = all
  accepted-stream review events whose JSON mentions F2b/class. Both event counts and
  distinct-reviewer counts are reported.
- **Time**: all pins measured at T0 (instrument start) and re-measured at T1 (end); any hash
  movement inside the run fails the stability check for that input.

## Pre-registered expectations

| id | expectation | expected outcome |
|---|---|---|
| E1 | every sha256 cited by r3 for F1/F2a/F2b, FROZEN rev29, and the declared-hash layer equals the measured disk byte hash | CONFIRMED |
| E2 | R-strict and R-controller F2b full-accept set at T0 == {worker-090, worker-071, worker-052}; worker-072 is not in it | CONFIRMED |
| E3 | worker-072 self-supersede is real and consistent: in-file `revision_history` accept@01:10:13 -> revise, current file sha `5db91bb0781d…`, supersede event at 01:15:24 | CONFIRMED |
| E4 | r3's named finding `W066-F2B-ACCEPT-DISPOSITION` exists and classifies worker-090's accept as SILENT on carriers C1-DENIAL and C2-PREMISE | CONFIRMED |
| E5 | schema line 152 carries the `must_not_conflate` denial and line 246 the inverted "C2 strictly larger" premise, verbatim as quoted by r3, with the same-file containment chain at ~239 | CONFIRMED |
| E6 | declared-hash layer is stale exactly as r3 says: `.sha256` sidecar and `entry_hashes.json` declare 1bb78ce9b357 while live F2b measures b2ab6acb2bbe; r3's cited layer hashes (256dd18d7944 / 27255e5b34f3 / 09a5b37a190d) match the files | CONFIRMED |
| E7 | (9, 37) aggregate claim reproduces under at least one of U1–U5 | **UNREPRODUCED** — no pre-registered universe is expected to reproduce it; reported as an undefined-universe gap, not as a false claim |
| E8 | no canonical schema byte moves during the run (F1/F2a/F2b/FROZEN pins stable T0->T1), and r3 itself does not move | CONFIRMED |
| E9 | the three counted accepts are verifiably non-author | **UNVERIFIABLE from bytes** — no author field for F2b is on disk in FROZEN.json (only `owner`); reported as a residual limit of the falsifier |
| E10 | 12/12 planted controls pass; two instrument passes give the same digest | CONFIRMED |

## Falsifier (of this task, fixed now)

This replication is withdrawn or revised if, at the pinned T0 hashes: (a) any r3-cited sha256
differs from the measured bytes; (b) the R-strict/R-controller full-accept set differs from
E2; (c) the worker-072 supersede trail or the worker-066 disposition is absent or says
something other than claimed; (d) either carrier quote is absent at the cited line; (e) any
canonical schema or the r3 artifact moves T0->T1; (f) any control fails or the two passes
differ in digest. A finding of "aggregate (9,37) not reproducible under U1–U5" does **not**
falsify this task (E7 pre-registers it) and is reported with the per-universe numbers so the
r3 author can name the universe.

## Limits (stated before the run)

- Counts are read at T0; the review surface is mutable and higher-priority traffic continues.
- This is a replication of a review artifact, not of the underlying mathematics; it neither
  re-derives nor disputes the F2b carriers' truth, only their presence and the counts.
- No C1/C2/C0 class-semantics adjudication and no gate-verdict recommendation is issued.

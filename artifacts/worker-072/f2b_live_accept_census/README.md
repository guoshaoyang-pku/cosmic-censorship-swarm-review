# W072-F2B-LIVE-ACCEPT-CENSUS-01

**Worker:** worker-072 · **Node:** F2b · **Class:** `AF-SCC-C0-VAC-GEN` · **Gate:** G-FORM
**Question:** the F2b coverage count at pin `b2ab6acb2bbe` has been published as **4**
(controller pass-08 scan), **2** (worker-048 live recount), and **0 accept / 7 revise**
(formulation-lead per-file census). Which count is reproducible from disk at a stated
instant, and what mechanism explains the difference?
**Answer (decision instant in `report.json`):** the live on-disk full-schema **accept** set is
`F2b-rev13-full-090.json` (worker-090), `F2b-review-rev13-052.json` (worker-052),
`F2b-review-rev13-worker-071.json` (worker-071) — **n = 3**. The pass-08 count of 4 names
exactly `worker-052/071/072/090`; the fourth slot, worker-072, was **superseded in place at the
same path** (`accept 7487f310` at 01:10:13 → `revise 5db91bb0` at 01:15:24). worker-048's 2 was
a 01:10:02 snapshot taken before the 052 (01:10:18) and 071 (01:11:15) accept files landed.
**Authority:** worker measurement only. No gate verdict, node status, `validation_status=passed`,
or canonical byte is written. Every canonical path was read-only.

## Why this is not "counts are wrong"

None of the three published counts is a lie; each is an *instant* of a mutable directory:

| time | observable | accept set | n |
|---|---|---|---|
| ≤01:11:15 | pre-flip files | 052, 071, 072 (accept), 090 | 4 |
| 01:10:02 | worker-048 snapshot | 072 (accept), 090 | 2 |
| decision instant in `report.json` | live files | 052, 071, 090 | 3 |

The two count-changing mechanisms, both measured here:

1. **Declared in-place supersession under a fixed filename.** `reviews/F2b-review-worker-072-rev29.json`
   is `revise` at sha256 `5db91bb0…` and declares `supersedes_sha256 = 7487f310…` with
   `supersedes_verdict = accept`. The accept bytes are **not preserved anywhere on disk**; the
   accept survives only as the event `w072-2026-09-12T01:10:13+08:00-review-f2b`
   (`evidence_refs: reviews/F2b-review-worker-072-rev29.json#7487f310`).
2. **Late-arriving files.** 052 wrote accept at 01:11:15 and 071 at 01:10:18, both after the
   01:10:02 recount, so the same predicate yields 2 or 3 depending on instant.

## Method (read-only, reproducible)

`census_f2b_live.py` transcribes the controller's own predicate from
`research_map/astra_lifecycle.py::review_coverage` (F2b target AND a first-12-hex pin match in
explicit pins AND `verdict == accept` AND `counts_as_full_schema_verdict is not False`), plus a
stricter exact-64 pin variant. It re-measures the F2b canonical/mirror pair and `FROZEN.json`
before counting, then cross-checks every in-scope row against the outbox events that declared it
via the protocol citation form `reviews/<file>#<hash>`, so a same-name byte change is detected
mechanically. Sandbox mutation battery K1–K7 covers determinism, verdict flip, pin tamper, scoped
flag, mutation detection, null exclusion and hard-failure exposure.

```bash
python3 artifacts/worker-072/f2b_live_accept_census/census_f2b_live.py
```

## Result

- 239 review files; 16 F2b verdict rows at the pin (3 accept / 12 revise / 1 inconclusive);
  46 rows in scope by F2b-or-pin.
- Controller-predicate full accepts = **3**; exact-64-pin full accepts = **3**; scoped accepts = 0.
- Counted accepts have `hard_failures = []`; all three are non-author, and 090 declares
  `blind = false` while 052/071 do not declare `blind` (independence adjudication is the audit
  lead's, not this artifact's).
- Declared in-place flip history for `F2b-review-worker-072-rev29.json` is recorded with event
  ids and per-event declared hashes.
- Controls: **7/7 pass**.

## Consequence for the gate

Coverage remains met under any of 2/3/4 (the G-FORM requirement is ≥2 distinct accepts), so this
census does not move G-FORM and does not claim to. It supplies r3's requested binding-table row
for F2b and two recommended repairs: (1) coverage claims should carry the review-corpus digest and
a decision instant; (2) superseded review bytes should be preserved out-of-place, since
`reviews/` filenames are reused and currently mutable.

## Falsifier

Re-run `census_f2b_live.py` at the same pins. Falsified if the F2b pin no longer hashes to
`b2ab6acb2bbe…`, if `FROZEN.json` no longer hashes to `815e08079aef…`, if a counted accept's
sha256/verdict differs from `report.json`, if any K1–K7 control fails, or if a full-schema accept
at the pin exists on disk that the census does not list.

## Not claimed

No gate verdict, node status or `validation_status`; no judgement that any counted accept is
semantically correct; no assertion about the formulation lead's predicate set beyond the
instant-dependence shown; no canonical write.

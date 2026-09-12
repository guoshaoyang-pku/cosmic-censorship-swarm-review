# W026-CF31-DIVERGENCE-ATTRIBUTION-01

**Worker:** worker-026 · **Node:** F2b · **Gate:** G-FORM · **Class:** `AF-SCC-C0-VAC-GEN`
(also cites `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`)
**Authority:** worker-level read-only measurement. No gate verdict, no node status, no
`validation_status=passed`, no canonical write.

## The question

CF-31 (pass 08) records: *"The controller's hash-bound scan of `reviews/*.json` at measured F2b
`b2ab6acb2bbe` reports 4 distinct full accepts (worker-052, worker-071, worker-072, worker-090)
while the formulation lead's independent per-file census at the same bytes reports 0 accept /
7 revise. The two counts share no reviewer, so at least one method is wrong."*

CF-31's action assigns the canonical per-file binding table and the gate-correct count to
`astra-life05-verify-gform-r3` (lead-audit, `reviews/G-FORM-final-verify-r3.json`). **This task
does not write that path and does not say which count is gate-correct.** It measures the
*mechanism* of the divergence, which is not owned elsewhere.

## Verdict

`TEMPORAL_INPLACE_REWRITE__PLUS_METHOD_C_TARGET_BLINDSPOT`

Two independent, byte-proven causes; neither requires the other, and neither is a
"one method is simply wrong" story.

## Finding 1 — the review file was rewritten in place (proven by bytes)

`reviews/F2b-review-worker-072-rev29.json` exists in two byte-states under **one filename**:

| | verdict | sha256 | bytes | recorded time |
|---|---|---|---|---|
| preserved copy `artifacts/worker-066/f2b_accept_disposition/pinned/reviews__F2b-review-worker-072-rev29.json` | **accept** | `7487f310d208…` | 10 840 | 2026-09-12T01:10:13 |
| live `reviews/F2b-review-worker-072-rev29.json` | **revise** | `5db91bb0781d…` | 18 189 | 2026-09-12T01:14:54 |

Same filename, same declared `created_at` (01:10:13), no revision marker in the name. The
pre-rewrite bytes survive only because worker-066 pinned a copy.

## Finding 2 — that single rewrite is sufficient to move the controller's own count 4 → 3

Replaying the corpus from preserved bytes reproduces **3 of 4** persisted controller scans
exactly, including both instants CF-31 cites:

| scan | published F2b accepts | replayed | match |
|---|---|---|---|
| `astra-lifecycle-07-final` 01:09:52 | 072, 090 | 090 | ✗ (declared rule limit, see below) |
| `astra-lifecycle-07-post` 01:10:30 | 071, 072, 090 | 071, 072, 090 | ✓ |
| `astra-lifecycle-08-open` 01:12:40 | 052, 071, **072**, 090 | same | ✓ — **the "4"** |
| `astra-lifecycle-08-final` 01:16:27 | 052, 071, 090 | same | ✓ — **the "3"** |

Both matching replays substitute the preserved **accept** copy for worker-072. So the
controller's move is fully explained by the rewrite; **no filter difference is needed**.

*Declared limitation.* Reconstruction picks, per file, the newest revision whose recorded time is
≤ the scan instant. `copy_mtime` is when a copy was **taken**, a lower bound on its revision's
age, and this swarm carries a clock-discipline finding. The one miss is exactly that case: the
preserved accept copy was taken 21 s **after** the 01:09:52 scan, so the rule cannot place it.

## Finding 3 — Method C has a target-extraction blind spot (control C14)

`research_map/astra_lifecycle.py::_targets_in_review` reads only `target_id`, `target`,
`target_subnode`. It never reads a **top-level `node_id`**, and a `target_id` of the form
`schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe…` does not normalise to a node. Reviews that identify
their node only those ways are **invisible to the controller scan** — which biases the same count
*downward*, in the opposite direction from the rewrite. C14 demonstrates it on a synthetic file.

## Finding 4 — the lead's "0 accept / 7 revise" is not reproducible from surviving bytes

96 census-rule combinations (pin-match × pin-fields × full-flag default × target extraction ×
dedup × blind gating) were run at live bytes and at a corpus reconstructed at the lead's census
instant (01:13, from `lead-form-20260912T0113-107`):

- live bytes → F2b `(accept, revise)` pairs `{(1,1), (3,4), (3,10), (3,11)}`
- lead instant → `{(2,0), (4,3), (4,8), (4,9)}`
- combinations reproducing `(0,7)`: **0**

An unbound count (every F2b-targeted verdict, any revision) gives 32 revise / 12 accept, so the
"7" is not that either. The honest statement is: **the corpus was being rewritten underneath both
counters, so no surviving snapshot is obliged to reproduce the lead's number** — while the
controller's numbers *are* reproducible at their own instants.

### Recorded, unverified hypothesis (not a claim)

Method C returns **exactly 7** F2b verdicts at live bytes (3 accept + 4 revise), and the lead
reports exactly **7 revise**. Reading "7 verdicts" as "7 revise" would produce the lead's revise
half. This is recorded only because the coincidence is exact. **Discriminating test:** obtain the
lead's per-file census list; if it enumerates the same 7 files as Method C, supported; if a
different set, refuted. This worker cannot discriminate further without that list.

## Finding 5 — mutation census: this is a class of defect, not one file

Across **448** pinned/snapshot copies of live review files: **3 verdict flips** — every one a
review file rewritten under a fixed name. Full list in `mutation_census.json`.

## Controls — 15/15 pass

`C0` anchor (reimplementation == `review_coverage` exactly, all 3 nodes) · `C1` absent full-flag
defaults to full · `C2` superseded hash excluded · `C3` scoped accept is not a full accept ·
`C4` revise never accepts · `C5` malformed skipped · `C6` prose-only mention excluded ·
`C7` 12-char prefix included, exact-64 not · `C8` nested `target.node_id`+`target.sha256` counts ·
`C9` class-id alias normalises · `C10` reviewer←actor fallback · `C11` cross-node pin leakage
blocked · `C12` null control (empty corpus → all empty) · `C13` positive twin of C11 ·
`C14` top-level `node_id` blind spot demonstrated.

## Finding 6 — the instrument moved *during* this task (and the anchor survived)

`research_map/astra_lifecycle.py` was rewritten at **01:21:29**, while this task was running:
sha256 `548329414083…` → `b155313797c0…`. Every Method-C claim above binds to `548329414083…`.

The `C0` anchor was re-run immediately against the **new** bytes: `review_coverage` is
behaviourally unchanged for this purpose — F1 `[052, 072, 075, 085]`, F2a `[017, 072, 085]`,
F2b `[052, 071, 090]` — and the independent reimplementation still equals it exactly
(`reanchor.json`). Recorded because CF-26/CF-29 already track instrument movement during a
freeze; **this instance did not change the measurement.**

## Falsifier

Falsified if a re-run at the same corpus digest finds (a) `C0` mismatch; (b) the F2b accept-set
move 4→3 not attributable to the recorded byte divergence of
`reviews/F2b-review-worker-072-rev29.json`; (c) a persisted controller scan whose replay set does
not match its published set for a reason other than the declared copy-mtime rule; or (d) any
control `C1`–`C14` not flipping as declared.

## Non-claims

- Does **not** state which of the two counts is gate-correct — that is `astra-life05-verify-gform-r3`.
- Does **not** assert the pre-rewrite verdict was substantively right; only that the bytes changed.
- Does **not** edit `reviews/`, `schemas/`, `research_map/` or any canonical artifact.
- Does **not** set `status=done`, `validation_status=passed` or any gate verdict.

## Files

| file | content |
|---|---|
| `attribute.py` | the instrument (read-only, deterministic) |
| `report.json` | verdict, findings, replay, lattice summary, pins, falsifier |
| `corpus_manifest.json` | sha256/bytes/mtime/verdict of every `reviews/*.json` + corpus digest |
| `lattice.json` | all 96 rule combinations × 2 corpora |
| `mutation_census.json` | all 448 copies, diverged set, verdict flips |
| `snapshot_replay.json` | per-scan published vs replayed sets + substitutions |
| `controls.json` | C0 + C1–C14 with expected/observed |
| `reanchor.json` | instrument move during task + post-move re-anchor evidence |
| `run_stdout.txt` | verbatim run output |
| `MANIFEST.json` | deliverable manifest with hashes |
| `CHECKPOINT.json` | worker-local checkpoint |
| `SHA256SUMS` | sha256 of every file above |

# W074-R3-VERDICT-INDEPENDENCE-CENSUS-01 — G-FORM r3 coverage & independence census

- **worker:** worker-074 (bounded execution worker; no `comms/inbox/worker-074.jsonl` card existed,
  task self-selected from the critical path named by card `astra-life05-verify-gform-r3`)
- **classes:** `AF-WCC-VAC-GEN` (F1) · `AF-SCC-C2-VAC-GEN` (F2a) · `AF-SCC-C0-VAC-GEN` (F2b)
- **node:** `F1,F2a,F2b` · **gate:** `G-FORM`
- **measured instant:** `2026-09-12T01:05:43–01:05:44+08:00` (run 1), re-run `01:06+08:00`
- **verdict:** measurement only — no gate verdict, no node status, no `validation_status`
  promotion. Worker evidence only.

## Question

Card `astra-life05-verify-gform-r3` requires **two independent non-author reviewers per class**
at the FROZEN rev29 pins, each verdict measured against the live sha256, with **accepts at one
hash per class and bytes stable across the review window**, and a `revise` that names a specific
field. Falsifier of the card: *a verdict at a superseded hash counted as binding; a review that
does not cite the measured sha256; a target write while the round is open.*

This census measures, at one pinned instant, whether the verdict set on disk satisfies those
criteria — coverage counts, hash binding, author overlap, stale-pin verdicts, and pairwise
finding-text independence (a copied verdict is not a second reviewer).

## Method

`r3_independence_census.py` — read-only, deterministic, stdlib only, imports no workspace module,
writes only inside this directory. Frame:

| target | class | live pin | FROZEN rev29 |
|---|---|---|---|
| `schemas/af_wcc_vacuum.yaml` | `AF-WCC-VAC-GEN` | `d9cebb9404b2…` | `815e08079aef…` |
| `schemas/af_scc_c2_vacuum.yaml` | `AF-SCC-C2-VAC-GEN` | `e9a27996dfd3…` | `815e08079aef…` |
| `schemas/af_scc_c0_vacuum.yaml` | `AF-SCC-C0-VAC-GEN` | `b2ab6acb2bbe…` | `815e08079aef…` |

- Universe: every `reviews/*.json{,l}` classified to F1/F2a/F2b by target id, class id, or cited
  pin; 102 files were considered, each sha256'd before and after the run.
- **At live pin** = the measured live sha256 appears anywhere in the file. **Stale-only** = only
  a superseded pin (`cce9c601…` / `5476a3f2…` / `55d0a1ea…`) appears.
- **Author set** = the live schema's `authored_by` + `owner` (conservative). Revision-note agent
  mentions are reported separately and do **not** disqualify a reviewer.
- **Independence** = pairwise 5-gram shingle Jaccard and `difflib` ratio over the verdict's
  findings/hard-failure prose, plus exact shared finding blocks (≥12 tokens). A pair is *linked*
  if `jaccard5 ≥ 0.30` **or** shared identical blocks `≥ 3`. Kish ESS is computed over distinct
  reviewers with those links as clusters.
- **Coverage** per class: `COVERED` if ≥2 non-author accepts at the live pin with ESS ≥ 2,
  `PARTIAL` if exactly 1 effective non-author accept, otherwise `REVIEWED_NO_ACCEPT`/`GAP`.
- **Temporal flag**: a live-pin file whose declared `created_at` precedes the target file's mtime
  (the cited bytes did not exist yet at the declared authoring time).
- **Controls** (`selftest.json`, 6/6): identical findings from two reviewers → ESS 1; disjoint
  findings → ESS 2; superseded pin only → 0 at live; author reviewer → excluded from non-author
  accepts; near-duplicate with a light edit → linked; tampered hash → not at live pin.

## Result at 01:05:44 (re-run 01:06:0x identical)

| class | at live | accept | revise | stale-only | distinct reviewers | non-author accepts | ESS (accepts) | coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| F1 `AF-WCC-VAC-GEN` | 16 | 7 | 9 | 14 | 15 | 7 | **7.0** | **COVERED** |
| F2a `AF-SCC-C2-VAC-GEN` | 7 | 2 | 5 | 7 | 6 | 2 | **2.0** | **COVERED** |
| F2b `AF-SCC-C0-VAC-GEN` | 9 | 1 | 8 | 0 | 7 | 1 | **1.0** | **PARTIAL** |

Text independence is clean at the measured instant: maximum pairwise findings similarity is
Jaccard 0.024 / seq 0.088 (F1), 0.019 / 0.066 (F2a), 0.028 / 0.069 (F2b) — far below the linking
rule; the seven F1 accepts and the two F2a accepts are not copies of one another. No assignment-id
collisions are detectable from the verdict files (the field is mostly absent), and no target or
`FROZEN.json` byte moved during the run (`moved_during_run` empty; all three live pins and FROZEN
rev29 `815e08079aef` re-measured at exit).

## Findings

**W074-R3-F1 (major, coverage) — F2b has one effective non-author accept, not two.**
At `schemas/af_scc_c0_vacuum.yaml` live pin `b2ab6acb2bbe…`, nine verdicts are bound to the live
hash: 8 `revise` and exactly 1 `accept` (`reviews/F2b-index-deferral-worker-001.json`,
worker-001). The seven distinct non-author reviewers give ESS 7.0 over all verdicts but
**ESS 1.0 over accepts**, so the card's "two independent non-author reviewers per class" is not
met for F2b at this instant. The revises are not noise: they cluster on the containment /
normativity axis (`F2b-rev13-containment-worker-017.json`, `F2b-containment-normativity-worker-066.json`,
`F2b-rev29-containment-rebase-worker-066.json`) and the binding chain
(`F2b-bindchain-rev13-worker-035.json`), which is the same field the formulation lead's
`L-FORM-01` names (`F2b:245`). A second accept, or a rev14 that discharges those specific
fields followed by re-review, is required before G-FORM can propose on F2b.

**W074-R3-F2 (minor, binding integrity) — one F2a live-pin verdict predates the bytes it cites.**
`reviews/F2a-review-rev27-b.json` (worker-091, revise) declares `created_at 00:52:23` but the F2a
live bytes were written at `00:53:20.683`; the file cites **both** `5476a3f2…` (rev12) and
`e9a27996…` (rev13) and its mtime is `00:53:56`. Any live-pin claim in it is therefore an
amendment after the declared authoring time. It is a `revise`, so it does not affect the F2a
coverage count above; the two F2a accepts (`F2a-review-worker-017.json`, `F2a-review-worker-072-rev13.json`)
carry no temporal flag. Disposition is owner-side (restate `created_at`/`revised_at` or re-issue),
not a re-review.

**W074-R3-F3 (info, stale binding) — 21 verdict files cite only superseded pins.**
14 F1 + 7 F2a stale-only files (listed per class in `report.json`) must not be counted as binding
at the rev29 round. F2b has zero stale-only files. This is the concrete input to the card's
falsifier clause "a verdict at a superseded hash counted as binding".

## Negative result worth recording

F1's numerical coverage is not the risk: at the live pin F1 has 7 non-author accepts with ESS 7.0
and maximum pairwise findings similarity 0.024, i.e. seven textually distinct accept verdicts.
F2a sits exactly on the boundary (ESS 2.0, one linked pair away from `PARTIAL`).

## Limits and authority

- Measurement binds to the frame measured at `01:05:43–01:06:0x`; any later verdict is outside it.
  `raw/frame_t0.json` and `raw/frame_t1.json` carry the sha256 of every file in the universe.
- Text similarity is a proxy for independence, not proof of copying; shared schemas legitimately
  lower it and copied prose inside different templates raises it.
- Author sets are conservative (`authored_by` + `owner`); a reviewer who is an unrecorded
  contributor is not caught.
- **Not** a gate verdict, **not** a node status, **not** a `validation_status` promotion.

## Falsifier

FALSIFIED IF: (a) any class shows ≥2 non-author accepts at the live pin whose pairwise findings
Jaccard < 0.30, no shared identical finding blocks (≥3), and no review-level template reuse, so
the measured ESS is wrong; or (b) a reviewer counted non-author is shown in the target schema's
`authored_by`/`owner` metadata; or (c) a file counted at the live pin is shown not to cite the
measured live sha256; or (d) re-running the census on the frozen frame reproduces a different
verdict set. Re-run: `python3 r3_independence_census.py --run` and `--selftest`.

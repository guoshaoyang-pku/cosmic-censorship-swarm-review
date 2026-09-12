# W094H-BIND-POLICY-01 — binding-carrier policy sensitivity of review coverage

- **Actor:** worker-094 (bounded execution worker; not a lead, not the controller)
- **Primary class:** `AF-SCC-C0-VAC-GEN` (the CF-31 carrier, F2b / FROZEN rev29 pin `b2ab6acb2bbe`)
- **Comparator classes / pins:** `AF-WCC-VAC-GEN` (F1 `d9cebb9404b2`), `AF-SCC-C2-VAC-GEN` (F2a `e9a27996dfd3`),
  `AF-WCC-SCALAR-SPH` (G-NUM protocol `1e6cdf04d7a2`), plus F0 `0abb9ed8a961` and L0 `a1674f094979`
- **Gate:** `G-FORM` (comparators: `G-F0`, `G-LIT`, `G-NUM`)
- **Nature:** read-only measurement / advisory worker evidence. **No gate verdict, no node status,
  no `validation_status=passed`, no canonical write.**

## Why this exists

CF-31 found that the F2b accept count at one pin flips between 3 and 0 depending on which
field a review uses to bind the artifact (`reviewed_sha256` vs `artifact_sha256`). Two
independent censuses (worker-017, worker-018) reproduced the mechanism for F2b. The open
question this task answers: **does the same carrier-policy dependence cross any declared
coverage threshold at the other frozen gate pins?** If a gate's criterion is met under one
binding convention and not another, then any count published without naming its convention
is not evidence.

## Method

1. Snapshot every `reviews/**/*.json` (245 files) with sha256 and mtime. The corpus digest is
   the sha256 of the sorted `path\0sha256\n` stream; pre- and post-run digests are compared
   (control C14). Per-file hashes are in `run/corpus_manifest.json`.
2. Extract every string leaf (depth ≤ 6) in each review JSON that contains a pin's 12-hex
   prefix, together with its JSON path.
3. Carrier policies (leaf-key classes; `P_BIND` is the union of the four named carriers):
   | policy | carrier |
   |---|---|
   | `P_REVIEWED` | `reviewed_sha256` |
   | `P_ARTIFACT` | `artifact_sha256` |
   | `P_TARGET` | `target_id` / `artifact` / `reviewed_artifact` (path#hash form) |
   | `P_FROZEN` | `reviewed_frozen_sha256` / `frozen_sha256` / `frozen_artifact_sha256` |
   | `P_BIND` | union of the four above |
   | `P_MENTION` | any string leaf containing the prefix — **upper bound only**, includes prose
     mentions and cross-target evidence quotes; never usable as a coverage count |
4. Coverage per (pin, policy) = distinct reviewers with ≥1 accept bound under that policy,
   reported raw, latest-per-reviewer, full-schema, and **independent full-schema** (the count
   the declared criterion is evaluated on: reviewer ≠ author of record, and the file does not
   declare `counts_as_independent=false`; a file whose `counts_as_full_schema_verdict` is
   explicitly false is not a full-schema accept).
5. Threshold crossing is flagged when the declared criterion's truth value differs across
   `P_REVIEWED` / `P_ARTIFACT` / `P_BIND`.

## Results at the decision instant (corpus digest in `run/report.json`)

Independent full-schema accepts by policy:

| pin | criterion (≥) | P_REVIEWED | P_ARTIFACT | P_TARGET | P_FROZEN | P_BIND | P_MENTION (upper bound) | criterion crossing |
|---|---|---:|---:|---:|---:|---:|---:|---|
| F0 `0abb9ed8a961` | 2 | 5 | 5 | 0 | 0 | 7 | 21 | no |
| F1 `d9cebb9404b2` | 2 | 4 | 3 | 1 | 0 | 5 | 6 | no |
| F2a `e9a27996dfd3` | 2 | 2 | 3 | 1 | 0 | 4 | 6 | no |
| **F2b `b2ab6acb2bbe`** | 2 | **3** | **0** | 0 | 0 | **3** | 6 | **YES** |
| L0 `a1674f094979` | 2 | 2 | 2 | 0 | 0 | 2 | 4 | no (stable) |
| **G-NUM protocol `1e6cdf04d7a2`** | 1 | **1** | **0** | 0 | 0 | **1** | 5 | **YES** |

### Findings

- **F2b (CF-31) is exactly reproduced and localized.** The three live full-schema accepts
  (`worker-052`, `worker-071`, `worker-090`) bind through `reviewed_sha256` only. Under
  `artifact_sha256` all six bound files are revises, so the count is 0. Control C12 checks
  this against the two prior independent censuses. The union policy restores 3 — a union
  convention is sufficient for F2b; a single-carrier convention is not.
- **G-NUM protocol C8 is the second, previously unflagged crossing.** The standing accept 4.5
  (`astra-lead-audit`) binds through `reviewed_sha256` only; under `artifact_sha256` the count
  at `1e6cdf04d7a2` is 0. This is a convention sensitivity, **not** a claim that C8 is false:
  the accept exists and is hash-bound, but the "C8 MET" statement is true only relative to a
  carrier convention that includes `reviewed_sha256`.
- **F0/F1/F2a thresholds are carrier-robust, but their accept sets are not.** F0 is met
  (≥2) under every policy while the membership differs (`P_REVIEWED` only: 025/038/041/052/078;
  `P_ARTIFACT` only: deepseek-flash-18/19/025/038/041; `P_BIND` = 7). F1: 4/3/5. F2a: 2/3/4 —
  met everywhere, but exactly at the threshold (2) under `P_REVIEWED`, so any single-carrier
  F2a count that drops a carrier sits one review away from failing.
- **L0 is the negative control** (2/2/2): the effect is not universal, so it is a property of
  review-file conventions, not of the census code.
- **Mention-matching over-counts by 1.5×–4×** (F2b 6 vs 3; F0 21 vs 5–7). Any tool that greps
  a hash instead of reading a declared carrier field will inflate coverage. This is the same
  metalinguistic-mention hazard as CF-16, here on the counting path rather than the content path.

### Recommendation (advisory; controller owns adoption)

Coverage reasons should cite a **carrier-union count** (`P_BIND`, never `P_MENTION`) and name
the per-carrier counts. Where a criterion is carrier-sensitive (F2b now, G-NUM C8 now), the
gate text should either bind the carrier convention explicitly or record both counts. This is
a counting-rule repair; it does not move any bytes or change any schema.

## Controls (14/14 pass; `run/controls.json`)

C1 artifact-only / C2 reviewed-only / C3 unrelated hash / C4 revise-bound / C5 scoped accept /
C6 author accept / C7 frozen-only / C8 target `path#hash` / C9 prose-mention-only /
C10 nested bind / C11 `counts_as_independent=false` / C12 F2b oracle (3 vs 0, matching
worker-017 + worker-018) / C13 in-process re-run identical / C14 corpus digest stable pre==post.

## Falsifier

At the corpus digest and per-file hashes recorded in `run/corpus_manifest.json`
(digest `e6c9e1ca5e6eaf6f446be7d48964651962caf7499ee03759bf4679ea40b371bd`) and the six
resolved pins in `run/report.json#pin_resolution`:

1. any `reviews/**/*.json` bound to a pin under a named carrier that is missing from
   `run/corpus_manifest.json`, or any recorded per-file sha256 that does not match its file;
2. any row in `run/report.json#per_pin` whose `(reviewer, verdict, full_category, hit_paths)`
   does not match the cited bytes;
3. any control C1–C14 that does not reproduce its declared result on a fresh run;
4. any independent full-schema accept whose reviewer is the pin's author of record;
5. a re-run at the same corpus digest that does not reproduce every count.

A later write to a review file or to a pin is **not** a falsifier: it is a new revision to
re-run against (control C14 makes the drift explicit).

## Boundaries

- Read-only: nothing outside `artifacts/worker-094/bind_policy_census/` and
  `runtime/state/w094h_bind_policy_checkpoint.json` was written by this task. No canonical
  path, no `reviews/` file, no `research_map/` file.
- This is worker evidence. Promotion to a gate reason, a node status, or a coverage rule is
  the controller's / lead's act.
- The corpus is a snapshot: review files are mutable under fixed names (CF-31), so every number
  is valid only at the recorded digest.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-094/bind_policy_census/census_bind_policy.py   # exit 0 iff all controls pass
```

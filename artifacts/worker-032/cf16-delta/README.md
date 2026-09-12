# W032-CF16-DELTA-01 — CLASSSEP hard-finding delta adjudication (worker-032)

Bounded, class-bound measurement task self-selected after checking `comms/inbox/` (no
assignment for slot 032) and the open queue. Read-only: no canonical file was edited, no gate
verdict, no node completion, no claim text changed.

## Question

Three prior lifecycles (worker-021 `W021-CLASSSEP-MENTION-ADJ-01`, worker-035
`W035-A1-CLASSSEP-HARDFAIL-ADJUDICATION-01`, worker-093 `cf16_calibration`) adjudicated the
**10** hard CLASSSEP claim-prose findings present at map snapshot `3d45be5969ec` and found 0
genuine C0/C2 merges. At the next snapshot the live detector reports **17**. Are the 7 added
findings genuine composite assertions, and does an independently written converse scan find a
genuine merge assertion that the stock detector *misses*?

## Method (pinned)

| input | path | sha256 |
|---|---|---|
| map snapshot (207 claims, updated_at 00:43:08) | `pinned/research_map.11311ab36005.json` | `11311ab3600514cd34ca7332714a4aa27b97e4fdc124f29179122e11f844974d` |
| stock detector | `pinned/class_separation.c266dbceca87.py` | `c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920` |
| curated labels (frozen before the report run) | `classification.json` | `118b9441887d7ae2f2b58a94b95094111daf9a111bbe023b99d5e4c98afcd92f` |
| report | `report.json` | `e9a185ba9fdfeeb266c23e1368b0de94806ea9fae5a56275089da11ec28347f1` |
| live-drift observation | `drift_observation.json` | `8d2919f4fbb41c9c259778ff9fb320a4e935906b56424998d02dfa2a8bb482d9` |
| harness | `adjudicate_delta.py` | `085d9e4e99bdd96fcde4ba793ad9b9bcf1765a554e6925a6f8240c19c917a386` |

Claims are keyed by **event_id + statement sha256**, not by array index (the claims array is
rebuilt from the event stream and indices shift).

1. **Reproduce** every hard CLASSSEP finding on the pinned snapshot with the pinned detector:
   17 findings on 12 distinct claims, 0 on non-claim surfaces.
2. **Delta**: 10 reproduce the prior adjudications exactly; **7 are new**, all from three
   post-adjudication verification claims — `w044-rev12-…-claim-f2b` (claim 180),
   `w085-cd03-…-claim-candidate-inert` (claim 187), `w035-cshf-…-claim-adjudication` (claim 192, ×5).
3. **Adjudicate** each with an independently written cue classifier (`classify_context`, no
   detector internals) plus a curated per-finding judgement in `classification.json`.
4. **Converse scan** (false negatives): an independent composite-merge pattern over all 207
   claims, assertion-cued, minus the detector-flagged spans. 38 composite mentions scanned,
   21 assertion-cued, 5 unflagged candidates, **0 genuine**.
5. **Controls**: 4 positive (synthetic genuine merges must be caught), 13 negative (the
   detector's own contexts must not be called genuine), plus the worker-07 27-fixture
   regression against the pinned detector.

## Result

- **17/17 findings are mention-level, 0 genuine assertions.** Labels: `NEGATED_MENTION` 7,
  `CASE_LABEL_MENTION` 4, `QUOTED_MENTION` 4, `DETECTOR_SELF_DESCRIPTION` 1,
  `DESCRIPTIVE_MENTION` 1. Curated/auto agreement 17/17.
- **The 7 new findings are all meta-traffic**: claim 180 negates the merge in a check list
  ("no C0/C2 merge"); claim 187 quotes the false-positive shape as a control; claim 192 quotes
  five separate detector-output strings while adjudicating them.
- **No declared composite class token anywhere**: every flagged claim's `class_id` resolves to
  frozen class ids only (`class_id_composite_tokens: 0`, `class_id_tokens_all_frozen: true`).
- **Converse scan clean**: no unflagged first-order merge assertion found.
- **Controls pass**: 4/4 positive, 13/13 negative, worker-07 regression 17/0/10/0 `PASS`.
- **Verdict `DELTA_ALL_MENTION_LEVEL`**, `problems: []`, exit 0.

## Concurrent work (independent replication, no priority claimed)

worker-093 published `W093-CLASSSEP-METAGROWTH-01` at `2026-09-12T00:49:28+08:00`, at the *same*
pin `11311ab3600514cd`, also concluding 0/17 first-order assertions
(`artifacts/worker-093/classsep_metagrowth/report.json#9d8574474639`). My run was independent and
concurrent; it **replicates** that result with a separately written classifier and adds the
converse false-negative scan. worker-093's claim/blocker events are
`w093-metagrowth-20260912T0049-claim` and `…-blocker-meta-routing`.

## Moving-target observation (separate file, not part of the pinned adjudication)

The live map moved during the run: `11311ab36005` (207 claims, 17 hard) →
`f06d40a8226a` (278 claims, 20 hard) in ~10 minutes. The 3 extra findings are exactly the
self-reproduction worker-093 predicted its own claim would mint — an independent confirmation of
the metagrowth mechanism. `drift_observation.json` lists them; they are **not** adjudicated here.
Practical consequence: the CLASSSEP hard count cannot converge while verification claims quote
the detector's finding strings; the audit-lead calibration (`astra-life01-a1-rebind`) or a
quotation/metalinguistic channel is required, not a re-count.

## Falsifier

Any new finding is a genuine composite assertion (label `GENUINE_ASSERTION` or a composite token
in its own `class_id`), OR the converse scan finds an unflagged non-negated, non-quoted claim
asserting C0 and C2 are one class, OR any pre-registered control fails, OR the worker-07
regression leaves 17/10/0/0.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-032/cf16-delta/adjudicate_delta.py --selftest
python3 artifacts/worker-032/cf16-delta/adjudicate_delta.py --created-at 2026-09-12T00:50:38+08:00
sha256sum artifacts/worker-032/cf16-delta/report.json   # expect e9a185ba9fdf…
```

## Non-claims

Measurement/checker-calibration evidence only. Not a gate verdict, not a node completion, not a
mathematics or physics claim, no canonical artifact edited, no claim text rephrased. The
converse scan is regex+cue based: it reports what it finds, it does not prove absence.

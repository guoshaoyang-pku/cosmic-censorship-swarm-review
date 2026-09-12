# W070-GFORM-CLAIM-REDUNDANCY-01 — evidence-basis redundancy in the G-FORM claim stream

worker-070, bounded class-bound task, read-only. One question:

> At a pinned snapshot of the accepted event stream, how much of the G-FORM claim
> traffic is distinct declared evidential basis, and how concentrated is it on the
> same canonical target pins?

**Authority:** worker evidence only. No gate verdict, no node status, no canonical
write, no ingest. Nothing here is a mathematics or physics claim.

## Pin

* source: `research_map/events.jsonl`
* snapshot: `snapshot/events.102265f79405.jsonl`
  sha256 `102265f79405929c5563271cd51b69d802e6275f0ddcd82395e8ea8bd488dacd`
  (8122 lines, 607 claim events, 12,694,814 bytes), copied and hash-verified
  before/after copy at 2026-09-12T01:23:44+08:00
* frame (pre-registered rules/controls/falsifier): `frame.json`
  sha256 `6e83bc0b7d9f...`; seal `frame.sha256.txt`
* instrument: `census_070_redundancy.py` sha256 `c4bf095c4783...`
  (rev3; rev1/rev2 aborted in controls C5/C7 before any measurement — see
  `snapshot/superseded/README.md`)

## Primary result (pre-registered)

Universe: claim events whose class binding intersects
{AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN}; evidence signature =
sorted set of distinct 12-hex sha256 tokens parsed from the declared reference
keys; clusters are exact-signature classes.

| measure | value |
|---|---|
| claims in universe | **450** (102 actors, 232 tasks) |
| distinct evidence signatures | **433** |
| redundancy factor (claims / signatures) | **1.0393** |
| largest identical-basis cluster | **6** (the empty-signature cluster: no hash token under any declared reference key) |
| exact-statement duplicate groups / claims | **13 / 30** (max group 3) |
| C0 (F2b) | 349 claims, 338 signatures |
| C2 (F2a) | 297 claims, 286 signatures |
| WCC (F1) | 307 claims, 296 signatures |
| secondary: `gate == G-FORM` | 234 claims, 227 signatures |
| secondary: cites FROZEN rev29 `815e08079aef` | 113 claims, 110 signatures |

Controls C1–C7 all pass (`report.json`, `run.log`): shared-hash clustering,
case/length normalisation, empty-ref rule, `path#line#hash` forms, universe union
rule, cluster-size identity + idempotence, signature recompute.

## Secondary result (post-frame addendum, exploratory)

`addendum.json` / `addendum_070.py` ask the complementary question *after* the
primary run: which canonical pins do those 450 claims attach to? Rules are stated
in the addendum and were written after the primary result.

| measure | value |
|---|---|
| claims citing at least one canonical pin | **353 / 450** |
| claims with no canonical pin | 97 |
| distinct target keys (set of canonical `path#hash12` pairs) | **202** |
| claims sharing a target key with at least one other claim | **306** |

Most-cited pins (claims / distinct actors citing them):

| pin | claims | actors |
|---|---|---|
| `research_map/formulation_taxonomy.yaml#0abb9ed8a961` | 114 | 58 |
| `artifacts/formulation/FROZEN.json#815e08079aef` | 113 | 63 |
| `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe` (F2b rev13) | 103 | 50 |
| `schemas/af_wcc_vacuum.yaml#d9cebb9404b2` (F1 rev13) | 77 | 51 |
| `schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3` (F2a rev13) | 76 | 43 |

**Reading.** The two measures point in opposite directions and both are honest:
by *declared full basis* the claims are almost all unique (1.039), because each
claim cites its own worker artifact hashes; by *target* the same claims are highly
concentrated (306/450 share a target key, ~50–63 distinct actors per frozen pin).
This is a citation-concentration measurement. It does **not** show that claims on
one pin are either redundant or independent in method — that needs the reviewer /
instrument-independence question, which this task does not decide.

## Files

| file | sha256 (12) | role |
|---|---|---|
| `frame.json` | `6e83bc0b7d9f` | pre-registered rules, controls, falsifier |
| `frame.sha256.txt` | `7f43cd475be5` | frame + runner seal |
| `census_070_redundancy.py` | `c4bf095c4783` | primary instrument (rev3) |
| `report.json` | `81e6ead3497e` | primary machine report |
| `addendum_070.py` | `4dc5a4789786` | post-frame addendum instrument |
| `addendum.json` | `4459e11b290a` | post-frame target-concentration report |
| `run.log` | `c6e9bb1dc4fd` | instrument log |
| `snapshot/events.102265f79405.jsonl` | `102265f79405` | pinned stream snapshot |
| `emit_events_070_redundancy.py` | — | writes SHA256SUMS, checkpoint, outbox events |
| `SUPERSEDED_SHA256SUMS.txt` | — | hashes of the three archived snapshots |
| `SHA256SUMS.txt` | — | hashes of the above |

Reproduce:

```bash
cd <repo root>
python3 artifacts/worker-070/gform_claim_redundancy/census_070_redundancy.py --run   # exit 0, controls 7/7
python3 artifacts/worker-070/gform_claim_redundancy/addendum_070.py                  # exit 0
```

`--preregister` re-copies the live stream and therefore pins a *new* snapshot; use
`--run` to reproduce the reported numbers at the pinned snapshot.

## Falsifier

Re-run `census_070_redundancy.py --run` against the snapshot sha256 in `frame.json`:
falsified if any reported count, signature, cluster membership or control outcome
differs; falsified if a claim in the universe is shown to cite a hash token outside
its reported signature, or if two claims reported in one cluster have non-identical
declared reference sets. The addendum is falsified if any per-pin count differs on
re-run or a cited canonical pair is missing. A snapshot hash mismatch voids rather
than falsifies. Findings are snapshot-bound (traffic continues) and assert nothing
about cosmic censorship.

## Limits

* Signature equality is over *declared* hashes only; it does not verify that the
  cited bytes exist or that the claim is correct.
* Hash parsing is limited to the declared reference keys; hashes embedded only in
  prose outside those keys are not counted.
* Exact-statement duplication is whitespace/case-normalised; near-duplicates
  (paraphrase) are not counted.
* `created_at` is not used for the universe because CF-6/CF-14 record future-dated
  agent timestamps; the snapshot line set is the universe boundary instead.

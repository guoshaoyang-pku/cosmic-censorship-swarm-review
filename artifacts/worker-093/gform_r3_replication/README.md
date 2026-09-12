# W093-GFORM-R3-REPLICATION-01 — independent replication of the G-FORM r3 F2b adjudication

- **worker**: worker-093 · **class**: `AF-SCC-C0-VAC-GEN` (F2b) · **gate**: G-FORM (no gate verdict issued)
- **replicated artifact**: `reviews/G-FORM-final-verify-r3.json`, sha256
  `d94dd2d5b7784b29d2aebe4d8d47391f51d00790ae08fa0458eed5a8805ff657`, mtime
  `2026-09-12T01:19:18.999625+08:00` (archived byte-verbatim in `pinned/`)
- **result**: `REPLICATION_PASS`; 10/10 checks, 12/12 controls, digest `f82f6cbf2f98` (full
  digest `f82f6cbf2f98bbac95fbd8ba65efaca5d158710abee77135e406b9dd94ec69d9`)
- **reproduce**: `python3 artifacts/worker-093/gform_r3_replication/verify_r3_replication.py`
  (read-only; exit 0 iff PASS; rules frozen in `PREREGISTRATION.md` before the run)
- **window**: pins at T0 `2026-09-12T01:23+08:00`, before the rev14/rev30 re-freeze. Any write
  to the canonical schemas voids this replication for the new bytes only.

## What reproduces

| check | claim replicated | result |
|---|---|---|
| E1 | r3's F1/F2a/F2b + FROZEN rev29 pins equal measured disk bytes | CONFIRMED |
| E2 | F2b full-schema accept set == {worker-090, worker-071, worker-052} under the strict binder, the shipped controller scan, and r3 | CONFIRMED (three-way) |
| E3 | worker-072 accept self-superseded: in-file rev1 accept@01:10:13 (`7487f310d208`) -> revise (`5db91bb0781d`); event `w072-f2b-selfsupersede-review-20260912T011524` @01:15:24; r3 cites it | CONFIRMED |
| E4 | r3's `W066-F2B-ACCEPT-DISPOSITION` exists (01:15:04) and records worker-090's accept as SILENT on `C1-DENIAL` and `C2-PREMISE` | CONFIRMED |
| E5 | carrier quotes verbatim at `schemas/af_scc_c0_vacuum.yaml:152` and `:246`, with the E_C0⊃…⊃E_C2 chain at `:239` | CONFIRMED |
| E6 | declared-hash layer stale as r3 says: `.sha256` sidecar (`256dd18d7944`) and `entry_hashes.json` (`09a5b37a190d`) both declare `1bb78ce9b357` while F2b measures `b2ab6acb2bbe`; `af_scc_regularities.yaml` `27255e5b34f3` | CONFIRMED |
| E8 | no pinned input moved T0->T1; review surface unchanged during the run (214 -> 214 rows, 0 changed) | CONFIRMED |
| E10 | 12 planted controls (prefix match/mismatch, nested pin, alias target, scoped accept, short pin, unparseable/missing-verdict skip, supersede mutation, determinism) | 12/12 |

Supporting census at T0: 39 `reviews/*.json` records target F2b under the alias map; 16 of them
bind `b2ab6acb2bbe` by a 12-hex explicit pin (3 full accepts, 12 revise, 1 inconclusive); the
targeted-binding subset is 11 (3 accept / 8 revise). The full-accept names are identical across
the independent binder, the controller import, and r3.

## What does not reproduce

**E7 — r3's aggregate `non_author_accepts_all: 9` / `revises: 37` is not reproduced by any
pre-registered universe.** Reported per the pre-registration as an undefined-universe gap, not
as a false claim:

| universe | accepts-all | revises |
|---|---|---|
| U1 strict binder, F2b-targeted files | 3 | 8 |
| U2 F2b-targeted files, any pin | 11 | 26 |
| U3 accepted-stream events, `target_id == F2b` | 15 events (14 distinct reviewers) | 46 events (29 reviewers) |
| U4 events, target contains F2b/class | 23 (20) | 90 (50) |
| U5 events, any F2b/class mention | 136 (68) | 309 (102) |
| **r3** | **9** | **37** |

r3 does not name the universe behind 9/37. The decision-relevant number — the full-accept set
— does reproduce exactly; the aggregate pair should be either re-derived with its filter stated
or cited as non-reproducible.

**E9 — "non-author" is not verifiable from bytes.** `artifacts/formulation/FROZEN.json` has no
author field for F2b (only `owner`), so r3's falsifier "a counted accept whose reviewer authored
the artifact" cannot be evaluated by an independent party from disk alone. The three counted
accepts are not schema owners by reviewer id, but that is an id-level, not a role-level, check.

## Limits / non-claims

- Read-only: no canonical schema, review, map, or inbox byte was written; no detector write; no
  controller checkpoint script was run.
- This replicates a review artifact's bytes and counts, not the mathematics of the carriers. It
  issues no gate verdict, no node status, no `validation_status=passed`, and does not adjudicate
  whether the accepting or the blocking verdicts are substantively right.
- Context, not a finding about r3: `research_map/astra_lifecycle.py` has moved since pass-08
  (`957c61e3eb0e` reviewed by worker-048 -> `b155313797c0` at T0), so the controller scan is
  itself a moving target; r3's numbers were replicated against the T0 bytes recorded here.
- The review surface is mutable under fixed names; this census is valid only at T0.

## Falsifier

Withdrawn or revised if, at the pinned T0 hashes: (a) any r3-cited sha256 differs from measured
bytes; (b) the three-way full-accept agreement fails; (c) the worker-072 supersede trail or the
worker-066 disposition is absent or different; (d) either carrier quote is absent at the cited
line; (e) any pinned input moves T0->T1; (f) a control fails or two passes differ in digest.
Failure to reproduce (9, 37) does not falsify this task: it was pre-registered.

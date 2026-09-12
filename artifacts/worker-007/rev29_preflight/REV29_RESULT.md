# W007-REV29-PREFLIGHT-01 — post-repair (rev29) result and moving-target note

> **FINAL UPDATE (~00:59).** The follow-up repair landed while this slot was finishing: both variant
> deltas were rebased at 00:57:02 (SET `strength` now reads *"strictly weaker than AF-WCC-VAC-GEN (the
> parent's single-q tail predicate entails the union reading; the converse fails on the omega-chain
> witness…)"*), FROZEN rev29 was republished at 00:57:26 (`815e08079aef`, **50 files**, 0 drift), and the
> final acceptance run gives **`REV29_ACCEPTANCE_PREDICATE__ALL_ITEMS_PASS` (I1–I4 all true, 50/50 pins
> resolve, 9/9 controls)** — see `report_rev29_final.json`. The earlier `report_rev29.json` (I3/I4 open)
> is the intermediate measurement and is preserved as evidence of the moving window. The two-staged
> chronology below is retained because it is the finding: rev29 was momentarily a non-binding base.

`README.md` describes the pre-repair baseline (`report.json` + `report_preflight_baseline.json`, identical
bytes). This file records what happened when FROZEN rev29 landed during the same worker slot.

## Timeline observed from this slot

| time (+08:00) | observation |
|---|---|
| 00:52 | pre-repair baseline frozen: I1 satisfied; I2/I3/I4 open at FROZEN rev28 `2f358f6722d9` (`report.json`) |
| 00:53:4x | three class schemas rewritten (F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe`) while FROZEN stayed rev28 |
| 00:54:08 | **unpinned window open**: `verify_frozen.py` exit 1, 7 drift paths (3 canonical schemas, 3 mirrors, `gate_test_report.json`) |
| 00:54:32 | FROZEN **rev29** published (`e1a8aaa394eb`, 48 files); window closes, `verify_frozen.py` exit 0 |
| 00:55:02 | FROZEN rev29 republished (`3d9e3d77fd87`) with the variant deltas and corpora pinned |
| 00:55:33 | first rev29 acceptance run — a case-sensitivity bug in the delta-strength predicate wrongly passed I3; fixed and covered by new control M9 |
| ~00:56 | second rev29 acceptance run (`report_rev29.json`): F1 had changed **again** (anchor lines 215→216, 236→237) and `artifacts/formulation/evidence/variant_delta_check.json` had drifted from its rev29 pin (`fc6ee058` → `0b23f0b2`) |

## Result at the FROZEN rev29 pins (`3d9e3d77fd87`, frozen_at 00:55:02)

| item | rev29 state (`report_rev29.json`) | flag |
|---|---|---|
| I1 cases rebind | 36/36 rows bound to live F0 rev5; canonical checker exit 0 | **pass** |
| I2 consistency-evidence binding | all three schemas declare `consistency_evidence_sha256 = 9e335e9ba1bf` = live | **pass** |
| I3 variant strictness | F1's inverted token is **gone** (0 occurrences; corrected at the new F1 bytes), but the SET delta `strength` still reads the pre-repair wording `"strictly stronger than AF-WCC-VAC-GEN"` at `45b9b6a8d192` | **open** |
| I4 FROZEN rev29 pins | revision 29, 47/48 pins resolve; `artifacts/formulation/evidence/variant_delta_check.json` drifted after the freeze (`fc6ee058` → `0b23f0b2`); F1 moved again during measurement | **open** |

Verdict of that run: `REV29_ACCEPTANCE_PREDICATE__OPEN_ITEMS=I3,I4`.

## Implication for the open G-FORM round

FROZEN rev29 is **not yet a stable binding base**: one item (I3, the SET variant record) is still
pre-repair and at least one pinned derived-evidence file (`variant_delta_check.json`) changed after the
rev29 freeze. Binding reviewers using Astra's pass-05 stop rule ("stop if a pinned file moves mid-round")
should either wait for the follow-up repair + FROZEN rev30, or bind explicitly to a hashes-stable window
measured with `verify_preflight.py --mode rev29`. The variant record itself is the remaining item named by
worker-076: the F1 prose is corrected, the `.variant-SET.delta.json` `strength` is not.

Re-run:

```bash
python3 artifacts/worker-007/rev29_preflight/verify_preflight.py --mode rev29
```

`ALL_ITEMS_PASS` requires I3's delta strength to be corrected *and* every FROZEN pin (including
`schemas/taxonomy_cases.jsonl`, the three schemas and the variant deltas) to equal live bytes at the same
run, with `verify_frozen.py` exit 0.

## Falsifier

A re-run at the same FROZEN rev29 manifest (`3d9e3d77fd87`) whose item flags differ from
`report_rev29.json`; or evidence that the SET delta `strength` token was already corrected at
`45b9b6a8d192` (it reads `strictly stronger than AF-WCC-VAC-GEN` here); or a `variant_delta_check.json`
whose bytes equal the rev29 pin `fc6ee058dd96` (they measure `0b23f0b29232` here).

## Non-claims

- Measurement only; no gate verdict, no node status, no canonical artifact edit.
- I3 records token presence/absence; the direction of the visibility relation is worker-076's
  machine-checked result, not re-derived here.
- The times are wall-clock from this slot; concurrent writers may have moved bytes between two of these
  measurements, which is precisely the recorded phenomenon.

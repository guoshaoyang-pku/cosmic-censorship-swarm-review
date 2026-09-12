# W027-F2A-HB1-INDEP-01 — independent verification of the F2a HF-B1 hashbound closure

Worker: worker-027 · Class: `AF-SCC-C2-VAC-GEN` (node F2a) · Gate: G-FORM · read-only.
Claim author under test: `deepseek-flash-05` (`artifacts/worker-05/verify/hb1_closure_report.json#c7eeab551128`).

## Verdict

`INDEPENDENTLY_VERIFIED_HB1_CLOSURE_VALID_UNPUBLISHED` (exit 0), at the pins recorded in `report.json`
(`pins_t0` = `pins_t1`, 12/12 unchanged; measurement digest
`184b54cbb63e28b76518690c841ee4e0a9463bca6c3f8eda94754aa35ffd0a94` identical over 2 in-process runs and one
separate process).

* **W027-HB1-F1 (main claim) — VERIFIED.** The live evidence record
  `artifacts/formulation/evidence/taxonomy_consistency.json#9e335e9ba1bf`
  embeds no sha256 of either compared taxonomy file (private hex64 scan: none; classifier: UNBOUND),
  so HF-B1 reproduces. The candidate
  `artifacts/worker-05/verify/taxonomy_consistency_hashbound.json#4c4803c540a1`
  embeds exactly the independently measured hashes of both compared files; the pinned generator
  reproduces it byte-for-byte over two runs; dropped in at the canonical evidence path in an
  isolated sandbox it makes every hard check of `check_class_binding_drift.py` pass for all three
  schemas, and the canonical `check_taxonomy_consistency.py` exits 0. No canonical byte was written.
* **W027-HB1-F2 (major, instrument) — CONFIRMED.** The proposed durable checker's B7 is a substring
  test (`declared in blob or declared[:16] in blob`). A record whose canonical binding hash shares
  only the first 16 hex chars (one suffix nibble flipped) passes **all** hard checks (exit 0), so B7
  does not verify that the record's declared revision equals the measured revision.
* **W027-HB1-F3 (minor, instrument) — CONFIRMED.** B7 binds only the canonical F0 hash; the
  supplement input `artifacts/formulation/formulation_taxonomy.yaml` is bound by no hard check, so a
  stale supplement hash passes.

F2/F3 are blind spots of the tool, not defects of the candidate; they gate *adopting the tool* as
the durable binding check. See the `blocker` event in `comms/outbox/worker-027.jsonl`.

## Method (independence)

Primary verdicts use this worker's own instruments: a recursive hex64 scanner, an
UNBOUND/BOUND/STALE classifier driven by independently recomputed live hashes, and a private
class-set consistency check. The author's checker is used only as a labelled cross-instrument
(P7/P8/IP1–IP3), and the canonical project checker as a second independent instrument (P9).
Sandbox roots are built under `scratch/` and never touch canonical paths.

## Pre-registered checks

| id | check | ok |
|---|---|---|
| P2 | True |
| P3 | True |
| P4 | True |
| P5 | True |
| P6 | True |
| P7 | True |
| P8 | True |
| P9 | True |

| id | control | ok |
|---|---|---|
| C1 | True |
| C2 | True |
| C3 | True |
| C4 | True |
| C5 | True |
| C6 | True |

Instrument probes (recorded, not gating): IP1=STALE/author_exit0; IP2=STALE/author_exit1; IP3=STALE/author_exit0

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-027/f2a_hb1_indep/verify_hb1_indep.py \
  --out artifacts/worker-027/f2a_hb1_indep/report.json \
  --work artifacts/worker-027/f2a_hb1_indep/scratch --repeat 2
```

Exit 0 = verified, 1 = claim not verified, 2 = void (input drift). `scratch/` holds the drift-checker
reports for the live record, the candidate drop-in and the three instrument probes, plus the
generator's two runs and the tamper fixtures.

## Falsifier

FALSIFIED if (a) any pinned input drifts T0->T1 (void, exit 2); (b) the live evidence embeds a sha256 of either compared file or an explicit input-hash field; (c) the candidate's embedded canonical/supplement hashes are not the measured live hashes; (d) the candidate's consistent claim is not reproduced by P5 or P9; (e) the generator's two runs are not byte-identical; (f) the candidate drop-in still hard-fails the author drift checker for any schema; (g) the live record passes B7; (h) any control misses its pre-registered expectation.

## Non-claims

- not a gate verdict; worker events cannot set status=done, validation_status=passed, or any gate verdict
- does not publish the candidate; the canonical write and the three schema re-pins belong to the formulation lead
- does not adjudicate the F2a assignment moving-target blocker (rev12 pin 5476a3f2 vs live e9a27996)
- author-level independence only: deepseek-flash-05 authored the claim; worker-027 did not author it
- records but does not adjudicate two blind spots in the author's drift checker (W027-HB1-F2/F3); hardening the tool is the tool owner's call

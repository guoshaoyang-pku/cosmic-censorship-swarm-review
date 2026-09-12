# W035-REV14-CONFORMANCE-PRECHECK-01

Bounded worker-035 task, node **F2b**, class **AF-SCC-C0-VAC-GEN**, gate **G-FORM**.
Read-only instrument + labeled fixture corpus for the REC-36 `rev14` / FROZEN `rev30` window.

This is an **instrument and a calibration record, not a verdict**. It cannot move a gate, a node
status or a `validation_status`; no canonical path was written.

## Why this exists

Pass 08 (`research_map/ASTRA_HANDOFF.md`, 01:18) authorizes exactly one `rev14` / FROZEN `rev30`
that must fold the two live F2b content defects and rebind several hashes; any byte move voids
every current verdict, and `astra-life05-verify-gform-r3` must then re-verify at the new pins.
The defects to be repaired are stated in prose. This instrument pre-registers them as machine
checks with per-check falsifiers and a mutant corpus, so the re-verification round can be
executed mechanically instead of re-read.

## Pre-registered checks

| id | severity | reads | fails when |
|---|---|---|---|
| P01 | blocking | `class_id`, `class_components.regularity_token`, `sibling_disjoint_from` | identity fields are not the C0 values (a C2/C0 merge) |
| P02 | blocking | every `*_sha256` under `f0_binding` + its declared path | a declared sha256 does not resolve to measured bytes |
| P03 | blocking | `declared_f0_sha256` vs live `research_map/formulation_taxonomy.yaml` | declared F0 hash ≠ measured F0 bytes (refresh owed) |
| P04 | blocking | every `must_not_conflate` entry vs the parsed ledger chain | a containment denial contradicts the chain (live defect **D1**) |
| P05 | blocking | `implication_ledger.forbidden_transfers[*].reason` vs chain order | a "strictly larger/smaller" assertion contradicts the chain (live defect **D2**) |
| P06 | advisory | `revision_history` vs live `declared_f0_sha256` | no row names the live F0 hash, timestamps non-monotone, or `unused` row carries deltas |
| P07 | advisory | `schemas/af_scc_c0_vacuum.yaml.sha256`, `entry_hashes.json` | either side pin ≠ measured canonical hash |
| P08 | advisory | `review_status` | `independent_reviewers` empty / verdict still `pending` |
| P09 | blocking | C0 vs C2 `extension_class_containment`, parsed by explicit `contains` / `subset of` relations | the two siblings order the extension sets differently |
| P10 | blocking | `artifacts/formulation/FROZEN.json` | FROZEN declares this artifact at a hash ≠ measured |
| P11 | advisory | `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` | canonical/mirror double-tree pair diverges |

P07/P10/P11 report `OBS` on non-canonical targets (fixtures); they are evaluated only for
`schemas/af_scc_c0_vacuum.yaml`.

## Calibration at the pinned rev13 bytes (2026-09-12T01:25+08:00)

Target `schemas/af_scc_c0_vacuum.yaml` `sha256:b2ab6acb2bbe…`, stable before and after the read
(no drift), FROZEN rev29 `815e08079aef…`, mirror aligned.

```
P01 PASS  P02 PASS  P03 PASS  P04 FAIL  P05 FAIL  P06 FAIL(adv)
P07 FAIL(adv)  P08 FAIL(adv)  P09 PASS  P10 PASS  P11 PASS
blocking_fail = [P04, P05]
```

* **P04/P05 FAIL reproduce the two live defects**, D1 (`regularity.must_not_conflate[0]`: "No
  containment with C2 or C0 is asserted here") and D2 (`forbidden_transfers[0].reason`: "C2 is a
  strictly larger extension class" against the file's own chain `E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2`).
  This matches the controller record (pass-08 G-FORM unmet text plus CF-31, `F2b-rev30-h2-direction-053.json`,
  `F2b-accept-audit` HF-W035-AA-01/02) measured independently by this instrument.
* P02/P03 PASS: both declared `f0_binding` hashes resolve and the refresh trigger is inactive.
* P09 PASS: C2 sibling line 237 and C0 line 239 order the four extension sets identically once
  the connectives are parsed (a naive first-occurrence comparison flags a false positive here —
  that bug was found and fixed by fixture F6 during construction).
* P06/P07/P08 FAIL are the already-recorded advisory findings F-035-01, F-035-02 and
  HF-W035-AA-03, not new.

## Controls

`make_fixtures.py` writes 8 fixtures derived from the pinned snapshot and asserts every fixture's
full status vector against `fixtures/expected.json`. **8/8 match** (`controls.json`).

| fixture | mutation | expected flip |
|---|---|---|
| F0_baseline | byte copy of rev13 | calibration vector |
| F1_d1_denial_removed | removes the containment denial | P04 → PASS |
| F2_d2_inversion_fixed | corrects the size direction | P05 → PASS |
| F3_both_fixed | F1+F2 | P04,P05 → PASS |
| F4_chain_corrupt | flips one hex char of `declared_f0_sha256` | P02 → FAIL, P03 → FAIL |
| F5_identity_leak | `regularity_token: C2` | P01 → FAIL |
| F6_crossfile_flip | C2 sibling chain order flipped | P09 → FAIL |
| F7_revhist_fix | names live F0 hash, monotone timestamps, clears unused deltas | P06 → PASS |

Honest construction record: on the first harness run F4 mismatched (P03 also flips, because a
corrupted declared-F0 hash is by construction a refresh-rule violation). The expectation was
corrected; this is the harness doing its job, and it is recorded rather than hidden.

## Using it on rev14

```bash
cd artifacts/worker-035/rev14_conformance_precheck
python3 precheck.py --file ../../../schemas/af_scc_c0_vacuum.yaml --out rev14_report.json
```

Pass criterion for the D1/D2 fold: **P04 and P05 both PASS** and no new blocking FAIL (P01/P02/
P03/P09/P10). Exit code 2 means ≥1 blocking FAIL. `--file`/`--c2` accept any copies, so the
instrument can be run against a proposed revision before it is canonical.

## Non-claims / authority

* Instrument and calibration only; **not** a gate verdict, **not** a node verdict, **not** an
  accept/revise of any artifact, and it does not overturn any reviewer verdict.
* No canonical path written; the reviewed artifact was not edited; snapshots and fixtures live
  only under this directory.
* P04/P05 flag contradictions between fields of the file. Whether a repaired revision is
  *scientifically* adequate remains a reviewer judgement; this instrument only closes the
  mechanical part of that judgement.
* `formal_model`-class statement accompanying this artifact asserts instrument behaviour
  (fixture match, calibration vector), not any statement about cosmic censorship.

## Self-falsifier

Any fixture in `fixtures/` whose observed status vector differs from `fixtures/expected.json`
falsifies **this instrument**. For the F2b use: a revision in which P04/P05 PASS but the D1/D2
text is still present in a rephrased form the patterns do not cover falsifies the instrument's
completeness, and must be reported as a detector blind spot rather than as a repair.

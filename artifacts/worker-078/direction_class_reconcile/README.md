# W078-DIRCENSUS-CLASS-RECONCILE-01 — direction-census classification reconciliation

**Worker:** worker-078 (bounded execution worker; evidence only)
**Class:** `AF-WCC-VAC-GEN` (corpus covers the four frozen classes) · **Node:** F0 · **Gate:** G-F0
**Pins:** FROZEN rev29 `815e08079aef`, F0 canonical `0abb9ed8a961`, F0 supplement `d7419b4e8963`,
F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, F2b `b2ab6acb2bbe`, VARIANT_REGISTRY `6bac9adea19e`,
`schemas/f1_falsifier_tests.jsonl` `56bcb4b3234b` — zero drift across the run.

## Why this task

Two workers classified the same pinned bytes differently:

- `W099-FORM-DIRECTION-CENSUS-01` lists **3 INVERTED** direction findings and leaves **34** hits in
  `MANUAL_REVIEW` (`artifacts/worker-099/form_direction_census/census.json#a8a1ff504dcd`).
- `W078-F0-SET-STRENGTH-ADJ-01` classified one of those three — the authoring-supplement D1 ledger
  `artifacts/formulation/formulation_taxonomy.yaml:176` — as a **historical mention**, not an
  operative claim, and separately found an operative inversion the census does not list
  (`research_map/formulation_taxonomy.yaml:94`).

An open controller disposition (OPT-A erratum vs OPT-B repair for the frozen F0 taxonomy) depends
on exactly this question: *which pinned lines would a repair have to touch?*

## Verdict

| site | census | w078 | class |
|---|---|---|---|
| `research_map/formulation_taxonomy.yaml:94` | not listed (CORRECT/MANUAL window) | **OPERATIVE_INVERTED** | SET variant definition says "strictly stronger"; SINGLEQ entails SET |
| `research_map/formulation_taxonomy.yaml:200` | INVERTED | **OPERATIVE_INVERTED** | class text asserts the set-based reading is strictly stronger |
| `schemas/af_scc_c0_vacuum.yaml:245-246` | INVERTED | **OPERATIVE_INVERTED** | reason clause calls C2 "a strictly larger extension class"; C2 is the smallest |
| `artifacts/formulation/formulation_taxonomy.yaml:176` | INVERTED | **HISTORICAL_MENTION** | resolved D1 divergence ledger; "strictly stronger" is inside the quoted superseded `f0_reading`; `status: resolved` |

- **Conflicts resolved:** the census's supplement:176 `INVERTED` is a **false positive** (no repair;
  rewriting a resolved ledger record would falsify it). The census is **under-inclusive** at
  canonical F0:94 (it lists only F0:200).
- **MANUAL_REVIEW residue:** all 34 census rows (34 unique keys) resolve to `NEGATIVE_SCOPE`,
  `DEFINITION`, `OPERATIVE_CORRECT` or `PROBE_RECORD`. **Zero new operative inversions.**
- **Census internal inconsistency recorded:** 3 keys (`F0:141`, `F2b:244`, `F2a:153`) appear twice
  in the census with two different verdicts (`MANUAL_REVIEW` and `CORRECT`), so its 34/25 row counts
  double-count those keys. Each is adjudicated once here.
- **Union repair manifest for OPT-B:** `F0:94-95`, `F0:200`, `F2b:245-246` (a candidate patch for
  F2b exists from `W001-F2B-REV13-CONTAINMENT-CLOSURE-01`). Supplement:176 is *not* repairable.

## Method (all pre-registered before execution)

1. 10 inputs pinned by sha256; start mismatch is exit 2, start/end drift voids the binding.
2. Candidate set = census rows ∪ own scan of the 8 audited files for `stronger|weaker|larger|smaller`.
   The census and the prior W078 report are measured inputs, not audited corpus.
3. Automatic rule triage (`classify_line`) over each candidate; where the line has multiple or no
   recognised subjects it returns `NEEDS_ADJUDICATION`.
4. `adjudication_table.json` (66 anchored entries) supplies the adjudicated verdict. Every anchor
   must occur verbatim in the pinned window or the instrument exits 5 (fail-closed). Both the
   automatic and the adjudicated verdict are reported for every candidate.
5. Truth direction is derived from the pins: declared containment chain
   `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0` (F2a:148, F2b:241-243), plus an independent re-derivation
   that SINGLEQ entails SET (384 chain-restricted preorder models, 0 violations) and that the
   converse fails (49/225/961 uncovered-tail certificates at N=8/16/32; no candidate cover survives).

The automatic line-level rules are a **triage layer only**: outside the three known sites they
produced 7 false `OPERATIVE_*` verdicts by attributing a comparative to a class token inside a
class name (e.g. registry:34 "STRONGER than AF-SCC-C2-VAC-GEN"). All such hits were read; the
census classification is upheld there and the corrections are recorded in
`rule_conflicts_on_out_of_scope_reference_hits`.

## Files

| file | role |
|---|---|
| `reconcile_direction_classification.py` | deterministic instrument (pins, scan, triage, truth derivation, controls) |
| `adjudication_table.json` | 66 anchored worker adjudications (anchor + verdict + reason) |
| `report.json` / `report_rerun.json` | primary evidence; byte-identical |
| `controls.json` | extracted control block (fixtures 10/10, anchors, census coverage, residue) |
| `snapshot/` + `SHA256SUMS.txt` | byte-exact pinned inputs and their hashes |
| `CHECKPOINT.json` | worker checkpoint (task, pins, verdict, falsifier) |

Reproduce:

```bash
python3 artifacts/worker-078/direction_class_reconcile/reconcile_direction_classification.py \
  --controls --created-at 2026-09-12T01:34:00+08:00 \
  --out artifacts/worker-078/direction_class_reconcile/report.json
```

## Falsifier

Re-run at the same pins: FALSIFIED if any pinned file drifts, if any own-scan strength line outside
the census windows is `OPERATIVE_INVERTED`, if any anchor stops matching, if any fixture flips, if
the truth-direction derivation reports a violation or a surviving cover candidate, or if
F0:94 / F0:200 / F2b:246 stop being operative strength assertions.

## Authority

Worker-level evidence only. Read-only on every canonical path; writes only under
`artifacts/worker-078/` and `runtime/state/`. No gate verdict, no node status, no
`validation_status=passed`.

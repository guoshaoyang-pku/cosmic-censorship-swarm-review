# W061-F0-DIRECTION-BLAST-08 — F0 SET/tail direction census + option blast radius

- **Worker:** worker-061 (bounded execution worker; one task, then exit)
- **Class:** `AF-WCC-VAC-GEN` — **Nodes:** F0, F1 — **Gate context:** G-F0 (passed, frozen), G-FORM (pending)
- **Question:** the reduced L-FORM-03 residual says the inverted SET/tail direction survives in the two
  FROZEN F0 artifacts. Enumerate every strength-direction claim in those two files, classify each
  against the order fact, and measure the hash blast radius of the controller's three disposition
  options. **No canonical artifact was edited by this task.**
- **Root pins (measured live, all match):**

| artifact | sha256 (12) |
|---|---|
| `research_map/formulation_taxonomy.yaml` (F0 canonical, rev5) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (F0 supplement) | `d7419b4e8963` |
| `artifacts/formulation/FROZEN.json` (rev29, frozen_at 00:57:26, 50 pins) | `815e08079aef` |
| `schemas/af_wcc_vacuum.yaml` / `af_scc_c2_vacuum.yaml` / `af_scc_c0_vacuum.yaml` (rev13) | `d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe` |
| `schemas/taxonomy_cases.jsonl` (36 rows + meta) | `ccf7041bd0ff` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf` |
| `research_map/research_map.json` (moving; measured at run) | `f344ed2aaea5` |

## Method

`probe_f0_direction_blast.py` is deterministic, stdlib + PyYAML, fail-closed (exit 0 measured /
1 control or pre-registration mismatch / 2 drift or unclassified strength line).

1. **Order fact re-derived in-run.** T = single-q tail predicate, S = union/set reading.
   All 389 preorders on ≤4 points × chains of length ≤3 × all non-empty I⁺ subsets =
   **154 452 cases: `T_and_not_S = 0`**; `S_and_not_T` witnessed. The explicit omega-chain
   certificate (γ and I⁺ both omega-chains, x_i ⪯ q_j iff i ≤ j) gives S true, T false, with
   **3660/3660 escape pairs holding**. Therefore: at the predicate level **T is strictly stronger,
   S strictly weaker**; at the negation level **¬S strictly stronger than ¬T**.
2. **Exhaustive census.** 15 pre-registered sites (every physical line in either file matching
   `stronger|weaker` must map to a site, else exit 2). Each site is extracted from its line window by
   a direction-tolerant regex and classified by rule, not by hand label.
3. **Fan-out scan.** `reviews/*.json` (field-aware: `reviewed_sha256` vs `companion_sha256` vs mere
   mention), `research_map.json` sections, `FROZEN.json` pins, the three rev13 `f0_binding` blocks,
   `taxonomy_cases.jsonl`, the accepted `events.jsonl` stream, and a whole-tree prefix grep
   (5 326 files mention either F0 hash, nearly all historical worker/review citations).
4. **Controls K1–K5** (sandbox copies only): repair the `:200` label → CORRECT; invert the CH label
   → INVERTED; repair the D1 relation to an explicit two-level form → CORRECT; unrelated prose edit
   → no verdict changes; two census runs byte-identical. **5/5 pass.**

## Result — 15 sites: 4 flagged, 11 correct

| site | file:line | classification |
|---|---|---|
| C-SET-DEF | canonical:94 | `PREDICATE_LABEL_INVERTED_NEGATION_SUPPORT_CORRECT` |
| C-VIS | canonical:200 | `PREDICATE_LABEL_INVERTED` |
| S-D1-READING | supplement:176 | `PREDICATE_LABEL_INVERTED` |
| S-D1-RELATION | supplement:176 | `RELATION_POLARITY_MISMATCH` |
| C-CH, C-C11-H2, C-C0STRONG, C-C0CLAIM, C-C0REJECT, C-C2WEAK, C-C2CLASS, C-C0SEP | canonical | CORRECT |
| S-C0STRONG, S-DISTWEAK, S-H2LOC | supplement | CORRECT |

### Findings

- **F-W061-F0DIR-01 (major, confirms L-FORM-03a).** Canonical `:200` says the set-based reading
  "is strictly stronger". Under the run's own order fact it is strictly *weaker* at the predicate
  level. The class predicate is unaffected (the same paragraph already fixes the single-q TAIL
  reading); this is a justification/precision defect in frozen bytes.
- **F-W061-F0DIR-02 (major, confirms L-FORM-03b).** Supplement `:176` D1 carries the same inversion
  in `f0_reading` ("(strictly stronger)") and a polarity-mismatched `relation`:
  `(b)` is recorded as the *negative* set reading ("lies outside J⁻(I⁺) as a SET") and `(c)` as the
  *positive* tail reading, so "F0 was stronger; (b) implies (c) but not conversely" cannot be right
  as written at one level. The two-level truth is `T ⇒ S, not conversely` ⇔ `¬S ⇒ ¬T, not conversely`.
- **F-W061-F0DIR-03 (minor, NEW — not named by the reduced L-FORM-03).** Canonical `:94`
  (variant SET definition) says the variant is "Strictly stronger than the parent class". Its own
  support clause is the negation-level ¬S ⇒ ¬T, which is correct; the unleveled predicate label is
  not. Repair with the same explicit two-level phrasing used at F1 rev13 (`schemas/af_wcc_vacuum.yaml`
  :214 EQUIVALENT, :235 "strictly WEAKER") or annotate the level.
- **F-W061-F0DIR-04 (info, measured blast radius).** 9 review files bind
  `reviewed_sha256 = 0abb9ed8a961` (F0-review-rev27-a/b, F0-review-025, F0-criteria-audit-078,
  F0-indep-082-rev5, F0-conformance-038-rev28, F0-sph-d3-verify-022, CF21-genericity-consistency-094,
  G-F0-final-verify-r2); exactly **1** review file binds `companion_sha256 = d7419b4e8963`
  (F0-sph-d3-verify-022). All 36 taxonomy-case rows + meta bind `0abb9ed8a961`; all three rev13
  schemas declare `declared_f0_sha256 = 0abb9ed8a961`; FROZEN rev29 pins both F0 paths.
- **F-W061-F0DIR-05 (info, clean set).** The 11 correct sites include every C0/C2/H2_loc regularity
  strength claim and the CH extension-subset claim; no unclassified `stronger|weaker` line exists in
  either F0 file; the repaired downstream sites (`F1:214/235`, `VARIANT_REGISTRY.json:57`,
  `SET.delta.json:11/27`, `CH.delta.json:11`) are consistent with the two-level statement.
- **F-W061-F0DIR-06 (info, provenance).** FROZEN rev29's own `rev29_delta` note still lists the SET
  registry and delta as carrying the inversion; the live bytes at `6bac9ade`/`64b8d639` no longer do
  (repaired after that note was written). Reviewers binding the note, not the live bytes, would
  overstate the residual.

### Disposition options — measured, not inferred

| option | writes | hash moves | stale verdicts | follow-on |
|---|---|---|---|---|
| **O1** edit supplement D1 | supplement only | supplement `d7419b4e8963` → new | 1 companion-bound verdict (46 files mention it) | FROZEN re-freeze |
| **O2** reopen F0 canonical | F0 canonical | canonical `0abb9ed8a961` → new | 9 `reviewed_sha256`-bound verdicts (82 files mention it) | G-F0 pass void; 3 schema bindings stale; 36-row corpus rebind; FROZEN re-freeze |
| **O3** map erratum, no artifact write | `research_map.json` (controller) | none | 0 | `controller_findings` entry only |

## Falsifiers

This pack is falsified by any one of: (a) a site classified INVERTED shown correct under the F0
predicate semantics, or a CORRECT site shown inverted; (b) a `stronger|weaker` line in either F0 file
that the census does not classify; (c) a file in the declared scan scope that binds either F0 hash but
is missing from the fan-out counts; (d) K1–K5 failing on re-run; (e) any pinned hash above moving
(re-measure voids the measurement, not the finding).

## Reproduce

```bash
python3 artifacts/worker-061/f0_direction_blast/probe_f0_direction_blast.py   # exit 0, controls 5/5
```

**Authority limits.** Worker evidence only: no gate verdict, no node status, no
`validation_status=passed`, no canonical artifact touched. The class predicate is not in question;
only the direction of recorded justifications is measured.

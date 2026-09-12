# W065 — rev12 delta, binding and provenance census (worker-065, 2026-09-12T00:37+08:00)

**Verdict: `REV12_DELTA_CENSUS_COMPLETE`** — all 17 controls pass, window STABLE, run exit 0.

This is a read-only measurement of the 00:31–00:32 republication of the formulation
artifacts. It does **not** judge whether rev12 is mathematically correct; that is the
reviewers' and controller's call. It measures what changed, whether the declared bindings
resolve against the bytes on disk, and whether revision provenance survived.

## 1. What was measured

| artifact | predecessor (last-reviewed) | rev12 (measured) | deltas | semantic | metadata |
|---|---|---|---|---|---|
| F0 declared taxonomy | `276009f4f63d` (rev4) | `0abb9ed8a961` (rev5) | 7 | 4 | 3 |
| F0 contract supplement | `c8e979a1eb48` (rev8) | `d7419b4e8963` (rev9) | 3 | 0 | 3 |
| F1 `af_wcc_vacuum.yaml` | `9a8bd4c96800` (rev11) | `cce9c60146d6` (rev12) | 25 | 16 | 9 |
| F2a `af_scc_c2_vacuum.yaml` | `b6123750b37d` (rev11) | `5476a3f2c6bc` (rev12) | 22 | 12 | 10 |
| F2b `af_scc_c0_vacuum.yaml` | `1bb78ce9b357` (rev11) | `55d0a1ea9bda` (rev12) | 22 | 12 | 10 |

Predecessor bytes are third-party pinned snapshots, each verified against its recorded
sha256 in control C1. Full per-path delta lists: `rev12_delta_census.json`.

## 2. Findings

- **W065-R12-01 (delta).** rev12 is a substantive semantic revision, not a metadata fix.
  F1/F2a/F2b replace the `(s,delta)` binder with a tagged disjoint-union index `r` in `D0`
  and propagate it through `D1`, `quantifiers.ordered`, `formal`, `negation`,
  `negation_normal_form`, `genericity` and `conclusion.statement_formal`. F1 additionally
  rewrites `D5` to the tail-pair `(q,t0)` predicate and adds
  `i_plus.predicate_abbreviation`. **Reviewers who accepted the predecessor cannot carry
  their verdict forward; the quantifier surface changed.**
- **W065-R12-02 (binding).** The contested `class_contract_pointer` is repaired: all three
  schemas now point at `research_map/formulation_taxonomy.yaml#classes.<CLASS>` (canonical)
  and add `class_contract_supplement_pointer` for
  `artifacts/formulation/formulation_taxonomy.yaml#class_contracts.<CLASS>`. Both fragments
  resolve (C-F1/F2a/F2b-ptr, C4, C7), and all three declare the same
  `f0_binding.declared_f0_sha256 = 0abb9ed8a961…`, equal to the measured F0 canonical hash
  (C-F1/F2a/F2b-f0, C10). The `consistency_evidence_sha256` also matches its file.
- **W065-R12-03 (hygiene).** The duplicate-top-level-key defect is gone. Strict YAML accepts
  all five artifacts with **zero duplicate keys at any depth**, while the predecessor
  snapshots of F1/F2a/F2b and of the F0 supplement are strict-REJECT (C5). Predecessor
  defect counts: F1 `revised_at`×7 + `revised_at_unused`×2; F2a `revised_at`×8; F2b
  `revised_at`×8; F0 supplement `revised_at`×6; F0 canonical was clean.
- **W065-R12-04 (provenance).** For F1/F2a/F2b, every predecessor raw header stamp
  (authored/revised/revised_at_unused) reappears in the new `revision_history` list; nothing
  was dropped (per-artifact `provenance` blocks).
- **W065-R12-05 (shared data class).** `quantifiers.domains.D0` is raw-identical across
  F1/F2a/F2b. `regularity.data_regularity` is equal modulo a punctuation variant
  (F1: `s > 5/2 and delta`, F2a/F2b: `s > 5/2, delta`); `conclusion.statement_formal`
  differs by class as designed (C11 controls the comparator).
- **Publication context (measured, not owned here).** `artifacts/formulation/FROZEN.json`
  is now revision 27, `frozen_at 00:32:59`, sha256 `5fa3b3bf95f2…`, and its five pins match
  the hashes above. The transient rev26→disk drift observed at 00:32 was closed by the
  owner before this census completed; no open pin drift was found at measurement time.

## 3. Point-in-time verdict binding at rev12 (`rev12_binding_probe.json`)

Scan of `reviews/*.json` + `comms/outbox/*.jsonl` review events at 00:37. Controller audit
remains authoritative; these are raw corpus counts, prefixes matched at 12 hex.

| artifact | accept | revise | inconclusive | distinct actors |
|---|---:|---:|---:|---|
| F0 `0abb9ed8a961` | 1 | 5 | 0 | 4 |
| F0 supplement `d7419b4e8963` | 1 | 3 | 0 | 3 |
| F1 `cce9c60146d6` | 0 | 4 | 0 | 3 |
| F2a `5476a3f2c6bc` | 0 | 5 | 0 | 4 |
| F2b `55d0a1ea9bda` | 0 | 4 | 0 | 3 |

The gate-critical reading: **F1/F2a/F2b have no accept at rev12 yet**, and the predecessor
accepts (e.g. worker-047 withdrew its F2a accept at `b6123750b37d`) do not bind to the new
bytes. Fresh verdicts must cite `cce9c60146d6` / `5476a3f2c6bc` / `55d0a1ea9bda`.

## 4. Controls (all 17 pass)

C1 predecessor snapshot hash; C-F1/F2a/F2b-ptr and -f0 fragment/hash bindings; C2 diff
sensitivity; C3 metadata classification; C4/C7 fragment resolver positive/negative/prefix;
C5 strict-detector direction on predecessor vs rev12; C6 provenance-loss detection;
C8 determinism; C9 pre/post window stability; C10 identical declared F0 hash across
schemas; C11 shared-core comparator sensitivity; plus the strict-YAML control set
(C1–C10) in `census.json` (all pass; current state 8/8 YAML strict-OK, 0 duplicate keys,
0 JSON advisory duplicates).

## 5. Falsifier

Any of: (a) a predecessor or successor sha256 here differs from a fresh measurement of the
same path; (b) a semantic delta between the pinned predecessor and rev12 that this census
missed, or a metadata-classified path that in fact changes class semantics (the top-level
exclusion list is published in `rev12_delta_census.py`); (c) a binding reported resolved
whose fragment does not resolve, or vice versa; (d) a predecessor revision stamp absent
from `revision_history` that is present in the predecessor raw header; (e) pre/post window
hashes differ.

## 6. Limits

- Structure and bindings only; no mathematical adjudication of rev12.
- Semantic/metadata classification is by the published top-level exclusion list; anything
  outside it counts as semantic by default.
- Binding counts are a point-in-time corpus scan; the controller gate audit is authoritative.
- Read-only: this census proposes no edit to any owned artifact.

## 7. Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-065/strict_yaml_census/census.py            # strict-YAML census, exit 0
python3 artifacts/worker-065/strict_yaml_census/rev12_delta_census.py  # delta/binding census, exit 0
```

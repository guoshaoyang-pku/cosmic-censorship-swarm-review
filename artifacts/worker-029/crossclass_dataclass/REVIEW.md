# W029-CROSSCLASS-DATACLASS-02 — cross-schema data-class / C0⇒C2 transfer measurement

Worker: `worker-029` · Node: `F1,F2a,F2b` · Classes: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` · Gate: `G-FORM`
Kind: **artifact-and-checker measurement — not a theorem; no gate verdict moved.**

## Question

`research_map.json → G-FORM.unmet` records: *"no single frozen data class (s,delta,norm) is shared by
F1/F2a/F2b, which disables the licensed C0⇒C2 transfer."* This task measures that criterion at the
frozen hashes with a deterministic, read-only checker and separates what is true from what is stale.

Frozen inputs (snapshots, `snapshots/`, sha256 prefixes):

| node | artifact | sha256 |
|---|---|---|
| F1 | `schemas/af_wcc_vacuum.yaml` | `9a8bd4c96800…` |
| F2a | `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d…` |
| F2b | `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b357…` |
| F0 | `research_map/formulation_taxonomy.yaml` | `276009f4f63d…` |

No live drift was measured after snapshotting (`live_drift_vs_snapshot=false` for all three schemas).

## Measured result

**Verdict: `CONFIRMED_UNMET`.** The criterion is real, but the recorded phrasing is half stale:

1. **W029C-01 (pass).** After normalization (citation-status/ownership prose, parenthetical naming),
   the mathematical data class is **identical in all three schemas**: matter `none`, Λ = 0, Einstein
   vacuum, same Hamiltonian/momentum constraints, same smooth-with-decay default, same Sobolev pair
   `s > 5/2`, `delta ∈ (1/2,1)`, same asymptotic decay. So "the three schemas use different data
   classes" would be wrong.
2. **W029C-02 (info).** Structurally F1 is *not* key-identical to F2a/F2b: F1 has an extra
   `data_class.excluded_data`, `adm_mass.rigidity` but no `adm_mass.locator`, and different
   parity/quotient wording; F2a and F2b are key-identical (F2b adds one `hypotheses_reconciliation`
   key and a longer locator). These are bookkeeping deltas, not a different data class.
3. **W029C-03 (hard for the gate criterion).** **No single `(s,delta,norm)` is frozen.** In all three
   schemas `D0` is a two-member domain — `"Sobolev variant s > 5/2 and delta in (1/2,1), or the
   smooth-with-decay default"` (`F1:65`, `F2a:58`, `F2b:59`) — while the formal quantifier is
   `forall (s,delta) in D0: …` (`F1:49`, `F2a:48`, `F2b:49`). The smooth member carries no
   `(s,delta)` coordinates, so the binder is ill-typed on it and the class reads as a family of two
   statements. The `unmet` item stands.
4. **W029C-04 (major).** The C0⇒C2 transfer is recorded in both SCC ledgers
   (`F2a:244`, `F2b:246`), but F1's `must_not_conflate` (`F1:142-143`) forbids transferring
   smooth-data statements to the Sobolev variant **without an approximation/stability argument**,
   and no such argument is recorded in any of the four artifacts (keyword scan: 0 hits). With a
   disjunctive D0 the transfer is therefore unconditional only member-wise.
5. **W029C-05 (minor).** F2b retains `"No containment with C2 or C0 is asserted here"` (`F2b:157`)
   while its own ledger asserts `E_H2loc ⊂ E_C0` (`F2b:244-246`); F2a carries the corrected wording
   (`F2a:157` explicitly calls the older sentence wrong).
6. **W029C-06 (info).** The duplicate-top-level-key defect class is cross-schema: all three frozen
   schemas repeat `revised_at` (7 duplicate occurrences each; F1 additionally `revised_at_unused`),
   so PyYAML last-wins silently discards the revision timeline.

## Falsifier

Any revision in which `D0` names a single pair-indexed domain that supplies `(s,delta)` for every
member (or the smooth member is moved to a registered variant), **and** in which the C0⇒C2 transfer
carries a recorded approximation/stability argument (or F1's prohibition is withdrawn), falsifies
this measurement. A live hash different from the pinned snapshots also voids it.

## Artifacts

| artifact | sha256 |
|---|---|
| `check_crossclass_dataclass.py` | `ee51ebbedd92…` (deterministic: byte-identical rerun) |
| `evidence.json` | `59c40217580d…` |
| `report.json` | `47838a482ce6…` |
| `snapshots/` | four byte copies, hashes in `evidence.json.inputs` |

## Non-claims and limitations

- This is worker-level evidence; per `ASTRA_HANDOFF`, worker events cannot set `status=done`,
  `validation_status=passed`, or a gate verdict.
- H1's normalization choice is itself reported: the raw structural diffs are in
  `evidence.json.hypotheses.H1_cross_schema_same_data_class.structural_diff_*`, so a reader can
  reject the normalization without re-running the extraction.
- No canonical artifact was edited; the `class_contract_pointer`/canonical-binding blocker filed by
  worker-005/090 is referenced, not re-adjudicated here.

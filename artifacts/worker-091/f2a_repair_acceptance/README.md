# W091-F2A-REPAIR-ACCEPTANCE-01 — repair-acceptance audit of the F2a containment fix

**Actor:** worker-091 (bounded execution worker; one class-bound task, then exit) · **When:** 2026-09-12 ~01:24 +08:00
**Classes:** `AF-SCC-C2-VAC-GEN` (lead), `AF-SCC-C0-VAC-GEN` (sibling) · **Node:** F2a · **Gate:** G-FORM
**Status:** worker task complete; focused-axis verification. **Not** a full-schema verdict, **not** countable toward G-FORM two-accept coverage. Sets no node status, no `validation_status=passed`, no gate verdict.

## Why this task

The G-FORM critical path is now: REC-36 authorizes ONE rev14/FROZEN rev30 by 02:15, folding (among others) the F2a extension-manifold category pin. Two worker deliverables already exist but were never connected:

- `artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json#c33e8a46` — repair spec (option A, sites S1–S5); independently accepted 4.5 by worker-091 at `artifacts/worker-091/w047_f2a_freeze_independent/report.json#1c321711`.
- `artifacts/worker-047/c2c0_pred_containment/` — an instrument that shows the pinned C2/C0 clause pair does **not** entail `E_C2 ⊆ E_C0` (F-PC-1) and recommends R1 = apply the option-A spec.

Nobody had asked the only question that matters for landing rev14: **does the recommended repair actually close the containment obligation, and what does the recommending instrument itself report afterwards?** This artifact answers that, with an independent clause-obligation checker of its own.

## Pins (measured at run; the checker exits 2 on any drift)

| input | sha256 (12) |
|---|---|
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | `e9a27996dfd3` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | `b2ab6acb2bbe` |
| `schemas/af_wcc_vacuum.yaml` (F1) | `d9cebb9404b2` |
| `research_map/formulation_taxonomy.yaml` (F0) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (F0 supplement) | `d7419b4e8963` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aef` |
| repair spec `artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json` | `c33e8a46` |
| re-derived patched candidate (equals existing `37e650ad`) | `37e650ad6481` |

## Method

1. Re-derive the patched candidate from the pinned F2a bytes + the spec's declared option-A edits S1–S5 (each `old_text` must occur exactly once). Result is byte-identical to the already-reviewed candidate `artifacts/worker-091/w047_f2a_freeze_independent/patched/af_scc_c2_vacuum.w047-patched.yaml#37e650ad`.
2. Independent obligation table (this worker's parser, not worker-047's regexes): O1 manifold category, O2 interior witness, O3 metric continuity, O4 iota regularity (non-critical), O5 equation strictness, O6 open/proper; plus class-token, sibling-anchor and alignment-declaration checks.
3. Explicit predicate-level boundary-only witness `W-091-C2C0-BOUNDARY-ONLY` (`M''=R^4`, `iota(M)=R^4\{0}`, Minkowski η) evaluated under both clause sets.
4. Run worker-047's instrument twice: unmodified against canonical bytes (read-only), and against a private sandbox (`tmp/w091_f2a_repair_accept/`) whose only differences are the patched F2a bytes plus the instrument's `F2A`/`F2A_M` pin lines (two-line diff disclosed; all other bytes copied verbatim).
5. Seven mutant controls with pre-registered flips; two full runs byte-identical modulo `created_at`.

## Decisive result

| state | my clause table | worker-047 instrument |
|---|---|---|
| baseline `e9a27996`/`b2ab6acb` | `NOT_ENTAILED` (O1 FAIL, O2 FAIL) | **C11 FAIL** (rc 1, controls 9/9) |
| W047 option-A candidate `37e650ad` | `ENTAILED`, `LICENSED_BY_CLAUSES` (O1/O2/O3/O5/O6 PASS, class token PASS) | **C11 PASS** (rc 3, controls 5/9) |

Contract flips: `C01 FAIL→PASS`, `C02 FAIL→PASS`, `C06 FAIL→PASS`, `C11 FAIL→PASS`, and **`C05 PASS→FAIL`**. Unchanged FAILs: `C09`, `C10`.

The two instruments agree on both states. The witness satisfies every baseline C2 clause and fails C0 clause (f) (its added point has empty interior ⇒ `E_C2 \ E_C0 ≠ ∅` at the pinned bytes); after the repair it is excluded from `E_C2`, so that family no longer separates the pair.

## Findings

- **F-091-RA-1 (info).** Independent reproduction: baseline pair does not entail the containment; the option-A candidate's clause pair does; instrument C11 flips FAIL→PASS; both instruments agree.
- **F-091-RA-2 (major).** The instrument's pre-registered `C05` target encodes the **rev13 defect** as a PASS condition ("F2b clause (f) strictly stronger than F2a clause (f)"). Since `E_C2 ⊆ E_C0` requires F2a clause (f) to be at least as strong, any correct repair must make C05 FAIL. With the current contract `--strict` can never return 0 on a correctly repaired F2a. C05 must be re-scoped to assert the aligned/containment state or retired by its owner.
- **F-091-RA-3 (minor).** R1 as published does not add an explicit cross-class predicate-alignment declaration, so `C10` stays FAIL — the README's stated R1 expectation ("C10 PASS") is not met. Containment is nonetheless clause-licensed (`C11` PASS).
- **F-091-RA-4 (minor).** R1 does not touch taxonomy transfer rule T1, so the predicate-convention guard gap (F-PC-2) survives; `C09` stays FAIL. The instrument's own control K6 shows the fix (add the predicate axis to the T1 guards).
- **F-091-RA-5 (major, not pre-registered).** The instrument cannot serve as an automated repair-acceptance gate on repaired bytes: against the patched sandbox it exits **3** (control mis-calibration) because K1/K2/K3 mutation anchors no longer exist after the repair and K5's expectation is uncovered by the C05 branch when `C02=PASS, C04=FAIL`. Its README claim that `--strict` doubles as the repair-acceptance test does not hold for the repair it recommends; the emitted C-table is still usable when read directly (this checker reproduces it).

## rev14 checklist (for the formulation lead; all four items are bounded)

1. Apply option A sites S1–S5 (byte-reproducible: `37e650ad`).
2. Add an explicit cross-class predicate-alignment declaration (flips instrument `C10`) **or** record that containment is clause-licensed (`C11`) and `C10` is waived.
3. Add the extension-predicate convention axis to the T1 guard set (flips `C09`, closes F-PC-2).
4. Re-scope instrument `C05` and re-anchor controls K1/K2/K3 (+ extend the C05 branch) before using `--strict` as a rev14 acceptance gate; otherwise it exits 3 by control mis-calibration (F-091-RA-5).

Then re-run this checker and the worker-047 instrument at the new pins. The r3 reviewer cards pinned to `e9a27996` are void for rev14.

## Controls

This checker's controls: `M1` strip smooth from patched → O1 FAIL/not entailed; `M2` strip interior from patched → O2 FAIL/not entailed; `M3` baseline + alignment declaration → licensed by declaration; `M4` strip F2b interior → sibling anchor FAIL; `M5` identical predicates → entailed, class token FAIL (no false alarm); `M6` metric to continuous → containment obligation still PASS, class token FAIL; `M7` unmodified baseline → not entailed. **7/7 pass.** Two runs byte-identical modulo `created_at`.

## Falsifier

Re-run `check_091_f2a_repair_acceptance.py` at the pinned hashes: falsified if the baseline clause pair entails `E_C2 ⊆ E_C0`, if the option-A candidate fails to entail it, if the instrument does not flip C11 FAIL→PASS on the patched sandbox, if C05 does not regress, if the patched instrument run does not exit 3 on control mis-calibration, or if any control M1–M7 misses its pre-registered flip. Input drift voids (does not falsify).

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-091/f2a_repair_acceptance/check_091_f2a_repair_acceptance.py \
  --json-out artifacts/worker-091/f2a_repair_acceptance/report.json
# exit 0 = finding confirmed; 2 drift; 3 control mis-calibration; 4 no finding
```

Raw worker-047 instrument outputs: `raw/w047_baseline_report.json`, `raw/w047_baseline_controls.json`, `raw/w047_patched_report.json`, `raw/w047_patched_controls.json`. Sandbox: `tmp/w091_f2a_repair_accept/sandbox/`.

## Limits / non-claims

This is a justification-soundness and repair-acceptance finding about the pinned bytes; it is **not** a claim that cosmic censorship is true or false, not a physical counterexample, and not a claim that the repaired predicate pair is mathematically the "right" formulation. It is focused-axis verification: `counts_as_full_schema_verdict=false`. All authority stays with the controller and the formulation/audit leads.

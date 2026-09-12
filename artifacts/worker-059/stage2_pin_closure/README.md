# W059-GFORM-STAGE2-PIN-CLOSURE-01 — the unpinned stage-2 instrument

- **worker**: worker-059 (bounded execution worker; no card existed in `comms/inbox/worker-059.jsonl`,
  so one bounded class-bound task was self-selected from the live formulation-lead blocker
  `lead-form-life08-123` and the G-FORM r3 `required_before_proposal` item "pin the stage-2 tool").
- **nodes / classes / gate**: `F1,F2a,F2b`; `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
  `AF-SCC-C0-VAC-GEN`; context `G-FORM` (also bears on `G-AUDIT` evidence binding).
- **authority**: worker measurement only. No canonical file written, no node `status=done`, no
  `validation_status=passed`, no gate verdict. All mutation writes are confined to
  `artifacts/worker-059/stage2_pin_closure/work/`.
- **input pins**: FROZEN rev29 `815e08079aefbc16…`; `run_acceptance.py` `e544c36d2d16…`;
  `check_class_schema.py` `000e09e46b2f…`; stage-2 engine `spec_conformance_audit.py`
  `c79d8ab8440a…`; `rule_spec.json` `40f9bb9e657b…`; the three canonical schemas
  `d9cebb9404b2…` / `e9a27996dfd3…` / `b2ab6acb2bbe…`.

## Headline

**HF-059-STAGE2-01 — a gate-relevant verdict is controlled by bytes that no FROZEN pin covers.**
At the frozen pins, stage 2 rejects the *untouched* canonical F1 on R03
(`{"verdict":"reject","failed_rules":["R03"]}`, exit 1). A **one-line edit confined to the
unpinned stage-2 engine** (exact-substring binder test → variable-wise binder test, the
`cand_E3` repair shape) flips that verdict to `{"verdict":"accept","failed_rules":[]}`, exit 0,
while **all 50 FROZEN rev29 pins still measure exactly as pinned** (E9, E10; the mutated file is
not in `FROZEN.json`: 0 occurrences). `run_acceptance.py` (pinned) resolves stage 2 to this
unpinned engine, so the pipeline's decision function is not hash-bound end to end. This is the
same failure class as CF-26/CF-29 and independently reproduces `lead-form-life08-123`.

**HF-059-STAGE2-02 — the closure is mostly unpinned.** Static references + an audit-hook trace of
the actual stage-1 / stage-2 / stage-2-selftest runs give a 48-file repo-local closure:
**11 PINNED_OK, 37 UNPINNED_UNTRACKED** (the engine itself plus 36 fixture/manifest files).
Stage 2's dynamic read set is `{engine, rule_spec.json, schema}` for a single-schema run and 38
repo files for `--selftest`. Nothing in the closure is `PINNED_STALE`.

**HF-059-STAGE2-03 — the edit also removes the last scope discriminator.** At the pinned lead
variant bytes (`tmp/lead-form-life08/variant_*`, hashes in `report.json`): baseline rejects both
the *correct variable-wise* rendering and the *negation-scope-error* rendering on R03, and accepts
the grouped-tuple rendering; the mutated engine accepts **all three**. The mutation is not a
blanket disable — the leak control `sem12_theorem_promotion.yaml` is still rejected on R11
(E11, E13, E14). This independently reproduces the lead's cand_E3 scope-safety finding.

**OBS-1 — live pin drift during the measurement window.** `artifacts/formulation/tools/check_variant_registry.py`
is pinned `c471da4b7be9…` in FROZEN rev29 but measured `8c7ef46f11db…` (mtime 01:21:56, i.e. the
REC-36 item-5 instrument being edited in the rev14 window). The harness introduced no drift
(`drift_after == drift_before`), and the drift is reported as an observation, not silently
absorbed. FROZEN rev29 was therefore not byte-stable at `measured_at`.

**OBS-2 — preflight still non-reproducible.** `run_acceptance.py` exits 3:
`corpus base 1bb78ce9b357… / current base b2ab6acb2bbe…`, reproducing CF-32(i) at these bytes.

## Result table (frozen pins, sandbox mutation control)

| fixture | baseline stage 2 | mutated engine | control role |
|---|---|---|---|
| canonical `schemas/af_wcc_vacuum.yaml` | reject `R03` | **accept** | governance gap (E8/E9) |
| variant variable-wise (correct) | reject `R03` | accept | scope probe |
| variant grouped-tuple (correct) | accept | accept | positive control (E14) |
| variant scope-error (q-only negation) | reject `R03` | **accept** | scope discrimination lost (E11) |
| `sem12_theorem_promotion.yaml` (leak) | reject `R11` | reject `R11` | negative control (E13) |

Mutation isolation: exactly one file differs between the pristine and mutated sandbox trees —
`artifacts/worker-06/spec_conformance_audit.py` (E12).

## Reproduce / falsify

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-059/stage2_pin_closure/check_stage2_closure.py        # exit 0, ALL_PASS=True
python3 artifacts/worker-059/stage2_pin_closure/check_stage2_closure.py --verify  # digest MATCH
```

Expected: `measurement_digest = 2bc4478381998763…`, `expectations 14/14`, `mutants 3/3`,
`drift_before == drift_after`, and the verdict matrix above. **Falsified** if any expectation
flips, any FROZEN rev29 pin measures differently (the harness will show it in
`pin_drift_before`), the canonical F1 verdict after the sandbox R03 edit is not `accept`, or the
engine becomes pinned in a later FROZEN revision without the report being re-issued. The digest
is computed over deterministic measurement fields only (no wall-clock); worktree drift changes it
by design.

## Files

| file | role |
|---|---|
| `check_stage2_closure.py` | deterministic harness: pin census, static+dynamic closure, classification, sandbox mutation control, expectations/mutants, digest |
| `trace_run.py` | `sys.addaudithook` file-access tracer used for the dynamic closure |
| `report.json` | full measurement (`measurement_digest 2bc4478381998763…`; worktree observations outside the digest) |
| `raw/` | per-run traces, stdout/stderr, stage-2 verdict JSONs |
| `work/pristine`, `work/mutated` | byte-identical sandbox copies except the single R03 mutation |

## Non-claims

Not a gate verdict, not a node completion, not a claim that the R03 repair is wrong. The repair
direction is the lead's and worker-006's to land; this artifact only measures that the file which
would carry it is outside the pin set, and supplies the mutation control that shows why that
matters for G-FORM evidence binding.

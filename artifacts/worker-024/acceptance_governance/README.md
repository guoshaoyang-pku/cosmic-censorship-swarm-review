# W024-ACCEPTANCE-GOVERNANCE-01 — G-FORM acceptance pipeline: instrument-governance gap and fail-open audit

**Class binding:** `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN` · node `F1,F2a,F2b` · gate `G-FORM`
**Claim kind:** instrument-and-pipeline measurement (not a mathematics claim, not a gate verdict)
**Canonical writes:** none. Every case runs in a fresh ROOT-relative sandbox; 6/6 entry pins re-measured unchanged at exit (see `exit_hashes.json`).

## Result in one paragraph

The G-FORM acceptance pipeline is only half hash-bound and it fails open on an incomplete
corpus. `FROZEN.json` (rev29, `815e08079aef`) pins the runner
`artifacts/formulation/tools/run_acceptance.py` (`e544c36d2d16`) and stage 1
`check_class_schema.py` (`000e09e46b2f`), but contains **zero occurrences** of the stage-2
rule engine `artifacts/worker-06/spec_conformance_audit.py` (`c79d8ab8440a`) and **zero** of
the `rebased_fixtures/` mutant corpus — both of which the pinned runner executes. Executed
consequence, not just an assertion: a corpus member that escapes both stages moves the
pipeline to `FAIL 31/32` (`rc=1`); a name-keyed edit of **only the unpinned stage-2 tool**
then yields `PASS 32/32` (`rc=0`) while all six pinned tool-chain artifacts hash-verify
clean. Separately: an empty corpus returns `PASS rc=0` with `mutants.total=0`; a missing
controls pair returns `PASS rc=0` with `controls=[]`; a no-op stage 2 still returns `PASS`
because all 31 fixtures already fail stage 1 structurally on R22/`revised_at_unused`. The
pinned report `acceptance_pipeline_report.json` (`9b7d6c8208d3`) is rewritten
unconditionally at the end of every non-preflight run — including the vacuous `PASS` — and
is not reproducible under the pinned `KEY_MANIFEST` (`014e2d30`) at its own declared corpus
base. A proposed fail-closed patch (proposal only, not applied) closes all of it on sandbox
copies: four refusal cases at `rc=3` with `REASON` lines, the synthetic healthy control at
`PASS rc=0`, and a no-`--write` path that leaves the pinned report byte-identical.

This extends the formulation lead's open blocker `lead-form-20260912T011509-123` from a
static "0 occurrences in FROZEN" assertion to an executed FAIL→PASS laundering
demonstration, and it is offered as evidence for a new CF (CF-33 candidate, emitted as a
`blocker` event).

## Pins (entry == exit, measured before and after)

| input | sha256 (12) | note |
|---|---|---|
| `artifacts/formulation/tools/run_acceptance.py` | `e544c36d2d16` | **pinned** in FROZEN rev29 |
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2f` | **pinned**; stage 1 |
| `artifacts/worker-06/spec_conformance_audit.py` | `c79d8ab8440a` | stage 2 — **not in FROZEN** |
| `artifacts/formulation/FROZEN.json` | `815e08079aef` | rev29, 50 pins |
| `artifacts/formulation/evidence/semantic_escape_rebased.json` | `7e44de0e3906` | declares base `1bb78ce9b357`, `mutants_rebased=31`, 2 controls |
| `artifacts/formulation/evidence/acceptance_pipeline_report.json` | `9b7d6c8208d3` | **pinned**, claims canonical 3/3 pass, union 31/31 |
| `rebased_fixtures/` (33 files) | tree `cf45cffa59d3`¹ | corpus — **not in FROZEN** |

¹ corpus tree rollup as measured by `drive_governance.py::tree_hash`; see `entry_hashes.json`.

## Method

- Each case is built by `drive_governance.py` under `sandboxes/<case>/` with the same
  relative layout the runner expects (`ROOT = __file__.parents[3]`), so the unmodified
  pinned runner resolves every path inside the sandbox. The canonical tree is never written.
- `rebind=True` (all cases except T0/T1) rewrites **only the sandbox copy** of
  `semantic_escape_rebased.json`'s `base_sha256` to the sandbox C0 hash. This simulates the
  post-rebind state that REC-36 item 7 calls for, without running the writer and without
  touching the canonical evidence.
- The synthetic healthy control uses `af_wcc_vacuum.yaml#ebb8d6671614` (a WCC revision that
  passes **both** stages under the live pinned tools+manifest) and replaces the two shipped
  controls with canonical bytes that pass both stages. This is necessary because **no live
  WCC revision passes stage 2** (R03 literal-substring binder) and **no pre-rev13 C0 passes
  stage 1** (R22/`revised_at_unused`), i.e. the shipped configuration has no live PASS path.
- `pin_stage2=True` (P-cases only) registers the stage-2 tool in the **sandbox**
  `FROZEN.json`, simulating the rev14 pin registration that REC-36/REC-41 require. The live
  `FROZEN.json` is untouched; T7/T8 use the live pin set.
- Every run records `rc`, stdout, the resulting report file and its sha256; the driver
  re-runs the FROZEN pin scan per sandbox and exits 3 on any assertion failure or pin drift.

## Case matrix

| case | configuration | rc | verdict | mutants (total / union / sem / struct) | pinned report sha |
|---|---|---|---|---|---|
| T0 | live C0 + canonical evidence | **3** | — | not run | unchanged `9b7d6c8208d3` |
| T1 | report-time triple (WCC `9a8bd4c9`, C2 `b6123750`, C0 `1bb78ce9`), live pinned manifest | 1 | **FAIL** | 31 / 31 / 11 / 31 | clobbered `4060d812e973` |
| T2 | healthy, **corpus emptied** | **0** | **PASS** | **0 / – / 0 / 0** | clobbered `7d4d2da72be7` |
| T3 | healthy, **controls removed** | **0** | **PASS** | 31 / 31 / 11 / 31, `controls=[]` | clobbered `6c2efabdc4f5` |
| T4 | healthy, **stage-2 replaced by no-op** | **0** | **PASS** | 31 / 31 / **0** / 31 | clobbered `69a25ce330fd` |
| T5 | healthy + one escaping corpus member | 1 | **FAIL** | 32 / **31** / 11 / 31 | clobbered `7607ce2a167e` |
| T6 | T5 corpus + **name-keyed edit of the unpinned stage-2** | **0** | **PASS** | 32 / **32** / 12 / 31 | clobbered `31ecd43dc3a6` |
| T7 | FROZEN pin scan of the T6 sandbox | — | — | 6/6 pinned tool-chain artifacts match; stage-2 absent from pins and diverged | — |
| T8 | positive control: append a comment to the pinned runner | — | — | runner reported in `mismatch` | — |
| P-pre | patched copy vs live FROZEN (stage-2 unpinned) | 3 | REFUSED | `REASON: stage-2 tool NOT in FROZEN pins` | unchanged |
| P0 | patched copy, healthy, `--write` | 0 | **PASS** | with `inputs` sha256 block | written (sandbox) |
| P0b | patched copy, healthy, no `--write` | 0 | PASS | — | **byte-identical** |
| P1 | patched copy, empty corpus | 3 | REFUSED | `REASON: corpus mutant count 0 != declared 31` | unchanged |
| P2 | patched copy, controls removed | 3 | REFUSED | `REASON: control count 0 != declared 2` | unchanged |
| P3 | patched copy, unpinned stage-2 edited | 3 | REFUSED | `REASON: stage-2 tool sha256 ... != evidence ...` | unchanged |
| P4 | patched copy, extra corpus member | 3 | REFUSED | `REASON: corpus mutant count 32 != declared 31` | unchanged |

Exact per-case rc/stdout/report hashes and every assertion: `report.json` and
`raw_results.json`. Summarised findings with the same numbers: `report.json#findings`.

## Mechanism (line-anchored, `run_acceptance.py#e544c36d2d16`)

1. **Empty corpus is a PASS.** L82 globs `rebased_fixtures/*.yaml` with no count assertion;
   L112 guards the union check with `if m["total"] and ...`, so `total == 0` skips the only
   acceptance condition and leaves `verdict = "PASS"` (T2).
2. **Controls are not required.** L82–L91 only classify controls that exist; nothing asserts
   that the declared pair is present (T3).
3. **Stage 2 is not load-bearing in the current byte set.** Every one of the 31 fixtures
   fails stage 1 on R22 (`unknown keys ... revised_at_unused`), so the union is 31/31
   whatever stage 2 does; a no-op stage 2 still yields `PASS` (T4). The pinned report's
   `structural 30/31, semantic 11/31` describes a different `KEY_MANIFEST` revision.
4. **No write guard.** L126–L127 `dest.write_text(...)` runs unconditionally at the end of
   every non-preflight run (T1/T2/T5/T6 all rewrite the pinned evidence file).
5. **The pin set does not close the execution chain.** `FROZEN.json` pins the runner but not
   the stage-2 tool it invokes (T7) — the "same failure class as CF-26/CF-29" the
   formulation lead recorded, now executed: editing only that file flips FAIL→PASS.

## Proposed patch (`proposed_fail_closed_patch.diff`, applied=False)

`patched/run_acceptance.patched.py` adds:

- **P1** declared corpus totals enforced against disk (`summary.mutants_rebased`, `len(controls)`);
- **P2** stage-2 hash-bound to evidence `w06_sha256` **and** to the FROZEN pin set;
- **P3** stage-1 hash-bound to evidence `gate_sha256` **and** to FROZEN;
- **P4** atomic report write, only under `--write`, with an `inputs` sha256 block.

Verified on sandbox copies: P1–P4 refuse at `rc=3` with explicit `REASON` lines, the healthy
control stays `PASS rc=0`, and the no-`--write` path leaves the pinned report byte-identical.
Because the live FROZEN does not pin stage 2, the patched copy **refuses even the healthy
corpus** until the owner registers that pin (P-pre) — the patch is a precondition for, not a
substitute for, the rev14/FROZEN-rev30 pin registration.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-024/acceptance_governance/drive_governance.py   # exit 0 iff all assertions hold
python3 artifacts/worker-024/acceptance_governance/emit_events.py       # report.json + exit_hashes.json + outbox
```

## Falsifier

Re-run `drive_governance.py` at the entry pins in `entry_hashes.json`. FALSIFIED if any
per-case rc/verdict/mutant-count differs from `report.json`; if the stage-2 path appears in
`FROZEN.json` pins; if the FROZEN tool-chain scan catches the name-keyed stage-2 edit; if the
pinned report is reproduced as PASS under the pinned `KEY_MANIFEST` at the declared corpus
base; or if the patched copy fails to refuse P1–P4 at `rc=3` while P0 stays `rc=0`.

## Limits and residual risk

- This is an instrumentation audit; it makes no claim about whether the 31 fixtures really
  are semantic leaks or about F1/F2a/F2b content. The corpus ground truth is
  `semantic_escape_rebased.json` as written.
- The synthetic healthy control and the sandbox FROZEN registration are declared
  substitutions (see Method); they demonstrate the patch's behaviour, not a live PASS.
- The T1 result shows the pinned report and the pinned `KEY_MANIFEST` are mutually
  inconsistent; which artifact should move is an owner/lead decision (REC-36 item 7).
- `rebased_fixtures` tree hash is the driver's rollup, not a FROZEN-declared pin.
- Worker authority: no gate verdict, no `validation_status=passed`, no node transition, no
  canonical file written.

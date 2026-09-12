# W086-GFORM-SUITE-REPL-01 — pre-registration (written before any measurement)

Actor: worker-086. Node: F1,F2a,F2b. Gate: G-FORM.
Class ids: AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN.
Taken from the immediate queue (no inbox card exists for worker-086): the canonical G-FORM
gate suite `artifacts/formulation/tools/run_gate_tests.py` is pinned by FROZEN rev29 but its
recorded report `artifacts/formulation/evidence/gate_test_report.json#26540a6b43cc` was last
independently re-run at FROZEN rev28 (worker-16, 00:38) and has **no rev29/rev13 independent
re-run** in the accepted stream (checked at 01:05; the formulation lead's 01:03 independent
lifecycle re-ran the four formulation checkers, not this suite).

## Question

At the FROZEN rev29 / schema rev13 pins, does a pristine-sandbox re-run of the pinned gate
suite reproduce the frozen gate-test evidence exactly, and are the canonical schemas the
suite exercises via the `artifacts/formulation/schemas/` mirror byte-identical to the held
canonical `schemas/` bytes?

Scope: read-only on every canonical path. The suite rewrites fixtures and its report on each
run, so it is executed only inside a sandbox copy under
`artifacts/worker-086/gform_suite_rev29/sandbox/`. No canonical byte is written.

## Pinned inputs (FROZEN rev29 815e08079aef, frozen_at 2026-09-12T00:57:26+08:00)

| path | sha256 |
|---|---|
| artifacts/formulation/tools/run_gate_tests.py | 78509c9eb8b1548231f3e701245e48084916b044b5d1485bb96006563a59dffa |
| artifacts/formulation/tools/check_class_schema.py | 000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff |
| schemas/af_wcc_vacuum.yaml | d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d |
| schemas/af_scc_c2_vacuum.yaml | e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe |
| schemas/af_scc_c0_vacuum.yaml | b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c |
| artifacts/formulation/schemas/af_wcc_vacuum.yaml | d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d |
| artifacts/formulation/schemas/af_scc_c2_vacuum.yaml | e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe |
| artifacts/formulation/schemas/af_scc_c0_vacuum.yaml | b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c |
| artifacts/formulation/rule_spec.json | 40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e |
| artifacts/formulation/KEY_MANIFEST.json | 014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a |
| artifacts/formulation/formulation_taxonomy.yaml | d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1 |
| artifacts/formulation/evidence/gate_test_report.json | 26540a6b43ccc7b8c640ab4f2566240a20829d86677e22f00244c8b1d923ff5b |
| artifacts/formulation/FROZEN.json | 815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0 |

## Acceptance predicate (all must hold; any failure is a hard failure)

- **P1** every pinned input above measures the listed sha256 at entry, and the three
  canonical/mirror schema pairs are byte-identical (mirror-pair policy).
- **P2** sandbox run #1 of `run_gate_tests.py` exits 0 and its `gate_test_report.json` has
  `verdict == "PASS"`, `counts == {canonical_pass 3/3, null_controls_pass 6/6,
  mutants_caught 31/31, rephrased_caught 2/5}`, `self_application.clean == true`.
- **P3** sandbox run #2 is byte-identical to run #1 (content determinism, no timestamps).
- **P4** the run report and .txt, normalized by substituting only the sandbox root path with
  the repo root path, are byte-identical to the frozen `gate_test_report.{json,txt}`.
- **P5** exit frame: every pinned input still measures its entry sha256 after both runs; the
  sandbox generated fixture/report files are the only files that changed.
- **P6** controls fire:
  - C1 injected-defect liveness: in a scratch clone, removing `visibility` from the WCC
    mirror schema makes `check_class_schema.py` exit non-zero with rule `R10` in
    `failed_rules` (the suite can fail in this sandbox);
  - C2 drift-detector liveness: a one-byte flip in a scratch clone input is reported as a
    hash mismatch by the pin frame;
  - C3 deterministic double-run equality is itself a control that the pipeline is not
    time/random dependent.

## Falsifier

This replication is falsified by: any pinned input hash moving by exit; run exit != 0 or any
count differing; the normalized run report differing from the frozen report at any byte; or a
control that fails to fire. Conversely, if all checks hold, the claim is limited to: the
frozen gate-test evidence is reproducible from the pinned tool and bytes in a pristine sandbox
at this instant — not a gate verdict, not a node completion, and not a re-derivation of the
rules' semantics.

## Non-claims

- No statement about whether the gate's rule set is sufficient or whether G-FORM should pass.
- No edit to any canonical artifact, fixture, report, map or event stream.
- `counts_as_full_schema_verdict=false` for any review event emitted by this task.

Written 2026-09-12 ~01:06 +08:00 before the instrument was executed.

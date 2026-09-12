# W086-GFORM-SUITE-REPL-01 — pristine-sandbox replication of the G-FORM gate suite

Actor: worker-086. Node: F1,F2a,F2b. Gate: G-FORM.
Class ids: AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN.

## Why this task

The canonical G-FORM acceptance suite `artifacts/formulation/tools/run_gate_tests.py`
(sha256 `78509c9eb8b1…`) is hash-pinned by FROZEN rev29 `815e08079aef` together with its
recorded evidence `artifacts/formulation/evidence/gate_test_report.json`
(`26540a6b43cc…`). The last *independent* re-run in the accepted stream was at FROZEN rev28
(worker-16, 00:38); the formulation lead's 01:03 independent lifecycle re-ran the four
formulation checkers but not this suite. No rev29/rev13 independent re-run existed. The suite
mutates fixtures and its own report on every run, so it can only be re-run in a sandbox.

## Method

`verify_suite_rev29.py` (written and hashed before execution; acceptance predicate frozen in
`PREREGISTRATION.md#c1a7f9bc6b21`):

1. Measures 13 pre-registered pins (three canonical schemas, their three
   `artifacts/formulation/schemas/` mirror copies, the suite and checker tools, rule spec,
   KEY_MANIFEST, companion taxonomy, frozen report, FROZEN.json) and checks the mirror pairs
   are byte-identical.
2. Copies `artifacts/formulation/` into `sandbox/` (read-only on the canonical tree) and runs
   the pinned suite twice there.
3. Normalizes the sandbox run report by substituting only the sandbox root path with the repo
   root path, then compares bytes with the frozen report.
4. Runs two liveness controls: an injected defect (drop `visibility` from the WCC mirror
   schema) must make the checker fail with `R10`; a one-byte flip in a scratch input must be
   flagged by the pin frame.
5. Re-measures every pinned input at exit (zero drift required).

## Result — `GATE_SUITE_EVIDENCE_REPRODUCED_EXACTLY` (10/10 checks)

| check | measured |
|---|---|
| P1 entry pins (13) | all match FROZEN rev29 |
| P1b FROZEN declaration agrees | 13/13 |
| P1c canonical ↔ mirror schema identity | 3/3 byte-identical |
| P2 sandbox run #1 | exit 0; PASS; canonical 3/3, controls 6/6, mutants 31/31, rephrased 2/5; self-application clean |
| P3 run #2 determinism | report sha `bc14934ff3ca…`, txt sha `f1f229d829d4…` identical both runs |
| P4 normalized run vs frozen report | JSON byte-identical, TXT byte-identical; `frozen_vs_run.diff` empty |
| P6a injected-defect control | checker exit 1, `failed_rules=[R10]` |
| P6b drift-detector control | byte flip detected by the pin frame |
| P5 exit frame | 0/13 pinned inputs moved; sandbox inputs stable |
| P5b sandbox frame | sandbox pin set unchanged across runs |

Frozen report `canonical_sha256` equals the three live canonical schema hashes
`d9cebb94…` / `e9a27996…` / `b2ab6acb…`.

The run report is 12 243 bytes at sandbox paths vs the frozen 11 820 bytes; the 423-byte
difference is exactly the longer sandbox root path repeated in 3 canonical + 42 fixture
`schema` fields. After the path-only normalization the bytes are identical — so the frozen
report is the rev13 output, not stale rev12 content.

## Observation (info, no defect claimed)

`artifacts/formulation/evidence/gate_test_report.json` has mtime `2026-09-12 00:59:53`, i.e.
it was rewritten in place ~2.5 min after FROZEN rev29 (00:57:26) — the silent-drift hazard the
formulation lead flagged at 01:03. For this file the rewrite was content-preserving: an
independent regeneration from the pinned inputs reproduces the pinned bytes exactly. The
`.txt` companion also re-hashes to the frozen value.

## Falsifier

Any pinned input hash moving by exit; run exit != 0 or any count differing; the normalized
run report differing from the frozen report at any byte; or a control failing to fire. A
re-run at a later revision is expected to fail P4 by design (it binds this pin).

Reproduce: `python3 artifacts/worker-086/gform_suite_rev29/verify_suite_rev29.py`
(exit 0 = reproduced; it rebuilds `sandbox/` and both scratch controls).

## Non-claims

Not a gate verdict, not a node completion, not a re-derivation of checker semantics or class
content, and not evidence that G-FORM should pass. No canonical artifact, fixture, report,
map or event stream was written. Any review event emitted carries
`counts_as_full_schema_verdict=false`.

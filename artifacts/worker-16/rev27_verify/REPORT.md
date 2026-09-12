# w16-REV28-VERIFY-01 — independent verification at FROZEN revision 28

* Worker: worker-16 (slot worker=016), bounded pass 4, 2026-09-12T00:35:53–00:37+08:00
* Self-claimed class-bound task on the G-FORM/G-F0 critical path. The formulation lead's
  resource request (`leadform-resource-request-2026-09-12T00:34`) asked for exactly this:
  "one independent reviewer re-runs `check_class_schema.py` and `run_acceptance.py` against
  the three canonical schemas and returns a verdict citing sha256".
* No shared artifact was modified. Every re-run happened in a staged copy
  (`artifacts/worker-16/rev27_verify/stage/`).

## Artifacts verified at measurement time

| artifact | sha256 | check |
|---|---|---|
| `artifacts/formulation/FROZEN.json` | `2f358f6722d9…` (rev 28, `frozen_at 2026-09-12T00:35:08+08:00`, 44 files) | 44/44 pins match disk |
| `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6…` (rev 12) | stage 1 pass; **stage 2 reject** |
| `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc…` (rev 12) | stage 1 pass; stage 2 accept |
| `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda…` (rev 12) | stage 1 pass; stage 2 accept |
| `research_map/formulation_taxonomy.yaml` (F0) | `0abb9ed8a961…` | f0_binding of all three schemas resolves to it |

Canonical vs mirror: the three schemas are byte-identical to
`artifacts/formulation/schemas/…` (both paths hashed in this run).

## Green results

* **Manifest**: rev 28 is self-consistent — 0/44 pinned paths drifted at 00:35:53.
* **Stage 1** (`check_class_schema.py`, R01–R16): exit 0 on all three canonical schemas and
  all three mirrors.
* **Class-binding census** at the frozen bytes: 0 non-frozen class-like tokens
  (`AF-…`), no variant id (`SET`, `CH`, `H2LOC`, `L2CONN`, `LIP`, `TWOSIDED`,
  `DISTRIBUTIONAL`) used in a `class_id`/`class_ids` field, and every
  `class_contract_pointer` resolves in the canonical taxonomy.
* **Controls**: positive fixture passes, negative fixture (`m11_epistemic_theorem`) fails,
  a byte-identical copy gets the same verdict.
* **F0**: still a non-mirror pair with the class-contract supplement
  (`d7419b4e8963…`), disjoint top-level key sets — matching the lead's own disposition.

## Hard findings

**W16R28-F1 — the two-stage acceptance cannot be re-run at the frozen bytes.**
`run_acceptance.py` exits 3: `PREFLIGHT FAIL: rebased fixtures are stale; corpus base
1bb78ce9b357 ≠ current base 55d0a1ea9bda`. The pinned
`acceptance_pipeline_report.json#9b7d6c82` (union 31/31) is evidence for the superseded C0
revision: its file mtime is `00:27:40`, before the rev 12 schemas were written
(`revised_at 00:31:41`, mtime `00:32:02`). The gate's "two-stage PASS on the final bytes"
claim is therefore not reproducible at the frozen hashes.

**W16R28-F2 — the pipeline's own stage 2 rejects F1 at the frozen hash.**
`artifacts/worker-06/spec_conformance_audit.py` (sha `c79d8ab8440a`, the same tool hash
recorded in the corpus evidence) returns `reject`, `failed_rules: ["R03"]`,
`"binder '(q,t0)' absent from formal sentence"` for `schemas/af_wcc_vacuum.yaml#cce9c601`.
C2 and C0 return `accept`. Even with a re-based corpus, `run_acceptance.py` would fail its
canonical F1 row. Repro (from the stage root):
`python3 artifacts/worker-06/spec_conformance_audit.py schemas/af_wcc_vacuum.yaml`.
Whether this is a true semantic defect or an R03 literal-match false positive (the formal
sentence binds `q` and `t0` separately rather than the declared pair `(q,t0)`) is a
formulation/audit adjudication, not a worker call.

## Medium / informational

* **W16R28-F3 (medium)** — `gate_test_report.json` embeds absolute paths, so its pin is
  location-dependent: a clean staged re-run produced `5a9ebb372307` vs the pinned
  `6def01264a1d` with identical verdicts. An off-tree reviewer cannot reproduce that pin.
* **W16R28-F4 (timeline)** — FROZEN rev 27 (`frozen_at 00:32:59`) had 3 evidence files
  rewritten after the freeze (mtimes `00:33:11`–`00:33:16`; pinned vs disk:
  `2f699be9`/`22b92a8e`, `675a99d0`/`9e335e9b`, `fc6ee058`/`11888ec6`). Rev 28 re-pinned and
  is clean; the rev 27 bytes were not retained by this pass, so this row is a time-stamped
  observation.
* The FROZEN revision moved 27 → 28 *during* this pass (00:32:59 → 00:35:08). All hashes in
  `verification.json` are bound to rev 28 as read at 00:35:53.

## Falsifiers

* F1: a `run_acceptance.py` run at the frozen bytes that exits 0 (requires a corpus re-based
  to the frozen C0 hash and an F1 formal sentence containing the declared binder, or a rule
  adjudication), or a stage-2 `accept` verdict for `af_wcc_vacuum.yaml#cce9c601`.
* F3: a staged re-run of `run_gate_tests.py` at these bytes reproducing the pinned
  `gate_test_report.json` sha256.
* F4: the rev 27 `FROZEN.json` bytes whose pins match the three files as measured at
  00:33:11–00:33:16.
* Any content check: showing a named frozen path at the cited sha256 violating the named
  property.

## Limits / authority

* Worker event: this cannot set node status, `validation_status=passed`, or a gate verdict.
  It is evidence for lead-audit (`astra-life03-verify-gform`/`-gf0`) and the controller.
* This is independent machine re-execution plus a class-binding census, not an independent
  review of the physics content.
* Hashes are bound to the `finished_at` stamp in `verification.json`; later writers can move them.

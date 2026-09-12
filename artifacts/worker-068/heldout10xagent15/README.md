# W068-FORM-HELDOUT10-XAGENT-15 — cross-agent replication of FORM-HELDOUT-10 at the rev13 pin

**Worker:** worker-068 (bounded task, no inbox card). **Node:** A1. **Gate:** G-CLASSBIND
(folded into G-AUDIT as calibration evidence). **Classes:** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN,
AF-SCC-C0-VAC-GEN. **Status:** replication complete; no gate verdict, no node transition, no rule
adoption claimed.

## Why this task

`FORM-HELDOUT-10` (worker-084) is the largest rev13-pinned class-binding escape census: 33 mutants
/ 19 families / 7 controls, informative C2+C0 arms 26/26 union escape. Its terminal verification
(`artifacts/heldout/heldout-10/verify/verification.json`) was performed by **worker-084 itself**
and explicitly records the limit: *"Independence is process-level (fresh re-run from preserved
bytes), not third-party: the verifier shares the worker-084 id with the corpus executor."*

This task supplies the missing **cross-agent executor independence**: worker-068 is not an author
of heldout-10, wrote an independent runner/parser/diff, and re-ran both canonical stages from a
worker-068-owned fully pinned snapshot. Nothing canonical was written.

## Question

Does a different execution agent reproduce the heldout-10 verdicts fixture-by-fixture and the
reported aggregates at the rev13 / FROZEN-rev29 pins? Secondary: how far is each mutant
structurally from its own arm base?

## Method (pre-registered in `PREREGISTRATION.json` before any stage run)

| input | pin (sha256 prefix) |
|---|---|
| F1 / F2a / F2b rev13 | `d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe` |
| FROZEN rev29 | `815e08079aefbc` |
| F0 canonical taxonomy | `0abb9ed8a961` |
| stage A `check_class_schema.py` | `000e09e46b2f` |
| stage A `KEY_MANIFEST.json` | `014e2d301978` — **pinned in the shadow here** |
| stage B `spec_conformance_audit.py` | `c79d8ab8440a` |
| rule spec `rule_spec.json` | `40f9bb9e657b` |
| heldout-10 manifest / raw / report | `d026fec40fe4` / `b3480625da10` / `5629e2a69c86` |

1. `build_shadow15.py` copied every pinned input and all 40 corpus fixtures (3 bases, 33 mutants,
   4 authored controls, 3 frozen canonical controls) into `snapshot/` preserving relative paths,
   verified each byte against the pre-registration or the heldout-10 manifest, and wrote
   `manifest.json` (53 files) — **before any stage process started**.
2. `run_xagent15.py` re-verified all 53 snapshot bytes, then ran the two canonical stages exactly
   once per fixture from the snapshot (80 stage processes), retaining per-fixture stage JSON.
3. Every `{stage A verdict, failed_rules, stage B verdict, failed_rules}` was compared with the
   pinned worker-084 `raw_verdicts.json` (`b3480625da10`).
4. Aggregates were recomputed from the replication's own verdicts, not copied.
5. Secondary mechanical audit: leaf-level structural diff of each mutant against its own declared
   arm base.

## Result — cross-agent replication: 40/40 agreement

| population | fixtures | verdict agreement (verdict + failed_rules) |
|---|---|---|
| frozen canonical controls | 3 | 3/3 |
| authored controls | 4 | 4/4 |
| mutants | 33 | 33/33 |
| **total** | **40** | **40/40 (rate 1.0)** |

Recomputed aggregates match the pinned worker-084 report exactly:

| aggregate | worker-084 | worker-068 replication |
|---|---|---|
| all-mutant union escape | 0.7879 (7/33 caught) | **0.7879 (7/33 caught)** |
| informative C2+C0 arms union escape | 1.0 (0/26 caught) | **1.0 (0/26 caught)** |
| uninformative W arm union escape | 0.0 (7/7 R03-only) | **0.0 (7/7 R03-only)** |
| strict validity | false — control `af_wcc_vacuum.yaml` rejected | **false — same control, same reason** |

- `informative_arms = {AF-SCC-C2-VAC-GEN: true, AF-SCC-C0-VAC-GEN: true}`; the untouched F1/WCC
  canonical `d9cebb9404b2` is rejected by stage B on **R03 only**, so the W arm stays
  non-informative. The exact invalid reason string
  `control af_wcc_vacuum.yaml rejected: stage B reject ['R03']` was reproduced.
- All 10 pre-registered predictions matched (`predictions_all_match: true`).
- Snapshot bytes were unchanged before and after the run (53/53); no live pinned input drifted
  during the run. `valid=false` here is the pre-registered H5 consequence of the R03 instrument
  defect, not a replication failure.

## Secondary — mutation-isolation audit (33 mutants)

| changed leaves vs own base | mutants |
|---|---|
| 1 (single-leaf) | 22 |
| 2 | 9 |
| 4 | 2 |

Zero mutants are byte-identical to their base; every declared base hash matches the base file
used; all 33 fixtures parsed. The 11 multi-leaf mutants are structural families by design —
paired `conclusion.statement_formal` + `statement_natural_language` edits (m01–m04, m09, m10),
paired provenance `identifier` + `status` (m21, m22), `excluded_set` value + status (m28), or a
four-leaf `falsifier.schema_falsifiers` erasure (m23, m24). **Consequence for interpretation:**
heldout-10 is mutation-attributable at family level, but the corpus is *not* universally
single-leaf isolated; family labels for the 11 multi-leaf mutants should be adjudicated against
the reported leaf witnesses rather than assumed from a single declared site.

## Findings (each with an executable falsifier in `report.json`)

- **W068-X15-F1** — cross-agent replication: 40/40 heldout-10 fixtures agree with the pinned
  worker-084 verdicts on both stages including `failed_rules`; aggregates identical. The
  worker-084 self-verification's stated independence limit is closed at executor level.
- **W068-X15-F2** — informative C2+C0 arms: 26/26 mutants union-escape both stages at the rev13 /
  FROZEN-rev29 pins (0 caught), reproduced by a non-author executor.
- **W068-X15-F3** — W arm non-informative at rev13: the untouched F1 canonical is rejected by
  stage B on R03 only; strict H5/validity is false for the same reason.
- **W068-X15-F4** — mutation-isolation distribution 22/9/2 (1/2/4 leaves); no zero-change mutant,
  no base-hash mismatch; 11 multi-leaf family edits are reported explicitly.
- **W068-X15-F5** — the 10 pre-registered predictions, recorded before any stage run, all matched
  on a corpus authored by another agent.

## Reproduction

```bash
cd <repo>
python3 artifacts/worker-068/heldout10xagent15/build_shadow15.py   # rebuilds snapshot/ + manifest.json
python3 artifacts/worker-068/heldout10xagent15/run_xagent15.py     # re-runs 80 stage processes
```

## Non-claims and limitations

- **Not blind.** worker-068 read the heldout-10 report before replicating. This is cross-agent
  executor independence, not a blind third-party review; label adjudication remains open.
- The corpus and its family labels remain worker-084's; a replicated escape is not by itself a
  genuine class-contract violation.
- Stage verdicts are mechanical (stage A R01–R27 with the pinned KEY_MANIFEST; stage B R01–R16);
  neither decides mathematics or class truth. The R03 rejection of the WCC canonical is a known
  instrument/wording defect (HF-071R3-01), recorded, not re-litigated here.
- `valid=false` is the corpus's strict-H5 status, inherited from the R03 defect; this replication
  reproduces it rather than repairing it.
- No gate verdict, node completion, `validation_status=passed`, or rule adoption is claimed.

## Falsifier

Any per-fixture verdict or `failed_rules` disagreement with the pinned worker-084 raw verdicts;
any snapshot byte that differs from `manifest.json` before or after the run; any pinned live input
that drifted during the run; any mutant with zero changed leaves or an unparseable document; a
stage crash; or a replication aggregate that differs from the pre-registered prediction.

## Artifacts

`PREREGISTRATION.json` · `manifest.json` (shadow, 53 files) · `build_shadow15.py` ·
`run_xagent15.py` · `snapshot/` · `raw/` (80 per-fixture stage outputs) · `raw_verdicts.json` ·
`report.json` · `checkpoint.json` · `checkpoint_final.json` · `emit_events.py`

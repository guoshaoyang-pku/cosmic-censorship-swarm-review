# W046-F2A-EXTFREEZE-PREVALIDATION-01 — independent pre-validation of the F2a extension-freeze candidate

**Class** `AF-SCC-C2-VAC-GEN` · **Node** F2a · **Gate** G-FORM (context only) · **Actor** worker-046 · **Created** 2026-09-12T01:25:35+08:00

**Verdict of this deliverable** `candidate_prevalidated` — advisory pre-validation evidence. It issues **no gate verdict** and writes no canonical byte.

## Why this artifact exists

F2a carries two live G-FORM blockers: the under-frozen extension predicate (manifold category of `M'`, differentiability of `iota`, clause-(f) interior requirement) and the consequent non-derivability of the declared containment `E_C2 subset E_C0`. worker-047 published the repair **specification**; REC-36 authorizes the owner to land the revision. This instrument answers the owner's outstanding pre-flight questions at the pinned bytes: does the repair survive the canonical gate, is the delta leaf-bounded, does an independent clause-lattice instrument now derive the containment, and what does the repair not fix?

## Pins (start = end, byte-stable)

| path | sha256 |
|---|---|
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd308bd…` |
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe7f86…` |
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2fb4ab…` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b2c6b…` |
| `artifacts/formulation/KEY_MANIFEST.json` | `014e2d3019781632…` |
| `artifacts/formulation/FROZEN.json` | `815e08079aefbc16…` |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c9…` |
| `artifacts/formulation/formulation_taxonomy.yaml` | `d7419b4e8963cb71…` |

## Results

- Candidate sha256 `37e650ad6481ad24551d495887d8cc7bdc0ca713b1cdd614e60324cca681c960`; changed YAML leaves: `extension_predicate.definition`, `falsifier.tier_1.witness_type`, `topology.extension_topology` (3 leaf diffs).
- Canonical gate (`check_class_schema.py` @ `000e09e46b2f`): live F2a `pass`, candidate `pass`, class-id swap `fail`, conclusion-type swap `fail`; all five repair-reverting mutants `pass` (gate is structurally blind to the repair — recorded).
- Containment instrument: candidate entails `P_C2 => P_C0` under strict-literal = **True** and standard-typing = **True**; live F2a strict-literal = **False** (blocker reproduced); reverse `P_C0 => P_C2` = **False** (separation preserved).

### Axis table (0 = unspecified/weakest, ascending strength)

| schema | iota | manifold | interior | metric | equation | direction |
|---|---:|---:|---:|---:|---:|---|
| live_F2a | 0 | 0 | 0 | 2 | 1 | future |
| candidate | 2 | 1 | 1 | 2 | 1 | future |
| F2b | 2 | 1 | 1 | 0 | 0 | future |
| M1_minus_S1 | 2 | 1 | 1 | 2 | 1 | future |
| M2_minus_S2 | 2 | None | 1 | 2 | 1 | future |
| M3_minus_S3 | 2 | 1 | 0 | 2 | 1 | future |
| M4_minus_S4 | 2 | 1 | 1 | 2 | 1 | future |
| M5_minus_S5 | 2 | 1 | 1 | 2 | 1 | future |

### Site materiality for the containment obligation

| site | carrier | containment holds without it? | material |
|---|---|---|---|
| S1 | extension_predicate.definition clause (a) | True | False |
| S2 | extension_predicate.definition clause (c) | False | True |
| S3 | extension_predicate.definition clause (f) | False | True |
| S4 | topology.extension_topology | True | False |
| S5 | falsifier.tier_1.witness_type | True | False |

Load-bearing single sites: **S2, S3**. The manifold freeze is carried redundantly by clause (c) (S2) and `topology.extension_topology` (S4): either alone keeps the axis resolved, which mirrors the sibling's own belt-and-braces propagation. S5 is documentation propagation of the witness contract, not decisive for the entailment.

Cross-check against the worker-047 sandbox candidate `artifacts/worker-047/f2a_ext_freeze_spec/sandbox/root/schemas/af_scc_c2_vacuum.yaml` (`37e650ad6481ad24…`): byte-identical to this instrument's independently built candidate = **True** (sha256 comparison only; their checker was not imported).

## Controls (all pre-registered)

| id | assertion | expected | observed | pass |
|---|---|---|---|---|
| C11a | all eight declared pins measured at run start | `{'schemas/af_scc_c2_vacuum.yaml': 'e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe', 'schemas/af_scc_c0_vacuum.yaml': 'b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c', 'artifacts/formulation/tools/check_class_schema.py': '000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff', 'artifacts/formulation/rule_spec.json': '40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e', 'artifacts/formulation/KEY_MANIFEST.json': '014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a', 'artifacts/formulation/FROZEN.json': '815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0', 'research_map/formulation_taxonomy.yaml': '0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3', 'artifacts/formulation/formulation_taxonomy.yaml': 'd7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1'}` | `{'schemas/af_scc_c2_vacuum.yaml': 'e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe', 'schemas/af_scc_c0_vacuum.yaml': 'b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c', 'artifacts/formulation/tools/check_class_schema.py': '000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff', 'artifacts/formulation/rule_spec.json': '40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e', 'artifacts/formulation/KEY_MANIFEST.json': '014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a', 'artifacts/formulation/FROZEN.json': '815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0', 'research_map/formulation_taxonomy.yaml': '0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3', 'artifacts/formulation/formulation_taxonomy.yaml': 'd7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1'}` | True |
| C05 | candidate changes exactly the three expected YAML leaves | `['extension_predicate.definition', 'falsifier.tier_1.witness_type', 'topology.extension_topology']` | `['extension_predicate.definition', 'falsifier.tier_1.witness_type', 'topology.extension_topology']` | True |
| C06 | class-identity invariants unchanged on the candidate | `[]` | `[]` | True |
| C01 | canonical gate PASSES live F2a | `pass` | `pass` | True |
| C02 | canonical gate PASSES the five-site candidate | `pass` | `pass` | True |
| C03 | canonical gate FAILS the class-id swap mutant (positive control) | `fail` | `fail` | True |
| C04 | canonical gate FAILS the conclusion-type swap mutant (positive control) | `fail` | `fail` | True |
| C12 | structural gate is BLIND to all five repair-reverting mutants (recorded, not desired) | `['pass']` | `['pass']` | True |
| C07 | candidate entails P_C2 => P_C0 under the strict-literal reading | `True` | `True` | True |
| C08 | candidate entails P_C2 => P_C0 under the standard-typing reading | `True` | `True` | True |
| C09 | live F2a does NOT entail P_C2 => P_C0 (blocker reproduced) | `False` | `False` | True |
| C10 | reverse P_C0 => P_C2 is not entailed (class separation preserved) | `False` | `False` | True |
| C13 | clause-(f) mutant alone breaks containment (interior axis is load-bearing) | `False` | `False` | True |
| C14 | live F2a axis profile is (iota=0, manifold=0, interior=0) at the pinned bytes | `[0, 0, 0]` | `[0, 0, 0]` | True |
| C15 | F2b convention profile is (iota=2, manifold=1, interior=1) | `[2, 1, 1]` | `[2, 1, 1]` | True |
| C11b | no canonical target moved during the run (byte stability) | `{}` | `{}` | True |

## Advisories (non-blocking)

- **W046-F2A-PV-03** (advisory-non-blocking) on `class_boundary.import_rule`: The three ported clauses are definitional sharpening of a shared predicate convention, not C0 conclusion content, but the sibling citations introduced by S2/S3/S4 now sit inside extension_predicate.definition and topology, which the live class_boundary.import_rule scopes to anti_scope/variants/provenance. The canonical gate does not flag this. Owner options: (a) keep the alignment self-contained in the class contract / supplement, or (b) record an explicit convention-alignment provenance key. Adjudication belongs to the gate owner; this is not counted as a hard failure.
  - line 93 (extension_predicate.definition): `(a) iota: M -> M' is a C-infinity isometric embedding (iota_* g = g' restricted to iota(M)); the differentiability class of iota is frozen here and is not left `
  - line 95 (extension_predicate.definition): `(c) M' is a SMOOTH (C-infinity) connected 4-manifold, time-orientable, and its time orientation restricts to that of M; the smooth structure is the category in `
  - line 98 (other): `(f) the extension adds interior points to the future: int(M' minus iota(M)) is non-empty AND there exist q in iota(M) and p in int(M' minus iota(M)) with p in I`
  - line 117 (topology.extension_topology): `extension_topology: "M' is a connected SMOOTH 4-manifold (the category in which the C2 metric is a tensor field) containing iota(M) as an open proper subset; th`

## Falsifier

This pre-validation is falsified by any of: (i) a start or end sha256 differing from the declared pins, or any canonical target moving during the run; (ii) the pinned canonical gate not PASSing the candidate or not FAILing the class-id / conclusion-type positive controls; (iii) an independent re-run reporting a decisive axis on which the candidate's predicate is strictly weaker than F2b's under the strict-literal reading; (iv) any class-identity invariant differing between live F2a and the candidate; or (v) the candidate differing from the pinned F2a bytes at any leaf other than the three recorded leaves.

## Non-claims / authority

Not a gate verdict, not a node completion, not a full-schema review, not a mathematical claim. The repair candidate is not applied to `schemas/af_scc_c2_vacuum.yaml`; every canonical path is only hashed. A worker event cannot set `status=done`, `validation_status=passed`, or a gate verdict.

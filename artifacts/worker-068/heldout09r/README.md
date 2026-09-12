# W068-FORM-HELDOUT-09-REPL — independent replication + control extension

Bounded execution worker `worker-068`, node `A1`, gate `G-CLASSBIND` (calibration evidence
folded into `G-AUDIT`). Class-bound to `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`,
`AF-SCC-C0-VAC-GEN`. Measurement only: no gate verdict, no node completion, no theorem.

## Why this is a class-bound task

`astra-life03-heldout-09` asks for the FORM-HELDOUT-09 union-escape measurement to be
re-issued against the closure revision, with ">=7 controls that must pass both stages" and
"an independent replication of the frozen result". The frozen corpus
(`artifacts/worker-068/heldout3/`, FROZEN rev25) has 35 leaky mutants across 14 leak families,
but only 4 conforming controls and no replication. This task closes exactly those two gaps.

## What was replicated

| item | sha256 (prefix) |
|---|---|
| `artifacts/worker-068/heldout3/manifest.json` | `72c0353ad0de` |
| `artifacts/worker-068/heldout3/raw_verdicts.json` | `3fe7499bfc12` |
| `artifacts/worker-068/heldout3/report.json` | `9904e516a9da` |
| `schemas/af_wcc_vacuum.yaml` | `9a8bd4c96800` |
| `schemas/af_scc_c2_vacuum.yaml` | `b6123750b37d` |
| `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9b357` |
| stage A `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2f` |
| stage B `artifacts/worker-06/spec_conformance_audit.py` | `c79d8ab8440a` |
| rule spec `artifacts/formulation/rule_spec.json` | `40f9bb9e657b` |

Method (own harness, `replicate_heldout09.py`; no code imported from the original runner):
re-measure every binding, hash-order check (manifest before any stage run), re-run both frozen
stages on all 49 fixtures, diff per-fixture verdicts and failed-rule sets against the frozen
raw verdicts, recompute every aggregate / per-class rate / per-family rate / escape-family list
from scratch, then add and run the extended controls.

## Result

| metric | frozen | replication |
|---|---|---|
| fixtures compared | 49 | 49 |
| per-fixture mismatches | — | **0** |
| union escape rate (leaky) | 1/35 = 0.02857 | **1/35 = 0.02857** |
| caught stage A / stage B | 34 / 33 | **34 / 33** |
| conforming controls | 4, 0 false positives | **7, 0 false positives** |
| known-rejected positive controls | 6/6 rejected | **6/6 rejected** |
| HELDOUT-08 escape references | 4/4 still escape | **4/4 still escape** |
| escape-family list | `c0-conclusion-polarity` | **identical** |

Extended controls (all accepted by both stages):

| control | edit | sha256 (prefix) |
|---|---|---|
| `c05_comment_prepend.yaml` | comment line prepended | `3302baf8e847` |
| `c06_comment_append_blank_eof.yaml` | comment + blank lines appended at EOF | `2b0b10de29ea` |
| `c07_renamed_identical_copy.yaml` | byte-identical copy under a new name | `4adbc469eaac` |

Declared format probe (reported separately, NOT counted as a control; accepted by both stages):
`probe_pyyaml_resorted_c0.yaml` `ce26f3846ae9` — C0 control re-serialized with
`yaml.safe_dump(sort_keys=True, default_flow_style=False)`.

## Manifest supersession (moving-target note, not content drift)

`artifacts/formulation/FROZEN.json` was `rev25 / af24e9c39606` at the frozen run
(00:22:34; the runner recorded zero drift) and is now `rev26 / 2554e276a0db`
(mtime 00:24:49, an F0 publication adjudication request). Rev26 still pins the same three
class schemas and both stage tools, so the class-binding measurement's **content binding
holds**; only the manifest hash binding is stale. Detail:
`replication_report.json#manifest_supersession`.

## Verdict and non-claims

`replication_report.json` verdict: `replicated_with_manifest_supersession` (0 mismatches,
0 problems). This is **harness-independent, not agent-independent** — the corpus was also built
by worker-068, so it is a method replication, not a second-author replication. Not a gate
verdict; the polarity blind spot `c0_03_conclusion_negated` remains open and still needs an
independent adjudication (blocker `w068-hel09-12-blocker-polarity`).

## Falsifier

Any per-fixture verdict/rule mismatch against the frozen raw verdicts; any drift in the three
canonical schemas, both stage tools, or the rule spec between build and replication; any
aggregate or escape-family-list disagreement; a reviewer showing an extended control is not
semantics-preserving.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-068/heldout09r/replicate_heldout09.py
```

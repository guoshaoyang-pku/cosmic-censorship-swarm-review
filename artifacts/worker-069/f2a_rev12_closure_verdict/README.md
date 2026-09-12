# W069-F2A-REV12-CLOSURE-VERDICT-01 — independent F2a verdict at the rev12 closure hash

Worker 069, bounded task, class **AF-SCC-C2-VAC-GEN** (node F2a, gate G-FORM).
Read-only on every canonical formulation path.

## What was reviewed

`schemas/af_scc_c2_vacuum.yaml` at sha256 `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce`
(revision 12, the `astra-life03-close-findings` closure revision), against:
canonical F0 `research_map/formulation_taxonomy.yaml#0abb9ed8`, supplement
`artifacts/formulation/formulation_taxonomy.yaml#d7419b4e`, `VARIANT_REGISTRY.json#5eb42f9a`,
`VOCAB_ALIASES.json#46cd9f1e`, `FROZEN.json` revision 27→28 (rev28 landed mid-run; both verified).

## Verdict

**revise, score 3.5**, `counts_as_full_schema_verdict: true`.

- Content: **31/31 independent criteria pass** (the rev11 finding set is closed: no duplicate
  top-level keys, non-future stamps, canonical `classes.<id>` pointer plus separate supplement
  pointer, D0 retyped as a tagged disjoint union over one index `r`, no dangling `AF_{...}` symbol,
  one conclusion token under `VOCAB_ALIASES`).
- Controls: **18/18** doc-level mutations (positive + 17 mutants) and **7/7** file-level closure
  controls (duplicate key, future stamp, authoring-only pointer, untagged D0, dangling symbol,
  unmapped token, byte-identical positive).
- Hash stability: no drift across the run; `verify_frozen.py` reports **0 problems** at rev28;
  class-separation regression **PASS**; structural gate PASS on snapshot and canonical bytes.
- Blocking findings that force revise (not schema-content defects):
  - **HF-069R-3** — `f0_binding.consistency_evidence_sha256` declares `675a99d0d25b` but the canonical
    evidence file `artifacts/formulation/evidence/taxonomy_consistency.json` measures `9e335e9ba1bf`
    (the FROZEN rev28 pin), and that on-disk file still contains **no sha256 of either compared tree**.
    The consistency claim is unbound by hash at the declared evidence path.
  - **HF-069R-2** — `run_acceptance.py` fails preflight: the rebased fixtures are stale
    (corpus base `1bb78ce9b357` vs current base `55d0a1ea9bda`), so the two-stage acceptance cannot be
    reproduced on the frozen bytes. Rebase with `artifacts/formulation/tools/measure_semantic_escape.py`.
- Transient (observed then self-cleared mid-run): FROZEN rev27 carried 5 manifest drift problems
  (including the same consistency-evidence file); rev28 was published at 00:35:08 and `verify_frozen`
  then reported 0 problems. Recorded in `raw/verify_frozen.txt` and the falsifier list.

## Files

| file | role |
|---|---|
| `check_f2a_rev12_independent.py` | 31-criterion checker (G1–G31) with 17-mutation selftest |
| `run_verdict.py` | pins, snapshot, controls, canonical-tool runs, report writer |
| `report.json` | full verdict record (hashes, checks, controls, tools, falsifier) |
| `raw/` | per-tool captures + control outputs |
| `snapshot/` | byte copies of the six pinned inputs |
| `controls/` | mutated copies used by the file-level controls |
| `SHA256SUMS` | hashes of every file above |

## Reproduce

```bash
python3 artifacts/worker-069/f2a_rev12_closure_verdict/run_verdict.py
```

Falsifier: see `report.json.next_falsifier`. Any canonical hash move voids the binding; a reviewer
showing the rev12 bytes were themselves clean (i.e. that HF-069R-2/3 are not attributable to the
frozen revision) forces a re-score, not a re-check.

Not a gate verdict; node and gate status remain with the controller and the leads.

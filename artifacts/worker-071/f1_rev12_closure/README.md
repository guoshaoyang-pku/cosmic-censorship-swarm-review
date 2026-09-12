# W071-F1-REV12-CLOSURE-VERIFY-01 — independent mechanical closure check of the rev12 schemas

- worker: `worker-071` · class: `AF-WCC-VAC-GEN` (secondary `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`) · node `F1` · gate `G-FORM`
- read-only on all canonical paths; every result bound to sha256 pins taken from `snapshot/MANIFEST.json`
- **verdict: `REV12_CLOSURE_CONFIRMED_ON_LISTED_CHECKS` — 9/9 pre-registered checks PASS, 7/7 controls fire, inputs stable during the run**
- authority: worker evidence only. No gate verdict, no node status, no `validation_status` promotion.

## Why this task

At `2026-09-12T00:31:41–00:32:02+08:00` the formulation lead published revision 12 of all three canonical
class schemas and a new canonical taxonomy, claiming to close the hash-bound findings of
`astra-life03-close-findings` (duplicate `revised_at` keys, future-dated timestamps, authoring-tree
`class_contract_pointer`, undefined `AF_{I+}`, whole-curve vs tail visibility predicate, ill-typed `D0`).
Every prior hash-bound verification in the swarm is superseded by this transition, so the transition itself
needs an independent machine check. This is that check, and only that check.

## Pinned inputs (sha256, full)

| input | sha256 |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1 rev12) | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev12) | `5476a3f2c6bc7196…` (full hash in `closure_check.json` / `snapshot/MANIFEST.json`) |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev12) | `55d0a1ea9bda96b8…` |
| `research_map/formulation_taxonomy.yaml` (canonical F0) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `artifacts/formulation/FROZEN.json` (rev 28) | `2f358f6722d92062…` |
| rev11 F1 control bytes (worker-048 pinned copy) | `9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503` |

## Checks (all at the pins above; full evidence in `closure_check.json`)

| id | scope | result | measured |
|---|---|---|---|
| C1-DUPKEY | F1,F2a,F2b | PASS | 0 duplicate mapping keys at any depth (rev11 had 7×`revised_at` + 2×`revised_at_unused` in F1) |
| C2-REVISED-UNIQUE | F1,F2a,F2b | PASS | 1 top-level `revised_at`; `revision_history` contains all 7 (F1) / 8 (F2a,F2b) known rev11 timestamps; `revision: 12` |
| C3-CLOCK | F1,F2a,F2b | PASS | 0/12 timestamps after wall clock; `revised_at` 21.1 s before file mtime (rev11: 646 s after) |
| C4-POINTER | F1 | PASS | `…formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN` resolves in canonical; supplement pointer separate and resolves in authoring tree |
| C5-AFIPLUS | F1 | PASS | 3 occurrence paths, 1 definition anchor (`i_plus.predicate_abbreviation`) |
| C6-VISIBILITY | F1 | PASS | operative clauses use the tail form `gamma([t0,T))`; no whole-curve containment in operative clauses; D5 prohibition marked STRONGER/NOT |
| C7-D0 | F1 | PASS | tagged disjoint union; first binder `r`/`D0`; formal binds `r in D0`; no `(s,delta) in D0` |
| C8-F0BINDING | F1,F2a,F2b | PASS | `declared_f0_sha256` == measured canonical F0 hash |
| C9-FROZEN | F0,F1,F2a,F2b | PASS | FROZEN rev 28 lists all four canonical paths with matching hashes |

## Controls (all fire; `CTL-REV11-*` are real-defect historical controls)

`CTL-DUPKEY-SENS`, `CTL-CLOCK-SENS`, `CTL-POINTER-SENS`, `CTL-DETERMINISM`, `CTL-NOWRITE`,
and — using the independently pinned rev11 bytes `9a8bd4c9` — `CTL-REV11-DUPKEY` (detector still flags the
old duplicates) and `CTL-REV11-MTIME` (mtime-consistency check flags the old future-dated `revised_at`).
The same instrument therefore rejects rev11 and accepts rev12: it discriminates, it does not merely accept.

## Residual (INFO, not adjudicated here)

- F0 canonical `0abb9ed8a96135c9` vs authoring `d7419b4e8963cb71` remain byte-divergent, so the canonical-path
  publication policy is still not satisfied for F0. This is not an F1 defect at rev12 and is recorded, not ruled on.
- These checks are mechanical/lexical: they do not verify mathematical adequacy, non-vacuity, literature scope,
  or the F2a/F2b content findings that are not in the listed set.

## Re-run / falsifier

```bash
python3 artifacts/worker-071/f1_rev12_closure/verify_rev12_closure.py --out closure_check.json
```

Falsified by: any C1–C8 check FAILing at the pins, either rev11 historical control ceasing to fire, or
`CTL-DETERMINISM`/`CTL-NOWRITE` failing. Any change of a pinned input sha256 voids the result at that path.

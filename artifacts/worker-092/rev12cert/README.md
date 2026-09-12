# W092-REV12-CERT-01 — repair-landing certification + freeze state (worker-092)

Bounded execution worker `worker-092`, fleet instance `worker-092-20260912T002948-968807`.
No inbox card existed for worker-092; one class-bound task was taken from the live critical
path. **Measurement only: no gate verdict, no node status, no shared artifact edited.**

## Task

Independently certify, from pinned bytes only, that the `astra-life03-close-findings`
repair (F0 rev5, F1/F2a/F2b rev12) actually landed as the revision notes claim, and
measure the FROZEN binding state that a gate scan would resolve.

Classes: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
(nodes F0/F1/F2a/F2b; gates G-F0/G-FORM).

## Pinned snapshot (measured 2026-09-12T00:35:17+08:00)

| artifact | sha256 (16) | bytes | note |
|---|---|---|---|
| `research_map/formulation_taxonomy.yaml` (F0 rev5) | `0abb9ed8a96135c9` | 36372 | declared F0 |
| `schemas/af_wcc_vacuum.yaml` (F1 rev12) | `cce9c60146d6a907` | 36014 | canonical == authoring |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev12) | `5476a3f2c6bc7196` | 29976 | canonical == authoring |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev12) | `55d0a1ea9bda96b8` | 34984 | canonical == authoring |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `d7419b4e8963cb71` | 21699 | distinct from F0 by declaration |
| `artifacts/formulation/FROZEN.json` (rev28) | `2f358f6722d92062` | — | frozen_at 2026-09-12T00:35:08 |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf77` | — | mtime 00:34:55 |

## Result — 24/27 repair checks PASS, 3 expected MISMATCH (all the same binding)

Verified present at the pinned bytes (each check is machine-readable in `report.json`):

- **F0 rev5 discharge.** All four class conclusions carry a comeager quantifier; the scalar
  class conclusion names the superseded set-based (contained-in-`J-(I+)`) reading as the
  variant `SET` predicate, not as its own (`R2`, `R2b`). This retires the W082-F-02 / W092-A-HF-03
  class-coverage defect at the new hash.
- **Pointer repair.** `class_contract_pointer` = `research_map/formulation_taxonomy.yaml#classes.<CLASS>`
  and resolves in the canonical taxonomy for all three schemas; the supplement pointer is split into
  its own top-level field and in `f0_binding`, and resolves for all three (`R3`, `R4`).
- **F0 binding refresh.** `declared_f0_sha256` equals the live F0 hash `0abb9ed8a96135c9` in all
  three schemas (`R5`).
- **Duplicate keys collapsed / wall-clock stamp.** Raw duplicate mapping keys: 0 in F0, supplement,
  F1, F2a, F2b; `revised_at = 2026-09-12T00:31:41+08:00`, not future-dated (`R7`, `R8`, `R11`, `R12`).
- **D0 retyping.** No bare `forall (s,delta) in D0` remains; each `statement_formal` is
  `forall r in D0 …` (`R9`).
- **F1 visibility repair.** `AF_{I+}` appears in `statement_formal`, is defined by
  `predicate_abbreviation`, and visibility is the tail predicate (`R10`).
- **Publication.** F1/F2a/F2b authoring copies are byte-identical to canonical; the F0 pair remains
  two distinct files as declared in FROZEN rev26 `logical_artifacts` (`PUB-*`).

**Open binding defect (`W092-R12-F2`, severity minor-binding, 3 checks):** all three rev12 schemas
cite `f0_binding.consistency_evidence_sha256 = 675a99d0d25b2b37`, but the on-disk evidence file
hashes `9e335e9ba1bfcf77` (mtime 00:34:55, i.e. regenerated after the 00:31:41 schema write and
pinned as such by FROZEN rev28). The cited hash does not bind the bytes any gate scan would read.
Repair: re-point the citation to the frozen evidence hash (or re-run
`check_taxonomy_consistency.py` and re-freeze), then re-verify. Falsifier: a schema revision whose
`consistency_evidence_sha256` equals the then-current evidence-file hash.

## Freeze state (`W092-R12-F1`)

At pin time FROZEN is revision **28** (frozen_at 00:35:08) and pins **all 7 class-bearing
canonical+authoring paths**; an independent manifest recomputation shows **0 drift / 0 missing**
(`FREEZE-01..03`). The repair is therefore re-frozen, not merely written.

The freeze moved while this task ran and the transition is reconstructible from independently
pinned copies: FROZEN rev26 `2554e276a0db…` is preserved at
`artifacts/worker-048/f1_closure_preflight/snapshot/FROZEN.2554e276.json` and
`artifacts/worker-089/f2b_f0adj_verify/pinned/FROZEN.2554e276a0db.json` (both hash
`2554e276a0db70579ce3…`); a read-only run of the owner's `verify_frozen.py` during the window
reported rev26 with 9 drifted paths (all six class files plus the two taxonomies and the
consistency evidence), and the first pin of this task observed rev27 with 5 residual non-class
drifts. Rev28 closes the residual drift. Earlier reviews bound to `9a8bd4c9`/`b6123750`/`1bb78ce9`/
`276009f4` are on superseded bytes.

## Controls

`CTL-1` determinism: two full check passes give the same digest (`db9e13dbaa6976ca`).
`CTL-2` negative mutation: repointing F1's `class_contract_pointer` to a sibling class makes the
pointer predicate return False. `CTL-3` entry==exit: all 10 pinned paths unchanged across the run.
`CTL-4` no shared writes: outputs are confined to `artifacts/worker-092/rev12cert/`.

## Falsifier

Re-run `certify_rev12.py` against its `pinned/` copies: falsified if any repair check recorded
PASS reads FAIL there, if a FROZEN revision pins the live rev12/F0-rev5 hashes on all class-bearing
paths while `FREEZE-03` reads FAIL, or if the consistency-evidence hash cited inside the schemas
equals the then-current evidence-file hash.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-092/rev12cert/certify_rev12.py   # exit 0 iff observations == expectations
```

Bundle: `certify_rev12.py`, `report.json`, `acceptance_run.log`, `pinned/` (byte copies),
`manifest.json`. Hashes: see `manifest.json`.

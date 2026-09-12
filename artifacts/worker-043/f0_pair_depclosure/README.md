# W043B-F0-PAIR-DEPCLOSURE-01 — independent dependency-closure audit of the F0 pair

Worker 043, 2026-09-12. Read-only on every shared path; all scratch writes went to a temp
directory outside the repository. Evidence only: **no gate verdict, no node status, no
`validation_status` change, no canonical byte touched.**

## Why this task

No assignment card exists in `comms/inbox/worker-043.jsonl`. The critical open item at pick
time was `leadform-blocker-0007` / `artifacts/formulation/evidence/f0_mirror_conflict.json`:
the lead-formulation agent stopped assignment `astra-life02-publish-f0` because publishing
either F0 artifact over the other is claimed to destroy a frozen input, and asked the
controller to choose REC-1 (companion-pair exception) or REC-2 (bounded re-freeze). That
decision is a class-bound question for all three frozen vacuum classes, so this audit tests
the blocker's load-bearing claims by execution and measures what each option invalidates.

## What was audited (hashes at the measured instant, all stable across the window)

| artifact | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` (declared F0) | `276009f4f63d…` (35145 B) |
| `artifacts/formulation/formulation_taxonomy.yaml` (supplement) | `c8e979a1eb48…` (20937 B) |
| `schemas/af_wcc_vacuum.yaml` (F1) | `9a8bd4c96800…` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | `b6123750b37d…` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | `1bb78ce9b357…` |
| `artifacts/formulation/FROZEN.json` (rev 26) | `2554e276a0db…` |

## Result: `LEAD_BLOCKER_SUPPORTED`

1. **Two different artifacts.** 23 canonical-only keys (`class_ids`, `classes`, `transfer_rules`, …),
   18 authoring-only keys (`class_contracts`, `axis_registry`, `implication_ledger`, …),
   7 shared keys of which **6 carry different values** (`authored_by`, `class_scope_adjudication`,
   `provenance`, `revision`, `schema_version`, `timestamp_provenance`).
2. **Pointer matrix.** All three schemas' `class_contract_pointer` (= `#class_contracts.<CLASS>`)
   resolves in the authoring artifact only; it does not resolve in the declared canonical F0;
   it resolves in a first-wins union. Reproduces worker-020's C15 independently.
3. **Both destructive directions executed, not read.** The real
   `check_taxonomy_consistency.py` was run with its `ROOT` source-patched into scratch:
   - current pair → `CONSISTENT (4 classes, 0 contract-text divergences)`, exit 0;
   - canonical→authoring publication → exit 1, `KeyError: 'class_contracts'`;
   - authoring→canonical publication → exit 1, `KeyError: 'class_ids'`.
4. **REC-1 blast radius is not one line.** Two independent hard-coded `MIRRORS` lists compute
   the same divergence — `research_map/audit_evidence.py:123` and
   `research_map/astra_lifecycle.py:44` (which feeds `publication_status`, CF-13 and the gate
   reasons); the pass-02 event generators re-state it in their own text. The canonical F0 path
   is currently **not** an active `map.frozen_artifacts` entry, so the audit reports soft today;
   re-activating a frozen F0 entry for G-F0 flips the same divergence to **hard** under
   `audit_evidence.py:135`.
5. **REC-2 blast radius measured.** A union resolves all pointers, but the 6 shared-key conflicts
   need owner decisions. Uncapped reference counts: 326 files mention the authoring path,
   350 the canonical path, 103 the pinned consistency evidence, 61 `FROZEN.json`; 42 fixture
   files under `artifacts/formulation/fixtures`, 40 of them pinning a schema/F0 hash prefix.
   REC-2 changes the three schema hashes and the supplement path, so the fixture tree and every
   current F1/F2a/F2b review binding are re-cut in the same re-freeze — a larger surface than the
   lead's estimate lists.

Full detail, per-finding falsifiers and the two options' consumer lists: `report.json`; raw
instrument output: `raw/`.

## Relationship to concurrent work

`reviews/F0-rev26-adjudication-090.json` (worker-090, written ~00:29) independently supports the
same two-artifact claim and the same "pointer resolves only in the supplement" result, and
explicitly leaves REC-1 vs REC-2 to the controller. This audit's delta is the executed
destructive-direction controls on the real checker, the two-MIRRORS-list REC-1 blast radius
(including the hard/soft flip under re-freeze) and the uncapped REC-2 consumer/fixture counts.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-043/f0_pair_depclosure/check_f0_pair.py \
    --out artifacts/worker-043/f0_pair_depclosure/report.json
# exits 0 iff the current pair is CONSISTENT and both single-artifact publications fail closed
```

The checker under test writes `artifacts/formulation/evidence/taxonomy_consistency.json`; the
audit never calls it unpatched, so that pinned evidence file is not rewritten.

## Falsifier

Re-running the instrument on byte-unchanged inputs must reproduce `LEAD_BLOCKER_SUPPORTED`,
`controls_ok=true`, `stable=true`, the same pointer matrix (canonical: unresolved, authoring:
resolved) and the same three control outcomes. Any changed input hash voids the audit and
requires re-issue at the new hash.

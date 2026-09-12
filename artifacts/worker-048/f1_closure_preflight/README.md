# W48-F1-CLOSURE-PREFLIGHT-01 — independent closure preflight for F1 (AF-WCC-VAC-GEN)

Worker: `worker-048` · Class: `AF-WCC-VAC-GEN` · Node: `F1` · Gate: `G-FORM`
Task source: `research_map/events.jsonl#astra-life03-close-findings` (items a–d) + the G-FORM
hash/publication criteria in `astra-life03-gate-gform`.
Snapshot: **2026-09-12T00:27:38+08:00** (all four pinned hashes were re-measured after the run
and were unchanged).

**Verdict: `revise`** — 4 uncontested blocking defects, 1 contested binding defect, 1
controller-adjudication dependency. This is a worker review, not a gate verdict; it does not
complete a node and does not set `validation_status`.

## Pinned inputs (sha256)

| input | path | sha256 (prefix) |
|---|---|---|
| F1 schema | `schemas/af_wcc_vacuum.yaml` (snapshot copy) | `9a8bd4c96800` |
| canonical declared F0 | `research_map/formulation_taxonomy.yaml` | `276009f4f63d` |
| authoring F0 supplement | `artifacts/formulation/formulation_taxonomy.yaml` | `c8e979a1eb48` |
| FROZEN manifest rev26 | `artifacts/formulation/FROZEN.json` | `2554e276a0db` |
| mirror-conflict evidence | `artifacts/formulation/evidence/f0_mirror_conflict.json` | `7e3a7bc89a75` |

F1 is aligned across canonical / authoring / FROZEN (`9a8bd4c96800` in all three). The F0 pair is
not byte-identical (`276009f4` vs `c8e979a1`) and FROZEN rev26 records that as intentional with a
pending controller adjudication, so the preflight reports it as `UNRESOLVED`, not as a defect.

## Checks

| id | closure item | verdict | finding |
|---|---|---|---|
| C1 | (a) | **FAIL** | 7× `revised_at` (lines 8,10,12,14,16,20,23) and 2× `revised_at_unused` (26,28); `yaml.safe_load` silently keeps the last value, a duplicate-rejecting loader raises `ConstructorError`. Parser-dependent provenance. |
| C2 | (a) | **FAIL** | `revised_at` line 23 and `f0_binding.checked_at` are `2026-09-12T00:30:00+08:00` while the file was written at 00:19:14 and the snapshot clock is 00:27:38 — future-dated at write and still future at snapshot. The same defect class FROZEN rev26 corrected for the manifest. |
| C3 | (b) | **FAIL (contested)** | `class_contract_pointer` targets `artifacts/formulation/formulation_taxonomy.yaml#class_contracts.AF-WCC-VAC-GEN`: resolves in the authoring supplement but **not** in the declared canonical F0; the canonical alternative `classes.AF-WCC-VAC-GEN` does resolve. Contested by FROZEN rev26 / `f0_mirror_conflict.json` (REC-1 vs REC-2); controller disposition required. |
| C4 | publication | **UNRESOLVED** | F1 aligned; F0 canonical/supplement byte-identity is unsatisfiable under the current frozen revisions (`f0_mirror_adjudication_request.status = blocked-pending-controller-adjudication`). Until REC-1 or REC-2 is recorded, the gate's `canonical == authoring` wording cannot be satisfied for F0. |
| C5 | (c) | **FAIL** | `conclusion.statement_formal` (line 251) calls `AF_{I+}(M_D)` and `complete(I+_D)`; neither symbol has a machine-readable definition anywhere in the document (`visible_singularity_from_I_plus` does, via `visibility.predicate_name`). `complete` is prose-only (`i_plus.completeness_definition`). |
| C6 | (d) | **FAIL** | `quantifiers.formal` (lines 54–55) uses whole-curve single-`q` containment `gamma subset J^-(q)`, while both the schema's own `visibility.definition` (lines 219–222) and the **canonical F0** `classes.AF-WCC-VAC-GEN.conclusion.text` declare the single-`q` **TAIL** predicate (`[t0,T)`), the latter explicitly citing review HF-06. Binder order and domain ids do agree (6/6), so the defect is the predicate form, not the quantifier order. |
| C7 | binding | PASS | `declared_f0_sha256 = 276009f4f63d` equals the measured canonical F0 hash. |
| C8 | gate | PASS | `class_id` recomposes correctly, is one of the four frozen ids, `conclusion_type = weak_cosmic_censorship` matches canonical `conclusion.type` and `axes.conclusion_type`; no C0/C2 token in the conclusion statements. |
| C9 | metadata | FAIL (advisory) | `review_status.independent_reviewers` is `[]` while four hash-bound F1 reviews exist on disk at `9a8bd4c96800` (all `revise`: astra-lead-audit, deepseek-flash-19, worker-090, worker-094). |

Cross-check against the gate's own reading: `astra-life03-gate-gform` lists the same defect
families and records F1 as "accept 4.5 plus three independent revises". The preflight adds two
things that reading does not: (i) the whole-curve/tail mismatch is a **cross-artifact**
contradiction against the declared canonical F0, not only an internal one; (ii) the (b)/publication
items are now formally contested by rev26 evidence and need a controller disposition rather than
another schema edit.

## Controls (mutation matrix)

The checker ships with six controls; all six behave as declared. Each repair flips exactly its
target check to PASS, and the corrupt-hash mutation flips C7 to FAIL, so no blocking check is
vacuous under its own rewrite.

| control | mutation | target | expected | observed |
|---|---|---|---|---|
| ctl-C1 | drop earlier duplicate top-level keys (keep last-wins content) | C1 | PASS | PASS |
| ctl-C2 | stamp all machine timestamps at now−5 min | C2 | PASS | PASS |
| ctl-C3 | repoint contract to `research_map/formulation_taxonomy.yaml#classes.<CLASS>` | C3 | PASS | PASS |
| ctl-C5 | add `symbol_definitions` for `AF_{I+}` and `complete` | C5 | PASS | PASS |
| ctl-C6 | rewrite containments to `gamma([t0,T)) subset J^-(q)` | C6 | PASS | PASS |
| ctl-C7 | corrupt `declared_f0_sha256` | C7 | FAIL | FAIL |

## Files

- `check_f1_closure.py` — standalone checker (stdlib + PyYAML; no import of any swarm gate).
  Exit codes: 0 accept, 1 revise, 2 inconclusive, 3 missing input, 4 pinned-hash mismatch,
  5 control failure.
- `report.json` — full machine-readable report at the pinned snapshot (includes input hashes,
  per-check evidence, falsifiers, control matrix, snapshot verification).
- `snapshot/` — byte copies of every input at the pinned hashes, with original mtimes preserved,
  so the report is re-verifiable after the live files move.

Re-run on the post-closure revision (pre-registered command):

```bash
python3 artifacts/worker-048/f1_closure_preflight/check_f1_closure.py \
  --schema <post-closure schemas/af_wcc_vacuum.yaml> --expect-sha256 <post-closure hash> \
  --now <wall clock> --controls --out report.postclosure.json
```

Expected post-closure outcome if the author closes (a), (c), (d) and the controller records a
disposition for (b): C1, C2, C5, C6 PASS; C3 PASS only under REC-2 (repoint) or stays FAIL-but-waived
under REC-1; C4 PASS only when one logical F0 is pinned to one hash in both trees or the pair
exception is recorded. Any other outcome falsifies this report's per-check claims at the new bytes.

## Falsifier for this artifact (snapshot-bounded)

At the bytes recorded in `report.json#inputs`: (a) any FAIL check that passes on an independent
re-implementation reading those same bytes; (b) any PASS check whose recorded value is not the
measured value at those bytes; (c) any control that does not flip as declared; (d) a controller
disposition already recorded at snapshot time that resolves C3/C4 and was missed here. A later
write to the live files is **not** a falsifier — it is a new revision to re-run against.

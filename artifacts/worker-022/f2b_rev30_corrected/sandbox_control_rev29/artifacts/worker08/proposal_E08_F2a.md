# Proposal E08-F2a (execution worker 08) — for lead-formulation approval

**Status: PROPOSED, NOT ASSIGNED, NOT STARTED.** No assignment exists in `comms/inbox`
(0 files, checked 2026-09-11T23:22+08:00). This packet is the fallback required by the
worker brief: inspect the immediate queue, propose one artifact-backed task, claim nothing.

## 1. Why this proposal, and why now

The formulation group's critical path starts at **F0 (taxonomy, status `done`)** → F1 (active)
→ F2 (queued, unowned). While building the evidence base for this proposal I ran a read-only
gate over `research_map/research_map.json` and it **fails**:

| node | status | validation_status | declared artifact | exists on disk |
|---|---|---|---|---|
| F0 | done | passed | `research_map/formulation_taxonomy.yaml` | **no** |
| A0 | done | passed | `evaluation_rubric.yaml` | **no** |

`python3 research_map/validate_map.py` still prints **VALID**, because it checks only that a
done node *declares* a non-empty artifact string; it never stats the path
(`validate_map.py` lines 23-26). This is the exact failure mode ASTRA_HANDOFF.md hard
decision 4 forbids ("A completed node requires an artifact and validation evidence"), and it
blocks F1, F2, L0, L1 and A1 by dependency. Full machine-readable evidence:
`artifacts/worker08/map_artifact_gate.json` (reproduce:
`python3 artifacts/worker08/check_map_artifacts.py`; exit 1 = fail).

The immediate queue (`research_map/ASTRA_HANDOFF.md` line 39) has one **unowned, class-bound**
node: F2, "write separate C2 and C0 strong-censorship schemas; never use 'C0 or C2'". This
proposal claims only the C2 half, because hard decision 1 keeps the two classes separate.

## 2. Proposed assignment

- **Task ID:** E08-F2a  **Node:** F2  **Group:** formulation  **Class:** `AF-SCC-C2-VAC-GEN`
- **Assignee:** deepseek-flash-08 (1 agent, ~2.0 agent-hours, 2 checkpoints)
- **Deliverable:** `schemas/af_scc_c2_vacuum.yaml` (map default path is
  `schemas/af_scc_regularities.yaml`; splitting it into one file per class is itself a
  decision for lead-formulation + Astra, because the map currently names one artifact for two
  classes that must never be merged).
- **Explicitly out of scope:** class `AF-SCC-C0-VAC-GEN` (separate task E08-F2b), class
  `AF-WCC-VAC-GEN` (F1), class `AF-WCC-SCALAR-SPH` (N0), and any conclusion in terms of
  C⁰-inextendibility.

The artifact must define the class with exact quantifiers, topology, weighted initial-data
class, genericity, I⁺, visibility (defined or explicitly marked *not part of the conclusion*),
and conclusion type. Wording of the C²-inextendibility statement and its source attribution
are **L1 citation dependencies**, recorded as `unresolved`; the draft may carry them only as
unresolved, never as verified.

## 3. Acceptance tests (machine-checkable where marked)

| id | check | machine |
|---|---|---|
| T1 | file exists at approved path, parses as YAML, `class_id == AF-SCC-C2-VAC-GEN` | yes |
| T2 | all required fields present and non-empty | yes |
| T3 | no foreign class id anywhere in the file | yes |
| T4 | every C⁰ token lives inside `anti_scope`; merged phrase "C0 or C2" absent | yes |
| T5 | `conclusion_type` in the schema enum; `open_problem`/`formal_model` unless a proof or L1-verified source is attached | yes |
| T6 | conclusion matches C²-inextendibility vocabulary, does not assert C⁰-inextendibility | yes |
| T7 | genericity names a topology/measure **and** a data topology | yes |
| T8 | provenance entries carry `citation_status ∈ {verified, unresolved}`; `unresolved_citations` present | yes |
| T9 | artifact recorded `unverified` until reviewer A1 accepts | yes |
| T10 | `check_map_artifacts.py` passes for the new artifact once the map marks it done | yes |

## 4. Rejection criteria and next falsifiers

- **R1 / FALSIFIER-1 (class leakage):** any C⁰-inextendibility conclusion or "C0 or C2" token
  outside `anti_scope` → reject.
- **R2 / FALSIFIER-2 (conclusion inflation):** `conclusion_type: theorem` with no proof
  artifact and no L1-verified source → reject.
- **R3 / FALSIFIER-3 (unenforceable visibility):** `visibility` used in the conclusion without
  a definition on the completed spacetime and a stated causal relation → revise.
- **R4 / FALSIFIER-4 (unbacked artifact):** node marked done while the file is absent or its
  hash does not match → reject done-status (the F0/A0 failure mode).

## 5. Preconditions and blockers

1. **F0 artifact missing** (blocker, see §1): F2 `depends_on` F0; the gate must pass before any
   downstream done-status is credible.
2. **Lead approval pending**: class binding, acceptance tests and artifact schema must be
   approved by lead-formulation per ASTRA_HANDOFF.md hard decision 3.
3. **L1 ledger absent** (`ledger/theorems.jsonl`): citation resolution cannot start; draft may
   proceed with `unresolved_citations` populated.

## 6. Evidence refs

`research_map/ASTRA_HANDOFF.md` (lines 30-31, 39, 62-64); `research_map/research_map.json`
(F0/F1/F2 nodes, line 62 cross edge); `research_map/ARCHITECTURE.md` (lines 13, 22, 46);
`artifacts/worker08/map_artifact_gate.json`; base `HANDOFF.md` §3 item 8, §6.

Machine-readable twin: `artifacts/worker08/proposal_E08_F2a.json`.

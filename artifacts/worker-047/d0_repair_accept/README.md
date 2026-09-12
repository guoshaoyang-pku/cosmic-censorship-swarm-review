# W047-D0-REPAIR-ACCEPT-02 — independent repair-acceptance verification

**Worker:** worker-047 · **Created:** 2026-09-12T00:37+08:00 · **Verdict:** `revise` (score 2.5)
**Node ids:** F0, F1, F2a, F2b · **Class ids:** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
**Task:** did the rev12 D0 well-typedness repair hold *end-to-end* across the class-contract
chain `canonical schema → declared-F0 pointer target → lead supplement`?

**Authority:** worker evidence only. Read-only with respect to canonical artifacts; this
directory is the only thing written. No gate verdict, no node status, no `validation_status`,
no canonical-file edit. The controller/leads own those.

## Why this task

The prior worker-047 task (`W047-GFORM-D0-XCLASS-01`, outbox 2026-09-12T00:30:19) found the
family-wide defect: D0 was a two-member disjunction while the binder was the pair `(s,delta)`
and the only ambient object was the weighted Sobolev product. A rev12 repair landed at
00:31–00:32: D0 is now a tagged disjoint union `r = smooth | (sobolev,s,delta)`, the binder is
`forall r in D0`, and `X^r_vac(AF)` is declared per branch. Its own falsifier required a
re-run at the **next canonical revision**; this is that run. worker-091, bound to the previous
taxonomy hash `276009f4`, explicitly asked for a fresh verdict at `0abb9ed8a961`; this binds it.

## Pinned inputs (all byte-stable across read; snapshots in `snapshot_rev12/`)

| key | path | rev | sha256 | bytes |
|---|---|---|---|---|
| F1 | `schemas/af_wcc_vacuum.yaml` | 12 | `cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3` | 36014 |
| F2a | `schemas/af_scc_c2_vacuum.yaml` | 12 | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` | 29976 |
| F2b | `schemas/af_scc_c0_vacuum.yaml` | 12 | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` | 34984 |
| TAX | `research_map/formulation_taxonomy.yaml` | 5 | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` | 36372 |
| SUP | `artifacts/formulation/formulation_taxonomy.yaml` | 9 | `d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1` | 21699 |
| CE | `artifacts/formulation/evidence/taxonomy_consistency.json` | — | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` | 495 |

## Method

Nine acceptance criteria A1–A9 were fixed in the instrument **before** the run (text in the
report's `pre_registered_criteria`), plus ten synthetic controls K1–K10 that must flip exactly
as pre-registered. A control mis-calibration makes the run fail closed (exit 2). The run is
deterministic (run2 == run3 modulo `created_at`), no network, and fails closed on unreadable or
drifting inputs. Run 1 failed closed on a genuine instrument bug (A4 probed
`conclusion.statement_formal` for the ambient subscript, which only `quantifiers.formal` carries
in F2a/F2b); the criteria were not weakened — the probe was corrected and re-calibrated. Run 1
is retained as `report_run1_instrument_bug.json` for provenance.

## Result

| criterion | F1 | F2a | F2b |
|---|---|---|---|
| A1 D0 typed union | PASS | PASS | PASS |
| A2 binder consistent (`forall r in D0`) | PASS | PASS | PASS |
| A3 ambient per branch | PASS | PASS | PASS |
| A4 G_r / X^r_vac indexing | PASS | PASS | PASS |
| A5 pointer resolves + hash-pins | PASS | PASS | PASS |
| **A6 pointer target typed (end-to-end)** | **FAIL** | **FAIL** | **FAIL** |
| A7 supplement aligned | INFO | INFO | INFO |
| A8 consistency evidence covers typing | FAIL (shared) | | |
| A9 no regression (dup keys, D0 identity) | PASS | PASS | PASS |

Controls: **K1–K10 all PASS** (10/10 calibrated). Verdict `revise` 2.5.

### RA-1 (critical): the repair stops at the schema; the pointed-to contract is still pair-bound

Each schema now declares
`class_contract_pointer: research_map/formulation_taxonomy.yaml#classes.<ID>` and
`f0_binding.declared_f0_sha256 == 0abb9ed8a961…` (A5 PASS). But the resolved class entry's
`conclusion.text` still reads, at taxonomy lines **193 / 274 / 346**:

> For every admissible **(s,delta)** there is a comeager set **G_{s,delta}** of data such that …

So the declared class contract binds the pair over a D0 that the same repair has just retyped
as a union containing the non-pair member `r = smooth`, and names a comeager set `G_{s,delta}`
that the schema no longer defines. Before rev12 the pointer resolved into the authoring tree
(hygiene finding); the re-point now makes this canonical. The taxonomy's own `H4` says the
weighted spaces `(s, delta)` "are owned by F1 and are unresolved here", and its `scope_statement`
says downstream-owned values "must be replaced, not inherited silently" — neither has happened
for the conclusion text.

### RA-2 (major): the green consistency evidence is silent on this relation

`taxonomy_consistency.json` reports `consistent: true`, `contract_divergences: []`, and compares
only `map_taxonomy` vs `lead_contract`. It does not compare the three schemas' D0/binder normal
forms, so it certifies a green state while A6 fails in all three classes (A8 FAIL).

### RA-3 (advisory): the supplement carries no typed index

The supplement `class_contracts.<ID>.conclusion_predicate` has no quantifier and its
`data_class_freeze` says "smooth-with-decay default with a registered Sobolev variant", which is
consistent with rev12 but cannot discharge the typed contract on its own.

## Minimal repairs (for the owner; not applied here)

1. Amend `classes.<ID>.conclusion.text` in the canonical taxonomy to the r-indexed form
   (`forall r in D0 … G_r subset X^r_vac(AF) …`) for all three classes, refresh
   `declared_f0_sha256`/`revised_at`, or record an adjudication that the taxonomy conclusion
   text is non-binding and re-point the schemas at the binding contract (RA-1).
2. Extend the consistency checker/evidence to compare schema D0/binder normal forms against the
   contract targets, or record the scope limitation in the evidence JSON (RA-2).
3. Add a typed D0 union component to the supplement contracts or explicitly subordinate them to
   the canonical taxonomy (RA-3).

## Falsifier

RA-1/RA-2 are falsified if, at a later canonical revision, each resolved contract target binds
the D0 index `r` (or a single regime) with `G_r`/`X^r_vac(AF)` and no `(s,delta)` pair binder,
`declared_f0_sha256` is refreshed, **and** the consistency evidence covers (or explicitly
disclaims) the schema↔contract typing relation. A later file write alone is not a falsifier:
the fresh hash must be measured and these criteria re-run.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-047/d0_repair_accept/check_d0_repair_accept_047.py \
    --strict --out /tmp/w047_ra.json \
    --snapshot-dir /tmp/w047_ra_snap    # expect exit 1: A6 x3 + A8 FAIL, controls 10/10
```

## Limitations

- A6 is an end-to-end *typing* criterion; it makes no physics claim and does not assess the
  mathematical truth of either censorship statement.
- F2a/F2b `conclusion.statement_formal` is the compact form and intentionally omits the ambient
  subscript (carried in `quantifiers.formal`); the instrument checks both fields accordingly.
- The verdict is bound to the six hashes above; later writes are outside its scope.

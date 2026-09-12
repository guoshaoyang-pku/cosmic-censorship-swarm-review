# W092-F2A-REV13-FULL-01 — independent F2a verdict at FROZEN rev29

**Verdict: `revise` (score 3.5)** for `AF-SCC-C2-VAC-GEN` at F2a
`e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe`, FROZEN rev29
`815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0`.

- worker-092, no inbox card existed for this slot. One bounded class-bound task taken:
  the first *full-schema* verdict at the final rev29 pins after
  `astra-life05-evidence-binding-repair` landed (the superseded rev12 hashes
  `cce9c60146d6` / `5476a3f2c6bc` / `55d0a1ea9bda` are void for coverage).
- Read-only on canonical paths. The instrument is independent (stdlib + PyYAML, no import of
  the canonical gate or consistency checker). 12/12 mutation controls fire; entry==exit for
  all 13 pre-registered pins.
- Worker measurement only: sets no node status, no `validation_status`, no gate verdict.

## Class content is clean at these bytes

| axis | result |
|---|---|
| identity / revision / sibling | `AF-SCC-C2-VAC-GEN`, rev13, disjoint from `AF-SCC-C0-VAC-GEN` |
| strict YAML, duplicate keys | 0 duplicate keys at any depth |
| conclusion token | `scc_c2_future_inextendibility`, registry-canonical, no C0 merge, no WCC inflation |
| D0 | tagged disjoint union `{smooth, (sobolev,s,delta)}`, `s > 5/2`, `delta in (1/2,1)` |
| quantifier chain | `forall r in D0 exists G_r comeager forall D in G_r: not exists proper_future_extension_in_class(MGHD(D))` |
| no theorem inflation | `epistemic_status=open_problem`, `known_status.status=open_problem` |
| canonical structural gate | `check_class_schema.py --json` exit 0, `failed_rules=[]` |
| class-separation detector | 0 findings; no class-shaped token outside the frozen four |

## Repair-card items at rev29 (astra-life05-evidence-binding-repair)

| item | state | measurement |
|---|---|---|
| I1 rebind `taxonomy_cases.jsonl` | **closed** | 36/36 rows `bound_taxonomy_sha_0abb9ed8a961`; meta `taxonomy_ref` = rev5 `0abb9ed8a961` |
| I2a declared evidence hash resolves | **closed** | 3/3 schemas declare `9e335e9ba1bf` == measured |
| I2b evidence *binds* compared trees | **open** | 495-byte evidence carries paths + `consistent:true`, no `map_taxonomy_sha256` / `lead_contract_sha256` |
| I3 F1 SET strictness | **closed** | schema line 235 now "strictly WEAKER"; SET delta rebased to rev13 with corrected `strength` |
| I4 FROZEN rev29 + events | **closed** | rev29, 50/50 pins resolve, `verify_frozen.py` exit 0, artifact events exist for every moved hash |

## Hard failures (all hash-bound, each with a falsifier)

| id | axis | falsifier |
|---|---|---|
| `HF-W092-R13-01` | consistency evidence is not hash-bound to the two compared trees (standing `HF-043-2` / `HF-035-F2A-2` / `HF-19-F2A-3` / `HF-088-F2a-CE` second half still unsatisfied at rev29) | evidence bytes contain the measured sha256 of `research_map/formulation_taxonomy.yaml` (0abb9ed8) and of the supplement (d7419b4e), declared pin == measured, re-freeze |
| `HF-W092-R13-02` | canonical evidence path was rewritten at 00:59:25, after the schema's `checked_at` 00:53:20 (bytes unchanged, `9e335e9b`): the unguarded canonical checker rewrites the path unconditionally | install the non-writing guard (worker-086 `cde1a165` / worker-022 guard) or run the checker only in sandboxes; re-stamp `checked_at` after the last rewrite; a quiet interval with `evidence_mtime <= checked_at` closes it |
| `HF-W092-R13-03` | `W090-VOCAB-01`: `conclusion_type` is the VOCAB_ALIASES canonical token, not the F0 `field_vocabulary.allowed` literal; worker-017's gate experiment shows the frozen gate *rejects* the F0 literal (R11) and accepts the registry canonical | a controller ruling recorded in the map, or an F0 allowed-list amendment at a pinned hash |
| `HF-W092-R13-04` | `HF-091-02`: `extension_predicate` does not freeze the manifold category of `M'` nor the regularity of `iota` (clauses (a)/(c)) | add the manifold category and `iota` regularity to `extension_predicate` at a new revision |
| `HF-W092-R13-05` | `HF-069R-2`: `run_acceptance.py` preflight still fails closed — rebased corpus base `1bb78ce9b357` != live authoring C0 `b2ab6acb2bbe` | rebase the semantic-escape corpus to the live C0 and re-run `run_acceptance.py` to exit 0 |

Minor, non-blocking: `l1_ledger_refs` uses `citation_status: verified_by_L1` (4/5 entries) — an
out-of-vocabulary token; worker-007's census found the underlying references resolved and verified
(no overclaim). Token hygiene only.

## Reproduction

```bash
python3 artifacts/worker-092/f2a_rev13_review/verify_f2a_rev13.py --stamp <iso8601>
# exit 0 accept / 1 revise / 3 pin drift (no report written)
```

`report.json` carries the 27 checks, the 12 controls, the closure matrix and the falsifier list.
The instrument aborts without writing if any pre-registered pin drifts.

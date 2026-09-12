# W054-GFORM-VERDICT-HASH-INTEGRITY-01 — worker-054

Measured at `2026-09-12T00:58:08.620504+08:00` (worker report only; no gate verdict).

## Canonical bytes at run start vs map declaration

| artifact | sha256 (16) | node hash in frozen map | match |
|---|---|---|---|
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c9` | `0abb9ed8a96135c9` | yes |
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79e` | `cce9c60146d6a907` | NO |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd308bd` | `5476a3f2c6bc7196` | NO |
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe7f86` | `55d0a1ea9bda96b8` | NO |

## Review-event classification

| classification | count |
|---|---|
| `AMBIGUOUS_TARGET` | 65 |
| `EVIDENCE_ONLY_HASH` | 185 |
| `STALE_BOUND` | 4 |
| `UNBOUND` | 113 |
| `UNRESOLVED_BOUND` | 98 |
| `VERIFIED_BOUND` | 19 |
| reviews total | 484 |

## Distinct reviewers bound to the current bytes

| target | accept (bound) | revise (bound) | criterion (>=2 distinct bound accepts) |
|---|---|---|---|
| F0 | deepseek-flash-18, worker-025, worker-038, worker-041, worker-067, worker-087 | astra-lead-audit, worker-003, worker-047, worker-048, worker-067 | **met** |
| F1 | — | worker-018, worker-095 | **not met** |
| F2a | worker-017, worker-072 | worker-066 | **met** |
| F2b | — | worker-044 | **not met** |

## Flags

- frozen input copies byte-stable: `{'events.jsonl': True, 'research_map.json': True, 'FROZEN.json': True}`
- run void: `False`
- canonical bytes changed since snapshot: `{'schemas/af_wcc_vacuum.yaml': False, 'schemas/af_scc_c2_vacuum.yaml': False, 'schemas/af_scc_c0_vacuum.yaml': False, 'research_map/formulation_taxonomy.yaml': False}`
- review events citing at least one path not covered by the FROZEN pin set: 404

## Falsifier

Re-run integrity.py in an unchanged tree: any classification that changes, any live input hash differing from input_snapshot_sha256, or a cited prefix resolving to non-matching bytes falsifies this report. Valid only while drift.detected is false.

# W035-F0-CLASSSEP-REPAIR-01 — worker-035 bounded task

## What this is

A hash-bound repair proposal for the **only hard evidence failure** in the swarm at
2026-09-12T00:20:07+08:00 (map sha256 `7f8792f85f0cfcde83997cd0fc1eb4a17d6be15393a520dbc63912619460fa3a` (re-pinned; see `checkpoint.json`)):

```
CLASSSEP: composite C0/C2 asserted as one class in claims[36].statement:
...'.directive=astra-classscope-02; the 2 split rows (TC-F0-N14 C0/C2 merge,
TC-F0-N15 WCC/SCC merge) need no new class and are d'
```

Target claim: `flash02-opencase-claim-0010b-20260912T0015` (node F0, gate G-F0,
classes `AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN`).

## Why the finding is prose-only

`schemas/taxonomy_cases.jsonl` records TC-F0-N14 (`as_filed_class_id=COMPOSITE_C0_C2`)
and TC-F0-N15 (`as_filed_class_id=COMPOSITE_WCC_SCC`) as **negative** fixtures with
`expected_resolution=reject_split_required`. The claim's shorthand "C0/C2 merge" *names
the case*, not an accepted fusion, but `research_map/class_separation.py` rule R1 sees a
composite token followed by `merge` inside its match window (the nearby word "split" sits
outside/precedence) and fires. The repair rewords only that clause, keeps every count and
identifier, and asserts the separation explicitly.

## Files

| file | sha256 (first 12) |
|---|---|
| `run_repair_check.py` | `21e9bf818dff` |
| `proposal.json` | `f786bddcfdb7` |
| `verification.json` | `a84283ce3df3` |
| `proposed/map_patch_claim_statement.json` | `d06fdf11f692` |
| `proposed/research_map.patched.json` | `8834c4419c75` |

Full hashes in the `.sha256` sidecars.

## Evidence

`run_repair_check.py` (offline, deterministic, 14/14 checks pass):

1. reproduces the single hard finding on the pinned bytes;
2. the reworded map differs **only** at `/claims/36/statement`;
3. the project's own `audit_evidence.audit()` on the patched **copy** reports
   `0` hard findings (baseline: exactly this `1`);
4. content invariants (9 cases / 7 deferred / 2 split / 0 new class ids / 0/9 rows /
   TC-F0-N14 / TC-F0-N15 / astra-classscope-02 / lead-decidable) are preserved;
5. a genuine merge paraphrase in the same slot is **still flagged** (detector not weakened);
6. the canonical `research_map.json` is byte-unchanged by the run.

## Acceptance / falsifier

Acceptance: controller replaces the statement of the claim identified **by event id**
(index may shift) and `python3 research_map/audit_evidence.py` exits 0.

Falsifier: stale precondition hash; any CLASSSEP finding on the patched map; any change
outside the target statement path; the negative control not flagged; validator no longer
VALID.

## Non-claims

Not a gate verdict; does not set `validation_status=passed`; does not edit the canonical
map; does not adjudicate the taxonomy cases themselves. Worker events emitted:
`comms/outbox/worker-035.jsonl` (4 artifact, 1 review, 1 claim, 2 status; 8/8 ingested, 0 rejected), ingested with
0 rejects; worker checkpoints `ckpt-20260912-002143`, `ckpt-20260912-002239`.

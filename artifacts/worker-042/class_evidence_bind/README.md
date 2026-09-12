# W042-CLASS-EVID-BIND-01 — class-bound evidence binding audit

- actor: worker-042; snapshot events.jsonl `ff3ae81f3938` (1293 events, 1293 lines); scan 2026-09-12T00:21:02+08:00 → 2026-09-12T00:21:02+08:00
- method: classify every evidence_ref of every claim bound to a frozen class; re-hash the files on disk; compare artifact-event sha256 declarations; re-hash at end for stability.
- re-run: `python3 artifacts/worker-042/class_evidence_bind/audit_class_evidence.py --events artifacts/worker-042/class_evidence_bind/snapshot/events_ff3ae81f3938.jsonl`

## Headline (snapshot-bound)

- frozen-class claim events: 45 of 50 claim events; evidence_refs on them: 190
- ref verdicts: hash_match=77, hash_stale=39, line_ref=1, unpinned=10, unresolvable=63
- class-bound artifact events: 276 of 561; verdicts: match=168, stale=108

## Per frozen class

| class | claims | refs | hash-bound | match rate | artifacts match/stale/missing |
|---|---:|---:|---:|---:|---|
| AF-WCC-VAC-GEN | 18 | 89 | 56 | 0.75 | 94/51/0 |
| AF-SCC-C2-VAC-GEN | 16 | 67 | 53 | 0.717 | 98/43/0 |
| AF-SCC-C0-VAC-GEN | 22 | 99 | 67 | 0.6866 | 96/59/0 |
| AF-WCC-SCALAR-SPH | 14 | 57 | 41 | 0.8049 | 65/21/0 |

## Findings (each carries its own falsifier)

- **W042-EB-01** (major): 39 hash-pinned evidence_ref(s) in class-bound claims cite a sha256 prefix that no longer matches the file on disk at snapshot ff3ae81f3938.
  - falsifier: Re-run this checker on the same events.jsonl sha256. This finding is FALSIFIED if any ref classified hash_stale re-hashes to a prefix match; a change to the inputs after the snapshot is not a falsifier.
- **W042-EB-03** (minor): 10 evidence_ref(s) name an existing file with no hash or line anchor (protocol rule 4 asks for `path#sha256-prefix`).
  - falsifier: Re-run this checker on the same events.jsonl sha256. This finding is FALSIFIED if any ref classified unpinned turns out to carry a hash prefix; a change to the inputs after the snapshot is not a falsifier.
- **W042-EB-04** (minor): 63 evidence_ref(s) cannot be mapped to a repo-relative path or line anchor (prose-only citations are not machine-checkable).
  - falsifier: Re-run this checker on the same events.jsonl sha256. This finding is FALSIFIED if any ref classified unresolvable resolves to a repo path on re-parse; a change to the inputs after the snapshot is not a falsifier.
- **W042-EB-05** (major): class-bound artifact events at this snapshot: 168 match, 108 stale, 0 missing, 0 with a non-hash sha256 placeholder.
  - falsifier: Re-run this checker on the same events.jsonl sha256. This finding is FALSIFIED if any artifact classified stale/missing/placeholder re-checks as a match; a change to the inputs after the snapshot is not a falsifier.

## Interpretation limits (why a stale verdict is not an accusation of error)

- A `hash_stale` verdict means the cited bytes changed after the event was written; the declaration may have been true at write time. It is exactly the binding-drift the controller records in CF-11/CF-13 and the G-FORM unmet item 'no accept at the current hash'.
- `unresolvable` refs are prose citations (`file.md line 39`, `map F2 line 28`); they cannot be machine-checked and are reported, not judged.
- Frozen schemas are expected to be revised; the actionable quantity is how many class-bound claims/artifacts still resolve to the current canonical bytes at the snapshot.

## Top drift targets (stale refs per file)

- `artifacts/formulation/FROZEN.json`: 3
- `artifacts/worker-06/blindspot_report.json`: 3
- `research_map/formulation_taxonomy.yaml`: 3
- `artifacts/flash-13/form_gate/gate_report.json`: 2
- `artifacts/worker-06/canonical_gate_run.json`: 2
- `research_map/research_map.json`: 2
- `schemas/af_scc_c0_vacuum.yaml`: 2
- `schemas/af_scc_c2_vacuum.yaml`: 2
- `schemas/af_wcc_vacuum.yaml`: 2
- `artifacts/flash-13/form_gate/check_class_schema.py`: 1

## Scope / non-claims

- This is a snapshot audit of a live workspace; verdicts bind to the recorded hashes only.
- No node is marked done, no gate verdict is claimed, no canonical artifact was edited.
- Classification is mechanical: `path#<hex-prefix>` is the only machine-checkable binding.

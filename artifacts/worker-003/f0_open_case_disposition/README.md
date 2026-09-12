# W003-F0-OPEN-CASE-DISPOSITION-01 — disposition of the 9 open taxonomy cases

**Worker:** worker-003 · **Node:** F0 · **Gate:** G-F0 · **Class scope:** the four frozen
class ids (`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`,
`AF-WCC-SCALAR-SPH`) · **Created:** 2026-09-12T00:51+08:00

**Authority note.** Worker evidence only. This artifact sets no node status, no
`validation_status` and no gate verdict. It does not create, rename or register a class;
the taxonomy's own `class_scope_adjudication` forbids new class ids pending Human PI.

## Why this task

`research_map/research_map.json#controller_gate_audit` (G-F0) lists as unmet:
"9 taxonomy cases remain open (new class vs split) and were never dispositioned by the
lead". `schemas/taxonomy_cases.jsonl` indeed carries exactly 9 rows with `"open": true`.
No other in-flight artifact computed their disposition (worker-076 verified corpus
content/pins; worker-087 reviewed the taxonomy itself; worker-073 verified the F0 pair
binding). This probe recomputes the disposition from the frozen taxonomy bytes only.

## Pinned inputs (fail-closed on drift)

| path | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` (rev5) | `0abb9ed8a96135c9…` |
| `schemas/taxonomy_cases.jsonl` | `ccf7041bd0ff3ce8…` |
| `artifacts/flash-02/leak_rule_catalog.json` | `ccec815ea61d5eb2…` |
| `artifacts/formulation/formulation_taxonomy.yaml` (F0-R supplement) | `d7419b4e8963cb71…` |

Zero drift before/after the run; the probe exits 3 on any pin change.

## Result — 9/9 recomputed, 9/9 agree with the corpus

| case | filed as | recomputed | gap kind / split targets | declared rule (supported) |
|---|---|---|---|---|
| N01 | AF-WCC-VAC-GEN | NO_CLASS | in-vocab, unmatched | G5 ✓ |
| N02 | AF-WCC-VAC-GEN | NO_CLASS | in-vocab, unmatched | G4 ✓ |
| N04 | AF-SCC-C2-VAC-GEN | NO_CLASS | out-of-vocabulary (electrovacuum) | G5 ✓ |
| N09 | AF-SCC-C0-VAC-GEN | NO_CLASS | in-vocab, unmatched | G4 ✓ |
| N10 | AF-WCC-SCALAR-SPH | NO_CLASS | in-vocab, unmatched | CG2+G4 ✓ |
| N11 | AF-WCC-SCALAR-SPH | NO_CLASS | in-vocab, unmatched | G5 ✓ |
| N14 | COMPOSITE_C0_C2 | **SPLIT** | → AF-SCC-C0 + AF-SCC-C2 | G3 ✓ |
| N15 | COMPOSITE_WCC_SCC | **SPLIT** | → AF-WCC-VAC + AF-SCC-C2 | X4 ✓ |
| N16 | AF-SCC-C0-VAC-GEN | NO_CLASS | out-of-vocabulary (Λ>0, de Sitter) | CG2 ✓ |

7 coverage gaps, 2 split cases, 0 silent refiles to an existing class.

## Minimal decision surface — 5 candidate descriptors

The 7 gap cases collapse to 5 distinct axis bundles (N01=N10 and N02=N11 are duplicates):

| id | axis bundle (family, matter, symmetry, asymptotics) | cases |
|---|---|---|
| CGAP-01 | SCC, electrovacuum (OOV), —, — | N04 |
| CGAP-02 | SCC, vacuum+Λ>0 (OOV), —, de Sitter (OOV) | N16 |
| CGAP-03 | SCC, massless_scalar_field, spherical, AF | N09 |
| CGAP-04 | WCC, massless_scalar_field, none_assumed, AF | N01, N10 |
| CGAP-05 | WCC, vacuum, spherical, AF | N02, N11 |

Candidate descriptors are unregistered analysis objects, **not** class ids.

## Findings

- **W003-DISP-03 (hard, process).** All 7 gap rows sit on a same-artifact rule conflict:
  `coverage_gaps.CG2` says such claims "must open a new class rather than be filed here",
  while `class_scope_adjudication` says "new class ids are rejected pending Human PI".
  No lead action can close the 7 inside the frozen taxonomy — the actionable path is
  candidate-descriptor registration plus Human PI escalation. The 2 splits are actionable
  with existing class ids.
- **W003-DISP-04 (minor).** CG2 enumerates "non-spherical matter models, Λ≠0, higher-genus
  ends", but two measured bundles are not instances of that text: CGAP-05 (spherical
  vacuum, no matter field) and CGAP-03 (spherical scalar SCC — missing axis is
  family/regularity, not matter). CG2 under-describes the gap set the corpus opens.
- **W003-DISP-05 (minor, corpus metadata).** Within the same
  `expected_resolution=reject_new_class_required`, `gate_expectation` is `reject` for
  N01/N02/N11 but `reject_new_class_required` for N04/N09/N10/N16.

## Method and controls

`dispose_open_cases.py` (stdlib + PyYAML, deterministic): selects `open == true` rows;
for each, matches the row's structural axis vector against the four class descriptors'
axes (`family, matter_model, symmetry, asymptotics, regularity_token, conclusion_type`;
`genericity_kind` excluded as provisional/owned by F1/F2); recomputes the guard set from
the axis diffs + `CG2`; derives split targets for composite filings by normalized C0/C2
token extraction; clusters gaps by axis bundle; compares against the corpus' declared
`expected_classification` / `expected_leak_rule` / `expected_resolution`.

Declared expectations: **13/13 pass**. Planted controls (in-memory mutants only):
**10/10 pass** — exact-class-match→refile, adding a covering class flips N02, removing the
filed class changes N11, open-flag mutation, pin-mutation detection, composite→split,
positive-case negative control, tampered expectation flagged, vocabulary extension moves
N04's gap kind, empty open set.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-003/f0_open_case_disposition/dispose_open_cases.py   # exit 0
sha256sum artifacts/worker-003/f0_open_case_disposition/report.json
```

Report: `artifacts/worker-003/f0_open_case_disposition/report.json`
(sha256 `b391f8b53a21015600cfc36566ad2a3f66cf0c84bf7ed8f989dadaac3bfc5d3e`).

## Falsifiers

- Any pinned input hash moves → every verdict is advisory and the drift guard fires (exit 3).
- A re-run at the pinned hashes that classifies any of the 9 differently, or an `open` set
  different from {N01,N02,N04,N09,N10,N11,N14,N15,N16} → voids the corresponding verdict.
- Showing any gap row is covered by an existing class descriptor → voids W003-DISP-01/02
  and the corresponding candidate descriptor.
- Showing that a lead may create a new class id without Human PI, or that CG2's phrase is
  defined elsewhere to include spherical vacuum / spherical SCC → voids W003-DISP-03/04.
- Showing `gate_expectation` documents the immediate verdict while `expected_resolution`
  documents a downstream requirement → voids W003-DISP-05 as a divergence.

## Non-claims

Not a mathematical verdict on any class statement. `NO_CLASS_IN_TAXONOMY` is about the
four frozen descriptors, not about the admissibility or interest of the missing class.
The corpus' `expected_*` fields are deepseek-flash-02's test expectations, not independent
authority. Whether any row blocks G-F0 is the audit lead's and controller's call.

# W072-F2B-INTERNAL-CONSISTENCY-01

Class-bound self-audit by worker-072 of its own F2b rev29 accept.

- **Class**: `AF-SCC-C0-VAC-GEN` (node `F2b`, gate `G-FORM`)
- **Target**: `schemas/af_scc_c0_vacuum.yaml`
  pinned at `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c`
  under `artifacts/formulation/FROZEN.json` rev29 `815e08079aefbc...`
- **Question**: do the two internal contradictions reported by the formulation
  lead lifecycle-07 (measurement 5) and first raised as blocking by worker-018
  (`W018-R13-F2B-B1/B2`) exist at the live frozen bytes — and if so, can
  worker-072's earlier full accept stand?

## Result

Both defects are present at the pin; the earlier accept is superseded to
`revise`.

| id | carrier | defect |
|---|---|---|
| D1 | `regularity.must_not_conflate[0]` (line 152) | denies C2/C0 containment while lines 239/241-244/250 assert `E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇ E_C2`; sibling F2a line 152 records the same denial as wrong |
| D2 | `implication_ledger.forbidden_transfers[0].reason` (line 246) | calls C2 the "strictly larger extension class" while line 239 makes `E_C2` innermost; the prohibition and the "weaker" conclusion are correct, the size premise is inverted (line 225 labels C2/C1/H2loc conclusions WEAKER) |

Instrument: 17/17 deterministic checks pass (all anchors verified), 7/7 mutant
controls discriminate exactly as pre-registered, target hash and mtime stable
before/after (read-only, no network, no model calls).

## Why the earlier accept was wrong

`artifacts/worker-072/f2b_review/check_f2b.py` (33 checks, all PASS) had no
internal cross-field consistency test: it verified each required slot in
isolation and never confronted `must_not_conflate[0]` or
`forbidden_transfers[0].reason` with the file's own `implication_ledger`
containment. That is an instrument gap, disclosed as finding F-06 in the
superseding review, not a hash or binding failure.

## Files

- `check_f2b_internal.py` — deterministic checker and mutant-control runner
- `report.json` — check results at the live pin
- `report_with_controls.json` — same plus control rows
- `controls/controls_summary.json` — K0-K5, K3b
- `MANIFEST.json` — sha256 of every file here

## Authority

Worker evidence only. No node status, no `validation_status=passed`, no gate
verdict, no write to `schemas/` or `artifacts/formulation/`. Gate coverage and
the blocking/advisory weight of D1/D2 belong to the audit lead at
`astra-life05-verify-gform-r3`.

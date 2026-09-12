# W036-CLASSSEP-DISJ-RULE-01 — staged container-disjunction rule (class-binding coverage fix)

**Worker:** `worker-036` · **Node:** `A1` · **Gate:** `G-AUDIT` / `G-CLASSBIND` · **Classes:** the four frozen
`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH` · **Generated:** 2026-09-12 ~00:50 +08:00

**Verdict:** the staged R5 rule closes the `class_ids` container blind spot measured in
`W036-CLASSSEP-DISJ-01/02/03`, with zero regressions on the standing corpus and zero change to any
non-container surface (probe `overall: PASS`, 23/23 checks, exit 0). It is **not applied** to any
canonical file, and its live blast radius is measured rather than assumed.

## Why this task exists

`W036-CLASSSEP-DISJ-01` (previous worker-036 lifecycle) measured that canonical
`research_map/class_separation.py` at `c266dbceca87` is silent on a `class_ids` container holding two or
more distinct frozen classes: the detector's `_scan_class_ids` checks each token for an internal
`C0`+`C2` merge or for being an unknown `AF-` token, and never looks at the container. Eight live
`ledger/theorems.jsonl` rows carry `C2+C0` / `WCC+C0` containers and were invisible; the standing
27-fixture regression corpus contains no such shape. That earlier lifecycle stopped at the finding and
named two unblock paths. This lifecycle executes path (a) as a **staged, measured candidate** (path (b),
a rubric scoping note, is not attempted here).

## What is staged

| file | sha256 (full) | role |
|---|---|---|
| `build_candidate.py` | see `CHECKPOINT.json` | mechanically derives the candidate from the pinned canonical snapshot; fails closed on hash/anchor mismatch |
| `candidate_class_separation.py` | see `CHECKPOINT.json` | canonical + exactly one inserted hunk (10 added lines, 0 removed); reverse-apply reproduces canonical byte-for-byte |
| `fixtures/disj_fixtures.jsonl` | see `CHECKPOINT.json` | 26 pre-registered cases: 8 positives, 13 negatives/orthogonality, 1 map-level, 3 text-route scope cases |
| `probe_disj_rule.py` | see `CHECKPOINT.json` | deterministic probe; all inputs read from `snapshots/`, no canonical file written |

The inserted rule (R5), container-level only:

```python
known = sorted({t.strip().upper() for t in toks if t.strip().upper() in KNOWN_CLASSES})
if len(known) >= 2:
    out.append(f"CLASSSEP: class_ids container disjoins {len(known)} frozen classes in {where}: {known!r}")
```

Statement/prose text is untouched, so the CF-16 metalinguistic false-positive class cannot be affected
by construction — and that is measured, not asserted (fixtures `N8`, `N12`, `M1`; check `H3b`).

## Measured (all from pinned snapshots)

- **Blind spot closed on the target rows.** On all three pinned L0 ledger revisions
  (`a1674f094979`, `3e3d35531421`, `ce42d205e761`) canonical yields **0** container findings and the
  candidate yields exactly rows **{3, 4, 24, 26, 29, 45, 57, 59}** — the eight rows named in
  `W036-CLASSSEP-DISJ-02` (`H4a`, `H4b`).
- **No regression.** Standing worker-07 corpus: canonical `17 tp / 0 fn / 10 tn / 0 fp`, candidate
  **identical per fixture**. Worker-027's OOD arity corpus: candidate classification unchanged (`H5a`–`H5d`).
- **Map counterfactual (frozen snapshot `3d45be5969ec`).** Canonical 10 findings → candidate **110**;
  **+100, −0**; every added finding is the container rule (`H3a`, `H3b`, `H3c` re-derives the same 100
  containers independently, label-for-label).
- **Precision is not free — the live blast radius, broken down.** Of the 100 added map findings, 94 are
  on `claims[*]` and 6 on nodes `F0`/`L0`/`L1`; by cardinality **58 are 4-class, 32 are 3-class, 10 are
  2-class** containers. The 3- and 4-class shapes are scope-metadata declarations, not singular class
  bindings. The HF-02 target population is the 8 ledger rows plus the 10 two-class map containers. The
  surface/cardinality policy is an owner decision; this packet measures the rule and its blast radius
  instead of assuming the policy.
- **Artifact-text route stays blind** (`findings_for_text` has no container parser): measured in `H7`
  and recorded as a limitation, not covered by the claim.
- **Harness power controls.** An inert R5 (threshold 99) adds nothing anywhere; an overfire R5
  (threshold 1) breaks ≥5 negative fixtures — so the battery can fail in both directions (`H6a`, `H6b`).

## Claim (worker level, `conclusion_type: formal_model`)

At the pinned hashes, R5-as-staged is a correct, regression-free coverage fix for the `class_ids`
container blind spot on structured declaration surfaces, and its live cost is exactly the 100 map
containers characterized above (8 ledger rows already adjudicated by worker-023 as needing relation
bindings rather than two class ids). This is **measurement evidence for the detector owner**, not a
gate verdict, node transition, or validated artifact.

## Falsifiers

See `report.json` `falsifiers` F1–F7; the load-bearing ones: any positive fixture unflagged or negative
flagged; any added map finding that is not the container rule; any of the 8 ledger rows missed; any
standing-corpus fixture changing classification; reverse-apply not reproducing canonical; the null /
overfire controls not behaving as measured; any measured input drifting mid-run.

## Reproduce

```bash
cd <repo root>
python3 artifacts/worker-036/classsep_disj_rule/build_candidate.py
python3 artifacts/worker-036/classsep_disj_rule/probe_disj_rule.py
```

Exit 0 ⇔ all 23 checks PASS. Inputs are read from `snapshots/` (hash-pinned in `CHECKPOINT.json`);
canonical `research_map/class_separation.py`, `research_map/research_map.json`, `ledger/theorems.jsonl`
and `runtime/state/artifact_hashes.json` are never written. `controls/` holds the two control modules
generated by the probe (inert and overfire R5) so the power controls are auditable offline.

# W085-CANDIDATE-CLASSSEP-DIFF-03 — staged detector candidate vs live class-separation surfaces

**Worker:** `worker-085` · **Node:** `F0` (surfaces F1/F2a/F2b) · **Gate:** `G-F0` · **Class:** `AF-WCC-VAC-GEN` (frozen four) · **Generated:** 2026-09-12T00:40+08:00

**Verdict:** `CANDIDATE_LIVE_INERT_HARD_COUNT_UNCHANGED` · **Checks:** 16/16 · **Probe exit 0**

**Question.** Does swapping canonical `research_map/class_separation.py` (`c266dbceca87`) for the staged candidate `proposed/class_separation.py` (`e2d24b927ee8`, worker-16 `CANDIDATE-PATCH.md`) change any class-separation finding on the live map / live artifact surfaces — in particular, does it clear the live hard CLASSSEP findings routed from `claims[i].statement` (CF-16)?

## Measured

| surface | canonical | candidate | removed | added |
|---|---|---|---|---|
| live map `3d45be59` — `findings_for_map` | 10 hard / 0 soft | 10 hard / 0 soft | 0 | 0 |
| 10 audited node artifact texts (snapshot) | 0 | 0 | 0 | 0 |
| **audit_evidence section-3 hard total** | **10** | **10** | **0** | **0** |

All 10 live findings are on `claims[*].statement` and all are already produced through the prose path (`findings_for_map` passes `mode="prose"` for claims). The candidate's R2-3 hunk changes mode selection only at *declaration-mode* call sites, so the live map is untouched. `ledger/theorems.jsonl` moved before freeze (`ce42d205e761` → snapshot `a1674f09`); the differential binds the snapshot.

## Latent deltas, attributed to hunks (synthetic battery)

| probe | surface | canonical | candidate | hunk |
|---|---|---|---|---|
| S1 bare `C0 or C2` in declaration-mode `statement` | node | hard | **none** | R2-3 |
| S8 same, list-valued `statement` | node | hard | **none** | R2-3 |
| S3 `do not split: C0 or C2` | label | none | **hard** | R2-2 |
| S9 `... merged C0/C2 ...` (the live FP shape) in declaration-mode `statement` | node | hard | **hard** | — (not cleared) |
| S2/S4/S5/S7 merge-assert shapes | node/artifact | hard | hard | — |
| S6 4-segment unknown `AF-WCC-VAC-BH` | node | none | none | tokenizer window |

**The decisive control is S9:** the candidate does not clear the live false-positive shape even on the surface it targets, because `_MERGE_ASSERT` ("merged") fires in prose mode as well. So applying the staged patch leaves the controller's hard CLASSSEP count exactly where it is; CF-16 needs a claim rephrase or a different checker change (e.g. treating test-case-name / quoted contexts), not this patch.

## Controls

- worker-07 27-fixture regression: **PASS 17/0/10/0** for both canonical and candidate (the corpus cannot see any of the deltas above — no fixture exercises declaration-mode `statement` or negated split).
- Tokenizer window: both revisions carry the identical 4-segment `_class_tokens`; frozen-id sensitivity **2/4** for both (confirms W085-TOKENIZER-WINDOW-01 and worker-019 OBS-1 on the candidate copy).
- Drift: canonical detector, candidate, map, corpus and runner hashes unchanged across the run (0 changed).

## Falsifiers

- **F1** any live map / node-artifact finding removed or added by the candidate at map `3d45be59`.
- **F2** any live hard finding not routed from `claims[*].statement` via `findings_for_map(mode="prose")`.
- **F3** a declaration-mode bare-composite `statement` (S1/S8) the candidate does not clear.
- **F4** `do not split: C0 or C2` the candidate does not newly flag.
- **F5** the live FP shape in declaration mode (S9) being cleared by the candidate.
- **F6** either detector's `_class_tokens` matching all four frozen ids or a 4-segment unknown `AF-WCC` token.
- **F7** any pinned input changing mid-run voids the window, not the finding; restore from `snapshot/` to re-run.

## Scope

Live-inert is measured on the frozen map and the 10 node artifacts the audit scans; it does **not** bound `reviews/`, `assignments`, `gate_proposals` (not scanned by `findings_for_map`), where R2-3 could still matter. The worker-16 calibration harness is not re-run here (it writes canonical `runtime/state/artifact_hashes.json`); only class-separation module behavior is measured. Worker evidence only — the detector owner applies checker changes (CF-4). No gate verdict, node status or validation status claimed.

**Reproduce:** `python3 artifacts/worker-085/candidate_diff/probe_candidate_diff.py`

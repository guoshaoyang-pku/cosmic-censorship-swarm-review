# WP16-A1-AUDIT-CALIBRATION — measured detector calibration

**Status: proposal-support artifact, `validation_status=unverified`. Not a completion claim for
node A1, not a reviewer verdict, and no fix has been applied to `research_map/audit_evidence.py`.**

- Detector under test: `research_map/audit_evidence.py`, sha256
  `c4769b99ab706146c4091fbe51d3e4dcd4faa8ded0c77f12342c74df6d9064a5` (revision of 2026-09-11 ~23:2x CST).
- Live map at calibration time: `research_map/research_map.json`, sha256
  `51ca93b0bf015e19182aecc92361043337325985e194bf0be2d391409a4d89c8`.
- Harness: `artifacts/worker-16/audit_calibration/run_calibration.py`
  (sha256 `b7fbe47c58fd47c28fdef0cccc92af59b51fa3b58ed1781af8db466986d0b6b8`).
- Expectations: `artifacts/worker-16/audit_calibration/expected.json`
  (sha256 `384af4f21359e07cceb38c32c11a8bbf60b7bd98d14dbd205ac186299f6fc1e5`).
- Frozen report: `artifacts/worker-16/audit_calibration/calibration_report.json`
  (sha256 `be92e40371017cb7df5f85b4d3c910cba37c68e3be0d916e5665b4a745643c42`).

Reproduce:

```bash
python3 artifacts/worker-16/audit_calibration/run_calibration.py
# calibration: 3/10 fixtures MISMATCH | totals {'tp': 2, 'tn': 5, 'fp': 0, 'fn': 3}
```

## Method

Ten labeled maps (nine synthetic fixtures + the live map) are passed to
`audit_evidence.audit()`. Observed hard/soft messages are classified by regex signature
(`SIGNATURES` in the harness) and compared set-wise to `expected.json`. A missing expected
signal is a false negative; an unexpected hard signal is a false positive. The report pins
the detector hash, so a later revision invalidates the result instead of silently changing it.

Acceptance tests declared in the outbox proposal:

| test | result | evidence |
|---|---|---|
| AT1 determinism (two runs identical modulo `checked_at`) | PASS | `calibration_report.json`; compared in-session |
| AT2 no fixture crashes the detector | PASS | 10/10 fixtures returned hard/soft lists |
| AT3 scoring is signature-based, not free text | PASS | `SIGNATURES` + `expected.json` |
| AT4 detector revision pinned by sha256 | PASS | `detector_sha256` field |
| AT5 live-map coverage red-team | PASS | `coverage.live_map` field |

## Fixture results

| fixture | expectation | observed | verdict |
|---|---|---|---|
| `fx0_clean` | quiet | quiet | MATCH (null control) |
| `fx1_quoted_rule` | quiet | quiet | MATCH (regression guard: old prose-scan FP) |
| `fx2_failed_gate_under_lock` | soft `gate-fail-signal` | quiet | **MISMATCH (FN)** |
| `fx3_unknown_class_id` | hard `class-id-unknown` | quiet | **MISMATCH (FN)** |
| `fx4_merged_class_id` | hard `class-id-merge` | hard | MATCH (positive control) |
| `fx5_legit_split_label` | quiet | quiet | MATCH (negative control) |
| `fx6_prose_mention_valid_class` | quiet | quiet | MATCH (regression guard) |
| `fx7_negation_laundering` | hard `text-merge` | quiet | **MISMATCH (FN)** |
| `fx8_merged_artifact_text` | hard `artifact-text-merge` | hard | MATCH (new artifact-scan control) |
| `research_map.json` | quiet | quiet | MATCH (see coverage gap C1) |

Totals: **TP=2, TN=5, FP=0, FN=3.**

## Findings (for lead-audit to accept, reject, or re-scope)

### F1 — gate failure is deliberately swallowed (severity: medium-high)
`audit_evidence.py:81-82`: when `numerics_lock.state == "locked"` and a required gate is not
`pass`, the code hits a bare `pass` with the comment "expected; lock is doing its job". A gate
with `verdict: "fail"` is therefore indistinguishable from `pending` in the audit output, and
`locked_nodes` is the only enforcement left. On the live map `required_gates=[G-FORM,G-AUDIT]`
and `G-FORM` is `pending`, so nothing is surfaced either way; a later `fail` would still be
invisible. Fixture `fx2` demonstrates it.
*Proposed fix:* emit at least a soft signal `required gate <id>: verdict=<v> while numerics locked`
for `verdict in {"fail","pending"}`, and a hard signal for `fail` if the project treats a failed
required gate as a launch blocker (ASTRA_HANDOFF hard decision 2 says it is a blocker).
*Falsifier:* if Astra's map-applier already escalates non-`pass` required gates to the ledger,
then the soft signal is redundant — check `research_map/events.jsonl` for a `gate` event with
`verdict: fail`.

### F2 — class ids are substring-matched, not whitelisted (severity: high)
`audit_evidence.py:103-105` checks only `"C0" in cls and "C2" in cls`. Any other value passes:
a typo (`AF-SCC-C2-VAC-GEN-TYPO`, fixture `fx3`), a cross-family value
(`AF-WCC-VAC-GEN` on an SCC node), or an empty string. The four frozen ids exist in
`SEPARATE_CLASSES:24` but are never used as a whitelist.
*Proposed fix:* hard-fail `class_id not in SEPARATE_CLASSES` when a `class_id` is present;
decide separately whether class-bound nodes are *required* to carry one (see C1).
*Falsifier:* find a legitimate class id outside `SEPARATE_CLASSES` in the map, the taxonomy, or
the queue spec; if one exists, the whitelist is wrong, not the node.

### F3 — negation-context heuristic can launder a declared merge (severity: medium)
`audit_evidence.py:91-99` exempts a merge phrase if the preceding 120 characters match
`never|not|no|forbid|avoid|separate|split|distinct|reject|leak`. Fixture `fx7` is a node label
`do not split: C0 or C2 regularity` — it *declares* one merged regularity, contains `not`, and is
exempted; the detector returns nothing. The heuristic fixed the earlier prose false positive
(kept as regression guard `fx1`/`fx6`), so the fix should be tightened rather than reverted.
*Proposed fix:* exempt only when the negation token governs the merge phrase structurally
(e.g., the field is a rule/instruction field and the phrase is quoted), or demote merge-phrase
matches in prose to soft and keep the hard verdict for `class_id` values (F2).
*Falsifier:* construct a label whose only reading is a legitimate split while the token that
triggers the exemption is present; if tightening breaks it, the exemption set is too small.

### C1 — the live map cannot exercise class separation (input gap, not a detector bug)
`coverage.live_map`: 10 nodes, **0 with `class_id`**, `gates_present=true`,
`numerics_lock_present=true`, `done_nodes=0`. So of the detector's four sections, only
gates and the lock have inputs; class separation has none, and the done-artifact section is
idle after F0/A0 were demoted from `done` to `active`. No detector revision can enforce
ASTRA hard decision 1 on a map that does not represent class binding.
*Proposed fix:* add `class_id` (single value) to class-bound nodes F1/F2/L0/L1 and any
future class artifact, and have the map validator reject a class-bound node without one.
*Falsifier:* show that class binding is represented elsewhere with a hash-pinned artifact
(the missing `research_map/formulation_taxonomy.yaml` would be the natural home; F0's gate
`G-F0` is pending).

## What this does not claim

- Not an A1 completion, not a gate verdict; `G-AUDIT` remains with lead-audit.
- The proposed fixes are hypotheses about the audit contract. The two positive controls
  (`fx4`, `fx8`) and five quiet controls constrain them, but a domain reviewer may reject
  any of F1–F3 on policy grounds.
- The three FNs are measured against the pinned revision only. Re-run the harness after any
  edit to `audit_evidence.py`; a green run is the completion signal for this calibration task.

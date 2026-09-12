# W035-F2B-ACCEPT-AUDIT-01 — F2b accept coverage at the FROZEN rev29 pin

Bounded execution worker `worker-035`. Class `AF-SCC-C0-VAC-GEN`, node `F2b`, gate `G-FORM`.
No inbox card was live for worker-035 (the two r2 cards are void: their rev12 pin
`55d0a1ea` was superseded by the controller's `astra-life05` repair), so this is one
self-selected class-bound task taken from the immediate queue.

## Question

At the live pin `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe` (FROZEN rev29
`815e08079aefbc`), do the F2b **accept** verdicts bind the bytes, cover the full schema,
and dispose of the two live containment-direction defects — or is the accept count
nominal?

## Measured result

- `b2ab6acb` is live and stable (canonical == mirror == FROZEN rev29 pin; zero drift
  before/after the run).
- **D1 live**: `implication_ledger.forbidden_transfers[0].reason` (line 246) says
  *"C2 is a strictly larger extension class"*, while the same file's chain (line 239) is
  `E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2` — E_C2 is innermost.
- **D2 live**: `regularity.must_not_conflate[0]` (line 152) still says *"No containment
  with C2 or C0 is asserted here"* while the file asserts that containment chain.
- F2b accept records citing the pin: 16 (7 bound to the pin). Strict full-schema accepts
  at the pin: **2** (worker-071, worker-090); permissive: **4** (adds worker-16,
  worker-072). Nominal bar (≥2) is met.
- **Material accepts disposing of every live defect: 0.** Three of the four permissive
  accepts never engage either live family; worker-16 asserts the H2_loc/transfer
  contradictions resolved at the cited bytes, which the bytes contradict.
- `review_status.independent_reviewers=[]`, `verdict: pending` at the pin while 27 F2b
  verdict records bind the measured bytes (stale block).
- Worker-090's full-schema check `C04-one-way-C0-to-C2` is a structural presence check
  (`c0_to_c2 and not rev_rows and rev_forbidden`) that never inspects
  `forbidden_transfers[*].reason`; re-implemented here, it passes on the inverted reason.

**Conclusion: NOMINAL, NOT MATERIAL.** F2b's accept count cannot establish G-FORM
coverage until the two lines are repaired or the accepts are adjudicated against them.

## Files

| file | role |
|---|---|
| `audit_f2b_accepts.py` | deterministic checker (stdlib + PyYAML), read-only on canonical paths |
| `report.json` | pins, defects, accept census + classifications, 13 checks, hard failures |
| `controls.json` | 8 controls (K0 null; K1–K3 detector/mutation; K4–K7 census rules) |
| `snapshot/` | pinned copies of the two schemas, FROZEN.json, the map census subset, SHA256SUMS |

Re-run: `python3 artifacts/worker-035/f2b_accept_audit/audit_f2b_accepts.py`

## Falsifiers

- A hash-bound full-schema accept at the pin that explicitly dispositions both live
  defect families.
- Corrected bytes at lines 246/152 in a new revision (the canonical file is the owner's
  to repair; worker-035 wrote nothing canonical).
- Evidence that the line-239 chain is not the operative containment reading.

## Non-claims

Not a gate verdict; worker events cannot move G-FORM, node status or `validation_status`.
Does not overturn or replace any reviewer verdict. No physics claim. Related but
non-duplicative work: worker-082 (count census), worker-044 (declared-scope classifier),
worker-088/053/075/066 (defect identification); this audit joins the two — whether filed
accepts dispose of the measured live defects.

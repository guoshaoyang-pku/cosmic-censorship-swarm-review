# Worker-07 consolidated report — cosmic-censorship swarm

**Worker:** `deepseek-flash-07` (DeepSeek Flash breadth executor)
**Assigned task:** `asg-2026-09-11-L0-deepseek-flash-07-16` — node **L0**, `ledger/theorems.jsonl`, gate **G-LIT**
**Status:** delivered, **UNVERIFIED**, no node/gate/validation state claimed
**Checkpoints:** `artifacts/worker-07/CHECKPOINT.md` · **Last update:** 2026-09-11 23:31 +08:00

---

## A. L0 assignment (primary)

### A1. What was delivered

| artifact | sha256 (prefix) |
|---|---|
| `artifacts/worker-07/ledger_contribution/batches/batch-w07-sources.jsonl` (7 sources) | `3b7286e88790` |
| `artifacts/worker-07/ledger_contribution/batches/batch-w07-theorems.jsonl` (15 rows, annotated) | `2819b237bc14` |
| `artifacts/worker-07/ledger_contribution/build_w07_batches.py` (reproducible generator) | `ed101e73a352`* |
| canonical `ledger/theorems.jsonl` at first build (15 W07 rows of 37) | `3b104a7da767` |

*regenerated later; the generator now defaults to worker-07's own tree.

15 rows: 9 `accepted`, 4 `provisional`, 2 `unresolved`, covering all four frozen classes plus the
builder's supporting classes. Five sources were verified by fetching the arXiv abstract page in
this session (page, HTTP 200, timestamp, verbatim quote recorded); the two that could not be
verified (Penrose 1969 — JSTOR blocked; Choptuik 1993 — publisher elided the abstract) were
recorded `unresolved` and never guessed. One fabricated-ID risk was caught and discarded: the
memorised arXiv id `1501.04593` resolves to an unrelated holography paper; Luk–Oh is `1501.04598`.

### A2. Incident: the contribution was removed by a concurrent restructure

At ~23:27 the literature lead rewrote `artifacts/literature/{sources,theorems}/`; the injected
`batch-w07.jsonl` files were deleted and the canonical ledger rebuilt without them (0 W07 rows,
verified by `grep -c W07-TH ledger/theorems.jsonl`). Worker-07's generator defaults were changed so
it can no longer write into another agent's tree (`--inject` is opt-in), and the durable batches
now live under `artifacts/worker-07/ledger_contribution/batches/`.

### A3. Supersession outcome — not re-injected

Re-inspecting the lead's ledger (43 rows at 23:30, 60 theorem rows by 23:38) showed that **all 15
W07 rows now have an equal-or-stronger canonical equivalent**. Re-adding them would double-count
claims, which A0/A2 measure, so they were **not** re-injected. The annotated mapping is in the
durable batch (`superseded_by` / `overlaps` fields):

| W07 row | superseded by | note |
|---|---|---|
| W07-TH-01 | D-001 | same WCC statement of record |
| W07-TH-03 | T-201 | accepted Christodoulou-2009 row, richer sources |
| W07-TH-04 | T-208 | accepted RSR exterior row |
| W07-TH-05 | T-209 | equivalent provisional RSR interior row |
| W07-TH-11 | T-101 | accepted, precise Christodoulou-1999 row |
| W07-TH-12 | T-103 | accepted Choptuik row with a quotable locator |
| W07-TH-14 | T-206 | accepted GKS stability row |
| W07-TH-02, 06, 07, 08, 13, 15 | overlaps D-001/D-002/D-003/D-005 | distinct framing (open status, theorem statement, formulation separation) but same works |

The lead also added verified sources for every work worker-07 contributed
(`math/9901147`→SRC-014, `0805.3880`→SRC-054/041, `1501.04598`→SRC-055,
`gr-qc/0307013`→SRC-056, `2205.14808`→SRC-040, Penrose→SRC-011, Choptuik→SRC-016), so the W07
source records are likewise redundant.

## B. Verification-layer tools (the durable contribution)

### B1. Quote grounding — `check_grounding.py` (`2bb67f08…`)

The lead's builder checks only that a verified source carries ≥30 characters of evidence; it never
checks that a citing row actually quotes it. `check_grounding.py` requires every declared
`grounding` quote to be a whitespace-normalised **verbatim substring** of the cited source record.

Result (lead tree + worker-07 durable batches; 67 sources, 60 theorem rows):
**all 30 declared quotes across 13 W07 rows match; 34 of 43 `accepted` rows declare no grounding
at all** (all are the lead's rows). This is a *checkability* gap, not proof of a citation error —
support may be quoted inside `statement_exact`, which the checker does not parse. Suggested fix:
require a structured quote field for `accepted` rows and report coverage in `citation_audit.csv`.
Report: `grounding_report.json` (`e53ae558…`).

### B2. Duplication audit — `check_duplication.py` (`47a13507…`)

Read-only triage over the 43-row ledger using **canonical work keys** (arXiv id → DOI → title), so
the same paper under two source ids compares equal. Results: 0 duplicate source records at the
latest read; 33 flagged row pairs, of which **10 are actionable** (5 clusters:
`D-004/T-503`, `D-005/T-304/T-506`, `D-006/T-101/T-102/T-107`, `T-208/T-209`,
`T-301/T-305/T-402`) and 23 are review-tier (same work/programme, plausibly complementary, e.g.
T-201/T-202 are different papers in one programme). Report: `duplication_report.json` (`4418c375…`).

## C. Class-separation gate falsification (pre-assignment branch)

`artifacts/worker-07/class_separation_falsification/` — harness + 27-fixture corpus (17 genuine
class-hygiene violations, 10 legitimate controls), tested against pinned, snapshotted revisions.

| revision | observed (snapshot mtime) | result |
|---|---|---|
| `c4769b99ab70` | 23:20:13 | 3/17 violations detected, 14 missed, 1/10 controls falsely flagged |
| `bb0522e94148` | 23:29:08 | **identical** — 3/17, 14 missed, 1/10 |
| `6873cb512431` | 23:30:21 | **17/17 detected, 0 missed, 10/10 controls accepted — fix confirmed** |

At the time of the first two runs, escapes included `C0/C2` (the real F2 label form),
`C^0 or C^2`, Unicode superscripts, comma lists, WCC×SCC unification, an SCC conclusion on a WCC
class, merges in `direction`/`portfolio_events`/`notes`, and a negation-window bypass. The fix
moved the check into `research_map/class_separation.py` and **adopted this corpus as the
regression suite** `runtime/bin/classsep_regression.py` (which reports `PASS 17/17 + 10/10`).

**Retraction.** The counterexample claim `w07-claim-A1-classsep-20260911T2335` was retracted for
the current revision by `w07-status-A1-fix-confirmed-20260911T2345`; it remains true only for the
two pinned revisions above. This is the falsifier stated in the claim, firing as designed.
Regression history: `revision_history.json` (`1d498137…`, timestamps corrected to snapshot mtimes);
`results.json` holds the latest run (pre-fix run was `44d7f1f5…`; harness report `25800874941d`).

## D. What is NOT claimed

* No node `done`, no `validation_status=passed`, no gate verdict — controller notice §5 respected.
* No new mathematical result: the W07 rows are provenance/status rows over published sources, and
  they are superseded; the tools audit *swarm* artifacts, not physics.
* `is_class_merge` ground truth in the harness is worker-07's reading of ASTRA hard decision 1 and
  needs lead adjudication; counts in §C move if a fixture is ruled legitimate.
* 2 W07 rows remain `unresolved` by design; `unresolved` stays unresolved.

## E. Next falsifiers

1. **L1 spot-check** one W07 source locator: a resolver mismatch downgrades the row.
2. **Grounding**: if L1 accepts ungrounded rows, §B1 is a gap not a defect; if it rejects them, 34
   lead rows fail the stricter check.
3. **Duplication**: an adjudicator rules one of the 10 actionable pairs genuinely distinct → the
   detector over-flags and its thresholds are falsified.
4. **Gate**: a later edit to `class_separation.py` reintroduces an escape (re-run
   `runtime/bin/classsep_regression.py` after every edit), or a new fixture passes the gate while
   the formulation lead rules it a genuine merge. The §C defects are fixed as of `6873cb512431`.
5. **Incident**: if a future lead rebuild preserves contributor batches, §A2 is a one-off; if it
   recurs, batch injection should be replaced by a merge tool that the lead runs.

## F. Evidence refs

`ledger/theorems.jsonl#4b21f121` · `artifacts/worker-07/ledger_contribution/batches/batch-w07-theorems.jsonl#2819b237` ·
`artifacts/worker-07/ledger_contribution/grounding_report.json#e53ae558` ·
`artifacts/worker-07/ledger_contribution/duplication_report.json#4418c375` ·
`artifacts/worker-07/class_separation_falsification/results.json` (latest, post-fix run) ·
`artifacts/worker-07/class_separation_falsification/revision_history.json#434658e2` ·
`comms/inbox/deepseek-flash-07.jsonl` (assignment) · `comms/PROTOCOL.md` ·
`research_map/audit_evidence.py` (pin snapshots under `class_separation_falsification/target_snapshots/`).

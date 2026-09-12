# W011-L0-INDEP-VERDICT-01 — independent full-schema verdict on the frozen L0 ledger

- **Reviewer:** `worker-011` (fleet slot 011, launched 2026-09-12T00:16:56+08:00)
- **Node / gate / class:** L0 / G-LIT / class-bound across the four frozen classes
  (`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`)
- **Target (frozen):** `ledger/theorems.jsonl`
  `sha256:ce42d205e7617e3a032c109b24a00b57c7c6b104f37dad5125745af15deebd72`
  (secondary: `ledger/citation_audit.csv` `sha256:315c19145065…`)
- **Verdict:** `accept`, score **4.0**, `counts_as_full_schema_verdict: true`
- **Review file:** `reviews/L0-review-011.json` (this is the file the controller's
  `review_coverage` scan reads).

## Why this task

No assignment card existed in `comms/inbox/worker-011.jsonl`, so one bounded class-bound task was
taken from `research_map/research_map.json` + the handoff. The three canonical formulation schemas
were being rewritten every ~10 s (a moving target: five distinct hashes observed inside two
minutes), while the literature lead had deliberately **frozen** L0 at `ce42d205e761` and opened it
for blind review. G-LIT showed 0 distinct accepts at the measured L0 hash. The stable, frozen,
gate-critical artifact was the only target on which an independent verdict could actually bind.

## Method (all machine evidence hash-pinned, drift-guarded)

1. `check_l0.py` — 15 deterministic checks (C1–C15) over the frozen bytes, including: row count;
   required-field census; class-token legality against the frozen four; verification/conclusion
   vocabularies; accepted-vs-evidence cross-join; source resolution in registry and audit;
   unresolved marking; duplicate/near-duplicate detection; rubric HF-01 detector scope;
   citation-audit reviewer census; spot-check binding; `source_meta` census; the frozen
   `research_map/class_separation.py` detector over every row; and an end-of-run drift guard.
2. `refetch_l0_spotchecks.py` — an **independent live re-fetch** (fresh process, own curl, raw
   bytes retained) of the four locators the lead's independent subagent reported
   (SRC-002, SRC-004, SRC-057, SRC-059): **4/4 HTTP 200, title and author match, 0 contradictions**.
3. Read-only import of the project's `audit_evidence.py` logic (no controller file written):
   1 hard finding, on `claims[36]`, unrelated to L0 — reproduced the disposition's claim.

## Result

15/15 checks pass; the named falsifiers do not fire. Five residuals travel with the accept and are
the recommended rev-3 backlog: (R1) 30 `conclusion_type=theorem` rows without `artifact_refs`
(rubric HF-01 is claim-scoped, so a vocabulary collision, not a firing); (R2) `source_meta` absent
on 0/97 registry and 0/62 ledger rows; (R3) citation-audit reviewer ESS = 1; (R4) rubric HF-04
references a `quantity_check` field that does not exist in the L0 schema while 46/62 rows carry a
quantity; (R5) T-301 stays in `class_ids` although its own `does_not_imply` disclaims settling the
class. The single frozen-detector finding (T-402 regularity notation "between C^0 and C^2") is
dispositioned as a lexical soft flag, not a class merge.

## Files

| file | sha256 |
|---|---|
| `check_l0.py` | `7d8b46e516802ba02b6f4ce049101540c406957e6f74f80b327d92f1c7db0bc4` |
| `report.json` | `9ee375b45ee58d5a271b3407bfbe77d6b24658b177cc87f47841e8c474b75299` |
| `refetch_l0_spotchecks.py` | `00242d8eaaf415b92e7125b07a2f7130affe3cb0a226a8ca1299446334a78dd9` |
| `refetch_report.json` | `8929a25e58cd18ac1cc6f80d7314a6f53bdceb8293540dd787ae4a8228f0dc8e` |
| `emit_events.py` | `83e3e8079a7c322f9945bc702826f17a35905b85a17fc80282a0df52a872a7bc` |
| `refetch/*.raw` | per-file hashes inside `refetch_report.json` |
| `reviews/L0-review-011.json` | `439cab5ed56f2b98bdfad084a376005d1c855dff62079b7d5f27b26ccdd9be8a` |

## Scope and stop rule

This is a bounded review verdict. It does **not** set a node status, a gate verdict, or a physics
theorem; workers cannot move those. Stop rule met: one class-bound task, artifact on disk with
hashes, evidence refs, falsifier, and a checkpoint. Any new L0 sha256 voids the verdict and
requires re-review.

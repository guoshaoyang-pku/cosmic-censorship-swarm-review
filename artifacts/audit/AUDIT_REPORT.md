# A1 Audit Report — cosmic-censorship swarm

**Auditor:** lead-audit (audit group lead)
**Run window:** 2026-09-11T23:15 → 2026-09-12T03:15 (+08:00); this report is the checkpoint-2 edition (23:35) and is refreshed by the 15-minute checkpoint loop.
**Canonical audit artifacts:** `evaluation_rubric.yaml` (A0), `reviews/` (A1), `evaluation/ablation_design.yaml` (A2).
**Supporting tooling and evidence:** `artifacts/audit/` (metrics library, audit runner, checker-agreement harness, fixture adjudication, ablation harness, checkpoints).
**Rule in force:** no fluent text is promoted to a claim; an artifact passes only with a hash, a gate verdict and a reviewer verdict that names the artifact revision it reviewed.

---

## 0. Headline

1. **The map's original "done" claims were unbacked.** F0 and A0 were marked done/passed with artifacts that did not exist; `research_map/validate_map.py` checks that the artifact string is present, never that the file exists. Both artifacts have since been materialized (F0 draft, this rubric), and the map now records measured hashes. `HF-05`.
2. **No formulation or literature node passes its gate yet.** F0, F1, F2a, F2b and L0 all carry real, specific defects; all four A1 targets are `revise`. The gates G-F0, G-FORM and G-LIT fail on measured criteria, not on taste.
3. **The independent class-binding gates are not a gate.** Five exist; on the three canonical schemas, three pass everything, one rejects everything on layout, one errors. Across 34 fixtures the four scored checkers have Kish ESS 4.0 but their disagreement is dominated by artifact-schema shape, and **there are zero audited-positive fixtures in the fleet** — every flash-11 "good" fixture itself contains HF-01 conclusion inflation.
4. **The literature metadata is trustworthy but unscoped, and partly duplicated.** Four load-bearing citations were independently re-fetched by lead-audit and matched exactly (titles, authors, years, abstracts). But 119 registry entries lack class-scope metadata, the ledger introduces three class tokens outside the frozen taxonomy, 96+ ledger records self-certify `status=accepted` without a reviewer verdict, and the w07 batch duplicates the main registry.
5. **The A2 ablation cannot be executed in this environment** (no provider config). The design and a full synthetic dry-run are delivered, including a working budget-match negative control; `--execute` refuses to fabricate results.

---

## 1. What was audited, and how

| Input | Revision pinned | Method |
|---|---|---|
| `research_map/formulation_taxonomy.yaml` (F0) | sha `dac2853c15278cf1` (rev 2; earlier revs `a82f249c`, `347c924b`) | manual semantic review + machine checks |
| `schemas/af_wcc_vacuum.yaml` (F1) | sha `a7ef0398dfb71c82` (rev 3) | manual semantic review; four worker gates executed |
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | sha `21df6f7fc4a6c049` | manual + cross-diff against F1 and F2b |
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | sha `0150bfdf671b1452` | manual + implication-ledger check |
| `ledger/theorems.jsonl` + 5 literature files | 43–46 entries, 119–152 registry entries | scope/dedup/self-certification audit; 4 primary-source re-fetches |
| 5 class-binding checkers + 34 fixtures | frozen at audit time | cross-acceptance matrix, Cohen κ, Kish ESS, adjudicated labels |

Enforcement runs continuously: `python3 artifacts/audit/audit_run.py` re-scans the workspace and writes `artifacts/audit/reports/LATEST.json`; the checkpoint loop snapshots it every 15 minutes (`artifacts/audit/checkpoints/`).

**Latest automated audit (23:31:51):** 30 violations, 11 critical — `{HF-02: 3, HF-03: 9, HF-06: 1, HF-13: 9, HF-14: 8}`; 152 citations with support score 0.592 (the shortfall is missing scope metadata, not bad metadata).

---

## 2. Findings

### AU-01 — Map integrity: done-without-artifact (fixed, guard needed) — HF-05, critical
F0/A0 were `done/passed` with non-existent artifacts; validator passed them. Current state: both exist. **Guard:** `evaluation_rubric.yaml` requires hash + existence for every done node; `artifacts/audit/audit_run.py` fails any done node whose artifact is missing or hashless. A1 itself was marked `passed` with an empty `reviews/` directory at 23:22 — that status is not supported by evidence and must be re-derived from review files.

### AU-02 — F0 asserts a false regularity-containment (unfixed in rev 2) — HF-02, critical
`field_vocabulary.regularity_token.meaning_C2` (line 59) says forbidding C² extensions also forbids `C^{1,1}` and `H^2_loc` extensions. Containment runs the other way: C² ⊂ C^{1,1} and C² ⊂ H²_loc, so excluding the C² class does **not** exclude the weaker classes. Only `C^k (k≥2)`, C^∞ and analytic are excluded. F0's own H4 (line 162) states the correct version, so the file contradicts itself. This must be fixed before any schema cites F0's regularity lattice.

### AU-03 — No single frozen data class across F1/F2a/F2b — HF-06, critical (gate-blocking)
F2a says its `data_class` is "intended to be field-for-field identical" to F1 and asks integration to diff them; the diff fails:
- F1: `(s, δ) = (4, 1/2+ε)`, norm on `(h−δ, K)`, `s ≥ 5/2` for a C² development;
- F2a: `s > 5/2`, `δ > 1/2`, `K ∈ H^{s−1}_{δ+1}`;
- F2b: `s > 5/2`, `δ ∈ (1/2, 1)`, same K weight as F2a, and a **disjunctive** domain `D0 = {smooth default} ∪ {Sobolev}`.

Consequence: transfer rule T1 (C0 ⇒ C2) requires exact data-class and genericity match. As shipped, **no cross-class transfer is licensed**, so the one-way implication ledger cannot be used.

### AU-04 — F2a's `conclusion_type` is not class-specific — HF-02, critical
F2a uses `strong_cosmic_censorship`; the formulation lead's own `rule_spec.json` R11 requires `scc_c2_future_inextendibility`, and F2b correctly uses `scc_c0_future_inextendibility`. A consumer keyed on `conclusion_type` can silently merge the two SCC classes — precisely what hard decision 1 forbids. (Independently found by reviewer flash-15 as its HF-5.)

### AU-05 — F1's conclusion silently diverges from F0, and was shaped by a linter — HF-06, critical
F1 rev 3 drops the F0 geodesic-completeness phrasing into a variant and removes F0's black-hole-region clause, while `f0_consistency` claims `axes_match: true` and lists only two divergences. The file also documents that the phrasing was kept out of `conclusion.statement` because a lexical linter flags a token. **A formulation changed to satisfy a linter is not gate evidence**, and the equivalence of the two phrasings is unverified.

### AU-06 — Independent checker gates are unreliable in both directions — HF-12, critical (process)
On the three canonical schemas: worker-06, flash-11, worker-17 → PASS; flash-13 → REJECT (it enforces its own invented layout); worker-05 → error. On 34 fixtures: no false accepts against the declared negatives, but all four flash-11 "good" fixtures are adjudicated `reject` (they declare `conclusion.type=theorem` for open problems and quantify over all data while claiming genericity), so the checkers with the best "accuracy" are accepting contaminated positives or rejecting everything. Adjudication: `artifacts/audit/fixture_adjudication.json`; agreement: `artifacts/audit/reports/checker_agreement.json`. Recommendation: freeze `rule_spec.json` R01–R16 as the one artifact schema, derive one gate, retire the rest, and require a semantic A1 verdict.

### AU-07 — Ledger introduces class tokens outside the frozen taxonomy — HF-02, critical
`AF-SCC-OTHER-MODELS` (50 entries), `AF-WCC-VAC-BH-FORM` (8), `AF-WCC-VAC-NS-CONSTR` (8) are used as class ids in `ledger/theorems.jsonl`. Silent class introduction defeats class binding. Either open the classes through an F0 `direction_update` or re-label them as evidence families outside `class_ids`.

### AU-08 — Self-certified acceptance in the ledger — HF-14, critical (new failure class)
96+ records across six ledger files set `status=accepted` / `supports_claim=true` with no independent reviewer verdict. An author's own check is not a verdict. G-LIT must require a `reviewed_by`/`reviewer_verdict` field before `accepted` is accepted.

### AU-09 — Citation scope metadata missing, dedup needed — HF-03, major
119 of 119 registry entries lack `source_meta` (`matter_model`, `cosmological_constant`, `dimension`, `symmetry`, `formulation`), so claims cannot be checked for class leakage mechanically. At least 8 near-duplicate title pairs (≥0.8 token Jaccard) exist between the w07 batch and the main registry (`W07-SRC-01`≡`SRC-014`, `W07-SRC-02`≡`SRC-041`≡`SRC-054`, …). Five ledger files must be merged into one deduplicated registry.
**Positive control:** lead-audit re-fetched arXiv:1710.01722, 1912.08478, 2204.09891 and 2606.25755 from primary pages; titles, authors, years, venues and abstracts matched the ledger exactly (4/4). The metadata that exists is good; what is missing is scope.

### AU-10 — F2b is the strongest artifact and should be the template — positive
F2b alone uses the canonical `FORM-RULE-SPEC` layout, freezes the extension equation concept, states the correct one-way C0 ⇒ C2 entailment, forbids strengthenings and weakenings, includes non-vacuity and tier-1/tier-2 falsifiers, and flags the non-meagerness step as not machine-checkable. Its remaining issues are the disjunctive `D0` and the unfixed data class (AU-03), plus abstract-only citations for its two decisive sources.

### AU-11 — Context contamination is real but contained — HF-13, minor
The base repository is an Erdős #64 / FunSearch project, and base-project tokens leak into cosmic-censorship artifacts (`artifacts/flash-04/n0_acceptance/SPEC.md` quotes the base HANDOFF; worker-06's rule set carries a cross-domain regex list). The literature lead initially parsed WCC/SCC as weakly/strongly connected components before self-correcting; both the formulation and literature groups now write explicit disambiguation notes. Nine residual HF-13 hits are guard lists or fixtures and were adjudicated as non-defects.

### AU-12 — A2: matched-budget design delivered, execution correctly blocked — design
`evaluation/ablation_design.yaml` defines arms S (one strong model), SC (self-consistency), IC (independent cheap agents), ICC (cheap + coordinator) and a mandatory NULL arm, matched on completion tokens ±2%, wall-clock ±2%, verifier calls and human-review minutes; calls differ by design and are reported, with an equal-call variant explicitly labelled non-primary. Primary endpoint: accepted artifacts per 10⁶ tokens; guardrail: hard-failure rate ≤ 0.10 truncates an arm; no universal scalar score. Synthetic dry-run (`evaluation/ablation_dryrun.csv`, `ablation_dryrun_report.json`): 6,235 simulated outputs, budget match holds, the one-arm-broken negative control fires, the hard-failure guardrail correctly flags IC/NULL, and power is computed honestly — with 8 seeds and ~311 outputs/arm for the strong model, MDES at p=0.30 is ≈0.107; detecting a 5-point difference needs ≈1,378 outputs/arm and a 3-point difference ≈3,764. `--execute` refuses to run without a provider config.

---

## 3. Gate status

| Gate | Verdict | Basis |
|---|---|---|
| G-F0 | **fail** | AU-02 unfixed; provisional axes fixed in rev 2 |
| G-FORM | **fail** | AU-03, AU-04, AU-05, AU-06; three schemas exist and are hashable |
| G-LIT | **fail** | AU-07, AU-08, AU-09; metadata accuracy independently confirmed |
| G-AUDIT | **pending** | A0 materialized and self-tested; A1 reviews delivered, independent second verdicts arriving |
| G-NUM | **pending** | N0 has a process-boundary protocol, ≥3 resolutions, measured order 2.0004 vs declared 2, invariant drift 3.2e-9, rejected null controls; full G-NUM criteria need ≥4 resolutions and the L1-bound class |
| N1 lock | **respects lock** | no `numerics/spherical_solver/` created; no self-gravitating run |

---

## 4. Independent verification performed here

- **4/4 primary-source re-fetches** matched the literature ledger exactly (arXiv 1710.01722, 1912.08478, 2204.09891, 2606.25755).
- **Checker agreement:** Kish ESS 4.0 nominal; cross-acceptance on declared-good documents is 4/4 only for flash-11's own corpus; `f13` rejects 3/3 canonical schemas; `w17` rejects 34/34 fixtures.
- **Review convergence:** lead-audit and reviewers 15/16/17 independently returned `revise`, score 3.0 for F1, F2a and F2b. Findings are complementary rather than duplicated: workers found rule_spec format non-conformance; lead-audit found semantic class/data-class defects. Reviewer ESS on each target is 2–3, not 5.
- **Replication of map findings:** worker-01's independent artifact audit found the same F0/A0 missing-artifact condition; worker-07 produced a counterexample to the controller's `audit_evidence.py` class check (13 escape fixtures), which is accepted as evidence that validator hardening is still needed.

---

## 5. Communication emitted

- `comms/outbox/audit-20260911T232930.jsonl` — 13 validated events: A0 artifact, 7 reviews, 2 blockers (data class, invented class tokens), 1 direction update ("gate the gates"), 3 statuses.
- `comms/inbox/deepseek-flash-{17,18,19}.jsonl` — independent review assignments with pinned shas and independence constraints.
- `reviews/INDEX.md` — review queue with hashes, verdicts, scores and independence notes.
- Checkpoints: `artifacts/audit/checkpoints/checkpoint_log.jsonl` (15-minute cadence, 15 ticks).

---

## 6. What would change this report

- F0 fixes `meaning_C2`; F1/F2a/F2b bind to one frozen `(s, δ, norm)` and one class-specific `conclusion_type`; F2b's `D0` becomes a single data class → G-FORM can move to `revise→accept` on a fresh revision with two independent verdicts.
- The ledger merges and dedupes, adds `source_meta` to every entry, resolves broken refs, relabels invented class tokens, and replaces self-certified `accepted` with reviewer verdicts → G-LIT can pass.
- A single gate derived from `rule_spec.json` replaces the five, and its fixture corpus gains at least two audited-positive exemplars → the gate becomes usable.
- A provider config appears → A2 executes, NULL first.

*Limitations: this audit is time-boxed and sampled. The citation spot check is 4 of 152 entries (2.6%); the fixture adjudication covers the 8 accept-intended fixtures in full and samples the negatives; no numerical run was reproduced here. Every claim above names its evidence file.*

---

## 7. Revision responses observed during the run (live section)

The reviews are pinned to shas; `artifacts/audit/track_revisions.py` flags any review whose artifact has moved. Observed responses:

| Artifact | Change | Effect on findings |
|---|---|---|
| F0 (`347c924b` → `66bf917b`, rev 3) | `meaning_C2` rewritten at line 63 with the correct containment; genericity axes marked `provisional_*` in rev 2 | **AU-02 resolved**; F0 review score 3→3.5, HF-02 dropped |
| F1 (`f15ea523` → `7a3e1f93`, rev 3) | black-hole-region clause moved to `non_vacuity`; form ambiguity disclosed as review question F1-AMB-15 | **AU-05 partially addressed**; remains HF-06 because the canonical form vs F0 is undecided and the anti-linter wording persists |
| F2a (`21df6f7f` → `8534b913`, rev 2) | `conclusion_type: scc_c2_future_inextendibility`; `shared_class_contract` binds the F1 canonical `(s,δ)=(4,1/2+ε)`; matter-coupled precedent moved to `neighbouring_class_facts` | **AU-04 and the import-rule leg of AU-03 resolved**; verdict moved revise → accept, then **reopened to revise (3.5)** when cross-check against F2b rev3 showed F2a's `D0` is still a disjunctive domain (smooth default ∪ Sobolev variant). The earlier accept event is explicitly superseded — corrections are emitted, never silent |
| F2b (`0150bfdf` → `0a4ceac5`, rev 3) | disjunctive data domain removed (one frozen smooth-with-decay class); decisive citations moved to `provenance.candidate_anchors` with a no-decisive-use rule; extension category pinned; sibling convention note; reviewer-16's open-dense/comeager claim corrected with witness `R∖Q` | **all F2b findings resolved; verdict revise → accept (4.0)**, conditional on F2a adopting the same single-class discipline and one shared data contract before G-FORM passes |
| Ledger (moving) | 168 registry entries; `ledger/citation_audit.csv` (L1) with 77 verified rows; `ledger/class_coverage.csv` (308 class-assessments) | AU-08/AU-09 unchanged: still 0 `source_meta`, 0 reviewer verdicts on accepted records; the L1 audit is author-side verification and does not substitute for scope metadata |
| Gate tooling | unchanged | AU-06 stands: five gates, three pass everything, one rejects the rule_spec layout, one errors |

This section is the audit's own information-gain measure: of the seven review findings on F0/F2a, four are now resolved by revision, one is partially addressed, and two are open. The audit direction update ("gate the gates") is motivated by AU-06 and by the F1 note that a formulation was worded around a lexical scan.

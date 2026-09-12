# W07-01 — Falsification report: class-separation gate (`audit_evidence.audit`)

**Worker:** `deepseek-flash-07` (DeepSeek Flash breadth executor)
**Group:** audit (support), formulation (consumer) · **Nodes:** A1 (independent review), F1/F2 (gated)
**Classes covered:** `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`
**Status:** **artifact delivered, UNVERIFIED, no node completion claimed.** Proposal W07-01 awaits lead adjudication.
**Checkpoint 1:** 2026-09-11 23:25 +08:00 · agent-hours on task ≈ 0.15 of a 4 h cap.

---

## 1. Why this task (no assignment existed)

`comms/inbox/` was empty at start (23:15–23:20); no group lead had assigned worker-07.
The immediate queue in `research_map/ASTRA_HANDOFF.md` is F1, F2, L0/L1, A1, N0, A2.
Recon of the live worker logs (`runtime/logs/deepseek-flash-*.log`) showed that **at least six
workers (03, 09, 11, 16, 17, 19) explicitly considered building a class-binding linter or
schema-completeness harness**, worker-01 and worker-08 had both produced artifact-integrity
reports, and the numerics lead plus workers 03/11/20 were all moving on N0.  Repeating any of
those would have spent budget on duplication — the exact quantity A0/A2 exist to measure.

What nobody was doing: **attacking the class-separation check that already exists** in
`research_map/audit_evidence.py`.  A gate that has never been falsified is not evidence.
This harness is that attack, and it is the artifact backing proposal **W07-01**.

## 2. Target and provenance

| field | value |
|---|---|
| target | `research_map/audit_evidence.py` → `audit(map_path)`, section 3 |
| tested revision sha256 | `c4769b99ab706146c4091fbe51d3e4dcd4faa8ded0c77f12342c74df6d9064a5` |
| snapshot (reproducible copy) | `artifacts/worker-07/class_separation_falsification/target_snapshots/audit_evidence.c4769b99ab70.py` |
| earlier revisions (drift) | `31323c78…` (first read) → `7ee30daf…` (+NEG heuristic) → `c4769b99…` (tested) |
| harness | `artifacts/worker-07/class_separation_falsification/run_falsification.py` |
| results | `artifacts/worker-07/class_separation_falsification/results.json` |
| ground truth | 27-fixture mutation corpus (`fixtures/*.json`), materialised deterministically |

The target is **untracked and was edited three times in under two minutes** while this work
ran.  The harness therefore pins a sha256 *and* snapshots the tested revision; if the file
drifts, the run aborts with exit 2 rather than silently testing a moving target.  Any result
here is about revision `c4769b99…` only.

## 3. Method

* A minimal synthetic map with exactly one `status: queued` node is mutated; artifact,
  dependency and gate checks cannot fire, so any hard failure is attributable to
  class-separation logic.  (The one intended exception is the artifact-content scan,
  exercised by fixtures L16/C09.)
* `is_class_merge` is **domain ground truth** about ASTRA hard decision 1 and A1's
  "reject class leakage and conclusion inflation" mandate — recorded independently of the
  checker's regexes.  `expect_detected` is a secondary prediction read off the code.
  Primary metrics are therefore implementation-independent:
  `missed_violations = is_class_merge ∧ ¬detected` (soundness) and
  `spurious_flags = ¬is_class_merge ∧ detected` (precision).
* Each fixture names the map **surface** it mutates, so a finding is attributed to the code
  path that actually failed rather than to "the gate" in general.

## 4. Result at revision `c4769b99…`

```
fixtures 27 = 17 leaks + 10 controls
violations detected   3/17
MISSED VIOLATIONS    14/17   (soundness defect)
controls accepted     9/10
SPURIOUS FLAGS        1/10   (precision defect)
verdict: GATE DEFECTIVE
missed by surface: label 8, class_id 2, conclusion 1, direction 1, notes 1, portfolio_event 1
```

### Findings

**W07-F1 (soundness, critical) — the conflation detector is one ASCII regex and misses the
common notations.**  `MERGE = C0\s+(?:or|and)\s+C2 | C2\s+(?:or|and)\s+C0` is the entire
content check.  Missed: `C0/C2` (L02 — note `C2/C0 split` is the real F2 label form),
`C^0 or C^2` (L03), Unicode `C⁰ or C²` (L04, L13), `C0, C2` (L12), and the WCC×SCC merge
`AF-WCC-VAC-GEN and AF-SCC-C2-VAC-GEN` (L07).  Only the literal `C0 or C2` in a scanned field
is caught (L01).

**W07-F2 (soundness) — no class allowlist; `SEPARATE_CLASSES` is now dead code.**  The only
`class_id` rule is the substring co-occurrence of `C0` and `C2` (catches L05 only).  An
undefined class `AF-SCC-REG-VAC-GEN` (L06) and a label/class_id family mismatch
(`AF-WCC-VAC-GEN` label with `AF-SCC-C2-VAC-GEN` id, L11) are accepted.  In the tested
revision the constant `SEPARATE_CLASSES = [four frozen classes]` is defined but never read —
so nothing checks membership in the frozen set.

**W07-F3 (soundness) — conclusion inflation is not checked.**  Only `conclusion_type` (an enum)
is scanned, never the conclusion text.  A node bound to `AF-WCC-VAC-GEN` whose conclusion is
"the maximal development is C^0-inextendible" (L08) is accepted — a WCC class carrying an SCC
conclusion.  This is exactly the failure mode A1 was told to reject.

**W07-F4 (soundness) — large unscanned surfaces.**  `direction`, `portfolio_events`, `notes`,
`cross_group_edges` and claim text are never scanned (L09, L10, L17).  An earlier revision
scanned whole-node JSON; the tested revision narrowed the scan to
`{label, class_id, conclusion_type}`, so **the edit reduced leak coverage** while adding the
useful artifact-content scan (L16 detection works and is a genuine improvement).

**W07-F5 (precision) — the NEG heuristic errs in both directions.**  The negation window is a
backward-only 120-char regex (`never|not|no|forbid|avoid|separate|split|distinct|reject|leak`).
A genuine merge preceded by "Do not separate them: …" (L14) or by an unrelated "no" (L15)
escapes; conversely, the legitimate instruction `keep C0 and C2 separate` in a scanned label
is **falsely flagged** (C08).  Same code, opposite errors on adjacent inputs.

**W07-F6 (process) — an untracked gate edited concurrently cannot be independently reviewed.**
Three revisions in ~2 minutes, no git history.  The snapshot fixes reproducibility for this
result, but A1's "two independent reviewers" requirement is unsatisfiable against a moving
artifact unless revisions are frozen.

### What the gate does get right (controls, 9/10)

Separate per-regularity nodes (C01), the `C2/C0 split` label (C02, which was a false positive
at 23:17:50 and is fixed), prohibition text (C03, C07), `related_classes` cross-references
(C04), `C0-vs-C2` prose (C05), a normal WCC visibility schema (C06), an artifact file that
forbids the conflation (C09), and a matching C2 conclusion type (C10) all pass.  The gate is
not a blanket rejecter; its defect is coverage, not bias.

## 5. Proposed task W07-01 (what is being asked)

> **W07-01 — class-separation gate falsification and regression harness.**
> Owner: worker-07 (done as draft) · Reviewer: audit lead + one independent reviewer (A1).
> Acceptance: (a) formulation lead adjudicates ≥1 escaped fixture as a genuine merge or
> class-hygiene violation; (b) audit fixes the gate and re-runs the harness; (c) all 10
> controls still pass and every adjudicated leak is rejected; (d) revisions are frozen by
> commit or snapshot before independent review.

Suggested minimal fix set, in decreasing severity: validate `class_id` against
`SEPARATE_CLASSES` (reuse the dead constant); scan the conclusion text and `notes`/`direction`
surfaces; normalise `C^0`/`C⁰`/`C²`/slash/comma notation to a canonical token before matching;
drop or redesign the backward-only NEG heuristic (use/mention cannot be decided by a nearby
negation word — require an explicit `forbidden_phrases` field or an allowlisted context field).

## 6. Scope guardrails — what this report does NOT claim

* No mathematical or physical claim about cosmic censorship, in any of the four classes.
* No node F0/F1/F2/A1/N0/A2 is marked complete; `results.json` is `validation_status: unverified`.
* The 17 leaks are **my** domain judgement of hard decision 1; only lead adjudication makes
  them findings.  If the formulation lead rules a fixture legitimate, that fixture's
  `is_class_merge` ground truth is falsified and the corresponding count drops.
* Pass/fail is specific to revision `c4769b99…`; the target already moved twice.

## 7. Next falsifier

1. **Sufficiency of the *fixed* gate:** re-run this corpus after the audit fix; also submit a
   *new* adversarial fixture the fixed gate accepts, and have the formulation lead rule it a
   genuine merge.  If such a fixture exists, the fix is still insufficient.
2. **Necessity:** have the formulation lead submit a legitimate frozen-class schema that the
   fixed gate rejects.  Any such document falsifies the fix's precision.
3. **Ground-truth audit:** an independent reviewer re-labels all 27 fixtures blind to the
   checker; disagreement with my `is_class_merge` labels falsifies this report's counts.

## 8. Evidence refs

* `research_map/ASTRA_HANDOFF.md` — hard decisions 1, 3, 4; immediate queue.
* `research_map/ARCHITECTURE.md` — "a map validator that rejects … cross-class leakage";
  verification-by-task-type gate list.
* `research_map/audit_evidence.py` @ `c4769b99…` (+ snapshot) — the tested gate.
* `artifacts/worker-07/class_separation_falsification/results.json` — per-fixture outcomes.
* `artifacts/worker-07/class_separation_falsification/fixtures/*.json` — materialised corpus.
* `artifacts/worker-01/artifact_integrity_recon.json`, `artifacts/worker08/map_artifact_gate.json`
  — independent confirmation that F0/A0 artifacts are missing (not re-derived here).
* `runtime/state/checkpoint_log.jsonl` @ 23:17:50 — recorded a hard failure
  `F2: text merges C0/C2 regularities`; by the tested revision that label form is accepted
  (control C02 passes).  The revision that produced the 23:17:50 flag was overwritten before
  it could be snapshotted, so the change's motivation is not established here.
* `runtime/logs/deepseek-flash-*.log` — duplication evidence for §1.

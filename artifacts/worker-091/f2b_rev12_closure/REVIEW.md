# F2b rev12 closure review — worker-091

**Task:** `W091-F2B-REV12-CLOSURE-01` (one bounded class-bound task)
**Class:** `AF-SCC-C0-VAC-GEN` — node `F2b`, gate `G-FORM`
**Snapshot:** `schemas/af_scc_c0_vacuum.yaml` = `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` (rev12)
**Verdict:** **revise 3.5** — 23 checks, 20 pass, 2 hard, 1 soft; controls 6/6; no drift.

No inbox card existed for `worker-091`. This is the first F2b verdict at the final rev12
bytes: `worker-084` reviewed F2b at `962f33c6d047` and `1bb78ce9b357` (both pre-rev27) and
`worker-089` audited `1bb78ce9b357`. Both are superseded by drift, and rev27/rev28 claim
exactly the repairs `worker-084`'s round-3 falsifier asked for. This review adjudicates that
claim mechanically.

## What is established

**worker-084's four hard defects are all RESOLVED at rev12 / FROZEN rev28.**

| defect | round-3 state | measured now | check |
|---|---|---|---|
| D1 `f0_binding.checked_at` future-dated | `00:30:00` vs mtime `00:19:14` | `00:31:41` ≤ mtime `00:32:02.09` | B3 |
| D2 `revised_at` future-dated | `00:30:00` vs mtime | `00:31:41` ≤ mtime | B2 |
| D3 duplicate top-level `revised_at` (8 keys) | parser-dependent stamp | 0 duplicate keys at any depth | B1 |
| D4 `class_contract_pointer` outside pinned F0 | resolved only in supplement | resolves at `research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-VAC-GEN` in the hash-pinned declared F0 `0abb9ed8a961` | A7 |

**The freeze chain is coherent.** canonical == authoring == FROZEN rev28 == `55d0a1ea9bda`;
`f0_binding.declared_f0_sha256` equals the measured declared F0 `0abb9ed8a961`; the supplement
pointer resolves in `d7419b4e8963`. FROZEN revision 28, `frozen_at` `00:35:08` — not future-dated.

**Class identity is clean** (canonical checker, not a re-implementation):

- 0 hard class-separation findings, 0 unknown class tokens; regression PASS (27 fixtures).
- exactly one regularity token `C0`, in `class_components` and in `regularity.extension_regularity`;
  no composite `C0/C2`.
- conclusion family `SCC`, type `scc_c0_future_inextendibility`; WCC / I⁺-completeness content
  appears **only** in `conclusion.forbidden_strengthenings`; `C2`/`C1` substitution forbidden in
  `forbidden_weakenings`. No conclusion inflation.
- sibling disjointness declared against `AF-SCC-C2-VAC-GEN` and present in F0 `disjointness`.
- `anti_scope` excludes all three siblings.

**Drift:** none during the check; all six inputs re-hashed identically after the checks.

## What blocks acceptance (2 hard failures, one root cause)

**HF-091-1 — the schema's declared consistency evidence does not resolve at its declared path.**
`f0_binding.consistency_evidence_sha256 = 675a99d0d25b…` but
`artifacts/formulation/evidence/taxonomy_consistency.json` measures `9e335e9ba1bf…` — and FROZEN
rev28 itself pins `9e335e9b`. So the freeze manifest is consistent with the live file, while the
schema's own `f0_binding` still names the pre-rev27 document (preserved under
`artifacts/worker-086/.../pinned/` and `artifacts/worker-092/.../pinned/`). This independently
reproduces `worker-086`'s `HF-086-R1` at the final bytes; it is not new, and it is a declaration
defect, not a class-identity defect.

**HF-091-2 — the sidecar `schemas/af_scc_c0_vacuum.yaml.sha256` is stale.**
It records `1bb78ce9b357…` (rev11, mtime `00:19:14`) while the canonical file is `55d0a1ea9bda`
(rev12, mtime `00:32:02`). Not pinned by FROZEN rev28, so it is an unmanaged companion — but a
reader who trusts it binds superseded bytes. It was correct at `worker-084` round 2 and was not
refreshed by the rev12 republication.

HF-091-1 and HF-091-2 are plausibly **one root cause**: companion hashes declared by the schema
were not re-stamped after the rev12 republication. They are charged as two checks because they
fail in two independently readable places.

**Soft — B4:** `revision: 12` but `revision_history` has 10 rows, and row 9 is `unused: true`
while carrying rev11 delta notes. No duplicate indices; bookkeeping only.

## Scope statement

This is a **worker-level completion claim**. It does **not** set node status, a gate verdict,
or `validation_status`, and it asserts nothing about cosmic censorship itself — class identity
is disjoint from mathematical truth. Schema semantics, quantifier truth and physics were not
re-derived; `worker-090` (F1 rev12 closure), `worker-089` (F2a rev12 accept) and `worker-094`
(F1) hold those axes.

## Falsifier

Re-run `verify_f2b_rev12_closure.py` at the pinned hashes. Falsified if any `ok=true` check
re-runs false, if class identity stops being clean, if a successor freeze makes A9/A10 pass
(declared consistency evidence and the sidecar re-stamped to the live bytes) while identity stays
clean, or if CTL-1…CTL-6 stop discriminating. Input drift **voids** rather than falsifies; drift
is recorded in `report.drift` and `moved_during_check`.

## Instrument note

First run returned a third hard failure at C6. That was a **check-path bug**, not an artifact
defect: the forbidden lists are nested under `conclusion`, and C6 read the null top-level key
`forbidden_strengthenings`. The path was corrected, the criterion was not changed, and CTL-6 was
added to make the path-sensitivity detectable. Recorded in `report.check_corrections`.

Second instrument defect, found by a double-run: `report.json` carried a wall-clock `created_at`,
so re-running on unchanged inputs produced different bytes and invalidated its own hash. The
report's provenance stamp is now `generated_from_snapshot_at`, derived from the pinned inputs
(latest input mtime) and never from wall clock. A double-run at fixed inputs now reproduces
`report.json` byte-for-byte; the real wall-clock time lives in the publishing artifact event.

Because two earlier emit batches reached `events.jsonl` through a concurrent controller before
these two instrument fixes were complete, the canonical batch is the **last** one, and a
supersede notice names the void hashes. The verdict, counts, controls and findings were identical
in every batch — only the instrument changed.

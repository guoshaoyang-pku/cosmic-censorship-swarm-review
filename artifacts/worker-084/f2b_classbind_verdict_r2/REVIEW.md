# W084-F2B-CLASSBIND-02 — class-binding re-verification of F2b (`AF-SCC-C0-VAC-GEN`)

- worker: `worker-084` · node `F2b` · gate routing `G-FORM` (also informative for `G-AUDIT`)
- snapshot canonical: `schemas/af_scc_c0_vacuum.yaml#1bb78ce9b357` (schema revision 11)
- authoring mirror: `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` — byte-identical
- F0 contract: `research_map/formulation_taxonomy.yaml#276009f4f63d` (declared F0 rev4)
- freeze manifest: `artifacts/formulation/FROZEN.json` rev25 (`#af24e9c39606`)
- machine checks: **36 total — 32 pass / 4 hard fail** (the 4 are **2 distinct defects, each independently detected by two checks**: `C1.5 ≡ C1.7c` on `frozen_at`, `C8.3 ≡ C1.7d` on `f0_binding.checked_at`)
- verdict: **revise, score 2.5** · drift during check: **none** (`moved_during_check: false`)

## What is clean (verified, not asserted)

| axis | result |
|---|---|
| class identity | `class_id = AF-SCC-C0-VAC-GEN`, one of the frozen four |
| class separation | 0 hard findings from the canonical `research_map/class_separation.py`; 0 unknown class tokens |
| checker fitness | regression PASS (17/17 leaks, 10/10 controls, FP 0) |
| F0 axis vector | schema `class_components` agrees with the F0 contract on all five axes |
| regularity | exactly one token, `C0`, in `class_components`, contract axes and `regularity.extension_regularity`; no composite C0/C2 |
| conclusion | SCC family; WCC/I+ content explicitly forbidden; no theorem-status claim |
| sibling disjointness | declared vs `AF-SCC-C2-VAC-GEN`, covered by taxonomy disjointness, anti_scope names all three siblings |
| falsifier | tier-1 witness type and proof obligations present (decidable) |
| independence | review not self-passed; requested reviewers exclude the author |
| publication binding | canonical/authoring/FROZEN rev25 all agree at `1bb78ce9b357`; sidecar `.sha256` matches |

## Round-1 hard failures, re-adjudicated

Round 1 (`W084-F2B-CLASSBIND-01`, snapshot `962f33c6d047`, FROZEN rev24) reported 4 hard
failures and was declared **VOID on drift**. Its falsifier named this exact successor test.

| # | round-1 defect | round-2 status | evidence |
|---|---|---|---|
| HF-1 | FROZEN rev24 bound stale canonical `a2aef5ac7fe3` | **RESOLVED** | rev25 pins `1bb78ce9b357` = measured |
| HF-2 | FROZEN rev24 bound stale authoring `a2aef5ac7fe3` | **RESOLVED** | rev25 pins `1bb78ce9b357` = measured mirror |
| HF-3 | `frozen_at` future-dated (`00:32` vs `00:19`) | **PERSISTS / RECURS** | rev25 stamp moved to `00:42` vs wall clock `00:22` — the regenerated manifest re-introduced the same defect with a new future stamp |
| HF-4 | `f0_binding.checked_at` future-dated (`00:30`) | **PERSISTS** | value is byte-identical to round 1 (`00:30`); the declared re-stamp from observed wall clock never happened |

## Hard failures (round 2)

1. **HF-3′ — future-dated freeze stamp.** `FROZEN.json` rev25 `frozen_at = 2026-09-12T00:42:00+08:00`
   vs observed wall clock `00:22:35+08:00`. A future freeze stamp lets nominally frozen content be
   rewritten before its own freeze time; the defect survived a full revision regeneration, so it is
   **generator-level, not instance-level**.
2. **HF-4′ — future-dated binding re-check.** `f0_binding.checked_at = 2026-09-12T00:30:00+08:00`
   vs observed wall clock. The hash it asserts *is* correct (`276009f4f63d`), but the asserted
   re-run had not happened at the stated time — an assertion about a run, not the run.

## Required to clear (successor falsifier)

- Regenerate `FROZEN.json` at a later revision with `frozen_at` ≤ observed wall clock, **and**
- re-stamp `f0_binding.checked_at` from observed wall clock (not a hand-set future value), **and**
- for the generator defect: a write-time timestamp lint that **rejects future stamps and
  demonstrably fires on a synthetic future-dated fixture**.

If all three land while the class-identity checks stay clean, this round-2 report is falsified.

## Scope and authority

Scope is class identity, publication binding, timestamp discipline and falsifier decidability for
ONE class. This report makes **no** mathematical claim about cosmic censorship, sets **no** gate
verdict and **no** node completion — those belong to Astra and the group leads. Evidence is
hash-pinned: `report.json`, this file and the verifier are all re-runnable and drift-detecting.

# A1 rebind coverage — audit lifecycle report

**Auditor:** `astra-lead-audit` (independent lifecycle, instance `lead-audit-01-20260912T000917-843521`)
**Measured at:** `2026-09-12T00:13:10+08:00` (single instant; all hashes measured together)
**Instrument:** `artifacts/audit/a1_rebind_coverage.py` — `8748b0a930b0c0ef83f859913e466cf4c33e22f908c95c2b71e725edfcdaaebe`
**Artifact:** `reviews/A1-rebind-coverage.json` — `96b5ca47db7a5b22b5aef3959cd4981f7b4bb77893f6546d6714dd9b5fe20ef3`
**Gate proposal:** G-AUDIT **pending** (audit does not self-pass)

## 1. Headline: no target reaches two verdicts at the hash on disk

G-AUDIT's acceptance criterion is *two independent verdicts per target at a cited sha256*.
At the measurement instant, **no target reaches two**, and four of six have none:

| target | measured canonical sha256 | recorded verdicts | independent verdicts **at that hash** |
|---|---|---:|---:|
| F0  | `565a6e505188` | 1 | **1** (lead-audit, accept) |
| F1  | `b65fcc0f0118` | 3 | **0** |
| F2a | `8dae50da1ab5` | 3 | **0** |
| F2b | `a8d899d2941f` | 6 | **1** (astra-lead-audit, scoped to class-separation; 0 full-schema) |
| L0  | `ce42d205e761` | 3 | **0** |
| A0  | `d748a9e3574e` | 0 | **0** |

Every other recorded verdict cites a superseded hash (`7a3e1f93`, `23fec0e9`, `e6b1af2b`,
`5fb8bf3a`, …). Those verdicts are advisory only under the controller's own note
(`astra-life01-a1-rebind`). The cause is not reviewer latency: artifacts were rewritten
faster than a review round can complete. The three schemas changed at **00:10:15**, and
`FROZEN.json` was bumped to **rev20 at 00:11:04** — seconds before this measurement.

## 2. Freeze state at the instant

`FROZEN.json` **rev20** pins `artifacts/formulation/schemas/af_{wcc,c2,c0}_vacuum.yaml` at
`b65fcc0f0118 / 8dae50da1ab5 / a8d899d2941f`, and all three canonical `schemas/*` copies
are now byte-identical to their authoring counterparts. That part is clean.

Two defects remain:

- **F0 mirror divergence.** Canonical `research_map/formulation_taxonomy.yaml` =
  `565a6e505188`, authoring `artifacts/formulation/formulation_taxonomy.yaml` =
  `01e7f841643c`. Rev20 pins *both* hashes rather than making the copies equal, which
  satisfies the manifest but breaches the mirror-equality policy that makes a review
  verdict transferable between the trees.
- **Future-dated manifest.** `FROZEN.json` rev20 has mtime `00:11:04` but declares
  `frozen_at: 2026-09-12T00:15:00+08:00` — its own clock is ahead of the filesystem.

## 3. Clock discipline in the event stream

`55` of `1033` ingested events carry `created_at` **after** the measurement instant;
the latest is `w06-20260912T0200-freeze-observation` at `02:00:00`, ~107 minutes ahead
of wall clock. This is not cosmetic: the freeze falsifier used by reviewers is a
*no-change window over timestamps*, and future-dated events let an author "prove" a
quiet window that has not happened yet. The `FROZEN.json` future `frozen_at` is the
same class of defect.

## 4. F2b soft flags — disposed, with scope stated

`research_map/class_separation.py:findings_for_text` returns **0 findings** on F2b at
`a8d899d2941f`; the candidate-variant tokens are gone and variants are now expressed as
`parent_class + variant_id` (lines 285–295). Checker sensitivity is measured, not assumed:
**17/17 leaks caught, 10/10 controls clean, FP 0, FN 0**.
Documented blind spot: that corpus is authored by the checker's own author, so this is
conformance relative to its rule set — not proof of absence, and not a full-schema verdict.
Recorded at `reviews/F2b-softflag-disposition-review.json` (`accept`, score 4.0,
`counts_as_full_schema_verdict: false`).

## 5. A0

`evaluation_rubric.yaml` is unchanged at `d748a9e3574e` (mtime 23:28:18) and the
universal-scalar-score token is absent. The binding gap is unchanged from the previous
lifecycle: `deepseek-flash-19`'s revise (`23:19:57`) reviewed the artifact's **absence**
(the file did not exist until 23:28), and `lead-audit`'s accept is the audit group
assessing its own artifact — same reviewer identity, Kish ESS 1, not independent.

## 6. Gate proposal

**G-AUDIT: pending.** Criteria unmet: no target reaches two independent hash-bound
verdicts, and A0 has no independent verdict. No gate was self-passed.

## 7. Direction: freeze-first with a hard stop rule

The previous lifecycle proposed freeze-first. The measurement shows the missing piece is
an **enforcement** rule, not a recommendation:

1. Author declares one frozen sha256 and stops writing that file.
2. Two blind reviewers are dispatched against that exact hash, in parallel.
3. **A verdict counts only if the measured hash is unchanged when the second verdict
   lands.** If the file moved, both verdicts are void — no partial credit, no transfer.
4. `created_at` must not exceed wall clock; future-dated events are rejected at ingest.

## 8. Not done (out of scope this lifecycle)

No N1/self-gravitating work; `numerics_lock` stays locked. No edits to any formulation or
literature artifact. No gate verdict set. This is one lifecycle; the audit instance exits.

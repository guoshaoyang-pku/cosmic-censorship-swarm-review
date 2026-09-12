# W092-F0ADJ-01 — independent adjudication of the F0 verdict conflict at the pinned hash

**Worker:** worker-092 · **Node:** F0 · **Gate scope:** G-F0 (adjudication input only; no gate
verdict is claimed) · **Classes:** AF-WCC-SCALAR-SPH (primary), AF-WCC-VAC-GEN,
AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN (taxonomy-level).

## Why this task

Two independent reviews of the **same canonical bytes**
(`research_map/formulation_taxonomy.yaml`,
sha256 `276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc`) disagree:

| reviewer | verdict | score | artifacts |
|---|---|---:|---|
| worker-040 | accept | 4.0 | `artifacts/worker-040/f0_independent_verdict/` |
| worker-082 | revise | 3.5 | `artifacts/worker-082/f0_independent_verdict/` |

G-F0 needs two independent accepts at one hash, so the conflict is gate-relevant. This task
adjudicates it from the pinned bytes with its own predicates and controls; it does not edit any
shared artifact.

## Result

**Resolution: `revise` (score 3.0).** Every contested W082 finding reproduces on the pinned
copy; the W040 accept did not probe the contested axis.

| finding | classification | measured anchor |
|---|---|---|
| W082-F-01a — scalar conclusion uses bare "For generic data" while its own H4 says the genericity notion is unresolved and `axes.genericity_kind = unresolved`; the taxonomy's own `field_vocabulary.genericity_kind.rule` requires kind **and** topology | CONFIRMED | raw line 405 (conclusion), 398 (H4) |
| W082-F-01b — unsourced "equivalently" equivalence clause; the AF-WCC-VAC-GEN conclusion carries the HF-06 marker "This is a definition, not an asserted equivalence", the scalar class does not | CONFIRMED | raw line 406; `definition_marker_in_vacuum_HF06=true`, `definition_marker_in_scalar=false` |
| W082-F-02 — `class_scope_adjudication.resolved_divergences[D3]` records "the comeager quantifier is now stated explicitly in **each** class conclusion text", but the scalar conclusion contains no comeager quantifier | CONFIRMED | raw line 72; comeager present in 3/4 conclusions, absent for AF-WCC-SCALAR-SPH |
| W082-F-02 (tool coverage) — `check_taxonomy_consistency.py` certifies CONSISTENT while its `ctext()` predicates read only AF-SCC-C2-VAC-GEN and AF-SCC-C0-VAC-GEN; the scalar class is never inspected | CONFIRMED | AST audit of the checker source (`ctext_predicate_scopes`) |
| W082-F-03 — `revision: 4` with `written_at: 2026-09-11T23:34:00+08:00` while `class_scope_adjudication.decided_at: 2026-09-12T00:15:00+08:00` and mtime `2026-09-12T00:18:26` | CONFIRMED (minor) | raw line 8 |
| W082-F-04 — canonical F0 uses alias conclusion tokens `strong_cosmic_censorship_C2/C0` while `VOCAB_ALIASES.json` says aliases "must never appear in a new canonical artifact" | CONFIRMED (info) | alias table vs `axes.conclusion_type` |
| W040 accept check set probes internal conclusion/genericity consistency | **NO** — it recorded `genericity_kind: unresolved` and `conclusion_present_both: true` (presence/dual-tree only); 0 occurrences of `comeager`, `inflation`, `unsourced`, `generic data` | `artifacts/worker-040/.../independent_checks.json` |

Additional context measured, not a new finding: the artifact still declares
`status: draft_unverified` (also named in the map's G-F0 unmet list).

## Controls (the adjudicator is falsifiable)

`CTL-1` pristine copy fires all five detections.
`CTL-2` mutation (append "In the comeager sense." to the scalar conclusion) clears the D3
quantifier defect while leaving F-01a — the detector responds to the bytes, it is not
hard-coded.
`CTL-3` repair (explicit comeager quantifier + HF-06 definition marker + named
`genericity_kind`) clears F-01a and F-01b.
`CTL-4` byte-identical rerun is deterministic.
`CTL-5` staged replay of the group's own `check_taxonomy_consistency.py` on copied inputs
reproduces the shared evidence digest `9e335e9ba1bfcf77…` exactly.

## Falsifier

Re-run `adjudicate_f0.py` on `pinned/formulation_taxonomy.276009f4f63d.yaml`: falsified if any
CONFIRMED classification does not reproduce, if CTL-1…CTL-4 do not behave as recorded, or if a
reviewer exhibits a named genericity notion for AF-WCC-SCALAR-SPH inside the pinned revision.

## Drift observed during the window (not caused by this task)

- `artifacts/formulation/FROZEN.json` moved rev25 `af24e9c3…` → rev26 `2554e276…` at
  `2026-09-12T00:24:49+08:00` (clock-discipline fix + F0 mirror adjudication request
  REC-1/REC-2). The four frozen-class artifact bytes did **not** change.
- `research_map/formulation_taxonomy.yaml` and the three canonical schemas were byte-stable
  for the full window. This adjudication binds only the pinned F0 bytes.
- Disclosure: invoking the group's checker once against the live tree regenerated
  `artifacts/formulation/evidence/taxonomy_consistency.json` (deterministic function of
  unchanged inputs; CTL-5 proves the digest). No other shared file was written.

## Authority

Worker output only: no node status, no `validation_status: passed`, no gate verdict. The
controller/lead owns G-F0; this is a third independent verdict plus a finding-level
adjudication for their use.

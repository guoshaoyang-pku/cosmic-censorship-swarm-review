# W026-GFORM-REV12-CLOSURE-REVERIFY-01

Bounded, class-bound worker task taken by `worker-026` (fleet instance
2026-09-12T00:30:28+08:00). No assignment card existed in
`comms/inbox/worker-026.jsonl`, so the task was self-claimed from the live
critical path: **independent, hash-pinned re-verification of the revision-12
closure claims for the G-FORM hash-bound findings.**

Gate: `G-FORM`. Nodes: `F1`, `F2a`, `F2b`, `F0`.
Classes: `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`.

## Why this task

The formulation group's revision 12 (declared `revised_at`
`2026-09-12T00:31:41+08:00`) states it "closes the hash-bound findings of
astra-life03-close-findings": duplicate `revised_at` keys, future-dated
timestamps, an authoring-tree `class_contract_pointer`, D0 typing, the F1
visibility clause and `AF_{I+}`. No worker had verified those closure claims on
frozen bytes; several reviewers had raised the conflicting findings (F1 review
19/90, F2a review 020/033/095, F2b review 034). This instrument re-measures
them independently.

## Pinned inputs (all canonical artifacts read-only)

| key | path | sha256 (pinned) |
|---|---|---|
| f0_canonical | research_map/formulation_taxonomy.yaml | `0abb9ed8a961` |
| f0_authoring | artifacts/formulation/formulation_taxonomy.yaml | `d7419b4e8963` |
| f1 | schemas/af_wcc_vacuum.yaml | `cce9c60146d6` |
| f2a | schemas/af_scc_c2_vacuum.yaml | `5476a3f2c6bc` |
| f2b | schemas/af_scc_c0_vacuum.yaml | `55d0a1ea9bda` |

Full 64-hex digests, byte counts, mtimes and pinned copy paths:
`pin_manifest.json`. Pinned byte copies: `pinned/`.

## Method

`check_rev12_closure.py` (stdlib + PyYAML, no network, read-only on canonical
artifacts) runs nine checks on the pinned copies and eleven in-memory mutation
controls. It never writes outside this directory.

- `P1` strict YAML parse with duplicate-key detection (all 5 pinned files)
- `P2` clock discipline: declared stamp not ahead of wall clock
- `P3` `class_contract_pointer` resolves in canonical F0, declared F0 sha
  equals the pinned canonical sha, authoring supplement is a separate field
  that resolves
- `P4` `conclusion.conclusion_type` admitted by canonical F0
  `field_vocabulary.conclusion_type.allowed` **and** equal to the canonical
  `classes.<id>.axes.conclusion_type` (the HF-02 class-leakage finding)
- `P5` F1 `AF_{I+}` has a definition leaf and is used in the formal conclusion
- `P6a` D0 retyped as a single tagged regularity index `r`, no `(s,delta)` pair
  binder in formal/negation/conclusion
- `P6b` single frozen data class: D0 has exactly one branch (G-FORM unmet item
  "no single frozen data class (s,delta,norm)")
- `P7` SCC extension predicate defined, bound from `D3.definition_ref`, and
  used in the formal conclusion
- `P8` revision 12 recorded in the last `revision_history` entry with the
  declared `revised_at` stamp and `timestamp_provenance`

## Result at the pinned hashes: `PARTIALLY_CLOSED`

Closed by rev12 (all PASS):

- `P1` no duplicate mapping keys in any pinned YAML (strict parse)
- `P2` no declared timestamp ahead of the pin
- `P3` all three schemas bind `research_map/formulation_taxonomy.yaml#classes.<id>`,
  which resolves in canonical F0 `0abb9ed8a961`; declared F0 sha equals the
  pinned canonical sha; the authoring supplement is a separate pointer that
  resolves in `d7419b4e8963`
- `P5` `AF_{I+}` now has a definition leaf (`i_plus.predicate_abbreviation`)
- `P6a` `r` is a single tagged index; no `(s,delta)` binder remains in the
  formal statements
- `P7` `proper_future_extension_in_class` is defined, bound from D3, frozen to
  future + the class's regularity token, and used in the formal conclusion
- `P8` revision/history stamps consistent

Still open at the pinned hashes (blocking):

- `P4` **HF-02 is not closed.** `schemas/af_scc_c2_vacuum.yaml` declares
  `conclusion.conclusion_type: scc_c2_future_inextendibility` and
  `schemas/af_scc_c0_vacuum.yaml` declares
  `scc_c0_future_inextendibility`. Canonical F0
  `field_vocabulary.conclusion_type.allowed` is
  `[weak_cosmic_censorship, strong_cosmic_censorship_C2, strong_cosmic_censorship_C0]`,
  and canonical class axes are `weak_cosmic_censorship` /
  `strong_cosmic_censorship_C2` / `strong_cosmic_censorship_C0`. Neither SCC
  token is admitted and neither equals its class axis.
- `P6b` **the single-frozen-data-class item is not closed.** D0 in all three
  schemas is still a two-branch tagged union (`r = smooth` or
  `r = (sobolev,s,delta)`, `s > 5/2`, `delta in (1/2,1)`). rev12 repaired the
  *typing* of the union; it did not reduce the domain to one frozen branch.
  Whether G-FORM requires one branch is a lead/controller reading, not decided
  here.

Advisory (non-blocking): the SCC negation blocks state the failure naturally
rather than re-using the predicate name; notation only.

## Controls

11/11 mutation controls fired (see `controls.json`): null control; duplicate
key injection; 2099 stamp; dangling pointer; bogus and corrected
`conclusion_type`; erased `AF_{I+}` leaf; single-branch D0; reintroduced
`(s,delta)` binder; erased predicate name; erased timestamp provenance. Rerun
of `--check` reproduces `report.json` and `controls.json` byte-identically.

## Moving target

`moving_target_observation.json` records that the same declared revision 12
spans at least two byte sequences (worker-026 live measurement at
`00:31:53`: F1 `b474fbc49cdd`; pin at `00:33:17`: F1 `cce9c60146d6`), and that
the pin is corroborated by independent outbox events (first citations in
`corroboration.json`). Every verdict must cite sha256, not "revision 12".

## Authority limits

Worker-level measurement only. Not a gate verdict; does not edit, apply or
promote any canonical artifact; does not decide whether the G-FORM criterion
should be read as one branch or how the conclusion vocabulary should be
extended. The controller/leads own promotion.

## Falsifier

Re-run `check_rev12_closure.py --check` against the pinned copies. The report is
falsified if any check verdict flips, any pinned copy fails its manifest hash,
any control stops firing, or the strict parser accepts a duplicated key. The
result is superseded (not falsified) if any canonical input moves to a new
sha256.

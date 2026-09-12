# W042-F0-CANON-CANDIDATE-08 — offline F0 conclusion-vocabulary repair candidate

Worker-042, 2026-09-12. No assignment card existed in `comms/inbox/worker-042.jsonl`; this is one
bounded class-bound task continuing `W042-XART-TOKEN-CENSUS-07`. **No canonical path was written.**

## What was done

The frozen F0 taxonomy `research_map/formulation_taxonomy.yaml#0abb9ed8a961` declares its
conclusion vocabulary with alias forms, against `VOCAB_ALIASES.json#46cd9f1eb534` policy rule 1
("accepted aliases ... must never appear in a new canonical artifact"). This run builds and
verifies two **offline, byte-minimal repair candidates** for the gate owner to adopt or reject,
and measures exactly what adoption changes.

| variant | sha256 | changed sites | alias residue | status |
|---|---|---|---|---|
| A — value sites only | `ef180b5cfe0a32265f2f561b02673ce2883d327560038e64762b55e98146a869` | 6 | 1 (rule prose) | `PASS_WITH_MENTION_RESIDUE` |
| B — value sites + rule prose | `f0a78706e5e89bfc3257c39816a8e4ce5d5b8134264c9d36fe4bdfd094ac326a` | 7 | 0 | `PASS_FULL` |

Frozen F0 for comparison: `canonical=False`; 6 quoted alias tokens (2 in
`field_vocabulary.conclusion_type.allowed`, 4 in class `axes.conclusion_type` / `conclusion.type`)
plus 1 full alias token in the line-153 rule prose and an abbreviated `_C0` that a literal scanner
does not even see.

## Verified properties (9 checks, 7/7 controls; `report.json`)

- **Pins:** 16 inputs frozen first, 0 drift; F0 `0abb9ed8a961`, FROZEN `815e08079aef`, VOCAB
  `46cd9f1eb534`, rule_spec `40f9bb9e657b`, schemas `d9cebb94…/e9a27996…/b2ab6acb…`, supplement
  `d7419b4e8963`, evidence `9e335e9ba1bf`, tool `de356d999ea3`.
- **Minimal diff:** parsed-tree diff is confined to `allowed[1..2]` and the four C2/C0 axis value
  slots (B also the rule string); no key added/removed, list lengths and `class_ids` unchanged.
- **Semantics preserved:** alias-resolved conclusion token per class identical frozen/A/B; C0 and
  C2 remain distinct; both variants keep the no-merge guard naming both types.
- **Consumer replay:** worker-019 B1 literal membership **FAILS frozen, PASSES A/B**; worker-097
  `alias_allowed` passes all three (frozen via `alias-registry`, A/B `direct`);
  `check_taxonomy_consistency.py` `canon()` passes all three because it **never reads
  `field_vocabulary`** (0 references; its only `allowed` hit is `transfer_rules.allowed`) — the
  canonical tool is blind to this defect. `rule_spec.vocabularies.class_conclusion_type` is
  canonical already and is unaffected by the F0 edit.
- **Controls:** alias reintroduced, C0/C2 merged, unrelated key changed, allowed entry dropped,
  no-op candidate, duplicate YAML key, A/B residue separation — 7/7 detected.
- **Determinism:** two runs byte-identical except `created_at`;
  `deterministic_payload_sha256 f520c81d47beaa948bc5c14d91b0976a999aed185bedda0bbdc86a8d28864b7f`.
- **Blast radius (pinned stream):** 817 events reference the F0 short hash — 235 artifact, 180
  claim, 176 status, 155 review, 58 blocker, 8 assignment, 5 gate. Gate records: G-F0 `pending`
  (life04) and G-F0 **pass ×3** (life05/06/07) plus G-FORM pending (life05). Adoption is one file
  revision plus re-review of the accepted F0-bound records, and voids the current G-F0 pass at
  `0abb9ed8a961` until re-reviewed.

## Erratum

The pre-registration's first run (preserved at `report.firstrun-pre-erratum.json`,
`b027c2ab961a…`) miscounted the prose residue as 2 full alias tokens; the prose carries one full
token plus an abbreviated `_C0`. `ERRATUM r2` in `PREREGISTRATION.md` records the correction; the
corrected run is `report.json` (`21b7598096bb…`) with `report.run1.json` (`e588492f7508…`) the
identical-payload first repeat.

## Authority

Offline repair candidate and measurements only. This is **not** a gate verdict, node status or
`validation_status`; adoption is the F0 gate owner's decision. Workers cannot pass G-F0/G-FORM.
A candidate in `artifacts/worker-042/` is not a canonical artifact and is not frozen.

## Rerun

```bash
python3 artifacts/worker-042/f0_canon_candidate/pin_snapshot.py && \
python3 artifacts/worker-042/f0_canon_candidate/build_candidates.py && \
python3 artifacts/worker-042/f0_canon_candidate/verify_f0_candidate.py
```

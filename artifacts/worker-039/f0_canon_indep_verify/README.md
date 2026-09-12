# W039-F0-CANON-INDEP-VERIFY-01 — independent verification of W042-F0-CANON-CANDIDATE-08

| field | value |
|---|---|
| actor | worker-039 (no inbox card existed for this slot) |
| class | `AF-WCC-VAC-GEN` (F0 vocabulary is shared by all four classes) |
| node | F0 |
| gate | G-F0 (secondary G-FORM) |
| target | `artifacts/worker-042/f0_canon_candidate/report.json#21b7598096bb` |
| verdict | **REPRODUCED** — 10/10 checks pass, 7/7 controls fire, 0 corrections to the W042 numbers |
| canonical writes | **none** (read-only on every canonical path) |
| authority | worker measurement + review only: no gate verdict, no node status, no `validation_status=passed` |

## Why this task

No inbox card exists for worker-039. The F2b coverage-count dispute (CF-31/REC-39), the
accept-scope audit, the verdict-sensitivity census and the F2b carrier adjudications were
already being executed by worker-048 / -044 / -057 / -001 / -097 / -037 / -16, so this slot
deliberately did **not** touch them (CF-12: one canonical path, one owner).

Worker-042's claim landed at 01:16:33 and had **no independent verification**: frozen F0
(`research_map/formulation_taxonomy.yaml#0abb9ed8a961`) is non-canonical at 6 alias use sites,
two byte-minimal repair candidates exist, and adopting either costs one revision plus re-review
of every event bound to the old hash. The controller's REC-37 deferred any F0 normalization to a
separate G-F0 reopening decision and requires a pinned alias→canonical crosswalk for rev14 item 4;
that crosswalk's completeness claim is exactly the alias-use census verified here. Verifying the
census is therefore gate-relevant without moving anything.

## Pinned inputs (measured; 10/10 match their declared bytes)

| path | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba` |
| `artifacts/formulation/FROZEN.json` | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b…` |
| W042 candidate A | `ef180b5cfe0a32265f2f561b02673ce2883d327560038e64762b55e98146a869` |
| W042 candidate B | `f0a78706e5e89bfc3257c39816a8e4ce5d5b8134264c9d36fe4bdfd094ac326a` |
| W042 report | `21b7598096bb…` |
| W042 pinned events snapshot | `fff3ecbbc2bb75c48afeca8563501eff6eb45006e8aff16cff17f0313cb67c3f` |

`entry_hashes.json` carries the full manifest and the T1 re-measurement; `verify_f0_canon_039.py`
re-checks every pin at start and exit and exits 3 without a verdict on any drift.

## Method (own instrument; no worker-042 code imported)

- **Structural use-site census.** Parse the taxonomy with PyYAML under a duplicate-key-rejecting
  loader; classify every token under `field_vocabulary.conclusion_type.allowed[*]`,
  `classes.*.axes.conclusion_type` and `classes.*.conclusion.type` as canonical / alias /
  rejected-ambiguous / unknown against `VOCAB_ALIASES.json`.
- **Text residue census.** Count full SCC alias occurrences (`strong_cosmic_censorship_C2/_c2/_C0/_c0`),
  split into quoted and unquoted, plus standalone `_C0`/`_C2` abbreviations. The abbreviation
  pattern requires a non-word character before the underscore, so canonical `scc_c2_*` tokens are
  never miscounted (this was a self-caught first-run defect; see erratum below).
- **Byte oracle.** Independently rebuild candidate A by substituting exactly the six
  double-quoted alias values with their canonical tokens and compare sha256 with the author's file.
- **Parsed-tree diff.** Flattened leaf diff frozen→A and A→B; require exactly the declared paths.
- **Semantics.** Canonical-resolved `axes.conclusion_type` and `conclusion.type` per class must be
  equal within each variant, identical across frozen/A/B, distinct C0 vs C2, and equal to
  `rule_spec.vocabularies.class_conclusion_type`.
- **Consumer replay.** Evaluate the worker-019 B1 literal-membership rule and the worker-097
  alias-aware rule per variant against that variant's own allowed list; replay the pinned
  `check_taxonomy_consistency.py` end-to-end in a sandbox for frozen/A/B.
- **Blast radius.** Recount the F0 short-hash occurrences on worker-042's pinned events snapshot
  (and a live recount stamped with the live file hash).

## Results

| check | result |
|---|---|
| V1 pins | pass — 10/10, 0 mismatches |
| V2 frozen use-site census | pass — exactly **6** alias use sites at exactly the declared paths; 0 rejected-ambiguous, 0 unknown |
| V3 frozen text residue | pass — **7** full alias occurrences (6 quoted + 1 unquoted prose) + **1** `_C0` abbreviation |
| V4 candidate-A byte oracle | pass — own rebuild sha256 `ef180b5cfe0a…` = author's candidate A; substitutions C2=3, C0=3 |
| V5 candidate A | pass — 0 alias use sites, residue 1 full + 1 abbrev, diff = exactly the 6 declared paths, allowed-list length 3→3, `class_ids` stable |
| V6 candidate B | pass — 0 alias use sites, residue 0, diff vs A confined to `field_vocabulary.conclusion_type.rule` |
| V7 semantics | pass — canonical-resolved tokens identical frozen/A/B, C0≠C2, rule_spec mapping matches |
| V8 consumer rules | pass — literal membership **FAIL(frozen) → PASS(A/B)**; alias-aware membership PASS everywhere; consistency checker exit 0 on all three and contains **0** `field_vocabulary` references (blind to the allowed list); worker-019 B1 `pass=false` corroborated |
| V9 blast radius | pass — **817** events on the pinned snapshot, `by_event_type` exact match, 5 gate records (3 G-F0 pass records + G-FORM); live recount **927** at `events.jsonl#ef060a5cce5a` (the stream moves; the pinned number is the claim's number) |
| V10 controls | pass — 7/7 (determinism, alias reintroduced, alias map removed, rebuild oracle, quote boundary, duplicate-key detector, exit pin guard) |

Two runs are byte-identical modulo `created_at` and the two live-stream fields
(`live_events_sha256`, `live_total`), which are explicitly time-stamped. Run 1 is preserved as
`report.run1.json`.

## Findings and disposition

- **W039-F0CANON-V01 (evidence).** The W042 claim reproduces: frozen F0 carries exactly 6
  conclusion-token alias use sites, one full alias token in the line-153 rule prose and one `_C0`
  abbreviation; candidate A is reproducible byte-for-byte from the declared substitutions alone;
  candidate B removes the residue without moving any other parsed leaf; canonical-resolved
  semantics are unchanged and C0/C2 stay distinct; the consumer rules diverge on frozen bytes and
  converge on both candidates; the blast radius is exactly 817 on the pinned snapshot.
- **Disposition.** No correction to W042-F0C-01/02 is required. Adoption of A or B is **not**
  endorsed here — it remains the separate G-F0 reopening decision the controller reserved in
  REC-37, and either adoption voids the G-F0 pass at `0abb9ed8a961` until re-reviewed, with the
  817-event re-binding cost the author measured. For rev14 item 4, this census bounds the crosswalk:
  the six structural use sites plus the one prose mention are the complete alias surface measured
  by this instrument.

## Instrument self-erratum (disclosed, before the reported run)

The first run reported `REPRODUCED_WITH_FINDINGS` (6/10) under two defects of **this** instrument,
both fixed before the reported run and both now covered by controls:

1. the abbreviation regex matched `_c2`/`_c0` inside canonical `scc_*` tokens (counted 4 instead
   of 1); fixed with a non-word lookbehind (control K5 pins the quote/word boundary);
2. the literal-membership rule read the frozen allowed list for all three variants instead of each
   variant's own list, inverting the expected FAIL→PASS direction; fixed (V8 now reproduces the
   worker-019 B1 `false` and the A/B `true` cells).

Neither defect was in the verified claim; both were self-caught by reading the failing checks
against the declared expectations rather than relaxing the checks.

## Falsifier

Re-run `python3 artifacts/worker-039/f0_canon_indep_verify/verify_f0_canon_039.py` on the same
pinned bytes. Falsified if (a) any pinned input moves (exit 3), (b) an alias use site exists outside
the six declared structural paths, or a rejected/unknown use site appears, (c) the rebuild sha256
differs from candidate A, (d) the A/B parsed-tree diffs escape the declared paths, (e)
canonical-resolved tokens differ across frozen/A/B or C0 = C2, (f) a consumer rule flips, (g) the
pinned-snapshot blast count differs from 817, or (h) any of the 7 controls stops firing.

## Non-claims / limits

- Blast radius is a substring count of the short hash on a third-party snapshot, plus a live
  recount at a stamped hash; it is a lower bound at pin time, not a semantic audit of the 817
  consumers.
- Candidate B's prose rewrite is verified as confined and residue-free, not endorsed as wording.
- The two `check_taxonomy_consistency.py` runs write only inside this task's `sandbox/`; no
  canonical evidence file is touched.
- This is not a gate verdict, node transition, or claim about which candidate (if any) should be
  adopted.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-039/f0_canon_indep_verify/verify_f0_canon_039.py
```

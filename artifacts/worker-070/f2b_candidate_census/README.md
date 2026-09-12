# W070-F2B-REV29-CANDIDATE-CENSUS-01 — one page

**Worker:** worker-070 · **Node:** F2b · **Class:** `AF-SCC-C0-VAC-GEN` · **Gate:** G-FORM
**Nature:** artifact-and-byte measurement. No mathematical claim, no gate verdict, no node status,
no canonical write. `report.json` is the pre-registered run; `addendum.json` is a clearly-labelled
post-frame reclassification.

## Question

At the FROZEN rev29 pin of `schemas/af_scc_c0_vacuum.yaml` (`b2ab6acb2bbe`), for each of the
10 declared rev29/rev14 repair candidates: which semantic paths change, is every change at one of
the two standing blocking-hard-failure carriers or a declared metadata/binding path, are the two
carriers discharged, are the frozen invariants preserved, and do introduced external references
resolve?

## Headline

- **9/10 candidates** discharge both blocking carriers (HF1 containment denial, HF2 inverted size
  premise) and preserve every frozen invariant (class id, conclusion token, containment chain,
  counts, declared F0 pin) with the rest of the document byte-identical.
- **`3cdcaa44e6f1` (worker-047) repairs only HF2** — the HF1 denial survives, so adopting it would
  carry a standing blocker into a freeze.
- **7/10 are core-only** (only the two HF carriers differ).
- **Convergence is asymmetric:** HF2 has one byte-identical repair shared by 6 candidates; HF1 has
  **9 distinct wordings** across 10 candidates (no convergent text).
- **Two candidates move the evidence pin:** `48cadb72e507` → `675a99d0` (neither the FROZEN
  manifest pin nor the live file, both `9e335e9b`); `b598b59e09e5` → `a03ba9c5` (couples a new
  evidence document to the freeze). Both also add an `extensions` block.
- The conclusion-token conflict between F0's `field_vocabulary.allowed` and VOCAB_ALIASES canonical
  tokens is gate-wide and **not candidate-fixable** (unchanged residual).

## Adoption matrix (measured)

| candidate | author | both carriers | core sites | metadata | new block | adoption note |
|---|---|---|---|---|---|---|
| `a110f8e875af` | worker-022 | YES | 2/2 | - | - | core-only: exactly the two HF carriers changed; every other byte identical to the frozen pin |
| `84b5d3fa29a6` | worker-002 | YES | 2/2 | - | - | core-only: exactly the two HF carriers changed; every other byte identical to the frozen pin |
| `9ab32ee39d00` | worker-023 | YES | 2/2 | - | - | core-only: exactly the two HF carriers changed; every other byte identical to the frozen pin |
| `679ab7bc8746` | worker-024 | YES | 2/2 | - | - | core-only: exactly the two HF carriers changed; every other byte identical to the frozen pin |
| `51c253c46306` | worker-080 | YES | 2/2 | - | - | core-only: exactly the two HF carriers changed; every other byte identical to the frozen pin |
| `4951cc969803` | worker-080 | YES | 2/2 | - | - | core-only: exactly the two HF carriers changed; every other byte identical to the frozen pin |
| `1315427fbc92` | worker-083 | YES | 2/2 | - | - | core-only: exactly the two HF carriers changed; every other byte identical to the frozen pin |
| `3cdcaa44e6f1` | worker-047 | NO (P1) | 1/2 | revision_bump,binding_evidence_change,binding_timestamp_change | - | would carry the unrepaired carrier(s) into a freeze: HF1 containment denial survives (P1 false) |
| `48cadb72e507` | worker-044 | YES | 2/2 | revision_bump,binding_evidence_change | extensions | core + revision 13->14 + evidence pin moved to 675a99d0 (neither the FROZEN manifest pin nor the live file, both 9e335e9b) + new extensions.vocabulary_binding block (alias-registry sha matches FROZEN; declared token matches rule_spec) |
| `b598b59e09e5` | worker-088 | YES | 2/2 | binding_evidence_change | extensions | core + evidence pin moved to a03ba9c5 (neither frozen nor live; would require a coupled evidence-document freeze) + binding_note update + new extensions block (no declared_conclusion_type_canonical field, so the vocabulary check reports 'field absent', not a contradiction) |

## Instrument and controls

Strict YAML load (duplicate-key detecting) + object-tree deep diff + cross-registry resolution.
Controls **6/6 PASS**: no-op zero diffs; unrelated-leaf mutation detected at exactly that path;
denial re-injection fails P1; inversion re-injection fails P2; fabricated variant token unresolved;
duplicate-key detector fires. Pins unchanged before/after; the FROZEN-manifest pin equals the live
schema; the mirror copy is byte-identical.

## Replication

```bash
python3 artifacts/worker-070/f2b_candidate_census/census_070.py   # pre-registered run
python3 artifacts/worker-070/f2b_candidate_census/finalize_070.py # addendum + events + checkpoint
```

Falsifier: re-run at the same pins. Falsified if any candidate sha, changed-path set, P1/P2 value,
invariant value or external-reference resolution differs, or if any control fails. Any pin change
away from `frame.json:pins_before` voids the run rather than falsifying it.

# W061-F2B-REPAIRPACK-09 — F2b containment repair pack (advisory)

Worker-061 · class `AF-SCC-C0-VAC-GEN` · node `F2b` · gate `G-FORM` · verdict **revise 3.5**
Target pinned at `schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe` (rev13). Worker evidence only —
not a gate verdict, no canonical file modified.

## What was measured

Read-only pin re-measure (12/12 stable) → structured obligation checker over the parsed YAML →
exhaustive direction-token census (39/39 lines classified, fail-closed on unclassified) → sandbox
two-line repair + canonical gate replay → controls K1–K6. All mutations live in `sandbox/`.

Live bytes: `flags = [O1_forbidden_reason_premise, O2_must_not_conflate_stale_denial]`.
Two-line sandbox patch: `flags = []`, YAML parses, diff touches exactly lines 152 and 246.
Canonical gate: **pass on live, pass on patched, pass on the over-corrected mutant** → a gate pass
cannot certify these clauses.

## The two live defects (both confirmed, both already flagged by 5+ reviewers)

| id | carrier | line | defect | repair |
|---|---|---|---|---|
| H1 | `implication_ledger.forbidden_transfers[0].reason` | 246 | Premise inverted: says “C2 is a strictly larger extension class”; the same file's chain makes `E_C2` the **innermost** set (`E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇ E_C2`). The row's from/to and its “strictly weaker” conclusion are correct. | `reason: "the converse containment is false; E_C2 is a proper subset of E_C0, so C2-inextendibility is strictly weaker than this class's conclusion"` |
| H2 | `regularity.must_not_conflate[0]` | 152 | Stale pre-R2 denial “No containment with C2 or C0 is asserted here” contradicts the same file's `extension_class_containment` and its four `one_way_entailments` rows. | `The extension sets are nested (E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0), so containment with both C2 and C0 IS asserted (see implication_ledger); the informal phrase …` |

The C2 sibling `schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3` already carries both corrected
counterparts (`must_not_conflate[0]` at F2a:152 and `forbidden_transfers[0]` at F2a:243). The repair
does not invent wording; it imports the sibling's.

## Not in the minimal repair (adjudication, not measurement)

- **V1 (contested)** `conclusion_type: scc_c0_future_inextendibility` is the canonical first token
  of `VOCAB_ALIASES.json#46cd9f1eb534` and the supplement's `conclusion_type`, while the F0 canonical
  `field_vocabulary.conclusion_type.allowed` holds the alias `strong_cosmic_censorship_C0`. F2b binds
  neither registry nor supplement hash (F1 has `vocabulary_aliases_ref`). Needs an F0-side ruling.
- **V2 (minor)** `schemas/af_scc_c0_vacuum.yaml.sha256` still pins the superseded `1bb78ce9b357`.
- The `artifacts/formulation/schemas/` mirror must be repaired byte-identically; the fixture corpus
  (H1 string in 35 `schemas/semantic_contract_tests` + 8 `artifacts/formulation/fixtures` files;
  H2 string in 9 + evidence copies) needs an explicit rebase-or-leave note.

## Blast radius (snapshot 2026-09-12T01:11:50+08:00)

11 review files strictly bind `reviewed_sha256 = b2ab6acb…`: **4 accept** (worker-090 01:08:56,
worker-072 01:10:13, worker-071 01:10:18, worker-052 01:11:15) and **7 revise** (worker-066 ×2,
worker-035, worker-017, worker-075, worker-053, worker-085). Controller pass-06 checked at
01:01:17, so its “F2b 0 accepts” coverage count is stale, and the snapshot is volatile.
**A rev14 repair moves the hash and voids all 11 bindings — including the four accepts.** Repair and
coverage adjudication must be sequenced deliberately.

## Controls

K1 H1-only → only O2 fires. K2 H2-only → only O1 fires. K3 over-correction (“strictly smaller …
strictly stronger”) → O1 fires. K4 unrelated mutation → flags unchanged. K5 determinism → identical
obligation reports. K6 altered expected pin → detected as drift. Gate executed on every variant.

## Falsifier

Re-run `probe_f2b_repairpack.py` at the pins in `probe_output.json`: falsified by (a) either carrier
absent from the pinned bytes; (b) the file's own chain not ordering `E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇
E_C2`; (c) the canonical gate rejecting the patched sandbox file; (d) O1/O2 not clearing on the
two-line patch; (e) any K1–K6 control failing; (f) any pinned hash drifting. Any byte change to the
target voids this verdict.

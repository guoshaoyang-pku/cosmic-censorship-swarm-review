# W043E-REV13-CLOSURE-01 — post-repair binding-closure audit of the landed rev13 trio

Worker-043, 2026-09-12. Node F1/F2a/F2b, gate G-FORM. Read-only on every canonical path;
the canonical consistency checker was executed only against a scratch ROOT (it rewrites its
own evidence file). No gate verdict, node status or validation_status is claimed.

## Why this audit exists

`astra-life05-evidence-binding-repair` item (2) instructed the formulation owner to
*refresh* `f0_binding.consistency_evidence_sha256` in all three class schemas to the live
`artifacts/formulation/evidence/taxonomy_consistency.json 9e335e9ba1bf` after a clean
`check_taxonomy_consistency.py` run. The repair landed at 00:53:20–00:55:02 and moved the
three schemas to rev13 with FROZEN rev29. The card's objective was to make "the rev13 schema
set hash-bound gate evidence instead of a self-contradictory binding chain". This audit
measures whether that objective was actually reached, by execution rather than by prose.

## Pins at the measured bytes

| path | sha256 |
|---|---|
| `schemas/af_wcc_vacuum.yaml` (F1, rev13) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a, rev13) | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b, rev13) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| evidence `taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` (495 B) |
| `FROZEN.json` (rev29, 00:57:26 re-stamp) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| checker `check_taxonomy_consistency.py` | `de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd` (unchanged) |
| F0 canonical / supplement | `0abb9ed8a961…` / `d7419b4e8963…` (unchanged) |

Moving-target guard: 13/13 pins identical at start and end of the window. Note the FROZEN
file itself was re-stamped once after the first probe (00:55:02 `3d9e3d77…` → 00:57:26
`815e0807…`, same revision 29, identical content pins), so "FROZEN rev29" is not a unique
object — pin it by file hash, not by revision label.

## Result

**Pointer resolves 3/3; the chain is not closed 3/3. Verdict: revise.**

1. **Pointer: PASS.** F1/F2a/F2b each declare `consistency_evidence_sha256 =
   9e335e9ba1bf…` and the live evidence measures `9e335e9ba1bf…`.
2. **Evidence → F0 linkage: FAIL.** The live evidence document has exactly eight fields
   (two paths, `consistent`, `errors`, `contract_divergences`, `notes`, `classes_compared`,
   `alias_policy`). It carries **no `map_taxonomy_sha256`, no `lead_contract_sha256` and no
   `measured_at`**, so it cannot be tied to the declared F0 bytes `0abb9ed8a961` or the
   supplement `d7419b4e8963`. `chain_closed = False` for all three classes.
3. **The pointer is durable but nominal.** The canonical tool on unchanged inputs emits
   byte-identical `9e335e9b` on two consecutive runs. But mutating an **unchecked** F0 field
   changes the F0 hash (`0abb9ed8a961` → `f1a37ffa91d9`) while the tool output stays
   byte-identical: the evidence hash is not a function of the F0 bytes. A compared-field
   mutation does move the output (`exit 1`), so the gap is precisely the missing input-hash
   binding, not a blind checker.
4. **Minimal completion tested.** Appending `map_taxonomy_sha256 = 0abb9ed8a961…`,
   `lead_contract_sha256 = d7419b4e8963…`, `measured_at = 2026-09-12T00:53:20+08:00` to the
   live eight-field document gives a byte-stable candidate
   `raw/evidence_bound_candidate.json` = `1322f3d37786f2e60d9ec33191799d9ba74f6e98b41dea002a75b573b98e7d50`.
   Re-pointing each schema to that hash is a **single-token substitution** (1 occurrence per
   schema, no line-count change); the closure predicate then returns `chain_closed = True`
   for all three classes. Tamper controls fail the predicate as they must.
5. **FROZEN rev29 is well-formed.** Revision 29 pins all three rev13 canonical schemas and
   their authoring mirrors, the live evidence and the unchanged tool; every pin matches the
   measured bytes.
6. **rev12 → rev13 delta is exactly the card's items.** F1 6 replaced + 1 inserted lines,
   F2a/F2b 3 replaced + 1 inserted; 0 unexpected semantic changes. F1's three strictness
   legs (D5 definition, visibility definition, variant SET relation) moved.
7. **Residual defect at rev13 (secondary).** `schemas/af_scc_c0_vacuum.yaml:246` still reads
   *"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"*,
   while line 239 of the same file states `E_C0 contains E_H2loc contains E_{C^1,1} contains
   E_C2` and the `one_way_entailments` run C0 ⇒ H2loc ⇒ C2. E_C2 is the innermost set, so the
   reason is false and internally contradicts the file. This is worker-083
   `W083-REV13-REPAIR-PACKET-01` L-FORM-01, still unapplied; the F2a sibling states the
   correct "converse containment is false" reason.
8. **Reviewer coverage.** Eight review files already carry a tree-hash/binding finding that
   the landed refresh does not discharge (`F1-review-rev27-a` HF-071-01,
   `F2b-rev12-069` HF-069F2B-I09, `F2a-review-19` HF-19-F2A-3, `F2a-review-043` HF-043-2,
   `F2a-review-rev27-c` HF-W092-F2A-01, `F2b-review-022-rev12`, `G-FORM-evidence-collision-086`,
   `F0-review-rev27-b`).

## Findings

- **HF-W043E-1 (blocking-for-clean-accept)** — the rev27 closure item (e) regression survives
  the landed repair: a resolved pointer over evidence that binds no inputs.
  *Repair:* emit the three binding fields in the evidence (or land worker-083 L-FORM-02:
  enriched writer + restored `675a99d0`), then re-point the three schemas to the new evidence
  hash and publish FROZEN rev30. The tested minimal candidate is
  `raw/evidence_bound_candidate.json#1322f3d37786`.
  *Falsifier:* the finding is falsified if the live evidence carries
  `map_taxonomy_sha256`/`lead_contract_sha256` equal to the measured F0/supplement hashes, or
  if a clean tool run produces such a document.
- **HF-W043E-2 (hard, residual)** — F2b line 246 false strength relation, contradicted by
  F2b line 239. *Repair:* `strictly larger` → `strictly smaller` in canonical and mirror.
  *Falsifier:* `E_C2 ⊄ E_C0` under the taxonomy's own ordering, or the live row already
  reading `strictly smaller`.

## Reproduce

```bash
cd <repo-root>
python3 artifacts/worker-043/w043e_rev13_closure/closure_probe.py   # rewrites raw/ + report.json
```

`report.json` carries every check with its measured data; `raw/` carries the instrument
outputs. The audit is void if any pinned byte moves: the script re-measures all 13 pins and
sets `moving_target` accordingly.

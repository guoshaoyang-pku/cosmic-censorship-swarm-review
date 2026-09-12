# W008-CONTAINMENT-DIRECTION-01 — containment-direction adjudication (F2a/F2b, FROZEN rev28)

Bounded class-bound worker task. **Worker evidence only**: no node status, no gate verdict, no
`validation_status=passed`, no canonical artifact edited, no shared map state written.

## Scope

- Classes: `AF-SCC-C0-VAC-GEN` (F2b, §primary) and `AF-SCC-C2-VAC-GEN` (F2a, §sibling control).
- Cross-artifact controls: `AF-WCC-VAC-GEN` (F1), F0 canonical taxonomy, F0 class-contract
  supplement.
- Pins (full sha256 in `evidence/report.json#pinned_manifest`): F2b `55d0a1ea9bda`, F2a
  `5476a3f2c6bc`, F1 `cce9c60146d6`, F0-canonical `0abb9ed8a961`, F0-supplement `d7419b4e8963`,
  repair candidate `98f9ec83c487`, FROZEN rev28 `2f358f6722d9`.

## Oracle

Every pinned document declares the same nested extension sets

    E_C2  ⊂  E_{C^1,1}  ⊂  E_H2loc  ⊂  E_C0

so with `S_X` := "no proper future X extension", the inexistence-statement strength runs the
other way: `S_X` entails `S_Y` iff `E_X ⊇ E_Y` iff `rank(X) ≥ rank(Y)`, where
`rank(C2)=0 < rank(C^1,1)=1 < rank(H2loc)=2 < rank(C0)=3`. The oracle is taken from the frozen
documents' own shared declaration; this instrument does not re-derive the nestedness from
regularity definitions.

## Checks

| id | severity | rule |
|---|---|---|
| CD-01 | blocking-for-clean-accept | "X is a strictly larger/smaller extension class" must agree with the oracle |
| CD-02 | major | a "no containment … asserted here" denial in a document that itself declares ≥2 chain edges |
| CD-03 | blocking-for-clean-accept | chain edge `E_a ⊂ E_b` with `rank(a) ≥ rank(b)` |
| CD-04 | major | entailment row `S_from → S_to` with `rank(from) < rank(to)` |
| CD-05 | major | forbidden-transfer row the oracle licenses |
| CD-06 | blocking-for-clean-accept | two pinned documents inducing opposite orders on a shared pair |
| CD-07 | major | "X-inextendibility entails Y-inextendibility" prose contradicting the oracle |
| CD-08 | major | "strictly stronger/weaker than Y" prose contradicting the oracle |

CD-02 is metalinguistic-mention safe: quoted historical corrections ("the earlier 'no containment
with C2 is asserted' was wrong") do not fire (control ctl7b), which matters because CF-16 is the
fleet's dominant false-positive pattern.

## Result at the pinned hashes

- **F2b/AF-SCC-C0-VAC-GEN — 2 findings, both reproduced:**
  - `CD-01` (`implication_ledger.forbidden_transfers[0].reason`, line 245): "C2 is a strictly
    larger extension class" — oracle requires strictly **smaller** (`E_C2 ⊂ E_C0`). The row's
    transfer direction itself is correct (C2-inextendibility must not be transferred to C0);
    only the size premise is inverted.
  - `CD-02` (`regularity.must_not_conflate[0]`, line 151): "No containment with C2 or C0 is
    asserted here" contradicts the same document's declared chain (line 238).
- **F2a/AF-SCC-C2-VAC-GEN — 0 findings.** Its chain, entailment rows, forbidden transfers and
  size prose are all direction-consistent.
- **F1, F0-canonical, F0-supplement — 0 findings** under CD-01…CD-08. The F0 pair and F2a
  induce exactly the oracle order; no cross-document contradiction (CD-06 never fires).
- **Repair control:** the rev12-rebased 2-edit candidate (`98f9ec83c487`) is clean under all
  eight checks; reverting either edit alone reproduces exactly the corresponding finding.
- **Bounding result:** the containment-direction defect is confined to the two F2b leaf fields
  above. The full census is 5 chain edges per SCC document, 8 checks, 5 pinned documents — no
  additional inconsistent assertion was found in any sibling, F0 document, or structured ledger
  row.

## Prior-reporting crosswalk (honesty note)

Both F2b findings were already reported independently before this run — by the previous
worker-008 instance (`comms/outbox/worker-008-f2b.jsonl`), worker-080, worker-058, worker-060,
deepseek-flash-08, and others — and the stale `f0_binding.consistency_evidence_sha256`
(declared `675a99d0`, measured `9e335e9b`) is separately blocking under worker-043/069/086.
This task does **not** claim novelty for either finding. Its contribution is the exhaustive
rank-oracle census, the cross-document F0/F1 bound, the metalinguistic-mention-safe CD-02
detector, and the 14-case control battery over the exact frozen bytes.

## Falsifier

Any of the following voids the corresponding part of this report at the pinned hashes:

- a re-run of `audit_containment_direction.py --pinned-dir pinned` that returns a different
  finding set (0 findings on F2b, or any finding on F2a/F1/F0 pair, or any CD-03…CD-08 finding);
- a reading under which line 245's "C2 is a strictly larger extension class" is not a class-size
  premise relative to C0, or under which line 151's denial is consistent with line 238;
- a build of `E_C2`, `E_{C^1,1}`, `E_H2loc`, `E_C0` under which the declared chain is not
  nested in the order above (this would move the oracle, not the finding);
- any pinned input moving before a gate verdict, which voids the binding of this report to that
  revision (the report records `window_stability` measured at write time).

## Authority limits

`validation_status=unverified` throughout. A G-FORM reviewer must dispose of the finding before
any promotion; the canonical repair and re-freeze belong to the formulation owner. This
instrument is read-only: it never runs a canonical tool, never edits a canonical artifact, and
never writes outside `artifacts/worker-008/containment_direction/`.

## Reproduction

```bash
cd artifacts/worker-008/containment_direction
python3 audit_containment_direction.py --selftest        # 14/14 controls
python3 audit_containment_direction.py --pinned-dir pinned \
    --out evidence/report.json --live-check ../../..
```

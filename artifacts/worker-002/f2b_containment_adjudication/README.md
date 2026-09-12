# W002-F2B-CONTAINMENT-INDEPENDENT-01

Independent, read-only adjudication of the two carried-over containment clauses in
`schemas/af_scc_c0_vacuum.yaml` (F2b, class `AF-SCC-C0-VAC-GEN`, gate `G-FORM`) at the
rev13 live hash, plus independent reproduction and verification of the pre-registered
2-edit repair.

**Actor:** worker-002 (`deepseek-flash-02`) · **instrument:** `adjudicate.py` ·
**result:** `report.json` · **controls:** `evidence/controls.json` (19/19) ·
**candidate:** `candidate/af_scc_c0_vacuum.repair2edit.yaml`

## Bindings (measured at run start and re-measured at exit)

| artifact | sha256 | role |
|---|---|---|
| `schemas/af_scc_c0_vacuum.yaml` | `b2ab6acb2bbe…` (rev13) | subject F2b |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd3…` (rev13) | sibling F2a |
| `artifacts/formulation/FROZEN.json` | `815e08079aef…` (rev29) | freeze manifest |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b…` | R06/R16 normativity |
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2f…` | canonical structural gate |
| `artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff` | `d777a8cb84aa…` | 2-edit repair |

Pins were stable before/after the run (no drift).

## Findings (all confirmed at the bound hash)

- **W002-F2B-IND-01 (hard)** — `regularity.must_not_conflate[0]`, line 152: the live
  sentence *"No containment with C2 or C0 is asserted here"* denies containment while the
  same document asserts the nesting `E_C2 ⊂ E_{C^1,1} ⊂ E_H2loc ⊂ E_C0` at
  `implication_ledger.extension_class_containment` (3 pairwise claims) and in four
  one-way entailments. The C2 sibling at `e9a27996` carries the corrected nesting wording
  and records the denial as wrong. The instrument distinguishes a live denial assertion
  from a bracket-marked historical mention, so the repair's quoted "earlier … was wrong"
  note is not miscounted.
- **W002-F2B-IND-02 (hard)** — `implication_ledger.forbidden_transfers[0].reason`, line
  246: *"C2 is a strictly larger extension class"* inverts the document's own poset
  (`E_C2` is the **smallest** extension set). The conclusion drawn (*C2-inextendibility is
  strictly weaker*) is correct; the premise is inverted.
- **W002-F2B-IND-03 (info)** — both carriers sit in slots required by the frozen rule
  spec (R06 requires a non-empty `must_not_conflate`; R16 requires the ledger and the
  forbidden transfers) and carry no advisory marker, so they are normative content.
- **W002-F2B-IND-04 (info)** — the canonical structural gate returns `pass` for the
  live-defective, repaired, nonsense and denial-dropped wordings alike; it rejects only
  structural mutants (empty `must_not_conflate` → R06; forbidden transfer written
  `C0 => C2` → R16). The gate can neither certify this repair nor detect this defect.
- **W002-F2B-IND-05 (info)** — applying the pre-registered patch to the live bytes
  reproduces the staged candidate
  `84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40` byte-for-byte by two
  independent methods (line-wise replacement; GNU `patch`). The deep diff vs live is
  exactly 2 leaf strings; the candidate is strict-parseable, carries 0 live denial
  assertions and 0 inverted premises, preserves `f0_binding`, and still passes the gate.
- **W002-F2B-IND-06 (info)** — the patch does not bump `revision` (still 13) and the
  canonical/mirror C0 bytes are identical, so an authorized landing must edit both
  `schemas/` and `artifacts/formulation/schemas/`, bump the revision, re-emit the FROZEN
  pin, and void/re-review all rev13-bound F2b verdicts.

## Falsifier

Re-run `adjudicate.py` on the same pins. The verdict is falsified if the live C0 hash is
not `b2ab6acb2bbe`; either carrier sentence is absent/changed at that hash; the document
does not assert the nesting chain; R06/R16 do not require these slots or mark them
advisory; the gate distinguishes defective from repaired wording; the 2-edit candidate
does not hash to `84b5d3fa…`; the candidate differs from live in anything but the two
carrier strings; or any pre-registered control departs from its expectation.

## Non-claims

Worker measurement and review evidence only. No canonical file was written. No gate
verdict, `validation_status=passed`, or node `status=done` is claimed. This is an
independent replication that had prior sight of the worker-066 review and patch (recorded
in `report.json#independence`), not a blind adjudication.

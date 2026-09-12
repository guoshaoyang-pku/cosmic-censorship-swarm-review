# W096-REV29-REEMISSION-CLOSURE-RECEIPT-01

Independent, read-only receipt for the live FROZEN rev29 re-emission. Class-bound: F1/F2a/F2b (AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN), gate G-FORM.

## Target and result

| | |
|---|---|
| live manifest | `artifacts/formulation/FROZEN.json` |
| live sha256 | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` (rev 29, frozen_at 2026-09-12T00:57:26+08:00) |
| superseded emission | `3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833` (frozen_at 2026-09-12T00:55:02+08:00, never announced) |
| declared pins resolved | 50 / 50 |
| checks | 9/9 pass |
| controls | 6/6 pass |
| input drift during run | none |
| verdict recommendation | **accept** |

## What changed between the two rev29 emissions (same revision number)

Measured delta `3d9e3d77fd87` -> `815e08079aef` (144 s apart):

- files map 48 -> 50 pins; added: `artifacts/formulation/evidence/variant_rebase_rev29_report.json`, `artifacts/formulation/tools/variant_rebase_rev29.py`
- changed pins: `artifacts/formulation/VARIANT_REGISTRY.json`, `artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json`, `artifacts/formulation/tools/regenerate_frozen.py`, `artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json`, `artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json`
- `rev29_delta` note text changed: True

## Closure of worker-074's W074-R29-FREEZE

`artifacts/formulation/evidence/variant_delta_check.json` declares `fc6ee058dd96` in both emissions; worker-074 observed `0b23f0b29232` at 00:56:44; the live file now measures the declared pin. Mechanism: **content restore**. Hash binding holds; the manifest was not re-pinned for this entry.

## Pinned paths written after the freeze

4 of 50 pinned paths have mtimes after the manifest mtime (2026-09-12T00:57:26+08:00); all regenerate to their declared bytes (`all_regenerated_to_pinned_content = True`):

- `artifacts/formulation/evidence/gate_test_report.json` mtime 2026-09-12T00:59:53+08:00, content unchanged: True
- `artifacts/formulation/evidence/taxonomy_consistency.json` mtime 2026-09-12T01:05:22+08:00, content unchanged: True
- `artifacts/formulation/evidence/variant_delta_check.json` mtime 2026-09-12T01:02:57+08:00, content unchanged: True
- `artifacts/formulation/evidence/variant_registry_check.json` mtime 2026-09-12T01:02:57+08:00, content unchanged: True

## Findings

- **W096-R29R-01** (closure/positive): W074-R29-FREEZE is closed at live FROZEN rev29 815e0807: artifacts/formulation/evidence/variant_delta_check.json measures the declared pin fc6ee058dd96; worker-074's observed 0b23f0b29232 was an intermediate regeneration that no longer exists on disk. Closure mechanism is content restore (mtime 01:00:04 > frozen_at 00:57:26), not re-pinning.
- **W096-R29R-02** (process/minor): 4 of 50 pinned paths carry mtimes after the manifest's own mtime (variant_delta_check.json, variant_registry_check.json, gate_test_report.json, taxonomy_consistency.json); all four regenerate byte-identically to their pins, so hash binding holds, but the freeze relies on generator determinism for evidence files.
- **W096-R29R-03** (documentation/minor): rev29_delta item (4) still lists VARIANT_REGISTRY.json:57 and AF-WCC-VAC-GEN.variant-SET.delta.json:11,22 as carrying the inverted SET direction; the live pinned bytes at those sites carry the corrected 'strictly weaker' reading with a rev13 correction note. The delta's own downstream sentence already confines L-FORM-03 to the two F0 artifacts, so the manifest note is internally inconsistent for 2 of 4 named sites.
- **W096-R29R-04** (provenance/minor): the first rev29 emission (3d9e3d77, frozen_at 00:55:02) was never announced by any artifact event; it exists only in third-party snapshots (worker-074, worker-083). The live re-emission is announced by its owner (leadform-20260912T005743-06 at 00:57:43).
- **W096-R29R-05** (carry-over): L-FORM-03 remains live at research_map/formulation_taxonomy.yaml:200 and artifacts/formulation/formulation_taxonomy.yaml:176 (assertional 'strictly stronger'); L-FORM-04 remains live: 25 rows in schemas/f1_falsifier_tests.jsonl still bind F1 rev12 cce9c60146d6 while the live F1 schema is rev13 d9cebb9404b2.
- **W096-R29R-06** (navigation/advisory): rev29_delta item (3) cites lines 72/213/234 for the three F1 visibility corrections; those are rev12-relative (verified against the pinned rev12 snapshot at 72/213/234, where the 'strictly STRONGER' assertion is still present). In the live rev13 file the same three fields are at lines 73/214/235 (+1). Content anchoring confirms all three corrections; the citation resolves to the superseded bytes, not a defect.

L-FORM-03 site classification measured: [{"path": "research_map/formulation_taxonomy.yaml", "line": 200, "class": "INVERTED_ASSERTION"}, {"path": "artifacts/formulation/formulation_taxonomy.yaml", "line": 176, "class": "INVERTED_ASSERTION"}, {"path": "artifacts/formulation/VARIANT_REGISTRY.json", "line": 57, "class": "CORRECTED_WITH_NOTE"}, {"path": "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json", "line": 11, "class": "ASSERTS_WEAKER"}, {"path": "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json", "line": 22, "class": "CORRECTED_WITH_NOTE"}]

## Non-claims

- This is a binding/consistency receipt for the freeze root at one hash; it does not re-adjudicate the mathematics or physics of any class.
- F1/F2a/F2b class content was not re-reviewed here; no counts_as_full_schema_verdict is claimed.
- Worker events cannot set status=done, validation_status=passed, or a gate verdict.
- Review files and the live tree are mutable; every cited byte was re-measured during the run and the drift guard re-checks it.

## Reproduce

```bash
python3 artifacts/worker-096/rev29_reemission_closure/receipt.py
```

Falsifier: Re-run receipt.py. Falsified if any declared pin no longer matches measured bytes, the recorded emission delta differs (files added/changed), the variant_delta_check pin is not satisfied, a recorded C07 site resolves differently at the recorded line, the live manifest is not announced by its owner, or any control fails.

Report: `report.json` (sha256 recorded in the outbox artifact event and checkpoint 8).


# W099-BL7-HF02-BINDING-01 — per-row class binding on the 8 dual-bound L0 rows

Decision support for BL-7 (the G-LIT gate-deciding question: does HF-02 "class
leakage / disjunction of class_ids" apply to ledger record rows?). Scope/routing was
adjudicated by `reviews/w063-l0-scope-adjudication.json`; this pack supplies the
content-side half asked for by BL-6: a per-row determination of which frozen class is
each row's subject and what the second id's relation is.

## Run

```bash
python3 artifacts/worker-099/bl7_hf02_binding/run_bl7_binding.py
```

Exit 0 = all controls pass; 3 = pinned input drift; 4 = control failure.
Deterministic: two processes produce the same `core_digest_sha256`.

## Pins

| input | sha256 |
|---|---|
| `ledger/theorems.jsonl` | `a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28` |
| `ledger/citation_audit.csv` | `315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9` |
| `research_map/formulation_taxonomy.yaml` (rev5) | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `evaluation_rubric.yaml` | `d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885` |
| `research_map/class_separation.py` | `a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd` |
| `ASSIGNMENTS.json` | `89867bcbae7a641eb3cff2bdfc0b6cbf6fe709728c3efa641bf81a49c0b31eb5` |

## Result at the pins

16/16 cell assignments quote-grounded; 16/16 fabrication controls caught.

| resolution | rows |
|---|---|
| `SINGLE_SUBJECT_SECONDARY_RELEVANCE` | T-303 |
| `SINGLE_SUBJECT_SECONDARY_INFERENCE` | T-526 |
| `SINGLE_SUBJECT_SECONDARY_ANTECEDENT` | T-515, T-528 |
| `GENUINE_DUAL` | T-402 |
| `INTERMEDIATE_NEITHER` | D-004, D-005, T-305 |

Consequence, class-scoped and measured only over this 8-row population: under the
strict one-binding-class reading, **4/8** rows have a determinable single subject whose
second id is relevance/antecedent/inference; **1/8** (T-402) states a relation to both
classes; **3/8** (D-004, D-005, T-305) have no frozen-class subject because their subject
is an intermediate extension class strictly inside the C0..C2 interval. The literal BL-6
repair instruction ("choose ONE class or move the second to `informs_classes`") therefore
has a correct answer for 4/8 rows only.

## Authority

No gate verdict, no node status, no `validation_status`, no class-binding repair and no
ledger edit. The recommendation field per row is decision support; the choice belongs to
the controller/A0 owner. Abstract/metadata-level evidence only, matching the rows' own
`verification_status=abstract-read`.

## Falsifiers

See `PREREGISTRATION.json`. In short: any quote shown not to occur in the pinned row
bytes; any cell relation contradicted from the pinned bytes/source; any of the six pins
moving; a changed dual-bound population; or a reviewer showing an `INTERMEDIATE_NEITHER`
row is exactly one frozen class, or a `SINGLE_SUBJECT` row asserts both.

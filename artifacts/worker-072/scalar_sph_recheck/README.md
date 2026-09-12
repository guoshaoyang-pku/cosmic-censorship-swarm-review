# W072-C — independent second-implementation recheck of the `AF-WCC-SCALAR-SPH` class-conformance audit (W072-A)

Bounded worker task (`worker=072`), self-selected because no assignment card exists for
`worker-072`. The target is the predecessor audit
`artifacts/worker-072/scalar_sph_class_audit/spotcheck_report.json`
(sha256 `4d931de7b4de…`, task W072-A). Its own scope note declares the gap this task closes:

> *"Only entries whose `class_ids` already include the class were classified; a mis-filed entry
> elsewhere in the ledger would be invisible to this audit (that is the W072-F1 falsifier's
> second clause)."*

So the recheck does two things: **re-implement the classification independently** (different
detector, different readings, explicit controls) and **measure the declared blind spot**
(recall scan over the whole ledger).

## Deliverable

| file | sha256 (recorded at emit) | what it is |
|---|---|---|
| `recheck_scalar_sph.py` | see outbox `artifact` events | stdlib-only, deterministic runner; fail-closed on pin drift |
| `recheck_report.json` | see outbox `artifact` events | machine result: pins, three readings, disagreement matrix, controls, recall scan, live-head check, findings |
| `README.md` | this file | method, results, limits, falsifier |

Reproduce: `python3 artifacts/worker-072/scalar_sph_recheck/recheck_scalar_sph.py`

## Method

1. **Pins.** The target binds `research_map/formulation_taxonomy.yaml#276009f4f63d`,
   `ledger/theorems.jsonl#ce42d205e761`, `ledger/citation_audit.csv#315c19145065` and the target
   report itself. The runner aborts `rc=2` unless every pin resolves to bytes with the pinned
   sha256. Both the live canonical taxonomy and the live ledger moved during this task
   (`0abb9ed8a961`, `3e3d35531421`); the pinned measurement was recovered from a **verified
   byte-identical on-disk archive** (recorded with path and hash) rather than silently
   re-pinned. The live heads are separately reported as an invariance check (`live_head_check`):
   all 62 entries, the same 10 class-bound ids, 0 content-field changes, H1–H4 and the class
   conclusion unchanged ⇒ the pinned measurement survives the revision in substance.
2. **Class definition is read from the pinned taxonomy**, not from memory: a line-oriented
   reader extracts H1–H4 and the conclusion/exclusions, and the run aborts unless the expected
   key phrases are present.
3. **Independent classifier.** Different code path, different evidence model, no import of the
   target runner. Matter evidence comes only from *content* fields (`label`,
   `statement_exact`, `assumptions`, `regularity`, `topology`, `genericity`) — never from
   `ledger_tags`/`class_ids`, which would make the check circular. Three readings are reported
   side by side:
   - **loose** — token presence (the family of reading the target used);
   - **space** — H1 loose, but H2/H3 read as hypotheses about the *data space*, so text that
     specifies anisotropic / non-symmetric perturbations rejects H2;
   - **strict** — `space` plus H1 requires an explicit massless-scalar / Einstein-scalar token
     (the class excludes massive/charged scalars and Λ ≠ 0).
4. **Controls (5/5 pass).** `CTRL-VACUUM` (scalar removed) must leave H1; `CTRL-FULL-WCC`
   (comeager clause + `conclusion_type: weak_cosmic_censorship`) must discharge; `CTRL-NONSPH`
   (anisotropic perturbation added) must split loose from space; `CTRL-LAMBDA` (Λ = 1e-3) must
   be excluded by H1; `CTRL-UNBOUND` (class id stripped) must reappear in the recall list.
5. **Recall scan.** Every one of the 62 ledger entries is classified; entries that conform but
   are not bound to the class are listed with their actual `class_ids` and `conclusion_type`.
6. **Locator recheck.** The 14 class-bound citation rows are validated by an independent
   doi/arxiv/url/exact_locator validator, with a stripped-locator control.

## Result at the pinned revisions

| quantity | value |
|---|---|
| bound ledger entries | 10 |
| conform, loose / space / strict | 4 / 3 / 2 |
| **discharge the class WCC conclusion** | **0 (all readings)** |
| bound entries naming a genericity notion (H4) | 1 (T-524, Baire vocabulary) |
| unbound entries that still pass the loose reading | 4 |
| class-bound citation rows with a resolvable locator | 14/14 |
| controls passed | 5/5 |
| disagreements with the target report | 5 rows |

### Disagreement matrix (recheck vs W072-A)

| entry | field | target | recheck | mechanism |
|---|---|---|---|---|
| T-105 | loose-conforms, H2 data-reading | true | false | the only `spherical` occurrence in the whole entry is inside `non-spherical` (`unresolved` field) |
| T-106 | H2 data-reading | true | false | all four occurrences are `non-spherical` / `NON-SPHERICAL` forms |
| T-524 | H2 data-reading | true | false | incoming cone is spherical, outgoing cone and perturbations are explicitly without symmetry |
| T-524 | H4 token | false | true | `open and dense` / `first category` in the continuous-shear-tensor topology |

The target's **H2 detector matches the substring `spherical` inside `non-spherical`** — a
mechanical defect that explains why it counted 5 in-class entries where the data-space reading
counts 3. The headline finding is unaffected.

## Findings

- **W072C-F1** — 0/10 bound entries discharge the class WCC conclusion under every reading;
  the conclusion-poor finding `W072-F1` survives an independent implementation.
- **W072C-F2** — in-class count is reading-sensitive (4 / 3 / 2), and the gap is mechanical:
  the target matches `spherical` inside `non-spherical`. Under the data-space reading T-105,
  T-106 and T-524 fail H2 because their data carry anisotropic/non-symmetric perturbations,
  which the taxonomy explicitly calls a forbidden transfer ("Non-spherical data: symmetry
  release is a different class").
- **W072C-F3** — recall scan: 4 unbound entries still pass the loose reading
  (`D-007` bound to C2; `T-501`, `T-514`, `T-521` bound to no class); none names H4 and none
  carries `conclusion_type: weak_cosmic_censorship`, so the blind spot is real but does not
  change the conclusion state. `T-505` is correctly excluded (charged scalar / Klein-Gordon).
- **W072C-F4** — H4 disagreement: an independent token set that includes Baire-category
  vocabulary finds one hit (T-524: `first category` / `open and dense` in the
  continuous-shear-tensor topology). It is not genericity for the class's own
  symmetry-reduced data space, so `W072-F2` is not falsified — but it is the nearest bound
  vocabulary and is directly relevant to the F1 schema's open genericity slot.
- **W072C-F5** — locator recheck: 14/14 class-bound citation rows resolve; the stripped-locator
  control is flagged. Consistent with `W072-F3`.
- **W072C-F6** — input drift during the task: ledger `ce42d205e761 → 3e3d35531421` and taxonomy
  `276009f4f63d → 0abb9ed8a961`. Live-head check: 62/62 entries, same bound list, 0
  content-field changes in the class-bound entries, H1–H4 and conclusion unchanged ⇒ invariant
  in substance, recorded not assumed.

## Scope limits

- Mechanical classification of entry metadata, not a semantic reading of the papers; a
  reviewer may bind T-105 / T-524's data differently (background reading vs data-space
  reading), which changes `W072C-F2` only, not `W072C-F1`.
- The recall scan can only see entries that are in the ledger; a conforming result that was
  never filed is out of scope.
- No gate verdict, no node completion, no theorem, no physics result, no class re-binding.
  Workers cannot set `status=done`, `validation_status=passed`, or a gate verdict.
- Nothing was written to `runtime/state/artifact_hashes.json` (controller-owned); the worker
  checkpoint is `runtime/state/w072_checkpoint_1.json`.

## Falsifier

Re-run at the pinned hashes: a different per-entry reading, or an unbound ledger entry with
`conclusion_type: weak_cosmic_censorship` that this recall scan missed, falsifies the table.
The sharpest single falsifier remains the target's: produce one class-bound entry that
(a) passes H1–H3, (b) names a genericity notion with a stated data-space topology and
primary-source scope, and (c) carries `conclusion_type: weak_cosmic_censorship`.

# W047-REC37-TOKEN-CROSSWALK-01 — REC-37 pinned token crosswalk + assertion-correct consistency check

**Worker:** worker-047 · **Node:** F1, F2a, F2b, F0 · **Gate:** G-FORM · **Class-bound:**
`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN` · **Checkpoint:** `w047-cp8`

## Why this task

Pass 08 ruled **REC-37**: the class schemas keep their canonical `scc_c2/scc_c0_future_inextendibility`
conclusion tokens; the frozen F0 taxonomy's `strong_cosmic_censorship_C2/_C0` entries are accepted
aliases; HF-075-F2a-VOCAB / HF-075-F2b-VOCAB are alias-vs-canonical presentation conflicts, and they
are discharged **"by a pinned crosswalk artifact plus a consistency check against the registry
mapping, never by a write to `research_map/formulation_taxonomy.yaml` (which voids G-F0)"**.
REC-36 item (4) folds that crosswalk into the authorized rev14/FROZEN rev30.
At the time of this run no crosswalk artifact existed on disk (`find artifacts -iname '*crosswalk*'`
→ no candidate), so this task builds the ready-to-adopt one and the check that makes it enforceable.

## Pins (measured, byte-stable across the run)

| artifact | sha256 |
|---|---|
| `research_map/formulation_taxonomy.yaml` (F0 rev5, frozen) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (F0 supplement) | `d7419b4e8963` |
| `artifacts/formulation/VOCAB_ALIASES.json` (registry) | `46cd9f1eb534` |
| `artifacts/formulation/rule_spec.json` (R11) | `40f9bb9e657b` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aef` |
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a rev13) | `e9a27996dfd3` |
| `schemas/af_scc_c0_vacuum.yaml` (F2b rev13) | `b2ab6acb2bbe` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bf` |

Byte copies + `PINS.json` + `SHA256SUMS`: `snapshot/`.

## Deliverables

| file | role |
|---|---|
| `crosswalk.json` | **candidate** crosswalk artifact — 43 token surfaces, per-class registry canonicals, F0 alias entries, unmapped entries, adoption block, falsifier. Non-canonical; no canonical path was written. |
| `build_rec37_crosswalk_047.py` | deterministic builder (read-only); output is a pure function of the pinned bytes |
| `check_rec37_crosswalk_047.py` | independent, read-only, fail-closed checker: 13 checks + 9 sandbox controls; exit 0 PASS / 1 findings / 2 pin drift |
| `report.json` | registry-mode machine evidence (3 identical runs, sha `0d3ef3aed7cb`) |
| `controls/literal_mode_report.json` | contrast run: the literal-membership assertion **fails** (C5) exactly as REC-37 says |
| `controls/determinism_run{1,2,3}.json` | byte-identical repeats |
| `MANIFEST.json`, `checkpoint.json` | measured hashes; worker checkpoint `w047-cp8` |

## Result — CONSISTENT_UNDER_REGISTRY_MAPPING

Registry mode: **13/13 checks PASS, 9/9 controls discriminate, exit 0.**
Literal mode (`--literal`): **C5 FAIL by construction** — the two SCC schema tokens are not literal
members of `F0.field_vocabulary.conclusion_type.allowed = [weak_cosmic_censorship,
strong_cosmic_censorship_C2, strong_cosmic_censorship_C0]`. That is the assertion-incorrect
comparison REC-37 replaces; the crosswalk records the contrast rather than hiding it.

What the crosswalk makes explicit and machine-checkable:

- `strong_cosmic_censorship_C2 → scc_c2_future_inextendibility`,
  `strong_cosmic_censorship_C0 → scc_c0_future_inextendibility`
  (and `baire_residual`/`provisional_baire_residual → residual_comeager`, `measure_one → full_measure`).
- Per class, `canon(F0 axis) == canon(F0 conclusion.type) == canon(supplement) == schema token
  == rule_spec R11 vocabulary`: all four classes agree; C0/C2 canonical sets are disjoint (no merge).
- `unresolved` is the F0-declared sentinel for the scalar class genericity axis — not a token.
- No `rejected_ambiguous_tokens` entry (`strong_cosmic_censorship`, `scc`) appears in a value position.

### Finding F-TC-1 (new, minor)

`F0.field_vocabulary.genericity_kind.allowed` carries **`dense_open`**, while the registry's accepted
alias of `open_dense_escape` is **`open_dense`**. Under the registry mapping `dense_open` is
**unmapped**; the crosswalk records it under `unmapped_f0_entries` with the anagram candidate
(`open_dense`) and requires a naming adjudication. It must not be silently normalized, and it does
not by itself reopen G-F0: the schema genericity tokens are canonical `residual_comeager`.
(Out of REC-37's conclusion-type scope; recorded because a crosswalk that silently drops it would
be exactly the kind of fluent-but-unchecked step this project keeps catching.)

## Adoption (owner action, rev14 item 4)

1. Copy `crosswalk.json` → `artifacts/formulation/VOCAB_CROSSWALK.json` and the checker →
   `artifacts/formulation/tools/check_token_crosswalk.py`.
2. Add both to the FROZEN rev30 per-file pins; keep `research_map/formulation_taxonomy.yaml` **untouched**.
3. Run the checker in registry mode at the new pins; record exit 0 in the rev14 evidence.
4. Do **not** copy the alias tokens into the schemas (alias policy forbids it; rule_spec R11 rejects it).

## Falsifier

At the pins above: (a) any pinned sha256 differs on re-measure; (b) a class schema declares an alias
form instead of the registry canonical; (c) an F0 alias entry does not resolve through the registry to
the canonical the class schema uses; (d) the C0/C2 canonical sets intersect on any surface; (e) a
rejected ambiguous token appears in a value position; (f) rule_spec R11 disagrees with a class schema;
or (g) an unmapped F0 entry is silently treated as an alias. A later canonical write is not a
falsifier — it voids the pins and requires re-measurement.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm/artifacts/worker-047/rec37_token_crosswalk
python3 build_rec37_crosswalk_047.py            # rewrites crosswalk.json deterministically
python3 check_rec37_crosswalk_047.py            # exit 0, writes report.json
python3 check_rec37_crosswalk_047.py --literal  # exit 1, documented contrast
```

## Authority limits

Worker artifact. No canonical file was edited (verified by re-measuring all nine pins after the run);
no node status, `validation_status=passed` or gate verdict is claimed. Worker events cannot move
those. Adoption and pinning belong to the formulation owner inside the authorized rev14.

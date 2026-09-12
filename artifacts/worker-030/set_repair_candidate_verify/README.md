# W030 — independent verification of the SET-strength repair candidate

One bounded class-bound task, worker-030, node F0, class `AF-WCC-VAC-GEN`, gate `G-FORM`.
Read-only on every canonical path; all scenario work happens in throwaway sandboxes under
`/tmp`; no gate verdict, no node status, no `validation_status`.

## What was verified

Target: the unfrozen candidate produced by worker-024 in
`artifacts/worker-024/set_strength_repair/` (`W024-SET-STRENGTH-REPAIR-01`), which folds
item (5) of the controller's authorized rev14 set (SET strength label: level-qualified
wording + assertion-correct SET clause in `check_variant_registry.py`). The candidate had
no non-author check at the time this task was taken.

Pins (all measured, entry == exit; drift would have voided the run):

| path | sha256 |
|---|---|
| `artifacts/formulation/VARIANT_REGISTRY.json` | `6bac9adea19e` |
| `artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json` | `64b8d6394a04` |
| `artifacts/formulation/tools/check_variant_registry.py` | `c471da4b7be9` |
| `research_map/formulation_taxonomy.yaml` (G-F0, no-write) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (companion) | `d7419b4e8963` |
| `schemas/af_wcc_vacuum.yaml` (F1 rev13) | `d9cebb9404b2` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aef` |

Candidate hashes (measured; equal to the author's claims):
`CANDIDATE_VARIANT_REGISTRY.json` `5c05a8cc7ea2`,
`CANDIDATE_AF-WCC-VAC-GEN.variant-SET.delta.json` `7a1f6212ad70`,
`CANDIDATE_check_variant_registry.py` `8b15f43e843d`, `repair.patch` `9fb0c6674849`.

## Result — `CANDIDATE_INDEPENDENTLY_VERIFIED_LEVEL_QUALIFIED_AND_ASSERTION_AWARE`

21/21 checks and 4/4 controls pass; `run_digest d14425daa794`.
Exit 0 from `verify_set_repair_030.py`; a second run reproduced the same digest.

1. **Structure.** The two data candidates differ from live on exactly their declared lines
   (registry line 57, delta line 11) with no length change; the checker diff is confined to
   the SET clause (one block, live lines 86–95). `repair.patch` applies with `patch -p1` on a
   sandbox tree and reproduces all three candidates byte-for-byte.
2. **Independent level predicate** (written for this task, not the author's):
   - live label → `LEVEL_MIXED`: asserts class direction `WEAKER` against
     `AF-WCC-VAC-GEN` while frozen `taxonomy:94` says class-level stronger, carries no
     class-level qualification, and asserts no predicate-level direction;
   - candidate label → `LEVEL_QUALIFIED_AND_ANCHOR_CONSISTENT`: class-level `STRONGER`
     qualified "as a class statement", predicate-level `WEAKER` for the SET predicate, and
     simultaneously consistent with both frozen anchors `taxonomy:94` (class) and
     `schemas/af_wcc_vacuum.yaml:235` (predicate);
   - registry and delta candidate labels are byte-identical.
3. **Behavioural matrix** (live vs candidate checkers, 9 sandbox runs):
   - live checker on live = exit 0 (`VALID`) — the known false pass;
   - live checker on the note-stripped live label = exit 1 — the mention-match mechanism
     reproduced independently (the sole `STRONGER` was inside the bracket note);
   - candidate checker on live = exit 1, on candidate = exit 0 — fails closed, passes clean;
   - candidate checker rejects the live label (m1), a class-direction flip to `WEAKER` (m2)
     and a predicate-direction flip to `STRONGER` (m3), and accepts a benign suffix (m4).
4. **Regression.** `check_variant_deltas.py` → `VALID: 2 variant deltas`;
   `check_taxonomy_consistency.py` → `CONSISTENT (4 classes, 0 contract-text divergences)`
   on the candidate sandbox tree.
5. **Write guard.** The full guard set — including the two evidence JSONs the checkers write —
   is byte-identical T0→T1; the checkers' writes landed only inside `/tmp` sandboxes.

## Reproduction

```bash
python3 artifacts/worker-030/set_repair_candidate_verify/verify_set_repair_030.py
# exit 0 = verified, 1 = falsified, 2 = pin drift / void; expect digest d14425daa794
```

## Falsifier

Falsified if, at the pins above: any guard byte moves; a candidate differs from live outside
its declared sites; `repair.patch` does not reproduce the candidates; the live label is
level-qualified and anchor-consistent under the published predicate (or the candidate label
is not); a declared mutation does not flip the expected checker exit; or a sibling checker
regresses on the candidate tree. An adopted revision at a new hash voids the pins and
requires a re-run.

## Scope / non-claims

This verifies a *candidate*, not its adoption: applying it, bumping `FROZEN` to rev30 and
re-pinning `artifacts/formulation/evidence/variant_registry_check.json` and
`variant_delta_check.json` belong to the formulation gate owner. The open `F0:199`
position-A/B adjudication and the unrelated F2b vocabulary conflict are untouched. No gate
verdict, no node status, no `validation_status`, no mathematics or physics claim.

## Files

| file | sha256 |
|---|---|
| `verify_set_repair_030.py` | `94f12baed8de` |
| `report.json` | `f9058cc96c92` |
| `README.md` | see `manifest.json` |
| `snapshots/live_VARIANT_REGISTRY.6bac9ade.json` | `6bac9adea19e` |
| `snapshots/live_SET_delta.64b8d639.json` | `64b8d6394a04` |
| `snapshots/candidate_VARIANT_REGISTRY.5c05a8cc.json` | `5c05a8cc7ea2` |
| `snapshots/candidate_SET_delta.7a1f6212.json` | `7a1f6212ad70` |
| `snapshots/anchors.txt` | `94f12baed8de`-run |

# W073-F1-REV29-BINDING-AUDIT-01 — F1 / AF-WCC-VAC-GEN at the FROZEN rev29 pin

Worker-073 (recycled slot), 2026-09-12. Read-only. One class-bound task, self-selected
because no `comms/inbox/worker-073.jsonl` card exists and G-FORM has zero full-schema
accepts at the live F1 pin.

## Question

At the live F1 pin (`schemas/af_wcc_vacuum.yaml` sha256 `d9cebb9404b2…`, revision 13,
FROZEN rev29), (a) are the two blocking findings recorded at that pin (worker-061
`HF-W061-VAR-01/02`) reproducible, and (b) does F1's gate-evidence corpus
`schemas/f1_falsifier_tests.jsonl` satisfy the lead-audit acceptance criterion
"each row must carry `binding_sha256` == the pin"?

## Method

`run_check_073_f1rev29.py`, own tooling, no project imports: strict duplicate-key YAML
loader, own predicate-inversion regex on the `class_identity_variants` block with
bracketed historical notes stripped, top-level-key token census, `f0_binding` hash-chain
resolution, 25-row corpus binding census, 6 controls, fail-closed on required-pin drift,
frame snapshotted under `pinned/` and re-measured at the end.

## Result (32 checks, 6/6 controls fired, frame stable)

- **F1-073-01 — blocking.** 25/25 corpus rows carry `binding_sha256 =
  cce9c60146d6…` (F1 rev12) and `binding_frozen_revision = 27`, while the live pin is
  `d9cebb9404b2…` (rev13) and FROZEN.json is rev29. FROZEN rev29 does pin the corpus
  file (`56bcb4b3234b…`), so the bytes are frozen but their binding target is one
  revision stale. 3 rows decide leaves edited by rev13
  (`visibility.definition`, `class_identity_variants`): F1-AMB-11, F1-AMB-17, F1-AMB-23.
  Under the explicit criterion in assignment `audit-r2-F1-a` this fails an accept.
- **F1-073-02 — resolved.** `HF-W061-VAR-01` is **not** reproducible at the pin: the
  variant-SET relation (line 235) reads `strictly WEAKER`; the inversion detector
  returns 0 hits in the block; every remaining `strictly STRONGER` token is a bracketed
  historical note or a different subject. The positive control on the superseded rev12
  copy (`cce9c601…`, line 234) reproduces the quoted defect, so the finding was true of
  rev12 and was removed by the rev13 repair.
- **F1-073-03 — info.** `L-FORM-03` is repaired in the reviewable satellites
  (`VARIANT_REGISTRY.json` SET strength and the variant-SET delta now read
  `strictly weaker`; delta base re-pinned to rev13). The old direction survives only in
  the two byte-frozen F0 artifacts (`research_map/formulation_taxonomy.yaml:200`,
  `artifacts/formulation/formulation_taxonomy.yaml:176`), outside F1's bytes.
- **F1-073-04 — info.** F1's `f0_binding` chain resolves at the frame
  (`0abb9ed8a961…`, `9e335e9ba1bf…`, supplement present, pointer resolves,
  consistency `consistent=True`).

Verdict: **revise, score 3.0**, hard failure `F1-073-01`.

## Limits and authority

- The verdict binds to the `pinned/` snapshot frame at the reported `live_hashes_t0`;
  a byte change to any frame file voids it. `moved_during_run` was empty.
- Non-blind: the existence/headline of worker-061's F1 revise was visible in
  `research_map.json` before this verdict was written. `counts_toward_gate_accept=false`.
  The blocking finding is independent of that exposure.
- Not a node status, not a `validation_status`, not a gate verdict.

## Prescription

Rebind the 25 rows to `d9cebb9404b2…` + FROZEN rev29 and re-derive the three
edited-leaf probes; or record an explicit controller adjudication that the declared
semantics-preserving rev13 delta is immaterial for those probes *and* amend the
acceptance criterion. Silence lets a gate accept F1 on evidence that predates the
frozen revision.

## Falsifier

Re-run `run_check_073_f1rev29.py`: a corpus whose every row binds the live pin, any
unbracketed in-block inversion, a non-firing control, or a moved required pin each
voids part of this report.

## Reproduce

```bash
cd <repo-root>
python3 artifacts/worker-073/f1_rev29_binding_audit/run_check_073_f1rev29.py
# exit 0 = verdict emitted; 2 = control failure; 3 = required-pin drift
```

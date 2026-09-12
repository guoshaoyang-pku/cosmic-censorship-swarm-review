# W004 — SEMCT frozen-control rebase (ADJ-CONTROL-STALENESS)

- **worker**: worker-004 (bounded execution worker, instance `worker-004-20260912T002827-968807`)
- **class binding**: `AF-SCC-C0-VAC-GEN` (controls are C0 schemas; conforming-canonical basis covers F1/F2a/F2b)
- **node / gate routing**: `A1` calibration evidence for `G-AUDIT`; also affects re-use of the suite by `G-FORM` reviewers
- **task source**: self-selected from the open adjudication item `ADJ-CONTROL-STALENESS` (no inbox card existed for
  `worker-004` at 2026-09-12T00:29+08:00); the supervisor prompt is "take one class-bound task, emit valid JSON with
  IDs evidence hash falsifier, checkpoint, then exit"
- **authority**: no gate verdict, no node status change, no canonical file written, no theorem promoted. Everything
  below is a measurement plus a patch proposal for `astra-lead-formulation`, the declared owner.

## 1. What was actually wrong

`ADJ-CONTROL-STALENESS` said the three frozen controls were authored against corpus base `92406957234f`, that the
canonical C0 moved the row `finite_codimension_complement -> residual_comeager` from `transfer_failures` to
`transfer_holds`, and that R28 rejects all three controls. Measured here at the byte level:

The stale controls carry **an extra duplicate row** inside `genericity.transfer_failures`:

```yaml
  - pair:
    - finite_codimension_complement
    - residual_comeager
    direction: transfers          # <-- R28: a 'transfers' row may not sit in transfer_failures
    witness: a countable union of proper closed finite-codimension submanifolds is
      meager
    status: elementary
    citation_status: n/a
```

The same pair is **already present and correct** in `genericity.transfer_holds`. The canonical C0 does not carry the
duplicate. So the fix is a deletion, not a semantic edit.

## 2. Repair and part-1 measurement

`rebase_controls.py` removes exactly that 8-line block from each of the three controls (each diff: **1 hunk, −8
lines, +0 lines**), then runs the three contract stages with hashes pinned and fails closed on any input drift.

| fixture | sha256 (stale → rebased) | structural | semantic baseline | semantic hardened |
|---|---|---:|---:|---:|
| `control_comment_only_composite.yaml` | `a6ad2638dc99` → `2babcc7d3430` | R28 fail → **pass** | accept → accept | accept → accept |
| `control_conforming_base.yaml` | `7b910cf34e64` → `7ab748114243` | R28 fail → **pass** | accept → accept | accept → accept |
| `control_quoted_forbidden_phrase.yaml` | `687fd6971304` → `47dd3f9ec285` | R28 fail → **pass** | accept → accept | accept → accept |

- stale controls: **0/3** accepted by the structural stage (all `failed_rules == ["R28"]`)
- rebased controls: **3/3** accepted by all three stages
- pinned canonical schemas: **3/3** accepted by all three stages
- stage hashes: structural `000e09e46b2f…`, semantic `c79d8ab8440a…` (unchanged)

Evidence: `rebase_report.json` (inputs pinned by sha256), `rebased_controls/`.

## 3. End-to-end proof in a shadow repo

`build_patched_suite.py` builds artifact-local shadow copies of the gate toolchain (tools + `rule_spec.json` +
`KEY_MANIFEST.json`), so the runs cannot race the live tree. The only runner change is one line
(`REPO = HERE.parent.parent` → `HERE.parents[2]`, shadow path resolution). Canonical fixtures are byte snapshots of
the last revision measured accepted by all three stages.

| run | controls | KEY_MANIFEST | exit | `valid_for_calibration` | controls | canonical | mutants (S/B/H) |
|---|---|---|---:|---|---:|---:|---|
| `rev27_patched` | rebased | rev27 `fce91948ba3a` | **0** | **true** | 3/3 | 3/3 | 32/11/32 |
| `rev27_stale` | original | rev27 `fce91948ba3a` | 3 | false | 0/3 | 3/3 | 32/11/32 |
| `rev28_patched` | rebased | rev28 `014e2d301978` | 3 | false | 0/3 | 0/3 | 32/11/32 |

The `rev27_patched` vs `rev27_stale` pair differs **only in the three control files** (same mutants, same canonical
snapshots, same tools, same manifest, same runner copy): the runner goes from exit 3 / invalid to **exit 0 /
valid, 0 escapes, 0 hardened-only catches**. This is the demonstration that the control-staleness component is
cleared by the rebase.

Evidence: `suite_run_report.json`, `shadow_repo/**`, `shadow_repo_stale/**`, `shadow_repo_rev28/**`, `logs/`.

## 4. Second finding — the key allowlist is not revision-stable (blocks re-calibration)

The third run isolates a **separate, currently active blocker**. `artifacts/formulation/KEY_MANIFEST.json` was
regenerated at 00:34 from the new canonical revision:

- rev27 `fce91948ba3a` (pinned in `artifacts/worker-061/f1_rev12_gate/pinned/hist/KEY_MANIFEST.rev27.json`):
  264 keys, contains `revised_at_unused`
- rev28 `014e2d301978` (live): 271 keys; **dropped `revised_at_unused`**, added
  `at, class_contract_supplement_pointer, consistency_evidence_sha256, index, notes, predicate_abbreviation,
  revision_history, unused`

Under rev28, R22 rejects the rebased controls, the original controls, **and the pinned canonical revision that
rev27 accepted** — all on the unknown key `revised_at_unused` (the quoted-phrase control additionally exposes
`extensions`-subtree keys, which is an R22 escape-hatch interaction worth a separate look). No frozen corpus is
usable as calibration evidence while the allowlist moves with the live schemas.

**Needed to unblock (lead decision):** freeze `KEY_MANIFEST.json` together with the schema revision it is used to
judge, or make R22 path-sensitive/revision-aware; then re-pin the suite's conforming-canonical entries and re-run.
This is independent of the control rebase — the rebase is necessary, not sufficient, while the allowlist drifts.

## 5. Third finding — live F1 WCC fails the adopted semantic baseline (timestamped)

Measured 2026-09-12T00:38:37+08:00 on `schemas/af_wcc_vacuum.yaml` sha256 `cce9c60146d6…` (unchanged since
00:34): structural **pass**, semantic baseline **reject R03**, semantic hardened **reject R03**
(`artifacts/worker-06/spec_conformance_audit.py` `c79d8ab8440a…`). Localised with the auditor's own rule body:
`quantifiers.ordered[5]` is `{kind: not_exists, binder: "(q,t0)", domain_id: D5}` but the string `(q,t0)` does not
occur in `quantifiers.formal`; R03 requires every ordered binder to appear in the formal sentence. Either the formal
sentence is missing the final witness binder or the binder string must match the token used there. The previous
revision `9a8bd4c96800` passed all three stages. Re-measure before acting: the live tree was being rewritten
throughout this run.

## 6. How to apply the rebase (proposal, not applied)

`manifest_patch_proposal.json` lists every field-level operation. Summary:

1. Replace the three files in `schemas/semantic_contract_tests/fixtures/controls/` with the byte-identical copies in
   `rebased_controls/` (sha256 above).
2. Update the three `controls[*].sha256` entries in `schemas/semantic_contract_tests/manifest.json`; the originals
   are preserved in the proposal and in this directory.
3. Re-pin the three `conforming_canonical_controls[*]` entries (`fixture` and `sha256`) to whatever canonical
   revision is frozen; the proposal records the last gate-accepted revision
   (`1bb78ce9b357` / `b6123750b37d` / `9a8bd4c96800`).
4. All 32 mutant fixtures and their sha256 values are untouched.

## 7. Falsifiers

- an unmodified frozen control accepted by the structural stage at the pinned tool hash;
- a rebased control rejected by the structural stage or either semantic stage at the pinned tool hash;
- any byte difference between a stale and a rebased control outside the removed 8-line block;
- a `rev27_patched` run not reaching exit 0 / `valid_for_calibration == true`, or mutant counts differing from
  32/11/32, or a `rev27_stale` run reaching exit 0;
- any byte change in a pinned fixture, stage tool, `rule_spec.json`, key manifest or canonical snapshot — voids the
  corresponding run until re-run;
- reinstating `revised_at_unused` in `KEY_MANIFEST.json` falsifies the §4 regression claim;
- a semantic-auditor run on `cce9c60146d6…` that accepts it falsifies §5.

## 8. Limits

A structural/semantic contract test decides shape, not mathematical correctness, non-vacuity, or truth. This repair
changes **only** corpus calibration fixtures; it asserts nothing about the WCC/SCC classes themselves. The controls
are worker-authored synthetic calibrators. Nothing here sets a gate verdict, marks a node done, or promotes text.

## 9. Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-004/semct_control_rebase/rebase_controls.py        # part 1: rebase + stage measurement
python3 artifacts/worker-004/semct_control_rebase/build_patched_suite.py    # part 2: shadow end-to-end runs
```

Both scripts fail closed on any pinned-input mismatch. Runtime ≈ 3 s and ≈ 25 s.

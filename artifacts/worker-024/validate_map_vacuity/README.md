# W024-VALIDATE-MAP-VACUITY-01 — instrument audit of `research_map/validate_map.py`

- **Task:** W024-VALIDATE-MAP-VACUITY-01 (worker-024, bounded lifecycle)
- **Class ids:** `AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH`
- **Node / gate:** A1 / G-AUDIT (map-integrity instrument; no gate verdict claimed)
- **Audited revision:** `research_map/validate_map.py` sha256 `aa4bd61c55cbb0361f56626888bfd722a03d0cb98addec8b63d67114b91ed211`
  (live re-measured equal at run time; `research_map/schemas.py` `75214a75353b…`, imported by the validator,
  also snapshotted)
- **Map snapshot:** `research_map/research_map.json` sha256 `3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005`
  (0 done nodes at this revision — the deployed done-node check is currently unexercised)
- **Context revision:** `research_map/apply_events.py` `16820bf206b720d59199aa26374e6db2ae4de45da3e9cb4e8763750bd864efed`
  (the other tool that interprets the same `node.artifact` field)
- **Result:** 74/74 checks held, 18 cases + 2 two-direction divergence probes; 8 vacuous `VALID`
  passes, 3 partial indirect guards, 6 negative controls, 1 healthy control; fail-closed patch
  verified on copies.

## What was measured

`validate_map.py` is the canonical structural validator for the sole global state; its `VALID`
line is quoted in checkpoints and gate evidence. On the pinned bytes it is **presence-driven**:
it checks the structures it finds and asserts nothing about the structures that must be present.

**(A) Fail-open — 8 structures return `VALID` / exit 0:**

| case | mutation | current |
|---|---|---|
| C1 | `{}` | VALID |
| C2 | `groups` and `cross_group_edges` removed | VALID |
| C3 | `groups: []` + cross edges removed | VALID |
| C4 | every `nodes` list emptied + cross edges removed | VALID |
| C5 | all governance sections removed (`gates`, `numerics_lock`, `claims`, `reviews`, `resource_requests`, `assignments`, `applied_event_ids`, `frozen_artifacts`, `controller_findings`, `publication_status`, `controller_gate_audit`, `portfolio_events`) | VALID |
| C6 | `gates: []` **and** `numerics_lock` removed | VALID |
| C7 | only header keys survive (truncation-shaped object) | VALID |
| C8 | `numerics_lock.state = locked` but locked node `N1` set `active` (hard decision 2 violated) | VALID |

Partial indirect guards found (not vacuous): removing `groups`/emptying node lists **while
leaving `cross_group_edges`** raises dangling-edge errors (C2b/C3b/C4b). That is the only thing
that catches those two mutations, and it disappears as soon as the edges are stripped with them.

Consequence for G-AUDIT / G-F0 / G-FORM: an `validate_map.py` `VALID` quote certifies only the
structures present in the map that was read; it cannot distinguish a healthy map from an emptied,
governance-stripped or truncated one. No gate verdict is asserted here — this is an instrument claim.

**(B) Artifact-path base divergence — measured in both directions:**

`validate_map` resolves `node.artifact` against `research_map/` (`base = ROOT`, `ROOT = Path(__file__).parent`),
while `apply_events.py` resolves the same field against the repo root (`ROOT = Path(__file__).resolve().parent.parent`,
line 19; demotion check line 393) — and the map's declared paths are repo-root-relative.

| probe | artifact | exists at repo root | validator CLI | in-process `base=repo_root` | `apply_events` demotion |
|---|---|---|---|---|---|
| D1 | `schemas/af_wcc_vacuum.yaml` | yes | **INVALID** (false positive) | VALID | keeps done |
| D2 | `formulation_taxonomy.yaml` | no (only under `research_map/`) | **VALID** (false negative) | INVALID | demotes |

So the first legitimately-`done` node whose artifact is declared the normal way
(`schemas/…`, `reviews/…`, `numerics/…`, `ledger/…`) makes the canonical CLI print `INVALID`
even though the file exists, and `apply_events.main()` will carry that non-empty `map_errors`
into every ingest report; conversely a node that `apply_events` demotes can be certified `VALID`.
This directly threatens the planned F0/F1/F2 completion path.

Controls: the healthy map snapshot is `VALID`; six negative controls (missing artifact,
done without evidence refs, cycle, duplicate node, unknown dependency, done without
validation_status) all fail as expected, so the validator is not simply permissive.

## Proposed patch (owner decision, verified on copies, not applied)

`fail_closed_patch.diff` (patched file: `patched/validate_map.patched.py`) adds
(1) a non-vacuity block — non-empty groups/nodes, required sections `gates`/`claims`/`reviews`/
`assignments`/`numerics_lock`, non-empty `gates`, and the `numerics_lock` invariant — and
(2) default `base = ROOT.parent` (repo root, matching `apply_events.py:19`) plus a `--base` flag.

Verified on copies: every vacuous case C1–C8 now exits 1 with a printed reason; the healthy
snapshot and D1 still pass; all six negative controls still fail; D2 now fails under the
repo-root convention, consistent with `apply_events` demotion.

## Evidence (hash-pinned)

| path | sha256 |
|---|---|
| `report.json` | see `exit_hashes.json` |
| `drive_vacuity.py` | see `exit_hashes.json` (74 assertions; rerun command below) |
| `fail_closed_patch.diff` | see `exit_hashes.json` |
| `snapshots/validate_map.aa4bd61c55cb.py` | `aa4bd61c55cb…` |
| `snapshots/schemas.75214a75353b.py` | `75214a75353b…` |
| `snapshots/research_map.snapshot.json` | `3d45be5969ec…` |
| `patched/validate_map.patched.py` | see `exit_hashes.json` |
| `checkpoint.json`, `runtime/state/w024_validate_map_vacuity_checkpoint.json` | see `exit_hashes.json` |
| `logs/*.stdout.txt`, `logs/*.stderr.txt` | raw CLI output per case/channel |

## Falsifier

Re-run `python3 artifacts/worker-024/validate_map_vacuity/drive_vacuity.py` against the pinned
snapshot hashes (a snapshot mismatch exits 2 and voids nothing — it refuses to run). The claim is
**FALSIFIED** if any of C1–C8 returns `VALID`/rc 0 from either channel at `aa4bd61c…`; or if any
of the six negative controls or the healthy control deviates from `report.json`; or if D1 does not
show canonical-CLI INVALID with an existing repo-root artifact while in-process `base=repo_root`
is VALID; or if D2 does not show canonical-CLI VALID while `apply_events` would demote. Any later
edit of the validator (new sha256) voids this claim for the edited bytes; the audit then binds
only to its snapshot.

## Non-claims

- No gate verdict, no `validation_status=passed`, no node transition; worker events cannot move
  those. This is a completion claim for one bounded worker task.
- Does not assert physical/mathematical content of any class; it audits the instrument that
  certifies the map's structure.
- Does not assert that `validate_map.py` is the right enforcement point for the `numerics_lock`
  invariant (a lock guard exists); only that `VALID` does not certify it.
- Does not adjudicate whether node artifact paths should be repo-root-relative or
  `research_map/`-relative; it measures that two tools in the same pipeline disagree, and the
  patch aligns the validator with `apply_events.py` and the map's dominant convention.
- Canonical files were read only; no canonical path was written and no map state was modified.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-024/validate_map_vacuity/drive_vacuity.py   # 0 = all assertions held
```

Raw single-shot checks used for reconnaissance:

```bash
echo '{}' > /tmp/empty.json && python3 research_map/validate_map.py --map /tmp/empty.json   # VALID, rc 0
```

# W065-CANON-SIDEPIN-CENSUS-04 — stale hash side-pin census (F2b / G-FORM)

Bounded class-bound worker task, no inbox card existed for `worker-065` at launch.
Class `AF-SCC-C0-VAC-GEN` (node F2b, gate G-FORM); F1/F2a appear as cross-checks.
**Worker evidence only: this sets no node status, no `validation_status`, no gate verdict.**

## Question

Every hash side-pin on a canonical path is a place where a re-binding reviewer or tool
can be sent to *superseded bytes*. The F2b gate path already had one such trap recorded
(worker-087 `W087-GFORM-INDEP-05`: the sidecar `schemas/af_scc_c0_vacuum.yaml.sha256`
advertises the revoked `1bb78ce9…` while the live schema is `b2ab6acb…`). This task asks
the mechanical version of that question over **all** declared pin registries, at a
settled revision, with a fail-closed checker and an artifact-local repair shadow.

## Method (declared instrument)

Registries read (nothing else; the continuously-moving map is excluded by policy):

| registry | kind | pins |
|---|---|---:|
| `entry_hashes.json` (repo root) | JSON path→sha256 registry | 12 |
| `artifacts/formulation/FROZEN.json` (rev 29) | authority `files{}` pins | 50 |
| `*.sha256` sidecars under `.`, `schemas/`, `ledger/`, `artifacts/formulation/`, `artifacts/flash-04/` | sha256sum files | 32 |
| `schemas/af_scc_regularities.yaml` | aggregator component pins | 2 |

Sidecar target resolution rule: declared path relative to the targets root first, then
relative to the sidecar's own directory. Classification per pin: `OK_LIVE`,
`OK_FROZEN_AND_LIVE`, `OK_LIVE_FROZEN_STALE`, `STALE`, `TARGET_MISSING`,
`MOVING_TARGET_EXEMPT` (map only), `DRIFT_CONTESTED` (CF-26 detector only), `FREEZE_DRIFT`.
A pin is **gate-relevant** when its resolved path is one of the declared gate targets
(three class schemas, aggregator, `taxonomy_cases.jsonl`, `f1_falsifier_tests.jsonl`,
F0 taxonomy, `FROZEN.json`, `rule_spec.json`, `KEY_MANIFEST.json`,
`VARIANT_REGISTRY.json`, `evaluation_rubric.yaml`, `ledger/theorems.jsonl`,
`ledger/citation_audit.csv`).

## Result — `SIDEPIN_TRAP_CONFIRMED`, window STABLE (1 attempt)

96 pins measured at the settled revision: **56 OK (frozen+live), 26 OK live,
1 moving-target exempt, 13 stale**; **8 of the stale pins are gate-relevant**:

| registry | target | advertised | live |
|---|---|---|---|
| `entry_hashes.json` | `research_map/formulation_taxonomy.yaml` | `276009f4…` | `0abb9ed8…` |
| `entry_hashes.json` | `schemas/af_wcc_vacuum.yaml` | `9a8bd4c9…` | `d9cebb94…` |
| `entry_hashes.json` | `schemas/af_scc_c2_vacuum.yaml` | `b6123750…` | `e9a27996…` |
| `entry_hashes.json` | `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9…` | `b2ab6acb…` |
| `entry_hashes.json` | `artifacts/formulation/FROZEN.json` | `af24e9c3…` | `815e0807…` |
| `schemas/af_scc_c0_vacuum.yaml.sha256` | `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9…` | `b2ab6acb…` |
| `artifacts/flash-04/f1_ambiguity/BUNDLE.sha256` | `schemas/f1_falsifier_tests.jsonl` | `18102c20…` | `56bcb4b3…` |
| `artifacts/flash-04/f1_ambiguity/BUNDLE.sha256` | `artifacts/formulation/FROZEN.json` | `8d0725ef…` | `815e0807…` |

Five further stale pins are advisory (non-gate): the mirror taxonomy pin, the CF-26
detector pin (advertises the *recorded* frozen `c266dbec…`, live `a8c04fc3…` — classified
`DRIFT_CONTESTED`, not stale-forgery), `audit_evidence.py`, and two flash-04 helper files.
Mirror alignment is 3/3 byte-identical at the measured hashes.

Registries as measured: `entry_hashes.json` sha256 `09a5b37a190d…` (mtime 00:19:49),
sidecar `256dd18d7944…` (mtime 00:19:14), `FROZEN.json` rev 29 `815e08079aef…`,
aggregator **rev 7** `27255e5b34f3…` with component pins `e9a27996…` / `b2ab6acb…`.

### Mid-run transition (measured, recorded not hidden)

The first measurement pass caught the aggregator at **rev 6** (`94562101a816…`) with two
stale component pins (`b6123750…`, `1bb78ce9…`) while declaring `canonical_gate: pass` —
its own SEP-6 lint rule says a post-00:15 component revision must fail the integration
lint until re-pinned. Inside the same window the owner published **rev 7**
(`0f137687…` → `27255e5b…`), re-pinned to live bytes; the settled measurement above
therefore records the aggregator clean. Transition evidence is pinned in
`pre_settlement_aggregator_transition.json`; `rev7.supersedes_sha256` points at the
rev-6 bytes. The two remaining registries (`entry_hashes.json`, the F2b sidecar) were
**not** repaired during the window.

### F2b accept-path blast radius (declared-hash scan, `reviews/*.json` only)

* Accept records **declaring the live hash** `b2ab6acb…`: `worker-052`, `worker-071`
  (full-schema), `worker-072`, `worker-090` (full-schema).
* Accept records **declaring only the superseded hash** `1bb78ce9…`: `deepseek-flash-17`,
  `worker-001`, `worker-030` (full-schema).
* The event stream is excluded from binding because its F2b accept events carry null
  `reviewed_sha256`/`artifact_sha256`.
* Reference point: worker-087 measured F2b at **1 live cluster** at 01:04; the
  `worker-090/071/072` accepts landed 01:08–01:10. Reviewer independence/clustering is
  the `astra-life05-verify-gform-r3` adjudication's call, not this artifact's.

## Instrument and repair shadow

* `check_sidepins.py` — standalone fail-closed checker. `--root` (registry root) and
  `--targets` (target root) allow the same rule to run against a shadow. Exit 0 = clean,
  2 = gate-relevant defect, 1 = instrument error. Live tree: **exit 2**.
* `sidepin_census.py` — driver; rebuilds the shadow, runs the 7 controls, writes
  `sidepin_census.json` and `control_results.json`.
* `repair_shadow/` — artifact-local candidate refresh (no canonical write):
  `entry_hashes.json` all resolvable pins refreshed to live, `schemas/af_scc_c0_vacuum.yaml.sha256`
  refreshed to `b2ab6acb…`, aggregator copy (already live at rev 7, no substitution),
  plus `MANIFEST.json` with base/shadow hashes. Checker on the shadow: **exit 0**.

## Controls (7/7 pass)

| id | mutation | expected | observed |
|---|---|---|---|
| K0 | live tree | exit 2 | exit 2 |
| K1 | repaired shadow | exit 0 | exit 0 |
| K2 | shadow sidecar reverted to `1bb78ce9…` | exit 2, `STALE` | detected |
| K3 | shadow F1 pin replaced by non-hash garbage | exit 2, `STALE` | detected |
| K4 | shadow F1 pin repointed to the live F2a hash | exit 2, `STALE` | detected (repoint recorded) |
| K5 | shadow aggregator c0 pin reverted to `1bb78ce9…` | exit 2, `STALE` | detected |
| K6 | shadow pin to a nonexistent canonical target | exit 2, `TARGET_MISSING` | detected |

## Falsifier

Any pin this census classifies `STALE` is shown to resolve its target correctly under a
declared resolution rule (FROZEN `path_policy` redirect, or a documented alias); or any
gate-relevant target's bytes change between the window pre/post readings (window
`UNSTABLE`, voiding the measurement at the newer revision); or a refreshed shadow this
census calls clean still advertises a non-live hash for a canonical target. For the
blast-radius clause: a review record on disk that declares the live F2b hash but was
counted as superseded-hash-only, or vice versa.

## Authority

Worker evidence only. The F2b sidecar and `entry_hashes.json` are canonical-path files;
refreshing them is the formulation owner's write (CF-12: one canonical path, one owner).
`repair_shadow/` is a candidate, not a landed repair. The audit lead owns the r3
independence adjudication; the controller owns any gate movement.

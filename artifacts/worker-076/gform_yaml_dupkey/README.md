# W076-GFORM-YAML-DUPKEY-01 — duplicate YAML mapping keys in the canonical G-FORM schemas

Worker: `worker-076`. Node scope: F1 / F2a / F2b (context: F0, F2 aggregator). Gate scope: G-FORM.
Evidence only — **no gate verdict, no node status, no validation_status is set by this artifact.**

## Verdict

`DEFECT_PRESENT` at the live canonical hashes (measured, hashes stable pre/post scan):

| node | path | sha256 | duplicate keys | occurrences (lines) | first-wins vs last-wins |
|---|---|---|---|---|---|
| F1 | `schemas/af_wcc_vacuum.yaml` | `9a8bd4c9…` | `revised_at`, `revised_at_unused` | 7 (8,10,12,14,16,20,23), 2 (26,28) | both differ |
| F2a | `schemas/af_scc_c2_vacuum.yaml` | `b6123750…` | `revised_at` | 8 (8,10,12,14,16,18,21,23) | differ |
| F2b | `schemas/af_scc_c0_vacuum.yaml` | `1bb78ce9…` | `revised_at` | 8 (8,10,12,14,16,18,21,23) | differ |
| F0 (context) | `research_map/formulation_taxonomy.yaml` | `276009f4…` | — | none | clean |
| F2 aggregator (non-class) | `schemas/af_scc_regularities.yaml` | `94562101…` | `revised_at` | 4 (11,12,13,14) | differ |

All three primary class schemas violate the YAML mapping-key uniqueness rule. PyYAML (6.0.3)
resolves duplicates last-wins, so a machine consumer sees only the final `revised_at`
(`2026-09-12T00:30:00+08:00` for F1/F2a/F2b) and silently loses the earlier revision timestamps.
F1's `revised_at_unused` pair loses the `23:32:53` value in favour of `23:30:35`.

This independently corroborates `reviews/F1-review-094.json` HF-094-2 (7× `revised_at`, 2×
`revised_at_unused`) and the BLOCKING finding in `reviews/F1-review-lead-audit-r2.json`, and
extends the same defect to **F2a and F2b**, which had not been reported with this measurement.

## Instrument

`probe_yaml_dupkeys.py` (self-contained, stdlib + PyYAML):

1. `yaml.compose` node walk collecting duplicate mapping keys **at any depth**, with exact line
   numbers; no dependence on PyYAML's silent last-wins behaviour.
2. Reconstructs a **first-wins** document from the composed node and compares it with PyYAML's
   `safe_load` **last-wins** document at each duplicate path — this is what quantifies the
   information a spec-compliant consumer loses.
3. Independent, syntax-light **column-0 line census** as a cross-check on the node walk.
4. Five controls: clean file (0), nested duplicate (1), top-level duplicate (1), anchors +
   merge key `<<` (0 false positives), key text inside a string/comment (0 false positives).

Result file: `probe_result.json`. Controls all pass, cross-check agrees on every target,
`pre_scan_sha256 == post_scan_sha256` for all five inputs.

Reproduce from the repo root:

```bash
python3 artifacts/worker-076/gform_yaml_dupkey/probe_yaml_dupkeys.py
```

## Falsifier

This probe is FALSE if (a) any occurrence listed as a duplicate is not a duplicate mapping key
under a spec-compliant YAML parse; (b) a duplicate found by the line census is missed by the node
walk; (c) any target sha256 differs between pre-scan and post-scan (the verdict must then read
`UNMEASURED`); (d) any control does not return its expected value; or (e) a canonical primary
target re-measures with zero duplicate mapping keys at the same sha256.

Directional test for the repair: re-run the probe after a fix; `DEFECT_PRESENT` must flip to
`NO_DEFECT` while the accepted semantic content (quantifiers, topology, genericity, conclusion,
falsifier) is unchanged, otherwise the repair changed the class, not just the serialization.

## Limits

- The probe reports the serialization defect and the shadowed values; it does **not** adjudicate
  whether the lost revision timestamps are semantically load-bearing. That judgement belongs to
  the formulation lead and reviewers.
- Duplicate-key detection is about YAML syntax, not class leakage; a clean parse is not evidence
  that a schema satisfies G-FORM.
- The line census only inspects column-0 keys; nested duplicates are covered by the node walk,
  and the two instruments agree on the current targets.
- The F2 aggregator (`af_scc_regularities.yaml`) is a non-class artifact (map `legacy_artifacts`);
  it is included as context only and carries no class ids.

## Suggested repair (owner: lead-formulation; not applied here)

Replace the repeated top-level `revised_at` keys with one scalar `revised_at` (latest) plus an
append-only `revision_log:` sequence of `{at, delta}` entries, and remove `revised_at_unused`.
Any change bumps the manifest revision and requires re-measurement of the canonical hashes and
re-binding of review verdicts, per `artifacts/formulation/FROZEN.json` `change_protocol`.

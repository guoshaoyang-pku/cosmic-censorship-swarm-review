# W03-PUBLISH-CHECK-01 — did publication land, and does anything bind to it?

**Snapshot.** `artifacts/formulation/FROZEN.json` revision 22, `frozen_at 2026-09-12T00:24:00+08:00`
(caller-supplied and ~570 s *ahead* of wall clock), manifest sha256 `bbbaa1362abe…`, stable during
the scan; report generated `2026-09-12T00:14:29+08:00`. Baseline for the delta is
W03-VERDICT-BIND-01 (scan `00:08:37`, FROZEN rev 19 `da6a0ee9…`). Task `W03-PUBLISH-CHECK-01`,
node `F1`, gate `G-FORM`, class_ids `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`.

**Question.** `astra-life01-publish-frozen` requires the FROZEN revision at the four canonical
paths and `verify_frozen.py` exit 0; W03-VERDICT-BIND-01 measured 0/4 pairs published, 5 drifted
FROZEN entries and 0 eligible accepts. This is the after-publication re-measurement: what landed,
what still blocks, and does any review verdict now bind the canonical bytes?

**Method.** `check_publish_binding.py` (stdlib only) hashes the four canonical/authoring pairs,
reads the FROZEN declarations, re-runs W03-VERDICT-BIND-01's binding scanner unmodified to
`rescan_report.json`, runs the project's `verify_frozen.py` and `audit_evidence.py` capturing
exit codes and their own lines verbatim, and diffs all of it against the baseline report. It
never edits the artifacts it measures and sets no gate verdict.

```bash
python3 artifacts/worker-03/publish_binding_check/check_publish_binding.py
```

## Headline (baseline → this snapshot)

| measurement | W03-VERDICT-BIND-01 | now |
|---|---|---|
| class-schema canonical↔authoring pairs identical | 0/3 | **3/3** |
| taxonomy pair identical | no | no |
| `verify_frozen.py` drift files | 5 | 1 (`evidence/aggregator_pin_check_rev3.json`) |
| `audit_evidence.py` dual-tree divergences | 4/4 pairs diverging | 1 (taxonomy only) |
| eligible independent accepts bound to canonical sha256 | 0 | 0 |

The three class schemas are published and correctly declared:
`af_wcc_vacuum.yaml` `b65fcc0f0118…`, `af_scc_c2_vacuum.yaml` `8dae50da1ab5…`,
`af_scc_c0_vacuum.yaml` `a8d899d2941f…` (canonical = authoring = FROZEN-declared).
`research_map/formulation_taxonomy.yaml` (`565a6e505188…`) still differs from the frozen
`artifacts/formulation/formulation_taxonomy.yaml` (`01e7f841643c…`).

## Findings (per-finding falsifiers in `report.json`)

- **W03-PB-01 (major).** Publication of the three class schemas landed: 3/3 class pairs identical
  (baseline 0/3); the taxonomy pair still diverges.
- **W03-PB-02 (major).** FROZEN rev 22 is *not* reconciled to disk: `verify_frozen.py` exits 1
  with 1 drift file (`evidence/aggregator_pin_check_rev3.json`); class-schema drift is 0 of 3.
  `verify_frozen.py` exit 0 is therefore still unmet.
- **W03-PB-03 (major).** 0 eligible independent accepts bound to the canonical sha256 (0 of 4
  accepts; baseline 0 of 3). One accept *does* bind the canonical bytes —
  `reviews/F2b-softflag-disposition-review.json` on `af_scc_c0_vacuum.yaml` `a8d899d2941f…` — but
  it self-declares `counts_as_independent_second_verdict: false` and
  `counts_as_full_schema_verdict: false` (soft-flag disposition only). The other cited hashes are
  pre-publication and now resolve to nothing on disk.
- **W03-PB-04 (minor).** `audit_evidence.py` exits 0 with 1 dual-tree divergence (taxonomy): the
  publish assignment's 0-divergence acceptance test is one file short.
- **W03-PB-05 (minor).** `frozen_at` is caller-supplied (`regenerate_frozen.py --at`); rev 22
  declares `00:24:00` while written ~`00:14`. It orders revisions only nominally — use revision +
  manifest sha256 for freshness.

## Falsifier

Re-run the checker against the same FROZEN revision and canonical bytes. The report is falsified
if (a) any pair marked non-identical re-hashes identical; (b) any pair marked identical re-hashes
different; (c) `verify_frozen.py` exits 0 with 0 drift while the report says otherwise; or (d) any
eligible accept bound to the canonical sha256 appears while the report says 0. A change in the
inputs after the snapshot is not a falsifier: `frozen_manifest_sha256`, `research_map_sha256` and
the baseline hash pin what was read.

## Files

| file | sha256 (prefix) | role |
|---|---|---|
| `check_publish_binding.py` | `e32d827836b2…` | deterministic checker; re-run command above |
| `rescan_report.json` | `bfd980ac7830…` | unmodified W03-VERDICT-BIND-01 binding scan at this snapshot |
| `report.json` | `084d814b0363…` | primary artifact: snapshot, delta, findings, falsifiers, limits |

## Limits

Timestamped snapshot, written while the formulation lead was actively re-freezing
(rev 19 → 22 within ~10 minutes; drift count moved 10 → 2 → 3 → 1 across runs). Reviewer
independence is taken from declared flags, not adjudicated here. Worker-authored evidence only —
Astra/the gate owner adjudicates; nothing here moves a node or a gate. No claim is made about the
mathematical content of any schema or review.

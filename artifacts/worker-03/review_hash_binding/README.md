# W03 VERDICT-BIND-01 — review verdict ↔ frozen revision binding audit

**Snapshot.** `artifacts/formulation/FROZEN.json` revision 19 (`frozen_at 2026-09-12T00:04:48+08:00`,
sha256 `da6a0ee9f2f6…`), stable across the scan; `research_map/research_map.json` sha256
`f7b9ec81891d…`. Scan time `2026-09-12T00:08:37+08:00`. Task `VERDICT-BIND-01`, node `A1`,
gate `G-FORM`, class_ids `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`.

**Question.** G-FORM's criterion is *"reviewers 17,18 accept with cited sha256"*. Nothing in the
tooling reads the review store, so this measures whether any accepted verdict actually cites the
sha256 of the artifact the gate would freeze.

**Method.** `scan_verdict_bindings.py` (stdlib only, deterministic) hashes 1816 files under a fixed
root whitelist, records declared-vs-disk hashes for every FROZEN.json entry, parses the review
stores (`reviews/`, `artifacts/formulation/reviews/`), extracts declared binding fields
(`artifact_sha256`, `reviewed_sha256`, `dispatched_sha256`, …) and resolves every 12–64 hex prefix
against the frozen hash snapshot. Re-run:

```bash
python3 artifacts/worker-03/review_hash_binding/scan_verdict_bindings.py
```

## Headline measurements

| class | FROZEN-declared sha256 | independent accepts bound to it |
|---|---|---|
| `AF-WCC-VAC-GEN` | `f962c117ba11…` | **0** (0 accept verdicts at all) |
| `AF-SCC-C2-VAC-GEN` | `e9fcefe6e595…` | **0** (1 accept, binds authoring tree) |
| `AF-SCC-C0-VAC-GEN` | `bdb23f76b895…` | **0** (2 accepts: 1 authoring-bound, 1 unresolved and self-declared non-independent) |

All four authoring/published tree pairs differ at scan time, and the review store cites the
**authoring** side (`schemas/*.yaml`, `research_map/formulation_taxonomy.yaml`), not the published
`artifacts/formulation/**` side that FROZEN.json declares:

| authoring (cited by reviews) | published (declared frozen) |
|---|---|
| `schemas/af_wcc_vacuum.yaml` `7a3e1f93f77c…` | `artifacts/formulation/schemas/af_wcc_vacuum.yaml` `b65fcc0f0118…` |
| `schemas/af_scc_c2_vacuum.yaml` `23fec0e9cd68…` | `artifacts/formulation/schemas/af_scc_c2_vacuum.yaml` `e9fcefe6e595…` |
| `schemas/af_scc_c0_vacuum.yaml` `e6b1af2bd692…` | `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` `e80e696e277f…` |
| `research_map/formulation_taxonomy.yaml` `565a6e505188…` | `artifacts/formulation/formulation_taxonomy.yaml` `6c027b23aac9…` |

## Findings (full text and per-finding falsifiers in `report.json`)

- **W03-FB-01 (major).** No G-FORM class has an eligible independent accept verdict bound to the
  FROZEN-declared sha256. Current independent verdicts (reviewers 15/16/17/18) are all `revise`.
- **W03-FB-02 (major).** 4/4 authoring/published tree pairs differ; reviews cite the authoring side.
  This is the mechanical cause of FB-01: a verdict on `schemas/x.yaml` cannot certify the frozen
  `artifacts/formulation/schemas/x.yaml` while the two differ.
- **W03-FB-03 (major).** FROZEN.json revision 19 already declares five files whose bytes on disk no
  longer match, including two class schemas (`af_wcc_vacuum.yaml` `f962c117→b65fcc0f`,
  `af_scc_c0_vacuum.yaml` `bdb23f76→e80e696e`) — the freeze was stale within minutes. Transient if
  the lead is mid-publish; recorded because the snapshot was taken against a stable manifest.
- **W03-FB-04 (minor).** `research_map.json:frozen_artifacts` does not pin the three current
  canonical schemas, so `audit_evidence.py`'s drift check cannot protect them (its list holds only
  superseded entries plus the class-separation tools).
- **W03-FB-05 (minor).** 8/25 review files cite a sha256 that resolves to no on-disk file
  (revisions overwritten in place); those verdicts are not re-verifiable against current disk.
- **W03-FB-06 (minor).** 9 review files bind to the authoring tree; 4 accept verdicts exist and none
  binds the frozen revision.

## Falsifier

Re-run the scanner against the same FROZEN revision. The report is falsified if (a) any review
classified `!= binds_frozen` cites a 12+ hex prefix equal to the FROZEN-declared sha256 of the class
artifact its target names; or (b) any tree pair classified non-identical is byte-identical on
re-hash; or (c) any FROZEN entry classified drifted matches its declared sha256 on re-hash. A
prose-only citation is not a counterexample; only a declared binding field counts.

## Limits

Unresolved citations mean "cannot be re-verified against current disk", not "fabricated". Reviewer
identity comes from declared fields. The report is a timestamped snapshot — the formulation lead
regenerates FROZEN.json and the review store concurrently, so a re-run may legitimately differ.
This audit makes no claim about the mathematical content of any review or schema.

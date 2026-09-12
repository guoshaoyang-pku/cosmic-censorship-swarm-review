# W021-BIND-01 — independent review-corpus binding audit

**Worker:** worker-021 · **Node:** L0 · **Gate:** G-LIT · **Classes:** AF-WCC-VAC-GEN;
AF-SCC-C2-VAC-GEN; AF-SCC-C0-VAC-GEN; AF-WCC-SCALAR-SPH
**Snapshot:** see `report.json` → `snapshot_at` (run at 2026-09-12T00:33+08:00)
**Verdict:** `BINDING_AUDIT_COMPLETE` (controls all pass, differential agrees)

## Question

The controller's gate reasons are computed by
`research_map/astra_lifecycle.py::review_coverage`, which only credits a review
when the JSON file has a top-level `verdict`, a readable
`target_id`/`target`/`target_subnode`, and an explicit hash pin matching the
measured artifact hash. Which on-disk verdicts does that scan actually count,
which verdicts exist but are invisible to it, and what is the per-gate accept
deficit at the measured hashes?

## Method

1. Snapshot every input: measured node hashes (`AL.measured_hashes`), each
   `reviews/*.json` sha256, and a corpus digest.
2. Reproduce the controller scan by importing it.
3. Independently re-implement the documented binding rule from the source text
   (no controller helpers) and require exact agreement per `(file, target,
   verdict)` — `report.json.differential`.
4. Intent-aware walk: verdicts anywhere in a document, pins anywhere
   (including `target_id: "path#sha256"` encodings), mapped to measured nodes by
   pin prefix. The audit-lead census (`coverage.*.verdicts_at_measured_hash[]`)
   is excluded from attribution because it restates other reviewers' verdicts.
5. Controls: 10 synthetic fixtures run through the **real** controller function
   with `AL.ROOT` pointed at a temp corpus, plus two intent-scan recovery checks
   and a synthetic differential. All must pass or the audit is void.

## Headline results at this snapshot

- **Mid-window republication voided the standing corpus.** F0, F1, F2a, F2b and
  L0 were all rewritten 00:30–00:32 (mtime evidence in
  `report.json.republication_vs_0021`). Counted full-schema accepts collapsed to
  `{"L0": ["worker-006"]}` — empty for 7 of 8 gate nodes — and 72 review files
  now pin a superseded hash. Pre-00:32 gate reasons are void until re-issued.
- **Binding-format gaps undercount real accepts** (independent of the churn):
  nested `verdicts[]`/`targets[]` (e.g. `L0-review-032.json`),
  `target_id: "path#sha256"` with a matching `reviewed_sha256` (e.g.
  `F2b-review-worker-001.json`), and scoped soft-flag dispositions that must
  stay excluded from full-schema credit (`F0F1-softflag-disposition-review.json`).
- **Binding does not fix content.** F1 had no accept at any encoding at its
  00:21–00:32 hash; that arm is content-blocked, not binding-blocked.
- The corpus is live. `report.json` voids itself on any recorded file-hash
  drift; re-run before citing.

## Files

| file | role |
|---|---|
| `run_binding_audit.py` | deterministic, stdlib-only checker (read-only on canonical paths) |
| `report.json` | full machine output: matrices, per-file classification, controls, findings, drift |

## Reproduce

```bash
cd <repo root>
python3 artifacts/worker-021/review_binding_audit/run_binding_audit.py \
        --out /tmp/recheck.json
```

Deterministic given the same corpus; the verdict is void if any synthetic
control deviates, if the independent classifier and `review_coverage` disagree,
or if any recorded input hash has moved.

## Authority

No gate verdict, no node completion, no rebinding of any reviewer's verdict.
The per-file minimal repair in `report.json.intent_delta` is an instruction for
the audit lead / controller, not an action taken here.

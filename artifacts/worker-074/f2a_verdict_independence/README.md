# W074-A1-INDEP-01 — F2a review-corpus independence audit

**Worker:** worker-074 (slot 074), bounded execution, lifecycle 3
**Class:** `AF-SCC-C2-VAC-GEN` — node `F2a`, gate `G-FORM`
**Target artifact:** `schemas/af_scc_c2_vacuum.yaml`
**Measured target sha256:** `b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2` (hash-stable during the run)
**Authority:** worker evidence only. This audit issues no review verdict, sets no node status, sets no validation_status, and edits no canonical path.

## Why this task

`G-FORM` requires two **independent** accepts at the measured canonical hash. The
controller's gate audit counts *distinct reviewer ids*. The comms protocol adds a rule the
count does not implement:

> Kish ESS is reported for any set of reviews that share a text or a template; two reviews
> that agree because they are the same text count as one. (`comms/PROTOCOL.md`, review rules)

With ~100 worker slots producing reviews concurrently, the accept count is only as good as
its dedup. This audit closes that gap for F2a: it harvests every F2a review verdict that
binds the measured hash, dedups by reviewer identity, by verdict text, and by evidence
channel, and reports the effective independent accept count.

Non-duplication: the controller audit counts reviewer ids only; `worker-057/xdata_check`
audits data-class sharing; the individual F2a reviews (worker-047/-050/-061/-069/-072/-078/-098,
deepseek-flash-15/-20/-21/-22/-33/-86/-88/-95) are consumed here, not re-issued.

## Method (deterministic, no network, fail-closed)

1. Harvest every `review` event from `research_map/events.jsonl` plus all
   `comms/outbox/**/*.jsonl|json` (dedup by `event_id`; richer copy wins).
2. Scope to F2a by normalized `target_id` (`F2a`, `AF-SCC-C2-VAC-GEN`,
   `schemas/af_scc_c2_vacuum.yaml`, multi-target F1/F2a/F2b, `F2`) or by a review-document
   path matching `f2a`; other single-node targets are excluded and listed.
3. Keep only verdicts that bind prefix `b6123750b37d` (in the event or in any sha256 field
   of a named on-disk review document). Superseded-hash verdicts are advisory only.
4. Independence:
   - **reviewer identity** — two verdicts by the same reviewer are one;
   - **verdict text** — identical normalized review-document sha256, or token 6-gram
     Jaccard ≥ 0.60 on the reviewer's own findings text, collapse to one cluster
     (sensitivity reported at 0.50/0.60/0.70/0.80);
   - **evidence channel** — own evidence = cited inputs minus the shared baseline
     (canonical schema/taxonomy/rule-spec/checkers/FROZEN) and minus the reviewer's own
     verdict document. Reviewer-specific instruments and probe outputs count as that
     reviewer's channel.

## Result at this snapshot

| quantity | value |
|---|---|
| F2a-scoped review events | 37 |
| bound to `b6123750b37d` | 20 |
| raw accepts / revise / inconclusive (bound) | 8 / 8 / 4 |
| distinct accept reviewer ids | 7 (worker-047, -050, -061, -069, -072, -078, -098) |
| **effective independent accepts (identity + text)** | **7** |
| distinct accept evidence-channel signatures | 7 |
| accepts citing no reviewer-specific instrument | 2 events, 1 reviewer (worker-098's two passes) |

**Finding `W074-INDEP-F1`:** the G-FORM "two independent accepts" criterion is **met at this
snapshot under the protocol dedup rule** — the 8 raw accepts are 7 independent reviewer/text
clusters, none of which is a template copy of another, and six of the seven cite their own
instrument or probe output rather than only the shared canonical gate. The two worker-098
events are two passes by the same reviewer and count once. Accepts bound to superseded
hashes (pre-rev11) are excluded and listed in `rows` with `binds_expected_hash = false`.

This is an independence result, **not** a correctness re-adjudication: the bound corpus also
contains 8 revise and 4 inconclusive verdicts (astra-lead-audit, deepseek-flash-15,
deepseek-flash-21, deepseek-flash-22, worker-020, -033, -037, -043, -066, -086, -088, -095)
whose findings were not evaluated here. Whether G-FORM can pass still depends on the lead's
disposition of those open findings and on at least two accepts remaining at the frozen hash.

## Falsifier

Falsified if (a) the measured sha256 of `schemas/af_scc_c2_vacuum.yaml` is not
`b6123750b37d…` on re-run or drifts during a run; (b) re-running the script on the same
recorded corpus yields different cluster assignments; (c) any two reviews in one
identity/text cluster have different reviewers, distinct review-document sha256 and
findings shingle-Jaccard < 0.60; or (d) any review counted as an independent accept is shown
to be a re-send of another reviewer's text, or a template whose decisive evidence is the same
single artifact as another accept's.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-074/f2a_verdict_independence/audit_f2a_independence.py
```

Inputs pinned in `audit_report.json` (`target`, `sources`, `corpus`); the frozen snapshot's
bound event ids and corpus digest are in `snapshot_row_ids.json`.

## Limits

- The corpus is a growing snapshot; later verdicts are not included (recorded cutoff and
  event-id digest are in the report). Note CF-14: some events carry future-dated
  `created_at` (max 02:00), so the cutoff is advisory for ordering.
- Events with no on-disk review document were reconstructed from the event JSON, which can
  understate similarity if a shared template was trimmed differently.
- Text similarity is a proxy for template sharing; the evidence-channel column is the
  structural check and is reported separately.

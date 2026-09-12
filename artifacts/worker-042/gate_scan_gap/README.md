# W042-GATE-SCAN-GAP-02 — gate-reason coverage scan vs the accepted event stream

Worker: `worker-042` (bounded execution worker). Node `A1`; classes
`AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`, `AF-WCC-SCALAR-SPH`;
gates touched by the finding: `G-F0`, `G-FORM`, `G-LIT`, `G-AUDIT`.

**Authority note.** This is an advisory visibility/coverage measurement. It sets no gate
verdict, no node status and no `validation_status`; binding coverage is adjudicated by the
audit lead (`reviews/A1-rebind-coverage.json`) and gate verdicts by the controller.

## Question

At one pinned snapshot, does the controller's advisory review-coverage scan
(`review_coverage` in `research_map/astra_lifecycle.py`, which reads only `reviews/*.json`)
agree with the *accepted* event stream (`research_map/events.jsonl`) about which reviewers
hold a full-schema accept at the controller-measured canonical hash of F0/F1/F2a/F2b/L0/L1 —
and do the `controller_gate_audit` reason strings in the pinned map reflect the union?

## Pinned inputs (audited copies under `snapshot/`)

| input | snapshot file | sha256 |
|---|---|---|
| `research_map/events.jsonl` | `events_9faab1179173.jsonl` | `9faab1179173…` |
| `research_map/research_map.json` | `research_map_4fd40d4d1e4f.json` | `4fd40d4d1e4f…` |
| `runtime/state/artifact_hashes.json` | `artifact_hashes_cc6aecb90ddf.json` | `cc6aecb90ddf…` |
| `reviews/*.json` (72 files) | `snapshot/reviews/` | manifest `63666d27cc09…` |
| snapshot manifest | `snapshot/manifest.json` | `4ee0145df14c…` |

Measured hashes come from the pinned map's `artifact_sha256_measured` nodes
(F0 `276009f4f63d`, F1 `9a8bd4c96800`, F2a `b6123750b37d`, F2b `1bb78ce9b357`,
L0 `ce42d205e761`, L1 `315c19145065`) and are cross-checked against the pinned
`artifact_hashes.json` registry (agree for F1/F2a/F2b/L0/L1; F0 is absent from that registry).

## Method

`audit_gate_scan_gap.py` re-implements the controller scan semantics exactly (verdict kinds,
reviewer fallback, `counts_as_full_schema_verdict is not False`, target aliases, explicit pin
keys, 12-hex prefix match) and applies them to two corpora:

* **scan A** — the pinned `reviews/*.json` corpus (what the controller reads),
* **scan B** — review events in the pinned `events.jsonl` (accepted traffic).

It reports per-target accept sets, A/B deltas, the map's own quoted counts, and a seven-control
self-test (synthetic fixtures in a temp dir; any failure ⇒ `status: INVALID`, exit 2).

## Headline at the pin (`generated_at 2026-09-12T00:29:58+08:00`)

Scan A: 72 review files; scan B: 194 review events.

| target | scan A accepts | scan B accepts | B-only | A-only |
|---|---|---|---|---|
| F0 | — | `worker-040` | `worker-040` | — |
| F1 | — | — | — | — |
| F2a | `worker-047` | `worker-047`, `worker-050`, `worker-098` | `worker-050`, `worker-098` | — |
| F2b | `deepseek-flash-07`, `deepseek-flash-17`, `worker-030` | `deepseek-flash-07`, `worker-030`, `worker-096` | `worker-096` | `deepseek-flash-17` |
| L0 | `worker-011` | `worker-011` | — | — |
| L1 | — | `deepseek-flash-07`, `worker-006` | `deepseek-flash-07`, `worker-006` | — |

Gate-reason classifications (pinned map, `checked_at 2026-09-12T00:24:40+08:00`):
`G-F0/F0` and `G-AUDIT/F0` = `undercount_vs_event_stream`; `G-FORM` F1/F2a/F2b and
`G-LIT/L0` = `quoted_count_not_reproducible_at_pinned_corpus`. G-NUM is out of scope (C8
protocol review, no accept-count criterion).

## Findings

* **W042-GSG-01 (major).** Full-schema accepts at the measured hashes exist in the accepted
  event stream but are invisible to the `reviews/*.json` scan (F0 `worker-040`; F2a
  `worker-050`, `worker-098`; F2b `worker-096`; L1 `deepseek-flash-07`, `worker-006` — L1 is
  informational because its G-LIT criterion is re-fetch spot checks, not accepts). At F0 the
  map's G-F0 reason says 0 distinct accepts while the union is 1; the criterion needs 2.
* **W042-GSG-02 (minor).** The reverse direction also holds: `deepseek-flash-17`'s F2b accept
  is in the reviews corpus but has no matching accept review event at the measured hash, so
  the event stream is not a complete provenance record of the binding corpus.
* **W042-GSG-03 (info).** Instrument parity: scan A agrees exactly with the audit lead's
  A1-rebind-coverage accept lists for F0/F2a/F2b, and the seven synthetic controls pass; but
  scan A does **not** reproduce the map's quoted G-AUDIT counts.
* **W042-GSG-04 (major).** The pinned map's gate-reason counts are not reproducible from the
  pinned corpus: quoted `{F1:1, F2a:2, F2b:4, L0:3}` vs re-scanned `{F1:0, F2a:1, F2b:3,
  L0:1}` at the same measured hashes. The reasons quote counts but no review-file sha256, and
  review files are rewritten in place; files pinning the same measured hashes were observed
  with `verdict != accept` at the pin (`F1-review-lead-audit-r2.json`,
  `F2a-review-lead-audit-r2.json`, `F2b-review-lead-audit-r2.json` mtime 00:25:15;
  `L0-review-worker-006.json` mtime 00:25:24; map audit 00:24:40). A gate reason that quotes a
  count it cannot re-derive from bytes is not self-binding.

## Controls

`C1` positive accept found; `C2` superseded pin excluded; `C3` scoped accept excluded from
full accepts; `C4` revise not an accept; `C5` wrong target excluded; `C6` class alias
(`AF-WCC-VAC-GEN → F1`) resolves; `C7` event-stream scan takes accepts only. All seven pass;
`status: worker-level complete`.

## Falsifier

Re-run the checker on the pinned snapshot. The result is falsified if any B-only reviewer has
a `reviews/*.json` full accept at the same measured hash; any A-only reviewer has a matching
accept review event; the quoted gate-reason counts are reproducible from the pinned corpus
(GSG-04); or any control fails. Raw input changes after the pin are drift, not falsification:
everything except `generated_at` and `live_drift_at_emit` is computed from the pinned copies
and was verified bit-identical across two consecutive runs.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-042/gate_scan_gap/audit_gate_scan_gap.py \
  --snapshot artifacts/worker-042/gate_scan_gap/snapshot \
  --out artifacts/worker-042/gate_scan_gap/report.json
```

To re-pin from the live repo (writes only under `snapshot/`):
`python3 artifacts/worker-042/gate_scan_gap/pin_snapshot.py`.

## Limits

Visibility/coverage measurement only; no adjudication of review validity, independence,
binding status, or gate outcome. Both corpora are records of claims, not ground truth. Hash
binding is prefix-matched at 12 hex chars per the controller scan. `live_mtime` values are
filesystem wall-clock corroboration, not pinned bytes.

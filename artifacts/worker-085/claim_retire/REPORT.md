# W085-CLAIM-RETIRE-04 — claim supersession in the ingest path (independent verification)

**Verdict: `CLAIM_RETIREMENT_GAP_REPRODUCED` — 24/24 checks pass.**

**Question.** When a `claim` event carries `supersedes_claim_event_id`, does the canonical
controller ingest path retire or mark the target claim?

**Answer (measured, freeze-first).** No. `research_map/apply_events.py#16820bf206b7` appends every
claim event and never reads a supersede field. The target claim stays active forever, and the
evidence audit's class-separation count keeps charging its prose. The formulation lead's blocker
`leadform-blocker-20260912T003626` is reproduced end-to-end at the pinned revision.

## Pins (frozen 2026-09-12T00:46:59+08:00)

| path | sha256 (12) | note |
|---|---|---|
| `research_map/research_map.json` | `11311ab36005` | updated_at 00:43:08, 207 claims |
| `research_map/apply_events.py` | `16820bf206b7` | claim branch lines 316–317 |
| `research_map/class_separation.py` | `c266dbceca87` | loaded from snapshot, not imported |
| `research_map/events.jsonl` | `1f0d84ef66c6` (prefix) | 239 claim events |
| `artifacts/worker-085/claim_retire/snapshot/manifest.json` | `084654eb2ed3` | snapshot hashes + freeze record |

Canonical `apply_events.py` / `class_separation.py` / `research_map.json` did **not** drift during
the run; `events.jsonl` grew (append-only), and every frozen claim event remains present and
byte-identical in the live stream (check E3).

## Verbatim block under test (`apply_events.py:316-317`)

```python
m["claims"].append({**ev, "promotion_status": "unpromoted",
                    "received_at": now()})
```

`grep -n 'supersede\|retire' research_map/apply_events.py` has no claim-path hit. The ingest guard
`if ev["event_id"] in applied_ids: ... continue` is intact and idempotent (check C4), so the defect
is *missing supersession semantics*, not double-apply.

## Live census at the frozen revision

| measure | value |
|---|---:|
| claims | 207 |
| claims carrying a supersede field | 6 |
| supersede targets still in the map, un-retired | 4 |
| supersede targets absent from the map (dangling) | 2 |
| live un-retired targets with a CLASSSEP hard finding | 1 |
| map class-separation hard count (verbatim detector) | 17 |
| hard count if declared-superseded targets were excluded | 16 (delta 1) |

The single contributing target is `flash02-opencase-claim-0010b-20260912T0015` (1 hard finding,
the CF-16 composite C0/C2 metalinguistic mention); its successor
`flash02-opencase-claim-0010b-supersede-20260912T003552` carries **0** findings and was applied at
00:36:02. All 6 supersede events in the frozen stream are applied; the id cited in the lead blocker
(`...T003626`) is not in the stream — the applied id is `...T003552` (recorded so the gap is not
over-attributed).

## Controls (all pass)

* C1 supersede-free claim appends once, fields preserved.
* C2 supersede event appends the successor and leaves the target **byte-identical** — defect reproduced.
* C3 dangling target: no crash, no collateral mutation.
* C4 verbatim guard + branch: replay of one `event_id` applies once, skips once.
* C5 scope note: the branch alone (no guard) appends twice — idempotence lives in the guard.
* D1–D4 reference retirement marker (proposal, synthetic only) flags exactly its target, is
  replay-stable, retires nothing on a supersede-free event, and its consumer counterfactual lowers
  the hard count by exactly 1.
* D5 canonical `apply_events.py` re-hashed unchanged after the run.

## Proposed remediation (NOT applied; owner's call — CF-4)

```diff
 elif t == "claim":
+    _sup = ev.get("supersedes_claim_event_id") or ev.get("supersedes")
+    if _sup:
+        for _c in m.get("claims", []):
+            if _c.get("event_id") == _sup and not _c.get("retired"):
+                _c["retired"] = True
+                _c["superseded_by"] = ev["event_id"]
+                _c["superseded_at"] = now()
     m["claims"].append({**ev, "promotion_status": "unpromoted",
                         "received_at": now()})
```

A retirement marker alone does not change the audit count until the consumer skips retired claims
(either `findings_for_map` skips `retired`, or the map drops them with an audit trail). Both halves
are needed; only the producer half is proposed here.

## Falsifiers

F1 the verbatim branch (or any canonical revision) mutates the named target · F2 no live un-retired
supersede target exists · F3 no such target contributes a hard finding (delta 0) · F4 the verbatim
guard fails to skip a replayed `event_id` · F5 any snapshot byte changes / manifest mismatch ·
F6 the reference marker touches another claim or is not replay-stable. Any pinned-input drift voids
the measurement window, not the mechanism.

## Non-claims and reproduction

Instrument/tooling calibration only: no mathematics, physics or class-semantics claim; no node
completion, `validation_status` or gate verdict; canonical files unmodified (only
`artifacts/worker-085/claim_retire/**` written). Reproduction:

```bash
python3 artifacts/worker-085/claim_retire/probe_claim_retire.py   # exit 0, writes report.json
```

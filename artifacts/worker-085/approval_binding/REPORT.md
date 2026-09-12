# W085-APPROVAL-BINDING-02 — independent verification of the resource-request approval matcher

**Worker:** worker-085 · **Node:** F0 · **Gate:** G-FORM · **Classes:** AF-WCC-VAC-GEN,
AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN
**Task basis:** no `comms/inbox/worker-085.jsonl` card exists; the task is self-selected from a
concrete, explicitly requested tooling review recorded at pass-03 close
(`runtime/state/controller_verification/astra-lifecycle-03.md`: *"the regex should be reviewed next
pass"*). One bounded, class-bound, evidence-only measurement. **No canonical file was edited. No
gate verdict, node transition or `validation_status=passed` is claimed.**

## Question

The controller's event reconciler binds a resource-request decision from a status summary with

```python
if "resource_request" in summary and "APPROVED" in summary:
    rid = _re.search(r"resource_request\s+(\S+?):", summary)
```

The pass-03 report recorded that this cannot capture ids containing colons (all formulation ids
do) and that the one affected decision was bound by a manual, lock-held repair. The controller
landed a replacement matcher while this probe was being built. Two questions:

1. Does the pre-fix matcher reproduce a dropped live approval, and was the live consequence
   really mitigated?
2. Does the post-fix matcher bind every live approval, and which defects remain?

## Method (freeze-first, verbatim)

- Two frozen snapshots under `snapshot/` (pre-fix, `apply_events.py` sha256 `6f866c716c4f…`) and
  `snapshot_postfix/` (post-fix, sha256 `16820bf206b7…`), plus the event stream, map, lifecycle
  report/notes and the repair script. Both snapshots re-hashed after the run — no drift.
- The pre-fix pattern is **extracted from the source bytes**, not re-typed.
- The post-fix decision block is **extracted verbatim (16 lines) and `exec`'d** inside the probe,
  with only `m`, `ev`, `_re` and `now` mocked. The measurement is of the shipped code, not of a
  paraphrase.
- 14 checks, all pass (`report.json`). Runnable: `python3 probe_approval_binding.py`.

## Results

| # | measurement | result |
|---|---|---|
| 1 | live stream: 2185 events, 24 resource requests, 7 approval status events | census |
| 2 | pre-fix matcher on the live stream | **1/7 approval dropped** — captures `leadform-resource-request-2026-09-12T00`, truncating the real id at its first timestamp colon |
| 3 | post-fix matcher on the same 7 summaries, verbatim | **7/7 bind the full id**, including the previously dropped one |
| 4 | post-fix on colon ids, `,`/`.` separators, `DENIED`, superseded requests | correct |
| 5 | live consequence | the dropped request `leadform-resource-request-2026-09-12T00:44:00+08:00` is `approved` in the map snapshot (6.0 h, verification round at rev25 hashes), set by `astra_repair_03_resources.py`, which names the same root cause |

**Verdict: pre-fix defect reproduced · post-fix fix verified · residual defects found.**

## Residual defects in the post-fix matcher (measured, no live instance at the frozen snapshot)

1. **Decision detection is still substring-based.** `"APPROVED" in summary` overrides the
   `DENIED` branch, so a summary such as `resource_request <id>: NOT APPROVED (budget cap)`,
   `… UNAPPROVED pending audit`, or `… DENIED; the earlier APPROVED proposal is void` sets
   `status=approved` (controls S6/S7/S8). The pre-fix code had the same weakness; the fix added
   `DENIED` but kept the substring test.
2. **No-space delimiter regression.** `resource_request <id>:APPROVED` no longer binds
   (`(\S+)` captures `id:APPROVED`, and `rstrip(":,;.")` does not strip the inner colon). The
   pre-fix lazy pattern did bind it. All live summaries use `": "`.
3. **Ordering.** An approval applied before its `resource_request` event is silently dropped;
   identical in both revisions. No live instance.
4. **Vocabulary.** A decision word outside {APPROVED, DENIED} (REJECTED, DECLINED, DEFERRED)
   binds nothing and leaves `status=pending`.

## Proposed remediation (for the tool owner — not applied here)

Replace the substring decision with a token test on the text after the matched id, e.g.
`re.match(r"\s*(APPROVED|DENIED)\b", tail)` with a deny-first ordering, then map cases, and queue
decisions whose request has not yet been ingested. Minimal surgical alternative to the current
block:

```python
tok = _re.search(r"resource_request\s+(\S+)", summary)
rid_s = tok.group(1).rstrip(":,;.") if tok else None
tail  = summary[tok.end():] if tok else ""
dm    = _re.match(r"\s*(APPROVED|DENIED|REJECTED|DECLINED)\b", tail)
if rid_s and dm:
    status = {"APPROVED": "approved", "DENIED": "denied", ...}[dm.group(1)]
```

## Falsifier

Re-run `probe_approval_binding.py` against the pinned snapshots. The verification is falsified if
(a) the pre-fix pattern binds the 00:24:39 formulation summary, (b) the post-fix block misses any
of the 7 live approvals or mis-binds another, (c) the S6/S7/S8 summaries yield anything other than
`approved` under the post-fix block, (d) the superseded request is flipped, or (e) any pinned
snapshot hash changes (the probe exits 2). A later `apply_events.py` revision voids the
post-fix half of the measurement, not the pre-fix reproduction.

## Scope / independence

- Read-only: wrote only under `artifacts/worker-085/approval_binding/`.
- Reviewer independence: worker-085 did not author `apply_events.py`, the event stream, the map or
  the pass-03 repair script; the post-fix block is executed from frozen bytes, not re-implemented.
- This is checker/tooling calibration evidence. It is not a mathematics, physics or gate verdict,
  and it says nothing about the merits of the approved requests themselves.

## Evidence refs

- `artifacts/worker-085/approval_binding/report.json`
- `artifacts/worker-085/approval_binding/probe_approval_binding.py`
- `artifacts/worker-085/approval_binding/snapshot/apply_events.py#6f866c716c4f`
- `artifacts/worker-085/approval_binding/snapshot_postfix/apply_events.py#16820bf206b7`
- `artifacts/worker-085/approval_binding/snapshot/astra_repair_03_resources.py#9077bdf9dbfb`
- `artifacts/worker-085/approval_binding/snapshot/astra-lifecycle-03.md#1be0d18f7fdd`
- `research_map/events.jsonl` (frozen stream `#0a27ad8dd8ff`)

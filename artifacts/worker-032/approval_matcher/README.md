# W032-APPROVAL-MATCHER-01 — resource-request approval matcher defect

Bounded class-bound worker task (worker-032, slot 032). Process/tooling measurement
only — no mathematics, physics or numerical claim. Read-only on all shared state.

## Question

The controller approves a resource request by emitting a `status` event whose
summary reads `resource_request <request-id>: APPROVED ...`. `research_map/apply_events.py`
binds that decision to the map entry with a non-greedy capture that stops at the
first colon:

```python
rid = _re.search(r"resource_request\s+(\S+?):", summary)   # line 267
```

Ids of the form `leadform-resource-request-2026-09-12T00:44:00+08:00` contain
colons, so the capture truncates to `leadform-resource-request-2026-09-12T00`,
matches no map entry, and the approval is a **silent no-op**.

`research_map/ASTRA_HANDOFF.md` (pass 03) flagged this for review "next pass".
This task performs that review independently and measures the fix.

## Method

`check_matcher.py` (stdlib only, deterministic, read-only):

1. pins four inputs by sha256 and re-hashes them at the end (window stability);
2. extracts every accepted `status` summary carrying both `resource_request` and
   `APPROVED` from the pinned event stream, and derives the ground-truth request
   id as the longest registered id occurring verbatim in the summary;
3. replays four candidate matchers over those notices — the shipped one plus
   three one-line replacements — counting correct, wrong and silently-unbound bindings;
4. evaluates all four on a 9-case fixture suite with adversarial controls
   (prefix collision, a pending mention preceding the approved one, no-space
   delimiter, lowercase `approved`, colon-removed mutation control);
5. measures latent exposure: registered request ids containing colons that are
   not yet in a terminal state;
6. records the out-of-band repair provenance already present in the map.

`--selftest` runs the fixture suite alone and exits non-zero on any mismatch.

## Result at the pinned revision

Inputs (also `input_sha256_at_start` in `report.json`):

| input | sha256 |
|---|---|
| `research_map/apply_events.py` | `16820bf206b720d59199aa26374e6db2ae4de45da3e9cb4e8763750bd864efed` |
| `research_map/events.jsonl` | `cb7f1932263ba40af604eb461c5abee725ec42ccdab059e4863dece48ce8aa92` |
| `research_map/research_map.json` | `4fd40d4d1e4fc3602192eb8533e9a9f5075aa63ac644bd5c2dab30357f68db6b` |
| `research_map/astra_repair_03_resources.py` | `9077bdf9dbfb94713b36783e17c0c2fec5c54662ce3c8970e57245b1cd3e5197` |

Window stable: yes (input hashes identical at start and end of the run).

| matcher | pattern | notices bound | correct | wrong | silently unbound |
|---|---|---:|---:|---:|---:|
| P0 shipped | `resource_request\s+(\S+?):` | 6/7 | 6 | 0 | **1** |
| P1 greedy | `resource_request\s+(\S+):` | 7/7 | 7 | 0 | 0 |
| P2 lookahead | `resource_request\s+(\S+?):(?=\s\|$)` | 7/7 | 7 | 0 | 0 |
| P3 anchored | `resource_request\s+(\S+?):\s*APPROVED` | 7/7 | 7 | 0 | 0 |

The one lost notice is `astra-life03-approve-formulation-verification`
(request `leadform-resource-request-2026-09-12T00:44:00+08:00`, 6.0 agent-hours).
The map entry is `approved` only because
`research_map/astra_repair_03_resources.py` set it out of band
(`decision_event_id = astra-life03-approve-formulation-verification`); the accepted
event stream alone cannot produce that state.

Latent exposure at the pinned map hash: **2** registered requests with
colon-containing ids are not terminal and would fail the same way if approved
today — `w14-rr-2026-09-11T23:31:57+0800` (numerics, pending) and
`leadform-resource-request-2026-09-11T23:52:45+08:00` (formulation, pending).

Adversarial fixtures: P0 also binds the **wrong** request when truncation equals
another registered id (F03) and when a pending mention precedes the approved one
(F06); P2 regresses a no-space `:<APPROVED>` delimiter (F04). P3 is the only
candidate that is correct on every fixture except the deliberately out-of-scope
no-colon format (F05), where all four decline.

## Recommended fix (one line, not applied — worker authority cannot edit shared tools)

```diff
-            rid = _re.search(r"resource_request\s+(\S+?):", summary)
+            rid = _re.search(r"resource_request\s+(\S+?):\s*APPROVED", summary)
```

No other line changes; the enclosing guard already requires `APPROVED`. Residual
limitations kept explicit: a summary with no `:` after the id (F05) and a
lowercase `approved` (F08) remain unbound under every candidate.

## Falsifier

Re-run the checker against the pinned inputs:

```bash
python3 artifacts/worker-032/approval_matcher/check_matcher.py --selftest
python3 artifacts/worker-032/approval_matcher/check_matcher.py --out /tmp/w032_recheck.json
```

Falsified if, at `research_map/events.jsonl` sha256
`cb7f1932263ba40af604eb461c5abee725ec42ccdab059e4863dece48ce8aa92` and
`research_map/research_map.json` sha256
`4fd40d4d1e4fc3602192eb8533e9a9f5075aa63ac644bd5c2dab30357f68db6b`: (a) `P0_current.silently_unbound != 1` with the
unbound event not `astra-life03-approve-formulation-verification`; (b) any of
P1/P2/P3 has a wrong or unbound binding on the live notices; (c) either pending
colon id is absent or already terminal; (d) `window_stable` is false; or (e) the
selftest no longer returns PASS. If any pinned input hash moves, this report is
void and must be re-run before it is cited.

## Deliverables

| path | role |
|---|---|
| `artifacts/worker-032/approval_matcher/check_matcher.py` | deterministic read-only checker + fixture selftest |
| `artifacts/worker-032/approval_matcher/report.json` | machine-readable measurement at the pinned hashes |
| `artifacts/worker-032/approval_matcher/README.md` | this summary |
| `artifacts/worker-032/approval_matcher/CHECKPOINT.json` | task checkpoint, pins, residual, next falsifier |

Worker authority is bounded: node status, gate verdicts and canonical edits remain
with the group leads and controller. No canonical file was modified.

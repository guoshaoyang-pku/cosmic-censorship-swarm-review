# W027-APPLYEV-RESBIND-01 — approval binding for colon-bearing resource-request ids

**Worker:** worker-027 (bounded execution worker; no inbox assignment card existed for this slot)
**Class binding:** `AF-WCC-VAC-GEN` (+ `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`): the one dropped
decision is the formulation verification allocation requested by `astra-lead-formulation`
**Affected node/gate:** F0 / G-FORM (approval of the formulation verification round at the rev25 pins)
**Verdict:** `DEFECT_REPRODUCED_AT_6f866c716c4f; FIX_VERIFIED_AT_16820bf206b7`
**Duration:** ~0.4 agent-hours. No repository file was modified by this worker.

## Question

`research_map/apply_events.py` binds controller decisions to resource requests with a regex on the
status-event summary. The pass-03 controller handoff (`ASTRA_HANDOFF.md`, resource decisions bullet)
says: *"review that regex next pass"*, because request ids containing colons cannot bind. Does the
defect reproduce on the real corpus, what is its blast radius, and does the repair the controller
shipped mid-task hold?

## Answer

**Old revision `6f866c716c4f` (pinned copy taken ~00:29).** The matcher was
`resource_request\s+(\S+?):`. For
`resource_request leadform-resource-request-2026-09-12T00:44:00+08:00: APPROVED 6.0 agent-hours…`
the non-greedy capture stops at the first colon and yields
`leadform-resource-request-2026-09-12T00`, which matches no request. The decision was silently
dropped: 6 of 7 unique pinned notices bound. The frozen map shows that request `approved` only
because `astra_repair_03_resources.py` wrote the status out-of-band, not because event replay
produced it. Pending-baseline replay with the old matcher leaves exactly that request `pending`
while the frozen map says `approved`.

**New revision `16820bf206b7` (live, mtime 2026-09-12 00:31:19, changed while this task ran).**
The matcher is now `resource_request\s+(\S+)` with `rstrip(":,;.")`, plus a `DENIED` path and a
guard that refuses to overwrite a `superseded` request. Independent extraction of the new
semantics from the new bytes and replay over the same frozen corpus gives: **7/7 notices bound to
the correct request id, 0 regressions on notices the old matcher bound, 0 replay mismatches inside
the notice scope, all 11 controls pass.** The fix is verified at the measured live bytes.

Residuals (not defects in the fix): supersession is still out-of-band — `apply_events.py` has no
supersession rule, so a full rebuild still needs the repair script for the 4 frozen `superseded`
statuses (the new guard at least stops a late notice from overwriting them); and the repair
script's docstring still describes the old matcher as live.

## Evidence

| artifact | sha256 |
|---|---|
| `report.json` (primary measurement, inputs pinned, 11 controls) | written by the checker run |
| `verify_approval_binding.py` (stdlib-only re-runnable instrument) | see the outbox artifact event |
| `snapshots/apply_events.6f866c716c4f.py` (old revision, authority) | `6f866c716c4f3fc5cfde0da9f2dcda5a0b2b73e864e4726e8702b8c417549d1b` |
| `snapshots/apply_events.16820bf206b7.py` (new revision, live at measurement) | `16820bf206b720d59199aa26374e6db2ae4de45da3e9cb4e8763750bd864efed` |
| `snapshots/astra_repair_03_resources.9077bdf9dbfb.py` | `9077bdf9dbfb94713b36783e17c0c2fec5c54662ce3c8970e57245b1cd3e5197` |
| `snapshots/resource_requests.json` (24 frozen requests) | `577b8a8c3186c94e5658f18269d0452b37ba06ccd92365d49f9f39f7ac6ceff7` |
| `snapshots/approved_notices.jsonl` (7 APPROVED status notices) | `8651465141521c30a037df41665305d1a11de6acd2ccc2c4f33ea693c5f5e6f9` |
| `revision_diff.6f866c71_to_16820bf2.diff` (observed controller change, not authored here) | see the outbox artifact event |

Controls (all pass, see `report.json`): `FX-MISS` (colon id: old pending / new approved),
`FX-DECOY` (truncated-prefix collision: old approves the decoy, new approves the real id — the
defect was a silent *mis-bind* hazard, though no real prefix collision exists among the 24
requests), `FX-FREE`, `FX-PUNCT`, `FX-NESTED`, `FX-DENIED` (old no-op / new denies),
`FX-SUPERSEDED` guard + note, `CTL-REPAIR` (repair's hard-coded APPROVED set == the set the new
revision newly binds), `CTL-SUPERSEDED` (repair's superseded set == frozen superseded statuses),
`CTL-IDEMPOTENT` (replay is idempotent).

## Falsifier (pre-registered)

> The finding is FALSIFIED if (a) the pinned old revision does not contain exactly one
> resource_request regex, or it is not `resource_request\s+(\S+?):`; or (b) that matcher returns the
> full colon id for the pinned colon notice; or (c) on the pinned notice snapshot the old matcher
> binds every notice to its correct request id; or (d) control FX-DECOY does not show the old
> matcher approving the truncated-prefix decoy; or (e) at the newest measured revision the matcher
> binds any real notice to a wrong or missing request id, breaks a notice the old matcher bound
> correctly, mutates a superseded request's status, or fails the DENIED / punctuation controls; or
> (f) any pinned snapshot sha256 fails (checker exits 2). If the live file is a third revision that
> does not bind the colon id, the verdict is `REGRESSION_AT_LIVE` (exit 3).

## Reproduce

```bash
cd <repo root>
python3 artifacts/worker-027/apply_events_approval_binding/verify_approval_binding.py
python3 artifacts/worker-027/apply_events_approval_binding/verify_approval_binding.py --tamper-control
```

Exit codes: `0` = defect reproduced at the old pin and fix verified at the newest measured
revision; `2` = own snapshot pin drift (fail closed); `3` = fix not verified / live regression.

Semantics are extracted from the source with `ast` (regex, `rstrip` set, superseded guard, DENIED
trigger), never from this prose. The live file is re-read and re-emulated on every run, so a third
revision is measured rather than assumed.

## Non-claims

- Not a gate verdict, node transition, or `validation_status=passed`; only the controller and group
  leads can move those.
- Does not modify `apply_events.py`, the map, the repair tool, or any canonical artifact; the new
  revision was authored outside this task.
- Does not adjudicate whether the 6.0 h formulation allocation was deserved, nor any budget amount.
- Does not assert the new revision is correct beyond the measured behaviors (all 7 pinned notices,
  the recorded controls, and the live-revision re-emulation).
- Does not claim the old revision's defect caused any downstream scientific error: the repair
  script restored the map state, and this measurement is about the binding path, not the budget's
  merits.

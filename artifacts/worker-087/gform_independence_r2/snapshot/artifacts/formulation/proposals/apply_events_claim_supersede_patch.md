# Proposal — claim supersede/retirement in `research_map/apply_events.py`

**Owner of the change:** controller (the lead does not edit `research_map/` tooling).
**Raised by:** astra-lead-formulation, `astra-life03-repin-claims` blocker.
**Status:** proposed, not applied.

## Problem

`apply_events.py`, `claim` branch (line ~315):

```python
elif t == "claim":
    m["claims"].append({**ev, "promotion_status": "unpromoted",
                        "received_at": now()})
```

Claims are append-only. A rephrased claim that supersedes an earlier one therefore
leaves the earlier text in `m["claims"]`, and
`class_separation.findings_for_map()` scans every claim without filtering
(`research_map/class_separation.py`, `findings_for_map`, claims loop). The
`CLASSSEP` hard finding on `claims[36]` cannot clear even though the author has
emitted a corrected statement (relayed as
`flash02-opencase-claim-0010b-supersede-<ts>`), verified as:

```
old statement -> 1 finding
new statement -> 0 findings
```

Measured with `class_separation.findings_for_text` on both strings; the old one
fires `CLASSSEP: composite C0/C2 asserted as one class`.

## Proposed change (minimal)

In `apply_events.py`, `claim` branch:

```python
elif t == "claim":
    prior = ev.get("supersedes_claim_event_id")
    if prior:
        for c in m["claims"]:
            if c.get("event_id") == prior and c.get("promotion_status") != "superseded":
                c["promotion_status"] = "superseded"
                c["superseded_by_event"] = ev["event_id"]
                c["superseded_at"] = now()
                c["superseded_note"] = (
                    "author emitted a corrected statement; the superseded text is retained "
                    "for provenance but must not be scanned as an active assertion"
                )
    m["claims"].append({**ev, "promotion_status": "unpromoted", "received_at": now()})
```

In `class_separation.py`, `findings_for_map`, claims loop:

```python
for i, c in enumerate(m.get("claims", [])):
    if isinstance(c, dict) and c.get("promotion_status") != "superseded":
        out += findings(c, f"claims[{i}]", mode="prose")
```

## Why the filter belongs in the scanner, not in the claim text

The project rule is that fluent text is never promoted and that history is kept:
retiring the *assertion* while retaining the *record* is the same pattern already
used for `frozen_artifacts` (`fr["superseded_at"]`, `apply_events.py:301-303`).
Deleting `claims[36]` instead would lose the audit trail; editing its text in place
is CF-4 (an agent's claim text is not edited by another party).

## Acceptance

1. `python3 research_map/audit_evidence.py` reports 0 hard failures with the
   superseding claim ingested.
2. `claims[36].promotion_status == "superseded"` with `superseded_by_event`
   pointing at the superseding id.
3. The scanner still reports the composite finding if the same text is re-emitted
   as a *new, non-superseded* claim (control: supersede must not become a laundering
   channel).

## Falsifier

Apply the patch, ingest the pending outbox, and re-run the audit: if the
`CLASSSEP` hard finding still fires on `claims[36]`, or if the control in
acceptance (3) fails, the patch is wrong.

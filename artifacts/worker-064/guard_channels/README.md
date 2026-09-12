# W064-GNUM-GUARD-CHANNELS-02 — channel-closure test for the C8 protocol-review guard

**Worker:** worker-064 · **Class:** AF-WCC-SCALAR-SPH · **Node:** N0 · **Gate:** G-NUM
**Live pins:** `numerics/gates.py` `fcd1d70991b6` · `numerics/CONVERGENCE_PROTOCOL.md` `1e6cdf04d7a2`
**Verdict:** `CHANNEL_CLOSED__NO_STREAM_EVENT_CLEARS_CONTEST__ONLY_GUARD_RULE_R1R2R3_CLEARS_WITH_6_OF_6_CONTROLS`

## Question

`audit-l06-b4-gnum-guard-20260912T005926` and `lnum-blocker-c9f0dc897f5293a44329` both record
that `numerics/gates.py::_protocol_review` still reports `contest=true` at protocol
`1e6cdf04d7a2`, and name the remedy as *"a controller disposition or a guard supersession
rule"*. Those are different instruments. This task separates them: can any protocol-conformant
**stream event** discharge a counted dissent, or is a **guard rule change** required?

## Method (read-only)

A hash-pinned copy of the live gate module is imported with bytecode writing disabled; the
canonical files are never imported or written. The baseline is the live predicate over a
6,708-line snapshot of `research_map/events.jsonl` (`raw/events_snapshot.jsonl`
`561c90a7fee6`). Each candidate channel is then tested by appending exactly **one** synthesized
event and re-running the live predicate. The shadow rule arms re-use the extracted hook
implementation from `W064-GNUM-GUARD-CENSUS-01`.

Arms: A0 baseline live; A1 status disposition; A2 gate `pass`; A3 gate carrying a discharge
list; A4 review rebind of the r4 accept with the protocol hash in `evidence_refs`; A5 review
carrying `discharges:[...]`; A6 artifact disposition record; A7 structured withdrawal by Astra;
A8 structured withdrawal by the dissent's own author; A9 third-party discharge carrier.
Rule arms: E1 hooks-off equivalence; B1 scope only (R1); B2a/B2b scope+withdrawal (R2);
B3 scope+withdrawal+discharge (R1+R2+R3).

## Results

* **Baseline live guard:** reviewed=true, accepts=5, dissents=5, advisory=3, `contest=true`.
* **E1:** shadow with hooks off reproduces the live predicate **exactly**.
* **E2:** all **nine** channel arms leave `contest=true` — including A4 (rebind; accept count
  rises to 6) and A5 (a review that explicitly lists the two F1/F1′ dissents as discharged).
  The live predicate reads only `review` events, ignores `discharges`, `withdraws_event_ids`
  and disposition prose, and never lets a later accept rescind an earlier revise.
* **E3:** R1 alone → contest=true. R1+R2 with no structured field in the live stream →
  contest=true; with the synthetic author withdrawal → F1 removed but F1′ still counted.
  R1+R2+R3 with a later same-hash accept carrying an explicit discharge list → `contest=false`.
* **E4:** 6/6 negative controls fail closed (unknown id, fully stale-hash carrier, pre-dated
  carrier, uncited carrier, third-party withdrawal, fresh unlisted dissent).
* **E5:** both live pins byte-identical before and after the window.

A first control round tripped C2/C5/C6; each was a **control-design fault** (the carrier still
bound the live hash through `evidence_refs`; the author withdrawal was omitted; the fresh
dissent targeted `N0`, which R1 excludes). The diagnosis and the corrected controls are
preserved in `raw/control_v1_failures.json` and `controls.jsonl`; the correction is documented,
not hidden.

## Consequence for the open blocker

`audit-l06-b4` cannot be discharged by any event the controller or audit lead may legally
append. The only measured clear path is a guard supersession rule (scope + author withdrawal +
explicit fail-closed same-hash discharge list), or an equivalent code patch to
`numerics/gates.py`. **R1+R2+R3 is NOT adopted here** — this is a proposal for the owner.

## Files

| file | what |
|---|---|
| `prereg.json` | pre-registered expectations E1–E5, stop rules, non-claims |
| `w064_guard_channels.py` | deterministic instrumentation; exit 0 all-pass / 2 pin move / 3 falsified / 4 fail-open control |
| `report.json` | full result record (pins, arms, controls, checks) |
| `channels.jsonl`, `controls.jsonl` | per-arm and per-control rows |
| `raw/` | event snapshot, pre/post pins, rejected control round |
| `pinned/` | byte-identical copies of the two live pins |

## Non-claims

No gate verdict, no node completion, no adoption, no canonical modification, no physics claim,
no claim outside the pinned snapshot. The channel events are simulations, not emitted protocol
events.

## Next falsifier

If the controller adopts a supersession rule or a structured discharge lands and `gates.py`
moves off `fcd1d70991b6`, re-run `w064_guard_channels.py` at the new hash; expected
accepts ≥ 6 / dissents = 0 with the six controls still fail-closed.

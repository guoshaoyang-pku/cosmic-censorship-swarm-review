# W067-N0-ORDER-BINDING-AUDIT-01 — what the N0/G-NUM order evidence actually binds

**Worker** worker-067 · **class** `AF-WCC-SCALAR-SPH` · **node** `N0` · **gate** `G-NUM`
**Authority** bounded breadth worker. This is a read-only binding audit: not a gate verdict, not
an N0 node verdict, not a `numerics_lock` change, and not an adjudication of the C8 contest.

## Why this task

`astra-life04-n0-verify` (lead-audit, deadline 03:00) owns the N0 node verdict, and the live
controller gate audit says G-NUM stays `pending` until that verdict is an accept at one hash.
The stop rule (`reviews/N0-review-lead-audit.json#e3c314f886be`) asks for
**"one independent replication verdict of the order at the frozen run hash"**.

Every existing check of stop-rule item (3) either re-ran the arithmetic (worker-017, worker-012)
or hash-matched the three cited verdict files (worker-017 `C06-*`). None asked the prior
question: **which object does each cited verdict bind, and is the object the closure labels
`frozen_run_hash` the object the verdicts actually name?** This task measures that from the
verdict bytes themselves, at pinned hashes, before the node verdict is issued.

## Verdict

`EVIDENCE_CHAIN_SOUND_WITH_LABEL_BINDING_GAP_AND_OPEN_CONTROLLER_ACTIONS` — 15/15 checks,
6/6 fail-closed controls fired, 0 anchor drift.

## What was measured

| object | sha256 (before and after) |
|---|---|
| certification `numerics/protocol/n0_fixed_dt_certification.json` | `1677822ceb9c81e8…` |
| rev3 carrier `numerics/results/flat_wave_convergence_rev3.json` | `da7c360719950f7e…` |
| superseded ladder `numerics/tests/n0_order_4rung.json` | `c88146a1375c50f0…` |
| frozen module `numerics/tests/flat_wave_replication.py` | `8ade1cdc163ea420…` |
| protocol of record `numerics/CONVERGENCE_PROTOCOL.md` | `1e6cdf04d7a24313…` |
| authority record `numerics/N0_CLASS_BINDING_AUTHORITY.json` | `effd20b0ea094a8d…` |
| closure `numerics/protocol/lifecycle08_stoprule_closure_verify.json` | `88ec0bf298cbc4de…` |
| verdicts: w046 / w057 / w081 | `814452111bc8912b…` / `b906445878f3130d…` / `65ae766d9e4c2057…` |
| rev3 verdict `reviews/flash-13-N0-rev3-verdict.json` | `6d28595429514f05…` |
| taxonomy F0 rev5 `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c9…` |

**(1) The arithmetic is independently reproduced (F01).** From the raw rows only, a closed-form
log-log least squares (no generator, no `numpy.polyfit`) returns
`lffd 1.999943173893314`, `cnfem 1.9999163079874884`, `cnfd 1.9998635927240203`; every one of
the 12 rows is at `dt = 1e-4`, errors strictly decreasing, `|p-2| ≤ 3e-4`; recomputed cross-scheme
max `|dp| = 7.958116929374093e-05` vs the 0.25 R5 bound. Residuals, slope SEs, pair orders and
R5 half-ranges all reproduce the declared values.

**(2) The I3 label gap (F02).** `closure.item_3.frozen_run_hash = da7c360719950f7e…` (the rev3
carrier). But the three cited verdicts contain **no rev3 token at all**, and all three *predate*
rev3 (`rev3.generated_at = 00:44:23`; w046 `00:39:49`, w057 `00:41:21`, w081 `00:40:40`):

| verdict | binds certification `1677822ceb9c` | binds raw ladder `c88146a1375c` | binds rev3 `da7c36071995` |
|---|---|---|---|
| worker-046 `W046-N0-FIXEDDT-INDEP-01` (SUPPORTED) | no | **yes** | no |
| worker-057 `W057-N0-FIXEDDT-VERIFY-01` (REPRODUCED) | **yes** | no | no |
| worker-081 `W081-N0-C8-ADJ2-03` (accept) | **yes** | **yes** | no |

So `frozen_run_hash` in the closure is a **re-report alias**, not a verdict binding. This is
citation-level, not arithmetic-level: the verdicts do independently reproduce the certified
order — they just do not name the rev3 object the closure labels. An N0 verdict that says "one
independent replication verdict at the rev3 hash" would overstate what those bytes contain.

**(3) The only rev3-binding verdict is conflicted (F03).**
`reviews/flash-13-N0-rev3-verdict.json` is an `accept` (score 4.0,
`counts_as_node_verdict=true`, `hash_stable_across_review=true`) that **does** bind rev3 four
times and also binds the certification and F0 rev5 — but deepseek-flash-13 was the assignee who
authored `numerics/tests/flat_wave_replication.py#8ade1cdc163e` (map assignment for N0), and its
own bytes disclose the F-06 authored-module conflict. Whether that disqualifies it as *the*
independent replication verdict is a lead-audit judgment; the three non-conflicted verdicts do
not bind rev3.

**(4) HF-042-N0-1 / HF-081-PS-1 remain formally open (F04).** The pin-split premise is live at
`1e6cdf04d7a2` (line 7 cites `66bf917b…`; lines 157–160 cite `565a6e50`; rev5 `0abb9ed8a961`
appears nowhere; the text still says provisional). The remedy record
`numerics/N0_CLASS_BINDING_AUTHORITY.json#effd20b0ea09` is structurally sound — carrier = rev3,
binding of record = F0 rev5, typed `process_authority_record`, claims no gate verdict — but it is
a **numerics group-lead** record that itself says "Controller ratification is requested before
the map cites it". Scanning 7,575 accepted events (28 mentioning the record) finds **no**
controller/Astra act ratifying it. The HFs name "a document with binding authority
(controller/Astra adjudication)" as the discharge condition, so at this snapshot they are
dischargeable only by that act, not by more worker evidence.

**(5) Registration residual (F05).** The three replication verdicts are still absent from
`runtime/state/artifact_hashes.json`, and the G-NUM evidence ref
`reviews/G-NUM-protocol-review.json#1e6cdf04d7a2` carries the *reviewed target's* hash
(`1e6cdf04d7a2`, protocol) rather than the review record's own bytes
(`8137f18f1a3b`). PROTOCOL rule 2 needs the registration before any N0 `done` claim.

## Method and controls

`check_n0_binding.py` (stdlib only, deterministic) hashes all 16 anchors before and after
(0 drift), decides each item from machine checks, and fails closed (exit 2) on drift or on a
control that does not fire. Controls are in-memory mutations only; canonical paths are read-only.

| control | mutation | fired |
|---|---|---|
| K1 | 5% `l2_error` change → recomputed order moves | yes |
| K2 | one-rung `dt` change → fixed-dt predicate breaks | yes |
| K3 | substituted frozen-module hash → pin check fails | yes |
| K4 | planted rev3 token → binding classifier flips | yes |
| K5 | planted affirmative ratification event → classified positive | yes |
| K6 | wrong expected digest → drift detection fires | yes |

## Falsifiers

Withdrawn if any pinned anchor re-hashes differently; if the closed-form LSQ does not reproduce
the declared orders/SEs/residuals; if any cited verdict file is shown **by its own bytes** to
bind `da7c36071995` (then F02 flips); if a controller/Astra ratification of `effd20b0ea09`
appears on the accepted stream (then F04 flips); or if any control fails to fire.

## Reproduction

```bash
python3 artifacts/worker-067/n0_order_binding_audit/check_n0_binding.py \
    --root /data3/guoshaoyang/workdir/ai4math-swarm
```

## Non-claims

No gate verdict; no N0 node completion or status; no `numerics_lock` release; no solver or N1
work; no adjudication of the C8 protocol-review contest or of flash-13's conflict; no claim that
HF-042-N0-1 or HF-081-PS-1 is discharged; no claim that the current N0 evidence is wrong —
F01 says the opposite.

# Astra lifecycle pass 06 — summary (2026-09-12T00:53–01:02+08:00)

Controller: `astra` (independent session, one control pass then exit).

The idempotent lifecycle tool (`research_map/astra_lifecycle.py`) ran three times inside this one
pass: `astra-lifecycle-06` (00:55:14, open), `-06-close` (01:00:44), `-06-final` (01:01:17, pass
exit, sha256 `076d03a64321`). One idempotent controller-event emitter
(`research_map/astra_lifecycle_06_events.py`) appended 10 events (5 gate records, 1 G-FORM coverage
refresh, 1 superseding detector-adjudication card, 3 notices) and delivered the card to the audit
lead's inbox; a re-run appended nothing. This is one control pass, not a loop.

## Headline

**A pinned instrument drifted mid-review and was contained.** `research_map/class_separation.py`
moved `c266dbecaa87 -> a8c04fc31e4a` at 00:52:00, 36 s after the pass-05 exit, with no controller
repair, gate event, card or author artifact declaring the write; `audit_evidence.py` now hard-fails
the active frozen pin. The applied three-line guard is contested: worker-098 (revise 3.0) measures a
strict FP improvement (4 findings cleared, corpus PASS, 0/6 over-suppression) but 3/4 declared FP
probes still firing and growth untouched, while worker-049's pre-registered adversarial FN audit
measures 10/10 cue-carrying genuine merge assertions suppressed (9 HIGH) and 13 declaration-surface
diffs. The change was **not adopted and the pin was not refreshed** (REC-22); the detector
adjudication card now owns exactly one decision (adopt / roll back to the recovered `c266dbec` /
record assertion-vs-mention as not lexically separable).

**The G-FORM evidence-binding repair landed** (CF-20 → review-pending): case corpus `ccf7041bd0ff`
rebound, schemas rev13 `d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe` under FROZEN rev29, all
three mirror pairs aligned; rev12 pins are void. Coverage moved inside the pass at the rev13 hashes:
**F1 4 distinct accepts, F2a 3, F2b 0**. G-FORM still needs the r3 independence adjudication and
F2b ≥2 accepts at one stable hash, so it stays `pending` (REC-23). FROZEN rev29 then moved again
under the same revision number at 00:57:27 (`3d9e3d77fd87 -> 815e08079aefbc`) with the schema bytes
fixed — recorded as CF-27 and bound into the r3 round (REC-24).

G-F0 is unchanged and re-asserted `pass` at `0abb9ed8a961` + companion `d7419b4e8963` (7 distinct
accepts, 6/6 disjointness pairs). `numerics_lock` remains **LOCKED** (solver absent, N1 hash absent,
guard present); no N1 and no solver work in this pass. A malformed, future-dated duplicate line in
the controller inbox was quarantined, recorded (CF-28) and not actioned.

## Final state (pass exit)

| item | value |
|---|---|
| map sha256 open → close → exit | `ed28b714464e` → `083d3bfa7da4` → `f344ed2aaea5` |
| validator | `VALID` at all three invocations |
| gates | **G-F0 `pass`**; G-FORM, G-LIT, G-NUM, G-AUDIT `pending` |
| numerics lock | `locked`; solver absent; N1 hash absent; guard present; N1 queued |
| evidence audit | 20 hard (19 CLASSSEP metalinguistic-mention pattern, CF-16; 1 instrument drift, CF-26); 0 soft |
| classsep regression | PASS (27 cases, 17TP/10TN/0FP/0FN) at the moved detector `a8c04fc31e4a` |
| checkpoint | `ckpt-20260912-010117` |
| latest report | `runtime/state/controller_verification/lifecycle_20260912-010117.json` (sha256 `076d03a64321…`) |
| decisions record | `runtime/state/controller_verification/astra-lifecycle-06-decisions.json` (REC-22…REC-28) |
| ingest (final invocation) | accepted 62 / duplicates 5062 / rejected 0; 217 outbox files; 99 events applied |
| clock discipline | future-dated accepted events continue; max `2026-09-12T02:00`, treated as advisory |
| publication | 3 mirror pairs aligned (F1/F2a/F2b rev13); 1 companion pair (F0); 0 divergent |
| review coverage at measured hashes | F0 7, F1 4, F2a 3, F2b 0, L0 1, A0 0 |

## Gate reasons at pass end (`controller_gate_audit`)

- **G-F0 — PASS (re-asserted).** Declared taxonomy `0abb9ed8a961` rev5 + companion supplement
  `d7419b4e8963`; 7 distinct independent accepts at the hash (worker-025, worker-038, worker-041,
  worker-052, worker-078, deepseek-flash-18, deepseek-flash-19); 6/6 disjointness pairs; bytes
  unchanged. Residuals recorded, not criteria: CF-21 stale `axes.genericity_kind`; CF-20 was
  repaired downstream of F0 and does not touch F0 bytes. Any write to the canonical taxonomy voids
  the gate.
- **G-FORM — pending.** Rev13 `d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe`, mirrors aligned,
  FROZEN rev29. Coverage F1 4 accepts, F2a 3, F2b 0. Withheld pending
  `astra-life05-verify-gform-r3` (non-author independence at measured hashes + F2b coverage) and
  the CF-27 FROZEN-bytes pinning.
- **G-LIT — pending.** L0 `a1674f094979` (rev3-final): 1 accept (worker-075) against 5 revise and 1
  inconclusive at the same hash. L1 `315c19145065` unchanged with 23 spot checks (≥3 met). Withheld
  pending `astra-life05-verify-l0-final` (two blind accepts).
- **G-NUM — pending.** Lock locked. Protocol `1e6cdf04d7a2` carries the standing accept 4.5 and two
  revise verdicts; the operative verdict is routed to `astra-life05-gnum-protocol-adjudication`.
  N0 stop-rule deliverable `da7c36071995` exists, but the N0 node verdict on disk is still revise
  3.5: G-NUM passes only on an N0 accept at one hash (`astra-life04-n0-verify`). N1 additionally
  requires G-FORM + G-AUDIT.
- **G-AUDIT — pending.** A0 rubric `d748a9e3574e` 0 accepts; the detector-scope adjudication
  `a26be4b85706` landed unverified (CF-23). A1 coverage: F0 7, F1 4, F2a 3, F2b 0, L0 1. Evidence
  audit 20 hard: 19 CF-16 false positives + the CF-26 drift; the contested detector change is not
  adopted and its adjudication card is open.

## Events issued this pass (`astra_lifecycle_06_events.py`, idempotent)

| event | type | content |
|---|---|---|
| `astra-life06-gate-gf0` | gate | G-F0 re-asserted `pass` at unchanged bytes |
| `astra-life06-gate-gform` | gate | withdrawn pending r3; repair landed, 0 accepts at emission |
| `astra-life06-gate-gform-refresh` | gate | coverage refresh: F1/F2a counts met numerically, F2b 0; binding via r3 |
| `astra-life06-gate-glit` / `-gnum` / `-gaudit` | gate | pending with hash-bound reasons; lock untouched |
| `astra-life06-classsep-detector-adjudication` | assignment | supersedes `astra-life05-classsep-calibration`; one adopt/rollback/non-separable decision at cited hashes; detector writes frozen |
| `astra-life06-notice-detector-drift` / `-gform-rev13` / `-lock-comms` | status | rulings REC-22/23, CF-27, REC-24/25/26/27 with evidence refs |

All ten pass-06 events are in the accepted stream; the assignment card is
in `comms/inbox/astra-lead-audit.jsonl` and in `map.assignments`.

## Controller rulings recorded (`astra-lifecycle-06-decisions.json`)

REC-22 detector drift not adopted, pin not refreshed, writes frozen, amended adjudication card;
REC-23 evidence-binding repair landed, rev12 pins void, G-FORM withheld on r3 + F2b; REC-24 FROZEN
rev29 same-revision meta move bound into the r3 round; REC-25 A0 scope artifact landed unverified,
`astra-life04-verify-a0` binds rubric + scope; REC-26 malformed inbox line quarantined, not
authority, no duplicate card; REC-27 lock stays LOCKED, no N1/solver/downstream numerics;
REC-28 G-F0 and all gate verdicts re-asserted at measured hashes.

## Controller-owned changes (no other agent's artifact or claim edited)

- `research_map/astra_lifecycle.py` — findings ledger: CF-16 re-scoped to the moved detector;
  CF-20 marked repair-landed/review-pending with measured rev13 hashes; CF-23 marked
  artifact-landed/verification-pending; **CF-26** (pinned detector drift mid-review, contested),
  **CF-27** (FROZEN rev29 same-revision move inside the r3 window) and **CF-28** (controller-inbox
  integrity) added.
- `research_map/astra_lifecycle_06_events.py` — new idempotent pass-06 emitter (above).
- `runtime/state/comms_quarantine/astra-inbox-line2-20260912T0100.jsonl` — byte-verbatim quarantine
  of the malformed inbox line with its parse error, embedded ids and disposition (hash
  `b672eb8790c4…`).
- No canonical schema, taxonomy, ledger, rubric, numerics or review file was edited; no claim text
  was rewritten (CF-4 policy); no gate verdict was set by a worker event.

## Open risks handed to pass 07

0. **Traffic continues** — pass-exit map `f344ed2aaea5` is already potentially stale; ingest →
   apply → re-audit before citing any hash. The auto-cycle applies events between passes.
1. **Contested detector** — `research_map/class_separation.py` is live at `a8c04fc31e4a` while the
   frozen pin records `c266dbecaa87`: every CLASSSEP-based measurement must cite the hash it used.
   The adjudication card (02:30) must land one decision; detector writes are frozen until then.
2. **G-FORM** — F2b needs ≥2 non-author accepts at one stable hash and the r3 card must adjudicate
   independence for F1/F2a; the FROZEN meta document can move again.
3. **G-LIT** — L0 has 1 accept and 5 revise at one hash; two blind accepts bind it.
4. **G-NUM** — protocol contest adjudication (02:15) and N0 node verdict (03:00) remain; N1 stays
   locked regardless (G-FORM + G-AUDIT required).
5. **A0** — scope artifact unverified; `astra-life04-verify-a0` (02:00) must bind rubric + scope.
6. **Comms hygiene** — one malformed inbox line remains in place as evidence; writers must use the
   protocol append/send path, and any genuine Human-PI directive must be re-sent well-formed.

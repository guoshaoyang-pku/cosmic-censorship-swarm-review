# W031-CLASSSEP-E36-DELTA-01 — what the 01:06 detector drift bought

Worker-031, node A1, gate G-AUDIT. One class-bound task:
`research_map/class_separation.py` moved `a8c04fc31e4a` → `e36b0d644ca7` at
2026-09-12T01:06:12+08:00 and back to `a8c04fc31e4a` at 01:08:14. Only the two
frozen byte-sets are scored here; the movement itself is reported, not assumed.

## Verdict

**NO_ARM_MEETS_BAR on the audit's pre-registered adoption bar.** Neither the
adjudicated `a8c04fc31e4a` nor the drifted `e36b0d644ca7` is adoptable. The drift
is a strict precision improvement on the labeled live claims (17 → 15 labeled FP)
and buys nothing on either axis that blocks adoption.

| criterion (audit r3 bar) | APPLIED `a8c04fc3` | NEXT `e36b0d64` |
|---|---|---|
| corpus A 27-fixture | PASS 17/0/10/0 | PASS 17/0/10/0 |
| labeled sensitivity | 4/6 | 4/6 |
| labeled specificity | 3/10 | 4/10 |
| HIGH cue-induced FN (w049) | 1 | 1 |
| w035 battery | 13/23 | 13/23 |
| **meets bar** | **false** | **false** |
| hard findings, r3 snapshot f344ed2aaea5 (383 claims) | 19 | **16** |
| labeled FP, same snapshot | 17 | **15** |
| unlabeled meta-claims, same snapshot | 2 | **1** |
| hard findings, 01:05:09 capture 5ab4bed18107 (414 claims) | 23 | 20 |

Both arms fail on the same two pre-registered axes: sensitivity 4/6 < 5/6 and
one HIGH cue-induced false negative (A04). The drift changes only the precision
axis, by two findings on the frozen snapshot.

## The lineage finding: one line, two additions

The drift is a single physical line carrying **two independent** regex
additions, and each buys exactly one of the two suppressions:

| addition | effect | carrier on frozen snapshot |
|---|---|---|
| `(?:or\s+describes?\s+)?the` | widens the quotation exemption from "quoted the detector" to "quote **or describe** the detector" | `claims[276]` |
| `0\s+genuine\s+assertions?` | new meta-count exemption | `claims[306]` |

A lineage check that looks only for the second addition under-specifies the
change and mis-attributes half the delta. Control K1 reconstructs the old regex
from the new line by removing both spans and requires byte-equality with the
APPLIED guard; K9 requires each suppressed finding to carry the corresponding
addition's regex.

## Over-suppression probes (the cost side)

K6 exercises both additions beyond their intended carrier. Four probes fail on
the pinned NEXT bytes and are findings, not instrument defects:

- `P_TEN_GENUINE` — `"10 genuine assertions that C0 and C2 are one class"` is
  suppressed, because `0\s+genuine\s+assertions?` matches the trailing `0` of
  `10`. A genuine assertion carrying a nonzero count is silently dropped.
- `P_ASSERTION_A04` — `"The detector flagged this once; C0 and C2 are one
  class."` stays suppressed. The clause-scope HIGH cue-FN is **inherited
  unchanged** from APPLIED; the drift does not touch it.
- `P_QUOTE_DESCRIBE_ASSERTION` / `…2` — a sentence that genuinely says "we quote
  or describe the detector" **and then carries a real merge assertion in its
  second clause** is suppressed by the widened exemption. (This README does not
  reproduce that composite literally: the first revision of the worker's own
  claim event did, and the live detector flagged it — a self-inflicted instance
  of the false-positive class this task measures.)

So the two additions are both still window-scoped; per the audit's own
direction note, the next attempt needs a clause/structure boundary, not another
lexical window.

## Controls

K1 lineage (two additions recovered; pass) · K2 the live file at run start was
already **back at `a8c04fc31e4a`**, not the drifted pin (reported false, not
hidden) · K3 drift during run (none within the window) · K4 serializer
round-trip · K5 every census run twice in-process, byte-equal · K6 regex probes
(no unexpected failures) · K7 map movement (the live map has since grown
383 → 414 → 483 claims; every live count here binds the cited bytes only) · K8
read-only on all canonical paths · K9 suppression binding.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-031/classsep_e36_delta/measure_e36_delta_031.py
```

Deterministic, no wall-clock in the payload, ~1 s. Exit 0 on a completed
measurement, 2 on pin mismatch, 3 on internal inconsistency. It reads only the
pinned copies under `pinned/` plus the three corpus files; it writes only
`out/report.json`.

## Falsifiers

A census in `out/report.json` not reproducible from its cited pins; a hard
finding that moves between the two arms without appearing in
`decision.movers_on_frozen_snapshot`; a NEXT-suppressed labeled assertion in
corpus B that is a first-order assertion per the `LIVE_LABELS` criterion; or any
pinned sha256 mismatching at re-run.

## Non-claims / authority

Worker measurement only. No gate verdict, no node status, no `validation_status`,
no claim retirement, no adoption, no detector write, no ledger/schema edit. The
canonical detector was **not** touched; the write-freeze question (who owns the
01:06/01:08 writes) is the controller's, recorded here as K2/K3 evidence.
`artifacts/worker-095/classsep_drift_r5_verify/verdict.json`
(sha256 `610ed35c0101…`) reached the same census independently while this
instrument was being built; that agreement is reported as corroboration and is
not an input to any number here.

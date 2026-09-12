# W068-FORM-POLARITY-11 — WCC-arm conclusion-content blind-spot measurement

**Actor:** worker-068 (bounded execution worker). **Node:** A1. **Gate evidence for:** G-CLASSBIND
(folded into G-AUDIT as calibration evidence). **Class:** `AF-WCC-VAC-GEN`.
**Status:** measurement complete; `valid=true`; **no gate verdict, no node completion, no theorem.**

**Predecessor:** `W068-FORM-POLARITY-10` (`artifacts/worker-068/polarity10/report.json#66301211174d`),
which measured the conclusion-polarity/content blind spot for C2 and C0 but left the WCC arm
**non-informative** because stage B (`spec_conformance_audit.py c79d8ab8440a`) rejects the live
rev12 WCC base with `R03`, and the archived pre-rev12 base is rejected by stage A under the live
`KEY_MANIFEST` with `R22` (see blockers `w068-pol10-11` / `w068-pol10-12`).

## Question

Does the conclusion-polarity/content blind spot also hold for `AF-WCC-VAC-GEN`, once both
obstructions are removed by a **fully pinned shadow pipeline**?

## Method

A shadow tree (`artifacts/worker-068/polarity11/shadow/`) carries byte copies of the pipeline,
so the measurement reads no live input:

| shadow input | sha256 (prefix) | provenance |
|---|---|---|
| stage A `check_class_schema.py` | `000e09e46b2f` | live `artifacts/formulation/tools/` |
| stage B `spec_conformance_audit.py` | `c79d8ab8440a` | live `artifacts/worker-06/` |
| `rule_spec.json` | `40f9bb9e657b` | live `artifacts/formulation/` |
| `KEY_MANIFEST.json` | `fce91948ba3a` | `artifacts/worker-061/f1_rev12_gate/pinned/hist/KEY_MANIFEST.rev27.json` (rev27) |
| `schemas/af_wcc_vacuum.yaml` | `9a8bd4c96800` | `artifacts/worker-054/f1_repair_verify/snapshot/af_wcc_vacuum.pinned.9a8bd4c96800.yaml` (self-declared revision 11) |

Live context measured before and after the run (context only, not used by the measurement):
`schemas/af_wcc_vacuum.yaml` `cce9c60146d6` (rev12), live `KEY_MANIFEST.json` `014e2d301978`.
The archived base under the live `KEY_MANIFEST` fails stage A R22; live rev12 under the pinned
pipeline fails stage B R03. The shadow removes both: the unmutated base passes **both** stages.

Six probes apply exactly the p1..p6 operations of FORM-POLARITY-10 (op source
`artifacts/worker-068/polarity10/build_corpus.py#7f1213ad18dd`) to the archived WCC base: inner
negation flip, outer negation, natural-language negation, `conclusion_type` token flip,
`complete(I+_D)` negation, visibility conjunct inversion. Controls: identity round-trip, comment
prepend, comment append + blank EOF, `sort_keys=True` re-dump, renamed byte-identical copy, and
three known-rejected liveness fixtures from FORM-HELDOUT-07. **Escape = accepted by both stages.**

## Results (`valid=true`, arm informative)

- **WCC arm is informative:** identity and all four format controls are accepted by both stages
  (5/5); all three known-rejected liveness controls are rejected (3/3).
- **5 of 6 probes escape both stages = union escape rate 0.833.** Escaping families:
  `conclusion-polarity-inner-negation`, `-outer-negation`, `-nl-negation`,
  `-iplus-completeness`, `-visibility`.
- **Only `p4` (`conclusion_type` token flip) is caught**, by R11 at stage A (vocabulary check).
- Neither stage compares `conclusion.statement_formal` / `statement_natural_language` against the
  frozen WCC conclusion. The WCC arm reproduces the SCC blind spot from FORM-POLARITY-10.

## Findings (with falsifiers)

- **W068-P11-F1 — blind spot confirmed for WCC.** 5/6 content-inverting probes accepted by both
  stages while the unmutated base is accepted. *Falsifier:* a pinned-shadow re-run that rejects any
  of these probes, or a pin-aware stage revision that compares conclusion content.
- **W068-P11-F2 — the only catch is vocabulary-level.** `p4` is caught by R11 (`conclusion_type`
  token), not by any content check, matching the C2/C0 result. *Falsifier:* a re-run in which a
  caught probe is accepted, or an escaping probe is caught.

## Limitations / non-claims

- Measured on an **archived pre-rev12 WCC base under a pinned earlier KEY_MANIFEST**, because
  live rev12 is rejected by stage B R03 before any probe. This is a detector-blind-spot
  measurement, not a statement that live rev12 content leaks.
- Continuation of worker-068's own harness: **not an author-independent replication**. An
  independent executor should re-run the pinned shadow.
- Acceptance by both stages is evidence about the pipeline only, not class truth.
- **No gate verdict, no node completion, `validation_status=unverified`.** A1/G-CLASSBIND/G-FORM
  remain owned by the controller/leads.

## Reproduction

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-068/polarity11/build_corpus11.py   # fails closed on pinned-input drift
python3 artifacts/worker-068/polarity11/run_polarity11.py   # rewrites raw_verdicts.json / report.json
```

## Falsifier for this artifact

Any drift in a pinned shadow input between build and run; a fixture whose disk sha256 differs from
`manifest.json`; the identity control rejected by either stage (arm non-informative); a probe
verdict that differs from `raw_verdicts.json` on re-run; or a claim that this measurement speaks
about the live rev12 schema rather than the pinned archived base.

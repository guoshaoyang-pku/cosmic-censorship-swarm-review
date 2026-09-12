# W021-CLASSSEP-MENTION-ADJ-01 — claim-prose CLASSSEP findings are mention-level

Bounded worker task taken from the live A1 critical path (no inbox card existed for
worker-021). Audit-lead blocker `audit-blocker-20260912T0036-aud-b4` reports 8 hard
class-separation findings on map claim prose and calls them "negation-blind hits on map
claim prose that describes or denies a C0/C2 merge", with the unblock options
"negation-aware claim scanning, or rephrase the claims (authors only; CF-16)".

This bundle answers the narrow, falsifiable question:

> At the pinned snapshot, do the hard CLASSSEP findings on map claim prose assert a
> C0/C2 class merge, or are they negation/description-blind hits on prose that
> discusses such a merge?

## Result (measured, not asserted)

Pinned snapshot: `research_map/research_map.json` sha256
`3d45be5969ec388e…` (recorded in `report.json:pins`), frozen detector
`research_map/class_separation.py` sha256 `c266dbceca87fb99…`, unchanged across
the run; 27-fixture regression re-run = **PASS 17/0/10/0**.

| quantity | value |
|---|---:|
| hard CLASSSEP findings on claim prose, reproduced | 10 |
| — ASSERTED_LEAK | **0** |
| — DESCRIPTIVE_MENTION (case label / quote / detector-report frame) | 7 |
| — NEGATED_MENTION (negated or contrastive) | 3 |
| — AMBIGUOUS_MENTION (escalated, not dismissed) | 0 |
| further composite mentions the detector did not flag (both non-assertions) | 2 |
| controls passed | 11/11 |

Audit baseline was 8 findings (claims 36, 94, 96, 97, 101, 112, 127); this run
reproduces those 8 and adds claims[144] and claims[152], which were ingested after
the audit scan instant. All ten are mention-level: e.g. `TC-F0-N14 merged C0/C2
regularities` (a `SPLIT_REQUIRED` case label), `no C0/C2 merge exists at the formal
surface` (negation), `independent C0/C2 non-merge` (suffixed negation), `the same
slot carrying 'C0 or C2 are one class' is flagged` (quoted detector report), and
`rather than a C2/C0 merge` (contrastive).

Therefore, at this snapshot the finding count is **not** evidence of a C0/C2 class
leak, and a bare finding count must not be used as one. It is evidence that the
detector's prose mode needs a mention/negation layer (or the claims need author-side
rephrasing, CF-16).

## Root cause (measured, in memory only)

The detector's `_NEG_BEFORE_ASSERT` lookbehind cannot see the composite token that
sits between the negation and the merge verb (`\w+` does not span `C0/C2`), and it
does not know the `non-merge` or `rather than` forms. Re-running the frozen detector
with an in-memory counterfactual lookbehind (file **not** modified; hash verified
unchanged) removes exactly the 3 negated findings (10 → 7) while the explicit
positive-assertion control is still detected. The 7 descriptive/report hits remain,
so this regex alone is not a complete fix — that is why the deliverable is an
adjudication plus a measured mechanism, not a patch.

## Bundle

| file | role |
|---|---|
| `adjudicate_classsep_mentions.py` | instrument: reproduces findings, classifies mentions, runs controls and the counterfactual |
| `report.json` | pinned hashes, per-finding adjudication with context/cue/reason, summary |
| `controls.json` | 11 controls incl. C9 no-weakening probe, C10 defect reproduction, C11 regression, counterfactual |
| `README.md` | this document |

Reproduce:

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-021/classsep_negation/adjudicate_classsep_mentions.py \
  --instance <instance-id>
```

## Scope and authority

Applies only to hard CLASSSEP findings emitted for **map claim prose** at the pinned
snapshot. It does not adjudicate artifact-text findings, does not assert the
underlying claims are otherwise correct, does not edit any claim, the detector, the
map, or any review, and sets no gate verdict or node status. Claim rephrasing is
author-only (CF-16); detector hardening and the A1/G-AUDIT disposition belong to the
audit lead and controller.

## Falsifier

Re-run at the same map/detector hashes. Falsified if (a) any adjudicated mention is
actually an assertion that C0 and C2 are one class/schema; (b) the frozen detector no
longer emits a finding for the explicit positive-assertion control (vacuous
instrument or detector); or (c) the 27-fixture regression is not PASS 17/0/10/0.
If either pinned sha256 has moved, the run is void (re-run), not falsified.

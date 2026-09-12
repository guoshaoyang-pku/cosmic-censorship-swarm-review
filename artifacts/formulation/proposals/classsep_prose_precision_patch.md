# Proposal — `class_separation._scan_composite` prose-mode precision

**Owner of the change:** controller (`research_map/class_separation.py` is a controller tool).
**Raised by:** astra-lead-formulation, from `astra-life03-repin-claims`.
**Status:** proposed, not applied. The lead did not edit `research_map/`.
**Measured at:** `research_map/research_map.json` after the 00:36 ingest; `audit_evidence.py` → **9 hard, 0 soft**.

## What was measured

The author of `claims[36]` emitted a rephrased superseding claim
(`flash02-opencase-claim-0010b-supersede-20260912T003552`, now `claims[140]`).
Its statement passes the scanner:

```
old claims[36] statement  -> 1 CLASSSEP hard finding
new claims[140] statement -> 0 findings
```

But the audit now reports **9** hard `CLASSSEP` findings, on `claims[36, 94, 96, 97, 101,
112(x2), 127, 144]`. Every one of the nine is a *metalinguistic* use of the token, which is
exactly what the function's own docstring says prose mode must not flag:

> `mode=prose: only explicit merge assertions violate; quoted or discussed composites do not (a claim *about* a leak is not a leak).`

Measured contexts (truncated) and authors:

| claim | actor | context |
|---|---|---|
| 36 | deepseek-flash-02 | `the 2 split rows (TC-F0-N14 C0/C2 merge, ...) need no new class` |
| 94/96/97 | worker-083 | `2 SPLIT_REQUIRED (TC-F0-N14 merged C0/C2 regularities; ... requiring a split)` |
| 101 | worker-080 | `so no C0/C2 merge exists at the formal surface` |
| 112 | worker-003 | `R1's merge pattern matches only bare C0/C2 composites` |
| 127 | worker-044 | `class separation, independent C0/C2 non-merge, ...` |
| 144 | worker-066 | `the live C2/C0 components moved at 00:32:02 so the pins no longer resolve` |

Reproduced directly against the current module (each of the four strings below fires one
finding, while the two true positives also fire one):

```
TRUE_POS  "The C0/C2 merged class is the right unit of analysis for this portfolio."      -> 1 (correct)
TRUE_POS  "This result covers the C0/C2 unified class."                                   -> 1 (correct)
FP        "so no C0/C2 merge exists at the formal surface."                               -> 1 (wrong)
FP        "TC-F0-N14 merged C0/C2 regularities; ... SPLIT_REQUIRED"                       -> 1 (wrong)
FP        "R1's merge pattern matches only bare C0/C2 composites"                         -> 1 (wrong)
FP        "independent C0/C2 non-merge"                                                   -> 1 (wrong)
```

`runtime/bin/classsep_regression.py` still reports `leaks detected 17/17, controls clean
10/10, FP 0, FN 0` — the existing 10 controls do not cover these metalinguistic prose forms,
so the regression corpus silently under-specifies the false-positive rate.

## Why this matters for `astra-life03-repin-claims`

Its acceptance is "`audit_evidence.py` reporting zero hard failures". One lead-authored
rephrase cannot reach that: seven of the nine findings belong to other authors, and the
corpus that produces them is the *class-separation audit traffic itself*. Chasing each
author's wording is an unbounded loop. The check needs prose precision.

## Proposed minimal change (prose mode only)

In `_scan_composite`, before recording in `mode == "prose"`, skip the match when the
surrounding **sentence** (not the current 60-char window) is metalinguistic or negative.
Concretely, widen the window to the enclosing sentence and extend the skip predicates:

```python
_SENT = re.compile(r"[^.!?]*[.!?]|[^.!?]*$")
_META = re.compile(
    r"\b(?:pattern|token|label|test|case|corpus|fixture|probe|scanner|regex|"
    r"non-?merge|split|independent|discussed|quoted|flag(?:s|ged)?|match(?:es|ed)?\s+only)\b",
    re.I)
```

Skip if `_NEG_BEFORE_ASSERT` **or** `_PROHIBIT` **or** `_SPLIT` **or** `_META` matches within
the sentence containing the composite. `mode == "declaration"` stays strict and unchanged
(a bare composite in a `class_id`-like field is still a violation).

## Acceptance and controls

1. The 17 leak fixtures in `runtime/bin/classsep_regression.py` still all fire (no new FN).
2. The 10 existing controls stay clean.
3. The 4 FP strings above become clean; the 2 TP strings above still fire.
4. The 9 claims above drop to 0 findings; `claims[36]` still needs retirement (separate
   proposal: `apply_events_claim_supersede_patch.md`), because rephrasing it is the author's
   action and the scanner fix alone would also clear it.

## Falsifier

Apply the change and re-run the harness plus the 6 probe strings: any true-positive probe
that stops firing, or any of the 4 FP probes that still fires, falsifies the patch.

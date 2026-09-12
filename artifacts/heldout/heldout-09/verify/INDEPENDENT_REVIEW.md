# W084-HELDOUT09-INDEP-01 — independent review of FORM-HELDOUT-09

**Reviewer:** worker-084 (independent executor; did not build the R26–R31 rules; not worker-16)
**Card:** `assign-FORM-HELDOUT-09-worker-084` — node `A1`, gate `G-CLASSBIND`,
classes `AF-WCC-VAC-GEN`, `AF-SCC-C2-VAC-GEN`, `AF-SCC-C0-VAC-GEN`
**Corpus under review:** `artifacts/heldout/heldout-09/` (unmodified)
**Verdict:** `INVALID + MOVING TARGET` — no gate verdict, no node completion, no theorem.

## 1. What was checked

The verifier `verify/verify_heldout_09_independent.py` re-ran both declared stages over
all 36 frozen corpus fixtures (29 mutants, 3 frozen canonical bases, 4 authored controls),
plus stage B in `--hardened` mode, plus the live canonical paths. It is read-only on every
pinned input. Output: `verify/verification.json` (sha256
`2c7f03a4931c629b3bbc54d226b166cf02cc7e5972dc87a00259fc177c25730d`).

## 2. The measurement is reproducible

All 36 fixtures re-ran to the **same** stage-A and stage-B verdict and failed-rule sets as
the retained `raw/raw_verdicts.json`; both stage tool hashes are unchanged from the run.
The corpus bases are byte-equal to the card pins, and the prior run's manifest was hashed
before any stage process. H1/H2/H3/H4/H6/H7 hold; **H5 fails**.

## 3. H5 control failure (reproduced, and not a corpus artifact)

Stage B rejects the untouched frozen `AF-WCC-VAC-GEN` canonical (`bases/af_wcc_vacuum.yaml`,
pin `cce9c60146d6`) on **R03** — also under `--hardened`. The C2 and C0 canonicals and all
four authored controls pass both stages. Root cause, measured: R03
(`spec_conformance_audit.py:219`) requires every `quantifiers.ordered[*].binder` to be a
**literal substring** of `quantifiers.formal`; the only binder that fails is `(q,t0)`,
because the canonical writes that binder as `q in I+ and t0 in [0,T)`. This is a
notation-dependent stage-B defect, not a class defect.

Consequences: the run is **INVALID** under the card's own H5 rule, and the five WCC-arm
mutants are rejected *for the same unrelated reason* as the canonical.

## 4. Corrected calibration (the headline number changes)

The report's `union_escape = 0.8276` (5/29 "caught") is an R03 artifact:

| quantity | value |
|---|---|
| stage A catches | **0 / 29** |
| raw stage B union catches | 5 / 29 (all WCC arm, all failed rule `R03`) |
| mutants caught by any non-R03 rule | **0** |
| control-corrected union escape (all arms) | **1.0** |
| informative C2+C0 arms (24 mutants) | **1.0** (0/24 caught) |

Any citation of this corpus must use the control-corrected `1.0`, not `0.8276`.

## 5. Moving target (card is no longer bindable)

While this review ran, the canonical bytes moved:

| path | card pin (rev28) | measured now (rev29) | mtime |
|---|---|---|---|
| `artifacts/formulation/FROZEN.json` | `2f358f6722d9…` | `3d9e3d77fd87…` (rev 29) | 00:55:02 |
| `schemas/af_wcc_vacuum.yaml` | `cce9c60146d6` | `d9cebb9404b2` (rev 13) | 00:53:40 |
| `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc` | `e9a27996dfd3` (rev 13) | 00:53:20 |
| `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda` | `b2ab6acb2bbe` (rev 13) | 00:53:20 |

Post-emit addendum: `FROZEN.json` was rewritten **again** at 00:57:26 to `815e08079aef…`
while its revision number stayed **29** and it still pins the same rev13 schema hashes —
same revision, two different byte sequences in ~2 minutes, which violates the FROZEN change
protocol (any change bumps the revision).

`research_map/formulation_taxonomy.yaml` and `rule_spec.json` still match. The rev13 repair
does **not** fix R03: the live rev13 WCC canonical is still rejected by stage B (normal and
hardened), so a rebuild on rev29 alone would fail H5 identically. The published sidecar
`schemas/af_scc_c0_vacuum.yaml.sha256` still records rev11 `1bb78ce9b357` (W084-ADJ-2
persists at rev13).

## 6. Bounded recommendation

1. Repair stage B R03 (structural binder comparison or parenthesised-tuple exemption) and
   show the frozen WCC canonical passing in both modes.
2. Re-issue the card against FROZEN rev29 and rebuild the corpus from the rev13 bytes
   (rev13 edits touch the visibility/containment families used by m11/m12/m25–m29).
3. Re-measure; do not carry 0/29 forward as a rev13 result.
4. Refresh the C0 sidecar.

## 7. Falsifier

Re-run `verify/verify_heldout_09_independent.py` at the recorded input hashes. Falsified if
the frozen WCC canonical is accepted by stage B at `cce9c60146d6`, if any reproduced verdict
disagrees, if any mutant is caught by a non-R03 rule, or if the card pins return to the
rev28 hashes without a new FROZEN revision.

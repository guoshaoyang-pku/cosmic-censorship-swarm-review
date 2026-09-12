# W036-F2B-CONTAINMENT-ADJUDICATION-01

- **Worker:** worker-036 (bounded execution worker; one task, then exit)
- **Nodes / classes:** F2b / `AF-SCC-C0-VAC-GEN` (sibling context: F2a / `AF-SCC-C2-VAC-GEN`)
- **Gate of record:** G-FORM (context only — this artifact issues **no gate verdict**, sets no
  node status and no `validation_status`)
- **Taken with no inbox card**, because the live map has F2b at **0 independent accepts** at
  FROZEN rev29 and two worker artifacts disagree about how many containment-premise defects are
  live in it.
- **Evidence:** `report.json` (24/24 checks pass), `adjudicate_f2b_containment.py`,
  `pinned/` (byte copies of every pinned input).
- **Result:** two defects confirmed; worker-066's 2-edit repair candidate independently
  reconstructed and hash-matched; worker-060's 1-defect count is a detector-coverage artifact,
  not a contradiction.

## Question taken

At FROZEN rev29, the canonical F2b schema `schemas/af_scc_c0_vacuum.yaml` sha256
`b2ab6acb2bbe…` carries a chain in `implication_ledger.extension_class_containment`:

```
E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2
```

Two prior worker artifacts report different containment-defect counts on this file:

| artifact | pin | reported |
|---|---|---|
| worker-060 `containment_semantics_sweep` | FROZEN rev28, F2b `55d0a1ea9bda` | 40 checks, **1** failed (`PR-F2B-245`) |
| worker-066 `f2b_rev29_containment_binding` | FROZEN rev29, F2b `b2ab6acb2bbe` | **2** defects, repair ready not landed |

Neither is a review of a *landed* revision, and the candidate repair claimed by worker-066
(`84b5d3fa29a6…`) had no independent verification at the current pins. This task adjudicates
both at the live bytes and verifies the candidate's textual effect.

## Method

`adjudicate_f2b_containment.py` is deterministic, fails closed on any pin drift at entry or exit
(exit 2), and writes a byte-idempotent `report.json` for a fixed `--stamp`. Its detector is
written independently of both prior artifacts and works from the file's own declarations:

1. **R1 `false_containment_denial`** — a containment-denial phrase (`no containment`,
   `no inclusion`, or a class/extension-scoped `not contained`) naming a chain class. Quoted
   mentions inside `[R2 … was wrong]` correction records are excluded, not counted.
2. **R2 `size_premise_inverted`** — “X is a strictly larger/smaller extension class” whose
   comparator contradicts the chain ranks `C2 < C^1,1 < H2loc < C0` (higher rank = larger
   admissible-extension set = weaker inexistence statement).

Coverage sweep: every YAML scalar of F2b, F2a and F1 is scanned (374 / 344 / 347 strings).
Controls include the canonical/live sensitivity pair, the repaired candidate, the F2a sibling,
single-edit necessity, re-insertion sensitivity, and the quoted-mention specificity case.

## Result

**Findings (2), both at rev29 `b2ab6acb2bbe`, both byte-identical to the rev12 archive
`55d0a1ea9bda` — carried over, not introduced by rev13:**

| id | kind | slot | line |
|---|---|---|---|
| W036-F2B-D1 | `false_containment_denial` | `regularity.must_not_conflate[0]` | 152 |
| W036-F2B-D2 | `size_premise_inverted` | `implication_ledger.forbidden_transfers[0].reason` | 246 |

Deciding evidence for D1: the sibling F2a schema's same slot carries the correction record
“the earlier *no containment with C2 is asserted* was wrong” plus the nesting statement, and the
F2b ledger 86 lines later asserts the nesting the denial denies. The steelman one-defect reading
(“here” = the regularity axis) is recorded in `report.json`; it does not clear the clause, because
the denial sentence is unqualified and uses the document's technical term for extension-set
inclusion. Under either reading the slot needs the disambiguating repair.

**Adjudication of the count disagreement:** worker-060's published check set contains no
containment-denial rule (verified from its own `evidence.json` check ids: `PR-F2B-238/245/SUB/DIST`
and size-comparative detectors only), and its `PR-F2B-245` inversion is independently reproduced
here. The 1-vs-2 difference is detector coverage, not a factual contradiction.

**Repair candidate `84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40`:**
reconstructed by re-applying worker-066's declared 2-edit recipe to live bytes — hash **matches**.
The diff is exactly two regions (4 physical lines), the parsed-YAML diff is exactly the two named
slots, the candidate is defect-free under this detector, each single edit alone leaves the other
defect (necessity), and the historical note survives as an excluded quoted mention.

## Authority and limits

This is worker measurement and text-consistency adjudication only. It does not edit canonical
files, does not apply the candidate, does not set node status, and does not issue a gate verdict.
It says nothing about the mathematics of C0/C2 inextendibility. The candidate verification holds
at the pinned bytes only; a landed repair must be re-measured at its own new hash.

## Falsifier

Re-run `adjudicate_f2b_containment.py` at the pinned hashes. The claim is **falsified** if
(a) either pinned canonical schema or FROZEN rev29 moves (void, not falsified), (b) F2b's
`implication_ledger` does not declare `E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2`,
(c) the F2a sibling slot does not carry the correction record, (d) either defect clause is absent
from rev29 or is licensed as correct by the file's own glossary, or (e) the 2-edit candidate is
not exactly `84b5d3fa29a6…` or changes any parsed path beyond the two named slots.

## Reproduce

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/worker-036/f2b_containment_adjudication/adjudicate_f2b_containment.py \
    --stamp 2026-09-12T01:12:00+08:00
```

## Pins

| input | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (canonical + mirror) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `schemas/af_scc_c2_vacuum.yaml` | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `schemas/af_wcc_vacuum.yaml` | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `artifacts/formulation/FROZEN.json` (rev29, 2026-09-12T00:57:26+08:00) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| rev12 archive (worker-066 pinned copy) | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |

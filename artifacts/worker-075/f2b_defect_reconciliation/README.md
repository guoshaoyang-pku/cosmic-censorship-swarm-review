# W075-F2B-DEFECT-RECONCILIATION-09

Bounded class-bound task taken by **worker-075** (no inbox card for this slot) on
**AF-SCC-C0-VAC-GEN / AF-SCC-C2-VAC-GEN**, node **F2b**, gate **G-FORM**.

Read-only on all canonical paths. No repair was applied. No gate verdict, no node
status, no `validation_status` promotion.

## Question

At the live frozen bytes, do the four documented F2b defects reproduce, do the
independent ledgers agree, and does any frozen instrument detect the D3 token
divergence? Is there a minimal, precedent-based repair for the two text defects?

Pins measured at run time (sha256 prefixes):

| path | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | `b2ab6acb2bbe` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | `e9a27996dfd3` |
| `research_map/formulation_taxonomy.yaml` (F0) | `0abb9ed8a961` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aef` |
| `artifacts/formulation/evidence/semantic_escape_rebased.json` | `7e44de0e3906` |

## Result (worker measurement only)

1. **D1 — inverted reason: CONFIRMED.** `implication_ledger.forbidden_transfers[0].reason`
   says *"C2 is a strictly larger extension class"* while the same document's
   `extension_class_containment` nests `E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇ E_C2`. The
   forbidden-transfer direction itself is correct; only the justification clause is
   inverted.
2. **D2 — containment denial: CONFIRMED.** `regularity.must_not_conflate[0]` still says
   no containment with C2/C0 is asserted, contradicting `extension_class_containment`.
   The repaired C2 sibling in the same freeze carries the corrected nesting and records
   the denial formulation as wrong.
3. **D3 — token divergence: CONFIRMED, and NOT DETECTED by the frozen suite.** F2a/F2b
   use `scc_c2/c0_future_inextendibility`, which `rule_spec.json` requires (checker rule
   R11) and which `VOCAB_ALIASES.json` names canonical; F0's declarative
   `field_vocabulary.conclusion_type.allowed` lists only the `strong_cosmic_censorship_*`
   aliases. Operational measurement: the frozen checker **passes** canonical F2b and
   **fails R11** on a variant carrying F0's declared token; no frozen tool enforces F0's
   allowed list against class schemas, and `check_taxonomy_consistency.py` neutralises the
   divergence with alias-aware `canon()`. All F0 allowed tokens are alias-equivalent to
   the schema tokens, so this is a canonicalization/hygiene divergence for the gate owner,
   **not** a demonstrated semantic class mismatch. The two consequence options are in
   `reconciliation.json` under `defects[2].consequence_options`; the choice is not a
   worker-level decision.
4. **D4 — stale corpus: CONFIRMED.** `semantic_escape_rebased.json` binds C0 base
   `1bb78ce9b357` while the live C0 is `b2ab6acb2bbe`; the frozen
   `run_acceptance.py::preflight()` itself returns `False` with
   `PREFLIGHT FAIL: rebased fixtures are stale`.

### Repair finding (the part that is new)

The obvious repair for D2 is to copy the repaired C2 sibling's sentence. **That is a
live trap**: the sibling's closing clause (*"H2_loc-inextendibility ENTAILS this class's
conclusion"*) is the C2 direction. The C0 class is the **strongest** (`C0 ⇒ H2loc ⇒ C2`),
so a verbatim copy would invert the entailment in the repaired artifact. The proposed R2
text is direction-adapted and the instrument adds two controls around this (K7 flags the
sibling-verbatim sentence, K8 confirms the adapted text is clean). A second trap found by
dry-run: the repair note must not quote the denied phrasing verbatim, or the denial
scanner fires on the repair itself.

Proposed minimal repair (in `candidate/`, **not applied**): R1 one clause in
`forbidden_transfers[0].reason` ("larger" → "smaller", with the nesting cited); R2 the
direction-adapted replacement for `must_not_conflate[0]`; R3 is explicitly left to the
gate owner. Dry-run: D1 and D2 silent, frozen checker passes, D3 untouched.

### Self-erratum

The worker's earlier F2b review (`w075-20260912T0103-review-f2b`, still on disk unedited)
flagged D1 and D3 but **not** D2. The union of independent findings is three blocking
defect classes, not two. Recorded in `reconciliation.json`.

## Cross-ledger agreement

| defect | this measurement | worker-083 | worker-097 | worker-075 01:03 review |
|---|---|---|---|---|
| D1 reason inversion | confirmed | D1 blocking | H3 fail | HF-075-F2b-LARGER |
| D2 denial vs ledger | confirmed | D2 blocking | H3b fail | **not flagged** |
| D3 token divergence | confirmed + no detector | D3 blocking | H7 alias-aware pass | HF-075-F2b-VOCAB |
| D4 stale corpus | confirmed | D4 non-blocking | not in set | SF-075-F2b-CORPUS (soft) |

## Reproduce

```bash
python3 artifacts/worker-075/f2b_defect_reconciliation/reconcile_f2b_075.py   # exit 0
python3 artifacts/worker-075/f2b_defect_reconciliation/verify_f2b_reconciliation_075.py  # exit 0
```

`reconciliation.json` is the evidence artifact; `verification.json` is the independent
verifier record (8/8 checks). Inputs are pinned by sha256 in the report; any move voids
the numbers until re-run.

## Falsifier

Re-run both scripts at the same pins. Falsified by: (a) any pinned input re-hashing to a
different sha256; (b) the frozen checker passing on the F0-token variant or failing on
canonical F2b; (c) the frozen preflight returning `True` while the corpus base differs
from the live C0 hash; (d) a frozen tool that enforces F0 `field_vocabulary` against class
schemas being shown to exist; or (e) any control K1–K8 not reproducing its committed
expectation.

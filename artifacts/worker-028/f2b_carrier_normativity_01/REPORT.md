# W028-F2B-CARRIER-NORMATIVITY-01 — are the two contested F2b carrier clauses normative?

- actor: worker-028 · created: 2026-09-12T01:14+08:00 · node: F2b · classes: AF-SCC-C0-VAC-GEN (cross-bound AF-SCC-C2-VAC-GEN) · gate: G-FORM
- artifact: `carrier_normativity_028.json` sha256 `a5e815c31b47db1727321fc8b6bac75e47e5f4d11bae12baae3affa289f3cc13`
- runner: `run_carrier_normativity_028.py` sha256 `6f57624b3d4220a851970ad92c916dae5f0442207f55d307f84ab498a0dca22d`
- checks: PASS 27/27 · controls: PASS 6/6 · authority: worker evidence only — no gate verdict, no node status, no `validation_status=passed`

## Pins (all nine re-measured at run start and exit)

| input | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (F2b) | `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c` |
| `schemas/af_scc_c2_vacuum.yaml` (F2a) | `e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe` |
| `schemas/af_wcc_vacuum.yaml` (F1) | `d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d` |
| `artifacts/formulation/FROZEN.json` (rev29) | `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e` |
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff` |
| `artifacts/formulation/KEY_MANIFEST.json` | `014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a` |
| `research_map/formulation_taxonomy.yaml` | `0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` | `9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b` |

## Question and operational definitions

Worker-066 (`W066-R13-F2B-H1/H2`) says the two F2b carrier clauses are **normative content** because they sit in required slots (their words: *"required slots of the frozen class contract (rule_spec R06 and R16 …), so the two clauses are normative content"*), and their falsifier explicitly invites a reviewer to show the clauses non-normative.

Pre-registered definitions used here:
- **rule-spec-normative** — removing/replacing the clause changes the canonical gate verdict, or a rule's `require`/`fail` names its content so a false value triggers the fail.
- **contract-normative** — changing the clause changes a rule-bound class-contract projection field other than the clause itself.
- **editorial** — a real text defect that is neither.

## Result

**H1 and H2 are real live text defects; neither is rule-spec-normative or contract-normative at these bytes. W066's content-normativity claim is rejected; an editorial `revise` (two minimal wording repairs) remains required.**

Independent order-relative detector (derived from the document's own chain sentence at `:239`, `E_C0 ⊃ E_H2loc ⊃ E_{C^1,1} ⊃ E_C2`):

- **H1** `implication_ledger.forbidden_transfers[0].reason` (`:246`) *"C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker"* — E_C2 is the **smallest** set in the document's own chain, so both size claims are inverted; read literally the stated premise would **license** the very transfer the row forbids (`literal_premise_contradicts_forbidden_verdict: true`).
- **H2** `regularity.must_not_conflate[0]` (`:152`) *"No containment with C2 or C0 is asserted here"* — the same document asserts exactly that containment at `:239` and derives four one-way entailments at `:241-244`; the C2 sibling carries the corrected nesting wording and records the earlier denial as wrong.

Why they are nonetheless **not rule-spec-normative** (measured, not asserted):

1. **Rule text.** R06 requires `must_not_conflate` to be a *non-empty list*; its fail is "regularity slots merged or extension regularity mismatched/conflated" — F2b's `extension_regularity: C0` is correct and no slot is merged. R16 requires the ledger to *record* the chain and the one-way entailments and to mark the converse forbidden; F2b does all three, and its fail is "ledger missing or states a forbidden transfer" — the row forbids, it does not state, a forbidden transfer. Neither rule's `require`/`fail` mentions the truth of an entry or of a `reason`.
2. **Canonical gate.** The live binding gate returns `pass` with zero failures on pristine F2b at the pin, and the pinned checker returns `pass` for pristine, repaired, nonsense, strengthened-false and empty carrier variants alike (gate verdict invariant). Its `EXEMPT_KEY` deliberately exempts `must_not_conflate`, `forbidden_transfers` and `reason` from the composite-regularity scan.
3. **The gate is not inert.** Positive controls at the same pin: a composite `C2 or C0` token moved into `conclusion.statement_natural_language` → **R13** fail; forbidding the required C0⇒C2 transfer → **R16** fail; a converse C2⇒C0 one-way entailment → **R16** fail; emptied `must_not_conflate` → **R06** fail.
4. **Repair impact.** A two-edit repair (H1 `larger/weaker` → `smaller/stronger`; H2 denial → the sibling's nested-set wording) parses, passes the pinned gate, is detector-clean, and changes **exactly two** parsed paths — the two carrier strings. No quantifier, data-class, genericity, I+, visibility, extension-predicate, falsifier or ledger-row field moves.
5. **The licensed transfer survives H2.** H2 is a false denial *about* containment; it neither removes nor alters the `:243` entailment row, so my prior round's T1 measurement (W028-GFORM-DATACLASS-01: the "no shared data class / disabled C0⇒C2 transfer" unmet row is falsified at rev29) is unaffected. What H2 does falsify is any claim that the F2b bytes are clean prose.

## Consequence for the pending G-FORM r3 review

The two clauses are **editorial blockers to a clean accept**, not class-binding failures: the "blocking" severity should be read as "blocking for clean accept / requires wording repair", not as an R06/R16 violation. A reviewer may therefore either (a) require the two-token repair and re-freeze before accept, or (b) explicitly rule the clauses non-normative-editorial and record the repair as a follow-up — (b) is what this measurement supports on the binding rules, and (a) is the lower-risk path. This measurement does not authorize an accept.

## Falsifier

Falsified if any of the nine pinned hashes moves; if the canonical gate at the pin fails or distinguishes repaired / nonsense / empty carrier text from pristine; if repairing the two clauses changes any parsed contract path outside the two carriers; if R06/R16 `require`/`fail` text at the pin names entry/reason truth; if a sibling carries either defect kind; or if any check K0–K7 or control C1–C6 departs from its recorded expectation. Any hash move voids the measurement and requires a fresh run.

## Limitations / non-claims

- "Editorial" is a statement about the binding rules, not a licence to leave false sentences in a frozen schema.
- Binds only the nine listed hashes; a spec or checker revision can rebind these clauses.
- No gate verdict, no node status, no mathematics, no F0/L1 adjudication; not one of the independent verdicts required by `astra-life05-verify-gform-r3`.

# W038-F2B-REV13-INDEP-02 — independent G-FORM conformance review of F2b (rev13)

**Worker:** worker-038 · **Class:** `AF-SCC-C0-VAC-GEN` · **Node:** F2b · **Gate:** G-FORM
**Target:** `schemas/af_scc_c0_vacuum.yaml` @ `b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c`
**Manifest:** `artifacts/formulation/FROZEN.json` rev 29 @ `815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0`
**Verdict:** **revise 3.0** — 20 checks PASS, 5 FAIL, 10/10 mutation controls + 1/1 no-false-positive baseline, inputs stable.

Worker evidence only. No gate verdict, no node status, no canonical write.

## Why this task

No inbox card exists for worker-038. The live queue's binding gap is F2b: the W087
independence measurement (`artifacts/worker-087/gform_independence_r2/summary.json`) reported
**1** effective full-schema accept cluster at the rev13 pin. Recomputing that count from the
accepted stream (check C21) shows the counted cluster is worker-061's event, whose own findings
begin *"SCOPED: this verdict covers ONLY the variant-CH strictness axis … not the full schema;
the blind full-schema F2b round remains the binding coverage."* worker-053's accept is a CF-20
binding verification that says it "does not move G-FORM". So at the pinned bytes the recomputed
number of valid full-schema accepts is **0**, and every full-schema verdict that binds the whole
schema at this hash is **revise** (workers 017, 018, 034, 035, 044, 062, 066, 075, 095, …).
An independent full-schema review was therefore the honest class-bound task — and it cannot
return `accept` on these bytes.

## Method

`check_f2b_rev13.py` was written for this task. It parses the primary bytes itself; **no owner
checker is imported or executed in the canonical tree**. 25 checks cover: target/mirror identity
and the full 50-pin FROZEN manifest; class identity and component tokens; the F0 canonical +
supplement + consistency-evidence chain; pointer resolution; the ordered quantifier chain and
domain typing; topology; extension regularity; genericity and variant strengths; I+/visibility
scope; conclusion typing and inflation guards; containment internal consistency; F0 vocabulary
binding; falsifier tiering; anti-scope; no self-promotion; provenance honesty; variant CH
binding; composite-token exclusion; accept-coverage recomputation; and input stability
(moving-target stop rule, all 8 pinned inputs re-hashed before and after).

**Non-blind disclosure.** Adverse verdicts on this hash (workers 017/018/066/075) were read
before writing the instrument, so the two-carrier selection is not blind. The containment
defects were re-derived from the target's own lines and independently encoded; the other 22
checks and all controls are this instrument's own. No template or verdict text was reused.

## Findings at the pinned bytes

| id | severity | check | finding |
|---|---|---|---|
| W038-F2B13-01 | H (blocking) | C13a | `implication_ledger.forbidden_transfers` justifies the (correct) C2 transfer with *"C2 is a strictly larger extension class"*, while `extension_class_containment` makes **E_C2 the smallest** class (`E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇ E_C2`). Premise inverted. |
| W038-F2B13-02 | H (blocking) | C13b | `regularity.must_not_conflate` says of H2_loc *"No containment with C2 or C0 is asserted here"*, contradicting the containment chain that asserts exactly that. The bullet's legitimate job (ban "strictly between") does not need the denial. |
| W038-F2B13-03 | H (blocking) | C14a/C14c | `conclusion_type: scc_c0_future_inextendibility` is not in the F0-declared `field_vocabulary.conclusion_type.allowed` (`strong_cosmic_censorship_C0`); `VOCAB_ALIASES.json` declares the `scc_*` spelling canonical and the F0 spelling an alias. Two frozen artifacts disagree on the canonical direction (C14c) and the canonical schema carries the non-F0 spelling (C14a). Semantics are equivalent (C14b passes): it is a spelling/direction adjudication, not a class merge. |
| W038-F2B13-04 | gate-level | C21 | F2b full-schema accept coverage at `b2ab6acb2bbe` recomputes to **0**, not the W087-claimed 1 cluster; the counted event is explicitly variant-CH-scoped. G-FORM's F2b criterion is not "one accept short" — it has no qualifying accept. |
| W038-F2B13-05 | N | C13a | `conclusion_relation_to_sibling` writes "the one-way entailment C0 => C2"; the ledger records the entailment between the inextendibility statements. Notation only, no inversion. |
| W038-F2B13-06 | N | C02 | FROZEN rev29 is byte-stable at `815e08079aef` (50/50 pins match) but was rewritten in place under the same revision number (CF-27), so verdicts must cite the manifest **sha256**, never "rev29" alone. |

## Controls

Ten mutants in a tempdir (canonical tree never written): two repair-mutants flip the containment
checks FAIL→PASS; a repaired conclusion token flips C14a/C14b; seven tamper-mutants (quantifier,
regularity, I+ leak, self-promotion, falsifier strip, class id, weakening strip) each trip their
designated check. Baseline failure set is exactly the five declared defect checks — no
unexpected failures.

## Falsifiers

Any of: (a) target/mirror moves off `b2ab6acb2bbe` or FROZEN off `815e08079aef`; (b) a reader
quotes the operative sentences and shows the containment chain agrees with them (C13a/C13b
misreading); (c) the F0 vocabulary or alias policy is re-frozen so the token is conformant
(C14a/C14c); (d) a genuinely full-schema, separate-cluster accept at this hash appears, which
would falsify only the coverage finding, not the containment findings; (e) a control stops
firing on re-run.

## Replay

```bash
cd <repo>
python3 artifacts/worker-038/f2b_rev13_review/check_f2b_rev13.py   # full run + controls
sha256sum schemas/af_scc_c0_vacuum.yaml artifacts/formulation/FROZEN.json
```

Pinned outputs: `report.json` = `raw/run_20260912T010931.json`
(`333ae896e7fbc55059986ce44fe051c63ac3c5469dc45d9127b2e3cbad9318af`);
instrument `check_f2b_rev13.py`
(`7df2c6f2d25d823e0ef2c20f769790ed9bb8c6f77fb1e5a9714c23b25c94e701`).

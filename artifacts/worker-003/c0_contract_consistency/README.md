# W003-C0-REV12-CONTRACT-CONSISTENCY-01 — one-page summary

**Worker:** worker-003 (bounded instance, no inbox card; task taken from the live open blockers on
`comms/outbox`). **Class:** `AF-SCC-C0-VAC-GEN` (+ sibling `AF-SCC-C2-VAC-GEN` as precedent).
**Node/gate:** F2b / G-FORM. **Nature:** read-only independent adjudication; no gate or node verdict.

## The question

Three independent reports disagreed about the frozen C0 schema's defect set at FROZEN rev28 /
`schemas/af_scc_c0_vacuum.yaml` sha256 `55d0a1ea…`:

| source | line 245 | line 234 | line 151 |
|---|---|---|---|
| worker-008 dual-defect + FORM-SEP-04 X3c | hard | — | hard (×2) |
| worker-058 sweep + rev12 delta cert | hard | hard | — |
| worker-096 F2b review | hard | — | — |

Which of `{245, 234, 151}` are genuine class-contract-**text** defects?

## Measured answer (22/22 declared expectations pass, zero drift)

**F1 · C0:245 — CONFIRMED (hard; premise only).** `forbidden_transfers[0].reason` says
“C2 is a strictly larger extension class”. The file's own `extension_class_containment` (C0:238)
and `one_way_entailments` (C0:240–242) declare `E_C2 ⊂ E_H2loc ⊂ E_C0`, and C0:224 calls C2/C1/H2_loc
claims **weaker** statements. The premise is inverted. The row's *consequence*
(“C2-inextendibility is strictly weaker”) is correct under the chain, so this is a one-token
premise repair (`larger` → `smaller`); the transfer ban itself is unaffected. All five sources agree.

**F2 · C0:234 — CONFIRMED (hard; bucket mislabel).** `forbidden_weakenings` contains
“replacing future by two-sided direction” while `forbidden_strengthenings` (C0:225) contains
“two-sided inextendibility (different, stronger statement)”. Two-sided is strictly stronger, so the
weakenings entry is erroneous, and the sibling C2:232 records the identical item as a repaired
mislabel: *“An earlier revision mislabelled it here as a weakening”* [R2 minor]. Only worker-058
flagged it; the C2 precedent adjudicates in its favour.

**F3 · C0:151 — CONFIRMED PATTERN (hard + scope caveat).** `must_not_conflate[0]` carries the
**live** sentence “No containment with C2 or C0 is asserted here” while C0:238 declares that
containment. The sibling C2:151 records this exact phrasing as *“was wrong”* [R2 major] and replaces
it with the positive nesting sentence; C0 claims the R2 chain correction (C0:14 index-5 delta,
C0:238 [R2 major]) but never received the C2:151 replacement. **Caveat, stated not hidden:** “here”
admits an entry-local reading (no containment asserted *within this entry*). The finding is
stale/unpropagated R2 text, not mathematical falsity. Only worker-008 flagged it.

**F4 · propagation audit.** Of five C2 `[R2]`-adjudicated superseded phrasings, exactly two failed to
propagate into C0 (P1 → F3, P2 → F2); three propagated correctly (P3 chain order, P4 entailment
placement, P5 `dense_escape` label). So the rev6 “containment chain” repair was partial.

## Method and controls

Stdlib-only, read-only, 8 inputs pinned by sha256, re-measured at the end; **drift ⇒ exit 3, no
verdict**. Text operations only (no YAML parser): sections resolved by indentation, `[revision notes]`
and `'quoted prior text'` stripped before scanning live prose. Controls: repaired-C0 synthetic →
all findings clear (sensitivity); inverted-C2 synthetic → chain control trips; C2's live
`must_not_conflate` is denial-free and carries the nesting sentence (specificity); three propagated
comparators stay silent.

## Reproduce

```bash
python3 artifacts/worker-003/c0_contract_consistency/probe_c0_contract_consistency.py   # exit 0, 22/22
```

## Frozen hash table

| artifact | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` | `55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6` |
| `schemas/af_scc_c2_vacuum.yaml` | `5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce` |
| `artifacts/formulation/FROZEN.json` | `2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1` |
| worker-008 dual-defect | `e36a7caba557dffc8c41a053ca77b422ff0745bcf8e711a98069f1d0f2709727` |
| worker-008 FORM-SEP-04 bundle | `eb9e91664bd6dc2a68ebe6a52f7677733ebe67146e7f23364dcfa105bfb88915` |
| worker-058 sweep_rev27 | `db27bfe64e81f9e7a53777692d29aa8cd4bdf6550b401461743f9eba757ce9ee` |
| worker-058 rev12_delta_cert | `a47f68bfd99ddafd050e84d48480baae028e620c3c63e6ba1911ee7456c6751b` |
| worker-096 F2b review | `f48102b3036abf91de313b3dcb35234d1e4862aca34348b16dee4596ddcec89c` |

## Falsifier

Re-run at the pinned hashes. Falsified if any declared expectation fails on identical bytes, the
repaired-C0 control does not go clean, the inverted-C2 control does not trip, or any pin drifts
(drift voids the run). At the next C0 freeze, re-run against the new hash: the three findings should
disappear if the implied repair set (report.json `repair_set_implied`) is applied; a surviving
finding falsifies that repair.

## Authority

Worker evidence only. No gate verdict, no node completion, no `validation_status` promotion.
Repairs are owned by lead-formulation; G-FORM adjudication by astra-lead-audit / astra.

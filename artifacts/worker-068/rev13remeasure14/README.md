# W068-FORM-REV13-REMEASURE-14 — definition-site escapes at the rev13 pin

**Worker:** worker-068 (bounded task, no inbox card). **Node:** A1. **Gate:** G-CLASSBIND
(folded into G-AUDIT as calibration evidence). **Classes:** AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN,
AF-SCC-C0-VAC-GEN. **Status:** measurement complete; no gate verdict, no node transition, no
rule adoption claimed.

Successor task to `W068-FORM-DEFFREEZE-13`, after the CF-20 evidence-binding repair published
rev13 (`d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe`) under FROZEN rev29 (`815e08079aef`).
All earlier worker-068 corpora were built on the archived rev11 shadow bases; this is the first
escape re-measurement against the published rev13 bytes.

## Question

Do the rev13 canonical schemas still accept the four isolated FORM-HELDOUT-08 definition-site
mutation families (`m04` adm-mass-erasure, `m16` containment-reversal, `m25`
completeness-definition-swap, `m29` data-domain-contradiction)?

## Method (pre-registered in `PREREGISTRATION.json` before the run)

| input | pin |
|---|---|
| F1 / F2a / F2b rev13 | `d9cebb9404b2` / `e9a27996dfd3` / `b2ab6acb2bbe` |
| FROZEN rev29 | `815e08079aefbc` |
| F0 canonical taxonomy | `0abb9ed8a961` |
| stage A `check_class_schema.py` | `000e09e46b2f` + KEY_MANIFEST `014e2d301978` |
| stage B `spec_conformance_audit.py` | `c79d8ab8440a` + rule_spec `40f9bb9e657b` |

1. Snapshot all pinned inputs, verify every source hash against the pre-registration, and build
   the corpus from the snapshot only.
2. For each mutation, replace exactly the declared leaf of the rev13 base with the value from
   the corresponding FORM-HELDOUT-08 reference file, and require a structural leaf diff equal to
   exactly that leaf. All four transplanted cleanly (1 changed leaf each).
3. Controls: untouched base, byte-identical identity copy, comment-prepended formatting copy for
   each of the three classes.
4. Run both pinned stages on all 13 fixtures. `escape := stage A pass AND stage B accept`.
   A class arm is informative only if its base and identity control are both accepted.
5. Secondary, proposal-only: the un-adopted R-CAND-D variants (`freeze_contract_min`,
   `freeze_defsites_min`, `freeze_conclusion`, `freeze_meta_only`) on the same corpus.

## Result at the rev13 pin

**C0 arm informative; 3/3 transplanted definition-site mutations escape both stages.**

| fixture | class | mutated leaf | stage A | stage B | escape |
|---|---|---|---|---|---|
| `iso_m04` | C0 | `data_class.adm_mass.sign` | pass | accept | **yes** |
| `iso_m16` | C0 | `implication_ledger.extension_class_containment` | pass | accept | **yes** |
| `iso_m29` | C0 | `quantifiers.domains.D2.definition` | pass | accept | **yes** |
| `iso_m25` | W | `i_plus.completeness_definition` | pass | reject (`R03`) | untestable |

- Base and identity controls for C2 and C0 are accepted by both stages; the formatting controls
  pass too. The measurement is valid at the snapshot pins (no drift, no stage anomaly).
- **The W arm is non-informative at rev13:** stage B rejects the untouched F1 rev13 base on
  `R03` (`binder '(q,t0)' absent from formal sentence`) — the already-recorded HF-071R3-01
  instrument/wording mismatch. No F1 escape claim is made; `iso_m25` is
  `untestable_by_protocol`, not caught.
- So the CF-20/rev13 repair did **not** close the three C0 definition-site escapes under the
  mechanical class-binding stages. This is the first hash-bound calibration datapoint against a
  known-positive corpus at the rev13 pin; it is worker evidence, and the mutation labels still
  need independent adjudication (see limitations).

### Secondary (proposal R-CAND-D, not adopted)

`freeze_contract_min` and `freeze_defsites_min` flag 4/4 transplanted mutations and 0/6
conforming/identity/formatting controls; `freeze_conclusion` (R-CAND-F surface) flags 0/4
mutations, confirming again that a conclusion-statement freeze cannot see this axis. Reported as
a measurement of a proposal, not as an adopted rule.

## Findings

- `W068-R14-F1` — C0 arm informative, 3/3 escapes at rev13 (base/identity accepted).
- `W068-R14-F2` — W arm non-informative at rev13 (F1 base rejected by stage B `R03`).
- `W068-R14-F3` — controls: 0 rejections in informative arms; the two W control rejections are
  the same `R03` as the W base; secondary freeze counts.
- `W068-R14-F4` — per-escape leaf witnesses (path + canonical-value hashes) for independent
  label adjudication.

## Reproduction

```bash
cd <repo>
python3 artifacts/worker-068/rev13remeasure14/build_rev13_corpus.py
python3 artifacts/worker-068/rev13remeasure14/run_rev13_remeasure.py
```

## Non-claims and limitations

- Author-built corpus: the four transplanted mutations are worker-068 labels. An independent
  reviewer must adjudicate each `W068-R14-F4` witness as a genuine class-contract violation
  before the escape counts are cited as detector false negatives. The witness previews and
  canonical-value hashes are in `raw_verdicts.json`.
- The W arm is untestable under this protocol, which is a statement about the instrument+wording
  pair, not about F1's mathematics.
- Stage verdicts are mechanical (stage A R01–R27 with the regenerated KEY_MANIFEST; stage B
  R01–R16 + undecided semantic rules); neither decides mathematics or class truth.
- No gate verdict, node completion, `validation_status=passed`, or rule adoption is claimed.

## Falsifier

Any isolated fixture whose structural diff contains more than the declared leaf; any stage
verdict on the rev13 base differing from the recorded baseline (A pass / B accept for C2 and
C0); any pinned input drift between snapshot and end; a non-transplantable fixture counted as
caught or escaped; any identity or formatting control rejected in an informative arm; or a
live-source hash change during the run that is not reported as drift.

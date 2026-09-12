# W007-F2B-CONTAINMENT-REPAIR-01 — containment-direction adjudication (AF-SCC-C0-VAC-GEN)

Bounded, class-bound worker task taken by `worker-007` (no inbox card exists for this slot).
Independent, hash-pinned, state-independent adjudication of the live F2b containment-direction
blocker at rev13, plus a reusable acceptance predicate for the staged repairs.

**Authority:** worker measurement only. No canonical file, map, node status, `validation_status`
or gate verdict was changed. This is a statement about document bytes and the containment
relation those bytes themselves declare — not a mathematics claim.

## Pins (measured before and after the run; 0 drift)

| path | sha256 (prefix) |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (rev13, reviewed subject) | `b2ab6acb2bbe` |
| `research_map/formulation_taxonomy.yaml` (declared F0) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (F0 supplement) | `d7419b4e8963` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b` |
| `artifacts/formulation/FROZEN.json` (rev29, 50 files) | `815e08079aef` |

Byte-identical copies are under `snapshot/`. The checker reads the snapshots and re-measures the
live paths against the pins, fail-closed.

## Method

The predicate is a function of a document alone (not a diff against a baseline):

1. Parse the document's own frozen containment chain (line 239) and derive the extension-set
   order `E_C2 ⊂ E_{C^{1,1}} ⊂ E_H2loc ⊂ E_C0`; cross-check it against the F0 supplement's
   `axis_registry.regularity_axis.containment`.
2. Locate every **live** containment denial (`No containment with ...`) in
   `regularity.must_not_conflate`, skipping quoted/withdrawn mentions ("earlier ... was wrong",
   "corrected from") — the CF-16 metalinguistic-mention pattern.
3. Locate every `larger|smaller|stronger|weaker extension class` premise, resolve its subject and
   comparison target from the row endpoints (or an explicit parenthetical), and test it against
   the derived order. (Statement strength runs opposite to set size: the larger the extension
   set, the stronger the "no proper future X extension" statement.)
4. Re-derive every `one_way_entailments` row direction and require the forbidden
   C2 → this-class transfer row to be present.
5. Check R06 (`must_not_conflate` non-empty) and R11 (`conclusion_type` == frozen
   `rule_spec.vocabularies.class_conclusion_type[AF-SCC-C0-VAC-GEN]`).

Verdict: `REPAIR_OK` iff every check passes; otherwise `REPAIR_OPEN` with itemised findings.

## Result — live document `b2ab6acb2bbe`: `REPAIR_OPEN`

| check | result |
|---|---|
| C1 chain matches frozen order | PASS |
| C2 no live containment denial | **FAIL** |
| C3 no false "larger class" premise | **FAIL** |
| C4 one-way entailments consistent (4 rows) | PASS |
| C5 forbidden C2 → this-class row present | PASS |
| C5b R06 `must_not_conflate` non-empty | PASS |
| C6 R11 `conclusion_type` matches rule_spec | PASS |
| C7 class identity / sibling disjointness | PASS |

- **F1 — `regularity.must_not_conflate[0]`, line 152:** `"No containment with C2 or C0 is
  asserted here"` contradicts the same document's line 239 chain. A strictly metalinguistic
  reading of "here" is grammatically available (and would make the sentence true of the bullet),
  but it sits in a normative list and is unsafe as written; three independent reviewers read it
  as a live denial (worker-066 H2, worker-017 B17-R13-02, worker-018 B1).
- **F2 — `implication_ledger.forbidden_transfers[0].reason`, line 246:** `"C2 is a strictly
  larger extension class, so C2-inextendibility is strictly weaker"` — the premise is inverted
  (E_C2 is the *smallest* set). The normative rule (no transfer from C2-inextendibility to this
  class) and the conclusion "strictly weaker" are correct; only the stated premise is false.

The class definition, conclusion, genericity, quantifiers and the four one-way entailments are
**unaffected**; both defects are local wording repairs in normative slots.

## Candidate adjudication (advisory; candidates are non-canonical staged files)

| candidate | measured sha256 | verdict | residual |
|---|---|---|---|
| `artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml` | `a110f8e875af` | `REPAIR_OK` | — |
| `artifacts/worker-044/f2b_rev13_integration/sandbox/schemas/af_scc_c0_vacuum.yaml` | `48cadb72e507` | `REPAIR_OK` | — |
| `artifacts/worker-044/f2b_acceptance_oracle/sandbox/schemas/af_scc_c0_vacuum.yaml` | `3ab16da27e7b` | **`REPAIR_OPEN`** | still carries both defects (line 286 denial, line 502 inverted premise) |

The third row is a genuine catch: a file in the acceptance-oracle path still asserts
`C2 is a strictly larger extension class` and still carries the live denial, despite its name.
A repair acceptance test that reads that file would accept an unfixed document.

## Controls (6/6 pass, in-memory only)

| control | expectation | observed |
|---|---|---|
| K1 inject the worker-022 corrected wording + corrected reason | `REPAIR_OK` | `REPAIR_OK` |
| K2 invert the document chain | chain check fails | fails |
| K3 delete the forbidden C2 → this-class row | C5 fails | fails |
| K4 empty `must_not_conflate` | R06 fails | fails |
| K5 alias `strong_cosmic_censorship_C0` token | R11 fails | fails |
| K6 re-inject the inverted premise | C3 fires | fires |

## Reuse

```bash
python3 artifacts/worker-007/f2b_containment_repair/verify_f2b_containment.py --emit \
    --generated-at <ISO-8601>
```

`report.json` is deterministic for a fixed `--generated-at` (verified byte-identical across two
runs). After the canonical rev14 lands, run the predicate on the new bytes: `REPAIR_OK` with the
six controls passing closes this task's question.

## Falsifier

At the same pins: (a) a re-reading under which the F2b `must_not_conflate[0]` denial is true of
the whole document (i.e. the document asserts no containment anywhere), or under which
"C2 is a strictly larger extension class" is true of the document's own order; (b) any pinned
input whose live bytes no longer measure the declared hash; (c) a repair candidate this
predicate passes while an independent reader finds an inverted containment sentence in it;
(d) a control that fails to fire as declared. A later revision of F2b supersedes — does not
falsify — this measurement.

## Non-claims and credit

- No gate verdict, no node status, no `validation_status=passed`; the audit lead and controller
  own those.
- Candidate verdicts are advisory measurements of staged files and authorise no promotion.
- The `conclusion_type` alias direction (`scc_*` canonical in rule_spec/VOCAB_ALIASES vs
  `strong_cosmic_censorship_*` in the F0 `field_vocabulary`) is recorded as an INFO
  cross-reference only; worker-048 `W48-GFORM-VOCAB-ADJUDICATION-01` already adjudicates it.
- Prior art credited: worker-066 (H1/H2), worker-017 (B17-R13-01/02), worker-018 (B1/B2),
  worker-075 (VOCAB/LARGER), worker-022 and worker-044 (repair candidates).

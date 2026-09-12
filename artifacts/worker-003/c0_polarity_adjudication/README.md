# W003-C0-POLARITY-ADJUDICATION-01 — independent adjudication of the `c0_03_conclusion_negated` escape

Actor `worker-003`, class `AF-SCC-C0-VAC-GEN`, node A1, gate `G-CLASSBIND` (calibration
evidence folded into G-AUDIT). Read-only with respect to every artifact it measures; all
outputs live under `artifacts/worker-003/c0_polarity_adjudication/`.

## The question

Blocker `w068-hel09r-13-blocker` (worker-068, 00:30) reports that the FORM-HELDOUT-09
two-stage class-binding pipeline accepts fixture `c0_03_conclusion_negated` and asks for an
independent reviewer (not worker-068) to adjudicate it. This artifact answers two questions:

1. Is the fixture a genuine class-contract violation, or a labelling artifact?
2. Does a minimal, independently implemented content-polarity check catch it without false
   positives on conforming inputs?

## Verdict

**CONFIRMED_BLIND_SPOT.** Both questions answer yes at the pinned hashes.

**The defect, measured.** A leaf-level semantic diff of the frozen rev11 base
`bases/af_scc_c0_vacuum.yaml#1bb78ce9b357` against the fixture `#1e8898ac7bad` yields exactly
two changed leaves, both in `conclusion`:

| field | frozen base | fixture |
|---|---|---|
| `statement_formal` | `... not exists proper_future_extension_in_class(MGHD(D))` | `... exists a proper future C0 metric extension of the maximal development` |
| `statement_natural_language` | `... future-inextendible as a continuous Lorentzian manifold.` | `... admit a maximal development with a proper future C0 metric extension.` |

`conclusion_type` stays `scc_c0_future_inextendibility`; `quantifiers.formal`,
`quantifiers.negation` and `quantifiers.negation_normal_form` stay in the canonical
non-existence form. The schema therefore asserts its own declared negation while carrying the
inextendibility token.

**Why the pipeline missed it.** `raw_verdicts.json#3fe7499bfc12` records the corpus-time
result: structural `exit 0 / pass`, semantic `exit 0 / accept`, `escaped_union: true`. The
rule that was expected to catch it (R11) checks `conclusion_type` against the class
vocabulary, and that token is unchanged. Nothing in the rule spec compares the polarity or
content of the conclusion statements with `conclusion_type`, `quantifiers.formal` or
`quantifiers.negation_normal_form`.

**The candidate check.** Four content criteria, all decided by one transparent lexical
polarity classifier with a declared trigger vocabulary and an explicit `undecided` outcome:

* C1 — statement polarity equals the polarity implied by the `conclusion_type` token;
* C2 — statement polarity equals `quantifiers.formal` polarity;
* C3 — statement polarity is the opposite of `quantifiers.negation_normal_form` polarity;
* C4 — statement polarity equals the nearest frozen class base's polarity.

The fixture disagrees with all eight decidable criteria (both statement fields × four
criteria); the base, the live rev12 canonical, the repair control and the negation-preserving
paraphrases agree.

## Controls and specificity (all re-runnable)

| control | expected | observed |
|---|---|---|
| rev11 base, live rev12 canonical | no flag | no flag |
| 4 conforming corpus controls | no flag | no flag |
| mutant `c0_03` | flag | flag |
| repair (two statement fields restored) | no flag | no flag |
| independently authored inversion (new wording) | flag | flag |
| negation-preserving paraphrase | no flag | no flag |
| two-sided classifier sanity (positive / negative) | flag / no flag | flag / no flag |
| specificity sweep, all 49 corpus fixtures | exactly 1 flag | 1 flag (`c0_03`) |

18/18 probe expectations pass; the sweep is silent on the other 48 fixtures (the WCC rows are
`undecided` for this vocabulary, not checked: their conclusions do not mention an extension).

## Second finding — the escape is currently masked, not fixed

`KEY_MANIFEST.json` is a live dependency of both stage verdicts but is **not pinned** by the
corpus manifest. It moved at `2026-09-12T00:34:42+08:00` (`#014e2d301978`), after the 00:22
corpus build and the 00:29 replication. A live re-run of the pinned structural stage now
rejects **both** the rev11 base and the mutant with `R22: unknown key ['revised_at_unused']`,
and rejects the conforming C0 control too. The live semantic stage still accepts the mutant
(`exit 0`). So the recorded accept is no longer reproducible end-to-end; the C0 rev11 family
is failing structurally for a reason unrelated to polarity. This must not be read as a fix.
The polarity adjudication itself stands on the pinned YAML bytes and the pinned rule spec.

## Scope and limits

* Structure/semantics of frozen bytes only. No physics, no mathematics, no class truth, no
  node completion, no gate verdict; worker events cannot set `done`/`passed`.
* The classifier decides only statements that mention extension/extendibility vocabulary; a
  polarity inversion phrased without it is `undecided`, not caught. It is a candidate rule
  extension (R11+), not an implementation of FORM-RULE-SPEC and not a replacement for review.
* Silent on WCC/C2 fixtures in the sweep means "undecided", not "verified".

## Falsifiers

* Re-run either frozen stage at the pinned hashes on the pinned fixture and get a rejection,
  or a semantic diff showing a change outside the two conclusion statement leaves: falsifies
  W003-PA-01.
* Show a rule-spec/gate revision already comparing conclusion content polarity: falsifies
  W003-PA-02.
* Any control in the matrix with a flag different from its declared expectation, or any
  swept fixture other than `c0_03` flagged: falsifies W003-PA-03.
* Any input hash drift (>0): the probe exits 3 without a verdict (re-run, not falsified).

## Frozen inputs

| input | sha256 |
|---|---|
| fixture `mutants/c0_03_conclusion_negated.yaml` | `1e8898ac7bad1b7db81961e9d27b05cc7e7ef8562d5c89a53c1e4a1afeea1f36` |
| base `bases/af_scc_c0_vacuum.yaml` (rev11) | `1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508` |
| structural stage `check_class_schema.py` | `000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff` |
| semantic stage `spec_conformance_audit.py` | `c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec` |
| rule spec `rule_spec.json` | `40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e` |
| corpus manifest / raw verdicts | `72c0353ad0de617adeb6f68fc5ad232886b30b3d2a998aa354fbbe9d0a854b18` / `3fe7499bfc12…` |
| live canonical `schemas/af_scc_c0_vacuum.yaml` (rev12, not pinned) | `b71ec02c601ddebf20511fd86b82754bfefe19fe3e759c8eab3d262f61172d5f` |

## Reproduce

```bash
python3 artifacts/worker-003/c0_polarity_adjudication/adjudicate_c0_polarity.py \
  --out artifacts/worker-003/c0_polarity_adjudication/report.json \
  --blindspot-out artifacts/worker-003/c0_polarity_adjudication/blindspot_entry.json
# exit 0 = all 18 expectations pass; 1 = expectation violated; 3 = input drift (no verdict)
```

Probe `adjudicate_c0_polarity.py#c769a71aecfe`, report `report.json#074394fe23ea`,
proposed blind-spot entry `blindspot_entry.json#c8a09a51e40b`.

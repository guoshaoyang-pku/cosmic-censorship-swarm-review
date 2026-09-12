# W076-F2B-LANDING-AUDIT-02 — F2b repair-candidate landing audit (AF-SCC-C0-VAC-GEN)

Bounded, class-bound worker task taken by `worker-076` (no inbox card exists for this slot).
Node `F2b`, class `AF-SCC-C0-VAC-GEN`, gate `G-FORM`.

**Question.** Two staged repairs of the live F2b containment defects are recorded as
`REPAIR_OK` by worker-007's containment predicate
(`artifacts/worker-007/f2b_containment_repair/report.json`): worker-022's minimal candidate
`a110f8e875af` and worker-044's integration candidate `48cadb72e507`. Which of them can be
promoted to the canonical path `schemas/af_scc_c0_vacuum.yaml` **without re-opening an
already-closed hard failure** and **without violating the FROZEN change protocol**?

**Method.** An independent checker (`audit_f2b_repair_candidates.py`, not derived from
worker-007's predicate) reads byte snapshots of every input, measures live hashes before and
after the run (0 drift), and evaluates 12 checks: class identity; both containment defects
(mention-aware); the `f0_binding` evidence/F0/supplement pins against live bytes; the FROZEN
change protocol; a metalinguistic self-contradiction test on the repaired bullet; line-diff
minimality against live; and the vocabulary-binding advisory. It additionally runs the
lead-owned conformance tool `artifacts/formulation/tools/check_class_schema.py` on every
target, and an R22 escape-hatch probe.

## Pins (measured, byte-identical snapshots under `snapshot/`)

| path | sha256 (prefix) |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (live rev13, subject) | `b2ab6acb2bbe` |
| `artifacts/formulation/evidence/taxonomy_consistency.json` (live) | `9e335e9ba1bf` |
| `research_map/formulation_taxonomy.yaml` (declared F0) | `0abb9ed8a961` |
| `artifacts/formulation/formulation_taxonomy.yaml` (F0 supplement) | `d7419b4e8963` |
| `artifacts/formulation/rule_spec.json` | `40f9bb9e657b` |
| `artifacts/formulation/VOCAB_ALIASES.json` | `46cd9f1eb534` |
| `artifacts/formulation/FROZEN.json` (rev29, 50 files) | `815e08079aef` |
| `artifacts/formulation/tools/check_class_schema.py` | `000e09e46b2f` |

## Verdicts

| target | sha256 (prefix) | verdict | blockers |
|---|---|---|---|
| live rev13 | `b2ab6acb2bbe` | NOT_PROMOTION_READY | F1 denial (line 152) + F2 inverted premise (line 246) |
| C022 minimal | `a110f8e875af` | NOT_PROMOTION_READY | **no revision bump** (same-revision byte move, CF-27); **metalinguistic self-contradiction**: the bullet *uses* "strictly between" as live text and then says the phrase "is not used" |
| C044 integration | `48cadb72e507` | NOT_PROMOTION_READY | **binding regression**: reverts `f0_binding.consistency_evidence_sha256` to `675a99d0…`, re-opening `W007-RP-HF-01` at live `9e335e9b…`; bumps `revision: 14` with **no revision_history entry** |
| C044 acceptance oracle | `3ab16da27e7b` | NOT_PROMOTION_READY | both live defects still present; stale evidence pin; 596 unclassified diff lines |
| **composite (staged)** | `940e54ad226c` | **PROMOTION_READY** | none (see checklist) |

The lead-owned conformance tool returns `pass` on **all five** targets, including the live
rev13 document and the stale oracle. That is expected — it does not implement the
containment-direction predicate — and it is why the review layer, not the schema gate, is
load-bearing here. The tool's only rejection in this audit is the R22 probe below.

## Findings

- **F1 — the two staged candidates are not interchangeable.** worker-007's predicate scores
  both `REPAIR_OK` because both fix the two containment slots. Against the live binding chain
  they diverge: C022 is semantically clean but protocol-incomplete; C044 is
  protocol-ready in revision number but silently reverts the rev13 evidence-binding repair.
  Promoting C044 as staged would re-open a hard failure that the lead already closed
  (`astra-life05-evidence-binding-repair`, rev13 delta note, line 20 of the live schema;
  reviewer `W007-RP-HF-01`).
- **F2 — C022's line-152 wording is self-contradictory.** It writes "...sits strictly between
  the C0 endpoint class and the C2 endpoint class..." and then "...the informal phrase
  'strictly between' is not used and must not be cited...". A normative `must_not_conflate`
  list should not assert P and "P's phrasing is not used". C044's wording avoids this by
  saying the phrase "is not a class definition".
- **F3 — worker-088's binding-completeness repair must not go under `f0_binding`.**
  `class_contract_supplement_sha256` is absent from `artifacts/formulation/KEY_MANIFEST.json`,
  and the R22 walk is a recursive flat allowlist. The probe
  `probe/f0_binding_naive_supplement_sha_probe.yaml#b2ed62f6f1ce` (live bytes plus that one key)
  is rejected by the lead's own tool with `failed_rules=['R22']`. The field must be placed
  under the documented `extensions:` escape hatch (the composite does exactly that).
- **F4 — the composite is promotion-ready.** `candidate/af_scc_c0_vacuum.repair-minimal.yaml`
  takes C044's line-152 wording (bracket omitted; revision_history carries the record), both
  candidates' line-246 correction, `revision: 14` + `revision_history[index 12]`, keeps the
  live `9e335e9b` evidence pin, and adds `extensions.binding_completeness` /
  `extensions.vocabulary_binding` pinned to the live supplement and alias-registry hashes.

## Promotion checklist for the lead (promotion is lead-owned)

1. Re-measure the pins above; if any moved, re-run the audit (verdicts are pinned).
2. Apply the composite's five changed semantic/protocol slots to the canonical path, or
   equivalent wording that satisfies B/C/G/H.
3. Regenerate `artifacts/formulation/FROZEN.json` (new F2b sha, revision bump) and re-run
   `check_class_schema.py` + `check_taxonomy_consistency.py`; refresh any declared
   `consistency_evidence_sha256` if the checker rewrites that file.
4. Dispatch two independent accept reviewers at the **new** hash; do not bind verdicts to
   `b2ab6acb2bbe`, `a110f8e875af` or `48cadb72e507`.

## Limits / authority

Worker measurement only. No canonical file, map node, `validation_status`, gate verdict or
node status was changed; the composite is staged and explicitly non-canonical. This is a
statement about bytes and declared bindings, not a mathematical claim about cosmic
censorship. Nothing here authorises promotion.

## Falsifier

At the pinned snapshots: (a) any candidate marked NOT_PROMOTION_READY passing every check
under an independent re-implementation at the same bytes; (b) the composite passing while any
changed line falls outside the classified repair slots; (c) live
`taxonomy_consistency.json` measuring other than `9e335e9b…` at the declared `checked_at`,
which would void finding F1 against C044; (d) `check_class_schema.py` returning `pass` on the
R22 probe.

## Reproduce

```bash
cd <repo root>
python3 artifacts/worker-076/f2b_repair_landing_audit/audit_f2b_repair_candidates.py
```

`run_stdout.txt` is the captured output of the recorded run; `SHA256SUMS` pins every
deliverable.

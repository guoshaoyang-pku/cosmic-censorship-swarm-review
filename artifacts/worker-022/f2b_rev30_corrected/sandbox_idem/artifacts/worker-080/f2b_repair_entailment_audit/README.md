# W080-F2B-REPAIR-H2E-01 — repair-introduced entailment inversion in the F2b repair candidate

Worker: `worker-080` · Node: `F2b` · Class: `AF-SCC-C0-VAC-GEN` · Gate: `G-FORM` · Read-only on every canonical path.

## One-line result

The circulating 2-edit F2b repair (`84b5d3fa`, pushed by worker-066 as the rebased candidate and by
worker-08 as `artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml`) fixes H1 but
**introduces a new hard defect**: its H2 replacement asserts `H2_loc-inextendibility ENTAILS this
class's conclusion` inside the **C0** file, which contradicts F2b's own containment chain and its own
`forbidden_weakenings` row. **Do not land it as-is.** Two finding-free corrected candidates are staged.

## Live state audited (all pinned)

| artifact | sha256 |
|---|---|
| `schemas/af_scc_c0_vacuum.yaml` (live F2b rev13) | `b2ab6acb2bbe7f86…` |
| `artifacts/formulation/schemas/af_scc_c0_vacuum.yaml` (mirror, byte-identical) | `b2ab6acb2bbe7f86…` |
| `artifacts/formulation/FROZEN.json` (rev29, declares the above) | `815e08079aefbc16…` |
| `schemas/af_scc_c2_vacuum.yaml` (C2 sibling) | `e9a27996dfd308bd…` |
| `artifacts/formulation/rule_spec.json` (R06/R16) | `40f9bb9e657b2c6b…` |
| repair candidate (worker-066 rebased = worker-08 candidate) | `84b5d3fa29a677ad…` |
| worker-008 reference candidate | `98f9ec83c487d692…` |

The two live defects H1/H2 are already established by worker-017 and worker-066 and are **not**
re-litigated here: H1 = inverted size premise at `implication_ledger.forbidden_transfers[0].reason`
(`:246`), H2 = false containment denial at `regularity.must_not_conflate[0]` (`:152`).

## The new finding (about the repair, not about live bytes)

F2b's own chain at `:239` is `E_C0 ⊇ E_H2loc ⊇ E_{C^1,1} ⊇ E_C2`, and `:241`–`:243` derive
`C0-inext ⇒ H2loc-inext ⇒ C2-inext`. Therefore the C0 class conclusion **entails**
H2_loc-inextendibility, and H2_loc-inextendibility entails the **C2 sibling's** conclusion — not this
class. F2b `:232` says exactly that: *"substituting H2_loc for C0 (H2_loc-inextendibility is weaker and
entails the C2 sibling, not this class)"*.

The candidate's H2 replacement (line `:152`) says the opposite:

> … so **H2_loc-inextendibility ENTAILS this class's conclusion** …

Inside the C0 file this is a repair-introduced inversion of the very direction the repair was meant to
restore. It is a near-verbatim copy of the C2 sibling's sentence at `schemas/af_scc_c2_vacuum.yaml:152`,
which is **true in the C2 file and false in the C0 file** — the truth of the sentence is class-relative
because of the phrase "this class".

Findings emitted by the harness:

| id | severity | line | carrier |
|---|---|---|---|
| `entailment_direction_inverted` | hard | 152 (candidate) | `regularity.must_not_conflate[0]` claim `H2loc-inext ⇒ C0-inext` not in the chain closure |
| `normative_contradiction` | hard | 232 (retained) | repaired clause contradicts the retained `forbidden_weakenings` row |

The canonical structural gate `check_class_schema.py#000e09e4` returns **PASS** for live, for the
defective candidate, and for both corrected candidates: the defect is **not machine-detectable by the
binding gate** (blindness re-measured, consistent with worker-017 CHK-15).

## Corrected repair candidates (staged, owner may adopt)

| file | sha256 | H2 wording | findings | gate |
|---|---|---|---|---|
| `staged/candidate_corrected.yaml` | `51c253c463067e25…` | explicit right direction (`this class's conclusion ⇒ H2loc-inext; H2loc-inext ⇒ C2 sibling`) | none | PASS |
| `staged/candidate_nesting_only.yaml` | `4951cc9698032996…` | nesting + pointer only, no entailment claim | none | PASS |

`repair_patch_corrected.diff` is the minimal diff from live to `candidate_corrected.yaml` (two leaf
lines only; H1 edit identical to the circulating repair). Owner (`astra-lead-formulation`) retains all
canonical writes: land one H2 wording, bump revision, mirror, re-freeze; then re-run this harness and
`rebind.py`.

## How to reproduce / falsify

```bash
python3 artifacts/worker-080/f2b_repair_entailment_audit/audit_h2_entailment.py
```

Deterministic, stdlib-only, fails closed on pin drift; `report.json` is regenerated. The audit is
falsified by: the chain admitting `H2loc-inext ⇒ C0-inext`; the retained `:232` row being read as
consistent with the candidate H2 sentence; the same claim string not being allowed for `own=C2` (which
would make the checker class-blind); either corrected candidate yielding a finding or failing the gate;
or any pinned byte moving.

## Controls (9/9 matched, pre-registered)

`K1` live → `{size_premise_inverted, false_containment_denial}` · `K2` candidate `84b5d3fa` →
`{entailment_direction_inverted, normative_contradiction}` · `K3` reference `98f9ec83` → same ·
`K4` corrected → ∅ · `K5` nesting-only → ∅ · `K6` C2 sibling's own sentence under `own=C2` → ∅
(class-relative control) · `K7` C2 with the direction reversed under `own=C2` →
`{entailment_direction_inverted}` · `K8` candidate with the claim deleted → ∅ · `K9` live with H1 fixed
only → `{false_containment_denial}`.

## Not claimed

No canonical write; no gate verdict; no node status; no `validation_status=passed`; no mathematical
claim about C0/C2 inextendibility; no claim that workers 017/066/08 missed the live defects they found —
this is about the repair text, which their taxonomies do not cover.

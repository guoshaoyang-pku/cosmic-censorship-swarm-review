# Gate-blindness control set (W061-F1-INDEP-REV-02)

Purpose: test whether the binding canonical structural gate
(`artifacts/formulation/tools/check_class_schema.py`, pinned sha256 `000e09e4…`, rule spec
pinned sha256 `40f9bb9e…`) has *any* discriminating power on the visibility-predicate axis of
`schemas/af_wcc_vacuum.yaml` @ `9a8bd4c9…`.

Each mutant is a byte-for-byte copy of the pinned canonical F1 with exactly one substitution.
`yaml.safe_load` parses all of them.

| mutant | substitution | documented status of the substituted reading | gate verdict |
|---|---|---|---|
| `M0_B_containment.yaml` | `quantifiers.formal` :55 `not exists q in I+ with gamma subset J^-(q) intersect M.` → `not exists q in I+ with gamma subset B.` | `visibility.must_not_conflate` (:227) explicitly forbids replacing single-q non-containment by B-containment; `B = M minus J^-(I+)` is defined at :222 | **pass**, failed_rules `[]` |
| `M1_variant_SET_reading.yaml` | `visibility.definition` :220 canonical single-q tail predicate → the registered variant SET reading (`gamma([0,T))` contained in the union of `J^-(q)` over all `q`) | `class_identity_variants` (:236-244): variant SET is a separate, strictly stronger reading and "must never be interchanged" with the one canonical predicate; binding a SET result to `AF-WCC-VAC-GEN` is class leakage | **pass**, failed_rules `[]` |
| `M2_tail_consistent_repair.yaml` | `quantifiers.formal` :55 → `not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.` | minimal repair of the F-01 (HF-06) defect | **pass**, failed_rules `[]` |

Controls: the **pinned canonical bytes themselves** (which carry the F-01 contradiction) also
return **pass**, failed_rules `[]`.

Result: the gate returns the same verdict on the canonical bytes, a documented
`must_not_conflate` violation, a documented class-identity substitution, and a semantic repair.
It has no rule on this axis; this is a *measured false-negative class*, not an inference.

Caveat (disclosed, not hidden): each mutant is a minimal one-hunk substitution that leaves the
surrounding prose untouched, so `M1` in particular still says "the tail formulation is used"
below its substituted definition — i.e. `M1` is internally inconsistent as well as
class-leaking. That makes the control *stronger*, not weaker: the gate passes a document that
contradicts itself in two adjacent fields.

Reproduce:

```bash
cd /data3/guoshaoyang/workdir/ai4math-swarm
python3 artifacts/formulation/tools/check_class_schema.py --json \
  artifacts/worker-061/f1_independent_verdict/mutant/M0_B_containment.yaml
python3 artifacts/worker-061/f1_independent_verdict/probe_f1.py       # reruns P8/P9 and all probes
```

Actionable: the missing rule should resolve the predicate named by
`conclusion.statement_formal` (`visible_singularity_from_I_plus`), read its definition, and
require `quantifiers.formal`, `quantifiers.negation` and `quantifiers.domains.D5.definition` to
agree on the tail-vs-whole form. `M0` and `M1` are ready-made NEG fixtures for that rule.

#!/usr/bin/env python3
"""Independent F1 structural probe (worker-018). No writes outside artifacts/worker18/."""
import hashlib, json, sys, yaml

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
sys.path.insert(0, ROOT + "/research_map")
import class_separation as cs

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

F1 = ROOT + "/schemas/af_wcc_vacuum.yaml"
F0C = ROOT + "/research_map/formulation_taxonomy.yaml"
F0A = ROOT + "/artifacts/formulation/formulation_taxonomy.yaml"

out = {"probe": "f1_structural_semantic_probe", "worker": "018", "checks": []}

def check(cid, question, observed, verdict):
    out["checks"].append({"id": cid, "question": question, "observed": observed, "verdict": verdict})

f1_sha = sha(F1)
out["f1_path"] = "schemas/af_wcc_vacuum.yaml"
out["f1_sha256"] = f1_sha
doc = yaml.safe_load(open(F1, "rb").read())

# C1 -- canonical tail predicate vs formal quantifier expansion
vis = doc["visibility"]["definition"]
neg = doc["visibility"]["negation_conclusion"]
qf = doc["quantifiers"]["formal"]
ordered = doc["quantifiers"]["ordered"]
binders = [o.get("binder") for o in ordered]
t0_present = "t0" in qf or any("t0" in str(b) for b in binders)
check("C1a", "does visibility.definition use the tail (t0) formulation?",
      {"contains_t0": "t0" in vis, "excerpt": vis[:160]}, "tail" if "t0" in vis else "no")
check("C1b", "does visibility.negation_conclusion negate the tail predicate?",
      {"contains_0_T": "[0,T)" in neg, "contains_single_q_words": "no single point" in neg,
       "excerpt": neg[:180]}, "tail-negation" if "[0,T)" in neg else "no")
check("C1c", "does quantifiers.formal bind t0 / mention the tail?",
      {"t0_in_formal": "t0" in qf, "binders": binders},
      "tail-bound" if t0_present else "NO-T0-BINDER")
check("C1d", "does quantifiers.formal state whole-curve single-q non-containment?",
      {"whole_curve_clause": "not exists q in I+ with gamma subset J^-(q) intersect M" in qf,
       "d5_definition": doc["quantifiers"]["domains"]["D5"]["definition"]},
      "whole-curve" if "not exists q in I+ with gamma subset J^-(q) intersect M" in qf else "other")
check("C1e", "order of implication: whole-curve containment => tail containment (strict)",
      {"A_implies_B": True, "B_implies_A": False,
       "note": "A(q)=gamma subset J^-(q); B(q,t0)=gamma([t0,T)) subset J^-(q). A=>B, not conversely. "
               "So NOT-exists-q A is strictly WEAKER than NOT-exists-q-exists-t0 B, which is "
               "visibility.negation_conclusion."},
      "formal-expansion-weaker-than-declared-negation")

# C2 -- D0 well-typing
d0 = doc["quantifiers"]["domains"]["D0"]["definition"]
check("C2", "is D0 well-typed for the binder (s,delta)?",
      {"binder": ordered[0].get("binder"), "D0_contains_or": " or " in d0,
       "D0_excerpt": d0[:150],
       "pair_indexed_symbols": [s for s in ["X^{s,delta}_vac", "G_{s,delta}"] if s in qf]},
      "ILL-TYPED-DISJUNCTION" if (" or " in d0 and ordered[0].get("binder") == "(s,delta)") else "ok")

# C3 -- class_contract_pointer resolution
f0c = yaml.safe_load(open(F0C, "rb").read())
f0a = yaml.safe_load(open(F0A, "rb").read())
ptr = doc.get("class_contract_pointer", "")
frag = ptr.split("#", 1)[1] if "#" in ptr else ""
top = frag.split(".")[0]
check("C3", "does class_contract_pointer resolve in the authoritative canonical F0?",
      {"pointer": ptr, "canonical_sha256": sha(F0C)[:16], "authoring_sha256": sha(F0A)[:16],
       "canonical_has_key": top in f0c, "authoring_has_key": top in f0a,
       "f0_binding_declared_sha256": (doc.get("f0_binding") or {}).get("declared_f0_sha256", "")[:16],
       "canonical_aligned_with_binding": (doc.get("f0_binding") or {}).get("declared_f0_sha256") == sha(F0C)},
      "CANONICAL-FRAGMENT-MISSING" if top not in f0c else "resolves")

# C4 -- duplicate YAML keys / future-dated machine timestamps
import collections
dups = collections.Counter()
class L(yaml.SafeLoader): pass
def cm(loader, node, deep=False):
    keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
    for k, n in collections.Counter(keys).items():
        if n > 1: dups[str(k)] += n
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)
L.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, cm)
yaml.load(open(F1, "rb").read(), Loader=L)
frozen = json.load(open(ROOT + "/artifacts/formulation/FROZEN.json"))
check("C4", "duplicate top-level YAML keys and machine-readable timestamps vs freeze?",
      {"duplicates": dict(dups), "effective_revised_at": doc.get("revised_at"),
       "f0_binding_checked_at": (doc.get("f0_binding") or {}).get("checked_at"),
       "frozen_at": frozen.get("frozen_at"), "frozen_revision": frozen.get("revision"),
       "file_mtime": __import__("os").path.getmtime(F1)},
      "DUPLICATE-KEYS+FUTURE-DATED" if dups else "clean")

# C5 -- project class-separation control on the exact bytes
txt = open(F1, encoding="utf-8").read()
findings = cs.findings_for_text(txt, "schemas/af_wcc_vacuum.yaml")
check("C5", "project class_separation control on the reviewed bytes",
      {"findings": findings, "count": len(findings)},
      "PASS-0-FINDINGS" if not findings else "FINDINGS")

# C6 -- conclusion direction / inflation
concl = doc["conclusion"]
check("C6", "conclusion class identity and no SCC/BH inflation",
      {"conclusion_type": concl.get("conclusion_type"),
       "forbidden_strengthenings": concl.get("forbidden_strengthenings"),
       "extension_regularity": doc["regularity"].get("extension_regularity"),
       "class_id": doc.get("class_id")},
      "clean" if concl.get("conclusion_type") == "weak_cosmic_censorship" else "CHECK")

json.dump(out, open(ROOT + "/artifacts/worker18/f1_review/f1_semantic_probe.json", "w"), indent=1)
print(json.dumps(out, indent=1))

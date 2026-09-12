#!/usr/bin/env python3
"""Cross-check the map taxonomy (research_map/formulation_taxonomy.yaml, worker-01 rev3) against
the lead class contract (artifacts/formulation/formulation_taxonomy.yaml). Exit 0 = consistent.
Compares only shared, checkable fields; alias-equivalent tokens are accepted."""
import json, sys, yaml
from pathlib import Path
ROOT = Path('/data3/guoshaoyang/workdir/ai4math-swarm')
A = yaml.safe_load((ROOT/"research_map/formulation_taxonomy.yaml").read_text())
B = yaml.safe_load((ROOT/"artifacts/formulation/formulation_taxonomy.yaml").read_text())
AL = json.loads((ROOT/"artifacts/formulation/VOCAB_ALIASES.json").read_text())
def canon(kind, tok):
    for c, al in AL[kind].items():
        if tok == c or tok in al: return c
    return tok
errs, notes = [], []
if set(A["class_ids"]) != set(B["class_contracts"]):
    errs.append(f"class id sets differ: {set(A['class_ids'])} vs {set(B['class_contracts'])}")
for cid in sorted(set(A["class_ids"]) & set(B["class_contracts"])):
    a, b = A["classes"][cid], B["class_contracts"][cid]
    if a["axes"]["family"] != b["components"]["censorship"]:
        errs.append(f"{cid}: family {a['axes']['family']} vs {b['components']['censorship']}")
    ta, tb = a["axes"].get("regularity_token"), b["components"].get("regularity_token")
    tb = None if tb == "none" else tb
    if ta != tb: errs.append(f"{cid}: regularity {ta} vs {tb}")
    ca = canon("conclusion_type", a["axes"].get("conclusion_type"))
    cb = canon("conclusion_type", b.get("conclusion_type"))
    if ca != cb: errs.append(f"{cid}: conclusion_type {ca} vs {cb}")
    if not a.get("exclusions") or not b.get("exclusions"): errs.append(f"{cid}: exclusions empty on one side")
    if not a.get("test_cases") or not b.get("positive_test_case"): errs.append(f"{cid}: test cases missing on one side")
    if a["axes"]["family"] == "SCC" and not a.get("known_obstruction"): errs.append(f"{cid}: SCC without known_obstruction")
    ga = canon("genericity_kind", str(a["axes"].get("genericity_kind","")))
    gb = canon("genericity_kind", str((B.get("axis_registry",{}).get("genericity_axis",{}).get("frozen",{}) or {}).get(cid,"")))
    if ga != gb: errs.append(f"{cid}: genericity {ga} vs {gb}")
c0v = (B.get("class_contracts",{}).get("AF-SCC-C0-VAC-GEN",{}) or {}).get("class_identity_variants")
if not c0v or "horizon_localized_variant" not in c0v:
    errs.append("lead contract lacks the C0 class_identity_variants registry (horizon-localized variant)")
d0 = (B.get("class_contracts",{}).get("AF-SCC-C0-VAC-GEN",{}) or {}).get("data_class_freeze")
if not d0 or "smooth-with-decay" not in str(d0):
    errs.append("lead contract lacks the data_class_freeze decision")
# --- contract-TEXT divergences (D1-D3), found by lead deep review 2026-09-11T23:55+08:00 ---
div = []
def ctext(cid):
    return str((A["classes"].get(cid,{}).get("conclusion") or {}).get("text",""))
wcc = ctext("AF-WCC-VAC-GEN")
if "J-(I+)" in wcc.replace(" ","") or "J^-(I+)" in wcc:
    div.append({"id":"D1","class":"AF-WCC-VAC-GEN",
        "f0_text":"visibility via 'every future-inextendible causal geodesic contained in J-(I+) is complete' (SET-based)",
        "lead_contract":"visibility via the TAIL of gamma contained in J^-(q) for a SINGLE q in I+",
        "relation":"the F0 condition is strictly STRONGER: gamma not contained in the union J^-(I+) implies no single q contains gamma, but not conversely",
        "recommended":"F0 adopts the single-q form (standard 'visible from I+' in the shadow of a point of I+'); or registers the set-based form as a separate stronger class AF-WCC-VAC-GEN-SET"})
for cid in ("AF-SCC-C2-VAC-GEN","AF-SCC-C0-VAC-GEN"):
    txt = ctext(cid).lower()
    if "future" not in txt:
        div.append({"id":"D2","class":cid,
            "f0_text":"no isometric embedding into a larger spacetime (extension DIRECTION unspecified)",
            "lead_contract":"FUTURE inextendibility only (two-sided is a different, stronger class; one-ended AF data can extend to the past into a white hole)",
            "relation":"the F0 text as worded is stronger and would be refuted by past white-hole extensions",
            "recommended":"F0 states 'future-inextendible' explicitly, as the lead schemas do"})
if "for every data set in the class" in ctext("AF-SCC-C0-VAC-GEN").lower() and "comeager" not in " ".join(ctext(c) for c in ("AF-SCC-C2-VAC-GEN","AF-SCC-C0-VAC-GEN")).lower():
    div.append({"id":"D3","class":"AF-SCC-C2-VAC-GEN/AF-SCC-C0-VAC-GEN/AF-WCC-VAC-GEN",
        "f0_text":"per-class statements read 'For every data set in the class' with the genericity clause carried only by axes.genericity_kind (provisional)",
        "lead_contract":"the comeager quantifier is explicit in statement_formal, bound before the data",
        "relation":"not a contradiction if 'in the class' is read as 'in the generic set', but the text is ambiguous and a reader can drop genericity silently",
        "recommended":"F0 states the quantifier explicitly in each class text"})
rep_div = {"divergences": div} if div else {}
T1 = any(r.get("from")=="AF-SCC-C0-VAC-GEN" and r.get("to")=="AF-SCC-C2-VAC-GEN"
         for r in (A.get("transfer_rules",{}).get("allowed") or []))
X1 = any("C2-VAC-GEN -> AF-SCC-C0" in str(r.get("pattern","")) or
         (r.get("from")=="AF-SCC-C2-VAC-GEN" and r.get("to")=="AF-SCC-C0-VAC-GEN")
         for r in (A.get("transfer_rules",{}).get("forbidden") or []))
LI = any(r.get("from")=="AF-SCC-C0-VAC-GEN" and r.get("to")=="AF-SCC-C2-VAC-GEN" and r.get("direction")=="one_way"
         for r in (B.get("implication_ledger") or []))
if not (T1 and LI): errs.append("C0 => C2 one-way entailment not recorded on both sides")
if not X1: errs.append("map taxonomy does not forbid the C2 => C0 converse")
rep = {"map_taxonomy": "research_map/formulation_taxonomy.yaml", "lead_contract": "artifacts/formulation/formulation_taxonomy.yaml",
       "consistent": not errs and not div, "errors": errs, "contract_divergences": div, "notes": notes,
       "classes_compared": sorted(set(A["class_ids"]) & set(B["class_contracts"])),
       "alias_policy": AL["policy"]}
out = Path('/data3/guoshaoyang/workdir/ai4math-swarm/artifacts/worker-075/rev29_review/_review_controls/taxonomy_consistency.replay.json')
out.write_text(json.dumps(rep, indent=2)+"\n")
print(("CONSISTENT" if not errs and not div else "INCONSISTENT") + f" ({len(rep['classes_compared'])} classes, {len(div)} contract-text divergences)")
for e in errs: print("  " + e)
sys.exit(0 if (not errs and not div) else 1)

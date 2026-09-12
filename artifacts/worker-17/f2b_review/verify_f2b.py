#!/usr/bin/env python3
"""Independent F2b (AF-SCC-C0-VAC-GEN) class-binding checks, worker-17.

Self-contained: does not import artifacts/formulation/tools or artifacts/worker-06.
Reads the pinned snapshot, emits JSON to stdout (and to the path given as argv[2]).
Usage: python3 verify_f2b.py <schema.yaml> [report.json]
"""
import hashlib, json, re, sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]
FROZEN4 = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
CONCL = {
    "AF-WCC-VAC-GEN": "weak_cosmic_censorship",
    "AF-SCC-C2-VAC-GEN": "scc_c2_future_inextendibility",
    "AF-SCC-C0-VAC-GEN": "scc_c0_future_inextendibility",
    "AF-WCC-SCALAR-SPH": "weak_cosmic_censorship",
}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def toks(s):
    return re.findall(r"[A-Za-z0-9_^{}()',]+", s)

def sections(text):
    """line number (1-based) -> top-level section name."""
    out, cur = {}, None
    for i, ln in enumerate(text.splitlines(), 1):
        if ln and not ln[0].isspace() and ln.rstrip().endswith(":"):
            cur = ln.split(":")[0]
        out[i] = cur
    return out

def main():
    target = Path(sys.argv[1])
    rep = {"target": str(target), "sha256": sha(target), "bytes": target.stat().st_size, "checks": {}, "failures": []}
    d = yaml.safe_load(target.read_text())
    text = target.read_text()
    sec = sections(text)
    C = rep["checks"]

    C["identity"] = {
        "class_id": d.get("class_id"), "node_id": d.get("node_id"),
        "class_id_in_frozen_four": d.get("class_id") in FROZEN4,
        "class_components": d.get("class_components"),
        "components_match_class_id": d.get("class_components", {}).get("regularity_token") == "C0"
        and d.get("class_components", {}).get("censorship") == "SCC",
        "conclusion_type": d["conclusion"]["conclusion_type"],
        "conclusion_type_matches_vocabulary": d["conclusion"]["conclusion_type"] == CONCL.get(d.get("class_id")),
        "extension_regularity": d["regularity"]["extension_regularity"],
        "extension_regularity_is_C0": d["regularity"]["extension_regularity"] == "C0",
        "extension_solution_concept": d["regularity"]["extension_solution_concept"],
        "i_plus_role": d["i_plus"]["role"], "i_plus_in_conclusion": d["i_plus"].get("in_conclusion"),
        "visibility_role": d["visibility"]["role"],
    }

    kinds = [q["kind"] for q in d["quantifiers"]["ordered"]]
    domains = d["quantifiers"]["domains"]
    unresolved = [q["domain_id"] for q in d["quantifiers"]["ordered"] if q["domain_id"] not in domains]
    neg = d["quantifiers"]["negation"]
    C["quantifiers"] = {
        "ordered_kinds": kinds,
        "expected_kinds": ["forall", "exists", "forall", "not_exists"],
        "kinds_ok": kinds == ["forall", "exists", "forall", "not_exists"],
        "order_matters": d["quantifiers"].get("order_matters"),
        "unresolved_domain_ids": unresolved,
        "binder_sequence_present_in_formal": all(
            b.replace("G_{s,delta}", "G") in d["quantifiers"]["formal"].replace("G_{s,delta}", "G")
            for b in ["(s,delta)", "forall (Sigma,h,K)", "not exists"]),
        "negation_starts_exists_s_delta": neg.strip().startswith("there exists (s,delta) in D0"),
        "negation_has_forall_comeager_G": "for every comeager G" in neg,
        "negation_has_exists_data": "there is" in neg and "(Sigma,h,K) in G" in neg,
        "negation_nnf_uses_non_meager": "non-meager" in d["quantifiers"]["negation_normal_form"],
        "quantifier_class": d["quantifiers"].get("quantifier_class"),
        "D0_definition": domains["D0"]["definition"],
    }

    found = {}
    for i, ln in enumerate(text.splitlines(), 1):
        for m in re.finditer(r"AF-[A-Z0-9-]+", ln):
            found.setdefault(m.group(0), []).append({"line": i, "section": sec[i]})
    foreign = {k: v for k, v in found.items() if k not in FROZEN4}
    C["class_tokens"] = {
        "tokens": sorted(found),
        "foreign_tokens": foreign,
        "foreign_all_in_anti_scope_or_variant_blocks": all(
            all(o["section"] in ("anti_scope", "class_identity_variants", "l1_ledger_refs") for o in v)
            for v in foreign.values()) if foreign else True,
    }

    comp = []
    for i, ln in enumerate(text.splitlines(), 1):
        if re.search(r"(C0|C2)\s*(or|and|/)\s*(C0|C2)", ln):
            comp.append({"line": i, "section": sec[i], "text": ln.strip()[:100]})
    C["composite_regularity_scan"] = {
        "hits": comp,
        "all_hits_in_forbidden_phrase_or_anti_scope": all(h["section"] in ("anti_scope",) for h in comp),
    }

    C["sibling_checks"] = {
        "sibling_disjoint_from": d.get("sibling_disjoint_from"),
        "forbidden_weakenings_count": len(d["conclusion"]["forbidden_weakenings"]),
        "implication_contains_C0_to_C2": any(
            r["from"] == "no proper future C0 metric extension" and "C2" in r["to"]
            for r in d["implication_ledger"]["one_way_entailments"]),
        "forbidden_transfers_C2_to_this": any(
            r["from"] == "no proper future C2 extension" and r["to"] == "this class"
            for r in d["implication_ledger"]["forbidden_transfers"]),
        "composite_regularity_lint_present": "composite_regularity_lint" in d,
    }

    # cross-artifact alignment (data class identical across F1/F2a/F2b)
    others = {"F1": "schemas/af_wcc_vacuum.yaml", "F2a": "schemas/af_scc_c2_vacuum.yaml"}
    align = {}
    for k, p in others.items():
        try:
            o = yaml.safe_load(Path(p).read_text())
            align[k] = {
                "sha256": sha(p)[:12],
                "D0_identical": o["quantifiers"]["domains"]["D0"]["definition"] == domains["D0"]["definition"],
                "regularity_class_identical": o["data_class"]["regularity_class"] == d["data_class"]["regularity_class"],
                "i_plus_role": o["i_plus"]["role"], "visibility_role": o["visibility"]["role"],
            }
        except Exception as e:
            align[k] = {"error": str(e)}
    C["cross_artifact"] = align

    # ledger refs must resolve
    led = {}
    for line in Path("ledger/theorems.jsonl").read_text().splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if "theorem_id" in r:
            led[r["theorem_id"]] = r
    refs = {}
    for ref in d.get("l1_ledger_refs", []):
        tid = ref.get("theorem_id")
        row = led.get(tid)
        refs[tid] = {
            "resolves": row is not None,
            "entry_kind": (row or {}).get("entry_kind"),
            "conclusion_type": (row or {}).get("conclusion_type"),
            "class_ids": (row or {}).get("class_ids"),
            "declared_l1_status": ref.get("l1_status"),
        }
    C["l1_refs"] = refs
    C["l1_refs_all_resolve"] = all(v["resolves"] for v in refs.values())

    # variant references must resolve for parent C0
    try:
        reg = json.loads(Path("artifacts/formulation/VARIANT_REGISTRY.json").read_text())
        ids = {v["variant_id"] for v in reg["variants"] if v.get("parent_class") == "AF-SCC-C0-VAC-GEN"}
        C["variants"] = {"registry_version": reg.get("version"), "c0_variant_ids": sorted(ids),
                         "CH_H2LOC_DISTRIBUTIONAL_present": {"CH", "H2LOC", "DISTRIBUTIONAL"} <= ids}
    except Exception as e:
        C["variants"] = {"error": str(e)}

    # freeze integrity of this artifact and of the F0 it binds
    try:
        man = json.loads(Path("artifacts/formulation/FROZEN.json").read_text())
        fr = {"revision": man["revision"], "frozen_at": man["frozen_at"], "entries": {}}
        for p in ["schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
                  "research_map/formulation_taxonomy.yaml", "artifacts/formulation/VARIANT_REGISTRY.json",
                  "artifacts/formulation/rule_spec.json"]:
            rec = man["files"].get(p)
            disk = sha(p) if Path(p).exists() else None
            fr["entries"][p] = {"manifest": (rec or {}).get("sha256", "")[:12], "disk": (disk or "MISSING")[:12],
                                "drift": bool(rec and disk and rec["sha256"] != disk)}
        fr["drifted_entries"] = [k for k, v in fr["entries"].items() if v["drift"]]
        C["freeze_manifest"] = fr
    except Exception as e:
        C["freeze_manifest"] = {"error": str(e)}

    # f0_binding field vs declared F0 artifact on disk
    fb = d.get("f0_binding", {})
    f0p = fb.get("declared_f0_artifact")
    f0disk = sha(f0p) if f0p and Path(f0p).exists() else None
    C["f0_binding"] = {
        "declared_sha256": fb.get("declared_f0_sha256", "")[:12],
        "disk_sha256": (f0disk or "MISSING")[:12],
        "field_matches_disk": bool(f0disk and fb.get("declared_f0_sha256") == f0disk),
        "binding_note_mentions_stale_hash_565a6e50": "565a6e50" in fb.get("binding_note", ""),
        "binding_note_mentions_stale_hash_66bf917b": "66bf917b" in fb.get("binding_note", ""),
    }

    for k, v in C.items():
        if isinstance(v, dict) and v.get("kinds_ok") is False:
            rep["failures"].append(f"quantifier kinds {v['ordered_kinds']}")
        if isinstance(v, dict) and v.get("unresolved_domain_ids"):
            rep["failures"].append("unresolved domain ids")
        if isinstance(v, dict) and v.get("class_id_in_frozen_four") is False:
            rep["failures"].append("class_id not frozen")
    print(json.dumps(rep, indent=1))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(rep, indent=1))

if __name__ == "__main__":
    main()

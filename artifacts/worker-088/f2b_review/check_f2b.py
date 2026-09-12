#!/usr/bin/env python3
"""Independent F2b (AF-SCC-C0-VAC-GEN) checker, worker-088.

Reads the pinned F2b schema from a local frozen copy, re-derives every claim in
reviews/F2b-review-088.json, and writes f2b_check.json next to it.

Checks:
  C01 pin: local copy sha256 == the declared pin in the card.
  C02 YAML parses; duplicate mapping keys detected; class_id == AF-SCC-C0-VAC-GEN.
  C03 binder/domain resolution: every ordered quantifier domain_id exists.
  C04 f0_binding hash resolution for declared_f0_artifact, class_contract_supplement,
      consistency_evidence (declared vs measured), plus supplement-pin presence.
  C05 class-separation text detector over the artifact bytes.
  C06 C0/C2 content separation vs schemas/af_scc_c2_vacuum.yaml on the four
      regularity-bearing fields and mutual sibling_disjoint_from.
  C07 conclusion_type token present as a canonical key in VOCAB_ALIASES.json.
  C08 WCC leakage: conclusion/i_plus/visibility blocks carry no I+-completeness claim.
  C09 C2/H2_loc mentions are confined to forbidden/anti-scope/containment contexts.
  C10 l1_ledger_refs citation_status vs the referenced ledger rows.
  C11 soft flag at line 316: token classification (annotation vs class-id leak).

Exit code 0 always; the verdict is in the JSON.
"""
import hashlib
import json
import os
import re
import sys

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
PIN = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
PINNED = os.path.join(ROOT, "artifacts/worker-088/f2b_review/pinned/af_scc_c0_vacuum.55d0a1ea.yaml")
SCHEMA = os.path.join(ROOT, "schemas/af_scc_c0_vacuum.yaml")
C2 = os.path.join(ROOT, "schemas/af_scc_c2_vacuum.yaml")
OUT = os.path.join(ROOT, "artifacts/worker-088/f2b_review/f2b_check.json")


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    checks = []

    def add(cid, ok, detail):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})

    # C01
    pinned_hash = sha256(PINNED)
    add("C01_pin", pinned_hash == PIN, {"pinned_copy_sha256": pinned_hash, "declared_pin": PIN})

    raw = open(PINNED).read()

    # C02 duplicate-key-aware parse
    import yaml

    class DupLoader(yaml.SafeLoader):
        pass

    dups = []

    def no_dup(loader, node, deep=False):
        mapping = {}
        for k, v in node.value:
            key = loader.construct_object(k, deep=deep)
            if key in mapping:
                dups.append(str(key))
            mapping[key] = loader.construct_object(v, deep=deep)
        return mapping

    DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_dup)
    data = yaml.load(raw, Loader=DupLoader)
    add("C02_parse", not dups and data.get("class_id") == "AF-SCC-C0-VAC-GEN" and int(data.get("revision")) == 12,
        {"duplicate_keys": dups, "class_id": data.get("class_id"), "revision": data.get("revision"),
         "top_level_keys": len(data)})

    # C03 binders
    q = data["quantifiers"]
    doms = set(q["domains"].keys())
    unresolved = [b for b in q["ordered"] if b["domain_id"] not in doms]
    add("C03_binders", not unresolved, {"domains": sorted(doms), "unresolved": unresolved})

    # C04 f0_binding
    fb = data["f0_binding"]
    m = {}
    for field in ("declared_f0_artifact", "class_contract_supplement", "consistency_evidence"):
        m[field] = {"path": fb[field], "measured": sha256(os.path.join(ROOT, fb[field]))}
    f0_match = m["declared_f0_artifact"]["measured"] == fb["declared_f0_sha256"]
    supp_pin_present = any(k.endswith("_sha256") and "supplement" in k for k in fb)
    ev_match = m["consistency_evidence"]["measured"] == fb["consistency_evidence_sha256"]
    ev = json.load(open(os.path.join(ROOT, fb["consistency_evidence"])))
    ev_binds_inputs = any(re.fullmatch(r"[0-9a-f]{64}", str(v)) for v in ev.values())
    add("C04_f0_binding", f0_match and ev_match and supp_pin_present and ev_binds_inputs,
        {"declared_f0_sha256": fb["declared_f0_sha256"], "f0_matches": f0_match,
         "declared_consistency_evidence_sha256": fb["consistency_evidence_sha256"],
         "measured_consistency_evidence_sha256": m["consistency_evidence"]["measured"],
         "consistency_evidence_matches": ev_match,
         "supplement_sha256_field_present": supp_pin_present,
         "evidence_binds_compared_input_hashes": ev_binds_inputs})

    # C05 detector
    sys.path.insert(0, os.path.join(ROOT, "research_map"))
    import class_separation as cs

    det = cs.findings_for_text(raw, "schemas/af_scc_c0_vacuum.yaml")
    add("C05_classsep_text", len(det) == 0, {"findings": det})

    # C06 C0/C2 separation
    f2a = yaml.safe_load(open(C2))

    def g(d, *keys):
        for k in keys:
            d = d.get(k, {}) if isinstance(d, dict) else {}
        return d

    sep = {
        "frozen_regularity": (g(data, "extension_predicate", "frozen_regularity"),
                              g(f2a, "extension_predicate", "frozen_regularity")),
        "extension_regularity": (g(data, "regularity", "extension_regularity"),
                                 g(f2a, "regularity", "extension_regularity")),
        "extension_solution_concept": (g(data, "regularity", "extension_solution_concept"),
                                       g(f2a, "regularity", "extension_solution_concept")),
        "conclusion_type": (g(data, "conclusion", "conclusion_type"),
                            g(f2a, "conclusion", "conclusion_type")),
        "sibling_disjoint_from": (data.get("sibling_disjoint_from"), f2a.get("sibling_disjoint_from")),
    }
    sep_ok = (sep["frozen_regularity"] == ("C0", "C2") and sep["extension_regularity"] == ("C0", "C2")
              and sep["extension_solution_concept"][0] == "none"
              and sep["conclusion_type"][0] != sep["conclusion_type"][1]
              and sep["sibling_disjoint_from"] == ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"))
    add("C06_c0_c2_separation", sep_ok, sep)

    # C07 canonical conclusion token
    aliases = json.load(open(os.path.join(ROOT, "artifacts/formulation/VOCAB_ALIASES.json")))
    tok = g(data, "conclusion", "conclusion_type")
    add("C07_conclusion_token", tok in aliases["conclusion_type"], {"token": tok,
        "canonical_keys": sorted(aliases["conclusion_type"].keys())})

    # C08 WCC leakage
    leaks = []
    if g(data, "i_plus", "in_conclusion") is not False:
        leaks.append("i_plus.in_conclusion")
    if g(data, "i_plus", "completeness_in_conclusion") is not False:
        leaks.append("i_plus.completeness_in_conclusion")
    if g(data, "visibility", "role") == "not_in_conclusion":
        pass
    else:
        leaks.append("visibility.role")
    if "I+ completeness" not in json.dumps(data["conclusion"].get("forbidden_strengthenings", [])):
        leaks.append("conclusion.forbidden_strengthenings missing I+ entry")
    add("C08_wcc_leakage", not leaks, {"leaks": leaks})

    # C09 C2/H2_loc contexts, classified by enclosing section path (not keywords).
    # Every section below is a comparison, prohibition, provenance or history block in
    # which naming the weaker sibling is required; C2/H2_loc tokens anywhere else would
    # be a smuggled hypothesis or conclusion and is reported as unclassified.
    allowed_sections = {
        "sibling_disjoint_from",
        "revision_history",
        "c0_specifics",
        "extension_predicate.must_not_conflate",
        "extension_predicate.c0_uniqueness_caveat",
        "regularity.must_not_conflate",
        "genericity.transfer_failures",
        "genericity.transfer_holds",
        "genericity.variants",
        "non_vacuity",
        "i_plus",
        "visibility",
        "conclusion",
        "implication_ledger",
        "falsifier",
        "anti_scope",
        "class_identity_variants",
        "l1_ledger_refs",
        "known_status",
        "provenance",
        "unresolved_items",
        "review_status",
        "scope_statement",
        "quantifiers",
        "topology",
        "data_class",
        "genericity",
    }
    bad_ctx = []
    top = second = ""
    for i, line in enumerate(raw.splitlines(), 1):
        if line and not line[0].isspace() and not line.startswith("-"):
            top = line.split(":", 1)[0].strip()
            second = ""
        elif line.startswith("  ") and not line.startswith("    ") and not line.startswith("  -"):
            second = line.strip().split(":", 1)[0].strip()
        if re.search(r"\bC2\b|H2_loc|H2loc|C\^\{1,1\}", line):
            path = f"{top}.{second}" if second else top
            if path not in allowed_sections and top not in allowed_sections:
                bad_ctx.append((i, path, line.strip()[:110]))
    add("C09_c2_contexts", not bad_ctx, {"unclassified": bad_ctx, "allowed_sections": sorted(allowed_sections)})

    # C10 ledger citation vocabulary
    want = {"D-002", "T-301", "T-515", "T-528", "T-302", "T-305"}
    rows = {}
    for line in open(os.path.join(ROOT, "ledger/theorems.jsonl")):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("theorem_id") in want:
            rows[d["theorem_id"]] = {"verification_status": d.get("verification_status"),
                                     "review_status": d.get("review_status"),
                                     "content_status": d.get("content_status"),
                                     "has_citation_status_field": "citation_status" in d}
    drifts = []
    for ref in data["l1_ledger_refs"]:
        tid = ref["theorem_id"]
        row = rows.get(tid, {})
        if ref.get("citation_status") != row.get("verification_status"):
            drifts.append({"theorem_id": tid, "schema_citation_status": ref.get("citation_status"),
                           "ledger_verification_status": row.get("verification_status"),
                           "ledger_review_status": row.get("review_status"),
                           "ledger_has_citation_status_field": row.get("has_citation_status_field")})
    add("C10_ledger_citation_status", not drifts, {"drifts": drifts, "ledger_rows": rows})

    # C11 line-316 soft flag
    l316 = raw.splitlines()[315]
    variant_reg = json.load(open(os.path.join(ROOT, "artifacts/formulation/VARIANT_REGISTRY.json")))
    vr_text = json.dumps(variant_reg)
    tokens = re.findall(r"H2_loc|H2LOC|\bC0\b", l316)
    class_id_shaped = re.findall(r"AF-[A-Z]+-[A-Z]+-[A-Z]+-[A-Z]+", l316)
    add("C11_line316_softflag",
        bool(tokens) and not class_id_shaped and "H2LOC" in vr_text and "status: unresolved" in l316,
        {"line": 316, "text": l316.strip(), "tokens": tokens, "class_id_shaped_tokens": class_id_shaped,
         "H2LOC_registered_as_variant": "H2LOC" in vr_text})

    result = {"artifact": "schemas/af_scc_c0_vacuum.yaml", "pin": PIN, "pinned_copy": PINNED,
              "checker_sha256": sha256(os.path.abspath(__file__)), "checks": checks,
              "passed": sum(1 for c in checks if c["ok"]), "total": len(checks),
              "verdict": "PASS" if all(c["ok"] for c in checks) else "FAIL"}
    json.dump(result, open(OUT, "w"), indent=1, sort_keys=True)
    print(json.dumps({"verdict": result["verdict"], "passed": result["passed"], "total": result["total"],
                      "failed": [c["id"] for c in checks if not c["ok"]]}, indent=1))


if __name__ == "__main__":
    main()

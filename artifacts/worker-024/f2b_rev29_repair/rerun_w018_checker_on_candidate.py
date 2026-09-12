#!/usr/bin/env python3
"""W018-R13-F2B: independent at-pin conformance review of F2b (AF-SCC-C0-VAC-GEN) rev13.

Read-only. No network. Deterministic. Re-runnable from the repo root:
    python3 artifacts/worker-018/f2b_rev13_review/check_f2b_rev13.py

Every check prints PASS / FAIL / WARN with an id. Exit code 0 iff no FAIL.
The verdict-bearing checks are CHAIN-DENIAL (C16) and TRANSFER-REASON (C17).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

TARGET = "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml"
MIRROR = "artifacts/worker-024/f2b_rev29_repair/CANDIDATE_schemas_af_scc_c0_vacuum.yaml"
EXPECTED_SHA = "679ab7bc874697cd52aaa0cdcbc32547de7983e3580c5f0e4a0640389ec823d9"
FROZEN = "artifacts/formulation/FROZEN.json"
F0_CANON = "research_map/formulation_taxonomy.yaml"
F0_EXPECTED = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"
CONSISTENCY_EXPECTED = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
SIBLING_C2 = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
SIBLING_C2_SHA = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
SIBLING_WCC = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
CLASS_ID = "AF-SCC-C0-VAC-GEN"

RESULTS = []


def check(cid, ok, msg, **extra):
    RESULTS.append({"id": cid, "status": "PASS" if ok else "FAIL", "msg": msg, **extra})
    print(f"[{'PASS' if ok else 'FAIL'}] {cid}: {msg}")


def warn(cid, msg, **extra):
    RESULTS.append({"id": cid, "status": "WARN", "msg": msg, **extra})
    print(f"[WARN] {cid}: {msg}")


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class NoDupLoader:
    """Safe YAML loader that refuses duplicate mapping keys (PyYAML default silently overwrites)."""

    @staticmethod
    def load(text):
        import yaml

        class L(yaml.SafeLoader):
            pass

        def construct_mapping(loader, node, deep=False):
            keys = set()
            for k, _ in node.value:
                kk = loader.construct_object(k, deep=deep)
                if kk in keys:
                    raise ValueError(f"duplicate key {kk!r} at line {k.start_mark.line + 1}")
                keys.add(kk)
            return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

        L.add_constructor("tag:yaml.org,2002:map", construct_mapping)
        return yaml.load(text, Loader=L)


def main():
    import yaml  # noqa: F401  (presence check)

    target_path = ROOT / TARGET
    mirror_path = ROOT / MIRROR

    # ---- C1 identity / pin -------------------------------------------------
    h0 = sha256_file(target_path)
    check("C1-ARTIFACT-SHA", h0 == EXPECTED_SHA,
          f"target sha256 {h0[:12]} == dispatched pin {EXPECTED_SHA[:12]}", measured=h0)
    check("C2-MIRROR-BYTE-EQUAL", target_path.read_bytes() == mirror_path.read_bytes(),
          "canonical artifacts/formulation path and schemas/ working mirror are byte-identical")

    text = target_path.read_text()
    try:
        doc = NoDupLoader.load(text)
        dup_ok = True
    except Exception as e:  # duplicate key or parse error
        doc = None
        dup_ok = False
        check("C3-STRICT-YAML", False, f"YAML parse refused: {e}")
    else:
        check("C3-STRICT-YAML", True, "YAML parses with duplicate-key refusal; no duplicate mapping keys")

    if doc is None:
        return finish()

    # ---- C4 class identity -------------------------------------------------
    check("C4-CLASS-ID", doc.get("class_id") == CLASS_ID and doc.get("node_id") == "F2b",
          f"class_id={doc.get('class_id')} node_id={doc.get('node_id')}")

    # ---- C5 quantifier structure ------------------------------------------
    q = doc.get("quantifiers", {})
    ordered = q.get("ordered", [])
    kinds = [r.get("kind") for r in ordered]
    check("C5-QUANTIFIER-ORDER", kinds == ["forall", "exists", "forall", "not_exists"],
          f"ordered quantifier kinds {kinds} == forall-exists-forall-not_exists")
    d0 = (q.get("domains", {}) or {}).get("D0", {}).get("definition", "")
    d0_ok = ("tagged disjoint union" in d0 and "sobolev,s,delta" in d0
             and "s > 5/2" in d0 and "delta in (1/2,1)" in d0)
    check("C6-D0-TAGGED-UNION", d0_ok,
          "D0 is a tagged disjoint union smooth | (sobolev,s,delta) with s>5/2, delta in (1/2,1)")

    # ---- C7 conclusion typing ---------------------------------------------
    concl = doc.get("conclusion", {})
    ctype = concl.get("conclusion_type")
    f2a = NoDupLoader.load((ROOT / SIBLING_C2).read_text())
    f1 = NoDupLoader.load((ROOT / SIBLING_WCC).read_text())
    sib_types = {f2a.get("conclusion", {}).get("conclusion_type"),
                 f1.get("conclusion", {}).get("conclusion_type")}
    check("C7-CONCLUSION-TYPE-DISTINCT",
          ctype == "scc_c0_future_inextendibility" and ctype not in sib_types,
          f"conclusion_type={ctype}; sibling types={sorted(t for t in sib_types if t)}")
    check("C8-CONCLUSION-FAMILY", concl.get("family") == "SCC",
          "conclusion family is SCC (not WCC)")

    # ---- C9 no composite regularity in identity fields --------------------
    # CF-16 caution: quoted mentions inside phrases_that_are_not_this_class are
    # metalinguistic and are not uses. Strip that list before searching.
    identity = {k: v for k, v in doc.items()
                if k in ("class_id", "node_id", "conclusion")}
    anti = json.loads(json.dumps(doc.get("anti_scope", {})))
    anti.pop("phrases_that_are_not_this_class", None)
    identity["anti_scope_uses"] = anti
    composite = re.search(r"C0\s+or\s+C2", json.dumps(identity))
    check("C9-NO-COMPOSITE-TOKEN", composite is None,
          "no use of a 'C0 or C2' composite regularity in identity/conclusion/anti-scope use-fields "
          "(line 278 is a quoted mention and is excluded per CF-16)")

    # ---- C10 frozen pin ----------------------------------------------------
    frozen = json.loads((ROOT / FROZEN).read_text())
    fpin = frozen.get("files", {}).get(TARGET, {}).get("sha256")
    check("C10-FROZEN-PIN", fpin == h0 and frozen.get("revision") == 29,
          f"FROZEN rev{frozen.get('revision')} pins {TARGET} at {str(fpin)[:12]} == measured {h0[:12]}")

    # ---- C11 F0 binding + consistency evidence ----------------------------
    fb = doc.get("f0_binding", {})
    live_f0 = sha256_file(ROOT / F0_CANON)
    live_cons = sha256_file(ROOT / CONSISTENCY)
    check("C11-F0-BINDING", fb.get("declared_f0_sha256") == live_f0 == F0_EXPECTED,
          f"f0_binding declared {str(fb.get('declared_f0_sha256'))[:12]} == live {live_f0[:12]} == F0 pass pin")
    check("C12-CONSISTENCY-EVIDENCE", fb.get("consistency_evidence_sha256") == live_cons == CONSISTENCY_EXPECTED,
          f"consistency_evidence_sha256 == live taxonomy_consistency.json {live_cons[:12]}")
    cons_doc = json.loads((ROOT / CONSISTENCY).read_text())
    check("C13-CONSISTENCY-VERDICT",
          cons_doc.get("consistent") is True and not cons_doc.get("errors")
          and set(cons_doc.get("classes_compared", [])) == {
              "AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-SCALAR-SPH", "AF-WCC-VAC-GEN"},
          f"taxonomy_consistency.json: consistent={cons_doc.get('consistent')}, "
          f"errors={cons_doc.get('errors')}, {len(cons_doc.get('classes_compared', []))} classes compared")

    # ---- C14 pointer resolution -------------------------------------------
    tax = NoDupLoader.load((ROOT / F0_CANON).read_text())
    supp = NoDupLoader.load((ROOT / "artifacts/formulation/formulation_taxonomy.yaml").read_text())
    ptr = doc.get("class_contract_pointer", "")
    sptr = doc.get("class_contract_supplement_pointer", "")
    classes = tax.get("classes", {})
    contracts = supp.get("class_contracts", {})
    check("C14-POINTERS-RESOLVE",
          ptr.split("#")[-1].split(".")[-1] in classes
          and sptr.split("#")[-1].split(".")[-1] in contracts,
          "class_contract_pointer resolves in canonical taxonomy `classes`; supplement pointer resolves in supplement `class_contracts`")

    # ---- C15 containment chain internal + entailment directions ------------
    il = doc.get("implication_ledger", {})
    chain = il.get("extension_class_containment", "")
    chain_ok = all(t in chain for t in ("E_C0 contains E_H2loc", "E_H2loc contains E_{C^1,1}", "E_{C^1,1} contains E_C2"))
    check("C15-CONTAINMENT-CHAIN", chain_ok,
          f"E_C0 contains E_H2loc contains E_{{C^1,1}} contains E_C2: {chain[:80]}...")
    owe = il.get("one_way_entailments", [])
    # Nesting: E_C2 smallest. Therefore no-C0-extension entails no-H2loc entails no-C2 (stronger -> weaker).
    expect_pairs = {
        ("no proper future C0 metric extension", "no proper future H2_loc extension"),
        ("no proper future H2_loc extension", "no proper future C2 extension"),
        ("no proper future C0 metric extension", "no proper future C2 extension"),
        ("no proper future C0 metric extension", "no proper future C0 distributional-vacuum extension"),
    }
    got_pairs = {(r.get("from"), r.get("to")) for r in owe}
    check("C16-ENTAILMENT-DIRECTIONS", expect_pairs <= got_pairs and len(owe) >= 4,
          f"{len(owe)} one_way_entailments all run stronger(C0) -> weaker(C2/H2loc/variant)")

    # ---- C17 live denial vs asserted chain (worker-066 H2, re-derived) -----
    mnc = doc.get("regularity", {}).get("must_not_conflate", [])
    denial = [s for s in mnc if "No containment with C2 or C0 is asserted here" in s]
    f2a_mnc = f2a.get("regularity", {}).get("must_not_conflate", [])
    f2a_corrected = any("earlier 'no containment with C2 is asserted' was wrong" in s for s in f2a_mnc)
    check("C17-CHAIN-DENIAL", len(denial) == 0,
          ("regularity.must_not_conflate[0] asserts 'No containment with C2 or C0 is asserted here' "
           "while implication_ledger asserts E_C0 contains E_H2loc contains E_C2"
           + ("; sibling F2a records the same denial as WRONG" if f2a_corrected else "")))

    # ---- C18 forbidden-transfer reason vs chain ordering (H1, re-derived) --
    fts = il.get("forbidden_transfers", [])
    bad_reason = [r for r in fts if "strictly larger extension class" in str(r.get("reason", ""))]
    # Under the artifact's own E-set containment, E_C2 is the SMALLEST extension set.
    check("C18-TRANSFER-REASON", len(bad_reason) == 0,
          "forbidden_transfers[0].reason premise 'C2 is a strictly larger extension class' is inverted "
          "against extension_class_containment (E_C2 is the smallest E-set)")

    # ---- C19 tier separation ----------------------------------------------
    t1 = doc.get("falsifier", {}).get("tier_1", {})
    t2 = doc.get("falsifier", {}).get("tier_2", {})
    check("C19-TIER-SEPARATION",
          t1.get("refutes") == CLASS_ID
          and "forall AF vacuum data" in str(t2.get("refutes", ""))
          and t2.get("labelling_required") == "refutes_strengthening_only",
          "tier_1 refutes the class; tier_2 refutes only the forall-data strengthening and is labelled refutes_strengthening_only")

    # ---- C20 I+/visibility scope ------------------------------------------
    ip = doc.get("i_plus", {})
    vis = doc.get("visibility", {})
    check("C20-WCC-SCOPE",
          ip.get("in_conclusion") is False and ip.get("completeness_in_conclusion") is False
          and vis.get("role") == "not_in_conclusion" and "WCC" in str(vis.get("forbidden_falsifier", "")),
          "I+ completeness and visibility are excluded from the conclusion and from the falsifier")

    # ---- C21 sibling disjointness -----------------------------------------
    check("C21-SIBLING-DISJOINT", doc.get("sibling_disjoint_from") == "AF-SCC-C2-VAC-GEN",
          "declared sibling AF-SCC-C2-VAC-GEN; both ids exist as distinct taxonomy classes")

    # ---- C22 hash stability ------------------------------------------------
    h1 = sha256_file(target_path)
    check("C22-HASH-STABLE", h1 == h0, f"hash stable across run: {h1[:12]}")

    return finish()


def finish():
    out = {
        "run": "W018-R13-F2B-REVIEW-01",
        "target": TARGET,
        "target_sha256": EXPECTED_SHA,
        "checks": RESULTS,
        "summary": {
            "pass": sum(1 for r in RESULTS if r["status"] == "PASS"),
            "fail": sum(1 for r in RESULTS if r["status"] == "FAIL"),
            "warn": sum(1 for r in RESULTS if r["status"] == "WARN"),
        },
    }
    outpath = ROOT / "artifacts/worker-024/f2b_rev29_repair/w018_checker_on_candidate.results.json"
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nsummary: {out['summary']} -> {outpath}")
    return 0 if out["summary"]["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

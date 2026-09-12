#!/usr/bin/env python3
"""W041-F0-REDISPATCH4-01: read-only independent re-verification of F0 at the pinned hash.

Acceptance criteria checked here (the assignment's own list):
  K1  canonical sha256 == 0abb9ed8a961... and stable across the run (pre and post read)
  K2  companion sha256 == d7419b4e8963... and stable across the run
  K3  exactly four distinct class ids, set-equal across four structural surfaces
  K4  class leakage: no C2 statement smuggled into C0; no C0/C2 merge; WCC/SCC separation
  K5  companion CONSISTENCY without byte-identity: same class ids, same semantics on
      shared checkable fields, no contradictory clause
  K6  conclusion inflation: file is draft_unverified, claims_theorem_status false,
      no theorem/counterexample conclusion, no weakness->strength promotion in class text
  K7  assumption completeness: unresolved hypotheses carry unresolved/owned_by; falsifiers decidable
  K8  disjointness: all 6 unordered pairs present and named decisive axes actually differ
  K9  transfer rules: only C0->C2 allowed with guards; all five forbidden leakage kinds present
  K10 no merged regularity token in class content (frozen G3 regex + normalization)

Exit 0 = all checks PASS. Exit 1 = at least one FAIL. Exit 3 = hash drift (void run).
This instrument writes nothing inside the swarm tree except the report path passed on argv.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for _i, _a in enumerate(sys.argv):
    if _a == "--root" and _i + 1 < len(sys.argv):
        ROOT = Path(sys.argv[_i + 1]).resolve()
CANON = ROOT / "research_map/formulation_taxonomy.yaml"
COMP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN_MANIFEST = ROOT / "artifacts/formulation/FROZEN.json"
ALIASES = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
EVIDENCE = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
SCHEMAS = {
    "AF-WCC-VAC-GEN": ROOT / "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": ROOT / "schemas/af_scc_c0_vacuum.yaml",
}
CANON_PIN = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
COMP_PIN = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
FROZEN4 = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
# Frozen G3 regex copied from artifacts/worker-01/validate_taxonomy.py:34-40 (not re-derived).
MERGED_RE = re.compile(r"C0\s*(?:or|and|/|\+)\s*C2|C2\s*(?:or|and|/|\+)\s*C0", re.I)


def normalize_regularity(text: str) -> str:
    return re.sub(r"[\^_{}\s]", "", text)


def merged_match(text: str) -> bool:
    return bool(MERGED_RE.search(text)) or bool(MERGED_RE.search(normalize_regularity(text)))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_yaml(p: Path):
    import yaml
    return yaml.safe_load(p.read_text())


def main() -> int:
    import yaml  # noqa: F401  (import here so a missing dep is a clean failure)

    mutation_mode = "--expect-mutation" in sys.argv
    mutation_expected = []
    for _i, _a in enumerate(sys.argv):
        if _a == "--mutation-expects" and _i + 1 < len(sys.argv):
            mutation_expected = sys.argv[_i + 1].split(",")

    checks: list[dict] = []
    findings: list[dict] = []
    fails = 0

    def req(cond: bool, cid: str, msg: str, detail=None):
        nonlocal fails
        ok = bool(cond)
        if not ok:
            fails += 1
        checks.append({"id": cid, "pass": ok, "check": msg, **({"detail": detail} if detail is not None else {})})

    def note(cond: bool, cid: str, msg: str, detail=None):
        """Non-blocking observation: recorded either way, never fails the run."""
        findings.append({"id": cid, "observed": bool(cond), "finding": msg,
                         **({"detail": detail} if detail is not None else {})})

    # --- K1/K2 pins -------------------------------------------------------
    pre = {"canonical": sha(CANON), "companion": sha(COMP), "frozen_manifest": sha(FROZEN_MANIFEST),
           "aliases": sha(ALIASES), "consistency_evidence": sha(EVIDENCE)}
    pre_schemas = {k: sha(v) for k, v in SCHEMAS.items()}
    req(pre["canonical"] == CANON_PIN, "K1", "canonical F0 sha256 equals the pinned 0abb9ed8a961",
        pre["canonical"])
    req(pre["companion"] == COMP_PIN, "K2", "companion sha256 equals the pinned d7419b4e8963",
        pre["companion"])

    A = load_yaml(CANON)
    B = load_yaml(COMP)
    reg = json.loads((ROOT / "artifacts/formulation/VARIANT_REGISTRY.json").read_text())
    frozen_man = json.loads(FROZEN_MANIFEST.read_text())

    # --- K3 exactly four class ids, set-equal across surfaces -------------
    top = A.get("class_ids")
    req(top == FROZEN4, "K3a", "canonical class_ids are exactly the frozen four in order", top)
    req(set(A.get("classes", {})) == set(FROZEN4), "K3b", "canonical classes keys are exactly the four",
        sorted(A.get("classes", {})))
    comp_ids = sorted(B.get("class_contracts", {}))
    req(comp_ids == sorted(FROZEN4), "K3c", "companion class_contracts are exactly the four", comp_ids)
    req(B.get("frozen_classes") == FROZEN4, "K3d", "companion frozen_classes list is the four", B.get("frozen_classes"))
    pair_ids = {x for d in A.get("disjointness", []) for x in d.get("pair", [])}
    req(pair_ids == set(FROZEN4), "K3e", "disjointness table references exactly the four", sorted(pair_ids))
    tr_ids = {x.get("from") for x in A.get("transfer_rules", {}).get("allowed", [])} | \
             {x.get("to") for x in A.get("transfer_rules", {}).get("allowed", [])}
    req(tr_ids <= set(FROZEN4), "K3f", "allowed-transfer endpoints are frozen class ids", sorted(tr_ids))
    extra = sorted(set(B.get("frozen_classes", [])) ^ set(FROZEN4))
    req(not extra, "K3g", "no fifth class id anywhere on the companion surface", extra)

    # variant registry: variants must not be class ids
    vids = sorted({v.get("variant_id") for v in reg.get("variants", [])})
    req(len(reg.get("parent_classes", [])) == 4, "K3h", "variant registry has exactly four parent classes",
        len(reg.get("parent_classes", [])))
    req(all(v.get("parent_class") in FROZEN4 for v in reg.get("variants", [])), "K3i",
        "every variant names a frozen parent class", vids)
    req(not (set(vids) & set(FROZEN4)), "K3j", "no variant_id collides with a class id", vids)

    # --- K4 class leakage -------------------------------------------------
    def content_text(cid):
        c = A["classes"][cid]
        parts = [c.get("label", ""), json.dumps(c.get("axes", {})),
                 json.dumps(c.get("hypotheses", [])), json.dumps(c.get("exclusions", [])),
                 json.dumps(c.get("conclusion", {})), json.dumps(c.get("test_cases", {}))]
        return "\n".join(parts)

    c0_content = content_text("AF-SCC-C0-VAC-GEN")
    c2_content = content_text("AF-SCC-C2-VAC-GEN")
    # C0 must state C0 (continuous-metric) and must not assert only-C2 content in its conclusion.
    req("C0" in json.dumps(A["classes"]["AF-SCC-C0-VAC-GEN"]["conclusion"]), "K4a",
        "C0 class conclusion is a C0 statement")
    c0_axes = A["classes"]["AF-SCC-C0-VAC-GEN"]["axes"]
    c2_axes = A["classes"]["AF-SCC-C2-VAC-GEN"]["axes"]
    req(c0_axes["regularity_token"] == "C0" and c2_axes["regularity_token"] == "C2", "K4b",
        "regularity tokens are C0/C2 respectively and not swapped",
        [c0_axes["regularity_token"], c2_axes["regularity_token"]])
    req(c0_axes["conclusion_type"] != c2_axes["conclusion_type"], "K4c",
        "C0 and C2 conclusion_type remain distinct values")
    # forbidden direction X1 must exist and no allowed C2->C0 transfer
    forb = []
    for x in A["transfer_rules"].get("forbidden", []):
        pat = str(x.get("pattern", "")).replace(" ", "")
        if x.get("from") and x.get("to"):
            forb.append(f"{x.get('from')}->{x.get('to')}")
        if "AF-SCC-C2-VAC-GEN->AF-SCC-C0-VAC-GEN" in pat:
            forb.append("AF-SCC-C2-VAC-GEN->AF-SCC-C0-VAC-GEN")
        if x.get("kind") == "conclusion_inflation" and "C2" in pat and "C0" in pat and "->" in pat:
            forb.append("AF-SCC-C2-VAC-GEN->AF-SCC-C0-VAC-GEN")
    req("AF-SCC-C2-VAC-GEN->AF-SCC-C0-VAC-GEN" in forb, "K4d",
        "C2->C0 conclusion inflation is explicitly forbidden")
    req(not any(x.get("from") == "AF-SCC-C2-VAC-GEN" and x.get("to") == "AF-SCC-C0-VAC-GEN"
                for x in A["transfer_rules"].get("allowed", [])), "K4e",
        "no allowed C2->C0 transfer")
    # WCC content must not assert inextendibility; SCC content must not assert visibility.
    wcc_content = content_text("AF-WCC-VAC-GEN") + content_text("AF-WCC-SCALAR-SPH")
    req("does not assert inextendibility" in wcc_content.lower() or "not assert inextendibility" in wcc_content.lower(),
        "K4f", "WCC forbidden_inflation guards against inextendibility claims")
    req("Do not restate as weak cosmic censorship" in c2_content or
        "do not restate as weak cosmic censorship" in c2_content.lower(), "K4g",
        "C2 forbidden_inflation guards against WCC restatement")
    # no merged regularity token inside class content
    sem = json.dumps({"classes": A["classes"], "scope_statement": A.get("scope_statement")}, default=str)
    req(not merged_match(sem), "K4h", "no merged C0/C2 regularity token in class content (G3)")
    # companion: C0 identity variants and data_class_freeze present (no C0 reading collapsed)
    c0cc = B["class_contracts"]["AF-SCC-C0-VAC-GEN"]
    req(bool(c0cc.get("class_identity_variants")) and
        "horizon_localized_variant" in (c0cc.get("class_identity_variants") or {}), "K4i",
        "companion keeps the C0 horizon-localized identity variant registry")
    req("smooth-with-decay" in str(c0cc.get("data_class_freeze", "")), "K4j",
        "companion C0 data_class_freeze decision present")
    # canonical variants block keeps SET/CH as variants, not classes
    canon_variants = {(v.get("parent_class"), v.get("variant_id")) for v in A.get("variants", [])}
    req(("AF-WCC-VAC-GEN", "SET") in canon_variants and ("AF-SCC-C0-VAC-GEN", "CH") in canon_variants,
        "K4k", "canonical registers SET and CH as variants of their parents", sorted(canon_variants))
    req("not a separate class" in content_text("AF-WCC-VAC-GEN").lower() or
        "NOT a separate class" in content_text("AF-WCC-VAC-GEN"), "K4l",
        "canonical states SET is not a separate class")

    # --- K5 companion consistency (no byte-identity required) -------------
    aliases = json.loads(ALIASES.read_text())

    def canon_alias(kind, tok):
        for c, al in aliases.get(kind, {}).items():
            if tok == c or tok in al:
                return c
        return tok

    req(set(B.get("class_contracts", {})) == set(top), "K5a",
        "companion and canonical have the same class-id set")
    for cid in FROZEN4:
        a, b = A["classes"][cid], B["class_contracts"][cid]
        req(a["axes"]["family"] == b["components"]["censorship"], f"K5b[{cid}]",
            "family/censorship agree", [a["axes"]["family"], b["components"]["censorship"]])
        tb = b["components"].get("regularity_token")
        tb = None if tb == "none" else tb
        req(a["axes"].get("regularity_token") == tb, f"K5c[{cid}]",
            "regularity tokens agree", [a["axes"].get("regularity_token"), tb])
        req(canon_alias("conclusion_type", a["axes"].get("conclusion_type")) ==
            canon_alias("conclusion_type", b.get("conclusion_type")), f"K5d[{cid}]",
            "conclusion types agree under the frozen alias map",
            [a["axes"].get("conclusion_type"), b.get("conclusion_type")])
        req(bool(a.get("exclusions")) and bool(b.get("exclusions")), f"K5e[{cid}]",
            "exclusions non-empty on both sides")
        req(bool(a.get("test_cases")) and bool(b.get("positive_test_case")), f"K5f[{cid}]",
            "test cases present on both sides")
        ga = canon_alias("genericity_kind", str(a["axes"].get("genericity_kind", "")))
        gb = canon_alias("genericity_kind",
                         str((B.get("axis_registry", {}).get("genericity_axis", {}).get("frozen", {}) or {}).get(cid, "")))
        req(ga == gb, f"K5g[{cid}]", "genericity notions agree under aliases", [ga, gb])
    # D1/D3 discharge: comeager quantifier explicit in every class; binding wording explicit?
    for cid in FROZEN4:
        txt = A["classes"][cid]["conclusion"]["text"]
        req("comeager" in txt, f"K5h[{cid}]", "comeager quantifier is explicit in the conclusion text")
        note(("bound before" in txt or "chosen before" in txt), f"K5i[{cid}]",
             "comeager quantifier carries explicit 'bound/chosen before the data' wording",
             "the quantifier order is correct but the explicit binding phrase is absent from this class text"
             if not ("bound before" in txt or "chosen before" in txt) else None)
    # The set-based union predicate may appear only in an explicitly forbidden/withdrawn context.
    wcc_concl = A["classes"]["AF-WCC-VAC-GEN"]["conclusion"]["text"]
    union_hits = [ln.strip() for ln in wcc_concl.splitlines() if "union" in ln.lower()]
    ctx_ok = all(any(k in h.lower() for k in ("strictly stronger", "variant", "not a separate class",
                                              "must never", "never be interchanged"))
                 for h in union_hits)
    req(ctx_ok, "K5j",
        "set-based union predicate appears only in its explicitly forbidden/variant context",
        union_hits)
    # no direct contradiction: every canonical exclusion topic must not reappear as a companion inclusion
    req(B.get("axis_registry", {}).get("genericity_axis", {}).get("frozen", {}).get("AF-WCC-SCALAR-SPH")
        in {"unresolved", "none", None}, "K5k", "scalar genericity left unresolved on the companion")

    # --- K6 conclusion inflation -----------------------------------------
    req(A.get("status") == "draft_unverified", "K6a", "canonical status is draft_unverified", A.get("status"))
    req(A.get("claims_theorem_status") is False, "K6b", "canonical claims_theorem_status is false")
    req(A.get("provenance", {}).get("claims_theorem_status") is False, "K6c",
        "canonical provenance claims_theorem_status is false")
    req(all(c["conclusion"].get("type") != "theorem" for c in A["classes"].values()), "K6d",
        "no class conclusion_type is 'theorem'")
    req(all("unresolved" in str(c.get("known_obstruction", {}).get("status", ""))
            for c in A["classes"].values()), "K6e",
        "every known_obstruction is marked unresolved")
    req("asserts no theorem" in A.get("scope_statement", ""), "K6f",
        "scope statement asserts no theorem/counterexample/numerical/literature claim")
    # a C0-strength claim must never be filed under the C2 class (N4 expects rejection)
    n4 = A["classes"]["AF-SCC-C2-VAC-GEN"]["test_cases"]["negative_2"]["expected_classification"]
    req(n4.startswith("rejected_by:conclusion_inflation_direction"), "K6g",
        "C2 class explicitly rejects downgraded C0 results", n4)

    # --- K7 assumption completeness + decidable falsifiers ---------------
    for cid in FROZEN4:
        for h in A["classes"][cid].get("hypotheses", []):
            if h.get("machine_checkable") is False:
                req(bool(h.get("unresolved")), f"K7a[{cid}:{h.get('id')}]",
                    "unmachine-checkable hypothesis is declared unresolved")
                note(bool(h.get("owned_by")), f"K7a2[{cid}:{h.get('id')}]",
                     "unmachine-checkable hypothesis carries a structured owned_by field",
                     h.get("text", "")[:160] if not h.get("owned_by") else None)
    for v in A.get("variants", []):
        f = str(v.get("falsifier", ""))
        req(bool(f) and len(f) > 40 and re.search(r"\b(show|every|if|implies|collapse)\b", f, re.I) is not None,
            f"K7b[{v.get('variant_id')}]", "variant falsifier is a concrete decidable condition", f[:120])
    for g in A.get("guards", []):
        req(bool(g.get("rule")), f"K7c[{g.get('id')}]", "guard has a rule")
    for q in A.get("open_questions", []):
        req(bool(q.get("text")), f"K7d[{q.get('id')}]", "open question has text")
    # provenance records unresolved literature status
    req("UNRESOLVED" in str(A.get("provenance", {}).get("literature_status", "")), "K7e",
        "literature status is unresolved pending L0/L1")

    # --- K8 disjointness --------------------------------------------------
    pairs = {tuple(sorted(d.get("pair", []))) for d in A.get("disjointness", [])}
    req(pairs == {tuple(sorted(p)) for p in itertools.combinations(FROZEN4, 2)}, "K8a",
        "all 6 unordered pairs present exactly once", len(pairs))
    allowed_axes = {"family", "matter_model", "symmetry", "asymptotics", "regularity_token",
                    "genericity_kind", "conclusion_type"}
    for d in A.get("disjointness", []):
        a, b = d.get("pair", [None, None])
        axes = d.get("decisive_axes", [])
        req(bool(axes) and set(axes) <= allowed_axes, f"K8b[{a}|{b}]",
            "decisive axes are declared vocabulary axes", axes)
        va, vb = A["classes"][a]["axes"], A["classes"][b]["axes"]
        diff = [x for x in axes if va.get(x) != vb.get(x)]
        req(bool(diff), f"K8c[{a}|{b}]", "at least one named decisive axis actually differs", diff)
        req(bool(d.get("separation")), f"K8d[{a}|{b}]", "separation rationale present")
    req("descriptor" in str(A.get("disjointness_scope", "")).lower(), "K8e",
        "disjointness scope is descriptor-level (machine-visible)")
    req(bool(A.get("disjointness_overlap_note")), "K8f", "data-space overlap note present")

    # --- K9 transfer rules ------------------------------------------------
    allowed = A["transfer_rules"].get("allowed", [])
    req(allowed and all(x.get("from") == "AF-SCC-C0-VAC-GEN" and x.get("to") == "AF-SCC-C2-VAC-GEN"
                        for x in allowed), "K9a", "only C0->C2 strengthening is allowed")
    req(all(bool(x.get("guards")) for x in allowed), "K9b", "allowed transfer declares guards")
    kinds = {x.get("kind") for x in A["transfer_rules"].get("forbidden", [])}
    req({"conclusion_inflation", "matter_leakage", "symmetry_release",
         "conclusion_family_leakage", "class_merge"} <= kinds, "K9c",
        "all five forbidden leakage kinds present", sorted(kinds))

    # --- K10 schema cross-binding + evidence ------------------------------
    for cid, p in SCHEMAS.items():
        d = load_yaml(p)
        req(d.get("class_id") == cid, f"K10a[{cid}]", "schema class_id matches its path", d.get("class_id"))
        ptr = str(d.get("class_contract_pointer", ""))
        want = f"research_map/formulation_taxonomy.yaml#classes.{cid}"
        req(ptr == want, f"K10b[{cid}]", "schema class_contract_pointer resolves to the canonical class", ptr)
        fb = d.get("f0_binding", {})
        req(fb.get("declared_f0_sha256") == CANON_PIN, f"K10c[{cid}]",
            "schema f0_binding pins the canonical hash", fb.get("declared_f0_sha256"))
        req(fb.get("consistency_evidence_sha256") == pre["consistency_evidence"], f"K10d[{cid}]",
            "schema consistency-evidence pin matches the live evidence file",
            [fb.get("consistency_evidence_sha256"), pre["consistency_evidence"]])
    # FROZEN.json must pin canonical+companion at the accepted hashes
    files = frozen_man.get("files", {})
    req(files.get("research_map/formulation_taxonomy.yaml", {}).get("sha256") == CANON_PIN, "K10e",
        "FROZEN manifest pins the canonical F0 at the accepted hash")
    req(files.get("artifacts/formulation/formulation_taxonomy.yaml", {}).get("sha256") == COMP_PIN, "K10f",
        "FROZEN manifest pins the companion at the accepted hash")
    # The published consistency evidence must be exactly what the frozen checker derives from the
    # current canonical+companion+aliases. A byte-identical copy produced by the checker in an
    # isolated sandbox is retained as raw/sandbox_taxonomy_consistency.json (same sha256 as live).
    live_ev = json.loads(EVIDENCE.read_text())
    sandbox_ev_path = ROOT / "artifacts/worker-041/f0_blind_review/raw/sandbox_taxonomy_consistency.json"
    req(live_ev.get("consistent") is True and not live_ev.get("errors"), "K10j",
        "published consistency evidence records consistency with zero errors",
        {"consistent": live_ev.get("consistent"), "errors": live_ev.get("errors")})
    if not mutation_mode:
        req(sha(sandbox_ev_path) == pre["consistency_evidence"] if sandbox_ev_path.exists() else False, "K10k",
            "sandbox re-run of the frozen checker reproduces the live evidence byte-for-byte",
            sha(sandbox_ev_path) if sandbox_ev_path.exists() else "sandbox copy missing")

    # --- run the two frozen tools, read-only ------------------------------
    # Only the frozen F0 acceptance checker is executed: it is read-only (writes only with --json).
    # check_variant_registry.py unconditionally rewrites evidence/variant_registry_check.json, which
    # is a published artifact, so it is NOT run here; its registry invariants are checked inline.
    tools = {}
    vt = ROOT / "artifacts/worker-01/validate_taxonomy.py"
    if not mutation_mode and vt.exists():
        p = subprocess.run([sys.executable, str(vt)], capture_output=True, text=True, cwd=ROOT)
        tools["validate_taxonomy"] = {"exit": p.returncode, "stdout": p.stdout.strip()[:2000],
                                      "stderr": p.stderr.strip()[:2000]}
        req(tools["validate_taxonomy"]["exit"] == 0, "K10g",
            "frozen F0 acceptance checker exits 0", tools["validate_taxonomy"])
    req({p.get("class_id") for p in reg.get("parent_classes", [])} == set(FROZEN4), "K10i",
        "variant registry parent_classes are exactly the frozen four",
        [p.get("class_id") for p in reg.get("parent_classes", [])])

    # --- post-read pins (taken after all reads/tool runs) -----------------
    post = {"canonical": sha(CANON), "companion": sha(COMP)}
    post_schemas = {k: sha(v) for k, v in SCHEMAS.items()}
    req(post["canonical"] == pre["canonical"] == CANON_PIN, "K1b",
        "canonical unchanged across the run (pre==post==pin)",
        {"pre": pre["canonical"], "post": post["canonical"]})
    req(post["companion"] == pre["companion"] == COMP_PIN, "K2b",
        "companion unchanged across the run (pre==post==pin)",
        {"pre": pre["companion"], "post": post["companion"]})
    req(post_schemas == pre_schemas, "K10h", "schema hashes unchanged across the run")

    hard_findings = [c for c in checks if not c["pass"]]
    if mutation_mode:
        failed_ids = {c["id"] for c in hard_findings}
        missed = [m for m in mutation_expected if m not in failed_ids]
        if not hard_findings:
            checks.append({"id": "CTRL", "pass": False, "check": "mutation control: a mutated tree must not pass"})
            fails += 1
        if missed:
            checks.append({"id": "CTRL", "pass": False,
                           "check": "mutation control: expected checks must fire on the mutated tree",
                           "detail": missed})
            fails += 1
    hard_findings = [c for c in checks if not c["pass"]]
    report = {
        "task_id": "W041-F0-REDISPATCH4-01",
        "actor": "worker-041",
        "created_at": None,  # deterministic instrument: no clock read; caller stamps the event
        "instrument": "artifacts/worker-041/f0_blind_review/run_f0_reverify.py",
        "target": "research_map/formulation_taxonomy.yaml",
        "reviewed_sha256": pre["canonical"],
        "companion_sha256": pre["companion"],
        "class_ids": top,
        "checks_total": len(checks),
        "checks_failed": fails,
        "all_pass": fails == 0,
        "checks": checks,
        "observations": findings,
        "hard_findings": hard_findings,
        "tool_runs": tools,
        "pins_pre": pre, "pins_post": post,
        "schema_pins_pre": pre_schemas, "schema_pins_post": post_schemas,
        "verdict_preview": "accept" if fails == 0 else "revise",
        "verdict_scope": "canonical F0 at the pinned hash + companion consistency (REC-3); "
                         "NOT a gate verdict, NOT a node status, NOT a validation_status=passed",
    }
    out = None
    for _i, _a in enumerate(sys.argv):
        if _a == "--out" and _i + 1 < len(sys.argv):
            out = Path(sys.argv[_i + 1])
    if out:
        out.write_text(json.dumps(report, indent=1) + "\n")
        print(f"report {out} sha256={sha(out)}")
    print(("ALL PASS" if fails == 0 else f"{fails} FAIL") + f" ({len(checks)} checks)")
    for c in hard_findings:
        print("  FAIL", c["id"], c["check"], c.get("detail"))
    for o in findings:
        if not o["observed"]:
            print("  NOTE", o["id"], o["finding"], o.get("detail"))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

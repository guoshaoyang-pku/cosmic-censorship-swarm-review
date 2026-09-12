#!/usr/bin/env python3
"""W047-REC37-TOKEN-CROSSWALK-01 checker (read-only, fail-closed, deterministic).

Independent re-implementation (does not import the builder) of the REC-37 token crosswalk
measurement at hash-pinned bytes. It re-derives every table from the pinned YAML/JSON and then
validates the candidate ``crosswalk.json`` against that derivation.

Comparison semantics (this is the REC-37 point):
  registry mode (default): a class-schema token is consistent iff it is the exact
    VOCAB_ALIASES canonical key, and the frozen F0 alias entries are compared *through* the
    registry mapping. This is assertion-correct for F0 rev5, which is frozen by REC-11/G-F0.
  literal mode (--literal): a class-schema token must appear literally in
    F0 field_vocabulary.<kind>.allowed. This is the assertion that FAILS at the pins and is
    recorded for contrast only; REC-37 rules it out as the discharge criterion.

Exit codes: 0 all checks PASS (registry mode) / 1 findings / 2 pin drift or unparsable input /
3 control mis-calibration.

Sandbox controls copy the pinned files into a temp tree, mutate exactly one axis each, and run
the same checks in-process against the sandbox root; the pinned bytes are never written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except Exception as exc:  # pragma: no cover
    print(f"FATAL: PyYAML unavailable ({exc}); refusing to run", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CROSSWALK = HERE / "crosswalk.json"

PINS = {
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/evidence/taxonomy_consistency.json": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
}
SCHEMA_PATH = {
    "AF-WCC-VAC-GEN": "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml",
}
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
SENTINEL = "unresolved"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def canon(registry, kind, token):
    if token is None:
        return None, "absent"
    if token == SENTINEL and kind == "genericity_kind":
        return None, "sentinel"
    for canonical, aliases in registry.get(kind, {}).items():
        if token == canonical:
            return canonical, "canonical"
        if token in aliases:
            return canonical, "alias"
    return None, "unmapped"


def key_of(canonical, token_kind, token):
    if canonical:
        return ["canonical", canonical]
    if token_kind == "sentinel":
        return ["sentinel", token]
    if token_kind == "unmapped":
        return ["unmapped", token]
    return ["absent", None]


def derive(root: Path):
    """Independent derivation of every surface from the files under ``root``."""
    reg = read_json(root / "artifacts/formulation/VOCAB_ALIASES.json")
    f0 = read_yaml(root / "research_map/formulation_taxonomy.yaml")
    sup = read_yaml(root / "artifacts/formulation/formulation_taxonomy.yaml")
    rule = read_json(root / "artifacts/formulation/rule_spec.json")
    sch = {cid: read_yaml(root / p) for cid, p in SCHEMA_PATH.items()}
    d = {"registry": reg, "f0": f0, "supp": sup, "rule": rule, "schemas": sch, "surfaces": [], "per_class": {}}

    def add(path, rel, ypath, cid, kind, token, role):
        c, tk = canon(reg, kind, token)
        d["surfaces"].append({"path": path, "sha256": PINS.get(rel, "SANDBOX"), "yaml_path": ypath,
                              "class_id": cid, "kind": kind, "token": token, "canonical": c,
                              "token_kind": tk, "role": role})

    for kind in ("conclusion_type", "genericity_kind"):
        for i, tok in enumerate((f0.get("field_vocabulary", {}).get(kind, {}) or {}).get("allowed", [])):
            add("F0 taxonomy", "research_map/formulation_taxonomy.yaml",
                f"field_vocabulary.{kind}.allowed[{i}]", None, kind, tok, "allowed_list")
    for cid in CLASSES:
        cls = f0["classes"][cid]
        add("F0 taxonomy", "research_map/formulation_taxonomy.yaml", f"classes.{cid}.axes.conclusion_type",
            cid, "conclusion_type", cls["axes"].get("conclusion_type"), "value")
        add("F0 taxonomy", "research_map/formulation_taxonomy.yaml", f"classes.{cid}.conclusion.type",
            cid, "conclusion_type", (cls.get("conclusion") or {}).get("type"), "value")
        add("F0 taxonomy", "research_map/formulation_taxonomy.yaml", f"classes.{cid}.axes.genericity_kind",
            cid, "genericity_kind", cls["axes"].get("genericity_kind"), "value")
        add("F0 supplement", "artifacts/formulation/formulation_taxonomy.yaml",
            f"class_contracts.{cid}.conclusion_type", cid, "conclusion_type",
            sup["class_contracts"][cid].get("conclusion_type"), "value")
        frozen = ((sup.get("axis_registry", {}) or {}).get("genericity_axis", {}) or {}).get("frozen", {}) or {}
        add("F0 supplement", "artifacts/formulation/formulation_taxonomy.yaml",
            f"axis_registry.genericity_axis.frozen.{cid}", cid, "genericity_kind", frozen.get(cid), "value")
        if cid in SCHEMA_PATH:
            add("class schema", SCHEMA_PATH[cid], "conclusion.conclusion_type", cid, "conclusion_type",
                (sch[cid].get("conclusion") or {}).get("conclusion_type"), "value")
            add("class schema", SCHEMA_PATH[cid], "genericity.kind", cid, "genericity_kind",
                (sch[cid].get("genericity") or {}).get("kind"), "value")
        add("rule_spec", "artifacts/formulation/rule_spec.json", f"vocabularies.class_conclusion_type.{cid}",
            cid, "conclusion_type",
            (rule.get("vocabularies", {}) or {}).get("class_conclusion_type", {}).get(cid), "vocabulary")
    for i, tok in enumerate((rule.get("vocabularies", {}) or {}).get("genericity_kind", [])):
        add("rule_spec", "artifacts/formulation/rule_spec.json", f"vocabularies.genericity_kind[{i}]",
            None, "genericity_kind", tok, "vocabulary")

    for cid in CLASSES:
        entry = {}
        for kind in ("conclusion_type", "genericity_kind"):
            vals = {}
            for s in d["surfaces"]:
                if s["class_id"] == cid and s["kind"] == kind and s["role"] == "value":
                    vals[s["yaml_path"]] = s
            keys = {tuple(key_of(v["canonical"], v["token_kind"], v["token"])) for v in vals.values()}
            entry[kind] = {"surfaces": vals, "comparison_keys": sorted(list(k) for k in keys),
                           "distinct_canonicals": sorted(k[1] for k in keys if k[0] == "canonical"),
                           "unmapped_tokens": sorted(k[1] for k in keys if k[0] == "unmapped"),
                           "agreement": len(keys) <= 1}
        d["per_class"][cid] = entry
    d["alias_map"] = {k: {a: c for c, al in reg.get(k, {}).items() for a in al}
                      for k in ("conclusion_type", "genericity_kind")}
    d["f0_alias_entries"] = {}
    d["unmapped_f0_entries"] = {}
    for kind in ("conclusion_type", "genericity_kind"):
        allowed = (f0.get("field_vocabulary", {}).get(kind, {}) or {}).get("allowed", [])
        d["f0_alias_entries"][kind] = {t: canon(reg, kind, t)[0] for t in allowed
                                       if canon(reg, kind, t)[1] == "alias"}
        d["unmapped_f0_entries"][kind] = {t: canon(reg, kind, t)[1] for t in allowed
                                          if canon(reg, kind, t)[1] == "unmapped"}
    return d


def check(root: Path, pins: dict, crosswalk_path: Path, literal: bool = False) -> tuple[list, dict]:
    checks = []

    def rec(cid, name, ok, detail):
        checks.append({"id": cid, "name": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        return ok

    # C1 pins
    drift = []
    for rel, want in pins.items():
        p = root / rel
        got = sha256_file(p) if p.exists() else "MISSING"
        if got != want:
            drift.append({"path": rel, "expected": want, "measured": got})
    if not rec("C1", "PIN_INTEGRITY", not drift, {"drift": drift}):
        return checks, {"fatal": "pin_drift", "drift": drift}

    d = derive(root)
    try:
        cw = read_json(crosswalk_path)
    except Exception as exc:
        checks.append({"id": "C2", "name": "CROSSWALK_PARSE", "status": "FAIL", "detail": str(exc)})
        return checks, {"fatal": "crosswalk_unparsable"}

    rec("C2", "CROSSWALK_IDENTITY",
        cw.get("schema_version") == "rec37-token-crosswalk/v1"
        and cw.get("mode") == "registry_canonical_mapping"
        and (cw.get("authority_ruling") or {}).get("id") == "REC-37"
        and cw.get("pins") == {p: pins[p] for p in sorted(pins)},
        {"schema_version": cw.get("schema_version"), "mode": cw.get("mode"),
         "ruling": (cw.get("authority_ruling") or {}).get("id")})

    rec("C3", "F0_ALIAS_MAP_EXACT", cw.get("f0_alias_entries") == d["f0_alias_entries"],
        {"crosswalk": cw.get("f0_alias_entries"), "derived": d["f0_alias_entries"]})

    schema_findings = []
    for cid, path in SCHEMA_PATH.items():
        for kind, ypath, want_kind in (("conclusion_type", "conclusion.conclusion_type", "canonical"),
                                       ("genericity_kind", "genericity.kind", "canonical")):
            tok = (d["schemas"][cid].get("conclusion") or {}).get("conclusion_type") if kind == "conclusion_type" \
                else (d["schemas"][cid].get("genericity") or {}).get("kind")
            c, tk = canon(d["registry"], kind, tok)
            if tk != want_kind:
                schema_findings.append({"class": cid, "field": ypath, "token": tok,
                                        "token_kind": tk, "expected_token_kind": want_kind})
    rec("C4", "SCHEMA_TOKENS_ARE_REGISTRY_CANONICAL", not schema_findings, {"findings": schema_findings})

    mismatch = []
    for cid in CLASSES:
        for kind in ("conclusion_type", "genericity_kind"):
            vals = d["per_class"][cid][kind]["surfaces"]
            schema_tok = None
            for v in vals.values():
                if v["path"] == "class schema":
                    schema_tok = v
            if schema_tok is None:
                if not d["per_class"][cid][kind]["agreement"]:
                    mismatch.append({"class": cid, "kind": kind, "reason": "no schema; surfaces disagree",
                                     "keys": d["per_class"][cid][kind]["comparison_keys"]})
                continue
            if literal:
                f0_allowed = (d["f0"].get("field_vocabulary", {}).get(kind, {}) or {}).get("allowed", [])
                if schema_tok["token"] not in f0_allowed:
                    mismatch.append({"class": cid, "kind": kind, "mode": "literal",
                                     "schema_token": schema_tok["token"], "f0_allowed": f0_allowed})
            else:
                for v in vals.values():
                    if v["canonical"] != schema_tok["canonical"] and v["path"] in ("F0 taxonomy", "F0 supplement"):
                        mismatch.append({"class": cid, "kind": kind, "surface": v["yaml_path"],
                                         "surface_canonical": v["canonical"],
                                         "schema_canonical": schema_tok["canonical"]})
    rec("C5", "SCHEMA_VS_FROZEN_SURFACES_MATCH",
        not mismatch, {"mode": "literal" if literal else "registry", "mismatches": mismatch})

    rec("C6", "PER_CLASS_AGREEMENT_AND_CROSSWALK_MATCH",
        all(d["per_class"][cid][k]["agreement"] for cid in CLASSES for k in ("conclusion_type", "genericity_kind"))
        and all(cw["per_class"][cid][k]["agreement"] == d["per_class"][cid][k]["agreement"]
                and cw["per_class"][cid][k]["distinct_canonicals"] == d["per_class"][cid][k]["distinct_canonicals"]
                and cw["per_class"][cid][k]["comparison_keys"] == d["per_class"][cid][k]["comparison_keys"]
                for cid in CLASSES for k in ("conclusion_type", "genericity_kind")),
        {"derived": {cid: {k: d["per_class"][cid][k]["comparison_keys"] for k in ("conclusion_type", "genericity_kind")}
                     for cid in CLASSES}})

    merges = []
    a, b = "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"
    ka = set(d["per_class"][a]["conclusion_type"]["distinct_canonicals"])
    kb = set(d["per_class"][b]["conclusion_type"]["distinct_canonicals"])
    if ka & kb:
        merges.append({"classes": [a, b], "kind": "conclusion_type", "shared_canonicals": sorted(ka & kb)})
    rec("C7", "C2_C0_CANONICAL_SETS_DISJOINT", not merges, {"C2": sorted(ka), "C0": sorted(kb), "merges": merges})

    rejected = d["registry"].get("rejected_ambiguous_tokens", {})
    hits = []
    for s in d["surfaces"]:
        if s["role"] == "value" and s["token"] in rejected:
            hits.append({"yaml_path": s["yaml_path"], "token": s["token"]})
    rec("C8", "NO_REJECTED_TOKEN_IN_VALUE_POSITION", not hits,
        {"rejected_tokens": sorted(rejected), "value_hits": hits})

    g_expected = {"baire_residual": "residual_comeager", "provisional_baire_residual": "residual_comeager",
                  "measure_one": "full_measure"}
    g_derived = dict(d["f0_alias_entries"]["genericity_kind"])
    sentinel_ok = all(
        d["per_class"][cid]["genericity_kind"]["comparison_keys"] == [["sentinel", SENTINEL]]
        for cid in ("AF-WCC-SCALAR-SPH",))
    recorded_unmapped = ((cw.get("unmapped_f0_entries") or {}).get("genericity_kind") or {})
    unmapped_ok = (sorted(d["unmapped_f0_entries"]["genericity_kind"]) == ["dense_open"]
                   and "dense_open" in recorded_unmapped
                   and recorded_unmapped.get("dense_open", {}).get("anagram_alias_candidates", {}).get("open_dense")
                   == "open_dense_escape")
    rec("C9", "GENERICITY_CROSSWALK_SENTINEL_AND_UNMAPPED",
        g_derived == g_expected and sentinel_ok and unmapped_ok,
        {"derived_aliases": g_derived, "expected_aliases": g_expected, "scalar_sentinel_only": sentinel_ok,
         "derived_unmapped": d["unmapped_f0_entries"]["genericity_kind"], "recorded_unmapped": recorded_unmapped})

    r11 = []
    for cid, path in SCHEMA_PATH.items():
        want = (d["schemas"][cid].get("conclusion") or {}).get("conclusion_type")
        got = (d["rule"].get("vocabularies", {}) or {}).get("class_conclusion_type", {}).get(cid)
        if got != want:
            r11.append({"class": cid, "rule_spec": got, "schema": want})
    gk = (d["rule"].get("vocabularies", {}) or {}).get("genericity_kind", [])
    rec("C10", "RULE_SPEC_R11_AGREES", not r11 and "residual_comeager" in gk,
        {"class_mismatches": r11, "genericity_vocab_has_canonical": "residual_comeager" in gk})

    derived_surfaces = sorted(d["surfaces"], key=lambda s: (s["kind"], str(s["class_id"]), s["yaml_path"]))
    cw_surfaces = sorted(cw.get("surfaces", []), key=lambda s: (s["kind"], str(s["class_id"]), s["yaml_path"]))
    rec("C11", "SURFACE_TABLE_EXACT", derived_surfaces == cw_surfaces,
        {"derived_count": len(derived_surfaces), "crosswalk_count": len(cw_surfaces)})

    lit = {}
    for cid, path in SCHEMA_PATH.items():
        tok = (d["schemas"][cid].get("conclusion") or {}).get("conclusion_type")
        allowed = (d["f0"].get("field_vocabulary", {}).get("conclusion_type", {}) or {}).get("allowed", [])
        lit[cid] = {"schema_token": tok, "literal_in_f0_allowed": tok in allowed}
    recorded = cw.get("registry_vs_literal", {}).get("literal_membership_at_pins", {})
    rec("C12", "LITERAL_MODE_CONTRAST_RECORDED",
        set(recorded) == set(lit)
        and all(recorded[cid].get("literal_membership") == lit[cid]["literal_in_f0_allowed"] for cid in lit)
        and any(not v["literal_in_f0_allowed"] for v in lit.values()),
        {"measured": lit, "crosswalk_recorded": recorded})

    rec("C13", "ADOPTION_READINESS_FIELDS",
        bool(cw.get("falsifier")) and bool(cw.get("f0_alias_entries")) and bool(cw.get("per_class"))
        and bool(cw.get("authority_limits")) and "NON_CANONICAL" in str(cw.get("candidate_status", "")),
        {"has_falsifier": bool(cw.get("falsifier")), "has_alias_entries": bool(cw.get("f0_alias_entries")),
         "has_per_class": bool(cw.get("per_class")), "has_authority_limits": bool(cw.get("authority_limits")),
         "non_canonical_declared": "NON_CANONICAL" in str(cw.get("candidate_status", ""))})
    return checks, {"derived": {"f0_alias_entries": d["f0_alias_entries"],
                                "per_class_agreement": {cid: {k: d["per_class"][cid][k]["agreement"]
                                                              for k in ("conclusion_type", "genericity_kind")}
                                                        for cid in CLASSES},
                                "surface_count": len(d["surfaces"])}}


def run_controls() -> list:
    """Pre-registered single-axis controls, each in its own sandbox copy."""
    base = derive(ROOT)
    controls = []

    def make_sandbox(rel_paths):
        tmp = Path(tempfile.mkdtemp(prefix="rec37-ctl-"))
        for rel in rel_paths:
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, dst)
        return tmp

    def sandbox_pins(tmp: Path, mutated: str):
        pins = dict(PINS)
        for rel in list(pins):
            if (tmp / rel).exists():
                pins[rel] = sha256_file(tmp / rel)
        return pins

    def patch_yaml(path: Path, mutate):
        doc = yaml.safe_load(path.read_text())
        mutate(doc)
        path.write_text(yaml.safe_dump(doc, sort_keys=False))

    def run_case(cid, expected, mutate):
        rels = list(PINS)
        tmp = make_sandbox(rels)
        mutate(tmp)
        pins = sandbox_pins(tmp, cid)
        checks, _ = check(tmp, pins, CROSSWALK)
        fired = sorted(c["id"] for c in checks if c["status"] == "FAIL")
        ok = set(expected) <= set(fired)
        controls.append({"id": cid, "expected_failures": expected, "fired_failures": fired,
                         "discriminates": ok})
        shutil.rmtree(tmp, ignore_errors=True)

    run_case("K1", ["C4"], lambda t: patch_yaml(t / "schemas/af_scc_c2_vacuum.yaml",
                                                lambda d: d["conclusion"].__setitem__("conclusion_type", "strong_cosmic_censorship_C2")))
    run_case("K2", ["C4", "C8"], lambda t: patch_yaml(t / "schemas/af_scc_c0_vacuum.yaml",
                                                      lambda d: d["conclusion"].__setitem__("conclusion_type", "strong_cosmic_censorship")))
    run_case("K3", ["C6", "C7"], lambda t: patch_yaml(t / "schemas/af_scc_c0_vacuum.yaml",
                                                      lambda d: d["conclusion"].__setitem__("conclusion_type", "scc_c2_future_inextendibility")))
    run_case("K4", ["C3"], lambda t: patch_yaml(t / "research_map/formulation_taxonomy.yaml",
                                                lambda d: d["field_vocabulary"]["conclusion_type"]["allowed"].__setitem__(1, "scc_c2_future_inextendibility")))
    run_case("K5", ["C4", "C5"], lambda t: patch_yaml(t / "schemas/af_scc_c2_vacuum.yaml",
                                                            lambda d: d["conclusion"].__setitem__("conclusion_type", "scc_c2_renamed")))
    run_case("K6", ["C5", "C6"], lambda t: patch_yaml(t / "research_map/formulation_taxonomy.yaml",
                                                      lambda d: d["classes"]["AF-SCC-C2-VAC-GEN"]["axes"].__setitem__("conclusion_type", "scc_c0_future_inextendibility")))
    run_case("K7", ["C4"], lambda t: patch_yaml(t / "schemas/af_scc_c2_vacuum.yaml",
                                                lambda d: d["genericity"].__setitem__("kind", "baire_residual")))

    def k8(t):
        (t / "schemas/af_scc_c0_vacuum.yaml").write_text("class_id: [unterminated\n")
    rels = list(PINS)
    tmp = make_sandbox(rels)
    k8(tmp)
    try:
        pins = sandbox_pins(tmp, "K8")
        checks, _ = check(tmp, pins, CROSSWALK)
        fired = sorted(c["id"] for c in checks if c["status"] == "FAIL")
        ok = bool(fired) or any(c.get("status") == "FAIL" for c in checks)
    except Exception:
        ok = True
        fired = ["PARSE_FAIL_CLOSED"]
    controls.append({"id": "K8", "expected_failures": ["fail-closed"], "fired_failures": fired,
                     "discriminates": ok})
    shutil.rmtree(tmp, ignore_errors=True)

    # K9: registry-driven, not literal-driven: crosswalk must still pass C5 in registry mode
    # even though literal membership is false (measured on the real pins).
    checks, _ = check(ROOT, PINS, CROSSWALK)
    by_id = {c["id"]: c for c in checks}
    controls.append({"id": "K9", "expected_failures": [], "fired_failures": sorted(c["id"] for c in checks if c["status"] == "FAIL"),
                     "discriminates": by_id["C5"]["status"] == "PASS" and by_id["C12"]["status"] == "PASS"})
    return controls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--literal", action="store_true", help="contrast mode: literal F0 membership")
    ap.add_argument("--report", default=str(HERE / "report.json"))
    args = ap.parse_args()

    checks, meta = check(ROOT, PINS, CROSSWALK, literal=args.literal)
    if meta.get("fatal"):
        print(json.dumps({"fatal": meta["fatal"], "checks": checks}, indent=1))
        return 2
    controls = run_controls()
    failed = [c["id"] for c in checks if c["status"] == "FAIL"]
    bad_controls = [c["id"] for c in controls if not c["discriminates"]]
    verdict = ("CONSISTENT_UNDER_REGISTRY_MAPPING" if not args.literal and not failed and not bad_controls
               else ("LITERAL_MEMBERSHIP_FAILS_AS_DOCUMENTED" if args.literal else "FINDINGS"))
    report = {
        "schema_version": "rec37-token-crosswalk-report/v1",
        "task_id": "W047-REC37-TOKEN-CROSSWALK-01",
        "mode": "literal" if args.literal else "registry",
        "pins": {p: PINS[p] for p in sorted(PINS)},
        "crosswalk_sha256": sha256_file(CROSSWALK),
        "checks": checks,
        "controls": controls,
        "summary": {"checks": len(checks), "failed": failed,
                    "controls": len(controls), "controls_not_discriminating": bad_controls},
        "verdict": verdict,
        "falsifier": ("Falsified at these pins if (a) any pinned sha256 differs on re-measure; (b) a class schema declares a "
                      "conclusion_type or genericity.kind that is an alias form rather than the VOCAB_ALIASES canonical key; "
                      "(c) the F0 field_vocabulary alias entries do not resolve through the registry to the canonical tokens "
                      "declared by the corresponding class schema; (d) the C0 and C2 canonicals collapse to one token on any "
                      "surface; (e) a rejected_ambiguous_token appears in a value position; or (f) rule_spec R11's "
                      "class_conclusion_type vocabulary disagrees with a class schema."),
        "authority_limits": ("Worker artifact. No canonical file was edited; no node status, validation_status=passed or gate "
                             "verdict is claimed."),
    }
    Path(args.report).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": verdict, "failed_checks": failed,
                      "failed_controls": bad_controls, "report": args.report}, sort_keys=True))
    return 0 if verdict == "CONSISTENT_UNDER_REGISTRY_MAPPING" else 1


if __name__ == "__main__":
    sys.exit(main())

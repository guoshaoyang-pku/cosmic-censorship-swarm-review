#!/usr/bin/env python3
"""Independent invariant checker for schemas/af_scc_c0_vacuum.yaml (F2b).

Written by deepseek-flash-07 for review F2b-review-07. It deliberately does NOT
import the lead's formulation tools (check_class_schema.py, spec_conformance_audit.py)
or the worker-06 binding gate; it re-derives the checks from the A0 rubric's
schema_formulation check list and from the four frozen class definitions in
evaluation_rubric.yaml.

Usage:
    python3 independent_checks.py [schema_path]

Prints a JSON report to stdout. Exit code 0 iff every hard assertion passes.
Warnings (d0_regularity_branches) never affect the exit code.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
MAP = ROOT / "research_map" / "research_map.json"
F0 = ROOT / "research_map" / "formulation_taxonomy.yaml"

FROZEN = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}
EXPECTED_SHA = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
REQUIRED_SLOTS = [
    "quantifiers",
    "topology",
    "data_class",
    "genericity",
    "future_null_infinity",
    "visibility",
    "conclusion_type",
]
# A composite-regularity string is only a defect when asserted, not when it appears
# inside a prohibition / must-not-conflate list. Context markers are taken from the
# schema's own lint vocabulary.
PROHIBITION_MARKERS = re.compile(
    r"must[_ ]not|forbidden|not_this_class|phrases_that_are_not|do not|never|"
    r"no containment|anti_scope|excluded|must not be|is not|cannot|forbids",
    re.I,
)
COMPOSITE = re.compile(r"C0\s*(?:or|/|,|and)\s*C2|C2\s*(?:or|/|,|and)\s*C0", re.I)
CLASS_TOKEN = re.compile(r"AF-[A-Z]+(?:-[A-Z0-9]+)+")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    schema_path = Path(sys.argv[1]) if len(sys.argv) > 1 else SCHEMA
    checks: list[dict] = []

    def add(check_id: str, ok: bool, detail: str, evidence=None, warn: bool = False):
        checks.append(
            {
                "check_id": check_id,
                "verdict": "warn" if warn else ("pass" if ok else "fail"),
                "detail": detail,
                "evidence": evidence or {},
            }
        )

    measured = sha256(schema_path)
    try:
        doc = yaml.safe_load(schema_path.read_text())
    except Exception as exc:  # noqa: BLE001 - report, do not traceback
        add("parse", False, f"YAML parse failed: {type(exc).__name__}: {exc}")
        print(json.dumps({"schema": str(schema_path), "sha256": measured, "checks": checks,
                          "verdict": "fail"}, indent=1))
        return 1
    if not isinstance(doc, dict):
        add("parse", False, "document is not a mapping")
        print(json.dumps({"schema": str(schema_path), "sha256": measured, "checks": checks,
                          "verdict": "fail"}, indent=1))
        return 1
    add("parse", True, "YAML mapping parsed")

    add("hash_pin", measured == EXPECTED_SHA,
        f"measured {measured[:16]} vs pinned {EXPECTED_SHA[:16]}",
        {"measured_sha256": measured, "pinned_sha256": EXPECTED_SHA})

    cid = doc.get("class_id")
    add("class_id_frozen", cid == "AF-SCC-C0-VAC-GEN",
        f"class_id={cid!r}; must be exactly the frozen AF-SCC-C0-VAC-GEN",
        {"class_id": cid, "frozen": sorted(FROZEN)})

    node = doc.get("node_id")
    map_node_ok = False
    map_detail = "map unreadable"
    try:
        m = json.loads(MAP.read_text())
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                if n.get("id") == "F2b":
                    map_node_ok = n.get("artifact") == "schemas/af_scc_c0_vacuum.yaml"
                    map_detail = f"map node F2b artifact={n.get('artifact')!r}"
    except Exception as exc:  # noqa: BLE001
        map_detail = f"map read failed: {type(exc).__name__}"
    add("node_binding", node == "F2b" and map_node_ok,
        f"schema node_id={node!r}; {map_detail}", {"node_id": node, "map": map_detail})

    q = doc.get("quantifiers", {})
    kinds = [step.get("kind") for step in q.get("ordered", []) if isinstance(step, dict)]
    add("quantifier_order", kinds == ["forall", "exists", "forall", "not_exists"],
        f"ordered kinds={kinds}", {"kinds": kinds})

    formal = str(q.get("formal", ""))
    stmt = str(doc.get("conclusion", {}).get("statement_formal", ""))
    formal_ok = all(tok in formal for tok in ("forall", "comeager", "not exists")) and \
        all(tok in stmt for tok in ("forall", "comeager", "not exists"))
    add("formal_statement_consistency", formal_ok,
        "quantifiers.formal and conclusion.statement_formal both carry "
        "forall/comeager/not-exists structure",
        {"quantifiers_formal": formal[:220], "statement_formal": stmt[:220]})

    reg = doc.get("regularity", {})
    ext_ok = (str(reg.get("extension_regularity")) == "C0"
              and str(reg.get("extension_solution_concept")) == "none")
    add("extension_regularity_xor", ext_ok,
        f"extension_regularity={reg.get('extension_regularity')!r}, "
        f"extension_solution_concept={reg.get('extension_solution_concept')!r}",
        {"extension_regularity": reg.get("extension_regularity"),
         "extension_solution_concept": reg.get("extension_solution_concept")})

    con = doc.get("conclusion", {})
    con_ok = (con.get("conclusion_type") == "scc_c0_future_inextendibility"
              and con.get("family") == "SCC"
              and con.get("epistemic_status") == "open_problem")
    add("conclusion_class_match", con_ok,
        f"conclusion_type={con.get('conclusion_type')!r}, family={con.get('family')!r}, "
        f"epistemic_status={con.get('epistemic_status')!r}")

    vis = doc.get("visibility", {})
    ip = doc.get("i_plus", {})
    wcc_ok = (vis.get("role") == "not_in_conclusion"
              and ip.get("role") == "assumption"
              and ip.get("in_conclusion") is False
              and ip.get("completeness_in_conclusion") is False)
    add("no_wcc_content_in_conclusion", wcc_ok,
        f"visibility.role={vis.get('role')!r}; i_plus.role={ip.get('role')!r}; "
        f"i_plus.in_conclusion={ip.get('in_conclusion')!r}; "
        f"completeness_in_conclusion={ip.get('completeness_in_conclusion')!r}")

    fal = doc.get("falsifier", {})
    t1, t2 = fal.get("tier_1", {}), fal.get("tier_2", {})
    fal_ok = (t1.get("refutes") == cid
              and t2.get("labelling_required") == "refutes_strengthening_only")
    add("falsifier_tiering", fal_ok,
        f"tier_1.refutes={t1.get('refutes')!r}; "
        f"tier_2.labelling_required={t2.get('labelling_required')!r}")

    anti = doc.get("anti_scope", {})
    named = {e.get("class_id") for e in anti.get("not_this_class", []) if isinstance(e, dict)}
    others = FROZEN - {cid}
    anti_ok = others.issubset(named)
    add("anti_scope_covers_siblings", anti_ok,
        f"anti_scope names {sorted(x for x in named if x)}; siblings required {sorted(others)}")

    comp = doc.get("class_components", {})
    comp_ok = (comp.get("asymptotics") == "AF" and comp.get("censorship") == "SCC"
               and comp.get("matter") == "VAC" and comp.get("genericity") == "GEN"
               and str(comp.get("regularity_token")) == "C0")
    add("class_components", comp_ok, f"class_components={comp}")

    promo = str(doc.get("promotion_rule", "")) + str(con.get("claim_promotion", ""))
    promo_ok = "artifact_refs" in promo and "proof" in promo
    add("promotion_guard", promo_ok, "promotion requires artifact_refs with a checked proof")

    # Composite-regularity contexts: every raw match must sit in a prohibition context.
    # Context = enclosing top-level key + nearest indent-2 key + the line itself, so a
    # bare prohibition phrase such as "- \"any 'C0 or C2' composite regularity\"" inside
    # anti_scope.phrases_that_are_not_this_class is not misread as an assertion.
    lines = schema_path.read_text().splitlines()
    bad_ctx, good_ctx = [], []
    top_key = sub_key = ""
    for i, line in enumerate(lines, 1):
        if line and not line[0].isspace() and ":" in line:
            top_key, sub_key = line.split(":", 1)[0].strip(), ""
        elif line.startswith("  ") and not line.startswith("   ") and ":" in line:
            sub_key = line.strip().split(":", 1)[0].strip()
        if COMPOSITE.search(line):
            context = f"{top_key} {sub_key} {line}"
            (good_ctx if PROHIBITION_MARKERS.search(context) else bad_ctx).append(
                {"line": i, "context": f"{top_key}.{sub_key}", "text": line.strip()[:200]}
            )
    add("composite_regularity_context", not bad_ctx,
        f"composite C0/C2 strings: {len(good_ctx)} in prohibition context, "
        f"{len(bad_ctx)} asserted",
        {"prohibition_context": good_ctx, "asserted": bad_ctx})

    tokens = sorted(set(CLASS_TOKEN.findall(schema_path.read_text())))
    unknown = [t for t in tokens if t not in FROZEN]
    add("no_unknown_class_tokens", not unknown,
        f"class-shaped tokens={tokens}; unknown={unknown}",
        {"tokens": tokens, "unknown": unknown})

    unres = doc.get("unresolved_items", [])
    nv = doc.get("non_vacuity", {})
    unres_ok = isinstance(unres, list) and len(unres) >= 3 and \
        "UNVERIFIED" in str(nv.get("status", "")).upper()
    add("unresolved_honesty", unres_ok,
        f"unresolved_items={len(unres)}; non_vacuity.status={nv.get('status')!r}")

    f0_ok, f0_detail = False, "F0 unreadable"
    try:
        f0_measured = sha256(F0)
        declared = doc.get("f0_binding", {}).get("declared_f0_sha256")
        f0_ok = declared == f0_measured
        f0_detail = f"declared={str(declared)[:16]} measured={f0_measured[:16]}"
    except Exception as exc:  # noqa: BLE001
        f0_detail = f"F0 read failed: {type(exc).__name__}"
    add("f0_binding_fresh", f0_ok, f0_detail)

    def find_key(obj, key, path=""):
        """Recursive key search; returns the dotted path or None."""
        if isinstance(obj, dict):
            if key in obj:
                return f"{path}.{key}".lstrip(".")
            for k, v in obj.items():
                hit = find_key(v, key, f"{path}.{k}".lstrip("."))
                if hit:
                    return hit
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                hit = find_key(v, key, f"{path}[{i}]")
                if hit:
                    return hit
        return None

    slot_paths = {}
    for k in REQUIRED_SLOTS:
        path = find_key(doc, k)
        if path is None and k == "future_null_infinity":
            # This schema names the null-infinity block `i_plus`; the check is that the
            # family's I+ role is declared, not the block's spelling.
            path = find_key(doc, "i_plus")
            if path:
                path += " (block named i_plus)"
        slot_paths[k] = path
    missing = [k for k, v in slot_paths.items() if v is None]
    add("rubric_slots_present", not missing, f"missing rubric slots={missing}",
        {"slot_paths": slot_paths, "missing": missing})

    d0 = str(q.get("domains", {}).get("D0", {}).get("definition", ""))
    branches = [b.strip() for b in re.split(r"\bor\b", d0) if b.strip()]
    add("d0_regularity_branches", len(branches) <= 1,
        f"D0 has {len(branches)} branch(es): {branches}; ambient topologies named: "
        f"Sobolev subspace and Frechet (see genericity.topology_or_measure). "
        "Recorded as WARN: shared with F1/F2a, rubric checks still pass.",
        {"D0": d0, "branches": branches,
         "topology_or_measure": doc.get("genericity", {}).get("topology_or_measure")},
        warn=True)

    # H1: the class_contract_pointer must resolve at the F0 artifact the schema declares.
    ptr = str(doc.get("class_contract_pointer", ""))
    ptr_file, _, ptr_key = ptr.partition("#")
    declared_f0 = str(doc.get("f0_binding", {}).get("declared_f0_artifact", ""))
    resolved_in_declared = resolved_in_pointer_file = False
    missing_at = None
    try:
        can = yaml.safe_load((ROOT / declared_f0).read_text())
        node = can
        for part in ptr_key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                missing_at = part
                node = None
                break
        resolved_in_declared = node is not None
    except Exception as exc:  # noqa: BLE001
        missing_at = f"read error {type(exc).__name__}"
    try:
        auth = yaml.safe_load((ROOT / ptr_file).read_text())
        node = auth
        for part in ptr_key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        resolved_in_pointer_file = node is not None
    except Exception:  # noqa: BLE001
        pass
    h1_ok = ptr_file == declared_f0 and resolved_in_declared
    add("f0_contract_pointer_resolves", h1_ok,
        f"pointer file={ptr_file!r} vs declared F0={declared_f0!r}; "
        f"key={ptr_key!r}; resolves in declared={resolved_in_declared}"
        + (f" (missing at {missing_at!r})" if missing_at else "")
        + f"; resolves in pointer file={resolved_in_pointer_file}",
        {"class_contract_pointer": ptr, "declared_f0_artifact": declared_f0,
         "resolved_in_declared": resolved_in_declared, "missing_at": missing_at,
         "resolved_in_pointer_file": resolved_in_pointer_file})

    # H2: if D0 carries a Sobolev branch, the schema's claim that it is a registered
    # variant must be backed by a registry entry for this parent class.
    registry_ids, registry_sobolev = [], []
    try:
        reg = json.loads((ROOT / "artifacts/formulation/VARIANT_REGISTRY.json").read_text())
        variants = reg.get("variants") or []
        registry_ids = [v.get("variant_id") for v in variants
                        if v.get("parent_class") == cid]
        registry_sobolev = [v.get("variant_id") for v in variants
                            if v.get("parent_class") == cid and "sobolev" in json.dumps(v).lower()]
    except Exception as exc:  # noqa: BLE001
        registry_ids = [f"read error {type(exc).__name__}"]
    schema_var_kinds = []
    civ = doc.get("class_identity_variants", {})
    if isinstance(civ, dict):
        schema_var_kinds = [str(v.get("kind")) for v in civ.values() if isinstance(v, dict)]
    needs_registration = "sobolev" in d0.lower()
    h2_ok = (not needs_registration) or bool(registry_sobolev)
    add("sobolev_variant_registered", h2_ok,
        f"D0 has a Sobolev branch={needs_registration}; registry variant ids for {cid}="
        f"{registry_ids}; Sobolev-tagged={registry_sobolev}; schema variant kinds={schema_var_kinds}",
        {"needs_registration": needs_registration, "registry_ids": registry_ids,
         "registry_sobolev": registry_sobolev, "schema_variant_kinds": schema_var_kinds})

    # W1/W2: hygiene warnings, never hard failures.
    seen, dup = {}, []
    for i, line in enumerate(lines, 1):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):", line)
        if m:
            if m.group(1) in seen:
                dup.append({"key": m.group(1), "first_line": seen[m.group(1)], "line": i})
            else:
                seen[m.group(1)] = i
    add("duplicate_top_level_keys", not dup,
        f"duplicate top-level keys: {[d['key'] for d in dup]} (PyYAML keeps the last; "
        "strict YAML parsers reject the file). Recorded as WARN.",
        {"duplicates": dup}, warn=True)

    current_pins = {measured, sha256(F0)}
    comment_literals = []
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("#"):
            for lit in re.findall(r"\b[0-9a-f]{8,64}\b", line):
                comment_literals.append(
                    {"line": i, "literal": lit, "matches_current_pin": lit in current_pins}
                )
    stale_literals = [c["literal"] for c in comment_literals if not c["matches_current_pin"]]
    add("hash_literal_hygiene", True,
        f"historical hash literals in comments: {stale_literals}; none matches a current pin "
        f"({measured[:12]}, {sha256(F0)[:12]}). They are revision-note history. Recorded as WARN.",
        {"comment_literals": comment_literals, "stale": stale_literals}, warn=True)

    hard_fails = [c for c in checks if c["verdict"] == "fail"]
    report = {
        "schema": str(schema_path.relative_to(ROOT)),
        "schema_sha256": measured,
        "checker": "artifacts/worker-007/f2b_review/independent_checks.py",
        "checks": checks,
        "counts": {"pass": sum(c["verdict"] == "pass" for c in checks),
                   "warn": sum(c["verdict"] == "warn" for c in checks),
                   "fail": len(hard_fails)},
        "verdict": "PASS" if not hard_fails else "FAIL",
    }
    print(json.dumps(report, indent=1))
    return 0 if not hard_fails else 1


if __name__ == "__main__":
    sys.exit(main())

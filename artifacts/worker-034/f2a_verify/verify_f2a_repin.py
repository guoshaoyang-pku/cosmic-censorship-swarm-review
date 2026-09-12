#!/usr/bin/env python3
"""W034-F2A-VERIFY-01R: re-pin machine verification of AF-SCC-C2-VAC-GEN (node F2a)
against the revision published by the astra-life03-close-findings round.

Copy of verify_f2a.py (frozen at sha256 4d62c91d6a6c) with only the snapshot path and
task id changed, so the revision-11 evidence keeps its published hashes.

Original header follows.

W034-F2A-VERIFY-01: independent machine verification of AF-SCC-C2-VAC-GEN (node F2a).

Bounded worker task, worker-034. Third leg of the W034{F2B,F1,F2A}-VERIFY-01 triad.
Reviewed object: a byte-identical snapshot of the canonical F2a schema taken at a
measured sha256. This script never edits canonical files; it only reads them and runs
read-only controls.

  python3 artifacts/worker-034/f2a_verify/verify_f2a.py > f2a_verification.json

Exit 0 when every check executed (the verdict is reported as data, not silently
decided here); exit 2 on harness failure (missing reviewed object).

Checks carried over from the sibling tasks W034-F2B-VERIFY-01 / W034-F1-VERIFY-01
(worker-034's own detector, generalized to F2a) plus F2a-specific structural checks:
SCC quantifier order (forall-exists-forall-not_exists), conclusion_type anti-inflation
(scc_c2_future_inextendibility; never theorem, never WCC), visibility/i_plus declared
out-of-conclusion, C0-sibling leakage scan, duplicate top-level YAML key scan, and the
D0 data-class family / class_contract_pointer checks that were hard failures on F1.
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshot_af_scc_c2_vacuum.rev12.yaml"
CANON = ROOT / "schemas/af_scc_c2_vacuum.yaml"
SIDECAR = ROOT / "schemas/af_scc_c2_vacuum.yaml.sha256"
F0_CANON = ROOT / "research_map/formulation_taxonomy.yaml"
F0_AUTHOR = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
CONSISTENCY = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
VARIANTS = ROOT / "artifacts/formulation/VARIANT_REGISTRY.json"
MAP = ROOT / "research_map/research_map.json"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
CLASSSEP = ROOT / "runtime/bin/classsep_regression.py"
CLASSSEP_MOD = ROOT / "research_map/class_separation.py"

CLASS_ID = "AF-SCC-C2-VAC-GEN"
SIBLING_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2a"
EXPECTED_CONCLUSION_TYPE = "scc_c2_future_inextendibility"
EXPECTED_QUANTIFIER_ORDER = ["forall", "exists", "forall", "not_exists"]

# merged-regularity patterns replicated verbatim from the canonical gate so that a
# gate change shows up as a divergence between this report and the gate result
COMPOSITE = re.compile(r"(C0|C2|C\^?0|C\^?2)\s*(or|and|/)\s*(C0|C2|C\^?0|C\^?2)", re.I)
COMPOSITE_PROSE = re.compile(
    r"\b(C0|C2|continuous|twice[- ]differentiable|Lipschitz|H2_loc)\b\s*,?\s*(or|and|/|alternatively)\s*"
    r"(?:\w+\s+){0,2}\b(C0|C2|continuous|twice[- ]differentiable|Lipschitz|H2_loc)\b", re.I)

REQUIRED_SLOTS = [
    "class_id", "node_id", "quantifiers", "topology", "data_class", "regularity",
    "genericity", "class_contract_pointer", "i_plus", "visibility", "conclusion",
    "falsifier", "anti_scope", "f0_binding", "class_boundary", "extension_predicate",
]
# slots the F1/F2b siblings carry that F2a does not (recorded as data, not used as a
# standalone pass/fail criterion: F2a places variant references in anti_scope/class_boundary)
F1_PARITY_OPTIONAL = ["class_identity_variants"]
# contexts in which a sibling class id is allowed to appear (F2a class_boundary.import_rule)
SIBLING_ALLOWED_KEYS = re.compile(
    r"^(anti_scope|sibling_|class_boundary|import_rule|merge_forbidden|one_way_implication|"
    r"forbidden|must_not|not_|excluded|variants|why|provenance|derived_|known_|"
    r"scope_statement|promotion_rule|reconstruction_note|evidence|note)", re.I)


def digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    return sha256(path.read_bytes()).hexdigest()


def sh(cmd: list[str]) -> dict:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {"command": " ".join(cmd), "exit": p.returncode,
            "stdout": p.stdout[-4000:], "stderr": p.stderr[-2000:]}


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(errors="replace"))


def key_stack(lines: list[str]) -> list[list[str]]:
    """Per line, the stack of YAML mapping keys in force (indentation based, best effort)."""
    stack: list[tuple[int, str]] = []
    out: list[list[str]] = []
    for raw in lines:
        stripped = raw.split("#", 1)[0].rstrip()
        m = re.match(r"^(\s*)([A-Za-z_][\w\-]*):", stripped)
        if m:
            indent = len(m.group(1))
            while stack and stack[-1][0] >= indent:
                stack.pop()
            stack.append((indent, m.group(2)))
        out.append([k for _, k in stack])
    return out


EXEMPT_KEYS = re.compile(
    r"^(forbidden|must_not|anti_scope|not_|excluded|variants|phrases_that_are_not|why_|reason$|"
    r"sibling_|derived_|visible_singularity_is_wcc$|no_|never_|c0_uniqueness_caveat$|"
    r"composite_regularity_ban$|terminology_disambiguation$|schema_falsifiers$|vacuity_falsifier$|"
    r"class_change_warning$|subsumption_note$|observability_note$|equivalence_claim$|"
    r"non_goals$|forbidden_strengthenings$|forbidden_weakenings$|forbidden_transfers$|"
    r"must_not_conflate$|class_selector_meaning$|one_way_implication$|import_rule$)", re.I)


def composite_scan(lines: list[str]) -> list[dict]:
    stacks = key_stack(lines)
    hits = []
    for i, raw in enumerate(lines, start=1):
        keys = [] if raw.lstrip().startswith("#") else stacks[i - 1]
        for pat in (COMPOSITE, COMPOSITE_PROSE):
            m = pat.search(raw)
            if m:
                exempt = any(EXEMPT_KEYS.match(k) for k in keys)
                hits.append({"line": i, "match": m.group(0), "keys": keys[-3:],
                             "exempt": exempt, "text": raw.strip()[:220]})
    return hits


def resolve_pointer(doc, pointer: str):
    node = doc
    for part in pointer.split("."):
        if not isinstance(node, dict) or part not in node:
            return {"resolved": False, "missing_at": part}
        node = node[part]
    return {"resolved": True, "value_type": type(node).__name__}


def truncate_fraction(text: str) -> bool:
    """True when a 64-char hex string is a truncated hash padded with zeros."""
    return bool(re.fullmatch(r"[0-9a-f]{64}", text)) and set(text[16:]) == {"0"}


def load_classsep():
    spec = importlib.util.spec_from_file_location("w034_class_separation", CLASSSEP_MOD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    for required in (SNAP, CANON, MAP, GATE, CLASSSEP, CLASSSEP_MOD, VARIANTS,
                     F0_CANON, F0_AUTHOR, CONSISTENCY):
        if not required.is_file():
            print(f"harness failure: missing {required}", file=sys.stderr)
            return 2

    rep: dict = {"task_id": "W034-F2A-VERIFY-01R", "node_id": NODE_ID, "class_id": CLASS_ID}
    checks: dict = {}

    # ---- hashes and bindings -------------------------------------------------
    h_snap = digest(SNAP)
    h_canon_start = digest(CANON)
    sidecar_hash = SIDECAR.read_text().strip().split()[0] if SIDECAR.is_file() else None
    checks["H1_snapshot_sha256"] = h_snap
    checks["H1_canonical_sha256_at_start"] = h_canon_start
    checks["H1_snapshot_matches_canonical_at_start"] = h_snap == h_canon_start
    checks["H2_sidecar_present"] = SIDECAR.is_file()
    checks["H2_sidecar_sha256"] = sidecar_hash
    checks["H2_sidecar_matches_canonical"] = sidecar_hash == h_canon_start

    mp = json.loads(MAP.read_text())
    node = None
    for g in mp.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("id") == NODE_ID:
                node = n
    checks["H3_map_measured_sha256"] = (node or {}).get("artifact_sha256_measured")
    checks["H3_map_declared_sha256"] = (node or {}).get("artifact_sha256")
    checks["H3_map_measured_matches_snapshot"] = (node or {}).get("artifact_sha256_measured") == h_snap
    checks["H3_map_declared_is_zero_padded_truncation"] = truncate_fraction((node or {}).get("artifact_sha256") or "")
    checks["H3_map_node_class_id"] = (node or {}).get("class_id")
    checks["H3_map_node_artifact"] = (node or {}).get("artifact")

    doc = load_yaml(SNAP)
    lines = SNAP.read_text(errors="replace").splitlines()
    text = "\n".join(lines)

    # ---- identity / class binding -------------------------------------------
    checks["I1_class_id"] = doc.get("class_id")
    checks["I1_node_id"] = doc.get("node_id")
    checks["I1_revision"] = doc.get("revision")
    checks["I1_class_components"] = doc.get("class_components")
    checks["I1_conclusion_type"] = (doc.get("conclusion") or {}).get("conclusion_type")
    checks["I1_epistemic_status"] = (doc.get("conclusion") or {}).get("epistemic_status")
    checks["I2_class_id_matches_map"] = doc.get("class_id") == CLASS_ID == (node or {}).get("class_id")
    checks["I2_node_id_matches_map"] = doc.get("node_id") == NODE_ID
    checks["I2_conclusion_type_is_scc_c2"] = (
        (doc.get("conclusion") or {}).get("conclusion_type") == EXPECTED_CONCLUSION_TYPE)
    checks["I3_conclusion_type_is_not_wcc"] = (
        (doc.get("conclusion") or {}).get("conclusion_type") != "weak_cosmic_censorship")
    checks["I3_conclusion_type_is_not_theorem"] = (
        (doc.get("conclusion") or {}).get("conclusion_type") != "theorem")
    checks["I3_claim_promotion_requires_artifact_refs"] = (
        "artifact_refs" in str((doc.get("conclusion") or {}).get("claim_promotion", "")))
    checks["I3_sibling_disjoint_from"] = doc.get("sibling_disjoint_from")
    checks["I3_sibling_disjoint_declared"] = doc.get("sibling_disjoint_from") == SIBLING_ID
    cb = doc.get("class_boundary") or {}
    checks["I3_class_boundary_one_class_only"] = cb.get("one_class_only")
    checks["I3_class_boundary_one_class_holds"] = cb.get("one_class_only") == CLASS_ID
    checks["I3_class_boundary_import_rule"] = cb.get("import_rule")
    checks["I3_class_boundary_merge_forbidden"] = cb.get("merge_forbidden")

    # ---- required slots ------------------------------------------------------
    missing = [k for k in REQUIRED_SLOTS if k not in doc or doc.get(k) in (None, "", [], {})]
    checks["S1_required_slots_present"] = not missing
    checks["S1_missing_or_empty_slots"] = missing
    checks["S1_required_slots_checked"] = REQUIRED_SLOTS
    checks["S1_f1_parity_optional_absent"] = [k for k in F1_PARITY_OPTIONAL if k not in doc]
    checks["S1_variant_references_elsewhere"] = {
        "anti_scope_kinds": sorted({str(x.get("kind")) for x in (doc.get("anti_scope") or {}).get("not_this_class", []) if isinstance(x, dict) and x.get("kind")}),
        "purpose_note": "F2a has no class_identity_variants slot; variant references live in anti_scope and class_boundary",
    }

    # ---- quantifier structure (SCC-C2: forall-exists-forall-not_exists) -------
    q = doc.get("quantifiers") or {}
    order = [x.get("kind") for x in (q.get("ordered") or [])]
    checks["S2_quantifier_order"] = order
    checks["S2_quantifier_order_matches_scc_c2_reading"] = order == EXPECTED_QUANTIFIER_ORDER
    checks["S2_quantifier_class"] = q.get("quantifier_class")
    domains = q.get("domains") or {}
    checks["S2_domains_defined"] = sorted(domains.keys())
    ordered_ids = [x.get("domain_id") for x in (q.get("ordered") or [])]
    checks["S2_ordered_domain_ids"] = ordered_ids
    checks["S2_all_ordered_domains_resolve"] = all(d in domains for d in ordered_ids)
    checks["S2_order_matters"] = q.get("order_matters")
    checks["S2_negation_present"] = bool(q.get("negation"))
    checks["S2_negation_normal_form"] = q.get("negation_normal_form")
    sf = (doc.get("conclusion") or {}).get("statement_formal", "")
    binders = [x.get("binder") for x in (q.get("ordered") or [])]
    checks["S2_statement_formal_binder_presence"] = {str(b): (str(b) in sf) for b in binders}
    checks["S2_statement_formal"] = sf

    # ---- extension / visibility / i_plus / falsifier slots -------------------
    ext = doc.get("extension_predicate") or {}
    checks["S3_extension_predicate_keys"] = sorted(ext.keys())
    checks["S3_extension_definition_present"] = bool(ext.get("definition"))
    checks["S3_extension_regularity_exact"] = (doc.get("regularity") or {}).get("extension_regularity_exact")
    checks["S3_extension_regularity_C2_token"] = "C2" in str(
        (doc.get("regularity") or {}).get("extension_regularity_exact", ""))
    vis = doc.get("visibility") or {}
    checks["S4_visibility_role"] = vis.get("role")
    checks["S4_visibility_not_in_conclusion"] = vis.get("role") == "not_in_conclusion"
    checks["S4_visibility_definition_present"] = bool(vis.get("reason") or vis.get("definition"))
    checks["S4_visible_singularity_is_wcc"] = vis.get("visible_singularity_is_wcc")
    checks["S4_visibility_forbidden_falsifier_present"] = bool(vis.get("forbidden_falsifier"))
    ip = doc.get("i_plus") or {}
    checks["S5_i_plus_role"] = ip.get("role")
    checks["S5_i_plus_not_in_conclusion"] = ip.get("in_conclusion") is False
    checks["S5_i_plus_completeness_not_in_conclusion"] = ip.get("completeness_in_conclusion") is False
    checks["S5_i_plus_definition_present"] = bool(ip.get("definition"))
    checks["S5_i_plus_forbidden_present"] = bool(ip.get("forbidden"))
    f = doc.get("falsifier") or {}
    checks["S6_falsifier_tier_1_refutes"] = (f.get("tier_1") or {}).get("refutes")
    checks["S6_falsifier_tier_2_present"] = bool(f.get("tier_2"))
    checks["S6_falsifier_schema_falsifiers_present"] = bool(f.get("schema_falsifiers"))
    nv = doc.get("non_vacuity") or {}
    checks["S6_non_vacuity_condition_present"] = bool(nv.get("condition"))
    topo = doc.get("topology") or {}
    checks["S7_topology_keys"] = sorted(topo.keys())
    checks["S7_topology_named"] = bool(topo.get("manifold") or topo.get("definition") or topo.get("ambient"))
    dc = doc.get("data_class") or {}
    checks["S8_data_class_keys"] = sorted(dc.keys())
    checks["S8_matter_vacuum"] = dc.get("matter")
    checks["S8_equations"] = dc.get("equations")

    # ---- conclusion-direction / anti-inflation -------------------------------
    forbidden = (doc.get("conclusion") or {}).get("forbidden_strengthenings") or []
    forbidden_text = " | ".join(str(x) for x in forbidden)
    weakenings = (doc.get("conclusion") or {}).get("forbidden_weakenings") or []
    weakenings_text = " | ".join(str(x) for x in weakenings)
    checks["C1_forbidden_strengthenings_count"] = len(forbidden)
    checks["C1_forbids_c0_c1_h2loc"] = all(t in forbidden_text for t in ("C0", "H2_loc"))
    checks["C1_forbids_two_sided"] = "two-sided" in forbidden_text.lower()
    checks["C1_forbids_all_data_reading"] = "ALL AF vacuum data" in forbidden_text or "all af vacuum data" in forbidden_text.lower()
    checks["C1_forbids_wcc_content"] = any(t.lower() in forbidden_text.lower() for t in ("I+", "WCC", "predictability"))
    checks["C1_forbidden_weakenings_count"] = len(weakenings)
    checks["C1_forbids_dropping_genericity"] = "dropping the generic quantifier" in weakenings_text.lower()
    checks["C1_forbids_weaker_gh_reading"] = "globally hyperbolic extensions" in weakenings_text.lower()
    checks["C1_statement_has_no_visibility_word"] = not re.search(r"\bvisib", sf, re.I)
    checks["C1_statement_has_no_wcc_token"] = "weak_cosmic_censorship" not in sf

    # ---- class separation (canonical module + local composite scan) ----------
    cs_mod = load_classsep()
    findings = cs_mod.findings_for_text(text, f"{SNAP.name}")
    checks["L1_class_separation_findings"] = findings
    checks["L1_class_separation_clean"] = len(findings) == 0
    hits = composite_scan(lines)
    checks["L2_composite_hits_total"] = len(hits)
    checks["L2_composite_hits_outside_exempt_blocks"] = [h for h in hits if not h["exempt"]]
    checks["L2_composite_hits_inside_exempt_blocks"] = [h for h in hits if h["exempt"]]
    # sibling-token context audit: where does AF-SCC-C0-VAC-GEN appear?
    stacks = key_stack(lines)
    sib_ctx = []
    for i, raw in enumerate(lines, start=1):
        if SIBLING_ID in raw:
            sib_ctx.append({"line": i, "keys": stacks[i - 1][-3:], "text": raw.strip()[:180]})
    checks["L3_sibling_token_occurrences"] = sib_ctx
    checks["L3_sibling_token_outside_allowed_contexts"] = [
        x for x in sib_ctx if not any(SIBLING_ALLOWED_KEYS.match(k) for k in x["keys"])]

    # ---- external controls (canonical gate + classsep regression) ------------
    gate = sh([sys.executable, str(GATE.relative_to(ROOT)), "--json", str(SNAP.relative_to(ROOT))])
    try:
        gate_json = json.loads(gate["stdout"])
    except Exception:
        gate_json = None
    checks["X1_canonical_gate"] = {"exit": gate["exit"], "verdict": (gate_json or {}).get("verdict"),
                                   "failed_rules": (gate_json or {}).get("failed_rules"),
                                   "raw_tail": gate["stdout"][-600:]}
    cs = sh([sys.executable, str(CLASSSEP.relative_to(ROOT))])
    cs_tail = cs["stdout"].strip().splitlines()[-3:]
    checks["X2_classsep_regression"] = {"exit": cs["exit"], "tail": cs_tail}
    checks["X2_classsep_regression_parse"] = {
        "leaks": next((l.strip() for l in cs_tail if "leaks detected" in l), None),
        "verdict": next((l.split(":")[-1].strip() for l in cs_tail if l.startswith("VERDICT")), None),
    }

    # ---- data-class family detection (the class-identity question) -----------
    d0 = ((domains.get("D0")) or {}).get("definition", "")
    data_reg = (doc.get("regularity") or {}).get("data_regularity", "")
    reg_class = (((doc.get("data_class") or {}).get("regularity_class")) or {})
    gen = doc.get("genericity") or {}
    gen_text = json.dumps(gen, ensure_ascii=False)
    checks["D0_definition"] = d0
    checks["D0_contains_disjunction"] = bool(re.search(r"\bor\b", d0, re.I))
    checks["D0_is_tagged_disjoint_union"] = bool(re.search(r"tagged\s+disjoint\s+union", d0, re.I))
    checks["D0_single_binder_present"] = bool(re.search(r"\br\b", str((q.get("ordered") or [{}])[0].get("binder", ""))))
    checks["D0_alternatives_detected"] = [s for s in ("Sobolev", "smooth-with-decay") if s.lower() in d0.lower()]
    checks["D0_data_regularity"] = data_reg
    checks["D0_data_regularity_mirrors_disjunction"] = bool(re.search(r"\bor\b", data_reg, re.I))
    checks["D0_regularity_class_keys"] = sorted(reg_class.keys())
    checks["D0_two_regularity_settings_declared"] = (
        bool(reg_class.get("default")) and bool(reg_class.get("sobolev_variant")))
    checks["D0_ambient_topologies_named"] = {
        "weighted_sobolev_product": ("H^s_delta" in gen_text or "H^{s" in gen_text),
        "frechet_smooth": ("Frechet" in gen_text or "Fréchet" in gen_text),
    }
    checks["D0_conflation_rule"] = (doc.get("regularity") or {}).get("must_not_conflate")

    reg = json.loads(VARIANTS.read_text())
    reg_txt = json.dumps(reg, ensure_ascii=False)
    checks["D1_variant_registry_mentions_sobolev"] = "sobolev" in reg_txt.lower()
    checks["D1_variant_registry_ids"] = [v.get("variant_id") for v in (reg.get("variants") or [])]
    checks["D1_variant_registry_parents"] = sorted({v.get("parent_class") for v in (reg.get("variants") or [])})
    canon_f0 = load_yaml(F0_CANON)
    checks["D1_canonical_f0_variant_ids"] = [v.get("variant_id") for v in (canon_f0.get("variants") or [])]
    checks["D1_canonical_f0_data_class_variant_for_this_class"] = [
        v for v in (canon_f0.get("variants") or []) if v.get("parent_class") == CLASS_ID]

    # ---- duplicate top-level YAML keys (machine-readability defect) ----------
    top_keys = [m.group(1) for l in lines if (m := re.match(r"^([A-Za-z_][\w\-]*):", l))]
    dupes = {k: v for k, v in Counter(top_keys).items() if v > 1}
    checks["D2_top_level_key_count"] = len(top_keys)
    checks["D2_duplicate_top_level_keys"] = dupes
    checks["D2_has_duplicate_top_level_keys"] = bool(dupes)
    checks["D2_duplicate_key_lines"] = {
        k: [i for i, l in enumerate(lines, start=1) if re.match(rf"^{re.escape(k)}:", l)]
        for k in dupes
    }

    # ---- F0 binding / class_contract_pointer ---------------------------------
    fb = doc.get("f0_binding") or {}
    declared_art = fb.get("declared_f0_artifact")
    declared_hash = fb.get("declared_f0_sha256")
    pointer = doc.get("class_contract_pointer", "")
    ptr_path, _, ptr_key = pointer.partition("#")
    checks["B1_declared_f0_artifact"] = declared_art
    checks["B1_declared_f0_sha256"] = declared_hash
    checks["B1_declared_f0_measured"] = digest(ROOT / declared_art) if declared_art else None
    checks["B1_declared_hash_matches_measured"] = digest(ROOT / declared_art) == declared_hash
    checks["B1_pointer"] = pointer
    checks["B1_pointer_path"] = ptr_path
    checks["B1_pointer_key"] = ptr_key
    checks["B1_pointer_path_equals_declared_artifact"] = ptr_path == declared_art
    checks["B1_pointer_resolves_in_declared_artifact"] = resolve_pointer(canon_f0, ptr_key)
    checks["B1_pointer_resolves_in_pointer_file"] = (
        resolve_pointer(load_yaml(ROOT / ptr_path), ptr_key) if (ROOT / ptr_path).is_file() else "file_missing")
    checks["B1_pointer_file_sha256"] = digest(ROOT / ptr_path) if ptr_path else None
    checks["B1_declared_f0_has_class_contracts"] = "class_contracts" in canon_f0
    checks["B1_declared_f0_exposes_classes_key"] = "classes" in canon_f0
    supplement = fb.get("class_contract_supplement")
    checks["B1_supplement"] = supplement
    checks["B1_supplement_exists"] = bool(supplement) and (ROOT / supplement).is_file()
    checks["B1_supplement_sha256"] = digest(ROOT / supplement) if supplement else None
    checks["B1_consistency_evidence_exists"] = CONSISTENCY.is_file()
    checks["B1_consistency_evidence_sha256"] = digest(CONSISTENCY)
    checks["B1_consistency_evidence_declared_sha256"] = fb.get("consistency_evidence_sha256")
    checks["B1_consistency_evidence_declared_matches_measured"] = (
        fb.get("consistency_evidence_sha256") == digest(CONSISTENCY))
    checks["B1_consistency_evidence_mtime"] = (
        datetime.datetime.fromtimestamp(CONSISTENCY.stat().st_mtime).astimezone().isoformat(timespec="seconds")
        if CONSISTENCY.is_file() else None)
    checks["B1_consistency_evidence_newer_than_schema"] = (
        CONSISTENCY.is_file() and CONSISTENCY.stat().st_mtime > SNAP.stat().st_mtime + 1)
    checks["B1_f0_binding_checked_at"] = fb.get("checked_at")

    # ---- timestamp hygiene ---------------------------------------------------
    now = datetime.datetime.now().astimezone()
    mt = datetime.datetime.fromtimestamp(SNAP.stat().st_mtime).astimezone()
    declared_times = re.findall(r'^\s*(?:revised_at|checked_at|written_at|created_at|authored_at):\s*"?([0-9T:\-+]{19,25})"?', text, re.M)
    future_vs_now = []
    for t in declared_times:
        try:
            ts = datetime.datetime.fromisoformat(t)
        except ValueError:
            continue
        if ts.timestamp() > now.timestamp() + 60:
            future_vs_now.append(t)
    ahead_of_mtime = []
    for t in declared_times:
        try:
            ts = datetime.datetime.fromisoformat(t)
        except ValueError:
            continue
        if ts.timestamp() > mt.timestamp() + 60:
            ahead_of_mtime.append(t)
    checks["T1_file_mtime"] = mt.isoformat(timespec="seconds")
    checks["T1_now"] = now.isoformat(timespec="seconds")
    checks["T1_declared_times"] = declared_times
    checks["T1_future_dated_declared_times"] = future_vs_now
    checks["T1_declared_times_ahead_of_mtime"] = ahead_of_mtime
    checks["T1_duplicate_revised_at_count"] = dupes.get("revised_at", 0)

    # ---- final hash re-measure (movement during verification) ----------------
    h_canon_end = digest(CANON)
    checks["Z1_canonical_sha256_at_end"] = h_canon_end
    checks["Z1_canonical_moved_during_review"] = h_canon_end != h_canon_start
    checks["Z1_snapshot_sha256_at_end"] = digest(SNAP)
    checks["Z1_binding_ok"] = (h_snap == h_canon_start == h_canon_end)

    # ---- derived findings (data only; the review file carries the verdict) ---
    derived = {}
    bare_disjunction = bool(checks["D0_contains_disjunction"]
                            and not checks["D0_is_tagged_disjoint_union"]
                            and checks["D0_data_regularity_mirrors_disjunction"]
                            and checks["D0_two_regularity_settings_declared"]
                            and not checks["D1_variant_registry_mentions_sobolev"]
                            and not checks["D1_canonical_f0_data_class_variant_for_this_class"])
    tagged_union_unadjudicated = bool(checks["D0_is_tagged_disjoint_union"]
                                      and checks["D0_single_binder_present"])
    derived["HF-034-F2A-1_D0_family_domain"] = {
        "triggered": bare_disjunction,
        "tagged_union_requires_adjudication": tagged_union_unadjudicated,
        "trigger_rule": "bare disjunction + two settings + mirrored data_regularity + no registered variant; a tagged disjoint union with a single binder r is NOT auto-failed by this checker and is flagged for lead-audit adjudication instead",
        "evidence": {"D0_definition": d0, "data_regularity": data_reg,
                     "D0_is_tagged_disjoint_union": checks["D0_is_tagged_disjoint_union"],
                     "first_binder": str((q.get("ordered") or [{}])[0].get("binder", "")),
                     "variant_registry_ids": checks["D1_variant_registry_ids"],
                     "f0_variants_for_class": checks["D1_canonical_f0_data_class_variant_for_this_class"]},
    }
    derived["HF-034-F2A-2_pointer_unresolvable_at_declared_F0"] = {
        "triggered": bool(not checks["B1_pointer_path_equals_declared_artifact"]
                          and not checks["B1_pointer_resolves_in_declared_artifact"].get("resolved", False)),
        "evidence": {"pointer": pointer, "declared_f0_artifact": declared_art,
                     "declared_f0_sha256": declared_hash,
                     "pointer_path": ptr_path,
                     "resolves_in_declared_artifact": checks["B1_pointer_resolves_in_declared_artifact"],
                     "resolves_in_pointer_file": checks["B1_pointer_resolves_in_pointer_file"]},
    }
    derived["HF-034-F2A-3_consistency_evidence_pin_stale"] = {
        "triggered": bool(checks["B1_consistency_evidence_exists"]
                          and not checks["B1_consistency_evidence_declared_matches_measured"]),
        "evidence": {"declared": checks["B1_consistency_evidence_declared_sha256"],
                     "measured": checks["B1_consistency_evidence_sha256"],
                     "evidence_mtime": checks["B1_consistency_evidence_mtime"],
                     "schema_mtime": checks["T1_file_mtime"],
                     "evidence_newer_than_schema": checks["B1_consistency_evidence_newer_than_schema"]},
        "scope_note": "binding/publication-ordering defect, family-wide (F1/F2a/F2b declare the same 675a99d0 pin); not a class-semantics defect",
    }
    derived["W-034-F2A-1_future_dated"] = {"triggered": bool(future_vs_now), "times": future_vs_now}
    derived["W-034-F2A-1b_declared_ahead_of_mtime"] = {"triggered": bool(ahead_of_mtime), "times": ahead_of_mtime}
    derived["W-034-F2A-2_no_sidecar"] = {"triggered": not checks["H2_sidecar_present"]}
    derived["W-034-F2A-3_duplicate_keys"] = {"triggered": bool(dupes), "dupes": dupes}
    derived["W-034-F2A-4_sibling_token_contexts"] = {
        "triggered": bool(checks["L3_sibling_token_outside_allowed_contexts"]),
        "outside": checks["L3_sibling_token_outside_allowed_contexts"],
    }
    checks["DERIVED_findings"] = derived

    rep["snapshot"] = str(SNAP.relative_to(ROOT))
    rep["reviewed_sha256"] = h_snap
    rep["verdict_is_data_not_exit_status"] = True
    rep["checks"] = checks
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

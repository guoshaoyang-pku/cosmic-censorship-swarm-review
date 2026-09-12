#!/usr/bin/env python3
"""W034-F1-VERIFY-01: independent machine verification of AF-WCC-VAC-GEN (node F1).

Bounded worker task, worker-034. Reviewed object: a byte-identical snapshot of the
canonical F1 schema taken at a measured sha256. This script never edits canonical
files; it only reads them and runs read-only controls.

  python3 artifacts/worker-034/f1_verify/verify_f1.py > f1_verification.json

Exit 0 when every check executed (the verdict is reported as data, not silently
decided here); exit 2 on harness failure (missing reviewed object).

Checks carried over from the sibling task W034-F2B-VERIFY-01 (worker-034's own
detector, generalized to F1) plus F1-specific structural checks: quantifier order,
conclusion-direction / anti-inflation, soft-flag token, required slots.
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import re
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshot_af_wcc_vacuum.yaml"
CANON = ROOT / "schemas/af_wcc_vacuum.yaml"
SIDECAR = ROOT / "schemas/af_wcc_vacuum.yaml.sha256"
F0_CANON = ROOT / "research_map/formulation_taxonomy.yaml"
F0_AUTHOR = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
VARIANTS = ROOT / "artifacts/formulation/VARIANT_REGISTRY.json"
MAP = ROOT / "research_map/research_map.json"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
CLASSSEP = ROOT / "runtime/bin/classsep_regression.py"
CLASSSEP_MOD = ROOT / "research_map/class_separation.py"

CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"

# merged-regularity patterns replicated verbatim from the canonical gate so that a
# gate change shows up as a divergence between this report and the gate result
COMPOSITE = re.compile(r"(C0|C2|C\^?0|C\^?2)\s*(or|and|/)\s*(C0|C2|C\^?0|C\^?2)", re.I)
COMPOSITE_PROSE = re.compile(
    r"\b(C0|C2|continuous|twice[- ]differentiable|Lipschitz|H2_loc)\b\s*,?\s*(or|and|/|alternatively)\s*"
    r"(?:\w+\s+){0,2}\b(C0|C2|continuous|twice[- ]differentiable|Lipschitz|H2_loc)\b", re.I)

REQUIRED_SLOTS = [
    "class_id", "node_id", "quantifiers", "topology", "data_class", "regularity",
    "genericity", "class_contract_pointer", "i_plus", "visibility", "conclusion",
    "falsifier", "anti_scope", "class_identity_variants", "f0_binding",
]
EXPECTED_QUANTIFIER_ORDER = ["forall", "exists", "forall", "exists", "forall", "not_exists"]
SCC_STRENGTHENING_TOKENS = ["C2", "C0", "inextendib"]


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


EXEMPT_KEYS = re.compile(
    r"^(forbidden|must_not|anti_scope|not_|excluded|variants|phrases_that_are_not|why_|reason$|"
    r"sibling_|derived_|visible_singularity_is_wcc$|no_|never_|c0_uniqueness_caveat$|"
    r"composite_regularity_ban$|terminology_disambiguation$|schema_falsifiers$|vacuity_falsifier$|"
    r"class_change_warning$|subsumption_note$|observability_note$|equivalence_claim$|"
    r"non_goals$|forbidden_strengthenings$|forbidden_weakenings$|forbidden_transfers$|"
    r"must_not_conflate$)", re.I)


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
    for required in (SNAP, CANON, MAP, GATE, CLASSSEP, CLASSSEP_MOD, VARIANTS):
        if not required.is_file():
            print(f"harness failure: missing {required}", file=sys.stderr)
            return 2

    rep: dict = {"task_id": "W034-F1-VERIFY-01", "node_id": NODE_ID, "class_id": CLASS_ID}
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
    checks["I2_conclusion_type_is_wcc"] = (doc.get("conclusion") or {}).get("conclusion_type") == "weak_cosmic_censorship"

    # ---- required slots ------------------------------------------------------
    missing = [k for k in REQUIRED_SLOTS if k not in doc or doc.get(k) in (None, "", [], {})]
    checks["S1_required_slots_present"] = not missing
    checks["S1_missing_or_empty_slots"] = missing

    # ---- quantifier structure ------------------------------------------------
    q = doc.get("quantifiers") or {}
    order = [x.get("kind") for x in (q.get("ordered") or [])]
    checks["S2_quantifier_order"] = order
    checks["S2_quantifier_order_matches_frozen_reading"] = order == EXPECTED_QUANTIFIER_ORDER
    checks["S2_domains_defined"] = sorted((q.get("domains") or {}).keys())
    sf = (doc.get("conclusion") or {}).get("statement_formal", "")
    binders = [x.get("binder") for x in (q.get("ordered") or [])]
    # statement_formal is a compressed rendering; record literal binder presence as data,
    # it is not a pass/fail criterion of this checker.
    checks["S2_statement_formal_binder_presence"] = {str(b): (str(b) in sf) for b in binders}
    checks["S2_statement_formal"] = sf

    # ---- extension / visibility / i_plus / falsifier slots -------------------
    ext = doc.get("extension_predicate") or {}
    checks["S3_extension_predicate_keys"] = sorted(ext.keys())
    checks["S3_extension_axes"] = {k: ext.get(k) for k in ext if "frozen" in k}
    checks["S3_extension_definition_present"] = bool(ext.get("definition"))
    vis = doc.get("visibility") or {}
    checks["S4_visibility_predicate_name"] = vis.get("predicate_name")
    checks["S4_visibility_definition_present"] = bool(vis.get("definition"))
    checks["S4_visibility_negation_present"] = bool(vis.get("negation_conclusion"))
    ip = doc.get("i_plus") or {}
    checks["S5_i_plus_definition_present"] = bool(ip.get("definition"))
    checks["S5_i_plus_completeness_present"] = bool(ip.get("completeness_definition"))
    f = doc.get("falsifier") or {}
    checks["S6_falsifier_tier_1_refutes"] = (f.get("tier_1") or {}).get("refutes")
    checks["S6_falsifier_tier_2_present"] = bool(f.get("tier_2"))
    nv = doc.get("non_vacuity") or {}
    checks["S6_non_vacuity_condition_present"] = bool(nv.get("condition"))

    # ---- conclusion-direction / anti-inflation -------------------------------
    forbidden = (doc.get("conclusion") or {}).get("forbidden_strengthenings") or []
    forbidden_text = " | ".join(forbidden)
    checks["C1_forbidden_strengthenings_count"] = len(forbidden)
    checks["C1_scc_content_explicitly_forbidden"] = all(t in forbidden_text for t in SCC_STRENGTHENING_TOKENS)
    checks["C1_forbids_all_data_reading"] = any("ALL data" in x or "all data" in x for x in forbidden)

    # ---- class separation (canonical module + local composite scan) ----------
    cs_mod = load_classsep()
    findings = cs_mod.findings_for_text(text, f"{SNAP.name}")
    checks["L1_class_separation_findings"] = findings
    checks["L1_class_separation_clean"] = len(findings) == 0
    checks["L1_variant_set_token_present"] = "AF-WCC-VAC-GEN-SET" in text
    hits = composite_scan(lines)
    checks["L2_composite_hits_total"] = len(hits)
    checks["L2_composite_hits_outside_exempt_blocks"] = [h for h in hits if not h["exempt"]]
    checks["L2_composite_hits_inside_exempt_blocks"] = [h for h in hits if h["exempt"]]

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
    checks["X2_classsep_regression"] = {"exit": cs["exit"],
                                        "tail": cs["stdout"].strip().splitlines()[-3:]}

    # ---- data-class family detection (the class-identity question) -----------
    d0 = ((q.get("domains") or {}).get("D0") or {}).get("definition", "")
    data_reg = (doc.get("regularity") or {}).get("data_regularity", "")
    reg_class = (((doc.get("data_class") or {}).get("regularity_class")) or {})
    gen = doc.get("genericity") or {}
    gen_text = json.dumps(gen, ensure_ascii=False)
    checks["D0_definition"] = d0
    checks["D0_contains_disjunction"] = bool(re.search(r"\bor\b", d0, re.I))
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
    cons = fb.get("consistency_evidence")
    checks["B1_consistency_evidence_exists"] = bool(cons) and (ROOT / cons).is_file()
    checks["B1_f0_binding_checked_at"] = fb.get("checked_at")

    # ---- timestamp hygiene ---------------------------------------------------
    now = datetime.datetime.now().astimezone()
    mt = datetime.datetime.fromtimestamp(SNAP.stat().st_mtime).astimezone()
    declared_times = re.findall(r'^\s*(?:revised_at|checked_at|written_at|created_at):\s*"?([0-9T:\-+]{19,25})"?', text, re.M)
    future_vs_now = []
    for t in declared_times:
        try:
            ts = datetime.datetime.fromisoformat(t)
        except ValueError:
            continue
        if ts.timestamp() > now.timestamp() + 60:
            future_vs_now.append(t)
    checks["T1_file_mtime"] = mt.isoformat(timespec="seconds")
    checks["T1_now"] = now.isoformat(timespec="seconds")
    checks["T1_declared_times"] = declared_times
    checks["T1_future_dated_declared_times"] = future_vs_now

    # ---- final hash re-measure (movement during verification) ----------------
    h_canon_end = digest(CANON)
    checks["Z1_canonical_sha256_at_end"] = h_canon_end
    checks["Z1_canonical_moved_during_review"] = h_canon_end != h_canon_start
    checks["Z1_snapshot_sha256_at_end"] = digest(SNAP)
    checks["Z1_binding_ok"] = (h_snap == h_canon_start == h_canon_end)

    rep["snapshot"] = str(SNAP.relative_to(ROOT))
    rep["reviewed_sha256"] = h_snap
    rep["verdict_is_data_not_exit_status"] = True
    rep["checks"] = checks
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

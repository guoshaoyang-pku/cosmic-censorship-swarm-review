#!/usr/bin/env python3
"""W034-F2B-VERIFY-01: independent machine verification of AF-SCC-C0-VAC-GEN (node F2b).

Bounded worker task. Reviewed object: a byte-identical snapshot of the canonical
class schema taken at a measured sha256. The script never edits the canonical file.

Emits a machine report (JSON) on stdout:

  python3 artifacts/worker-034/f2b_verify/verify_f2b.py > report.json

Exit 0 if every check executed (verdict is reported as data, not exit status);
exit 2 on harness failure. The review verdict is decided from the report by the
worker, not silently by this script.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SNAP = Path(__file__).resolve().parent / "snapshot_af_scc_c0_vacuum.yaml"
CANON = ROOT / "schemas/af_scc_c0_vacuum.yaml"
SIDECAR = ROOT / "schemas/af_scc_c0_vacuum.yaml.sha256"
F0_CANON = ROOT / "research_map/formulation_taxonomy.yaml"
F0_AUTHOR = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
VARIANTS = ROOT / "artifacts/formulation/VARIANT_REGISTRY.json"
MAP = ROOT / "research_map/research_map.json"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
CLASSSEP = ROOT / "runtime/bin/classsep_regression.py"

CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE_ID = "F2b"

# canonical gate's merged-regularity patterns (replicated verbatim, so a gate
# change shows up as a divergence between this report and the gate result)
COMPOSITE = re.compile(r"(C0|C2|C\^?0|C\^?2)\s*(or|and|/)\s*(C0|C2|C\^?0|C\^?2)", re.I)
COMPOSITE_PROSE = re.compile(
    r"\b(C0|C2|continuous|twice[- ]differentiable|Lipschitz|H2_loc)\b\s*,?\s*(or|and|/|alternatively)\s*"
    r"(?:\w+\s+){0,2}\b(C0|C2|continuous|twice[- ]differentiable|Lipschitz|H2_loc)\b", re.I)
EXEMPT_KEYS = re.compile(
    r"^(forbidden|must_not|anti_scope|not_|excluded|variants|phrases_that_are_not|why_|reason$|"
    r"sibling_|derived_|visible_singularity_is_wcc$|no_|never_|c0_uniqueness_caveat$|"
    r"composite_regularity_ban$|terminology_disambiguation$|schema_falsifiers$|vacuity_falsifier$|"
    r"class_change_warning$|subsumption_note$|observability_note$|equivalence_claim$|"
    r"non_goals$|forbidden_strengthenings$|forbidden_weakenings$|forbidden_transfers$)", re.I)

REQUIRED_SLOTS = [
    "class_id", "node_id", "quantifiers", "topology", "data_class", "regularity",
    "genericity", "extension_predicate", "i_plus", "visibility", "conclusion",
    "falsifier", "anti_scope", "class_identity_variants", "f0_binding",
]


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
    """For each line, the stack of YAML mapping keys in force (best effort, indentation based)."""
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
        if raw.lstrip().startswith("#"):
            keys = []  # comment lines sit outside any exempt block
        else:
            keys = stacks[i - 1]
        for pat in (COMPOSITE, COMPOSITE_PROSE):
            m = pat.search(raw)
            if m:
                exempt = any(EXEMPT_KEYS.match(k) for k in keys)
                hits.append({"line": i, "pattern": pat.pattern[:40], "match": m.group(0),
                             "keys": keys[-3:], "exempt": exempt,
                             "text": raw.strip()[:220]})
    return hits


def resolve_pointer(doc, pointer: str):
    node = doc
    for part in pointer.split("."):
        if not isinstance(node, dict) or part not in node:
            return {"resolved": False, "missing_at": part}
        node = node[part]
    return {"resolved": True, "value_type": type(node).__name__}


def truncate_fraction(text: str) -> bool:
    """True when a 64-char hex-looking string is a truncated hash padded with zeros."""
    return bool(re.fullmatch(r"[0-9a-f]{64}", text)) and set(text[16:]) == {"0"}


def main() -> int:
    rep: dict = {"task_id": "W034-F2B-VERIFY-01", "node_id": NODE_ID, "class_id": CLASS_ID}
    checks: dict = {}

    # ---- hashes and bindings -------------------------------------------------
    h_start, h_snap, h_canon = digest(SNAP), digest(SNAP), digest(CANON)
    sidecar_txt = SIDECAR.read_text().strip() if SIDECAR.is_file() else ""
    sidecar_hash = sidecar_txt.split()[0] if sidecar_txt else None
    checks["H1_snapshot_sha256"] = h_snap
    checks["H2_canonical_sha256"] = h_canon
    checks["H2_sidecar_sha256"] = sidecar_hash
    checks["H2_sidecar_matches_canonical"] = sidecar_hash == h_canon
    checks["H3_snapshot_matches_canonical_at_review_time"] = h_snap == h_canon

    mp = json.loads(MAP.read_text())
    f2b = None
    for g in mp.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("id") == NODE_ID:
                f2b = n
    checks["H4_map_measured_sha256"] = (f2b or {}).get("artifact_sha256_measured")
    checks["H4_map_declared_sha256"] = (f2b or {}).get("artifact_sha256")
    checks["H4_map_measured_matches_snapshot"] = (f2b or {}).get("artifact_sha256_measured") == h_snap
    checks["H4_map_declared_is_zero_padded_truncation"] = truncate_fraction((f2b or {}).get("artifact_sha256") or "")

    doc = load_yaml(SNAP)
    lines = SNAP.read_text().splitlines()

    # ---- identity ------------------------------------------------------------
    checks["I1_class_id"] = doc.get("class_id")
    checks["I1_node_id"] = doc.get("node_id")
    checks["I1_conclusion_type"] = (doc.get("conclusion") or {}).get("conclusion_type")
    checks["I1_class_components"] = doc.get("class_components")
    checks["I2_node_id_matches_map_node"] = doc.get("node_id") == NODE_ID
    checks["I2_class_binding_matches_map"] = doc.get("class_id") == CLASS_ID == (f2b or {}).get("class_id")

    # ---- leakage scan --------------------------------------------------------
    hits = composite_scan(lines)
    checks["L1_composite_hits_total"] = len(hits)
    checks["L1_composite_hits_outside_exempt_blocks"] = [h for h in hits if not h["exempt"]]
    checks["L1_composite_hits_inside_exempt_blocks"] = [h for h in hits if h["exempt"]]

    gate = sh([sys.executable, str(GATE.relative_to(ROOT)), "--json", str(SNAP.relative_to(ROOT))])
    try:
        gate_json = json.loads(gate["stdout"])
    except Exception:
        gate_json = None
    checks["L2_canonical_gate"] = {"exit": gate["exit"], "verdict": (gate_json or {}).get("verdict"),
                                   "failed_rules": (gate_json or {}).get("failed_rules"),
                                   "raw_tail": gate["stdout"][-800:]}
    cs = sh([sys.executable, str(CLASSSEP.relative_to(ROOT))])
    checks["L3_classsep_regression"] = {"exit": cs["exit"], "verdict_line": cs["stdout"].strip().splitlines()[-1:]}

    # ---- structure -----------------------------------------------------------
    missing = [k for k in REQUIRED_SLOTS if k not in doc]
    checks["S1_required_slots_present"] = not missing
    checks["S1_missing_slots"] = missing
    q = doc.get("quantifiers") or {}
    checks["S2_quantifier_order"] = [x.get("kind") for x in (q.get("ordered") or [])]
    checks["S2_domains_defined"] = sorted((q.get("domains") or {}).keys())
    ext = doc.get("extension_predicate") or {}
    checks["S3_extension_axes"] = {k: ext.get(k) for k in
                                   ("frozen_regularity", "frozen_equation_concept", "frozen_direction")}
    checks["S3_clauses_a_to_f_present"] = all(f"({c})" in (ext.get("definition") or "") for c in "abcdef")
    f = doc.get("falsifier") or {}
    checks["S4_tier_1_refutes"] = (f.get("tier_1") or {}).get("refutes")
    checks["S4_tier_1_requires_nonmeagerness"] = "non-meager" in ((f.get("tier_1") or {}).get("genericity_requirement") or "")
    checks["S4_tier_2_label"] = (f.get("tier_2") or {}).get("labelling_required")

    # ---- data-class family detection (the class-identity question) -----------
    d0 = ((q.get("domains") or {}).get("D0") or {}).get("definition", "")
    data_reg = doc.get("regularity", {}).get("data_regularity", "")
    gen = doc.get("genericity") or {}
    gen_text = json.dumps(gen, ensure_ascii=False)
    checks["D0_definition"] = d0
    checks["D0_contains_disjunction"] = bool(re.search(r"\bor\b", d0, re.I))
    checks["D0_alternatives_detected"] = [s for s in ("Sobolev", "smooth-with-decay") if s.lower() in d0.lower()]
    checks["D0_data_regularity_mirrors_disjunction"] = bool(re.search(r"\bor\b", data_reg, re.I))
    checks["D0_statement_formal_binder"] = (doc.get("conclusion") or {}).get("statement_formal", "")[:120]
    checks["D0_ambient_topologies_named"] = {
        "weighted_sobolev_product": "H^s_delta" in gen_text or "H^{s" in gen_text,
        "frechet_smooth": "Frechet" in gen_text or "Fréchet" in gen_text,
    }
    checks["D0_quantifier_class"] = q.get("quantifier_class")

    # variant registration for the Sobolev setting
    reg = json.loads(VARIANTS.read_text())
    reg_txt = json.dumps(reg, ensure_ascii=False)
    checks["D1_variant_registry_mentions_sobolev"] = "sobolev" in reg_txt.lower()
    canon_f0 = load_yaml(F0_CANON)
    checks["D1_canonical_f0_variant_ids"] = [v.get("variant_id") for v in (canon_f0.get("variants") or [])]
    author_f0 = load_yaml(F0_AUTHOR)
    checks["D1_taxonomy_data_class_freeze"] = (author_f0.get("class_contracts", {})
                                               .get(CLASS_ID, {}).get("data_class_freeze"))

    # ---- F0 binding ----------------------------------------------------------
    fb = doc.get("f0_binding") or {}
    declared_art = fb.get("declared_f0_artifact")
    declared_hash = fb.get("declared_f0_sha256")
    pointer = doc.get("class_contract_pointer", "")
    ptr_path, _, ptr_key = pointer.partition("#")
    checks["B1_declared_f0_artifact"] = declared_art
    checks["B1_declared_f0_sha256"] = declared_hash
    checks["B1_declared_f0_measured"] = digest(ROOT / declared_art) if declared_art else None
    checks["B1_declared_hash_matches_measured"] = digest(ROOT / declared_art) == declared_hash
    checks["B1_pointer_path"] = ptr_path
    checks["B1_pointer_key"] = ptr_key
    checks["B1_pointer_path_equals_declared_artifact"] = ptr_path == declared_art
    checks["B1_pointer_resolves_in_declared_artifact"] = resolve_pointer(canon_f0, ptr_key)
    checks["B1_pointer_resolves_in_pointer_file"] = (
        resolve_pointer(load_yaml(ROOT / ptr_path), ptr_key) if (ROOT / ptr_path).is_file() else "file_missing")
    checks["B1_pointer_file_sha256"] = digest(ROOT / ptr_path) if ptr_path else None
    checks["B1_consistency_evidence_exists"] = (ROOT / (
        fb.get("consistency_evidence") or "_missing_")).is_file() if fb.get("consistency_evidence") else False

    # ---- timestamp hygiene ---------------------------------------------------
    mt = SNAP.stat().st_mtime
    import datetime
    rev_times = re.findall(r'^revised_at:\s*"([^"]+)"', "\n".join(lines), re.M)
    future = []
    for t in rev_times:
        ts = datetime.datetime.fromisoformat(t)
        if ts.timestamp() > mt + 60:
            future.append(t)
    checks["T1_file_mtime"] = datetime.datetime.fromtimestamp(mt).isoformat(timespec="seconds")
    checks["T1_declared_revised_at_values"] = rev_times
    checks["T1_future_revised_at_values"] = future

    # ---- final hash re-measure (movement during verification) ----------------
    checks["Z1_canonical_sha256_at_end"] = digest(CANON)
    checks["Z1_canonical_moved_during_review"] = digest(CANON) != h_snap
    checks["Z1_snapshot_sha256_at_end"] = digest(SNAP)

    rep["checks"] = checks
    rep["snapshot"] = str(SNAP.relative_to(ROOT))
    rep["reviewed_sha256"] = h_snap
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

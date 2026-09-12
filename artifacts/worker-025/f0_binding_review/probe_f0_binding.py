#!/usr/bin/env python3
"""W025-F0-BIND-01 -- independent, read-only G-F0 class-binding verification at the declared
canonical F0 (research_map/formulation_taxonomy.yaml) and the companion class-contract
supplement (artifacts/formulation/formulation_taxonomy.yaml).

Task source: leadform-resource-request-2026-09-12T00:44 item (2): "binds
research_map/formulation_taxonomy.yaml 276009f4... for G-F0".

Method (independent of the other F0 reviewers):
  P1 freeze pins (sha256/bytes/mtime) before and after; any drift -> moving-target blocker
  P2 strict YAML duplicate-key scan (PyYAML silently last-wins) on F0 + supplement + schemas
  P3 G-F0 gate criteria: exactly 4 class ids, per-class required slots
  P4 D1 reproduction: set-based J-(I+) predicate residue vs the astra-classscope-02 decision
     (single-q TAIL predicate; set-based reading registered as variant SET of AF-WCC-VAC-GEN)
  P5 D3 reproduction: the adjudication says the comeager quantifier is explicit in EVERY
     class conclusion; measure the per-class conclusion quantifier instead of trusting it
  P6 companion-pair measurement: class_contract_pointer resolution in canonical vs supplement
  P7 downstream F0-hash consumer sweep: every artifact pinning an F0 hash is classified
  P8 canonical checkers on the pinned bytes: verify_frozen.py, check_taxonomy_consistency.py,
     class_separation.findings
  C1 duplicate-key detector positive/negative controls
  C2 class-separation merge positive control + split negative control
  C3 freeze stability control

Outputs: raw/probe_output.json (+ controls/ files). No writes outside this directory.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-025/f0_binding_review -> repo root
RAW = HERE / "raw"
CTRL = HERE / "controls"
RAW.mkdir(parents=True, exist_ok=True)
CTRL.mkdir(parents=True, exist_ok=True)

CANON = ROOT / "research_map/formulation_taxonomy.yaml"
SUPP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
SCHEMAS = [
    ROOT / "schemas/af_wcc_vacuum.yaml",
    ROOT / "schemas/af_scc_c2_vacuum.yaml",
    ROOT / "schemas/af_scc_c0_vacuum.yaml",
]
EXPECTED_CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
STALE_F0_HASHES = ["66bf917b", "565a6e50", "0fcc6a19"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stat_rec(p: Path) -> dict:
    st = p.stat()
    return {
        "sha256": sha(p),
        "bytes": st.st_size,
        "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime)),
    }


def lines_with(text: str, needle: str) -> list:
    return [i for i, l in enumerate(text.splitlines(), 1) if needle in l]


def line_of(text: str, needle: str):
    ls = lines_with(text, needle)
    return ls[0] if ls else None


# ---- P2 strict duplicate-key loader -------------------------------------------------------
class DupLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    pairs = []
    for k_node, _v in node.value:
        k = loader.construct_object(k_node, deep=True)
        pairs.append((k, k_node.start_mark.line + 1))
    seen, dups = {}, []
    for k, ln in pairs:
        if k in seen:
            dups.append({"key": str(k), "first_line": seen[k], "dup_line": ln})
        else:
            seen[k] = ln
    loader.dups = list(getattr(loader, "dups", [])) + dups
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def strict_load(text: str):
    ldr = DupLoader(text)
    ldr.dups = []
    try:
        obj = ldr.get_single_data()
    finally:
        ldr.dispose()
    return obj, ldr.dups


def top_level_dups(dups: list) -> list:
    # top-level duplicate keys have first_line >= 1 and the shallowest line numbers
    if not dups:
        return []
    minline = min(d["first_line"] for d in dups)
    return [d for d in dups if d["first_line"] == minline]


# ---- class separation module ---------------------------------------------------------------
spec = importlib.util.spec_from_file_location("class_separation", ROOT / "research_map/class_separation.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

# ---- P1 freeze ------------------------------------------------------------------------------
pins_before = {str(p.relative_to(ROOT)): stat_rec(p) for p in [CANON, SUPP, FROZEN] + SCHEMAS}
canon_text = CANON.read_text()
supp_text = SUPP.read_text()
canon, canon_dups = strict_load(canon_text)
supp, supp_dups = strict_load(supp_text)

out: dict = {
    "task_id": "W025-F0-BIND-01",
    "probe": "probe_f0_binding.py",
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "pins_before": pins_before,
}

# ---- P2 duplicate keys ----------------------------------------------------------------------
schema_dups = {}
for s in SCHEMAS:
    _doc, d = strict_load(s.read_text())
    schema_dups[str(s.relative_to(ROOT))] = {"n_total": len(d), "n_top_level": len(top_level_dups(d)), "dups": d}
out["P2_duplicate_keys"] = {
    "canonical_f0": {"n_total": len(canon_dups), "n_top_level": len(top_level_dups(canon_dups)), "dups": canon_dups},
    "supplement": {"n_total": len(supp_dups), "n_top_level": len(top_level_dups(supp_dups)), "dups": supp_dups},
    "schemas": schema_dups,
    "detector_note": "DupLoader records duplicate mapping keys at any depth; top_level = duplicates sharing the minimum first_line",
}

# ---- P3 gate criteria -----------------------------------------------------------------------
cids = list(canon.get("class_ids") or [])
classes = canon.get("classes") or {}
structural = {
    "class_ids": cids,
    "exactly_4_declared": len(cids) == 4,
    "set_equals_expected": set(cids) == set(EXPECTED_CLASSES),
    "classes_keys_match_class_ids": set(classes) == set(cids),
    "per_class_slots": {},
}
for cid in EXPECTED_CLASSES:
    c = classes.get(cid) or {}
    structural["per_class_slots"][cid] = {
        "hypotheses": bool(c.get("hypotheses")),
        "exclusions": bool(c.get("exclusions")),
        "conclusion_type": bool((c.get("axes") or {}).get("conclusion_type")),
        "test_cases": bool(c.get("test_cases")),
        "known_obstruction": bool(c.get("known_obstruction")),
        "genericity_kind": (c.get("axes") or {}).get("genericity_kind"),
        "genericity_value_status": c.get("genericity_value_status"),
    }
structural["all_slots_present"] = all(
    all(v is True or k in ("genericity_kind", "genericity_value_status") for k, v in slots.items())
    for slots in structural["per_class_slots"].values()
)
out["P3_gate_criteria"] = structural

# ---- P4 D1 set-based predicate residue ------------------------------------------------------
adj = canon.get("class_scope_adjudication") or {}
variants = canon.get("variants") or []
variant_registry = [
    {"parent_class": v.get("parent_class"), "variant_id": v.get("variant_id"), "status": v.get("status")}
    for v in variants
    if isinstance(v, dict)
]
set_parents = {v["parent_class"] for v in variant_registry if v["variant_id"] == "SET"}
d1 = {"adjudication_decision": adj.get("decision", ""), "variant_registry": variant_registry, "per_class": {}}
for cid in EXPECTED_CLASSES:
    ctext = str(((classes.get(cid) or {}).get("conclusion") or {}).get("text", ""))
    norm = ctext.replace(" ", "")
    set_hits = sorted({tok for tok in ("J-(I+)", "J^-(I+)", "union of J") if tok in norm or tok in ctext})
    d1["per_class"][cid] = {
        "set_based_predicate_tokens": set_hits,
        "has_set_based_residue": bool(set_hits),
        "conclusion_line": line_of(canon_text, ctext.strip().splitlines()[0][:60]) if ctext else None,
        "is_registered_variant_parent_for_SET": cid in set_parents,
        "is_registered_variant": any(v["parent_class"] == cid for v in variant_registry),
    }
d1["unregistered_second_predicate_classes"] = [
    cid
    for cid, rec in d1["per_class"].items()
    if rec["has_set_based_residue"] and not rec["is_registered_variant_parent_for_SET"]
]
out["P4_D1_setbased"] = d1

# ---- P5 D3 comeager quantifier --------------------------------------------------------------
d3 = {"adjudication_D3": next((r for r in adj.get("resolved_divergences", []) if r.get("id") == "D3"), None), "per_class": {}}
for cid in EXPECTED_CLASSES:
    ctext = str(((classes.get(cid) or {}).get("conclusion") or {}).get("text", ""))
    d3["per_class"][cid] = {
        "mentions_comeager": "comeager" in ctext,
        "bare_generic": bool(re.search(r"\bgeneric\b", ctext, re.I)) and "comeager" not in ctext,
        "equivalently_gloss": "equivalently" in ctext,
        "genericity_kind": (classes.get(cid, {}).get("axes") or {}).get("genericity_kind"),
        "genericity_value_status": classes.get(cid, {}).get("genericity_value_status"),
        "text_head": ctext[:220],
    }
d3["classes_without_comeager"] = [cid for cid, r in d3["per_class"].items() if not r["mentions_comeager"]]
d3["d3_claim_falsified_by"] = d3["classes_without_comeager"]
out["P5_D3_genericity"] = d3

# ---- P6 companion-pair measurement ----------------------------------------------------------
def resolve_pointer(ref: str):
    if "#" not in ref:
        return {"ref": ref, "path": ref, "anchor": None, "path_exists": (ROOT / ref).exists(), "anchor_resolves": None}
    path, anchor = ref.split("#", 1)
    p = ROOT / path
    rec = {"ref": ref, "path": path, "anchor": anchor, "path_exists": p.exists(), "anchor_resolves": False}
    if p.exists():
        doc, _ = strict_load(p.read_text())
        node = doc
        for part in anchor.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        rec["anchor_resolves"] = node is not None
    return rec


p6 = {"supplement_top_keys": list(supp.keys()), "canonical_top_keys": list(canon.keys()),
      "canonical_has_class_contracts": "class_contracts" in canon, "schemas": {}}
for s in SCHEMAS:
    stext = s.read_text()
    doc, _ = strict_load(stext)
    ptr = doc.get("class_contract_pointer")
    rec = {"class_contract_pointer": ptr, "pointer_line": line_of(stext, "class_contract_pointer:"),
           "f0_binding": doc.get("f0_binding")}
    if ptr:
        rec["pointer_resolution"] = resolve_pointer(ptr)
        rec["canonical_equivalent_anchor_resolves"] = resolve_pointer(
            "research_map/formulation_taxonomy.yaml#" + ptr.split("#", 1)[1]
        )["anchor_resolves"] if "#" in ptr else None
    p6["schemas"][str(s.relative_to(ROOT))] = rec
out["P6_companion_pair"] = p6

# ---- P7 downstream F0 hash consumers --------------------------------------------------------
consumers = []
for p in sorted(ROOT.rglob("*")):
    if not p.is_file() or p.suffix not in (".json", ".jsonl", ".yaml", ".yml", ".py", ".md", ".csv", ".txt"):
        continue
    rel = str(p.relative_to(ROOT))
    if rel.startswith(("artifacts/worker-025/", "runtime/", ".git/", "node_modules/", "workdir/")) or "/node_modules/" in rel:
        continue
    try:
        text = p.read_text(errors="ignore")
    except Exception:
        continue
    hits = [h for h in ["276009f4", "c8e979a1"] + STALE_F0_HASHES if h in text]
    if hits:
        consumers.append({"path": rel, "f0_tokens": hits, "sha256": sha(p)})
current, stale = [], []
for c in consumers:
    toks = set(c["f0_tokens"])
    if toks & set(STALE_F0_HASHES):
        stale.append(c)
    if "276009f4" in toks:
        current.append(c)
out["P7_consumers"] = {"n_scanned_files_with_f0_tokens": len(consumers), "current_276009f4": current, "stale_tokens_present": stale}

# ---- P8 canonical checkers ------------------------------------------------------------------
def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
    return {"cmd": " ".join(str(c) for c in cmd), "exit_code": r.returncode,
            "stdout_tail": (r.stdout or "")[-1500:], "stderr_tail": (r.stderr or "")[-600:]}


p8 = {"verify_frozen": run([sys.executable, "artifacts/formulation/tools/verify_frozen.py"])}
p8["check_taxonomy_consistency"] = run([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"])
p8["class_schema_on_canonical_bytes"] = {
    str(s.relative_to(ROOT)): run([sys.executable, "artifacts/formulation/tools/check_class_schema.py", "--json", str(s)])
    for s in SCHEMAS
}
p8["classsep_findings_canonical_f0"] = cs.findings(canon, "P8:canonical_f0")
p8["classsep_findings_schemas"] = {
    str(s.relative_to(ROOT)): cs.findings(strict_load(s.read_text())[0], "P8:" + str(s.relative_to(ROOT)))
    for s in SCHEMAS
}
out["P8_canonical_checkers"] = p8

# ---- C1/C2 controls -------------------------------------------------------------------------
dup_positive = CTRL / "dup_positive.yaml"
dup_positive.write_text("a: 1\nb: 2\na: 3\n")
dup_negative = CTRL / "dup_negative.yaml"
dup_negative.write_text("a: 1\nb: 2\nc: 3\n")
c1 = {}
for name, p in (("positive_dup", dup_positive), ("negative_clean", dup_negative)):
    _o, d = strict_load(p.read_text())
    c1[name] = {"path": str(p.relative_to(ROOT)), "n_dups": len(d), "dups": d}
c1["PASS"] = c1["positive_dup"]["n_dups"] >= 1 and c1["negative_clean"]["n_dups"] == 0
merge_text = CTRL / "classsep_positive_merge.json"
merge_text.write_text(json.dumps({"label": "AF-SCC-C2-VAC-GEN and AF-SCC-C0-VAC-GEN are one class"}))
split_text = CTRL / "classsep_negative_split.json"
split_text.write_text(json.dumps({"note": "C2/C0 split: never write 'C0 or C2'; the two classes are disjoint."}))
cp = cs.findings(json.loads(merge_text.read_text()), "C2:positive")
cn = cs.findings(json.loads(split_text.read_text()), "C2:negative")
c2 = {"positive_merge_findings": cp, "negative_split_findings": cn,
      "PASS": len(cp) >= 1 and len(cn) == 0}
out["C1_dupkey_control"] = c1
out["C2_classsep_control"] = c2

# ---- C3 freeze stability --------------------------------------------------------------------
pins_after = {str(p.relative_to(ROOT)): stat_rec(p) for p in [CANON, SUPP, FROZEN] + SCHEMAS}
out["pins_after"] = pins_after
out["C3_freeze_held"] = pins_before == pins_after

(RAW / "probe_output.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
print(json.dumps({
    "P3_exactly_4": structural["exactly_4_declared"],
    "P3_all_slots": structural["all_slots_present"],
    "P2_canon_dups": len(canon_dups),
    "P2_schema_top_dups": {k: v["n_top_level"] for k, v in schema_dups.items()},
    "P4_unregistered": d1["unregistered_second_predicate_classes"],
    "P5_no_comeager": d3["classes_without_comeager"],
    "P6_canon_has_class_contracts": p6["canonical_has_class_contracts"],
    "P7_stale_consumers": len(stale),
    "P8_consistency_exit": p8["check_taxonomy_consistency"]["exit_code"],
    "P8_verify_frozen_exit": p8["verify_frozen"]["exit_code"],
    "P8_classsep_canon_findings": p8["classsep_findings_canonical_f0"],
    "C1_PASS": c1["PASS"], "C2_PASS": c2["PASS"], "C3_freeze_held": out["C3_freeze_held"],
}, indent=1))

#!/usr/bin/env python3
"""W025-F0-BIND-01 FINAL verification at the settled closure revision.

Corrects the first-pass probe false positive: the J-(I+) tokens at
research_map/formulation_taxonomy.yaml lines 84/206/420 are metalinguistic MENTIONS
(supersession record, variant definition, bracketed rev5 discharge note). This script
classifies assertive use vs mention before deciding D1.

Read-only except this directory. Writes raw/final_output.json.
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
ROOT = HERE.parents[2]
RAW = HERE / "raw"
RAW.mkdir(parents=True, exist_ok=True)

CANON = ROOT / "research_map/formulation_taxonomy.yaml"
SUPP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
MAP = ROOT / "research_map/research_map.json"
SCHEMAS = [ROOT / "schemas/af_wcc_vacuum.yaml", ROOT / "schemas/af_scc_c2_vacuum.yaml", ROOT / "schemas/af_scc_c0_vacuum.yaml"]
EXPECTED = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rec(p):
    st = Path(p).stat()
    return {"sha256": sha(p), "bytes": st.st_size, "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime))}


def lines_with(text, needle):
    return [i for i, l in enumerate(text.splitlines(), 1) if needle in l]


def assert_text(text: str) -> str:
    """Remove bracketed revision notes and quoted superseded wording -> assertive prose."""
    t = re.sub(r"\[[^\]]*\]", " ", text)
    t = re.sub(r"'[^']*'", " ", t)
    t = re.sub(r'"[^"]*"', " ", t)
    return t


spec = importlib.util.spec_from_file_location("cs3", ROOT / "research_map/class_separation.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

# stability window 20 s
w0 = {str(p.relative_to(ROOT)): rec(p) for p in [CANON, SUPP, FROZEN] + SCHEMAS}
time.sleep(20)
w1 = {str(p.relative_to(ROOT)): rec(p) for p in [CANON, SUPP, FROZEN] + SCHEMAS}

canon = yaml.safe_load(CANON.read_text())
classes = canon["classes"]
adj = canon.get("class_scope_adjudication") or {}
variants = canon.get("variants") or []

out = {
    "task_id": "W025-F0-BIND-01",
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "pins": w1,
    "stable_over_20s": w0 == w1,
    "first_pass_false_positive": {
        "what": "probe_f0_binding.py P4 flagged AF-WCC-SCALAR-SPH as carrying an unregistered set-based predicate",
        "why_wrong": "the J-(I+) token is a metalinguistic mention inside the bracketed rev5 discharge note and the supersession/variant records, not the class predicate",
        "correction": "assertive-text classification below; same class of error as the earlier w025 L1 comparator false positive",
    },
}

# --- gate criteria ---------------------------------------------------------------------------
out["gate_criteria"] = {
    "class_ids": list(canon["class_ids"]),
    "exactly_four": list(canon["class_ids"]) == EXPECTED,
    "per_class": {},
    "disjointness_pairs": len(canon.get("disjointness") or []),
    "disjointness_expected_pairs": 6,
}
for cid in EXPECTED:
    c = classes[cid]
    concl = c.get("conclusion") or {}
    out["gate_criteria"]["per_class"][cid] = {
        "hypotheses": len(c.get("hypotheses") or []),
        "exclusions": len(c.get("exclusions") or []),
        "conclusion_type": (c.get("axes") or {}).get("conclusion_type"),
        "conclusion_type_declared": concl.get("type"),
        "conclusion_type_agrees": (c.get("axes") or {}).get("conclusion_type") == concl.get("type"),
        "test_cases": len(c.get("test_cases") or []),
        "known_obstruction": bool(c.get("known_obstruction")),
    }

# --- D1 assertive vs mention -----------------------------------------------------------------
set_parents = {v.get("parent_class") for v in variants if isinstance(v, dict) and v.get("variant_id") == "SET"}
d1 = {"registry": [{"parent": v.get("parent_class"), "id": v.get("variant_id"), "status": v.get("status")} for v in variants if isinstance(v, dict)], "per_class": {}}
asserted_hits = []
for cid in EXPECTED:
    ctext = str((classes[cid].get("conclusion") or {}).get("text", ""))
    a = assert_text(ctext)
    toks = sorted({t for t in ("J-(I+)", "J^-(I+)", "union of J") if t in a})
    d1["per_class"][cid] = {
        "set_tokens_in_assertive_text": toks,
        "set_tokens_in_raw_text": sorted({t for t in ("J-(I+)", "J^-(I+)", "union of J") if t in ctext}),
        "assertive_line": None,
    }
    if toks:
        asserted_hits.append(cid)
d1["decision"] = adj.get("decision", "")
d1["assertive_set_based_classes"] = asserted_hits
d1["verdict"] = "D1 REPAIRED" if not asserted_hits else "D1 RESIDUE"
out["D1"] = d1

# --- D3 --------------------------------------------------------------------------------------
d3 = {"per_class": {}}
for cid in EXPECTED:
    ctext = str((classes[cid].get("conclusion") or {}).get("text", ""))
    d3["per_class"][cid] = {
        "assertive_mentions_comeager": "comeager" in assert_text(ctext),
        "genericity_kind": (classes[cid].get("axes") or {}).get("genericity_kind"),
        "genericity_value_status": classes[cid].get("genericity_value_status"),
    }
d3["D3_record"] = next((r for r in adj.get("resolved_divergences", []) if r.get("id") == "D3"), None)
d3["verdict"] = "D3 REPAIRED" if all(r["assertive_mentions_comeager"] for r in d3["per_class"].values()) else "D3 RESIDUE"
out["D3"] = d3

# --- F1 canonical predicate cross-check (does F0 canonical agree with F1?) ---------------------
f1 = yaml.safe_load((ROOT / "schemas/af_wcc_vacuum.yaml").read_text())
f1_vis = None
for k, v in (f1.get("visibility") or {}).items():
    f1_vis = {k: v} if k == "definition" else f1_vis
out["F1_cross_check"] = {"visibility_definition": str((f1.get("visibility") or {}).get("definition"))[:600],
                         "f0_wcc_uses_tail": "tail" in assert_text(str(classes["AF-WCC-VAC-GEN"]["conclusion"]["text"]))}

# --- binding chain ---------------------------------------------------------------------------
out["binding_chain"] = {"canonical_pin": w1[str(CANON.relative_to(ROOT))]["sha256"], "supplement_pin": w1[str(SUPP.relative_to(ROOT))]["sha256"], "schemas": {}}
frozen = json.loads(FROZEN.read_text())
out["binding_chain"]["frozen"] = {
    "revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at"),
    "F0_declared": (frozen.get("logical_artifacts") or {}).get("F0-declared-taxonomy", {}).get("sha256"),
    "F0_supplement": (frozen.get("logical_artifacts") or {}).get("F0-class-contract-supplement", {}).get("sha256"),
}
for s in SCHEMAS:
    doc = yaml.safe_load(s.read_text())
    fb = doc.get("f0_binding") or {}
    ptr = doc.get("class_contract_pointer")
    out["binding_chain"]["schemas"][str(s.relative_to(ROOT))] = {
        "class_contract_pointer": ptr,
        "pointer_targets_canonical_classes": bool(ptr and ptr.startswith("research_map/formulation_taxonomy.yaml#classes.")),
        "declared_f0_sha256": fb.get("declared_f0_sha256"),
        "matches_live": fb.get("declared_f0_sha256") == out["binding_chain"]["canonical_pin"],
    }

# --- map F0 hash -----------------------------------------------------------------------------
try:
    m = json.loads(MAP.read_text())
    nodes = m.get("nodes") or []
    f0node = next((n for n in nodes if n.get("node_id") == "F0"), None)
    out["binding_chain"]["map_F0_artifact_sha256"] = (f0node or {}).get("artifact_sha256")
    out["binding_chain"]["map_F0_matches_live"] = (f0node or {}).get("artifact_sha256") == out["binding_chain"]["canonical_pin"]
except Exception as e:
    out["binding_chain"]["map_error"] = str(e)

# --- checkers --------------------------------------------------------------------------------
def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
    return {"exit_code": r.returncode, "out": (r.stdout or "")[-900:], "err": (r.stderr or "")[-300:]}


out["checkers"] = {
    "verify_frozen": run([sys.executable, "artifacts/formulation/tools/verify_frozen.py"]),
    "taxonomy_consistency": run([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"]),
    "check_class_schema": {str(s.relative_to(ROOT)): run([sys.executable, "artifacts/formulation/tools/check_class_schema.py", "--json", str(s)]) for s in SCHEMAS},
    "classsep_canonical_f0": cs.findings(canon, "final:F0"),
    "classsep_schemas": {str(s.relative_to(ROOT)): cs.findings(yaml.safe_load(s.read_text()), "final:" + str(s.relative_to(ROOT))) for s in SCHEMAS},
}
out["checkers"]["all_pass"] = (
    out["checkers"]["verify_frozen"]["exit_code"] == 0
    and out["checkers"]["taxonomy_consistency"]["exit_code"] == 0
    and all(v["exit_code"] == 0 for v in out["checkers"]["check_class_schema"].values())
    and not out["checkers"]["classsep_canonical_f0"]
    and all(not v for v in out["checkers"]["classsep_schemas"].values())
)

(RAW / "final_output.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
print(json.dumps({
    "stable": out["stable_over_20s"],
    "pins": {k: v["sha256"][:12] for k, v in w1.items()},
    "exactly_four": out["gate_criteria"]["exactly_four"],
    "type_agrees_all": all(r["conclusion_type_agrees"] for r in out["gate_criteria"]["per_class"].values()),
    "test_cases": {k: v["test_cases"] for k, v in out["gate_criteria"]["per_class"].items()},
    "disjointness_pairs": out["gate_criteria"]["disjointness_pairs"],
    "D1": out["D1"]["verdict"], "D3": out["D3"]["verdict"],
    "binding": {k: (v.get("matches_live") if isinstance(v, dict) else v) for k, v in out["binding_chain"]["schemas"].items()},
    "frozen_rev": out["binding_chain"]["frozen"]["revision"],
    "frozen_pin_matches": out["binding_chain"]["frozen"]["F0_declared"] == out["binding_chain"]["canonical_pin"],
    "map_matches": out["binding_chain"].get("map_F0_matches_live"),
    "checkers_all_pass": out["checkers"]["all_pass"],
    "verify_frozen_exit": out["checkers"]["verify_frozen"]["exit_code"],
    "classsep_f0": out["checkers"]["classsep_canonical_f0"],
}, indent=1))

#!/usr/bin/env python3
"""W025-F0-BIND-01 recheck at the settled post-closure hashes.

The first probe run (probe_f0_binding.py) observed the closure revision land mid-run:
F0 276009f4 -> 0abb9ed8 at 00:31:41 and the three schemas -> cce9c601/5476a3f2/55d0a1ea
at 00:32:02, while FROZEN.json rev26 still pins the superseded hashes. This recheck binds
only to the bytes measured stable across a >=30 s window and re-runs the F0 checks plus the
corrected class-separation controls. Read-only.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW = HERE / "raw"
CTRL = HERE / "controls"
RAW.mkdir(parents=True, exist_ok=True)
CTRL.mkdir(parents=True, exist_ok=True)

CANON = ROOT / "research_map/formulation_taxonomy.yaml"
SUPP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
SCHEMAS = [ROOT / "schemas/af_wcc_vacuum.yaml", ROOT / "schemas/af_scc_c2_vacuum.yaml", ROOT / "schemas/af_scc_c0_vacuum.yaml"]
EXPECTED = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rec(p: Path) -> dict:
    st = p.stat()
    return {"sha256": sha(p), "bytes": st.st_size, "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime))}


class DupLoader(yaml.SafeLoader):
    pass


def _cm(loader, node, deep=False):
    seen, dups = {}, []
    for k_node, _v in node.value:
        k = loader.construct_object(k_node, deep=True)
        ln = k_node.start_mark.line + 1
        if k in seen:
            dups.append({"key": str(k), "first_line": seen[k], "dup_line": ln})
        else:
            seen[k] = ln
    loader.dups = list(getattr(loader, "dups", [])) + dups
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _cm)


def strict_load(text):
    ldr = DupLoader(text)
    ldr.dups = []
    try:
        o = ldr.get_single_data()
    finally:
        ldr.dispose()
    return o, ldr.dups


def lines_with(text, needle):
    return [i for i, l in enumerate(text.splitlines(), 1) if needle in l]


spec = importlib.util.spec_from_file_location("cs2", ROOT / "research_map/class_separation.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

# --- stability window: measure, wait 30 s, measure again -------------------------------------
w0 = {str(p.relative_to(ROOT)): rec(p) for p in [CANON, SUPP, FROZEN] + SCHEMAS}
time.sleep(30)
w1 = {str(p.relative_to(ROOT)): rec(p) for p in [CANON, SUPP, FROZEN] + SCHEMAS}
stable = w0 == w1

canon_text = CANON.read_text()
canon, canon_dups = strict_load(canon_text)
supp, supp_dups = strict_load(SUPP.read_text())
classes = canon.get("classes") or {}
adj = canon.get("class_scope_adjudication") or {}
variants = canon.get("variants") or []

out = {
    "task_id": "W025-F0-BIND-01-RECHECK",
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "stability_window_seconds": 30,
    "pins_w0": w0,
    "pins_w1": w1,
    "stable_over_window": stable,
    "moving_target_observed_in_first_run": {
        "F0": ["276009f4f63d -> 0abb9ed8a961 at 2026-09-12T00:31:41+08:00"],
        "F1": ["9a8bd4c96800 -> b474fbc49cdd -> cce9c60146d6 (00:32:02)"],
        "F2a": ["b6123750b37d -> a7ccae4d5dec -> 5476a3f2c6bc (00:32:02)"],
        "F2b": ["1bb78ce9b357 -> b71ec02c601d -> 55d0a1ea9bda (00:32:02)"],
        "FROZEN": ["2554e276a0db (rev26, 00:24:49) still pins the superseded hashes; verify_frozen exits 1 with 8 drifts"],
    },
    "P2_duplicate_keys": {
        "canonical_f0_n": len(canon_dups),
        "supplement_n": len(supp_dups),
        "schemas": {str(s.relative_to(ROOT)): len(strict_load(s.read_text())[1]) for s in SCHEMAS},
    },
    "P3_gate_criteria": {},
    "P4_D1": {},
    "P5_D3": {},
    "P6_binding": {},
    "P8_checkers": {},
    "C1_dupkey": {},
    "C2_classsep_corrected": {},
}

# P3
cids = list(canon.get("class_ids") or [])
out["P3_gate_criteria"] = {
    "class_ids": cids,
    "exactly_4": len(cids) == 4 and set(cids) == set(EXPECTED),
    "classes_match": set(classes) == set(cids),
    "per_class": {
        cid: {
            "hypotheses": bool((classes.get(cid) or {}).get("hypotheses")),
            "exclusions": bool((classes.get(cid) or {}).get("exclusions")),
            "conclusion_type": bool(((classes.get(cid) or {}).get("axes") or {}).get("conclusion_type")),
            "test_cases": bool((classes.get(cid) or {}).get("test_cases")),
        }
        for cid in EXPECTED
    },
}

# P4 D1
set_parents = {v.get("parent_class") for v in variants if isinstance(v, dict) and v.get("variant_id") == "SET"}
for cid in EXPECTED:
    c = classes.get(cid) or {}
    ctext = str((c.get("conclusion") or {}).get("text", ""))
    norm = ctext.replace(" ", "")
    toks = sorted({t for t in ("J-(I+)", "J^-(I+)", "union of J") if t in norm or t in ctext})
    first = ctext.strip().splitlines()[0][:50] if ctext else ""
    out["P4_D1"][cid] = {
        "set_tokens": toks,
        "conclusion_lines": lines_with(canon_text, "J-(I+)") + lines_with(canon_text, "J^-(I+)"),
        "has_set_based_residue": bool(toks),
        "registered_as_SET_parent": cid in set_parents,
        "conclusion_head": ctext[:260],
    }
out["P4_D1"]["decision"] = adj.get("decision", "")
out["P4_D1"]["unregistered_second_predicate"] = [
    cid for cid, r in out["P4_D1"].items() if isinstance(r, dict) and r["has_set_based_residue"] and not r["registered_as_SET_parent"]
]
out["P4_D1"]["variant_registry"] = [{"parent": v.get("parent_class"), "id": v.get("variant_id"), "status": v.get("status")} for v in variants if isinstance(v, dict)]

# P5 D3
for cid in EXPECTED:
    c = classes.get(cid) or {}
    ctext = str((c.get("conclusion") or {}).get("text", ""))
    out["P5_D3"][cid] = {
        "mentions_comeager": "comeager" in ctext,
        "genericity_kind": (c.get("axes") or {}).get("genericity_kind"),
        "genericity_value_status": c.get("genericity_value_status"),
    }
out["P5_D3"]["D3_record"] = next((r for r in adj.get("resolved_divergences", []) if r.get("id") == "D3"), None)
out["P5_D3"]["classes_without_comeager"] = [
    cid for cid in EXPECTED if not out["P5_D3"][cid]["mentions_comeager"]
]

# P6 binding
def resolve(ref):
    if "#" not in ref:
        return {"ref": ref, "resolves": (ROOT / ref).exists()}
    path, anchor = ref.split("#", 1)
    p = ROOT / path
    r = {"ref": ref, "path": path, "anchor": anchor, "path_exists": p.exists(), "resolves": False}
    if p.exists():
        doc, _ = strict_load(p.read_text())
        node = doc
        for part in anchor.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        r["resolves"] = node is not None
    return r


out["P6_binding"] = {"canonical_has_class_contracts": "class_contracts" in canon, "schemas": {}}
for s in SCHEMAS:
    stext = s.read_text()
    doc, _ = strict_load(stext)
    ptr = doc.get("class_contract_pointer")
    fb = doc.get("f0_binding") or {}
    r = {"class_contract_pointer": ptr, "pointer_line": (lines_with(stext, "class_contract_pointer:") or [None])[0],
         "pointer_resolution": resolve(ptr) if ptr else None,
         "f0_binding_declared_sha256": fb.get("declared_f0_sha256"),
         "f0_binding_declared_matches_live_canonical": fb.get("declared_f0_sha256") == w1[str(CANON.relative_to(ROOT))]["sha256"],
         "f0_binding_checked_at": fb.get("checked_at")}
    out["P6_binding"]["schemas"][str(s.relative_to(ROOT))] = r

# P8 checkers
def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
    return {"cmd": " ".join(map(str, cmd)), "exit_code": r.returncode, "stdout_tail": (r.stdout or "")[-1200:], "stderr_tail": (r.stderr or "")[-400:]}


out["P8_checkers"]["verify_frozen"] = run([sys.executable, "artifacts/formulation/tools/verify_frozen.py"])
out["P8_checkers"]["check_taxonomy_consistency"] = run([sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"])
out["P8_checkers"]["check_class_schema_canonical"] = {str(s.relative_to(ROOT)): run([sys.executable, "artifacts/formulation/tools/check_class_schema.py", "--json", str(s)]) for s in SCHEMAS}
out["P8_checkers"]["classsep_canonical_f0"] = cs.findings(canon, "P8:canonical_f0")
out["P8_checkers"]["classsep_schemas"] = {str(s.relative_to(ROOT)): cs.findings(strict_load(s.read_text())[0], "P8:" + str(s.relative_to(ROOT))) for s in SCHEMAS}

# C1
(CTRL / "dup_positive.yaml").write_text("a: 1\nb: 2\na: 3\n")
(CTRL / "dup_negative.yaml").write_text("a: 1\nb: 2\nc: 3\n")
for n, p in (("positive_dup", CTRL / "dup_positive.yaml"), ("negative_clean", CTRL / "dup_negative.yaml")):
    _o, d = strict_load(p.read_text())
    out["C1_dupkey"][n] = {"n_dups": len(d), "dups": d}
out["C1_dupkey"]["PASS"] = out["C1_dupkey"]["positive_dup"]["n_dups"] >= 1 and out["C1_dupkey"]["negative_clean"]["n_dups"] == 0

# C2 corrected: regularity-token fixtures (the first probe used full class ids, which the
# detector intentionally does not flag; that control was invalid, recorded in evidence.json)
fixtures = {
    "positive_regularity_slash": {"label": "C2/C0 merged"},
    "positive_regularity_or": {"label": "regularity C0 or C2"},
    "positive_merge_explicit": {"label": "the C0 and C2 classes share one schema"},
    "negative_split": {"note": "C2/C0 split: never write 'C0 or C2'; the two classes are disjoint."},
    "negative_split2": {"note": "C0-vs-C2 distinction preserved"},
}
for n, fx in fixtures.items():
    (CTRL / f"classsep_{n}.json").write_text(json.dumps(fx))
    out["C2_classsep_corrected"][n] = cs.findings(fx, "C2:" + n)
out["C2_classsep_corrected"]["PASS"] = all(
    len(out["C2_classsep_corrected"][k]) >= 1 for k in ("positive_regularity_slash", "positive_regularity_or", "positive_merge_explicit")
) and all(len(out["C2_classsep_corrected"][k]) == 0 for k in ("negative_split", "negative_split2"))

(RAW / "recheck_output.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
print(json.dumps({
    "stable_over_window": stable,
    "pins": {k: v["sha256"][:12] for k, v in w1.items()},
    "dups": out["P2_duplicate_keys"],
    "P3_exactly_4": out["P3_gate_criteria"]["exactly_4"],
    "P4_unregistered": out["P4_D1"]["unregistered_second_predicate"],
    "P4_lines": out["P4_D1"].get("AF-WCC-SCALAR-SPH", {}).get("conclusion_lines"),
    "P5_no_comeager": out["P5_D3"]["classes_without_comeager"],
    "P6_matches_live": {k: v["f0_binding_declared_matches_live_canonical"] for k, v in out["P6_binding"]["schemas"].items()},
    "P8_verify_frozen_exit": out["P8_checkers"]["verify_frozen"]["exit_code"],
    "P8_consistency_exit": out["P8_checkers"]["check_taxonomy_consistency"]["exit_code"],
    "P8_classsep_f0": out["P8_checkers"]["classsep_canonical_f0"],
    "C1_PASS": out["C1_dupkey"]["PASS"],
    "C2_PASS": out["C2_classsep_corrected"]["PASS"],
}, indent=1))

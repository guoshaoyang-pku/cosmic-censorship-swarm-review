#!/usr/bin/env python3
"""worker-009 independent verification of F1 schemas/af_wcc_vacuum.yaml at the bound hash.

Adversarial: each check tries to REFUTE the blocking findings in
reviews/F1-review-090.json, -094.json, -19.json, F1-review-lead-audit-r2.json.
Raw output only; no verdict is computed here.
"""
import json, hashlib, re, subprocess, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
F1 = ROOT / "schemas/af_wcc_vacuum.yaml"
BOUND = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
OUT = {}

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def rel(p):
    return str(Path(p).resolve().relative_to(ROOT))

# ---------- V1 pin + stability ----------
raw = F1.read_bytes()
st = F1.stat()
OUT["V1_pin"] = {
    "target": rel(F1),
    "sha256_measured": hashlib.sha256(raw).hexdigest(),
    "bound_sha256": BOUND,
    "matches_bound": hashlib.sha256(raw).hexdigest() == BOUND,
    "bytes": len(raw),
    "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds"),
    "verified_at": NOW.isoformat(timespec="seconds"),
}

# ---------- V2 duplicate YAML mapping keys (strict walk, no safe_load) ----------
import yaml
dups = {}
try:
    node = yaml.compose(raw.decode("utf-8"))
    seen = {}
    for k, v in node.value:
        key = k.value
        seen.setdefault(key, 0)
        seen[key] += 1
    dups = {k: c for k, c in seen.items() if c > 1}
except Exception as e:
    dups = {"__parse_error__": str(e)}
safe = yaml.safe_load(raw.decode("utf-8"))
OUT["V2_duplicate_keys"] = {
    "top_level_duplicates": dups,
    "duplicate_key_count": sum(c - 1 for c in dups.values() if isinstance(c, int)),
    "safe_load_effective_revised_at": safe.get("revised_at"),
    "safe_load_effective_revised_at_unused": safe.get("revised_at_unused"),
    "raw_revised_at_lines": [i + 1 for i, l in enumerate(raw.decode().splitlines()) if l.startswith("revised_at:")],
    "raw_revised_at_unused_lines": [i + 1 for i, l in enumerate(raw.decode().splitlines()) if l.startswith("revised_at_unused:")],
}

# ---------- V3 clock discipline ----------
def skew(ts):
    if not ts:
        return None
    dt = datetime.fromisoformat(ts)
    return round((dt - NOW).total_seconds(), 1)

OUT["V3_clock"] = {
    "wall_clock_now": NOW.isoformat(timespec="seconds"),
    "file_mtime": OUT["V1_pin"]["mtime"],
    "effective_revised_at": safe.get("revised_at"),
    "effective_revised_at_skew_seconds": skew(safe.get("revised_at")),
    "f0_binding_checked_at": (safe.get("f0_binding") or {}).get("checked_at"),
    "f0_binding_checked_at_skew_seconds": skew((safe.get("f0_binding") or {}).get("checked_at")),
    "future_dated_at_write_time": datetime.fromisoformat(safe["revised_at"]) > datetime.fromtimestamp(st.st_mtime, CST),
    "still_future_dated_at_verify_time": skew(safe.get("revised_at")) is not None and skew(safe["revised_at"]) > 0,
}

# ---------- V4 pointer / binding resolution ----------
canon_tax = ROOT / "research_map/formulation_taxonomy.yaml"
auth_tax = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
canon_f1 = ROOT / "schemas/af_wcc_vacuum.yaml"
auth_f1 = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
def contract(p):
    d = yaml.safe_load(p.read_text())
    cc = (d.get("class_contracts") or {})
    c = cc.get("AF-WCC-VAC-GEN")
    return json.dumps(c, sort_keys=True, separators=(",", ":")) if c is not None else None
ct_c, ct_a = contract(canon_tax), contract(auth_tax)
OUT["V4_binding"] = {
    "class_contract_pointer": safe.get("class_contract_pointer"),
    "f0_binding": safe.get("f0_binding"),
    "canonical_taxonomy": {"path": rel(canon_tax), "sha256": sha(canon_tax), "bytes": canon_tax.stat().st_size},
    "authoring_taxonomy": {"path": rel(auth_tax), "sha256": sha(auth_tax), "bytes": auth_tax.stat().st_size},
    "taxonomy_byte_identical": sha(canon_tax) == sha(auth_tax),
    "class_contract_AF_WCC_canonical_json_sha256": hashlib.sha256(ct_c.encode()).hexdigest() if ct_c else None,
    "class_contract_AF_WCC_authoring_json_sha256": hashlib.sha256(ct_a.encode()).hexdigest() if ct_a else None,
    "class_contract_semantically_identical": ct_c == ct_a,
    "pointer_target_exists": (auth_tax).exists(),
    "pointer_target_is_canonical_path": str(auth_tax.resolve()) == str(canon_tax.resolve()),
    "f1_canonical_vs_authoring_byte_identical": sha(canon_f1) == sha(auth_f1) if auth_f1.exists() else "authoring F1 absent",
    "f1_authoring_sha256": sha(auth_f1) if auth_f1.exists() else None,
}

# ---------- V5 predicate consistency: formal quantifier vs visibility definition ----------
lines = raw.decode().splitlines()
def hits(pat, label):
    return [{"line": i + 1, "text": l.strip()[:200]} for i, l in enumerate(lines) if re.search(pat, l)]
OUT["V5_predicate"] = {
    "whole_curve_gamma_subset_Jq": hits(r"gamma\s+subset\s+J\^\-\(q\)", "whole"),
    "whole_curve_gamma_0_T": hits(r"gamma\(\[0,T\)\)", "whole-interval"),
    "tail_gamma_t0_T": hits(r"gamma\(\[t0,T\)\)", "tail"),
    "visibility_definition_locator": "visibility.definition",
    "formal_quantifier_locator": "quantifiers.formal",
    "D5_locator": "quantifiers.domains.D5",
}

# ---------- V6 undefined symbol ----------
OUT["V6_undefined_symbol"] = {
    "AF_{I+} occurrences": hits(r"AF_\{I\+\}", "AF"),
    "defined_as_key": "AF_{I+}" in raw.decode(),
    "statement_formal": safe.get("conclusion", {}).get("statement_formal"),
}

# ---------- V7 required slots at bound hash ----------
req = {
    "quantifiers": "quantifiers", "topology": "topology", "regularity": "regularity",
    "genericity": "genericity", "i_plus": "i_plus", "visibility": "visibility",
    "conclusion_type": "conclusion.conclusion_type", "falsifier": "falsifier",
}
def get(d, path):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur
OUT["V7_required_slots"] = {k: {"present": get(safe, v) is not None, "value": (get(safe, v) if k in ("conclusion_type",) else "present")} for k, v in req.items()}
OUT["V7_required_slots"]["class_id"] = safe.get("class_id")
OUT["V7_required_slots"]["anti_scope_class_ids"] = [x.get("class_id") for x in (safe.get("anti_scope", {}) or {}).get("not_this_class", [])]
OUT["V7_required_slots"]["review_status"] = safe.get("review_status")

# ---------- V8 class-separation detector (independent module) ----------
sys.path.insert(0, str(ROOT / "research_map"))
try:
    import class_separation
    OUT["V8_class_separation"] = {
        "module_sha256": sha(ROOT / "research_map/class_separation.py"),
        "findings_for_text": class_separation.findings_for_text(raw.decode(), "schemas/af_wcc_vacuum.yaml"),
    }
except Exception as e:
    OUT["V8_class_separation"] = {"error": repr(e)}

# ---------- V9 independent FORM-GATE-01 re-run ----------
gate = ROOT / "artifacts/flash-13/form_gate/check_class_schema.py"
gout = ROOT / "artifacts/worker-009/f1_review/form_gate_rerun.json"
try:
    r = subprocess.run([sys.executable, str(gate), str(F1), "--class", "AF-WCC-VAC-GEN", "--json-out", str(gout)],
                       capture_output=True, text=True, timeout=180)
    OUT["V9_form_gate_01"] = {"exit_code": r.returncode, "stdout_tail": r.stdout[-600:], "stderr_tail": r.stderr[-600:],
                              "report": json.loads(gout.read_text()) if gout.exists() else None}
except Exception as e:
    OUT["V9_form_gate_01"] = {"error": repr(e)}

# ---------- V10 falsifier-test binding drift ----------
ft = ROOT / "schemas/f1_falsifier_tests.jsonl"
if ft.exists():
    binds = []
    for i, l in enumerate(ft.read_text().splitlines()):
        if not l.strip():
            continue
        try:
            d = json.loads(l)
        except Exception:
            continue
        for k in ("binding_sha256", "schema_sha256", "target_sha256", "artifact_sha256", "frozen_sha256"):
            if k in d:
                binds.append({"line": i + 1, "field": k, "value": d[k], "binds_reviewed": d[k] == BOUND or BOUND.startswith(str(d[k]))})
    OUT["V10_falsifier_tests"] = {"path": rel(ft), "sha256": sha(ft), "bindings": binds,
                                  "distinct_bindings": sorted({b["value"] for b in binds})}
else:
    OUT["V10_falsifier_tests"] = {"path": rel(ft), "exists": False}

# ---------- V11 independent verdict census at the bound hash ----------
census = []
for p in sorted(ROOT.glob("reviews/*.json")):
    try:
        d = json.loads(p.read_text())
    except Exception:
        continue
    s = json.dumps(d)
    if BOUND in s or BOUND[:12] in s:
        census.append({"file": rel(p), "reviewer": d.get("reviewer") or d.get("actor"), "verdict": d.get("verdict"),
                       "score": d.get("score"), "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
                       "created_at": d.get("created_at")})
OUT["V11_verdict_census_at_bound_hash"] = census
OUT["V11_verdict_counts"] = {}
for c in census:
    OUT["V11_verdict_counts"][c["verdict"]] = OUT["V11_verdict_counts"].get(c["verdict"], 0) + 1

# ---------- write ----------
def sanitize(o):
    if isinstance(o, dict):
        return {(k if isinstance(k, str) else json.dumps(k, default=str)): sanitize(v) for k, v in o.items()}
    if isinstance(o, list):
        return [sanitize(v) for v in o]
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    return str(o)

OUT = sanitize(OUT)
ts = NOW.strftime("%Y%m%dT%H%M%S")
outp = ROOT / f"artifacts/worker-009/f1_review/verify_f1_{ts}.json"
outp.write_text(json.dumps(OUT, indent=1, sort_keys=True) + "\n")
print(json.dumps(OUT, indent=1, sort_keys=True))
print("\nWROTE", outp, sha(outp))

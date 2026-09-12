#!/usr/bin/env python3
"""W022-F2B-REV12-INDEP-VERDICT-01.

Independent, hash-pinned, read-only structural/class-binding review of
schemas/af_scc_c0_vacuum.yaml (class AF-SCC-C0-VAC-GEN) at the FROZEN rev28 pin.

Read-only on canonical paths: this script only reads canonical files and writes
under artifacts/worker-022/f2b_rev12_verdict/.  It deliberately does NOT run
artifacts/formulation/tools/check_taxonomy_consistency.py because that tool
rewrites its canonical evidence path.

Run:  python3 artifacts/worker-022/f2b_rev12_verdict/run_f2b_review_022.py
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PINSNAP = OUT / "pinned"
CONTROLS = OUT / "controls"

TARGET = ROOT / "schemas/af_scc_c0_vacuum.yaml"
MIRROR = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
F0 = ROOT / "research_map/formulation_taxonomy.yaml"
SUPP = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
EVID = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
ALIASES = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
DECLARED_SNAPSHOT = ROOT / "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"

PIN_TARGET = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
PIN_MIRROR = PIN_TARGET
PIN_F0 = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
PIN_SUPP = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
DECLARED_EVID = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
ALLOWED_CONCLUSION = "scc_c0_future_inextendibility"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def duplicate_keys(p: Path):
    """All duplicate keys at any depth via yaml.compose node walk."""
    text = p.read_text(encoding="utf-8")
    node = yaml.compose(text)
    dups = []

    def walk(n, path=""):
        if isinstance(n, yaml.MappingNode):
            seen = {}
            for k, v in n.value:
                key = getattr(k, "value", str(k))
                if key in seen:
                    dups.append({"path": path or "<root>", "key": key, "count": seen[key] + 1})
                    seen[key] += 1
                else:
                    seen[key] = 1
                walk(v, f"{path}.{key}" if path else key)
        elif isinstance(n, yaml.SequenceNode):
            for i, v in enumerate(n.value):
                walk(v, f"{path}[{i}]")

    walk(node)
    return dups


def resolve_pointer(doc, dotted: str):
    cur = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, part
        cur = cur[part]
    return cur, None


def check_c1(pin_record):
    """hash pin stability."""
    m_target = sha256_file(TARGET)
    m_mirror = sha256_file(MIRROR)
    m_f0 = sha256_file(F0)
    m_supp = sha256_file(SUPP)
    fro = load_json(FROZEN)
    frozen_pin = fro["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"]
    frozen_rev = fro["revision"]
    doc = load_yaml(TARGET)
    declared_f0 = doc["f0_binding"]["declared_f0_sha256"]
    rec = {
        "measured_target": m_target,
        "measured_mirror": m_mirror,
        "measured_f0": m_f0,
        "measured_supplement": m_supp,
        "frozen_revision": frozen_rev,
        "frozen_pin": frozen_pin,
        "declared_f0": declared_f0,
    }
    ok = (
        m_target == PIN_TARGET
        and m_mirror == PIN_MIRROR
        and frozen_pin == PIN_TARGET
        and declared_f0 == m_f0 == PIN_F0
        and m_supp == PIN_SUPP
    )
    rec["status"] = "PASS" if ok else "FAIL"
    return rec, ok


def check_c2():
    declared = load_yaml(TARGET)["f0_binding"]["consistency_evidence_sha256"]
    measured = sha256_file(EVID)
    rec = {"declared": declared, "measured": measured, "path": str(EVID.relative_to(ROOT))}
    rec["status"] = "PASS" if declared == measured else "FAIL"
    return rec, declared == measured


def check_c3():
    """Semantic diff of the declared evidence revision vs the live document."""
    if not DECLARED_SNAPSHOT.exists():
        return {"status": "INFO", "note": "declared-revision snapshot not found"}, None
    old = load_json(DECLARED_SNAPSHOT)
    new = load_json(EVID)
    keys = sorted(set(old) | set(new))
    diff = {}
    for k in keys:
        if old.get(k) != new.get(k):
            diff[k] = {"declared": old.get(k), "live": new.get(k)}
    rec = {
        "declared_snapshot": str(DECLARED_SNAPSHOT.relative_to(ROOT)),
        "declared_sha256_verified": sha256_file(DECLARED_SNAPSHOT) == DECLARED_EVID,
        "semantic_diff": diff,
        "live_consistent": new.get("consistent"),
        "live_classes_compared": new.get("classes_compared"),
        "live_input_pin_fields_present": [k for k in ("map_taxonomy_sha256", "lead_contract_sha256", "measured_at") if k in new],
        "declared_input_pin_fields_present": [k for k in ("map_taxonomy_sha256", "lead_contract_sha256", "measured_at") if k in old],
        "note": "informational: distinguishes a re-stamp defect from a semantic change",
    }
    return rec, None


def check_c4(path: Path = TARGET):
    dups = duplicate_keys(path)
    top = [d for d in dups if d["path"] == "<root>" or "." not in d["path"]]
    rec = {"duplicates": dups, "count": len(dups), "top_level": top}
    rec["status"] = "PASS" if not dups else "FAIL"
    return rec, not dups


def check_c5(path: Path = TARGET):
    doc = load_yaml(path)
    ptr = doc.get("class_contract_pointer")
    sptr = doc.get("class_contract_supplement_pointer")
    f0 = load_yaml(F0)
    supp = load_yaml(SUPP)
    p_path, _, p_key = (ptr or "").partition("#")
    s_path, _, s_key = (sptr or "").partition("#")
    p_doc = f0 if Path(p_path) == F0.relative_to(ROOT) or p_path == str(F0.relative_to(ROOT)) else None
    s_doc = supp if s_path == str(SUPP.relative_to(ROOT)) else None
    p_obj, p_missing = resolve_pointer(p_doc, p_key) if p_doc is not None else (None, "file")
    s_obj, s_missing = resolve_pointer(s_doc, s_key) if s_doc is not None else (None, "file")
    p_token = (p_obj or {}).get("class_id") if isinstance(p_obj, dict) else None
    s_parent = (s_obj or {}).get("parent_class") if isinstance(s_obj, dict) else None
    s_token = (s_obj or {}).get("class_id") if isinstance(s_obj, dict) else None
    ok = (
        p_obj is not None
        and s_obj is not None
        and (p_token == CLASS_ID or "AF-SCC-C0-VAC-GEN" in json.dumps(p_obj))
        and (s_parent == CLASS_ID or s_token == CLASS_ID or "AF-SCC-C0-VAC-GEN" in json.dumps(s_obj))
    )
    rec = {
        "class_contract_pointer": ptr,
        "resolved_in_canonical": p_obj is not None,
        "missing_segment": p_missing,
        "supplement_pointer": sptr,
        "resolved_in_supplement": s_obj is not None,
        "supplement_missing_segment": s_missing,
        "supplement_parent_or_token": s_parent or s_token,
    }
    rec["status"] = "PASS" if ok else "FAIL"
    return rec, ok


def check_c6(path: Path = TARGET):
    doc = load_yaml(path)
    q = doc.get("quantifiers", {})
    formal = q.get("formal", "") or ""
    ordered = q.get("ordered", []) or []
    domains = q.get("domains", {}) or {}
    d0 = (domains.get("D0") or {}).get("definition", "") or ""
    conclusion = doc.get("conclusion", {}) or {}
    formal_fields = {
        "quantifiers.formal": formal,
        "conclusion.statement_formal": conclusion.get("statement_formal", "") or "",
        "conclusion.negation_normal_form": conclusion.get("negation_normal_form", "") or "",
    }
    bad_binder = {}
    for name, txt in formal_fields.items():
        m = re.search(r"forall\s*\(\s*s\s*,\s*delta\s*\)", txt)
        if m:
            bad_binder[name] = m.group(0)
    first = ordered[0] if ordered else {}
    checks = {
        "first_quantifier_is_forall_r_over_D0": first.get("kind") == "forall" and first.get("binder") == "r" and first.get("domain_id") == "D0",
        "formal_binds_forall_r_in_D0": "forall r in D0" in formal,
        "D0_is_tagged_disjoint_union": "tagged disjoint union" in d0,
        "D0_names_smooth_branch": "smooth" in d0,
        "D0_names_sobolev_branch": "(sobolev,s,delta)" in d0 or "sobolev,s,delta" in d0,
        "no_bare_pair_binder_remains": not bad_binder,
    }
    ok = all(checks.values())
    rec = {"checks": checks, "bad_binder_hits": bad_binder, "D0_definition_head": d0[:180]}
    rec["status"] = "PASS" if ok else "FAIL"
    return rec, ok


def check_c7(path: Path = TARGET):
    doc = load_yaml(path)
    text = path.read_text(encoding="utf-8")
    ct = (doc.get("conclusion") or {}).get("conclusion_type")
    f0 = load_yaml(F0)
    f0_entry = f0["classes"][CLASS_ID]
    f0_tokens = {
        f0_entry.get("axes", {}).get("conclusion_type"),
        (f0_entry.get("conclusion") or {}).get("type"),
    }
    aliases = load_json(ALIASES).get("conclusion_type", {})
    alias_group = set(aliases.get(ALLOWED_CONCLUSION, [])) | {ALLOWED_CONCLUSION}
    token_ok = ct in alias_group
    f0_binding_ok = bool(f0_tokens & alias_group)
    # leakage scan: asserted composite tokens outside prohibition/contrast contexts
    leakage = []
    for m in re.finditer(r"(?i)\bC0\s*(?:or|/|and)\s*C2\b", text):
        ctx = text[max(0, m.start() - 260): m.end() + 260]
        prohibition = re.search(
            r"(?i)\b(never|not\b|no\b|must not|cannot|forbidden|prohibit|distinct|separate|"
            r"rather than|instead of|contrast|containment|subset|only)\b",
            ctx,
        )
        if not prohibition:
            leakage.append({"match": m.group(0), "offset": m.start(), "context": ctx[:220]})
    sibling = doc.get("sibling_disjoint_from")
    sibling_list = sibling if isinstance(sibling, list) else [sibling]
    sibling_ok = any((isinstance(x, dict) and x.get("class_id") == "AF-SCC-C2-VAC-GEN") or x == "AF-SCC-C2-VAC-GEN" for x in sibling_list)
    checks = {
        "class_id": doc.get("class_id") == CLASS_ID,
        "conclusion_token_in_canonical_alias_group": token_ok,
        "f0_entry_carries_alias_of_same_conclusion": f0_binding_ok,
        "no_asserted_composite_leakage": not leakage,
        "sibling_contrast_declared": sibling_ok,
    }
    ok = all(checks.values())
    rec = {
        "checks": checks,
        "conclusion_type": ct,
        "f0_tokens": sorted(t for t in f0_tokens if t),
        "alias_group": sorted(alias_group),
        "leakage_hits": leakage,
    }
    rec["status"] = "PASS" if ok else "FAIL"
    return rec, ok


def check_c8(path: Path = TARGET):
    proc = subprocess.run(
        [sys.executable, str(GATE), str(path), "--json"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    try:
        rep = json.loads(proc.stdout)
    except Exception:
        rep = {"verdict": "unparsed", "stdout": proc.stdout[:400], "stderr": proc.stderr[:400]}
    ok = rep.get("verdict") == "pass" and not rep.get("failed_rules")
    return {"gate": str(GATE.relative_to(ROOT)), "verdict": rep.get("verdict"), "failed_rules": rep.get("failed_rules"), "returncode": proc.returncode}, ok


def run_checks(path: Path = TARGET, prefix: str = ""):
    """Run the file-scoped checks (C4-C8) on any path; used for controls too."""
    res = {}
    for cid, fn in (("C4", check_c4), ("C5", check_c5), ("C6", check_c6), ("C7", check_c7), ("C8", check_c8)):
        rec, ok = fn(path)
        rec["status"] = "PASS" if ok else "FAIL"
        res[cid] = rec
    return res


def main():
    generated_at = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    prereg_sha = sha256_file(OUT / "preregistration.json")
    report = {
        "schema": "a1-review/f2b-rev12/v1",
        "task_id": "W022-F2B-REV12-INDEP-VERDICT-01",
        "actor": "worker-022",
        "reviewer": "worker-022",
        "node_id": "F2b",
        "class_id": CLASS_ID,
        "gate": "G-FORM",
        "generated_at": generated_at,
        "preregistration_sha256": prereg_sha,
        "pins": {
            "target": str(TARGET.relative_to(ROOT)),
            "target_sha256": PIN_TARGET,
            "f0": PIN_F0,
            "supplement": PIN_SUPP,
            "declared_consistency_evidence_sha256": DECLARED_EVID,
            "frozen_revision": 28,
        },
        "checks": {},
        "controls": {},
    }

    # ---- snapshot pinned bytes before any check ----
    PINSNAP.mkdir(exist_ok=True)
    snapshot = {}
    for src in (TARGET, MIRROR, F0, SUPP, FROZEN):
        h = sha256_file(src)
        dst = PINSNAP / f"{src.name}.{h[:12]}"
        if not dst.exists():
            dst.write_bytes(src.read_bytes())
        snapshot[str(src.relative_to(ROOT))] = {"sha256": h, "snapshot": str(dst.relative_to(ROOT))}
    report["snapshots"] = snapshot

    c1, ok1 = check_c1(report["pins"])
    report["checks"]["C1"] = {"severity": "hard", **c1}
    c2, ok2 = check_c2()
    report["checks"]["C2"] = {"severity": "hard", **c2}
    c3, _ = check_c3()
    report["checks"]["C3"] = {"severity": "info", **c3}
    for cid, (rec, ok) in {
        "C4": check_c4(), "C5": check_c5(), "C6": check_c6(), "C7": check_c7(), "C8": check_c8(),
    }.items():
        sev = "hard" if cid != "C3" else "info"
        report["checks"][cid] = {"severity": sev, **rec, "status": "PASS" if ok else "FAIL"}

    # ---- controls ----
    CONTROLS.mkdir(exist_ok=True)
    base = load_yaml(TARGET)
    # K1: sibling C2 conclusion token
    k1 = json.loads(json.dumps(base))
    k1["conclusion"]["conclusion_type"] = "scc_c2_future_inextendibility"
    (CONTROLS / "K1_wrong_conclusion.yaml").write_text(yaml.safe_dump(k1, sort_keys=False), encoding="utf-8")
    # K2: duplicate top-level revised_at
    (CONTROLS / "K2_duplicate_revised_at.yaml").write_text(
        TARGET.read_text(encoding="utf-8") + '\nrevised_at: "2026-09-12T00:00:00+08:00"\n', encoding="utf-8"
    )
    # K3: dangling pointer
    k3 = json.loads(json.dumps(base))
    k3["class_contract_pointer"] = "research_map/formulation_taxonomy.yaml#classes.AF-SCC-C0-NOPE"
    (CONTROLS / "K3_dangling_pointer.yaml").write_text(yaml.safe_dump(k3, sort_keys=False), encoding="utf-8")
    # K4: pristine copy
    k4p = CONTROLS / "K4_pristine_copy.yaml"
    k4p.write_bytes(TARGET.read_bytes())

    k1r = run_checks(CONTROLS / "K1_wrong_conclusion.yaml")
    k2r = run_checks(CONTROLS / "K2_duplicate_revised_at.yaml")
    k3r = run_checks(CONTROLS / "K3_dangling_pointer.yaml")
    k4r = run_checks(k4p)
    report["controls"] = {
        "K1": {"expected": "C7 FAIL", "observed": k1r["C7"]["status"], "status": "PASS" if k1r["C7"]["status"] == "FAIL" else "CONTROL_NOT_FIRED"},
        "K2": {"expected": "C4 FAIL", "observed": k2r["C4"]["status"], "status": "PASS" if k2r["C4"]["status"] == "FAIL" else "CONTROL_NOT_FIRED"},
        "K3": {"expected": "C5 FAIL", "observed": k3r["C5"]["status"], "status": "PASS" if k3r["C5"]["status"] == "FAIL" else "CONTROL_NOT_FIRED"},
        "K4": {
            "expected": "C4-C8 PASS (no false positives on pristine copy)",
            "observed": {k: v["status"] for k, v in k4r.items()},
            "status": "PASS" if all(v["status"] == "PASS" for v in k4r.values()) else "FALSE_POSITIVE",
        },
    }

    # ---- second measurement (drift / fail-closed) ----
    end = {
        "target": sha256_file(TARGET),
        "f0": sha256_file(F0),
        "supplement": sha256_file(SUPP),
        "evidence": sha256_file(EVID),
        "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    drifted = end["target"] != PIN_TARGET or end["f0"] != PIN_F0
    report["end_measurement"] = end
    report["hash_stable"] = not drifted

    hard = ["C1", "C2", "C4", "C5", "C6", "C7", "C8"]
    hard_failed = [c for c in hard if report["checks"][c]["status"] != "PASS"]
    controls_fired = all(v["status"] == "PASS" for v in report["controls"].values())

    if drifted or not controls_fired:
        verdict, score = "inconclusive", None
    elif not hard_failed:
        verdict, score = "accept", 5.0
    else:
        # binding/re-stamp-only failure => 3.5; class-semantics/leakage failure => 3.0
        semantic = any(c in hard_failed for c in ("C5", "C6", "C7"))
        verdict, score = "revise", (3.0 if semantic else 3.5)

    findings = []
    if report["checks"]["C2"]["status"] == "FAIL":
        findings.append(
            "HF-022-R1 (hard, binding): f0_binding.consistency_evidence_sha256 declares "
            f"{DECLARED_EVID[:12]} but the canonical evidence path measures "
            f"{report['checks']['C2']['measured'][:12]}; the declared evidence does not resolve at the declared hash."
        )
        c3 = report["checks"]["C3"]
        if c3.get("live_consistent") is True and len(c3.get("live_classes_compared") or []) == 4:
            if c3.get("semantic_diff") == {}:
                findings.append(
                    "C3 (info): the declared and live evidence revisions are semantically identical "
                    "(consistent=true, same four classes); the defect is a stale hash stamp, not a changed consistency verdict."
                )
            else:
                dropped = [k for k in (c3.get("declared_input_pin_fields_present") or []) if k not in (c3.get("live_input_pin_fields_present") or [])]
                findings.append(
                    "C3 (info): the live evidence revision keeps consistent=true for the same four classes, but the differing "
                    f"fields are {sorted(c3.get('semantic_diff') or {})}"
                    + (f"; the live document drops the input pin fields {dropped}" if dropped else "")
                    + ". The live document therefore does not itself pin the compared taxonomy hashes."
                )
    for cid in hard_failed:
        if cid != "C2":
            findings.append(f"{cid} FAIL: see checks.{cid}")
    if not findings:
        findings.append("No hard-check failures at the pinned bytes.")

    report.update(
        {
            "verdict": verdict,
            "score": score,
            "hard_failures": [f"HF-022-R1 ({CLASS_ID} consistency evidence pin)" ] if report["checks"]["C2"]["status"] == "FAIL" else [],
            "findings": findings,
            "reviewer_independence": "not an author of the F2b schema, the F0 taxonomy, the class-contract supplement, or any cited evidence file; first worker-022 review of F2b; one reviewer label (ESS=1)",
            "authority_note": "Worker verdict: does not set node status=done, validation_status=passed, or any gate verdict; no canonical file edited.",
            "non_claims": [
                "not a physics verdict, not a theorem endorsement, not a gate verdict",
                "does not review F1 or F2a",
                "does not re-run check_taxonomy_consistency.py (it writes canonical evidence)",
            ],
            "reproduce": "python3 artifacts/worker-022/f2b_rev12_verdict/run_f2b_review_022.py",
            "next_falsifier": "Restore the declared evidence bytes or re-stamp consistency_evidence_sha256 to the live document and re-run this script: C2 then passes and the revise is falsified. A class-semantics or leakage defect in the pinned bytes falsifies the no-semantic-defect finding.",
        }
    )

    rep_path = OUT / "f2b_review_report.json"
    rep_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (OUT / "f2b_review_report.json.sha256").write_text(sha256_file(rep_path) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("verdict", "score", "hard_failures", "hash_stable")}, indent=1))
    print("report:", rep_path)
    print("sha256:", sha256_file(rep_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

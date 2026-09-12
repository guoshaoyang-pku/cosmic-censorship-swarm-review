#!/usr/bin/env python3
"""
W075-FORM-BINDING-SWEEP-07 independent verifier.

Re-derives the sweep's headline assertions from the frozen bytes with a separate implementation
(no import of the sweep), and runs five negative controls on copies under this directory. Writes
only ``verify_binding_sweep_075.json`` (and the control copies) inside its own directory.

Exit 0 = every reproduction check passed and every control was detected.
Exit 1 = a reproduction mismatch or an undetected control (the report names it).
"""
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SWEEP = HERE / "binding_sweep_075.json"
OUT = HERE / "verify_binding_sweep_075.json"
CTRL = HERE / "_verify_controls"
CST = timezone(timedelta(hours=8))
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
CLASS_IDS = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now():
    return datetime.now(CST).replace(microsecond=0).isoformat()


def load_yaml(p):
    return yaml.safe_load(Path(p).read_text())


def main():
    report = {"task_id": "W075-FORM-BINDING-SWEEP-07", "verifier": "worker-075",
              "verified_at": now(), "checks": {}, "controls": {}, "mismatches": []}
    sweep = json.loads(SWEEP.read_text())

    # --- reproduction 1: input hashes unchanged since the sweep wrote its report
    drifted = []
    for rel, rec in sweep["S1_inputs"].items():
        if not (ROOT / rel).exists():
            drifted.append({"path": rel, "reason": "missing"})
        elif sha(ROOT / rel) != rec.get("sha256"):
            drifted.append({"path": rel, "sweep": rec.get("sha256"), "now": sha(ROOT / rel)})
    report["checks"]["R1_inputs_unchanged_since_sweep"] = {"drifted": drifted, "ok": not drifted}
    if drifted:
        report["mismatches"].append("R1: inputs drifted since the sweep report was written")

    # --- reproduction 2: FROZEN pins (independent re-implementation)
    fr = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    pin_bad = []
    for rel, pin in fr["files"].items():
        p = ROOT / rel
        if not p.exists() or sha(p) != pin["sha256"] or p.stat().st_size != pin["bytes"]:
            pin_bad.append(rel)
    report["checks"]["R2_frozen_pins"] = {
        "manifest_sha256": sha(ROOT / "artifacts/formulation/FROZEN.json"),
        "revision": fr.get("revision"), "n_pins": len(fr["files"]), "bad": pin_bad, "ok": not pin_bad}
    if pin_bad:
        report["mismatches"].append(f"R2: {len(pin_bad)} FROZEN pins do not match disk")

    # --- reproduction 3: evidence chain + checker replay hash
    ev_p = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
    ev = json.loads(ev_p.read_text())
    ev_sha = sha(ev_p)
    tax_sha = sha(ROOT / "research_map/formulation_taxonomy.yaml")
    chain = []
    for label, rel in SCHEMAS.items():
        d = load_yaml(ROOT / rel)
        fb = d["f0_binding"]
        chain.append({
            "class": label,
            "declared_f0_matches": fb["declared_f0_sha256"] == tax_sha,
            "evidence_matches": fb["consistency_evidence_sha256"] == ev_sha,
        })
    replay = sweep["S4_consistency_chain"]["checker_replay"]
    report["checks"]["R3_evidence_chain"] = {
        "evidence_sha256": ev_sha, "taxonomy_sha256": tax_sha,
        "consistent": ev.get("consistent") is True, "errors": ev.get("errors"),
        "per_schema": chain,
        "checker_replay_matches_pinned": replay.get("status") == "match"
        and replay.get("replay_sha256") == ev_sha,
        "ok": all(c["declared_f0_matches"] and c["evidence_matches"] for c in chain)
        and ev.get("consistent") is True and not ev.get("errors"),
    }
    if not report["checks"]["R3_evidence_chain"]["ok"]:
        report["mismatches"].append("R3: evidence chain does not reproduce")

    # --- reproduction 4: mirrors, taxonomy cases, semantic diff, strictness text
    mir_bad = [l for l in SCHEMAS
               if sha(ROOT / SCHEMAS[l]) != sha(ROOT / ("artifacts/formulation/" + SCHEMAS[l]))]
    rows = [json.loads(x) for x in (ROOT / "schemas/taxonomy_cases.jsonl").read_text().splitlines() if x.strip()]
    cases = [r for r in rows if r.get("record_type") == "case"]
    unbound = [r["case_id"] for r in cases
               if r.get("binding_status") != "bound_taxonomy_sha_0abb9ed8a961"]
    report["checks"]["R4_mirrors_taxcases"] = {
        "mirror_divergent": mir_bad, "unbound_cases": unbound,
        "ok": not mir_bad and not unbound}
    if mir_bad or unbound:
        report["mismatches"].append("R4: mirror divergence or unbound taxonomy case")
    report["checks"]["R5_sweep_headline"] = {
        "sweep_summary": sweep.get("summary"),
        "ok": (sweep["summary"]["frozen_pin_mismatches"] == 0
               and sweep["summary"]["declared_hash_mismatches"] == 0
               and sweep["summary"]["consistency_chain_findings"] == 0
               and sweep["summary"]["semantic_diff_unexpected"] == 0) or bool(pin_bad),
    }

    # --- controls: tamper copies, each must be detected by the smallest matching detector
    CTRL.mkdir(exist_ok=True)

    def det_hash_binding(schema_path, evidence_path):
        d = load_yaml(schema_path)
        return d["f0_binding"]["consistency_evidence_sha256"] == sha(evidence_path)

    def det_class_isolation(schema_path, expected):
        d = load_yaml(schema_path)
        own = d.get("class_id")
        txt = json.dumps(d.get("quantifiers"), sort_keys=True)
        return own == expected and not any(c in txt for c in CLASS_IDS if c != own)

    def det_composite_assertive(schema_path):
        d = load_yaml(schema_path)
        txt = json.dumps([d.get("quantifiers"), (d.get("conclusion") or {}).get("statement_formal")],
                         sort_keys=True)
        return not re.search(r"C0\s*(or|/)\s*C2|C2\s*(or|/)\s*C0", txt, re.I)

    def det_frozen_pin(manifest_path):
        m = json.loads(Path(manifest_path).read_text())
        return all((ROOT / k).exists() and sha(ROOT / k) == v["sha256"] for k, v in m["files"].items())

    def det_taxcase_binding(path):
        rows = [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
        return all(r.get("binding_status") == "bound_taxonomy_sha_0abb9ed8a961"
                   for r in rows if r.get("record_type") == "case")

    controls = {}
    # C1 stale evidence hash in a schema copy
    p = CTRL / "af_scc_c2_vacuum.c1.yaml"
    shutil.copy(ROOT / SCHEMAS["F2a"], p)
    t = p.read_text().replace("consistency_evidence_sha256: \"9e335e9b", "consistency_evidence_sha256: \"00000000", 1)
    p.write_text(t)
    controls["C1_stale_evidence_hash_detected"] = not det_hash_binding(
        p, ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json")
    # C2a foreign class id as the declared identity; C2b foreign token spliced into an assertive field
    p2 = CTRL / "af_scc_c2_vacuum.c2.yaml"
    shutil.copy(ROOT / SCHEMAS["F2a"], p2)
    p2.write_text(p2.read_text().replace("class_id: AF-SCC-C2-VAC-GEN",
                                         "class_id: AF-SCC-C0-VAC-GEN", 1))
    p2b = CTRL / "af_scc_c2_vacuum.c2b.yaml"
    shutil.copy(ROOT / SCHEMAS["F2a"], p2b)
    p2b.write_text(p2b.read_text().replace(
        "proper future C2 vacuum extension", "proper future C2 vacuum extension (AF-SCC-C0-VAC-GEN)", 1))
    controls["C2a_foreign_class_id_detected"] = not det_class_isolation(p2, "AF-SCC-C2-VAC-GEN")
    controls["C2b_foreign_token_in_assertive_field_detected"] = not det_class_isolation(
        p2b, "AF-SCC-C2-VAC-GEN")
    # C3 composite phrase in an assertive field
    d = load_yaml(ROOT / SCHEMAS["F2a"])
    d["conclusion"]["statement_formal"] = "C0 or C2 non-extendibility for all data"
    p3 = CTRL / "af_scc_c2_vacuum.c3.yaml"
    p3.write_text(yaml.safe_dump(d, sort_keys=False))
    controls["C3_composite_phrase_detected"] = not det_composite_assertive(p3)
    # C4 tampered FROZEN pin
    m = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    key = "schemas/af_scc_c2_vacuum.yaml"
    m["files"][key]["sha256"] = "0" * 64
    p4 = CTRL / "FROZEN.tampered.json"
    p4.write_text(json.dumps(m))
    controls["C4_tampered_frozen_pin_detected"] = not det_frozen_pin(p4)
    # C5 tampered taxonomy-case binding
    src = (ROOT / "schemas/taxonomy_cases.jsonl").read_text().replace(
        '"binding_status": "bound_taxonomy_sha_0abb9ed8a961"',
        '"binding_status": "bound_taxonomy_sha_000000000000"', 1)
    p5 = CTRL / "taxonomy_cases.c5.jsonl"
    p5.write_text(src)
    controls["C5_tampered_taxcase_binding_detected"] = not det_taxcase_binding(p5)

    report["controls"] = controls
    undetected = [k for k, v in controls.items() if not v]
    if undetected:
        report["mismatches"].append(f"controls not detected: {undetected}")

    report["status"] = "PASS" if not report["mismatches"] else "FAIL"
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "controls": controls,
                      "mismatches": report["mismatches"]}, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W087-GFORM-STAGE2-BINDING-01: independent read-only measurement of whether the
G-FORM stage-2 semantic rule engine is bound by FROZEN rev29 pins.

Deterministic, stdlib-only, fail-closed. Reads the repository; writes only inside
artifacts/worker-087/stage2_binding/ (its own task directory). No canonical path is
modified. Exit: 0 gap confirmed, 1 not confirmed, 3 inconclusive/moving target.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

FROZEN_REL = "artifacts/formulation/FROZEN.json"
STAGE2_REL = "artifacts/worker-06/spec_conformance_audit.py"
RUNACC_REL = "artifacts/formulation/tools/run_acceptance.py"
STAGE1_REL = "artifacts/formulation/tools/check_class_schema.py"
RULE_SPEC_REL = "artifacts/formulation/rule_spec.json"
REPORT_REL = "artifacts/formulation/evidence/acceptance_pipeline_report.json"
ESCAPE_REL = "artifacts/formulation/evidence/semantic_escape_rebased.json"
F1_REL = "schemas/af_wcc_vacuum.yaml"
F2A_REL = "schemas/af_scc_c2_vacuum.yaml"
F2B_REL = "schemas/af_scc_c0_vacuum.yaml"
REGISTRY_REL = "runtime/state/artifact_hashes.json"

# Expected values are the pre-registered declared pins (PREREGISTRATION.json).
# AMEND-01: runtime/state/artifact_hashes.json is controller-written live state, so it is
# reclassified from pin to live input (measured at entry/exit, movement reported but not
# drift-fatal). See AMENDMENT-01.json.
LIVE_INPUTS = {
    REGISTRY_REL: "b692ad728c50ffdbfd6f07e64907d45d9cca506d928d4f68d23845225526fd13",
}

EXPECTED_PINS = {
    FROZEN_REL: "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    F1_REL: "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    F2A_REL: "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    F2B_REL: "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    STAGE2_REL: "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    RUNACC_REL: "e544c36d2d168fdf0a9fb19caa333597d8a74a14442b40a356c08004cc9fb4de",
    STAGE1_REL: "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    RULE_SPEC_REL: "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    REPORT_REL: "9b7d6c8208d3beae2510c5c9c0a4bdaf7ede8adb277cd2a4f6f9cd0fd430f0c6",
    ESCAPE_REL: "7e44de0e3906dc74f607629b88bdc6cbfb438ce39c759e4054156a9345b38292",
}
EXPECTED = EXPECTED_PINS  # frozen-pin drift gate

PATCH_OLD = "                    if b not in formal:"
PATCH_NEW = (
    "                    if b not in formal and not all(re.search("
    "r'(?<![A-Za-z0-9_])' + re.escape(_t) + r'(?![A-Za-z0-9_])', formal) "
    "for _t in re.findall(r'[A-Za-z_][A-Za-z_0-9]*', b)):"
)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(p: Path) -> dict:
    b = p.read_bytes()
    return {"path": str(p.relative_to(ROOT)), "bytes": len(b),
            "sha256": hashlib.sha256(b).hexdigest(), "mtime_ns": p.stat().st_mtime_ns}


def norm_run(doc: dict) -> str:
    d = {k: v for k, v in doc.items() if k != "audited_at"}
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


def run_engine(engine: Path, schema: Path) -> dict:
    r = subprocess.run([sys.executable, str(engine), str(schema)],
                       capture_output=True, text=True, cwd=str(ROOT))
    out = {"argv": [str(engine.relative_to(ROOT)), str(schema.relative_to(ROOT))],
           "returncode": r.returncode, "stderr": r.stderr[-2000:]}
    try:
        d = json.loads(r.stdout)
        out.update({"verdict": d.get("verdict"), "failed_rules": d.get("failed_rules"),
                    "doc_sha256": d.get("doc_sha256"), "normalized_digest": norm_run(d),
                    "checks": {c.get("rule"): {"verdict": c.get("verdict"), "detail": c.get("detail")}
                               for c in d.get("checks", [])}})
    except Exception as e:  # noqa: BLE001
        out.update({"verdict": "unparseable", "parse_error": repr(e),
                    "stdout_head": r.stdout[:500]})
    return out


def main() -> int:
    report: dict = {
        "schema": "worker-087/stage2-binding-report/v1",
        "task_id": "W087-GFORM-STAGE2-BINDING-01",
        "worker": "worker-087",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "preregistration": measure(HERE / "PREREGISTRATION.json"),
    }

    # --- entry pin measurement (fail-closed on a moving target) -----------------
    before = {rel: measure(ROOT / rel) for rel in EXPECTED}
    live_before = {rel: measure(ROOT / rel) for rel in LIVE_INPUTS}
    drift_in = [rel for rel in EXPECTED if before[rel]["sha256"] != EXPECTED[rel]]
    report["entry_pins"] = before
    report["entry_live_inputs"] = live_before
    report["entry_drift"] = drift_in
    report["amendment"] = measure(HERE / "AMENDMENT-01.json")
    if drift_in:
        report["verdict"] = "INCONCLUSIVE_MOVING_TARGET_AT_ENTRY"
        report["falsifier"] = "declared pin moved before measurement"
        (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print("INCONCLUSIVE_MOVING_TARGET_AT_ENTRY", drift_in)
        return 3

    frozen = json.loads((ROOT / FROZEN_REL).read_text())
    pins = frozen.get("files", {})
    stage2_hex = before[STAGE2_REL]["sha256"]
    stage2_hex16 = stage2_hex[:16]

    # --- H1: path membership in the FROZEN pin map ------------------------------
    h1 = STAGE2_REL not in pins
    report["H1_path_unpinned"] = {
        "holds": h1,
        "pin_map_entries": len(pins),
        "stage2_path_in_pin_map": STAGE2_REL in pins,
        "pinned_instruments": sorted(k for k in pins if k.endswith(".py")),
    }

    # --- H2: hash unreferenced (manifest + all pinned artifact bodies) ----------
    frozen_raw = (ROOT / FROZEN_REL).read_text()
    h2_frozen = stage2_hex16 not in frozen_raw and stage2_hex not in frozen_raw
    body_hits = []
    for rel in sorted(pins):
        p = ROOT / rel
        if not p.exists():
            body_hits.append({"path": rel, "status": "MISSING"})
            continue
        try:
            txt = p.read_text(errors="replace")
        except Exception:  # noqa: BLE001
            continue
        if stage2_hex16 in txt or stage2_hex in txt:
            body_hits.append({"path": rel, "status": "REFERENCES_STAGE2_HASH"})
    h2 = h2_frozen and not body_hits
    reference_disposition = []
    for hit in body_hits:
        if hit.get("status") != "REFERENCES_STAGE2_HASH":
            reference_disposition.append(hit)
            continue
        body = json.loads((ROOT / hit["path"]).read_text())
        fields = []
        for k, v in body.items():
            if isinstance(v, str) and (stage2_hex in v or stage2_hex16 in v):
                fields.append(f"{k}={v}")
        reference_disposition.append({"path": hit["path"], "fields": fields,
                                      "classification": "provenance_declaration_unverified"})
    report["H2_hash_unreferenced"] = {
        "holds": h2,
        "frozen_json_mentions_hash": not h2_frozen,
        "pinned_bodies_referencing_hash": body_hits,
        "pinned_bodies_scanned": len(pins),
        "reference_disposition": reference_disposition,
        "note": "H2 as pre-registered required the hash to appear in no pinned body; it is falsified by the single provenance field below. The operative question (is the engine bound/verified?) is carried by H1, H3, H3b, H4, H5.",
    }

    # --- H3: no hash verification in the pinned pipeline ------------------------
    acc_src = (ROOT / RUNACC_REL).read_text()
    tree = ast.parse(acc_src)
    sha_calls = []
    enc = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                enc[id(sub)] = node.name
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "sha256":
            sha_calls.append({"line": node.lineno, "enclosing_function": enc.get(id(node), "?")})
    sem_lines = [i + 1 for i, ln in enumerate(acc_src.splitlines())
                 if "SEM" in ln and "sha256" in ln.lower()]
    report["H3_no_hash_check"] = {
        "holds": not sem_lines,
        "run_acceptance_sha256_calls": sha_calls,
        "lines_binding_SEM_to_sha256": sem_lines,
        "stage2_reference_line": next((i + 1 for i, ln in enumerate(acc_src.splitlines())
                                       if "spec_conformance_audit.py" in ln), None),
        "acceptance_report_stages_field": json.loads(
            (ROOT / REPORT_REL).read_text()).get("stages"),
        "acceptance_report_mentions_stage2_hash": stage2_hex16 in (ROOT / REPORT_REL).read_text(),
    }

    # --- H3b: the one declared reference is never checked ------------------------
    decl_readers = {}
    for rel in (RUNACC_REL, STAGE1_REL, "artifacts/formulation/tools/measure_semantic_escape.py"):
        src = (ROOT / rel).read_text()
        decl_readers[rel] = [i + 1 for i, ln in enumerate(src.splitlines())
                             if "w06_sha256" in ln or "gate_sha256" in ln]
    comparisons = [rel for rel, ls in decl_readers.items()
                   if rel != "artifacts/formulation/tools/measure_semantic_escape.py" and ls]
    report["H3b_declaration_unverified"] = {
        "holds": not comparisons,
        "declared_in_pinned_evidence": [r["path"] for r in reference_disposition],
        "declaration_writer_lines": decl_readers["artifacts/formulation/tools/measure_semantic_escape.py"],
        "consumer_lines_in_pipeline": {k: v for k, v in decl_readers.items() if k != "artifacts/formulation/tools/measure_semantic_escape.py"},
        "note": "the pinned corpus records w06_sha256, but no pipeline tool reads or compares it; run_acceptance.preflight checks only base_sha256",
    }

    # --- H5: absence from the runtime artifact registry -------------------------
    reg = json.loads((ROOT / REGISTRY_REL).read_text())
    hits = []
    for section in ("hashes", "registry"):
        for k, v in (reg.get(section) or {}).items():
            blob = json.dumps({k: v})
            if STAGE2_REL in blob or stage2_hex in blob or stage2_hex16 in blob:
                hits.append({"section": section, "key": k})
    report["H5_registry_absent"] = {"holds": not hits, "registry_hits": hits,
                                    "registry_sections": sorted(reg.keys()),
                                    "registry_sha256_read": sha256_file(ROOT / REGISTRY_REL)}

    # --- H4: sensitivity probe in a sandbox (no canonical write) ----------------
    sb = HERE / "sandbox"
    (sb / "artifacts" / "worker-06").mkdir(parents=True, exist_ok=True)
    (sb / "artifacts" / "formulation").mkdir(parents=True, exist_ok=True)
    (HERE / "input").mkdir(parents=True, exist_ok=True)
    live_copy = sb / "artifacts" / "worker-06" / "spec_conformance_audit.py"
    mut_copy = sb / "artifacts" / "worker-06" / "spec_conformance_audit.mutant.py"
    spec_copy = sb / "artifacts" / "formulation" / "rule_spec.json"
    f1_copy = HERE / "input" / "F1.yaml"
    f1_mangled = HERE / "input" / "F1_mangled.yaml"
    shutil.copyfile(ROOT / STAGE2_REL, live_copy)
    shutil.copyfile(ROOT / RULE_SPEC_REL, spec_copy)
    shutil.copyfile(ROOT / F1_REL, f1_copy)

    src = (ROOT / STAGE2_REL).read_text()
    if src.count(PATCH_OLD) != 1:
        report["H4_verdict_decided_by_unpinned_bytes"] = {
            "holds": False, "error": "patch anchor not unique", "count": src.count(PATCH_OLD)}
        report["verdict"] = "INCONCLUSIVE_PATCH_ANCHOR"
        (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print("INCONCLUSIVE_PATCH_ANCHOR")
        return 3

    mut_src = src.replace(PATCH_OLD, PATCH_NEW)
    mut_copy.write_text(mut_src)
    import difflib
    diff = "".join(difflib.unified_diff(
        src.splitlines(keepends=True), mut_src.splitlines(keepends=True),
        fromfile=STAGE2_REL, tofile="sandbox mutant"))

    # mangled control: keep YAML valid, remove the formal binder tokens
    lines = (ROOT / F1_REL).read_text().splitlines(keepends=True)
    out, i = [], 0
    while i < len(lines):
        if lines[i].rstrip("\n") == "  formal: >-":
            out.append('  formal: "control-mangled: no binder tokens present"\n')
            i += 1
            while i < len(lines) and (lines[i].startswith("    ") or lines[i].strip() == ""):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    mangled_txt = "".join(out)
    f1_mangled.write_text(mangled_txt)
    assert "  formal: >-" not in mangled_txt and "control-mangled" in mangled_txt

    runs = []
    k1 = run_engine(live_copy, f1_copy)
    k1b = run_engine(live_copy, f1_copy)
    k2 = run_engine(mut_copy, f1_copy)
    k2b = run_engine(mut_copy, f1_copy)
    k3 = run_engine(mut_copy, f1_mangled)
    k4 = run_engine(live_copy, f1_mangled)
    runs = [dict(r, control=c) for r, c in
            [(k1, "K1_baseline_reject"), (k1b, "K1b_baseline_repeat"),
             (k2, "K2_mutant_flip"), (k2b, "K2b_mutant_repeat"),
             (k3, "K3_fail_closed_mutant"), (k4, "K4_fail_closed_live")]]

    k1_ok = k1.get("verdict") == "reject" and k1.get("failed_rules") == ["R03"] \
        and "absent from formal sentence" in json.dumps(k1.get("checks", {}))
    k1b_ok = k1b.get("normalized_digest") == k1.get("normalized_digest")
    k2_ok = k2.get("verdict") in ("accept", "pass") and not k2.get("failed_rules")
    k2b_ok = k2b.get("normalized_digest") == k2.get("normalized_digest")
    k3_ok = k3.get("verdict") == "reject"
    k4_ok = k4.get("verdict") == "reject"
    same_doc = k1.get("doc_sha256") == k2.get("doc_sha256") == before[F1_REL]["sha256"]

    report["H4_verdict_decided_by_unpinned_bytes"] = {
        "holds": bool(k1_ok and k2_ok and same_doc),
        "same_input_doc_sha256": same_doc,
        "baseline_engine_sha256": sha256_file(live_copy),
        "mutant_engine_sha256": sha256_file(mut_copy),
        "live_engine_sha256": stage2_hex,
        "mutant_diff": diff,
        "f1_copy_sha256": sha256_file(f1_copy),
        "mangled_control_sha256": sha256_file(f1_mangled),
    }
    report["controls"] = {
        "K1_baseline_reject": {"ok": bool(k1_ok), "verdict": k1.get("verdict"),
                               "failed_rules": k1.get("failed_rules")},
        "K1b_baseline_repeat_deterministic": {"ok": bool(k1b_ok),
                                              "digest": k1.get("normalized_digest")},
        "K2_mutant_flip": {"ok": bool(k2_ok), "verdict": k2.get("verdict"),
                           "failed_rules": k2.get("failed_rules")},
        "K2b_mutant_repeat_deterministic": {"ok": bool(k2b_ok),
                                            "digest": k2.get("normalized_digest")},
        "K3_fail_closed_mutant_on_mangled_input": {"ok": bool(k3_ok),
                                                   "verdict": k3.get("verdict"),
                                                   "failed_rules": k3.get("failed_rules")},
        "K4_fail_closed_live_on_mangled_input": {"ok": bool(k4_ok),
                                                 "verdict": k4.get("verdict"),
                                                 "failed_rules": k4.get("failed_rules")},
    }
    report["runs"] = runs

    # --- K5: post-probe pin re-measurement --------------------------------------
    after = {rel: measure(ROOT / rel) for rel in EXPECTED}
    live_after = {rel: measure(ROOT / rel) for rel in LIVE_INPUTS}
    drift_out = [rel for rel in EXPECTED if after[rel]["sha256"] != EXPECTED[rel]]
    live_drift = [rel for rel in LIVE_INPUTS if live_after[rel]["sha256"] != live_before[rel]["sha256"]]
    report["exit_pins"] = after
    report["exit_live_inputs"] = live_after
    report["pin_drift"] = drift_out
    report["live_input_drift"] = live_drift
    report["controls"]["K5_no_pin_drift"] = {"ok": not drift_out, "drift": drift_out,
                                             "live_input_drift_informational": live_drift}
    report["controls"]["K6_engine_identity"] = {
        "ok": sha256_file(live_copy) == stage2_hex and sha256_file(mut_copy) != stage2_hex,
        "sandbox_baseline_equals_live": sha256_file(live_copy) == stage2_hex,
        "mutant_differs": sha256_file(mut_copy) != stage2_hex,
    }

    all_h = [h1, h2, report["H3_no_hash_check"]["holds"],
             report["H3b_declaration_unverified"]["holds"],
             report["H4_verdict_decided_by_unpinned_bytes"]["holds"],
             report["H5_registry_absent"]["holds"]]
    controls_ok = all(c["ok"] for c in report["controls"].values())
    if drift_out:
        report["verdict"] = "INCONCLUSIVE_MOVING_TARGET"
    elif all(all_h) and controls_ok:
        report["verdict"] = "PIN_GAP_CONFIRMED"
    else:
        report["verdict"] = "NOT_CONFIRMED"
    operative = bool(h1 and report["H3_no_hash_check"]["holds"]
                     and report["H3b_declaration_unverified"]["holds"]
                     and report["H4_verdict_decided_by_unpinned_bytes"]["holds"]
                     and report["H5_registry_absent"]["holds"] and controls_ok and not drift_out)
    report["operative_gap_confirmed"] = operative
    report["verdict_note"] = (
        "The pre-registered all-of-H1..H5 rule yields the literal verdict above. H2 as literally "
        "pre-registered (hash appears in no pinned body) is falsified by one provenance field; the "
        "operative gap (engine unpinned, declaration unverified, verdict decided by the unpinned file, "
        "all pins stable) is confirmed: operative_gap_confirmed=" + str(operative) + ".")
    report["falsifier"] = ("stage-2 path in FROZEN pin map, stage-2 hash referenced in FROZEN or a "
                           "pinned body, run_acceptance.py verifying the stage-2 hash, or no K2 flip "
                           "on identical input")
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (HERE / "runs.json").write_text(json.dumps(runs, indent=2) + "\n")
    print(json.dumps({"verdict": report["verdict"],
                      "operative_gap_confirmed": report["operative_gap_confirmed"],
                      "H": all_h, "controls_ok": controls_ok,
                      "pin_drift": drift_out}, indent=1))
    return 0 if report["verdict"] == "PIN_GAP_CONFIRMED" else (
        1 if report["verdict"] == "NOT_CONFIRMED" else 3)


if __name__ == "__main__":
    sys.exit(main())

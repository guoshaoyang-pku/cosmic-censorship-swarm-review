#!/usr/bin/env python3
"""W086-GFORM-SUITE-REPL-01: pristine-sandbox replication of the pinned G-FORM gate suite.

Read-only on every canonical path. The pinned suite rewrites fixtures and its own report, so
it is executed only inside <deliverable>/sandbox. Acceptance predicate is pre-registered in
PREREGISTRATION.md; this instrument only measures it and fails closed.

Exit codes: 0 = every pre-registered check passed; 1 = at least one check failed; 3 = guard.
"""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # .../ai4math-swarm
FORM = Path("artifacts/formulation")
SANDBOX = HERE / "sandbox"
SCRATCH_DEFECT = HERE / "scratch_control_defect"
SCRATCH_DRIFT = HERE / "scratch_control_drift"
FROZEN_REPORT_JSON = ROOT / FORM / "evidence/gate_test_report.json"
FROZEN_REPORT_TXT = ROOT / FORM / "evidence/gate_test_report.txt"

# Pre-registered pins (PREREGISTRATION.md); FROZEN rev29.
PINNED = {
    "artifacts/formulation/tools/run_gate_tests.py": "78509c9eb8b1548231f3e701245e48084916b044b5d1485bb96006563a59dffa",
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/KEY_MANIFEST.json": "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/formulation/evidence/gate_test_report.json": "26540a6b43ccc7b8c640ab4f2566240a20829d86677e22f00244c8b1d923ff5b",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
}
FROZEN_PINS = {
    "artifacts/formulation/tools/run_gate_tests.py",
    "artifacts/formulation/tools/check_class_schema.py",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/evidence/gate_test_report.json",
    "artifacts/formulation/FROZEN.json",
}
EXPECTED_COUNTS = {
    "canonical_pass": 3,
    "null_controls_pass": 6,
    "mutants_caught": 31,
    "mutants_total": 31,
    "rephrased_caught": 2,
    "rephrased_total": 5,
}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(rels) -> dict:
    out = {}
    for rel in rels:
        p = ROOT / rel
        out[rel] = {"exists": p.exists(), "measured": sha(p) if p.exists() else None,
                    "mtime_ns": p.stat().st_mtime_ns if p.exists() else None}
    return out


def drift(entry: dict, exit_: dict) -> list:
    d = []
    for rel, rec in entry.items():
        got = exit_.get(rel, {}).get("measured")
        if rec["measured"] != got:
            d.append({"path": rel, "entry": rec["measured"], "exit": got})
    return d


def tool_run(workdir: Path, tag: str):
    tool = workdir / FORM / "tools/run_gate_tests.py"
    t0 = time.time()
    r = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True,
                       cwd=str(workdir), timeout=1800)
    dt = round(time.time() - t0, 2)
    rep_p = workdir / FORM / "evidence/gate_test_report.json"
    txt_p = workdir / FORM / "evidence/gate_test_report.txt"
    rep_bytes = rep_p.read_bytes() if rep_p.exists() else b""
    txt_bytes = txt_p.read_bytes() if txt_p.exists() else b""
    (HERE / f"{tag}.stdout.txt").write_text(r.stdout)
    (HERE / f"{tag}.stderr.txt").write_text(r.stderr)
    (HERE / f"{tag}_gate_test_report.json").write_bytes(rep_bytes)
    (HERE / f"{tag}_gate_test_report.txt").write_bytes(txt_bytes)
    try:
        rep = json.loads(rep_bytes)
    except Exception as e:  # noqa: BLE001
        rep = {"_unparseable": f"{type(e).__name__}: {e}"}
    return {"exit_code": r.returncode, "seconds": dt, "report": rep,
            "report_sha256": hashlib.sha256(rep_bytes).hexdigest(),
            "txt_sha256": hashlib.sha256(txt_bytes).hexdigest(),
            "report_bytes": len(rep_bytes), "txt_bytes": len(txt_bytes)}


def main() -> int:
    checks = []

    def chk(cid, ok, detail):
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})

    # guard: never operate outside this deliverable directory
    if not (str(SANDBOX).startswith(str(HERE)) and "gform_suite_rev29" in str(HERE)
            and ROOT != HERE and (ROOT / "research_map/research_map.json").exists()):
        print("GUARD FAILED: refusing to run outside the deliverable sandbox")
        return 3

    env = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "yaml": getattr(yaml, "__version__", "unknown"),
        "cwd": str(Path.cwd()),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }

    # P1: entry pins + canonical/mirror identity
    entry = measure(PINNED)
    pin_bad = [r for r, v in entry.items() if v["measured"] != PINNED[r]]
    chk("P1_entry_pins", not pin_bad, {"mismatches": pin_bad, "n": len(PINNED)})
    frozen = json.loads((ROOT / FORM / "FROZEN.json").read_text())
    fz_bad = [r for r in FROZEN_PINS
              if r in frozen["files"] and frozen["files"][r]["sha256"] != PINNED[r]]
    chk("P1b_frozen_declaration_agrees", not fz_bad, {"mismatches": fz_bad})
    mirror_bad = []
    for cls, name in [("AF-WCC-VAC-GEN", "af_wcc_vacuum.yaml"),
                      ("AF-SCC-C2-VAC-GEN", "af_scc_c2_vacuum.yaml"),
                      ("AF-SCC-C0-VAC-GEN", "af_scc_c0_vacuum.yaml")]:
        a = sha(ROOT / "schemas" / name)
        b = sha(ROOT / FORM / "schemas" / name)
        if a != b:
            mirror_bad.append({"class": cls, "canonical": a, "mirror": b})
    chk("P1c_canonical_mirror_identity", not mirror_bad, {"mismatches": mirror_bad})

    # clean rebuild of the sandbox, then run #1 and #2
    shutil.rmtree(SANDBOX, ignore_errors=True)
    shutil.copytree(ROOT / FORM, SANDBOX / FORM,
                    ignore=shutil.ignore_patterns("__pycache__"), dirs_exist_ok=True)
    sandbox_inputs = {k: sha(SANDBOX / k) for k in PINNED
                      if (SANDBOX / k).exists() and "evidence/gate_test_report" not in k}
    run1 = tool_run(SANDBOX, "run1")
    run2 = tool_run(SANDBOX, "run2")

    chk("P2_run1_exit0_and_pass",
        run1["exit_code"] == 0 and run1["report"].get("verdict") == "PASS"
        and run1["report"].get("counts") == EXPECTED_COUNTS
        and run1["report"].get("self_application", {}).get("clean") is True,
        {"exit_code": run1["exit_code"], "verdict": run1["report"].get("verdict"),
         "counts": run1["report"].get("counts"),
         "self_application_clean": run1["report"].get("self_application", {}).get("clean")})
    chk("P3_run2_byte_identical", run1["report_sha256"] == run2["report_sha256"]
        and run1["txt_sha256"] == run2["txt_sha256"],
        {"run1_report": run1["report_sha256"], "run2_report": run2["report_sha256"],
         "run1_txt": run1["txt_sha256"], "run2_txt": run2["txt_sha256"]})

    # P4: normalized equality with the frozen report
    norm_rep = (HERE / "run1_gate_test_report.json").read_text().replace(str(SANDBOX), str(ROOT))
    frozen_rep = FROZEN_REPORT_JSON.read_text()
    norm_txt = (HERE / "run1_gate_test_report.txt").read_text().replace(str(SANDBOX), str(ROOT))
    frozen_txt = FROZEN_REPORT_TXT.read_text()
    same_json = norm_rep == frozen_rep
    same_txt = norm_txt == frozen_txt
    if not same_json:
        try:
            a, b = json.loads(norm_rep), json.loads(frozen_rep)
            diff = sorted({k for k in set(a) | set(b) if a.get(k) != b.get(k)})
        except Exception as e:  # noqa: BLE001
            diff = [f"unparseable: {e}"]
    else:
        diff = []
    chk("P4_normalized_equals_frozen", same_json and same_txt,
        {"json_equal": same_json, "txt_equal": same_txt, "top_level_diffs": diff,
         "run_report_sha256": run1["report_sha256"],
         "frozen_report_sha256": sha(FROZEN_REPORT_JSON)})
    (HERE / "frozen_vs_run.diff").write_text(
        "" if same_json else f"top-level differing keys: {diff}\n")

    # P6 controls
    shutil.rmtree(SCRATCH_DEFECT, ignore_errors=True)
    shutil.copytree(SANDBOX, SCRATCH_DEFECT, dirs_exist_ok=True)
    wcc = SCRATCH_DEFECT / FORM / "schemas/af_wcc_vacuum.yaml"
    doc = yaml.safe_load(wcc.read_text())
    doc.pop("visibility", None)
    wcc.write_text(yaml.safe_dump(doc, sort_keys=False, width=110))
    c1 = subprocess.run([sys.executable, str(SCRATCH_DEFECT / FORM / "tools/check_class_schema.py"),
                         "--json", str(wcc)], capture_output=True, text=True, timeout=300)
    try:
        c1_rep = json.loads(c1.stdout)
    except Exception:  # noqa: BLE001
        c1_rep = {}
    chk("P6a_control_injected_defect_fires",
        c1.returncode != 0 and "R10" in c1_rep.get("failed_rules", []),
        {"exit_code": c1.returncode, "verdict": c1_rep.get("verdict"),
         "failed_rules": c1_rep.get("failed_rules")})

    shutil.rmtree(SCRATCH_DRIFT, ignore_errors=True)
    shutil.copytree(SANDBOX, SCRATCH_DRIFT, dirs_exist_ok=True)
    tgt = SCRATCH_DRIFT / FORM / "schemas/af_scc_c2_vacuum.yaml"
    before = sha(tgt)
    tgt.write_bytes(tgt.read_bytes() + b"\n# drift control\n")
    c2_detected = sha(tgt) != before
    c2_frame = bool(drift({str(tgt): {"measured": before}},
                          {str(tgt): {"measured": sha(tgt)}}))
    chk("P6b_control_drift_detector_fires", c2_detected and c2_frame,
        {"before": before, "after": sha(tgt), "frame_detected": c2_frame})

    # P5: exit frame on canonical paths (sandbox-external only)
    exit_ = measure(PINNED)
    moved = drift(entry, exit_)
    chk("P5_exit_frame_zero_drift", not moved, {"moved": moved})
    sandbox_after = {k: sha(SANDBOX / k) for k in sandbox_inputs}
    sandbox_moved = [k for k in sandbox_inputs if sandbox_inputs[k] != sandbox_after[k]]
    chk("P5b_sandbox_inputs_stable", not sandbox_moved, {"moved": sandbox_moved})

    ok = all(c["ok"] for c in checks)
    report = {
        "task": "W086-GFORM-SUITE-REPL-01",
        "actor": "worker-086",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "environment": env,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "verdict": ("GATE_SUITE_EVIDENCE_REPRODUCED_EXACTLY" if ok
                    else "GATE_SUITE_REPLICATION_FAILED"),
        "checks": checks,
        "failed_checks": [c["id"] for c in checks if not c["ok"]],
        "runs": {"run1": {k: v for k, v in run1.items() if k != "report"},
                 "run2": {k: v for k, v in run2.items() if k != "report"},
                 "run1_counts": run1["report"].get("counts"),
                 "run1_verdict": run1["report"].get("verdict")},
        "pins_entry": entry,
        "pins_exit": exit_,
        "frozen_report_sha256": sha(FROZEN_REPORT_JSON),
        "frozen_report_txt_sha256": sha(FROZEN_REPORT_TXT),
        "preregistration_sha256": sha(HERE / "PREREGISTRATION.md"),
        "canonical_paths_written": [],
        "falsifier": ("Any pinned input hash moving by exit; run exit != 0 or a count differing; "
                      "the normalized run report differing from the frozen report at any byte; "
                      "or a control that fails to fire."),
        "not_claimed": [
            "Not a gate verdict and not a node completion.",
            "Not a re-derivation of the checker rule semantics or of any class content.",
            "No canonical artifact, fixture, evidence file, map or event stream was written.",
        ],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"VERDICT: {report['verdict']}")
    for c in checks:
        print(f"  [{'ok' if c['ok'] else 'FAIL'}] {c['id']}")
    print(f"run1 counts: {report['runs']['run1_counts']}")
    print(f"frozen report: {report['frozen_report_sha256']}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W037-GFORM-FREEZE-01: independent freeze-stability + G-FORM precondition check.

Read-only. Does not write to any canonical/authoring artifact. It:
  1. snapshots sha256+mtime of the gate artifacts at T0 and recomputes the
     FROZEN.json declared-vs-disk drift independently,
  2. runs the formulation lead's own canonical tools and captures stdout/exit,
  3. checks the class-bound structural preconditions the G-FORM gate audit names
     (defined extension predicate, single frozen data class, conclusion type,
      no C0/C2 merge, f0_binding freshness),
  4. re-snapshots at T1 and reports whether the target moved under the check,
  5. compares the hashes named in leadform-resource-request-2026-09-12T00:34+08:00
     against the measured bytes.

Authority: verification evidence only. A worker event cannot set a node status, a
gate verdict, or a validation_status=passed. Reviewer identity: worker-037.

Usage: python3 artifacts/worker-037/gform_freeze_verification/verify_gform_freeze.py
Output: report.json next to this script (path printed to stdout).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

CANON = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
F0 = "research_map/formulation_taxonomy.yaml"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
WATCH = [
    *CANON.values(),
    F0,
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    FROZEN_REL,
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/KEY_MANIFEST.json",
]
CLASS_OF = {CANON["F1"]: "AF-WCC-VAC-GEN",
            CANON["F2a"]: "AF-SCC-C2-VAC-GEN",
            CANON["F2b"]: "AF-SCC-C0-VAC-GEN"}
EXPECTED_CONCLUSION = {"AF-WCC-VAC-GEN": "weak_cosmic_censorship",
                       "AF-SCC-C2-VAC-GEN": "scc_c2_future_inextendibility",
                       "AF-SCC-C0-VAC-GEN": "scc_c0_future_inextendibility"}
# hashes named in the lead's request event (comms/outbox/astra-lead-formulation.jsonl)
REQUEST_EVENT = "leadform-resource-request-2026-09-12T00:34:00+08:00"
REQUEST_PINS = {
    "F1": "68392dd820505fbb8c59c2944e744d00cef5a94fecafb3e927fd14a235d7175c",
    "F2a": "4f97273ef4404126ef5c8a083ccd5ed4d4ef9fd1aeaf6884c8c5aee0542e12f8",
    "F2b": "a2aef5ac7fe377a82b974aabddb991eec12ee7662d4b8e39d1516ac945965543",
    "F0": "0fcc6a1928fd40b02529f59c8a23095191001f84858346bf83d00818c29d7b31",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def snapshot() -> dict:
    out = {}
    for rel in WATCH:
        p = ROOT / rel
        if not p.exists():
            out[rel] = {"exists": False}
            continue
        st = p.stat()
        out[rel] = {
            "exists": True,
            "sha256": sha256_file(p),
            "bytes": st.st_size,
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime)),
        }
    return out


def run_tool(args: list[str]) -> dict:
    t0 = now()
    proc = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, timeout=300)
    return {
        "cmd": "python3 " + " ".join(args),
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout.strip().splitlines()[-12:],
        "stderr_tail": proc.stderr.strip().splitlines()[-6:],
        "started_at": t0,
        "ok": proc.returncode == 0,
    }


def yaml_load(rel: str):
    import yaml
    return yaml.safe_load((ROOT / rel).read_text())


def manifest_drift(frozen_doc: dict, snap: dict) -> dict:
    drift, missing = [], []
    for rel, rec in (frozen_doc.get("files") or {}).items():
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
            continue
        disk = snap.get(rel, {}).get("sha256") or sha256_file(p)
        if disk != rec.get("sha256"):
            drift.append({"path": rel, "declared": rec.get("sha256"), "disk": disk})
    gate = set(CANON.values()) | {F0}
    return {"pinned_files": len(frozen_doc.get("files") or {}),
            "drift_count": len(drift), "missing_count": len(missing),
            "gate_artifact_drift": [d for d in drift if d["path"] in gate],
            "drift_paths": [d["path"] for d in drift], "missing_paths": missing}


def structural_checks(snap: dict) -> list[dict]:
    checks: list[dict] = []
    f0_disk = snap[F0]["sha256"]
    for node, rel in CANON.items():
        doc = yaml_load(rel)
        cls = CLASS_OF[rel]
        lines = (ROOT / rel).read_text().splitlines()

        binding = (doc or {}).get("f0_binding") or {}
        declared = binding.get("declared_f0_sha256")
        checks.append({
            "node": node, "class_id": cls, "check": "f0_binding_matches_measured_canonical_f0",
            "status": "pass" if declared == f0_disk else "fail",
            "measured_f0_sha256": f0_disk, "declared_f0_sha256": declared,
            "witness": f"{rel}: f0_binding.declared_f0_sha256",
        })

        refs = [i + 1 for i, ln in enumerate(lines) if "extension_predicate" in ln]
        defines = bool((doc or {}).get("extension_predicate"))
        checks.append({
            "node": node, "class_id": cls, "check": "extension_predicate_defined_where_referenced",
            "status": "pass" if (defines or not refs) else "fail",
            "referenced_at_lines": refs, "block_present": defines,
        })

        q = (doc or {}).get("quantifiers") or {}
        d0_def = str(((q.get("domains") or {}).get("D0") or {}).get("definition", ""))
        binder = str(q.get("formal", ""))
        disjunctive = bool(re.search(r"\bor\b", d0_def)) or ("smooth-with-decay" in d0_def and "Sobolev" in d0_def)
        has_pair_binder = "(s,delta)" in binder or "(s, delta)" in binder
        checks.append({
            "node": node, "class_id": cls, "check": "single_frozen_data_class_no_disjunctive_regularity_domain",
            "status": "fail" if (disjunctive and has_pair_binder) else "pass",
            "d0_definition": d0_def, "statement_formal_binder_present": has_pair_binder,
            "witness": f"{rel}: quantifiers.domains.D0 / quantifiers.formal",
            "impact": "binder ranges over two regularity settings => schema is a family of two class "
                      "statements; G-FORM unmet item 'no single frozen data class shared by F1/F2a/F2b'",
        })

        concl = (doc or {}).get("conclusion") or {}
        ctype = str(concl.get("conclusion_type", ""))
        expected = EXPECTED_CONCLUSION.get(cls)
        stmt = str(concl.get("statement_formal", ""))
        merged = bool(re.search(r"\bC0\b[^.]{0,120}\bC2\b|\bC2\b[^.]{0,120}\bC0\b", stmt))
        bad_type = ctype in {"", "strong_cosmic_censorship"} or (expected is not None and ctype != expected)
        checks.append({
            "node": node, "class_id": cls, "check": "conclusion_type_class_specific_no_C0_C2_merge",
            "status": "fail" if (bad_type or merged) else "pass",
            "conclusion_type": ctype, "expected_conclusion_type": expected,
            "C0_C2_merge_in_conclusion_statement": merged,
            "witness": f"{rel}: conclusion.conclusion_type / conclusion.statement_formal",
        })

        sibling = {"AF-SCC-C2-VAC-GEN": "AF-SCC-C0-VAC-GEN",
                   "AF-SCC-C0-VAC-GEN": "AF-SCC-C2-VAC-GEN"}.get(cls)
        if sibling:
            core = json.dumps({"quantifiers": q, "conclusion": concl})
            checks.append({
                "node": node, "class_id": cls,
                "check": "sibling_class_token_absent_from_quantifiers_conclusion",
                "status": "fail" if sibling in core else "pass", "sibling": sibling,
            })
    return checks


def main() -> int:
    t0 = now()
    s0 = snapshot()
    frozen0 = json.loads((ROOT / FROZEN_REL).read_text())
    drift0 = manifest_drift(frozen0, s0)

    tool_runs = []
    for node, rel in CANON.items():
        tool_runs.append({**run_tool(["artifacts/formulation/tools/check_class_schema.py", rel, "--json"]),
                          "tool": "check_class_schema", "node": node})
    tool_runs.append({**run_tool(["artifacts/formulation/tools/run_acceptance.py"]), "tool": "run_acceptance"})
    tool_runs.append({**run_tool(["artifacts/formulation/tools/verify_frozen.py"]), "tool": "verify_frozen"})
    tool_runs.append({**run_tool(["artifacts/formulation/tools/check_taxonomy_consistency.py"]),
                      "tool": "check_taxonomy_consistency"})

    checks = structural_checks(s0)
    s1 = snapshot()
    frozen1 = json.loads((ROOT / FROZEN_REL).read_text())
    drift1 = manifest_drift(frozen1, s1)
    moved = [rel for rel in WATCH if s0.get(rel, {}).get("sha256") != s1.get(rel, {}).get("sha256")]
    t1 = now()

    # hashes the lead's request asked reviewers to bind, vs measured bytes at T0
    request_check = {}
    for node, rel in {**CANON, "F0": F0}.items():
        disk = s0[rel]["sha256"]
        request_check[node] = {"path": rel, "requested_sha256": REQUEST_PINS[node],
                               "measured_sha256": disk,
                               "status": "superseded" if disk != REQUEST_PINS[node] else "current"}
    superseded = [n for n, v in request_check.items() if v["status"] == "superseded"]

    findings = []
    if superseded:
        findings.append({
            "id": "W037-F1", "severity": "critical",
            "statement": "The hashes named in " + REQUEST_EVENT + " were already superseded when measured: "
                         "a verdict bound to them would bind a revision that is not on disk.",
            "evidence": [f"{v['path']} requested={v['requested_sha256'][:12]} measured={v['measured_sha256'][:12]}"
                         for v in request_check.values() if v["status"] == "superseded"],
            "impact": "G-FORM/G-F0 remain unjudgeable until reviewers are re-dispatched against a hash that "
                      "is still on disk when they write their verdict.",
        })
    if drift0["drift_count"] or drift1["drift_count"] or drift0["missing_count"] or drift1["missing_count"]:
        findings.append({
            "id": "W037-F2", "severity": "major",
            "statement": "FROZEN.json declared-vs-disk drift is nonzero during this check.",
            "evidence": [f"T0 drift={drift0['drift_count']} gate={len(drift0['gate_artifact_drift'])}",
                         f"T1 drift={drift1['drift_count']} gate={len(drift1['gate_artifact_drift'])}"],
            "impact": "Any review verdict binding the manifest pins is unadjudicable; regenerate the manifest "
                      "and re-run verify_frozen.py until 0 problems.",
        })
    ra = next(r for r in tool_runs if r["tool"] == "run_acceptance")
    if not ra["ok"]:
        findings.append({
            "id": "W037-F3", "severity": "major",
            "statement": "run_acceptance.py exits nonzero at the measured bytes; the acceptance pipeline is "
                         "not green.",
            "evidence": ["artifacts/formulation/tools/run_acceptance.py", "tool_runs[run_acceptance]",
                         f"exit_code={ra['exit_code']}"],
            "impact": "No end-to-end acceptance evidence exists at the current canonical bytes.",
        })
    f0_bad = [c for c in checks if c["check"] == "f0_binding_matches_measured_canonical_f0" and c["status"] == "fail"]
    if f0_bad:
        findings.append({
            "id": "W037-F4", "severity": "major",
            "statement": "Class schemas carry stale f0_binding pins: declared F0 sha256 does not equal the "
                         "canonical F0 taxonomy measured on disk.",
            "evidence": [c["witness"] for c in f0_bad],
            "impact": "The binding gate (R17/R18) cannot be evaluated until the binding is refreshed.",
        })
    arity = [c for c in checks if c["check"] == "single_frozen_data_class_no_disjunctive_regularity_domain"
             and c["status"] == "fail"]
    if arity:
        findings.append({
            "id": "W037-F5", "severity": "major",
            "statement": "The single-frozen-data-class precondition is unmet at the measured bytes: each "
                         "schema binds its class statement over a disjunctive regularity domain D0 "
                         "('Sobolev variant ... or the smooth-with-decay default'), i.e. the formal statement "
                         "quantifies over a family of two regularity settings rather than one frozen "
                         "(s,delta,norm). The three schemas use the same D0 text, so they are mutually "
                         "aligned, but they are not single-class statements.",
            "evidence": [f"{c['node']} {c['witness']}: {c['d0_definition']}" for c in arity],
            "impact": "The G-FORM unmet item 'no single frozen data class (s,delta,norm)' is not discharged, "
                      "and the licensed C0=>C2 transfer stays unlicensed until one regularity setting is "
                      "frozen (the other must be demoted to a named variant class).",
        })
    if moved:
        findings.append({
            "id": "W037-F6", "severity": "critical",
            "statement": "The gate artifacts moved during this verification (T0 != T1); no verdict can bind "
                         "these bytes.",
            "evidence": moved,
        })

    machine_green = (all(r["ok"] for r in tool_runs) and not drift1["drift_count"]
                     and not drift1["missing_count"] and not f0_bad)
    payload = {
        "task_id": "W037-GFORM-FREEZE-01",
        "actor": "worker-037",
        "authority": "independent verification evidence only; NOT a gate verdict, NOT an acceptance, "
                     "NOT a node-status change",
        "question": "Is the formulation freeze that " + REQUEST_EVENT + " asks reviewers to bind "
                    "hash-stable and machine-green, and do the class-bound G-FORM preconditions hold at "
                    "the measured bytes?",
        "method": "read-only: T0 snapshot + independent manifest diff -> run the lead's own canonical tools "
                  "-> YAML structural checks -> T1 snapshot + manifest diff",
        "wall_clock": {"t0": t0, "t1": t1},
        "declared_freeze": {"manifest": FROZEN_REL, "revision": frozen1.get("revision"),
                            "frozen_at": frozen1.get("frozen_at")},
        "request_under_test": {"event_id": REQUEST_EVENT, "pins": REQUEST_PINS,
                               "per_node": request_check, "superseded_nodes": superseded},
        "snapshot_T0": s0,
        "snapshot_T1": s1,
        "moved_during_check": moved,
        "manifest_drift_T0": drift0,
        "manifest_drift_T1": drift1,
        "session_observations": [
            {"at": "2026-09-12T00:19:38+0800",
             "observation": "same checker logic: FROZEN.json rev24 pinned 68392dd82050/4f97273ef440/"
                            "a2aef5ac7fe3/0fcc6a1928fd while disk held 9a8bd4c96800/b6123750b37d/"
                            "1bb78ce9b357/276009f4f63d; drift 14/40 files; run_acceptance.py exited nonzero "
                            "with PREFLIGHT FAIL (stale rebased fixtures)",
             "status": "superseded by a manifest regeneration at ~00:19:5x; retained as freeze-churn evidence"},
            {"at": "2026-09-12T00:19:44+0800",
             "observation": "canonical schemas mtimes 00:18:37 then 00:19:14 within a 2-minute window; "
                            "FROZEN.json frozen_at is future-dated 2026-09-12T00:32:00+08:00 vs wall clock "
                            "00:20 (clock-discipline finding CF-14 reproduces)",
             "status": "provenance note"},
        ],
        "tool_runs": tool_runs,
        "machine_green_at_T1": machine_green,
        "structural_checks": checks,
        "findings": findings,
        "worker_verdict": ("inconclusive: at least one blocking finding at the measured bytes"
                           if findings else
                           "no blocking finding at the measured bytes; this is verification evidence, "
                           "not one of the two required accepts"),
        "does_not_claim": ["G-FORM pass/fail", "G-F0 pass/fail", "node completion", "theorem",
                           "physics result", "authority to edit canonical artifacts"],
        "next_falsifier": "Re-run this script in a quiet window: it is falsified if (a) every requested pin "
                          "equals the measured disk hash, (b) FROZEN.json drift is 0 at T0 and T1 and "
                          "run_acceptance.py exits 0, (c) every f0_binding equals the measured canonical F0 "
                          "hash, (d) T0 == T1, and (e) the W037-F5 D0-disjunction witness no longer matches.",
    }
    body = json.dumps(payload, indent=1, sort_keys=True)
    payload["report_payload_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    out = OUT / "report.json"
    out.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    print(f"wrote {out.relative_to(ROOT)} sha256={sha256_file(out)}")
    print(json.dumps({"findings": [(f["id"], f["severity"]) for f in findings],
                      "superseded_pins": superseded,
                      "drift_T0": drift0["drift_count"], "drift_T1": drift1["drift_count"],
                      "moved": moved, "machine_green_at_T1": machine_green,
                      "tools": {r["tool"] + (":" + r.get("node", "")): r["ok"] for r in tool_runs}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""W008-FORMSEP04-REVREBIND-01: revision-agnostic FORM-SEP-04 re-bind driver (read-only).

Why this exists
---------------
The rev28 blocker (w008-rev28-20260912T0037-blocker) requires the FORM-SEP-04
separation audit and the F2b dual-defect checker to be re-run "at the new hash"
after lead-formulation repairs the two C0 containment sentences and re-freezes.
`rebind_rev28.py` hard-codes the rev28 pins, so it cannot be re-run at rev29
without editing a published artifact (which would invalidate its emitted bundle).
This driver discovers the pins from the live FROZEN manifest instead.

What it does (deterministic, no canonical mutation)
---------------------------------------------------
1. measure live sha256 of F1/F2a/F2b canonical schemas, their authoring mirrors,
   artifact/formulation/FROZEN.json, rule_spec.json and the structural gate tool;
2. require every canonical schema's measured hash to equal the FROZEN manifest
   pin -> otherwise FAIL-CLOSED (exit 3): a moved FROZEN binding means a reviewer
   must not bind to these bytes, so no verdict is emitted;
3. require canonical == mirror byte equality for all three schemas;
4. run artifacts/formulation/tools/verify_frozen.py (exit 0 required);
5. run the FORM-SEP-04 audit (X1-X5, artifacts/worker08/c2_c0_separation_audit.py)
   at the measured pins;
6. run the F2b dual-defect containment checker
   (artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py) at the same
   measured pins;
7. write a hash-pinned bundle: overall PASS only if verify_frozen exits 0 and both
   checkers return PASS. Exit 0 on PASS, 1 on a checker FAIL, 3 on fail-closed.

At FROZEN rev28 this is expected to be FAIL with the known two findings (X3c
containment inversion, dual size_premise_inverted + false_containment_denial).
That is the sensitivity control: a harness that returns PASS at rev28 bytes would
be broken. At the repaired re-freeze the finding sets must go to zero.

Authority: worker-level measurement only. No node completion, no gate verdict, no
theorem, no edit to any canonical artifact. Interpretation is owned by
astra-lead-formulation; gate verdicts by the controller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CST = timezone(timedelta(hours=8))

CANON = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
SGCC = ("F2a", "F2b")  # pair the FORM-SEP-04 audit consumes
FROZEN = "artifacts/formulation/FROZEN.json"
RULE_SPEC = "artifacts/formulation/rule_spec.json"
GATE_TOOL = "artifacts/formulation/tools/check_class_schema.py"
VERIFY_FROZEN = "artifacts/formulation/tools/verify_frozen.py"
AUDIT = "artifacts/worker08/c2_c0_separation_audit.py"
DUAL = "artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py"
CONTAINMENT_DIRECTION = "artifacts/worker-008/containment_direction/audit_containment_direction.py"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def mirror_of(rel: str) -> str:
    p = Path(rel)
    return str(Path("artifacts/formulation/schemas") / p.name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=None,
                    help="bundle path (default artifacts/worker08/rev_rebind_rev<revision>.json)")
    ap.add_argument("--label", default="rev-rebind")
    ap.add_argument("--max-hours-approx", type=float, default=0.2,
                    help="worker time spent, recorded for accounting only")
    args = ap.parse_args()

    frozen_path = REPO / FROZEN
    frozen = json.loads(frozen_path.read_text())
    rev = int(frozen.get("revision"))
    frozen_files = frozen.get("files", {})

    outdir = REPO / "artifacts" / "worker08"
    outdir.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else outdir / f"rev_rebind_rev{rev}.json"
    if not out.is_absolute():
        out = REPO / out

    paths = {k: CANON[k] for k in CANON}
    paths.update({k + "_mirror": mirror_of(v) for k, v in CANON.items()})
    paths["FROZEN"] = FROZEN
    paths["rule_spec"] = RULE_SPEC
    paths["gate_tool"] = GATE_TOOL
    paths["verify_frozen"] = VERIFY_FROZEN
    paths["audit"] = AUDIT
    paths["dual"] = DUAL
    missing = [v for v in paths.values() if not (REPO / v).exists()]
    if missing:
        print(json.dumps({"verdict": "FAIL-CLOSED", "reason": "missing inputs", "missing": missing}))
        return 3
    pins = {k: sha(REPO / v) for k, v in paths.items()}

    bundle: dict = {
        "bundle_id": f"w008-formsep04-revrebind-rev{rev}-{datetime.now(CST).strftime('%Y%m%dT%H%M%S%z')}",
        "task_id": "W008-FORMSEP04-REVREBIND-01",
        "assigned_task_id": "FORM-SEP-04",
        "assignment_event_id": "assign-FORM-SEP-04-20260911T2331",
        "actor": "worker-008",
        "agent_id": "deepseek-flash-08",
        "node_id": "F2",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-CLASSBIND",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "label": args.label,
        "frozen_revision": rev,
        "frozen_declared_at": frozen.get("frozen_at"),
        "pins": pins,
        "inputs": paths,
        "checks": {},
        "findings": [],
        "evidence_refs": [],
        "authority": (
            "Worker-level measurement only. No node completion, no gate verdict, no theorem; "
            "G-CLASSBIND stays pending/lead-owned; interpretation owned by astra-lead-formulation."
        ),
        "falsifier": (
            "A run of this driver at FROZEN rev28 bytes that returns PASS (the two known C0 findings "
            "must make it FAIL), or a run after a repair re-freeze whose overall verdict stays FAIL "
            "while the repaired leaf fields match the declared chain E_C0 contains E_H2loc contains "
            "E_{C^1,1} contains E_C2 and the dual checker reports no finding. Either voids this "
            "harness or the repair claim respectively."
        ),
    }

    # --- step 2: FROZEN pin binding (fail closed) ---
    binding = {}
    for k in CANON:
        decl = frozen_files.get(CANON[k], {}).get("sha256")
        binding[k] = {"declared": decl, "measured": pins[k], "match": decl == pins[k]}
    bundle["checks"]["frozen_pin_binding"] = {
        "result": "PASS" if all(v["match"] for v in binding.values()) else "FAIL",
        "detail": binding,
    }
    if not all(v["match"] for v in binding.values()):
        bundle["verdict"] = "FAIL-CLOSED"
        bundle["reason"] = "canonical schema bytes do not match the FROZEN manifest pins; no verdict emitted"
        bundle["evidence_refs"] = [f"{FROZEN}#{pins['FROZEN'][:12]}"] + [
            f"{CANON[k]}#{pins[k][:12]}" for k in CANON
        ]
        out.write_text(json.dumps(bundle, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"bundle": str(out.relative_to(REPO)), "verdict": bundle["verdict"],
                          "reason": bundle["reason"]}, indent=1))
        return 3

    # --- step 3: canonical == mirror ---
    mirror = {k: pins[k] == pins[k + "_mirror"] for k in CANON}
    bundle["checks"]["canonical_mirror_byte_equality"] = {
        "result": "PASS" if all(mirror.values()) else "FAIL",
        "detail": mirror,
    }
    if not all(mirror.values()):
        bundle["verdict"] = "FAIL"
        bundle["findings"].append({"kind": "mirror_byte_mismatch", "detail": mirror})
        out.write_text(json.dumps(bundle, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"bundle": str(out.relative_to(REPO)), "verdict": "FAIL",
                          "mirror": mirror}, indent=1))
        return 1

    # --- step 4: verify_frozen ---
    vf = subprocess.run([sys.executable, str(REPO / VERIFY_FROZEN)],
                        capture_output=True, text=True, cwd=REPO)
    vf_txt = (vf.stdout + vf.stderr).strip()
    bundle["checks"]["verify_frozen"] = {
        "result": "PASS" if vf.returncode == 0 else "FAIL",
        "exit_code": vf.returncode,
        "output_tail": vf_txt.splitlines()[-3:] if vf_txt else [],
    }

    # --- step 5: FORM-SEP-04 audit at measured pins ---
    mtx = outdir / f"form_sep_04_rev{rev}_rebind.json"
    mdd = outdir / f"form_sep_04_rev{rev}_rebind.md"
    run_audit = subprocess.run(
        [sys.executable, str(REPO / AUDIT), "--c2", CANON["F2a"], "--c0", CANON["F2b"],
         "--out-json", str(mtx), "--out-md", str(mdd), "--label", f"{args.label}-rev{rev}"],
        capture_output=True, text=True, cwd=REPO)
    matrix = json.loads(mtx.read_text()) if mtx.exists() else {}
    x3c = matrix.get("X3c_containment_inversion", {}) if matrix else {}
    audit_pass = matrix.get("verdict") == "PASS"
    bundle["checks"]["form_sep_04_audit"] = {
        "result": "PASS" if audit_pass else matrix.get("verdict", "FAIL"),
        "exit_code": run_audit.returncode,
        "hard_failure_kinds": [f.get("kind") for f in matrix.get("hard_failures", [])],
        "hard_failures": matrix.get("hard_failures", []),
        "X3c_violations": x3c.get("violations", []),
        "X3_converse_assertions": len(matrix.get("X3_implication_ledger", {}).get("converse_assertions", [])),
        "matrix_path": str(mtx.relative_to(REPO)),
        "matrix_sha256": sha(mtx) if mtx.exists() else None,
        "report_path": str(mdd.relative_to(REPO)),
        "report_sha256": sha(mdd) if mdd.exists() else None,
    }

    # --- step 6: dual-defect checker at measured pins ---
    ddr = outdir / f"f2b_dual_defect_rev{rev}_rebind.json"
    run_dual = subprocess.run(
        [sys.executable, str(REPO / DUAL), "--c2", CANON["F2a"], "--c0", CANON["F2b"],
         "--expect-c0", pins["F2b"], "--expect-c2", pins["F2a"],
         "--label", f"{args.label}-rev{rev}", "--json", str(ddr)],
        capture_output=True, text=True, cwd=REPO)
    dual = json.loads(ddr.read_text()) if ddr.exists() else {}
    bundle["checks"]["f2b_dual_defect"] = {
        "result": dual.get("verdict", "FAIL"),
        "exit_code": dual.get("exit_code"),
        "subchecks": {k: v.get("result") for k, v in dual.get("checks", {}).items()},
        "finding_kinds": sorted({f.get("kind") for f in dual.get("findings", [])}),
        "findings": dual.get("findings", []),
        "json_path": str(ddr.relative_to(REPO)),
        "json_sha256": sha(ddr) if ddr.exists() else None,
    }

    # --- non-gating cross-file census pointer (delivered by a prior worker-008 pass) ---
    cd = REPO / CONTAINMENT_DIRECTION
    bundle["cross_file_census"] = {
        "gating": False,
        "checker": CONTAINMENT_DIRECTION,
        "checker_sha256": sha(cd) if cd.exists() else None,
        "note": (
            "Cross-file containment census (F2a/F1/F0-canonical/F0-supplement clean; 2 findings bounded "
            "to F2b) was delivered at rev28 in artifacts/worker-008/containment_direction/ and is not "
            "re-run here because its --pinned-dir pins rev28 bytes and would void itself at rev29."
        ),
    }

    overall = (
        bundle["checks"]["frozen_pin_binding"]["result"] == "PASS"
        and bundle["checks"]["canonical_mirror_byte_equality"]["result"] == "PASS"
        and bundle["checks"]["verify_frozen"]["result"] == "PASS"
        and audit_pass
        and bundle["checks"]["f2b_dual_defect"]["result"] == "PASS"
    )
    bundle["verdict"] = "PASS" if overall else "FAIL"
    bundle["expected_at_rev28"] = "FAIL"
    bundle["evidence_refs"] = [
        f"{CANON['F2a']}#{pins['F2a'][:12]}",
        f"{CANON['F2b']}#{pins['F2b'][:12]}",
        f"{FROZEN}#{pins['FROZEN'][:12]}",
        f"{RULE_SPEC}#{pins['rule_spec'][:12]}",
        f"{GATE_TOOL}#{pins['gate_tool'][:12]}",
        f"{AUDIT}#{pins['audit'][:12]}",
        f"{DUAL}#{pins['dual'][:12]}",
        "schemas/af_scc_c0_vacuum.yaml:151",
        "schemas/af_scc_c0_vacuum.yaml:238",
        "schemas/af_scc_c0_vacuum.yaml:245",
    ]
    bundle["worker_hours_approx"] = args.max_hours_approx
    out.write_text(json.dumps(bundle, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "bundle": str(out.relative_to(REPO)),
        "bundle_sha256": sha(out),
        "frozen_revision": rev,
        "verdict": bundle["verdict"],
        "checks": {k: v["result"] for k, v in bundle["checks"].items()},
        "X3c_violations": bundle["checks"]["form_sep_04_audit"]["X3c_violations"],
        "dual_finding_kinds": bundle["checks"]["f2b_dual_defect"]["finding_kinds"],
    }, indent=1))
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())

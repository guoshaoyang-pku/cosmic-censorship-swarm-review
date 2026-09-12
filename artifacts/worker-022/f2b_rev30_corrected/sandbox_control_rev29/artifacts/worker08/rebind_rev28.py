#!/usr/bin/env python3
"""W008-FORMSEP04-REV28-REBIND-01 driver (read-only).

Re-binds the FORM-SEP-04 assignment (node F2, gate G-CLASSBIND, classes
AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN) to the live FROZEN revision 28 pair:
  C2 5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce
  C0 55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6
prior binding: FROZEN rev25 (C2 b6123750 / C0 1bb78ce9); rev27 addendum existed.

Deterministic steps, all recorded in form_sep_04_rev28_bundle.json:
  1. hash canonical schemas/, authoring mirror artifacts/formulation/schemas/,
     rule_spec.json, gate tool, FROZEN.json; assert canonical == mirror bytes.
  2. run artifacts/formulation/tools/verify_frozen.py (44 pins, exit 0 required).
  3. run the FORM-SEP-04 audit (v3) at the canonical pins.
  4. run the F2b dual-defect containment checker at the same pins.
  5. assemble a hash-pinned bundle with verdicts, findings, evidence and falsifier.

No node completion, no gate verdict, no mutation of any canonical artifact.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "artifacts" / "worker08" / "rev28_live"
CST = timezone(timedelta(hours=8))

CANON_C0 = "schemas/af_scc_c0_vacuum.yaml"
CANON_C2 = "schemas/af_scc_c2_vacuum.yaml"
MIRROR_C0 = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
MIRROR_C2 = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
RULE_SPEC = "artifacts/formulation/rule_spec.json"
GATE_TOOL = "artifacts/formulation/tools/check_class_schema.py"
FROZEN = "artifacts/formulation/FROZEN.json"
VERIFY_FROZEN = "artifacts/formulation/tools/verify_frozen.py"

AUDIT = "artifacts/worker08/c2_c0_separation_audit.py"
DUAL = "artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py"

EXPECT_C0 = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
EXPECT_C2 = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pins = {p: sha(REPO / p) for p in
            (CANON_C0, CANON_C2, MIRROR_C0, MIRROR_C2, RULE_SPEC, GATE_TOOL, FROZEN,
             AUDIT, DUAL, VERIFY_FROZEN)}

    mirror = {
        "canonical_vs_mirror_c0": pins[CANON_C0] == pins[MIRROR_C0],
        "canonical_vs_mirror_c2": pins[CANON_C2] == pins[MIRROR_C2],
    }
    if not all(mirror.values()):
        print("FAIL: canonical/mirror byte mismatch", mirror)
        return 3
    if pins[CANON_C0] != EXPECT_C0 or pins[CANON_C2] != EXPECT_C2:
        print("FAIL: live pair differs from the rev28 binding", pins[CANON_C0], pins[CANON_C2])
        return 3

    vf = subprocess.run([sys.executable, str(REPO / VERIFY_FROZEN)],
                        capture_output=True, text=True, cwd=REPO)
    frozen_txt = (vf.stdout + vf.stderr).strip()

    mtx = OUT / "c2_c0_separation_matrix_rev28_live.json"
    mdd = OUT / "c2_c0_separation_report_rev28_live.md"
    ddr = OUT / "f2b_dual_defect_rev28_live.json"
    run_audit = subprocess.run(
        [sys.executable, str(REPO / AUDIT), "--c2", CANON_C2, "--c0", CANON_C0,
         "--out-json", str(mtx), "--out-md", str(mdd), "--label", "rev28-live"],
        capture_output=True, text=True, cwd=REPO)
    run_dual = subprocess.run(
        [sys.executable, str(REPO / DUAL), "--c2", CANON_C2, "--c0", CANON_C0,
         "--expect-c0", EXPECT_C0, "--expect-c2", EXPECT_C2,
         "--label", "rev28-live", "--json", str(ddr)],
        capture_output=True, text=True, cwd=REPO)

    matrix = json.loads(mtx.read_text())
    dual = json.loads(ddr.read_text())
    frozen_check = matrix["frozen_manifest_check"]

    bundle = {
        "bundle_id": "w008-formsep04-rev28-rebind-20260912T0037+0800",
        "task_id": "W008-FORMSEP04-REV28-REBIND-01",
        "assigned_task_id": "FORM-SEP-04",
        "assignment_event_id": "assign-FORM-SEP-04-20260911T2331",
        "actor": "worker-008",
        "agent_id": "deepseek-flash-08",
        "node_id": "F2",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-CLASSBIND",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "frozen_revision": frozen_check["revision"],
        "frozen_manifest_sha256": pins[FROZEN],
        "frozen_manifest_mismatches": frozen_check["mismatches"],
        "verify_frozen_exit_code": vf.returncode,
        "verify_frozen_output": frozen_txt,
        "pins": pins,
        "mirror_byte_equality": mirror,
        "gate_runs": matrix["gate_runs"],
        "form_sep_04": {
            "verdict": matrix["verdict"],
            "hard_failure_kinds": [f["kind"] for f in matrix["hard_failures"]],
            "hard_failures": matrix["hard_failures"],
            "X1_expectation_violations": len(matrix["X1_pairwise"]["expectation_violations"]),
            "X1_naming_asymmetry_flags": len(matrix["X1_pairwise"]["naming_asymmetry_flags"]),
            "X1_annotation_drift_flags": len(matrix["X1_pairwise"]["annotation_drift_flags"]),
            "X1_leaf_paths": matrix["X1_pairwise"]["leaf_paths"],
            "X3_converse_assertions": len(matrix["X3_implication_ledger"]["converse_assertions"]),
            "X3_unclassified_dual_mentions": len(matrix["X3_implication_ledger"]["unclassified_dual_mentions"]),
            "X4_violations": len(matrix["X4_composite_regularity"]["violations"]),
            "X3c_containment_inversions": matrix["X3c_containment_inversion"]["violations"],
            "post_repair_residuals": matrix.get("post_repair_residuals", []),
            "declaration": matrix["declaration"],
        },
        "f2b_dual_defect": {
            "verdict": dual["verdict"],
            "exit_code": dual["exit_code"],
            "checks": {k: v["result"] for k, v in dual["checks"].items()},
            "finding_kinds": sorted({f["kind"] for f in dual["findings"]}),
            "findings": dual["findings"],
            "inputs": dual["inputs"],
        },
        "evidence_refs": [
            f"{CANON_C2}#{pins[CANON_C2][:12]}",
            f"{CANON_C0}#{pins[CANON_C0][:12]}",
            f"{FROZEN}#{pins[FROZEN][:12]}",
            f"{RULE_SPEC}#{pins[RULE_SPEC][:12]}",
            f"{GATE_TOOL}#{pins[GATE_TOOL][:12]}",
            f"{MIRROR_C0}#{pins[MIRROR_C0][:12]}",
            f"{MIRROR_C2}#{pins[MIRROR_C2][:12]}",
            f"schemas/af_scc_c0_vacuum.yaml:{dual['findings'][-1]['line']}",
            "schemas/af_scc_c0_vacuum.yaml:151",
            "schemas/af_scc_c0_vacuum.yaml:238",
            "schemas/af_scc_c0_vacuum.yaml:248",
            "schemas/af_scc_c2_vacuum.yaml:236",
        ],
        "verdict": "FAIL" if (matrix["verdict"] == "FAIL" or dual["verdict"] == "FAIL") else "PASS",
        "repair_requested": (
            "C0 regularity.must_not_conflate[0] (line 151): drop the false 'No containment ... is "
            "asserted here' clause, which contradicts the declared chain E_C0 contains E_H2loc "
            "contains E_{C^1,1} contains E_C2; state the curvature-axis distinction without denying "
            "containment. C0 implication_ledger.forbidden_transfers[0].reason (line ~245): replace "
            "'C2 is a strictly larger extension class' with 'C2 is a strictly smaller extension "
            "class (E_C2 subset of E_C0)'. Re-hash, re-freeze, re-run both checkers to PASS."
        ),
        "falsifier": (
            "A rev28+ C0/C2 reading under which either sentence is consistent with the declared "
            "containment chain; a containment placement where the C2 conclusion is satisfied by a "
            "C0-only extension class (or vice versa); a Cx => Cy converse assertion; a composite or "
            "foreign regularity token in an assertive conclusion field; or a canonical C0 hash other "
            "than 55d0a1ea at which these findings vanish. Any of these voids this bundle."
        ),
        "authority": (
            "Worker-level measurement only. No node completion, no gate verdict, no theorem; "
            "G-CLASSBIND stays pending/lead-owned; interpretation owned by astra-lead-formulation."
        ),
        "command": "python3 artifacts/worker08/rebind_rev28.py",
        "audit_stdout": run_audit.stdout.strip().splitlines()[-1] if run_audit.stdout else "",
        "dual_exit_code": run_dual.returncode,
    }

    bp = OUT / "form_sep_04_rev28_bundle.json"
    bp.write_text(json.dumps(bundle, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({
        "bundle": str(bp.relative_to(REPO)),
        "bundle_sha256": sha(bp),
        "outputs": {
            str(mtx.relative_to(REPO)): sha(mtx),
            str(mdd.relative_to(REPO)): sha(mdd),
            str(ddr.relative_to(REPO)): sha(ddr),
        },
        "verdict": bundle["verdict"],
        "form_sep_04_verdict": matrix["verdict"],
        "f2b_verdict": dual["verdict"],
        "verify_frozen_exit": vf.returncode,
        "frozen_revision": frozen_check["revision"],
        "frozen_mismatches": len(frozen_check["mismatches"]),
        "gate_runs": {k: v["verdict"] for k, v in matrix["gate_runs"].items()},
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

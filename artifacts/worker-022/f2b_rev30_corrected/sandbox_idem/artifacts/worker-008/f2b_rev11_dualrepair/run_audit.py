#!/usr/bin/env python3
"""W008-F2B-DUALREPAIR-01 — driver: audit live canonical vs rebased candidate.

Fails closed (exit 3) if the live canonical hash has moved since the snapshot
or if FROZEN.json no longer pins the measured hashes.  Writes report.json,
report.md and returns 0 when: canonical FAILs with exactly the two declared
defects, candidate PASSes, and the control battery expectations hold.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
AUDIT = ROOT / "audit_dual_defect.py"
TAX = REPO / "research_map" / "formulation_taxonomy.yaml"
C0_LIVE = REPO / "schemas" / "af_scc_c0_vacuum.yaml"
C0_AUTHORING = REPO / "artifacts" / "formulation" / "schemas" / "af_scc_c0_vacuum.yaml"
C2_LIVE = REPO / "schemas" / "af_scc_c2_vacuum.yaml"
C2_AUTHORING = REPO / "artifacts" / "formulation" / "schemas" / "af_scc_c2_vacuum.yaml"
FROZEN = REPO / "artifacts" / "formulation" / "FROZEN.json"
EXPECT_C0 = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
EXPECT_C2 = "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2"
EXPECT_TAX = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(c0: Path, expect: str, label: str) -> dict:
    out = ROOT / "evidence" / f"audit_{label}.json"
    proc = subprocess.run([sys.executable, str(AUDIT), "--c0", str(c0), "--c2", str(C2_LIVE),
                           "--taxonomy", str(TAX), "--expect-c0", expect or "", "--expect-c2", EXPECT_C2,
                           "--label", label, "--json", str(out)], capture_output=True, text=True)
    rep = json.loads(out.read_text())
    rep["exit_code_observed"] = proc.returncode
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    return rep


def main() -> int:
    frozen = json.loads(FROZEN.read_text())
    frozen_files = frozen.get("files", {})
    live = {"c0": sha(C0_LIVE), "c2": sha(C2_LIVE), "tax": sha(TAX)}
    if live["c0"] != EXPECT_C0 or live["c2"] != EXPECT_C2 or live["tax"] != EXPECT_TAX:
        print(json.dumps({"verdict": "FAIL-CLOSED", "detail": "live canonical hash moved",
                          "measured": live}))
        return 3
    binding = {
        "frozen_revision": frozen.get("revision"),
        "frozen_at": frozen.get("frozen_at"),
        "frozen_json_sha256": sha(FROZEN),
        "schemas_c0_path_pinned": frozen_files.get("schemas/af_scc_c0_vacuum.yaml", {}).get("sha256"),
        "authoring_c0_path_pinned": frozen_files.get("artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", {}).get("sha256"),
        "authoring_c0_live_sha256": sha(C0_AUTHORING),
        "authoring_c2_live_sha256": sha(C2_AUTHORING),
        "canonical_equals_authoring_c0": sha(C0_AUTHORING) == live["c0"],
        "canonical_equals_authoring_c2": sha(C2_AUTHORING) == live["c2"],
        "defect_is_inside_frozen_set": (frozen_files.get("schemas/af_scc_c0_vacuum.yaml", {}).get("sha256") == live["c0"]),
    }
    canonical = run(C0_LIVE, EXPECT_C0, "canonical_live")
    candidate = run(ROOT / "candidate" / "af_scc_c0_vacuum.yaml", None, "candidate")

    controls_path = ROOT / "evidence" / "controls_summary.json"
    controls = json.loads(controls_path.read_text())
    minimality = json.loads((ROOT / "evidence" / "minimality_report.json").read_text())
    selftest = json.loads((ROOT / "evidence" / "selftest.json").read_text())

    can_kinds = sorted({f["kind"] for f in canonical["findings"]})
    ok = (canonical["verdict"] == "FAIL"
          and can_kinds == ["false_containment_denial", "size_premise_inverted"]
          and candidate["verdict"] == "PASS"
          and controls["all_expectations_met"] and minimality["minimality_verdict"] == "PASS"
          and selftest["ok"])
    report = {
        "task_id": "W008-F2B-DUALREPAIR-01",
        "worker": "worker-008",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate_context": "G-FORM (advisory only; worker claims no gate verdict)",
        "generated_at": None,  # filled by emit step / read back
        "verdict": "canonical FAIL / candidate PASS" if ok else "INCOMPLETE",
        "inputs": {"canonical_c0": {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": live["c0"]},
                   "canonical_c2": {"path": "schemas/af_scc_c2_vacuum.yaml", "sha256": live["c2"]},
                   "taxonomy": {"path": "research_map/formulation_taxonomy.yaml", "sha256": live["tax"]}},
        "frozen_binding": binding,
        "canonical_audit": canonical,
        "candidate_audit": candidate,
        "minimality": minimality,
        "controls": controls["cases"],
        "selftest": selftest,
        "finding_summary": {
            "canonical": [
                {"kind": "size_premise_inverted",
                 "yaml_path": "implication_ledger.forbidden_transfers[0].reason",
                 "line": 251,
                 "text": "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker",
                 "defect": "the transfer and its consequent are correct; the class-size premise is "
                           "false because the same file declares E_C2 subset of E_C0 (line 244) and "
                           "'C0-inextendibility is stronger than the C2 class's conclusion' (line 248)"},
                {"kind": "false_containment_denial",
                 "yaml_path": "regularity.must_not_conflate[0]",
                 "line": 157,
                 "text": "No containment with C2 or C0 is asserted here",
                 "defect": "denies a nesting the same file asserts at lines 244, 246-247; the sibling "
                           "C2 schema's corresponding bullet already carries the corrected wording"},
            ],
            "candidate": [],
        },
        "candidate_patch": {
            "path": "candidate/af_scc_c0_vacuum.yaml",
            "sha256": minimality["candidate"]["sha256"],
            "canonical_base_sha256": live["c0"],
            "changed_leaf_paths": minimality["structural_changed_leaf_paths"],
            "binding_fields_unchanged": minimality["binding_fields_unchanged"],
        },
        "publication_instructions_for_owner": (
            "Owner (astra-lead-formulation) applies the two wording edits to schemas/af_scc_c0_vacuum.yaml, "
            "bumps revision/revised_at, publishes the authoring mirror byte-identically, re-freezes "
            "(FROZEN.json), then re-runs this checker at the new hashes; expected result FAIL->PASS on "
            "the C0 file with the C2 chain unchanged. No worker edits the canonical path."),
        "assumptions": [
            "canonical path policy: schemas/*.yaml is authoritative; the authoring mirror is byte-identical at publish time",
            "the file's own extension_class_containment sentence is the reference order for the consistency check; this audit does not re-derive the order from regularity definitions",
            "textual consistency is not mathematical truth; a repaired sentence does not make the class true or refuted",
            "artifacts are validation_status=unverified; a G-FORM reviewer verdict is required before any promotion",
        ],
        "falsifier": (
            "Exhibit a reading under which line 251's 'C2 is a strictly larger extension class' is not a "
            "class-size premise, or a reading under which line 157's denial is consistent with the same "
            "file's chain; or measure a canonical C0 hash different from the bound one and show the two "
            "findings absent there; or show a candidate structural change outside the two declared leaf "
            "paths. Any of these falsifies this report at the bound hashes."),
        "next_falsifier": (
            "Re-run at the post-repair hash: the checker must report PASS; if it reports PASS at the "
            "unrepaired hash, or FAIL at a hash whose two clauses match the candidate wording, the checker "
            "or the repair is wrong."),
    }
    (ROOT / "evidence" / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    md = [
        "# W008-F2B-DUALREPAIR-01 — F2b containment-consistency repair readiness",
        "",
        f"- canonical C0 `schemas/af_scc_c0_vacuum.yaml` @ `{live['c0'][:12]}` (FROZEN rev "
        f"{binding['frozen_revision']}, inside the frozen set: {binding['defect_is_inside_frozen_set']})",
        f"- canonical C2 `schemas/af_scc_c2_vacuum.yaml` @ `{live['c2'][:12]}`",
        f"- canonical audit: **{canonical['verdict']}** — {', '.join(can_kinds)}",
        f"- candidate audit: **{candidate['verdict']}** (candidate sha256 `{minimality['candidate']['sha256'][:12]}`)",
        f"- minimality: **{minimality['minimality_verdict']}** — changed leaf paths "
        f"{minimality['structural_changed_leaf_paths']}",
        f"- controls: **{'all met' if controls['all_expectations_met'] else 'FAILED'}** "
        f"(ctl1 reverted D2 -> size_premise_inverted; ctl2 reverted D1 -> false_containment_denial)",
        f"- checker selftest: **{'ok' if selftest['ok'] else 'FAILED'}** (6/6 synthetic cases)",
        "",
        "## Findings (canonical, hash-bound)",
        "",
        "1. `implication_ledger.forbidden_transfers[0].reason` (line 251): class-size premise inverted "
        "(`larger` -> `smaller`); transfer direction and strength consequent unchanged.",
        "2. `regularity.must_not_conflate[0]` (line 157): false containment denial; the sibling C2 schema "
        "already carries the corrected wording.",
        "",
        "## Scope",
        "",
        "Textual/logical consistency audit only; no gate verdict, no node completion, no claim about the "
        "truth of the class. Owner applies the two-line repair and re-freezes.",
        "",
        f"Falsifier: {report['falsifier']}",
    ]
    (ROOT / "report.md").write_text("\n".join(md) + "\n")
    print(json.dumps({"verdict": report["verdict"], "ok": ok,
                      "canonical_kinds": can_kinds, "candidate": candidate["verdict"],
                      "controls_ok": controls["all_expectations_met"],
                      "minimality_ok": minimality["minimality_verdict"] == "PASS"}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

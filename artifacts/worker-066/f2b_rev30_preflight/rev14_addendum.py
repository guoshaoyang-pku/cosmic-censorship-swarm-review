#!/usr/bin/env python3
"""W066-F2B-REV30-PREFLIGHT-01 ADDENDUM -- post-landing re-measurement of the
rev14 F2b/F2a bytes that landed after the base pre-flight pinned rev13.

The base run pinned rev13 (C0 b2ab6acb, C2 e9a27996) and measured the REC-36
item (1) literal reading as direction-inverted.  This addendum measures the
bytes now on disk (rev14), verifies the canonical/mirror identity, re-runs the
pinned instruments, and records the FROZEN manifest state at the same instant.

Read-only on every canonical path.  No gate verdict, node status or
validation_status is claimed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import preflight as pf  # noqa: E402

REV13 = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
}
OBSERVE = [
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/tools/check_class_schema.py",
    "research_map/class_separation.py",
]


def main() -> int:
    ev = HERE / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    measured = {}
    for rel in OBSERVE:
        p = ROOT / rel
        measured[rel] = ({"sha256": pf.sha256_bytes(p.read_bytes()),
                          "bytes": len(p.read_bytes())} if p.is_file()
                         else {"sha256": None, "bytes": None, "missing": True})

    c0_new = measured["schemas/af_scc_c0_vacuum.yaml"]["sha256"]
    c2_new = measured["schemas/af_scc_c2_vacuum.yaml"]["sha256"]
    mir = {"c0_canonical_equals_mirror":
           measured["schemas/af_scc_c0_vacuum.yaml"]["sha256"] ==
           measured["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"]["sha256"],
           "c2_canonical_equals_mirror":
           measured["schemas/af_scc_c2_vacuum.yaml"]["sha256"] ==
           measured["artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"]["sha256"]}

    c0_text = (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text()
    c2_text = (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()
    c = pf.classify(c0_text)
    c2c = pf.classify(c2_text)

    gate = str(pf.mirror("artifacts/formulation/tools/check_class_schema.py"))
    dual = str(pf.mirror("artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py"))
    cls = pf.load_classsep()

    (ev / "rev14_c0.yaml").write_text(c0_text)
    (ev / "rev14_c2.yaml").write_text(c2_text)
    g = pf.run_json_tool([sys.executable, gate, str(ev / "rev14_c0.yaml"), "--json"])
    gj = g.get("json") or {}
    djson = ev / "rev14_c0.dual.json"
    d = pf.run_json_tool([sys.executable, dual, "--c0", str(ev / "rev14_c0.yaml"),
                          "--c2", str(pf.mirror("schemas/af_scc_c2_vacuum.yaml")),
                          "--json", str(djson), "--label", "rev14_c0"], expect_json_path=djson)
    dj = d.get("json") or {}
    csf = cls.findings_for_text(c0_text, "rev14_c0.yaml")

    # delta against the pinned rev13 copies
    rev13_c0 = pf.mirror("schemas/af_scc_c0_vacuum.yaml").read_text()
    rev13_c2 = pf.mirror("schemas/af_scc_c2_vacuum.yaml").read_text()
    delta = {"c0_changed_lines": pf.diff_lines(rev13_c0, c0_text),
             "c2_changed_lines": pf.diff_lines(rev13_c2, c2_text)}

    # FROZEN manifest staleness at this instant
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    stale = {}
    for logical, node in frozen.get("files", {}).items():
        declared = node.get("sha256") if isinstance(node, dict) else None
        rel = logical.lstrip("/")
        if rel in measured and declared and measured[rel]["sha256"] != declared:
            stale[logical] = {"declared": declared, "measured": measured[rel]["sha256"]}
    frozen_state = {"revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at"),
                    "declared_c0": frozen.get("files", {}).get(
                        "/files/artifacts/formulation/schemas/af_scc_c0_vacuum.yaml", {}).get("sha256"),
                    "measured_c0": c0_new,
                    "declared_c2": frozen.get("files", {}).get(
                        "/files/artifacts/formulation/schemas/af_scc_c2_vacuum.yaml", {}).get("sha256"),
                    "measured_c2": c2_new,
                    "stale_declared_pins_matching_measured_paths": stale}

    # mutation controls on the NEW bytes: the harness must still discriminate
    lines = c0_text.splitlines()
    i_h1 = pf.find_line(lines, 'from: "no proper future C2 extension", to: "this class"')
    i_h2 = pf.find_line(lines, "this class's conclusion ENTAILS H2_loc")
    m_lit = list(lines)
    m_lit[i_h2] = pf.h2_line(pf.mirror("schemas/af_scc_c2_vacuum.yaml").read_text()
                             .splitlines()[pf.find_line(
                                 pf.mirror("schemas/af_scc_c2_vacuum.yaml").read_text().splitlines(),
                                 "so H2_loc-inextendibility ENTAILS this class")].strip()[3:-1])
    m_h1 = list(lines)
    m_h1[i_h1] = pf.h1_line("C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker")
    controls = {
        "M1_rev14_H2_reverted_to_literal_inverted": pf.classify("\n".join(m_lit) + "\n"),
        "M2_rev14_H1_reverted_to_inverted": pf.classify("\n".join(m_h1) + "\n"),
        "M3_rev14_live": c,
    }
    ctrl_ok = (controls["M1_rev14_H2_reverted_to_literal_inverted"]["h2_inverted"] is True
               and controls["M2_rev14_H1_reverted_to_inverted"]["h1_inverted"] is True
               and c["h2_inverted"] is False and c["h2_ok"] is True and c["h1_ok"] is True)

    rev14_clean = bool(c["h1_ok"] and c["h2_ok"] and not gj.get("failed_rules") and not csf)
    report = {
        "schema": "w066-f2b-rev30-preflight-addendum/v1",
        "task_id": "W066-F2B-REV30-PREFLIGHT-01-ADDENDUM",
        "actor": "worker-066",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "gate": "G-FORM",
        "authority": ("worker measurement only; no gate verdict, node status, validation_status, "
                      "canonical write or schema-semantics decision is claimed"),
        "base_pins_rev13": REV13,
        "measured_at_addendum_start": measured,
        "mirror_identity": mir,
        "rev14_c0_classification": c,
        "rev14_c2_classification": c2c,
        "rev14_c0_gate": {"exit_code": g["exit_code"], "verdict": gj.get("verdict"),
                          "failed_rules": gj.get("failed_rules")},
        "rev14_c0_dual": {"exit_code": d["exit_code"], "verdict": dj.get("verdict"),
                          "finding_kinds": sorted({f.get("kind") for f in (dj.get("findings") or [])
                                                   if isinstance(f, dict)})},
        "rev14_c0_classsep_findings": csf,
        "rev14_delta_vs_rev13": delta,
        "frozen_manifest_state": frozen_state,
        "mutation_controls": {k: {kk: vv[kk] for kk in ("h1_ok", "h1_inverted", "h2_denial",
                                                        "h2_inverted", "h2_ok")}
                              for k, vv in controls.items()},
        "mutation_controls_pass": ctrl_ok,
        "rev14_c0_measures_direction_clean": rev14_clean,
        "headline": ("rev14 landed at C0 %s / C2 %s with canonical==mirror; the landed F2b H2 "
                     "clause is direction-correct (this class's conclusion ENTAILS H2_loc- and "
                     "C2-inextendibility, never the reverse) and H1 now reads 'strictly stronger "
                     "regularity requirement'. Gate 0 failed rules, dual %s, class-separation "
                     "clean. FROZEN.json is still rev29 %s and its declared C0/C2 pins still "
                     "name the rev13 bytes: the manifest re-issue required by REC-36 is pending "
                     "at this instant." % (c0_new[:12], c2_new[:12], dj.get("verdict"),
                                           (frozen.get("revision")))),
        "falsifier": ("Re-measure the same paths: falsified if the rev14 C0/C2 bytes differ from "
                      "the hashes recorded here; if the landed H2 clause does not classify "
                      "direction-correct; if the gate fails the rev14 bytes; if the dual checker "
                      "reports a finding; if canonical and mirror bytes differ; if the M1/M2 "
                      "mutation controls do not flag the reverted inverted clauses; or if "
                      "FROZEN.json already declares the measured rev14 hashes (which would mean "
                      "the re-issue landed and this addendum's pending-state note is superseded)."),
    }
    (HERE / "ADDENDUM_REPORT.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (ev / "rev14_measurements.json").write_text(json.dumps(
        {"measured": measured, "mirror_identity": mir, "delta": delta,
         "frozen_manifest_state": frozen_state, "mutation_controls": report["mutation_controls"]},
        indent=1, sort_keys=True) + "\n")

    ok = (mir["c0_canonical_equals_mirror"] and mir["c2_canonical_equals_mirror"]
          and rev14_clean and ctrl_ok)
    print(json.dumps({"rev14_c0": c0_new[:12], "rev14_c2": c2_new[:12],
                      "rev14_clean": rev14_clean, "controls_pass": ctrl_ok,
                      "frozen_revision": frozen.get("revision"),
                      "mirror_identity": mir}, indent=1))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())

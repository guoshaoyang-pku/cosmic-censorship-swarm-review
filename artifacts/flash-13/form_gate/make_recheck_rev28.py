#!/usr/bin/env python3
"""Build the rev28 canonical recheck record for FORM-GATE-01 (G-CLASSBIND).

Reads the three artifacts produced by this iteration, the gate, the probe, both control
reports and FROZEN.json, and writes a single hash-bound record. No self-hash: the record's
sha256 is carried by the artifact event that publishes it (same convention as FROZEN.json).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "canonical_recheck_rev28.json"
TS = datetime.now().strftime("%Y%m%dT%H%M%S")
PREFIX = f"f13-fg6-{TS}"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
gate_report = json.loads((HERE / "gate_report_rev28.json").read_text())
fixtures = json.loads((HERE / "fixture_suite_report.json").read_text())
probe = json.loads((HERE / "f1_tail_visibility_probe_rev28.json").read_text())

publication = {
    "canonical_dir": "schemas/",
    "authoring_dir": "artifacts/formulation/schemas/",
    "byte_identical": all(
        sha(ROOT / p) == sha(ROOT / q)
        for p, q in [
            ("schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
            ("schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
            ("schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
        ]
    ),
}

record = {
    "actor": "deepseek-flash-13",
    "task_id": "F13-G-CLASSBIND-REV28-RECHECK",
    "task": ("Independent executable class-schema gate re-verdict at the F1/F2a/F2b rev12 "
             "canonical hashes, plus the lead's declared F1 next-falsifier probe (tail "
             "visibility predicate vs quantifiers.formal). Bounded worker task, no gate self-pass."),
    "assignment_source": ("No new lead assignment card exists for deepseek-flash-13 (last card: "
                          "astra-numfix-02, closed 00:09; FORM-GATE-01 assign-FORM-GATE-01-20260911T2331 "
                          "remains the standing class-bound assignment). Trigger: lead-form-20260912T003626-00/01/02 "
                          "'Prior verdicts are superseded; re-review required at the new hash.'"),
    "gate_id": "G-CLASSBIND",
    "node_id": "F1",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "canonical_revision": "rev12 (F1 cce9c60146d6 / F2a 5476a3f2c6bc / F2b 55d0a1ea9bda)",
    "frozen_manifest": {
        "path": "artifacts/formulation/FROZEN.json",
        "sha256": sha(ROOT / "artifacts/formulation/FROZEN.json"),
        "revision": frozen.get("revision"),
        "frozen_at": frozen.get("frozen_at"),
    },
    "gate": {
        "path": "artifacts/flash-13/form_gate/check_class_schema.py",
        "sha256": sha(HERE / "check_class_schema.py"),
        "version": gate_report.get("gate_version"),
        "revision_note": gate_report["results"][0].get("gate_revision"),
        "spec": gate_report.get("spec"),
    },
    "published_rule_text": {
        "path": "artifacts/formulation/rule_spec.json",
        "sha256": sha(ROOT / "artifacts/formulation/rule_spec.json"),
        "spec_version": json.loads((ROOT / "artifacts/formulation/rule_spec.json").read_text()).get("spec_version"),
        "rule_ids": [f"R{i:02d}" for i in range(1, 17)],
    },
    "artifacts": {
        "gate_report_rev28.json": sha(HERE / "gate_report_rev28.json"),
        "fixture_suite_report.json": sha(HERE / "fixture_suite_report.json"),
        "f1_tail_visibility_probe.py": sha(HERE / "f1_tail_visibility_probe.py"),
        "f1_tail_visibility_probe_rev28.json": sha(HERE / "f1_tail_visibility_probe_rev28.json"),
        "canonical_recheck_rev20.json": sha(HERE / "canonical_recheck_rev20.json"),
    },
    "results": [
        {
            "class_id": r["class_id"],
            "path": "schemas/" + ("af_wcc_vacuum.yaml" if r["class_id"] == "AF-WCC-VAC-GEN"
                                  else "af_scc_c2_vacuum.yaml" if r["class_id"] == "AF-SCC-C2-VAC-GEN"
                                  else "af_scc_c0_vacuum.yaml"),
            "sha256": r["sha256"],
            "frozen_match": r["frozen_match"],
            "verdict": r["verdict"],
            "per_rule": {k: v["status"] for k, v in r["per_rule"].items()},
        }
        for r in gate_report["results"]
    ],
    "gate_report_verdict": gate_report.get("verdict"),
    "fixture_suite": fixtures.get("summary"),
    "tail_visibility_probe": {
        "verdict": probe.get("verdict"),
        "target_sha256": probe["target"]["sha256"],
        "checks_passed": sum(1 for c in probe["checks"] if c["status"] == "pass"),
        "checks_total": len(probe["checks"]),
        "whole_curve_residue_scan": {
            "flagged": probe["whole_curve_residue_scan"]["flagged_count"],
            "exempted": probe["whole_curve_residue_scan"]["exempted_count"],
            "variant_contexts": probe["whole_curve_residue_scan"]["variant_context_count"],
        },
        "finite_model_control": probe["finite_model_control"]["counts"],
        "self_controls": probe["self_controls"],
    },
    "publication": publication,
    "open_blocker": ("F-GATE-4 remains open: the published rule_spec.json is spec_version 1.2 "
                     "with R01-R16 only, while the lead's canonical tool enforces R17-R31 with no "
                     "published rule text; this gate is bounded to R01-R16 and cannot be compared "
                     "at parity. Not re-measured this iteration."),
    "falsifier": (
        "a rev12 canonical schema failing any R01-R16 check under this gate; a single-rule mutant "
        "accepted by the fixture suite; a frozen-hash change without a FROZEN.json revision bump; a "
        "class_contract_pointer that does not resolve in canonical taxonomy 0abb9ed8a961; a normative "
        "visibility slot at F1 cce9c60146d6 that is not the tail form; a whole-curve residue outside an "
        "exempted contrast sentence or the registered SET variant; or a finite model where whole-curve "
        "containment holds while the tail predicate fails"
    ),
    "next_falsifier": (
        "an independent reviewer exhibiting a spacetime (not abstract model) classified differently "
        "under quantifiers.formal and the tail visibility predicate at F1 cce9c60146d6, or publishing "
        "R17+ so the parity gap can be closed"
    ),
    "not_claimed": [
        "no gate verdict and no gate self-pass; G-CLASSBIND stays pending and this is reviewer evidence",
        "no node completion; F1/F2a/F2b stay active",
        "validation_status of every artifact in this record is unverified",
        "the tail probe is structural/order-theoretic; it constructs no spacetime",
    ],
    "events": [
        f"{PREFIX}-art-gatereport",
        f"{PREFIX}-art-fixturesuite",
        f"{PREFIX}-art-tailprobedriver",
        f"{PREFIX}-art-tailprobe",
        f"{PREFIX}-art-recheck",
        f"{PREFIX}-claim",
        f"{PREFIX}-status",
        f"{PREFIX}-gate-proposal",
    ],
    "event_prefix": PREFIX,
}

OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "sha256": sha(OUT)}, indent=1))

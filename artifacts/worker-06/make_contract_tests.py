#!/usr/bin/env python3
"""Author the canonical semantic contract-test suite for assignment astra-w06-01.

Copies the frozen W06 semantic corpus (32 leak mutants + 3 controls) into
schemas/semantic_contract_tests/fixtures/ and writes the contract manifest that
maps every fixture to the rule(s) it tests, its expected verdict, and a slot for
the observed verdict (filled by run_contract_tests.py).

The originals under artifacts/worker-06/semantic_fixtures/ are left byte-identical:
earlier reports and event evidence_refs are hash-bound to them, so "move" is
implemented as relocate-with-provenance (see manifest.provenance.relocation_note).

No gate id is created. G-CLASSBIND proposals are folded into G-AUDIT as
calibration evidence, per assignment astra-w06-01.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SOURCE = HERE / "semantic_fixtures"
DEST = ROOT / "schemas" / "semantic_contract_tests"
FIXTURES = DEST / "fixtures"
CONTROLS = FIXTURES / "controls"

CLASS_UNDER_TEST = "AF-SCC-C0-VAC-GEN"
CLASS_IDS = ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-WCC-VAC-GEN"]


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse_hardened_rules() -> list[dict]:
    """Extract H01-H17 rows from HARDENED_RULES.md (primary artefact, not retyped)."""
    rows = []
    text = (HERE / "HARDENED_RULES.md").read_text()
    for line in text.splitlines():
        m = re.match(r"\|\s*(H\d\d)\s*\|\s*(R\d\d)\s*\|(.*?)\|(.*?)\|(.*?)\|\s*$", line)
        if m:
            hid, maps_to, delta, examples, fp_note = (x.strip() for x in m.groups())
            rows.append({
                "item_id": f"ADJ-{hid}",
                "rule_id": hid,
                "maps_to_spec_rule": maps_to,
                "delta": delta,
                "example_fixtures": [e.strip() for e in examples.split(",") if e.strip()],
                "false_positive_note": fp_note,
                "status": "proposed_not_adopted",
                "adjudication_required": True,
                "owner": "astra-lead-formulation",
                "evidence_refs": ["artifacts/worker-06/HARDENED_RULES.md",
                                  "artifacts/worker-06/blindspot_report.json"],
            })
    return rows


def main():
    src_manifest_path = SOURCE / "manifest.json"
    src = json.loads(src_manifest_path.read_text())
    report = json.loads((HERE / "blindspot_report.json").read_text())
    per_fixture = {r["fixture"]: r for r in report.get("per_fixture", [])}

    if DEST.exists():
        shutil.rmtree(DEST)
    FIXTURES.mkdir(parents=True)
    CONTROLS.mkdir(parents=True)

    def copy_fixture(rel: str, dst: Path):
        s = SRC_ROOT / rel
        dst.write_bytes(s.read_bytes())
        return sha(dst), sha(s)

    SRC_ROOT = ROOT

    fixtures = []
    for i, e in enumerate(src["fixtures"], 1):
        name = e["fixture"]
        dst = FIXTURES / name
        dsha, ssha = copy_fixture(e["path"], dst)
        rep = per_fixture.get(name, {})
        fixtures.append({
            "test_id": f"SCT-M{i:03d}",
            "kind": "leak_mutant",
            "fixture": f"fixtures/{name}",
            "sha256": dsha,
            "class_under_test": CLASS_UNDER_TEST,
            "class_ids_covered": CLASS_IDS,
            "rules_tested": e.get("expected_rules", []),
            "leak_family": e.get("leak_family"),
            "s1_class": e.get("s1_class"),
            "rephrased": bool(e.get("rephrased")),
            "expected_verdict": "reject",
            "mutation": e.get("mutation"),
            "proposed_repair": e.get("repair"),
            "hardened_caught": rep.get("hardened_caught"),
            "hardened_failed_rules": rep.get("hardened_failed_rules", []),
            "observed": None,
            "source_fixture": e["path"],
            "source_sha256": ssha,
        })

    controls = []
    for i, e in enumerate(src["controls"], 1):
        name = e["fixture"]
        dst = CONTROLS / name
        dsha, ssha = copy_fixture(e["path"], dst)
        controls.append({
            "test_id": f"SCT-C{i:02d}",
            "kind": "frozen_control",
            "fixture": f"fixtures/controls/{name}",
            "sha256": dsha,
            "class_under_test": CLASS_UNDER_TEST,
            "rules_tested": [],
            "expected_verdict": "accept",
            "note": e.get("note"),
            "observed": None,
            "source_fixture": e["path"],
            "source_sha256": ssha,
            "frozen_base_sha256": src.get("base_sha256"),
        })

    conforming = []
    for i, rel in enumerate(["schemas/af_scc_c0_vacuum.yaml",
                             "schemas/af_scc_c2_vacuum.yaml",
                             "schemas/af_wcc_vacuum.yaml"], 1):
        conforming.append({
            "test_id": f"SCT-K{i:02d}",
            "kind": "conforming_canonical",
            "fixture": rel,
            "sha256": sha(ROOT / rel),
            "expected_verdict": "accept",
            "observed": None,
            "note": "current canonical schema at build time; not a copy",
        })

    hardened = parse_hardened_rules()
    adjudication = [{
        "item_id": "ADJ-CONTROL-STALENESS",
        "status": "needs_lead_decision",
        "owner": "astra-lead-formulation",
        "finding": ("the three frozen controls were authored against corpus base "
                    f"{src.get('base_sha256', '?')[:12]}; the current canonical C0 moved the "
                    "finite_codimension_complement -> residual_comeager row from transfer_failures to "
                    "transfer_holds, so canonical gate rule R28 rejects all three controls. "
                    "The control basis for any current-revision run is therefore invalid until the "
                    "lead either rebases the controls to the current canonical layouts or pins the "
                    "gate revision used for calibration."),
        "evidence_refs": ["artifacts/worker-06/semantic_fixtures/manifest.json",
                          "schemas/af_scc_c0_vacuum.yaml",
                          "artifacts/formulation/tools/check_class_schema.py"],
        "falsifier": ("a run of the frozen controls against the current binding gate that accepts all "
                      "three, or a canonical C0 whose transfer_holds places that row in transfer_failures"),
    }]
    adjudication += hardened
    adjudication += [
        {"item_id": "ADJ-SEM-1", "status": "non_machine_checkable",
         "owner": "astra-lead-formulation",
         "finding": "SEM-1: no mechanical rule decides non-meagerness of the extendible set.",
         "falsifier": "a decidable criterion for non-meagerness that two independent readers resolve identically"},
        {"item_id": "ADJ-SEM-2", "status": "non_machine_checkable",
         "owner": "astra-lead-formulation",
         "finding": "SEM-2: whether a wording leak changes the mathematical class cannot be decided by the runner.",
         "falsifier": "a class-change witness that is machine-checkable per leak family"},
        {"item_id": "ADJ-SEM-3", "status": "out_of_scope",
         "owner": "astra-lead-audit",
         "finding": "SEM-3: truth, non-vacuity and physical correctness of a schema are out of scope for any structural gate.",
         "falsifier": "not falsifiable by a structural corpus; requires the numerics/audit gates"},
    ]

    manifest = {
        "suite_id": "SEM-CONTRACT-TESTS",
        "assignment": "astra-w06-01",
        "author": "worker-06 (deepseek-flash-06)",
        "created_at": now(),
        "status": "unverified worker artifact; lead-formulation decides rule adoption rule by rule",
        "gate_routing": {
            "g_classbind": "not adopted as a separate gate id",
            "folded_into": "G-AUDIT",
            "role": "calibration_evidence",
        },
        "provenance": {
            "source_corpus": "artifacts/worker-06/semantic_fixtures/",
            "source_manifest": "artifacts/worker-06/semantic_fixtures/manifest.json",
            "source_manifest_sha256": sha(src_manifest_path),
            "relocation_note": ("fixtures copied byte-identically to this canonical location; originals retained "
                                "because prior reports and event evidence_refs are hash-bound to them"),
            "rules_version": src.get("rules_version"),
            "corpus_base": src.get("base"),
            "corpus_base_sha256": src.get("base_sha256"),
        },
        "stages": {
            "structural": {
                "tool": "artifacts/formulation/tools/check_class_schema.py",
                "sha256_at_build": sha(ROOT / "artifacts/formulation/tools/check_class_schema.py"),
                "invocation": "python3 artifacts/formulation/tools/check_class_schema.py --json <fixture>",
            },
            "semantic_baseline": {
                "tool": "artifacts/worker-06/spec_conformance_audit.py",
                "sha256_at_build": sha(HERE / "spec_conformance_audit.py"),
                "invocation": "python3 artifacts/worker-06/spec_conformance_audit.py <fixture> --json <out>",
            },
            "semantic_hardened": {
                "tool": "artifacts/worker-06/spec_conformance_audit.py",
                "sha256_at_build": sha(HERE / "spec_conformance_audit.py"),
                "invocation": "python3 artifacts/worker-06/spec_conformance_audit.py <fixture> --hardened --json <out>",
            },
        },
        "fixtures": fixtures,
        "controls": controls,
        "conforming_canonical_controls": conforming,
        "adjudication_items": adjudication,
        "run_record": None,
    }
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    shutil.copy2(HERE / "run_contract_tests.py", DEST / "run_contract_tests.py")
    print(f"wrote {DEST/'manifest.json'} and {DEST/'run_contract_tests.py'}")
    print(f"fixtures: {len(fixtures)} mutants, {len(controls)} frozen controls, "
          f"{len(conforming)} conforming canonical controls, {len(adjudication)} adjudication items")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Assemble artifacts/worker-038/f0_conformance/report.json from the run outputs.

Reads: run_manifest.txt, worker01_validation.json, independent_checks.json.
Writes: report.json (and prints a short summary). Idempotent.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = D.parents[2]


def sha(p: str) -> str:
    h = hashlib.sha256()
    with (ROOT / p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    manifest = (D / "run_manifest.txt").read_text()
    run_at = re.search(r"run_at=(\S+)", manifest).group(1)
    commands = re.findall(r"^(\S+) exit=(\d+)$", manifest, re.M)
    pins_before, pins_after = {}, {}
    section = None
    for line in manifest.splitlines():
        if line.startswith("### PINS"):
            section = pins_before if line.strip() == "### PINS (sha256 at run time)" else pins_after
            continue
        if section is not None and re.match(r"^[0-9a-f]{64}  ", line):
            h, p = line.split("  ", 1)
            section[p.strip()] = h
    checker = json.loads((D / "worker01_validation.json").read_text())
    indep = json.loads((D / "independent_checks.json").read_text())

    report = {
        "task": "W038-F0-CONFORMANCE-01",
        "worker": "worker-038",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": indep["class_ids"],
        "reviewed_at": run_at,
        "reviewed_revision": {"path": "research_map/formulation_taxonomy.yaml",
                              "sha256": pins_before["research_map/formulation_taxonomy.yaml"],
                              "revision_field": 4,
                              "status_field": "draft_unverified"},
        "pins": {
            "before": pins_before,
            "after": pins_after,
            "stable_across_run": pins_before == pins_after,
            "declared_checker": f"artifacts/worker-01/validate_taxonomy.py#{pins_before['artifacts/worker-01/validate_taxonomy.py']}",
            "supplement": f"artifacts/formulation/formulation_taxonomy.yaml#{pins_before['artifacts/formulation/formulation_taxonomy.yaml']}",
            "rubric": f"evaluation_rubric.yaml#{pins_before['evaluation_rubric.yaml']}",
            "frozen_manifest": f"artifacts/formulation/FROZEN.json#{pins_before['artifacts/formulation/FROZEN.json']}",
        },
        "commands": [{"name": n, "exit_code": int(c)} for n, c in commands],
        "declared_checker_run": {
            "path": "artifacts/worker-01/validate_taxonomy.py",
            "sha256": pins_before["artifacts/worker-01/validate_taxonomy.py"],
            "checks_passed": checker.get("checks_passed"),
            "checks_failed": checker.get("checks_failed"),
            "cases_checked": checker.get("cases_checked"),
            "verdict": checker.get("verdict"),
            "note": ("author-family tooling (its author drafted F0), executed here in a fresh process at "
                     "the pinned bytes; treated as one input, not as the independent verdict"),
        },
        "independent_checks": {
            "path": "artifacts/worker-038/f0_conformance/check_f0_independent.py",
            "sha256": pins_before["artifacts/worker-038/f0_conformance/check_f0_independent.py"],
            "summary": indep["summary"],
            "checks": indep["checks"],
        },
        "verdict": indep["verdict"],
        "verdict_scope": ("independent worker evidence on the machine-checkable G-F0 criteria "
                          "(four separate class ids, 6/6 recomputed disjointness pairs, G2/G3, "
                          "FROZEN pin, canonical/supplement role separation, rubric axis cross-check); "
                          "NOT a gate verdict, NOT a node-completion claim, NOT a physics judgement"),
        "residual_observations": [
            {"id": "OBS-01", "status": "non_blocking",
             "text": ("conclusion-label vocabulary differs across artifacts: A0 rubric conclusion_primary "
                      "'future_asymptotic_predictability' vs F0 conclusion_type 'weak_cosmic_censorship'; "
                      "F1 records the equivalence as UNVERIFIED. Cross-artifact vocabulary, not a G-F0 "
                      "criterion failure; carry it into any A1/G-FORM verdict.")},
            {"id": "OBS-02", "status": "by_design",
             "text": ("genericity_kind is provisional_baire_residual for the three vacuum classes and "
                      "unresolved for AF-WCC-SCALAR-SPH, and every class carries unresolved hypotheses "
                      "owned by F1/F2/L1. This is honest placeholder status in a draft_unverified file, "
                      "not a claim, and it is not a G-F0 criterion failure.")},
            {"id": "OBS-03", "status": "declared_gap",
             "text": ("coverage_gaps CG1 declares that AF-WCC-SCALAR-SPH has no F-node; the taxonomy "
                      "records the gap rather than hiding it.")},
        ],
        "falsifier": indep["falsifier"],
        "claims_not_made": indep["claims_not_made"] + [
            "no claim that validate_taxonomy.py is a sufficient G-F0 acceptance test",
        ],
        "authority_note": indep["authority_note"],
        "independence": ("reviewer worker-038 is not an author of research_map/formulation_taxonomy.yaml, "
                         "artifacts/formulation/formulation_taxonomy.yaml, evaluation_rubric.yaml, "
                         "FROZEN.json, artifacts/worker-01/validate_taxonomy.py, or any F1/F2 schema; "
                         "the reviewer's only other work in this swarm is the A0 validator-mechanism check."),
        "evidence_refs": [
            f"research_map/formulation_taxonomy.yaml#{pins_before['research_map/formulation_taxonomy.yaml']}",
            f"artifacts/worker-01/validate_taxonomy.py#{pins_before['artifacts/worker-01/validate_taxonomy.py']}",
            f"artifacts/worker-038/f0_conformance/check_f0_independent.py#{pins_before['artifacts/worker-038/f0_conformance/check_f0_independent.py']}",
            f"artifacts/formulation/FROZEN.json#{pins_before['artifacts/formulation/FROZEN.json']}",
            f"evaluation_rubric.yaml#{pins_before['evaluation_rubric.yaml']}",
        ],
    }
    (D / "report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(D / "report.json"), "verdict": report["verdict"],
                      "sha256": sha("artifacts/worker-038/f0_conformance/report.json")}, indent=1))


if __name__ == "__main__":
    main()

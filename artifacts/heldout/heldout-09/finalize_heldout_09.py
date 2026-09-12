#!/usr/bin/env python3
"""FORM-HELDOUT-09 findings annotation + hash re-binding (worker-084).

Adds the interpretation block to report.json (measurement verdicts are NOT changed) and
re-binds report.json / checkpoint.json to the findings artifact.  Run once after
run_heldout_09.py has produced report.json and checkpoint.json.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    raw = json.loads((HERE / "raw" / "raw_verdicts.json").read_text())
    a = report["aggregates"]
    ia = report["aggregates_informative_arms_only"]
    man_sha = report["manifest_sha256_before_run"]
    raw_sha = sha(HERE / "raw" / "raw_verdicts.json")

    wcc = [x for x in raw["results"] if x["arm"] == "W"]
    wcc_details = sorted({d["detail"] for x in wcc for d in x["stage_b"]["failed_checks"]})
    escape_families = [f["family"] for f in a["escape_families"]]

    findings = {
        "finding_id": "w084-heldout09-findings",
        "corpus_id": "FORM-HELDOUT-09",
        "task_id": "FORM-HELDOUT-09",
        "assignment": report["assignment"],
        "worker": report["worker"], "actor": report["actor"],
        "node_id": report["node_id"], "gate": report["gate"],
        "class_ids": report["class_ids"],
        "created_at": now(),
        "status": "independent measurement evidence; no gate verdict, no node completion, no theorem",
        "headline": (
            "On the rev12/FROZEN rev28 frozen bytes the two-stage pipeline's H5 control set fails: "
            "stage B rejects the frozen AF-WCC-VAC-GEN canonical on R03, so the run is INVALID as a "
            "whole. On the two informative arms (C2+C0) the union of both stages catches 0 of 24 "
            "semantic leaks (union escape 1.0) while all authored controls pass both stages."),
        "findings": [
            {
                "id": "W084-F1",
                "severity": "hard",
                "kind": "pipeline calibration / H5 control failure",
                "statement": (
                    "The frozen canonical schemas/af_wcc_vacuum.yaml (sha256 cce9c60146d6) is rejected "
                    "by stage B (spec_conformance_audit.py c79d8ab8440a) on R03: 'binder '(q,t0)' absent "
                    "from formal sentence'. Stage B requires every quantifiers.ordered binder to occur as "
                    "a literal substring of quantifiers.formal; the canonical formal sentence writes the "
                    "D5 binder as 'q in I+ and t0 in [0,T)' instead of the parenthesised token '(q,t0)'. "
                    "Stage A accepts the same bytes. This is a formatting false positive, not a class defect."),
                "consequence": (
                    "H5 is false, valid=false, and the 5 WCC-arm mutants are 'caught' by stage B for a "
                    "reason unrelated to their mutations; the WCC arm is non-informative (format-dominated)."),
                "evidence_refs": [
                    "artifacts/heldout/heldout-09/report.json",
                    "artifacts/heldout/heldout-09/raw/raw_verdicts.json#" + raw_sha[:12],
                    "schemas/af_wcc_vacuum.yaml#" + report["pins"]["schemas/af_wcc_vacuum.yaml"][:12],
                ],
                "observed_rule_details": wcc_details,
            },
            {
                "id": "W084-F2",
                "severity": "hard",
                "kind": "measured union escape (informative arms)",
                "statement": (
                    f"Informative arms AF-SCC-C2-VAC-GEN + AF-SCC-C0-VAC-GEN (canonical controls accepted "
                    f"by both stages): {ia['mutants']} mutants across {len(ia['escape_families'])} families, "
                    f"union escape {ia['union_escape']} (structural {ia['structural_escape']}, semantic "
                    f"{ia['semantic_escape']}); stage A catches {ia['structural_caught']}, stage B catches "
                    f"{ia['semantic_caught']}."),
                "consequence": (
                    "Every one of the 24 semantic class-violations built on the frozen rev28 C2/C0 bytes "
                    "passes both stages. The pipeline's union has no measured coverage of these axes at "
                    "the pinned hashes."),
                "escaping_families": escape_families,
                "evidence_refs": [
                    "artifacts/heldout/heldout-09/report.json",
                    "artifacts/heldout/heldout-09/raw/raw_verdicts.json#" + raw_sha[:12],
                    "artifacts/heldout/heldout-09/manifest.json#" + man_sha[:12],
                ],
            },
            {
                "id": "W084-F3",
                "severity": "info",
                "kind": "control calibration",
                "statement": (
                    "All 4 authored controls (2 conforming rephrases, 2 negated-phrase quotations in "
                    "anti_scope) are accepted by BOTH stages: c01_conforming_c2_polished, "
                    "c02_conforming_c0_polished, c03_quoted_wcc_phrase_c2, c04_quoted_composite_c0. The "
                    "C2/C0 frozen canonicals are accepted by both stages. Only the WCC frozen canonical "
                    "fails (W084-F1), so the failure is class-specific, not corpus-wide format domination."),
                "evidence_refs": [
                    "artifacts/heldout/heldout-09/report.json",
                    "artifacts/heldout/heldout-09/raw/raw_verdicts.json#" + raw_sha[:12],
                ],
            },
            {
                "id": "W084-F4",
                "severity": "info",
                "kind": "pipeline coverage shape",
                "statement": (
                    "Stage A (structural, 000e09e46b2f) escaped 29/29 mutants and Stage B (semantic, "
                    "c79d8ab8440a) escaped 24/29; the 5 semantic catches are the WCC-arm fixtures that "
                    "inherit the W084-F1 base rejection. No mutant was caught on its own axis by either "
                    "stage in this corpus."),
                "evidence_refs": [
                    "artifacts/heldout/heldout-09/raw/raw_verdicts.json#" + raw_sha[:12],
                ],
            },
        ],
        "falsifier": report["falsifier"],
        "stop_rule": report["stop_rule"],
        "do_not_claim": report["do_not_claim"],
        "budget": {"budget_agent_hours": 3.0,
                   "hours_used_estimate": 0.5,
                   "note": "measurement run itself 6 s; estimate covers recon, corpus authoring, run, comms"},
    }
    (HERE / "findings.json").write_text(json.dumps(findings, indent=2) + "\n")
    findings_sha = sha(HERE / "findings.json")

    report["analysis_ref"] = {
        "path": "artifacts/heldout/heldout-09/findings.json", "sha256": findings_sha,
        "note": "interpretation only; measurement verdicts in this report are unchanged",
    }
    report["stage_b_wcc_r03_control_failure"] = {
        "control": "schemas/af_wcc_vacuum.yaml",
        "class_id": "AF-WCC-VAC-GEN",
        "stage_a": "pass", "stage_b": "reject", "failed_rules": ["R03"],
        "detail": wcc_details,
        "diagnosis": ("literal-substring binder check in stage B R03 vs the canonical parenthesised "
                      "binder '(q,t0)' written as 'q in I+ and t0 in [0,T)' in quantifiers.formal"),
        "effect": "H5 control failure -> valid=false; WCC arm non-informative",
    }
    report["hours_used_estimate"] = 0.5
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    report_sha = sha(HERE / "report.json")

    ck = json.loads((HERE / "checkpoint.json").read_text())
    ck["report_sha256"] = report_sha
    ck["findings_sha256"] = findings_sha
    ck["analysis_ref"] = report["analysis_ref"]
    ck["stage_b_wcc_r03_control_failure"] = report["stage_b_wcc_r03_control_failure"]
    ck["hours_used_estimate"] = 0.5
    ck["artifacts"]["findings"] = "artifacts/heldout/heldout-09/findings.json"
    (HERE / "checkpoint.json").write_text(json.dumps(ck, indent=2) + "\n")

    print(json.dumps({"report_sha256": report_sha, "findings_sha256": findings_sha,
                      "raw_verdicts_sha256": raw_sha, "manifest_sha256": man_sha,
                      "checkpoint_sha256": sha(HERE / "checkpoint.json")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

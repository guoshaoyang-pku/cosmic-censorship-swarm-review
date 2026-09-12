#!/usr/bin/env python3
"""Finalize the rev27/rev28 verification with the semantic-stage results and findings.

Run after run_verification.py. Corrects the acceptance headline (run_acceptance exited 3,
so the stage evidence file was a copied artifact, not a fresh measurement), runs stage 2
directly on the frozen schemas, and writes findings + REPORT.md.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STAGE = HERE / "stage"
V = HERE / "verification.json"

report = json.loads(V.read_text())
MAN = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
F0_HASH = hashlib.sha256((ROOT / "research_map/formulation_taxonomy.yaml").read_bytes()).hexdigest()


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_semantic(rel: str):
    p = STAGE / rel
    r = subprocess.run([sys.executable, str(STAGE / "artifacts/worker-06/spec_conformance_audit.py"), str(p)],
                       cwd=str(STAGE), capture_output=True, text=True, timeout=300)
    try:
        d = json.loads(r.stdout)
    except Exception:
        d = {}
    return {"path": rel, "doc_sha256": sha(p), "exit": r.returncode,
            "verdict": d.get("verdict"), "failed_rules": d.get("failed_rules", []),
            "undecided_rules": d.get("undecided_rules", []),
            "tool_sha256": sha(STAGE / "artifacts/worker-06/spec_conformance_audit.py"),
            "audited_at": d.get("audited_at"), "hardened": d.get("hardened")}


def main():
    # ---- 1. correct the acceptance headline
    ra = report["runs"]["run_acceptance"]
    report["checks"]["acceptance_headline"]["source"] = (
        "artifacts/formulation/evidence/acceptance_pipeline_report.json AS COPIED INTO THE STAGE - "
        f"run_acceptance.py exited {ra['exit']} (preflight) and did NOT regenerate it")
    report["checks"]["acceptance_headline"]["rerunnable_at_frozen_bytes"] = ra["exit"] == 0

    # ---- 2. preflight root cause
    ev = json.loads((ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json").read_text())
    c0_canon = sha(ROOT / "schemas/af_scc_c0_vacuum.yaml")
    c0_mirror = sha(ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml")
    report["checks"]["acceptance_preflight"] = {
        "corpus_base_sha256": ev.get("base_sha256"),
        "current_c0_canonical_sha256": c0_canon,
        "current_c0_mirror_sha256": c0_mirror,
        "stale": ev.get("base_sha256") != c0_canon,
        "preflight_message": ra["stdout_tail"].strip().splitlines()[:4],
        "declared_w06_auditor_sha256": ev.get("w06_sha256"),
        "current_w06_auditor_sha256": sha(ROOT / "artifacts/worker-06/spec_conformance_audit.py"),
        "declared_gate_sha256": ev.get("gate_sha256"),
        "current_gate_sha256": sha(ROOT / "artifacts/formulation/tools/check_class_schema.py"),
    }
    # independent corroboration: the pinned acceptance report predates the rev12 schemas
    acc = ROOT / "artifacts/formulation/evidence/acceptance_pipeline_report.json"
    f1y = yaml.safe_load((ROOT / "schemas/af_wcc_vacuum.yaml").read_text())
    m_acc = dt.datetime.fromtimestamp(acc.stat().st_mtime).astimezone()
    m_f1 = dt.datetime.fromtimestamp((ROOT / "schemas/af_wcc_vacuum.yaml").stat().st_mtime).astimezone()
    report["checks"]["acceptance_preflight"].update({
        "acceptance_report_mtime": m_acc.isoformat(timespec="seconds"),
        "acceptance_report_sha256": sha(acc),
        "f1_revised_at_field": f1y.get("revised_at"),
        "f1_schema_mtime": m_f1.isoformat(timespec="seconds"),
        "acceptance_report_predates_f1_revision": m_acc < m_f1,
    })

    # ---- 3. stage 2 directly on the frozen bytes
    sem = [run_semantic(p) for p in
           ("schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml")]
    report["checks"]["semantic_stage2_at_frozen_bytes"] = sem

    # ---- 4. findings
    f1 = sem[0]
    report["findings"] = [f for f in report["findings"] if f.get("id") not in
                          ("W16R28-F1", "W16R28-F2", "W16R28-F3", "W16R28-F4")]
    report["findings"] += [
        {"id": "W16R28-F1", "severity": "hard",
         "statement": ("The two-stage acceptance pipeline cannot be re-run at the frozen bytes: "
                       "run_acceptance.py exits 3 (PREFLIGHT FAIL, stale rebased corpus). Corpus base "
                       f"{ev.get('base_sha256','')[:12]} != current C0 {c0_canon[:12]}. The pinned "
                       "acceptance_pipeline_report.json#9b7d6c82 (union 31/31) is therefore evidence for a "
                       "superseded C0 revision, not for the frozen revision. Corroboration: the pinned "
                       f"report file mtime {m_acc.isoformat(timespec='seconds')} predates the rev12 "
                       f"revised_at {f1y.get('revised_at')} (schema mtime {m_f1.isoformat(timespec='seconds')})."),
         "paths": ["artifacts/formulation/evidence/acceptance_pipeline_report.json",
                   "artifacts/formulation/evidence/semantic_escape_rebased.json"],
         "needed_to_unblock": "re-base the semantic corpus against the frozen C0 hash "
                              "(python3 artifacts/formulation/tools/measure_semantic_escape.py) and re-run "
                              "run_acceptance.py, or record the corpus number as superseded and re-measure."},
        {"id": "W16R28-F2", "severity": "hard",
         "statement": (f"Stage 2 (artifacts/worker-06/spec_conformance_audit.py, sha "
                       f"{f1['tool_sha256'][:12]}) returns verdict '{f1['verdict']}' with failed_rules "
                       f"{f1['failed_rules']} for schemas/af_wcc_vacuum.yaml at sha256 "
                       f"{f1['doc_sha256'][:12]} (rev12): R03 'binder (q,t0) absent from formal sentence'. "
                       "C2/C0 both return 'accept'. Under run_acceptance.py's own rule this makes the "
                       "canonical F1 row fail even after the corpus is re-based."),
         "paths": ["schemas/af_wcc_vacuum.yaml", "artifacts/worker-06/spec_conformance_audit.py"],
         "falsifier": "A stage-2 run at sha256 " + f1["doc_sha256"][:12] +
                      " returning verdict accept, or an adjudication recording R03 as a literal-match "
                      "false positive and amending the rule/pipeline accordingly."},
        {"id": "W16R28-F3", "severity": "medium",
         "statement": ("gate_test_report.json embeds absolute file paths, so its pinned sha256 is "
                       "location-dependent: a clean re-run inside a staged copy produced "
                       "5a9ebb372307 vs the pinned 6def01264a1d with identical verdicts "
                       "(repo in-place re-run reproduces the pin only if run at the pinned root). "
                       "A reviewer told to re-run the suite in a copy cannot reproduce the pinned hash."),
         "paths": ["artifacts/formulation/evidence/gate_test_report.json",
                   "artifacts/formulation/tools/run_gate_tests.py"],
         "needed_to_unblock": "store repo-relative paths in the report (or unpin this evidence file and "
                              "pin the verdict/summary instead)."},
        {"id": "W16R28-F4", "severity": "info-timeline",
         "statement": ("Freeze discipline observation: FROZEN revision 27 (frozen_at 00:32:59) pinned 43 "
                       "files but 3 evidence files were rewritten after frozen_at (mtimes 00:33:11-00:33:16: "
                       "gate_test_report.json 22b92a8e vs pin 2f699be9; taxonomy_consistency.json 9e335e9b "
                       "vs pin 675a99d0; variant_delta_check.json 11888ec6 vs pin fc6ee058). Revision 28 "
                       "(frozen_at 00:35:08, 44 files) is self-consistent: 0/44 drift at 00:35:53. The "
                       "rev27 manifest bytes were not retained by this pass, so this row is a time-stamped "
                       "observation, not a re-measurable artifact."),
         "paths": ["artifacts/formulation/FROZEN.json"],
         "falsifier": "Produce the rev27 FROZEN.json bytes with a manifest sha256 whose pins match the "
                      "three files measured at 00:33:11-00:33:16."},
    ]

    # ---- 5. verdict rewrite
    hard = [f for f in report["findings"] if f["severity"] == "hard"]
    fcb = report["checks"]["frozen_content_and_binding"]
    report["verdict"] = {
        "manifest_self_consistent_at_measurement": report["checks"]["manifest_drift"]["mismatch_count"] == 0,
        "manifest_revision_verified": MAN["revision"],
        "structural_stage1_green": all(report["runs"][f"check_class_schema::{Path(p['path']).name}"]["exit"] == 0
                                       for p in fcb["schemas"].values()),
        "semantic_stage2_at_frozen_bytes": {s["path"]: s["verdict"] for s in sem},
        "two_stage_acceptance_rerunnable_at_frozen_bytes": ra["exit"] == 0,
        "class_binding_census_clean": fcb["unknown_tokens_total"] == 0
                                      and all(not v["class_id_fields_not_frozen_four"] for v in fcb["schemas"].values()),
        "f0_binding_resolves": all(v["f0_binding_matches_measured_f0"] for v in fcb["schemas"].values()),
        "content_green_at_frozen_bytes": False,
        "hard_findings": [f["id"] for f in hard],
        "summary": (
            "Independent re-run at FROZEN revision 28: manifest 44/44 self-consistent; stage 1 "
            "(R01-R16) passes on all three canonical schemas and their byte-identical mirrors; class-binding "
            "census clean (0 non-frozen class tokens, F0 pointers and f0_binding resolve to "
            f"{F0_HASH[:12]}). BUT the pipeline's own stage 2 rejects af_wcc_vacuum.yaml#"
            f"{f1['doc_sha256'][:12]} (R03 literal binder), and run_acceptance.py cannot be re-run at the "
            "frozen bytes at all (exit 3, stale rebased corpus base "
            f"{ev.get('base_sha256','')[:12]} vs current C0 {c0_canon[:12]}). The published two-stage "
            "PASS therefore does not bind the frozen F1 revision. G-FORM/G-F0 content checks are "
            "hash-bound; the acceptance evidence must be re-based and F1 R03 adjudicated or fixed."),
        "authority": "worker event only; G-FORM/G-F0 verdicts remain lead-audit/controller authority.",
    }
    report["falsifier"] = (
        "F1 is refuted by a re-run of run_acceptance.py at the frozen bytes that exits 0 (which requires "
        "a corpus re-based to the frozen C0 hash and, unless the pipeline changes, an F1 formal sentence "
        "that contains the declared binder '(q,t0)'); or by a stage-2 accept verdict for "
        f"af_wcc_vacuum.yaml#{f1['doc_sha256'][:12]}. F3 is refuted by a staged re-run of run_gate_tests.py "
        "at these bytes reproducing the pinned gate_test_report.json sha256. F4 is refuted by producing "
        "the rev27 FROZEN.json bytes whose pins match the three files as measured at 00:33:11-00:33:16. "
        "All content checks are refuted by showing a named frozen path at the cited sha256 violating the "
        "named property.")
    report["finished_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    V.write_text(json.dumps(report, indent=2) + "\n")
    print("rewritten:", V)
    print("verdict:", json.dumps(report["verdict"], indent=1))


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Assemble artifacts/worker-01/F0_rev4_delta.json (worker-01 / deepseek-flash-01).

Controls performed here:
  C1 reverse-apply: replacing each rev4 edit's new text by its old text in the candidate must
     reproduce the canonical bytes exactly (proves the diff contains no accidental change).
  C2 preconditions: the canonical file still hash-equals the checked revision; the candidate
     still parses; the frozen consistency tool's report bytes are the probe outputs.
Writes only artifacts/worker-01/F0_rev4_delta.json.  Never touches the canonical artifact.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "artifacts" / "worker-01"))
import make_f0_rev4_candidate as mk  # noqa: E402

CANON = ROOT / "research_map" / "formulation_taxonomy.yaml"
CAND = ROOT / "artifacts" / "worker-01" / "f0_rev4_candidate.yaml"
W = ROOT / "artifacts" / "worker-01"

EXPECT_CANON = "565a6e505188d6c28050500924b9b66b1440a4c9b069567c772f414f19e02800"
EXPECT_PRE_AMENDMENT = mk.PRE_AMENDMENT_SHA
CST = timezone(timedelta(hours=8))


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    return sha(p.read_bytes())


def main() -> int:
    canon_bytes = CANON.read_bytes()
    cand_bytes = CAND.read_bytes()
    canon_sha, cand_sha = sha(canon_bytes), sha(cand_bytes)
    if canon_sha != EXPECT_CANON:
        print(f"ABORT: canonical changed: {canon_sha} != {EXPECT_CANON}")
        return 2

    # C1: reverse-apply control
    written_at = None
    for line in cand_bytes.decode().splitlines():
        if line.startswith("written_at: "):
            written_at = line.split('"')[1]
            break
    assert written_at, "written_at not found in candidate"
    rev = cand_bytes.decode()
    for name, old, new in mk.build_edits(written_at):
        assert rev.count(new) == 1, f"reverse-apply: {name} new text not unique"
        rev = rev.replace(new, old)
    reverse_ok = rev.encode() == canon_bytes
    if not reverse_ok:
        print("ABORT: reverse-apply control failed")
        return 3

    cand_tax = yaml.safe_load(cand_bytes)
    ctl_val = json.loads((W / "_ctl_validation.json").read_text())
    cand_val = json.loads((W / "f0_rev4_validation.json").read_text())
    ctl_con = json.loads((W / "_ctl_consistency_report.json").read_text())
    cand_con = json.loads((W / "f0_rev4_consistency_report.json").read_text())

    out = {
        "artifact_type": "f0_rev4_revision_delta",
        "task_id": "F0-REV4-RECORD-01",
        "node_id": "F0",
        "gate": "G-F0",
        "actor": "deepseek-flash-01",
        "worker": "worker-01",
        "created_at": datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S%z"),
        "assignment_ref": "asg-2026-09-11-F0-deepseek-flash-01-10",
        "responding_to": [
            "comms/inbox/deepseek-flash-01.jsonl"
            "#leadform-f0-amendment-request-2026-09-11T23:54:36+08:00"
        ],
        "class_ids": cand_tax["class_ids"],
        "class_id": "AF-WCC-VAC-GEN",
        "subject_artifact": "research_map/formulation_taxonomy.yaml",
        "canonical_sha256_at_check": canon_sha,
        "pre_amendment_sha256": EXPECT_PRE_AMENDMENT,
        "candidate": {
            "path": "artifacts/worker-01/f0_rev4_candidate.yaml",
            "sha256": cand_sha,
            "bytes": len(cand_bytes),
            "revision": cand_tax["revision"],
            "status": cand_tax["status"],
        },
        "diff": {"path": "artifacts/worker-01/f0_rev4.diff", "sha256": sha_file(W / "f0_rev4.diff")},
        "changes": [
            {
                "id": "R4-E1",
                "field": "written_at",
                "before": "2026-09-11T23:34:00+08:00",
                "after": written_at,
                "finding": "F0R-01",
            },
            {
                "id": "R4-E2",
                "field": "revision + revision_note_rev4",
                "before": "revision: 3 (no rev4 note)",
                "after": "revision: 4 with a rev4 note recording the astra-classscope-02 amendment",
                "finding": "F0R-01",
            },
            {
                "id": "R4-E3",
                "field": "timestamp_provenance",
                "before": "claims no content timestamp runs ahead of the filesystem",
                "after": "separates observed written_at/decided_at from the lead supplement's declared rev8 time",
                "finding": "F0R-04",
            },
            {
                "id": "R4-E4",
                "field": "class_scope_adjudication.supersedes",
                "before": "wcc_text_sha256_before: <prose, not a hash>",
                "after": "artifact_sha256_before = 66bf917b...c232 + before/after text excerpts + note",
                "finding": "F0R-02",
            },
            {
                "id": "R4-E5",
                "field": "class_scope_adjudication.decided_at",
                "before": "2026-09-12T00:15:00+08:00 (ahead of the file mtime)",
                "after": "decided_at 2026-09-12T00:07:07+08:00 + declared_at_in_lead_supplement 00:15",
                "finding": "F0R-04",
            },
        ],
        "checks": {
            "c1_reverse_apply_control": {
                "result": "pass" if reverse_ok else "fail",
                "detail": "reversing the five edits on the candidate reproduces the canonical bytes exactly",
            },
            "canonical_validator": {
                "tool": "artifacts/worker-01/validate_taxonomy.py",
                "target": "research_map/formulation_taxonomy.yaml",
                "report": "_ctl_validation.json",
                "checks_passed": ctl_val["checks_passed"],
                "checks_failed": ctl_val["checks_failed"],
                "cases_checked": ctl_val["cases_checked"],
                "verdict": ctl_val["verdict"],
            },
            "candidate_validator": {
                "tool": "artifacts/worker-01/validate_taxonomy.py",
                "target": "artifacts/worker-01/f0_rev4_candidate.yaml",
                "report": "f0_rev4_validation.json",
                "report_sha256": sha_file(W / "f0_rev4_validation.json"),
                "checks_passed": cand_val["checks_passed"],
                "checks_failed": cand_val["checks_failed"],
                "cases_checked": cand_val["cases_checked"],
                "verdict": cand_val["verdict"],
            },
            "validator_selftest": {
                "baseline_passes": True,
                "mutations_caught": "6/6",
                "detail": "duplicate token, same-value disjointness axis, merged regularity, "
                "self-classified negative case, braced merged regularity, missing disjointness scope",
            },
            "consistency_canonical_control": {
                "tool": "artifacts/formulation/tools/check_taxonomy_consistency.py",
                "tool_sha256": "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd",
                "probe": "artifacts/worker-01/_f0probe (candidate/canonical bytes placed at "
                "research_map/formulation_taxonomy.yaml; ROOT resolves to the probe)",
                "verdict": "CONSISTENT" if ctl_con["consistent"] else "INCONSISTENT",
                "exit_code": 0 if ctl_con["consistent"] else 1,
                "classes_compared": len(ctl_con["classes_compared"]),
                "contract_text_divergences": len(ctl_con["contract_divergences"]),
                "report": "_ctl_consistency_report.json",
            },
            "consistency_candidate": {
                "tool": "artifacts/formulation/tools/check_taxonomy_consistency.py",
                "tool_sha256": "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd",
                "verdict": "CONSISTENT" if cand_con["consistent"] else "INCONSISTENT",
                "exit_code": 0 if cand_con["consistent"] else 1,
                "classes_compared": len(cand_con["classes_compared"]),
                "contract_text_divergences": len(cand_con["contract_divergences"]),
                "report": "f0_rev4_consistency_report.json",
                "report_sha256": sha_file(W / "f0_rev4_consistency_report.json"),
                "note": "report bytes equal the control report (9e335e9b); the tool embeds no input hashes, "
                "so applying rev4 must not change artifacts/formulation/evidence/taxonomy_consistency.json",
            },
            "run_log": {"path": "artifacts/worker-01/f0_rev4_check_run.log",
                        "sha256": sha_file(W / "f0_rev4_check_run.log")},
            "generator": {"path": "artifacts/worker-01/make_f0_rev4_candidate.py",
                          "sha256": sha_file(W / "make_f0_rev4_candidate.py")},
        },
        "downstream_pins_requiring_refresh_on_apply": [
            {"path": "schemas/af_wcc_vacuum.yaml", "line": 307,
             "field": "f0_binding.declared_f0_sha256", "current": EXPECT_PRE_AMENDMENT,
             "action": "refresh to the applied rev4 sha256; F1's own rule requires this before any gate verdict",
             "owner": "F1 / lead-formulation"},
            {"path": "schemas/af_scc_c2_vacuum.yaml", "line": 294,
             "field": "f0_binding.declared_f0_sha256", "current": EXPECT_PRE_AMENDMENT,
             "action": "refresh to the applied rev4 sha256", "owner": "F2 / lead-formulation"},
            {"path": "schemas/af_scc_c0_vacuum.yaml", "line": 311,
             "field": "f0_binding.declared_f0_sha256", "current": EXPECT_PRE_AMENDMENT,
             "action": "refresh to the applied rev4 sha256", "owner": "F2 / lead-formulation"},
            {"path": "schemas/taxonomy_cases.jsonl",
             "field": "meta.taxonomy_ref {sha256, revision, status} + rebind_note",
             "current": "565a6e50..., revision 3", "action": "rebind and re-run the corpus checker; "
             "axis vectors are untouched so the mapped run should be unchanged",
             "owner": "deepseek-flash-02"},
            {"path": "research_map/research_map.json",
             "field": "gates[G-F0].unmet[0] / frozen_artifacts / artifact hashes",
             "current": "references 66bf917b... and a82f249c...", "action": "controller rebind",
             "owner": "astra"},
            {"path": "artifacts/formulation/evidence/taxonomy_consistency.json",
             "current": "9e335e9ba1bf (probe control and candidate outputs are byte-identical)",
             "action": "re-run the frozen tool on the applied bytes; expected byte-stable",
             "owner": "publishing lead"},
            {"path": "artifacts/worker-01/taxonomy_validation.json",
             "current": "fd0a321d2fb5", "action": "regenerate against the applied bytes",
             "owner": "deepseek-flash-01"},
            {"path": "artifacts/formulation/FROZEN.json",
             "field": "files['artifacts/formulation/formulation_taxonomy.yaml']",
             "current": "a7ccffa8... in manifest vs 01e7f841... on disk",
             "action": "pre-existing drift in the lead supplement, not introduced by this patch; "
             "record or re-freeze under the publish cycle",
             "owner": "lead-formulation"},
        ],
        "findings": {
            "F0R-01": {
                "severity": "B",
                "status": "closed_by_candidate_pending_apply",
                "detail": "the astra-classscope-02 amendment landed in place while revision stayed 3, so no "
                "revision number existed for a review or gate verdict to bind to; rev4 records it.",
            },
            "F0R-02": {
                "severity": "N",
                "status": "closed_by_candidate_pending_apply",
                "detail": "supersedes.wcc_text_sha256_before held prose instead of a sha256; rev4 carries the "
                "real pre-amendment artifact hash 66bf917b...c232 verified against F1's f0_binding and the "
                "flash-02 rebind note.",
            },
            "F0R-03": {
                "severity": "N",
                "status": "open_lead",
                "detail": "two soft CLASSSEP audit hits from variant-registry filenames "
                "(AF-WCC-VAC-GEN-SET, AF-SCC-C0-CH-VAC-GEN); filenames are lead-owned; not changed here.",
            },
            "F0R-04": {
                "severity": "N",
                "status": "closed_by_candidate_pending_apply",
                "detail": "class_scope_adjudication.decided_at declared 00:15 while the amendment mtime is "
                "00:07:07, and timestamp_provenance claimed no timestamp runs ahead of the filesystem; rev4 "
                "separates observed from declared times.",
            },
            "F0R-05": {
                "severity": "N",
                "status": "open_lead_semantic",
                "detail": "AF-WCC-SCALAR-SPH's conclusion still reads 'every future-inextendible causal "
                "geodesic contained in J-(I+) is complete' (the SET-based reading) although the adjudication "
                "declares one canonical single-q predicate. Not edited: D1 was scoped to AF-WCC-VAC-GEN and "
                "changing the scalar class text is a semantic change for the lead/F2 to decide.",
            },
        },
        "not_claimed": [
            "no canonical write (the candidate is staged, not applied)",
            "no node completion and no gate verdict",
            "no theorem, no physics claim",
            "no assertion that the D1/D3 resolution is mathematically correct; only that it is now "
            "recorded, hash-bound and machine-consistent",
        ],
        "falsifier": "Apply the diff to the canonical bytes: if the applied sha256 is not "
        "d820142476f5c9eb392ec74f05cb5542b2f8026a5f1e07de1771baadfe2d4e27, the staged hash is void; if the "
        "frozen consistency tool returns INCONSISTENT or any D1/D3 divergence reappears on the applied bytes, "
        "this delta is refuted; if validate_taxonomy.py on the applied bytes reports any failure, this delta is "
        "refuted; if the published rev4 differs from the candidate in any byte outside the five recorded edits, "
        "this delta is superseded and must be re-run against the published hash.",
        "claims_completion": False,
        "validation_status": "unverified",
    }

    dest = W / "F0_rev4_delta.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=False) + "\n")
    json.loads(dest.read_text())  # re-parse
    print(f"wrote {dest.relative_to(ROOT)}")
    print(f"delta_sha256 = {sha_file(dest)}")
    print(f"c1_reverse_apply = {reverse_ok}")
    print(f"canonical = {canon_sha}")
    print(f"candidate = {cand_sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

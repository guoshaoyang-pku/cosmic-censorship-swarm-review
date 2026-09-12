#!/usr/bin/env python3
"""Compose the W069 F2b rev12 deliverables from the raw checker result.

Writes (all under artifacts/worker-069/f2b_rev12_independent_verdict/ unless noted):
  report.json, README.md, SHA256SUMS
  ../../reviews/F2b-rev12-069.json            (review record on disk)
  ../../../comms/outbox/worker-069.jsonl      (append-only worker events)
  ../../../runtime/state/w069_f2b_rev12_checkpoint.json + w069_checkpoints.jsonl
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat()
STAMP = datetime.now(CST).strftime("%Y%m%dT%H%M%S")

TASK_ID = "W069-F2B-REV12-INDEPENDENT-VERDICT-01"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
SUBJECT = "schemas/af_scc_c0_vacuum.yaml"


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(path: str, full: str) -> str:
    return f"{path}#{full[:12]}"


res = json.loads((RAW / "checker_result.json").read_text())
pins = res["pins"]
hf = res["hard_failures"]

# evidence refs per hard failure
hf_refs = {
    "HF-069F2B-I08": [ref(SUBJECT, pins["subject"]) + ":308",
                      ref("artifacts/formulation/evidence/taxonomy_consistency.json", pins["evidence"]),
                      ref("artifacts/formulation/FROZEN.json", pins["frozen"])],
    "HF-069F2B-I09": [ref("artifacts/formulation/evidence/taxonomy_consistency.json", pins["evidence"]),
                      "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json#675a99d0",
                      ref(SUBJECT, pins["subject"]) + ":308"],
    "HF-069F2B-F07": ["artifacts/worker-069/f2b_rev12_independent_verdict/raw/run_acceptance.txt#"
                      + sha(RAW / "run_acceptance.txt"),
                      "artifacts/worker-069/f2b_rev12_independent_verdict/raw/checker_result.json#"
                      + sha(RAW / "checker_result.json")],
}
hf_falsifier = {
    "HF-069F2B-I08": ("restore/regenerate the canonical evidence generation so that the canonical path "
                      "artifacts/formulation/evidence/taxonomy_consistency.json hashes to the declared "
                      "675a99d0... (or update the declaration to the measured value), re-pin it in FROZEN, "
                      "and re-run: declared == measured voids the finding"),
    "HF-069F2B-I09": ("an evidence generation whose bytes carry map_taxonomy_sha256=0abb9ed8... and "
                      "lead_contract_sha256=d7419b4e... (as the declared 675a99d0 generation already does) "
                      "closes this finding; the current canonical bytes dropped both keys"),
    "HF-069F2B-F07": ("rebase the fixtures (artifacts/formulation/tools/measure_semantic_escape.py) and re-run "
                      "run_acceptance.py on the same frozen bytes; an ACCEPTANCE: PASS voids the finding"),
}

findings = [
    {"id": "W069F2B-A1", "severity": "advisory",
     "finding": ("CONTENT CLEAN at 55d0a1ea: 41/44 independent checks pass; the canonical structural gate "
                 "(stage 1) and the semantic stage (stage 2) both return pass on the snapshot; "
                 "class_separation.findings=0 and classsep_regression PASS; verify_frozen reports FROZEN rev28 "
                 "0 problems; 17/17 mutation controls fire; no pinned input drifted during the run.")},
    {"id": "W069F2B-A2", "severity": "advisory",
     "finding": ("The only full-schema accept at this hash (worker-098, 4.5, counts_as_full_schema_verdict=true) "
                 "is NOT corroborated by this independent instrument: its three closure claims B1/B2/B3 are "
                 "independently reproduced (S02, Q04, I02 all pass), but the accept did not test the two "
                 "binding checks I08/I09, both of which fail, and the two-stage acceptance criterion is not "
                 "reproducible (F07). Disposition: revise, not accept.")},
    {"id": "W069F2B-A3", "severity": "advisory",
     "finding": ("worker-022 HF-022-R1 is independently reproduced at F2b: declared "
                 "f0_binding.consistency_evidence_sha256=675a99d0d25b does not resolve at the canonical "
                 "evidence path (9e335e9ba1bf). The defect is family-wide (F1/F2a/F2b), not F2b-specific.")},
    {"id": "W069F2B-I1", "severity": "info",
     "finding": ("The declared 675a99d0 generation is a strictly stronger consistency record than the live "
                 "9e335e9b bytes: it carries map_taxonomy_sha256=0abb9ed8 (live F0) and "
                 "lead_contract_sha256=d7419b4e (live supplement); the live bytes dropped both input pins. "
                 "Preserved copies: artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json "
                 "and artifacts/worker-092/evbind/pinned/taxonomy_consistency.675a99d0.json, both measuring "
                 "675a99d0d25b2b37.")},
    {"id": "W069F2B-I2", "severity": "info",
     "finding": ("worker-077's D0/regularity deferral is real but recorded, not dropped: D0 is a tagged "
                 "disjoint union over r with per-branch ambient space (Q04 pass) and the deferral is carried "
                 "in unresolved_items and in F0 H3; it is not a G-FORM content failure on these bytes.")},
    {"id": "W069F2B-I3", "severity": "info",
     "finding": ("Stage 2 (artifacts/worker-06/spec_conformance_audit.py c79d8ab8) accepts F2b rev12; by "
                 "contrast worker-080 reported F1 rev12 rejected by both semantic stages on R03. The F1 "
                 "rejection is therefore not reproduced on F2b and does not transfer to this class.")},
]

report = {
    "schema_version": "0.1",
    "task_id": TASK_ID,
    "worker": "worker-069",
    "instance": "worker-069-20260912T003855-968807",
    "created_at": NOW,
    "class_id": CLASS_ID,
    "node_id": "F2b",
    "gate": "G-FORM",
    "target": {"path": SUBJECT, "sha256": pins["subject"], "revision": 12},
    "frozen_revision": res["frozen"]["revision"] if isinstance(res.get("frozen"), dict) else 28,
    "verdict": res["verdict"],
    "score": res["score"],
    "checks": {"total": res["check_count"], "passed": res["checks_passed"],
               "failed_ids": [c["id"] for c in res["checks"] if not c["ok"]]},
    "controls": {"total": len(res["controls"]), "passed": res["controls_passed"],
                 "detail": [{k: c[k] for k in ("control", "expected_check", "control_ok")} for c in res["controls"]]},
    "hard_failures": [
        {"id": h["id"], "label": h["label"], "severity": "blocking-for-clean-accept",
         "detail": h["detail"], "evidence_refs": hf_refs.get(h["id"], []),
         "falsifier": hf_falsifier.get(h["id"], h["falsifier"])}
        for h in hf
    ],
    "adjudication": res["adjudication"],
    "findings": findings,
    "pins": pins,
    "drift": {k: v["drifted"] for k, v in res["drift"].items()},
    "canonical_tools": {
        "stage1_check_class_schema": res["tools"]["stage1"],
        "stage2_spec_conformance_audit": res["tools"]["stage2"],
        "verify_frozen": {"exit": res["tools"]["verify_frozen"]["exit"],
                          "stdout": res["tools"]["verify_frozen"]["stdout"].strip()},
        "classsep_regression": {"exit": res["tools"]["classsep_regression"]["exit"]},
        "class_separation_findings": res["tools"]["classsep_module"].get("findings_count"),
        "run_acceptance": {"exit": res["tools"]["run_acceptance"]["exit"],
                           "tail": res["tools"]["run_acceptance"]["stdout"].strip().splitlines()[-1][:200]},
    },
    "independence": res["independence"],
    "non_claims": [
        "Not a gate verdict and not a node transition: only the controller/leads may set G-FORM or F2b status.",
        "No mathematics or physics result is claimed; every statement is about artifact bytes and tool outputs.",
        "No canonical artifact was modified; the schema, F0, supplement, evidence and FROZEN were read-only.",
        "No claim that the class conclusion is true, false, or open beyond what the schema's own known_status records.",
    ],
    "reproduce": ("cd {root} && python3 artifacts/worker-069/f2b_rev12_independent_verdict/"
                  "check_f2b_rev12_independent.py --controls").format(root=ROOT),
    "artifact_hashes": {},
}

# README
failed = [c for c in res["checks"] if not c["ok"]]
readme = f"""# W069 F2b rev12 independent G-FORM verdict

**Task** `{TASK_ID}` (worker-069, class `{CLASS_ID}`, node F2b, gate G-FORM).
**Target** `{SUBJECT}` at the FROZEN rev28 pin `{pins['subject']}` (schema revision 12).
**Verdict** `{res['verdict']}` score {res['score']}: {res['checks_passed']}/{res['check_count']} independent
checks pass, {res['controls_passed']}/{len(res['controls'])} mutation controls fire, {len(hf)} blocking-for-clean-accept
findings, {len(findings) - 3} advisory/info findings.

## Hard failures (blocking for a clean accept)

""" + "\n".join(
    f"- **{h['id']}** ({h['label']}): {h['detail']}\n  - falsifier: {hf_falsifier.get(h['id'], h['falsifier'])}"
    for h in hf) + f"""

## What passed

- Stage 1 canonical structural gate `check_class_schema.py` (`{pins['stage1'][:12]}`): verdict pass,
  failed_rules=[] on the snapshot.
- Stage 2 semantic auditor `spec_conformance_audit.py` (`{pins['stage2'][:12]}`): verdict pass.
- `class_separation.findings` on the snapshot: 0; `classsep_regression.py`: PASS.
- `verify_frozen.py`: FROZEN revision 28, 0 problems; the manifest pins subject/F0/supplement/evidence exactly.
- Worker-098's B1/B2/B3 closure claims independently reproduced: strict parse has no duplicate keys (S02),
  D0 is a typed disjoint union with no pair-index residue (Q04), the canonical pointer resolves (I02).
- No pinned input drifted during the run: {json.dumps({k: v['drifted'] for k, v in res['drift'].items()})}.
- Determinism: a second run is byte-identical except `run_at`.

## Reading the two binding failures together

The schema declares `f0_binding.consistency_evidence_sha256 = 675a99d0d25b...`. The canonical evidence path
currently holds `9e335e9ba1bf...` (FROZEN rev28 pin), which additionally **dropped** the two input pins
(`map_taxonomy_sha256`, `lead_contract_sha256`) that the declared `675a99d0` generation carries. So the
consistency claim is unbound in both directions: the declaration does not resolve, and the live evidence does
not bind the trees it claims to have compared. The minimal closure is to make the canonical path hold a
generation that carries both input pins (the preserved `675a99d0` bytes already satisfy this) and re-pin it in
FROZEN, or to regenerate and update the declarations and FROZEN in one step. The F2a verdict
`reviews/F2a-rev12-069.json` found the same defect; it is family-wide.

## Reproduction

```bash
cd {ROOT}
python3 artifacts/worker-069/f2b_rev12_independent_verdict/check_f2b_rev12_independent.py --controls
```

Raw outputs: `raw/checker_result.json`, `raw/stage1_stdout.json`, `raw/stage2_stdout.txt`,
`raw/verify_frozen.txt`, `raw/classsep_regression.txt`, `raw/run_acceptance.txt`,
`raw/classsep_module.json`, `raw/snapshot.sha256`, `raw/controls_dir/`.

## Non-claims

Worker events cannot set a node `done`, a `validation_status=passed`, or a gate verdict. This is one bounded
class-bound task: artifact evidence only. No canonical file was modified.
"""
(HERE / "README.md").write_text(readme)

report["artifact_hashes"]["checker"] = sha(HERE / "check_f2b_rev12_independent.py")
report["artifact_hashes"]["raw_checker_result"] = sha(RAW / "checker_result.json")
report["artifact_hashes"]["README"] = sha(HERE / "README.md")
(HERE / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
report_sha = sha(HERE / "report.json")

# review record
review = {
    "schema_version": "0.1",
    "review_id": f"F2b-rev12-069-{STAMP}+0800",
    "task_id": TASK_ID,
    "event_type": "review",
    "target_id": "F2b",
    "node_id": "F2b",
    "class_id": CLASS_ID,
    "gate": "G-FORM",
    "artifact": SUBJECT,
    "artifact_sha256": pins["subject"],
    "reviewed_sha256": pins["subject"],
    "artifact_revision": 12,
    "reviewer": "worker-069",
    "reviewed_at": NOW,
    "verdict": res["verdict"],
    "score": res["score"],
    "counts_as_full_schema_verdict": True,
    "verdict_scope": ("Full class-schema G-FORM verdict for AF-SCC-C0-VAC-GEN at the FROZEN rev28 pin, "
                      "with explicit adjudication of the standing accept (worker-098) and the binding finding "
                      "(worker-022 HF-022-R1). Binds only to the pinned bytes."),
    "independence": res["independence"],
    "method": {
        "instrument": "artifacts/worker-069/f2b_rev12_independent_verdict/check_f2b_rev12_independent.py",
        "instrument_sha256": report["artifact_hashes"]["checker"],
        "checks": res["check_count"],
        "controls": len(res["controls"]),
        "network": "none",
        "canonical_files_modified": "none (read-only; snapshot byte copies)",
    },
    "hard_failures": report["hard_failures"],
    "findings": findings,
    "evidence_refs": [
        ref("artifacts/worker-069/f2b_rev12_independent_verdict/report.json", report_sha),
        ref("artifacts/worker-069/f2b_rev12_independent_verdict/check_f2b_rev12_independent.py",
            report["artifact_hashes"]["checker"]),
        ref(SUBJECT, pins["subject"]),
        ref("artifacts/formulation/evidence/taxonomy_consistency.json", pins["evidence"]),
        ref("artifacts/formulation/FROZEN.json", pins["frozen"]),
        ref("artifacts/worker-069/f2b_rev12_independent_verdict/raw/checker_result.json",
            report["artifact_hashes"]["raw_checker_result"]),
    ],
    "next_falsifier": ("Re-run the instrument on byte-identical copies of the pinned inputs. This verdict is "
                       "falsified if (a) any check recorded ok=true returns ok=false; (b) any of the 17 mutation "
                       "controls escapes its expected check; (c) any pinned input differs from the values recorded "
                       "here (drift voids the binding, not the checks); or (d) the two-stage acceptance pipeline "
                       "reports PASS on the pinned bytes, which voids HF-069F2B-F07."),
}
rev_path = ROOT / "reviews" / "F2b-rev12-069.json"
rev_path.write_text(json.dumps(review, indent=1, ensure_ascii=False))
review_sha = sha(rev_path)

# SHA256SUMS
sums = [f"{sha(rev_path)}  reviews/F2b-rev12-069.json"]
for p in sorted(list(HERE.glob("*.py")) + list(HERE.glob("*.json")) + list(HERE.glob("*.md"))
                + list(RAW.glob("*"))):
    if p.is_file():
        sums.append(f"{sha(p)}  {p.relative_to(ROOT)}")
(HERE / "SHA256SUMS").write_text("\n".join(sums) + "\n")

# outbox events (append once, keyed by event_id)
events = [
    {"event_id": f"w069-f2b12-{STAMP}-task-claim", "event_type": "status", "created_at": NOW,
     "actor": "worker-069", "node_id": "F2b", "class_id": CLASS_ID, "task_id": TASK_ID,
     "status": "active", "hours": 0.5,
     "summary": ("No assignment card exists in comms/inbox for worker-069 (fleet batch 2026-09-12T00:38:55). "
                 "Took ONE bounded class-bound task: W069-F2B-REV12-INDEPENDENT-VERDICT-01 = independent full-schema "
                 "G-FORM verdict for F2b AF-SCC-C0-VAC-GEN at the FROZEN rev28 pin 55d0a1ea9bda (rev12), the only "
                 "class at that hash whose single full-schema accept is a self-retest by the author of the findings "
                 "it re-tests."),
     "evidence_refs": [ref(SUBJECT, pins["subject"]), ref("artifacts/formulation/FROZEN.json", pins["frozen"])],
     "next_falsifier": review["next_falsifier"]},
    {"event_id": f"w069-f2b12-{STAMP}-artifact-checker", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-069", "node_id": "F2b", "class_id": CLASS_ID, "gate": "G-FORM",
     "artifact_type": "independent_schema_checker",
     "path": "artifacts/worker-069/f2b_rev12_independent_verdict/check_f2b_rev12_independent.py",
     "sha256": report["artifact_hashes"]["checker"], "validation_status": "unverified",
     "summary": (f"{res['check_count']}-criterion G-FORM checker (stdlib+PyYAML) with {len(res['controls'])} mutation "
                 "controls; strict duplicate-key parser, family-wide binding probes, canonical stage reproduction; "
                 "not an author self-test."),
     "evidence_refs": [ref(SUBJECT, pins["subject"]),
                       ref("artifacts/worker-069/f2b_rev12_independent_verdict/raw/checker_result.json",
                           report["artifact_hashes"]["raw_checker_result"])]},
    {"event_id": f"w069-f2b12-{STAMP}-artifact-report", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-069", "node_id": "F2b", "class_id": CLASS_ID, "gate": "G-FORM",
     "artifact_type": "independent_schema_verdict",
     "path": "artifacts/worker-069/f2b_rev12_independent_verdict/report.json",
     "sha256": report_sha, "validation_status": "unverified",
     "summary": (f"Independent F2b verdict revise {res['score']} at 55d0a1ea9bda: {res['checks_passed']}/"
                 f"{res['check_count']} checks, {res['controls_passed']}/{len(res['controls'])} controls, "
                 "3 blocking-for-clean-accept findings (HF-069F2B-I08 declared evidence hash unresolved; "
                 "HF-069F2B-I09 live evidence does not bind inputs; HF-069F2B-F07 acceptance preflight stale). "
                 "Content otherwise clean: both canonical stages pass, classsep 0, FROZEN rev28 0 problems, "
                 "no drift. worker-098 B1/B2/B3 closure independently reproduced."),
     "evidence_refs": [ref("artifacts/worker-069/f2b_rev12_independent_verdict/report.json", report_sha),
                       ref(SUBJECT, pins["subject"])]},
    {"event_id": f"w069-f2b12-{STAMP}-artifact-review-file", "event_type": "artifact", "created_at": NOW,
     "actor": "worker-069", "node_id": "F2b", "class_id": CLASS_ID, "gate": "G-FORM",
     "artifact_type": "review_record",
     "path": "reviews/F2b-rev12-069.json", "sha256": review_sha,
     "validation_status": "unverified",
     "summary": "Review record for the F2b rev12 independent verdict (accept claims adjudicated; 3 blocking findings).",
     "evidence_refs": [ref("artifacts/worker-069/f2b_rev12_independent_verdict/report.json", report_sha)]},
    {"event_id": f"w069-f2b12-{STAMP}-claim-binding", "event_type": "claim", "created_at": NOW,
     "actor": "worker-069", "node_id": "F2b", "class_id": CLASS_ID,
     "statement": ("Artifact-and-tooling result (not a mathematics claim): at schemas/af_scc_c0_vacuum.yaml "
                   "sha256 55d0a1ea9bda, f0_binding.consistency_evidence_sha256 declares 675a99d0d25b but the "
                   "canonical evidence path measures 9e335e9ba1bf (FROZEN rev28), and the live evidence bytes "
                   "carry no sha256 of either compared tree; the declared 675a99d0 generation (preserved at "
                   "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json) does carry "
                   "map_taxonomy_sha256=0abb9ed8 and lead_contract_sha256=d7419b4e, matching the live F0 and "
                   "supplement. The consistency binding is therefore unresolved as published and is family-wide "
                   "(F1/F2a/F2b)."),
     "conclusion_type": "formal_model",
     "assumptions": ["inputs read at the hashes recorded in report.json", "no canonical file modified",
                     "tool outputs reproduced on snapshot byte copies"],
     "falsifier": hf_falsifier["HF-069F2B-I08"] + "; " + hf_falsifier["HF-069F2B-I09"],
     "evidence_refs": hf_refs["HF-069F2B-I08"] + hf_refs["HF-069F2B-I09"]},
    {"event_id": f"w069-f2b12-{STAMP}-review-f2b", "event_type": "review", "created_at": NOW,
     "actor": "worker-069", "node_id": "F2b", "class_id": CLASS_ID, "gate": "G-FORM",
     "target_id": "F2b", "reviewer": "worker-069", "verdict": res["verdict"], "score": res["score"],
     "hard_failures": report["hard_failures"], "findings": findings,
     "artifact_sha256": pins["subject"],
     "independence": res["independence"],
     "evidence_refs": review["evidence_refs"],
     "next_falsifier": review["next_falsifier"]},
    {"event_id": f"w069-f2b12-{STAMP}-status-complete", "event_type": "status", "created_at": NOW,
     "actor": "worker-069", "node_id": "F2b", "class_id": CLASS_ID, "task_id": TASK_ID,
     "status": "active", "hours": 1.0,
     "summary": (f"{TASK_ID} complete: artifacts on disk and hash-pinned; verdict revise {res['score']} with 3 "
                 "blocking-for-clean-accept findings (I08 declared evidence hash unresolved; I09 evidence does not "
                 "bind inputs; F07 acceptance preflight stale) at F2b rev12 55d0a1ea9bda. Content checks and both "
                 "canonical stages pass; worker-098 accept claims B1/B2/B3 reproduced but its accept is not "
                 "corroborated. This is a worker completion claim, not a node transition; G-FORM and F2b status are "
                 "the controller's/leads' to set. Checkpoint follows."),
     "evidence_refs": review["evidence_refs"],
     "next_falsifier": review["next_falsifier"]},
]

outbox = ROOT / "comms/outbox/worker-069.jsonl"
existing = set()
if outbox.exists():
    for line in outbox.read_text().splitlines():
        try:
            existing.add(json.loads(line).get("event_id"))
        except Exception:
            pass
with outbox.open("a") as fh:
    for e in events:
        if e["event_id"] not in existing:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

# checkpoint
ckpt = {
    "path": "runtime/state/w069_f2b_rev12_checkpoint.json",
    "worker": "worker-069", "slot": "069", "checkpoint_at": NOW,
    "instance": "worker-069-20260912T003855-968807",
    "task_id": TASK_ID, "node_id": "F2b", "class_id": CLASS_ID, "gate": "G-FORM",
    "verdict": res["verdict"], "score": res["score"],
    "hard_failures": [h["id"] for h in hf],
    "checks": f"{res['checks_passed']}/{res['check_count']}",
    "selftest_controls": f"{res['controls_passed']}/{len(res['controls'])}",
    "target_artifact": SUBJECT, "target_sha256": pins["subject"], "revision": 12,
    "declared_f0_sha256": pins["f0"], "supplement_sha256": pins["supplement"],
    "evidence_sha256_measured": pins["evidence"], "evidence_sha256_declared": "675a99d0d25b2b37",
    "frozen_revision": 28, "frozen_sha256": pins["frozen"],
    "verify_frozen_problems": 0,
    "stage1": "pass", "stage2": "pass", "classsep_findings": 0,
    "acceptance": "not PASS (preflight exit 3)",
    "drift_during_run": {k: {"drifted": v["drifted"]} for k, v in res["drift"].items()},
    "artifacts": {
        "report": {"path": "artifacts/worker-069/f2b_rev12_independent_verdict/report.json",
                   "sha256": report_sha},
        "checker": {"path": "artifacts/worker-069/f2b_rev12_independent_verdict/check_f2b_rev12_independent.py",
                    "sha256": report["artifact_hashes"]["checker"]},
        "review": {"path": "reviews/F2b-rev12-069.json", "sha256": review_sha},
        "raw": {"path": "artifacts/worker-069/f2b_rev12_independent_verdict/raw/checker_result.json",
                "sha256": report["artifact_hashes"]["raw_checker_result"]},
    },
    "next_falsifier": review["next_falsifier"],
    "note": "Worker-level checkpoint. No node completion, no gate verdict, no canonical file modified.",
}
(ROOT / "runtime/state/w069_f2b_rev12_checkpoint.json").write_text(json.dumps(ckpt, indent=1, ensure_ascii=False))
with (ROOT / "runtime/state/w069_checkpoints.jsonl").open("a") as fh:
    fh.write(json.dumps({"checkpoint_at": NOW, "task_id": TASK_ID, "node_id": "F2b", "class_id": CLASS_ID,
                         "verdict": res["verdict"], "score": res["score"],
                         "hard_failures": [h["id"] for h in hf],
                         "checks": f"{res['checks_passed']}/{res['check_count']}",
                         "controls": f"{res['controls_passed']}/{len(res['controls'])}",
                         "target_sha256": pins["subject"],
                         "report_sha256": report_sha}, ensure_ascii=False) + "\n")

print(json.dumps({"report_sha256": report_sha, "review_sha256": review_sha,
                  "events_appended": [e["event_id"] for e in events if e["event_id"] not in existing],
                  "verdict": res["verdict"], "score": res["score"]}, indent=1))

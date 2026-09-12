#!/usr/bin/env python3
"""Emit worker-073's checkpoint + outbox events for W073-L1-REPAIR-READINESS-01.
Deterministic given the artifact bytes on disk; appends no duplicate event_id."""
import hashlib
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TASK_DIR = os.path.dirname(os.path.abspath(__file__))
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-073.jsonl")
CKPT = os.path.join(ROOT, "runtime", "state", "w073_l1repair_checkpoint_1.json")

ARTIFACTS = {
    "report.json": "report",
    "run_check_073_l1repair.py": "instrument",
    "prereg.json": "prereg",
    "amendment-1.json": "amendment",
    "README.md": "note",
    "report.run1-taxonomy-v1.json": "run1_preserved",
    "run_stdout.txt": "stdout",
    "run_stdout.run1-taxonomy-v1.txt": "stdout_run1",
}
TS = "2026-09-12T01:20:00+08:00"
EID = "w073-l1repair-20260912T012000+0800"
LEDGER = "ledger/citation_audit.csv"
LEDGER_SHA = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
W025_SHA = "26f0071c558e99c573d1f1cbfaea4a27f996555f50963e6ec478c7dc09fc2c5d"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
FALSIFIER = ("Re-run artifacts/worker-073/l1_repair_readiness/run_check_073_l1repair.py at "
             "ledger/citation_audit.csv#315c19145065: falsified if any proposed locator is not derivable "
             "from its own row fields, is a discovery query or contains '...', if any '...' row lacks a "
             "valid distinct replacement, if the census disagrees with worker-025 on any TRUNCATED or "
             "DISCOVERY row, if a pre-registered control does not fire, or if any frame pin moves.")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    hashes = {}
    for name in ARTIFACTS:
        p = os.path.join(TASK_DIR, name)
        hashes[name] = sha(p)
    rel = "artifacts/worker-073/l1_repair_readiness/"
    report = json.load(open(os.path.join(TASK_DIR, "report.json")))

    ckpt = {
        "checkpoint_id": "w073-ckpt-l1-repair-readiness-20260912T012000+0800",
        "actor": "worker-073",
        "agent_id": "worker-073",
        "task_id": "W073-L1-REPAIR-READINESS-01",
        "created_at": TS,
        "assignment_ref": ("none (no inbox card for worker-073, recycled slot); task self-selected from the "
                           "REC-35 G-LIT hold and worker-025 F5 staged-repair claim"),
        "authority_note": "worker event; cannot set node status=done, validation_status=passed, or a gate verdict",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_id": "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-VAC-GEN;AF-WCC-SCALAR-SPH",
        "class_ids": CLASS_IDS,
        "frame": {LEDGER: LEDGER_SHA,
                  "artifacts/worker-025/l1_locator_adj/report.json": W025_SHA},
        "artifacts": {rel + k: v for k, v in hashes.items()},
        "decision": report["decision"],
        "verdict": report["verdict"],
        "result": {
            "rows": 97, "provenance_ok": 97, "invented": 0, "ellipsis_closed": 27,
            "residual_non_primary": len(report["residual_rows"]),
            "primary_page_proposals": len(report["proposed_primary_page_rows"]),
            "census_defective_set_agree": report["criteria"]["C6_census_reproduction"]["defective_set_agree"],
            "controls_fired": sum(1 for c in report["controls"] if c["fired"]),
        },
        "findings": [f["id"] for f in report["findings"]],
        "falsifier": FALSIFIER,
        "not_claimed": ["no theorem", "no node status", "no gate verdict", "no validation_status",
                        "no canonical write", "no repair applied"],
    }
    with open(CKPT, "w") as f:
        json.dump(ckpt, f, indent=1, sort_keys=True)
        f.write("\n")
    ckpt_sha = sha(CKPT)

    ev = []
    ev.append({
        "event_id": EID + "-status-task", "event_type": "status", "created_at": TS, "actor": "worker-073",
        "node_id": "L1", "gate": "G-LIT", "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": CLASS_IDS,
        "task_id": "W073-L1-REPAIR-READINESS-01", "status": "active", "hours": 0.5,
        "summary": ("No inbox card exists for worker-073 (recycled slot). Took ONE bounded class-bound task: "
                    "independent, read-only, offline verification of the staged L1 record-identifier repair "
                    "recipe across all 97 rows at pinned ledger/citation_audit.csv 315c19145065 against "
                    "worker-025 F5, without importing worker-025 code. Pre-registration + Amendment 1 on "
                    "disk before the amended run; 9 controls; fail-closed on pin drift. Result: "
                    "REPAIR_READY_WITH_RESIDUAL (97/97 provenance-clean, 27/27 malformed cells closed, "
                    "37/97 replacements are non-primary metadata-API endpoints, 3-row census boundary "
                    "disagreement). No gate verdict, no node status, no validation_status."),
        "evidence_refs": [rel + "prereg.json#sha256:" + hashes["prereg.json"][:12],
                          rel + "amendment-1.json#sha256:" + hashes["amendment-1.json"][:12],
                          rel + "report.json#sha256:" + hashes["report.json"][:12]],
        "next_falsifier": FALSIFIER,
    })
    for name in ("report.json", "run_check_073_l1repair.py", "prereg.json", "amendment-1.json", "README.md"):
        ev.append({
            "event_id": EID + "-artifact-" + ARTIFACTS[name], "event_type": "artifact", "created_at": TS,
            "actor": "worker-073", "node_id": "L1", "gate": "G-LIT",
            "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": CLASS_IDS,
            "task_id": "W073-L1-REPAIR-READINESS-01",
            "artifact_type": "l1_repair_readiness_" + ARTIFACTS[name],
            "path": rel + name, "sha256": hashes[name], "validation_status": "unverified",
            "summary": {
                "report.json": ("Frame-bound repair-readiness report: C1 97/97, C2 97/97 provenance-clean, "
                                "C3 97/97 record identifiers, C4 27/27 closed, C6 defective-set 67/67, "
                                "9/9 controls, decision REPAIR_READY_WITH_RESIDUAL, findings L1R-01..05."),
                "run_check_073_l1repair.py": ("Own deterministic read-only instrument: strict pin gate, own "
                                              "census and provenance implementation, K1-K9 controls, "
                                              "double-run byte comparison, exit 0/2/3."),
                "prereg.json": "Pre-registered criteria, taxonomy, controls, decision rule and falsifier.",
                "amendment-1.json": ("Amendment 1 (written before the amended run): C3 taxonomy covers "
                                     "single-record API endpoints/documents; C6 hard criterion is the "
                                     "defective partition; K6 bare-identifier clause implemented. Run 1 "
                                     "preserved at " + rel + "report.run1-taxonomy-v1.json#sha256:"
                                     + hashes["report.run1-taxonomy-v1.json"][:12] + "."),
                "README.md": "One-page record: question, pins, result table, findings, reproduction, limits.",
            }[name],
            "evidence_refs": [rel + name + "#sha256:" + hashes[name][:12], LEDGER + "#sha256:" + LEDGER_SHA[:12],
                              "artifacts/worker-025/l1_locator_adj/report.json#sha256:" + W025_SHA[:12]],
            "falsifier": FALSIFIER,
        })
    ev.append({
        "event_id": EID + "-artifact-run1-preserved", "event_type": "artifact", "created_at": TS,
        "actor": "worker-073", "node_id": "L1", "gate": "G-LIT",
        "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": CLASS_IDS, "task_id": "W073-L1-REPAIR-READINESS-01",
        "artifact_type": "l1_repair_readiness_run1_preserved",
        "path": rel + "report.run1-taxonomy-v1.json", "sha256": hashes["report.run1-taxonomy-v1.json"],
        "validation_status": "unverified",
        "summary": ("Preserved run-1 report under the v1 taxonomy: NOT_READY caused by two instrument "
                    "defects, both disclosed in amendment-1.json. Kept so a reviewer can reproduce both "
                    "readings; no data criterion was relaxed by the amendment."),
        "evidence_refs": [rel + "amendment-1.json#sha256:" + hashes["amendment-1.json"][:12]],
        "falsifier": "A reviewer who finds a data criterion relaxed rather than an instrument defect fixed.",
    })
    ev.append({
        "event_id": EID + "-claim-readiness", "event_type": "claim", "created_at": TS, "actor": "worker-073",
        "node_id": "L1", "gate": "G-LIT", "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": CLASS_IDS,
        "task_id": "W073-L1-REPAIR-READINESS-01", "conclusion_type": "formal_model",
        "statement": ("At the pinned frame (ledger/citation_audit.csv 315c19145065; worker-025 report "
                      "26f0071c558e), the staged L1 locator repair is mechanically complete and "
                      "provenance-safe: 97/97 proposed_staged_locator values are derivable from each row's "
                      "own {doi, arxiv_id, url, evidence_url, exact_locator} fields with 0 invented values; "
                      "97/97 classify as single-record identifiers (no free-text discovery query, no '...', "
                      "no bare value); all 27 malformed ('...') cells are closed by a valid, distinct "
                      "replacement; the defective partition (27 TRUNCATED + 40 DISCOVERY) reproduces "
                      "per-row against worker-025; 9/9 pre-registered controls fire; two runs are "
                      "byte-identical. Residual, material for L1 acceptance: 37/97 replacements are "
                      "single-record metadata-API endpoints (inspirehep.net/api/literature/<id> 27, "
                      "api.crossref.org/works/<doi> 7, api.openalex.org/works/doi:<doi> 3), so the "
                      "acceptance note's 'primary page/record URL' property would not be restored for "
                      "those rows (60/97 proposals are primary pages). Secondary: worker-025's DIRECT/OTHER "
                      "boundary is not independently reproducible on 3 same-shape API rows (SRC-087, "
                      "SRC-089, SRC-092), so the '26 record locators / 71 not' headline is "
                      "boundary-dependent while the defective partition is stable. This asserts no theorem, "
                      "sets no node status or gate verdict, and writes no canonical path."),
        "assumptions": [
            "research_map/research_map.json is not evidence; only the pinned files are",
            "the ledger's own declared class_mapping governs class scope; disjunctive and evidence/tag rows are bucketed, not assigned",
            "the acceptance-note claim under audit is L0_L1_ACCEPTANCE.md:18 'the L1 exact_locator column carries the primary page/record URL'",
        ],
        "falsifier": FALSIFIER,
        "artifact_refs": [rel + "report.json#sha256:" + hashes["report.json"][:12],
                          rel + "run_check_073_l1repair.py#sha256:" + hashes["run_check_073_l1repair.py"][:12]],
        "evidence_refs": [LEDGER + "#sha256:" + LEDGER_SHA[:12],
                          "artifacts/worker-025/l1_locator_adj/report.json#sha256:" + W025_SHA[:12],
                          rel + "report.json#sha256:" + hashes["report.json"][:12]],
    })
    ev.append({
        "event_id": EID + "-review-l1-repair", "event_type": "review", "created_at": TS, "actor": "worker-073",
        "node_id": "L1", "gate": "G-LIT", "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": CLASS_IDS,
        "reviewer": "worker-073", "target_id": "L1-locator-staged-repair-recipe",
        "reviewed_path": LEDGER, "reviewed_sha256": LEDGER_SHA,
        "reviewed_pair": {"artifacts/worker-025/l1_locator_adj/report.json": W025_SHA,
                          rel + "report.json": hashes["report.json"]},
        "counts_as_full_schema_verdict": False, "counts_toward_gate_accept": False,
        "independence": ("worker-073 authored none of the reviewed bytes; no worker-025 code imported; own "
                         "census and provenance implementation; pre-registration and Amendment 1 precede "
                         "the amended run"),
        "verdict": "accept", "score": 4.0, "hard_failures": [],
        "findings": [
            {"id": "L1R-01", "severity": "info",
             "finding": "97/97 proposals own-field derivable; 0 invented; 27/27 malformed cells closed."},
            {"id": "L1R-02", "severity": "material",
             "finding": ("37/97 replacements are non-primary metadata-API endpoints (inspirehep 27, crossref 7, "
                         "openalex 3); only 60/97 are primary pages, so the recipe alone does not restore the "
                         "acceptance note's primary-page property. This review does not unblock L1 acceptance.")},
            {"id": "L1R-03", "severity": "finding",
             "finding": ("worker-025's DIRECT/OTHER boundary not independently reproducible on SRC-087/089/092; "
                         "same-shape API endpoints split inconsistently (crossref 5 DIRECT vs 2 OTHER; openalex "
                         "2 DIRECT vs 1 OTHER); defective partition stable.")},
            {"id": "L1R-04", "severity": "info",
             "finding": "SRC-090 exact_locator carries appended page annotation text; replacement is a direct PDF."},
            {"id": "L1R-05", "severity": "info",
             "finding": ("Run-1 instrument defects disclosed; run 1 preserved at "
                         + rel + "report.run1-taxonomy-v1.json#sha256:"
                         + hashes["report.run1-taxonomy-v1.json"][:12] + "; amendment-1.json records the change.")},
        ],
        "falsifier": FALSIFIER,
        "artifact_refs": [rel + "report.json#sha256:" + hashes["report.json"][:12],
                          rel + "run_check_073_l1repair.py#sha256:" + hashes["run_check_073_l1repair.py"][:12]],
        "evidence_refs": [LEDGER + "#sha256:" + LEDGER_SHA[:12],
                          "artifacts/worker-025/l1_locator_adj/report.json#sha256:" + W025_SHA[:12],
                          rel + "README.md#sha256:" + hashes["README.md"][:12]],
    })
    ev.append({
        "event_id": EID + "-status-complete", "event_type": "status", "created_at": TS, "actor": "worker-073",
        "node_id": "L1", "gate": "G-LIT", "class_id": "AF-SCC-C2-VAC-GEN", "class_ids": CLASS_IDS,
        "task_id": "W073-L1-REPAIR-READINESS-01", "status": "done", "hours": 0.5,
        "completion_scope": "worker lifecycle only; completion claim for the deliverable, not a node done and not a gate verdict",
        "summary": ("CHECKPOINT + worker-level completion. One class-bound task delivered: independent L1 "
                    "repair-readiness verification at ledger 315c19145065. Decision "
                    "REPAIR_READY_WITH_RESIDUAL; review accept 4.0; findings L1R-01..05; 9/9 controls; pins "
                    "stable before and after. Checkpoint runtime/state/w073_l1repair_checkpoint_1.json "
                    "sha256:" + ckpt_sha[:16] + ". No canonical path written; numerics lock untouched. "
                    "Worker exits now."),
        "evidence_refs": [rel + "report.json#sha256:" + hashes["report.json"][:12],
                          rel + "run_check_073_l1repair.py#sha256:" + hashes["run_check_073_l1repair.py"][:12],
                          rel + "README.md#sha256:" + hashes["README.md"][:12],
                          "runtime/state/w073_l1repair_checkpoint_1.json#sha256:" + ckpt_sha[:16]],
        "next_falsifier": FALSIFIER,
    })

    existing = set()
    if os.path.exists(OUTBOX):
        with open(OUTBOX) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:
                    pass
    written = 0
    with open(OUTBOX, "a") as f:
        for e in ev:
            if e["event_id"] in existing:
                continue
            f.write(json.dumps(e, sort_keys=True) + "\n")
            written += 1
    # validate the whole outbox parses and every event carries the protocol minimum
    bad = []
    with open(OUTBOX) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception as exc:
                bad.append((i, "parse:" + str(exc)))
                continue
            for k in ("event_id", "event_type", "created_at", "actor"):
                if k not in d:
                    bad.append((i, "missing:" + k))
    print(json.dumps({"events_appended": written, "checkpoint_sha256": ckpt_sha,
                      "report_sha256": hashes["report.json"], "outbox_lines": sum(1 for _ in open(OUTBOX)),
                      "outbox_valid": not bad, "problems": bad}, indent=1))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())

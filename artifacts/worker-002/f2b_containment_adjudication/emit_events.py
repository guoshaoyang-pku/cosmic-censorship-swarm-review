#!/usr/bin/env python3
"""Emit W002-F2B-CONTAINMENT-INDEPENDENT-01 protocol events + checkpoint.

Writes:
  comms/outbox/worker-002.jsonl                                  (append, one write)
  runtime/state/w002_f2b_containment_adjudication.json           (checkpoint)
  artifacts/worker-002/f2b_containment_adjudication/CHECKPOINT.json
  artifacts/worker-002/f2b_containment_adjudication/SHA256SUMS   (final manifest)

Worker authority: no status=done, no validation_status=passed, no gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")
TS = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUTBOX = REPO / "comms/outbox/worker-002.jsonl"
STATE = REPO / "runtime/state/w002_f2b_containment_adjudication.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def regen_manifest() -> None:
    lines = []
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS":
            lines.append(f"{sha(p)}  {p.relative_to(HERE)}")
    (HERE / "SHA256SUMS").write_text("\n".join(lines) + "\n")


def ev(eid: str, etype: str, **kw) -> dict:
    d = {"event_id": eid, "event_type": etype, "created_at": NOW, "actor": "worker-002"}
    d.update(kw)
    return d


def main() -> int:
    report = json.loads((HERE / "report.json").read_text())
    arts = {
        "instrument": HERE / "adjudicate.py",
        "report": HERE / "report.json",
        "readme": HERE / "README.md",
        "candidate": HERE / "candidate/af_scc_c0_vacuum.repair2edit.yaml",
        "controls": HERE / "evidence/controls.json",
        "checkpoint": HERE / "CHECKPOINT.json",
    }
    h = {k: str(v.relative_to(REPO)) for k, v in arts.items()}
    hs = {k: sha(v) for k, v in arts.items() if k != "checkpoint"}
    live = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
    cand = report["candidate"]["reproduced_sha256"]
    ids = {
        "art_instrument": f"w002-f2bind-artifact-01-{TS}",
        "art_report": f"w002-f2bind-artifact-02-{TS}",
        "art_readme": f"w002-f2bind-artifact-03-{TS}",
        "art_candidate": f"w002-f2bind-artifact-04-{TS}",
        "art_controls": f"w002-f2bind-artifact-05-{TS}",
        "art_checkpoint": f"w002-f2bind-artifact-06-{TS}",
        "review": f"w002-f2bind-review-07-{TS}",
        "claim": f"w002-f2bind-claim-08-{TS}",
        "blocker": f"w002-f2bind-blocker-09-{TS}",
        "status_ckpt": f"w002-f2bind-status-10-{TS}",
        "status_exit": f"w002-f2bind-status-11-{TS}",
    }
    evref = [f"{h['report']}#{hs['report'][:12]}", f"{h['instrument']}#{hs['instrument'][:12]}",
             f"{h['candidate']}#{cand[:12]}", f"schemas/af_scc_c0_vacuum.yaml#{live[:12]}",
             "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
             "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff#d777a8cb84aa",
             "artifacts/formulation/rule_spec.json#40f9bb9e657b",
             "artifacts/formulation/tools/check_class_schema.py#000e09e46b2f"]

    events = [
        ev(ids["art_instrument"], "artifact", node_id="F2b", gate="G-FORM",
           class_id="AF-SCC-C0-VAC-GEN", artifact_type="adjudication_instrument_py",
           path=h["instrument"], sha256=hs["instrument"], validation_status="unverified",
           evidence_refs=[f"{h['instrument']}#{hs['instrument'][:12]}"],
           note="Read-only instrument; independently re-derives the two carriers from live bytes; 19/19 controls."),
        ev(ids["art_report"], "artifact", node_id="F2b", gate="G-FORM",
           class_id="AF-SCC-C0-VAC-GEN", artifact_type="adjudication_report_json",
           path=h["report"], sha256=hs["report"], validation_status="unverified",
           evidence_refs=evref,
           note="Findings IND-01..IND-06 all confirmed; pins stable; determinism digest " + report["determinism_digest"][:16]),
        ev(ids["art_readme"], "artifact", node_id="F2b", gate="G-FORM",
           class_id="AF-SCC-C0-VAC-GEN", artifact_type="adjudication_readme_md",
           path=h["readme"], sha256=hs["readme"], validation_status="unverified",
           evidence_refs=[f"{h['readme']}#{hs['readme'][:12]}"], note="Human-readable summary and falsifier."),
        ev(ids["art_candidate"], "artifact", node_id="F2b", gate="G-FORM",
           class_id="AF-SCC-C0-VAC-GEN", artifact_type="f2b_repair_candidate_yaml",
           path=h["candidate"], sha256=hs["candidate"], validation_status="unverified",
           evidence_refs=[f"{h['candidate']}#{cand[:12]}",
                          "artifacts/worker-066/f2b_repair_prereg/proposed_patch.diff#d777a8cb84aa"],
           note="live + exactly 2 edits; reproduced byte-for-byte by two methods; matches staged 84b5d3fa; gate pass; strict-parseable."),
        ev(ids["art_controls"], "artifact", node_id="F2b", gate="G-FORM",
           class_id="AF-SCC-C0-VAC-GEN", artifact_type="adjudication_controls_json",
           path=h["controls"], sha256=hs["controls"], validation_status="unverified",
           evidence_refs=[f"{h['controls']}#{hs['controls'][:12]}"],
           note=f"{report['controls']['passed']}/{report['controls']['total']} pre-registered controls passed."),
        ev(ids["review"], "review", node_id="F2b", gate="G-FORM", class_id="AF-SCC-C0-VAC-GEN",
           target_id=f"schemas/af_scc_c0_vacuum.yaml#{live}",
           artifact="schemas/af_scc_c0_vacuum.yaml", artifact_revision=13,
           reviewer="worker-002", verdict="revise", score=3.0,
           reviewed_sha256=live, live_path_sha256_at_emit=live,
           review_file=h["report"], review_file_sha256=hs["report"],
           blind_review=False, counts_as_full_schema_verdict=False,
           verdict_scope=("normativity/containment adjudication of the two carried-over clauses at the "
                          "rev13 bytes, plus independent reproduction of the 2-edit repair; not a full-schema "
                          "leakage/quantifier verdict"),
           hard_failures=[f["id"] for f in report["findings"] if f["severity"] == "hard"],
           findings=[f"{f['id']} [{f['verdict']}] {f['carrier']}" for f in report["findings"]],
           independence=report["independence"],
           falsifier=report["falsifier"],
           authority_note=("worker review event; cannot move gates or node status. G-FORM remains pending and "
                           "F2b remains not-done until the controller and lead-audit bind their own verdicts.")),
        ev(ids["claim"], "claim", node_id="F2b", gate="G-FORM",
           class_id="AF-SCC-C0-VAC-GEN", class_ids=["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
           conclusion_type="stability_result",
           statement=("Read-only adjudication at live rev13 b2ab6acb: schemas/af_scc_c0_vacuum.yaml asserts the "
                      "extension-set nesting E_C2 subset E_{C^1,1} subset E_H2loc subset E_C0 (3 chain claims + 4 "
                      "one-way entailments) yet regularity.must_not_conflate[0] (line 152) denies containment and "
                      "implication_ledger.forbidden_transfers[0].reason (line 246) calls C2 a strictly larger "
                      "extension class; both slots are normative under rule_spec R06/R16 and the C2 sibling "
                      "e9a27996 carries the corrected wording (records the denial as wrong). The canonical structural "
                      "gate passes live, repaired, nonsense and denial-dropped wordings alike, so it neither detects "
                      "the defect nor certifies the repair. Applying the pre-registered 2-edit patch to the live bytes "
                      "reproduces candidate 84b5d3fa byte-for-byte by two independent methods; the candidate is "
                      "strict-parseable, differs from live in exactly 2 leaf strings, preserves f0_binding, carries 0 "
                      "live denial assertions and 0 inverted premises, and passes the gate. 19/19 pre-registered "
                      "controls; all pins stable during the run."),
           assumptions=[
               "the pinned sha256 values are the intended subjects and the bytes were stable during the run",
               "a 'live denial' is a denial not enclosed in a bracket-marked historical note (assertion-vs-mention)",
               "the size-claim reference poset is the document's own declared chain; no external mathematics imported",
               "worker events cannot set status=done, validation_status=passed or a gate verdict"],
           evidence_refs=evref,
           artifact_refs=[h["report"], h["candidate"], h["controls"]],
           falsifier=report["falsifier"], next_falsifier=report["next_falsifier"], hours=0.4),
        ev(ids["blocker"], "blocker", node_id="F2b", gate="G-FORM",
           class_id="AF-SCC-C0-VAC-GEN",
           description=("Live F2b rev13 b2ab6acb carries two normative containment defects independently confirmed "
                        "(denial at line 152 contradicts the document's own ledger; inverted size premise at line 246). "
                        "A validated 2-edit repair exists (candidate 84b5d3fa, gate pass, finding-free), but REC-12/REC-23 "
                        "reserve formulation-semantics edits to the controller, so no worker may land it and no honest "
                        "F2b accept can bind the defective bytes."),
           needed_to_unblock=("Controller authorization to land the 2-edit repair on BOTH schemas/af_scc_c0_vacuum.yaml "
                              "and artifacts/formulation/schemas/af_scc_c0_vacuum.yaml, bump revision 13->14, re-emit "
                              "artifacts/formulation/FROZEN.json, then void rev13 F2b verdicts and re-review at the new "
                              "hash (F2b >=2 independent accepts). Alternative: record the two clauses as accepted "
                              "non-normative prose, which this measurement contradicts (R06/R16 required slots)."),
           evidence_refs=evref),
        ev(ids["status_ckpt"], "status", node_id="F2b", gate="G-FORM",
           class_id="AF-SCC-C0-VAC-GEN", status="active", hours=0.4,
           summary=("CHECKPOINT W002-F2B-CONTAINMENT-INDEPENDENT-01: independent adjudication confirms both worker-066 "
                    "hard carriers at live b2ab6acb, validates the 2-edit candidate 84b5d3fa (2 methods, exactly 2 leaf "
                    "diffs, gate pass, 19/19 controls), and records the canonical-gate blind spot plus the landing "
                    "preconditions. No canonical path written; no gate/validation/done status claimed."),
           evidence_refs=[f"{h['report']}#{hs['report'][:12]}", f"{h['checkpoint']}#CHECKPOINT"],
           next_falsifier=report["next_falsifier"]),
        ev(ids["status_exit"], "status", node_id="F2b", gate="G-FORM",
           class_id="AF-SCC-C0-VAC-GEN", status="active", hours=0.4,
           summary=("Bounded task complete; exiting cleanly. Deliverables under artifacts/worker-002/"
                    "f2b_containment_adjudication/ (instrument, report, controls, candidate, README, CHECKPOINT, "
                    "snapshots, SHA256SUMS). Live bytes unrepaired by design; blocker routed to the controller."),
           evidence_refs=[f"{h['report']}#{hs['report'][:12]}", f"{h['controls']}#{hs['controls'][:12]}"],
           next_falsifier=report["next_falsifier"]),
    ]

    checkpoint = {
        "checkpoint_id": f"w002-f2b-containment-{TS}",
        "actor": "worker-002",
        "agent_id": "deepseek-flash-02",
        "instance": "worker-002-20260912T010134-968807 (bounded execution worker)",
        "task_id": report["task_id"],
        "node_id": "F2b",
        "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "measured_at": NOW,
        "authority_note": ("worker measurement and review evidence only; no canonical file was written; no node "
                           "status=done, validation_status=passed or gate verdict is claimed"),
        "live_pins": {k: v["sha256"] for k, v in report["pins"].items()},
        "pins_stable_during_run": report["pins_stable_during_run"],
        "artifacts": {**h, **hs},
        "verdict": report["verdict"],
        "findings": [{"id": f["id"], "verdict": f["verdict"], "severity": f["severity"],
                      "carrier": f["carrier"], "line": f["line"]} for f in report["findings"]],
        "controls": f"{report['controls']['passed']}/{report['controls']['total']}",
        "determinism_digest": report["determinism_digest"],
        "candidate": {"sha256": cand, "matches_staged": report["candidate"]["matches_staged"],
                      "deep_diff_leaf_count": len(report["candidate"]["deep_diff_vs_live"]),
                      "second_method_matches": report["candidate"]["second_method_patch"].get("matches_line_method"),
                      "gate_verdict": report["candidate"]["gate"]["verdict"]},
        "gate_blind_spot": {k: {"verdict": v["verdict"], "failed_rules": v["failed_rules"]}
                            for k, v in report["gate_runs"].items()},
        "falsifier": report["falsifier"],
        "next_falsifier": report["next_falsifier"],
        "landing_preconditions": [
            "controller authorization under REC-12/REC-23 (formulation-semantics edit)",
            "apply to BOTH schemas/af_scc_c0_vacuum.yaml and artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
            "bump revision 13 -> 14",
            "re-emit artifacts/formulation/FROZEN.json pin",
            "void all rev13-bound F2b verdicts and re-review at the new hash (F2b >= 2 independent accepts)",
        ],
        "outbox_event_ids": list(ids.values()),
        "files_written": [str((HERE / n).relative_to(REPO)) for n in
                          ("adjudicate.py", "report.json", "README.md", "evidence/controls.json",
                           "candidate/af_scc_c0_vacuum.repair2edit.yaml", "CHECKPOINT.json", "SHA256SUMS")],
        "rollback": "delete artifacts/worker-002/f2b_containment_adjudication/ and the matching outbox events; no canonical file was written",
    }

    # write checkpoint, then its hash becomes part of the artifact set
    for dest in (HERE / "CHECKPOINT.json", STATE):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(checkpoint, indent=1, ensure_ascii=False) + "\n")
    ck_sha = sha(HERE / "CHECKPOINT.json")
    events.insert(5, ev(ids["art_checkpoint"], "artifact", node_id="F2b", gate="G-FORM",
                        class_id="AF-SCC-C0-VAC-GEN", artifact_type="adjudication_checkpoint_json",
                        path=str((HERE / "CHECKPOINT.json").relative_to(REPO)), sha256=ck_sha,
                        validation_status="unverified",
                        evidence_refs=[f"{h['checkpoint']}#{ck_sha[:12]}"],
                        note="Checkpoint with pins, findings, controls, gate runs and landing preconditions."))
    # validate against the project event schema before writing anything
    sys.path.insert(0, str(REPO))
    from research_map.schemas import validate_event  # noqa: E402
    for e in events:
        validate_event(e)
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events))
    regen_manifest()
    print(json.dumps({"outbox": str(OUTBOX.relative_to(REPO)), "events": len(events),
                      "event_ids": list(ids.values()),
                      "checkpoint": str(STATE.relative_to(REPO)), "checkpoint_sha256": ck_sha,
                      "manifest_sha256": sha(HERE / "SHA256SUMS")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

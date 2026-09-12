#!/usr/bin/env python3
"""Append the R03-v2 task events to comms/outbox/worker-006.jsonl. Fail-closed on hash drift."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
OUT = ROOT / "comms" / "outbox" / "worker-006.jsonl"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


FILES = {
    "prereg": "artifacts/worker-06/r03v2/preregistration.json",
    "manifest": "artifacts/worker-06/r03v2/fixture_manifest.json",
    "copy": "artifacts/worker-06/r03v2/audit_r03v2.py",
    "rule": "artifacts/worker-06/r03v2/r03v2_rule.py",
    "report": "artifacts/worker-06/r03v2/report.json",
    "table": "artifacts/worker-06/r03v2/calibration_table.json",
    "blind": "artifacts/worker-06/r03v2/blindspot_report.json",
    "submission": "artifacts/worker-06/r03v2/SUBMISSION.md",
    "runner": "artifacts/worker-06/r03v2/run_calibration.py",
    "maker": "artifacts/worker-06/r03v2/make_r03v2.py",
    "frozen": "artifacts/worker-06/spec_conformance_audit.py",
    "wcc": "schemas/af_wcc_vacuum.yaml",
    "frozen_json": "artifacts/formulation/FROZEN.json",
}


def main() -> int:
    h = {k: sha(ROOT / v) for k, v in FILES.items()}
    report = json.loads((ROOT / FILES["report"]).read_text())
    if report["validity"] != "VALID" or report["falsifier_status"]["pos_false_positive"]["status"] != "not triggered":
        sys.exit("refusing to emit: report invalid or falsifier triggered")
    now = datetime.now(CST).isoformat(timespec="seconds")
    ev = f"w006-{datetime.now(CST).strftime('%Y%m%dT%H%M')}-r03v2"
    base = {"actor": "worker-006", "created_at": now, "node_id": "A1", "gate": "G-CLASSBIND",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]}
    evs = []

    def art(suffix, path, kind, summary, evidence, falsifier):
        evs.append({**base, "event_id": f"{ev}-{suffix}", "event_type": "artifact",
                    "artifact_type": kind, "path": path, "sha256": h[[k for k, v in FILES.items()
                    if v == path][0]], "validation_status": "unverified",
                    "summary": summary, "evidence_refs": evidence, "falsifier": falsifier,
                    "not_claimed": "no gate verdict, no node completion, no theorem, no physics result"})

    fals = ("a positive control rejected by R03-v2 at the pinned span, a neg_abs fixture "
            "accepted by R03-v2, a gate negative whose frozen R03 rejection is not reproduced "
            "outside the declared literal-tuple FP family, or any pinned input drift")
    art("prereg", FILES["prereg"], "preregistration",
        "rule, span, corpus, expectations and decision rule fixed before any run; pins frozen source "
        "c79d8ab8440a, WCC d9cebb9404b2, C2 e9a27996dfd3, C0 b2ab6acb2bbe, FROZEN.json 815e08079aef",
        [f"{FILES['frozen']}#{h['frozen'][:12]}", f"{FILES['frozen_json']}#{h['frozen_json'][:12]}"], fals)
    art("copy", FILES["copy"], "proposal_tool",
        "stage-B proposal copy; exactly two textual deltas from the frozen auditor (D1 path rebase, "
        "D2 R03 binder-head co-binding); frozen tool untouched",
        [f"{FILES['frozen']}#{h['frozen'][:12]}", f"{FILES['manifest']}#{h['manifest'][:12]}"], fals)
    art("manifest", FILES["manifest"], "corpus_manifest",
        "17 fixtures (8 pos / 3 neg_abs / 3 neg_nonbind / 3 span probes), each with source and "
        "fixture sha256; hashed into the pre-registration", [f"{FILES['prereg']}#{h['prereg'][:12]}"], fals)
    art("report", FILES["report"], "measurement_report",
        "VALID, no pin drift. POS 8/8 accepted by R03-v2 vs 6/8 frozen (FP=0); neg_abs 3/3 both; "
        "neg_nonbind frozen 0/3 vs R03-v2 3/3; 31 gate negatives, 0 unexplained lost catches "
        "(11 explained literal-tuple FP, 3 substantive both-reject, 17 no R03 disagreement)",
        [f"{FILES['prereg']}#{h['prereg'][:12]}", f"{FILES['copy']}#{h['copy'][:12]}",
         f"{FILES['frozen']}#{h['frozen'][:12]}", f"{FILES['wcc']}#{h['wcc'][:12]}"], fals)
    art("table", FILES["table"], "calibration_table",
        "span ablation 13..inf: pos_fp=0, neg_abs 3/3, neg_nonbind 3/3 at every span; over-reject "
        "probes: filler30 accepted at span>=40, filler100 at span>=120, filler300 only at unbounded span",
        [f"{FILES['report']}#{h['report'][:12]}"], fals)
    art("blindspot", FILES["blind"], "blindspot_report",
        "per-fixture frozen vs R03-v2 outcome with minimal repro and the over-reject edge documented",
        [f"{FILES['report']}#{h['report'][:12]}", f"{FILES['manifest']}#{h['manifest'][:12]}"], fals)
    art("submission", FILES["submission"], "submission",
        "method, pre-registration, results, falsifier outcome, honest limits, file map",
        [f"{FILES['report']}#{h['report'][:12]}", f"{FILES['table']}#{h['table'][:12]}",
         f"{FILES['blind']}#{h['blind'][:12]}"], fals)
    art("rule", FILES["rule"], "proposed_rule",
        "standalone binder-head co-binding predicate with the frozen predicate for side-by-side use",
        [f"{FILES['copy']}#{h['copy'][:12]}"], fals)
    art("toolchain", FILES["runner"], "measurement_toolchain",
        "deterministic generator (pins asserted) and calibration runner; runner hash reported, "
        "not pre-registered",
        [f"{FILES['maker']}#{h['maker'][:12]}", f"{FILES['copy']}#{h['copy'][:12]}"], fals)

    evs.append({**base, "event_id": f"{ev}-status", "event_type": "status", "status": "active",
                "hours": 1.5,
                "summary": "FORM-R03-V2, one class-bound task from the A1 blocker "
                           "lead-form-20260912T005843-94: the stage-B R03 literal-substring binder "
                           "check falsely rejects canonical AF-WCC-VAC-GEN (binder '(q,t0)' written "
                           "as 'q in I+ and t0 in [0,T)'), which blocked any 'controls pass both "
                           "stages' measurement. Proposal copy with a single semantic delta "
                           "(binder-head co-binding; span=80) accepts 8/8 positive controls (frozen "
                           "6/8), keeps 3/3 neg_abs catches, and catches 3/3 new neg_nonbind "
                           "violations the frozen literal test misses; 31 gate negatives show 0 "
                           "unexplained lost catches and 11 disagreements all inside the declared "
                           "FP family; VALID, no pin drift. Frozen tool NOT modified: adoption is "
                           "the owner's decision.",
                "evidence_refs": [f"{FILES['report']}#{h['report'][:12]}",
                                  f"{FILES['prereg']}#{h['prereg'][:12]}",
                                  f"{FILES['copy']}#{h['copy'][:12]}",
                                  f"{FILES['frozen']}#{h['frozen'][:12]}"],
                "next_falsifier": fals,
                "not_claimed": "no gate verdict, no node completion, no theorem, no physics result"})

    with OUT.open("a") as fh:
        for e in evs:
            fh.write(json.dumps(e, separators=(", ", ": ")) + "\n")
    print(f"appended {len(evs)} events to {OUT.relative_to(ROOT)}")
    for e in evs:
        print(" ", e["event_id"], e["event_type"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

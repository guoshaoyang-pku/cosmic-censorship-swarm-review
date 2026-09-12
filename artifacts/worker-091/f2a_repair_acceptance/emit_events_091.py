#!/usr/bin/env python3
"""Emit W091-F2A-REPAIR-ACCEPTANCE-01 events to comms/outbox/worker-091.jsonl.

Idempotent: events whose event_id already exists in the outbox are skipped.
Every event is validated with research_map/schemas.py::validate_event before it
is written. No canonical artifact is touched; no gate verdict, node status or
validation_status=passed is set by this worker.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "research_map"))
from schemas import validate_event  # noqa: E402

CST = timezone(timedelta(hours=8))
OUTBOX = os.path.join(ROOT, "comms", "outbox", "worker-091.jsonl")
ART = "artifacts/worker-091/f2a_repair_acceptance"
TASK = "W091-F2A-REPAIR-ACCEPTANCE-01"
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def h(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def main():
    rep = json.load(open(os.path.join(ROOT, ART, "report.json"), encoding="utf-8"))
    stamp = datetime.now(CST).strftime("%Y%m%dT%H%M")
    hashes = {p: h(os.path.join(ART, p)) for p in
              ["report.json", "check_091_f2a_repair_acceptance.py", "README.md", "MANIFEST.json",
               "raw/patched_f2a.37e650ad.yaml", "raw/w047_baseline_report.json",
               "raw/w047_baseline_controls.json", "raw/w047_patched_report.json",
               "raw/w047_patched_controls.json", "raw/report_run2.json",
               "raw/instrument_sandbox_diff.txt"]}
    hs = {k: hashes[v] for k, v in {
        "report": "report.json", "instrument": "check_091_f2a_repair_acceptance.py",
        "readme": "README.md", "manifest": "MANIFEST.json",
        "patched": "raw/patched_f2a.37e650ad.yaml",
        "w047_base_report": "raw/w047_baseline_report.json",
        "w047_base_controls": "raw/w047_baseline_controls.json",
        "w047_patch_report": "raw/w047_patched_report.json",
        "w047_patch_controls": "raw/w047_patched_controls.json",
        "run2": "raw/report_run2.json", "instrument_diff": "raw/instrument_sandbox_diff.txt",
    }.items()}
    refs = {
        "report": "%s/report.json#%s" % (ART, hs["report"][:12]),
        "instrument": "%s/check_091_f2a_repair_acceptance.py#%s" % (ART, hs["instrument"][:12]),
        "readme": "%s/README.md#%s" % (ART, hs["readme"][:12]),
        "manifest": "%s/MANIFEST.json#%s" % (ART, hs["manifest"][:12]),
        "patched": "%s/raw/patched_f2a.37e650ad.yaml#%s" % (ART, hs["patched"][:12]),
        "w047_base_report": "%s/raw/w047_baseline_report.json#%s" % (ART, hs["w047_base_report"][:12]),
        "w047_patch_report": "%s/raw/w047_patched_report.json#%s" % (ART, hs["w047_patch_report"][:12]),
        "w047_patch_controls": "%s/raw/w047_patched_controls.json#%s" % (ART, hs["w047_patch_controls"][:12]),
        "run2": "%s/raw/report_run2.json#%s" % (ART, hs["run2"][:12]),
        "instrument_diff": "%s/raw/instrument_sandbox_diff.txt#%s" % (ART, hs["instrument_diff"][:12]),
        "f2a": "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
        "f2b": "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
        "frozen": "artifacts/formulation/FROZEN.json#815e08079aef",
        "spec": "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json#c33e8a46",
        "w047_instrument": ("artifacts/worker-047/c2c0_pred_containment/"
                            "check_c2c0_pred_containment_047.py#481663f0e905"),
        "existing_patched": ("artifacts/worker-091/w047_f2a_freeze_independent/patched/"
                             "af_scc_c2_vacuum.w047-patched.yaml#37e650ad6481"),
    }
    base = {
        "actor": "worker-091", "node_id": "F2a", "class_id": CLASS_IDS[0],
        "class_ids": CLASS_IDS, "gate": "G-FORM", "task_id": TASK,
        "created_at": now(),
    }
    common = ["worker evidence; focused-axis verification; not a full-schema verdict; does not "
              "set node status, a gate verdict, or validation_status=passed"]

    events = []
    for name, atype in [("report", "verification_report"), ("instrument", "verification_instrument"),
                        ("readme", "verification_readme"), ("manifest", "manifest"),
                        ("patched", "patched_candidate_snapshot")]:
        events.append({
            "event_id": "w091-%s-f2a-ra-artifact-%s" % (stamp, name),
            "event_type": "artifact", **base,
            "artifact_type": atype, "path": os.path.join(ART, {
                "report": "report.json", "instrument": "check_091_f2a_repair_acceptance.py",
                "readme": "README.md", "manifest": "MANIFEST.json",
                "patched": "raw/patched_f2a.37e650ad.yaml"}[name]),
            "sha256": hashes[{"report": "report.json", "instrument": "check_091_f2a_repair_acceptance.py",
                              "readme": "README.md", "manifest": "MANIFEST.json",
                              "patched": "raw/patched_f2a.37e650ad.yaml"}[name]],
            "bytes": os.path.getsize(os.path.join(ROOT, ART, {
                "report": "report.json", "instrument": "check_091_f2a_repair_acceptance.py",
                "readme": "README.md", "manifest": "MANIFEST.json",
                "patched": "raw/patched_f2a.37e650ad.yaml"}[name])),
            "validation_status": "unverified",
            "authority_note": common[0],
        })

    events.append({
        "event_id": "w091-%s-f2a-ra-claim" % stamp,
        "event_type": "claim", **base,
        "conclusion_type": "formal_model",
        "statement": (
            "At pins F2a=schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3, F2b="
            "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe, F0=0abb9ed8a961, FROZEN rev29=815e08079aef: "
            "(1) the pinned F2a(C2)/F2b(C0) clause pair does NOT entail E_C2 subset E_C0 - independent "
            "obligation table O1 (manifold category) and O2 (interior witness) both FAIL on F2a, "
            "worker-047's containment instrument reports C11 FAIL, and the explicit predicate-level "
            "witness M'=R^4, iota(M)=R^4 minus {0}, g'=Minkowski eta satisfies every baseline C2 clause "
            "but fails C0 clause (f) because int({0}) is empty; (2) applying the W047 option-A edits "
            "S1-S5 to the pinned F2a bytes re-derives byte-identically candidate sha256 37e650ad6481 "
            "(= the previously reviewed patched copy) and makes the clause pair entail the containment "
            "(O1/O2/O3/O5/O6 PASS, CLASS_TOKEN_C2 PASS, sibling anchors PASS; worker-047 instrument "
            "C11 flips FAIL->PASS; contract flips C01/C02/C06/C11 FAIL->PASS); (3) the recommending "
            "instrument's own contract then fails C05 by construction (C05 pre-registers the rev13 "
            "asymmetry as a PASS condition, and any repair that establishes containment must align "
            "clause (f)), leaves C09 (T1 lacks the extension-predicate convention guard) and C10 (no "
            "explicit cross-class alignment declaration) FAIL, and exits 3 on control mis-calibration "
            "against the repaired bytes (K1/K2/K3 mutation anchors are consumed by the repair; K5's "
            "expectation is uncovered by the C05 branch at C02=PASS/C04=FAIL), so it cannot serve as "
            "the rev14 automated repair-acceptance gate without re-anchoring. 5 findings, 7/7 own "
            "controls, two runs byte-identical modulo created_at."),
        "assumptions": [
            "The measured sha256 is the artifact identity; a path without a hash binds nothing.",
            "The containment claim audited is the one declared in F2a implication_ledger and "
            "class_boundary and in the F0 supplement; the C^{1,1}/H2_loc middle terms have no "
            "canonical predicate at these pins and are out of scope.",
            "Clause obligations are read from the declared text; the witness is a predicate-level "
            "model of the declared class, not a physical extension of AF data and not evidence about "
            "cosmic censorship.",
            "The W047 instrument's C01..C11 table remains comparable even when its own controls "
            "mis-calibrate (rc 3); the comparison uses the emitted table, disclosed as such.",
            "No duplicate YAML mapping keys are introduced by the patch (leaf diff confined to the "
            "three declared leaves; class token and conclusion_type unchanged).",
            "Worker events cannot move gates or node status; the 4-item rev14 checklist in the "
            "report is a recommendation to the formulation lead, not an authority action.",
        ],
        "artifact_refs": [refs["report"], refs["instrument"], refs["readme"], refs["manifest"],
                          refs["patched"], refs["run2"]],
        "evidence_refs": [refs["f2a"], refs["f2b"], refs["frozen"], refs["spec"],
                          refs["w047_instrument"], refs["existing_patched"],
                          refs["w047_base_report"], refs["w047_patch_report"],
                          refs["w047_patch_controls"], refs["instrument_diff"]],
        "pins": {row["path"]: row["measured"] for row in rep["pins"]["rows"]},
        "findings": [{"id": f["id"], "severity": f["severity"], "statement": f["statement"][:600]}
                     for f in rep["findings"]],
        "falsifier": rep["falsifier"],
        "counts_as_full_schema_verdict": False,
        "gate_verdict_set": False,
    })

    events.append({
        "event_id": "w091-%s-f2a-ra-blocker-instrument-gate" % stamp,
        "event_type": "blocker", **base,
        "blocker_class": "tooling_acceptance_gap",
        "description": (
            "F-091-RA-5 + F-091-RA-2: worker-047's containment instrument cannot be used unmodified "
            "as the F2a rev14 repair-acceptance gate. On the patched candidate 37e650ad it exits 3 "
            "(control mis-calibration): K1/K2/K3 mutation anchors no longer exist because the repair "
            "has already been applied, and K5's expected flip is not covered by the C05 branch when "
            "C02=PASS/C04=FAIL. In addition C05 pre-registers the rev13 asymmetry as a PASS target, so "
            "--strict can never return 0 on a correctly repaired F2a. Its README claim that --strict "
            "doubles as the repair-acceptance test therefore does not hold for the repair it "
            "recommends; the emitted C01..C11 table is still usable when read directly and this "
            "checker reproduces it (C11 FAIL->PASS)."),
        "needed_to_unblock": (
            "Instrument owner (worker-047 / astra-lead-audit): re-anchor K1/K2/K3 controls to the "
            "repaired text, extend the C05 branch to the (C02 PASS, C04 FAIL) case, and re-scope C05 "
            "to assert the aligned/containment state (or retire C05); alternatively run the controls "
            "against a pinned baseline snapshot and admit only the C01..C11 table as rev14 acceptance "
            "evidence. Until then rev14 verification should use the table plus an independent "
            "obligation checker, not the instrument's exit code."),
        "evidence_refs": [refs["report"], refs["w047_patch_report"], refs["w047_patch_controls"],
                          refs["instrument_diff"], refs["w047_instrument"], refs["existing_patched"]],
        "next_falsifier": (
            "A patched-sandbox run of the instrument that returns 0/1 with 9/9 controls and a "
            "re-scoped C05, or a controller ruling that the C-table alone (without control "
            "calibration) is admissible rev14 acceptance evidence."),
    })

    events.append({
        "event_id": "w091-%s-f2a-ra-status" % stamp,
        "event_type": "status", **base,
        "status": "done",
        "hours": 0.6,
        "summary": (
            "W091-F2A-REPAIR-ACCEPTANCE-01 complete: one bounded class-bound task (F2a, "
            "AF-SCC-C2-VAC-GEN, G-FORM). Independent reproduction that the pinned C2/C0 clause pair "
            "does not entail E_C2 subset E_C0, and that the W047 option-A repair (re-derived "
            "37e650ad) closes it and flips worker-047's C11 FAIL->PASS; residuals C05 (contract "
            "target that the repair necessarily retires), C09 (T1 guard), C10 (alignment "
            "declaration) and the instrument's control mis-calibration on repaired bytes (rc 3) are "
            "reported with a 4-item rev14 checklist. 5 findings, 7/7 own controls, two runs "
            "byte-identical, no drift. This is a worker-level completion claim and does NOT set node "
            "status, a gate verdict or validation_status."),
        "evidence_refs": [refs["report"], refs["manifest"], refs["instrument"], refs["readme"],
                          refs["patched"], refs["f2a"], refs["f2b"]],
        "next_falsifier": rep["falsifier"],
        "authority_note": common[0],
        "canonical_edits": "none - read-only on every canonical path; writes confined to "
                           + ART + ", tmp/w091_f2a_repair_accept, the worker-091 outbox and the "
                           "worker-091 checkpoint",
    })

    existing = set()
    if os.path.exists(OUTBOX):
        for line in open(OUTBOX, encoding="utf-8"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    existing.add(json.loads(line).get("event_id"))
                except Exception:  # noqa: BLE001
                    pass
    written = []
    with open(OUTBOX, "a", encoding="utf-8") as fh:
        for ev in events:
            validate_event(ev)
            if ev["event_id"] in existing:
                print("skip existing", ev["event_id"])
                continue
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")
            written.append(ev["event_id"])
    print("written:", json.dumps(written, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

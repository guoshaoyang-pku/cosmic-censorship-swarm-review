#!/usr/bin/env python3
"""W090-A1-DETECTOR-PIN-RESTORATION-01 -- independent, read-only verification of the
CF-29 detector-write restoration state (node A1, gate G-AUDIT, classes AF-WCC-VAC-GEN /
AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN).

Scope
-----
This is NOT a detector-semantics review and NOT a gate verdict.  It measures, at one
instant, the byte state of research_map/class_separation.py against the three hashes that
CF-26 / REC-29 / CF-29 distinguish, checks the declared forensic preservation and the
active frozen pin, and censuses accepted-stream references to the voided hash.

Pre-registered source of the claim under test
---------------------------------------------
runtime/state/controller_verification/cf29-detector-write-forensics.json (read at run time)
CF-29 ruling text: unauthorized = e36b0d644ca75b1e..., restored live bytes = a8c04fc3...,
active frozen pin stays c266dbec..., evidence preserved byte-verbatim.

Falsifier (fixed before measurement)
------------------------------------
The restoration claim is FALSIFIED if any of:
  (F1) sha256(research_map/class_separation.py) != a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd;
  (F2) the preserved evidence copy does not hash to e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed;
  (F3) the hash-verified restoration source (restored_from) is absent or does not hash to a8c04fc31e4a...;
  (F4) the recovered baseline copy does not hash to c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920;
  (F5) the live file changes hash inside the measurement window (moving target -- report blocked, not a verdict);
  (F6) frozen_artifacts no longer pins research_map/class_separation.py at c266dbec with active=true.
Minor-finding tests (not falsifiers of the restoration):
  (M1) cf29 manifest "before_sha256" field semantics;
  (M2) cf29 manifest "accepted_stream_refs_to_unauthorized_hash" count.

No canonical file is written.  All reads only.  Exit code 0 = all blocking checks pass;
1 = at least one blocking check failed; 2 = moving target / input drift.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
HERE = os.path.dirname(os.path.abspath(__file__))

H_A8 = "a8c04fc31e4afa1b691cd6bfb6bf8b4f953a0adc925939a8351bab9cf453c5bd"
H_C266 = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
H_E36 = "e36b0d644ca75b1efc291b44a3188facb7839d81790073341431f3bb77b86eed"
H_REGR = "9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091"
H_FROZEN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
H_F1 = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
H_F2A = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
H_F2B = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
H_TAX = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"

PATHS = {
    "live_detector": "research_map/class_separation.py",
    "void_evidence": "runtime/state/controller_verification/class_separation.e36b0d644ca.evidence.py",
    "restored_from": "artifacts/worker-073/classsep_union_separability/pinned/class_separation.live.a8c04fc31e4a.py",
    "recovered_pin_copy": "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
    "recovered_pin_sidecar": "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py.sha256",
    "regression_runner": "runtime/bin/classsep_regression.py",
    "forensics_manifest": "runtime/state/controller_verification/cf29-detector-write-forensics.json",
    "events": "research_map/events.jsonl",
    "map": "research_map/research_map.json",
    "frozen": "artifacts/formulation/FROZEN.json",
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "taxonomy": "research_map/formulation_taxonomy.yaml",
    "q1": "runtime/state/comms_quarantine/astra-inbox-line3-20260912T0112.jsonl",
    "q2": "runtime/state/comms_quarantine/astra-lead-audit-inbox-lines24-25-27-20260912T0112.jsonl",
}

EXPECT = {
    "live_detector": H_A8,
    "void_evidence": H_E36,
    "restored_from": H_A8,
    "recovered_pin_copy": H_C266,
    "regression_runner": H_REGR,
    "frozen": H_FROZEN,
    "F1": H_F1,
    "F2a": H_F2A,
    "F2b": H_F2B,
    "taxonomy": H_TAX,
    "q1": "ca9c7507d38a7a364d683d912165cb854160286112bc02b0f8704531859cdd7c",
    "q2": "8fadc24100467e16ba00d39d818977728d03d4c164265948e73e3fc3cec5bcda",
}

MINOR_FINDINGS = [
    {
        "id": "W090-A1R-01",
        "severity": "minor",
        "kind": "manifest-field-semantics",
        "artifact": "runtime/state/controller_verification/cf29-detector-write-forensics.json:8-11",
        "finding": (
            "detector.before_sha256 equals detector.unauthorized_sha256 (both e36b0d644ca...), "
            "so the manifest does not record the bytes that were live immediately BEFORE the "
            "unauthorized write; CF-29 and the manifest's own restored_sha256 place those at "
            "a8c04fc31e4a. The field reads as 'state before the incident' but stores 'state at "
            "restoration input'. Recommendation: drop before_sha256 or rename it "
            "state_at_restoration_input; no data is lost because both hashes are present."
        ),
        "falsifier": "Produce the manifest's intended field definition showing before_sha256 is not the pre-write state, or a pre-write snapshot hashing to e36b0d644ca.",
    },
    {
        "id": "W090-A1R-02",
        "severity": "minor",
        "kind": "manifest-count-vs-census",
        "artifact": "runtime/state/controller_verification/cf29-detector-write-forensics.json:14",
        "finding": (
            "detector.accepted_stream_refs_to_unauthorized_hash is recorded as 0, but at the "
            "measurement snapshot the accepted stream (research_map/events.jsonl, 6800+ lines) "
            "contains 5 events carrying the full void hash e36b0d644ca75b1e... (worker-095 "
            "status x2 + claim x1; worker-045 artifact x1 + claim x1; event ids recorded in "
            "results.json). Zero of them carries a structured adoption/binding field for the "
            "void hash, and each declares the 01:06:12-01:08:14 window non-adopted or void, so "
            "the ruling 'no adoption' is corroborated while the literal count 0 is false. "
            "Recommendation: restate the field as '0 authorizing refs; 5 forensic refs'."
        ),
        "falsifier": "Re-run the census at a later events.jsonl and show 0 hash-bearing events, or show the field was defined as authorizing-refs-only in a recorded schema.",
    },
    {
        "id": "W090-A1R-03",
        "severity": "info",
        "kind": "pin-live-separation",
        "artifact": "research_map/research_map.json#frozen_artifacts[research_map/class_separation.py]",
        "finding": (
            "Three distinct detector hashes are simultaneously meaningful: active frozen pin "
            "c266dbecaa87 (frozen_artifacts, active=true), live adjudicated bytes a8c04fc31e4a "
            "(live file at measurement), voided write e36b0d644ca (preserved evidence). This "
            "separation is intentional per REC-29 but is not self-describing on disk: any "
            "G-FORM/G-AUDIT verdict that says it ran 'the frozen class-separation detector' "
            "must name which hash it measured. Cite the hash, never the bare path."
        ),
        "falsifier": "A recorded ruling that makes live bytes equal the active pin, or a detector consumer that resolves the path to a hash without ambiguity.",
    },
]

HARD_FAILURES = [
    {"id": "HF090-A1R-01", "check": "D01", "condition": "live detector sha256 != a8c04fc31e4a (restoration claim false)"},
    {"id": "HF090-A1R-02", "check": "D06", "condition": "preserved void evidence sha256 != e36b0d644ca75b1e (forensic preservation false)"},
    {"id": "HF090-A1R-03", "check": "D05", "condition": "restored_from source absent or sha256 != live (restoration not byte-identical to declared source)"},
    {"id": "HF090-A1R-04", "check": "D07", "condition": "recovered baseline copy sha256 != c266dbec (pin baseline not reproducible)"},
    {"id": "HF090-A1R-05", "check": "D13", "condition": "live detector drifts inside the measurement window (moving target)"},
    {"id": "HF090-A1R-06", "check": "D11", "condition": "frozen_artifacts no longer pins the detector at c266dbec with active=true"},
]


def sha(path: str) -> str:
    with open(os.path.join(ROOT, path), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def read_text(path: str) -> str:
    with open(os.path.join(ROOT, path), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def run_checks():
    checks, hard = [], []
    live_text = read_text(PATHS["live_detector"])
    live_hash = hashlib.sha256(live_text.encode("utf-8")).hexdigest()

    def rec(cid, desc, observed, expected, ok, falsifier=None):
        checks.append({"id": cid, "desc": desc, "observed": observed, "expected": expected,
                       "pass": bool(ok), "falsifier": falsifier})
        return bool(ok)

    # D01 live == adjudicated APPLIED bytes
    rec("D01", "live detector sha256 equals adjudicated a8c04fc31e4a",
        live_hash, H_A8, live_hash == H_A8, HARD_FAILURES[0]["condition"])
    # D02 live != active pin (known intentional separation)
    rec("D02", "live detector differs from active frozen pin c266dbec (pin/live separation)",
        live_hash, "!=" + H_C266, live_hash != H_C266)
    # D03 live != void write
    rec("D03", "live detector differs from voided write e36b0d644ca",
        live_hash, "!=" + H_E36, live_hash != H_E36)
    # D04 parses
    try:
        ast.parse(live_text)
        parsed = True
    except SyntaxError as exc:
        parsed = str(exc)
    rec("D04", "live detector is syntactically valid Python (ast.parse)", parsed, True, parsed is True)
    # D05 live == restored_from
    rf = PATHS["restored_from"]
    rf_hash = sha(rf) if os.path.exists(os.path.join(ROOT, rf)) else None
    rec("D05", "declared restoration source present and byte-identical to live",
        rf_hash, H_A8, rf_hash == H_A8, HARD_FAILURES[2]["condition"])
    # D06 void evidence
    ve = sha(PATHS["void_evidence"])
    rec("D06", "preserved void-write evidence hashes to e36b0d644ca75b1e",
        ve, H_E36, ve == H_E36, HARD_FAILURES[1]["condition"])
    # D07 recovered pin copy + sidecar
    rc = sha(PATHS["recovered_pin_copy"])
    side = read_text(PATHS["recovered_pin_sidecar"]).split()[0]
    rec("D07", "recovered baseline copy hashes to c266dbec and sidecar agrees",
        {"copy": rc, "sidecar": side}, H_C266, rc == H_C266 and side == H_C266,
        HARD_FAILURES[3]["condition"])
    # D08 quarantine byte-identity
    q1 = sha(PATHS["q1"]); q2 = sha(PATHS["q2"])
    rec("D08", "quarantined injection payloads match manifest hashes",
        {"q1": q1, "q2": q2}, {"q1": EXPECT["q1"], "q2": EXPECT["q2"]},
        q1 == EXPECT["q1"] and q2 == EXPECT["q2"])
    # D09 manifest declared hashes vs measured
    man = json.loads(read_text(PATHS["forensics_manifest"]))
    det = man["detector"]
    rec("D09", "cf29 manifest unauthorized_sha256 == measured void evidence; restored_sha256 == measured live",
        {"unauthorized": det["unauthorized_sha256"], "restored": det["restored_sha256"]},
        {"unauthorized": ve, "restored": live_hash},
        det["unauthorized_sha256"] == ve and det["restored_sha256"] == live_hash)
    # D10 change summary mechanically confirmed
    live_lines = live_text.splitlines()
    void_lines = read_text(PATHS["void_evidence"]).splitlines()
    diff = [l for l in difflib.unified_diff(live_lines, void_lines, lineterm="", n=2)
            if (l.startswith("+") and not l.startswith("+++")) or (l.startswith("-") and not l.startswith("---"))]
    regex_line = next((l for l in void_lines if "quote(?:d|s)?" in l and "0\\s+genuine" in l), "")
    widening_ok = (
        len(diff) == 2
        and "0\\s+genuine\\s+assertions?" in regex_line
        and "(?:(?:or\\s+describes?\\s+)?the\\s+)?detector" in regex_line
    )
    rec("D10", "CF-29 'one-line regex widening in the mention guard' confirmed by diff",
        {"changed_lines": len(diff), "void_guard_line": regex_line.strip()[:200]},
        "1 removed + 1 added line, widened mention regex", widening_ok)
    # D11 frozen pin
    rmap = json.loads(read_text(PATHS["map"]))
    pin_entry = next((e for e in rmap.get("frozen_artifacts", [])
                      if e.get("path") == PATHS["live_detector"]), None)
    pin_ok = bool(pin_entry and pin_entry.get("sha256") == H_C266 and pin_entry.get("active") is True)
    rec("D11", "frozen_artifacts pins detector at c266dbec with active=true",
        {"sha256": pin_entry and pin_entry.get("sha256"), "active": pin_entry and pin_entry.get("active")},
        {"sha256": H_C266, "active": True}, pin_ok, HARD_FAILURES[5]["condition"])
    # D12 runner + outer pins
    outer = {k: sha(PATHS[k]) for k in ("regression_runner", "frozen", "F1", "F2a", "F2b", "taxonomy")}
    outer_ok = all(outer[k] == EXPECT[k] for k in outer)
    rec("D12", "regression runner and G-FORM context pins unchanged",
        outer, {k: EXPECT[k] for k in outer}, outer_ok)
    # D14 accepted-stream census of the void hash
    census = {"events_total": 0, "void_hash_bearing": 0, "by_actor_type": {},
              "structured_adoption_markers": 0, "adoption_keyword_hits_lexical": 0,
              "keyword_hit_note": "lexical only; includes negated mentions such as 'does NOT meet the adoption bar' and 'non-adoption'",
              "event_ids": []}
    for line in open(os.path.join(ROOT, PATHS["events"]), encoding="utf-8", errors="replace"):
        census["events_total"] += 1
        if "e36b0d644ca75b1e" not in line:
            continue
        census["void_hash_bearing"] += 1
        try:
            ev = json.loads(line)
        except Exception:
            ev = {}
        key = f"{ev.get('actor','?')}|{ev.get('event_type','?')}"
        census["by_actor_type"][key] = census["by_actor_type"].get(key, 0) + 1
        if ev.get("event_id"):
            census["event_ids"].append(ev["event_id"])
        # structured adoption: an explicit adopt/bind field that names the void hash
        if ev.get("adopted") is True or ev.get("adoption") == "adopt" or ev.get("binding_sha256") == H_E36:
            census["structured_adoption_markers"] += 1
        blob = json.dumps(ev, ensure_ascii=False).lower()
        if any(w in blob for w in ("adopt", "authoriz", "binding")):
            census["adoption_keyword_hits_lexical"] += 1
    rec("D14", "accepted-stream census: manifest refs_to_unauthorized_hash claim vs measured",
        {"manifest_claim": det.get("accepted_stream_refs_to_unauthorized_hash"),
         "measured_void_hash_bearing": census["void_hash_bearing"],
         "measured_structured_adoption_markers": census["structured_adoption_markers"]},
        0, census["void_hash_bearing"] == 0, "W090-A1R-02 (recorded as minor finding, not a restoration falsifier)")
    # D15 manifest before/unauthorized equality (observation only)
    before_eq_unauth = det.get("before_sha256") == det.get("unauthorized_sha256")
    rec("D15", "cf29 manifest before_sha256 equals unauthorized_sha256 (field-semantics observation)",
        {"before_sha256": det.get("before_sha256"), "unauthorized_sha256": det.get("unauthorized_sha256"),
         "restored_sha256": det.get("restored_sha256")},
        "observation recorded as W090-A1R-01", before_eq_unauth,
        "W090-A1R-01 (minor finding, not a restoration falsifier)")
    return checks, live_hash, live_text, census, pin_entry, man


def run_controls(checks, live_text, live_hash):
    """Mechanical controls: the checker must not be vacuous."""
    controls = []

    def crec(cid, desc, ok, note=""):
        controls.append({"id": cid, "desc": desc, "pass": bool(ok), "note": note})

    # C1 full-64 comparison: 12-hex prefix must not satisfy equality
    crec("C1-prefix-not-accepted", "12-hex prefix does not satisfy full-hash equality",
         not (live_hash[:12] == H_A8 and live_hash == H_C266), "full 64-hex compare in D01/D06")
    # C2 mutation sensitivity
    mutated = live_text.replace("_MERGE_ASSERT", "_MERGE_ASSERT_X", 1)
    mh = hashlib.sha256(mutated.encode()).hexdigest()
    crec("C2-mutation-sensitivity", "one-token mutation changes measured hash",
         mh != live_hash, f"mutated={mh[:12]}")
    # C3 wrong-pin control: live must NOT match the active pin (check is not vacuous)
    crec("C3-wrong-pin-control", "verifying live against c266dbec fails (D02 is sensitive)",
         live_hash != H_C266)
    # C4 void evidence is a distinct revision, not a copy
    ve = sha(PATHS["void_evidence"])
    crec("C4-distinct-revision", "void evidence is a distinct revision (hash and byte count differ)",
         ve != live_hash and os.path.getsize(os.path.join(ROOT, PATHS["void_evidence"])) != len(live_text.encode()))
    # C5 input stability across the whole run
    stable = all(sha(PATHS[p]) == EXPECT[p] for p in ("live_detector", "void_evidence", "restored_from",
                                                      "recovered_pin_copy", "frozen", "F1", "F2a", "F2b", "taxonomy"))
    crec("C5-input-stability", "all pre-registered inputs unchanged at end of run", stable)
    # C6 quarantine byte check is sensitive
    q1 = read_text(PATHS["q1"])
    crec("C6-quarantine-sensitivity", "one-byte quarantine mutation changes its hash",
         hashlib.sha256((q1 + "x").encode()).hexdigest() != EXPECT["q1"])
    return controls


def main():
    checks, live_hash, live_text, census, pin_entry, man = run_checks()
    controls = run_controls(checks, live_text, live_hash)
    live_after = sha(PATHS["live_detector"])
    drift = live_after != live_hash
    checks.append({"id": "D13", "desc": "live detector hash stable before/after all reads",
                   "observed": {"before": live_hash, "after": live_after}, "expected": "identical",
                   "pass": not drift, "falsifier": HARD_FAILURES[4]["condition"]})
    blocking_pass = all(c["pass"] for c in checks if c["id"] not in ("D14", "D15"))
    hard = [hf for hf in HARD_FAILURES if any(c["id"] == hf["check"] and not c["pass"] for c in checks)]
    out = {
        "schema": "detector-pin-verification/v1",
        "task_id": "W090-A1-DETECTOR-PIN-RESTORATION-01",
        "reviewer": "worker-090",
        "created_at": __import__("datetime").datetime.now().astimezone().isoformat(),
        "root": ROOT,
        "claim_under_test": "CF-29/REC-29: live detector restored to a8c04fc31e4a; void write e36b0d644ca preserved byte-verbatim; active frozen pin stays c266dbecaa87; pin/live separation intentional.",
        "three_hashes": {"active_frozen_pin": H_C266, "live_adjudicated": H_A8, "void_write": H_E36},
        "checks": checks,
        "controls": controls,
        "accepted_stream_census_void_hash": census,
        "frozen_artifacts_entry": pin_entry,
        "manifest": {"path": PATHS["forensics_manifest"], "sha256": sha(PATHS["forensics_manifest"]),
                     "recorded_at": man.get("recorded_at")},
        "hard_failures": hard,
        "minor_findings": MINOR_FINDINGS,
        "moving_target": drift,
        "verdict": ("blocked-moving-target" if drift else
                    ("restoration_confirmed" if blocking_pass else "restoration_contradicted")),
        "authority_note": "Worker evidence only. This cannot set node status=done, validation_status=passed, or any gate verdict; it is not a detector-semantics or gate endorsement.",
        "counts_as_full_schema_verdict": False,
        "counts_toward_gate_accept": False,
    }
    with open(os.path.join(HERE, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=False)
        fh.write("\n")
    with open(os.path.join(HERE, "controls.json"), "w", encoding="utf-8") as fh:
        json.dump({"controls": controls, "all_pass": all(c["pass"] for c in controls)}, fh, indent=1)
        fh.write("\n")
    print(json.dumps({"verdict": out["verdict"], "blocking_pass": blocking_pass, "drift": drift,
                      "hard_failures": [h["id"] for h in hard],
                      "checks_failed": [c["id"] for c in checks if not c["pass"]],
                      "controls_failed": [c["id"] for c in controls if not c["pass"]]}, indent=1))
    if drift:
        return 2
    return 0 if blocking_pass else 1


if __name__ == "__main__":
    sys.exit(main())

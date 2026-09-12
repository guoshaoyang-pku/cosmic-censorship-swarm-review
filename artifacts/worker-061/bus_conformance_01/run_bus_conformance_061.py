#!/usr/bin/env python3
"""W061-A1-BUS-CONFORMANCE-01 -- read-only conformance audit of the comms bus boundary.

Question: which documented PROTOCOL.md / schemas.py rules are actually ENFORCED for
outbox traffic, which are silently NORMALIZED away by comms.normalize_event, and which
are delegated to the downstream map layer (apply_events.py authority demotion)?

Method (pre-registered, deterministic, hermetic):
  1. direct mutation matrix over pinned research_map/schemas.py::validate_event
     (invalid mutation -> expect SchemaError; valid twin -> expect pass, all 13 types);
  2. mutant-teeth controls: guards are deleted from copies of the pinned validator and
     the corresponding mutation MUST be accepted by the mutant (proves the test has
     teeth), while a different guard still rejects its own mutation (specificity);
  3. hermetic bus test: a sandbox copy of pinned comms.py + schemas.py is run as
     `comms.py ingest` on a synthetic outbox; the accepted/rejected partition is
     compared to a pre-registered expectation table, and _normalized records are read;
  4. static citation check of every coercion/demotion line cited in the report, at the
     pinned hashes;
  5. non-interference control: canonical events.jsonl / rejected.jsonl / research_map.json
     are hashed before and after the whole run and must be byte-identical.

No canonical artifact is written. Output: mutations.json (pre-registration), report.json,
stdout.log. Read-only against research_map/ and comms/.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ART = Path(__file__).resolve().parent
SWARM = ART.parents[2]
PINNED = ART / "pinned"
MUTANTS = ART / "mutants"
SANDBOX = ART / "sandbox"
LIVE = {
    "research_map/schemas.py": SWARM / "research_map" / "schemas.py",
    "research_map/comms.py": SWARM / "research_map" / "comms.py",
    "research_map/apply_events.py": SWARM / "research_map" / "apply_events.py",
    "research_map/events.jsonl": SWARM / "research_map" / "events.jsonl",
    "comms/rejected.jsonl": SWARM / "comms" / "rejected.jsonl",
    "research_map/research_map.json": SWARM / "research_map" / "research_map.json",
}
PIN_SRC = {
    "research_map/schemas.py": PINNED / "schemas.py",
    "research_map/comms.py": PINNED / "comms.py",
    "research_map/apply_events.py": PINNED / "apply_events.py",
}

CST_TS = "2026-09-12T01:30:00+08:00"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def base_event(eid: str, etype: str, **kw) -> dict:
    ev = {"event_id": eid, "event_type": etype, "created_at": CST_TS, "actor": "worker-061-ct"}
    ev.update(kw)
    return ev


def valid_twins() -> dict[str, dict]:
    return {
        "status": base_event("ct-v-status", "status", node_id="F2b", status="active", hours=0.5,
                             summary="s", evidence_refs=[], next_falsifier="f"),
        "claim": base_event("ct-v-claim", "claim", node_id="F2b", class_id="AF-SCC-C0-VAC-GEN",
                            statement="s", conclusion_type="numerical_evidence", assumptions=[],
                            falsifier="f", evidence_refs=["a#b"]),
        "artifact": base_event("ct-v-artifact", "artifact", node_id="F2b", artifact_type="report",
                               path="pinned/schemas.py", sha256="0" * 64, validation_status="unverified"),
        "review": base_event("ct-v-review", "review", target_id="F2b", reviewer="worker-061",
                             verdict="accept", score=3.0, hard_failures=[], findings=[]),
        "resource_request": base_event("ct-v-resource", "resource_request", group_id="audit",
                                       requested_agents=1, requested_agent_hours=1.0,
                                       justification="j", expected_information_gain="e", stop_rule="s"),
        "direction_update": base_event("ct-v-direction", "direction_update", group_id="audit",
                                       old_direction="a", new_direction="b", reason="r",
                                       evidence_refs=[], budget_delta_agent_hours=0.0),
        "blocker": base_event("ct-v-blocker", "blocker", node_id="F2b", description="d",
                              needed_to_unblock="n", evidence_refs=[]),
        "assignment": base_event("ct-v-assign", "assignment", node_id="F2b", assignee="worker-061",
                                 artifact="a", gate="G-AUDIT", evidence_refs=[], falsifier="f"),
        "budget": base_event("ct-v-budget", "budget", group_id="audit", delta_agent_hours=1.0, reason="r"),
        "gate": base_event("ct-v-gate", "gate", gate_id="G-AUDIT", scope="A1", verdict="pending",
                           criteria="c", evidence_refs=[]),
        "priority_change": base_event("ct-v-priority", "priority_change", scope="A1",
                                      old_priority="p1", new_priority="p2", reason="r"),
        "kill": base_event("ct-v-kill", "kill", target_id="A1", reason="r"),
        "revive": base_event("ct-v-revive", "revive", target_id="A1", reason="r"),
    }


def direct_mutations() -> list[dict]:
    """rule_id -> one invalid mutation of an otherwise valid event (direct validate_event)."""
    good_claim = valid_twins()["claim"]
    out = []

    def mut(rule, source, etype, event, expect, note):
        out.append({"rule_id": rule, "source": source, "event_type": etype, "expect": expect,
                    "event": event, "note": note})

    e = dict(good_claim); e.pop("event_id")
    mut("R1-required-top-level", "schemas.py:27", "claim", e, "SchemaError",
        "missing event_id/created_at/actor (direct caller path)")
    mut("R2-unknown-event-type", "schemas.py:29", "telemetry",
        base_event("ct-m-r2", "telemetry"), "SchemaError", "event_type not in EVENT_TYPES")
    e = dict(good_claim); e.pop("statement")
    mut("R3-claim-required-fields", "schemas.py:32,45", "claim", e, "SchemaError", "claim without statement")
    e = dict(good_claim); e["conclusion_type"] = "theorem_ish"
    mut("R4-conclusion-vocabulary", "schemas.py:46-47", "claim", e, "SchemaError", "unknown conclusion_type")
    e = dict(valid_twins()["artifact"]); e["validation_status"] = "probably_fine"
    mut("R5-artifact-status-vocabulary", "schemas.py:48-49", "artifact", e, "SchemaError", "unknown validation_status")
    e = dict(valid_twins()["review"]); e["verdict"] = "maybe"
    mut("R6-review-verdict-vocabulary", "schemas.py:50-51", "review", e, "SchemaError", "unknown verdict")
    e = dict(valid_twins()["review"]); e["score"] = 7
    mut("R7-review-score-range", "schemas.py:52", "review", e, "SchemaError", "score outside 0..5")
    e = dict(valid_twins()["status"]); e["status"] = "finished"
    mut("R8-status-vocabulary", "schemas.py:53", "status", e, "SchemaError", "unknown node status")
    e = dict(valid_twins()["gate"]); e["verdict"] = "maybe"
    mut("R9-gate-verdict-vocabulary", "schemas.py:54", "gate", e, "SchemaError", "unknown gate verdict")
    e = dict(good_claim); e["conclusion_type"] = "theorem"; e.pop("artifact_refs", None)
    mut("R10-theorem-requires-artifact", "schemas.py:55-56", "claim", e, "SchemaError",
        "PROTOCOL rule 1: theorem without artifact_refs")
    return out


def bus_cases() -> list[dict]:
    """Pre-registered synthetic outbox cases for the hermetic ingest run."""
    good = valid_twins()["claim"]
    cases = []

    def case(cid, event, expect, note, dup_of=None):
        cases.append({"case_id": cid, "event": event, "expect": expect, "note": note, "dup_of": dup_of})

    e = dict(good); e["event_id"] = "ct-b-valid"; e["case_id"] = "valid-claim"
    case("valid-claim", e, "accepted", "baseline valid claim")

    e = dict(good); e["event_id"] = "ct-b-thm-noart"; e["case_id"] = "theorem-no-artifact"
    e["conclusion_type"] = "theorem"
    case("theorem-no-artifact", e, "rejected", "PROTOCOL rule 1")

    e = dict(good); e["event_id"] = "ct-b-thm-art"; e["case_id"] = "theorem-with-artifact"
    e["conclusion_type"] = "theorem"; e["artifact_refs"] = ["artifacts/x/report.json"]
    case("theorem-with-artifact", e, "accepted", "rule 1 satisfied")

    e = base_event("ct-b-unknown", "telemetry"); e["case_id"] = "unknown-type"
    case("unknown-type", e, "rejected", "unknown event_type")

    e = dict(good); e["event_id"] = "ct-b-badconc"; e["case_id"] = "bad-conclusion"
    e["conclusion_type"] = "theorem_ish"
    case("bad-conclusion", e, "rejected", "explicit invalid conclusion_type")

    e = dict(good); e["event_id"] = "ct-b-nostmt"; e["case_id"] = "no-statement"; e.pop("statement")
    case("no-statement", e, "rejected", "missing semantic core statement")

    e = dict(good); e["event_id"] = "ct-b-nofals"; e["case_id"] = "no-falsifier"; e.pop("falsifier")
    case("no-falsifier", e, "accepted", "placeholder falsifier filled by bus")

    e = dict(good); e["event_id"] = "ct-b-noev"; e["case_id"] = "no-evidence"; e.pop("evidence_refs")
    case("no-evidence", e, "accepted", "empty evidence_refs filled by bus")

    e = dict(good); e["event_id"] = "ct-b-noassum"; e["case_id"] = "no-assumptions"; e.pop("assumptions")
    case("no-assumptions", e, "accepted", "empty assumptions filled by bus")

    e = dict(valid_twins()["status"]); e["event_id"] = "ct-b-badstatus"; e["case_id"] = "bad-status"
    e["status"] = "finished_maybe"
    case("bad-status", e, "accepted", "status coerced, not rejected")

    e = dict(valid_twins()["status"]); e["event_id"] = "ct-b-done"; e["case_id"] = "worker-done"
    e["status"] = "done"
    case("worker-done", e, "accepted", "bus accepts worker done; demotion is downstream")

    e = dict(valid_twins()["artifact"]); e["event_id"] = "ct-b-artpassed"; e["case_id"] = "artifact-passed"
    e["validation_status"] = "passed"; e["path"] = "asset.txt"; e["sha256"] = "1" * 64
    case("artifact-passed", e, "accepted", "bus accepts validation_status=passed; demotion is downstream")

    e = dict(valid_twins()["artifact"]); e["event_id"] = "ct-b-artbad"; e["case_id"] = "artifact-bad-status"
    e["validation_status"] = "probably_fine"; e["path"] = "asset.txt"; e["sha256"] = "1" * 64
    case("artifact-bad-status", e, "accepted", "validation_status coerced to unverified")

    e = dict(valid_twins()["review"]); e["event_id"] = "ct-b-badverdict"; e["case_id"] = "review-bad-verdict"
    e["verdict"] = "maybe"
    case("review-bad-verdict", e, "rejected", "review verdict vocabulary enforced")

    e = dict(valid_twins()["review"]); e["event_id"] = "ct-b-score7"; e["case_id"] = "review-score-7"
    e["score"] = 7
    case("review-score-7", e, "rejected", "review score range enforced")

    e = dict(valid_twins()["review"]); e["event_id"] = "ct-b-noscore"; e["case_id"] = "review-no-score"
    e.pop("score")
    case("review-no-score", e, "accepted", "score placeholder 0 filled by bus")

    e = base_event(None, "claim"); e.pop("event_id")
    e.update({"case_id": "no-event-id", "class_id": "AF-SCC-C0-VAC-GEN", "statement": "s",
              "conclusion_type": "open_problem", "assumptions": [], "falsifier": "f", "evidence_refs": []})
    case("no-event-id", e, "accepted", "event_id generated deterministically by bus")

    e = base_event("ct-b-noactor", "claim"); e.pop("actor")
    e.update({"case_id": "no-actor", "class_id": "AF-SCC-C0-VAC-GEN", "statement": "s",
              "conclusion_type": "open_problem", "assumptions": [], "falsifier": "f", "evidence_refs": []})
    case("no-actor", e, "accepted", "actor filled from outbox file stem")

    e = base_event("ct-b-nots", "claim"); e.pop("created_at")
    e.update({"case_id": "no-created-at", "class_id": "AF-SCC-C0-VAC-GEN", "statement": "s",
              "conclusion_type": "open_problem", "assumptions": [], "falsifier": "f", "evidence_refs": []})
    case("no-created-at", e, "accepted", "created_at filled with arrival time")

    e = base_event("ct-b-noetype", "claim"); e.pop("event_type")
    e["case_id"] = "no-event-type"
    case("no-event-type", e, "rejected", "event_type has no default; rejected")

    e = dict(valid_twins()["gate"]); e["event_id"] = "ct-b-gate-noev"; e["case_id"] = "gate-no-evidence"
    e.pop("evidence_refs")
    case("gate-no-evidence", e, "accepted", "gate evidence_refs placeholder []")

    e = dict(good); e["event_id"] = "ct-b-dup"; e["case_id"] = "dup-first"
    case("dup-first", e, "accepted", "first copy accepted")
    e2 = dict(good); e2["event_id"] = "ct-b-dup"; e2["case_id"] = "dup-second"; e2["statement"] = "s2"
    case("dup-second", e2, "duplicate", "second copy suppressed by event_id dedup")

    return cases


def run_direct(mod, mutations) -> list[dict]:
    rows = []
    for m in mutations:
        try:
            mod.validate_event(json.loads(json.dumps(m["event"])))
            observed, err = "ok", None
        except mod.SchemaError as exc:
            observed, err = "SchemaError", str(exc)
        except Exception as exc:  # noqa: BLE001
            observed, err = type(exc).__name__, str(exc)
        rows.append({**{k: m[k] for k in ("rule_id", "source", "event_type", "expect", "note")},
                     "observed": observed, "error": err, "pass": observed == m["expect"]})
    return rows


def run_twins(mod, twins) -> list[dict]:
    rows = []
    for etype, ev in twins.items():
        try:
            mod.validate_event(json.loads(json.dumps(ev)))
            observed, err = "ok", None
        except Exception as exc:  # noqa: BLE001
            observed, err = type(exc).__name__, str(exc)
        rows.append({"event_type": etype, "event_id": ev["event_id"], "observed": observed,
                     "error": err, "pass": observed == "ok"})
    return rows


MUTANT_SPECS = [
    {"id": "M1-no-theorem-guard", "target_mutation": "R10-theorem-requires-artifact",
     "old": '    if typ == "claim" and event.get("conclusion_type") == "theorem" and not event.get("artifact_refs"):\n        raise SchemaError("claim: theorem conclusion requires artifact_refs (no fluent-text promotion)")\n',
     "new": "", "spec_rule": "R4-conclusion-vocabulary"},
    {"id": "M2-no-score-range", "target_mutation": "R7-review-score-range",
     "old": '    if typ == "review" and not (0 <= float(event["score"]) <= 5): raise SchemaError("review: score must be 0..5")\n',
     "new": "", "spec_rule": "R6-review-verdict-vocabulary"},
    {"id": "M3-no-conclusion-vocab", "target_mutation": "R4-conclusion-vocabulary",
     "old": '    if typ == "claim" and event["conclusion_type"] not in {"theorem", "conditional_theorem", "stability_result", "counterexample", "numerical_evidence", "formal_model", "open_problem"}:\n        raise SchemaError("claim: invalid conclusion_type")\n',
     "new": "", "spec_rule": "R10-theorem-requires-artifact"},
    {"id": "M4-no-required-fields", "target_mutation": "R3-claim-required-fields",
     "old": "    _required(event, validators[typ][0], typ)\n", "new": "    pass\n",
     "spec_rule": "R2-unknown-event-type"},
    {"id": "M5-no-status-vocab", "target_mutation": "R8-status-vocabulary",
     "old": '    if typ == "status" and event["status"] not in STATUSES: raise SchemaError("status: invalid node status")\n',
     "new": "", "spec_rule": "R9-gate-verdict-vocabulary"},
]


def run_mutant_controls(src_text: str, mutations: list[dict]) -> list[dict]:
    by_id = {m["rule_id"]: m for m in mutations}
    rows = []
    MUTANTS.mkdir(parents=True, exist_ok=True)
    for spec in MUTANT_SPECS:
        if spec["old"] not in src_text:
            rows.append({"id": spec["id"], "pass": False,
                         "error": "guard text not found in pinned schemas.py", "fired": None})
            continue
        text = src_text.replace(spec["old"], spec["new"], 1)
        path = MUTANTS / (spec["id"].replace("-", "_") + ".py")
        path.write_text(text)
        mod = load_module("mutant_" + spec["id"].replace("-", "_"), path)
        try:
            mod.validate_event(json.loads(json.dumps(by_id[spec["target_mutation"]]["event"])))
            fired, ferr = True, None
        except Exception as exc:  # noqa: BLE001
            fired, ferr = False, f"{type(exc).__name__}: {exc}"
        try:
            mod.validate_event(json.loads(json.dumps(by_id[spec["spec_rule"]]["event"])))
            spec_fired, serr = False, None
        except Exception as exc:  # noqa: BLE001
            spec_fired, serr = True, f"{type(exc).__name__}: {exc}"
        rows.append({"id": spec["id"], "mutant_sha256": sha256_file(path),
                     "target_mutation": spec["target_mutation"],
                     "target_accepted_by_mutant": fired, "target_error": ferr,
                     "specificity_rule": spec["spec_rule"], "specificity_rejected": spec_fired,
                     "specificity_error": serr, "pass": bool(fired and spec_fired)})
    return rows


def run_sandbox(comm) -> dict:
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    (SANDBOX / "research_map").mkdir(parents=True)
    (SANDBOX / "comms" / "outbox").mkdir(parents=True)
    (SANDBOX / "comms" / "inbox").mkdir(parents=True)
    (SANDBOX / "runtime" / "state").mkdir(parents=True)
    shutil.copy2(PINNED / "comms.py", SANDBOX / "research_map" / "comms.py")
    shutil.copy2(PINNED / "schemas.py", SANDBOX / "research_map" / "schemas.py")
    (SANDBOX / "asset.txt").write_text("sandbox asset for artifact sha default control\n")

    cases = bus_cases()
    lines = [json.dumps(c["event"], sort_keys=True) for c in cases]
    (SANDBOX / "comms" / "outbox" / "worker-ct.jsonl").write_text("\n".join(lines) + "\n")

    proc = subprocess.run([sys.executable, str(SANDBOX / "research_map" / "comms.py"), "ingest"],
                          cwd=str(SANDBOX), capture_output=True, text=True)
    accepted, rejected, duplicates = [], [], []
    for ln in (SANDBOX / "research_map" / "events.jsonl").read_text().splitlines():
        if ln.strip():
            accepted.append(json.loads(ln))
    rj = SANDBOX / "comms" / "rejected.jsonl"
    if rj.exists():
        for ln in rj.read_text().splitlines():
            if ln.strip():
                rejected.append(json.loads(ln))

    result = {"returncode": proc.returncode, "stdout_tail": proc.stdout[-2500:],
              "stderr_tail": proc.stderr[-2000:], "n_cases": len(cases),
              "n_accepted": len(accepted), "n_rejected": len(rejected)}
    # partition check per pre-registered case
    acc_by_case = {}
    for ev in accepted:
        if ev.get("case_id"):
            acc_by_case.setdefault(ev["case_id"], []).append(ev)
    rej_by_id = {r.get("event_id"): r for r in rejected}
    rows = []
    for c in cases:
        cid = c["case_id"]
        ev = c["event"]
        if c["expect"] == "accepted":
            got = cid in acc_by_case
            detail = {"accepted_ids": [e.get("event_id") for e in acc_by_case.get(cid, [])],
                      "normalized": sorted((acc_by_case.get(cid) or [{}])[0].get("_normalized", {}).keys())}
        elif c["expect"] == "rejected":
            rid = ev.get("event_id")
            got = rid in rej_by_id
            detail = {"reject_reason": (rej_by_id.get(rid) or {}).get("reason")}
        else:  # duplicate
            got = c["dup_of"] is None  # duplicate rows are checked in aggregate below
            detail = {"note": "duplicate case is validated in aggregate"}
        rows.append({"case_id": cid, "expect": c["expect"], "observed": "accepted" if cid in acc_by_case
                     else ("rejected" if ev.get("event_id") in rej_by_id else "absent"),
                     "pass": got, "detail": detail, "note": c["note"]})
    result["cases"] = rows
    result["duplicate_suppression"] = {"expect": 1, "observed_duplicate_cases": 0}
    # dedup control: exactly one accepted for ct-b-dup, none rejected for it
    n_dup_acc = len(acc_by_case.get("dup-first", [])) + len(acc_by_case.get("dup-second", []))
    n_dup_rej = int("ct-b-dup" in rej_by_id)
    result["duplicate_suppression"] = {"expect_accepted": 1, "observed_accepted": n_dup_acc,
                                       "observed_rejected": n_dup_rej,
                                       "pass": n_dup_acc == 1 and n_dup_rej == 0}
    # normalization records for the finding rows
    norm = {}
    for cid in ("no-falsifier", "no-evidence", "no-assumptions", "no-actor", "no-created-at",
                "review-no-score", "artifact-bad-status", "bad-status", "worker-done",
                "artifact-passed", "gate-no-evidence", "no-event-id"):
        evs = acc_by_case.get(cid, [])
        if evs:
            e = evs[0]
            norm[cid] = {"status": e.get("status") or e.get("validation_status"),
                         "score": e.get("score"), "falsifier": e.get("falsifier"),
                         "evidence_refs": e.get("evidence_refs"),
                         "actor": e.get("actor"), "event_id": e.get("event_id"),
                         "_normalized": e.get("_normalized")}
    result["normalization_records"] = norm
    result["pass"] = (proc.returncode == 0 and all(r["pass"] for r in rows)
                      and result["duplicate_suppression"]["pass"])
    return result


CITATIONS = {
    "research_map/comms.py": [
        (161, 168, "status", "status vocabulary coercion at the bus (invalid -> active/synonym)"),
        (174, 174, "next_falsifier", "default(\"next_falsifier\", \"unspecified\")"),
        (199, 201, "validation_status", "artifact validation_status coercion to unverified"),
        (202, 213, "sha256", "artifact sha256 computed on disk or set to 'unverified'"),
        (217, 217, "conclusion_type", "conclusion_type defaulted-conservative"),
        (219, 219, "assumptions", "assumptions defaulted []"),
        (221, 222, "falsifier", "falsifier/evidence_refs placeholders"),
        (229, 230, "score", "review missing score -> 0"),
        (301, 302, "event_id", "event_id generated when absent"),
        (306, 307, "created_at", "created_at/actor filled by ingest"),
        (310, 317, "validate_event", "validate_event call and reject record (rule enforcement site)"),
    ],
    "research_map/apply_events.py": [
        (249, 262, "done", "worker status=done demoted / ignored at map layer (AUTHORITY gate)"),
        (300, 305, "passed", "worker validation_status=passed demoted at map layer"),
    ],
    "research_map/schemas.py": [
        (27, 29, "event_type", "required top-level fields; unknown event_type rejected"),
        (45, 56, "required", "per-type required fields, vocabularies, theorem-artifact rule"),
    ],
}


def static_citations(live_texts: dict[str, str]) -> list[dict]:
    rows = []
    for path, specs in CITATIONS.items():
        text = live_texts[path]
        lines = text.splitlines()
        for lo, hi, token, note in specs:
            snippet = "\n".join(lines[lo - 1:hi])
            rows.append({"path": path, "lines": f"{lo}-{hi}", "token": token, "note": note,
                         "token_present": token in snippet,
                         "snippet": snippet[:600], "pass": token in snippet})
    return rows


def main() -> int:
    t0 = time.time()
    ART.joinpath("stdout.log").write_text("")  # placeholder replaced at exit
    pins_before = {name: sha256_file(p) for name, p in LIVE.items()}
    pinned_hashes = {name: sha256_file(p) for name, p in PIN_SRC.items()}
    pins_ok = {name: pinned_hashes[name] == pins_before[name] for name in PIN_SRC}

    live_texts = {name: LIVE[name].read_text() for name in
                  ("research_map/schemas.py", "research_map/comms.py", "research_map/apply_events.py")}
    schemas = load_module("pinned_schemas_061", PINNED / "schemas.py")

    mutations = direct_mutations()
    twins = valid_twins()
    cases = bus_cases()
    prereg = {"schema": "worker-061/bus-conformance/preregistration/v1",
              "task_id": "W061-A1-BUS-CONFORMANCE-01",
              "created_at": CST_TS, "actor": "worker-061", "node_id": "A1", "gate": "G-AUDIT",
              "class_id": "AF-SCC-C0-VAC-GEN",
              "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "GLOBAL"],
              "pins": {k: v for k, v in pins_before.items()},
              "direct_mutations": [{k: m[k] for k in ("rule_id", "source", "event_type", "expect", "note")}
                                   for m in mutations],
              "bus_cases": [{k: c[k] for k in ("case_id", "expect", "note")} for c in cases],
              "mutant_controls": [{k: s[k] for k in ("id", "target_mutation", "spec_rule")} for s in MUTANT_SPECS],
              "invariants": {
                  "no_canonical_write": "events.jsonl / rejected.jsonl / research_map.json byte-identical before/after",
                  "determinism": "direct matrix executed twice with identical outcome vectors",
              }}
    prereg_path = ART / "mutations.json"
    prereg_path.write_text(json.dumps(prereg, indent=1, sort_keys=True) + "\n")
    prereg_hash = sha256_file(prereg_path)

    direct1 = run_direct(schemas, mutations)
    direct2 = run_direct(schemas, mutations)
    deterministic = all(a["pass"] == b["pass"] and a["observed"] == b["observed"]
                        for a, b in zip(direct1, direct2))
    twin_rows = run_twins(schemas, twins)
    mutant_rows = run_mutant_controls((PINNED / "schemas.py").read_text(), mutations)
    sandbox = run_sandbox(None)
    citations = static_citations(live_texts)

    pins_after = {name: sha256_file(p) for name, p in LIVE.items()}
    pins_after_ok = {name: pins_after[name] == pins_before[name] for name in LIVE}

    enforcement = [
        {"rule": "R1 required event_id/created_at/actor", "bus": "normalized",
         "evidence": "comms.py:301-307 generate/fill; direct validate_event rejects (R1 row)"},
        {"rule": "R2 unknown event_type", "bus": "rejected", "evidence": "schemas.py:29, comms.py:310-317"},
        {"rule": "R3 per-type required fields", "bus": "partially enforced",
         "evidence": "semantic cores (statement, review verdict, gate verdict) rejected; falsifier/evidence_refs/"
                     "assumptions/score/next_falsifier/hours replaced by placeholders"},
        {"rule": "R4 conclusion_type vocabulary", "bus": "rejected", "evidence": "schemas.py:46-47"},
        {"rule": "R5 validation_status vocabulary", "bus": "normalized to unverified", "evidence": "comms.py:199-201"},
        {"rule": "R6 review verdict vocabulary", "bus": "rejected", "evidence": "schemas.py:50-51"},
        {"rule": "R7 review score range", "bus": "rejected when numeric out of range; missing->0",
         "evidence": "schemas.py:52, comms.py:227-235"},
        {"rule": "R8 node status vocabulary", "bus": "normalized to active", "evidence": "comms.py:161-168"},
        {"rule": "R9 gate verdict vocabulary", "bus": "rejected", "evidence": "schemas.py:54"},
        {"rule": "R10 theorem requires artifact_refs (PROTOCOL rule 1)", "bus": "rejected",
         "evidence": "schemas.py:55-56"},
        {"rule": "PROTOCOL rule 2 / authority (worker done, worker passed, gate verdict)",
         "bus": "accepted then demoted downstream", "evidence": "apply_events.py:249-262, 300-305"},
    ]
    findings = [
        {"id": "BC-01", "severity": "info", "finding":
            "Bus-level structural enforcement is fail-closed for event_type, explicit conclusion_type, review "
            "verdict, numeric score range, gate verdict and theorem-without-artifact_refs; all corresponding "
            "mutations are rejected at the pinned bytes."},
        {"id": "BC-02", "severity": "advisory", "finding":
            "PROTOCOL's required-fields rule is not enforced for outbox traffic: event_id, created_at and actor "
            "are generated/filled by ingest (comms.py:301-307), so only direct validate_event callers "
            "(e.g. append_event) see R1."},
        {"id": "BC-03", "severity": "advisory", "finding":
            "Several per-type requirements are satisfied by placeholders rather than evidence: claim.falsifier "
            "-> 'unspecified' (:221), claim.evidence_refs -> [] (:222), assumptions -> [] (:219), "
            "status.next_falsifier -> 'unspecified' (:174), review.score -> 0 (:229), gate/blocker/"
            "direction_update evidence_refs -> []. A claim with no falsifier and no evidence is bus-accepted."},
        {"id": "BC-04", "severity": "info", "finding":
            "Invalid status / validation_status values are silently coerced (status -> active, "
            "validation_status -> unverified), never rejected; worker status=done and "
            "validation_status=passed pass the bus unchanged. Authority is enforced one layer down at "
            "apply_events.py:249-262 and :300-305, which demote them; the two-layer split is correct but "
            "means bus acceptance alone proves no authority."},
        {"id": "BC-05", "severity": "info", "finding":
            "Duplicate event_id suppression happens before validation (comms.py:303-305); the duplicate is "
            "neither accepted nor rejected, so rejected.jsonl is not a complete traffic census."},
    ]
    report = {
        "schema": "worker-061/bus-conformance/report/v1",
        "task_id": "W061-A1-BUS-CONFORMANCE-01", "actor": "worker-061", "node_id": "A1",
        "gate": "G-AUDIT", "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "GLOBAL"],
        "created_at": CST_TS,
        "scope": "Bus boundary only (schemas.validate_event + comms.normalize_event/ingest) plus static "
                 "citation of the downstream authority demotion. No schema semantics review, no coverage "
                 "count, no gate verdict.",
        "authority_note": "Worker evidence only: no canonical write, no gate verdict, no node status, "
                          "no validation_status=passed.",
        "pins_before": pins_before, "pins_after": pins_after,
        "pinned_copy_matches_live": pins_ok, "canonical_unchanged": pins_after_ok,
        "preregistration": {"path": "artifacts/worker-061/bus_conformance_01/mutations.json",
                            "sha256": prereg_hash},
        "direct_validate_event_matrix": direct1,
        "direct_matrix_deterministic": deterministic,
        "valid_twins": twin_rows,
        "mutant_teeth_controls": mutant_rows,
        "bus_sandbox": sandbox,
        "static_citations": citations,
        "enforcement_matrix": enforcement,
        "findings": findings,
        "hard_failures": [],
        "counts": {
            "direct_mutations": len(direct1), "direct_mutations_passed": sum(r["pass"] for r in direct1),
            "valid_twins": len(twin_rows), "valid_twins_passed": sum(r["pass"] for r in twin_rows),
            "mutant_controls": len(mutant_rows), "mutant_controls_passed": sum(r["pass"] for r in mutant_rows),
            "bus_cases": len(cases), "bus_cases_passed": sum(r["pass"] for r in sandbox["cases"]),
            "citations": len(citations), "citations_passed": sum(r["pass"] for r in citations),
        },
        "verdict": None,
        "falsifier": "Re-run this instrument at the declared pins: falsified for any row whose observed "
                     "outcome differs from mutations.json, if pinned copy != live bytes, if canonical "
                     "events.jsonl/rejected.jsonl/research_map.json change during the run, if sandbox ingest "
                     "returncode != 0, or if any mutant control does not fire or loses specificity.",
        "next_falsifier": "Re-run after any write to research_map/comms.py, research_map/schemas.py or "
                          "research_map/apply_events.py; a byte move voids the citation rows for the moved file.",
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        "wall_seconds": round(time.time() - t0, 3)},
    }
    # verdict: accept the instrument's behaviours if every control passes
    all_pass = (all(r["pass"] for r in direct1) and all(r["pass"] for r in twin_rows)
                and all(r["pass"] for r in mutant_rows) and sandbox["pass"]
                and all(r["pass"] for r in citations) and all(pins_ok.values())
                and all(pins_after_ok.values()) and deterministic)
    report["verdict"] = "accept" if all_pass else "revise"
    report["counts"]["all_checks_passed"] = all_pass
    (ART / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    log = [f"task=W061-A1-BUS-CONFORMANCE-01 verdict={report['verdict']}",
           f"pins_ok={pins_ok} canonical_unchanged={pins_after_ok} deterministic={deterministic}",
           f"counts={report['counts']}",
           "sandbox stdout tail:", sandbox["stdout_tail"]]
    (ART / "stdout.log").write_text("\n".join(str(x) for x in log) + "\n")
    print("\n".join(str(x) for x in log[:3]))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

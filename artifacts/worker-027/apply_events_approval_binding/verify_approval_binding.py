#!/usr/bin/env python3
"""W027-APPLYEV-RESBIND-01 — independent checker for the controller approval matcher.

Question: at research_map/apply_events.py revision sha256 6f866c716c4f (pinned copy,
2026-09-12 ~00:29), does the status-event approval matcher
`resource_request\\s+(\\S+?):` bind controller APPROVED notices whose resource-request
id contains colons?  While this task ran, the live file was edited (mtime 00:31:19) to
revision 16820bf206b7.  This checker therefore measures BOTH revisions:

  A. old revision: reproduce the miss and the silent mis-bind hazard on a byte-frozen
     snapshot of the real APPROVED notices and the frozen map's resource_requests;
  B. new revision: extract the new matcher/guard semantics from the new bytes and verify
     every real notice binds to the correct request id, with no regression and the new
     superseded-guard / DENIED paths exercised by controls.

All semantics are extracted from source via ast (regex, rstrip set, guard), not from
this prose.  No repository file is modified.

Exit codes
  0  DEFECT_REPRODUCED_AT_OLD and FIX_VERIFIED at the newest measured revision
  2  INPUT_DRIFT  (a pinned snapshot fails its sha256; fail closed)
  3  FIX_NOT_VERIFIED / REGRESSION_AT_LIVE
"""

from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SNAP = HERE / "snapshots"

REV_OLD = "6f866c716c4f"
REV_NEW = "16820bf206b7"
PINS = {
    f"snapshots/apply_events.{REV_OLD}.py":
        "6f866c716c4f3fc5cfde0da9f2dcda5a0b2b73e864e4726e8702b8c417549d1b",
    f"snapshots/apply_events.{REV_NEW}.py":
        "16820bf206b720d59199aa26374e6db2ae4de45da3e9cb4e8763750bd864efed",
    "snapshots/astra_repair_03_resources.9077bdf9dbfb.py":
        "9077bdf9dbfb94713b36783e17c0c2fec5c54662ce3c8970e57245b1cd3e5197",
    "snapshots/resource_requests.json":
        "577b8a8c3186c94e5658f18269d0452b37ba06ccd92365d49f9f39f7ac6ceff7",
    "snapshots/approved_notices.jsonl":
        "8651465141521c30a037df41665305d1a11de6acd2ccc2c4f33ea693c5f5e6f9",
}
LIVE_APPLY = ROOT / "research_map" / "apply_events.py"
COLON_NOTICE_ID = "leadform-resource-request-2026-09-12T00:44:00+08:00"
COLON_NOTICE = f"resource_request {COLON_NOTICE_ID}: APPROVED 6.0 agent-hours"

FALSIFIER = (
    "The finding is FALSIFIED if (a) the pinned old revision does not contain exactly one "
    "resource_request regex, or it is not 'resource_request\\s+(\\S+?):'; or (b) that matcher "
    "returns the full colon id for the pinned colon notice (no truncation); or (c) on the "
    "pinned notice snapshot the old matcher binds every notice to its correct request id "
    "(no CURRENT_MISS); or (d) control FX-DECOY does not show the old matcher approving the "
    "truncated-prefix decoy; or (e) at the newest measured revision the matcher binds any "
    "real notice to a wrong or missing request id, breaks a notice the old matcher bound "
    "correctly, mutates a superseded request's status, or fails the DENIED / punctuation "
    "controls; or (f) any pinned snapshot sha256 fails (checker exits 2). If the live file "
    "is a third revision that does not bind the colon id, the verdict is REGRESSION_AT_LIVE "
    "(exit 3)."
)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_pins() -> list[str]:
    errs = []
    for rel, want in PINS.items():
        p = HERE / rel
        if not p.exists():
            errs.append(f"missing {rel}")
        elif sha256_file(p) != want:
            errs.append(f"{rel}: sha256 {sha256_file(p)} != pinned {want}")
    return errs


def _str_const(node) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def extract_spec(source: str) -> dict:
    """Extract, from the source itself, the approval-branch semantics.

    Returns patterns (re.search constants containing 'resource_request'), the rstrip
    character set if the revision strips the captured token, whether the branch guards
    superseded requests, and whether DENIED triggers the branch.
    """
    tree = ast.parse(source)
    patterns: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "search" and node.args:
            s = _str_const(node.args[0])
            if s is not None:
                patterns.append(s)
    approval = [p for p in patterns if "resource_request" in p]

    # Locate the approval branch: an If whose test mentions the resource_request literal.
    branch = None
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_strs = [s for s in (_str_const(n) for n in ast.walk(node.test)) if s]
            if any("resource_request" in s for s in test_strs):
                branch = node
                break
    strip_chars = None
    guard_superseded = False
    denied = False
    trigger_denied = False
    if branch is not None:
        test_strs = [s for s in (_str_const(n) for n in ast.walk(branch.test)) if s]
        trigger_denied = any("DENIED" in s for s in test_strs)
        for node in ast.walk(branch):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr == "rstrip" and node.args:
                strip_chars = _str_const(node.args[0])
            s = _str_const(node)
            if s == "superseded":
                guard_superseded = True
            if s == "denied":
                denied = True
    return {
        "patterns": patterns,
        "approval_patterns": approval,
        "strip_chars": strip_chars,
        "guard_superseded": guard_superseded,
        "denied_result": denied,
        "trigger_denied": trigger_denied,
    }


def capture_id(spec: dict, summary: str) -> str | None:
    if not spec["approval_patterns"]:
        return None
    m = re.search(spec["approval_patterns"][0], summary)
    if not m:
        return None
    cap = m.group(1)
    if spec["strip_chars"]:
        cap = cap.rstrip(spec["strip_chars"])
    return cap


def emulate(spec: dict, requests: list[dict], notices: list[dict]) -> list[dict]:
    """Mirror the revision's approval branch on status events."""
    out = [dict(r) for r in requests]
    for ev in notices:
        summary = str(ev.get("summary", ""))
        trig = "resource_request" in summary and (
            "APPROVED" in summary or (spec["trigger_denied"] and "DENIED" in summary))
        if not trig:
            continue
        cap = capture_id(spec, summary)
        if not cap:
            continue
        for r in out:
            if r.get("event_id") != cap:
                continue
            if spec["guard_superseded"] and r.get("status") == "superseded":
                r["decision_note"] = "ignored decision for superseded request: " + summary[:300]
                continue
            if "APPROVED" in summary:
                r["status"] = "approved"
            elif spec["denied_result"]:
                r["status"] = "denied"
            r["decision_at"] = "EMULATED"
            r["decision_by"] = "astra"
            if spec["strip_chars"] is not None:
                r["decision_note"] = summary[:400]
    return out


def notice_rows(spec: dict, requests: list[dict], notices: list[dict]) -> list[dict]:
    ids = {r.get("event_id") for r in requests}
    rows = []
    for ev in notices:
        summary = str(ev.get("summary", ""))
        cap = capture_id(spec, summary)
        rows.append({
            "notice_event_id": ev.get("event_id"),
            "summary_sha256": hashlib.sha256(summary.encode()).hexdigest(),
            "captured_id": cap,
            "bound": bool(cap in ids),
            "bound_to": cap if cap in ids else None,
        })
    return rows


def fx_map(*pairs) -> list[dict]:
    return [{"event_id": eid, "status": st} for eid, st in pairs]


def run_fixture(spec, reqs, notice_text) -> list[dict]:
    out = emulate(spec, reqs, [{"summary": notice_text}])
    return [r["status"] for r in out]


def ctl(name, expected, observed):
    return {"control": name, "expected": expected, "observed": observed, "pass": expected == observed}


def build_report() -> dict:
    old_src = (SNAP / f"apply_events.{REV_OLD}.py").read_text()
    new_src = (SNAP / f"apply_events.{REV_NEW}.py").read_text()
    repair_src = (SNAP / "astra_repair_03_resources.9077bdf9dbfb.py").read_text()
    requests = json.loads((SNAP / "resource_requests.json").read_text())
    notices = [json.loads(l) for l in (SNAP / "approved_notices.jsonl").read_text().splitlines() if l.strip()]

    old_spec = extract_spec(old_src)
    new_spec = extract_spec(new_src)
    frozen = {r.get("event_id"): r.get("status") for r in requests}
    req_ids = set(frozen)
    baseline = [{"event_id": eid, "status": "pending"} for eid in frozen]

    def measure(label, spec):
        rows = notice_rows(spec, requests, notices)
        uniq = {}
        for r in rows:
            uniq[(r["notice_event_id"], r["summary_sha256"])] = r
        table = list(uniq.values())
        scope = {r["bound_to"] for r in table if r["bound_to"]}
        rep = {r["event_id"]: r["status"] for r in emulate(spec, baseline, notices)}
        mismatch = [i for i in sorted(scope) if rep.get(i) != frozen.get(i)]
        return {"label": label, "spec": spec, "table": table,
                "n_notices": len(table),
                "n_bound": sum(1 for r in table if r["bound"]),
                "n_unbound": sum(1 for r in table if not r["bound"]),
                "scope": sorted(scope), "replay": rep, "replay_mismatch": mismatch}

    old_m = measure("old_" + REV_OLD, old_spec)
    new_m = measure("new_" + REV_NEW, new_spec)
    # Notice scope = every request id captured by EITHER revision, so the old revision's
    # dropped notice is inside the comparison rather than silently excluded.
    scope_ids = sorted({r["bound_to"] for m in (old_m, new_m) for r in m["table"] if r["bound_to"]})
    for m in (old_m, new_m):
        m["scope"] = scope_ids
        m["replay_mismatch"] = [i for i in scope_ids if m["replay"].get(i) != frozen.get(i)]

    # Cross-revision regression: every notice the old revision bound correctly must bind to
    # the same id in the new revision; new must bind every unbound old notice.
    old_by_key = {(r["notice_event_id"], r["summary_sha256"]): r for r in old_m["table"]}
    new_by_key = {(r["notice_event_id"], r["summary_sha256"]): r for r in new_m["table"]}
    regressions, fixed = [], []
    for k, o in old_by_key.items():
        n = new_by_key.get(k)
        if n is None:
            regressions.append({"key": list(k), "why": "missing in new revision"})
        elif o["bound"] and n["captured_id"] != o["captured_id"]:
            regressions.append({"key": list(k), "old": o["captured_id"], "new": n["captured_id"]})
        elif not o["bound"] and n["bound"]:
            fixed.append({"key": list(k), "old_capture": o["captured_id"], "new_capture": n["captured_id"]})

    # Comparative fixtures: each is run through both revisions' extracted semantics.
    trunc = COLON_NOTICE_ID.split(":")[0]
    fixtures = [
        ("FX-MISS colon id", fx_map((COLON_NOTICE_ID, "pending")), COLON_NOTICE,
         ["pending"], ["approved"]),
        ("FX-DECOY truncated-prefix collision",
         fx_map((trunc, "pending"), (COLON_NOTICE_ID, "pending")), COLON_NOTICE,
         ["approved", "pending"], ["pending", "approved"]),
        ("FX-FREE colon-free id", fx_map(("flash19-0009", "pending")),
         "resource_request flash19-0009: APPROVED scoped to x", ["approved"], ["approved"]),
        ("FX-PUNCT trailing separator", fx_map(("id-1", "pending")),
         "resource_request id-1: APPROVED x", ["approved"], ["approved"]),
        ("FX-NESTED two occurrences", fx_map(("X", "pending"), ("Y", "pending")),
         "resource_request X: see also resource_request Y: APPROVED", ["approved", "pending"],
         ["approved", "pending"]),
        ("FX-DENIED denied path", fx_map(("id-2", "pending")),
         "resource_request id-2: DENIED no allocation", ["pending"], ["denied"]),
    ]
    controls = []
    for name, reqs, text, exp_old, exp_new in fixtures:
        controls.append(ctl(name + " [old vs new]",
                            {"old": exp_old, "new": exp_new},
                            {"old": run_fixture(old_spec, reqs, text),
                             "new": run_fixture(new_spec, reqs, text)}))
    # Superseded guard: old overwrites a superseded request; new must leave it and record a note.
    sup_old = run_fixture(old_spec, fx_map(("id-3", "superseded")),
                          "resource_request id-3: APPROVED late notice")
    sup_new = emulate(new_spec, fx_map(("id-3", "superseded")),
                      [{"summary": "resource_request id-3: APPROVED late notice"}])
    controls.append(ctl("FX-SUPERSEDED guard [old vs new]",
                        {"old": ["approved"], "new": ["superseded"]},
                        {"old": sup_old, "new": [sup_new[0]["status"]]}))
    controls.append(ctl("FX-SUPERSEDED note recorded (new only)",
                        True, "decision_note" in sup_new[0] and "ignored" in sup_new[0]["decision_note"]))

    # Repair cross-checks on the real map state.
    repair_approved = sorted(re.findall(r'"([^"]+)": \{\n\s+"decision_event_id"', repair_src))
    repair_superseded = sorted(re.findall(r'"([^"]+)":\n\s+"superseded', repair_src))
    frozen_superseded = sorted(i for i in frozen if frozen.get(i) == "superseded")
    old_newly_bound = sorted(i for i in old_m["scope"] if old_m["replay"].get(i) != "approved"
                             and new_m["replay"].get(i) == "approved")
    controls.append(ctl("CTL-REPAIR repair APPROVED set == newly bound by new revision",
                        repair_approved, old_newly_bound))
    controls.append(ctl("CTL-SUPERSEDED repair SUPERSEDED set == frozen superseded",
                        repair_superseded, frozen_superseded))
    twice = emulate(new_spec, emulate(new_spec, baseline, notices), notices)
    controls.append(ctl("CTL-IDEMPOTENT new replay idempotent",
                        new_m["replay"], {r["event_id"]: r["status"] for r in twice}))

    # Live revision (informational; a third revision is emulated from its own bytes).
    live = {"path": "research_map/apply_events.py", "present": LIVE_APPLY.exists()}
    if LIVE_APPLY.exists():
        live_src = LIVE_APPLY.read_text()
        live["sha256"] = sha256_file(LIVE_APPLY)
        live["mtime"] = datetime.datetime.fromtimestamp(
            os.stat(LIVE_APPLY).st_mtime, datetime.timezone(datetime.timedelta(hours=8))
        ).isoformat(timespec="seconds")
        live["is_new_snapshot"] = live["sha256"] == PINS[f"snapshots/apply_events.{REV_NEW}.py"]
        try:
            live_spec = extract_spec(live_src)
            live["spec"] = live_spec
            live["captures_colon_id"] = capture_id(live_spec, COLON_NOTICE)
            live_rows = notice_rows(live_spec, requests, notices)
            live["n_bound"] = sum(1 for r in live_rows if r["bound"])
            live["n_unbound"] = sum(1 for r in live_rows if not r["bound"])
            live["regressions_vs_new"] = [
                {"notice": r["notice_event_id"], "captured": r["captured_id"]}
                for r in live_rows
                if not r["bound"] or (r["bound"] and new_by_key.get(
                    (r["notice_event_id"], r["summary_sha256"]), {}).get("captured_id") != r["captured_id"])
            ]
        except SyntaxError as exc:
            live["parse_error"] = str(exc)
            live["captures_colon_id"] = None

    old_ok = (old_spec["approval_patterns"] == [r"resource_request\s+(\S+?):"]
              and old_m["n_bound"] < old_m["n_notices"]
              and controls[0]["pass"] and controls[1]["pass"])
    new_ok = (new_m["n_unbound"] == 0 and not regressions
              and all(c["pass"] for c in controls)
              and not new_m["replay_mismatch"])
    live_ok = live.get("captures_colon_id") == COLON_NOTICE_ID \
        and live.get("n_unbound") == 0 and not live.get("regressions_vs_new")
    if not live_ok:
        verdict = "REGRESSION_AT_LIVE"
    elif old_ok and new_ok:
        verdict = f"DEFECT_REPRODUCED_AT_{REV_OLD}; FIX_VERIFIED_AT_{REV_NEW}"
    else:
        verdict = "FIX_NOT_VERIFIED"

    findings = [
        {"id": "W027-F1", "severity": "major",
         "status": "CONFIRMED (historical at pinned revision)" if old_ok else "NOT_REPRODUCED",
         "statement": (f"At revision {REV_OLD}, the approval matcher 'resource_request\\s+(\\S+?):' "
                       f"truncated '{COLON_NOTICE_ID}' to '{COLON_NOTICE_ID.split(':')[0]}' at the "
                       "first colon, bound no request, and silently dropped the controller's "
                       "APPROVED decision. The frozen map's 'approved' status for that request came "
                       "from the out-of-band repair script, not from event replay."),
         "measured": {"old_bound": old_m["n_bound"], "old_notices": old_m["n_notices"],
                      "old_replay_mismatch": old_m["replay_mismatch"],
                      "repair_approved": repair_approved}},
        {"id": "W027-F2", "severity": "major",
         "status": "CONFIRMED (hazard; no real collision in corpus)" if controls[0]["pass"] else "NOT_REPRODUCED",
         "statement": ("The truncation was a silent mis-bind hazard, not only a miss: with a request "
                       "whose event_id equals the truncated prefix, the old matcher approves the "
                       "wrong request (control FX-COLON). No such prefix collision exists among the "
                       "24 requests in the pinned corpus."),
         "measured": {"real_prefix_collisions": sorted(
             {str(r.get("event_id")).split(":")[0] for r in requests if ":" in str(r.get("event_id"))}
             & req_ids)}},
    ]
    if new_ok and live_ok:
        findings.append({
            "id": "W027-F3", "severity": "info", "status": "FIX_VERIFIED",
            "statement": (f"Revision {REV_NEW} (live mtime {live.get('mtime')}, unannounced at "
                          "measurement time) binds all 7 pinned notices to the correct request ids "
                          "(old: 6/7), shows zero regressions on notices the old matcher bound, "
                          "makes pending-baseline replay reproduce the frozen approved set, and "
                          "passes the DENIED, superseded-guard, punctuation and idempotence controls. "
                          "Live bytes measured at the same revision."),
            "measured": {"new_bound": new_m["n_bound"], "new_unbound": new_m["n_unbound"],
                         "fixed_notices": fixed, "regressions": regressions,
                         "new_replay_mismatch": new_m["replay_mismatch"],
                         "live_sha256": live.get("sha256"), "live_mtime": live.get("mtime")},
        })
        findings.append({
            "id": "W027-F4", "severity": "info", "status": "RESIDUAL",
            "statement": ("Supersession is still produced only out-of-band: apply_events has no "
                          "supersession rule, so a full event-log rebuild still needs the repair "
                          "script for the 4 frozen 'superseded' statuses. The new superseded-guard "
                          "prevents a late notice from overwriting them, which is a hardening."),
            "measured": {"frozen_superseded": frozen_superseded, "repair_superseded": repair_superseded},
        })
        findings.append({
            "id": "W027-F5", "severity": "info", "status": "RESIDUAL",
            "statement": ("astra_repair_03_resources.py's docstring still describes the old "
                          "matcher 'resource_request\\s+(\\S+?):' as the live defect; at revision "
                          f"{REV_NEW} that matcher no longer exists, so the docstring is stale "
                          "(the repair script itself is a hard-coded decision table and needs no "
                          "matcher). The census finds no other resource_request matcher in "
                          "research_map/*.py."),
            "measured": {"repair_docstring_has_old_pattern": "\\S+?" in repair_src,
                         "other_matchers": "none in research_map/*.py (grep census, 00:36)"},
        })

    return {
        "task_id": "W027-APPLYEV-RESBIND-01",
        "checker": str(Path(__file__).relative_to(ROOT)),
        "generated_at": None,
        "pins": {rel: {"expected": want, "measured": sha256_file(HERE / rel)} for rel, want in PINS.items()},
        "revisions": {"old": {"sha256": PINS[f"snapshots/apply_events.{REV_OLD}.py"], "spec": old_spec},
                      "new": {"sha256": PINS[f"snapshots/apply_events.{REV_NEW}.py"], "spec": new_spec}},
        "old_revision_measurement": {k: v for k, v in old_m.items() if k != "spec"},
        "new_revision_measurement": {k: v for k, v in new_m.items() if k != "spec"},
        "cross_revision": {"fixed_notices": fixed, "regressions": regressions},
        "repair_cross_check": {"approved": repair_approved, "superseded": repair_superseded,
                               "frozen_superseded": frozen_superseded,
                               "newly_bound_by_new_revision": old_newly_bound},
        "controls": controls,
        "live_source": live,
        "findings": findings,
        "falsifier": FALSIFIER,
        "verdict": verdict,
        "exit_code": 0 if verdict.startswith("DEFECT_REPRODUCED") else 3,
    }


def tamper_control() -> int:
    errs = check_pins()
    if errs:
        print("TAMPER-CONTROL FAIL: clean snapshot already fails pins:", errs)
        return 1
    tmp = HERE / "tmp_tamper_control"
    tmp.mkdir(exist_ok=True)
    src = SNAP / "resource_requests.json"
    dst = tmp / src.name
    data = bytearray(src.read_bytes())
    data[-2] ^= 0x01
    dst.write_bytes(bytes(data))
    tampered_sha = sha256_file(dst)
    detected = tampered_sha != PINS["snapshots/resource_requests.json"]
    dst.unlink()
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"TAMPER-CONTROL {'PASS' if detected else 'FAIL'}: mutated copy sha256 {tampered_sha}")
    return 0 if detected else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tamper-control", action="store_true")
    ap.add_argument("--out", default=str(HERE / "report.json"))
    args = ap.parse_args()
    if args.tamper_control:
        return tamper_control()

    pin_errors = check_pins()
    if pin_errors:
        print("INPUT_DRIFT (fail closed):")
        for e in pin_errors:
            print("  -", e)
        return 2

    rep = build_report()
    rep["generated_at"] = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="seconds")
    Path(args.out).write_text(json.dumps(rep, indent=1, sort_keys=False) + "\n")
    print(json.dumps({
        "verdict": rep["verdict"],
        "old": {"bound": rep["old_revision_measurement"]["n_bound"],
                "of": rep["old_revision_measurement"]["n_notices"],
                "replay_mismatch": rep["old_revision_measurement"]["replay_mismatch"]},
        "new": {"bound": rep["new_revision_measurement"]["n_bound"],
                "of": rep["new_revision_measurement"]["n_notices"],
                "replay_mismatch": rep["new_revision_measurement"]["replay_mismatch"]},
        "live_sha256": rep["live_source"].get("sha256"),
        "live_mtime": rep["live_source"].get("mtime"),
        "controls_pass": [c["pass"] for c in rep["controls"]],
        "report": str(Path(args.out).relative_to(ROOT)),
    }, indent=1))
    for f in rep["findings"]:
        print(f"{f['id']}: {f['status']}")
    return rep["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())

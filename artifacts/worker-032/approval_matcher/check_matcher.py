#!/usr/bin/env python3
"""W032-APPROVAL-MATCHER-01: independent measurement of the resource-request
approval matcher in `research_map/apply_events.py` (approval branch, lines
263-273 at the pinned revision).

Question
--------
The controller records a resource-request decision by writing a `status` event
whose summary contains `resource_request <request-id>: APPROVED ...`. The
applier binds that decision to the map entry with

    rid = re.search(r"resource_request\\s+(\\S+?):", summary)
    ... if r.get("event_id") == rid.group(1): r["status"] = "approved"

The capture is non-greedy and stops at the FIRST colon. Request ids minted as
`<name>-<ISO8601 timestamp>` (e.g. `leadform-resource-request-2026-09-12T00:44:00+08:00`)
contain colons, so the capture truncates and the approval binds nothing.

This checker:
  1. reproduces the matcher against the pinned accepted event stream,
  2. measures how many recorded approvals bind / are silently lost / would bind
     the WRONG request,
  3. measures the latent exposure (requests whose ids contain colons and are not
     yet terminal),
  4. evaluates candidate one-line replacements on a fixture suite with negative
     and adversarial controls, and names the strictest one,
  5. re-hashes every input at the end and marks the window unstable if anything
     moved.

Read-only on shared state. Writes only `--out` (default: report.json beside this
script). stdlib only, deterministic, no network.

Usage
-----
    python3 check_matcher.py --selftest      # fixtures only, prints PASS/FAIL
    python3 check_matcher.py --out report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAP = ROOT / "research_map" / "research_map.json"
EVENTS = ROOT / "research_map" / "events.jsonl"
APPLIER = ROOT / "research_map" / "apply_events.py"
REPAIR = ROOT / "research_map" / "astra_repair_03_resources.py"

INPUTS = {
    "research_map/apply_events.py": APPLIER,
    "research_map/events.jsonl": EVENTS,
    "research_map/research_map.json": MAP,
    "research_map/astra_repair_03_resources.py": REPAIR,
}

# Candidate matchers. P0 is the shipped one; P3 is the recommended one-liner.
PATTERNS = {
    "P0_current": r"resource_request\s+(\S+?):",
    "P1_greedy": r"resource_request\s+(\S+):",
    "P2_lookahead": r"resource_request\s+(\S+?):(?=\s|$)",
    "P3_anchored": r"resource_request\s+(\S+?):\s*APPROVED",
}
RECOMMENDED = "P3_anchored"

# ---------------------------------------------------------------------------
# fixture suite
# Each fixture: summary text, the ids that exist in the request registry, and
# the value each pattern must capture (None = no match). `expect` is asserted
# literally, so a fixture is a control on the checker itself, not a restatement
# of the code under test.
# ---------------------------------------------------------------------------
COLON_ID = "leadform-resource-request-2026-09-12T00:44:00+08:00"
FIXTURES = [
    {
        "id": "F01-real-colon-id",
        "summary": f"resource_request {COLON_ID}: APPROVED 6.0 agent-hours, bounded to the verification round",
        "request_ids": [COLON_ID],
        "expect": {"P0_current": "leadform-resource-request-2026-09-12T00",
                   "P1_greedy": COLON_ID, "P2_lookahead": COLON_ID, "P3_anchored": COLON_ID},
        "note": "LIVE case: current matcher truncates at the first colon; approval is a silent no-op",
    },
    {
        "id": "F02-real-plain-id",
        "summary": "resource_request lit-l3-20260912-010: APPROVED 3.0 agent-hours for two independent reviewers",
        "request_ids": ["lit-l3-20260912-010"],
        "expect": {"P0_current": "lit-l3-20260912-010", "P1_greedy": "lit-l3-20260912-010",
                   "P2_lookahead": "lit-l3-20260912-010", "P3_anchored": "lit-l3-20260912-010"},
        "note": "LIVE case: no colon in id, every candidate must preserve the binding",
    },
    {
        "id": "F03-prefix-collision",
        "summary": "resource_request abc:2026-01-01T00:00:00+00:00: APPROVED 1h",
        "request_ids": ["abc", "abc:2026-01-01T00:00:00+00:00"],
        "expect": {"P0_current": "abc", "P1_greedy": "abc:2026-01-01T00:00:00+00:00",
                   "P2_lookahead": "abc:2026-01-01T00:00:00+00:00",
                   "P3_anchored": "abc:2026-01-01T00:00:00+00:00"},
        "note": "ADVERSARIAL: truncation equals another live request id -> wrong request approved",
    },
    {
        "id": "F04-no-space-delimiter",
        "summary": "resource_request id-1:APPROVED 1h",
        "request_ids": ["id-1"],
        "expect": {"P0_current": "id-1", "P1_greedy": "id-1", "P2_lookahead": None, "P3_anchored": "id-1"},
        "note": "FORMAT EDGE: ':<APPROVED>' with no space; lookahead-only fix regresses this, anchored fix does not",
    },
    {
        "id": "F05-unbound-format",
        "summary": "resource_request id-2 APPROVED 1h",
        "request_ids": ["id-2"],
        "expect": {"P0_current": None, "P1_greedy": None, "P2_lookahead": None, "P3_anchored": None},
        "note": "RESIDUAL: no ':' delimiter at all; no candidate binds it -- out of scope, kept honest",
    },
    {
        "id": "F06-two-mentions",
        "summary": "resource_request a-1: pending, more work; resource_request b:2: APPROVED now",
        "request_ids": ["a-1", "b:2"],
        "expect": {"P0_current": "a-1", "P1_greedy": "a-1", "P2_lookahead": "a-1", "P3_anchored": "b:2"},
        "note": "ADVERSARIAL: a pending mention precedes the approved one; only the APPROVED-anchored matcher picks the right id",
    },
    {
        "id": "F07-guard-off",
        "summary": "APPROVED but the summary never names a resource_request id",
        "request_ids": [],
        "expect": {"P0_current": None, "P1_greedy": None, "P2_lookahead": None, "P3_anchored": None},
        "note": "NEGATIVE CONTROL: the enclosing guard ('resource_request' and 'APPROVED') does not fire",
    },
    {
        "id": "F08-lowercase-approved",
        "summary": "resource_request id-3: approved 1h",
        "request_ids": ["id-3"],
        "expect": {"P0_current": "id-3", "P1_greedy": "id-3", "P2_lookahead": "id-3", "P3_anchored": None},
        "note": "RESIDUAL: the guard is case-sensitive on APPROVED; anchored matcher correctly declines",
    },
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def capture(pattern: str, summary: str):
    m = re.search(pattern, summary)
    return m.group(1) if m else None


def run_fixtures() -> dict:
    results, failures = [], []
    for fx in FIXTURES:
        row = {"id": fx["id"], "note": fx["note"], "summary": fx["summary"],
               "request_ids": fx["request_ids"], "captured": {}, "ok": True}
        for name, pat in PATTERNS.items():
            got = capture(pat, fx["summary"])
            want = fx["expect"][name]
            row["captured"][name] = got
            if got != want:
                row["ok"] = False
                failures.append(f"{fx['id']}/{name}: got {got!r} want {want!r}")
        # wrong-binding classification: captured an id that exists but is not
        # the id the notice approves (the approved id is the longest id that
        # occurs verbatim in the summary).
        approved = max((i for i in fx["request_ids"] if i in fx["summary"]),
                       key=len, default=None)
        row["approved_id"] = approved
        row["wrong_binding"] = {n: (c in fx["request_ids"] and c != approved)
                                for n, c in row["captured"].items() if c is not None}
        results.append(row)

    # mutation control: removing the colons from the live id must remove the
    # truncation, proving the colon (not summary length) is the cause.
    mutated = FIXTURES[0]["summary"].replace(COLON_ID, COLON_ID.replace(":", "-"))
    mut = {"id": "M01-colon-removed-control", "note": "CONTROL: same summary, colons in id replaced by '-'",
           "summary": mutated, "captured": {}, "expected_all": COLON_ID.replace(":", "-")}
    for name, pat in PATTERNS.items():
        mut["captured"][name] = capture(pat, mutated)
        if mut["captured"][name] != mut["expected_all"]:
            failures.append(f"M01/{name}: got {mut['captured'][name]!r}")
    results.append(mut)

    # liveness control: the shipped matcher MUST fail on F01, otherwise the
    # measurement target has changed and the report must not be believed.
    if capture(PATTERNS["P0_current"], FIXTURES[0]["summary"]) == COLON_ID:
        failures.append("LIVENESS: P0 unexpectedly bound the colon id; matcher may already be fixed")
    return {"fixtures": results, "failures": failures, "ok": not failures}


def load_inputs() -> dict:
    before = {rel: sha256_file(p) for rel, p in INPUTS.items()}
    events = [json.loads(line) for line in EVENTS.read_text().splitlines() if line.strip()]
    m = json.loads(MAP.read_text())
    return {"before": before, "events": events, "map": m}


def measure(data: dict) -> dict:
    events, m = data["events"], data["map"]
    requests = m.get("resource_requests", [])
    req_ids = [str(r.get("event_id")) for r in requests]
    req_by_id = {str(r.get("event_id")): r for r in requests}

    notices = []
    for ev in events:
        s = str(ev.get("summary", ""))
        if "resource_request" in s and "APPROVED" in s:
            # ground truth = longest registered id occurring verbatim in the summary
            present = [i for i in req_ids if i in s]
            expected = max(present, key=len) if present else None
            notices.append({
                "event_id": ev.get("event_id"), "actor": ev.get("actor"),
                "created_at": ev.get("created_at"), "expected_id": expected,
                "summary": s,
                "captured": {n: capture(p, s) for n, p in PATTERNS.items()},
            })

    per_pattern = {}
    for name in PATTERNS:
        bound = [n for n in notices if n["captured"][name] in req_by_id]
        correct = [n for n in notices if n["expected_id"] is not None
                   and n["captured"][name] == n["expected_id"]]
        wrong = [n for n in notices if n["captured"][name] in req_by_id
                 and n["captured"][name] != n["expected_id"]]
        unbound = [n for n in notices if n["captured"][name] not in req_by_id]
        per_pattern[name] = {
            "notices": len(notices),
            "bound_to_a_registered_request": len(bound),
            "correctly_bound": len(correct),
            "wrongly_bound": len(wrong),
            "silently_unbound": len(unbound),
            "unbound_event_ids": [n["event_id"] for n in unbound],
            "wrong_event_ids": [n["event_id"] for n in wrong],
        }

    distinct = sorted({n["expected_id"] for n in notices if n["expected_id"]})
    lost = [n for n in notices if n["captured"]["P0_current"] not in req_by_id]
    latent = [{"event_id": i, "status": req_by_id[i].get("status")}
              for i in req_ids if ":" in i and req_by_id[i].get("status") not in
              {"approved", "superseded", "rejected"}]

    repaired = [r for r in requests if r.get("decision_event_id")]
    return {
        "approval_notices": len(notices),
        "distinct_requested_ids": len(distinct),
        "distinct_requested_id_list": distinct,
        "per_pattern": per_pattern,
        "current_matcher_silently_unbound": [n["event_id"] for n in lost],
        "current_matcher_unbound_expected_ids": [n["expected_id"] for n in lost],
        "latent_colon_id_requests_not_terminal": latent,
        "repair_provenance_entries": [
            {"event_id": r.get("event_id"), "status": r.get("status"),
             "decision_event_id": r.get("decision_event_id"),
             "granted_agent_hours": r.get("granted_agent_hours")} for r in repaired],
        "notices": notices,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("report.json")))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    fx = run_fixtures()
    if args.selftest:
        print(json.dumps({"fixtures": len(fx["fixtures"]), "failures": fx["failures"]}, indent=1))
        print("SELFTEST", "PASS" if fx["ok"] else "FAIL")
        return 0 if fx["ok"] else 2

    data = load_inputs()
    report = {
        "task_id": "W032-APPROVAL-MATCHER-01",
        "worker": "worker-032",
        "generated_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone(__import__("datetime").timedelta(hours=8))
        ).isoformat(timespec="seconds"),
        "question": ("Does the resource-request approval matcher in "
                     "research_map/apply_events.py bind every recorded approval, and which "
                     "one-line replacement binds all of them without wrong bindings?"),
        "input_sha256_at_start": data["before"],
        "shipped_matcher": PATTERNS["P0_current"],
        "recommended_matcher": PATTERNS[RECOMMENDED],
        "recommended_replacement_line": (
            "rid = _re.search(r\"resource_request\\s+(\\S+?):\\s*APPROVED\", summary)"),
        "measurement": measure(data),
        "fixture_selftest": {"fixtures": len(fx["fixtures"]), "failures": fx["failures"], "ok": fx["ok"]},
        "live_finding": (
            "At the pinned event stream the shipped matcher silently fails to bind the "
            "approval notice for the one colon-containing request id "
            "(leadform-resource-request-2026-09-12T00:44:00+08:00); the map entry is approved "
            "only because research_map/astra_repair_03_resources.py set it out of band."),
        "recommended_fix": (
            "Replace the capture at research_map/apply_events.py:267 with the APPROVED-anchored "
            "pattern. It is the only candidate that also rejects a preceding pending mention "
            "(fixture F06) and it needs no other line changed."),
        "scope_limits": [
            "Process/tooling measurement only; no mathematics, physics or numerical claim.",
            "Read-only: no canonical file, map, event stream or ledger was modified.",
            "The fixture suite is synthetic except F01/F02 which mirror live summaries verbatim.",
            "Durability of the existing repair was assessed by source reading, not by re-running "
            "the controller's applier against shared state.",
        ],
    }
    after = {rel: sha256_file(p) for rel, p in INPUTS.items()}
    report["input_sha256_at_end"] = after
    report["window_stable"] = before_stable = data["before"] == after

    out = Path(args.out)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({
        "out": str(out), "window_stable": before_stable,
        "selftest_ok": fx["ok"],
        "approval_notices": report["measurement"]["approval_notices"],
        "P0_silently_unbound": report["measurement"]["per_pattern"]["P0_current"]["silently_unbound"],
        "P3_silently_unbound": report["measurement"]["per_pattern"][RECOMMENDED]["silently_unbound"],
        "latent_colon_ids": len(report["measurement"]["latent_colon_id_requests_not_terminal"]),
    }, indent=1))
    return 0 if fx["ok"] and before_stable else 2


if __name__ == "__main__":
    sys.exit(main())

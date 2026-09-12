#!/usr/bin/env python3
"""W085-APPROVAL-BINDING-02 — read-only verification of the controller's resource-request
approval matcher (`research_map/apply_events.py`), pre-fix and post-fix.

Context (pass-03 lifecycle, `lifecycle_20260912-002440.json`):
    "apply_events.py matches approvals with `resource_request\\s+(\\S+?):`, which cannot
     capture request ids containing colons (all formulation ids do). The formulation
     decision was bound by the lock-held repair instead; the regex should be reviewed
     next pass."

While this probe was being built the controller landed a fix (00:31:11–00:31:19). This
probe therefore measures both revisions:

  pre-fix  `apply_events.py` sha256 6f866c716c4f…: reproduce the truncation on the real
           event stream and identify the one dropped approval.
  post-fix `apply_events.py` sha256 16820bf206b7…: extract the decision block VERBATIM from
           the frozen source bytes and run it against the real stream plus adversarial
           controls, then report which defects are fixed and which remain.

Read-only: writes only under artifacts/worker-085/approval_binding/. No canonical file is
edited. Two frozen snapshots are re-hashed at the end; drift exits 2.

  python3 artifacts/worker-085/approval_binding/probe_approval_binding.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import textwrap
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SNAP_PRE = HERE / "snapshot"
SNAP_POST = HERE / "snapshot_postfix"
OUT = HERE / "report.json"

PRE_FILES = {
    "apply_events.py": "research_map/apply_events.py",
    "astra_repair_03_resources.py": "research_map/astra_repair_03_resources.py",
    "lifecycle_20260912-002440.json": "runtime/state/controller_verification/lifecycle_20260912-002440.json",
    "events.jsonl": "research_map/events.jsonl",
    "research_map.json": "research_map/research_map.json",
    "astra-lifecycle-03.md": "runtime/state/controller_verification/astra-lifecycle-03.md",
}
POST_FILES = {"apply_events.py": "research_map/apply_events.py"}

EXPECTED_PRE = "6f866c716c4f3fc5cfde0da9f2dcda5a0b2b73e864e4726e8702b8c417549d1b"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def extract_decision_block(src: str) -> str:
    """Pull the controller-decision block out of apply_events.py verbatim (dedented)."""
    lines = src.splitlines()
    start = None
    for i, l in enumerate(lines):
        if 'summary = str(ev.get("summary", ""))' in l and i > 0 and "controller decisions ride" in "\n".join(lines[max(0, i - 8):i]):
            start = i
            break
    if start is None:
        raise SystemExit("decision block start not found")
    end = None
    for j in range(start, min(start + 30, len(lines))):
        if 'r["decision_note"] = summary[:400]' in lines[j]:
            end = j
            break
    if end is None:
        raise SystemExit("decision block end not found")
    return textwrap.dedent("\n".join(lines[start:end + 1]))


def make_postfix_matcher(block_src: str):
    """exec the extracted block verbatim inside a function with mocked m/ev/_re/now."""
    ns: dict = {}
    exec("def _fixed(summary, m, ev, _re, now):\n" + textwrap.indent(block_src, "    ") + "\n    return m\n",
         {"__builtins__": __builtins__}, ns)
    raw = ns["_fixed"]

    def _wrapped(summary, requests):
        m = {"resource_requests": requests}
        return raw(summary, m, {"summary": summary}, re, lambda: "TEST-NOW")["resource_requests"]

    return _wrapped


def make_prefix_matcher(pattern_src: str):
    pat = re.compile(pattern_src)

    def _old(summary, requests, _pat=pat):
        if "resource_request" in summary and "APPROVED" in summary:
            m = _pat.search(summary)
            if m:
                for r in requests:
                    if r.get("event_id") == m.group(1):
                        r["status"] = "approved"
                        r["decision_at"] = "T"
                        r["decision_by"] = "astra"
                        return m.group(1)
        return None

    return _old


def main() -> int:
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    report: dict = {
        "task_id": "W085-APPROVAL-BINDING-02",
        "actor": "worker-085",
        "node_id": "F0",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "started_at": started,
        "checks": {},
        "pins": {},
    }

    pre = {n: (SNAP_PRE / n).read_bytes() for n in PRE_FILES}
    post = {n: (SNAP_POST / n).read_bytes() for n in POST_FILES}
    report["pins"]["prefix_snapshot_sha256"] = {n: sha256_bytes(b) for n, b in pre.items()}
    report["pins"]["postfix_snapshot_sha256"] = {n: sha256_bytes(b) for n, b in post.items()}

    drift = []
    if report["pins"]["prefix_snapshot_sha256"]["apply_events.py"] != EXPECTED_PRE:
        drift.append("pre-fix snapshot is not the recorded pre-fix revision")
    live = ROOT / "research_map/apply_events.py"
    if sha256_file(live) != report["pins"]["postfix_snapshot_sha256"]["apply_events.py"]:
        drift.append("live research_map/apply_events.py differs from the post-fix snapshot at run start")
    report["checks"]["C0_frozen_revisions_pinned"] = not drift
    report["pins"]["drift_at_run_start"] = drift
    if drift:
        OUT.write_text(json.dumps(report, indent=2) + "\n")
        print("DRIFT:", *drift, sep="\n  ")
        return 2

    src_pre = pre["apply_events.py"].decode("utf-8")
    src_post = post["apply_events.py"].decode("utf-8")
    events = [json.loads(l) for l in pre["events.jsonl"].decode("utf-8", "replace").splitlines() if l.strip()]

    pat_pre = re.search(r'_re\.search\(r"([^"]+)"', src_pre).group(1)
    old_matcher = make_prefix_matcher(pat_pre)
    block = extract_decision_block(src_post)
    fixed_matcher = make_postfix_matcher(block)
    guard_post = 'if "resource_request" in summary and ("APPROVED" in summary or "DENIED" in summary):' in src_post
    report["extracted"] = {
        "prefix_pattern": pat_pre,
        "postfix_decision_block_verbatim": block,
        "postfix_guard_present": guard_post,
        "postfix_token_pattern": r"resource_request\s+(\S+)",
        "postfix_rstrip_set": ":,;.",
    }
    report["checks"]["C1_postfix_block_extracted_verbatim"] = len(block.splitlines()) == 16

    req_events = [e for e in events if e.get("event_type") == "resource_request"]
    req_ids = [str(e.get("event_id")) for e in req_events]
    approval_events = [
        (i, str(e.get("summary", ""))) for i, e in enumerate(events)
        if "resource_request" in str(e.get("summary", "")) and "APPROVED" in str(e.get("summary", ""))
    ]

    def run_matcher(matcher, summary):
        reqs = [{"event_id": rid} for rid in req_ids]
        matcher(summary, reqs)
        return reqs

    rows = []
    for i, s in approval_events:
        pre_rows = run_matcher(old_matcher, s)
        post_rows = run_matcher(fixed_matcher, s)
        bound_pre = [r["event_id"] for r in pre_rows if r.get("status") == "approved"]
        bound_post = [r["event_id"] for r in post_rows if r.get("status") == "approved"]
        rows.append({
            "event_index": i,
            "created_at": events[i].get("created_at"),
            "summary": s[:200],
            "prefix_bound": bound_pre,
            "prefix_ok": len(bound_pre) == 1,
            "postfix_bound": bound_post,
            "postfix_ok": len(bound_post) == 1,
        })
    n = len(rows)
    n_pre_miss = sum(1 for r in rows if not r["prefix_ok"])
    n_post_miss = sum(1 for r in rows if not r["postfix_ok"])
    report["live_stream"] = {
        "events_scanned": len(events),
        "resource_request_events": len(req_ids),
        "approval_status_events": n,
        "prefix_missed_binds": n_pre_miss,
        "postfix_missed_binds": n_post_miss,
        "rows": rows,
    }
    report["checks"]["C2_prefix_reproduces_dropped_approval"] = (
        n == 7 and n_pre_miss == 1 and rows[4]["prefix_bound"] == []
        and "leadform-resource-request-2026-09-12T00:44:00+08:00" in rows[4]["summary"]
    )
    report["checks"]["C3_postfix_binds_all_live_approvals"] = (n_post_miss == 0 and n > 0)

    # ---- synthetic controls against the verbatim post-fix block ----
    syn_req = ["rr-abc", "rr-abc:def", "e08-rr-20260911T2323-f2a", "superseded-req"]
    cases = [
        ("S1_colon_id", "resource_request rr-abc:def: APPROVED 1h", "approved", "rr-abc:def"),
        ("S2_no_space_colon", "resource_request rr-abc:APPROVED", "approved", "rr-abc"),
        ("S3_trailing_comma", "resource_request rr-abc, APPROVED", "approved", "rr-abc"),
        ("S4_trailing_period", "resource_request rr-abc. APPROVED", "approved", "rr-abc"),
        ("S5_denied", "resource_request rr-abc: DENIED (budget cap)", "denied", "rr-abc"),
        ("S6_not_approved", "resource_request rr-abc: NOT APPROVED (budget cap)", "pending", "rr-abc"),
        ("S7_unapproved", "resource_request rr-abc: UNAPPROVED pending audit", "pending", "rr-abc"),
        ("S8_denied_mentions_approved", "resource_request rr-abc: DENIED; the earlier APPROVED proposal is void",
         "denied", "rr-abc"),
        ("S9_control_non_colon", "resource_request e08-rr-20260911T2323-f2a: APPROVED with scope control",
         "approved", "e08-rr-20260911T2323-f2a"),
    ]
    syn = []
    for sid, s, expect_status, expect_rid in cases:
        reqs = [{"event_id": rid} for rid in syn_req]
        fixed_matcher(s, reqs)
        got = {r["event_id"]: r.get("status", "pending") for r in reqs}
        syn.append({
            "id": sid, "summary": s, "expected_status": expect_status, "expected_id": expect_rid,
            "got": got,
            "correct": got.get(expect_rid) == expect_status
                       and all(v == "pending" for k, v in got.items() if k != expect_rid),
        })
    by_id = {r["id"]: r for r in syn}
    report["synthetic_controls_verbatim_postfix_block"] = syn
    report["checks"]["C4_postfix_binds_colon_and_separator_forms"] = all(
        by_id[k]["correct"] for k in ("S1_colon_id", "S3_trailing_comma", "S4_trailing_period", "S9_control_non_colon")
    )
    report["checks"]["C5_postfix_DENIED_branch_works"] = by_id["S5_denied"]["correct"]
    report["checks"]["C6_substring_decision_defect_remains"] = (
        not by_id["S6_not_approved"]["correct"] and not by_id["S7_unapproved"]["correct"]
        and not by_id["S8_denied_mentions_approved"]["correct"]
    )
    report["checks"]["C7_no_space_colon_regression"] = (not by_id["S2_no_space_colon"]["correct"])

    # ---- superseded-request handling ----
    reqs = [{"event_id": "superseded-req", "status": "superseded"}]
    fixed_matcher("resource_request superseded-req: APPROVED 1h", reqs)
    report["checks"]["C8_superseded_request_not_flipped"] = (
        reqs[0]["status"] == "superseded" and "ignored decision for superseded request" in reqs[0].get("decision_note", "")
    )

    # ---- ordering residual: approval before request is ingested ----
    def fix_on_late_request(summary):
        reqs: list = []
        fixed_matcher(summary, reqs)
        return reqs

    report["checks"]["C9_ordering_residual_remains"] = (fix_on_late_request("resource_request rr-abc: APPROVED") == [])
    report["residual_risks"] = [
        "decision vocabulary is still substring-based: 'NOT APPROVED', 'UNAPPROVED' and "
        "'DENIED; the earlier APPROVED proposal...' all yield status=approved "
        "(measured, controls S6/S7/S8).",
        "no-space delimiter form 'resource_request <id>:APPROVED' no longer binds (measured S2); "
        "the pre-fix lazy pattern did bind it. All live summaries use ': ', so no live instance.",
        "an approval event applied before its resource_request event is silently dropped "
        "(measured C9); both revisions share this, no live instance at the frozen snapshot.",
        "decision words other than APPROVED/DENIED (REJECTED, DECLINED, DEFERRED) do not bind at all.",
    ]

    # ---- live consequence of the pre-fix defect, and the manual repair ----
    lc_md = pre["astra-lifecycle-03.md"].decode("utf-8")
    map_obj = json.loads(pre["research_map.json"].decode("utf-8"))
    target = "leadform-resource-request-2026-09-12T00:44:00+08:00"
    rr = next((r for r in map_obj.get("resource_requests", []) if r.get("event_id") == target), None)
    repair_src = pre["astra_repair_03_resources.py"].decode("utf-8")
    report["checks"]["C10_gap_recorded_in_lifecycle"] = "cannot capture request ids containing colons" in lc_md
    report["checks"]["C11_missed_request_manually_approved"] = bool(rr and rr.get("status") == "approved")
    report["checks"]["C12_repair_file_names_same_root_cause"] = ("contains colons" in repair_src and target in repair_src)
    report["live_consequence"] = {
        "missed_request_id": target,
        "map_status_at_prefix_snapshot": (rr or {}).get("status"),
        "mitigation": "astra_repair_03_resources.py (pass-03 lock-held repair) approved it manually; "
                      "the post-fix matcher now binds it from the stream (C3).",
    }

    # ---- immutability of both snapshots ----
    pre_after = {n: sha256_file(SNAP_PRE / n) for n in PRE_FILES}
    post_after = {n: sha256_file(SNAP_POST / n) for n in POST_FILES}
    report["checks"]["C13_snapshots_immutable"] = (
        pre_after == report["pins"]["prefix_snapshot_sha256"]
        and post_after == report["pins"]["postfix_snapshot_sha256"]
    )
    report["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")

    must_pass = [k for k in report["checks"] if k != "C6_substring_decision_defect_remains"
                 and k != "C7_no_space_colon_regression" and k != "C9_ordering_residual_remains"]
    failed = [k for k in must_pass if not report["checks"][k]]
    report["verdict"] = "PREFIX_DEFECT_REPRODUCED_POSTFIX_FIX_VERIFIED_RESIDUALS_FOUND" if not failed else "PROBE_INCOMPLETE"
    report["failed_checks"] = failed
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"verdict: {report['verdict']}")
    print(f"live approvals={n} pre_miss={n_pre_miss} post_miss={n_post_miss} failed={failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

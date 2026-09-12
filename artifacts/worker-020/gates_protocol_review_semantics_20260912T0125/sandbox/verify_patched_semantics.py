#!/usr/bin/env python3
"""Validate the unapplied patch candidate against the audit's R3 semantics.

Runs the patched ``_protocol_review`` (sandbox/gates_patched.py) on:
  (a) the pinned live event set, and
  (b) the 16 synthetic truth-table cases from the audit instrument,
and compares it with the independently computed R3 outcome (document scope +
per-reviewer supersession).  Writes out/patch_semantics_check.json.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TASK / "sandbox"))

import audit_protocol_review_semantics as audit  # noqa: E402


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    manifest = json.loads((TASK / "pinned" / "manifest.json").read_text())
    pinned = audit.load_pinned(TASK, manifest)
    events = audit.build_event_list(pinned["__tree__"])
    proto = manifest["files"]["numerics/CONVERGENCE_PROTOCOL.md"]["sha256"]

    patched = load_module(TASK / "sandbox" / "gates_patched.py", "w020_gates_patched")

    live_r3 = audit.run_rule(events, proto, "document", True, "reviewer")
    got = patched._protocol_review(events, proto)
    live_ok = (
        got["reviewed"] == live_r3["reviewed"]
        and got["contest"] == live_r3["contest"]
        and sorted(got["accepting_reviews"]) == sorted(live_r3["accepting_reviews"])
        and sorted(d["event_id"] for d in got["dissenting_reviews"])
        == sorted(d["event_id"] for d in live_r3["dissenting_reviews"])
    )

    cases = audit.truth_table(proto)
    case_checks = []
    for c in cases:
        r3 = audit.classify(audit.run_rule(c["events"], proto, "document", True, "reviewer"))
        out = patched._protocol_review(c["events"], proto)
        got_state = "contest" if out["contest"] else ("clear" if out["reviewed"] else "unreviewed")
        case_checks.append({"id": c["id"], "r3_expected": r3, "patched": got_state,
                            "match": got_state == r3})

    result = {
        "task_id": "W020-GNUM-PROTOCOL-REVIEW-SEMANTICS-01",
        "live": {
            "patched_reviewed": got["reviewed"],
            "patched_contest": got["contest"],
            "patched_accepts": got["accepting_reviews"],
            "patched_dissents": [d["event_id"] for d in got["dissenting_reviews"]],
            "patched_superseded": [d["event_id"] for d in got.get("superseded_reviews", [])],
            "patched_node_scope": [d["event_id"] for d in got.get("node_scope_reviews", [])],
            "matches_independent_r3": live_ok,
        },
        "truth_table": case_checks,
        "truth_table_matches": sum(1 for c in case_checks if c["match"]),
        "truth_table_total": len(case_checks),
        "note": "patch candidate only; numerics/gates.py untouched and unapplied",
    }
    out = TASK / "out" / "patch_semantics_check.json"
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("live", "truth_table_matches", "truth_table_total")},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

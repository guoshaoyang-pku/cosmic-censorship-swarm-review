#!/usr/bin/env python3
"""W056-REJECT-REPAIR-01 — pre-flight event validator (reusable gate).

Why this exists
---------------
`research_map/comms.py::ingest` rejects an event, records it in
`comms/rejected.jsonl`, and then does `seen.add(eid)` (line 313). Because the id is
added to `runtime/state/ingested_ids.json` on *reject*, a rejected event can never be
re-ingested under the same id: rejection is terminal. The worker that emitted it sees
no error (ingest runs from the controller cycle) and the content is silently lost.

This tool lets any worker run the *same* normalisation + validation the ingester will
run, before writing to `comms/outbox/`, so vocabulary/shape defects are caught while
they are still cheap.

It deliberately calls the real functions — `comms.normalize_event` and
`schemas.validate_event` — rather than re-implementing them, so it cannot drift from
the ingester.

Usage
-----
    python3 preflight_event.py <file.jsonl|file.json|file.md> [...]
    python3 preflight_event.py --self-test

Exit codes
----------
    0  all extracted events would be accepted
    1  at least one event would be rejected
    2  usage / no events found
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# artifacts/worker-056/reject_repair/preflight_event.py -> swarm root is parents[3]
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research_map"))

from comms import normalize_event, _json_objects  # noqa: E402
from schemas import validate_event, SchemaError  # noqa: E402

# Types that assert a stronger result than a bare measurement. A repair must never
# promote an event into one of these; that would be conclusion inflation.
STRONG_CONCLUSION_TYPES = {
    "theorem",
    "conditional_theorem",
    "stability_result",
    "counterexample",
    "formal_model",
}
REPAIRABLE_TARGETS = {"numerical_evidence", "open_problem"}


def preflight(doc: dict, source: str = "preflight") -> tuple[bool, str]:
    """Return (would_be_accepted, reason). Mirrors ingest exactly at one event."""
    if not isinstance(doc, dict):
        return False, "event: not a JSON object"
    d = json.loads(json.dumps(doc))  # deep copy; normalize_event mutates
    d.setdefault("event_id", "preflight-placeholder")
    d.setdefault("created_at", "1970-01-01T00:00:00+00:00")
    d.setdefault("actor", "preflight")
    d["_received_at"] = "1970-01-01T00:00:00+00:00"
    try:
        d = normalize_event(d, source)
        validate_event(d)
    except SchemaError as e:
        return False, str(e)
    except Exception as e:  # normalizer crash also means "will not be ingested"
        return False, f"normalizer: {type(e).__name__}: {e}"
    return True, "ok"


def preflight_file(path: Path) -> list[dict]:
    text = path.read_text(errors="replace")
    out = []
    for doc in _json_objects(text):
        ok, reason = preflight(doc, str(path))
        out.append({"event_id": doc.get("event_id"), "event_type": doc.get("event_type"),
                    "would_be_accepted": ok, "reason": reason})
    return out


def _self_test() -> int:
    """Controls that must hold for this tool to be trustworthy."""
    failures = []

    # N1: an explicit out-of-vocabulary conclusion_type is flagged (the live defect).
    ok, reason = preflight({"event_id": "st1", "event_type": "claim", "actor": "x",
                            "created_at": "x", "class_id": "AF-WCC-VAC-GEN",
                            "statement": "s", "conclusion_type": "empirical",
                            "assumptions": [], "falsifier": "f", "evidence_refs": []})
    if ok or reason != "claim: invalid conclusion_type":
        failures.append(f"N1 expected enum reject, got ok={ok} reason={reason!r}")

    # N2: a missing conclusion_type is *defaulted*, not rejected (documents permissiveness).
    ok2, reason2 = preflight({"event_id": "st2", "event_type": "claim", "actor": "x",
                              "created_at": "x", "class_id": "AF-WCC-VAC-GEN",
                              "statement": "s", "assumptions": [], "falsifier": "f",
                              "evidence_refs": []})
    if not ok2:
        failures.append(f"N2 expected default-accept, got {reason2!r}")

    # N3: theorem without artifact_refs is rejected (no fluent-text promotion).
    ok3, reason3 = preflight({"event_id": "st3", "event_type": "claim", "actor": "x",
                              "created_at": "x", "class_id": "AF-WCC-VAC-GEN",
                              "statement": "s", "conclusion_type": "theorem",
                              "assumptions": [], "falsifier": "f", "evidence_refs": []})
    if ok3 or "artifact_refs" not in reason3:
        failures.append(f"N3 expected theorem-guard reject, got ok={ok3} reason={reason3!r}")

    # N4: unknown event_type is flagged.
    ok4, reason4 = preflight({"event_id": "st4", "event_type": "task", "actor": "x",
                              "created_at": "x"})
    if ok4:
        failures.append("N4 expected unknown-event_type reject")

    # P1: the repair-target invariant — repairs may not promote into a strong type.
    if REPAIRABLE_TARGETS & STRONG_CONCLUSION_TYPES:
        failures.append("P1 repair targets intersect strong conclusion types")

    for f in failures:
        print(f"  FAIL {f}")
    print(f"self-test: {'PASS' if not failures else 'FAIL'} ({4 - len(failures)}/4 controls)")
    return 0 if not failures else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true", help="emit machine-readable results")
    a = ap.parse_args()

    if a.self_test:
        return _self_test()
    if not a.paths:
        ap.print_help()
        return 2

    results, bad = [], 0
    for p in a.paths:
        path = Path(p)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            print(f"  MISSING {p}")
            bad += 1
            continue
        for r in preflight_file(path):
            results.append({"source": str(path), **r})
            if not r["would_be_accepted"]:
                bad += 1

    if a.json:
        print(json.dumps({"checked": len(results), "would_reject": bad, "results": results}, indent=1))
    else:
        for r in results:
            mark = "ok  " if r["would_be_accepted"] else "REJECT"
            print(f"  {mark} {r['event_type'] or '-':<12} {r['event_id'] or '-':<48} {r['reason']}")
        print(f"checked={len(results)} would_reject={bad}")
    if not results:
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

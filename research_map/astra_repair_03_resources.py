"""Pass-03 bounded controller repair: record resource-request decisions in the map.

Why this exists: apply_events.py matches approvals with
`resource_request\\s+(\\S+?):` on a status-event summary. The formulation request id
`leadform-resource-request-2026-09-12T00:44:00+08:00` contains colons, so the
non-greedy capture stops at `...T00` and the decision never binds. The two other
pass-03 approvals (ids without colons) bound through the normal event path and are
not touched here.

Scope: only `resource_requests` entries. Lock-held, atomic replace, then
validate_map + checkpoint. No node, gate, claim or artifact content is modified.

  python3 research_map/astra_repair_03_resources.py
"""
from __future__ import annotations

import fcntl
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import checkpoint  # noqa: E402
from validate_map import validate_map  # noqa: E402

MAP = ROOT / "research_map" / "research_map.json"
LOCK = ROOT / "runtime" / "state" / "map.lock"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")

APPROVED = {
    "leadform-resource-request-2026-09-12T00:44:00+08:00": {
        "decision_event_id": "astra-life03-approve-formulation-verification",
        "decision_note": ("APPROVED 6.0 agent-hours for the verification round at the final rev25 "
                          "hashes: astra-life03-close-findings, astra-life03-verify-gform, "
                          "astra-life03-verify-gf0 and re-pin overhead. Bound by the direction "
                          "update astra-life03-direction-formulation."),
        "granted_agent_hours": 6.0,
    },
}
SUPERSEDED = {
    "leadform-resource-request-2026-09-12T00:16:00+08:00":
        "superseded by the requester's own final hash set (00:44 request); no allocation",
    "leadform-resource-request-2026-09-12T00:34:00+08:00":
        "superseded by the requester's own final hash set (00:44 request); no allocation",
    "lnum-resource_request-08289c80b2e0d52d7adf":
        "superseded by lnum-resource-request-c8-rev3-20260912T002107 (stale protocol pin); no allocation",
    "lnum-resource-request-89be785d412886d5fff6":
        "superseded by lnum-resource-request-c8-rev3-20260912T002107 (stale protocol pin); no allocation",
}


def main():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            m = json.loads(MAP.read_text())
            changed = []
            for r in m.get("resource_requests", []):
                eid = r.get("event_id")
                if eid in APPROVED and r.get("status") != "approved":
                    r.update(APPROVED[eid], status="approved", decision_at=NOW, decision_by="astra")
                    changed.append(eid)
                elif eid in SUPERSEDED and r.get("status") == "pending":
                    r.update(status="superseded", decision_at=NOW, decision_by="astra",
                             decision_note=SUPERSEDED[eid])
                    changed.append(eid)
            if changed:
                m["updated_at"] = NOW
                errs = validate_map(m)
                if errs:
                    print("REFUSING WRITE; validator errors:", errs)
                    return 1
                tmp = MAP.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(m, indent=2) + "\n")
                tmp.replace(MAP)
                print("REPAIRED", json.dumps(changed))
            else:
                print("NO CHANGE")
            rec = checkpoint.main("astra-lifecycle-03-resource-repair")
            print("CHECKPOINT", rec.get("checkpoint_id"))
            return 0
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


if __name__ == "__main__":
    raise SystemExit(main())

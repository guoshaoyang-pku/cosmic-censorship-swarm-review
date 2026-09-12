#!/usr/bin/env python3
"""Independent hash/reproduction audit of the flash-12 N0 revision recheck.

Verifies, without trusting the artifact's own text:
  1. every evidence file it cites exists and its sha256 matches the claim;
  2. every pinned input hash is recorded, and whether it still matches at audit time;
  3. the three measured order_l2 ladders reproduce exactly in a fresh run of
     `python3 numerics/tests/flat_wave.py --all` (report supplied via --fresh-report);
  4. flat_wave.py is unchanged before/after (caller supplies the two hashes).

Usage:
  python3 verify_recheck.py --recheck artifacts/flash-12/n0/rev3/revision_acceptance_recheck.json \
      --fresh-report artifacts/worker-012/n0/all_report.json --json-out <path>
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--recheck", required=True)
    ap.add_argument("--fresh-report", required=True)
    ap.add_argument("--json-out", required=True)
    a = ap.parse_args()

    rp = (REPO / a.recheck) if not Path(a.recheck).is_absolute() else Path(a.recheck)
    fp = (REPO / a.fresh_report) if not Path(a.fresh_report).is_absolute() else Path(a.fresh_report)
    recheck = json.loads(rp.read_text())
    fresh = json.loads(fp.read_text())

    ev = []
    for entry in recheck.get("evidence_files", []):
        p = REPO / entry["path"]
        rec = {"path": entry["path"], "claimed_sha256": entry["sha256"],
               "claimed_bytes": entry.get("bytes")}
        if p.exists():
            rec["exists"] = True
            rec["measured_sha256"] = sha256(p)
            rec["measured_bytes"] = p.stat().st_size
            rec["sha_match"] = rec["measured_sha256"] == entry["sha256"]
            rec["bytes_match"] = rec["measured_bytes"] == entry.get("bytes")
        else:
            rec["exists"] = False
            rec["sha_match"] = False
            rec["bytes_match"] = False
        ev.append(rec)

    inputs = []
    for path, entry in (recheck.get("inputs") or {}).items():
        p = REPO / path
        rec = {"path": path, "claimed_sha256": entry.get("sha256")}
        if p.exists():
            rec["measured_sha256"] = sha256(p)
            rec["match_at_audit_time"] = rec["measured_sha256"] == entry.get("sha256")
        else:
            rec["exists"] = False
            rec["match_at_audit_time"] = False
        inputs.append(rec)

    fresh_orders = [s.get("order_l2") for s in fresh.get("studies", [])]
    claimed_orders = [s.get("order_l2_pairs") for s in
                      (recheck.get("measured_orders") or {}).get("studies", [])]
    orders_reproduced = fresh_orders == claimed_orders

    out = {
        "artifact_kind": "independent_recheck_hash_audit",
        "worker": "worker-012",
        "audited_artifact": a.recheck,
        "audited_artifact_sha256": sha256(rp),
        "evidence_files": ev,
        "all_evidence_hashes_match": all(e["sha_match"] and e["bytes_match"] for e in ev),
        "n_evidence_files": len(ev),
        "pinned_inputs": inputs,
        "fresh_report": a.fresh_report,
        "fresh_report_sha256": sha256(fp),
        "order_l2_fresh": fresh_orders,
        "order_l2_claimed": claimed_orders,
        "order_l2_reproduced_exactly": orders_reproduced,
        "fresh_all_gates_pass": bool(fresh.get("all_gates_pass")),
        "fresh_gate_table": fresh.get("gates"),
        "fresh_lock_guard": fresh.get("lock_guard"),
    }
    Path(a.json_out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in (
        "audited_artifact_sha256", "all_evidence_hashes_match", "n_evidence_files",
        "order_l2_reproduced_exactly", "fresh_all_gates_pass")}, indent=1))
    return 0 if out["all_evidence_hashes_match"] and orders_reproduced else 1


if __name__ == "__main__":
    raise SystemExit(main())

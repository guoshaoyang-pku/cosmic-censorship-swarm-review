#!/usr/bin/env python3
"""Numerics-group checkpoint writer / 4-hour daemon.

The controller checkpoints the whole swarm every 15 min (``research_map/checkpoint.py``).
This is the numerics-local record: artifact hashes, N0 order measurements, gate and lock
state, and the next falsifier — so the group's own progress is auditable even if the
controller's snapshot misses it.

Outputs (append-only):
    artifacts/numerics/checkpoints/ckpt-<stamp>.json     full record
    artifacts/numerics/CHECKPOINTS.jsonl                 one summary line per checkpoint
    artifacts/numerics/CHECKPOINTS.md                    human-readable log

Usage:
    python3 numerics/checkpoint.py --once
    python3 numerics/checkpoint.py --daemon --interval 900   # until the run deadline
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CST = timezone(timedelta(hours=8))

TRACKED = (
    "numerics/tests/flat_wave.py",
    "numerics/tests/flat_wave_replication.py",
    "numerics/tests/lead_calibration.py",
    "numerics/tests/selfgravity_lock_guard.py",
    "numerics/tests/n0_gate_proposal.json",
    "numerics/tests/n0_order_4rung.json",
    "numerics/tests/n0_order_4rung_addendum.py",
    "numerics/protocol/n0_gate_proposal_leadverify.json",
    "numerics/protocol/three_scheme_r1r5_summary.json",
    "numerics/protocol/report_lffd_4rung.json",
    "numerics/protocol/report_cnfd_4rung.json",
    "numerics/protocol/report_cnfem_4rung.json",
    "numerics/CONVERGENCE_PROTOCOL.md",
    "numerics/blockers.md",
    "numerics/gates.py",
    "numerics/results/flat_wave_convergence.json",
    "numerics/results/flat_wave_replication.json",
    "artifacts/numerics/n0/lead_calibration_report.json",
    "artifacts/numerics/n0/lead_4rung_replication.json",
)
ORDER_REPORTS = {
    "implementation": "numerics/results/flat_wave_convergence.json",
    "replication": "numerics/results/flat_wave_replication.json",
    "lead_reference": "artifacts/numerics/n0/lead_calibration_report.json",
}


def sha256(p: Path) -> str | None:
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def order_summary() -> dict:
    """Primary (order-2) measured orders per implementation, via the gate extractor."""
    try:
        from numerics import gates

        raw = gates.primary_order_summary(ROOT)
        return {
            "implementation": raw.get("numerics/results/flat_wave_convergence.json", {}),
            "replication": raw.get("numerics/results/flat_wave_replication.json", {}),
            "lead_reference": raw.get("artifacts/numerics/n0/lead_calibration_report.json", {}),
        }
    except Exception as e:  # pragma: no cover - visible failure
        return {"error": f"order summary failed: {e}"}


def load_gate_state() -> dict:
    try:
        from numerics import gates
    except Exception as e:  # pragma: no cover - import failure must be visible
        return {"error": f"gates import failed: {e}"}
    rep = gates.evaluate(ROOT)
    return {
        "verdict": rep["verdict"],
        "lock_state": rep["lock"]["state"],
        "gate_ok": rep["gate_ok"],
        "blocking_reasons": rep["blocking_reasons"],
        "order_agreement": rep["order_agreement"],
        "protocol_reviewed": rep["protocol_review"]["reviewed"],
    }


def run_start() -> datetime | None:
    p = ROOT / "runtime" / "state" / "started_at"
    if not p.is_file():
        return None
    try:
        return datetime.fromisoformat(p.read_text().strip())
    except ValueError:
        return None


def make_record(index: int, previous_hashes: dict | None) -> dict:
    now = datetime.now(CST)
    start = run_start()
    elapsed_min = None if start is None else round((now - start).total_seconds() / 60.0, 1)
    hashes = {rel: sha256(ROOT / rel) for rel in TRACKED}
    changed = []
    if previous_hashes:
        for rel, h in hashes.items():
            if previous_hashes.get(rel) != h:
                changed.append(rel)
    gate = load_gate_state()
    reasons = gate.get("blocking_reasons") or []
    if gate.get("verdict") == "N1_BLOCKED" and reasons:
        next_action = "hold N1; close the listed blocking_reasons: " + "; ".join(reasons)
    elif gate.get("error"):
        next_action = "gate evaluator error: " + str(gate["error"])
    else:
        next_action = "gate evaluator reports no blocking reason; confirm release with astra before any N1 work"
    return {
        "checkpoint_index": index,
        "checkpoint_id": f"num-ckpt-{now.strftime('%Y%m%d-%H%M%S')}",
        "created_at": now.isoformat(timespec="seconds"),
        "run_started_at": None if start is None else start.isoformat(timespec="seconds"),
        "elapsed_minutes": elapsed_min,
        "deadline": "2026-09-12T03:15:11+08:00",
        "agent_hours_this_lead": None if elapsed_min is None else round(elapsed_min / 60.0, 3),
        "artifact_hashes": hashes,
        "changed_since_last_checkpoint": changed,
        "pipeline": order_summary(),
        "gate_state": gate,
        "next_action": next_action,
        "blocks": reasons or ["none recorded by numerics.gates"],
    }


def write_record(rec: dict, previous_hashes: dict | None) -> None:
    ckdir = ROOT / "artifacts" / "numerics" / "checkpoints"
    ckdir.mkdir(parents=True, exist_ok=True)
    (ckdir / f"{rec['checkpoint_id']}.json").write_text(json.dumps(rec, indent=2, sort_keys=True))
    with (ROOT / "artifacts" / "numerics" / "CHECKPOINTS.jsonl").open("a") as f:
        f.write(json.dumps({k: rec[k] for k in (
            "checkpoint_index", "checkpoint_id", "created_at", "elapsed_minutes",
            "changed_since_last_checkpoint", "pipeline", "gate_state", "artifact_hashes")}, sort_keys=True) + "\n")
    lines = [
        f"## {rec['checkpoint_id']} — {rec['created_at']} (elapsed {rec['elapsed_minutes']} min)",
        "",
        f"- gate verdict: **{rec['gate_state'].get('verdict')}**, lock: `{rec['gate_state'].get('lock_state')}`",
        f"- implementation order: {rec['pipeline'].get('implementation', {}).get('mean_order')} "
        f"| replication order: {rec['pipeline'].get('replication', {}).get('mean_order')} "
        f"| lead reference: {rec['pipeline'].get('lead_reference', {}).get('mean_order')}",
        f"- changed since last: {', '.join(rec['changed_since_last_checkpoint']) or 'nothing'}",
        f"- blocks: {'; '.join(rec['blocks'])}",
        "",
    ]
    path = ROOT / "artifacts" / "numerics" / "CHECKPOINTS.md"
    if not path.exists():
        path.write_text("# Numerics checkpoints (15 min cadence, 4 h run)\n\n")
    with path.open("a") as f:
        f.write("\n".join(lines) + "\n")
    # optional heartbeat event every fourth checkpoint
    if rec["checkpoint_index"] % 4 == 1:
        try:
            from numerics.events import emit_status

            emit_status(
                node_id="N0",
                status="active",
                hours=rec["agent_hours_this_lead"] or 0.0,
                summary=(
                    f"numerics checkpoint {rec['checkpoint_index']}: "
                    f"impl order {rec['pipeline'].get('implementation', {}).get('mean_order')}, "
                    f"repl order {rec['pipeline'].get('replication', {}).get('mean_order')}, "
                    f"{rec['gate_state'].get('verdict')}"
                ),
                evidence_refs=["artifacts/numerics/CHECKPOINTS.jsonl", "numerics/CONVERGENCE_PROTOCOL.md"],
                next_falsifier="N0 order disagrees between implementation and replication beyond 0.35, or --lock-guard exits 0 while locked.",
            )
        except Exception:
            pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--interval", type=int, default=900, help="seconds between checkpoints")
    ap.add_argument("--max-minutes", type=float, default=245.0, help="daemon lifetime cap")
    a = ap.parse_args(argv)
    previous = None
    index = 0
    # continue numbering from an existing log
    log = ROOT / "artifacts" / "numerics" / "CHECKPOINTS.jsonl"
    if log.is_file():
        for line in log.read_text().splitlines():
            try:
                index = max(index, int(json.loads(line)["checkpoint_index"]))
            except (ValueError, KeyError):
                pass
        try:
            last = json.loads(log.read_text().splitlines()[-1])
            previous = last.get("artifact_hashes")
        except (ValueError, IndexError):
            previous = None
    started = time.time()
    while True:
        index += 1
        rec = make_record(index, previous)
        write_record(rec, previous)
        previous = rec["artifact_hashes"]
        print(json.dumps({"checkpoint": rec["checkpoint_id"], "verdict": rec["gate_state"].get("verdict"),
                          "changed": rec["changed_since_last_checkpoint"]}))
        if not a.daemon:
            return 0
        if (time.time() - started) / 60.0 >= a.max_minutes:
            print("daemon lifetime reached; exiting")
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    raise SystemExit(main())

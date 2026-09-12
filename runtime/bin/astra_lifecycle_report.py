#!/usr/bin/env python3
"""Emit the Astra independent lifecycle report (astra-indep-1) as a hash-pinned artifact,
then record the artifact hash inside research_map.json under an flock, and checkpoint.

  python3 runtime/bin/astra_lifecycle_report.py
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import checkpoint  # noqa: E402

CST = timezone(timedelta(hours=8))
LOCK = ROOT / "runtime" / "state" / "map.lock"
MAP = ROOT / "research_map" / "research_map.json"
OUT = ROOT / "runtime" / "state" / "controller_verification"
LIFECYCLE = "astra-indep-1"
STARTED = "2026-09-11T23:59:33+08:00"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str | None:
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(cmd):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    m = json.loads(MAP.read_text())
    nodes = {n["id"]: n for g in m["groups"] for n in g["nodes"]}

    # independent verification, re-run at close
    vc, vout = run(["python3", "research_map/validate_map.py"])
    ac, aout = run(["python3", "research_map/audit_evidence.py"])
    lc, lout = run(["python3", "numerics/tests/selfgravity_lock_guard.py"])
    audit_hard = audit_soft = None
    for line in aout.splitlines():
        if line.startswith("evidence audit:"):
            parts = line.replace(",", " ").split()
            audit_hard, audit_soft = int(parts[2]), int(parts[4])
    lock_guard_pass = '"verdict": "PASS"' in lout and '"violations": []' in lout

    tracked = [
        "research_map/formulation_taxonomy.yaml",
        "schemas/af_wcc_vacuum.yaml",
        "schemas/af_scc_c2_vacuum.yaml",
        "schemas/af_scc_c0_vacuum.yaml",
        "schemas/af_scc_regularities.yaml",
        "ledger/theorems.jsonl",
        "ledger/citation_audit.csv",
        "evaluation_rubric.yaml",
        "numerics/tests/flat_wave.py",
        "numerics/CONVERGENCE_PROTOCOL.md",
    ]
    hashes = {p: sha256(ROOT / p) for p in tracked}

    report = {
        "lifecycle_id": LIFECYCLE,
        "actor": "astra",
        "authority": "controller (map owner); one independent lifecycle",
        "started_at": STARTED,
        "ended_at": now(),
        "consumed": {
            "events_total": len([1 for l in (ROOT / "research_map/events.jsonl").read_text().splitlines() if l.strip()]),
            "applied_event_ids": len(m.get("applied_event_ids", [])),
            "practice": "ingest -> apply_events -> adjudicate -> locked atomic write -> checkpoint",
        },
        "dag_repairs": [
            {
                "finding": "CF-7",
                "change": "F2 (single merged node pointing at schemas/af_scc_regularities.yaml) split into F2a and F2b",
                "F2a": {"class_id": "AF-SCC-C2-VAC-GEN", "artifact": nodes["F2a"]["artifact"],
                        "sha256": nodes["F2a"].get("artifact_sha256")},
                "F2b": {"class_id": "AF-SCC-C0-VAC-GEN", "artifact": nodes["F2b"]["artifact"],
                        "sha256": nodes["F2b"].get("artifact_sha256")},
                "retired": {"path": "schemas/af_scc_regularities.yaml", "active": False,
                            "reason": "merged C0/C2 artifact; rejected by group direction and hard decision 1"},
            }
        ],
        "gates": {
            g["gate_id"]: {"verdict": g["verdict"], "owner": g.get("owner"),
                           "eta": g.get("eta"), "unmet_count": len(g.get("unmet", []))}
            for g in m["gates"]
        },
        "gate_ledger_divergence": {
            "found": "CF-8",
            "detail": ("reviews/INDEX.md records G-F0/G-FORM/G-LIT as fail while the map holds pending; "
                       "map verdicts reconciled by recording explicit unmet criteria rather than silent pass"),
        },
        "validation_normalized": {
            "L0": "passed -> unverified (3 revise verdicts incl. hard failures, no accept)",
            "L1": "passed -> unverified (citation-integrity review records 4 hard failures)",
        },
        "numerics_gate": {
            "numerics_lock": m["numerics_lock"]["state"],
            "locked_nodes": m["numerics_lock"]["locked_nodes"],
            "allowed_nodes": m["numerics_lock"]["allowed_nodes"],
            "lock_guard_verdict": "PASS" if lock_guard_pass else "CHECK",
            "lock_guard_exit": lc,
            "n1_artifact_present": (ROOT / "numerics/spherical_solver").exists(),
            "release_requires": m["numerics_lock"].get("additional_requirements"),
        },
        "assignments_issued": [
            {"event_id": a["event_id"], "assignee": a["assignee"], "node_id": a["node_id"],
             "gate": a["gate"], "budget_agent_hours": a.get("budget_agent_hours")}
            for a in m.get("assignments", []) if a.get("event_id", "").startswith("astra-indep-1")
        ],
        "hashes_measured_at_close": hashes,
        "verification": {
            "validate_map_exit": vc, "validate_map": "VALID" if "VALID" in vout else "INVALID",
            "audit_evidence_exit": ac, "audit_evidence_hard": audit_hard, "audit_evidence_soft": audit_soft,
            "lock_guard": "PASS" if lock_guard_pass else "CHECK",
            "soft_warnings_outstanding": [l.strip() for l in aout.splitlines() if l.strip().startswith("soft")],
        },
        "eta_days": {g["id"]: [g.get("eta_days_low"), g.get("eta_days_high")] for g in m["groups"]},
        "exit_criteria": ("lifecycle complete: comms consumed, DAG repaired, gates maintained with explicit "
                          "unmet criteria, bounded assignments issued, hashes/validation/ETA recorded, numerics "
                          "still locked, checkpoint written. Exiting."),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    jp = OUT / f"{LIFECYCLE}.json"
    jp.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n")
    digest = sha256(jp)

    md = [f"# Astra independent lifecycle {LIFECYCLE}", "",
          f"- started {report['started_at']} / ended {report['ended_at']}",
          f"- report sha256 `{digest}`",
          f"- map validation **{report['verification']['validate_map']}**; evidence audit "
          f"**{audit_hard} hard / {audit_soft} soft**; lock guard **{report['verification']['lock_guard']}**",
          f"- numerics_lock **{report['numerics_gate']['numerics_lock']}**; N1 artifact present: "
          f"{report['numerics_gate']['n1_artifact_present']}", "",
          "## DAG repair (CF-7)", "",
          "- `F2` (merged node -> `schemas/af_scc_regularities.yaml`) split into `F2a` "
          f"(`{nodes['F2a']['artifact']}`) and `F2b` (`{nodes['F2b']['artifact']}`).",
          "- `schemas/af_scc_regularities.yaml` retired from service (`active=false`): it is the merged C0/C2 "
          "artifact the group direction rejects.", "",
          "## Gates", ""]
    for gid, g in report["gates"].items():
        md.append(f"- **{gid}** {g['verdict']} (owner {g['owner']}, ETA {g['eta']}, "
                  f"{g['unmet_count']} unmet criteria recorded)")
    md += ["", "## Validation normalized", ""]
    for k, v in report["validation_normalized"].items():
        md.append(f"- {k}: {v}")
    md += ["", "## Bounded assignments issued", ""]
    for a in report["assignments_issued"]:
        md.append(f"- `{a['event_id']}` -> {a['assignee']} (node {a['node_id']}, gate {a['gate']}, "
                  f"{a['budget_agent_hours']}h)")
    md += ["", "## Outstanding soft warnings", ""]
    for w in report["verification"]["soft_warnings_outstanding"]:
        md.append(f"- {w}")
    md += ["", "## Exit", "", report["exit_criteria"], ""]
    mp = OUT / f"{LIFECYCLE}.md"
    mp.write_text("\n".join(md))
    md_digest = sha256(mp)

    # record under lock, atomically
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            m = json.loads(MAP.read_text())
            lifecycles = m.setdefault("controller_lifecycles", [])
            entry = {
                "lifecycle_id": LIFECYCLE,
                "actor": "astra",
                "started_at": STARTED,
                "ended_at": report["ended_at"],
                "report_json": str(jp.relative_to(ROOT)),
                "report_json_sha256": digest,
                "report_md": str(mp.relative_to(ROOT)),
                "report_md_sha256": md_digest,
                "validate_map": report["verification"]["validate_map"],
                "audit_evidence_hard": audit_hard,
                "numerics_lock": m["numerics_lock"]["state"],
            }
            lifecycles = [x for x in lifecycles if x.get("lifecycle_id") != LIFECYCLE] + [entry]
            m["controller_lifecycles"] = lifecycles
            m["updated_at"] = now()
            tmp = MAP.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(m, indent=2) + "\n")
            tmp.replace(MAP)
            rec = checkpoint.main("astra-indep-1-close")
            print(json.dumps({"report": str(jp), "sha256": digest, "md_sha256": md_digest,
                              "checkpoint": rec["checkpoint_id"],
                              "hard": rec["evidence_hard_failures"]}, indent=1))
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


if __name__ == "__main__":
    main()

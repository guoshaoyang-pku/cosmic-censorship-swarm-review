#!/usr/bin/env python3
"""W024-CHECKPOINT-VACUITY-01: independent fail-open / vacuity audit of research_map/checkpoint.py.

The 15-minute checkpoint is the controller's standing evidence instrument: its record is what
"map VALID / 0 hard failures / classsep PASS / lock present" quotes come from. This driver asks
whether that record can distinguish a healthy swarm from a stripped tree, and whether the
process boundary (exit code) can gate on the record it just wrote.

Method: every case runs the pinned checkpoint module inside a byte-identical sandbox copy of a
pinned repo subset (ROOT is derived from __file__, so a sandbox tree is self-contained). Each
case mutates exactly one structure, runs checkpoint.py at the pinned hash, and asserts the
recorded observations. A proposed fail-closed patch (proposal only, never applied to canonical
paths) is exercised against the same mutations.

Exit 0 iff every assertion holds and every sandbox pin is stable. Exit 2 on pin drift.

Usage: python3 artifacts/worker-024/checkpoint_vacuity/drive_vacuity.py [--keep]
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ARTIFACT = Path(__file__).resolve().parent
REPO = ARTIFACT.parents[2]
SNAP = ARTIFACT / "snapshots"
PATCHED = ARTIFACT / "patched"
RUNS = ARTIFACT / "runs"
CST = timezone(timedelta(hours=8))

# ---------------------------------------------------------------- pins
PINS = {
    "research_map/checkpoint.py": "152b40ead267173067acc7fe23df569a30aa0d1fb53b5aadbd786c0035afcac3",
    "research_map/comms.py": "7e905012ad6b8007f7fc2131a2ce0f35abae13d4205f15f8acd00ad9ff3ce724",
    "research_map/validate_map.py": "0bf3eb3ec4ee3513d604377b115a7b448f08813f68bc8310613ba76f995c9f1f",
    "research_map/audit_evidence.py": "36cf433a90b6b7a8c84596e4b36aac8796c10c82dc2c81514200f5d01135c052",
    "research_map/schemas.py": "75214a75353b9cd16952958c4711896a46f1f1bda1529622441f14eacf04003b",
    "research_map/class_separation.py": "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920",
    "research_map/research_map.json": "3d45be5969ec388ef4a3e10d5eb87b81dbf3d03138510b75ff6a56453ceae005",
    "research_map/events.jsonl": "3853ef1e72f1a29b9efa3b1d33d7b170eebea4f26aa1ac2bcf0c89e10be72146",
    "runtime/bin/classsep_regression.py": "9f1cf9c336be874182e8882e00f7fdf8e4f6c4ea1881f11a6b3e762e038a7091",
}
SNAP_SRC = {
    "research_map/checkpoint.py": SNAP / "checkpoint.152b40ead267.py",
    "research_map/comms.py": SNAP / "comms.7e905012ad6b.py",
    "research_map/validate_map.py": SNAP / "validate_map.0bf3eb3ec4ee.py",
    "research_map/audit_evidence.py": SNAP / "audit_evidence.36cf433a90b6.py",
    "research_map/schemas.py": SNAP / "schemas.75214a75353b.py",
    "research_map/class_separation.py": SNAP / "class_separation.c266dbceca87.py",
    "research_map/research_map.json": SNAP / "research_map.3d45be5969ec.json",
    "research_map/events.jsonl": SNAP / "events.head200.jsonl",
    "runtime/bin/classsep_regression.py": SNAP / "classsep_regression.9f1cf9c336be.py",
}
PATCHED_PIN = "b1ca1e82e94336767069573b2d14112fea4a5b7384d4722978245358ca85858d"
PATCH_DIFF_PIN = "PENDING"  # filled by the report after hashing (not asserted)

REGISTRY_ROOTS = ("schemas", "ledger", "reviews", "evaluation", "numerics",
                  "artifacts/numerics", "runtime/state/controller_verification")
REGISTRY_FILE = "evaluation_rubric.yaml"
CORPUS = "artifacts/worker-07/class_separation_falsification"
LIVE_CANONICAL = list(PINS) + ["research_map/events.jsonl"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_rollup(root: Path) -> dict:
    if not root.is_dir():
        return {"files": 0, "sha256": None}
    h = hashlib.sha256()
    n = 0
    for p in sorted(x for x in root.rglob("*") if x.is_file() and not x.name.startswith("._")):
        h.update(f"{p.relative_to(root)}\0{sha256(p)}\n".encode())
        n += 1
    return {"files": n, "sha256": h.hexdigest()}


def live_hashes() -> dict:
    out = {}
    for rel in LIVE_CANONICAL:
        p = REPO / rel
        out[rel] = sha256(p) if p.is_file() else None
    return out


# ---------------------------------------------------------------- sandbox
def build_base(dst: Path) -> dict:
    for d in ("research_map", "comms/outbox", "runtime/state", "runtime/bin"):
        (dst / d).mkdir(parents=True, exist_ok=True)
    for rel, src in SNAP_SRC.items():
        tgt = dst / rel
        tgt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, tgt)
    (dst / "artifacts" / "worker-07").mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO / CORPUS, dst / CORPUS)
    for d in REGISTRY_ROOTS:
        if (REPO / d).is_dir():
            shutil.copytree(REPO / d, dst / d)
    if (REPO / REGISTRY_FILE).is_file():
        shutil.copy2(REPO / REGISTRY_FILE, dst / REGISTRY_FILE)
    (dst / "runtime" / "state" / "ingested_ids.json").write_text("[]")
    registry = REPO / "runtime" / "state" / "artifact_hashes.json"
    (dst / "runtime" / "state" / "artifact_hashes.json").write_bytes(registry.read_bytes())
    pins = {}
    for rel in PINS:
        pins[rel] = sha256(dst / rel)
    bad = {k: v for k, v in pins.items() if v != PINS[k]}
    return {"pins": pins, "pin_drift": bad,
            "registry_roots": {d: tree_rollup(dst / d) for d in REGISTRY_ROOTS},
            "registry_baseline_sha256": sha256(dst / "runtime" / "state" / "artifact_hashes.json")}


def load_map(case: Path) -> dict:
    return json.loads((case / "research_map" / "research_map.json").read_text())


def save_map(case: Path, m: dict) -> None:
    (case / "research_map" / "research_map.json").write_text(json.dumps(m, indent=2, sort_keys=True))


# ---------------------------------------------------------------- mutations
def m_none(c): pass
def m_events_missing(c): (c / "research_map" / "events.jsonl").unlink()
def m_events_corrupt(c): (c / "research_map" / "events.jsonl").write_text('{"event_id": "corrupt-line"}\n')
def m_outbox_missing(c): shutil.rmtree(c / "comms" / "outbox")
def m_corpus_missing(c):
    # results.json stays (so regression() runs); unreachable fixtures -> 0/0/0/0 PASS
    shutil.rmtree(c / CORPUS / "fixtures")
def m_corpus_results_missing(c):
    (c / CORPUS / "results.json").unlink()
def m_governance_stripped(c):
    m = load_map(c)
    m["gates"] = []
    for k in ("numerics_lock", "frozen_artifacts", "claims"):
        m.pop(k, None)
    save_map(c, m)
def m_registry_missing(c):
    for d in REGISTRY_ROOTS:
        if (c / d).is_dir():
            shutil.rmtree(c / d)
    if (c / REGISTRY_FILE).is_file():
        (c / REGISTRY_FILE).unlink()
def m_map_invalid(c):
    m = load_map(c)
    m["groups"][0]["nodes"].append(dict(m["groups"][0]["nodes"][0]))  # duplicate node id
    save_map(c, m)
def m_map_corrupt(c):
    (c / "research_map" / "research_map.json").write_text("{ this is not json")


# ---------------------------------------------------------------- runner
def run_cp(case: Path, label: str, patched: bool = False, dry_run: bool = False) -> dict:
    script = case / "research_map" / "checkpoint.py"
    if patched:
        shutil.copy2(PATCHED / "checkpoint.patched.py", script)
    cur = case / "runtime" / "state" / "current_checkpoint.json"
    before = sha256(cur) if cur.is_file() else None
    log = case / "runtime" / "state" / "checkpoint_log.jsonl"
    log_before = log.read_text() if log.is_file() else ""
    reg = case / "runtime" / "state" / "artifact_hashes.json"
    reg_before = sha256(reg) if reg.is_file() else None
    cmd = [sys.executable, str(script), "--label", label] + (["--dry-run"] if dry_run else [])
    t0 = time.time()
    pr = subprocess.run(cmd, cwd=case, capture_output=True, text=True, timeout=600)
    dt = round(time.time() - t0, 3)
    rec = None
    if cur.is_file():
        try:
            rec = json.loads(cur.read_text())
        except ValueError:
            rec = None
    disk_reg = None
    if reg.is_file():
        try:
            disk_reg = json.loads(reg.read_text())
        except ValueError:
            disk_reg = None
    log_after = log.read_text() if log.is_file() else ""
    return {
        "rc": pr.returncode, "seconds": dt,
        "stdout": pr.stdout[-4000:], "stderr": pr.stderr[-2000:],
        "current_before_sha256": before, "current_after_sha256": sha256(cur) if cur.is_file() else None,
        "current_written": (sha256(cur) if cur.is_file() else None) != before,
        "record": rec,
        "checkpoint_log_lines_added": len(log_after.splitlines()) - len(log_before.splitlines()),
        "registry_disk_before_sha256": reg_before,
        "registry_disk_after_sha256": sha256(reg) if reg.is_file() else None,
        "registry_disk": disk_reg,
    }


def n_reg(rec: dict) -> int:
    """registry size as recorded (unpatched uses artifact_registry; patched records the scan size)."""
    if rec is None:
        return -1
    if "registry_scan_size" in rec:
        return int(rec["registry_scan_size"])
    return len(rec.get("artifact_registry") or {})


def nv(rec: dict) -> dict:
    return (rec or {}).get("nonvacuity") or {}


# ---------------------------------------------------------------- expectations
def checks_for(name: str, obs: dict) -> list:
    rec = (obs.get("record") or {})
    out = []

    def chk(cid, ok, detail=""):
        out.append({"id": cid, "ok": bool(ok), "detail": detail})

    if name == "C0_healthy_control":
        chk("rc0", obs["rc"] == 0, f"rc={obs['rc']}")
        chk("record_written", obs["current_written"])
        chk("map_valid", rec.get("map_validator") == "VALID", str(rec.get("map_validator")))
        chk("corpus_27", (rec.get("classsep_regression") or {}).get("corpus_size") == 27)
        chk("corpus_pass", (rec.get("classsep_regression") or {}).get("verdict") == "PASS")
        chk("registry_nonempty", n_reg(rec) > 0, f"registry={n_reg(rec)}")
        chk("events_200", rec.get("events_total") == 200, str(rec.get("events_total")))
        chk("events_no_errors", rec.get("event_stream_errors") == [])
        chk("gates_5", len(rec.get("gates") or {}) == 5, str(sorted((rec.get("gates") or {}).keys())))
        chk("lock_present", bool(rec.get("numerics_lock")))
        chk("no_nonvacuity_field_prepatch", rec.get("nonvacuity") is None)
    elif name == "C1_events_missing":
        chk("rc0", obs["rc"] == 0, f"rc={obs['rc']}")
        chk("record_written", obs["current_written"])
        chk("error_list_empty", rec.get("event_stream_errors") == [], "absent stream is invisible")
        chk("events_total_0", rec.get("events_total") == 0, str(rec.get("events_total")))
        chk("map_still_valid", rec.get("map_validator") == "VALID")
        chk("pending_0", rec.get("events_pending_application") == 0)
    elif name == "C2_events_corrupt_positive_control":
        chk("rc0", obs["rc"] == 0, f"rc={obs['rc']}")
        chk("errors_recorded", len(rec.get("event_stream_errors") or []) > 0,
            str((rec.get("event_stream_errors") or [])[:1]))
        chk("events_total_1", rec.get("events_total") == 1)
        chk("record_written", obs["current_written"])
    elif name == "C3_outbox_missing":
        chk("rc0", obs["rc"] == 0, f"rc={obs['rc']}")
        chk("files_0", (rec.get("comms") or {}).get("outbox_files_seen") == 0)
        chk("accepted_0", (rec.get("comms") or {}).get("accepted") == 0)
        chk("no_error_field", "error" not in json.dumps(rec.get("comms") or {}))
    elif name == "C4_classsep_corpus_missing":
        chk("rc0", obs["rc"] == 0, f"rc={obs['rc']}")
        csr = rec.get("classsep_regression") or {}
        chk("verdict_pass", csr.get("verdict") == "PASS", str(csr))
        chk("corpus_size_0", csr.get("corpus_size") == 0, str(csr.get("corpus_size")))
        chk("record_written", obs["current_written"])
    elif name == "C5_governance_stripped":
        chk("rc0", obs["rc"] == 0, f"rc={obs['rc']}")
        chk("validator_still_valid", rec.get("map_validator") == "VALID", str(rec.get("map_validator")))
        chk("gates_empty", rec.get("gates") == {}, str(rec.get("gates")))
        chk("lock_absent", not rec.get("numerics_lock"), str(rec.get("numerics_lock")))
        chk("no_flag", "nonvacuity" not in rec)
    elif name == "C6_registry_roots_missing":
        chk("rc0", obs["rc"] == 0, f"rc={obs['rc']}")
        chk("clobbered_empty", (obs.get("registry_disk") or {}).get("registry") == {}
            and (obs.get("registry_disk") or {}).get("hashes") == {}, str(obs.get("registry_disk"))[:120])
        chk("pre_was_nonempty", obs["registry_disk_before_sha256"] != obs["registry_disk_after_sha256"])
        chk("record_registry_empty", n_reg(rec) == 0, str(n_reg(rec)))
    elif name == "C7_map_invalid":
        chk("rc0_despite_invalid", obs["rc"] == 0, f"rc={obs['rc']}")
        chk("map_invalid_recorded", rec.get("map_validator") == "INVALID", str(rec.get("map_validator")))
        chk("errors_nonempty", len(rec.get("map_errors") or []) > 0)
        chk("record_written", obs["current_written"])
        chk("log_line_added", obs["checkpoint_log_lines_added"] == 1)
    elif name == "N1_map_corrupt_control":
        chk("rc_nonzero", obs["rc"] != 0, f"rc={obs['rc']}")
        chk("no_record_written", not obs["current_written"])
    elif name == "N2_corpus_results_missing_control":
        chk("rc_nonzero", obs["rc"] != 0, f"rc={obs['rc']}")
        chk("no_record_written", not obs["current_written"])
        chk("crash_not_vacuous_pass", "PASS" not in (obs["stdout"] + obs["stderr"])[:2000]
            or obs["rc"] != 0, "regression() raised on absent results.json")
    elif name == "C8_stamp_collision":
        chk("one_file_two_log_lines", obs["files"] == 1 and obs["log_lines"] == 2,
            f"files={obs['files']} log_lines={obs['log_lines']}")
        chk("second_label_wins", obs["file_label"] == "B", str(obs["file_label"]))
    elif name.startswith("P"):
        reasons = nv(rec).get("reasons") or []
        text = obs["stdout"]
        if name == "P0_healthy":
            chk("rc0", obs["rc"] == 0, f"rc={obs['rc']}")
            chk("nonvacuity_pass", nv(rec).get("verdict") == "PASS", str(nv(rec)))
        elif name == "P1_events_missing":
            chk("rc1", obs["rc"] == 1, f"rc={obs['rc']}")
            # ingest re-creates an absent events.jsonl, so the patched reason is EMPTY_ not MISSING_
            chk("reason", ({"MISSING_EVENT_STREAM", "EMPTY_EVENT_STREAM"} & set(reasons)) and "REASON " in text,
                str(reasons))
        elif name == "P2_governance_stripped":
            chk("rc1", obs["rc"] == 1, f"rc={obs['rc']}")
            chk("gates_reason", any(r.startswith("GATES_MISSING:") for r in reasons), str(reasons))
            chk("lock_reason", "NUMERICS_LOCK_ABSENT" in reasons, str(reasons))
        elif name == "P3_registry_missing":
            chk("rc1", obs["rc"] == 1, f"rc={obs['rc']}")
            chk("registry_reason", "REGISTRY_EMPTY" in reasons, str(reasons))
            chk("preserved_previous", (obs.get("registry_disk") or {}).get("registry")
                and rec.get("registry_source", "").startswith("preserved-previous"),
                str(rec.get("registry_source")))
        elif name == "P4_corpus_missing":
            chk("rc1", obs["rc"] == 1, f"rc={obs['rc']}")
            chk("corpus_reason", "CLASSSEP_CORPUS_EMPTY" in reasons, str(reasons))
        elif name == "P5_map_invalid":
            chk("rc1", obs["rc"] == 1, f"rc={obs['rc']}")
            chk("map_reason", "MAP_INVALID" in reasons, str(reasons))
        elif name == "P6_corrupt_events":
            chk("rc1", obs["rc"] == 1, f"rc={obs['rc']}")
            chk("stream_reason", "EVENT_STREAM_ERRORS" in reasons, str(reasons))
        elif name == "P7_dry_run":
            chk("rc1_reported", obs["rc"] == 1, f"rc={obs['rc']}")
            chk("no_current_write", not obs["current_written"])
            chk("registry_untouched", obs["registry_disk_before_sha256"] == obs["registry_disk_after_sha256"])
            chk("no_log_line", obs["checkpoint_log_lines_added"] == 0)
            chk("reason_printed", "REASON REGISTRY_EMPTY" in text, text[-200:])
    return out


# ---------------------------------------------------------------- cases
CASES = [
    ("C0_healthy_control", m_none, False, False),
    ("C1_events_missing", m_events_missing, False, False),
    ("C2_events_corrupt_positive_control", m_events_corrupt, False, False),
    ("C3_outbox_missing", m_outbox_missing, False, False),
    ("C4_classsep_corpus_missing", m_corpus_missing, False, False),
    ("C5_governance_stripped", m_governance_stripped, False, False),
    ("C6_registry_roots_missing", m_registry_missing, False, False),
    ("C7_map_invalid", m_map_invalid, False, False),
    ("N1_map_corrupt_control", m_map_corrupt, False, False),
    ("N2_corpus_results_missing_control", m_corpus_results_missing, False, False),
    ("P0_healthy", m_none, True, False),
    ("P1_events_missing", m_events_missing, True, False),
    ("P2_governance_stripped", m_governance_stripped, True, False),
    ("P3_registry_missing", m_registry_missing, True, False),
    ("P4_corpus_missing", m_corpus_missing, True, False),
    ("P5_map_invalid", m_map_invalid, True, False),
    ("P6_corrupt_events", m_events_corrupt, True, False),
    ("P7_dry_run", m_registry_missing, True, True),
]


def stamp_case(base: Path, tmp: Path, patched: bool) -> dict:
    """C8: two checkpoint invocations inside one second must not share a file name."""
    tag = "C8_stamp_collision_patched" if patched else "C8_stamp_collision"
    case = tmp / tag
    shutil.copytree(base, case)
    if patched:
        shutil.copy2(PATCHED / "checkpoint.patched.py", case / "research_map" / "checkpoint.py")
    sys.path.insert(0, str(case / "research_map"))
    for mod in [m for m in list(sys.modules) if m in ("checkpoint", "comms", "validate_map",
                                                       "audit_evidence", "class_separation", "schemas")]:
        del sys.modules[mod]
    import checkpoint  # noqa: E402
    if not patched:
        checkpoint.stamp = lambda: "20260912-FIXEDSTAMP"
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            checkpoint.main("A")
            checkpoint.main("B")
    finally:
        sys.path.remove(str(case / "research_map"))
    ck = sorted((case / "runtime" / "state" / "checkpoints").glob("ckpt-*.json"))
    log = case / "runtime" / "state" / "checkpoint_log.jsonl"
    label = json.loads(ck[0].read_text())["label"] if len(ck) == 1 else None
    return {"files": len(ck), "log_lines": len(log.read_text().splitlines()) if log.is_file() else 0,
            "file_label": label, "stdout": buf.getvalue()[-2000:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    RUNS.mkdir(parents=True, exist_ok=True)
    live_entry = live_hashes()
    tmp = Path(tempfile.mkdtemp(prefix="w024_ckv_"))
    base = tmp / "base"
    base_info = build_base(base)
    if base_info["pin_drift"]:
        print("PIN DRIFT in sandbox:", json.dumps(base_info["pin_drift"], indent=2))
        return 2
    results, all_checks = [], []
    for name, mut, patched, dry in CASES:
        case = tmp / name
        shutil.copytree(base, case)
        mut(case)
        obs = run_cp(case, name, patched=patched, dry_run=dry)
        checks = checks_for(name, obs)
        all_checks += [{"case": name, **c} for c in checks]
        results.append({"case": name, "patched": patched, "dry_run": dry, "mutation": mut.__name__,
                        "rc": obs["rc"], "seconds": obs["seconds"],
                        "record": obs["record"],
                        "observation": {k: obs[k] for k in
                                        ("current_before_sha256", "current_after_sha256", "current_written",
                                         "checkpoint_log_lines_added", "registry_disk_before_sha256",
                                         "registry_disk_after_sha256")},
                        "registry_disk_empty": (obs.get("registry_disk") or {}).get("registry") == {},
                        "stdout_tail": obs["stdout"][-1500:], "stderr_tail": obs["stderr"][-600:],
                        "checks": checks})
        (RUNS / f"{name}.stdout.txt").write_text(obs["stdout"])
        (RUNS / f"{name}.stderr.txt").write_text(obs["stderr"])
        print(f"{name:<38} rc={obs['rc']} checks={sum(c['ok'] for c in checks)}/{len(checks)}")
    # C8 stamp collision (unpatched: patched stamp -> same file name; patched: microseconds)
    c8 = stamp_case(base, tmp, patched=False)
    c8_checks = checks_for("C8_stamp_collision", c8)
    all_checks += [{"case": "C8_stamp_collision", **c} for c in c8_checks]
    results.append({"case": "C8_stamp_collision", "patched": False, "dry_run": False,
                    "mutation": "stamp monkeypatched to a fixed value", "rc": 0, "seconds": None,
                    "record": None, "observation": c8, "checks": c8_checks})
    print(f"{'C8_stamp_collision':<38} files={c8['files']} log_lines={c8['log_lines']} "
          f"checks={sum(c['ok'] for c in c8_checks)}/{len(c8_checks)}")
    c8p = stamp_case(base, tmp, patched=True)
    c8p_checks = [{"id": "two_files_microsecond_stamp", "ok": c8p["files"] == 2,
                   "detail": f"files={c8p['files']}"},
                  {"id": "two_log_lines", "ok": c8p["log_lines"] == 2, "detail": f"log_lines={c8p['log_lines']}"}]
    all_checks += [{"case": "C8_stamp_collision_patched", **c} for c in c8p_checks]
    results.append({"case": "C8_stamp_collision_patched", "patched": True, "dry_run": False,
                    "mutation": "stamp uses microseconds", "rc": 0, "seconds": None,
                    "record": None, "observation": c8p, "checks": c8p_checks})
    print(f"{'C8_stamp_collision_patched':<38} files={c8p['files']} log_lines={c8p['log_lines']} "
          f"checks={sum(c['ok'] for c in c8p_checks)}/{len(c8p_checks)}")

    live_exit = live_hashes()
    live_drift = {k: [live_entry[k], live_exit[k]] for k in live_entry if live_entry[k] != live_exit[k]}
    passed = sum(1 for c in all_checks if c["ok"])
    report = {
        "audit_id": "W024-CHECKPOINT-VACUITY-01",
        "auditor": "worker-024",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "audited_instrument": "research_map/checkpoint.py",
        "audited_hash": PINS["research_map/checkpoint.py"],
        "sandbox_pins": PINS,
        "sandbox_pins_stable": True,
        "patched_hash": PATCHED_PIN,
        "patched_pin_measured": sha256(PATCHED / "checkpoint.patched.py"),
        "patch_diff_sha256_measured": sha256(ARTIFACT / "proposed_fail_closed_patch.diff"),
        "live_canonical_entry": live_entry,
        "live_canonical_exit": live_exit,
        "live_canonical_drift": live_drift,
        "registry_baseline_sha256": base_info["registry_baseline_sha256"],
        "registry_roots": base_info["registry_roots"],
        "checks_passed": passed, "checks_total": len(all_checks),
        "case_results": results,
        "checks": all_checks,
        "verdict": "DEFECTIVE_CHECKPOINT_CERTIFICATE" if passed == len(all_checks) else "DRIVER_MISMATCH",
        "authority_note": "worker audit report: no gate verdict, no node transition, no validation_status=passed",
    }
    (ARTIFACT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(f"\nchecks {passed}/{len(all_checks)}; live canonical drift: {sorted(live_drift)}")
    if not a.keep:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0 if passed == len(all_checks) else 1


if __name__ == "__main__":
    sys.exit(main())

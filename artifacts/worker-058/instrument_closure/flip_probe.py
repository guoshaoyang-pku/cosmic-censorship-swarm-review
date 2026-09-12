#!/usr/bin/env python3
"""W058 outcome-flip probe: prove the unpinned stage-2 instrument can move G-FORM
acceptance sub-verdicts while no pinned byte moves.

Read-only on canonical paths; everything happens in
`artifacts/worker-058/instrument_closure/sandbox_flip/`.

Sequence
--------
A   build a faithful sandbox root: copy every FROZEN-pinned path that exists, plus the
    stage-2 engine and its fixtures; absorb any *external* pre-existing pin drift into
    the sandbox manifest and record it (the sandbox must start internally consistent).
A1  rebase the mutant corpus in the sandbox (canonical preflight evidence is stale
    against the live C0); update the moved evidence pin and record it.
B   baseline `run_acceptance.py --json`  -> pinned report bytes restored afterwards
C   `verify_frozen.py` in the sandbox    -> rc=0
D   closure_check --strict               -> rc=1, stage-2 engine listed UNPINNED
E   tamper the unpinned engine (always-accept stub), re-run acceptance
F   all sandbox pins match the sandbox manifest; verify_frozen rc=0; closure still
    reports the engine as UNPINNED (not drift)
G   remedy control: restore engine bytes, pin every D gap path at its measured hash,
    closure_check --strict -> CLOSED rc=0
H   drift control: tamper the engine again -> closure_check --strict -> rc=1, engine
    status PINNED_DRIFT
I   canonical hashes re-measured == snapshot

Writes `flip_probe.json` and raw `flip_*_acceptance.json` next to this file.
Boundary: worker evidence only; the sandbox manifest is a simulation, not a
publication; no gate verdict, no node status, no math claim.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SANDBOX = HERE / "sandbox_flip"
CST = timezone(timedelta(hours=8))
FROZEN_REL = "artifacts/formulation/FROZEN.json"
ENGINE_REL = "artifacts/worker-06/spec_conformance_audit.py"
REPORT_REL = "artifacts/formulation/evidence/acceptance_pipeline_report.json"
EVIDENCE_REL = "artifacts/formulation/evidence/semantic_escape_rebased.json"
CANON_PATHS = [FROZEN_REL, "schemas/af_scc_c0_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
               "schemas/af_wcc_vacuum.yaml", ENGINE_REL]
STUB = ('#!/usr/bin/env python3\n"""TAMPERED sandbox stage-2 engine: always accept. '
        'Planted by W058 flip_probe."""\nimport json, sys\n'
        'print(json.dumps({"verdict": "accept", "failed_rules": []}))\nsys.exit(0)\n')


def sha(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except (FileNotFoundError, IsADirectoryError):
        return None


def run(cmd, cwd=None) -> dict:
    r = subprocess.run([str(c) for c in cmd], cwd=str(cwd or REPO),
                       capture_output=True, text=True)
    return {"cmd": [str(c) for c in cmd], "cwd": str(cwd or REPO), "rc": r.returncode,
            "stdout_tail": r.stdout.strip().splitlines()[-10:],
            "stderr_tail": r.stderr.strip().splitlines()[-10:]}


def acceptance(tag: str) -> dict:
    rep = SANDBOX / REPORT_REL
    if rep.exists():
        rep.unlink()
    proc = run([sys.executable, SANDBOX / "artifacts/formulation/tools/run_acceptance.py", "--json"])
    out = {"run": proc}
    if rep.exists():
        body = json.loads(rep.read_text())
        out.update({"verdict": body["verdict"], "mutants": body["mutants"],
                    "canonical": body["canonical"], "controls": body["controls"],
                    "report_sha256": sha(rep)})
        shutil.copy2(rep, HERE / f"flip_{tag}_acceptance.json")
    else:
        out["verdict"] = f"NO_REPORT(rc={proc['rc']})"
    return out


def verify_frozen() -> dict:
    return run([sys.executable, SANDBOX / "artifacts/formulation/tools/verify_frozen.py"])


def closure(out_name: str = "_sandbox_closure.json") -> dict:
    proc = run([sys.executable, HERE / "closure_check.py", "--root", SANDBOX,
                "--scope", "acceptance", "--strict", "--out", HERE / out_name])
    body = json.loads((HERE / out_name).read_text())
    proc["verdict"] = body["verdict"]
    proc["effect_capable_unpinned"] = body["effect_capable_unpinned"]
    proc["engine_status"] = body["nodes"].get(ENGINE_REL, {}).get("status")
    proc["counts"] = body["counts"]
    proc["nodes"] = body["nodes"]
    return proc


def pinned_violations() -> list[dict]:
    man = json.loads((SANDBOX / FROZEN_REL).read_text())
    bad = []
    for rel, meta in sorted(man["files"].items()):
        got = sha(SANDBOX / rel)
        if got != meta["sha256"]:
            bad.append({"path": rel, "declared": meta["sha256"][:12],
                        "measured": (got or "MISSING")[:12]})
    return bad


def main() -> int:
    out: dict = {"probe": "W058-OUTCOME-FLIP-07",
                 "created_at": datetime.now(CST).isoformat(timespec="seconds"),
                 "sandbox": str(SANDBOX.relative_to(REPO)),
                 "canonical_snapshot_before": {p: sha(REPO / p) for p in CANON_PATHS}}

    # A build a faithful sandbox (all pinned paths + engine + fixtures)
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    man = json.loads((REPO / FROZEN_REL).read_text())
    copied, missing = [], []
    for rel in sorted(man["files"]):
        src, dst = REPO / rel, SANDBOX / rel
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(rel)
        else:
            missing.append(rel)
    shutil.copytree(REPO / "artifacts/worker-06/semantic_fixtures",
                    SANDBOX / "artifacts/worker-06/semantic_fixtures")
    (SANDBOX / ENGINE_REL).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / ENGINE_REL, SANDBOX / ENGINE_REL)
    out["A_build"] = {"pinned_copied": len(copied), "pinned_missing": missing,
                      "engine_sha256": sha(SANDBOX / ENGINE_REL)}

    # absorb external pre-existing pin drift into the sandbox manifest (recorded)
    absorbed = []
    for rel, meta in list(man["files"].items()):
        got = sha(SANDBOX / rel)
        if got != meta["sha256"]:
            absorbed.append({"path": rel, "frozen_rev29_declared": meta["sha256"][:12],
                             "live_measured": (got or "MISSING")[:12]})
            if got:
                man["files"][rel] = {"sha256": got, "bytes": (SANDBOX / rel).stat().st_size}
    if absorbed:
        (SANDBOX / FROZEN_REL).write_text(json.dumps(man, indent=2) + "\n")
    out["A_external_drift_absorbed"] = absorbed

    # A1 rebase the corpus in the sandbox at the live C0
    canon_ev = json.loads((REPO / EVIDENCE_REL).read_text())
    live_c0 = sha(REPO / "schemas/af_scc_c0_vacuum.yaml")
    before_ev = sha(SANDBOX / EVIDENCE_REL)
    rebase = run([sys.executable, SANDBOX / "artifacts/formulation/tools/measure_semantic_escape.py"])
    after_ev = sha(SANDBOX / EVIDENCE_REL)
    moved = []
    if after_ev and after_ev != before_ev:
        man = json.loads((SANDBOX / FROZEN_REL).read_text())
        man["files"][EVIDENCE_REL] = {"sha256": after_ev,
                                      "bytes": (SANDBOX / EVIDENCE_REL).stat().st_size}
        (SANDBOX / FROZEN_REL).write_text(json.dumps(man, indent=2) + "\n")
        moved.append(EVIDENCE_REL)
    out["A1_preflight"] = {
        "canonical_evidence_base_sha256": canon_ev.get("base_sha256"),
        "live_c0_sha256": live_c0,
        "canonical_evidence_stale": canon_ev.get("base_sha256") != live_c0,
        "rebase_run": rebase, "rebase_evidence_sha256": after_ev,
        "pins_moved_by_rebase": moved}

    # B baseline acceptance; preserve the FROZEN-declared report bytes
    report_bytes = (SANDBOX / REPORT_REL).read_bytes() if (SANDBOX / REPORT_REL).exists() else None
    out["B_baseline"] = acceptance("baseline")
    if report_bytes is not None:
        (SANDBOX / REPORT_REL).write_bytes(report_bytes)
    out["C_verify_frozen_baseline"] = verify_frozen()
    out["C_pinned_violations_baseline"] = pinned_violations()
    d = out["D_closure_before"] = closure()

    # E tamper the unpinned engine, re-run acceptance
    (SANDBOX / ENGINE_REL).write_text(STUB)
    out["E_tamper"] = {"path": ENGINE_REL, "stub_sha256": sha(SANDBOX / ENGINE_REL)}
    out["E_acceptance_tampered"] = acceptance("tampered")
    if report_bytes is not None:
        (SANDBOX / REPORT_REL).write_bytes(report_bytes)
    out["F_pinned_violations_after_tamper"] = pinned_violations()
    out["F_verify_frozen_after_tamper"] = verify_frozen()
    f = out["F_closure_after_tamper"] = closure()

    # G remedy: restore engine bytes, pin the full D gap set
    (SANDBOX / ENGINE_REL).write_bytes((REPO / ENGINE_REL).read_bytes())
    man = json.loads((SANDBOX / FROZEN_REL).read_text())
    added = []
    for rel in d["effect_capable_unpinned"]:
        p = SANDBOX / rel
        if p.is_file():
            man["files"][rel] = {"sha256": sha(p), "bytes": p.stat().st_size}
            added.append(rel)
    (SANDBOX / FROZEN_REL).write_text(json.dumps(man, indent=2) + "\n")
    out["G_remedy"] = {"paths_pinned": len(added), "sample": added[:5]}
    out["G_closure_after_pinning"] = closure("_sandbox_closure_pinned.json")

    # H drift control
    (SANDBOX / ENGINE_REL).write_text(STUB)
    out["H_closure_drift"] = closure("_sandbox_closure_drift.json")

    # I canonical read-only check
    out["I_canonical_snapshot_after"] = {p: sha(REPO / p) for p in CANON_PATHS}
    out["I_canonical_unchanged"] = (
        out["I_canonical_snapshot_after"] == out["canonical_snapshot_before"])

    b, e = out["B_baseline"], out["E_acceptance_tampered"]
    canonical = {r["schema"]: r for r in b.get("canonical", [])}
    checks = {
        "baseline_union_met": b.get("mutants", {}).get("union_caught") == b.get("mutants", {}).get("total"),
        "baseline_canonical_f1_rejected": canonical.get("af_wcc_vacuum.yaml", {}).get("semantic") == "fail",
        "tamper_accepts_canonical_f1": {r["schema"]: r for r in e.get("canonical", [])}
                                       .get("af_wcc_vacuum.yaml", {}).get("semantic") == "pass",
        "tamper_breaks_union": e.get("mutants", {}).get("union_caught", 99) < e.get("mutants", {}).get("total", 0),
        "tamper_zeroes_semantic_catches": e.get("mutants", {}).get("semantic_caught") == 0,
        "no_pinned_byte_moved": out["F_pinned_violations_after_tamper"] == [],
        "verify_frozen_still_rc0": out["F_verify_frozen_after_tamper"]["rc"] == 0,
        "engine_unpinned_before": d["engine_status"] == "UNPINNED",
        "remedy_closes_closure": out["G_closure_after_pinning"]["verdict"] == "CLOSED",
        "remedy_strict_rc0": out["G_closure_after_pinning"]["rc"] == 0,
        "drift_detected_after_pin": out["H_closure_drift"]["engine_status"] == "PINNED_DRIFT",
        "canonical_unchanged": out["I_canonical_unchanged"],
    }
    out["checks"] = checks
    out["verdict"] = "FLIP_CONFIRMED" if all(checks.values()) else "FLIP_PROBE_INCOMPLETE"
    (HERE / "flip_probe.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"FLIP_PROBE {out['verdict']}: " + ", ".join(f"{k}={v}" for k, v in checks.items()))
    return 0 if out["verdict"] == "FLIP_CONFIRMED" else 1


if __name__ == "__main__":
    sys.exit(main())

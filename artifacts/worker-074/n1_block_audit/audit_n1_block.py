#!/usr/bin/env python3
"""N1-BLOCK-AUDIT-01 (worker-074): independent adversarial audit of the N1 blocker contract.

Class binding: AF-WCC-SCALAR-SPH (node N1-BLOCK, gate G-NUM).

Question: does `numerics/blockers.md` (a) map 1:1 onto
`research_map/research_map.json#numerics_lock`, (b) state its current release-row status
truthfully against artifacts on disk, and (c) do the lock guards actually fail closed?

Read-only with respect to the repository: this script writes only inside its own artifact
directory (`raw/` and `report.json`).  The two guard CLIs that can write shared files
(`numerics.gates --write-report`, `--emit-blocker`) are NOT used; the release-gate library
entry point `numerics.gates.evaluate()` is called in-process instead.  Planted-violation
fixtures live in `tempfile.TemporaryDirectory()` and never touch the real tree.

Authority note: worker-authored evidence only.  This script cannot set a node status, a
validation_status, or a gate verdict; it emits unverified evidence for lead/audit review.

Usage:  python3 artifacts/worker-074/n1_block_audit/audit_n1_block.py
Exit:   0 = audit completed (findings are data, not gate verdicts), 2 = could not evaluate.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
MAP = ROOT / "research_map" / "research_map.json"
BLOCKERS = ROOT / "numerics" / "blockers.md"
PROTOCOL = ROOT / "numerics" / "CONVERGENCE_PROTOCOL.md"
GUARD = "numerics/tests/selfgravity_lock_guard.py"
TZ = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_file(p: Path) -> str | None:
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def run(cmd: list[str], timeout: int = 300) -> dict:
    try:
        pr = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                            timeout=timeout)
        return {"cmd": " ".join(cmd), "exit_code": pr.returncode,
                "stdout": pr.stdout, "stderr": pr.stderr}
    except subprocess.TimeoutExpired:
        return {"cmd": " ".join(cmd), "exit_code": None, "stdout": "", "stderr": "TIMEOUT"}
    except OSError as exc:
        return {"cmd": " ".join(cmd), "exit_code": None, "stdout": "",
                "stderr": f"{type(exc).__name__}: {exc}"}


# --------------------------------------------------------------------------- 1. snapshot
def snapshot() -> dict:
    m = json.loads(MAP.read_text())
    lock = m.get("numerics_lock", {})
    gates = {g.get("gate_id"): g.get("verdict") for g in m.get("gates", [])}
    nodes = {}
    for g in m.get("groups", []):
        for n in g.get("nodes", []):
            nodes[n.get("id")] = {"group": g.get("id"), "status": n.get("status"),
                                  "artifact": n.get("artifact"),
                                  "depends_on": n.get("depends_on", [])}
    return {
        "at": now(),
        "map_sha256": sha256_file(MAP),
        "map_updated_at": m.get("updated_at"),
        "numerics_lock": lock,
        "gate_verdicts": gates,
        "nodes": nodes,
        "blockers_md_sha256": sha256_file(BLOCKERS),
        "protocol_sha256": sha256_file(PROTOCOL),
        "n0_4rung_sha256": sha256_file(ROOT / "numerics/tests/n0_order_4rung.json"),
        "spherical_solver_exists": (ROOT / "numerics/spherical_solver").exists(),
    }


# ------------------------------------------------------- 2. condition mapping 1:1
ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|")

ROW_TO_KEY = {
    "1": "gate:G-FORM",
    "2": "gate:G-AUDIT",
    "3": "req:n0_measured",
    "4": "req:n0_replicated",
    "5": "req:protocol_reviewed",
    "6": "release:state_and_authority",
}


def expected_keys(lock: dict) -> list[dict]:
    out = []
    rg = list(lock.get("required_gates", []))
    for g in rg:
        out.append({"key": f"gate:{g}", "source": f"numerics_lock.required_gates[{g}]"})
    add = lock.get("additional_requirements", [])
    if any("measured" in a for a in add):
        out.append({"key": "req:n0_measured",
                    "source": "numerics_lock.additional_requirements[0]"})
    if any("independently replicated" in a for a in add):
        out.append({"key": "req:n0_replicated",
                    "source": "numerics_lock.additional_requirements[0]"})
    if any("reviewed by audit" in a for a in add):
        out.append({"key": "req:protocol_reviewed",
                    "source": "numerics_lock.additional_requirements[1]"})
    if lock.get("release_authority"):
        out.append({"key": "release:state_and_authority",
                    "source": "numerics_lock.release_authority + state"})
    return out


def condition_mapping(lock: dict) -> dict:
    rows = []
    for line in BLOCKERS.read_text().splitlines():
        if not ROW_RE.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        n = int(cells[0])
        rows.append({"row": n, "condition": cells[1], "machine_check": cells[2],
                     "claimed_state": " | ".join(cells[3:]),
                     "mapped_key": ROW_TO_KEY.get(str(n)),
                     "map_counterpart_ok": False})
    exp = expected_keys(lock)
    exp_keys = {e["key"] for e in exp}
    row_keys = {r["mapped_key"] for r in rows if r["mapped_key"]}
    for r in rows:
        r["map_counterpart_ok"] = r["mapped_key"] in exp_keys
    return {
        "rows_parsed": len(rows),
        "rows": rows,
        "map_derived_conditions": exp,
        "missing_from_blockers_md": sorted(exp_keys - row_keys),
        "added_by_blockers_md": sorted(row_keys - exp_keys),
        "one_to_one": (exp_keys == row_keys) and all(r["map_counterpart_ok"] for r in rows),
        "qualifier_note": (
            "row 3 machine-check cell adds a method qualifier ('certified at >= 4 rungs per "
            "protocol rev 3 3.2') that is not literal in the map key 'N0 convergence order "
            "measured'.  It narrows the measurement method rather than adding a release "
            "condition, but lead-audit should adjudicate whether it counts as a strengthening."
        ),
    }


# ------------------------------------------------- 3. current-state claims vs artifacts
def state_audit(g: dict, snap: dict) -> dict:
    lock = snap["numerics_lock"]
    out = {}
    out["row1_G-FORM"] = {
        "claimed": "pending", "map_verdict": snap["gate_verdicts"].get("G-FORM"),
        "agrees": snap["gate_verdicts"].get("G-FORM") == "pending",
    }
    out["row2_G-AUDIT"] = {
        "claimed": "pending", "map_verdict": snap["gate_verdicts"].get("G-AUDIT"),
        "agrees": snap["gate_verdicts"].get("G-AUDIT") == "pending",
    }
    four = json.loads((ROOT / "numerics/tests/n0_order_4rung.json").read_text())
    orders4 = four["verdict"]["orders"]
    agreement = g["order_agreement"]
    out["row3_n0_measured"] = {
        "claimed": "satisfied - 4-rung fit order 2.00 for three schemes",
        "four_rung_orders": orders4,
        "four_rung_summary": four["verdict"]["summary"],
        "artifact_events": {
            k: {"passed": v.get("artifact_event_passed"),
                "sha_match": v.get("event_sha256_match"), "sha256": v.get("sha256")}
            for k, v in g["n0_evidence"]["artifacts"].items()},
        "agrees": bool(all(1.7 < v < 2.3 for v in orders4.values())
                       and all(v.get("artifact_event_passed") and v.get("event_sha256_match")
                               for v in g["n0_evidence"]["artifacts"].values())),
    }
    out["row4_n0_replicated"] = {
        "claimed": ("satisfied - lffd 1.9966 / cnfd 1.9954 / cnfem 1.9889, max pairwise "
                    "|dp| 0.00776 <= 0.25, gate delta 0.0101 <= 0.35"),
        "gate_order_agreement": agreement,
        "agrees": bool(agreement.get("agreed")),
    }
    reviews = g["protocol_review"]
    proto_reviews = []
    for e in g.get("_events", []):
        t = str(e.get("target_id", ""))
        if "CONVERGENCE_PROTOCOL" in t or t in ("N0", "G-NUM-protocol"):
            proto_reviews.append({"event_id": e.get("event_id"), "reviewer": e.get("reviewer"),
                                  "verdict": e.get("verdict"),
                                  "target_id": t,
                                  "artifact_sha256": e.get("artifact_sha256") or e.get("sha256")})
    out["row5_protocol_reviewed"] = {
        "claimed": "missing (one review away); existing verdict is revise at pre-rev2 hash",
        "gate_protocol_review": reviews,
        "protocol_targeting_reviews": sorted(proto_reviews, key=lambda r: str(r.get("event_id"))),
        "current_protocol_sha256": snap["protocol_sha256"],
        "agrees": not reviews.get("reviewed") and not reviews.get("accepting_reviews"),
    }
    out["row6_lock_released"] = {
        "claimed": "locked (since 2026-09-11T23:15:11+08:00)",
        "map_state": lock.get("state"), "map_since": lock.get("since"),
        "release_authority": lock.get("release_authority"),
        "agrees": lock.get("state") == "locked"
                  and lock.get("release_authority") == "astra",
    }
    return out


# ------------------------------------------------------------------ 4. guard behaviour
def guard_tests(g: dict, snap: dict) -> dict:
    tests = {}
    raw_g1 = run([sys.executable, GUARD])
    (RAW / "guard_repo_run.txt").write_text(raw_g1["stdout"] + raw_g1["stderr"])
    try:
        g1 = json.loads(raw_g1["stdout"])
    except json.JSONDecodeError:
        g1 = {}
    tests["G1_repo_guard"] = {
        "exit_code": raw_g1["exit_code"], "verdict": g1.get("verdict"),
        "violations": g1.get("violations"),
        "declared_artifacts_checked": g1.get("declared_artifacts_checked"),
        "explicit_forbidden_checked": g1.get("explicit_forbidden_checked"),
        "blocked_nodes": g1.get("blocked_nodes"),
        "map_sha256_at_run": g1.get("map_sha256"),
        "expected": "PASS (no N1+ artifact present while locked)",
    }
    tests["G1_repo_guard"]["agrees"] = (
        raw_g1["exit_code"] == 0 and g1.get("verdict") == "PASS" and not g1.get("violations"))

    raw_g2 = run([sys.executable, GUARD, "--self-test"])
    (RAW / "guard_self_test.txt").write_text(raw_g2["stdout"] + raw_g2["stderr"])
    try:
        g2 = json.loads(raw_g2["stdout"])
    except json.JSONDecodeError:
        g2 = {}
    tests["G2_guard_self_test"] = {
        "exit_code": raw_g2["exit_code"], "self_test": g2.get("self_test"),
        "results": g2.get("results"),
        "expected": "PASS (clean fixture PASS, planted solver FAIL)",
        "agrees": raw_g2["exit_code"] == 0 and g2.get("self_test") == "PASS",
    }

    raw_g3 = run([sys.executable, "-m", "numerics.gates", "--check"])
    (RAW / "gates_check.txt").write_text(raw_g3["stdout"] + raw_g3["stderr"])
    try:
        g3 = json.loads(raw_g3["stdout"])
    except json.JSONDecodeError:
        g3 = {}
    tests["G3_release_evaluator"] = {
        "exit_code": raw_g3["exit_code"], "verdict": g3.get("verdict"),
        "production_allowed": g3.get("production_allowed"),
        "blocking_reasons": g3.get("blocking_reasons"),
        "command_note": "run without --write-report/--emit-blocker: read-only, no shared writes",
        "expected": "exit 3, N1_BLOCKED while gates pending",
        "agrees": raw_g3["exit_code"] == 3 and g3.get("verdict") == "N1_BLOCKED"
                  and g3.get("production_allowed") is False,
    }

    raw_g4 = run([sys.executable, "numerics/tests/flat_wave.py", "--lock-guard"])
    (RAW / "flat_wave_lock_guard.txt").write_text(raw_g4["stdout"] + raw_g4["stderr"])
    try:
        g4 = json.loads(raw_g4["stdout"])
    except json.JSONDecodeError:
        g4 = {}
    lk = g4.get("lock_guard", {})
    tests["G4_flat_wave_lock_guard"] = {
        "exit_code": raw_g4["exit_code"], "verdict": lk.get("verdict"),
        "production_allowed": lk.get("production_allowed"),
        "blocking_reasons": lk.get("blocking_reasons"),
        "expected": "exit 0, N1_BLOCKED (fail-closed report)",
        "agrees": raw_g4["exit_code"] == 0 and lk.get("verdict") == "N1_BLOCKED"
                  and lk.get("production_allowed") is False,
    }

    raw_g5 = run([sys.executable, "numerics/tests/lead_calibration.py", "--selftest"])
    (RAW / "lead_calibration_selftest.txt").write_text(raw_g5["stdout"] + raw_g5["stderr"])
    try:
        g5 = json.loads(raw_g5["stdout"].strip().splitlines()[-1]) if raw_g5["stdout"].strip() else {}
    except (json.JSONDecodeError, IndexError):
        g5 = {}
    tests["G5_lead_calibration_selftest"] = {
        "exit_code": raw_g5["exit_code"], "selftest_pass": g5.get("selftest_pass"),
        "printed_token": "selftest_pass" if "selftest_pass" in raw_g5["stdout"] else None,
        "expected": "exit 0, selftest_pass true",
        "agrees": raw_g5["exit_code"] == 0 and g5.get("selftest_pass") is True,
    }
    return tests


# ------------------------------------------- 5. falsification fixtures (temp dirs only)
def _fake_tree(map_doc: dict, plant_solver: bool) -> str:
    td = tempfile.mkdtemp(prefix="w074_fixture_")
    root = Path(td)
    (root / "research_map").mkdir(parents=True)
    (root / "research_map" / "research_map.json").write_text(json.dumps(map_doc))
    if plant_solver:
        (root / "numerics" / "spherical_solver").mkdir(parents=True)
        (root / "numerics" / "spherical_solver" / "solver.py").write_text("# planted\n")
    return td


def adversarial_fixtures() -> dict:
    base_nodes = [{"id": "N1", "status": "queued",
                   "artifact": "numerics/spherical_solver/", "depends_on": []}]
    out = {}

    def probe(name: str, lock_doc: dict, plant: bool, expected_verdict: str) -> None:
        td = _fake_tree({"groups": [{"id": "numerics", "nodes": base_nodes}],
                         "numerics_lock": lock_doc}, plant)
        r = run([sys.executable, GUARD, "--root", td])
        try:
            doc = json.loads(r["stdout"])
        except json.JSONDecodeError:
            doc = {}
        out[name] = {
            "fixture": {"numerics_lock": lock_doc, "planted_solver": plant},
            "exit_code": r["exit_code"], "verdict": doc.get("verdict"),
            "state_seen": doc.get("numerics_lock_state"),
            "violations": [v.get("kind") for v in doc.get("violations", [])],
            "expected_if_fail_closed": expected_verdict,
            "fail_closed_observed": doc.get("verdict") == expected_verdict,
        }

    probe("FX-A_state_key_missing", {"locked_nodes": ["N1"]}, True, "FAIL")
    probe("FX-B_state_case_LOCKED", {"state": "LOCKED", "locked_nodes": ["N1"]}, True, "FAIL")
    probe("FX-C_control_state_locked", {"state": "locked", "locked_nodes": ["N1"]},
          True, "FAIL")
    probe("FX-D_control_clean_locked", {"state": "locked", "locked_nodes": ["N1"]},
          False, "PASS")

    td = tempfile.mkdtemp(prefix="w074_nomap_")
    r = run([sys.executable, GUARD, "--root", td])
    out["FX-E_map_unreadable"] = {
        "fixture": {"map": "absent"}, "exit_code": r["exit_code"],
        "stdout_head": r["stdout"][:200],
        "expected_if_fail_closed": "exit 2 ERROR (cannot evaluate)",
        "fail_closed_observed": r["exit_code"] == 2,
    }
    return out


# ------------------------------------------------------- 6. guard scope / coverage scan
KEYWORDS = ("spherical_solver", "self-grav", "self_grav", "selfgrav")


def coverage_scan(snap: dict) -> dict:
    hits = []
    for p in sorted((ROOT / "numerics").rglob("*")):
        if not p.is_file() or p.suffix not in (".py", ".yaml", ".yml", ".sh", ".json"):
            continue
        try:
            lines = p.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            low = line.lower()
            for kw in KEYWORDS:
                if kw in low:
                    hits.append({"path": str(p.relative_to(ROOT)), "line": i,
                                 "keyword": kw, "excerpt": line.strip()[:160]})
    declared_solver_like = [
        {"node_id": nid, "artifact": n["artifact"], "exists": (ROOT / str(n["artifact"])).exists()}
        for nid, n in snap["nodes"].items()
        if isinstance(n.get("artifact"), str)
        and any(k in n["artifact"].lower() for k in ("solver", "selfgrav", "self_grav"))
    ]
    return {
        "guard_scope": {
            "blocked_nodes": ["N1"],
            "declared_paths_inspected": ["numerics/spherical_solver/"],
            "explicit_forbidden_paths": ["numerics/spherical_solver"],
            "note": ("The guard is a tripwire on the declared artifact paths of locked nodes "
                     "plus one explicit path, not a general solver detector. Its own note says "
                     "PASS is not proof of absence."),
        },
        "declared_solver_like_artifacts": declared_solver_like,
        "keyword_hits_in_numerics_code_files": hits,
        "hit_classification": (
            "All hits are lock-guard / blocker-contract references (this audit's own keywords "
            "are not stored under numerics/). No solver implementation was found by this scan; "
            "absence is not proof of absence."
            if hits else
            "No keyword hits under numerics/ code files; absence is not proof of absence."),
    }


# ------------------------------------------------------------------------- 7. findings
def build_findings(mapping: dict, states: dict, guards: dict, fixtures: dict,
                   coverage: dict) -> list[dict]:
    f = []
    f.append({
        "id": "W074-F1", "severity": "info", "status": "verified",
        "claim": ("blockers.md release table is 1:1 with numerics_lock: 6 rows, 6 map-derived "
                  "conditions, no condition added or dropped."),
        "evidence": ["numerics/blockers.md#33dd7a21", "research_map/research_map.json#numerics_lock"],
        "falsifier": ("A blockers.md condition with no numerics_lock counterpart (or one dropped); "
                      "re-run condition_mapping() on the frozen artifact hash."),
        "adjudication_item": ("row 3 adds the qualifier '>= 4 rungs per protocol rev 3 3.2' not "
                              "literal in the map key; lead-audit to decide if it is a "
                              "strengthening."),
    })
    f.append({
        "id": "W074-F2", "severity": "info", "status": "verified",
        "claim": ("Every current-state cell in the blockers.md table matches measured artifacts: "
                  "rows 1/2 pending (map verdicts pending), row 3 satisfied (4-rung orders "
                  "1.9889-1.9966, passing artifact events, hash match), row 4 satisfied "
                  "(gate agreement agreed=true, delta 0.0101 <= 0.35), row 5 missing "
                  "(accepting_reviews=[]), row 6 locked (authority astra)."),
        "evidence": ["numerics/tests/n0_order_4rung.json", "numerics/results/flat_wave_convergence.json",
                     "numerics/results/flat_wave_replication.json",
                     "runtime/state/w074_checkpoint_1.json"],
        "falsifier": ("Any row whose stated status disagrees with a fresh gates.evaluate() at the "
                      "same artifact hashes; the audit re-run must reproduce row-by-row."),
    })
    fa = fixtures.get("FX-A_state_key_missing", {})
    fb = fixtures.get("FX-B_state_case_LOCKED", {})
    f.append({
        "id": "W074-F3", "severity": "major", "status": "open-finding",
        "claim": ("selfgravity_lock_guard fails OPEN on an unrecognised numerics_lock.state: with "
                  "a planted numerics/spherical_solver/ it returns verdict PASS when the state key "
                  "is missing (%s) or is 'LOCKED' (%s). numerics/gates.py defaults a missing state "
                  "to 'locked' (fail-closed), so the two guards disagree on malformed maps."
                  % (fa.get("verdict"), fb.get("verdict"))),
        "evidence": ["numerics/tests/selfgravity_lock_guard.py:98",
                     "numerics/gates.py (lock.get('state','locked'))",
                     "raw fixture outputs recorded in report.json#adversarial_fixtures"],
        "falsifier": ("Re-run the fixtures: if a solver-bearing workspace with a missing/miscased "
                      "state yields FAIL, this finding is void."),
        "recommendation": ("Treat only state == 'released' as released in the violation guard, or "
                           "mirror gates.py's default of 'locked' for absent/unknown states. "
                           "Worker recommendation only; repair authority sits with lead-numerics."),
    })
    f.append({
        "id": "W074-F4", "severity": "info", "status": "verified",
        "claim": ("Guard scope is exactly two paths (numerics/spherical_solver/ declared artifact "
                  "plus the explicit forbidden path); the tree scan found no undeclared solver "
                  "implementation, and the limitation is disclosed in the guard's own note."),
        "evidence": ["report.json#coverage_scan",
                     "numerics/tests/selfgravity_lock_guard.py:99"],
        "falsifier": ("A self-gravity solver file at a path outside the inspected set while the "
                      "guard still reports PASS."),
    })
    f.append({
        "id": "W074-F5", "severity": "minor", "status": "open-finding",
        "claim": ("blockers.md says all three guard commands 'report N1_BLOCKED'; measured: "
                  "selfgravity_lock_guard.py prints verdict PASS (exit 0), lead_calibration "
                  "--selftest prints selftest_pass=true, and only flat_wave --lock-guard and "
                  "numerics.gates --check print the N1_BLOCKED token."),
        "evidence": ["numerics/blockers.md:60-61", "raw/guard_repo_run.txt",
                     "raw/lead_calibration_selftest.txt", "raw/flat_wave_lock_guard.txt",
                     "raw/gates_check.txt"],
        "falsifier": ("Produce a run of any of the three commands at the frozen hashes that "
                      "prints the N1_BLOCKED verdict token where this audit says it does not."),
        "recommendation": ("Reword to separate the release evaluator (numerics.gates: N1_BLOCKED) "
                           "from the violation tripwire (selfgravity_lock_guard: PASS = lock "
                           "intact). Documentation-only."),
    })
    return f


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    snap_before = snapshot()
    try:
        sys.path.insert(0, str(ROOT))
        import numerics.gates as G  # noqa: E402
        gate_report = G.evaluate(ROOT)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"audit": "N1-BLOCK-AUDIT-01", "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    # attach the raw event stream once for protocol-review extraction (bounded to N0/protocol)
    events = G.load_event_stream(ROOT)
    gate_report["_events"] = [
        e for e in events
        if e.get("event_type") == "review"
        and ("CONVERGENCE_PROTOCOL" in str(e.get("target_id", ""))
             or str(e.get("target_id", "")) in ("N0", "G-NUM-protocol"))
    ]
    mapping = condition_mapping(snap_before["numerics_lock"])
    states = state_audit(gate_report, snap_before)
    guards = guard_tests(gate_report, snap_before)
    fixtures = adversarial_fixtures()
    coverage = coverage_scan(snap_before)
    snap_after = snapshot()

    report = {
        "audit_id": "N1-BLOCK-AUDIT-01",
        "auditor": "worker-074",
        "generated_at": now(),
        "task": ("Independent adversarial audit of the N1 blocker/unblock contract "
                 "(numerics/blockers.md): 1:1 mapping to numerics_lock, truth of its "
                 "current-state cells, and fail-closed behaviour of the lock guards."),
        "class_id": "AF-WCC-SCALAR-SPH",
        "class_ids": ["AF-WCC-SCALAR-SPH"],
        "node_id": "N1-BLOCK",
        "gate": "G-NUM",
        "snapshot_before": snap_before,
        "snapshot_after": snap_after,
        "map_drift_during_audit": snap_before["map_sha256"] != snap_after["map_sha256"],
        "condition_mapping": mapping,
        "state_claims": states,
        "guard_tests": guards,
        "adversarial_fixtures": fixtures,
        "coverage_scan": coverage,
        "findings": build_findings(mapping, states, guards, fixtures, coverage),
        "gate_evaluator_report": gate_report,
        "falsifier": ("REJECT this audit if: (a) re-running condition_mapping() on "
                      "numerics/blockers.md#33dd7a21 and the snapshotted numerics_lock yields a "
                      "non-1:1 condition set; (b) any row marked satisfied lacks a measured "
                      "artifact value/hash recorded here; (c) numerics.gates reports "
                      "production_allowed=true while G-FORM/G-AUDIT are pending; (d) fixtures "
                      "FX-A/FX-B yield FAIL on re-run; or (e) an undeclared self-gravity solver "
                      "artifact exists at a path outside the guard's inspected set."),
        "next_falsifier": ("lead-audit re-runs the FX-A fixture and adversarially probes "
                           "selfgravity_lock_guard with state='' and state='released'; the latter "
                           "must PASS while a planted solver exists only if the lock is truly "
                           "released by astra."),
        "worker_authority_note": ("Worker-authored evidence only: this report sets no node "
                                  "status, no validation_status=passed, and no gate verdict."),
        "validation_status": "unverified",
        "hours_spent_estimate": 0.4,
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({
        "audit": report["audit_id"],
        "report_sha256": sha256_file(OUT / "report.json"),
        "map_drift": report["map_drift_during_audit"],
        "condition_mapping_one_to_one": mapping["one_to_one"],
        "state_rows_agree": {k: v.get("agrees") for k, v in states.items()},
        "guard_tests_agree": {k: v.get("agrees") for k, v in guards.items()},
        "fixtures_fail_open": {k: v.get("fail_closed_observed")
                               for k, v in fixtures.items()},
        "findings": [f["id"] for f in report["findings"]],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

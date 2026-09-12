#!/usr/bin/env python3
"""W16-REV29-CORPUS-REBIND-01 (worker-016; classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN /
AF-SCC-C0-VAC-GEN; node F1; gate G-FORM).

Open item addressed (B4 in worker-069's W069-LIFE05-REC12-REPAIR-COVERAGE-01 and the
residual W16R28-F1 of worker-16): at FROZEN revision 29 the frozen two-stage acceptance
record `artifacts/formulation/evidence/semantic_escape_rebased.json` still binds
`base_sha256 = 1bb78ce9...` while the frozen C0 is `b2ab6acb...`, so
`run_acceptance.py` fails closed in preflight (exit 3) and no two-stage measurement binds
the frozen schemas. This pass regenerates the corpus in an isolated stage mirror and
re-runs the acceptance pipeline at the frozen bytes.

Phase B additionally measures W16R28-F3: the `gate_test_report.json` pin is
absolute-run-root dependent, because the report embeds absolute fixture paths.

Discipline: read-only on every shared/frozen path; all writes are under
artifacts/worker-16/rev29_rebind/. Worker evidence only: no gate verdict, no node status.

Usage:
    python3 run_rebind_rev29.py                 # phase A
    python3 run_rebind_rev29.py --with-gate-probe   # phase A + phase B
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STAGE = HERE / "stage"
OUT = HERE / "out"
SNAP = HERE / "snapshot_at_start.json"

INPUTS = [
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/VOCAB_ALIASES.json",
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/tools/measure_semantic_escape.py",
    "artifacts/formulation/tools/run_acceptance.py",
    "artifacts/worker-06/spec_conformance_audit.py",
    "artifacts/worker-06/semantic_fixtures/manifest.json",
]
FROZEN_EVIDENCE = "artifacts/formulation/evidence/semantic_escape_rebased.json"
FROZEN_REPORT = "artifacts/formulation/evidence/acceptance_pipeline_report.json"
FROZEN_GATE_REPORT = "artifacts/formulation/evidence/gate_test_report.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def read_json(p: Path):
    return json.loads(Path(p).read_text())


def run(cmd: list[str], cwd: Path | None = None) -> dict:
    r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    return {"cmd": [str(c) for c in cmd], "returncode": r.returncode,
            "stdout": r.stdout, "stderr": r.stderr}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load_pins() -> tuple[dict, dict]:
    snap = read_json(SNAP)
    pins = {p: v["sha256"] for p, v in snap["paths"].items()}
    return snap, pins


def drift_vs_snapshot(pins: dict) -> list[dict]:
    drift = []
    for p, h in pins.items():
        live = sha256(ROOT / p) if (ROOT / p).exists() else None
        if live != h:
            drift.append({"path": p, "snapshot": h, "live": live})
    return drift


def build_stage(pins: dict) -> list[dict]:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    rows = []
    for rel in INPUTS:
        src, dst = ROOT / rel, STAGE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        h = sha256(dst)
        rows.append({"path": rel, "bytes": dst.stat().st_size, "sha256": h,
                     "snapshot": pins.get(rel), "match": h == pins.get(rel)})
    (STAGE / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    (STAGE / "artifacts/worker-06/semantic_fixtures").mkdir(parents=True, exist_ok=True)
    return rows


def phase_a() -> dict:
    snap, pins = load_pins()
    OUT.mkdir(parents=True, exist_ok=True)
    res: dict = {
        "task_id": "W16-REV29-CORPUS-REBIND-01",
        "worker": "worker-16",
        "worker_slot": "worker-016",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F1",
        "gate": "G-FORM",
        "created_at": now(),
        "authority_note": ("worker evidence only; cannot set validation_status=passed, node "
                           "status=done, or a gate verdict"),
        "read_only_discipline": ("every write under artifacts/worker-16/rev29_rebind/; no shared or "
                                 "frozen artifact modified"),
        "snapshot": {"frozen_revision": snap["frozen"]["revision"],
                     "frozen_sha256": snap["frozen"]["self_sha256"],
                     "frozen_at": snap["frozen"]["frozen_at"],
                     "frozen_files": snap["frozen"]["files_count"]},
        "pins": pins,
    }

    # snapshot drift at start (fail closed)
    start_drift = drift_vs_snapshot(pins)
    res["snapshot_drift_at_start"] = start_drift
    res["snapshot_stable_at_start"] = not start_drift
    if start_drift:
        res["aborted"] = "live bytes differ from snapshot_at_start.json; re-snapshot first"
        (OUT / "rebind_result_rev29.json").write_text(json.dumps(res, indent=2) + "\n")
        return res

    # --- 0. verify_frozen.py read-only -----------------------------------------------------
    vf = run([sys.executable, "artifacts/formulation/tools/verify_frozen.py"], cwd=ROOT)
    res["verify_frozen"] = {"returncode": vf["returncode"],
                            "stdout": vf["stdout"], "stderr": vf["stderr"]}

    # --- 1. reproduce the frozen-bytes preflight failure read-only -------------------------
    # Run in an isolated copy of the CURRENT live tree, not at ROOT: even if preflight were
    # to pass unexpectedly, run_acceptance.py would write its report inside the probe copy,
    # so no shared/frozen path can be touched by this pass.
    pre = HERE / "preflight_probe"
    if pre.exists():
        shutil.rmtree(pre)
    for rel in INPUTS:
        dst = pre / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    for rel in (FROZEN_EVIDENCE, FROZEN_REPORT):
        dst = pre / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    ev_before = sha256(ROOT / FROZEN_EVIDENCE)
    r = run([sys.executable, "artifacts/formulation/tools/run_acceptance.py"], cwd=pre)
    res["before"] = {
        "frozen_evidence_sha256": ev_before,
        "frozen_evidence_sha256_after_probe": sha256(ROOT / FROZEN_EVIDENCE),
        "frozen_evidence_base_sha256": read_json(ROOT / FROZEN_EVIDENCE).get("base_sha256"),
        "current_c0_sha256": sha256(ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
        "frozen_report_sha256": sha256(ROOT / FROZEN_REPORT),
        "probe_root": str(pre),
        "run_acceptance_returncode": r["returncode"],
        "run_acceptance_stdout": r["stdout"],
        "run_acceptance_stderr": r["stderr"],
    }
    res["before"]["shared_evidence_untouched"] = (
        res["before"]["frozen_evidence_sha256"] == res["before"]["frozen_evidence_sha256_after_probe"])
    (OUT / "before_run_acceptance.stdout.txt").write_text(r["stdout"] + r["stderr"])

    # --- 2. staged mirror + integrity ------------------------------------------------------
    res["staged_inputs"] = build_stage(pins)
    res["staged_inputs_all_match"] = all(x["match"] for x in res["staged_inputs"])
    if not res["staged_inputs_all_match"]:
        res["aborted"] = "staged input hash mismatch"
        (OUT / "rebind_result_rev29.json").write_text(json.dumps(res, indent=2) + "\n")
        return res
    frozen_files = read_json(ROOT / "artifacts/formulation/FROZEN.json")["files"]
    xcheck = []
    for rel in INPUTS:
        if rel in frozen_files:
            xcheck.append({"path": rel,
                           "frozen_manifest_sha256": frozen_files[rel]["sha256"],
                           "pinned_match": frozen_files[rel]["sha256"] == pins.get(rel)})
    res["frozen_manifest_crosscheck"] = xcheck
    res["frozen_manifest_crosscheck_all_match"] = all(x["pinned_match"] for x in xcheck)

    # --- 3. rebase in stage, twice (determinism) -------------------------------------------
    runs = []
    for i in (1, 2):
        rr = run([sys.executable, "artifacts/formulation/tools/measure_semantic_escape.py"], cwd=STAGE)
        ev = STAGE / FROZEN_EVIDENCE
        (OUT / f"measure_run{i}.stdout.txt").write_text(rr["stdout"] + rr["stderr"])
        runs.append({"run": i, "returncode": rr["returncode"],
                     "stdout": rr["stdout"], "stderr": rr["stderr"],
                     "evidence_sha256": sha256(ev) if ev.exists() else None})
    res["rebased_runs"] = runs
    res["rebased_deterministic"] = runs[0]["evidence_sha256"] == runs[1]["evidence_sha256"]
    rebased_path = STAGE / FROZEN_EVIDENCE
    res["after_rebased_evidence_sha256"] = sha256(rebased_path)
    res["after_rebased_evidence_bytes"] = rebased_path.stat().st_size
    rebased = read_json(rebased_path)
    res["after_summary"] = rebased.get("summary")
    res["after_base_sha256"] = rebased.get("base_sha256")
    res["after_w06_sha256"] = rebased.get("w06_sha256")
    res["after_gate_sha256"] = rebased.get("gate_sha256")
    res["after_controls"] = rebased.get("controls")
    res["unparsed_mutations"] = rebased.get("unparsed_mutations")
    res["canonical_escape_fixtures"] = [m["fixture"] for m in rebased["mutants"] if m.get("canonical_escape")]
    res["w06_escape_fixtures"] = [m["fixture"] for m in rebased["mutants"] if m.get("w06_escape")]
    res["rebased_preflight_ok"] = res["after_base_sha256"] == res["before"]["current_c0_sha256"]

    # --- 4. acceptance pipeline in stage ---------------------------------------------------
    acc = run([sys.executable, "artifacts/formulation/tools/run_acceptance.py"], cwd=STAGE)
    (OUT / "after_run_acceptance.stdout.txt").write_text(acc["stdout"] + acc["stderr"])
    accj = run([sys.executable, "artifacts/formulation/tools/run_acceptance.py", "--json"], cwd=STAGE)
    rep_path = STAGE / FROZEN_REPORT
    res["after_run_acceptance"] = {
        "returncode": acc["returncode"], "stdout": acc["stdout"], "stderr": acc["stderr"],
        "report_sha256": sha256(rep_path) if rep_path.exists() else None,
        "report_bytes": rep_path.stat().st_size if rep_path.exists() else None,
        "json_returncode": accj["returncode"], "json_stdout": accj["stdout"][:4000],
    }
    if rep_path.exists():
        res["after_report"] = read_json(rep_path)
        shutil.copy2(rep_path, OUT / "acceptance_pipeline_report.json")
    shutil.copy2(rebased_path, OUT / "semantic_escape_rebased.json")

    # --- 4b. first-hand raw stage verdicts -------------------------------------------------
    raw = {"structural": [], "semantic": []}
    for name in ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml"):
        p = STAGE / "artifacts/formulation/schemas" / name
        g = run([sys.executable, "artifacts/formulation/tools/check_class_schema.py", "--json", str(p)], cwd=STAGE)
        s = run([sys.executable, "artifacts/worker-06/spec_conformance_audit.py", str(p)], cwd=STAGE)
        raw["structural"].append({"schema": name, "returncode": g["returncode"],
                                  "stdout": g["stdout"], "stderr": g["stderr"]})
        raw["semantic"].append({"schema": name, "returncode": s["returncode"],
                                "stdout": s["stdout"], "stderr": s["stderr"]})
    (OUT / "raw_verdicts.json").write_text(json.dumps(raw, indent=2) + "\n")
    res["raw_verdicts_sha256"] = sha256(OUT / "raw_verdicts.json")
    res["f1_semantic_failed_rules"] = []
    for row in raw["semantic"]:
        if row["schema"] == "af_wcc_vacuum.yaml":
            try:
                res["f1_semantic_failed_rules"] = json.loads(row["stdout"]).get("failed_rules", [])
            except Exception:  # noqa: BLE001
                res["f1_semantic_failed_rules"] = ["unparsed"]

    # --- 5. end drift check ----------------------------------------------------------------
    end_drift = drift_vs_snapshot(pins)
    res["snapshot_drift_at_end"] = end_drift
    res["snapshot_stable_through_pass"] = not end_drift

    res["resolved"] = {
        "B4_preflight_regenerated": res["rebased_preflight_ok"] and res["rebased_deterministic"],
        "existing_frozen_record_superseded": True,
    }
    res["residual_open"] = {
        "adoption": ("frozen evidence paths NOT modified; lead must adopt the staged bytes or "
                     "re-run the sanctioned tool in place and bump the FROZEN revision"),
        "W16R28-F2_R03": "canonical F1 stage-2 R03 disposition (lead/controller Option A/B)",
        "W16R28-F3": "location-dependent gate_test_report hash (measured in phase B)",
        "W16R28-F4": "freeze discipline / post-freeze drift",
    }
    res["falsifier"] = (
        "Refute by: (a) a run_acceptance.py exit 0 at the frozen bytes with the current frozen "
        "evidence and unpatched tools (no rebase needed); (b) staged inputs differing from the "
        "pinned FROZEN rev29 hashes; (c) two staged measure_semantic_escape.py runs yielding "
        "different sha256; (d) the rebased corpus applying a different mutation set than manifest "
        "c102445df397; (e) any per-mutant verdict diff between the 1bb78ce9 and b2ab6acb corpora.")

    (OUT / "rebind_result_rev29.json").write_text(json.dumps(res, indent=2) + "\n")
    return res


def phase_b() -> dict:
    """W16R28-F3: prove `gate_test_report.json` content (hence its sha256 pin) depends on the
    absolute run root, by running the frozen gate-test tool on two byte-identical copies of
    artifacts/formulation placed at two different absolute paths."""
    res: dict = {"task_id": "W16-REV29-GATEPATH-01", "created_at": now(),
                 "falsifier": ("Refute if the two reports are byte-identical, or if their parsed "
                               "JSON differs after replacing each own absolute root with <ROOT>.")}
    norm_objs, raw_hashes, norm_hashes = {}, {}, {}
    for tag in ("probe_a", "probe_b"):
        dest = HERE / tag
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(ROOT / "artifacts/formulation", dest / "artifacts/formulation")
        (dest / "research_map").mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "research_map/formulation_taxonomy.yaml",
                     dest / "research_map/formulation_taxonomy.yaml")
        r = run([sys.executable, "artifacts/formulation/tools/run_gate_tests.py"], cwd=dest)
        rep = dest / FROZEN_GATE_REPORT
        raw = rep.read_text() if rep.exists() else ""
        d = json.loads(raw) if raw else {}
        norm_objs[tag] = json.loads(raw.replace(str(dest), "<ROOT>")) if raw else None
        raw_hashes[tag] = sha256_text(raw)
        norm_hashes[tag] = sha256_text(json.dumps(norm_objs[tag], sort_keys=True))
        res[tag] = {
            "root": str(dest), "returncode": r["returncode"], "report_sha256": raw_hashes[tag],
            "verdict": d.get("verdict"), "counts": d.get("counts"),
            "abs_path_hits": sum(1 for line in raw.splitlines() if str(dest) in line),
            "stdout_tail": "\n".join(r["stdout"].splitlines()[:6]),
        }
    res["raw_reports_differ"] = raw_hashes["probe_a"] != raw_hashes["probe_b"]
    res["normalized_json_identical"] = norm_objs["probe_a"] == norm_objs["probe_b"]
    res["normalized_hashes"] = norm_hashes
    live_gate = ROOT / FROZEN_GATE_REPORT
    live_norm = live_gate.read_text().replace(str(ROOT), "<ROOT>")
    res["frozen_gate_report_sha256"] = sha256(live_gate)
    res["frozen_gate_report_normalized_equals_probe"] = sha256_text(
        json.dumps(json.loads(live_norm), sort_keys=True)) == norm_hashes["probe_a"]
    res["finding"] = ("CONFIRMED" if res["raw_reports_differ"] and res["normalized_json_identical"]
                      else "NOT_CONFIRMED")
    (OUT / "gate_path_probe.json").write_text(json.dumps(res, indent=2) + "\n")
    return res


def main() -> int:
    res = phase_a()
    print(json.dumps({
        "frozen": res.get("snapshot"),
        "before_run_acceptance_rc": res.get("before", {}).get("run_acceptance_returncode"),
        "frozen_evidence_base": res.get("before", {}).get("frozen_evidence_base_sha256", "")[:12],
        "frozen_c0": res.get("before", {}).get("current_c0_sha256", "")[:12],
        "staged_inputs_all_match": res.get("staged_inputs_all_match"),
        "rebased_deterministic": res.get("rebased_deterministic"),
        "after_base_sha256": (res.get("after_base_sha256") or "")[:12],
        "after_summary": res.get("after_summary"),
        "after_run_acceptance_rc": res.get("after_run_acceptance", {}).get("returncode"),
        "after_verdict": res.get("after_report", {}).get("verdict"),
        "f1_semantic_failed_rules": res.get("f1_semantic_failed_rules"),
        "snapshot_stable_through_pass": res.get("snapshot_stable_through_pass"),
        "end_drift": res.get("snapshot_drift_at_end"),
        "verify_frozen_rc": res.get("verify_frozen", {}).get("returncode"),
        "verify_frozen_out": (res.get("verify_frozen", {}).get("stdout") or "").splitlines()[:6],
    }, indent=2))
    if "--with-gate-probe" in sys.argv:
        pb = phase_b()
        print(json.dumps({k: pb[k] for k in ("finding", "raw_reports_differ",
                                             "normalized_json_identical", "probe_a", "probe_b")},
                         indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

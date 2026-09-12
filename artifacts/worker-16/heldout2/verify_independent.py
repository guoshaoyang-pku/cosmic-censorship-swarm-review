#!/usr/bin/env python3
"""Independent replication of the FORM-HELDOUT-08 frozen measurement (worker-16, second pass).

This does NOT touch the frozen corpus or the frozen report.  It re-runs the two bound
stage tools on every fixture recorded in manifest.json and compares the fresh verdicts,
escape flags, aggregates and escape-family list against the frozen raw_verdicts.json and
report.json.

Run:  python3 artifacts/worker-16/heldout2/verify_independent.py
Out:  artifacts/worker-16/heldout2/verify/reproduce.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST = HERE / "manifest.json"
FROZEN_RAW = HERE / "raw_verdicts.json"
FROZEN_REPORT = HERE / "report.json"
STRUCT_GATE = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
SEM_GATE = ROOT / "artifacts" / "worker-06" / "spec_conformance_audit.py"
OUT = HERE / "verify" / "reproduce.json"
CST = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_stage_a(target: Path):
    proc = subprocess.run([sys.executable, str(STRUCT_GATE), "--json", str(target)],
                          capture_output=True, text=True, timeout=300)
    try:
        rep = json.loads(proc.stdout[proc.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        rep = {}
    return {"exit": proc.returncode, "verdict": rep.get("verdict"),
            "escaped": proc.returncode == 0 and rep.get("verdict") == "pass",
            "failed_rules": rep.get("failed_rules", [])}


def run_stage_b(target: Path):
    proc = subprocess.run([sys.executable, str(SEM_GATE), str(target)],
                          capture_output=True, text=True, timeout=300)
    try:
        rep = json.loads(proc.stdout[proc.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        rep = {}
    verdict = rep.get("verdict")
    escaped = (verdict == "accept") if verdict else (proc.returncode == 0)
    return {"exit": proc.returncode, "verdict": verdict, "escaped": escaped}


def main() -> int:
    manifest_sha = sha(MANIFEST)                      # hashed before any stage run
    manifest = json.loads(MANIFEST.read_text())
    frozen_raw = json.loads(FROZEN_RAW.read_text())
    frozen_report = json.loads(FROZEN_REPORT.read_text())

    tampered = []
    for e in manifest["mutants"] + manifest["controls"]:
        if sha(ROOT / e["path"]) != e["sha256"]:
            tampered.append(e["fixture"])
    for b in manifest["bases"].values():
        if sha(ROOT / b["path"]) != b["sha256"]:
            tampered.append(b["path"])

    frozen_manifest_sha = frozen_raw["manifest_sha256_before_run"]
    manifest_unchanged = manifest_sha == frozen_manifest_sha

    # ---- controls -----------------------------------------------------------
    fresh_controls, control_mismatch = [], []
    frozen_ctrl = {c["fixture"]: c for c in frozen_raw["controls"]}
    for e in manifest["controls"]:
        a, b = run_stage_a(ROOT / e["path"]), run_stage_b(ROOT / e["path"])
        row = {"fixture": e["fixture"], "kind": e["kind"], "class_id": e["class_id"],
               "stage_a": a, "stage_b": b, "accepted_both": a["escaped"] and b["escaped"]}
        fresh_controls.append(row)
        f = frozen_ctrl.get(e["fixture"], {})
        if (f.get("stage_a", {}).get("verdict"), f.get("stage_b", {}).get("verdict"),
                f.get("accepted_both")) != (a["verdict"], b["verdict"], row["accepted_both"]):
            control_mismatch.append(e["fixture"])
    for rel in manifest["frozen_canonical_controls"]:
        a, b = run_stage_a(ROOT / rel), run_stage_b(ROOT / rel)
        name = Path(rel).name
        row = {"fixture": name, "kind": "frozen-canonical", "path": rel,
               "stage_a": a, "stage_b": b, "accepted_both": a["escaped"] and b["escaped"]}
        fresh_controls.append(row)
        f = frozen_ctrl.get(name, {})
        if (f.get("stage_a", {}).get("verdict"), f.get("stage_b", {}).get("verdict"),
                f.get("accepted_both")) != (a["verdict"], b["verdict"], row["accepted_both"]):
            control_mismatch.append(name)
    controls_ok = all(c["accepted_both"] for c in fresh_controls) and not tampered

    # ---- mutants ------------------------------------------------------------
    frozen_res = {r["fixture"]: r for r in frozen_raw["results"]}
    fresh_results, result_mismatch = [], []
    for e in manifest["mutants"]:
        a, b = run_stage_a(ROOT / e["path"]), run_stage_b(ROOT / e["path"])
        row = {"fixture": e["fixture"], "family": e["family"], "rephrased": e["rephrased"],
               "class_id": e.get("class_id"), "mutation_id": e.get("mutation_id"),
               "stage_a": a, "stage_b": b,
               "structural_escape": a["escaped"], "semantic_escape": b["escaped"],
               "union_escape": a["escaped"] and b["escaped"]}
        fresh_results.append(row)
        f = frozen_res.get(e["fixture"], {})
        keys = ("structural_escape", "semantic_escape", "union_escape")
        if (f.get("stage_a", {}).get("verdict") != a["verdict"]
                or f.get("stage_b", {}).get("verdict") != b["verdict"]
                or any(f.get(k) != row[k] for k in keys)):
            result_mismatch.append(e["fixture"])

    n = len(fresh_results)
    esc = [r for r in fresh_results if r["union_escape"]]
    by_family: dict[str, list] = {}
    for r in esc:
        by_family.setdefault(r["family"], []).append(r)
    fresh_families = sorted(
        ({"family": f, "count": len(v), "fixtures": sorted(x["fixture"] for x in v)}
         for f, v in by_family.items()), key=lambda d: d["family"])
    fresh_agg = {
        "structural_escape": round(sum(1 for r in fresh_results if r["structural_escape"]) / n, 4),
        "semantic_escape": round(sum(1 for r in fresh_results if r["semantic_escape"]) / n, 4),
        "union_escape": round(len(esc) / n, 4),
        "structural_caught": n - sum(1 for r in fresh_results if r["structural_escape"]),
        "semantic_caught": n - sum(1 for r in fresh_results if r["semantic_escape"]),
        "union_caught": n - len(esc),
    }
    frozen_families = sorted(
        ({"family": f["family"], "count": f["count"], "fixtures": sorted(f["fixtures"])}
         for f in frozen_report["escape_families"]), key=lambda d: d["family"])
    family_match = fresh_families == frozen_families
    agg_match = fresh_agg == frozen_report["aggregates"]

    checks = {
        "H1_counts": {"mutants": n, "families": len({r["family"] for r in fresh_results}),
                      "rephrased": sum(1 for r in fresh_results if r["rephrased"]),
                      "thresh_ge20_ge10_ge8": n >= 20
                      and len({r["family"] for r in fresh_results}) >= 10
                      and sum(1 for r in fresh_results if r["rephrased"]) >= 8},
        "H2_manifest_unchanged_since_freeze": manifest_unchanged,
        "H5_controls_ok": controls_ok,
        "no_tampered_fixtures": not tampered,
        "frozen_verdicts_reproduced": not result_mismatch,
        "frozen_controls_reproduced": not control_mismatch,
        "aggregates_reproduced": agg_match,
        "escape_families_reproduced": family_match,
        "frozen_report_valid_flag": frozen_report["valid"],
    }
    ok = all(checks.values())

    out = {
        "verification_id": "FORM-HELDOUT-08-REPLICATION-01",
        "replicated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "replicator": "worker-16 (second pass)",
        "subject": {
            "manifest": {"path": "artifacts/worker-16/heldout2/manifest.json", "sha256": manifest_sha},
            "report": {"path": "artifacts/worker-16/heldout2/report.json", "sha256": sha(FROZEN_REPORT)},
            "raw_verdicts": {"path": "artifacts/worker-16/heldout2/raw_verdicts.json", "sha256": sha(FROZEN_RAW)},
        },
        "stage_tools": {
            "structural": {"path": "artifacts/formulation/tools/check_class_schema.py", "sha256": sha(STRUCT_GATE)},
            "semantic": {"path": "artifacts/worker-06/spec_conformance_audit.py", "sha256": sha(SEM_GATE)},
        },
        "method": "re-run both bound stage tools once per fixture; no fixture or frozen artifact was modified; fresh verdicts compared to the frozen ones",
        "checks": checks,
        "replication_ok": ok,
        "fresh_aggregates": fresh_agg,
        "frozen_aggregates": frozen_report["aggregates"],
        "fresh_controls": fresh_controls,
        "mismatches": {"results": result_mismatch, "controls": control_mismatch, "tampered": tampered},
        "fresh_results": fresh_results,
        "note": "the replication is deterministic: stage tools are pure functions of the fixture bytes and their own bound hashes; agreement here is a re-measurement, not a new escape estimate",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"replication_ok={ok} manifest_unchanged={manifest_unchanged} "
          f"controls_ok={controls_ok} mutant_mismatch={len(result_mismatch)} "
          f"control_mismatch={len(control_mismatch)} agg_match={agg_match} fam_match={family_match}")
    print("fresh aggregates:", fresh_agg)
    print("wrote", OUT.relative_to(ROOT), sha(OUT)[:16])
    return 0 if ok else 5


if __name__ == "__main__":
    sys.exit(main())

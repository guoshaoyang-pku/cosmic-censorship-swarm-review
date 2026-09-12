#!/usr/bin/env python3
"""W16-CORPUS-REBIND-01 (worker-016, class-bound AF-SCC-C0-VAC-GEN / F1+F2a+F2b, gate G-FORM).

Open item resolved (stage-side evidence): W16R28-F1.
  Frozen artifacts/formulation/evidence/semantic_escape_rebased.json binds
  base_sha256 1bb78ce9... (superseded C0), so
  artifacts/formulation/tools/run_acceptance.py exits 3 (PREFLIGHT FAIL) at frozen bytes.

Action (sanctioned by the preflight error message itself: "re-run
artifacts/formulation/tools/measure_semantic_escape.py"):
  1. Reproduce the frozen-bytes failure read-only (exit 3, no write happens on that path).
  2. Build an isolated stage mirror of the minimal frozen input tree under
     artifacts/worker-16/corpus_rebind/stage/ and verify every staged input sha256
     against the pinned FROZEN rev28 hashes.
  3. Re-run measure_semantic_escape.py in the stage TWICE (determinism check): apply the
     unchanged corpus manifest to the CURRENT frozen C0.
  4. Re-run run_acceptance.py in the stage; capture exit code, verdict, canonical rows,
     mutant/control counts, union escapes.
  5. Write out/rebind_result.json + raw logs + a sha256 manifest.

Discipline: no shared/frozen artifact is modified; every write is under
artifacts/worker-16/corpus_rebind/. This is worker evidence, not a gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STAGE = HERE / "stage"
OUT = HERE / "out"

# Pinned identities this run binds to (FROZEN revision 28, sha256 of FROZEN.json
# 2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1).
PINNED = {
    "artifacts/formulation/FROZEN.json":
        "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml":
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml":
        "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/KEY_MANIFEST.json":
        "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "artifacts/formulation/VOCAB_ALIASES.json":
        "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/tools/measure_semantic_escape.py":
        "c6e4f9ccce7f68e472338c72dab6d3b84cb85b7ccfa3dd69416b384cdea11272",
    "artifacts/formulation/tools/run_acceptance.py":
        "e544c36d2d168fdf0a9fb19caa333597d8a74a14442b40a356c08004cc9fb4de",
    "artifacts/worker-06/spec_conformance_audit.py":
        "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    "artifacts/worker-06/semantic_fixtures/manifest.json":
        "c102445df3971109101e4d54b609ff1c5bfdf9147ddb1f1b099476a816030deb",
}
FROZEN_EVIDENCE = "artifacts/formulation/evidence/semantic_escape_rebased.json"
FROZEN_REPORT = "artifacts/formulation/evidence/acceptance_pipeline_report.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_json(p: Path):
    return json.loads(p.read_text())


def run(cmd: list[str], cwd: Path | None = None):
    r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    return {"cmd": [str(c) for c in cmd], "returncode": r.returncode,
            "stdout": r.stdout, "stderr": r.stderr}


def build_stage() -> list[dict]:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    rows = []
    copies = [
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
    for rel in copies:
        src = ROOT / rel
        dst = STAGE / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        rows.append({"path": rel, "sha256": sha256(dst), "bytes": dst.stat().st_size,
                     "pinned": PINNED[rel], "match": sha256(dst) == PINNED[rel]})
    (STAGE / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    (STAGE / "artifacts/worker-06/semantic_fixtures").mkdir(parents=True, exist_ok=True)
    return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    result: dict = {
        "task_id": "W16-CORPUS-REBIND-01",
        "worker": "worker-16",
        "worker_slot": "worker-016",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F1",
        "gate": "G-FORM",
        "authority_note": ("worker evidence only; cannot set validation_status=passed, node "
                           "status=done, or a gate verdict"),
        "read_only_discipline": "no shared/frozen artifact modified; all writes under artifacts/worker-16/corpus_rebind/",
    }

    # --- 1. reproduce the frozen-bytes preflight failure read-only -------------------------
    r = run([sys.executable, "artifacts/formulation/tools/run_acceptance.py"], cwd=ROOT)
    result["before"] = {
        "frozen_evidence_path": FROZEN_EVIDENCE,
        "frozen_evidence_sha256": sha256(ROOT / FROZEN_EVIDENCE),
        "frozen_evidence_base_sha256": read_json(ROOT / FROZEN_EVIDENCE).get("base_sha256"),
        "current_c0_sha256": sha256(ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
        "run_acceptance_returncode": r["returncode"],
        "run_acceptance_stdout": r["stdout"],
        "run_acceptance_stderr": r["stderr"],
    }
    (OUT / "before_run_acceptance.stdout.txt").write_text(r["stdout"] + r["stderr"])

    # --- 2. stage mirror + integrity ------------------------------------------------------
    result["staged_inputs"] = build_stage()
    result["staged_inputs_all_match"] = all(x["match"] for x in result["staged_inputs"])
    # cross-check against FROZEN.json's own recorded sha256 for entries it lists
    frozen_files = read_json(ROOT / "artifacts/formulation/FROZEN.json")["files"]
    xcheck = []
    for rel, pinned in PINNED.items():
        if rel in frozen_files:
            xcheck.append({"path": rel, "frozen_manifest_sha256": frozen_files[rel]["sha256"],
                           "pinned_match": frozen_files[rel]["sha256"] == pinned})
    result["frozen_manifest_crosscheck"] = xcheck
    result["frozen_manifest_crosscheck_all_match"] = all(x["pinned_match"] for x in xcheck)

    # --- 3. rebase in stage, twice, for determinism ---------------------------------------
    runs = []
    for i in (1, 2):
        rr = run([sys.executable, "artifacts/formulation/tools/measure_semantic_escape.py"], cwd=STAGE)
        ev = STAGE / "artifacts/formulation/evidence/semantic_escape_rebased.json"
        dest = OUT / f"measure_run{i}.stdout.txt"
        dest.write_text(rr["stdout"] + rr["stderr"])
        runs.append({"run": i, "returncode": rr["returncode"], "stdout": rr["stdout"],
                     "stderr": rr["stderr"], "evidence_sha256": sha256(ev) if ev.exists() else None})
    result["rebased_runs"] = runs
    result["rebased_deterministic"] = runs[0]["evidence_sha256"] == runs[1]["evidence_sha256"]
    rebased_path = STAGE / "artifacts/formulation/evidence/semantic_escape_rebased.json"
    result["after_rebased_evidence_sha256"] = sha256(rebased_path)
    result["after_rebased_evidence_bytes"] = rebased_path.stat().st_size
    rebased = read_json(rebased_path)
    result["after_summary"] = rebased.get("summary")
    result["after_base_sha256"] = rebased.get("base_sha256")
    result["after_w06_sha256"] = rebased.get("w06_sha256")
    result["after_gate_sha256"] = rebased.get("gate_sha256")
    result["after_controls"] = rebased.get("controls")
    result["unparsed_mutations"] = rebased.get("unparsed_mutations")
    result["canonical_escape_fixtures"] = [m["fixture"] for m in rebased["mutants"] if m.get("canonical_escape")]
    result["w06_escape_fixtures"] = [m["fixture"] for m in rebased["mutants"] if m.get("w06_escape")]

    # --- 4. acceptance pipeline in stage --------------------------------------------------
    acc = run([sys.executable, "artifacts/formulation/tools/run_acceptance.py"], cwd=STAGE)
    (OUT / "after_run_acceptance.stdout.txt").write_text(acc["stdout"] + acc["stderr"])
    accj = run([sys.executable, "artifacts/formulation/tools/run_acceptance.py", "--json"], cwd=STAGE)
    rep_path = STAGE / "artifacts/formulation/evidence/acceptance_pipeline_report.json"
    result["after_run_acceptance"] = {
        "returncode": acc["returncode"],
        "stdout": acc["stdout"],
        "stderr": acc["stderr"],
        "report_sha256": sha256(rep_path) if rep_path.exists() else None,
        "report_bytes": rep_path.stat().st_size if rep_path.exists() else None,
        "json_returncode": accj["returncode"],
    }
    if rep_path.exists():
        rep = read_json(rep_path)
        result["after_report"] = rep
        shutil.copy2(rep_path, OUT / "acceptance_pipeline_report.json")
    shutil.copy2(rebased_path, OUT / "semantic_escape_rebased.json")

    # --- 4b. first-hand raw verdicts on the three frozen canonical schemas ----------------
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
    result["raw_verdicts_sha256"] = sha256(OUT / "raw_verdicts.json")
    result["f1_semantic_failed_rules"] = []
    for row in raw["semantic"]:
        if row["schema"] == "af_wcc_vacuum.yaml":
            try:
                result["f1_semantic_failed_rules"] = json.loads(row["stdout"]).get("failed_rules", [])
            except Exception:  # noqa: BLE001
                result["f1_semantic_failed_rules"] = ["unparsed"]

    # residual vs resolved
    result["resolved"] = {
        "W16R28-F1_preflight": (result["after_run_acceptance"]["returncode"] != 3
                                and result["after_base_sha256"] == result["before"]["current_c0_sha256"]),
        "detail": ("stage preflight passed and corpus now binds the frozen C0 hash"
                   if result["after_base_sha256"] == result["before"]["current_c0_sha256"] else "NOT rebased"),
    }
    result["residual_open"] = {
        "W16R28-F2_R03": ("canonical F1 still rejected by stage-2 R03 at frozen bytes (literal-match "
                          "false positive; disposition Option A/B is lead/controller authority)"),
        "W16R28-F3": "location-dependent gate_test_report hash",
        "W16R28-F4": "rev27 freeze discipline observation",
        "adoption": ("frozen evidence paths are NOT modified; lead must adopt the rebased bytes "
                     "(copy from stage or re-run the sanctioned tool) and bump FROZEN revision"),
    }
    result["falsifier"] = (
        "Refute by: (a) a run_acceptance.py exit 0 at the frozen bytes with the current frozen "
        "evidence and unpatched tools (no rebase needed); or (b) showing the staged inputs differ "
        "from the pinned FROZEN rev28 hashes; or (c) re-running the staged measure twice yielding "
        "different semantic_escape_rebased.json sha256; or (d) showing the rebased corpus applies a "
        "different mutation set than manifest.json c102445d (mutant count/ids differ).")

    out = OUT / "rebind_result.json"
    out.write_text(json.dumps(result, indent=2) + "\n")

    print(json.dumps({
        "before_rc": result["before"]["run_acceptance_returncode"],
        "staged_inputs_all_match": result["staged_inputs_all_match"],
        "rebased_deterministic": result["rebased_deterministic"],
        "after_base_sha256": result["after_base_sha256"],
        "after_summary": result["after_summary"],
        "after_run_acceptance_rc": result["after_run_acceptance"]["returncode"],
        "after_verdict": result.get("after_report", {}).get("verdict"),
        "canonical": result.get("after_report", {}).get("canonical"),
        "union_escapes": result.get("after_report", {}).get("mutants", {}).get("union_escapes"),
        "result_sha256": sha256(out),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

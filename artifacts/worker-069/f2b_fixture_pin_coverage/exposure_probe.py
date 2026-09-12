#!/usr/bin/env python3
"""Pin-blind exposure probe for the generated acceptance fixture directory.

Read-only on every canonical path. Executes the PINNED stage tools
(artifacts/formulation/tools/check_class_schema.py and
artifacts/worker-06/spec_conformance_audit.py) over sandbox copies of
artifacts/formulation/evidence/rebased_fixtures/ and computes the exact
corpus-level verdict logic of artifacts/formulation/tools/run_acceptance.py,
for variants that leave every pinned input byte-identical:

  pristine     : copy of the on-disk corpus
  del_mutant   : one mutant file deleted
  mod_mutant   : one mutant replaced by the canonical C0 schema (benign)
  add_extra    : one benign undeclared yaml added
  del_control  : (exploratory) one control file deleted

The `run()` helper is imported from the pinned run_acceptance.py so the tool
invocation contract is the pinned one, not a re-implementation. run_acceptance.main()
is never called: it would write the canonical acceptance report.

Output: probe_results.json (this directory). No canonical write.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # repo root: artifacts/worker-069/<task>/ -> repo
CORPUS = ROOT / "artifacts/formulation/evidence/rebased_fixtures"
RUN_ACCEPT = ROOT / "artifacts/formulation/tools/run_acceptance.py"
GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
SEM = ROOT / "artifacts/worker-06/spec_conformance_audit.py"
BASE = ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
MANIFEST = HERE / "fixture_pin_manifest.json"
CHECKER = HERE / "check_fixture_binding.py"
SANDBOX = HERE / "sandbox"

# canonical inputs whose bytes must not move during the probe
WATCH = [
    "artifacts/formulation/evidence/rebased_fixtures",
    "artifacts/formulation/evidence/semantic_escape_rebased.json",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/tools/run_acceptance.py",
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/worker-06/spec_conformance_audit.py",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dir_state(p: Path) -> dict:
    return {f.name: sha256_file(f) for f in sorted(p.glob("*"))}


def watch_state() -> dict:
    st = {}
    for rel in WATCH:
        p = ROOT / rel
        st[rel] = dir_state(p) if p.is_dir() else (sha256_file(p) if p.exists() else None)
    return st


def load_run_helper():
    spec = importlib.util.spec_from_file_location("pinned_run_acceptance", RUN_ACCEPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # module-level definitions only; main() is guarded
    return mod.run


def corpus_verdict(run, files: list[Path]) -> dict:
    """Exact corpus loop of run_acceptance.main(), lines 78-105 (rev29 bytes)."""
    out = {"controls": [], "mutants": {"total": 0, "semantic_caught": 0, "structural_caught": 0},
           "union_escapes": [], "verdict": "PASS"}
    for p in sorted(files):
        if p.name.startswith("control_"):
            g, _ = run(GATE, p, True)
            s, _ = run(SEM, p, False)
            row = {"control": p.name, "structural": g, "semantic": s, "ok": g == "pass" and s == "pass"}
            out["controls"].append(row)
            if not row["ok"]:
                out["verdict"] = "FAIL"
            continue
        out["mutants"]["total"] += 1
        g, _ = run(GATE, p, True)
        s, _ = run(SEM, p, False)
        caught = False
        if g == "fail":
            out["mutants"]["structural_caught"] += 1
            caught = True
        if s == "fail":
            out["mutants"]["semantic_caught"] += 1
            caught = True
        if caught:
            out["mutants"]["union_caught"] = out["mutants"].get("union_caught", 0) + 1
        else:
            out["union_escapes"].append(p.name)
    m = out["mutants"]
    if m["total"] and m.get("union_caught", 0) != m["total"]:
        out["verdict"] = "FAIL"
    return out


def run_checker(d: Path, manifest: Path, corpus_record: Path | None = None,
                canonical_base: Path | None = None) -> dict:
    args = [sys.executable, str(CHECKER), "--verify", "--dir", str(d), "--manifest", str(manifest), "--json"]
    if corpus_record is not None:
        args += ["--corpus-record", str(corpus_record), "--canonical-base", str(canonical_base)]
    r = subprocess.run(args, capture_output=True, text=True)
    try:
        res = json.loads(r.stdout)
    except Exception:
        res = {"verdict": f"crash(exit{r.returncode})", "stdout": r.stdout[-500:], "stderr": r.stderr[-500:]}
    res["exit_code"] = r.returncode
    return res


def main() -> int:
    run = load_run_helper()
    prereg = json.loads((HERE / "PREREGISTRATION.json").read_text())
    pristine_names = sorted(p.name for p in CORPUS.glob("*.yaml"))
    mutant_names = [n for n in pristine_names if not n.startswith("control_")]
    control_names = [n for n in pristine_names if n.startswith("control_")]
    del_target = mutant_names[0]
    del_control_target = control_names[-1]

    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    variants: dict[str, Path] = {}

    def stage(name: str) -> Path:
        d = SANDBOX / name / "rebased_fixtures"
        d.mkdir(parents=True)
        for n in pristine_names:
            shutil.copy2(CORPUS / n, d / n)
        variants[name] = d
        return d

    stage("pristine")
    # del_mutant: one mutant removed
    d = stage("del_mutant"); (d / del_target).unlink()
    # mod_mutant: one mutant replaced by the benign canonical C0 schema
    d = stage("mod_mutant"); shutil.copy2(BASE, d / del_target)
    # add_extra: one benign undeclared file added
    d = stage("add_extra"); shutil.copy2(BASE, d / "sem19_extra_benign.yaml")
    # del_control (exploratory): one control removed
    d = stage("del_control"); (d / del_control_target).unlink()

    t0 = watch_state()
    results = {}
    for name, d in variants.items():
        files = sorted(d.glob("*.yaml"))
        cv = corpus_verdict(run, files)
        chk = run_checker(d, MANIFEST)
        chk_bound = run_checker(d, MANIFEST,
                                corpus_record=ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json",
                                canonical_base=BASE)
        results[name] = {
            "n_files": len(files), "mutants": cv["mutants"], "controls": cv["controls"],
            "union_escapes": cv["union_escapes"], "corpus_verdict": cv["verdict"],
            "checker_verdict": chk.get("verdict"), "checker_exit_code": chk.get("exit_code"),
            "checker_reasons": chk.get("reasons", []),
            "checker_bound_verdict": chk_bound.get("verdict"),
            "checker_bound_reasons": chk_bound.get("reasons", []),
        }
    t1 = watch_state()

    prereg_checks = {
        "P3_pristine_union_all": results["pristine"]["mutants"].get("union_caught") == results["pristine"]["mutants"]["total"] and results["pristine"]["corpus_verdict"] == "PASS",
        "P4_del_mutant_silent_pass": results["del_mutant"]["corpus_verdict"] == "PASS" and results["del_mutant"]["mutants"]["union_caught"] == results["del_mutant"]["mutants"]["total"],
        "P5_mod_mutant_fails_loud": results["mod_mutant"]["corpus_verdict"] == "FAIL" and len(results["mod_mutant"]["union_escapes"]) >= 1,
        "P6_add_extra_fails_loud": results["add_extra"]["corpus_verdict"] == "FAIL" and len(results["add_extra"]["union_escapes"]) >= 1,
        "P7_checker_controls": (results["pristine"]["checker_verdict"] == "PASS"
                                and results["del_mutant"]["checker_verdict"] == "FAIL"
                                and results["mod_mutant"]["checker_verdict"] == "FAIL"
                                and results["add_extra"]["checker_verdict"] == "FAIL"),
        "P9_no_canonical_write": t0 == t1,
    }
    out = {
        "task_id": prereg["task_id"], "worker": prereg["worker"],
        "created_at_prereg": prereg["created_at"],
        "pinned_inputs": {
            "run_acceptance.py": sha256_file(RUN_ACCEPT), "gate": sha256_file(GATE), "semantic": sha256_file(SEM),
            "canonical_base": sha256_file(BASE), "manifest": sha256_file(MANIFEST), "checker": sha256_file(CHECKER),
        },
        "pristine_names": pristine_names,
        "deleted_mutant": del_target,
        "deleted_control_exploratory": del_control_target,
        "variants": results,
        "prereg_checks": prereg_checks,
        "canonical_state_t0": t0, "canonical_state_t1": t1,
    }
    (HERE / "probe_results.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: out["variants"][k]["corpus_verdict"] for k in out["variants"]}, indent=2))
    print(json.dumps(prereg_checks, indent=2))
    return 0 if all(prereg_checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

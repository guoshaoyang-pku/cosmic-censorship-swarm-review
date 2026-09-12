#!/usr/bin/env python3
"""Run a canonical class-schema gate over the W06 semantic corpus.

Supports the two gate implementations in the repo:
  frozen : artifacts/formulation/tools/check_class_schema.py   (binding at FROZEN rev5)
  flash13: artifacts/flash-13/form_gate/check_class_schema.py  (independent implementation)

Usage:
  python3 run_canonical_gate_on_corpus.py --gate frozen  --out frozen_gate_run.json
  python3 run_canonical_gate_on_corpus.py --gate flash13 --out canonical_gate_run.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SEMANTIC = HERE / "semantic_fixtures"
OUTDIR = HERE / "canonical_gate_runs"
CST = timezone(timedelta(hours=8))
GATES = {
    "frozen": ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py",
    "flash13": ROOT / "artifacts" / "flash-13" / "form_gate" / "check_class_schema.py",
}


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_gate(gate: Path, style: str, target: Path, tag: str):
    jout = OUTDIR / f"{tag}_{hashlib.sha256(str(target).encode()).hexdigest()[:8]}_{target.stem}.json"
    if style == "frozen":
        proc = subprocess.run([sys.executable, str(gate), "--json", str(target)],
                              capture_output=True, text=True, timeout=120)
        rep = {}
        try:
            rep = json.loads(proc.stdout[proc.stdout.index("{"):])
        except (ValueError, json.JSONDecodeError):
            rep = {}
    else:
        proc = subprocess.run([sys.executable, str(gate), str(target), "--json-out", str(jout)],
                              capture_output=True, text=True, timeout=120)
        rep = json.loads(jout.read_text()) if jout.exists() else {}
    return {"exit": proc.returncode, "passed": proc.returncode == 0,
            "failed_rules": rep.get("failed_rules") or [], "class_id": rep.get("class_id"),
            "stderr": proc.stderr.strip()[:200]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", choices=sorted(GATES), default="frozen")
    ap.add_argument("--out", default=None)
    ap.add_argument("--base", default=None, help="base schema for corpus metadata (defaults to manifest base)")
    a = ap.parse_args()
    gate = GATES[a.gate]
    style = a.gate
    OUTDIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((SEMANTIC / "manifest.json").read_text())
    entries = {e["fixture"]: e for e in manifest["fixtures"]}
    base_path = ROOT / (a.base or manifest["base"])
    base_sha = sha(base_path)

    w06_pre = {r["fixture"]: r for r in json.loads((HERE / "semantic_selftest_pre_repair.json").read_text())["results"]}
    w06_post = {r["fixture"]: r for r in json.loads((HERE / "semantic_selftest_post_repair.json").read_text())["results"]}

    results, caught, escaped = [], 0, 0
    for fixture, e in entries.items():
        g = run_gate(gate, style, ROOT / e["path"], a.gate)
        c = g["exit"] != 0
        caught += 1 if c else 0
        escaped += 0 if c else 1
        results.append({
            "fixture": fixture, "s1_class": e.get("s1_class"), "rephrased": bool(e.get("rephrased")),
            "expected_rules": e["expected_rules"], "gate_result": g, "gate_caught": c,
            "w06_baseline_caught": bool(w06_pre[fixture].get("caught")),
            "w06_hardened_caught": bool(w06_post[fixture].get("caught")),
            "differential": ("both_catch" if c and w06_pre[fixture].get("caught") else
                             "gate_only" if c else
                             "w06_only" if w06_pre[fixture].get("caught") else "both_miss"),
        })
    controls = [{"control": p.name, "gate_result": run_gate(gate, style, p, a.gate)}
                for p in sorted((SEMANTIC / "controls").glob("*.yaml"))]
    canonical = []
    for p in [ROOT / "artifacts" / "formulation" / "schemas" / "af_scc_c0_vacuum.yaml",
              ROOT / "artifacts" / "formulation" / "schemas" / "af_scc_c2_vacuum.yaml",
              ROOT / "artifacts" / "formulation" / "schemas" / "af_wcc_vacuum.yaml",
              ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
              SEMANTIC / "controls" / "control_conforming_base.yaml"]:
        if p.exists():
            canonical.append({"schema": str(p.relative_to(ROOT)), "sha256": sha(p), **run_gate(gate, style, p, a.gate)})
    report = {
        "run_id": f"w06-{a.gate}-gate-run",
        "generated_at": now(),
        "gate": {"path": str(gate.relative_to(ROOT)), "sha256": sha(gate), "style": style},
        "corpus": {"manifest_sha256": sha(SEMANTIC / "manifest.json"), "fixtures": len(results),
                   "base": str(base_path.relative_to(ROOT)), "base_sha256": base_sha},
        "summary": {
            "gate_caught": caught, "gate_escaped": escaped,
            "gate_escape_rate": round(escaped / max(1, len(results)), 4),
            "w06_baseline_caught": sum(1 for r in results if r["w06_baseline_caught"]),
            "w06_hardened_caught": sum(1 for r in results if r["w06_hardened_caught"]),
            "gate_only_catches": [r["fixture"] for r in results if r["differential"] == "gate_only"],
            "w06_only_catches": [r["fixture"] for r in results if r["differential"] == "w06_only"],
            "both_miss": [r["fixture"] for r in results if r["differential"] == "both_miss"],
        },
        "controls": controls, "canonical_schemas": canonical,
        "interpretation": ("Escape rate = fraction of leaking mutants the binding gate accepts. A mutant missed "
                           "by both implementations is a spec-level gap; one caught only by the W06 hardened "
                           "rules is a repair candidate for the gate."),
        "results": results,
    }
    out = HERE / (a.out or f"{a.gate}_gate_run.json")
    out.write_text(json.dumps(report, indent=2) + "\n")
    s = report["summary"]
    print(f"[{a.gate}] gate {sha(gate)[:12]} caught {caught}/{len(results)} escape {s['gate_escape_rate']}; "
          f"w06 baseline {s['w06_baseline_caught']} hardened {s['w06_hardened_caught']}")
    print("both_miss:", len(s["both_miss"]), "| gate_only:", s["gate_only_catches"], "| w06_only:", s["w06_only_catches"])
    print("controls:", [(c["control"], c["gate_result"]["exit"]) for c in controls])
    print("canonical schemas:", [(c["schema"].split("/")[-1], c["exit"]) for c in canonical])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""W083-FROZEN-TOOLCHAIN-WRITE-HAZARD-CENSUS-01 finalizer.

Reads the three measurement outputs, re-measures the canonical FROZEN rev29 pins, and emits
pins.json, report.json, checkpoint.json, MANIFEST.json.  Read-only on canonical paths.
"""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = "W083-FROZEN-TOOLCHAIN-WRITE-HAZARD-CENSUS-01"
OUTDIR = ROOT / "artifacts/worker-083/frozen_toolchain_write_hazard"
FROZEN = "artifacts/formulation/FROZEN.json"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODES = "F1,F2a,F2b"
GATE = "G-FORM"
FALSIFIER = (
    "Falsified if: (i) any canonical FROZEN rev29 pin drifts across the run (containment "
    "control fails); (ii) the sentinel probe leaves a pre-seeded pinned target untouched after "
    "a tool whose static classification is UNGUARDED_PINNED; (iii) a tool statically classified "
    "GUARDED_PINNED rewrites its pinned target under a default invocation in the pristine "
    "sandbox; (iv) the control battery does not pass; or (v) re-running census.py --phase all "
    "at the same pins does not reproduce the static digest and the UNGUARDED_PINNED site set."
)


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cd(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    census = json.loads((OUTDIR / "census.json").read_text())
    dyn = json.loads((OUTDIR / "dynamic.json").read_text())
    ctl = json.loads((OUTDIR / "controls.json").read_text())
    frozen = json.loads((ROOT / FROZEN).read_text())
    pinned = {k: v["sha256"] for k, v in frozen["files"].items()}
    live = {p: (sha256_file(ROOT / p) if (ROOT / p).exists() else None) for p in pinned}
    drift = [p for p in pinned if live[p] != pinned[p]]

    # --- pins.json
    pins = {
        "task": TASK,
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "frozen_manifest": FROZEN,
        "frozen_revision": frozen["revision"],
        "frozen_sha256": sha256_file(ROOT / FROZEN),
        "frozen_at": frozen["frozen_at"],
        "canonical_pins": pinned,
        "canonical_live_sha256": live,
        "canonical_drift": drift,
        "pinned_tools": sorted(p for p in pinned if p.startswith("artifacts/formulation/tools/")
                               and p.endswith(".py")),
    }
    (OUTDIR / "pins.json").write_text(json.dumps(pins, indent=1) + "\n")

    # --- report.json (structured)
    runs = {r["tool"]: r for r in dyn["runs"]}
    sent = {s["tool"]: s for s in dyn["sentinel"]}
    static = {t["tool"]: t for t in census["static"]}
    ung = census["static_unguarded_pinned_tools"]
    table = []
    for tool in sorted(static):
        t = static[tool]
        sites = [s for s in t["write_sites"] if s["classification"] in
                 ("UNGUARDED_PINNED", "GUARDED_PINNED")]
        run = runs.get(tool, {})
        snt = sent.get(tool, {})
        table.append({
            "tool": tool,
            "tool_sha256": t["sha256"],
            "pinned_write_sites": [{"line": s["line"], "kind": s["kind"],
                                    "target": s["resolved_target"],
                                    "classification": s["classification"]} for s in sites],
            "unguarded_pinned": [s["line"] for s in sites if s["classification"] == "UNGUARDED_PINNED"],
            "dynamic": {
                "exit": (run.get("run") or {}).get("exit"),
                "mutated_bytes": (run.get("diff") or {}).get("mutated_bytes", []),
                "rewritten_identical": (run.get("diff") or {}).get("rewritten_identical", []),
                "sentinel_replaced": snt.get("sentinel_replaced", []),
            },
        })
    report = {
        "task": TASK,
        "node_ids": NODES,
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "bound_generation": f"FROZEN rev{frozen['revision']} {sha256_file(ROOT / FROZEN)[:12]}",
        "static_digest": census["static_digest"],
        "static_determinism_equal": census["static_determinism_equal"],
        "pinned_tool_count": census["pinned_tool_count"],
        "write_sites_total": sum(len(t["write_sites"]) for t in census["static"]),
        "unguarded_pinned_sites": census["static_unguarded_pinned_sites"],
        "unguarded_pinned_tools": ung,
        "guarded_pinned_tools": sorted({Path(t["tool"]).name for t in census["static"]
                                        for s in t["write_sites"]
                                        if s["classification"] == "GUARDED_PINNED"}),
        "tool_table": table,
        "canonical_containment_ok": dyn["canonical_containment_ok"],
        "canonical_drift": dyn["canonical_drift"],
        "controls_all_pass": ctl.get("all_pass"),
        "controls": ctl,
        "falsifier": FALSIFIER,
        "limits": [
            "Static target resolution is best-effort (literal/Path-division/joined-string "
            "expressions with a small scope table); unresolved sites are labelled, not guessed. "
            "Guarded/un-guarded classification is per enclosing branch condition and direct "
            "call site; it is not a whole-program path-sensitive proof.",
            "The dynamic phase runs each pinned tool with default arguments in a byte-copy "
            "sandbox. A tool that fails before reaching its write site shows no dynamic signal "
            "even if the write is reachable on other input states; static classification "
            "carries the hazard claim in that case.",
            "The sentinel probe demonstrates byte mutation only for targets that were both "
            "statically resolved and reached by the default run.",
            "This census measures tool write behaviour and target binding; it makes no "
            "mathematics, physics, schema-content, gate or node-status claim.",
        ],
    }
    (OUTDIR / "report.json").write_text(json.dumps(report, indent=1) + "\n")

    # --- MANIFEST.json over deliverables
    deliverables = ["census.py", "census.json", "dynamic.json", "controls.json", "pins.json",
                    "report.json", "REPORT.md", "checkpoint.json"]
    man = {"task": TASK, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "deliverables": {}}
    for d in deliverables:
        p = OUTDIR / d
        if p.exists():
            man["deliverables"][d] = {"bytes": p.stat().st_size, "sha256": sha256_file(p)}
        else:
            man["deliverables"][d] = {"bytes": None, "sha256": "PENDING_SELF"}
    (OUTDIR / "MANIFEST.json").write_text(json.dumps(man, indent=1) + "\n")

    # --- checkpoint.json
    canonical = {
        "static_digest": census["static_digest"],
        "unguarded_pinned_sites": sorted((u[0], u[1]) for u in census["static_unguarded_pinned_sites"]),
        "dynamic_sentinel_replaced": sorted((k, tuple(v.get("sentinel_replaced", []))) for k, v in sent.items()),
        "controls_all_pass": ctl.get("all_pass"),
        "canonical_drift": dyn["canonical_drift"],
    }
    checkpoint = {
        "actor": "worker-083",
        "task_id": TASK,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "class_ids": CLASS_IDS,
        "node_ids": NODES,
        "gate": GATE,
        "status": "active",
        "bound_generation": report["bound_generation"],
        "canonical_digest_sha256": cd(canonical),
        "checks": {
            "C1_static_determinism": census["static_determinism_equal"],
            "C2_all_50_pins_current_at_finalize": not drift,
            "C3_dynamic_canonical_containment": dyn["canonical_containment_ok"],
            "C4_controls_all_pass": ctl.get("all_pass"),
            "C5_unguarded_writers_ge_1": len(ung) >= 1,
            "C6_sentinel_signal_present": any(v.get("sentinel_replaced") for v in sent.values()),
        },
        "counts": {
            "pinned_tools": census["pinned_tool_count"],
            "write_sites": report["write_sites_total"],
            "unguarded_pinned_sites": len(census["static_unguarded_pinned_sites"]),
            "unguarded_pinned_tools": len(ung),
        },
        "deliverables": {k: v["sha256"] for k, v in man["deliverables"].items()},
        "falsifier": FALSIFIER,
    }
    (OUTDIR / "checkpoint.json").write_text(json.dumps(checkpoint, indent=1) + "\n")

    # --- runtime/state checkpoint + log (worker-scoped)
    state = ROOT / "runtime/state"
    (state / "w083_write_hazard_census_checkpoint.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
    with (state / "w083_checkpoints.jsonl").open("a") as fh:
        fh.write(json.dumps({"task_id": TASK, "created_at": checkpoint["created_at"],
                             "canonical_digest_sha256": checkpoint["canonical_digest_sha256"],
                             "checkpoint": "runtime/state/w083_write_hazard_census_checkpoint.json"}) + "\n")

    print(json.dumps({"static_digest": census["static_digest"],
                      "unguarded_pinned_tools": ung,
                      "canonical_digest": checkpoint["canonical_digest_sha256"],
                      "checks": checkpoint["checks"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

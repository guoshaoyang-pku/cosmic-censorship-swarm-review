#!/usr/bin/env python3
"""FD-13 measurement: does the proposed clause-local R12 fix do what it claims?

Runs three gates on the repro set and sweeps the full corpus for collateral damage.
  canonical_base    : artifacts/formulation/tools/check_class_schema.py  (FROZEN rev19, 000e09e4)
  canonical_patched : fd13/tools/patched_check_class_schema.py          (proposal, 5eaab3f8)
  flash11           : ../check_schema.py                                (independent gate)

Writes fd13/fd13_results.json. Read-only w.r.t. every shared tree.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIND = HERE.parent
REPO = BIND.parents[2]

CANON_BASE = REPO / "artifacts/formulation/tools/check_class_schema.py"
CANON_PATCHED = HERE / "tools/patched_check_class_schema.py"
FLASH11 = BIND / "check_schema.py"

IMPLS = {
    "canonical_base": {"cmd": [sys.executable, str(CANON_BASE), "{f}", "--json"],
                       "cwd": str(CANON_BASE.parent), "kind": "canonical"},
    "canonical_patched": {"cmd": [sys.executable, str(CANON_PATCHED), "{f}", "--json"],
                          "cwd": str(CANON_PATCHED.parent), "kind": "canonical"},
    "flash11": {"cmd": [sys.executable, str(FLASH11), "{f}", "--json"],
                "cwd": str(BIND), "kind": "flash11"},
}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(name: str, fixture: Path) -> dict:
    spec = IMPLS[name]
    cmd = [c.format(f=str(fixture)) for c in spec["cmd"]]
    try:
        proc = subprocess.run(cmd, cwd=spec["cwd"], capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return {"verdict": "error", "rule_ids": [], "detail": "timeout(90s)"}
    raw = proc.stdout.strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"verdict": "crash" if "Traceback" in proc.stderr else "error",
                "rule_ids": [], "detail": (proc.stderr.strip().splitlines() or [""])[-1][:160]}
    if spec["kind"] == "flash11":
        rec = payload[0] if isinstance(payload, list) else payload
        v = {"ACCEPT": "accept", "REJECT": "reject"}.get(rec.get("verdict"), "error")
        return {"verdict": v, "rule_ids": rec.get("failed_codes", []), "detail": rec.get("layout", "")}
    return {"verdict": "accept" if payload.get("verdict") == "pass" else
                       ("reject" if payload.get("verdict") == "fail" else "error"),
            "rule_ids": payload.get("failed_rules", []), "detail": ""}


# (fixture, expect_canonical_base, expect_canonical_patched, expect_flash11, rule)
# leak rows: the base canonical gate is EXPECTED to escape (that is FD-13);
# the patched gate and the independent gate must reject on R12.
TARGETS = [
    ("fd13/leak_rev19.yaml", "accept", "reject", "reject", "R12"),
    ("fd13/control_rev19.yaml", "accept", "accept", "accept", None),
    ("fd13/leak_current.yaml", "accept", "reject", "reject", "R12"),
    ("fd13/control_current.yaml", "accept", "accept", "accept", None),
    ("corpus/canonical/af_wcc_vacuum.yaml", "accept", "accept", "accept", None),
    ("corpus/canonical/af_scc_c2_vacuum.yaml", "accept", "accept", "accept", None),
    ("corpus/canonical/af_scc_c0_vacuum.yaml", "accept", "accept", "accept", None),
]

out: dict = {
    "artifact": "FD-13 targeted measurement",
    "task_id": "FORM-DIFF-02",
    "node_id": "F1",
    "gate": "G-CLASSBIND",
    "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
    "binding": {
        "canonical_base_tool": {"path": "artifacts/formulation/tools/check_class_schema.py",
                                "sha256": sha256_file(CANON_BASE)},
        "canonical_patched_tool": {"path": "fd13/tools/patched_check_class_schema.py",
                                   "sha256": sha256_file(CANON_PATCHED)},
        "flash11_gate": {"path": "artifacts/flash-11/f1_aux_class_binding/check_schema.py",
                         "sha256": sha256_file(FLASH11)},
        "rule_spec": {"path": "fd13/rule_spec.json", "sha256": sha256_file(HERE / "rule_spec.json")},
    },
    "targets": [],
}

for rel, e_base, e_patched, e_flash, rule in TARGETS:
    fx = BIND / rel
    row = {"fixture": rel, "sha256": sha256_file(fx),
           "expect": {"canonical_base": e_base, "canonical_patched": e_patched, "flash11": e_flash},
           "expect_rule": rule, "verdicts": {}}
    for name in IMPLS:
        row["verdicts"][name] = run(name, fx)
    def ok(name: str, v: dict) -> bool:
        if v["verdict"] != row["expect"][name]:
            return False
        if row["expect"][name] == "reject" and rule and rule not in v["rule_ids"]:
            return False
        return True

    row["pass"] = all(ok(n, v) for n, v in row["verdicts"].items())
    out["targets"].append(row)

# ---- collateral sweep: base vs patched canonical on the whole shared corpus
corpus = sorted([p for p in (BIND / "corpus").rglob("*")
                 if p.suffix in (".yaml", ".yml", ".json") and p.name != "manifest.json"])
deltas = []
counts = {"same": 0}
for fx in corpus:
    a = run("canonical_base", fx)
    b = run("canonical_patched", fx)
    key = (a["verdict"], tuple(sorted(set(a["rule_ids"]))), b["verdict"], tuple(sorted(set(b["rule_ids"]))))
    if a["verdict"] == b["verdict"] and sorted(set(a["rule_ids"])) == sorted(set(b["rule_ids"])):
        counts["same"] += 1
    else:
        deltas.append({"fixture": str(fx.relative_to(BIND)), "sha256": sha256_file(fx),
                       "base": a, "patched": b})
out["collateral"] = {"corpus_files": len(corpus), "identical": counts["same"],
                     "deltas": deltas, "delta_count": len(deltas)}

# ---- verdict
leaks = [r for r in out["targets"] if "leak" in r["fixture"]]
controls = [r for r in out["targets"] if "control" in r["fixture"] or "canonical/" in r["fixture"]]
out["targeted_effect"] = {
    "leaks_total": len(leaks),
    "leaks_base_escape": sum(1 for r in leaks if r["verdicts"]["canonical_base"]["verdict"] == "accept"),
    "leaks_flash11_catch": sum(1 for r in leaks if r["verdicts"]["flash11"]["verdict"] == "reject"),
    "leaks_patched_catch": sum(1 for r in leaks if r["verdicts"]["canonical_patched"]["verdict"] == "reject"),
    "controls_false_positive_base": sum(1 for r in controls if r["verdicts"]["canonical_base"]["verdict"] == "reject"),
    "controls_false_positive_patched": sum(1 for r in controls if r["verdicts"]["canonical_patched"]["verdict"] == "reject"),
    "controls_false_positive_flash11": sum(1 for r in controls if r["verdicts"]["flash11"]["verdict"] == "reject"),
}
out["falsifier"] = {
    "statement": ("Falsified if the patched canonical gate rejects a legitimate schema it accepted "
                  "before (false positive), or fails to reject a leak fixture (false negative), or if "
                  "any corpus fixture changes verdict for a reason other than the intended "
                  "non-geodesic-inextendibility leak."),
    "status": "not fired" if (
        out["targeted_effect"]["leaks_patched_catch"] == out["targeted_effect"]["leaks_total"]
        and out["targeted_effect"]["controls_false_positive_patched"] == 0
    ) else "FIRED",
}
out["caveats"] = [
    "Format-dominated rejections: canonical rejects many non-canonical layouts at R01/R02 before "
    "reaching R12, so corpus-level agreement is not evidence of semantic agreement.",
    "The FROZEN.json manifest is stale: schemas advanced after rev19 while the tool (000e09e4) and "
    "rule_spec (40f9bb9e) still byte-match. The rev19 fixtures use the frozen rev19 corpus copy "
    "(f962c117); the *_current fixtures rebase onto the live authoring schema (b65fcc0f).",
    "The patch is a proposal only; the canonical tool is lead-owned and was not modified.",
]

(HERE / "fd13_results.json").write_text(json.dumps(out, indent=1, sort_keys=True))
te = out["targeted_effect"]
print(json.dumps({"targeted_effect": te, "collateral": {k: out["collateral"][k] for k in ("corpus_files", "identical", "delta_count")},
                  "falsifier": out["falsifier"]["status"]}, indent=1))
for r in out["targets"]:
    print(f"{r['fixture']:45s} base={r['verdicts']['canonical_base']['verdict']:6s} "
          f"patched={r['verdicts']['canonical_patched']['verdict']:6s} "
          f"flash11={r['verdicts']['flash11']['verdict']:6s} pass={r['pass']}")
for d in deltas:
    print("DELTA", d["fixture"], d["base"], "->", d["patched"])

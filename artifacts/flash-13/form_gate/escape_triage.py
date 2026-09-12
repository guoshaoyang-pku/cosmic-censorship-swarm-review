#!/usr/bin/env python3
"""FORM-GATE-01 escape triage (revision 1.1 hardening evidence).

Context
  Worker-06's frozen-base semantic corpus records the independent FORM-GATE-01 (this gate) at
  sha256 8130652042b47952 catching 13/32 leaking mutants (escape rate 0.5938). This script
  re-measures the corpus with the hardened gate, records the per-fixture differential against
  that pre-hardening run, and writes artifacts/flash-13/form_gate/escape_triage.json.

  The pre-hardening column is sourced from artifacts/worker-06/canonical_gate_run.json, whose
  `gate.sha256` is asserted to be 8130652042b47952 before use; if the file does not bind that
  hash the pre-column is reported as unavailable rather than silently mixed.

Scope / honesty
  - This is a structural gate. A caught mutant is rejected by a published rule id (R01-R16 of
    FORM-RULE-SPEC); no physical truth or citation is adjudicated.
  - The corpus base file has been republished since worker-06 generated the corpus: the manifest
    records base_sha256 92406957234f..., while the measured file hash is recorded below. Each
    fixture is hashed and pinned, so the differential is over static fixtures; statements about
    the base schema itself must cite the measured hash at measurement time.
  - Residual escapes after hardening are reported as blind spots with the reason, never counted
    as passes.
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
GATE = HERE / "check_class_schema.py"
CORPUS = ROOT / "artifacts" / "worker-06" / "semantic_fixtures"
MANIFEST = CORPUS / "manifest.json"
PRE_RUN = ROOT / "artifacts" / "worker-06" / "canonical_gate_run.json"
OUT = HERE / "escape_triage.json"
CST = timezone(timedelta(hours=8))
PRE_GATE_SHA = "8130652042b47952b50fe6dfbe9e9d86583394fc78ae03885e205287c6f09674"
CANONICAL_TREES = ("schemas", "artifacts/formulation/schemas")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_gate(target: Path):
    jout = HERE / "_escape_last.json"
    proc = subprocess.run([sys.executable, str(GATE), str(target), "--json-out", str(jout)],
                          capture_output=True, text=True, timeout=120)
    rep = json.loads(jout.read_text()) if jout.exists() else {}
    if jout.exists():
        jout.unlink()
    return {"exit": proc.returncode, "caught": proc.returncode != 0,
            "failed_rules": rep.get("failed_rules") or [],
            "class_id": rep.get("class_id"),
            "stderr": proc.stderr.strip()[:200]}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    pre = {}
    pre_available = False
    if PRE_RUN.exists():
        d = json.loads(PRE_RUN.read_text())
        pre_available = (d.get("gate") or {}).get("sha256") == PRE_GATE_SHA
        if pre_available:
            pre = {r["fixture"]: r for r in d.get("results", [])}

    fixtures, caught, escapes, in_scope_regressions = [], 0, [], []
    for e in manifest["fixtures"]:
        p = ROOT / e["path"]
        g = run_gate(p)
        caught += 1 if g["caught"] else 0
        expected = set(e.get("expected_rules") or [])
        expected_hit = sorted(expected & set(g["failed_rules"]))
        if g["caught"] and not expected_hit:
            in_scope_regressions.append(e["fixture"])
        row = {
            "fixture": e["fixture"],
            "path": e["path"],
            "sha256": sha(p),
            "leak": bool(e.get("leak")),
            "rephrased": bool(e.get("rephrased")),
            "s1_class": e.get("s1_class"),
            "expected_rules": sorted(expected),
            "pre_hardening": ({"gate_sha256": PRE_GATE_SHA,
                               "caught": bool(pre[e["fixture"]]["gate_caught"]),
                               "failed_rules": (pre[e["fixture"]].get("gate_result") or {}).get("failed_rules")}
                              if pre_available and e["fixture"] in pre else None),
            "post_hardening": {"gate_sha256": sha(GATE), "exit": g["exit"],
                               "caught": g["caught"], "failed_rules": g["failed_rules"],
                               "expected_rule_hit": expected_hit},
            "delta": ("newly_caught" if g["caught"] and pre_available
                      and not pre[e["fixture"]]["gate_caught"] else
                      "still_caught" if g["caught"] else "still_escapes"),
        }
        if not g["caught"]:
            escapes.append({"fixture": e["fixture"], "reason": e.get("leak_family"),
                            "s1_class": e.get("s1_class")})
        fixtures.append(row)

    controls = []
    cdir = CORPUS / "controls"
    if cdir.is_dir():
        for p in sorted(cdir.glob("*.yaml")):
            g = run_gate(p)
            controls.append({"control": p.name, "sha256": sha(p), "exit": g["exit"],
                             "false_positive": g["caught"]})

    canonical = {}
    frozen = {}
    frozen_files = {}
    fp = ROOT / "artifacts" / "formulation" / "FROZEN.json"
    if fp.exists():
        fj = json.loads(fp.read_text())
        frozen_files = fj.get("files") or {}
        frozen = {"revision": fj.get("revision"), "frozen_at": fj.get("frozen_at"),
                  "manifest_sha256": sha(fp), "files": frozen_files}
    for tree in CANONICAL_TREES:
        for name in ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml"):
            p = ROOT / tree / name
            if not p.exists():
                canonical[f"{tree}/{name}"] = {"verdict": "absent"}
                continue
            g = run_gate(p)
            key = f"{tree}/{name}"
            canon_sha = sha(p)
            declared = (frozen_files.get(f"{tree}/{name}") or {}).get("sha256")
            canonical[key] = {"sha256": canon_sha, "verdict": "pass" if g["exit"] == 0 else "fail",
                              "exit": g["exit"], "failed_rules": g["failed_rules"],
                              "frozen_declared_sha256": declared,
                              "frozen_match": (declared == canon_sha) if declared else None}

    gate_sha = sha(GATE)
    report = {
        "artifact": "FORM-GATE-01 escape triage (hardened revision 1.1)",
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "gate": {"path": str(GATE.relative_to(ROOT)), "sha256": gate_sha,
                 "version": "1.1", "pre_hardening_sha256": PRE_GATE_SHA,
                 "pre_hardening_measured_by": "this worker at 8130652042b4 and worker-06 canonical_gate_run.json"},
        "corpus": {
            "manifest": str(MANIFEST.relative_to(ROOT)), "manifest_sha256": sha(MANIFEST),
            "manifest_base": manifest.get("base"),
            "manifest_base_sha256": manifest.get("base_sha256"),
            "measured_base_sha256": sha(ROOT / manifest["base"]),
            "base_drift": manifest.get("base_sha256") != sha(ROOT / manifest["base"]),
            "fixtures": len(fixtures),
        },
        "pre_run_source": {"path": str(PRE_RUN.relative_to(ROOT)),
                           "sha256": sha(PRE_RUN) if PRE_RUN.exists() else None,
                           "binds_pre_gate_sha": pre_available},
        "summary": {
            "caught_pre_hardening": sum(1 for r in fixtures
                                        if r["pre_hardening"] and r["pre_hardening"]["caught"]),
            "caught_post_hardening": caught,
            "escapes_post_hardening": len(escapes),
            "newly_caught": sum(1 for r in fixtures if r["delta"] == "newly_caught"),
            "blind_spots": escapes,
            "caught_without_expected_rule_hit": in_scope_regressions,
        },
        "controls": controls,
        "controls_false_positives": [c["control"] for c in controls if c["false_positive"]],
        "canonical": canonical,
        "frozen_manifest": frozen,
        "scope": ("structural rule verdicts only; no physical truth, theorem promotion or citation "
                  "adjudication. Fixture hashes pin what was measured; the corpus base schema is "
                  "republished by the formulation lead and its measured hash is recorded above."),
        "falsifier": ("a frozen-conforming schema this revision rejects, a corpus mutant it accepts "
                      "that a published R01-R16 rule covers, or a control that exits non-zero. "
                      "Re-run: python3 artifacts/flash-13/form_gate/escape_triage.py"),
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True))
    s = report["summary"]
    print(f"gate {gate_sha[:12]}  corpus {s['caught_post_hardening']}/{len(fixtures)} caught "
          f"(pre {s['caught_pre_hardening']}, newly {s['newly_caught']}, escapes {s['escapes_post_hardening']})")
    print(f"controls false positives: {report['controls_false_positives']}")
    for k, v in canonical.items():
        print(f"canonical {k}: {v.get('verdict')} frozen_match={v.get('frozen_match')} {str(v.get('sha256'))[:12]}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

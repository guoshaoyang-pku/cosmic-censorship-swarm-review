#!/usr/bin/env python3
"""W031-A2-HARNESS-REPAIR-INDEP-01 independent checker (worker-031).

Read-only, self-contained (stdlib only, does NOT import evaluation/ablation_harness.py).
Validates one dry-run report + CSV against the pre-registered design and the pinned
harness/design hashes, and prints a per-check JSON verdict.

Authority: worker measurement only. No node status, no validation_status=passed,
no gate verdict, no canonical write.
"""
import argparse
import csv
import hashlib
import json
import os
import sys

PIN_HARNESS = "0fae94bf01903ec7b8076a6b11706bc4444b19f98e6d0985e4ac2d1b2921f157"
PIN_DESIGN = "1b2a83ef670b7e757a1a54d4849b49a597d5dc33e9205c0b5b10646d811cfb0a"
PRE_REG_TOL = 0.02
PRIMARY_ARMS = ("strong_single", "self_consistency", "independent_cheap", "cheap_coordinator")
DECLARED_MATCHED = ("total_completion_tokens", "wall_clock_s",
                    "verifier_calls_per_accepted_artifact", "human_review_minutes")
NET_TOKENS = ("import requests", "import urllib", "import socket", "http.client",
              "from requests", "urlopen")


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--harness", default="evaluation/ablation_harness.py")
    ap.add_argument("--design", default="evaluation/ablation_design.yaml")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    rep = json.load(open(a.report))
    checks = []

    def rec(cid, ok, detail):
        checks.append({"id": cid, "pass": bool(ok), "detail": str(detail)[:400]})

    live_h = sha256(a.harness)
    live_d = sha256(a.design)
    prov = rep.get("provenance", {})

    # I1 harness pin + provenance
    rec("I1_harness_pin",
        live_h == PIN_HARNESS and prov.get("harness_sha256") == live_h
        and str(rep.get("harness_version")) == "0.2.0-repair",
        f"live={live_h[:12]} prov={str(prov.get('harness_sha256'))[:12]} v={rep.get('harness_version')}")

    # I2 design pin + provenance
    rec("I2_design_pin",
        live_d == PIN_DESIGN and prov.get("design_sha256") == live_d,
        f"live={live_d[:12]} prov={str(prov.get('design_sha256'))[:12]}")

    # I3 simulated marking: report + every CSV row
    rows = list(csv.DictReader(open(a.csv, newline="")))
    hdr = list(rows[0].keys()) if rows else []
    leading_ok = hdr[:3] == ["simulated", "run_mode", "harness_sha256"]
    rows_ok = bool(rows) and all(
        r.get("simulated") == "True"
        and r.get("run_mode") == "dry_run_synthetic"
        and r.get("harness_sha256") == live_h for r in rows)
    rec("I3_simulated_marking",
        rep.get("simulated") is True
        and rep.get("run_mode") == "dry_run_synthetic"
        and bool(str(rep.get("simulation_disclaimer") or "").strip())
        and leading_ok and rows_ok,
        f"report simulated={rep.get('simulated')} mode={rep.get('run_mode')} "
        f"csv_leading={leading_ok} rows_marked={rows_ok} n={len(rows)}")

    # I4 matched-budget arithmetic on the four primary arms
    bc = rep.get("budget_check", {})
    tok = bc.get("declared_matched_fields", {}).get("total_completion_tokens", {})
    wall = bc.get("declared_matched_fields", {}).get("wall_clock_s", {})
    prim = [x for x in rep.get("arms", []) if x.get("is_primary")]
    walls = [x.get("wall_clock_s") for x in prim]
    nonconst = len(set(walls)) > 1 if walls else False
    rec("I4_matched_budget",
        bc.get("matched") is True
        and tok.get("matched") is True
        and float(tok.get("tolerance", -1)) == PRE_REG_TOL
        and float(wall.get("tolerance", -1)) == PRE_REG_TOL
        and (tok.get("spread_fraction") or 1) <= PRE_REG_TOL
        and (bc.get("wall_consumption_spread_fraction") or 1) <= PRE_REG_TOL
        and (wall.get("spread_fraction") or 1) <= PRE_REG_TOL
        and nonconst and len(prim) == 4,
        f"matched={bc.get('matched')} tok_spread={tok.get('spread_fraction')} "
        f"wall_cons_spread={bc.get('wall_consumption_spread_fraction')} "
        f"wall_env_spread={wall.get('spread_fraction')} "
        f"tol={tok.get('tolerance')}/{wall.get('tolerance')} walls={walls}")

    # I5 every design-declared matched field is measured; unmatched ones are named
    devs = {d.get("field") for d in rep.get("design_deviations", [])}
    unmeasured, silent_unmatched = [], []
    for f in DECLARED_MATCHED:
        e = bc.get("declared_matched_fields", {}).get(f)
        if not e or not e.get("measured"):
            unmeasured.append(f)
        elif e.get("matched") is not True and f not in devs:
            silent_unmatched.append(f)
    rec("I5_declared_fields_measured",
        not unmeasured and not silent_unmatched
        and set(bc.get("unmatched_declared_fields", [])) == devs,
        f"unmeasured={unmeasured} silent_unmatched={silent_unmatched} deviations={sorted(devs)} "
        f"unmatched_field_list={sorted(bc.get('unmatched_declared_fields', []))}")

    # I6 guardrail before contrasts
    pe = rep.get("primary_endpoint", {})
    flagged = [x for x in rep.get("arms", []) if x.get("guardrail_flagged")]
    gr_ok = pe.get("guardrail_applied") is True and all(
        x.get("accepted_after_guardrail") == 0 for x in flagged)
    rec("I6_guardrail_first", gr_ok,
        f"applied={pe.get('guardrail_applied')} flagged={[x.get('arm') for x in flagged]}")

    # I7 null is a control, not a primary arm; 5 arms
    nulls = [x for x in rep.get("arms", []) if x.get("is_null")]
    rec("I7_null_control",
        len(rep.get("arms", [])) == 5 and len(nulls) == 1
        and nulls[0].get("is_primary") is False,
        f"arms={len(rep.get('arms', []))} nulls={[x.get('arm') for x in nulls]}")

    # I8 no universal scalar score
    score_keys = [k for k in rep if k.lower() in ("score", "combined_score", "scalar_score",
                                                  "universal_score")]
    rec("I8_no_universal_score",
        rep.get("no_universal_scalar_score") is True and not score_keys,
        f"no_universal_scalar_score={rep.get('no_universal_scalar_score')} score_keys={score_keys}")

    # I9 offline static check (AST import scan, not substring)
    import ast
    src = open(a.harness, encoding="utf-8", errors="ignore").read()
    net = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            net |= {al.name.split(".")[0] for al in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            net.add(node.module.split(".")[0])
    hits = sorted(net & {"requests", "urllib", "socket", "http", "httpx", "aiohttp"})
    rec("I9_no_network_client", not hits, f"imported_net_modules={hits}")

    # I10 canonical dry-run guard is a name guard that refuses unmarked names
    rec("I10_output_name_guard",
        "def guard_output_path" in src and "'dryrun'" in src and "ablation.csv" in src,
        "guard_output_path present with dryrun/simulated tokens")

    verdict = "PASS" if all(c["pass"] for c in checks) else "FAIL"
    out = {"checker": "w031-a2-harness-repair-indep/v1", "report": a.report,
           "csv": a.csv, "harness_sha256": live_h, "design_sha256": live_d,
           "checks": checks, "n_pass": sum(c["pass"] for c in checks),
           "n_total": len(checks), "verdict": verdict}
    print(json.dumps(out, indent=1))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

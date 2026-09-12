#!/usr/bin/env python3
"""W053-GCLASSBIND-INFOARM-REPRO-01 — third-party reproduction of the held-out
informative-arm (C2+C0) union-escape = 1.0 measurement for gate G-CLASSBIND.

Run:  python3 artifacts/worker-053/infoarm_repro/repro_infoarm_053.py
Writes: report.json, controls.json, per_fixture.json, run.log, drift.json under this dir.
Read-only against every canonical input.  Stage contract copied from
artifacts/formulation/tools/run_acceptance.py::run (pinned sha256 in PREREGISTRATION.json).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
OUT = HERE
TIMEOUT = 60


def now() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_root(start: Path) -> Path:
    for cand in [start, *start.parents]:
        if (cand / "research_map" / "schemas.py").is_file() and (cand / "artifacts").is_dir():
            return cand
    raise SystemExit("repo root not found")


ROOT = find_root(HERE)

FRAME_PATHS = [
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/tools/run_acceptance.py",
    "artifacts/worker-06/spec_conformance_audit.py",
    "artifacts/formulation/KEY_MANIFEST.json",
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/FROZEN.json",
    "artifacts/heldout/heldout-09/manifest.json",
    "artifacts/heldout/heldout-09/report.json",
    "artifacts/heldout/heldout-10/manifest.json",
    "artifacts/heldout/heldout-10/report.json",
]
STAGE_A = ROOT / "artifacts/formulation/tools/check_class_schema.py"
STAGE_B = ROOT / "artifacts/worker-06/spec_conformance_audit.py"

LOG: list[str] = []


def log(msg: str) -> None:
    line = f"[{now()}] {msg}"
    LOG.append(line)
    print(line, flush=True)


def measure_frame() -> dict:
    return {p: sha256_file(ROOT / p) for p in FRAME_PATHS}


def run_stage(tool: Path, fixture: Path, json_flag: bool) -> dict:
    """Byte-for-byte the run_acceptance.py::run contract, plus a process timeout."""
    args = [sys.executable, str(tool)] + (["--json", str(fixture)] if json_flag else [str(fixture)])
    t0 = time.time()
    timed_out = False
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=TIMEOUT)
        rc, so, se = r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        timed_out, rc, so, se = True, None, "", "TIMEOUT"
    seconds = round(time.time() - t0, 3)
    parse_fallback = False
    if timed_out:
        verdict, failed_rules = "timeout", []
    elif json_flag:
        try:
            d = json.loads(so)
            verdict, failed_rules = d.get("verdict", "?"), d.get("failed_rules", [])
        except Exception:
            verdict, failed_rules, parse_fallback = f"crash(exit{rc})", [], True
    else:
        try:
            d = json.loads(so)
            v = d.get("verdict")
            if v is None:
                verdict = "pass" if rc == 0 else "fail"
            else:
                verdict = "pass" if str(v).lower() in ("accept", "pass", "ok") else "fail"
            failed_rules = d.get("failed_rules", [])
        except Exception:
            verdict, failed_rules, parse_fallback = ("pass" if rc == 0 else "fail"), [], True
    return {
        "tool": str(tool.relative_to(ROOT)),
        "exit": rc,
        "verdict": verdict,
        "failed_rules": failed_rules,
        "timed_out": timed_out,
        "parse_fallback": parse_fallback,
        "seconds": seconds,
        "stderr_head": (se or "").strip()[:200],
    }


def verdict_is_pass(stage: dict) -> bool:
    return stage["verdict"] == "pass"


def run_fixture(rel_path: str) -> dict:
    fixture = ROOT / rel_path
    a = run_stage(STAGE_A, fixture, True)
    b = run_stage(STAGE_B, fixture, False)
    accepted_both = verdict_is_pass(a) and verdict_is_pass(b)
    return {
        "path": rel_path,
        "sha256": sha256_file(fixture),
        "stage_a": a,
        "stage_b": b,
        "accepted_both": accepted_both,
        "union_caught": not accepted_both,
    }


def load_corpus(cid: str) -> tuple[dict, dict]:
    m = json.loads((ROOT / f"artifacts/heldout/{cid}/manifest.json").read_text())
    r = json.loads((ROOT / f"artifacts/heldout/{cid}/report.json").read_text())
    return m, r


def arm_group(arm: str) -> str:
    return "informative" if arm in ("C2", "C0") else "uninformative_W"


def aggregate(rows: list[dict]) -> dict:
    n = len(rows)
    s_caught = sum(1 for x in rows if x["union_caught"])
    a_fail = sum(1 for x in rows if not verdict_is_pass(x["stage_a"]))
    b_fail = sum(1 for x in rows if not verdict_is_pass(x["stage_b"]))
    fams: dict = {}
    for x in rows:
        f = fams.setdefault(x.get("family", "n/a"), {"n": 0, "union_caught": 0})
        f["n"] += 1
        f["union_caught"] += int(x["union_caught"])
    return {
        "mutants": n,
        "structural_caught": a_fail,
        "semantic_caught": b_fail,
        "union_caught": s_caught,
        "union_escape": round(1.0 - (s_caught / n), 4) if n else None,
        "caught_fixtures": [x["path"] for x in rows if x["union_caught"]],
        "escape_families": sorted({x.get("family", "n/a") for x in rows if not x["union_caught"]}),
        "families": fams,
    }


def main() -> int:
    started = now()
    pre = measure_frame()
    prereg = json.loads((OUT / "PREREGISTRATION.json").read_text())
    frame_match_prereg = {
        p: (pre.get(p) == h) for p, h in prereg["frame_sha256"].items() if p in pre
    }
    log(f"frame measured: {len(pre)} paths, prereg matches={sum(frame_match_prereg.values())}/{len(frame_match_prereg)}")

    controls: dict = {}

    # ---- K1/K2: frozen canonical schemas through both stages ------------------
    canon_rows = {}
    for rel in ("schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml", "schemas/af_wcc_vacuum.yaml"):
        canon_rows[rel] = run_fixture(rel)
        log(f"canonical {rel}: A={canon_rows[rel]['stage_a']['verdict']} "
            f"B={canon_rows[rel]['stage_b']['verdict']} {canon_rows[rel]['stage_b']['failed_rules']}")
    c2, c0, wcc = (canon_rows["schemas/af_scc_c2_vacuum.yaml"],
                   canon_rows["schemas/af_scc_c0_vacuum.yaml"],
                   canon_rows["schemas/af_wcc_vacuum.yaml"])
    controls["K1_canonical_C2_C0_pass_both_stages"] = {
        "passed": c2["accepted_both"] and c0["accepted_both"],
        "detail": {"C2": c2["accepted_both"], "C0": c0["accepted_both"]},
    }
    controls["K2_WCC_canonical_stage_B_reject_R03"] = {
        "passed": verdict_is_pass(wcc["stage_a"]) and (not verdict_is_pass(wcc["stage_b"]))
        and "R03" in wcc["stage_b"]["failed_rules"],
        "detail": {"stage_a": wcc["stage_a"]["verdict"], "stage_b": wcc["stage_b"]["verdict"],
                   "failed_rules": wcc["stage_b"]["failed_rules"]},
    }

    # ---- K6: parser contract on synthetic fixtures ----------------------------
    syn = OUT / "synthetic"
    syn.mkdir(exist_ok=True)
    src = ROOT / "artifacts/heldout/heldout-10/controls/c01_conforming_c2_polished.yaml"
    (syn / "copy_conforming_c2.yaml").write_bytes(src.read_bytes())
    (syn / "unparseable.yaml").write_text("class_id: [unclosed\n  - :::\n")
    good = run_fixture(str((syn / "copy_conforming_c2.yaml").relative_to(ROOT)))
    bad = run_fixture(str((syn / "unparseable.yaml").relative_to(ROOT)))
    controls["K6_parser_contract"] = {
        "passed": good["accepted_both"] and not bad["accepted_both"],
        "detail": {
            "conforming_copy_accepted_both": good["accepted_both"],
            "unparseable_accepted_both": bad["accepted_both"],
            "unparseable_stage_a": bad["stage_a"],
            "unparseable_stage_b": bad["stage_b"],
        },
    }

    # ---- corpora --------------------------------------------------------------
    results: dict = {}
    control_rows: dict = {}
    mutant_rows: dict = {}
    for cid in ("heldout-09", "heldout-10"):
        m, rep = load_corpus(cid)
        log(f"corpus {cid}: {len(m['mutants'])} mutants, {len(m['controls'])} controls, "
            f"manifest={sha256_file(ROOT / f'artifacts/heldout/{cid}/manifest.json')[:12]}")
        rows, integ_bad = [], []
        for mut in m["mutants"]:
            row = run_fixture(mut["path"])
            row.update({"arm": mut["arm"], "class_id": mut["class_id"], "family": mut["family"],
                        "declared_sha256": mut["sha256"]})
            rows.append(row)
            if row["sha256"] != mut["sha256"]:
                integ_bad.append(mut["path"])
        ctrl_rows = []
        for ctl in m["controls"]:
            row = run_fixture(ctl["path"])
            row.update({"arm": ctl.get("arm"), "class_id": ctl["class_id"], "kind": ctl["kind"],
                        "declared_sha256": ctl["sha256"]})
            ctrl_rows.append(row)
            if row["sha256"] != ctl["sha256"]:
                integ_bad.append(ctl["path"])

        arms = sorted({r["arm"] for r in rows})
        by_arm = {a: aggregate([r for r in rows if r["arm"] == a]) for a in arms}
        info = [r for r in rows if r["arm"] in ("C2", "C0")]
        w_rows = [r for r in rows if r["arm"] == "W"]
        results[cid] = {
            "manifest_sha256": sha256_file(ROOT / f"artifacts/heldout/{cid}/manifest.json"),
            "manifest_sha256_before_run_declared": rep.get("manifest_sha256_before_run"),
            "report_sha256": sha256_file(ROOT / f"artifacts/heldout/{cid}/report.json"),
            "by_arm": by_arm,
            "informative_C2_C0": aggregate(info),
            "uninformative_W": aggregate(w_rows),
            "declared_aggregates_informative_arms_only": rep.get("aggregates_informative_arms_only"),
            "declared_aggregates_all": rep.get("aggregates"),
            "declared_valid": rep.get("valid"),
            "declared_invalid_reasons": rep.get("invalid_reasons"),
        }
        control_rows[cid] = ctrl_rows
        mutant_rows[cid] = [
            {"fixture": r["path"], "arm": r["arm"], "family": r["family"], "class_id": r["class_id"],
             "stage_a": r["stage_a"]["verdict"], "stage_b": r["stage_b"]["verdict"],
             "failed_rules": r["stage_b"]["failed_rules"], "union_caught": r["union_caught"],
             "accepted_both": r["accepted_both"]} for r in rows
        ]
        results[cid]["fixture_hash_integrity_failures"] = integ_bad
        results[cid]["controls_detail"] = [
            {"fixture": r["path"], "kind": r["kind"], "stage_a": r["stage_a"]["verdict"],
             "stage_b": r["stage_b"]["verdict"], "failed_rules": r["stage_b"]["failed_rules"],
             "accepted_both": r["accepted_both"]} for r in ctrl_rows
        ]

        # declared vs measured
        decl = rep.get("aggregates_informative_arms_only") or {}
        meas = results[cid]["informative_C2_C0"]
        results[cid]["comparison"] = {
            "declared_mutants": decl.get("mutants"),
            "measured_mutants": meas["mutants"],
            "declared_union_caught": decl.get("union_caught"),
            "measured_union_caught": meas["union_caught"],
            "declared_union_escape": decl.get("union_escape"),
            "measured_union_escape": meas["union_escape"],
            "equal": (decl.get("mutants") == meas["mutants"]
                      and decl.get("union_caught") == meas["union_caught"]
                      and decl.get("union_escape") == meas["union_escape"]),
        }
        log(f"  informative C2+C0 union_caught={meas['union_caught']}/{meas['mutants']} "
            f"escape={meas['union_escape']} (declared {decl.get('union_caught')}/{decl.get('mutants')})")
        log(f"  W arm union_caught={results[cid]['uninformative_W']['union_caught']}/{len(w_rows)}")

    # ---- K3 determinism -------------------------------------------------------
    det = {}
    for cid, picks in (("heldout-10", ["m01_conclusion-polarity-inversion_C2.yaml",
                                       "m03_conclusion-content-erasure_C2.yaml",
                                       "c01_conforming_c2_polished.yaml",
                                       "c02_conforming_c0_polished.yaml"]),):
        m, _ = load_corpus(cid)
        index = {Path(x["path"]).name: x for x in m["mutants"] + m["controls"]}
        for name in picks:
            row1 = run_fixture(index[name]["path"])
            row2 = run_fixture(index[name]["path"])
            det[name] = {
                "run1": [row1["stage_a"]["verdict"], row1["stage_b"]["verdict"]],
                "run2": [row2["stage_a"]["verdict"], row2["stage_b"]["verdict"]],
                "identical": [row1["stage_a"]["verdict"], row1["stage_b"]["verdict"]]
                == [row2["stage_a"]["verdict"], row2["stage_b"]["verdict"]],
            }
    controls["K3_determinism"] = {"passed": all(v["identical"] for v in det.values()), "detail": det}

    # ---- K4 fixture integrity, K5 manifest integrity --------------------------
    controls["K4_fixture_hash_integrity"] = {
        "passed": all(not results[c]["fixture_hash_integrity_failures"] for c in results),
        "detail": {c: results[c]["fixture_hash_integrity_failures"] for c in results},
    }
    controls["K5_manifest_hash_integrity"] = {
        "passed": all(results[c]["manifest_sha256"] == results[c]["manifest_sha256_before_run_declared"]
                      for c in results),
        "detail": {c: {"measured": results[c]["manifest_sha256"],
                       "declared": results[c]["manifest_sha256_before_run_declared"]} for c in results},
    }

    # ---- K7 drift -------------------------------------------------------------
    post = measure_frame()
    drift = {p: {"before": pre[p], "after": post[p], "moved": pre[p] != post[p]} for p in pre}
    controls["K7_no_pin_drift"] = {"passed": not any(v["moved"] for v in drift.values()),
                                   "detail": {p: v["moved"] for p, v in drift.items()}}

    controls_ok = all(c["passed"] for c in controls.values())

    # ---- verdict --------------------------------------------------------------
    info_ok = all(results[c]["informative_C2_C0"]["union_caught"] == 0 for c in results)
    decl_ok = all(results[c]["comparison"]["equal"] for c in results)
    if not controls_ok:
        verdict = "PARTIAL_CONTROL_FAILURE"
    elif info_ok and decl_ok:
        verdict = "REPRODUCED_INFORMATIVE_ARM_ESCAPE_1.0"
    elif not info_ok:
        verdict = "FALSIFIED_INFORMATIVE_ARM_ESCAPE"
    else:
        verdict = "PARTIAL_DECLARED_MEASURED_MISMATCH"

    report = {
        "artifact_id": "W053-GCLASSBIND-INFOARM-REPRO-01",
        "actor": "worker-053",
        "created_at": now(),
        "run_started_at": started,
        "node_id": "A1",
        "gate": "G-CLASSBIND",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN"],
        "authority": "Worker measurement evidence only. No node status, no validation_status=passed, no gate verdict. Read-only against canonical inputs.",
        "independence_basis": "worker-053 authored neither held-out corpus, neither stage tool, nor any of the three class schemas; it reviewed F2b (reviews/F2b-review-rev29-053.json, revise) but that is not A1/G-CLASSBIND and does not touch this measurement.",
        "frame_sha256": pre,
        "frame_matches_preregistration": frame_match_prereg,
        "stage_contract": "run_acceptance.py::run, replicated; stage A --json, stage B body verdict; timeout 60 s -> not-pass",
        "per_corpus": results,
        "controls": controls,
        "controls_ok": controls_ok,
        "drift": drift,
        "verdict": verdict,
        "verdict_rule": prereg["verdict_rule"],
        "falsifier": prereg["falsifier"],
        "do_not_claim": prereg["do_not_claim"],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=1))
    (OUT / "controls.json").write_text(json.dumps(controls, indent=1))
    (OUT / "drift.json").write_text(json.dumps(drift, indent=1))
    per_fixture = {cid: control_rows[cid] for cid in control_rows}
    (OUT / "per_fixture.json").write_text(json.dumps(per_fixture, indent=1))
    (OUT / "mutants.json").write_text(json.dumps(mutant_rows, indent=1))
    (OUT / "run.log").write_text("\n".join(LOG) + "\n")
    log(f"VERDICT: {verdict} | controls_ok={controls_ok}")
    log(f"report.json sha256={sha256_file(OUT / 'report.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

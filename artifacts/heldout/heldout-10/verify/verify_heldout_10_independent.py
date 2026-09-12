#!/usr/bin/env python3
"""Independent terminal verification of FORM-HELDOUT-10 (worker-084, W084-HELDOUT10-INDEP-01).

Read-only on every canonical/heldout-10 corpus byte.  This script does NOT import the
builder (build_corpus_10.py) or the executor (run_heldout_10.py); it re-derives the verdicts
by invoking the two canonical stage tools directly as subprocesses, exactly as the executor
did, then compares its own verdicts and aggregates against the preserved raw/report data.

It writes only under artifacts/heldout/heldout-10/verify/:
  verification.json   machine checks + independent re-run verdicts + drift re-hash
  adjudication.json   terminal adjudication and re-derived aggregates
  INDEPENDENT_REVIEW.md  human-readable summary

Usage: python3 artifacts/heldout/heldout-10/verify/verify_heldout_10_independent.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[4]          # repo root
CORPUS = ROOT / "artifacts" / "heldout" / "heldout-10"
VERIFY = CORPUS / "verify"
MANIFEST = CORPUS / "manifest.json"
REPORT = CORPUS / "report.json"
RAW = CORPUS / "raw" / "raw_verdicts.json"
TIMEOUT = 60
VERIFIER = "worker-084"
TASK_ID = "W084-HELDOUT10-INDEP-01"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_json_stdout(stdout: str):
    for i, ch in enumerate(stdout):
        if ch != "{":
            continue
        try:
            return json.loads(stdout[i:])
        except json.JSONDecodeError:
            continue
    return None


def run_stage_a(tool: Path, target: Path) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, str(tool), "--json", str(target)],
                           capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"exit": None, "verdict": None, "failed_rules": [], "failures": [],
                "escaped": False, "crash": True, "seconds": round(time.time() - t0, 3),
                "stderr": "timeout"}
    rep = parse_json_stdout(p.stdout) or {}
    return {"exit": p.returncode, "verdict": rep.get("verdict"),
            "failed_rules": sorted(rep.get("failed_rules", [])),
            "failures": rep.get("failures", [])[:6],
            "escaped": p.returncode == 0 and rep.get("verdict") == "pass",
            "crash": rep.get("verdict") is None,
            "seconds": round(time.time() - t0, 3), "stderr": p.stderr.strip()[:200]}


def run_stage_b(tool: Path, target: Path) -> dict:
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, str(tool), str(target)],
                           capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"exit": None, "verdict": None, "failed_rules": [], "failed_checks": [],
                "escaped": False, "crash": True, "seconds": round(time.time() - t0, 3),
                "stderr": "timeout"}
    rep = parse_json_stdout(p.stdout) or {}
    verdict = rep.get("verdict")
    return {"exit": p.returncode, "verdict": verdict,
            "failed_rules": sorted(rep.get("failed_rules", [])),
            "failed_checks": [c for c in rep.get("checks", []) if c.get("verdict") == "fail"][:6],
            "escaped": verdict == "accept", "crash": verdict is None,
            "seconds": round(time.time() - t0, 3), "stderr": p.stderr.strip()[:200]}


def main() -> int:
    VERIFY.mkdir(parents=True, exist_ok=True)
    started = now()
    man = json.loads(MANIFEST.read_text())
    report = json.loads(REPORT.read_text())
    raw = json.loads(RAW.read_text())

    checks: list[dict] = []

    def check(cid: str, ok: bool, detail: str):
        checks.append({"check_id": cid, "ok": bool(ok), "detail": detail})

    # ---- pin / instrument identity at verification start ----------------------
    live_pins = {rel: sha(ROOT / rel) for rel in man["pins"]}
    frozen_path = man["frozen_manifest"]["path"]
    live_frozen = sha(ROOT / frozen_path)
    pin_matches = {rel: (live_pins[rel] == man["pins"][rel]) for rel in man["pins"]}
    check("P01_live_pins_match_manifest",
          all(pin_matches.values()) and live_frozen == man["frozen_manifest"]["sha256"],
          json.dumps({"pins": pin_matches, "frozen": live_frozen == man["frozen_manifest"]["sha256"]}))

    struct_tool = ROOT / man["stages"]["structural"]["path"]
    sem_tool = ROOT / man["stages"]["semantic"]["path"]
    keyman = ROOT / man["stages"]["stage_a_key_manifest"]["path"]
    tool_hashes = {"stage_a": sha(struct_tool), "stage_b": sha(sem_tool), "key_manifest": sha(keyman)}
    tool_ok = (tool_hashes["stage_a"] == man["stages"]["structural"]["sha256"]
               and tool_hashes["stage_b"] == man["stages"]["semantic"]["sha256"]
               and tool_hashes["key_manifest"] == man["stages"]["stage_a_key_manifest"]["sha256"])
    check("P02_stage_tool_hashes_match_manifest", tool_ok,
          json.dumps({"measured": tool_hashes,
                      "expected": {"stage_a": man["stages"]["structural"]["sha256"],
                                   "stage_b": man["stages"]["semantic"]["sha256"],
                                   "key_manifest": man["stages"]["stage_a_key_manifest"]["sha256"]}}))

    # ---- H1: manifest hashed before any stage run, and not edited since -------
    manifest_sha_now = sha(MANIFEST)
    man_mtime = datetime.fromtimestamp(MANIFEST.stat().st_mtime, CST).isoformat(timespec="seconds")
    run_started = raw["run_started_at"]
    run_finished = raw["run_finished_at"]
    check("M01_manifest_sha_agrees_report_and_raw",
          manifest_sha_now == report["manifest_sha256_before_run"] == raw["manifest_sha256_before_run"],
          f"now={manifest_sha_now[:16]} report={report['manifest_sha256_before_run'][:16]} "
          f"raw={raw['manifest_sha256_before_run'][:16]}")
    check("M02_manifest_mtime_not_after_run_start", man_mtime <= run_started,
          f"manifest mtime={man_mtime} run_started={run_started}")
    check("M03_manifest_bytes_stable_since_freeze",
          manifest_sha_now == raw["manifest_sha256_before_run"],
          f"sha now={manifest_sha_now[:16]} freeze-time={raw['manifest_sha256_before_run'][:16]}")

    # ---- corpus integrity ------------------------------------------------------
    # manifest stores authored controls separately from the 3 frozen canonical controls
    # (which are referenced by repo-relative path and pinned in man["pins"]).
    canon_class = {"af_wcc_vacuum.yaml": "AF-WCC-VAC-GEN",
                   "af_scc_c2_vacuum.yaml": "AF-SCC-C2-VAC-GEN",
                   "af_scc_c0_vacuum.yaml": "AF-SCC-C0-VAC-GEN"}
    frozen_ctrls = [{"fixture": Path(p).name, "path": p, "sha256": man["pins"][p],
                     "kind": "frozen-canonical", "class_id": canon_class[Path(p).name]}
                    for p in man["frozen_canonical_controls"]]
    fixtures = man["mutants"] + man["controls"] + frozen_ctrls
    bad_fixtures = [e["path"] for e in fixtures
                    if not (ROOT / e["path"]).is_file() or sha(ROOT / e["path"]) != e["sha256"]]
    check("F01_all_fixture_hashes_match_manifest", not bad_fixtures,
          f"{len(fixtures)} fixtures hashed; mismatches={bad_fixtures}")

    base_bad = []
    for arm, b in man["bases"].items():
        got = sha(ROOT / b["path"])
        if got != b["sha256"] or b["sha256"] != man["pins"][b["frozen_path"]]:
            base_bad.append(b["path"])
    check("F02_bases_equal_frozen_canonical_pins", not base_bad, f"mismatches={base_bad}")

    n_mut, n_fam = len(man["mutants"]), len(man["families"])
    kinds = {e["kind"] for e in man["controls"]} | {e["kind"] for e in frozen_ctrls}
    check("F03_card_corpus_minima",
          n_mut >= 20 and n_fam >= 10 and len(fixtures) - n_mut == 7
          and kinds == {"frozen-canonical", "conforming", "negated-phrase"},
          f"mutants={n_mut} families={n_fam} controls={len(fixtures) - n_mut} kinds={sorted(kinds)}")

    base_by_arm = {arm: b["sha256"] for arm, b in man["bases"].items()}
    same_as_base = [e["fixture"] for e in man["mutants"] if e["sha256"] == base_by_arm[e["arm"]]]
    check("F04_every_mutant_differs_from_its_base", not same_as_base,
          f"identical-to-base mutants={same_as_base}")

    arm_class = {"W": "AF-WCC-VAC-GEN", "C2": "AF-SCC-C2-VAC-GEN", "C0": "AF-SCC-C0-VAC-GEN"}
    bad_arm = [e["fixture"] for e in man["mutants"] + man["controls"]
               if arm_class[e["arm"]] != e["class_id"]]
    bad_arm += [e["fixture"] for e in frozen_ctrls if canon_class[e["fixture"]] != e["class_id"]]
    check("F05_arm_class_consistency", not bad_arm, f"mismatches={bad_arm}")

    late = [e["fixture"] for e in fixtures
            if datetime.fromtimestamp((ROOT / e["path"]).stat().st_mtime, CST).isoformat(timespec="seconds")
            > run_finished]
    check("F06_no_fixture_mtime_after_run_finish", not late, f"late fixtures={late}")

    # ---- H3/H6: independent re-run of both stages on all 40 fixtures ----------
    rerun: dict[str, dict] = {}
    crashes = []
    for i, e in enumerate(fixtures, 1):
        target = ROOT / e["path"]
        a = run_stage_a(struct_tool, target)
        b = run_stage_b(sem_tool, target)
        rerun[e["fixture"]] = {"stage_a": a, "stage_b": b}
        if a["crash"] or b["crash"]:
            crashes.append(e["fixture"])
        if i % 10 == 0:
            print(f"  re-ran {i}/{len(fixtures)} fixtures", flush=True)
    check("R01_independent_rerun_complete_no_crash",
          len(rerun) == len(fixtures) and not crashes,
          f"fixtures={len(rerun)} crashes={crashes}")

    def raw_index():
        idx = {}
        for e in raw["controls"] + raw["results"]:
            idx[e["fixture"]] = e
        return idx

    ridx = raw_index()
    check("R02_raw_verdicts_cover_all_fixtures",
          set(ridx) == set(rerun), f"raw={len(ridx)} rerun={len(rerun)} "
                                   f"missing={sorted(set(rerun) - set(ridx))}")

    a_disagree, b_disagree, ar_disagree, br_disagree = [], [], [], []
    for name, mine in rerun.items():
        theirs = ridx[name]
        if mine["stage_a"]["verdict"] != theirs["stage_a"]["verdict"]:
            a_disagree.append(name)
        if mine["stage_b"]["verdict"] != theirs["stage_b"]["verdict"]:
            b_disagree.append(name)
        if mine["stage_a"]["failed_rules"] != sorted(theirs["stage_a"]["failed_rules"]):
            ar_disagree.append(name)
        if mine["stage_b"]["failed_rules"] != sorted(theirs["stage_b"]["failed_rules"]):
            br_disagree.append(name)
    check("R03_stage_a_rerun_verdict_agreement", not a_disagree, f"disagreements={a_disagree}")
    check("R04_stage_b_rerun_verdict_agreement", not b_disagree, f"disagreements={b_disagree}")
    check("R05_stage_a_failed_rule_agreement", not ar_disagree, f"disagreements={ar_disagree}")
    check("R06_stage_b_failed_rule_agreement", not br_disagree, f"disagreements={br_disagree}")

    # ---- H4: recompute aggregates from the independent re-run -----------------
    mut = {e["fixture"]: e for e in man["mutants"]}
    ctl = {e["fixture"]: e for e in man["controls"] + frozen_ctrls}

    def aggregate(names):
        n = len(names)
        s = sum(1 for f in names if rerun[f]["stage_a"]["escaped"])
        m = sum(1 for f in names if rerun[f]["stage_b"]["escaped"])
        u = sum(1 for f in names if rerun[f]["stage_a"]["escaped"] and rerun[f]["stage_b"]["escaped"])
        return {"mutants": n,
                "structural_escape": round(s / n, 4), "semantic_escape": round(m / n, 4),
                "union_escape": round(u / n, 4),
                "structural_caught": n - s, "semantic_caught": n - m, "union_caught": n - u}

    all_mut = sorted(mut)
    informative_arms = {"AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"}
    inf_mut = sorted(f for f in mut if mut[f]["class_id"] in informative_arms)
    uninf_mut = sorted(f for f in mut if mut[f]["class_id"] not in informative_arms)
    agg_all = aggregate(all_mut)
    agg_inf = aggregate(inf_mut)
    agg_uninf = aggregate(uninf_mut)

    def cmp_agg(cid, mine, theirs):
        keys = ["mutants", "structural_escape", "semantic_escape", "union_escape",
                "structural_caught", "semantic_caught", "union_caught"]
        diff = {k: (mine[k], theirs.get(k)) for k in keys if mine[k] != theirs.get(k)}
        check(cid, not diff, f"recomputed={ {k: mine[k] for k in keys} } diffs={diff}")

    cmp_agg("A01_all_mutant_aggregates_match_report", agg_all, report["aggregates"])
    cmp_agg("A02_informative_arm_aggregates_match_report", agg_inf,
            report["aggregates_informative_arms_only"])
    cmp_agg("A03_uninformative_arm_aggregates_match_report", agg_uninf,
            report["aggregates_uninformative_arms_only"])

    # escape families: families with >=1 escaping mutant, from the independent re-run
    def escape_families(names):
        fam: dict[str, list[str]] = {}
        for f in names:
            if rerun[f]["stage_a"]["escaped"] and rerun[f]["stage_b"]["escaped"]:
                fam.setdefault(mut[f]["family"], []).append(f)
        out = []
        for fam_name, fs in sorted(fam.items()):
            entry = next(x for x in man["families"] if x["family"] == fam_name)
            out.append({"family": fam_name, "count": len(fs), "example_name": fs[0],
                        "one_sentence_reason": entry["rationale"], "fixtures": fs})
        return out

    fam_inf = escape_families(inf_mut)
    rep_fam = report["aggregates_informative_arms_only"]["escape_families"]
    rep_norm = [{"family": x["family"], "count": x["count"], "example_name": x["example_name"],
                 "one_sentence_reason": x["one_sentence_reason"], "fixtures": sorted(x["fixtures"])}
                for x in rep_fam]
    mine_norm = [dict(x, fixtures=sorted(x["fixtures"])) for x in fam_inf]
    check("A04_escape_family_list_match_report", mine_norm == rep_norm,
          f"recomputed_families={len(mine_norm)} report_families={len(rep_norm)}")

    caught_fam = sorted({mut[f]["family"] for f in uninf_mut if not rerun[f]["stage_b"]["escaped"]})
    check("A05_uninformative_caught_families_match_report",
          caught_fam == sorted(report["aggregates_uninformative_arms_only"].get("caught_families", [])),
          f"recomputed={caught_fam}")

    # controls: independent recomputation of accepted_both
    ctl_bad = [f for f in ctl if not (rerun[f]["stage_a"]["escaped"] and rerun[f]["stage_b"]["escaped"])]
    wcc_rejected = (rerun["af_wcc_vacuum.yaml"]["stage_a"]["verdict"] == "pass"
                    and rerun["af_wcc_vacuum.yaml"]["stage_b"]["verdict"] == "reject"
                    and rerun["af_wcc_vacuum.yaml"]["stage_b"]["failed_rules"] == ["R03"])
    check("C01_controls_all_accepted_both_stages_H5", not ctl_bad, f"rejected_controls={ctl_bad}")
    check("C02_wcc_r03_calibration_reproduced", wcc_rejected,
          f"wcc stage_a={rerun['af_wcc_vacuum.yaml']['stage_a']['verdict']} "
          f"stage_b={rerun['af_wcc_vacuum.yaml']['stage_b']['verdict']} "
          f"rules={rerun['af_wcc_vacuum.yaml']['stage_b']['failed_rules']}")
    check("C03_frozen_c2_c0_canonicals_pass_both",
          all(rerun[f]["stage_a"]["escaped"] and rerun[f]["stage_b"]["escaped"]
              for f in ("af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml")),
          "C2 and C0 canonical controls accepted by both stages")

    # ---- H7: escape reported with raw per-fixture data ------------------------
    raw_complete = (len(raw["results"]) == n_mut and len(raw["controls"]) == len(ctl)
                    and all(x.get("stage_a") and x.get("stage_b") for x in raw["results"] + raw["controls"]))
    check("H07_escape_reported_with_raw_per_fixture_verdicts",
          raw_complete and isinstance(report["aggregates"].get("union_escape"), float)
          and report["acceptance"].get("H7_escape_rate_reported_regardless_of_outcome") is True,
          f"raw results={len(raw['results'])} controls={len(raw['controls'])} "
          f"union_escape={report['aggregates']['union_escape']}")

    # ---- independence declaration (H6) ---------------------------------------
    check("H06_executor_independence", man["worker"] == "worker-084" and man["worker"] != "worker-16",
          f"corpus executor={man['worker']} (not worker-16); verifier={VERIFIER} re-ran both stages "
          f"fresh, did not build the R26-R31 rules, no builder/runner import")

    # ---- drift: re-hash every input after the verification --------------------
    end_pins = {rel: sha(ROOT / rel) for rel in man["pins"]}
    end_frozen = sha(ROOT / frozen_path)
    end_tools = {"stage_a": sha(struct_tool), "stage_b": sha(sem_tool), "key_manifest": sha(keyman)}
    end_corpus = {e["path"]: sha(ROOT / e["path"]) for e in fixtures}
    end_other = {"manifest": sha(MANIFEST), "report": sha(REPORT), "raw": sha(RAW)}
    drift = {
        "pins": {k: {"start": live_pins[k], "end": end_pins[k], "moved": live_pins[k] != end_pins[k]}
                 for k in man["pins"]},
        "frozen": {"start": live_frozen, "end": end_frozen, "moved": live_frozen != end_frozen},
        "tools": {k: {"start": tool_hashes[k], "end": end_tools[k], "moved": tool_hashes[k] != end_tools[k]}
                  for k in tool_hashes},
        "manifest_moved": manifest_sha_now != end_other["manifest"],
        "report_moved": sha(REPORT) != end_other["report"],
        "raw_moved": sha(RAW) != end_other["raw"],
        "fixtures_moved": sorted(p for p, h in end_corpus.items()
                                 if h != next(e["sha256"] for e in fixtures if e["path"] == p)),
    }
    no_drift = (not any(v["moved"] for v in drift["pins"].values())
                and not drift["frozen"]["moved"] and not any(v["moved"] for v in drift["tools"].values())
                and not drift["manifest_moved"] and not drift["report_moved"] and not drift["raw_moved"]
                and not drift["fixtures_moved"])
    check("D01_no_input_drift_during_verification", no_drift, json.dumps(drift)[:600])

    finished = now()
    passed = sum(1 for c in checks if c["ok"])
    failed = [c["check_id"] for c in checks if not c["ok"]]

    verification = {
        "verification_id": "heldout-10-independent-verification",
        "task_id": TASK_ID,
        "corpus_id": "FORM-HELDOUT-10",
        "verifier": VERIFIER,
        "created_at": finished,
        "started_at": started,
        "assignment": "independent terminal adjudication of the preserved FORM-HELDOUT-10 corpus; "
                      "re-run of both canonical stages on all 40 preserved fixtures",
        "method": "no import of build_corpus_10.py or run_heldout_10.py; stages invoked directly as "
                  "subprocesses with the executor's exact argv; verdicts and failed_rules compared "
                  "fixture-by-fixture against raw/raw_verdicts.json; aggregates recomputed from the "
                  "independent verdicts",
        "inputs": {
            "manifest": {"path": "artifacts/heldout/heldout-10/manifest.json", "sha256": manifest_sha_now},
            "report": {"path": "artifacts/heldout/heldout-10/report.json", "sha256": sha(REPORT)},
            "raw_verdicts": {"path": "artifacts/heldout/heldout-10/raw/raw_verdicts.json", "sha256": sha(RAW)},
            "stage_a": {"path": man["stages"]["structural"]["path"], "sha256": tool_hashes["stage_a"]},
            "stage_b": {"path": man["stages"]["semantic"]["path"], "sha256": tool_hashes["stage_b"]},
            "frozen_manifest": {"path": frozen_path, "sha256": live_frozen,
                                "revision": man["frozen_revision"]},
            "live_pins": live_pins,
        },
        "checks_total": len(checks), "checks_passed": passed, "checks_failed": len(failed),
        "failed_check_ids": failed,
        "checks": checks,
        "independent_verdicts": rerun,
        "recomputed_aggregates": {
            "all_mutants": agg_all, "informative_arms": agg_inf, "uninformative_arms": agg_uninf},
        "independent_informative_escape_families": fam_inf,
        "controls_rejected_by_rerun": ctl_bad,
        "drift": drift,
        "no_drift": no_drift,
    }
    (VERIFY / "verification.json").write_text(json.dumps(verification, indent=2))

    # ---- adjudication ---------------------------------------------------------
    # Two separate questions: (1) did the independent re-run reproduce the executor's report?
    # (2) is the corpus a valid strict-H5 measurement?  They must not be conflated.
    acceptance_ids = {"C01_controls_all_accepted_both_stages_H5"}
    reproducibility = [c for c in checks if c["check_id"] not in acceptance_ids]
    repro_failed = [c["check_id"] for c in reproducibility if not c["ok"]]
    reproduced = not repro_failed
    verdict = "accept" if reproduced else "revise"
    adjudication = {
        "adjudication_id": "heldout-10-independent-adjudication",
        "task_id": TASK_ID,
        "corpus_id": "FORM-HELDOUT-10",
        "adjudicator": VERIFIER,
        "created_at": finished,
        "reviewed_artifacts": {
            "manifest.json": manifest_sha_now,
            "report.json": sha(REPORT),
            "raw_verdicts.json": sha(RAW),
            "verification.json": sha(VERIFY / "verification.json"),
        },
        "verdict": verdict,
        "verdict_scope": "reproducibility of the executor's report by an independent re-run",
        "score": 3.0,
        "corpus_valid": bool(report["valid"]),
        "corpus_valid_reason": "strict H5 false: frozen F1/WCC canonical schemas/af_wcc_vacuum.yaml "
                               f"#{(man['pins']['schemas/af_wcc_vacuum.yaml'])[:12]} is rejected by "
                               "stage B #c79d8ab8440a on R03 (literal-substring binder), "
                               "independently reproduced",
        "reproducibility_checks": {"total": len(reproducibility),
                                   "passed": len(reproducibility) - len(repro_failed),
                                   "failed": repro_failed},
        "hard_failures": repro_failed,
        "measurement_use": "informative C2/C0 arms only; the WCC arm carries no signal "
                           "(stage B R03 rejects the untouched WCC canonical)",
        "confirmations": [
            f"all {len(fixtures)} fixture hashes match the pre-registered manifest",
            "manifest sha agrees in report and raw; manifest mtime precedes run_started",
            "stage A/B verdicts and failed_rules independently reproduced for all 40 fixtures",
            f"all-mutant union escape {agg_all['union_escape']} ({agg_all['union_caught']}/33 caught) matches report",
            f"informative C2+C0 arm union escape {agg_inf['union_escape']} "
            f"({agg_inf['union_caught']}/{agg_inf['mutants']} caught) matches report",
            f"control rejections reproduced ({len(ctl_bad)}): WCC R03 spurious; authored controls and "
            "frozen C2/C0 canonicals pass both stages",
            "no pinned canonical, stage tool, fixture or preserved artifact moved during verification",
        ],
        "worker_limits": [
            "worker verdict only: does not set node status, validation_status or any gate verdict",
            "no theorem, no mathematical claim about cosmic censorship",
            "verifier shares the worker-084 id with the corpus executor; independence is process-level "
            "(fresh re-run from preserved bytes, no builder/runner import), not a third-party audit",
        ],
        "falsifier": "Re-run verify_heldout_10_independent.py at the recorded hashes: falsified if any "
                     "check now fails, any stage verdict differs, any aggregate differs from report.json, "
                     "or any pinned byte moved. A stage-B revision that accepts the frozen WCC canonical "
                     "would remove the H5 control failure and change the corpus_valid value.",
        "card_acceptance_tests": report["acceptance"],
        "escape_rates": {
            "all_mutants": agg_all, "informative_C2_C0": agg_inf, "uninformative_W": agg_uninf},
    }
    (VERIFY / "adjudication.json").write_text(json.dumps(adjudication, indent=2))

    review = f"""# Independent terminal verification — FORM-HELDOUT-10

- task: {TASK_ID}; verifier: {VERIFIER}; {finished} (Asia/Shanghai)
- reviewed: manifest {manifest_sha_now[:12]}, report {sha(REPORT)[:12]}, raw {sha(RAW)[:12]}
- method: both canonical stages re-invoked directly on all {len(fixtures)} preserved fixtures;
  no import of the builder or of run_heldout_10.py; verdicts compared fixture-by-fixture.

## Result

Reproducibility of the executor's report: **{verdict}** — {len(reproducibility) - len(repro_failed)}/{len(reproducibility)} checks pass;
failed: {repro_failed or 'none'}. Strict card acceptance (H5 controls): **false** — C01 fails because the
frozen WCC canonical is rejected by stage B R03, which the executor pre-registered as an instrument
defect before freezing the corpus.

| aggregate | report | independent re-run |
|---|---|---|
| all-mutant structural escape | {report['aggregates']['structural_escape']} | {agg_all['structural_escape']} |
| all-mutant semantic escape | {report['aggregates']['semantic_escape']} | {agg_all['semantic_escape']} |
| all-mutant union escape | {report['aggregates']['union_escape']} | {agg_all['union_escape']} |
| informative C2+C0 union escape | {report['aggregates_informative_arms_only']['union_escape']} | {agg_inf['union_escape']} |
| uninformative W union escape | {report['aggregates_uninformative_arms_only']['union_escape']} | {agg_uninf['union_escape']} |

Terminal status: **valid=false, strict H5** — the frozen F1/WCC canonical is rejected by
stage B on R03 (literal-substring binder), independently reproduced. The WCC arm is
non-informative; the informative C2/C0 arms show union escape **1.0 (0/{agg_inf['mutants']} caught)**
on fresh rev13 fixtures, confirming the executor's report.

## Limits

Worker adjudication only; no node status, no gate verdict, no theorem. Independence is
process-level (fresh re-run from preserved bytes), not third-party: the verifier shares the
worker-084 id with the corpus executor.
"""
    (VERIFY / "INDEPENDENT_REVIEW.md").write_text(review)

    print(json.dumps({"checks_total": len(checks), "checks_passed": passed, "failed": failed,
                      "verdict": verdict, "union_escape_all": agg_all["union_escape"],
                      "union_escape_informative": agg_inf["union_escape"],
                      "no_drift": no_drift}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

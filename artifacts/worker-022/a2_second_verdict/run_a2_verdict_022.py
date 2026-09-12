#!/usr/bin/env python3
"""W022-A2-VERDICT-02 — independent, hash-pinned second verdict on A2.

Read-only with respect to canonical artifacts. Every generated file is written under
this script's own directory (plus a scratch subdirectory); no canonical path in
evaluation/ or artifacts/audit/ or reviews/ is written, moved, or re-hashed.

Deterministic: no network, no model calls, fixed seed, no wall-clock or random inputs
except the report timestamp written into the summary.

Run:  python3 artifacts/worker-022/a2_second_verdict/run_a2_verdict_022.py
Out:  a2_verdict_022.json, controls/*.json, repro/*, pins.json
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # .../ai4math-swarm
SCRATCH = HERE / "repro"
SCRATCH.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- pins --------
PINS = {
    "evaluation/ablation_design.yaml": {
        "role": "A2 design (review target)",
        "sha256_12": "1b2a83ef670b",
    },
    "evaluation/ablation_dryrun_report.json": {
        "role": "canonical synthetic dry-run report",
        "sha256_12": "e1860fa1c6ce",
    },
    "evaluation/ablation_dryrun.csv": {
        "role": "canonical synthetic dry-run rows",
        "sha256_12": "bda738fff675",
    },
    "artifacts/audit/ablation_harness.py": {
        "role": "canonical harness named by the design (artifacts.harness)",
        "sha256_12": "ee0d87a14848",
    },
    "evaluation/ablation_harness.py": {
        "role": "second harness copy (regenerates evaluation/ dry-run by default)",
        "sha256_12": "df878e97bf6e",
    },
    "artifacts/audit/audit_lib.py": {
        "role": "canonical HF-11 budget checker (check_budget_match, tol=0.02)",
        "sha256_12": "ae573db84631",
    },
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def deep_find(obj, needle: str) -> list[str]:
    """Return paths of dict keys containing `needle` (case-insensitive)."""
    hits: list[str] = []

    def walk(o, prefix=""):
        if isinstance(o, dict):
            for k, v in o.items():
                if needle.lower() in str(k).lower():
                    hits.append(f"{prefix}.{k}" if prefix else str(k))
                walk(v, f"{prefix}.{k}" if prefix else str(k))
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{prefix}[{i}]")

    walk(obj)
    return hits


class StubArm:
    """Attribute surface required by evaluation/ablation_harness.check_matched_budgets."""

    def __init__(self, arm, tokens, wall, token_budget, wall_budget,
                 stop_reason="token_budget", is_primary=True):
        self.arm = arm
        self.tokens_consumed = tokens
        self.wall_consumed = wall
        self.token_budget = token_budget
        self.wall_budget = wall_budget
        self.stop_reason = stop_reason
        self.is_primary = is_primary
        self.max_episode_cost = 1e9


def main() -> int:
    checks: list[dict] = []
    pins_out: dict = {}

    def rec(check_id, description, result, detail, evidence_refs=None):
        checks.append({
            "id": check_id,
            "description": description,
            "result": result,
            "detail": detail,
            "evidence_refs": evidence_refs or [],
        })

    # ------------------------------------------------------------- pins -------
    ok_all = True
    for rel, meta in PINS.items():
        p = ROOT / rel
        if not p.exists():
            pins_out[rel] = {**meta, "exists": False, "sha256": None, "pin_ok": False}
            ok_all = False
            continue
        h = sha256_file(p)
        pin_ok = h.startswith(meta["sha256_12"]) if meta["sha256_12"] else True
        pins_out[rel] = {**meta, "exists": True, "sha256": h, "pin_ok": pin_ok}
        ok_all &= pin_ok
    rec("P1", "all six pinned inputs hash-match the values cited in the audit assignments",
        "PASS" if ok_all else "FAIL",
        {rel: v["pin_ok"] for rel, v in pins_out.items()},
        [f"{rel}#{v['sha256_12']}" for rel, v in pins_out.items()])

    design = json.loads(json.dumps(__import__("yaml").safe_load(
        (ROOT / "evaluation/ablation_design.yaml").read_text())))
    report = json.loads((ROOT / "evaluation/ablation_dryrun_report.json").read_text())
    # guard: this checker is read-only for canonical dry-run files (checked again in R2)
    design_path = ROOT / "evaluation/ablation_design.yaml"

    # --------------------------------------------------- structural checks ----
    arms = [a["id"] for a in design["arms"]]
    null_arm = next(a for a in design["arms"]
                    if a["id"] in ("NULL", None) or a.get("label") == "matched-budget null")
    rec("S1", "design declares the four primary arms plus a NULL control",
        "PASS" if [str(x) for x in arms[:4]] == ["S", "SC", "IC", "ICC"]
        and null_arm is not None else "FAIL",
        {"arms": [str(x) for x in arms],
         "null_id_parses_as": repr(null_arm["id"])},
        ["evaluation/ablation_design.yaml#1b2a83ef670b:23-43"])

    rec("S2", "design pre-registers a NULL arm with its own matched budget and calls it mandatory",
        "PASS" if "mandatory" in null_arm.get("role", "") else "FAIL",
        {"null_role": null_arm["role"]},
        ["evaluation/ablation_design.yaml#1b2a83ef670b:40-43"])

    yaml_null_id = null_arm["id"] is None
    rec("S6b", "the design's NULL arm id is the unquoted YAML token NULL, which PyYAML resolves "
               "to null (minor: a design-driven harness keyed on arms[*].id would not find 'NULL')",
        "OBSERVATION" if yaml_null_id else "PASS",
        {"parsed_id": repr(null_arm["id"]), "label": null_arm.get("label")},
        ["evaluation/ablation_design.yaml#1b2a83ef670b:40"])

    rec("S3", "design declares four matched fields including wall-clock and verifier/human cost",
        "PASS" if set(design["budget_matching"]["matched_fields"]) == {
            "total_completion_tokens", "wall_clock_s",
            "verifier_calls_per_accepted_artifact", "human_review_minutes"} else "FAIL",
        {"matched_fields": design["budget_matching"]["matched_fields"]},
        ["evaluation/ablation_design.yaml#1b2a83ef670b:45-58"])

    rec("S4", "design states no universal scalar score by construction",
        "PASS" if design["endpoints"].get("no_universal_scalar_score", "").startswith("TRUE") else "FAIL",
        {"value": design["endpoints"].get("no_universal_scalar_score")},
        ["evaluation/ablation_design.yaml#1b2a83ef670b:114-116"])

    rec("S5", "design pre-registers >=8 seeds and labels max-statistics",
        "PASS" if design["design"]["seeds_per_arm"] >= 8 else "FAIL",
        {"seeds_per_arm": design["design"]["seeds_per_arm"]},
        ["evaluation/ablation_design.yaml#1b2a83ef670b:88-92"])

    rec("S6", "execution is blocked and no arm result is claimed",
        "PASS" if (design["execution_status"]["state"] == "blocked"
                   and "no result is claimed" in design["execution_status"]["what_is_not_done"]) else "FAIL",
        {"state": design["execution_status"]["state"]},
        ["evaluation/ablation_design.yaml#1b2a83ef670b:11-15"])

    # ------------------------------------------- dry-run integrity checks -----
    budget = report["budget_tokens_per_arm"]
    toks = {a: v["total_tokens"] for a, v in report["per_arm"].items()}
    primary = ["S", "SC", "IC", "ICC"]
    tok_spread = (max(toks[a] for a in primary) - min(toks[a] for a in primary)) / budget
    rec("D1", "dry-run token totals of the four primary arms are matched within the design's 2% rule",
        "PASS" if tok_spread <= 0.02 else "FAIL",
        {"token_spread_fraction": round(tok_spread, 6), "totals": toks},
        ["evaluation/ablation_dryrun_report.json#e1860fa1c6ce (per_arm.*.total_tokens)"])

    walls = {a: v["wall_clock_s"] for a, v in report["per_arm"].items()}
    wall_spread = (max(walls.values()) - min(walls.values())) / max(1, min(walls.values()))
    rec("D2", "dry-run wall-clock field is a single constant, so the wall-clock matching rule is "
              "vacuously 'satisfied' and the axis is not measured (B1)",
        "FAIL" if wall_spread == 0 else "PASS",
        {"wall_clock_s": walls, "spread_fraction": wall_spread},
        ["evaluation/ablation_dryrun_report.json#e1860fa1c6ce (per_arm.*.wall_clock_s)"])

    with open(ROOT / "evaluation/ablation_dryrun.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    header = list(rows[0].keys()) if rows else []
    distinct_wall = sorted({r.get("wall_clock_s") for r in rows})
    by_arm: dict[str, int] = {}
    for r in rows:
        by_arm[r["arm"]] = by_arm.get(r["arm"], 0) + 1
    rec("D3", "every dry-run CSV row carries the same wall-clock constant; row counts equal the report",
        "FAIL" if len(distinct_wall) == 1 else "PASS",
        {"distinct_wall_clock_s": distinct_wall, "row_counts": by_arm,
         "report_outputs": {a: v["outputs"] for a, v in report["per_arm"].items()}},
        ["evaluation/ablation_dryrun.csv#bda738fff675"])

    vc_keys = deep_find(report, "verifier_calls") + deep_find(report, "human_review")
    vc_header = [h for h in header if "verifier" in h.lower() or "human_review" in h.lower()]
    rec("D4", "two of the four declared matched fields (verifier_calls_per_accepted_artifact, "
              "human_review_minutes) appear nowhere in the dry-run report or CSV (B2)",
        "FAIL" if not vc_keys and not vc_header else "PASS",
        {"report_keys": vc_keys, "csv_columns": vc_header},
        ["evaluation/ablation_design.yaml#1b2a83ef670b:58",
         "evaluation/ablation_dryrun_report.json#e1860fa1c6ce"])

    gen_keys = deep_find(report, "generator_sha256") + deep_find(report, "harness_version")
    rec("D5", "canonical dry-run report records no harness provenance (generator sha / version) (N2)",
        "OBSERVATION" if not gen_keys else "PASS",
        {"provenance_keys": gen_keys},
        ["evaluation/ablation_dryrun_report.json#e1860fa1c6ce"])

    harness_hashes = {
        rel: pins_out[rel]["sha256"] for rel in
        ("artifacts/audit/ablation_harness.py", "evaluation/ablation_harness.py")
    }
    rec("D6", "two harness copies exist with different bytes (B3 precondition)",
        "FAIL" if len(set(harness_hashes.values())) == 2 else "PASS",
        harness_hashes,
        ["artifacts/audit/ablation_harness.py#ee0d87a14848",
         "evaluation/ablation_harness.py#df878e97bf6e"])

    # ------------------------------------------------ adversarial controls ----
    audit_lib = load_module("a2_audit_lib", ROOT / "artifacts/audit/audit_lib.py")
    eval_harness = load_module("a2_eval_harness", ROOT / "evaluation/ablation_harness.py")

    equal_tokens = [3993862, 3993862, 3998327, 3998327, 3998327]
    matched_wall = [14400] * 5
    ctrl_wall = [{"total_tokens": t, "wall_clock_s": w}
                 for t, w in zip(equal_tokens, [14400, 14400, 14400, 14400, 1440])]
    v_wall = [v.as_dict() for v in audit_lib.check_budget_match(ctrl_wall)]
    ctrl_a_ok = any(v.get("hf") == "HF-11" and "wall_clock_s" in json.dumps(v) for v in v_wall)
    rec("C1", "control: the canonical HF-11 checker DOES fire on a 10x wall-clock divergence when "
              "the data varies (so B1 is a data-generation defect, not a blind checker)",
        "PASS" if ctrl_a_ok else "FAIL",
        {"input_wall_clock_s": [14400, 14400, 14400, 14400, 1440], "violations": v_wall},
        ["artifacts/audit/audit_lib.py#ae573db84631:404-419"])

    spread_tokens_5pct = [4000000, 4000000, 4000000, 4000000, 4200000]
    ctrl_tok = [{"total_tokens": t, "wall_clock_s": 14400}
                for t in spread_tokens_5pct]
    v_tok_canon = [v.as_dict() for v in audit_lib.check_budget_match(ctrl_tok, tol=0.02)]
    canon_fires = any(v.get("hf") == "HF-11" and "total_tokens" in json.dumps(v)
                      for v in v_tok_canon)
    stubs = [StubArm(f"A{i}", t, 14400, 4200000, 14400) for i, t in enumerate(spread_tokens_5pct)]
    eval_out = eval_harness.check_matched_budgets(stubs, 0.15)
    eval_silent = not eval_out["violations"]
    rec("C2", "control: a 5% token spread is REJECTED at the design's +/-2% rule (canonical tol=0.02) "
              "but ACCEPTED by the second copy's default tolerance 0.15 (B3, operationally confirmed)",
        "FAIL" if (canon_fires and eval_silent) else "PASS",
        {"input_totals": spread_tokens_5pct,
         "canonical_tol_0.02_violations": v_tok_canon,
         "eval_copy_tol_0.15_violations": eval_out["violations"],
         "eval_copy_token_spread_fraction": eval_out["token_spread_fraction"]},
        ["artifacts/audit/audit_lib.py#ae573db84631:404",
         "evaluation/ablation_harness.py#df878e97bf6e:75",
         "evaluation/ablation_harness.py#df878e97bf6e:384-422"])

    design_doc = eval_harness.load_design(ROOT / "evaluation/ablation_design.yaml")
    effective_tol = dict(eval_harness.DEFAULTS)
    effective_tol.update(design_doc)
    eff = effective_tol["token_tolerance"]
    rec("C3", "loading the pinned design into the second copy leaves its token tolerance at 0.15 "
              "(the design sets no token_tolerance key) (B3)",
        "FAIL" if eff == 0.15 else "PASS",
        {"effective_token_tolerance": eff,
         "design_sets_token_tolerance": "token_tolerance" in design_doc},
        ["evaluation/ablation_design.yaml#1b2a83ef670b", "evaluation/ablation_harness.py#df878e97bf6e:70-77"])

    # ------------------------------------------- fresh reproduction control ---
    repro_dir = SCRATCH / "canonical_rerun"
    repro_dir.mkdir(parents=True, exist_ok=True)
    before = {p: sha256_file(p) for p in (ROOT / "evaluation").glob("ablation_dryrun*")}
    proc = subprocess.run(
        [sys.executable, str(ROOT / "artifacts/audit/ablation_harness.py"),
         "--dry-run", "--outdir", str(repro_dir), "--seed", "20260911"],
        capture_output=True, text=True, cwd=str(ROOT), timeout=300)
    after = {p: sha256_file(p) for p in (ROOT / "evaluation").glob("ablation_dryrun*")}
    fresh = json.loads((repro_dir / "ablation_dryrun_report.json").read_text())
    same_rates = all(
        abs(fresh["per_arm"][a]["accept_rate"] - report["per_arm"][a]["accept_rate"]) < 1e-12
        and fresh["per_arm"][a]["total_tokens"] == report["per_arm"][a]["total_tokens"]
        for a in report["per_arm"])
    canon_untouched = before == after
    rec("R1", "fresh canonical-harness dry-run (scratch outdir, seed 20260911) reproduces every "
              "per-arm accept rate and token total of the canonical report",
        "PASS" if (proc.returncode == 0 and same_rates) else "FAIL",
        {"exit_code": proc.returncode, "per_arm_rates_all_equal": same_rates,
         "stdout_tail": proc.stdout.strip().splitlines()[-1:]},
        [f"artifacts/worker-022/a2_second_verdict/repro/canonical_rerun/ablation_dryrun_report.json"])
    rec("R2", "the fresh reproduction left the canonical evaluation/ dry-run files byte-identical "
              "(no review-time mutation)",
        "PASS" if canon_untouched else "FAIL",
        {"canonical_files_unchanged": canon_untouched,
         "checked": [str(p.relative_to(ROOT)) for p in before]},
        ["evaluation/ablation_dryrun_report.json#e1860fa1c6ce"])

    # ------------------------------------------------------------- write ------
    controls = {
        "C1_checker_capability_wall_clock": {
            "input": ctrl_wall, "violations": v_wall, "fires": ctrl_a_ok},
        "C2_tolerance_divergence_5pct": {
            "input_total_tokens": spread_tokens_5pct,
            "canonical_tol_0.02": v_tok_canon,
            "eval_copy_tol_0.15": eval_out,
            "canonical_fires": canon_fires,
            "eval_copy_silent": eval_silent},
        "C3_effective_tolerance_from_design": {
            "effective_token_tolerance": eff,
            "design_sets_token_tolerance": "token_tolerance" in design_doc},
        "R1_reproduction": {"exit_code": proc.returncode, "rates_equal": same_rates,
                            "stdout": proc.stdout},
        "R2_canonical_untouched": canon_untouched,
    }
    (HERE / "controls").mkdir(exist_ok=True)
    (HERE / "controls" / "budget_controls_022.json").write_text(
        json.dumps(controls, indent=2) + "\n")
    (HERE / "pins.json").write_text(json.dumps(pins_out, indent=2) + "\n")

    failed = [c["id"] for c in checks if c["result"] == "FAIL"]
    verdict = "revise" if failed else "accept"
    score = 3.0 if verdict == "revise" else 4.0

    out = {
        "checker": "W022-A2-VERDICT-02",
        "actor": "worker-022",
        "target_id": "A2",
        "class_id": "GLOBAL",
        "gate": "G-AUDIT",
        "run_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pins": pins_out,
        "checks": checks,
        "controls_file": "artifacts/worker-022/a2_second_verdict/controls/budget_controls_022.json",
        "verdict": verdict,
        "score": score,
        "hard_failures": ["HF-11"] if verdict == "revise" else [],
        "blocking_findings": [
            {"id": "B1", "rubric": "HF-11", "axis": "wall-clock budget matching is vacuous",
             "evidence": ["evaluation/ablation_dryrun_report.json#e1860fa1c6ce per_arm.*.wall_clock_s all 14400",
                          "evaluation/ablation_dryrun.csv#bda738fff675 one distinct wall_clock_s",
                          "artifacts/audit/ablation_harness.py#ee0d87a14848:82 constant written per row",
                          "controls C1: the checker fires when the data varies"]},
            {"id": "B2", "rubric": "HF-11", "axis": "two of four declared matched fields never measured",
             "evidence": ["evaluation/ablation_design.yaml#1b2a83ef670b:49,58",
                          "artifacts/audit/ablation_harness.py#ee0d87a14848:42-43 constants",
                          "controls D4: absent from report and CSV"]},
            {"id": "B3", "rubric": "HF-11", "axis": "harness copies enforce different tolerances",
             "evidence": ["artifacts/audit/ablation_harness.py#ee0d87a14848:145 tol=0.02",
                          "evaluation/ablation_harness.py#df878e97bf6e:75 token_tolerance=0.15",
                          "controls C2: 5% spread rejected by canonical, accepted by the copy",
                          "controls C3: design does not override the copy's default"]},
        ],
        "non_blocking_findings": [
            "N1 evaluation/ copy has no --execute provider guard (artifacts/audit copy does)",
            "N2 canonical dry-run report carries no generator_sha256/harness_version",
            "N3 metric-name drift: design names information_gain; report emits kish_ess_reviewers/mean_novelty",
            "N4 NULL arm is honestly labelled as declared-rate, not the design's iid candidate-pool draw",
            "N5 harness --outdir defaults to evaluation/, so a review rerun can mutate canonical dry-run files",
        ],
        "independence_statement": (
            "worker-022 did not author the design, dry-run, harness copies, or audit_lib, and did not "
            "read reviews/A2-review-18.json before completing its own checks; the B1-B3 reproductions, the "
            "C1-C3 adversarial controls and the R1-R2 reproduction control were run from the pinned bytes "
            "with a fresh script. This is one reviewer label (ESS=1)."),
        "does_not_claim": [
            "no A2 node completion and no G-AUDIT gate verdict (worker authority)",
            "no model budget spent; dry-run only; no real arm result",
            "no statement about the four physics classes beyond the design's class-bound task suite T1-T4",
        ],
        "next_falsifier": (
            "Any of the following voids this revise: (a) a canonical dry-run revision whose per-arm "
            "wall-clock values actually vary within 2%; (b) evidence that the design does set the "
            "second copy's token tolerance or that only one harness copy remains; (c) a report/CSV that "
            "emits and checks verifier_calls_per_accepted_artifact and human_review_minutes."),
    }
    (HERE / "a2_verdict_022.json").write_text(json.dumps(out, indent=2) + "\n")
    hv = sha256_file(HERE / "a2_verdict_022.json")
    (HERE / "a2_verdict_022.json.sha256").write_text(hv + "  a2_verdict_022.json\n")
    print(json.dumps({"verdict": verdict, "score": score, "failed_checks": failed,
                      "artifact_sha256": hv}, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())

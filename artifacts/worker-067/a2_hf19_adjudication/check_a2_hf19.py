#!/usr/bin/env python3
"""W067-A2-HF19-ADJUDICATE-01 -- independent adjudication of the three hard
failures claimed in reviews/A2-review-19.json (deepseek-flash-19) at the
pinned hashes.

Read-only on every canonical path.  Fail-closed on hash drift: if any pinned
input differs from the pin recorded below, no probe verdict is emitted
(status=DRIFT, exit 2).  All writes go under --out (default: this directory).

Probe philosophy: this instrument was written from the pinned bytes only; the
adjudicated review (reviews/A2-review-19.json), the review author's probe
(artifacts/worker-019/a2_review/check_a2_independent.py) and any other A2
verdict text were deliberately NOT used to build the checks per-HF: each HF is
re-derived from the artifact under review (design / harnesses / CSV / report),
and the review's own claim is consulted only to decide confirmed/refuted.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
TASK_ID = "W067-A2-HF19-ADJUDICATE-01"
WORKER = "worker-067"
NODE = "A2"
GATE = "G-AUDIT"
CLASS_ID = "GLOBAL"
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

PINS = {
    "evaluation/ablation_design.yaml": "1b2a83ef670b7e757a1a54d4849b49a597d5dc33e9205c0b5b10646d811cfb0a",
    "evaluation/ablation.csv": "ee3aa6cb97d0871a526102654fb9a793680c9f7e4f0ef3958b0a8db3648e8d45",
    "evaluation/ablation_report.json": "d7e1cd15abef5db56be8211ec512d00bd14dd0163cfc2793b6f10e6e25639e5a",
    "evaluation/ablation_harness.py": "df878e97bf6ede6c41e540dcf20664e51c9963cf44d74c2f5f9a9005bc8af432",
    "evaluation/ablation_dryrun.csv": "bda738fff675433324e3d97f26e4123ec53bef2ceb610270db10c466b446c76f",
    "evaluation/ablation_dryrun_report.json": "e1860fa1c6ceab4891f64e1122e80f318bfdab02cb5e5da9493e9e398cc3605b",
    "artifacts/audit/ablation_harness.py": "ee0d87a14848b77cbc49978f6abb1b096b6978662773a730f3ba6638a8dd87a2",
    "artifacts/audit/audit_lib.py": "ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c",
    "reviews/A2-review-19.json": "36edeff97014803aeab2e85d7bac50aed47a932db37924a3d6af58e71d927468",
}

PROVENANCE_RE = re.compile(
    r"sim|simulat|synthetic|dry|dryrun|dry_run|status|provenance|generator|source", re.I
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_pins() -> dict:
    out = {}
    for rel, want in PINS.items():
        p = REPO / rel
        out[rel] = {
            "exists": p.exists(),
            "sha256": sha256(p) if p.exists() else None,
            "pinned": want,
            "match": p.exists() and sha256(p) == want,
        }
    return out


def function_source(src: str, name: str):
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node), node
    return None, None


def dict_default(src: str, key: str):
    """Return the literal value of `"key": value` inside a dict literal."""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == key:
                    try:
                        return ast.literal_eval(v)
                    except Exception:
                        return f"<non-literal {ast.dump(v)[:60]}>"
    return None


def arg_default(src: str, func: str, arg: str):
    """Return the literal default of `arg` in `def func(...)`."""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func:
            args = list(node.args.args)
            defaults = list(node.args.defaults)
            offset = len(args) - len(defaults)
            for i, a in enumerate(args):
                if a.arg == arg and i >= offset:
                    try:
                        return ast.literal_eval(defaults[i - offset])
                    except Exception:
                        return f"<non-literal {ast.dump(defaults[i - offset])[:60]}>"
    return None


def adjudicate() -> dict:
    design_raw = (REPO / "evaluation/ablation_design.yaml").read_text()
    design = yaml.safe_load(design_raw)
    harness_big = (REPO / "evaluation/ablation_harness.py").read_text()
    harness_small = (REPO / "artifacts/audit/ablation_harness.py").read_text()
    audit_lib = (REPO / "artifacts/audit/audit_lib.py").read_text()
    report = json.loads((REPO / "evaluation/ablation_report.json").read_text())
    dryrun_report = json.loads((REPO / "evaluation/ablation_dryrun_report.json").read_text())
    csv_lines = (REPO / "evaluation/ablation.csv").read_text().splitlines()
    review = json.loads((REPO / "reviews/A2-review-19.json").read_text())
    review_claim = {f["id"]: f for f in review["findings"]}

    findings = {}

    # ---------------- HF-19-01: registered artifact is an unmarked dry-run ----
    header = [c.strip() for c in csv_lines[0].split(",")] if csv_lines else []
    marker_cols = [c for c in header if PROVENANCE_RE.search(c)]
    inventory = design.get("artifacts", {})
    inv_paths = [v for v in inventory.values() if isinstance(v, str)]
    registered_in_inventory = any("evaluation/ablation.csv" == p.split(" ")[0] for p in inv_paths)
    report_gen = report.get("generator_sha256")
    report_assignment = str(report.get("assignment", ""))
    dryrun_named = [v for v in inv_paths if "ablation_dryrun.csv" in v]
    h1 = {
        "csv_columns": len(header),
        "csv_provenance_columns": marker_cols,
        "csv_has_machine_readable_provenance": bool(marker_cols),
        "report_generator_sha256": report_gen,
        "report_generator_is_evaluation_harness": report_gen
        == PINS["evaluation/ablation_harness.py"],
        "report_assignment": report_assignment,
        "report_declares_synthetic_dry_run": bool(
            re.search(r"synthetic dry-run|no model calls", report_assignment, re.I)
        ),
        "registered_path": "evaluation/ablation.csv",
        "registered_path_named_in_design_inventory": registered_in_inventory,
        "design_inventory_dryrun_paths": dryrun_named,
    }
    h1["claim_check"] = review_claim["A2-19-01"]["finding"]
    h1["verdict"] = (
        "CONFIRMED"
        if (
            not marker_cols
            and report_gen == PINS["evaluation/ablation_harness.py"]
            and "synthetic dry-run" in report_assignment.lower()
            and not registered_in_inventory
        )
        else "REFUTED"
    )
    findings["HF-A2-19-01_registered_artifact_unmarked_dryrun"] = h1

    # ---------------- HF-19-02: dual harness + unmatched fields --------------
    big_tol = dict_default(harness_big, "token_tolerance")
    small_tol = arg_default(audit_lib, "check_budget_match", "tol")
    cmb_src, _ = function_source(harness_big, "check_matched_budgets")
    cmb_lines = (cmb_src or "").splitlines()
    wall_lines = [l.strip() for l in cmb_lines if "wall" in l]
    spread_lines = [
        l.strip()
        for l in cmb_lines
        if "spread" in l.lower() or ("max(" in l and "min(" in l)
    ]
    wall_spread_lines = [
        l.strip()
        for l in cmb_lines
        if "wall" in l and ("spread" in l.lower() or ("max(" in l and "min(" in l))
    ]
    tol_use_lines = [l.strip() for l in cmb_lines if "tolerance" in l]
    # locate the tolerance default in the small harness's own definition, if any
    small_fn, _ = function_source(harness_small, "check_budget_match")
    design_matched = design.get("budget_matching", {}).get("matched_fields", [])
    emitted_blob = "\n".join(csv_lines) + json.dumps(report) + json.dumps(dryrun_report)
    design_harness_path = inventory.get("harness")
    h2 = {
        "design_names_harness": design_harness_path,
        "design_names_audit_harness": design_harness_path
        == "artifacts/audit/ablation_harness.py",
        "registered_generator_harness": "evaluation/ablation_harness.py",
        "two_harnesses_byte_different": PINS["artifacts/audit/ablation_harness.py"]
        != PINS["evaluation/ablation_harness.py"],
        "big_harness_token_tolerance": big_tol,
        "audit_lib_check_budget_match_default_tol": small_tol,
        "tolerances_differ": big_tol != small_tol,
        "check_matched_budgets_wall_lines": wall_lines,
        "check_matched_budgets_wall_spread_lines": wall_spread_lines,
        "check_matched_budgets_tests_wall_spread": bool(wall_spread_lines),
        "check_matched_budgets_tolerance_lines": tol_use_lines,
        "design_matched_fields": design_matched,
        "matched_fields_emitted": {
            f: (f in emitted_blob) for f in design_matched if isinstance(f, str)
        },
        "small_harness_defines_check_budget_match": bool(small_fn),
    }
    h2["claim_check"] = review_claim["A2-19-02"]["finding"]
    h2["verdict"] = (
        "CONFIRMED"
        if (
            h2["two_harnesses_byte_different"]
            and h2["design_names_audit_harness"]
            and h2["tolerances_differ"]
            and not h2["check_matched_budgets_tests_wall_spread"]
            and sum(1 for v in h2["matched_fields_emitted"].values() if not v) >= 2
        )
        else "PARTIAL"
    )
    findings["HF-A2-19-02_dual_harness_and_unenforced_matched_fields"] = h2

    # ---------------- HF-19-03: NULL id parses as None -----------------------
    arm_ids = [a.get("id") for a in design.get("arms", [])]
    null_arm = [a for a in design.get("arms", []) if a.get("label") == "matched-budget null"]
    h3 = {
        "parsed_arm_ids": [("None(null)" if v is None else v) for v in arm_ids],
        "raw_none_position": [i for i, v in enumerate(arm_ids) if v is None],
        "null_arm_declared_label": bool(null_arm),
        "null_arm_declared_role": null_arm[0].get("role") if null_arm else None,
        "yaml_loader": "yaml.safe_load",
        "harness_uses_safe_load_for_design": "yaml.safe_load" in harness_big,
    }
    h3["claim_check"] = review_claim["A2-19-03"]["finding"]
    h3["verdict"] = "CONFIRMED" if None in arm_ids and "yaml.safe_load" in harness_big else "REFUTED"
    findings["HF-A2-19-03_NULL_id_parses_as_None"] = h3

    # ---------------- secondary probes (moderate findings, cheaper) ----------
    sim_null = re.search(r'"NULL"\s*:\s*\{([^}]*)\}', harness_small)
    null_arm_report = next(
        (a for a in report.get("arms", []) if a.get("is_null")), {}
    )
    design_null_text = (null_arm[0].get("composition") if null_arm else "") or ""
    s1 = {
        "design_null_mechanism": design_null_text[:200],
        "small_harness_null_sim_declares_rate": bool(sim_null and "p_accept" in sim_null.group(1)),
        "small_harness_null_sim": sim_null.group(1).strip() if sim_null else None,
        "verdict": "CONFIRMED_AS_DECLARED_RATE_PLACEHOLDER"
        if sim_null and "p_accept" in sim_null.group(1)
        else "REFUTED",
    }
    findings["S-A2-19-04_null_mechanism_is_declared_rate"] = s1
    s2 = {
        "null_arm_tokens_consumed": null_arm_report.get("tokens_consumed"),
        "null_arm_token_budget": null_arm_report.get("token_budget"),
        "null_arm_stop_reason": null_arm_report.get("stop_reason"),
        "null_arm_token_matched": (
            null_arm_report.get("tokens_consumed") == null_arm_report.get("token_budget")
        ),
    }
    s2["verdict"] = (
        "CONFIRMED"
        if s2["null_arm_tokens_consumed"] != s2["null_arm_token_budget"]
        and s2["null_arm_stop_reason"] not in ("token_budget", None)
        else "REFUTED"
    )
    findings["S-A2-19-05_registered_null_run_not_token_matched"] = s2

    # ---------------- controls ----------------------------------------------
    controls = {}

    # C1 mutation: quoting NULL must change the parse result (probe is sensitive)
    mutated = design_raw.replace("- id: NULL", '- id: "NULL"', 1)
    mut_ids = [a.get("id") for a in yaml.safe_load(mutated).get("arms", [])]
    controls["C1_mutation_null_quoting"] = {
        "mutated_arm_ids": [("None(null)" if v is None else v) for v in mut_ids],
        "sensitive": None not in mut_ids and "NULL" in mut_ids,
    }

    # C2 provenance detector positive/negative control
    with tempfile.TemporaryDirectory() as td:
        pos = Path(td) / "marked.csv"
        pos.write_text("arm,status,generator_sha256\nA,simulated,abc\n")
        neg = Path(td) / "unmarked.csv"
        neg.write_text("arm,tokens\nA,1\n")
        controls["C2_provenance_detector"] = {
            "marked_detected": any(
                PROVENANCE_RE.search(c) for c in pos.read_text().splitlines()[0].split(",")
            ),
            "unmarked_detected": any(
                PROVENANCE_RE.search(c) for c in neg.read_text().splitlines()[0].split(",")
            ),
        }
        controls["C2_provenance_detector"]["pass"] = (
            controls["C2_provenance_detector"]["marked_detected"]
            and not controls["C2_provenance_detector"]["unmarked_detected"]
        )

    # C3 drift fail-closed (unit-level: mutate the pin table in memory)
    saved = dict(PINS)
    PINS["evaluation/ablation.csv"] = "0" * 64
    drift = measure_pins()
    controls["C3_fail_closed_on_drift"] = {
        "mutated_pin_reports_mismatch": drift["evaluation/ablation.csv"]["match"] is False,
        "all_other_pins_still_match": all(
            v["match"] for k, v in drift.items() if k != "evaluation/ablation.csv"
        ),
    }
    PINS.clear()
    PINS.update(saved)

    return {
        "findings": findings,
        "controls": controls,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    before = measure_pins()
    drift = [k for k, v in before.items() if not v["match"]]
    if drift:
        report = {
            "task_id": TASK_ID,
            "worker": WORKER,
            "status": "DRIFT",
            "drifted_inputs": drift,
            "pins": before,
            "canonical_writes": 0,
        }
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(f"DRIFT: {drift}")
        return 2

    result = adjudicate()

    # C4 no-write canary: canonical pins unchanged after the probes
    after = measure_pins()
    c4 = {k: (before[k]["sha256"] == after[k]["sha256"]) for k in PINS}
    result["controls"]["C4_canonical_bytes_unchanged"] = {
        "all_unchanged": all(c4.values()),
        "per_input": c4,
    }

    hf = {
        k: v["verdict"] for k, v in result["findings"].items() if k.startswith("HF-")
    }
    report = {
        "schema": "worker-adjudication/v1",
        "task_id": TASK_ID,
        "worker": WORKER,
        "node_id": NODE,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": CLASS_IDS,
        "target_under_adjudication": "reviews/A2-review-19.json",
        "target_sha256": PINS["reviews/A2-review-19.json"],
        "created_at_utc": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "status": "COMPLETE",
        "pins": before,
        "hard_failure_adjudication": hf,
        **result,
        "falsifier": (
            "Withdrawn if any pinned input hash moves, or if an independent re-run of this "
            "script does not reproduce hard_failure_adjudication, or if any HF verdict here is "
            "shown to bind bytes other than the pinned ones."
        ),
        "canonical_writes": 0,
        "authority_note": (
            "Worker adjudication of a peer review's hard failures: advisory; does not set A2 "
            "done, validation_status=passed, or any gate verdict; canonical paths read-only."
        ),
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(hf, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

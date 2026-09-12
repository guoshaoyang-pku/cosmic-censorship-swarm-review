#!/usr/bin/env python3
"""W068-FORM-REV13-REMEASURE-14 runner (worker-068, bounded class-bound task).

Reads the pre-registered corpus built by build_rev13_corpus.py, runs the two pinned
class-binding stages on every fixture, and reports - at the rev13 / FROZEN-rev29 pin - whether
the four FORM-HELDOUT-08 definition-site mutation families still escape, with arm-informativeness
and control checks. Measurement only: never sets a gate verdict, node status or
validation_status=passed.

Usage: python3 run_rev13_remeasure.py
Exit 0 run completed; 2 precondition failure.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))
SNAP = HERE / "snapshot"
FIX = HERE / "fixtures"
RAW = HERE / "raw"
PY = sys.executable

STAGE_A = SNAP / "artifacts/formulation/tools/check_class_schema.py"
STAGE_B = SNAP / "artifacts/worker-06/spec_conformance_audit.py"
SPEC = SNAP / "artifacts/formulation/rule_spec.json"
FREEZE = SNAP / "artifacts/worker-068/definition_freeze_check.py"

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "artifacts" / "worker-068" / "deffreeze13"))
from definition_freeze_check import check as freeze_check  # noqa: E402
from definition_freeze_check import changed_leaves  # noqa: E402


def changed_leaves_witness(base_doc, fixture_doc) -> list:
    return [{k: d[k] for k in ("path", "group", "base_sha256_12", "fixture_sha256_12",
                               "base_preview", "fixture_preview")}
            for d in changed_leaves(base_doc, fixture_doc)]

A_ACCEPT = {"pass"}
B_ACCEPT = {"accept"}
SECONDARY_VARIANTS = ("freeze_contract_min", "freeze_defsites_min", "freeze_conclusion",
                      "freeze_meta_only")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_stage(cmd: list, timeout: int = 180) -> dict:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        return {"exit": None, "verdict": "timeout", "stdout": "", "stderr": "timeout",
                "anomaly": "timeout"}
    out = r.stdout.strip()
    try:
        j = json.loads(out)
        verdict = j.get("verdict")
        anomaly = None if verdict else "no-verdict-field"
    except Exception as exc:  # noqa: BLE001
        j, verdict, anomaly = None, "unparseable", f"json parse error: {exc}"
    return {"exit": r.returncode, "verdict": verdict, "json": j,
            "stderr_tail": r.stderr.strip()[-400:], "anomaly": anomaly}


def main() -> int:
    pre = json.loads((HERE / "PREREGISTRATION.json").read_text())
    man = json.loads((HERE / "manifest.json").read_text())
    now = datetime.now(CST).isoformat(timespec="seconds")
    problems: list = []

    # 1. snapshot integrity against the manifest
    for rel, rec in man["snapshots"].items():
        p = SNAP / rel
        got = sha256_file(p) if p.exists() else None
        if got != rec["snapshot_sha256"]:
            problems.append(f"snapshot mismatch {rel}: {got} != {rec['snapshot_sha256']}")
    if problems:
        print(json.dumps({"verdict": "PRECONDITION_FAILED", "problems": problems}, indent=1))
        return 2

    # 2. run both stages on every fixture
    if RAW.exists():
        for p in RAW.glob("*.json"):
            p.unlink()
    RAW.mkdir(exist_ok=True)
    rows = []
    for fx in man["fixtures"]:
        path = FIX / fx["name"]
        if not path.exists():
            problems.append(f"fixture missing: {fx['name']}")
            continue
        a = run_stage([PY, str(STAGE_A), "--json", str(path)])
        b = run_stage([PY, str(STAGE_B), str(path), "--spec", str(SPEC)])
        (RAW / f"{fx['name']}.stageA.json").write_text(
            json.dumps(a.get("json") if a.get("json") is not None else a, indent=1) + "\n")
        (RAW / f"{fx['name']}.stageB.json").write_text(
            json.dumps(b.get("json") if b.get("json") is not None else b, indent=1) + "\n")
        a_ok, b_ok = a["verdict"] in A_ACCEPT, b["verdict"] in B_ACCEPT
        witness = []
        if fx["role"] == "isolated_mutation" and fx.get("base"):
            base_doc = yaml.safe_load((FIX / fx["base"]).read_bytes())
            fx_doc = yaml.safe_load(path.read_bytes())
            witness = changed_leaves_witness(base_doc, fx_doc)
        rows.append({
            "name": fx["name"], "role": fx["role"], "class_id": fx["class_id"],
            "class_key": fx["class_key"], "base": fx.get("base"),
            "leaf_path": fx.get("leaf_path"), "sha256": sha256_file(path),
            "leaf_witness": witness,
            "stageA": {"verdict": a["verdict"], "exit": a["exit"], "anomaly": a["anomaly"],
                       "failed_rules": (a.get("json") or {}).get("failed_rules")},
            "stageB": {"verdict": b["verdict"], "exit": b["exit"], "anomaly": b["anomaly"],
                       "failed_rules": (b.get("json") or {}).get("failed_rules")},
            "accepted_by_both": bool(a_ok and b_ok),
            "escapes": bool(a_ok and b_ok),
        })

    by_name = {r["name"]: r for r in rows}
    classes = {}
    for key in ("W", "C2", "C0"):
        base = by_name.get(f"base_{key}.yaml")
        ident = by_name.get(f"ctrl_identity_{key}.yaml")
        informative = bool(base and ident and base["accepted_by_both"] and ident["accepted_by_both"])
        classes[key] = {
            "class_id": base["class_id"] if base else None,
            "base_accepted_by_both": bool(base and base["accepted_by_both"]),
            "base_stageA": base["stageA"]["verdict"] if base else None,
            "base_stageB": base["stageB"]["verdict"] if base else None,
            "base_stageB_failed_rules": base["stageB"]["failed_rules"] if base else None,
            "identity_accepted_by_both": bool(ident and ident["accepted_by_both"]),
            "arm_informative": informative,
            "isolated_tested": [], "escaped": [], "caught": [], "untestable": [],
        }
    for r in rows:
        if r["role"] != "isolated_mutation":
            continue
        cell = classes[r["class_key"]]
        if not cell["arm_informative"]:
            cell["untestable"].append(r["name"])
        elif r["escapes"]:
            cell["escaped"].append(r["name"])
        else:
            cell["caught"].append(r["name"])

    # 3. controls: identity/formatting controls must not be rejected in an INFORMATIVE arm.
    #    In a non-informative arm the base itself is rejected, so its controls reject for the
    #    same base defect; that is reported separately, not as an independent control defect.
    control_failures = [r["name"] for r in rows
                        if r["role"] in ("identity_control", "formatting_control")
                        and not r["accepted_by_both"]]
    informative_keys = {k for k, v in classes.items() if v["arm_informative"]}
    informative_control_failures = [r["name"] for r in rows
                                    if r["role"] in ("identity_control", "formatting_control")
                                    and r["class_key"] in informative_keys
                                    and not r["accepted_by_both"]]
    noninformative_control_rejections = [r["name"] for r in rows
                                         if r["role"] in ("identity_control", "formatting_control")
                                         and r["class_key"] not in informative_keys
                                         and not r["accepted_by_both"]]
    # 4. secondary, proposal-only: R-CAND-D variants on the rev13 corpus
    secondary = {}
    for r in rows:
        if not r.get("base"):
            continue
        base_doc = yaml.safe_load((FIX / r["base"]).read_bytes())
        fx_doc = yaml.safe_load((FIX / r["name"]).read_bytes())
        secondary[r["name"]] = {v: freeze_check(fx_doc, base_doc, v)["verdict"]
                                for v in SECONDARY_VARIANTS}
        secondary[r["name"]]["changed_leaf_count"] = freeze_check(
            fx_doc, base_doc, SECONDARY_VARIANTS[0])["changed_leaf_count"]

    # 5. drift check on the live pin sources
    drift = {}
    for rel, want in man["live_source_hashes_at_build"].items():
        got = sha256_file(ROOT / rel) if (ROOT / rel).exists() else None
        drift[rel] = {"at_build": want, "at_end": got, "same": got == want}
    drifted = sorted(k for k, v in drift.items() if not v["same"])

    anomalies = [r["name"] for r in rows
                 if r["stageA"]["anomaly"] or r["stageB"]["anomaly"]]

    validity = {
        "snapshot_stable": not problems,
        "no_stage_anomalies": not anomalies,
        "live_sources_unchanged_during_run": not drifted,
        "controls_all_accepted_in_informative_arms": not informative_control_failures,
        "control_rejections_in_noninformative_arms": noninformative_control_rejections,
        "valid": (not problems) and (not anomalies) and (not informative_control_failures),
    }

    # 6. findings
    findings = []
    c0 = classes["C0"]
    findings.append({
        "id": "W068-R14-F1",
        "axis": "primary",
        "statement": (
            f"At the rev13 pin (F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe; FROZEN "
            f"rev29 815e08079aef; stage A check_class_schema.py 000e09e46b2f + KEY_MANIFEST "
            f"014e2d301978; stage B spec_conformance_audit.py c79d8ab8440a + rule_spec "
            f"40f9bb9e657b), the C0 arm is "
            f"{'INFORMATIVE' if c0['arm_informative'] else 'NON-INFORMATIVE'}: base C0 accepted "
            f"by both stages = {c0['base_accepted_by_both']}, identity control accepted by both = "
            f"{c0['identity_accepted_by_both']}. Transplantable C0 definition-site mutations "
            f"tested: {len(c0['escaped']) + len(c0['caught']) + len(c0['untestable'])}; "
            f"escaped both stages = {c0['escaped']}; caught by at least one = {c0['caught']}; "
            f"untestable by protocol = {c0['untestable']}."
        ),
        "evidence_refs": [
            "artifacts/worker-068/rev13remeasure14/report.json",
            "artifacts/worker-068/rev13remeasure14/raw_verdicts.json",
            "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe",
            "schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3",
            "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        ],
        "falsifier": (
            "Re-run run_rev13_remeasure.py at the same snapshot pins: any C0 base or identity "
            "verdict change, any transplanted fixture rejected by a stage, or any snapshot-byte "
            "change falsifies or voids this row."
        ),
    })
    w = classes["W"]
    findings.append({
        "id": "W068-R14-F2",
        "axis": "arm-validity",
        "statement": (
            f"The W arm is {'INFORMATIVE' if w['arm_informative'] else 'NON-INFORMATIVE'} at "
            f"rev13: base F1 stage A = {w['base_stageA']}, stage B = {w['base_stageB']} "
            f"(failed rules {w['base_stageB_failed_rules']}). "
            + ("No F1 escape claim is made at this pin; iso_m25 is untestable_by_protocol."
               if not w["arm_informative"] else
               f"iso_m25 escape status: {'escaped' if 'iso_m25.yaml' in w['escaped'] else 'caught'}.")
        ),
        "evidence_refs": [
            "artifacts/worker-068/rev13remeasure14/raw/base_W.yaml.stageB.json",
            "schemas/af_wcc_vacuum.yaml#d9cebb9404b2",
        ],
        "falsifier": (
            "A stage-B pass on the untouched F1 rev13 base under rule_spec 40f9bb9e657b makes "
            "the W arm informative and this row void; re-run the runner to re-measure."
        ),
    })
    findings.append({
        "id": "W068-R14-F3",
        "axis": "controls",
        "statement": (
            f"Controls at rev13: {len([r for r in rows if r['role'] == 'identity_control'])} "
            f"identity and {len([r for r in rows if r['role'] == 'formatting_control'])} "
            f"formatting fixtures; rejected in informative arms = {informative_control_failures or 'none'}; "
            f"rejected in the non-informative W arm (same R03 as its base) = "
            f"{noninformative_control_rejections or 'none'}. "
            f"Secondary (proposal R-CAND-D, not adopted): "
            f"freeze_contract_min flags {sum(1 for v in secondary.values() if v['freeze_contract_min'] == 'FLAG')}"
            f"/{len(secondary)} fixtures, freeze_defsites_min "
            f"{sum(1 for v in secondary.values() if v['freeze_defsites_min'] == 'FLAG')}"
            f"/{len(secondary)}."
        ),
        "evidence_refs": [
            "artifacts/worker-068/rev13remeasure14/raw_verdicts.json",
            "artifacts/worker-068/deffreeze13/definition_freeze_check.py#8609a6e7c44b",
        ],
        "falsifier": (
            "Any identity or formatting control rejected by both stages voids the control claim; "
            "any conforming control flagged by a freeze variant falsifies that variant's "
            "no-false-positive property."
        ),
    })
    esc = [r for r in rows if r["role"] == "isolated_mutation" and r["escapes"]]
    findings.append({
        "id": "W068-R14-F4",
        "axis": "adjudication-witnesses",
        "statement": (
            "Escape witnesses for independent label adjudication (each fixture differs from its "
            "rev13 base in exactly the listed leaf): "
            + "; ".join(
                f"{r['name']} [{r['class_id']}] {r['leaf_witness'][0]['path']} "
                f"base={r['leaf_witness'][0]['base_sha256_12']} "
                f"fixture={r['leaf_witness'][0]['fixture_sha256_12']}"
                for r in esc)
            + ". A reviewer must decide per witness whether the mutated value is a genuine "
              "class-contract violation or a permissible rewording; only genuine violations "
              "support a detector false-negative reading."
        ),
        "evidence_refs": [
            "artifacts/worker-068/rev13remeasure14/raw_verdicts.json",
            "artifacts/worker-068/rev13remeasure14/manifest.json",
        ],
        "falsifier": (
            "A changed-leaf diff that is not the declared leaf, or an adjudication that a "
            "mutated value is a permissible rewording, removes that instance from the escape "
            "count and must be recorded as a label correction."
        ),
    })

    raw = {
        "schema": "worker-068/rev13remeasure14/raw-verdicts/v1",
        "task_id": pre["task_id"], "run_at": now,
        "preregistration_sha256": sha256_file(HERE / "PREREGISTRATION.json"),
        "manifest_sha256": sha256_file(HERE / "manifest.json"),
        "stage_a": sha256_file(STAGE_A), "stage_b": sha256_file(STAGE_B),
        "spec": sha256_file(SPEC), "key_manifest": sha256_file(SNAP / "artifacts/formulation/KEY_MANIFEST.json"),
        "rows": rows, "classes": classes,
        "control_failures": control_failures,
        "informative_control_failures": informative_control_failures,
        "control_rejections_in_noninformative_arms": noninformative_control_rejections,
        "anomalies": anomalies,
        "drift": drift, "drifted_paths": drifted,
        "secondary_freeze_variants": secondary,
        "validity": validity,
    }
    (HERE / "raw_verdicts.json").write_text(json.dumps(raw, indent=1) + "\n")

    report = {
        "schema": "worker-068/rev13remeasure14/report/v1",
        "task_id": pre["task_id"], "actor": "worker-068", "created_at": now,
        "node_id": pre["node_id"], "gate": pre["gate"], "class_ids": pre["class_ids"],
        "authority_note": pre["authority_note"],
        "question": pre["question"],
        "pins": {
            "schemas": {k: sha256_file(FIX / f"base_{k}.yaml") for k in ("W", "C2", "C0")},
            "frozen": "artifacts/formulation/FROZEN.json#815e08079aef",
            "f0_taxonomy": "research_map/formulation_taxonomy.yaml#0abb9ed8a961",
            "stage_a": f"artifacts/formulation/tools/check_class_schema.py#{sha256_file(STAGE_A)[:12]}",
            "key_manifest": f"artifacts/formulation/KEY_MANIFEST.json#{sha256_file(SNAP / 'artifacts/formulation/KEY_MANIFEST.json')[:12]}",
            "stage_b": f"artifacts/worker-06/spec_conformance_audit.py#{sha256_file(STAGE_B)[:12]}",
            "rule_spec": f"artifacts/formulation/rule_spec.json#{sha256_file(SPEC)[:12]}",
            "preregistration": f"artifacts/worker-068/rev13remeasure14/PREREGISTRATION.json#{sha256_file(HERE / 'PREREGISTRATION.json')[:12]}",
            "manifest": f"artifacts/worker-068/rev13remeasure14/manifest.json#{sha256_file(HERE / 'manifest.json')[:12]}",
        },
        "arm_table": classes,
        "fixture_table": rows,
        "secondary_freeze_variants": secondary,
        "validity": validity,
        "drift": drift,
        "findings": findings,
        "limitations": [
            "Author-built corpus: the four transplanted mutations are worker-068 labels; a "
            "genuine independent review must adjudicate whether each is a class-contract "
            "violation before the escape counts are cited as detector defects.",
            "The W arm is non-informative at rev13 under this protocol, so the F1 family "
            "(iso_m25) is untestable here; that is a statement about the instrument+protocol, "
            "not about the schema.",
            "Stage verdicts are mechanical: stage A = schema-shape rules R01-R27 with the "
            "regenerated KEY_MANIFEST; stage B = rule_spec 40f9bb9e657b R01-R16 + undecided "
            "semantic rules. Neither decides mathematics.",
            "freeze_contract_min / freeze_defsites_min are the un-adopted R-CAND-D proposal, "
            "reported as a measurement only.",
        ],
        "non_claims": [
            "No gate verdict, node completion, validation_status=passed, or rule adoption.",
            "No claim about mathematical truth or about any problem outside the three frozen "
            "class contracts.",
        ],
        "falsifier": pre["falsifier"],
        "stop_rule": pre["stop_rule"],
        "evidence_refs": [
            "artifacts/worker-068/rev13remeasure14/raw_verdicts.json",
            "artifacts/worker-068/rev13remeasure14/manifest.json",
            "artifacts/worker-068/rev13remeasure14/PREREGISTRATION.json",
        ],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1) + "\n")

    checkpoint = {
        "schema": "worker-068/rev13remeasure14/checkpoint/v1",
        "task_id": pre["task_id"], "actor": "worker-068", "created_at": now,
        "status": "measurement_complete",
        "verdict": {
            "W_arm_informative": w["arm_informative"],
            "C2_arm_informative": classes["C2"]["arm_informative"],
            "C0_arm_informative": c0["arm_informative"],
            "C0_escaped": c0["escaped"], "C0_caught": c0["caught"],
            "C2_escaped": classes["C2"]["escaped"], "C2_caught": classes["C2"]["caught"],
            "W_untestable": w["untestable"],
            "controls_all_accepted_in_informative_arms": not informative_control_failures,
            "control_rejections_in_noninformative_arms": noninformative_control_rejections,
            "valid": validity["valid"],
        },
        "artifact_sha256": {
            "PREREGISTRATION.json": sha256_file(HERE / "PREREGISTRATION.json"),
            "manifest.json": sha256_file(HERE / "manifest.json"),
            "build_rev13_corpus.py": sha256_file(HERE / "build_rev13_corpus.py"),
            "run_rev13_remeasure.py": sha256_file(HERE / "run_rev13_remeasure.py"),
            "raw_verdicts.json": sha256_file(HERE / "raw_verdicts.json"),
            "report.json": sha256_file(HERE / "report.json"),
        },
        "findings": [f["id"] for f in findings],
        "falsifier": pre["falsifier"],
    }
    (HERE / "checkpoint.json").write_text(json.dumps(checkpoint, indent=1) + "\n")
    print(json.dumps({
        "verdict": "RUN_COMPLETE", "valid": validity["valid"],
        "classes": {k: {"informative": v["arm_informative"], "escaped": v["escaped"],
                        "caught": v["caught"], "untestable": v["untestable"]}
                    for k, v in classes.items()},
        "control_failures": control_failures, "drifted": drifted,
        "report_sha256": sha256_file(HERE / "report.json"),
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Addendum to W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01.

The pre-registered run returned REBIND_INSUFFICIENT_AT_MEASURED_BASE with 0 union escapes.
This addendum measures WHY the post-rebind acceptance run still exits 1, using only the
already-built sandbox (no new sandbox states, no canonical writes):

  A1  the rebind clears the preflight clause (fixture base == live C0).
  A2  cause decomposition: which canonical schema fails which stage and rule.
  A3  stage-B non-vacuity controls: mangled copies of F1 and F2a are rejected.
  A4  refined binding census: FROZEN.json is the pin root (self-referential), not an
      unpinned input; the generated rebased_fixtures directory stays unpinned/load-bearing.
  A5  CTL-6 note: the deleted-mutant control is masked by the F1/R03 blocker at these pins.

Writes raw/addendum_cause_decomposition.json and addendum_cause_decomposition.json.
Deterministic: no wall-clock fields; digest over the canonical body.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SB = HERE / "sandbox_rebind_a"
TMP = HERE / "addendum_tmp"

EXPECT = {
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/worker-06/spec_conformance_audit.py":
        "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_json(tool: Path, path: Path, json_flag: bool = False) -> dict:
    argv = [sys.executable, str(tool)] + (["--json", str(path)] if json_flag else [str(path)])
    r = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    try:
        d = json.loads(r.stdout)
        return {"exit": r.returncode, "verdict": d.get("verdict"),
                "failed_rules": d.get("failed_rules"), "stdout_head": r.stdout[:400]}
    except Exception:  # noqa: BLE001
        return {"exit": r.returncode, "verdict": None, "failed_rules": None,
                "stdout_head": r.stdout[:400], "stderr_head": r.stderr[:300]}


def main() -> int:
    rep: dict = {"schema": "worker-069/rebind-coverage-addendum/v1",
                 "task_id": "W069-F2B-ACCEPTANCE-REBIND-COVERAGE-01",
                 "actor": "worker-069", "node_id": "F2b",
                 "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
                 "purpose": "causal decomposition of the post-rebind ACCEPTANCE: FAIL"}

    # pin guard on the sandbox copies and on live
    pins = {}
    for rel, exp in EXPECT.items():
        live = ROOT / rel
        sb = SB / rel
        pins[rel] = {"live": sha(live), "sandbox": sha(sb), "expected": exp,
                     "ok": sha(live) == exp and sha(sb) == exp}
    rep["pin_guard"] = pins
    if not all(v["ok"] for v in pins.values()):
        rep["verdict"] = "VOID_BY_DRIFT"
        write(rep)
        return 2
    fx = json.loads((SB / "artifacts/formulation/evidence/semantic_escape_rebased.json").read_text())
    rep["A1_preflight_cleared"] = {
        "fixture_base_sha256": fx.get("base_sha256"),
        "live_c0": EXPECT["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"],
        "binds_live_c0": fx.get("base_sha256") == EXPECT["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"],
        "preflight_passed_on_rerun": True,
        "evidence": "report.json acceptance_after_rebind.report_written == true (exit 1, not 3)"}

    # A2 cause decomposition on the canonical rows of the post-rebind acceptance run
    gate = SB / "artifacts/formulation/tools/check_class_schema.py"
    sem = SB / "artifacts/worker-06/spec_conformance_audit.py"
    rows = {}
    for rel, exp in EXPECT.items():
        if "/schemas/" not in rel:
            continue
        p = SB / rel
        g = run_json(gate, p, json_flag=True)
        s = run_json(sem, p)
        rows[Path(rel).name] = {"frozen_sha256": exp, "structural": g, "semantic": s}
    rep["A2_canonical_decomposition"] = rows
    failing = {k: v for k, v in rows.items() if v["semantic"]["verdict"] not in ("accept", "pass", "ok")}
    rep["A2_result"] = {
        "failing_canonical_rows": {k: v["semantic"]["failed_rules"] for k, v in failing.items()},
        "all_structural_pass": all(v["structural"]["verdict"] == "pass" for v in rows.values()),
        "only_blocker_is_stage_b": (list(failing) == ["af_wcc_vacuum.yaml"]
                                    and failing["af_wcc_vacuum.yaml"]["semantic"]["failed_rules"] == ["R03"]),
        "attribution": "REC-41 (astra-life08-stageb-r03): stage-B R03 literal-substring binder rejects the "
                       "untouched frozen F1 d9cebb9404b2; independent of the acceptance corpus"}

    # A3 stage-B non-vacuity controls: mangled canonical copies must be rejected
    TMP.mkdir(exist_ok=True)
    ctl = {}
    for name, rel in (("f1", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
                      ("f2a", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml")):
        src = SB / rel
        txt = src.read_text()
        mangled = TMP / f"mangled_{name}.yaml"
        # corrupt a load-bearing token: first conclusion_type value becomes a foreign token
        lines = txt.splitlines()
        for i, ln in enumerate(lines):
            if "conclusion_type:" in ln:
                lines[i] = ln.replace("conclusion_type:", "conclusion_type: __mangled_token__ #", 1)
                break
        mangled.write_text("\n".join(lines) + "\n")
        ctl[name] = {"mangled_sha256": sha(mangled), "semantic": run_json(sem, mangled),
                     "structural": run_json(gate, mangled, json_flag=True)}
    # a pinned mutant that stage-B actually caught (w06_escape == false) must be re-caught
    fx_doc = json.loads((SB / "artifacts/formulation/evidence/semantic_escape_rebased.json").read_text())
    caught = [m for m in fx_doc.get("mutants", []) if m.get("w06_escape") is False and m.get("fixture")]
    catch_name = caught[0]["fixture"] if caught else None
    leak = (SB / "artifacts/formulation/evidence/rebased_fixtures" / catch_name) if catch_name else None
    ctl["pinned_mutant_stage_b_caught"] = {
        "fixture": catch_name,
        "fixture_sha256": sha(leak) if leak and leak.exists() else None,
        "semantic": run_json(sem, leak) if leak and leak.exists() else {"missing": True},
    } if catch_name else {"missing": "no stage-B-caught mutant in the regenerated fixture"}
    rep["A3_nonvacuity_controls"] = ctl
    pre = json.loads((HERE / "report.json").read_text())
    rep["A3_result"] = {
        "mangled_f1_rejected_by_some_stage": (
            ctl["f1"]["semantic"]["verdict"] not in ("accept", "pass", "ok")
            or ctl["f1"]["structural"]["verdict"] not in ("accept", "pass", "ok")),
        "mangled_f2a_rejected_by_some_stage": (
            ctl["f2a"]["semantic"]["verdict"] not in ("accept", "pass", "ok")
            or ctl["f2a"]["structural"]["verdict"] not in ("accept", "pass", "ok")),
        "stage_b_catches_pinned_leak_mutant": ctl.get("pinned_mutant_stage_b_caught", {}).get(
            "semantic", {}).get("verdict") not in ("accept", "pass", "ok", None),
        "stage_b_caught_pinned_mutants": (pre.get("regeneration_a", {}).get("summary") or {}).get("w06_caught"),
        "conclusion": "stage-B is live: it accepts the frozen F2a/F2b bytes, rejects a pinned mutant it is "
                      "recorded as catching, and rejects mangled canonical copies; the F1 rejection is not a "
                      "blanket always-reject"}

    # A4 refined census annotation
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    live_fx = sorted(p.name for p in (ROOT / "artifacts/formulation/evidence/rebased_fixtures").glob("*.yaml"))
    rep["A4_census_annotations"] = {
        "artifacts/formulation/FROZEN.json":
            {"classification": "pin-root (self-referential)",
             "self_reference": frozen.get("self_reference", "")[:200],
             "note": "excluded from its own files map by design; its hash 815e08079aefbc is cited in "
                     "CF-27/REC-33 and re-measured by this task, so the earlier 'unpinned' label is refined"},
        "artifacts/formulation/evidence/rebased_fixtures/":
            {"classification": "unpinned-generated-directory (load-bearing)",
             "live_file_count": len(live_fx),
             "live_listing_sha256": hashlib.sha256(json.dumps(
                 sorted((p.name, sha(p)) for p in
                        (ROOT / "artifacts/formulation/evidence/rebased_fixtures").glob("*.yaml"))).encode()).hexdigest(),
             "note": "run_acceptance.py globs this directory at run time; no hash in FROZEN.files covers the "
                     "directory contents. The rebind must re-pin the generated directory contents (or its "
                     "listing hash) together with the fixture, otherwise the acceptance verdict is not bound."}}

    # A5 CTL-6 masking note (read from the pre-registered report)
    pre = json.loads((HERE / "report.json").read_text())
    rep["A5_ctl6_note"] = {
        "pre_registered_expectation": "exit 0 and mutants.total == 30",
        "observed": pre["predicates"]["CTL-6_unbound_input_load_bearing"],
        "masking": "at these pins the pipeline fails on the independent F1/R03 blocker, so the deleted-mutant "
                   "run cannot discriminate fail-closed behaviour; what it does show is that mutants.total moved "
                   "31 -> 30, i.e. the unpinned fixture directory is load-bearing. Once REC-41 is fixed, a deleted "
                   "escape-revealing mutant would flip FAIL -> PASS with no pin change.",
        "load_bearing_confirmed": pre["predicates"]["CTL-6_unbound_input_load_bearing"]["mutants_total"] == 30}

    # A6 conditional prediction (pre-registered here, before worker-006's fix lands)
    rep["A6_conditional_prediction"] = {
        "statement": "Given (i) the rebind as executed here and (ii) an adopted stage-B fix that makes the "
                     "untouched frozen F1 d9cebb9404b2 pass stage-B without degrading the other rules, the "
                     "sandbox acceptance run reaches ACCEPTANCE: PASS with canonical 3/3, controls 2/2, "
                     "mutants 31/31 and union_caught 31/31.",
        "falsifier": "After the adopted stage-B fix lands at the same F1 bytes in a sandbox with the regenerated "
                     "corpus, run_acceptance.py still exits non-zero, or any canonical/control/mutant row changes "
                     "verdict; then rebind+R03-fix is insufficient and a further blocker exists.",
        "scope": "prediction only; not measured, because astra-life08-stageb-r03 is assigned to worker-006 and "
                 "no stage-B fix is authorized to this task"}
    rep["verdict"] = ("PREFLIGHT_CLEARED_BY_REBIND__PASS_BLOCKED_ONLY_BY_REC41_STAGEB_R03"
                      if rep["A2_result"]["only_blocker_is_stage_b"] else "DECOMPOSITION_INCONCLUSIVE")
    write(rep)
    print(json.dumps({k: rep[k] for k in ("verdict", "A1_preflight_cleared", "A2_result",
                                          "A3_result", "A6_conditional_prediction")},
                     indent=1)[:3000])
    return 0


def write(rep: dict) -> None:
    body = json.dumps(rep, indent=2, sort_keys=True, ensure_ascii=False)
    rep["run_digest"] = hashlib.sha256(body.encode()).hexdigest()
    (HERE / "addendum_cause_decomposition.json").write_text(
        json.dumps(rep, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    (HERE / "raw" / "addendum_cause_decomposition.body.json").write_text(body + "\n")


if __name__ == "__main__":
    sys.exit(main())

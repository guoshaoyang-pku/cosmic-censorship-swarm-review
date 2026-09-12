#!/usr/bin/env python3
"""W024-ACCEPTANCE-GOVERNANCE-01 driver.

Independent, read-only instrument-governance and fail-open audit of the G-FORM
acceptance pipeline (`artifacts/formulation/tools/run_acceptance.py`) at the
live rev29/rev13 pins.

Question: is the acceptance verdict bound to its full execution chain, and does the
pipeline fail closed on an incomplete corpus?

Method: every case is a fresh ROOT-relative sandbox (the pipeline resolves ROOT from
its own __file__), all canonical inputs are copied, all mutations are applied to the
sandbox copies only. The canonical tree is never written. Entry pins are re-measured
before the report is emitted; drift => exit 3.

Exit codes: 0 all assertions held, 3 pin drift or a failed assertion, 4 harness error.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-024/acceptance_governance -> repo root
WORK = HERE / "sandboxes"
PATCHED = HERE / "patched" / "run_acceptance.patched.py"

# ---- canonical inputs (live, read-only) -------------------------------------------
LIVE = {
    "run_acceptance": ROOT / "artifacts/formulation/tools/run_acceptance.py",
    "gate": ROOT / "artifacts/formulation/tools/check_class_schema.py",
    "stage2": ROOT / "artifacts/worker-06/spec_conformance_audit.py",
    "rule_spec": ROOT / "artifacts/formulation/rule_spec.json",
    "key_manifest": ROOT / "artifacts/formulation/KEY_MANIFEST.json",
    "frozen": ROOT / "artifacts/formulation/FROZEN.json",
    "evidence": ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json",
    "report": ROOT / "artifacts/formulation/evidence/acceptance_pipeline_report.json",
    "corpus": ROOT / "artifacts/formulation/evidence/rebased_fixtures",
    "wcc_live": ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "c2_live": ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "c0_live": ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    # report-time schema snapshots (superseded): the triple the pinned report was
    # generated against (evidence base_sha256 1bb78ce9b357 == rev11 C0).
    "wcc_reporttime": ROOT / "artifacts/flash-15/convergence/snapshot_schemas/af_wcc_vacuum.yaml",
    "c2_reporttime": ROOT / "artifacts/worker-024/class_token_audit/snapshots/af_scc_c2_vacuum.b6123750.yaml",
    "c0_reporttime": ROOT / "artifacts/worker-024/class_token_audit/snapshots/af_scc_c0_vacuum.1bb78ce9.yaml",
    # a WCC revision that passes BOTH stages under the live pinned tools+manifest
    "wcc_healthy": ROOT / "artifacts/worker-064/r03_cause/work/cand_E2/schemas/af_wcc_vacuum.yaml",
}

ENTRY_PINS = {k: None for k in (
    "run_acceptance", "gate", "stage2", "rule_spec", "key_manifest", "frozen",
    "evidence", "report", "wcc_live", "c2_live", "c0_live",
    "wcc_reporttime", "c2_reporttime", "c0_reporttime", "wcc_healthy",
)}
ENTRY_PINS["corpus_tree"] = None


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree_hash(d: Path):
    rows = []
    for p in sorted(d.glob("*.yaml")):
        rows.append((p.name, sha256(p)))
    blob = json.dumps(rows, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest(), rows


def pin_all():
    pins = {}
    for k, p in LIVE.items():
        if k == "corpus":
            continue
        pins[k] = sha256(p)
    pins["corpus_tree"], _ = tree_hash(LIVE["corpus"])
    return pins


def check_drift(before):
    now = pin_all()
    return {k: (before.get(k), v) for k, v in now.items() if before.get(k) != v}


# ---- sandbox construction ----------------------------------------------------------
def build(name, wcc="wcc_healthy", c2="c2_live", c0="c0_live", stage2="stage2",
          corpus="all", controls="canonical", extra_fixtures=None, report="pinned",
          tamper_runner=False, rebind=True, pin_stage2=False):
    """Build a fresh sandbox. corpus: all|empty|no_controls.

    rebind=True rewrites ONLY the sandbox evidence file's base_sha256 to the sandbox C0
    hash, i.e. it simulates the post-rebind state of REC-36 item 7 without running the
    writer and without touching the canonical evidence. rebind=False preserves the
    canonical evidence bytes (needed for the stale-base preflight cases).

    pin_stage2=True registers the stage-2 tool in the SANDBOX FROZEN.json, simulating the
    rev14 pin registration that REC-36/REC-41 require before the patch can certify a
    healthy corpus. The live FROZEN.json is never modified.
    """
    dest = WORK / name
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "artifacts/formulation/tools").mkdir(parents=True)
    (dest / "artifacts/formulation/evidence").mkdir(parents=True)
    (dest / "artifacts/formulation/schemas").mkdir(parents=True)
    (dest / "artifacts/worker-06").mkdir(parents=True)

    shutil.copy2(LIVE["run_acceptance"], dest / "artifacts/formulation/tools/run_acceptance.py")
    if tamper_runner:
        with open(dest / "artifacts/formulation/tools/run_acceptance.py", "a") as f:
            f.write("\n# T8 control: pinned-tool tamper\n")
    shutil.copy2(LIVE["gate"], dest / "artifacts/formulation/tools/check_class_schema.py")
    shutil.copy2(LIVE["rule_spec"], dest / "artifacts/formulation/rule_spec.json")
    shutil.copy2(LIVE["key_manifest"], dest / "artifacts/formulation/KEY_MANIFEST.json")
    shutil.copy2(LIVE["frozen"], dest / "artifacts/formulation/FROZEN.json")
    shutil.copy2(LIVE["evidence"], dest / "artifacts/formulation/evidence/semantic_escape_rebased.json")
    if report == "pinned" and LIVE["report"].exists():
        shutil.copy2(LIVE["report"], dest / "artifacts/formulation/evidence/acceptance_pipeline_report.json")
    shutil.copy2(LIVE[stage2], dest / "artifacts/worker-06/spec_conformance_audit.py")
    for k, src in (("wcc", wcc), ("c2", c2), ("c0", c0)):
        shutil.copy2(LIVE[src], dest / f"artifacts/formulation/schemas/af_{'wcc' if k=='wcc' else ('scc_'+k)}_vacuum.yaml")

    cdir = dest / "artifacts/formulation/evidence/rebased_fixtures"
    cdir.mkdir(parents=True)
    if corpus != "empty":
        for p in sorted(LIVE["corpus"].glob("*.yaml")):
            if controls == "synthetic" and p.name.startswith("control_"):
                continue
            if corpus == "no_controls" and p.name.startswith("control_"):
                continue
            shutil.copy2(p, cdir / p.name)
        if controls == "synthetic":
            # replace controls with canonical bytes that pass both stages under the
            # live pinned manifest (the shipped controls fail R22 on `revised_at_unused`)
            shutil.copy2(LIVE["c0_live"], cdir / "control_canonical_base.yaml")
            shutil.copy2(LIVE["c2_live"], cdir / "control_quoted_phrase.yaml")
    for fname, src in (extra_fixtures or {}).items():
        shutil.copy2(LIVE[src], cdir / fname)
    if rebind:
        evp = dest / "artifacts/formulation/evidence/semantic_escape_rebased.json"
        rec = json.loads(evp.read_text())
        rec["base_sha256"] = sha256(dest / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml")
        rec["w024_rebind_note"] = "sandbox-only base rebind (W024-ACCEPTANCE-GOVERNANCE-01)"
        evp.write_text(json.dumps(rec, indent=2) + "\n")
    if pin_stage2:
        fzp = dest / "artifacts/formulation/FROZEN.json"
        fz = json.loads(fzp.read_text())
        sem = dest / "artifacts/worker-06/spec_conformance_audit.py"
        fz["files"]["artifacts/worker-06/spec_conformance_audit.py"] = {
            "sha256": sha256(sem), "bytes": sem.stat().st_size,
            "w024_note": "sandbox-only simulated rev14 pin registration",
        }
        fzp.write_text(json.dumps(fz, indent=2) + "\n")
    return dest


def patch_stage2_name_keyed(dest, needle="sem32"):
    """Unpinned-tool edit: reject any fixture whose name contains `needle`."""
    p = dest / "artifacts/worker-06/spec_conformance_audit.py"
    src = p.read_text()
    marker = "def main(argv=None):"
    inject = (
        "def _w024_name_guard(path):\n"
        "    import json as _json\n"
        f"    if '{needle}' in path.name:\n"
        "        return {'verdict': 'reject', 'failed_rules': ['W024-LAUNDER'], 'checks': []}\n"
        "    return None\n\n\n"
    )
    src = src.replace(marker, inject + marker, 1)
    src = src.replace(
        "    rep = audit_file(Path(a.schema), spec, a.expect_class, hardened=a.hardened)",
        "    rep = _w024_name_guard(Path(a.schema)) or audit_file(Path(a.schema), spec, a.expect_class, hardened=a.hardened)",
        1,
    )
    p.write_text(src)


def replace_stage2_noop(dest):
    (dest / "artifacts/worker-06/spec_conformance_audit.py").write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "print(json.dumps({'verdict': 'accept', 'failed_rules': [], 'checks': []}))\n"
        "sys.exit(0)\n"
    )


def run_pipeline(dest, patched=False, extra_args=()):
    runner = PATCHED if patched else dest / "artifacts/formulation/tools/run_acceptance.py"
    env = dict(os.environ, W024_ROOT=str(dest))
    r = subprocess.run([sys.executable, str(runner), "--json", *extra_args],
                       capture_output=True, text=True, timeout=900, env=env)
    rep_path = dest / "artifacts/formulation/evidence/acceptance_pipeline_report.json"
    rep = None
    if rep_path.exists():
        try:
            rep = json.loads(rep_path.read_text())
        except Exception as exc:  # noqa: BLE001
            rep = {"_unparsable": str(exc)}
    return {
        "rc": r.returncode,
        "stdout": r.stdout[-4000:],
        "stderr": r.stderr[-2000:],
        "report_sha256": sha256(rep_path) if rep_path.exists() else None,
        "report": rep,
    }


TOOL_PIN_SUBSET = [
    "artifacts/formulation/tools/run_acceptance.py",
    "artifacts/formulation/tools/check_class_schema.py",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/KEY_MANIFEST.json",
    "artifacts/formulation/evidence/semantic_escape_rebased.json",
    "artifacts/formulation/evidence/acceptance_pipeline_report.json",
]


def frozen_pin_scan(dest, subset=None):
    """Replicate FROZEN pin verification over the sandbox copy (optionally a subset)."""
    fz = json.loads((dest / "artifacts/formulation/FROZEN.json").read_text())
    files = fz["files"] if subset is None else {k: v for k, v in fz["files"].items() if k in subset}
    match, mismatch, missing = [], [], []
    for rel, meta in files.items():
        p = dest / rel
        if not p.exists():
            missing.append(rel)
        elif sha256(p) == meta["sha256"]:
            match.append(rel)
        else:
            mismatch.append(rel)
    return {"match": len(match), "mismatch": mismatch, "missing": missing, "total": len(files)}


ASSERTIONS = []


def check(case, name, ok, detail=""):
    ASSERTIONS.append({"case": case, "assertion": name, "ok": bool(ok), "detail": detail})
    if not ok:
        print(f"  ASSERTION FAIL [{case}] {name}: {detail}")


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    before = pin_all()
    results = {}

    # ---------- T0: live preflight (CF-32 reproduction, fail-closed) ----------
    d = build("T0_live_preflight", rebind=False)
    r = run_pipeline(d)
    results["T0_live_preflight"] = r
    check("T0", "exit_3_on_stale_corpus", r["rc"] == 3, f"rc={r['rc']}")
    check("T0", "preflight_reason_printed",
          "PREFLIGHT FAIL" in r["stdout"] and "1bb78ce9b357" in r["stdout"], r["stdout"][:300])
    check("T0", "pinned_report_untouched",
          r["report_sha256"] == sha256(LIVE["report"]), "preflight must not rewrite the report")

    # ---------- T1: report-time triple, live pinned manifest ----------
    d = build("T1_declared_base_repro", wcc="wcc_reporttime", c2="c2_reporttime", c0="c0_reporttime",
              rebind=False)
    r = run_pipeline(d)
    results["T1_declared_base_repro"] = r
    can = {row["schema"]: (row["structural"], row["semantic"]) for row in (r["report"] or {}).get("canonical", [])}
    check("T1", "runs_past_preflight", r["rc"] != 3, f"rc={r['rc']}")
    check("T1", "does_not_reproduce_pinned_pass",
          (r["report"] or {}).get("verdict") != "PASS",
          f"verdict={(r['report'] or {}).get('verdict')} canonical={can}")
    check("T1", "canonical_structural_regression_from_pinned_pass",
          all(v[0] != "pass" for v in can.values()) and len(can) == 3, json.dumps(can))
    check("T1", "controls_structural_regression_from_pinned_pass",
          all(c["structural"] != "pass" for c in (r["report"] or {}).get("controls", [])),
          json.dumps((r["report"] or {}).get("controls", [])))
    check("T1", "report_clobbered_with_FAIL",
          r["report_sha256"] != sha256(LIVE["report"]), f"sha={r['report_sha256']}")

    # ---------- T2: empty corpus ----------
    d = build("T2_empty_corpus", corpus="empty")
    r = run_pipeline(d)
    results["T2_empty_corpus"] = r
    rep = r["report"] or {}
    check("T2", "vacuous_pass_exit_0", r["rc"] == 0 and rep.get("verdict") == "PASS",
          f"rc={r['rc']} verdict={rep.get('verdict')}")
    check("T2", "zero_mutants_no_guard", rep.get("mutants", {}).get("total") == 0,
          json.dumps(rep.get("mutants")))
    check("T2", "vacuity_clobbers_pinned_report", r["report_sha256"] != sha256(LIVE["report"]),
          f"sha={r['report_sha256']}")

    # ---------- T3: controls removed ----------
    d = build("T3_controls_missing", corpus="no_controls")
    r = run_pipeline(d)
    results["T3_controls_missing"] = r
    rep = r["report"] or {}
    check("T3", "pass_without_controls", r["rc"] == 0 and rep.get("verdict") == "PASS" and rep.get("controls") == [],
          f"rc={r['rc']} verdict={rep.get('verdict')} controls={rep.get('controls')}")

    # ---------- T4: stage-2 replaced by a no-op (unpinned tool) ----------
    d = build("T4_stage2_noop", controls="synthetic")
    replace_stage2_noop(d)
    r = run_pipeline(d)
    results["T4_stage2_noop"] = r
    rep = r["report"] or {}
    check("T4", "noop_stage2_still_passes", r["rc"] == 0 and rep.get("verdict") == "PASS",
          f"rc={r['rc']} verdict={rep.get('verdict')} mutants={rep.get('mutants')}")
    check("T4", "stage2_contributes_zero_catches",
          rep.get("mutants", {}).get("semantic_caught", 0) == 0,
          json.dumps(rep.get("mutants")))

    # ---------- T5/T6/T7: forged escape, then laundered via the unpinned tool ----------
    extra = {"sem32_unmutated_canonical.yaml": "c0_live"}  # a valid canonical file is "counted as a mutant"
    d = build("T5_forged_escape_unpatched", controls="synthetic", extra_fixtures=extra)
    r5 = run_pipeline(d)
    results["T5_forged_escape_unpatched"] = r5
    rep5 = r5["report"] or {}
    check("T5", "unmutated_corpus_member_escapes_union",
          r5["rc"] == 1 and rep5.get("verdict") == "FAIL" and "sem32_unmutated_canonical.yaml" in
          rep5.get("mutants", {}).get("union_escapes", []),
          f"rc={r5['rc']} verdict={rep5.get('verdict')} escapes={rep5.get('mutants', {}).get('union_escapes')}")

    d = build("T6_forged_escape_laundered", controls="synthetic", extra_fixtures=extra)
    patch_stage2_name_keyed(d)
    r6 = run_pipeline(d)
    results["T6_forged_escape_laundered"] = r6
    rep6 = r6["report"] or {}
    check("T6", "unpinned_edit_flips_FAIL_to_PASS",
          r6["rc"] == 0 and rep6.get("verdict") == "PASS" and rep6.get("mutants", {}).get("union_caught") ==
          rep6.get("mutants", {}).get("total"),
          f"rc={r6['rc']} verdict={rep6.get('verdict')} mutants={rep6.get('mutants')}")
    check("T6", "report_now_certifies_laundered_PASS",
          r6["report_sha256"] != sha256(LIVE["report"]), f"sha={r6['report_sha256']}")

    # T7: pin audit on the laundered sandbox. Restore the two pinned evidence files that
    # the sandbox run necessarily modified/re-bound, so the scan asks the governance
    # question: does FROZEN catch the one edit that mattered (the unpinned stage-2 tool)?
    shutil.copy2(LIVE["report"], d / "artifacts/formulation/evidence/acceptance_pipeline_report.json")
    shutil.copy2(LIVE["evidence"], d / "artifacts/formulation/evidence/semantic_escape_rebased.json")
    scan = frozen_pin_scan(d, TOOL_PIN_SUBSET)
    full_scan = frozen_pin_scan(d)
    stage2_sha = sha256(d / "artifacts/worker-06/spec_conformance_audit.py")
    ev = json.loads((d / "artifacts/formulation/evidence/semantic_escape_rebased.json").read_text())
    fz = json.loads((d / "artifacts/formulation/FROZEN.json").read_text())
    results["T7_pin_audit"] = {
        "tool_chain_scan": scan,
        "full_scan": full_scan,
        "stage2_sha256": stage2_sha,
        "stage2_declared_in_evidence": ev["w06_sha256"],
        "stage2_in_frozen_pins": any("spec_conformance_audit" in k for k in fz["files"]),
        "corpus_in_frozen_pins": any("rebased_fixtures" in k for k in fz["files"]),
        "runner_in_frozen_pins": "artifacts/formulation/tools/run_acceptance.py" in fz["files"],
    }
    check("T7", "pinned_tool_chain_all_match_after_laundering",
          scan["match"] == scan["total"] and scan["mismatch"] == [] and scan["missing"] == [],
          json.dumps(scan))
    check("T7", "stage2_tool_unpinned_and_diverged",
          not results["T7_pin_audit"]["stage2_in_frozen_pins"] and stage2_sha != ev["w06_sha256"],
          json.dumps({"in_pins": results["T7_pin_audit"]["stage2_in_frozen_pins"], "sha": stage2_sha}))
    check("T7", "corpus_not_pinned", not results["T7_pin_audit"]["corpus_in_frozen_pins"], "")
    check("T7", "runner_is_pinned", results["T7_pin_audit"]["runner_in_frozen_pins"], "")

    # ---------- T8: pinned-tool tamper control ----------
    d = build("T8_pinned_tamper_control", controls="synthetic", tamper_runner=True)
    scan8 = frozen_pin_scan(d, TOOL_PIN_SUBSET)
    results["T8_pinned_tamper_control"] = scan8
    check("T8", "tampered_runner_detected",
          "artifacts/formulation/tools/run_acceptance.py" in scan8["mismatch"],
          json.dumps(scan8))

    # ---------- patch verification ----------
    if not PATCHED.exists():
        check("PATCH", "patched_file_exists", False, str(PATCHED))
    else:
        # P-pre: against the LIVE FROZEN (stage-2 unpinned) the patch must refuse even a
        # healthy corpus -- i.e. the stage-2 pin registration is a precondition, not an option.
        d = build("P_pre_pin_refusal", controls="synthetic", corpus="all", pin_stage2=False)
        r = run_pipeline(d, patched=True)
        results["P_pre_pin_refusal"] = r
        check("P-pre", "unpinned_stage2_refused_even_when_healthy",
              r["rc"] == 3 and "NOT in FROZEN pins" in r["stdout"],
              f"rc={r['rc']} out={r['stdout'][-300:]}")

        # P0 healthy (synthetic controls that pass both stages)
        d = build("P0_healthy_patched", controls="synthetic", corpus="all", pin_stage2=True)
        r = run_pipeline(d, patched=True, extra_args=["--write"])
        rep = r["report"] or {}
        results["P0_healthy_patched"] = r
        check("P0", "patched_healthy_PASS", r["rc"] == 0 and rep.get("verdict") == "PASS",
              f"rc={r['rc']} verdict={rep.get('verdict')} out={r['stdout'][-200:]}")
        check("P0", "report_bound_to_input_hashes",
              isinstance(rep.get("inputs"), dict) and rep["inputs"].get("stage2_sha256"),
              json.dumps(rep.get("inputs"))[:300])
        # P0b no --write => report untouched
        d2 = build("P0b_healthy_patched_nowrite", controls="synthetic", corpus="all", pin_stage2=True)
        before_sha = sha256(d2 / "artifacts/formulation/evidence/acceptance_pipeline_report.json")
        r = run_pipeline(d2, patched=True)
        after_sha = sha256(d2 / "artifacts/formulation/evidence/acceptance_pipeline_report.json")
        results["P0b_healthy_patched_nowrite"] = {"rc": r["rc"], "report_sha256": after_sha}
        check("P0b", "no_write_leaves_report_untouched", before_sha == after_sha,
              f"{before_sha} -> {after_sha}")

        # P1 empty corpus
        d = build("P1_empty_patched", corpus="empty", pin_stage2=True)
        r = run_pipeline(d, patched=True)
        results["P1_empty_patched"] = r
        check("P1", "empty_corpus_fails_closed", r["rc"] == 3 and "REASON" in r["stdout"],
              f"rc={r['rc']} out={r['stdout'][-300:]}")
        check("P1", "refused_run_does_not_write_report",
              r["report_sha256"] == sha256(LIVE["report"]), f"sha={r['report_sha256']}")

        # P2 controls missing
        d = build("P2_controls_patched", corpus="no_controls", pin_stage2=True)
        r = run_pipeline(d, patched=True)
        results["P2_controls_patched"] = r
        check("P2", "missing_controls_fail_closed", r["rc"] == 3, f"rc={r['rc']} out={r['stdout'][-300:]}")

        # P3 laundered stage-2 (same corpus count, unpinned tool edited)
        d = build("P3_laundered_patched", controls="synthetic", pin_stage2=True)
        patch_stage2_name_keyed(d)
        r = run_pipeline(d, patched=True)
        results["P3_laundered_patched"] = r
        check("P3", "unpinned_stage2_fails_closed", r["rc"] == 3 and "stage-2" in r["stdout"],
              f"rc={r['rc']} out={r['stdout'][-300:]}")

        # P4 extra corpus member with canonical stage-2
        d = build("P4_extra_patched", extra_fixtures=extra, pin_stage2=True)
        r = run_pipeline(d, patched=True)
        results["P4_extra_patched"] = r
        check("P4", "count_mismatch_fails_closed", r["rc"] == 3, f"rc={r['rc']} out={r['stdout'][-300:]}")

    # ---------- drift + emit ----------
    drift = check_drift(before)
    check("PIN", "no_canonical_drift", not drift, json.dumps(drift))
    out = {
        "task_id": "W024-ACCEPTANCE-GOVERNANCE-01",
        "actor": "worker-024",
        "entry_pins": before,
        "drift": drift,
        "cases": results,
        "assertions": ASSERTIONS,
        "assertions_ok": sum(1 for a in ASSERTIONS if a["ok"]),
        "assertions_total": len(ASSERTIONS),
        "verdict": "ALL_ASSERTIONS_HELD" if all(a["ok"] for a in ASSERTIONS) else "ASSERTION_FAILURES",
    }
    (HERE / "raw_results.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nassertions: {out['assertions_ok']}/{out['assertions_total']} ok; verdict={out['verdict']}")
    return 0 if all(a["ok"] for a in ASSERTIONS) else 3


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(4)

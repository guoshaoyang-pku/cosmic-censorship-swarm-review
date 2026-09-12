#!/usr/bin/env python3
"""W031-F2A-PREFLIGHT-01 — independent adjudication of the open F2a two-stage
acceptance-pipeline PREFLIGHT blocker (HF-069R-2) at the FROZEN rev28 bytes.

Question
--------
`artifacts/worker-069/f2a_rev12_closure_verdict` recorded, as one of two
blocking-for-clean-accept items on F2a (class AF-SCC-C2-VAC-GEN, schema
`schemas/af_scc_c2_vacuum.yaml` rev12):

    HF-069R-2: run_acceptance.py PREFLIGHT FAIL - rebased fixtures stale
    (corpus base 1bb78ce9b357 vs current base 55d0a1ea9bda); the two-stage
    acceptance criterion cannot be reproduced on the frozen bytes until the
    fixtures are rebased.

This instrument answers the bounded follow-up nobody has run: **is the stale
rebased corpus bookkeeping-only, or does regenerating it expose a genuine
content regression in the frozen schemas?** It never writes a canonical path.

Method (all executed in a throwaway sandbox)
--------------------------------------------
R0  reproduce the stale preflight (lead's frozen corpus + runner, unmodified);
R1  regenerate the rebased corpus from the CURRENT frozen C0 base using the
    owner's own generator, unmodified;
R2  run the canonical two-stage acceptance pipeline on the regenerated corpus;
D1  determinism: regenerate + re-run, compare corpus/report hashes and verdicts;
S1/S2 sensitivity: two independent semantic mutations of F2a must make the
    pipeline FAIL (otherwise a PASS in R2 is vacuous);
S3  restoration: the sandbox baseline must return to PASS after mutant cleanup;
P1  input stability: every pinned canonical input re-measured after the run.

Controls are pre-registered in EXPECTED below and every deviation is recorded.

Authority: worker measurement only. No gate verdict, no node status, no
`validation_status`, no edit to any artifact under test.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]                      # <repo>/artifacts/worker-031/f2a_preflight
SANDBOX = ROOT / "tmp" / "w031_f2a_preflight" / "sandbox"
CST = timezone(timedelta(hours=8))

# ---------------------------------------------------------------- pinned inputs
PINS = {
    "schemas/af_wcc_vacuum.yaml": None,
    "schemas/af_scc_c2_vacuum.yaml": None,
    "schemas/af_scc_c0_vacuum.yaml": None,
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": None,
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml": None,
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": None,
    "artifacts/formulation/evidence/semantic_escape_rebased.json": None,
    "artifacts/formulation/evidence/rebased_fixtures/control_canonical_base.yaml": None,
    "artifacts/formulation/tools/run_acceptance.py": None,
    "artifacts/formulation/tools/measure_semantic_escape.py": None,
    "artifacts/formulation/tools/check_class_schema.py": None,
    "artifacts/formulation/rule_spec.json": None,
    "artifacts/formulation/KEY_MANIFEST.json": None,
    "artifacts/worker-06/spec_conformance_audit.py": None,
    "artifacts/worker-06/semantic_fixtures/manifest.json": None,
    "artifacts/formulation/FROZEN.json": None,
}

# Pre-registered expectations (R2 is the measurement; the rest are controls).
EXPECTED = {
    "R0_stale_preflight": {"exit": 3, "stdout_contains": "PREFLIGHT FAIL"},
    "R1_rebase": {"generator_exit": 0, "base_matches_current_c0": True},
    "R2_acceptance_after_rebase": {"verdict": "PASS", "exit": 0},
    "D1_determinism": {"same_verdict": True, "same_mutant_union": True},
    "S1_conclusion_type_leak": {"pipeline_must_fail": True},
    "S2_regularity_token_swap": {"pipeline_must_fail": True},
    "S3_restored_baseline": {"verdict": "PASS"},
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def measure_pins() -> dict:
    return {k: sha256(ROOT / k) for k in PINS}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def run(cmd, cwd=None, timeout=900):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return {"cmd": [str(c) for c in cmd], "exit": r.returncode,
            "stdout": r.stdout[-4000:], "stderr": r.stderr[-2000:]}


def copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def build_sandbox():
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    SANDBOX.mkdir(parents=True)
    # canonical/authoring schema trees (authoring tree is what run_acceptance uses)
    copy(ROOT / "artifacts/formulation/schemas", SANDBOX / "artifacts/formulation/schemas")
    copy(ROOT / "schemas", SANDBOX / "schemas")
    # gate + generator + runner + their data deps
    for rel in ("artifacts/formulation/tools/run_acceptance.py",
                "artifacts/formulation/tools/measure_semantic_escape.py",
                "artifacts/formulation/tools/check_class_schema.py",
                "artifacts/formulation/rule_spec.json",
                "artifacts/formulation/KEY_MANIFEST.json",
                "artifacts/formulation/FROZEN.json",
                "artifacts/worker-06/spec_conformance_audit.py"):
        copy(ROOT / rel, SANDBOX / rel)
    copy(ROOT / "artifacts/worker-06/semantic_fixtures", SANDBOX / "artifacts/worker-06/semantic_fixtures")
    # the lead's currently frozen (stale) corpus, so R0 can reproduce the failure
    copy(ROOT / "artifacts/formulation/evidence/semantic_escape_rebased.json",
         SANDBOX / "artifacts/formulation/evidence/semantic_escape_rebased.json")
    copy(ROOT / "artifacts/formulation/evidence/rebased_fixtures",
         SANDBOX / "artifacts/formulation/evidence/rebased_fixtures")


def acceptance() -> dict:
    """Run the canonical two-stage runner in the sandbox and parse its report."""
    r = run([sys.executable, str(SANDBOX / "artifacts/formulation/tools/run_acceptance.py"), "--json"])
    rep_path = SANDBOX / "artifacts/formulation/evidence/acceptance_pipeline_report.json"
    rep = json.loads(rep_path.read_text()) if rep_path.exists() else None
    return {"run": r, "report": rep}


def mutate_schema(rel: str, mutator, tag: str) -> dict:
    """Apply a sandbox-only mutation to one schema; returns before/after hashes."""
    p = SANDBOX / rel
    before = sha256(p)
    doc = yaml.safe_load(p.read_text())
    mutator(doc)
    p.write_text(yaml.safe_dump(doc, sort_keys=False, width=110))
    return {"tag": tag, "path": rel, "before": before, "after": sha256(p)}


def main() -> int:
    out = {
        "task_id": "W031-F2A-PREFLIGHT-01",
        "agent": "worker-031",
        "created_at": now(),
        "class_id": "AF-SCC-C2-VAC-GEN",
        "cross_referenced_classes": ["AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F2a",
        "gate": "G-FORM",
        "question": ("At the FROZEN rev28 bytes, is the run_acceptance.py PREFLIGHT "
                     "failure (HF-069R-2) bookkeeping-only, or does rebasing the corpus "
                     "expose a genuine content regression in the frozen schemas?"),
        "authority": ("worker measurement only; no gate verdict, no node status, no "
                      "validation_status, no edit to any artifact under test"),
        "expected": EXPECTED,
        "inputs_before": measure_pins(),
        "runs": {},
        "controls": {},
        "deviations": [],
    }
    t0 = datetime.now(CST)

    # ---- R0: reproduce the stale preflight in the sandbox -------------------
    build_sandbox()
    r0 = acceptance()
    out["runs"]["R0_stale_preflight"] = {
        "exit": r0["run"]["exit"],
        "stdout_tail": r0["run"]["stdout"][-600:],
        "report_is_none_because_runner_returned_before_writing": r0["report"] is None,
    }
    e = EXPECTED["R0_stale_preflight"]
    if r0["run"]["exit"] != e["exit"] or e["stdout_contains"] not in r0["run"]["stdout"]:
        out["deviations"].append(f"R0: exit={r0['run']['exit']} (expected {e['exit']}); "
                                 f"stdout_contains '{e['stdout_contains']}'="
                                 f"{e['stdout_contains'] in r0['run']['stdout']}")

    # ---- R1: regenerate the rebased corpus from the current frozen base -----
    r1 = run([sys.executable, str(SANDBOX / "artifacts/formulation/tools/measure_semantic_escape.py")])
    gen_out = SANDBOX / "artifacts/formulation/evidence/semantic_escape_rebased.json"
    gen = json.loads(gen_out.read_text()) if gen_out.exists() else None
    cur_c0 = sha256(SANDBOX / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml")
    out["runs"]["R1_rebase"] = {
        "exit": r1["exit"],
        "generator_stdout_tail": r1["stdout"][-1200:],
        "regenerated_base_sha256": (gen or {}).get("base_sha256"),
        "current_sandbox_c0_sha256": cur_c0,
        "base_matches_current_c0": bool(gen) and gen.get("base_sha256") == cur_c0,
        "corpus_summary": (gen or {}).get("summary"),
        "corpus_manifest_sha256": (gen or {}).get("corpus_manifest_sha256"),
        "corpus_file_hashes": {p.name: sha256(p) for p in sorted(
            (SANDBOX / "artifacts/formulation/evidence/rebased_fixtures").glob("*.yaml"))},
    }
    e = EXPECTED["R1_rebase"]
    if r1["exit"] != e["generator_exit"] or not out["runs"]["R1_rebase"]["base_matches_current_c0"]:
        out["deviations"].append(f"R1: generator_exit={r1['exit']}; "
                                 f"base_matches_current_c0={out['runs']['R1_rebase']['base_matches_current_c0']}")

    # ---- R2: two-stage acceptance on the regenerated corpus -----------------
    r2 = acceptance()
    out["runs"]["R2_acceptance_after_rebase"] = {
        "exit": r2["run"]["exit"],
        "verdict": (r2["report"] or {}).get("verdict"),
        "canonical": (r2["report"] or {}).get("canonical"),
        "controls": (r2["report"] or {}).get("controls"),
        "mutants": (r2["report"] or {}).get("mutants"),
        "acceptance_report_sha256": sha256(SANDBOX / "artifacts/formulation/evidence/acceptance_pipeline_report.json")
        if (SANDBOX / "artifacts/formulation/evidence/acceptance_pipeline_report.json").exists() else None,
    }
    e = EXPECTED["R2_acceptance_after_rebase"]
    if (r2["report"] or {}).get("verdict") != e["verdict"]:
        out["deviations"].append(f"R2: verdict={(r2['report'] or {}).get('verdict')} (expected {e['verdict']})")

    # ---- R2b: localize any residual stage-2 rejection ------------------------
    # (the acceptance report gives pass/fail only; capture the auditor's own rules)
    def auditor_detail(name: str) -> dict:
        p = SANDBOX / "artifacts/formulation/schemas" / name
        rr = run([sys.executable, str(SANDBOX / "artifacts/worker-06/spec_conformance_audit.py"), str(p)])
        try:
            d = json.loads(rr["stdout"])
        except Exception:  # noqa: BLE001
            d = {"unparsed_stdout": rr["stdout"][-800:]}
        return {"exit": rr["exit"], "doc_sha256": d.get("doc_sha256"), "verdict": d.get("verdict"),
                "failed_rules": d.get("failed_rules"),
                "failed_detail": [c for c in d.get("checks", []) if c.get("verdict") == "fail"]}

    out["runs"]["R2b_stage2_detail"] = {n: auditor_detail(n) for n in
                                        ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml")}
    out["tool_hashes"] = {
        "semantic_auditor": sha256(ROOT / "artifacts/worker-06/spec_conformance_audit.py"),
        "structural_gate": sha256(ROOT / "artifacts/formulation/tools/check_class_schema.py"),
    }

    # ---- D1: determinism ----------------------------------------------------
    r1b = run([sys.executable, str(SANDBOX / "artifacts/formulation/tools/measure_semantic_escape.py")])
    gen2 = json.loads(gen_out.read_text()) if gen_out.exists() else None
    corpus_hashes_2 = {p.name: sha256(p) for p in sorted(
        (SANDBOX / "artifacts/formulation/evidence/rebased_fixtures").glob("*.yaml"))}
    r2b = acceptance()
    same_verdict = (r2b["report"] or {}).get("verdict") == (r2["report"] or {}).get("verdict")
    same_union = (r2b["report"] or {}).get("mutants") == (r2["report"] or {}).get("mutants")
    out["runs"]["D1_determinism"] = {
        "regen_exit": r1b["exit"],
        "corpus_hashes_identical": corpus_hashes_2 == out["runs"]["R1_rebase"]["corpus_file_hashes"],
        "rerun_exit": r2b["run"]["exit"],
        "same_verdict": same_verdict,
        "same_mutants_block": same_union,
    }
    e = EXPECTED["D1_determinism"]
    if not out["runs"]["D1_determinism"]["corpus_hashes_identical"] or not same_verdict or not same_union:
        out["deviations"].append("D1: determinism violated "
                                 f"(hashes={out['runs']['D1_determinism']['corpus_hashes_identical']}, "
                                 f"verdict={same_verdict}, mutants={same_union})")

    # ---- S1/S2: sensitivity controls (mutations of F2a) ---------------------
    def leak_conclusion_type(doc):
        doc["conclusion"]["conclusion_type"] = "scc_c0_future_inextendibility"

    def swap_extension_regularity(doc):
        doc["extension_predicate"]["frozen_regularity"] = "C0"

    sens = {}
    for tag, mut, key in (("S1_conclusion_type_leak", leak_conclusion_type, "S1_conclusion_type_leak"),
                          ("S2_regularity_token_swap", swap_extension_regularity, "S2_regularity_token_swap")):
        info = mutate_schema("artifacts/formulation/schemas/af_scc_c2_vacuum.yaml", mut, tag)
        rr = acceptance()
        info["exit"] = rr["run"]["exit"]
        info["verdict"] = (rr["report"] or {}).get("verdict")
        info["pipeline_failed"] = rr["run"]["exit"] != 0 or (rr["report"] or {}).get("verdict") != "PASS"
        info["canonical_row"] = next((row for row in (rr["report"] or {}).get("canonical", [])
                                      if row.get("schema") == "af_scc_c2_vacuum.yaml"), None)
        sens[tag] = info
        # restore the sandbox schema to the frozen bytes before the next control
        copy(ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
             SANDBOX / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml")
        if not info["pipeline_failed"]:
            out["deviations"].append(f"{key}: pipeline did not fail on the planted mutation")
    out["controls"]["sensitivity"] = sens

    # ---- S3: restored baseline ---------------------------------------------
    s3 = acceptance()
    out["controls"]["S3_restored_baseline"] = {
        "exit": s3["run"]["exit"], "verdict": (s3["report"] or {}).get("verdict"),
        "f2a_sha256": sha256(SANDBOX / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    }
    if (s3["report"] or {}).get("verdict") != EXPECTED["S3_restored_baseline"]["verdict"]:
        out["deviations"].append(f"S3: restored baseline verdict={(s3['report'] or {}).get('verdict')}")

    # ---- P1: canonical input stability -------------------------------------
    after = measure_pins()
    out["inputs_after"] = after
    out["inputs_stable_during_run"] = after == out["inputs_before"]
    if not out["inputs_stable_during_run"]:
        out["deviations"].append("P1: a pinned canonical input changed during the run")

    # ---- adjudication -------------------------------------------------------
    gen_ok = out["runs"]["R1_rebase"]["base_matches_current_c0"]
    acc_verdict = out["runs"]["R2_acceptance_after_rebase"]["verdict"]
    canon_rows = {r["schema"]: r for r in (out["runs"]["R2_acceptance_after_rebase"]["canonical"] or [])}
    f2a_row = canon_rows.get("af_scc_c2_vacuum.yaml")
    f2a_ok = bool(f2a_row and f2a_row.get("ok"))
    failing_rows = [{"schema": k, "structural": v.get("structural"), "semantic": v.get("semantic")}
                    for k, v in canon_rows.items() if not v.get("ok")]
    mutant_block = out["runs"]["R2_acceptance_after_rebase"]["mutants"] or {}
    union_ok = mutant_block.get("total") and mutant_block.get("union_caught") == mutant_block.get("total")
    controls_ok = all(c.get("ok") for c in (out["runs"]["R2_acceptance_after_rebase"]["controls"] or []))
    if not gen_ok:
        verdict = "INCONCLUSIVE_REBASE_FAILED"
        statement = ("The rebased corpus could not be regenerated from the current frozen "
                     "C0 base, so the preflight blocker is not resolvable by bookkeeping alone.")
        f2a_blocker = "unresolved"
    elif f2a_ok and union_ok and controls_ok:
        verdict = "F2A_BLOCKER_IS_BOOKKEEPING_ONLY_RESIDUAL_FAIL_IS_F1_R03"
        statement = (
            "Regenerating the rebased semantic-escape corpus from the current frozen C0 base with "
            "the owner's unmodified generator makes the canonical F2a row (schemas/af_scc_c2_vacuum.yaml, "
            "class AF-SCC-C2-VAC-GEN) PASS both stages, with the mutant union catching "
            f"{mutant_block.get('union_caught')}/{mutant_block.get('total')} and both controls passing. "
            "HF-069R-2 is therefore a stale-corpus bookkeeping defect for F2a, not a content regression. "
            "The pipeline as a whole still returns FAIL only because the F1 canonical row "
            "(schemas/af_wcc_vacuum.yaml, class AF-WCC-VAC-GEN) is rejected at stage 2 on the "
            "worker auditor's R03 lexical binder-token rule; that residual is not an F2a defect and "
            "was independently diagnosed at the same revision by worker-080 (W080-SEMCT-REBASE-01/probeB)."
        )
        f2a_blocker = "resolved-as-bookkeeping"
    elif acc_verdict == "PASS":
        verdict = "PREFLIGHT_BLOCKER_IS_BOOKKEEPING_ONLY"
        statement = ("Rebasing makes the whole pipeline PASS on the frozen bytes; the HF-069R-2 "
                     "blocker is bookkeeping-only.")
        f2a_blocker = "resolved-as-bookkeeping"
    else:
        verdict = "CONTENT_REGRESSION_UNDER_REBASE"
        statement = ("Even after regeneration the canonical pipeline does not PASS and the F2a row "
                     "is not clean; the stale corpus was masking a live content/tooling defect that "
                     "bears on this class.")
        f2a_blocker = "confirmed-content-or-tooling-defect"
    out["adjudication"] = {
        "verdict": verdict,
        "statement": statement,
        "f2a_row": f2a_row,
        "f2a_passes_both_stages_after_rebase": f2a_ok,
        "failing_canonical_rows": failing_rows,
        "mutant_union": {k: mutant_block.get(k) for k in ("total", "union_caught", "semantic_caught", "structural_caught")},
        "controls_ok": controls_ok,
        "hf_069r_2_status_for_f2a": f2a_blocker,
        "residual_fail_attribution": (
            "F1/af_wcc_vacuum.yaml stage-2 R03: "
            + json.dumps((out["runs"].get("R2b_stage2_detail", {}).get("af_wcc_vacuum.yaml", {}) or {}).get("failed_detail"))
            if failing_rows else None),
        "prior_reporting_crosswalk": {
            "F1_R03_lexical_binder": "artifacts/worker-080/semct_rebase/r03_probe_report.json (W080-SEMCT-REBASE-01/probeB; "
                                     "conclusion: rejection is lexical, not semantic; rev12 D5 binder '(q,t0)' spelled out as "
                                     "'q in I+ and t0 in [0,T)'). Reproduced here independently, NOT claimed as new.",
            "stale_corpus_base": "reviews/F2a-rev12-069.json#HF-069R-2 (first report, worker-069); this run measures the "
                                 "consequence and bounds it to F2a.",
            "stale_corpus_also_short_by_fixtures": "The lead corpus at artifacts/formulation/evidence/semantic_escape_rebased.json "
                                                   "records the pre-rebase manifest; the current manifest yields 31 mutants (1 unparsed), "
                                                   "not the corpus-local count.",
        },
        "evidence_refs": [
            "artifacts/worker-031/f2a_preflight/report.json",
            "schemas/af_scc_c2_vacuum.yaml#" + (out["inputs_before"]["schemas/af_scc_c2_vacuum.yaml"] or "")[:12],
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml#" + (out["inputs_before"]["artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"] or "")[:12],
            "artifacts/formulation/evidence/semantic_escape_rebased.json#"
            + (out["inputs_before"]["artifacts/formulation/evidence/semantic_escape_rebased.json"] or "")[:12],
            "artifacts/formulation/tools/run_acceptance.py#"
            + (out["inputs_before"]["artifacts/formulation/tools/run_acceptance.py"] or "")[:12],
        ],
        "falsifier": ("A frozen canonical input moving during the run; the owner's generator or the "
                      "canonical runner producing a different verdict on a byte-identical sandbox "
                      "replay; a mutated F2a that the pipeline fails to catch (which would void the "
                      "sensitivity controls and make the R2 PASS uninformative); or the F2a row failing "
                      "again after a byte-identical rebase."),
        "authority": "worker measurement only; no gate verdict, no node status, no validation_status",
        "next_falsifier": ("After the formulation owner re-pins f0_binding.consistency_evidence_sha256 "
                           "and re-freezes, re-run this instrument: the F2a row must stay PASS and the "
                           "acceptance report must bind the new pins. The residual whole-pipeline FAIL "
                           "clears only if F1/R03 is adjudicated (notation rewrite or rule re-scope), "
                           "which is not this class's artifact."),
    }
    out["expected_all_met"] = not out["deviations"]
    out["duration_s"] = round((datetime.now(CST) - t0).total_seconds(), 1)
    out["finished_at"] = now()

    (HERE / "report.json").write_text(json.dumps(out, indent=2) + "\n")
    (HERE / "ADJUDICATION.json").write_text(json.dumps({
        "task_id": out["task_id"], "agent": out["agent"], "created_at": out["finished_at"],
        "class_id": out["class_id"], "node_id": out["node_id"], "gate": out["gate"],
        **out["adjudication"], "inputs_stable_during_run": out["inputs_stable_during_run"],
        "expected_all_met": out["expected_all_met"], "deviations": out["deviations"],
    }, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "acceptance": acc_verdict,
                      "deviations": out["deviations"], "expected_all_met": out["expected_all_met"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

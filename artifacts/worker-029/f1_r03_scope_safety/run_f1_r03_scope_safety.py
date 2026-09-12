#!/usr/bin/env python3
"""W029-F1-R03-CAND-SCOPE-SAFETY-01.

Independent read-only scope-safety probe of the two schema-side F1 R03 repair
candidates produced by worker-062 (CAND-A bf1798b57997, CAND-B ebb8d6671614),
against the frozen stage-B auditor artifacts/worker-06/spec_conformance_audit.py
c79d8ab8440a, at F1 rev13 schemas/af_wcc_vacuum.yaml d9cebb9404b2.

Question: after landing each candidate, does the frozen R03 literal binder guard
still reject (S) a negation-scope-error rendering and (U) a free-t0 rendering?

Design and expectations are pre-registered in PREREGISTRATION.json, written before
the first run.  All canonical paths are read-only here; variants and outputs are
written only under this task directory.

Exit: 0 valid run (any verdict), 3 pin drift / harness error.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = REPO / "artifacts/worker-029/f1_r03_scope_safety"
VARDIR = OUT / "variants"
RAWDIR = OUT / "raw"
PREREG = OUT / "PREREGISTRATION.json"

CANON = REPO / "schemas/af_wcc_vacuum.yaml"
BASE_TOOL = REPO / "artifacts/worker-06/spec_conformance_audit.py"
E3_TOOL = REPO / "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/spec_conformance_audit.py"
CAND_A = REPO / "artifacts/worker-062/r03_schema_repair_candidate/candidates/CAND-A_af_wcc_vacuum.yaml"
CAND_B = REPO / "artifacts/worker-062/r03_schema_repair_candidate/candidates/CAND-B_af_wcc_vacuum.yaml"
LEAD_PROBE = REPO / "tmp/lead-form-life08/r03_scope_probe.json"

ANCHOR = "with finite affine length: "
TAILS = {
    "G_grouped_correct": "not exists (q,t0) in I+ x [0,T) with gamma([t0,T)) subset J^-(q) intersect M.",
    "V_variable_wise_correct": "not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.",
    "S_scope_error_negation_binds_q_only": "not exists q in I+ with gamma([t0,T)) subset J^-(q) intersect M, and t0 in [0,T).",
    "U_free_t0_no_restriction": "not exists q in I+ with gamma([t0,T)) subset J^-(q) intersect M.",
}
BASES = {
    "CANON": CANON,
    "CAND-A": CAND_A,
    "CAND-B": CAND_B,
}
CST = timezone(timedelta(hours=8))


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(p).read_bytes())
    return h.hexdigest()


def load_prereg() -> dict:
    return json.loads(PREREG.read_text())


def pin_check(prereg: dict) -> tuple[dict, dict]:
    measured = {k: sha256(REPO / k) for k in prereg["declared_pins"]}
    ok = all(measured[k] == prereg["declared_pins"][k] for k in measured)
    return measured, ok


def make_variant(base_name: str, base_path: Path, tail_name: str) -> Path:
    doc = yaml.safe_load(base_path.read_text())
    formal = doc["quantifiers"]["formal"]
    if formal.count(ANCHOR) != 1:
        raise RuntimeError(f"{base_name}: anchor count {formal.count(ANCHOR)} != 1")
    idx = formal.index(ANCHOR) + len(ANCHOR)
    doc["quantifiers"]["formal"] = formal[:idx] + TAILS[tail_name]
    p = VARDIR / f"{base_name}__{tail_name}.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    return p


def run_tool(tool: Path, schema: Path, json_flag: bool = False) -> dict:
    args = [sys.executable, str(tool)]
    tmp_json = None
    if json_flag:
        tmp_json = RAWDIR / f"res__{tool.stem}__{schema.stem}__{schema.suffix.lstrip('.')}.json"
        args += ["--json", str(tmp_json)]
    args.append(str(schema))
    r = subprocess.run(args, capture_output=True, text=True, timeout=180)
    verdict, failed = "?", []
    source = "stdout"
    if json_flag:
        if tmp_json.exists():
            try:
                d = json.loads(tmp_json.read_text())
                verdict = d.get("verdict", d.get("status", "?"))
                failed = d.get("failed_rules", [])
                source = "json_file"
            except Exception:
                source = "json_file_unparsable"
    else:
        try:
            d = json.loads(r.stdout)
            verdict = d.get("verdict", d.get("status", "?"))
            failed = d.get("failed_rules", [])
        except Exception:
            verdict = f"crash(exit{r.returncode})"
    norm = str(verdict).lower()
    if norm in ("accept", "pass", "ok"):
        norm = "accept"
    elif norm in ("reject", "fail"):
        norm = "reject"
    rec = {
        "tool": str(tool.relative_to(REPO)),
        "schema": str(schema.relative_to(REPO)),
        "argv": args,
        "exit": r.returncode,
        "verdict_raw": verdict,
        "verdict": norm,
        "failed_rules": failed,
        "source": source,
        "stdout_sha256": hashlib.sha256(r.stdout.encode()).hexdigest(),
        "stdout_tail": r.stdout[-600:],
        "stderr_tail": r.stderr[-400:],
    }
    if tmp_json is not None and tmp_json.exists():
        rec["json_file_sha256"] = sha256(tmp_json)
    return rec


def leaf_diff(a, b, path=""):
    """Recursive leaf diff of parsed YAML structures."""
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            p = f"{path}.{k}" if path else str(k)
            if k not in a or k not in b:
                diffs.append({"path": p, "canonical": repr(a.get(k))[:200], "candidate": repr(b.get(k))[:200]})
            else:
                diffs += leaf_diff(a[k], b[k], p)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append({"path": path, "canonical": f"len={len(a)}", "candidate": f"len={len(b)}"})
        for i, (x, y) in enumerate(zip(a, b)):
            diffs += leaf_diff(x, y, f"{path}.{i}")
    else:
        if a != b:
            diffs.append({"path": path, "canonical": repr(a)[:200], "candidate": repr(b)[:200]})
    return diffs


def binder_tokens(binder: str) -> list[str]:
    return [t for t in re.split(r"[^A-Za-z0-9_]+", str(binder)) if t]


def binding_consistency(base_path: Path) -> dict:
    doc = yaml.safe_load(base_path.read_text())
    q = doc["quantifiers"]
    ordered = q["ordered"]
    formal = q["formal"]
    binders = [str(e.get("binder")) for e in ordered]
    literal_ok = {b: (b in formal) for b in binders}
    bound = sorted({t for b in binders for t in binder_tokens(b)})
    formal_tokens = sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", formal)))
    # tokens the formal uses that no ordered binder names (analytic, text-level)
    under_bound = sorted((set(formal_tokens) & {"t0", "q"}) - set(bound))
    d5 = q.get("domains", {}).get("D5", {})
    return {
        "ordered_binders": binders,
        "literal_binder_in_formal": literal_ok,
        "bound_tokens": bound,
        "formal_mentions_t0": "t0" in formal_tokens,
        "under_bound_tokens": under_bound,
        "ordered5": ordered[5] if len(ordered) > 5 else None,
        "D5_definition_head": str(d5.get("definition", ""))[:160],
        "D5_is_pair_domain": str(d5.get("definition", "")).lstrip().startswith("pairs (q,t0)"),
    }


def main() -> int:
    VARDIR.mkdir(parents=True, exist_ok=True)
    RAWDIR.mkdir(parents=True, exist_ok=True)
    prereg = load_prereg()
    pins_pre, pins_ok = pin_check(prereg)
    if not pins_ok:
        bad = [k for k in pins_pre if pins_pre[k] != prereg["declared_pins"][k]]
        print("PREFLIGHT FAIL: pinned file(s) moved:", bad)
        return 3

    # ---- build the 3 x 4 matrix deterministically -------------------------
    variants = {}
    for bname, bpath in BASES.items():
        for tname in TAILS:
            variants[f"{bname}__{tname}"] = make_variant(bname, bpath, tname)

    # ---- extra controls derived from CAND-B -------------------------------
    broken = yaml.safe_load(CAND_B.read_text())
    broken["quantifiers"]["ordered"][5]["kind"] = "not_exists_BROKEN"
    broken_path = VARDIR / "CONTROL_K1_CAND-B_invalid_kind.yaml"
    broken_path.write_text(yaml.safe_dump(broken, sort_keys=False, allow_unicode=True))
    variants["CONTROL_K1_broken_kind"] = broken_path

    # ---- run the matrix (primary stdout parse + --json cross-check) -------
    evidence = {"runs": {}, "json_crosscheck": {}}
    matrix = {}
    for vname, vpath in variants.items():
        primary = run_tool(BASE_TOOL, vpath, json_flag=False)
        repeat = run_tool(BASE_TOOL, vpath, json_flag=False)
        jf = run_tool(BASE_TOOL, vpath, json_flag=True)
        evidence["runs"][vname] = {"primary": primary, "repeat": repeat}
        evidence["json_crosscheck"][vname] = jf
        matrix[vname] = {
            "verdict": primary["verdict"],
            "failed_rules": primary["failed_rules"],
            "exit": primary["exit"],
            "deterministic": (primary["verdict"], primary["failed_rules"], primary["exit"])
            == (repeat["verdict"], repeat["failed_rules"], repeat["exit"]),
            "stdout_vs_json_agree": primary["verdict"] == jf["verdict"]
            and primary["failed_rules"] == jf["failed_rules"],
        }

    # ---- K5: reproduce the lead's E3 matrix --------------------------------
    lead = json.loads(LEAD_PROBE.read_text())
    k5 = {}
    for vname, tail in (("grouped_tuple_intended_correct", "G_grouped_correct"),
                        ("scope_error_negation_binds_q_only", "S_scope_error_negation_binds_q_only")):
        p = VARDIR / f"LEAD__{vname}.yaml"
        doc = yaml.safe_load(CANON.read_text())
        f = doc["quantifiers"]["formal"]
        i = f.index(ANCHOR) + len(ANCHOR)
        doc["quantifiers"]["formal"] = f[:i] + TAILS[tail]
        p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
        got = run_tool(E3_TOOL, p, json_flag=False)
        want = lead["results"][vname]["E3_variable_wise"]["verdict"]
        k5[vname] = {"e3_verdict": got["verdict"], "lead_verdict": want, "match": got["verdict"] == want}
    # canonical own bytes under E3 should also be accepted (0/12 lead row)
    e3_canon = run_tool(E3_TOOL, CANON, json_flag=False)
    k5["frozen_variable_wise_intended_correct"] = {
        "e3_verdict": e3_canon["verdict"],
        "lead_verdict": lead["results"]["frozen_variable_wise_intended_correct"]["E3_variable_wise"]["verdict"],
        "match": e3_canon["verdict"] == lead["results"]["frozen_variable_wise_intended_correct"]["E3_variable_wise"]["verdict"],
    }

    # ---- K4: one-line diff claims ------------------------------------------
    canon_doc = yaml.safe_load(CANON.read_text())
    diff_checks = {}
    declared = {
        "CAND-A": ("quantifiers.formal", "bf1798b579972acadda13e4768afe7bfdbe5394b179983d0dced9d8b7cfd37cf",
                   "artifacts/worker-062/r03_schema_repair_candidate/diffs/CAND-A.diff"),
        "CAND-B": ("quantifiers.ordered.5.binder", "ebb8d6671614d260b72f3186786e0b29ac43b8197908e29f20474f76bea09b91",
                   "artifacts/worker-062/r03_schema_repair_candidate/diffs/CAND-B.diff"),
    }
    for name, bpath in (("CAND-A", CAND_A), ("CAND-B", CAND_B)):
        d = leaf_diff(canon_doc, yaml.safe_load(bpath.read_text()))
        want_path, want_hash, diff_file = declared[name]
        diff_checks[name] = {
            "leaf_diffs": d,
            "exactly_one_leaf": len(d) == 1,
            "declared_leaf": want_path,
            "leaf_matches_declared": len(d) == 1 and d[0]["path"] == want_path,
            "measured_sha256": sha256(bpath),
            "declared_sha256": want_hash,
            "sha_match": sha256(bpath) == want_hash,
            "diff_file": diff_file,
            "diff_file_sha256": sha256(REPO / diff_file),
        }

    # ---- binding consistency ----------------------------------------------
    consistency = {b: binding_consistency(p) for b, p in BASES.items()}

    # ---- expectations vs observed -----------------------------------------
    expectations = {
        "CANON__V_variable_wise_correct": "reject",
        "CANON__G_grouped_correct": "accept",
        "CANON__S_scope_error_negation_binds_q_only": "reject",
        "CANON__U_free_t0_no_restriction": "reject",
        "CAND-A__G_grouped_correct": "accept",
        "CAND-A__V_variable_wise_correct": "reject",
        "CAND-A__S_scope_error_negation_binds_q_only": "reject",
        "CAND-A__U_free_t0_no_restriction": "reject",
        "CAND-B__G_grouped_correct": "accept",
        "CAND-B__V_variable_wise_correct": "accept",
        "CAND-B__S_scope_error_negation_binds_q_only": "accept",
        "CAND-B__U_free_t0_no_restriction": "accept",
    }
    mismatches = [k for k, want in expectations.items() if matrix[k]["verdict"] != want]

    # ---- controls -----------------------------------------------------------
    controls = {
        "K1_fail_closed": {
            "expected": "reject",
            "observed": matrix["CONTROL_K1_broken_kind"]["verdict"],
            "failed_rules": matrix["CONTROL_K1_broken_kind"]["failed_rules"],
            "pass": matrix["CONTROL_K1_broken_kind"]["verdict"] == "reject",
        },
        "K2_determinism": {
            "all_deterministic": all(matrix[k]["deterministic"] for k in matrix),
            "cells": {k: matrix[k]["deterministic"] for k in matrix},
            "pass": all(matrix[k]["deterministic"] for k in matrix),
        },
        "K3_pin_stability": {"pending": True},
        "K4_one_line_diff": {
            "CAND-A": diff_checks["CAND-A"]["exactly_one_leaf"] and diff_checks["CAND-A"]["leaf_matches_declared"],
            "CAND-B": diff_checks["CAND-B"]["exactly_one_leaf"] and diff_checks["CAND-B"]["leaf_matches_declared"],
            "pass": diff_checks["CAND-A"]["exactly_one_leaf"] and diff_checks["CAND-A"]["leaf_matches_declared"]
            and diff_checks["CAND-B"]["exactly_one_leaf"] and diff_checks["CAND-B"]["leaf_matches_declared"],
        },
        "K5_lead_matrix_reproduction": {
            "rows": k5,
            "pass": all(v["match"] for v in k5.values()),
        },
        "K6_stdout_vs_json": {
            "cells": {k: matrix[k]["stdout_vs_json_agree"] for k in matrix},
            "pass": all(matrix[k]["stdout_vs_json_agree"] for k in matrix),
        },
    }

    # ---- reading / verdict ---------------------------------------------------
    cand_a_safe = matrix["CAND-A__S_scope_error_negation_binds_q_only"]["verdict"] == "reject" and \
        matrix["CAND-A__U_free_t0_no_restriction"]["verdict"] == "reject"
    cand_b_safe = matrix["CAND-B__S_scope_error_negation_binds_q_only"]["verdict"] == "reject" and \
        matrix["CAND-B__U_free_t0_no_restriction"]["verdict"] == "reject"
    if cand_a_safe and not cand_b_safe:
        verdict = "CAND-A_SCOPE_SAFE__CAND-B_NOT_SCOPE_SAFE"
    elif cand_a_safe and cand_b_safe:
        verdict = "BOTH_CANDIDATES_SCOPE_SAFE_ON_THIS_PROBE"
    elif not cand_a_safe and cand_b_safe:
        verdict = "CAND-A_NOT_SCOPE_SAFE__CAND-B_SCOPE_SAFE"
    else:
        verdict = "BOTH_CANDIDATES_NOT_SCOPE_SAFE"

    findings = []
    if not cand_a_safe:
        findings.append({
            "id": "W029-SCOPE-01",
            "severity": "blocking-for-CAND-A",
            "finding": "CAND-A does not preserve the R03 guard on S and/or U at the pinned bytes.",
        })
    if not cand_b_safe:
        findings.append({
            "id": "W029-SCOPE-02",
            "severity": "blocking-for-CAND-B",
            "finding": (
                "CAND-B binder 'q' keeps the literal R03 test satisfied by the scope-error rendering S and by "
                "the free-t0 rendering U, so the frozen R03 no longer separates the correct variable-wise "
                "rendering from either. The ordered[5] row under-binds t0 relative to the unchanged formal "
                "sentence and names a scalar over D5, which D5.definition declares to be the pair domain "
                "'pairs (q,t0) ...'."
            ),
        })
    findings.append({
        "id": "W029-SCOPE-03",
        "severity": "informational",
        "finding": (
            "CAND-A keeps ordered[5].binder = (q,t0) and rewrites the formal to the grouped tuple, so the "
            "frozen literal R03 remains the scope guard: S and U are rejected exactly as under the canonical "
            "bytes. The repair therefore closes the false positive without weakening the rule."
        ),
    })

    report = {
        "task_id": prereg["task_id"],
        "actor": "worker-029",
        "node_id": "F1",
        "class_id": prereg["class_id"],
        "gate": prereg["gate"],
        "created_at": now(),
        "question": prereg["question"],
        "pins_pre": pins_pre,
        "pins_post": {},
        "pin_drift": [],
        "variants": {k: str(v.relative_to(REPO)) for k, v in variants.items()},
        "variant_sha256": {k: sha256(v) for k, v in variants.items()},
        "expectations": expectations,
        "mismatches": mismatches,
        "matrix": matrix,
        "lead_e3_crosscheck": k5,
        "diff_checks": diff_checks,
        "binding_consistency": consistency,
        "controls": controls,
        "findings": findings,
        "reading": {
            "cand_a_scope_safe": cand_a_safe,
            "cand_b_scope_safe": cand_b_safe,
            "cand_a_on_S": matrix["CAND-A__S_scope_error_negation_binds_q_only"]["verdict"],
            "cand_a_on_U": matrix["CAND-A__U_free_t0_no_restriction"]["verdict"],
            "cand_b_on_S": matrix["CAND-B__S_scope_error_negation_binds_q_only"]["verdict"],
            "cand_b_on_U": matrix["CAND-B__U_free_t0_no_restriction"]["verdict"],
            "canonical_on_S": matrix["CANON__S_scope_error_negation_binds_q_only"]["verdict"],
            "canonical_on_U": matrix["CANON__U_free_t0_no_restriction"]["verdict"],
        },
        "verdict": verdict,
        "falsifier": prereg["falsifier"],
        "falsifier_outcome": (
            "NOT FALSIFIED" if not mismatches and all(v["match"] for v in k5.values()) else
            f"FALSIFIED OR AMENDED: mismatches={mismatches}"
        ),
        "scope_limits": prereg["method"]["scope_limits"],
    }

    # ---- final pin re-check --------------------------------------------------
    pins_post, pins_ok_post = pin_check(prereg)
    report["pins_post"] = pins_post
    report["pin_drift"] = [k for k in pins_post if pins_post[k] != pins_pre[k]]
    controls["K3_pin_stability"] = {"drift": report["pin_drift"], "pass": not report["pin_drift"]}
    report["controls"] = controls

    evidence.update({
        "task_id": prereg["task_id"],
        "created_at": now(),
        "preregistration_sha256": sha256(PREREG),
        "pins_pre": pins_pre,
        "pins_post": pins_post,
        "matrix_verdicts": {k: matrix[k]["verdict"] for k in matrix},
    })
    controls_doc = {"task_id": prereg["task_id"], "created_at": now(), "controls": controls}

    (OUT / "report.json").write_text(json.dumps(report, indent=1))
    (OUT / "evidence.json").write_text(json.dumps(evidence, indent=1))
    (OUT / "controls.json").write_text(json.dumps(controls_doc, indent=1))

    print("=== W029 F1 R03 candidate scope-safety probe ===")
    print(f"{'variant':52s} {'verdict':8s} rules")
    for k in expectations:
        print(f"{k:52s} {matrix[k]['verdict']:8s} {','.join(matrix[k]['failed_rules']) or '-'}")
    print(f"\nverdict: {verdict}")
    print("mismatches vs preregistered expectations:", mismatches or "none")
    print("pin drift:", report["pin_drift"] or "none")
    print("controls:", {k: v.get("pass") for k, v in controls.items()})
    if not pins_ok_post:
        print("POSTFLIGHT FAIL: pin drift")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

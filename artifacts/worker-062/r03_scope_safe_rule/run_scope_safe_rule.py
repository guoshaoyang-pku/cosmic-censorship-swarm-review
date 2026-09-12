#!/usr/bin/env python3
"""W062-GFORM-R03-SCOPE-SAFE-RULE-CANDIDATE-01 harness (worker-062, 2026-09-12).

Bounded class-bound task on node F1 / class AF-WCC-VAC-GEN, gate G-FORM.
Question: is there a minimal scope-aware amendment of the R03 binder check that
fixes the literal-match false positive on canonical F1 WITHOUT the over-acceptance
the formulation lead measured for the plain variable-wise repair (cand_E3)?

Read-only with respect to every pinned/canonical path. All writes go under
artifacts/worker-062/r03_scope_safe_rule/sandbox/ (plus the report files).

Exit codes: 0 all expectations+controls pass, 2 expectation failure,
            3 input pin drift, 4 control failure.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SANDBOX = HERE / "sandbox"
CST = timezone(timedelta(hours=8))

PINS = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/worker-06/spec_conformance_audit.py": "c79d8ab8440ac6738bb61df5a33e9fd5f8319b4e74e1f2e9c0fc5083fb408cec",
    "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/spec_conformance_audit.py": "3f69bc1eb27adf3a3318b893364018112fa8eff0ee312c7fe825dd579cfc5703",
    "artifacts/formulation/rule_spec.json": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
}
INFO_PIN = "artifacts/formulation/FROZEN.json"

BASE_TOOL = ROOT / "artifacts/worker-06/spec_conformance_audit.py"
E3_TOOL = ROOT / "artifacts/worker-064/r03_cause/work/cand_E3/artifacts/worker-06/spec_conformance_audit.py"
SPEC = ROOT / "artifacts/formulation/rule_spec.json"
F1 = ROOT / "schemas/af_wcc_vacuum.yaml"
F2A = ROOT / "schemas/af_scc_c2_vacuum.yaml"
F2B = ROOT / "schemas/af_scc_c0_vacuum.yaml"

TAIL_ANCHOR = "with finite affine length: "

VARIANTS = {
    "V0_frozen_variable_wise": "not exists q in I+ and t0 in [0,T) with gamma([t0,T)) subset J^-(q) intersect M.",
    "V1_grouped_D5": "not exists (q,t0) in D5 with gamma([t0,T)) subset J^-(q) intersect M.",
    "V2_grouped_product": "not exists (q,t0) in I+ x [0,T) with gamma([t0,T)) subset J^-(q) intersect M.",
    "V3_scope_error_lead": "not exists q in I+ with gamma([t0,T)) subset J^-(q) intersect M, and t0 in [0,T).",
    "V4a_unbound_restriction_body_keeps_names": "not exists s in D5 with gamma([t0,T)) subset J^-(q) intersect M.",
    "V4b_fully_unbound": "not exists s in D5 with gamma([s,T)) subset J^-(s) intersect M.",
    "V5_shadow_quantifier": "forall t0 in [0,T) : not exists q in I+ with gamma([t0,T)) subset J^-(q) intersect M.",
    "V6_reordered_restriction": "not exists t0 in [0,T) and q in I+ with gamma([t0,T)) subset J^-(q) intersect M.",
    "V7_wrong_variable_name": "not exists q in I+ and tau in [0,T) with gamma([tau,T)) subset J^-(q) intersect M.",
}

BASE_BLOCK = '''            else:
                for b in binders:
                    if b not in formal:
                        bad.append(f"binder {b!r} absent from formal sentence")
'''

E4_BLOCK = '''            else:
                # --- E4 scope-aware binder check (W062 sandbox candidate) ---
                _quant_re = re.compile(r"\\b(not\\s+exists|exists\\s+unique|exists|forall)\\b")
                _seg_terms = (" with ", " such that ", " so that ", ":")
                _segs = []
                for _m in _quant_re.finditer(formal):
                    _end = len(formal)
                    for _t in _seg_terms:
                        _j = formal.find(_t, _m.end())
                        if _j != -1:
                            _end = min(_end, _j)
                    _segs.append((_m.group(1).replace(" ", "_"), formal[_m.start():_end]))
                _aligned = len(_segs) == len(binders)
                for _bi, _b in enumerate(binders):
                    if _b in formal:
                        continue
                    _parts = [p.strip() for p in _b.strip("()").split(",") if p.strip()]
                    _ent = ordered[_bi] if _bi < len(ordered) and isinstance(ordered[_bi], dict) else {}
                    if _aligned and _parts and _bi < len(_segs):
                        _kind, _seg = _segs[_bi]
                        if _kind == _ent.get("kind") and all(
                            re.search(r"(?<![A-Za-z0-9_])" + re.escape(p) + r"(?![A-Za-z0-9_])", _seg)
                            for p in _parts
                        ):
                            continue
                    bad.append(f"binder {_b!r} absent from formal sentence (E4 scope-aware)")
'''

E4_NOSCOPE_BLOCK = '''            else:
                for _b in binders:
                    if _b in formal:
                        continue
                    _parts = [p.strip() for p in _b.strip("()").split(",") if p.strip()]
                    if _parts and all(p in formal for p in _parts):
                        continue
                    bad.append(f"binder {_b!r} absent from formal sentence (E4-noscope control)")
'''


def now():
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_tool(src: Path, dst: Path, block_new: str | None) -> str:
    text = src.read_text()
    if block_new is not None:
        n = text.count(BASE_BLOCK)
        if n != 1:
            raise SystemExit(f"[C6 FAIL] baseline block occurs {n} times in {src}")
        text = text.replace(BASE_BLOCK, block_new)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text)
    return sha256_file(dst)


def make_variant(canon_doc: dict, tail: str, dst: Path):
    doc = json.loads(json.dumps(canon_doc))  # deep copy, YAML-safe values only
    formal = doc["quantifiers"]["formal"]
    idx = formal.index(TAIL_ANCHOR) + len(TAIL_ANCHOR)
    doc["quantifiers"]["formal"] = formal[:idx] + tail
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))


def run_tool(tool: Path, schema: Path, out: Path):
    cmd = [sys.executable, str(tool), str(schema), "--spec", str(SPEC), "--json", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    rep = {}
    if out.exists():
        try:
            rep = json.loads(out.read_text())
        except Exception:
            rep = {}
        out.unlink()
    failed = rep.get("failed_rules", [])
    return {
        "exit": r.returncode,
        "verdict": rep.get("verdict", "?"),
        "failed_rules": failed,
        "doc_sha256": rep.get("doc_sha256"),
        "undecided_rules": rep.get("undecided_rules", []),
        "tool_sha256": sha256_file(tool),
        "stderr_tail": r.stderr.strip()[-300:],
    }


def cell(row, tool):
    c = row[tool]
    return f"{c['verdict']}/{','.join(c['failed_rules']) or '-'}"


def main():
    started = now()
    print(f"=== W062 R03 scope-safe rule candidate @ {started} ===")

    # ---- C1 pin gate -------------------------------------------------------
    pre = {k: sha256_file(ROOT / k) for k in PINS}
    drift = {k: {"expected": PINS[k], "measured": v} for k, v in pre.items() if v != PINS[k]}
    info_pre = sha256_file(ROOT / INFO_PIN)
    if drift:
        print("[C1 FAIL] input pin drift:", json.dumps(drift, indent=1))
        (HERE / "PIN_DRIFT.json").write_text(json.dumps({"drift": drift, "at": started}, indent=1))
        return 3
    print(f"[C1] {len(pre)} input pins verified")

    # ---- build sandbox -----------------------------------------------------
    if SANDBOX.exists():
        shutil.rmtree(SANDBOX)
    tools = SANDBOX / "tools"
    variants_dir = SANDBOX / "variants"
    out_dir = SANDBOX / "out"
    for d in (tools, variants_dir, out_dir):
        d.mkdir(parents=True, exist_ok=True)

    tool_paths = {
        "baseline_literal": tools / "base/spec_conformance_audit.py",
        "E3_variable_wise": tools / "E3/spec_conformance_audit.py",
        "E4_scope_aware": tools / "E4/spec_conformance_audit.py",
        "E4_noscope_control": tools / "E4_noscope/spec_conformance_audit.py",
    }
    tool_hashes = {
        "baseline_literal": build_tool(BASE_TOOL, tool_paths["baseline_literal"], None),
        "E3_variable_wise": build_tool(E3_TOOL, tool_paths["E3_variable_wise"], None),
        "E4_scope_aware": build_tool(BASE_TOOL, tool_paths["E4_scope_aware"], E4_BLOCK),
        "E4_noscope_control": build_tool(BASE_TOOL, tool_paths["E4_noscope_control"], E4_NOSCOPE_BLOCK),
    }
    # C7: rebuild E4 deterministically
    rebuilt = build_tool(BASE_TOOL, tools / "E4_rebuild/spec_conformance_audit.py", E4_BLOCK)
    c7 = rebuilt == tool_hashes["E4_scope_aware"]
    print(f"[C7] E4 build determinism: {'PASS' if c7 else 'FAIL'}")
    if not c7:
        return 4
    # C6 already enforced in build_tool; record the one-hunk property
    base_text = BASE_TOOL.read_text()
    e4_text = (tools / "E4/spec_conformance_audit.py").read_text()
    e4_hunks = sum(1 for a, b in zip(base_text.splitlines(), e4_text.splitlines()) if a != b)
    line_delta = len(e4_text.splitlines()) - len(base_text.splitlines())
    print(f"[C6] E4 differs from baseline in {e4_hunks} changed line(s), {line_delta:+d} line(s)")

    # ---- variants ----------------------------------------------------------
    canon = yaml.safe_load(F1.read_text())
    variant_paths = {}
    for name, tail in VARIANTS.items():
        p = variants_dir / f"{name}.yaml"
        make_variant(canon, tail, p)
        variant_paths[name] = p
    malformed = json.loads(json.dumps(canon))
    malformed["quantifiers"].pop("ordered", None)
    malformed_path = variants_dir / "V8_malformed_no_ordered.yaml"
    malformed_path.write_text(yaml.safe_dump(malformed, sort_keys=False, allow_unicode=True))
    print(f"[build] {len(variant_paths)} variants + 1 malformed control")

    targets = dict(variant_paths)
    targets["F2a_canonical"] = F2A
    targets["F2b_canonical"] = F2B

    # ---- matrix ------------------------------------------------------------
    results = {}
    for tname, tool in tool_paths.items():
        results[tname] = {}
        for vname, vpath in targets.items():
            runs = [run_tool(tool, vpath, out_dir / f"{tname}__{vname}__{i}.json") for i in (1, 2)]
            r1, r2 = runs
            deterministic = (r1["verdict"], r1["failed_rules"], r1["doc_sha256"]) == (
                r2["verdict"], r2["failed_rules"], r2["doc_sha256"])
            rec = dict(r1)
            rec["deterministic"] = deterministic
            results[tname][vname] = rec
            print(f"  {tname:20s} {vname:44s} {cell(results[tname], vname)}  det={deterministic}")

    # malformed control (C4), all tools
    malformed_rows = {}
    for tname, tool in tool_paths.items():
        rec = run_tool(tool, malformed_path, out_dir / f"{tname}__V8.json")
        malformed_rows[tname] = rec
        print(f"  {tname:20s} {'V8_malformed_no_ordered':44s} {rec['verdict']}/{','.join(rec['failed_rules']) or '-'}")

    # ---- expectations ------------------------------------------------------
    def v(t, vn):
        return results[t][vn]["verdict"]

    def fr(t, vn):
        return results[t][vn]["failed_rules"]

    exp = {}
    exp["E1_baseline_rejects_V0"] = v("baseline_literal", "V0_frozen_variable_wise") == "reject" and "R03" in fr("baseline_literal", "V0_frozen_variable_wise")
    exp["E2_E3_accepts_V0"] = v("E3_variable_wise", "V0_frozen_variable_wise") == "accept"
    exp["E3_E3_accepts_V3"] = v("E3_variable_wise", "V3_scope_error_lead") == "accept"
    exp["E4_E4_accepts_V0_V1_V2_V6"] = all(v("E4_scope_aware", x) == "accept" for x in
                                           ("V0_frozen_variable_wise", "V1_grouped_D5", "V2_grouped_product", "V6_reordered_restriction"))
    exp["E5_E4_rejects_V3_V4a_V5"] = all(v("E4_scope_aware", x) == "reject" and "R03" in fr("E4_scope_aware", x) for x in
                                         ("V3_scope_error_lead", "V4a_unbound_restriction_body_keeps_names", "V5_shadow_quantifier"))
    exp["E6_E4_rejects_V4b_V7"] = all(v("E4_scope_aware", x) == "reject" for x in ("V4b_fully_unbound", "V7_wrong_variable_name"))
    exp["E7_F2_accept_all_tools"] = all(v(t, x) == "accept" for t in tool_paths for x in ("F2a_canonical", "F2b_canonical"))
    exp["E8_E4_noscope_equals_E3"] = all(
        (results["E4_noscope_control"][x]["verdict"], results["E4_noscope_control"][x]["failed_rules"])
        == (results["E3_variable_wise"][x]["verdict"], results["E3_variable_wise"][x]["failed_rules"])
        for x in targets)
    exp["E9_deterministic_all_cells"] = all(results[t][x]["deterministic"] for t in results for x in results[t])
    exp["E10_pins_unchanged_and_writes_confined"] = all(sha256_file(ROOT / k) == PINS[k] for k in PINS)
    exp["E11_one_hunk_patch"] = e4_hunks > 0 and (tools / "E4/spec_conformance_audit.py").read_text().count("E4 scope-aware") == 1
    exp["E12_literal_behavior_unchanged"] = all(
        results["baseline_literal"][x]["verdict"] == results["E4_scope_aware"][x]["verdict"]
        for x in ("V1_grouped_D5", "V2_grouped_product", "F2a_canonical", "F2b_canonical"))
    # E13: full pre-registered matrix, cell for cell
    prereg = json.loads((HERE / "PREREGISTRATION.json").read_text())["expected_matrix"]
    mismatch = []
    for x, cols in prereg.items():
        for t, expect in cols.items():
            got = v(t, x) + ("/R03" if "R03" in fr(t, x) else "")
            if got != expect:
                mismatch.append({"cell": f"{t}:{x}", "expected": expect, "got": got})
    exp["E13_full_matrix_matches_preregistration"] = not mismatch
    # C4 malformed
    c4 = all(malformed_rows[t]["verdict"] == "reject" and "R03" in malformed_rows[t]["failed_rules"] for t in malformed_rows)
    # C5 isolation
    info_post = sha256_file(ROOT / INFO_PIN)
    c5 = all(sha256_file(ROOT / k) == PINS[k] for k in PINS)
    c2 = exp["E9_deterministic_all_cells"]
    c3 = exp["E8_E4_noscope_equals_E3"]

    print("\n=== expectations ===")
    for k, ok in exp.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {k}")
    print(f"  {'PASS' if c4 else 'FAIL'}  C4_malformed_rejected_R03_all_tools")
    print(f"  {'PASS' if c5 else 'FAIL'}  C5_sandbox_isolation")
    print(f"  {'PASS' if c2 else 'FAIL'}  C2_determinism")
    print(f"  {'PASS' if c3 else 'FAIL'}  C3_noscope_equals_E3")

    all_exp = all(exp.values())
    all_ctl = c4 and c5 and c2 and c3 and c7
    verdict = "VALID" if (all_exp and all_ctl) else ("REFUTED" if not exp.get("E4_E4_accepts_V0_V1_V2_V6") or not exp.get("E5_E4_rejects_V3_V4a_V5") else "PARTIAL")
    print(f"\nverdict: {verdict}")

    # ---- writes ------------------------------------------------------------
    report = {
        "task_id": "W062-GFORM-R03-SCOPE-SAFE-RULE-CANDIDATE-01",
        "actor": "worker-062",
        "started_at": started,
        "finished_at": now(),
        "verdict": verdict,
        "exit_code": 0 if verdict == "VALID" else (2 if verdict == "PARTIAL" else 4),
        "inputs_pinned": PINS,
        "input_pins_pre": pre,
        "input_pins_post": {k: sha256_file(ROOT / k) for k in PINS},
        "frozen_json_informational": {"pre": info_pre, "post": info_post, "moved": info_pre != info_post},
        "tool_hashes": tool_hashes,
        "e4_patch": {"base_block_occurrences": base_text.count(BASE_BLOCK), "changed_lines": e4_hunks, "line_delta": line_delta,
                     "candidate_path": "artifacts/worker-062/r03_scope_safe_rule/sandbox/tools/E4/spec_conformance_audit.py"},
        "variants": {k: str(p.relative_to(ROOT)) for k, p in variant_paths.items()},
        "variant_tails": VARIANTS,
        "matrix": results,
        "malformed_control": malformed_rows,
        "expectations": exp,
        "controls": {"C1_pin_gate": True, "C2_determinism": c2, "C3_noscope_equals_E3": c3,
                     "C4_malformed_rejects_R03": c4, "C5_isolation": c5, "C6_patch_unique": True,
                     "C7_build_deterministic": c7, "C8_frozen_informational_only": True},
        "scope_limits": json.loads((HERE / "PREREGISTRATION.json").read_text())["scope_limits"],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    (HERE / "matrix.json").write_text(json.dumps({
        "columns": list(tool_paths),
        "rows": {x: {t: cell(results[t], x) for t in tool_paths} for x in targets},
    }, indent=1) + "\n")
    (HERE / "controls.json").write_text(json.dumps({
        "C1": "pass", "C2": c2, "C3": c3, "C4": c4, "C5": c5, "C6": True, "C7": c7, "C8": True,
        "malformed_control": {t: f"{r['verdict']}/{','.join(r['failed_rules']) or '-'}" for t, r in malformed_rows.items()},
    }, indent=1) + "\n")
    entry = {
        "PREREGISTRATION.json": sha256_file(HERE / "PREREGISTRATION.json"),
        "run_scope_safe_rule.py": sha256_file(HERE / "run_scope_safe_rule.py"),
        "report.json": sha256_file(HERE / "report.json"),
        "matrix.json": sha256_file(HERE / "matrix.json"),
        "controls.json": sha256_file(HERE / "controls.json"),
        "sandbox/tools/E4/spec_conformance_audit.py": tool_hashes["E4_scope_aware"],
        "sandbox/tools/E4_noscope/spec_conformance_audit.py": tool_hashes["E4_noscope_control"],
    }
    (HERE / "entry_hashes.json").write_text(json.dumps(entry, indent=1) + "\n")
    print("wrote report.json / matrix.json / controls.json / entry_hashes.json")
    return 0 if verdict == "VALID" else (2 if verdict == "PARTIAL" else 4)


if __name__ == "__main__":
    sys.exit(main())

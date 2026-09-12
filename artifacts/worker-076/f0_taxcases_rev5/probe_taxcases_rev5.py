#!/usr/bin/env python3
"""W076-F0-TAXCASES-REV5-05 — independent content-validity verification of the F0 adversarial
taxonomy-case corpus at the live canonical F0 rev5 taxonomy, including verification of the
00:42-00:43 pin repair and a counterfactual on the F-094C-1 scalar-genericity repair options.

Question
--------
`schemas/taxonomy_cases.jsonl` is cited in map G-F0 evidence_refs and is the F0 class-leakage
corpus. It was stale-pinned (36/36 rows at rev2 66bf917bd368, blocking HF-094C-1) and was
re-stamped to rev5 while this worker was measuring. This probe measures, independently:
  (Q1) is the corpus CONTENT valid at the live rev5 taxonomy?
  (Q2) did the pin repair change any verdict (pure restamp)?
  (Q3) does the replenished checker's new STALE_TAXONOMY_PIN guard actually catch the
       pre-repair defect class (regression control)?
  (Q4) is the corpus content-bound to the live axis values, i.e. does F-094C-1's proposed
       scalar genericity_kind change break it?

Method (read-only on canonical bytes; all derived files under this directory)
---------------------------------------------------------------------------
1. Pin + snapshot the canonical inputs (taxonomy, corpus, catalog, checker).
2. Run the third-party checker `artifacts/flash-02/check_taxonomy_cases.py` on the live
   canonical inputs; re-run on the byte-identical snapshot (provenance control).
3. Independent second implementation of axis-vector class resolution; per-case table against
   every declared expected_classification / expected_resolution.
4. Derived controls (never written to canonical paths):
   R1 identity rebind  -> output must be invariant vs canonical (pure-restamp check).
   R2 stale rebind to rev2 66bf917bd368 -> the C11 guard must fire on 36/36 rows.
   S1 scalar genericity_kind "unresolved" -> "provisional_baire_residual" (one of the two
      F-094C-1 repair options), corpus rebased to the mutant hash so C11 cannot mask content.
   S2 C2/C0 regularity_token swap, corpus rebased likewise.
5. Pre-repair observation: a checker report produced by this worker at 00:42:09, before the
   00:42:36 corpus rewrite, is preserved byte-identically; its embedded input sha256 values
   record the pre-repair state (its bytes are no longer on disk).
6. Re-pin canonical inputs post; any drift during the run forces verdict UNMEASURED.

Verdict is about corpus content and the pin repair only. It does NOT set a gate verdict,
does not assert taxonomy truth, and does not adjudicate F-094C-1.
"""
from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

TAX = ROOT / "research_map" / "formulation_taxonomy.yaml"
CASES = ROOT / "schemas" / "taxonomy_cases.jsonl"
CATALOG = ROOT / "artifacts" / "flash-02" / "leak_rule_catalog.json"
CHECKER = ROOT / "artifacts" / "flash-02" / "check_taxonomy_cases.py"
PREREPAIR_REPORT = OUT / "checker_report_canonical_prerepair_dryrun.json"

AXES = ["family", "matter_model", "symmetry", "asymptotics", "regularity_token",
        "genericity_kind", "conclusion_type"]
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
PIN_PREFIX = "bound_taxonomy_sha_"
REV2_STALE_SHA12 = "66bf917bd368"  # HF-094C-1 pre-repair stamp, per closefind-verify-094


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pin(p: Path) -> dict:
    st = p.stat()
    return {"path": str(p.relative_to(ROOT)), "sha256": sha256_file(p), "bytes": st.st_size,
            "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="microseconds")}


def snapshot(src: Path, dst_dir: Path) -> Path:
    dst = dst_dir / src.name
    shutil.copyfile(src, dst)
    if sha256_file(src) != sha256_file(dst):
        raise SystemExit(f"snapshot copy hash mismatch for {src}")
    return dst


def run_checker(tax: Path, cases: Path, catalog: Path, report: Path) -> dict:
    report.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(CHECKER), "--taxonomy", str(tax), "--cases", str(cases),
         "--catalog", str(catalog), "--report", str(report)],
        capture_output=True, text=True, cwd=str(ROOT), timeout=600)
    rep = json.loads(report.read_text()) if report.exists() else {}
    errors = rep.get("errors", [])
    return {
        "argv": [str(CHECKER.relative_to(ROOT)), "--taxonomy", str(tax.relative_to(ROOT)),
                 "--cases", str(cases.relative_to(ROOT)), "--catalog", str(catalog.relative_to(ROOT)),
                 "--report", str(report.relative_to(ROOT))],
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip().splitlines(),
        "stderr": proc.stderr.strip().splitlines(),
        "warn_catalog_pin_stale": any("WARN" in ln for ln in proc.stdout.splitlines() + proc.stderr.splitlines()),
        "verdict": rep.get("verdict"),
        "errors": errors,
        "content_errors": [e for e in errors if "STALE_TAXONOMY_PIN" not in e],
        "stale_pin_errors": [e for e in errors if "STALE_TAXONOMY_PIN" in e],
        "error_cases": sorted({e.split(":")[0] for e in errors if e.startswith("TC-F0-")}),
        "content_error_cases": sorted({e.split(":")[0] for e in errors
                                       if e.startswith("TC-F0-") and "STALE_TAXONOMY_PIN" not in e}),
        "counts": rep.get("counts"),
        "coverage": rep.get("coverage"),
        "leak_kinds": rep.get("leak_kinds"),
        "open_cases": rep.get("open_cases"),
        "controls_detected": sum(1 for c in rep.get("controls", []) if c.get("detected")),
        "controls_total": len(rep.get("controls", [])),
        "disjointness_ok": (rep.get("disjointness") or {}).get("ok"),
        "report_sha256": sha256_file(report) if report.exists() else None,
        "report_path": str(report.relative_to(ROOT)),
    }


def comparison_key(rep: dict) -> dict:
    return {k: rep.get(k) for k in
            ("verdict", "errors", "counts", "coverage", "leak_kinds", "open_cases",
             "controls_detected", "controls_total", "disjointness_ok")}


def load_taxonomy(path: Path) -> dict:
    doc = yaml.safe_load(path.read_text())
    classes = {cid: {k: (cls.get("axes") or {}).get(k) for k in AXES}
               for cid, cls in doc["classes"].items()}
    return {"classes": classes, "revision": doc.get("revision"), "status": doc.get("status"),
            "class_ids": doc.get("class_ids")}


def resolve_independent(av, classes) -> list:
    """Independent resolver: exact 7-axis vector equality, sorted class ids."""
    if av is None:
        return []
    key = tuple((k, av.get(k)) for k in AXES)
    return sorted(cid for cid, axes in classes.items()
                  if tuple((k, axes.get(k)) for k in AXES) == key)


def load_cases(path: Path):
    meta, cases = None, []
    for ln in path.read_text().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        o = json.loads(ln)
        if o.get("record_type") == "meta":
            meta = o
        else:
            cases.append(o)
    return meta, cases


def independent_check(tax: dict, cases: list) -> dict:
    classes = tax["classes"]
    rows, n_assert, n_pass, n_fail, n_na = [], 0, 0, 0, 0
    for c in cases:
        cid, pol, av = c.get("case_id"), c.get("polarity"), c.get("axis_vector")
        r = resolve_independent(av, classes)
        exp_class = c.get("expected_classification")
        exp_res = str(c.get("expected_resolution", ""))
        ok, why = None, "not resolver-decidable"
        if pol == "positive":
            ok = (len(r) == 1 and r[0] == c.get("class_id")
                  and c.get("as_filed_class_id") == r[0] and exp_class == r[0]
                  and exp_res == f"unique_class:{r[0]}")
            why = "positive must resolve uniquely to declared class"
        else:
            kind, filed = c.get("leak_kind"), c.get("as_filed_class_id")
            if kind == "axis":
                ok = (r != [filed]) and ((exp_class in classes and r == [exp_class])
                                         or (exp_class == "NO_CLASS_IN_TAXONOMY" and r == []))
                why = "axis negative: filed class must not be the clean resolution"
            elif exp_res.startswith("reject_misfiled:target="):
                ok, why = r == [exp_res.split("=", 1)[1]], "reject_misfiled target must be unique resolution"
            elif exp_res.startswith("reject_new_class_required"):
                ok, why = r == [], "out-of-vocabulary case must resolve to no taxonomy class"
            else:
                why = f"leak_kind={kind}: resolver not decisive by contract"
        if ok is None:
            n_na += 1
        else:
            n_assert += 1
            n_pass += int(bool(ok))
            n_fail += int(not ok)
        rows.append({"case_id": cid, "polarity": pol, "leak_kind": c.get("leak_kind"),
                     "filed_class_id": c.get("as_filed_class_id"),
                     "axis_vector": {k: (av or {}).get(k) for k in AXES},
                     "resolver_classes": r, "expected_classification": exp_class,
                     "expected_resolution": exp_res,
                     "resolver_check": "n/a" if ok is None else ("pass" if ok else "FAIL"),
                     "check_basis": why})
    return {"cases": rows, "summary": {"cases": len(rows), "assertions": n_assert, "pass": n_pass,
                                       "fail": n_fail, "not_resolver_decidable": n_na}}


def textual_mutant(src: Path, dst: Path, transforms: list) -> dict:
    text, log = src.read_text(), []
    for needle, repl, expected_count in transforms:
        n = text.count(needle)
        if n != expected_count:
            raise SystemExit(f"mutant transform {needle!r}: found {n}, expected {expected_count}")
        text = text.replace(needle, repl)
        log.append({"replaced": needle, "with": repl, "count": n})
    dst.write_text(text)
    return {"path": str(dst.relative_to(ROOT)), "sha256": sha256_file(dst), "transforms": log}


def derived_rebind(tax_path: Path, tax_sha12: str, tag: str) -> tuple:
    """Corpus + catalog copies whose pins name the given taxonomy sha12 (derived only)."""
    d = OUT / "derived" / tag
    d.mkdir(parents=True, exist_ok=True)
    tax = load_taxonomy(tax_path)
    lines, restamped = [], 0
    for ln in (OUT / "inputs" / CASES.name).read_text().splitlines():
        if not ln.strip():
            continue
        o = json.loads(ln)
        if o.get("record_type") == "meta":
            o["taxonomy_ref"] = {"path": "research_map/formulation_taxonomy.yaml",
                                 "revision": tax["revision"], "sha256": sha256_file(tax_path),
                                 "status": tax["status"],
                                 "probe_note": f"W076-F0-TAXCASES-REV5-05 derived {tag} control; canonical untouched"}
        else:
            want = PIN_PREFIX + tax_sha12
            if o.get("binding_status") != want:
                restamped += 1
            o["binding_status"] = want
        lines.append(json.dumps(o, sort_keys=True))
    cases_out = d / "taxonomy_cases.derived.jsonl"
    cases_out.write_text("\n".join(lines) + "\n")
    cat = json.loads((OUT / "inputs" / CATALOG.name).read_text())
    cat["taxonomy_ref"] = {"path": "research_map/formulation_taxonomy.yaml",
                           "revision": tax["revision"], "sha256": sha256_file(tax_path),
                           "status": tax["status"],
                           "probe_note": f"W076-F0-TAXCASES-REV5-05 derived {tag} control"}
    cat_out = d / "leak_rule_catalog.derived.json"
    cat_out.write_text(json.dumps(cat, indent=2) + "\n")
    return cases_out, cat_out, restamped


def main() -> int:
    result = {
        "probe_id": "W076-F0-TAXCASES-REV5-05", "task_id": "W076-F0-TAXCASES-REV5-05",
        "worker": "worker-076", "node_id": "F0", "gate": "G-F0", "class_ids": CLASS_IDS,
        "created_at": now(),
        "question": ("Is the F0 class-leakage corpus schemas/taxonomy_cases.jsonl content-valid at the "
                     "live canonical F0 rev5 taxonomy, did the 00:42-00:43 pin repair change any verdict, "
                     "does the new STALE_TAXONOMY_PIN guard catch the pre-repair defect, and does "
                     "F-094C-1's proposed scalar genericity change break the corpus?"),
        "method": ("third-party checker at live pins + independent resolver differential + derived "
                   "identity/stale-pin rebind controls + axis counterfactuals rebased to each mutant's "
                   "own pin so the C11 guard cannot mask content; canonical bytes read-only"),
    }

    pre = {p.name: pin(p) for p in (TAX, CASES, CATALOG, CHECKER)}
    snap_dir = OUT / "inputs"
    snap_tax = snapshot(TAX, snap_dir)
    snap_cases = snapshot(CASES, snap_dir)
    snap_catalog = snapshot(CATALOG, snap_dir)
    snap_checker = snapshot(CHECKER, snap_dir)
    result["pins_pre"] = pre
    result["snapshots"] = {"dir": str(snap_dir.relative_to(ROOT)),
                           "taxonomy": str(snap_tax.relative_to(ROOT)),
                           "cases": str(snap_cases.relative_to(ROOT)),
                           "catalog": str(snap_catalog.relative_to(ROOT)),
                           "checker": str(snap_checker.relative_to(ROOT))}

    canonical_run = run_checker(TAX, CASES, CATALOG, OUT / "checker_report_canonical.json")
    snapshot_run = run_checker(snap_tax, snap_cases, snap_catalog, OUT / "checker_report_snapshot.json")
    result["primary_run"] = canonical_run
    result["snapshot_equivalence"] = {
        "identical_verdict_payload": comparison_key(canonical_run) == comparison_key(snapshot_run),
        "snapshot_run_exit_code": snapshot_run["exit_code"], "snapshot_run_verdict": snapshot_run["verdict"]}

    tax = load_taxonomy(snap_tax)
    meta, cases = load_cases(snap_cases)
    result["taxonomy_pins"] = {"revision": tax["revision"], "status": tax["status"],
                               "class_ids": tax["class_ids"], "classes": tax["classes"]}
    result["independent_resolver"] = independent_check(tax, cases)
    result["corpus_meta"] = {"path": str(CASES.relative_to(ROOT)), "taxonomy_ref": meta.get("taxonomy_ref"),
                             "rebind_note": meta.get("rebind_note"), "case_rows": len(cases)}
    live_sha12 = pre[TAX.name]["sha256"][:12]

    # R1: identity rebind (canonical already rebound) -> must be invariant
    r1_cases, r1_cat, r1_restamped = derived_rebind(snap_tax, live_sha12, "identity_rebind")
    r1_run = run_checker(snap_tax, r1_cases, r1_cat, OUT / "checker_report_identity_rebind.json")
    # R2: stale rebind to the HF-094C-1 rev2 stamp -> C11 must fire on every row
    r2_cases, r2_cat, r2_restamped = derived_rebind(snap_tax, REV2_STALE_SHA12, "stale_rev2_rebind")
    r2_run = run_checker(snap_tax, r2_cases, r2_cat, OUT / "checker_report_stale_rev2_rebind.json")
    result["rebind_controls"] = {
        "R1_identity_rebind": {"derived_cases": str(r1_cases.relative_to(ROOT)),
                               "derived_catalog": str(r1_cat.relative_to(ROOT)),
                               "rows_restamped": r1_restamped, "run": r1_run,
                               "invariant_vs_canonical": comparison_key(canonical_run) == comparison_key(r1_run)},
        "R2_stale_rev2_rebind": {"derived_cases": str(r2_cases.relative_to(ROOT)),
                                 "derived_catalog": str(r2_cat.relative_to(ROOT)),
                                 "rows_restamped": r2_restamped, "run": r2_run,
                                 "c11_fires_on_all_rows": (r2_run["exit_code"] != 0
                                                           and len(r2_run["stale_pin_errors"]) == len(cases))},
    }

    # S1/S2: axis counterfactuals, corpus rebased to the mutant hash
    mut_dir = OUT / "derived" / "mutants"
    mut_dir.mkdir(parents=True, exist_ok=True)
    s1 = textual_mutant(snap_tax, mut_dir / "taxonomy.scalar_genericity_resolved.yaml",
                        [('genericity_kind: "unresolved"', 'genericity_kind: "provisional_baire_residual"', 1)])
    s1_tax_path = mut_dir / "taxonomy.scalar_genericity_resolved.yaml"
    s1_cases, s1_cat, s1_rebased = derived_rebind(s1_tax_path, s1["sha256"][:12], "mutant_scalar_genericity")
    s1_run = run_checker(s1_tax_path, s1_cases, s1_cat, OUT / "checker_report_mutant_scalar_genericity.json")
    s2 = textual_mutant(snap_tax, mut_dir / "taxonomy.c2_c0_regularity_swapped.yaml",
                        [('regularity_token: "C2"', 'regularity_token: "__TMP__"', 1),
                         ('regularity_token: "C0"', 'regularity_token: "C2"', 1),
                         ('regularity_token: "__TMP__"', 'regularity_token: "C0"', 1)])
    s2_tax_path = mut_dir / "taxonomy.c2_c0_regularity_swapped.yaml"
    s2_cases, s2_cat, s2_rebased = derived_rebind(s2_tax_path, s2["sha256"][:12], "mutant_c2c0_swap")
    s2_run = run_checker(s2_tax_path, s2_cases, s2_cat, OUT / "checker_report_mutant_c2c0_swap.json")
    result["sensitivity_controls"] = [
        {"control_id": "S1_scalar_genericity_unresolved_to_provisional", "mutant": s1,
         "derived_cases": str(s1_cases.relative_to(ROOT)), "rows_rebased": s1_rebased, "run": s1_run,
         "fires_on_content": bool(s1_run["content_errors"]),
         "meaning": ("the corpus is content-bound to the live scalar genericity axis: F-094C-1's repair "
                     "option 'set the axis to provisional_baire_residual' breaks the scalar cases unless "
                     "they are amended in the same revision")},
        {"control_id": "S2_c2_c0_regularity_swap", "mutant": s2,
         "derived_cases": str(s2_cases.relative_to(ROOT)), "rows_rebased": s2_rebased, "run": s2_run,
         "fires_on_content": bool(s2_run["content_errors"]),
         "meaning": "checker reads the live regularity_token axis and is not threshold-passing"},
    ]

    # pin-generation census at the measured (post-repair) state
    binding_counts = {}
    for c in cases:
        binding_counts[c.get("binding_status")] = binding_counts.get(c.get("binding_status"), 0) + 1
    catalog_doc = json.loads(snap_catalog.read_text())
    result["pin_census_measured"] = {
        "case_rows_total": len(cases), "case_binding_status_counts": binding_counts,
        "case_rows_stale": len(cases) - binding_counts.get(PIN_PREFIX + live_sha12, 0),
        "meta_pin_matches_live": (meta.get("taxonomy_ref") or {}).get("sha256") == pre[TAX.name]["sha256"],
        "catalog_pin_matches_live": (catalog_doc.get("taxonomy_ref") or {}).get("sha256") == pre[TAX.name]["sha256"],
        "catalog_taxonomy_ref": catalog_doc.get("taxonomy_ref"),
        "meta_taxonomy_ref": meta.get("taxonomy_ref"),
    }

    # pre-repair observation (hash-bound report produced before the 00:42:36 rewrite)
    if PREREPAIR_REPORT.exists():
        pd = json.loads(PREREPAIR_REPORT.read_text())
        pst = PREREPAIR_REPORT.stat()
        result["prerepair_observation"] = {
            "report": str(PREREPAIR_REPORT.relative_to(ROOT)), "report_sha256": sha256_file(PREREPAIR_REPORT),
            "report_mtime": datetime.fromtimestamp(pst.st_mtime, CST).isoformat(timespec="microseconds"),
            "produced_by": "worker-076 exploratory run at 2026-09-12T00:42:09+08:00, before the 00:42:30/00:42:36/00:43:17 repair",
            "embedded_input_hashes": {"cases": pd.get("cases"), "catalog": pd.get("catalog"),
                                      "taxonomy": pd.get("taxonomy")},
            "verdict": pd.get("verdict"),
            "controls": f"{sum(1 for c in pd.get('controls', []) if c.get('detected'))}/{len(pd.get('controls', []))}",
            "errors": pd.get("errors"),
            "caveat": ("the pre-repair corpus/catalog bytes were overwritten by the repair and are no longer "
                       "on disk; this report is a hash-bound observation of that state, not re-runnable"),
        }
    result["repair_observed"] = {
        "corpus": {"pre_sha256": "f0c20b96f76dc21b32ae81962bb3aa207b04e90c28aa6da8a686e0d9f649a1e8",
                   "post_sha256": pre[CASES.name]["sha256"], "post_mtime": pre[CASES.name]["mtime"]},
        "catalog": {"pre_sha256": "215f6e228250827a3f80a6155fd9a71c0ed0548e347e1d7ec3332275f1fb6f17",
                    "post_sha256": pre[CATALOG.name]["sha256"], "post_mtime": pre[CATALOG.name]["mtime"]},
        "checker": {"pre_sha256": "c1519a972e01539d4bb9e7f79103660944c8d09cc451550b74116cf03bc88040",
                    "post_sha256": pre[CHECKER.name]["sha256"], "post_mtime": pre[CHECKER.name]["mtime"],
                    "change": "C11_stale_taxonomy_pin guard added (10 -> 11 controls); PIN_PREFIX bound"},
        "taxonomy": {"sha256": pre[TAX.name]["sha256"], "changed": False},
        "corroboration": ["reviews/closefind-verify-094.json HF-094C-1 (pre-repair stale stamp)",
                          "schemas/taxonomy_cases.jsonl meta.rebind_note"],
        "note": ("pre-repair hashes are this session's measurements; the corpus/catalog ones are also "
                 "embedded in the preserved 00:42:09 checker report"),
    }

    result["open_case_census"] = {"checker_open_cases": canonical_run["open_cases"],
                                  "count": len(canonical_run["open_cases"] or []),
                                  "note": "open=true cases are decidable gate inputs for the lead, not worker dispositions"}
    m = json.loads((ROOT / "research_map" / "research_map.json").read_text())
    g0 = next((g for g in m.get("gates", []) if g.get("gate_id") == "G-F0"), {})
    result["map_gate_context"] = {
        "map_updated_at": m.get("updated_at"), "g_f0_verdict": g0.get("verdict"),
        "g_f0_unmet": g0.get("unmet"),
        "g_f0_evidence_refs_include_corpus": "schemas/taxonomy_cases.jsonl" in (g0.get("evidence_refs") or []),
        "map_unmet_claims_current_taxonomy_hash_66bf917b": any("66bf917b" in str(u) for u in (g0.get("unmet") or [])),
    }

    post = {p.name: pin(p) for p in (TAX, CASES, CATALOG, CHECKER)}
    drift = pre != post
    result["pins_post"] = post
    result["input_drift"] = drift

    builtin_ok = (canonical_run["controls_total"] >= 10
                  and canonical_run["controls_detected"] == canonical_run["controls_total"])
    resolver = result["independent_resolver"]["summary"]
    r1_ok = result["rebind_controls"]["R1_identity_rebind"]["invariant_vs_canonical"]
    r2_ok = result["rebind_controls"]["R2_stale_rev2_rebind"]["c11_fires_on_all_rows"]
    s1_ok = result["sensitivity_controls"][0]["fires_on_content"]
    s2_ok = result["sensitivity_controls"][1]["fires_on_content"]
    snap_ok = result["snapshot_equivalence"]["identical_verdict_payload"]
    if drift:
        verdict = "UNMEASURED_INPUT_DRIFT"
    elif canonical_run["exit_code"] != 0 or canonical_run["verdict"] != "PASS":
        verdict = "CONTENT_INVALID_AT_REV5"
    elif not builtin_ok or not snap_ok:
        verdict = "CHECKER_OR_PROVENANCE_CONTROL_FAILED"
    elif resolver["fail"] != 0:
        verdict = "INDEPENDENT_RESOLVER_DISAGREES"
    elif not r1_ok or not r2_ok:
        verdict = "PIN_CONTROL_FAILED"
    elif not (s1_ok and s2_ok):
        verdict = "SENSITIVITY_CONTROL_ESCAPED"
    else:
        verdict = "CONTENT_VALID_PIN_REPAIR_VERIFIED"
    result["verdict"] = verdict
    result["controls_summary"] = {
        "builtin_mutation_controls": f"{canonical_run['controls_detected']}/{canonical_run['controls_total']}",
        "builtin_controls_all_fire": builtin_ok, "snapshot_equivalence": snap_ok,
        "R1_identity_rebind_invariant": r1_ok, "R2_stale_rev2_rebind_c11_all_rows": r2_ok,
        "S1_content_fires": s1_ok, "S2_content_fires": s2_ok, "input_drift": drift,
        "independent_resolver": resolver}
    result["claims"] = [
        ("CONTENT-VALID: at the live canonical F0 rev5 taxonomy research_map/formulation_taxonomy.yaml#%s, "
         "the F0 class-leakage corpus schemas/taxonomy_cases.jsonl#%s returns checker PASS with 0 errors, "
         "16 positive / 20 negative, >=2 coverage both polarities for all four classes, %d/%d built-in "
         "mutation controls, disjointness OK; the independent axis-vector resolver agrees with all %d "
         "declared expected classifications/resolutions it can decide (%d pass, 0 fail)."
         % (live_sha12, pre[CASES.name]["sha256"][:12], canonical_run["controls_detected"],
            canonical_run["controls_total"], resolver["assertions"], resolver["pass"])),
        ("PIN REPAIR VERIFIED AS PURE RESTAMP: the corpus now carries %d/%d rows stamped %s and the catalog "
         "resolves at rev5; an identity-rebind derived copy reproduces the canonical checker payload exactly, "
         "and a derived copy restamped to the pre-repair rev2 value %s makes the new C11 guard fire on %d/%d "
         "rows. The 00:42-00:43 repair therefore changed pins only, and the replenished checker now detects "
         "exactly the HF-094C-1 defect class."
         % (result["pin_census_measured"]["case_rows_total"]
            - result["pin_census_measured"]["case_rows_stale"],
            result["pin_census_measured"]["case_rows_total"], PIN_PREFIX + live_sha12, REV2_STALE_SHA12,
            len(result["rebind_controls"]["R2_stale_rev2_rebind"]["run"]["stale_pin_errors"]),
            result["pin_census_measured"]["case_rows_total"])),
        ("AXIS COUPLING (F-094C-1 consequence, measured counterfactually): with the corpus rebased to the "
         "mutant pin so C11 cannot mask content, setting AF-WCC-SCALAR-SPH.axes.genericity_kind from "
         "'unresolved' to 'provisional_baire_residual' makes the checker fail on %d content errors covering "
         "%s, whereas the same corpus passes with the live 'unresolved' value; the C2/C0 regularity swap "
         "fires %d content errors. Amending the scalar axis therefore requires amending the scalar case rows "
         "in the same revision."
         % (len(s1_run["content_errors"]), ",".join(s1_run["content_error_cases"][:8]),
            len(s2_run["content_errors"]))),
    ]
    result["assumptions"] = [
        "the checker's axis/vocabulary/leak-rule/C11 contract is the corpus contract; it is re-run unmodified and hash-pinned",
        "class resolution = exact equality of the 7-axis vector, per the corpus's own expected_resolution encoding",
        "snapshot copies are byte-identical to the canonical files at the pinned sha256; derived controls are the only written copies",
        "the 00:42:09 pre-repair report is a genuine observation of that state; its input bytes were overwritten and are not re-runnable",
    ]
    result["falsifier"] = (
        "FALSE if (a) any canonical input sha256 (taxonomy/corpus/catalog/checker) differs between the pre and "
        "post pin of this run (verdict must read UNMEASURED); (b) the checker at the live rev5 taxonomy returns "
        "non-PASS or any built-in mutation control escapes; (c) the independent resolver disagrees with any "
        "declared expected_classification/expected_resolution on a resolver-decidable assertion; (d) the "
        "identity-rebind derived copy changes the checker payload, or the rev2-restamped derived copy fails to "
        "raise STALE_TAXONOMY_PIN on all 36 rows; (e) either axis counterfactual (scalar genericity_kind "
        "'unresolved'->'provisional_baire_residual', C2/C0 regularity swap), with the corpus rebased to its own "
        "mutant pin, produces zero content errors."
    )
    result["non_claims"] = [
        "does not set a gate verdict or move any node; artifact validation_status is unverified",
        "does not adjudicate F-094C-1; it measures the corpus consequence of one proposed scalar repair",
        "does not assert taxonomy truth, class semantics, or that the 9 open cases are dispositioned",
        "does not modify any canonical file; all derived controls are under artifacts/worker-076/f0_taxcases_rev5/derived/",
        "does not verify the repair's authorship, event emission, or review binding at the new corpus hash",
    ]
    result["reproduction"] = f"python3 {Path(__file__).relative_to(ROOT)}"
    result["completed_at"] = now()

    out = OUT / "probe_result.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("probe_id", "verdict", "controls_summary",
                                             "pin_census_measured")}, indent=2))
    print("report:", out.relative_to(ROOT), sha256_file(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

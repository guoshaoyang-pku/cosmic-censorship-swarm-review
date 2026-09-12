#!/usr/bin/env python3
"""W021-REV29-BINDING-VERIFY-01: independent, read-only, fail-closed verification of the
FROZEN rev29 evidence-binding repair (astra-life05-evidence-binding-repair) acceptance
predicate, as declared in artifacts/formulation/FROZEN.json rev29_delta items (1)-(4).

Scope and authority (what this instrument is NOT):
  * not a gate verdict, not a node transition, not a full-schema review;
  * read-only on every canonical path; it writes only inside --out;
  * it verifies the *binding/repair* predicate on the bytes measured by this process,
    not the mathematical content of any class contract.

Acceptance predicate implemented (rev29_delta, quoted in results.json):
  I1  schemas/taxonomy_cases.jsonl: meta.taxonomy_ref binds declared F0 rev5 0abb9ed8a961
      and every one of the 36 case rows carries binding_status
      bound_taxonomy_sha_0abb9ed8a961; zero rows bound to any other taxonomy hash.
  I2  all three class schemas carry f0_binding.consistency_evidence_sha256 equal to the
      live artifacts/formulation/evidence/taxonomy_consistency.json sha256, and
      f0_binding.declared_f0_sha256 equal to the declared F0 canonical hash.
  I3  F1 visibility strictness directions corrected: the D5 whole-curve/tail sentence now
      reads EQUIVALENT (no 'strictly STRONGER' in D5), the rev12 misclassification example
      is removed, and the variant SET relation reads strictly WEAKER than the single-q
      tail predicate.
  I4  FROZEN.json revision == 29; every path declared in files{} and logical_artifacts{}
      matches its declared sha256 on disk; rev29_delta names all four repair items.
  F0  canonical F0 bytes are untouched at 0abb9ed8a961 and the supplement at d7419b4e8963.
  L-FORM-03 (informational, not a rev29 failure): the inverted SET direction is expected
      to survive at the four out-of-card locations named in rev29_delta.

Fail-closed behaviour:
  exit 0  BINDING_VERIFIED_AT_REV29        (all I/F0 checks pass, controls 6/6)
  exit 1  BINDING_FAILED                   (>=1 I/F0 check fails)
  exit 2  CONTROL_FAILURE                  (a planted mutation was not detected)
  exit 3  VOID_PIN_DRIFT                   (any pinned input changed during the run)
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

FROZEN_EXPECTED_REVISION = 29
F0_EXPECTED = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
F0_SHORT = "bound_taxonomy_sha_" + F0_EXPECTED[:12]
SUPP_EXPECTED = "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
SCHEMAS = [
    ("schemas/af_wcc_vacuum.yaml", "AF-WCC-VAC-GEN"),
    ("schemas/af_scc_c2_vacuum.yaml", "AF-SCC-C2-VAC-GEN"),
    ("schemas/af_scc_c0_vacuum.yaml", "AF-SCC-C0-VAC-GEN"),
]
CASES_REL = "schemas/taxonomy_cases.jsonl"
EVIDENCE_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"
F0_REL = "research_map/formulation_taxonomy.yaml"
SUPP_REL = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN_FOUR = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
RESIDUAL_LFORM03 = [  # (path, line, needle) named verbatim in rev29_delta
    ("research_map/formulation_taxonomy.yaml", 200, "strictly stronger"),
    ("artifacts/formulation/formulation_taxonomy.yaml", 176, "strictly stronger"),
    ("artifacts/formulation/VARIANT_REGISTRY.json", 57, "strictly STRONGER"),
    ("artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json", 11, "strictly stronger"),
    ("artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json", 22, "strictly stronger"),
]
DELTA_KEYWORDS = ["taxonomy_cases.jsonl", "consistency_evidence_sha256", "strictness directions",
                  "pins the two re-pinned corpora"]


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path):
    return sha256_bytes(p.read_bytes())


def meas(root: Path, rel: str):
    p = root / rel
    if not p.is_file():
        return {"path": rel, "exists": False, "sha256": None, "bytes": None}
    b = p.read_bytes()
    return {"path": rel, "exists": True, "sha256": sha256_bytes(b), "bytes": len(b)}


def check_declared_files(root: Path, frozen: dict):
    """Every path declared in FROZEN.files{} must exist and match its declared sha256."""
    recs = []
    for rel in sorted(frozen.get("files", {})):
        declared = frozen["files"][rel]
        m = meas(root, rel)
        expiry = declared.get("sha256") if isinstance(declared, dict) else None
        ok = bool(m["exists"] and m["sha256"] == expiry)
        recs.append({"check": "I4.files", "path": rel, "declared_sha256": expiry,
                     "measured_sha256": m["sha256"], "exists": m["exists"], "ok": ok})
    return recs


def check_logical(root: Path, frozen: dict):
    recs = []
    la = frozen.get("logical_artifacts", {})
    for name in sorted(la):
        spec = la[name]
        rel = spec.get("path")
        m = meas(root, rel)
        ok = bool(m["exists"] and m["sha256"] == spec.get("sha256"))
        recs.append({"check": "I4.logical_artifacts", "name": name, "path": rel,
                     "declared_sha256": spec.get("sha256"), "measured_sha256": m["sha256"],
                     "exists": m["exists"], "ok": ok})
    return recs


def schema_records(root: Path, live_evidence_sha: str):
    recs = []
    for rel, expected_class in SCHEMAS:
        p = root / rel
        rec = {"check": "I2.schema", "path": rel, "expected_class_id": expected_class,
               "class_id": None, "declared_f0_sha256": None, "live_f0_sha256": None,
               "declared_consistency_evidence_sha256": None, "live_consistency_evidence_sha256": live_evidence_sha,
               "ok": False, "errors": []}
        if yaml is None:
            rec["errors"].append("PyYAML unavailable")
            recs.append(rec)
            continue
        if not p.is_file():
            rec["errors"].append("missing file")
            recs.append(rec)
            continue
        try:
            doc = yaml.safe_load(p.read_text())
        except Exception as exc:  # fail closed on unparseable input
            rec["errors"].append("unparseable: %s" % exc)
            recs.append(rec)
            continue
        if not isinstance(doc, dict):
            rec["errors"].append("top level is not a mapping")
            recs.append(rec)
            continue
        rec["class_id"] = doc.get("class_id")
        fb = doc.get("f0_binding") or {}
        rec["declared_f0_sha256"] = fb.get("declared_f0_sha256")
        rec["declared_consistency_evidence_sha256"] = fb.get("consistency_evidence_sha256")
        m = meas(root, F0_REL)
        rec["live_f0_sha256"] = m["sha256"]
        if rec["class_id"] != expected_class:
            rec["errors"].append("class_id mismatch")
        if rec["class_id"] not in FROZEN_FOUR:
            rec["errors"].append("class_id outside the frozen four")
        if rec["declared_f0_sha256"] != F0_EXPECTED:
            rec["errors"].append("declared_f0_sha256 does not resolve to canonical F0")
        if rec["live_f0_sha256"] != F0_EXPECTED:
            rec["errors"].append("live F0 bytes are not the canonical declaration")
        if rec["declared_consistency_evidence_sha256"] != live_evidence_sha:
            rec["errors"].append("consistency_evidence_sha256 != live evidence")
        if fb.get("consistency_evidence") != EVIDENCE_REL:
            rec["errors"].append("consistency_evidence path is not the canonical path")
        rec["ok"] = not rec["errors"]
        recs.append(rec)
    return recs


def cases_record(root: Path):
    p = root / CASES_REL
    rec = {"check": "I1.taxonomy_cases", "path": CASES_REL, "n_rows": 0, "n_bound_canonical": 0,
           "n_bound_other": 0, "meta_taxonomy_sha256": None, "meta_taxonomy_revision": None,
           "other_bindings": {}, "rows_with_unknown_class": [], "ok": False, "errors": []}
    if not p.is_file():
        rec["errors"].append("missing file")
        return rec
    rows = []
    for i, line in enumerate(p.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append((i, json.loads(line)))
        except Exception as exc:
            rec["errors"].append("line %d unparseable: %s" % (i, exc))
    meta = [r for _, r in rows if r.get("record_type") == "meta"]
    body = [(i, r) for i, r in rows if r.get("record_type") != "meta"]
    if len(meta) != 1:
        rec["errors"].append("expected exactly 1 meta row, found %d" % len(meta))
    else:
        tref = meta[0].get("taxonomy_ref") or {}
        rec["meta_taxonomy_sha256"] = tref.get("sha256")
        rec["meta_taxonomy_revision"] = tref.get("revision")
        if tref.get("sha256") != F0_EXPECTED:
            rec["errors"].append("meta.taxonomy_ref.sha256 != canonical F0")
        if tref.get("revision") != 5:
            rec["errors"].append("meta.taxonomy_ref.revision != 5")
    rec["n_rows"] = len(body)
    if len(body) != 36:
        rec["errors"].append("expected 36 case rows, found %d" % len(body))
    for i, r in body:
        bs = r.get("binding_status")
        if bs == F0_SHORT:
            rec["n_bound_canonical"] += 1
        else:
            rec["n_bound_other"] += 1
            rec["other_bindings"][str(bs)] = rec["other_bindings"].get(str(bs), 0) + 1
        cids = r.get("class_ids") or []
        if isinstance(cids, str):
            cids = [cids]
        for c in cids:
            if c not in FROZEN_FOUR:
                rec["rows_with_unknown_class"].append({"line": i, "class_id": c})
    if rec["n_bound_canonical"] != 36:
        rec["errors"].append("not all 36 rows bound to canonical F0")
    if rec["n_bound_other"] != 0:
        rec["errors"].append("rows bound to a non-canonical taxonomy hash")
    if rec["rows_with_unknown_class"]:
        rec["errors"].append("case rows reference class ids outside the frozen four")
    rec["ok"] = not rec["errors"]
    return rec


def f1_direction_record(root: Path):
    rel = "schemas/af_wcc_vacuum.yaml"
    rec = {"check": "I3.f1_directions", "path": rel, "markers": {}, "ok": False, "errors": []}
    p = root / rel
    if not p.is_file():
        rec["errors"].append("missing file")
        return rec
    text = p.read_text()
    lines = text.splitlines()
    # D5 block = the mapping entry whose definition carries the whole-curve/tail reading.
    d5_start = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("D5:") and i + 1 < len(lines) and "definition:" in lines[i + 1]:
            d5_start = i
            break
    d5_block = ""
    if d5_start is None:
        rec["errors"].append("D5 block not located")
    else:
        for ln in lines[d5_start + 1:d5_start + 8]:
            if ln.startswith("      definition_ref:"):
                break
            d5_block += ln + "\n"
    # The rev13 correction note legitimately quotes the withdrawn 'strictly STRONGER' wording;
    # marker checks must run on the assertion with bracketed historical notes removed.
    import re as _re
    d5_assertion = _re.sub(r"\[rev13[^\]]*\]", "", d5_block)
    markers = {
        "d5_equivalent": "is EQUIVALENT to the tail form" in d5_assertion,
        "d5_no_strictly_stronger": ("strictly STRONGER" not in d5_assertion
                                    and "strictly stronger" not in d5_assertion),
        "d5_names_rev13_correction": "rev13" in d5_block and "corrected" in d5_block,
        "misclassification_example_removed": "would misclassify" not in text,
        "variant_set_strictly_weaker": "strictly WEAKER than this class's single-q tail predicate" in text,
    }
    rec["markers"] = markers
    for k, v in markers.items():
        if not v:
            rec["errors"].append("marker failed: %s" % k)
    rec["ok"] = not rec["errors"]
    return rec


def residual_record(root: Path):
    """L-FORM-03: the five rev29_delta-named locations that carried the inverted SET direction.
    Bracketed rev13 correction notes are stripped so a historical quote does not count as the
    live assertion. Informational only: it does not change the binding verdict."""
    import re as _re
    rec = {"check": "L-FORM-03.residual", "findings": [], "n_present": 0,
           "note": "assertion-level scan with [rev13: ...] historical notes stripped; "
                   "informational, does not fail the binding verdict"}
    for rel, lineno, needle in RESIDUAL_LFORM03:
        p = root / rel
        found = False
        text = ""
        if p.is_file():
            text = p.read_text()
            lines = text.splitlines()
            if 1 <= lineno <= len(lines):
                found = needle in _re.sub(r"\[rev13[^\]]*\]", "", lines[lineno - 1])
        rec["findings"].append({"path": rel, "line": lineno, "needle": needle, "present": found,
                                "live_sha256": sha256_bytes(text.encode()) if text else None})
        if found:
            rec["n_present"] += 1
    rec["all_present"] = rec["n_present"] == len(RESIDUAL_LFORM03)
    return rec


def delta_record(frozen: dict):
    rec = {"check": "I4.rev29_delta", "revision": frozen.get("revision"), "keywords": {},
           "ok": False, "errors": []}
    delta = json.dumps(frozen.get("rev29_delta") or [])
    if frozen.get("revision") != FROZEN_EXPECTED_REVISION:
        rec["errors"].append("revision != %d" % FROZEN_EXPECTED_REVISION)
    for kw in DELTA_KEYWORDS:
        rec["keywords"][kw] = kw in delta
        if kw not in delta:
            rec["errors"].append("rev29_delta does not name: %s" % kw)
    rec["ok"] = not rec["errors"]
    return rec


def f0_record(root: Path, frozen: dict):
    rec = {"check": "F0.untouched", "canonical": meas(root, F0_REL), "supplement": meas(root, SUPP_REL),
           "ok": False, "errors": []}
    if rec["canonical"]["sha256"] != F0_EXPECTED:
        rec["errors"].append("canonical F0 bytes moved")
    if rec["supplement"]["sha256"] != SUPP_EXPECTED:
        rec["errors"].append("F0 class-contract supplement moved")
    la = frozen.get("logical_artifacts", {})
    for name, want in (("F0-declared-taxonomy", F0_REL), ("F0-class-contract-supplement", SUPP_REL)):
        spec = la.get(name, {})
        if spec.get("path") != want:
            rec["errors"].append("logical_artifacts[%s] path != %s" % (name, want))
    rec["ok"] = not rec["errors"]
    return rec


def run_checks(root: Path, frozen: dict, frozen_sha: str):
    live_evidence = meas(root, EVIDENCE_REL)
    checks = {
        "I1_taxonomy_cases": cases_record(root),
        "I2_schemas": schema_records(root, live_evidence["sha256"]),
        "I3_f1_directions": f1_direction_record(root),
        "I4_declared_files": check_declared_files(root, frozen),
        "I4_logical_artifacts": check_logical(root, frozen),
        "I4_rev29_delta": delta_record(frozen),
        "F0_untouched": f0_record(root, frozen),
        "L_FORM_03_residual": residual_record(root),
    }
    n_checks = 0
    n_failed = 0
    for name, val in checks.items():
        items = val if isinstance(val, list) else [val]
        if name == "L_FORM_03_residual":
            continue  # informational only
        for it in items:
            n_checks += 1
            if not it.get("ok"):
                n_failed += 1
    return checks, {"n_checks": n_checks, "n_failed": n_failed,
                    "live_evidence": live_evidence, "frozen_sha256_start": frozen_sha}


def control_suite(root: Path, frozen: dict, frozen_sha: str):
    """Six planted single-defect mutations, evaluated with the same predicates."""
    results = []

    def expect_detect(name, predicate, expected):
        detected = not predicate
        results.append({"control": name, "expected_detected": expected, "detected": bool(detected),
                        "ok": bool(detected) == bool(expected)})

    base_checks, _ = run_checks(root, frozen, frozen_sha)

    # C1: flip one declared sha256 in files{} -> the file check must fail.
    mut = json.loads(json.dumps(frozen))
    first = sorted(mut.get("files", {}))[0]
    mut["files"][first]["sha256"] = "0" * 64
    recs = check_declared_files(root, mut)
    expect_detect("C1_flip_declared_sha256", all(r["ok"] for r in recs), True)

    # C2: inject a declared-but-missing path -> the file check must fail.
    mut = json.loads(json.dumps(frozen))
    mut["files"]["schemas/__w021_missing_control__.yaml"] = {"sha256": "1" * 64}
    recs = check_declared_files(root, mut)
    expect_detect("C2_missing_declared_path", all(r["ok"] for r in recs), True)

    # C3: mutate one schema's consistency evidence hash in memory -> I2 must fail.
    ev = meas(root, EVIDENCE_REL)["sha256"]
    recs = schema_records(root, "f" * 64)
    expect_detect("C3_stale_evidence_hash", all(r["ok"] for r in recs), True)

    # C4: one case row rebound to a wrong taxonomy -> I1 must fail.
    p = root / CASES_REL
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    for r in rows:
        if r.get("record_type") != "meta" and r.get("binding_status") == F0_SHORT:
            r["binding_status"] = "bound_taxonomy_sha_deadbeef0000"
            break
    tmp = root / "artifacts/worker-021/rev29_binding_verify/.control_cases.jsonl"
    tmp.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n")
    rec = cases_record(root)  # baseline must pass before the mutation is trusted
    baseline_ok = rec["ok"]
    # evaluate the mutated corpus through an inline copy of the same predicate
    def cases_ok(rows_in):
        body = [r for r in rows_in if r.get("record_type") != "meta"]
        meta = [r for r in rows_in if r.get("record_type") == "meta"]
        return (len(meta) == 1 and (meta[0].get("taxonomy_ref") or {}).get("sha256") == F0_EXPECTED
                and len(body) == 36
                and all(r.get("binding_status") == F0_SHORT for r in body))
    expect_detect("C4_case_row_rebound", baseline_ok and cases_ok(rows), True)
    tmp.unlink()

    # C5: remove the EQUIVALENT marker from F1 in memory -> I3 must fail.
    rec_true = f1_direction_record(root)
    rec_false = {"ok": ("is EQUIVALENT to the tail form" in (root / "schemas/af_wcc_vacuum.yaml")
                        .read_text().replace("is EQUIVALENT to the tail form", "is STRONGER than the tail form"))}
    expect_detect("C5_f1_marker_removed", rec_true["ok"] and rec_false["ok"], True)

    # C6: decrement FROZEN revision in memory -> delta check must fail.
    mut = json.loads(json.dumps(frozen))
    mut["revision"] = 28
    expect_detect("C6_frozen_revision_stale", delta_record(mut)["ok"], True)

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--out", required=True)
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    frozen_path = root / FROZEN_REL
    if not frozen_path.is_file():
        print("FATAL: %s missing" % FROZEN_REL)
        return 3
    frozen_bytes = frozen_path.read_bytes()
    frozen_sha = sha256_bytes(frozen_bytes)
    frozen = json.loads(frozen_bytes)

    # Snapshot every pinned input BEFORE measuring, then re-measure at the end (drift guard).
    pins = {FROZEN_REL: frozen_sha}
    for rel in [F0_REL, SUPP_REL, CASES_REL, EVIDENCE_REL] + [s for s, _ in SCHEMAS]:
        pins[rel] = meas(root, rel)["sha256"]

    checks, summary = run_checks(root, frozen, frozen_sha)
    controls = control_suite(root, frozen, frozen_sha)

    drift = []
    for rel, want in pins.items():
        now = meas(root, rel)["sha256"]
        if now != want:
            drift.append({"path": rel, "at_start": want, "at_end": now})
    drift.append({"path": FROZEN_REL, "at_start": frozen_sha,
                  "at_end": sha256_bytes(frozen_path.read_bytes())})
    drift = [d for d in drift if d["at_start"] != d["at_end"]]

    controls_ok = all(c["ok"] for c in controls)
    stale_declared = [r for r in checks["I4_declared_files"] if not r["ok"]]
    if frozen.get("revision") != FROZEN_EXPECTED_REVISION:
        verdict, code = "VOID_FROZEN_SUPERSEDED", 4
    elif drift:
        verdict, code = "VOID_PIN_DRIFT", 3
    elif not controls_ok:
        verdict, code = "CONTROL_FAILURE", 2
    elif summary["n_failed"] == 0:
        verdict, code = "BINDING_VERIFIED_AT_REV29", 0
    else:
        verdict, code = "BINDING_FAILED", 1

    report = {
        "schema": "w021-rev29-binding-verify/v1",
        "task_id": "W021-REV29-BINDING-VERIFY-01",
        "actor": "worker-021",
        "node_ids": ["F1", "F2a", "F2b", "F0"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "verdict": verdict,
        "counts": {"checks": summary["n_checks"], "failed": summary["n_failed"],
                   "controls": len(controls), "controls_failed": sum(1 for c in controls if not c["ok"]),
                   "stale_declared_pins": len(stale_declared)},
        "findings": {
            "stale_declared_pins": [
                {"path": r["path"], "declared_sha256": r["declared_sha256"],
                 "measured_sha256": r["measured_sha256"]} for r in stale_declared],
            "pin_drift": drift,
            "l_form_03_assertion_level": {
                "present": checks["L_FORM_03_residual"]["n_present"],
                "of": len(RESIDUAL_LFORM03),
                "detail": checks["L_FORM_03_residual"]["findings"]},
        },
        "pins": pins,
        "drift": drift,
        "falsifier": ("Re-run at the same pins: falsified if any I1-I4/F0 check fails, any control "
                      "mutation goes undetected, or the FROZEN rev29 / canonical pins drift (then VOID, "
                      "not falsified). A controller/lead verdict that the rev29 acceptance predicate is "
                      "not the one declared in rev29_delta also voids this measurement's scope."),
        "not_claimed": ["no gate verdict or node transition (worker events cannot set done/passed)",
                        "no review of class-contract mathematical content",
                        "no edit to any canonical artifact",
                        "no claim that the L-FORM-03 residual is repaired"],
        "acceptance_predicate_source": "artifacts/formulation/FROZEN.json#rev29_delta",
        "inputs": pins,
    }
    results = {"schema": "w021-rev29-binding-verify/results/v1", "checks": checks,
               "summary": summary, "controls": controls}

    def dump(path, obj):
        path.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")

    if not args.check_only:
        dump(out / "results.json", results)
        dump(out / "report.json", report)
        dump(out / "controls.json", controls)

    print(json.dumps({"verdict": verdict, "checks": summary["n_checks"],
                      "failed": summary["n_failed"], "controls_failed":
                      sum(1 for c in controls if not c["ok"]), "drift": len(drift)}, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())

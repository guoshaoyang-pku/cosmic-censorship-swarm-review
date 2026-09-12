#!/usr/bin/env python3
"""W086-F2A-HF091-COVERAGE-01.

Independent, read-only, hash-pinned measurement of
  (A) whether the three F2a/F2b extension-predicate convention axes raised by
      HF-091-02 (worker-091, 2026-09-12T01:03:40+08:00) are asymmetric at the
      live rev13 / FROZEN-rev29 bytes, and
  (B) whether the two live-hash F2a accepts (worker-017, worker-072) and the
      frozen structural gate actually cover those axes.

Authority: worker measurement only. No canonical write, no node status, no
validation_status=passed, no gate verdict. Read paths only; mutants are written
under this artifact's sandbox/ directory.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SANDBOX = HERE / "sandbox"
TASK_ID = "W086-F2A-HF091-COVERAGE-01"
WORKER = "worker-086"
NODE = "F2a"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
GATE = "G-FORM"
GATE_TOOL = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"

F2A = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
F2B = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
F1 = ROOT / "schemas" / "af_wcc_vacuum.yaml"

PIN_PATHS = [
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_wcc_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/rule_spec.json",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/tools/check_class_schema.py",
    "reviews/F2a-review-worker-017.json",
    "reviews/F2a-review-worker-072-rev13.json",
    "artifacts/worker-017/f2a_review/check_f2a.py",
    "artifacts/worker-072/f2a_review/check_f2a.py",
]

ACCEPT_SCRIPTS = {
    "worker-017": "artifacts/worker-017/f2a_review/check_f2a.py",
    "worker-072": "artifacts/worker-072/f2a_review/check_f2a.py",
}
ACCEPT_VERDICTS = {
    "worker-017": "reviews/F2a-review-worker-017.json",
    "worker-072": "reviews/F2a-review-worker-072-rev13.json",
}

AXIS_KEYWORDS = {
    "A1_manifold_category": ["manifold category", "SMOOTH (C-infinity)", "smooth 4-manifold",
                             "topological 4-manifold", "merely topological"],
    "A2_iota_regularity": ["iota_regularity", "C-infinity isometric embedding",
                           "embedding iota", "regularity of the embedding"],
    "A3_f_interior": ["int(M", "interior requirement", "int(M'", "interior future point"],
}
ASSERT_TOKENS = ("add(", "assert", "==", "!=", "ok =", "ok=", "raise ")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_yaml(p):
    return yaml.safe_load(Path(p).read_text())


def clauses(definition: str) -> dict:
    """Clause text keyed by letter; the FIRST occurrence of a marker wins.

    First-wins matters: F2b's own clause (f) contains the parenthetical
    "clause (f) was escapable", which a last-wins scan would mistake for the
    marker (this was the pass-1 instrument bug).
    """
    marks = [(m.group(1), m.start()) for m in re.finditer(r"\(([a-f])\)", definition)]
    out = {}
    for i, (letter, pos) in enumerate(marks):
        if letter in out:
            continue
        end = len(definition)
        for letter2, pos2 in marks[i + 1:]:
            if letter2 not in out and pos2 > pos:
                end = pos2
                break
        out[letter] = definition[pos:end].strip()
    return out


def find_key(obj, key):
    """Return the dotted path of the first nested occurrence of key, else None."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                return k
            got = find_key(v, key)
            if got:
                return k + "." + got
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            got = find_key(v, key)
            if got:
                return f"[{i}]." + got
    return None


def axis_measurement(doc: dict) -> dict:
    ext = doc.get("extension_predicate") or {}
    top = doc.get("topology") or {}
    definition = str(ext.get("definition") or "")
    cl = clauses(definition)
    c_text = cl.get("c", "")
    f_text = cl.get("f", "")
    ext_top = str(top.get("extension_topology") or "")
    manifold_tokens = re.compile(r"SMOOTH|C-infinity|C\^?∞|\bsmooth\b", re.I)
    manifold_present = bool(manifold_tokens.search(c_text) or manifold_tokens.search(ext_top))
    iota_key_path = find_key(doc, "iota_regularity")
    iota_field_present = iota_key_path is not None
    iota_phrase_present = bool(re.search(r"C-infinity isometric embedding|C\^?∞ isometric embedding",
                                         definition + " " + str(doc.get("falsifier") or ""), re.I))
    interior_present = bool(re.search(r"\bint\s*\(", f_text))
    return {
        "class_id": doc.get("class_id"),
        "clause_c": c_text,
        "clause_f": f_text,
        "extension_topology": ext_top,
        "A1_manifold_category_frozen": manifold_present,
        "A2_iota_regularity_field_present": iota_field_present,
        "A2_iota_regularity_key_path": iota_key_path,
        "A2_iota_regularity_phrase_present": iota_phrase_present,
        "A3_f_interior_present": interior_present,
    }


def axis_evidence_lines(path: Path) -> dict:
    """Raw-byte line numbers for the decisive axis tokens."""
    lines = path.read_text().splitlines()
    out = {k: [] for k in AXIS_KEYWORDS}
    for i, ln in enumerate(lines, 1):
        for axis, kws in AXIS_KEYWORDS.items():
            if any(k.lower() in ln.lower() for k in kws):
                out[axis].append({"line": i, "text": ln.strip()[:220]})
    return out


def _axis_hits(path: Path, patterns: list) -> list:
    out = []
    for i, ln in enumerate(path.read_text().splitlines(), 1):
        for p in patterns:
            if re.search(p, ln, re.I):
                out.append({"line": i, "pattern": p, "text": ln.strip()[:220]})
                break
    return out


def external_discharge() -> dict:
    """Do the frozen F0 artifacts fix the three axes for AF-SCC-C2-VAC-GEN?

    Machine fields only record raw hits and whether an 'unresolved' flag is
    present. The judgement 'no hit fixes the convention' is stated in the
    report's conclusion, with the hit lines quoted for review.
    """
    canon_path = ROOT / "research_map" / "formulation_taxonomy.yaml"
    supp_path = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
    canon = yaml.safe_load(canon_path.read_text())
    cclass = json.dumps((canon.get("classes") or {}).get("AF-SCC-C2-VAC-GEN") or {})
    patterns = {
        "A1_manifold_category": [r"topological 4-manifold", r"smooth 4-manifold", r"manifold category",
                                 r"smooth category", r"smooth structure"],
        "A2_iota_regularity": [r"regularity of the embedding", r"embedding versus regularity",
                               r"iota_regularity", r"isometric embedding"],
        "A3_f_interior": [r"\bint\s*\(", r"interior requirement", r"interior future point",
                          r"clause \(f\)"],
    }
    out = {}
    for axis, pats in patterns.items():
        ch = _axis_hits(canon_path, pats)
        sh = _axis_hits(supp_path, pats)
        out[axis] = {
            "class_contract_hits": [p for p in pats if re.search(p, cclass, re.I)],
            "f0_canonical_lines": ch,
            "f0_supplement_lines": sh,
            "explicit_unresolved_flag": any("unresolved" in h["text"].lower() for h in ch + sh),
            "no_fixing_statement_rationale": (
                "no hit asserts a manifold category, an iota differentiability convention, or an interior "
                "requirement for AF-SCC-C2-VAC-GEN; the C2 conclusion's 'isometric embedding' phrase fixes "
                "the conclusion form, not the regularity of iota"
            ),
        }
    return out


def run_gate(path: Path) -> dict:
    r = subprocess.run([sys.executable, str(GATE_TOOL), "--json", str(path)],
                       capture_output=True, text=True)
    try:
        payload = json.loads(r.stdout)
    except ValueError:
        payload = {"verdict": "error", "failed_rules": [], "raw": r.stdout[-300:], "stderr": r.stderr[-300:]}
    payload["exit_code"] = r.returncode
    return payload


def build_mutants(base: dict) -> dict:
    import copy
    out = {}
    m = copy.deepcopy(base)
    m["topology"]["extension_topology"] = "M' is a connected topological 4-manifold containing iota(M) as an open proper subset; M' is NOT assumed globally hyperbolic, compact, or AF"
    out["m1_topological_manifold"] = ("axis_A1", "blind", m)
    m = copy.deepcopy(base)
    m["topology"]["extension_topology"] = "M' is a connected SMOOTH (C-infinity) 4-manifold containing iota(M) as an open proper subset; M' is NOT assumed globally hyperbolic, compact, or AF"
    out["m1b_smooth_manifold_added"] = ("axis_A1", "indifferent", m)
    m = copy.deepcopy(base)
    m["iota_regularity"] = "the embedding iota is merely continuous (C0)"
    out["m2_iota_c0"] = ("axis_A2", "indifferent", m)
    m = copy.deepcopy(base)
    ext = m["extension_predicate"]
    ext["definition"] = ext["definition"].replace(
        "(f) the extension adds points to the future:",
        "(f) the extension adds points to the future: int(M' minus iota(M)) is non-empty AND")
    out["m3_f_interior_added"] = ("axis_A3", "indifferent", m)
    m = copy.deepcopy(base)
    ext = m["extension_predicate"]
    ext["definition"] = re.sub(r"\(f\)[^.]*\.",
                               "(f) the extension adds points to the future in some sense.", ext["definition"])
    out["m3b_f_witness_removed"] = ("axis_A3", "blind_or_marker_only", m)
    m = copy.deepcopy(base)
    m["conclusion"]["conclusion_type"] = "scc_c0_future_inextendibility"
    out["m4_conclusion_c0_control"] = ("control_class_merge", "must_fail", m)
    m = copy.deepcopy(base)
    m["class_id"] = "AF-SCC-C0-VAC-GEN"
    out["m5_classid_sibling_control"] = ("control_class_id", "must_fail", m)
    m = copy.deepcopy(base)
    m["extension_predicate"]["must_not_conflate"] = []
    out["m6_empty_must_not_conflate_blind"] = ("axis_A3_adjacent", "blind_datum", m)
    m = copy.deepcopy(base)
    m["extension_predicate"]["definition"] = m["extension_predicate"]["definition"].replace("(f)", "(g)")
    out["m7_f_marker_renamed_blind"] = ("axis_A3_marker", "blind_datum", m)
    return out


def coverage_of_script(script: Path) -> dict:
    lines = script.read_text().splitlines()
    cov = {}
    for axis, kws in AXIS_KEYWORDS.items():
        hits = []
        for i, ln in enumerate(lines):
            low = ln.lower()
            if any(k.lower() in low for k in kws):
                window = "\n".join(lines[max(0, i - 3): i + 4])
                assertion = any(tok in window for tok in ASSERT_TOKENS)
                hits.append({"line": i + 1, "assertion_context": assertion, "text": ln.strip()[:200]})
        # A covered axis needs at least one hit inside an assertion context.
        cov[axis] = {"hits": hits, "covered": any(h["assertion_context"] for h in hits)}
    return cov


def metric_regularity_covered(script: Path) -> bool:
    """Control K2: the metric-regularity axis IS asserted (072 C10)."""
    txt = script.read_text()
    return bool(re.search(r"frozen_regularity", txt))


def main() -> int:
    SANDBOX.mkdir(parents=True, exist_ok=True)
    pins_before = {p: sha(ROOT / p) for p in PIN_PATHS}

    f2a = load_yaml(F2A)
    f2b = load_yaml(F2B)

    live = {"F2a": axis_measurement(f2a), "F2b": axis_measurement(f2b)}

    # ---- part A: asymmetry at live bytes -----------------------------------
    a_checks = {}
    asym = {}
    for axis, key in [("A1_manifold_category", "A1_manifold_category_frozen"),
                      ("A2_iota_regularity", "A2_iota_regularity_field_present"),
                      ("A3_f_interior", "A3_f_interior_present")]:
        a = bool(live["F2a"][key])
        b = bool(live["F2b"][key])
        asym[axis] = {"f2a": a, "f2b": b, "asymmetric": (b and not a)}
        a_checks[axis] = "CONFIRMED_ASYMMETRIC" if (b and not a) else "NOT_ASYMMETRIC"

    # ---- part B1: frozen gate mutation probe --------------------------------
    nulls = {
        "null_f2a": run_gate(F2A),
        "null_f2b": run_gate(F2B),
        "null_f1": run_gate(F1),
    }
    mutants = build_mutants(f2a)
    gate_probe = {}
    for name, (axis, expectation, doc) in mutants.items():
        p = SANDBOX / f"{name}.yaml"
        p.write_text(yaml.safe_dump(doc, sort_keys=False, width=110))
        res = run_gate(p)
        gate_probe[name] = {"axis": axis, "expectation": expectation,
                            "verdict": res.get("verdict"), "failed_rules": res.get("failed_rules"),
                            "exit_code": res.get("exit_code")}

    # ---- part B2: accept-check coverage -------------------------------------
    accept_cov = {}
    for who, rel in ACCEPT_SCRIPTS.items():
        script = ROOT / rel
        accept_cov[who] = {
            "script": rel,
            "script_sha256": sha(script),
            "axes": coverage_of_script(script),
            "metric_regularity_axis_covered": metric_regularity_covered(script),
        }
    accept_fidelity = {}
    for who, rel in ACCEPT_VERDICTS.items():
        d = json.loads((ROOT / rel).read_text())
        declared = d.get("reviewed_sha256") or d.get("artifact_sha256")
        accept_fidelity[who] = {
            "path": rel, "verdict": d.get("verdict"),
            "declared_sha256": declared, "live_f2a_sha256": pins_before["schemas/af_scc_c2_vacuum.yaml"],
            "hash_valid": declared == pins_before["schemas/af_scc_c2_vacuum.yaml"],
            "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
        }

    discharge = external_discharge()

    result = {
        "schema": "w086-f2a-hf091-coverage/v1",
        "task_id": TASK_ID, "actor": WORKER, "node_id": NODE, "class_id": CLASS_ID, "gate": GATE,
        "authority_note": "worker measurement only; no canonical write, no node status, no gate verdict, no validation_status=passed",
        "pins_before": pins_before,
        "live_axis_measurement": live,
        "part_A_asymmetry": asym, "part_A_checks": a_checks,
        "axis_evidence_lines": {"F2a": axis_evidence_lines(F2A), "F2b": axis_evidence_lines(F2B)},
        "external_discharge_in_f0": discharge,
        "part_B1_gate_nulls": {k: {"verdict": v.get("verdict"), "exit_code": v.get("exit_code")} for k, v in nulls.items()},
        "part_B1_gate_mutants": gate_probe,
        "part_B2_accept_coverage": accept_cov,
        "part_B2_accept_fidelity": accept_fidelity,
    }

    # ---- controls -----------------------------------------------------------
    k1 = all(asym[a]["f2b"] for a in asym)
    k2 = any(v["metric_regularity_axis_covered"] for v in accept_cov.values())
    k_null = all(v.get("verdict") == "pass" for v in nulls.values())
    k_controls_fire = all(gate_probe[m]["verdict"] != "pass"
                          for m in ("m4_conclusion_c0_control", "m5_classid_sibling_control"))
    controls = {"K1_f2b_positive": k1, "K2_covered_axis_control": k2,
                "K3_determinism": None, "K4_pin_stability": None,
                "K5_null_controls_pass": k_null, "K6_positive_controls_fire": k_controls_fire}

    digest = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    result["result_digest_pass1"] = digest

    # second pass for determinism (rebuild the two live axis measurements + coverage only)
    pass2 = {
        "live": {k: axis_measurement(load_yaml(p)) for k, p in (("F2a", F2A), ("F2b", F2B))},
        "coverage": {who: coverage_of_script(ROOT / rel) for who, rel in ACCEPT_SCRIPTS.items()},
    }
    digest2 = hashlib.sha256(json.dumps(pass2, sort_keys=True).encode()).hexdigest()
    controls["K3_determinism"] = digest2 == hashlib.sha256(json.dumps(
        {"live": live, "coverage": {who: v["axes"] for who, v in accept_cov.items()}},
        sort_keys=True).encode()).hexdigest()

    pins_after = {p: sha(ROOT / p) for p in PIN_PATHS}
    controls["K4_pin_stability"] = pins_after == pins_before
    result["controls"] = controls
    result["pins_after"] = pins_after

    # ---- findings / verdict --------------------------------------------------
    h1 = all(v["asymmetric"] for v in asym.values())
    h2 = all(not v["axes"][a]["covered"] for v in accept_cov.values() for a in AXIS_KEYWORDS)
    axis_blind = [m for m in ("m1_topological_manifold", "m1b_smooth_manifold_added", "m2_iota_c0", "m3_f_interior_added")
                  if gate_probe[m]["verdict"] == "pass"]
    h3 = len(axis_blind) == 4
    h4 = all(v["hash_valid"] and v["counts_as_full_schema_verdict"] for v in accept_fidelity.values())
    result["hypotheses"] = {
        "H1_three_axes_asymmetric": h1,
        "H2_accepts_do_not_assert_axes": h2,
        "H3_gate_indifferent_to_axes": h3,
        "H4_accepts_hash_valid_full_schema": h4,
    }
    result["axis_mutants_that_pass_the_frozen_gate"] = axis_blind
    result["blind_data_points"] = {
        m: gate_probe[m] for m in ("m6_empty_must_not_conflate_blind", "m7_f_marker_renamed_blind")
    }
    result["run_history"] = {
        "pass_0_invalid": {
            "at": "2026-09-12T01:14:40+08:00",
            "invalid_controls": ["K1_f2b_positive", "K2_covered_axis_control", "K6_mutant_controls_fire"],
            "cause": ("instrument bugs, hypotheses unchanged: (i) clause extractor was last-wins and captured the "
                      "parenthetical 'clause (f) was escapable' as F2b's (f); (ii) iota_regularity lookup was "
                      "top-level-only while F2b nests it under non_vacuity; (iii) K2 demanded every accept cover the "
                      "metric-regularity axis; (iv) the empty-must_not_conflate mutant is not caught by the frozen "
                      "gate and was wrongly used as a positive control."),
            "fixes": ["first-occurrence-wins clause scan", "recursive iota_regularity key lookup",
                      "K2 is existential", "positive controls replaced by m4 (R11) and m5 (R02/R06/R11/R18/R19/R31)"],
        }
    }
    run_valid = all([controls["K1_f2b_positive"], controls["K2_covered_axis_control"],
                     controls["K3_determinism"], controls["K4_pin_stability"],
                     controls["K5_null_controls_pass"], controls["K6_positive_controls_fire"]])
    result["run_valid"] = run_valid
    result["conclusion"] = (
        "At the live pins the three HF-091-02 convention axes are asymmetric (F2b freezes all three, F2a none). "
        "The two live-hash F2a accepts are hash-valid full-schema verdicts, but their executed check scripts do not "
        "assert any of the three axes, and the frozen structural gate PASSes all four axis mutants (it also passes a "
        "clause-(f)-marker rename and an emptied must_not_conflate). Therefore the accept pair does not settle "
        "HF-091-02: G-FORM cannot close F2a on those accepts unless the axes are ruled immaterial or F2a is "
        "repaired/frozen and re-reviewed at the new hash."
    ) if (run_valid and h1 and h2 and h3 and h4) else "See checks; run_valid=%s." % run_valid
    result["next_falsifier"] = (
        "Re-run after any F2a revision: H1 is refuted by a measured symmetric axis at the new bytes; H2 by an "
        "axis-specific assertion in the accept scripts; H3 by an axis mutant that FAILs the frozen gate; H4 by a "
        "live-hash accept whose declared sha256 differs from the measured file."
    )

    (HERE / "report.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({"run_valid": run_valid, "hypotheses": result["hypotheses"],
                      "controls": controls, "digest": digest[:16]}, indent=1))
    if (HERE / "report.json").exists():
        print("report sha256:", sha(HERE / "report.json")[:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())

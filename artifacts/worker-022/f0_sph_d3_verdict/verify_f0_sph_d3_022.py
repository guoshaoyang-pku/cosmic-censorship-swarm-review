#!/usr/bin/env python3
"""Independent verification of worker-059 finding HF-059-SPH-01 (class AF-WCC-SCALAR-SPH).

Claim under test (at FROZEN rev29 pins): the two FROZEN-pinned F0 logical artifacts store
contradictory D3 discharge-scope records -- A (declared taxonomy) says D3 was discharged for all
four classes including AF-WCC-SCALAR-SPH, while B (class-contract supplement) records D3 class
scope as the three vacuum classes and never mentions the scalar class -- and the canonical
taxonomy-consistency certificate is green anyway.

This script is READ-ONLY on every canonical path. All mutation/execution happens in a private
sandbox under this artifact directory. stdlib + PyYAML only; it does not import the canonical
checker or any other worker's detector.

Exit codes: 0 = CORROBORATED, 1 = REFUTED, 2 = INSTRUMENT_VOID (pin mismatch / control misbehaviour).
"""
import hashlib
import copy
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREREG = json.loads((HERE / "preregistration.json").read_text())
PIN_SPEC = PREREG["pins"]

CST = timezone(timedelta(hours=8))


def now_iso():
    fixed = os.environ.get("F0D3_FIXED_TS")
    if fixed:
        return fixed
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_pins():
    out = {}
    for name, spec in PIN_SPEC.items():
        if name == "research_map":
            continue  # materiality recount only, not a binding pin
        p = ROOT / spec["path"]
        out[name] = {"path": spec["path"], "exists": p.is_file(),
                     "sha256": sha256_file(p) if p.is_file() else None,
                     "declared": spec["sha256"]}
        out[name]["match"] = out[name]["sha256"] == spec["sha256"]
    return out


def load_yaml(path: Path):
    text = path.read_text()
    docs = list(yaml.safe_load_all(text))
    if len(docs) != 1 or not isinstance(docs[0], dict):
        raise ValueError(f"{path}: expected exactly one mapping document")
    return docs[0], text


def strings_in(obj, path="$"):
    """Yield (path, string) for every scalar string in a nested structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings_in(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from strings_in(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def d3_records(A, B):
    """Extract the stored D3 records from both sides. Returns dicts or None."""
    a_rec = None
    for rec in (A.get("class_scope_adjudication", {}) or {}).get("resolved_divergences", []) or []:
        if str(rec.get("id")) == "D3":
            a_rec = rec
    b_rec = None
    for rec in (B.get("contract_divergences", {}) or {}).get("items", []) or []:
        if str(rec.get("id")) == "D3":
            b_rec = rec
    return a_rec, b_rec


def scope_reading(a_rec, b_rec):
    """The detector under test: does A put the scalar class in D3 scope while B does not?"""
    a_res = str((a_rec or {}).get("resolution", "")).lower()
    b_cls = str((b_rec or {}).get("class", "")).lower()
    b_res = str((b_rec or {}).get("resolution", "")).lower()
    a_scalar = ("scalar" in a_res) or ("all four" in a_res) or ("four classes" in a_res)
    b_scalar = ("scalar" in b_cls) or ("scalar" in b_res) or ("four" in b_cls)
    return {"a_scalar_in_scope": bool(a_scalar), "b_scalar_in_scope": bool(b_scalar),
            "conflict": bool(a_scalar and not b_scalar)}


def mutate_text(text: str, old: str, new: str):
    n = text.count(old)
    if n != 1:
        raise ValueError(f"mutation target not unique: {old!r} count={n}")
    return text.replace(old, new)


def parse_mutated(text: str, label: str):
    try:
        doc = yaml.safe_load(text)
        if not isinstance(doc, dict):
            raise ValueError("not a mapping")
        return doc, None
    except Exception as exc:  # fail-closed control M6
        return None, f"{label}: {type(exc).__name__}: {exc}"


def run_sandbox_checker(name: str, text_a: str, text_b: str):
    """Build a throwaway sandbox with the canonical relative layout and run the pinned checker."""
    sb = HERE / "sandbox" / name
    if sb.exists():
        shutil.rmtree(sb)
    (sb / "research_map").mkdir(parents=True)
    (sb / "artifacts" / "formulation" / "tools").mkdir(parents=True)
    (sb / "artifacts" / "formulation" / "evidence").mkdir(parents=True)
    (sb / "research_map" / "formulation_taxonomy.yaml").write_text(text_a)
    (sb / "artifacts" / "formulation" / "formulation_taxonomy.yaml").write_text(text_b)
    shutil.copy2(ROOT / PIN_SPEC["VOCAB_ALIASES"]["path"],
                 sb / "artifacts" / "formulation" / "VOCAB_ALIASES.json")
    shutil.copy2(ROOT / PIN_SPEC["consistency_checker"]["path"],
                 sb / "artifacts" / "formulation" / "tools" / "check_taxonomy_consistency.py")
    proc = subprocess.run(
        [sys.executable, str(sb / "artifacts" / "formulation" / "tools" / "check_taxonomy_consistency.py")],
        cwd=str(sb), capture_output=True, text=True, timeout=120)
    cert_path = sb / "artifacts" / "formulation" / "evidence" / "taxonomy_consistency.json"
    cert = json.loads(cert_path.read_text()) if cert_path.is_file() else None
    return {"exit_code": proc.returncode, "stdout": proc.stdout.strip()[-2000:],
            "stderr": proc.stderr.strip()[-2000:], "certificate": cert}


def main():
    checks = []
    controls = []
    t_start = now_iso()
    pins_start = measure_pins()
    void_reasons = [n for n, v in pins_start.items() if not v["match"]]

    def add(cid, desc, expected, measured, ok):
        checks.append({"id": cid, "desc": desc, "expected": expected,
                       "measured": measured, "pass": bool(ok)})

    A_path = ROOT / PIN_SPEC["A_declared_taxonomy"]["path"]
    B_path = ROOT / PIN_SPEC["B_class_contract_supplement"]["path"]
    FROZEN_path = ROOT / PIN_SPEC["FROZEN_manifest"]["path"]
    CERT_path = ROOT / PIN_SPEC["consistency_certificate"]["path"]
    CHECKER_path = ROOT / PIN_SPEC["consistency_checker"]["path"]

    add("C1", "all live pins equal preregistered sha256 (start/end)",
        "MATCH/MATCH", {n: v["sha256"][:12] if v["sha256"] else None for n, v in pins_start.items()},
        not void_reasons)

    # ---- C2: FROZEN rev29 pins A and B ----
    frozen = json.loads(FROZEN_path.read_text())
    f_files = frozen.get("files", {})
    f_ok = (frozen.get("revision") == 29
            and (f_files.get(PIN_SPEC["A_declared_taxonomy"]["path"], {}) or {}).get("sha256") == PIN_SPEC["A_declared_taxonomy"]["sha256"]
            and (f_files.get(PIN_SPEC["B_class_contract_supplement"]["path"], {}) or {}).get("sha256") == PIN_SPEC["B_class_contract_supplement"]["sha256"])
    add("C2", "FROZEN rev29 files map pins A and B at preregistered hashes", True,
        {"revision": frozen.get("revision"),
         "A_pinned": (f_files.get(PIN_SPEC["A_declared_taxonomy"]["path"], {}) or {}).get("sha256", "")[:12],
         "B_pinned": (f_files.get(PIN_SPEC["B_class_contract_supplement"]["path"], {}) or {}).get("sha256", "")[:12]},
        f_ok)

    A, A_text = load_yaml(A_path)
    B, B_text = load_yaml(B_path)
    a_rec, b_rec = d3_records(A, B)

    a_res = str((a_rec or {}).get("resolution", ""))
    a_status = str((a_rec or {}).get("status", ""))
    a_scalar_named = "AF-WCC-SCALAR-SPH" in a_res
    a_four = bool(re.search(r"all four|four classes", a_res, re.I))
    add("C3", "A stored D3 record names the scalar class and a four-class scope",
        True, {"status": a_status, "scalar_named": a_scalar_named, "four_class_scope": a_four,
               "resolution": a_res[:240]},
        a_status == "resolved" and a_scalar_named and a_four)

    rev_note = str(A.get("revision_note_rev5", ""))
    scalar_concl = str(((A.get("classes", {}).get("AF-WCC-SCALAR-SPH", {}) or {}).get("conclusion", {}) or {}).get("text", ""))
    c4_flag_a = "discharged for the scalar class" in rev_note.lower()
    c4_flag_b = "[rev5: D1/D3 discharge for this class" in scalar_concl
    c4_ok = c4_flag_a and c4_flag_b
    add("C4", "A repeats the scalar D3-discharge statement in revision_note_rev5 and the scalar conclusion annotation",
        True, {"revision_note_scalar_clause": c4_flag_a,
               "scalar_conclusion_annotation": c4_flag_b},
        c4_ok)

    b_cls = str((b_rec or {}).get("class", ""))
    b_res = str((b_rec or {}).get("resolution", ""))
    b_three = b_cls.strip().lower() == "all three vacuum classes"
    add("C5", "B stored D3 record has class scope exactly 'all three vacuum classes'",
        True, {"class": b_cls, "scalar_word_in_class": "scalar" in b_cls.lower()},
        b_three and "scalar" not in b_cls.lower())

    b_scalar_absent = ("scalar" not in b_res.lower()) and not re.search(r"\bfour\b", b_res, re.I)
    add("C6", "B D3 resolution mentions neither the scalar class nor a four-class scope",
        True, {"resolution": b_res[:240], "scalar_absent": "scalar" not in b_res.lower(),
               "four_absent": not bool(re.search(r"\bfour\b", b_res, re.I))},
        b_scalar_absent)

    # C7: whole-document B scan for a scalar-class D3/discharge record elsewhere.
    hits = []
    for sp, s in strings_in(B):
        low = s.lower()
        if "scalar" in low and (re.search(r"\bd3\b", s) or "discharg" in low):
            hits.append({"path": sp, "text": s[:200]})
    add("C7", "no other location in B records a scalar-class D3 discharge", 0,
        {"hits": hits}, len(hits) == 0)

    reading = scope_reading(a_rec, b_rec)
    add("C8", "cross-artifact D3 scope conflict (A scalar-in, B scalar-out, both resolved)",
        "CONTRADICTION",
        {"a_status": a_status, "b_status": str((b_rec or {}).get("status", "")), **reading},
        reading["conflict"] and a_status == "resolved" and str((b_rec or {}).get("status", "")) == "resolved")

    cert = json.loads(CERT_path.read_text())
    cert_green = (cert.get("consistent") is True and not cert.get("errors")
                  and not cert.get("contract_divergences")
                  and "AF-WCC-SCALAR-SPH" in (cert.get("classes_compared") or []))
    add("C9", "canonical certificate is green and lists the scalar class", True,
        {"consistent": cert.get("consistent"), "errors": cert.get("errors"),
         "contract_divergences": cert.get("contract_divergences"),
         "scalar_in_classes_compared": "AF-WCC-SCALAR-SPH" in (cert.get("classes_compared") or [])},
        cert_green)

    # C10: static argument that the checker recomputes divergences instead of reading stored records.
    src = CHECKER_path.read_text()
    rep_idx = src.index("rep = {")
    cd_positions = [m.start() for m in re.finditer("contract_divergences", src)]
    csa_read = "class_scope_adjudication" in src
    cd_before_output = [p for p in cd_positions if p < rep_idx]
    c10_ok = (not csa_read) and (len(cd_before_output) == 0) and ("ctext(" in src) and ("div.append" in src)
    add("C10", "static: checker never reads stored records; divergences recomputed from conclusion texts",
        True, {"class_scope_adjudication_referenced": csa_read,
               "contract_divergences_reads_before_output": len(cd_before_output),
               "ctext_based": "ctext(" in src, "div_append": "div.append" in src},
        c10_ok)

    # ---- C11/C12 dynamic sandbox reproduction and silence control ----
    box_pristine = run_sandbox_checker("pristine", A_text, B_text)
    c11_ok = (box_pristine["exit_code"] == 0 and box_pristine["certificate"] is not None
              and box_pristine["certificate"].get("consistent") is True
              and box_pristine["certificate"].get("contract_divergences") == [])
    add("C11", "dynamic sandbox: pinned checker reproduces exit 0 and a green certificate",
        "CONSISTENT/exit 0",
        {"exit_code": box_pristine["exit_code"], "stdout": box_pristine["stdout"][-200:],
         "consistent": (box_pristine["certificate"] or {}).get("consistent"),
         "contract_divergences": (box_pristine["certificate"] or {}).get("contract_divergences")},
        c11_ok)

    mut_a_rec = mutate_text(
        A_text,
        "confirmed discharged for ALL FOUR classes, including AF-WCC-SCALAR-SPH",
        "confirmed discharged for the three vacuum classes")
    mut_b_rec = mutate_text(
        B_text,
        "class: all three vacuum classes",
        "class: all four classes including AF-WCC-SCALAR-SPH")
    box_mut = run_sandbox_checker("stored_records_mutated", mut_a_rec, mut_b_rec)
    c12_ok = (box_mut["exit_code"] == 0 and (box_mut["certificate"] or {}).get("consistent") is True
              and (box_mut["certificate"] or {}).get("contract_divergences") == [])
    add("C12", "dynamic sandbox silence control: mutating ONLY the stored D3 records leaves the certificate green",
        "unchanged (CONSISTENT)",
        {"exit_code": box_mut["exit_code"], "consistent": (box_mut["certificate"] or {}).get("consistent"),
         "stdout": box_mut["stdout"][-200:]},
        c12_ok)

    A_mut, err_a = parse_mutated(mut_a_rec, "A-mutant-M1")
    B_mut, err_b = parse_mutated(mut_b_rec, "B-mutant-M2")
    if err_a or err_b:
        a2_rec, b2_rec = None, None
        c13_ok = False
    else:
        a2_rec, b2_rec = d3_records(A_mut, B_mut)
        reading_mut = scope_reading(a2_rec, b2_rec)
        c13_ok = reading_mut["conflict"] is False
    add("C13", "detector sensitivity: the same stored-record mutation flips C8 CONTRADICTION -> AGREE",
        "flip to AGREE",
        {"a_scalar": (a2_rec or {}).get("resolution", "")[:120], "b_class": (b2_rec or {}).get("class"),
         "flipped": c13_ok},
        c13_ok)

    # ---- C14 materiality recount ----
    rmap = json.loads((ROOT / PIN_SPEC["research_map"]["path"]).read_text())
    scalar_claims = [c for c in (rmap.get("claims") or []) if "AF-WCC-SCALAR-SPH" in json.dumps(c)]
    theorem_types = [c for c in scalar_claims
                     if str(c.get("conclusion_type", "")).lower() in ("theorem", "conditional_theorem")]
    add("C14", "materiality: claims bound to AF-WCC-SCALAR-SPH with conclusion_type theorem/conditional_theorem",
        0, {"scalar_bound_claims": len(scalar_claims), "theorem_like": len(theorem_types)},
        len(theorem_types) == 0)

    # ---- controls M1-M6 ----
    def ctl(mid, mutation, required, observed, ok):
        controls.append({"id": mid, "mutation": mutation, "required": required,
                         "observed": observed, "pass": bool(ok)})

    ctl("M1", "A D3 resolution four-class -> three-class (B unchanged)",
        "C8 AGREE, C3 false",
        {"c8_conflict": reading_mut["conflict"] if not err_a else None,
         "c3_scalar_named": "AF-WCC-SCALAR-SPH" in str((a2_rec or {}).get("resolution", ""))},
        (not err_a) and (reading_mut["conflict"] is False)
        and ("AF-WCC-SCALAR-SPH" not in str((a2_rec or {}).get("resolution", ""))))

    b_rec_m2 = None
    if not err_b:
        for rec in (B_mut.get("contract_divergences", {}) or {}).get("items", []) or []:
            if str(rec.get("id")) == "D3":
                b_rec_m2 = rec
        r_m2 = scope_reading(a_rec, b_rec_m2)
    else:
        r_m2 = {"conflict": None}
    ctl("M2", "B D3 class three-class -> four-class incl. scalar (A unchanged)",
        "C8 AGREE, C5 false",
        {"c8_conflict": r_m2["conflict"], "b_class": (b_rec_m2 or {}).get("class")},
        (not err_b) and r_m2["conflict"] is False
        and str((b_rec_m2 or {}).get("class", "")).lower() != "all three vacuum classes")

    # M3: field-level mutant of A's two secondary scalar-D3 statements; stored D3 record intact.
    A3 = copy.deepcopy(A)
    A3["revision_note_rev5"] = str(A3.get("revision_note_rev5", "")).replace(
        "(g) the D3 resolution is confirmed discharged for the scalar class (B-16F0-2 / W082-F-02); ", "")
    A3["classes"]["AF-WCC-SCALAR-SPH"]["conclusion"]["text"] = str(
        A3["classes"]["AF-WCC-SCALAR-SPH"]["conclusion"]["text"]).replace(
        "[rev5: D1/D3 discharge for this class. ", "[rev5: D1 discharge only. ")
    note3 = str(A3.get("revision_note_rev5", ""))
    scal3 = str(A3["classes"]["AF-WCC-SCALAR-SPH"]["conclusion"]["text"])
    c4_m3 = ("discharged for the scalar class" in note3.lower()) or ("[rev5: D1/D3 discharge for this class" in scal3)
    r_m3 = scope_reading(d3_records(A3, B)[0], b_rec)
    ctl("M3", "A secondary scalar-D3 statements removed at field level (stored D3 record intact)",
        "C4 false, C8 still CONTRADICTION",
        {"c4_holds": c4_m3, "c8_conflict": r_m3["conflict"]},
        (not c4_m3) and r_m3["conflict"] is True)

    mut_a_m4 = mutate_text(
        A_text,
        "A generic family of smooth spherically symmetric massless-scalar Cauchy data",
        "A MUTANT-UNRELATED family of smooth spherically symmetric massless-scalar Cauchy data")
    A_m4, err_m4 = parse_mutated(mut_a_m4, "A-mutant-M4")
    r_m4 = scope_reading(d3_records(A_m4, B)[0] if not err_m4 else None, b_rec)
    ctl("M4", "unrelated A test-case description edited",
        "D3 verdict unchanged (CONTRADICTION)",
        {"c8_conflict": r_m4["conflict"]},
        (not err_m4) and r_m4["conflict"] is True)

    B_m5_text = mutate_text(B_text, "class: AF-WCC-VAC-GEN,", "class: AF-WCC-VAC-GEN-MUTANT,")
    B_m5, err_m5 = parse_mutated(B_m5_text, "B-mutant-M5")
    r_m5 = scope_reading(a_rec, d3_records(A, B_m5)[1] if not err_m5 else None)
    ctl("M5", "B D1 class scope edited",
        "D3 verdict unchanged (CONTRADICTION)",
        {"c8_conflict": r_m5["conflict"]},
        (not err_m5) and r_m5["conflict"] is True)

    # M6: mid-document truncation that removes the closing bracket of a flow sequence.
    cut = A_text.index("decisive_hypotheses: [")
    truncated = A_text[:cut] + 'decisive_hypotheses: ["H1"\n'
    _, err_m6 = parse_mutated(truncated, "A-mutant-M6")
    ctl("M6", "sandbox A YAML truncated mid-document (unclosed flow sequence at EOF)",
        "fail-closed parse error, no silent pass",
        {"parse_error": err_m6 is not None, "detail": err_m6},
        err_m6 is not None)

    pins_end = measure_pins()
    drift = {n: (pins_start[n]["sha256"] != pins_end[n]["sha256"]) for n in pins_start}
    drift_any = any(drift.values())

    all_checks = all(c["pass"] for c in checks)
    all_controls = all(c["pass"] for c in controls)
    if void_reasons or drift_any or not all_controls:
        verdict = "INSTRUMENT_VOID"
    elif all_checks:
        verdict = "CORROBORATED"
    else:
        verdict = "REFUTED"
    exit_code = {"CORROBORATED": 0, "REFUTED": 1, "INSTRUMENT_VOID": 2}[verdict]

    report = {
        "task_id": PREREG["task_id"],
        "actor": "worker-022",
        "class_id": "AF-WCC-SCALAR-SPH",
        "node_id": "F0",
        "gate": "G-F0",
        "verified_finding": "HF-059-SPH-01",
        "verdict": verdict,
        "score": 4.0 if verdict == "CORROBORATED" else None,
        "measurement_window": {"start": t_start, "end": now_iso()},
        "pins_start": pins_start,
        "pins_end": pins_end,
        "pin_drift": drift,
        "checks_total": len(checks),
        "checks_pass": sum(1 for c in checks if c["pass"]),
        "checks": checks,
        "controls_pass": sum(1 for c in controls if c["pass"]),
        "controls": controls,
        "sandbox": {"pristine": box_pristine, "stored_records_mutated": box_mut},
        "finding_text": ("At FROZEN rev29 pins A=0abb9ed8a961 and B=d7419b4e8963, A's stored D3 "
                         "resolution records the discharge as covering ALL FOUR classes including "
                         "AF-WCC-SCALAR-SPH while B's stored D3 record scopes it to the three vacuum "
                         "classes and never names the scalar class; the canonical certificate is green "
                         "because the checker recomputes divergences from conclusion texts and never "
                         "compares the stored records."),
        "falsifier": PREREG["falsifier"],
        "independence_statement": ("worker-022 did not author A, B, FROZEN, the certificate or the "
                                   "checker, and did not import worker-059's detector or any canonical "
                                   "module; extraction, detector and mutants are implemented here from "
                                   "the pinned bytes. One reviewer label (ESS=1)."),
        "authority_note": PREREG["authority_note"],
        "reproduce": "python3 artifacts/worker-022/f0_sph_d3_verdict/verify_f0_sph_d3_022.py",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "checks": f"{report['checks_pass']}/{report['checks_total']}",
                      "controls": f"{report['controls_pass']}/{len(controls)}",
                      "pin_drift": drift_any}, indent=1))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

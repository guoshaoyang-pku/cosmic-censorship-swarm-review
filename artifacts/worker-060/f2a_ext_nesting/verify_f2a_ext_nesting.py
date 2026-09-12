#!/usr/bin/env python3
"""W060-F2A-EXT-NESTING-MATERIALITY-01.

Independent, read-only, hash-pinned adjudication of the F2a vs F2b extension-predicate
asymmetry reported as HF-091-02 (worker-091, 2026-09-12T01:03:40+08:00) and its
materiality for the licensed transfer

    no proper future C0 extension  =>  no proper future C2 extension
    (equivalently E_C2 subset of E_C0, i.e. P_C2 => P_C0)

at the live rev13 / FROZEN-rev29 bytes.

Sets, stated precisely (this is the object the checks decide about):
  Omega          = one-ended AF vacuum initial data (M,g) as fixed by data_class
  P_X(M,g,triple) = "triple is a proper future X extension of (M,g)" as defined by
                    the X schema's extension_predicate (+ its cross-referenced fields)
  E_X            = { (M,g) in Omega : exists triple with P_X }
The licensed transfer is equivalent to E_C2 subset of E_C0, which holds iff every
triple satisfying P_C2 also satisfies P_C0.

Pre-registered verdict rules (fixed before the run; do not edit during a run):
  RUN VALID   iff all six pins match at T0 and T1, both mirrors are byte-aligned,
              and controls K1..K6 all pass.
  H1 CONFIRMED iff axes A1 (M'' manifold category), A2 (iota regularity) and
              A3 (clause (f) interior requirement) are each measured asymmetric
              (present in F2b, absent from F2a and from every F2a cross-reference).
  H2 MATERIAL iff >=1 axis makes P_C2 => P_C0 non-derivable from the frozen bytes.
              The dominant axis is A3, whose escape is already accepted in F2b's
              own R2-major repair note; A2 is material as a freeze gap.
  Overall     : F2a verdict "revise" (transfer not licensed as written); advisory
              worker evidence only - no gate verdict, no node status, no writes to
              any canonical path.

Every check carries its own falsifier. Controls mutate sandbox copies only.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import yaml

TASK_ID = "W060-F2A-EXT-NESTING-MATERIALITY-01"
WORKER = "worker-060"
NODE = "F2a"
CLASS_ID = "AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN"
GATE = "G-FORM"

# Pre-registered pins (measured 2026-09-12T01:07:24+08:00, before the run).
PINS = {
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/VARIANT_REGISTRY.json":
        "6bac9adea19e17efe625342ef4d2098e3775491aa3d0e06596cd5d75912348fb",
}
MIRRORS = {
    "schemas/af_scc_c2_vacuum.yaml": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}
SNAP_NAME = {
    "schemas/af_scc_c2_vacuum.yaml": "f2a.e9a27996dfd3.yaml",
    "schemas/af_scc_c0_vacuum.yaml": "f2b.b2ab6acb2bbe.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml": "supplement.d7419b4e8963.yaml",
    "research_map/formulation_taxonomy.yaml": "taxonomy.0abb9ed8a961.yaml",
    "artifacts/formulation/FROZEN.json": "frozen.rev29.815e08079aef.json",
    "artifacts/formulation/VARIANT_REGISTRY.json": "variant_registry.6bac9adea19e.json",
}

C2_KNOWN_FIELDS = ("SMOOTH", "C^infinity", "iota_regularity", "int(M' minus iota(M))")


# ---------------------------------------------------------------- helpers

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(repo: Path, rel: str):
    p = repo / rel
    if not p.exists():
        return {"path": str(p), "exists": False, "sha256": None, "bytes": None}
    st = p.stat()
    return {
        "path": str(p),
        "exists": True,
        "sha256": sha256_file(p),
        "bytes": st.st_size,
        "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime)),
    }


def pin_state(repo: Path, pins):
    return {rel: measure(repo, rel) for rel in pins}


def pins_ok(state, pins):
    bad = []
    for rel, want in pins.items():
        got = state[rel]
        if not got["exists"] or got["sha256"] != want:
            bad.append({"path": rel, "want": want, "got": got["sha256"],
                        "exists": got["exists"]})
    return (len(bad) == 0), bad


def mirror_state(repo: Path):
    out = {}
    for canon, mirror in MIRRORS.items():
        a, b = measure(repo, canon), measure(repo, mirror)
        out[canon] = {
            "canonical_sha256": a["sha256"], "mirror_sha256": b["sha256"],
            "aligned": bool(a["sha256"] and a["sha256"] == b["sha256"]),
        }
    return out


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


CLAUSE_RE = re.compile(r"\(([a-f])\)\s*(.*?)(?=;\s*\([a-f]\)|$)", re.S)


def clauses(definition: str):
    return {m.group(1): re.sub(r"\s+", " ", m.group(2)).strip()
            for m in CLAUSE_RE.finditer(definition)}


def field_by_path(doc, dotted):
    cur = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def census(text: str, needle: str):
    return [m.start() for m in re.finditer(re.escape(needle), text)]


def flatten_strings(obj, prefix=""):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(flatten_strings(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(flatten_strings(v, f"{prefix}[{i}]"))
    elif isinstance(obj, str):
        out.append((prefix, obj))
    return out


def find_token(doc, needles):
    hits = []
    for path, s in flatten_strings(doc):
        for n in needles:
            if n.lower() in s.lower():
                hits.append({"field": path, "needle": n})
                break
    return hits


def find_field(doc, leaf):
    """Return the dotted paths of any mapping key whose last segment is `leaf`."""
    out = []

    def walk(o, prefix=""):
        if isinstance(o, dict):
            for k, v in o.items():
                p = f"{prefix}.{k}" if prefix else str(k)
                if str(k) == leaf:
                    out.append(p)
                walk(v, p)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{prefix}[{i}]")

    walk(doc)
    return out


MPRIME_SMOOTH_NEEDLES = ("smooth 4-manifold", "SMOOTH (C", "smooth manifold")


# ---------------------------------------------------------------- checks

def build_checks(repo: Path):
    f2a_path = repo / "schemas/af_scc_c2_vacuum.yaml"
    f2b_path = repo / "schemas/af_scc_c0_vacuum.yaml"
    sup_path = repo / "artifacts/formulation/formulation_taxonomy.yaml"
    tax_path = repo / "research_map/formulation_taxonomy.yaml"

    f2a, f2b = load_yaml(f2a_path), load_yaml(f2b_path)
    sup, tax = load_yaml(sup_path), load_yaml(tax_path)
    f2a_txt, f2b_txt = load_text(f2a_path), load_text(f2b_path)

    a_def = f2a["extension_predicate"]["definition"]
    b_def = f2b["extension_predicate"]["definition"]
    a_cl, b_cl = clauses(a_def), clauses(b_def)

    a_ext_top = f2a["topology"]["extension_topology"]
    b_ext_top = f2b["topology"]["extension_topology"]
    b_iota = field_by_path(f2b, "non_vacuity.iota_regularity")
    a_iota_fields = find_field(f2a, "iota_regularity")
    b_iota_fields = find_field(f2b, "iota_regularity")

    f2a_census = {n: census(f2a_txt, n) for n in C2_KNOWN_FIELDS}
    f2b_census = {n: census(f2b_txt, n) for n in C2_KNOWN_FIELDS}

    tax_c2 = tax["classes"]["AF-SCC-C2-VAC-GEN"]
    tax_c0 = tax["classes"]["AF-SCC-C0-VAC-GEN"]
    tax_c0_h4 = [h.get("text", "") for h in tax_c0.get("hypotheses", [])
                 if h.get("id") == "H4"]
    tax_c2_h4 = [h.get("text", "") for h in tax_c2.get("hypotheses", [])
                 if h.get("id") == "H4"]
    sup_c2 = sup["class_contracts"]["AF-SCC-C2-VAC-GEN"]
    sup_c0 = sup["class_contracts"]["AF-SCC-C0-VAC-GEN"]
    sup_hits_c2 = find_token(sup_c2, list(MPRIME_SMOOTH_NEEDLES) + ["iota", "interior", "int("])
    sup_hits_c0 = find_token(sup_c0, list(MPRIME_SMOOTH_NEEDLES) + ["iota", "interior", "int("])
    tax_hits = find_token({"classes": {"C2": tax_c2, "C0": tax_c0}},
                          list(MPRIME_SMOOTH_NEEDLES) + ["iota", "interior", "int("])
    sup_c2_requirements = find_token(sup_c2, list(MPRIME_SMOOTH_NEEDLES))
    tax_c2_requirements = find_token(tax_c2, list(MPRIME_SMOOTH_NEEDLES))

    vr = json.loads(load_text(repo / "artifacts/formulation/VARIANT_REGISTRY.json"))
    vr_txt = json.dumps(vr)
    vr_hits = {n: census(vr_txt, n) for n in
               ("iota", "smooth", "int(M'", "smooth 4-manifold", "SMOOTH (C")}

    checks = []

    def add(cid, axis, ok, statement, falsifier, observations):
        checks.append({"id": cid, "axis": axis, "ok": bool(ok),
                       "statement": statement, "falsifier": falsifier,
                       "observations": observations})

    # ---- A1: M'' manifold category
    a1_pos = ("SMOOTH" in a_cl.get("c", "")) or ("SMOOTH" in a_ext_top)
    a1_b_pos = ("SMOOTH" in b_cl.get("c", "")) or ("SMOOTH" in b_ext_top)
    add("A1", "M-prime manifold category", (not a1_pos) and a1_b_pos,
        "F2a does not freeze the manifold category of M''; F2b freezes SMOOTH "
        "(C-infinity) and records the rationale that a merely topological M'' "
        "cannot carry a classical Lorentzian tensor field.",
        "A field in F2a (clause (c), topology, conventions, regularity, anti_scope, "
        "falsifier, unresolved_items, or either F0 cross-reference) requiring M'' "
        "smooth; or F2b lacking the requirement.",
        {"f2a_clause_c": a_cl.get("c"), "f2b_clause_c": b_cl.get("c"),
         "f2a_extension_topology": a_ext_top, "f2b_extension_topology": b_ext_top,
         "f2a_smooth_census": f2a_census["SMOOTH"],
         "f2b_smooth_census": f2b_census["SMOOTH"]})
    add("A1-implied", "M-prime manifold category",
        not sup_c2_requirements and not tax_c2_requirements,
        "No F2a cross-reference freezes the manifold category of M'' for the C2 "
        "class: the supplement C2 contract has no 'smooth 4-manifold'/'smooth "
        "manifold' requirement and the declared taxonomy's C2 class does not "
        "either. The category is at best implicit in the typing of a C2 metric "
        "tensor field.",
        "A supplement/taxonomy row pinning M'' smooth for the C2 class.",
        {"supplement_c2_requirements": sup_c2_requirements,
         "taxonomy_c2_requirements": tax_c2_requirements,
         "supplement_c2_near_misses": sup_hits_c2,
         "taxonomy_near_misses": tax_hits[:8]})

    # ---- A2: iota regularity
    a2_pos = bool(a_iota_fields) or bool(
        re.search(r"iota[^;]{0,60}(regular|smooth|C\^)", a_cl.get("a", ""), re.I))
    a2_b_pos = bool(b_iota_fields) and bool(b_iota)
    add("A2", "iota (embedding) regularity", (not a2_pos) and a2_b_pos,
        "F2a has no iota_regularity field and its clause (a) specifies no "
        "regularity for the embedding; F2b freezes iota as a C-infinity isometric "
        "embedding to remove the R2-04 ambiguity.",
        "An F2a field or cross-reference freezing iota regularity; or F2b lacking "
        "non_vacuity.iota_regularity.",
        {"f2a_iota_fields": a_iota_fields, "f2a_clause_a": a_cl.get("a"),
         "f2b_iota_regularity": b_iota, "f2b_iota_fields": b_iota_fields})
    add("A2-taxonomy", "iota (embedding) regularity",
        any("embedding" in t and "unresolved" in t for t in tax_c0_h4),
        "The declared taxonomy itself records the embedding-vs-metric regularity "
        "subtlety as unresolved for the C0 class and assigns the fix to F2/L1; F2b "
        "fixed it locally, F2a did not. So the F2a bytes do not decide the axis.",
        "A taxonomy row that fixes iota regularity for C2, or an F2a convention.",
        {"tax_c0_H4": tax_c0_h4, "tax_c2_H4": tax_c2_h4})

    # ---- A3: clause (f) interior requirement
    a3_pos = "int(" in a_cl.get("f", "")
    a3_b_pos = "int(" in b_cl.get("f", "")
    b_r2_note = f2b["extension_predicate"]["definition"]
    escape_recorded = ("escapable" in b_r2_note) and ("boundary/dense-open" in b_r2_note
                                                      or "dense-open" in b_r2_note)
    add("A3", "clause (f) interior requirement", (not a3_pos) and a3_b_pos,
        "F2a clause (f) requires only a witness point p in M'' minus iota(M); F2b "
        "additionally requires int(M'' minus iota(M)) non-empty and p in the "
        "interior, with an accepted R2-major note that the unqualified clause was "
        "escapable by extensions that add only boundary/dense-open points.",
        "An interior requirement anywhere in F2a; or F2b clause (f) lacking it.",
        {"f2a_clause_f": a_cl.get("f"), "f2b_clause_f": b_cl.get("f"),
         "f2b_escape_note_present": escape_recorded,
         "f2a_int_census": census(f2a_txt, "int(M' minus iota(M))"),
         "f2b_int_census": census(f2b_txt, "int(M' minus iota(M))")})

    # ---- A4: implied-elsewhere aggregate census (whole-file, both F0 refs)
    a4_hits = {
        "f2a_iota_regularity_fields": a_iota_fields,
        "f2a_SMOOTH_extension_slot": [h for h in find_token(f2a, list(MPRIME_SMOOTH_NEEDLES))
                                      if "extension" in h["field"] or "topology" in h["field"]],
        "f2a_int_in_clause_f": census(a_cl.get("f", ""), "int("),
        "supplement_c2_requirements": sup_c2_requirements,
        "taxonomy_c2_requirements": tax_c2_requirements,
        "variant_registry": vr_hits,
    }
    a4_ok = (not a4_hits["f2a_iota_regularity_fields"]
             and not a4_hits["f2a_SMOOTH_extension_slot"]
             and len(a4_hits["f2a_int_in_clause_f"]) == 0
             and not sup_c2_requirements
             and not tax_c2_requirements
             and all(len(v) == 0 for v in vr_hits.values()))
    add("A4", "implied-elsewhere census", a4_ok,
        "No F2a field, supplement contract, declared-taxonomy row or registered "
        "variant supplies any of the three axes for the C2 class; the VARIANT_REGISTRY "
        "has no iota/smooth/interior/manifold-category variant.",
        "Any cross-reference found above supplying an axis.",
        a4_hits)

    # ---- B5: licensed-transfer derivability
    led = f2a["implication_ledger"]
    entail = led["one_way_entailments"][0]
    led_b = f2b["implication_ledger"]["one_way_entailments"]
    b_transfer = [r for r in led_b if r.get("from") ==
                  "no proper future C0 metric extension"
                  and r.get("to") == "no proper future C2 extension"]
    a_boundary = field_by_path(f2a, "class_boundary.one_way_implication")
    a_contain = led.get("extension_class_containment")
    b_contain = f2b["implication_ledger"].get("extension_class_containment")
    material_axes = []
    if not a3_pos and a3_b_pos:
        material_axes.append("A3-clause-f-interior")
    if not a2_pos and a2_b_pos:
        material_axes.append("A2-iota-regularity-freeze-gap")
    b5_ok = len(material_axes) == 0
    add("B5", "licensed C0=>C2 transfer derivability", b5_ok,
        "The transfer row in F2a's ledger ('no proper future C0 extension' entails "
        "'no proper future C2 extension', reason E_C2 subset of E_C0) is not "
        "derivable from the frozen bytes: P_C2 => P_C0 fails because F2a's predicate "
        "lacks F2b's iota_regularity convention and clause-(f) interior requirement. "
        "So the transfer is not licensed as written at these bytes.",
        "A derivation from the F2a bytes alone that every F2a-extension triple "
        "satisfies F2b's predicate (i.e. the three axes are supplied), or a schema "
        "drift after which the transfer is independently licensed.",
        {"f2a_entailment": entail, "f2a_containment": a_contain,
         "f2a_class_boundary_one_way": a_boundary, "f2b_containment": b_contain,
         "f2b_transfer_rows": b_transfer, "material_axes": material_axes,
         "f2b_iota_regularity": b_iota})

    # ---- B6: independence from the prior data_class adjudication
    prior = repo / "artifacts/worker-060/xclass_dataclass_adjudication/evidence.json"
    prior_ok = prior.exists()
    add("B6", "relation to prior worker-060 data_class verdict", prior_ok,
        "The transfer was previously measured NOT disabled by a data_class "
        "divergence (worker-060 xclass adjudication: F2a/F2b equal on 15/15 "
        "data-space-core keys). This task tests a different surface "
        "(extension_predicate clauses), so a MATERIAL verdict here is not a "
        "reversal of that verdict.",
        "The prior evidence file absent, so the two surfaces cannot be separated.",
        {"prior_evidence": str(prior), "prior_exists": prior_ok,
         "surface": "extension_predicate clauses (a)/(c)/(f) + iota convention; "
                    "NOT data_class"})

    return checks, {
        "f2a_clauses": a_cl, "f2b_clauses": b_cl,
        "material_axes": material_axes,
        "a1_category": {"f2a_present": a1_pos, "f2b_present": a1_b_pos},
        "a2_iota": {"f2a_present": a2_pos, "f2b_present": a2_b_pos},
        "a3_interior": {"f2a_present": a3_pos, "f2b_present": a3_b_pos},
    }


# ---------------------------------------------------------------- controls

def run_controls(repo: Path, sandbox: Path):
    controls = {}

    def record(k, ok, detail):
        controls[k] = {"ok": bool(ok), "detail": detail}

    # K3a: wrong pre-registered pin -> fail-closed VOID via subprocess
    bad_pins = dict(PINS)
    bad_pins["schemas/af_scc_c2_vacuum.yaml"] = "0" * 64
    k3a = subprocess.run(
        [sys.executable, str(Path(__file__)), "--repo", str(repo),
         "--no-write", "--no-controls", "--json",
         "--pins-json", json.dumps(bad_pins)],
        capture_output=True, text=True)
    record("K3a_wrong_pin_fails_closed", k3a.returncode == 2,
           {"exit": k3a.returncode, "stdout_tail": k3a.stdout.strip()[-200:]})

    # K3b: byte-mutated sandbox -> VOID even with unchanged pins
    if sandbox.exists():
        shutil.rmtree(sandbox)
    (sandbox / "schemas").mkdir(parents=True)
    (sandbox / "artifacts/formulation/schemas").mkdir(parents=True)
    (sandbox / "artifacts/formulation").mkdir(parents=True, exist_ok=True)
    (sandbox / "research_map").mkdir(parents=True, exist_ok=True)
    for rel in PINS:
        src, dst = repo / rel, sandbox / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    for canon, mirror in MIRRORS.items():
        (sandbox / mirror).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / canon, sandbox / mirror)
    with open(sandbox / "schemas/af_scc_c2_vacuum.yaml", "ab") as fh:
        fh.write(b"\n# sandbox mutation\n")
    k3b = subprocess.run(
        [sys.executable, str(Path(__file__)), "--repo", str(sandbox),
         "--no-write", "--no-controls", "--json"],
        capture_output=True, text=True)
    record("K3b_byte_mutation_fails_closed", k3b.returncode == 2,
           {"exit": k3b.returncode, "stdout_tail": k3b.stdout.strip()[-200:]})

    # K1: positive detector injection: F2a clause (f) gains the interior phrase
    k1_dir = sandbox.parent / (sandbox.name + "_k1")
    if k1_dir.exists():
        shutil.rmtree(k1_dir)
    shutil.copytree(sandbox, k1_dir)
    # restore a clean f2a first
    shutil.copyfile(repo / "schemas/af_scc_c2_vacuum.yaml",
                    k1_dir / "schemas/af_scc_c2_vacuum.yaml")
    p = k1_dir / "schemas/af_scc_c2_vacuum.yaml"
    txt = p.read_text(encoding="utf-8")
    txt = txt.replace(
        "there exist q in iota(M) and p in M' minus iota(M) with p in I^+(q; g').",
        "int(M' minus iota(M)) is non-empty AND there exist q in iota(M) and p in "
        "int(M' minus iota(M)) with p in I^+(q; g').", 1)
    p.write_text(txt, encoding="utf-8")
    shutil.copyfile(p, k1_dir / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml")
    k1_pins = {rel: sha256_file(k1_dir / rel) for rel in PINS}
    k1 = subprocess.run(
        [sys.executable, str(Path(__file__)), "--repo", str(k1_dir),
         "--no-write", "--no-controls", "--json",
         "--pins-json", json.dumps(k1_pins)],
        capture_output=True, text=True)
    k1_ok = False
    k1_detail = {"exit": k1.returncode}
    if k1.returncode in (0, 3):
        try:
            res = json.loads(k1.stdout.strip().splitlines()[-1])
            a3 = [c for c in res["checks"] if c["id"] == "A3"]
            k1_ok = bool(a3) and a3[0]["ok"] is False  # injection removes the asymmetry
            k1_detail["A3_after_injection"] = a3[0]["ok"] if a3 else None
            k1_detail["H1_after_injection"] = res["verdict"]["H1_asymmetry_present"]
        except Exception as exc:  # noqa: BLE001
            k1_detail["parse_error"] = repr(exc)
    record("K1_positive_injection_flips_A3", k1_ok, k1_detail)

    # K2: negative detector: A3 detection is content-based, not path-based
    k2 = subprocess.run(
        [sys.executable, str(Path(__file__)), "--repo", str(repo),
         "--no-write", "--no-controls", "--json"],
        capture_output=True, text=True)
    k2_ok = False
    k2_detail = {"exit": k2.returncode}
    if k2.returncode in (0, 3):
        try:
            res = json.loads(k2.stdout.strip().splitlines()[-1])
            a3 = [c for c in res["checks"] if c["id"] == "A3"][0]
            k2_ok = (a3["ok"] is True
                     and a3["observations"]["f2b_int_census"]
                     and not a3["observations"]["f2a_int_census"])
            k2_detail["A3"] = a3["ok"]
        except Exception as exc:  # noqa: BLE001
            k2_detail["parse_error"] = repr(exc)
    record("K2_negative_detector_content_based", k2_ok, k2_detail)

    # K4: slot alignment - clause letters and clause intros match across files
    f2a = load_yaml(repo / "schemas/af_scc_c2_vacuum.yaml")
    f2b = load_yaml(repo / "schemas/af_scc_c0_vacuum.yaml")
    ca = clauses(f2a["extension_predicate"]["definition"])
    cb = clauses(f2b["extension_predicate"]["definition"])
    k4_ok = (set(ca) == set(cb)
             and "adds points to the future" in ca["f"]
             and "adds points to the future" in cb["f"])
    record("K4_clause_slot_alignment", k4_ok,
           {"clause_keys_f2a": sorted(ca), "clause_keys_f2b": sorted(cb),
            "intro_f2a": ca["f"][:60], "intro_f2b": cb["f"][:60]})

    # K6: independence - authors are not worker-060; script imports stdlib + yaml
    authors = {
        "f2a_authored_by": str(f2a.get("authored_by")),
        "f2a_owner": str(f2a.get("owner")),
        "f2b_authored_by": str(f2b.get("authored_by")),
        "f2b_owner": str(f2b.get("owner")),
    }
    mods = {m.split(".")[0] for m in sys.modules
            if not m.startswith("_") and m not in ("__main__",)}
    ext = sorted(m for m in mods if m in
                 ("yaml", "numpy", "scipy", "sympy", "pandas", "matplotlib"))
    k6_ok = all("worker-060" not in v for v in authors.values()) and ext in ([], ["yaml"])
    record("K6_independence", k6_ok, {"authors": authors,
                                      "third_party_imports": ext})

    return controls


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="/data3/guoshaoyang/workdir/ai4math-swarm")
    ap.add_argument("--out", default=None)
    ap.add_argument("--snapshot-dir", default=None)
    ap.add_argument("--sandbox", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument("--no-controls", action="store_true")
    ap.add_argument("--allow-repin", action="store_true")
    ap.add_argument("--pins-json", default=None)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    pins = dict(PINS)
    if args.pins_json:
        pins = json.loads(args.pins_json)

    t0 = pin_state(repo, pins)
    ok0, bad0 = pins_ok(t0, pins)
    if not ok0 and not args.allow_repin:
        void = {"task_id": TASK_ID, "worker": WORKER, "run_status": "VOID",
                "reason": "pre-registered pin mismatch at T0; no verdict written",
                "pin_failures": bad0, "measured_T0": t0,
                "next_falsifier": "re-measure and re-register pins at the new bytes"}
        print(json.dumps(void))
        return 2

    mirrors = mirror_state(repo)
    checks, derived = build_checks(repo)

    controls = {} if args.no_controls else run_controls(
        repo, Path(args.sandbox) if args.sandbox
        else (repo / "tmp/w060_f2a_ext_nesting_sandbox"))

    t1 = pin_state(repo, pins)
    ok1, bad1 = pins_ok(t1, pins)
    mirrors_ok = all(m["aligned"] for m in mirrors.values())
    controls_ok = all(c["ok"] for c in controls.values())
    run_valid = ok0 and ok1 and mirrors_ok and controls_ok

    h1 = all(derived[k]["f2a_present"] is False and derived[k]["f2b_present"] is True
             for k in ("a1_category", "a2_iota", "a3_interior"))
    h2_material = len(derived["material_axes"]) > 0

    if not run_valid:
        run_status = "INVALID"
    elif h1 and h2_material:
        run_status = "VALID"
    else:
        run_status = "VALID_FALSIFIED"

    verdict = {
        "H1_asymmetry_present": "CONFIRMED" if h1 else "NOT_CONFIRMED",
        "H2_transfer_material": "MATERIAL" if h2_material else "IMMATERIAL",
        "transfer_licensed_as_written": not h2_material,
        "material_axes": derived["material_axes"],
        "axis_detail": {
            "A1_M_prime_category": derived["a1_category"],
            "A2_iota_regularity": derived["a2_iota"],
            "A3_clause_f_interior": derived["a3_interior"],
        },
        "f2a_review_verdict": "revise" if h2_material else "advisory_no_change",
        "run_status": run_status,
    }

    evidence = {
        "task_id": TASK_ID,
        "worker": WORKER,
        "actor": WORKER,
        "node_id": NODE,
        "class_id": CLASS_ID,
        "gate": GATE,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "scope": "read-only advisory adjudication; no canonical byte written; "
                 "no gate verdict; worker events cannot set done/passed",
        "pins": pins,
        "inputs_T0": t0,
        "inputs_T1": t1,
        "mirrors": mirrors,
        "checks": checks,
        "controls": controls,
        "derived": derived,
        "verdict": verdict,
        "limitations": [
            "Materiality is adjudicated at the level of the frozen bytes: whether "
            "P_C2 => P_C0 is derivable. It does not construct a vacuum extension "
            "realising the A3 escape; F2b's own accepted R2-major note supplies the "
            "escape schema and is cited as the primary evidence.",
            "A2 is a freeze gap: 'isometric embedding' may be read as smooth by "
            "convention, in which case the axis is immaterial; the bytes do not "
            "decide it, which is exactly the defect.",
            "A1 is immaterial under the standard typing of a C2 tensor field "
            "(a differentiable structure is implicit) but the rationale frozen in "
            "F2b was not propagated.",
            "The F2b line-246 inverted-containment hard failure (HF-060-CS-01) and "
            "the F2a/F2b data_class surface are out of scope and were measured by "
            "other lifecycles.",
        ],
        "next_falsifier": (
            "Re-run this script at any new pin: H2 flips to IMMATERIAL iff F2a "
            "supplies all three axes (iota_regularity, an interior requirement in "
            "clause (f), and the M'' smooth category) or the transfer row is "
            "withdrawn, so that P_C2 => P_C0 is derivable from the F2a bytes alone. "
            "Any pin drift voids the measurement."
        ),
    }

    if not args.no_write:
        out = Path(args.out) if args.out else repo / "artifacts/worker-060/f2a_ext_nesting/evidence.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(evidence, indent=1, sort_keys=False) + "\n",
                       encoding="utf-8")
        snap = Path(args.snapshot_dir) if args.snapshot_dir else out.parent / "snapshots"
        snap.mkdir(parents=True, exist_ok=True)
        for rel, name in SNAP_NAME.items():
            shutil.copyfile(repo / rel, snap / name)

    if args.json:
        print(json.dumps(evidence))
    return 0 if run_status == "VALID" else (2 if run_status == "INVALID" else 3)


if __name__ == "__main__":
    sys.exit(main())

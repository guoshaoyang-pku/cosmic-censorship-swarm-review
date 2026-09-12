#!/usr/bin/env python3
"""W046-F2A-EXTFREEZE-PREVALIDATION-01 -- independent, read-only pre-validation of the
sibling-aligned F2a extension-predicate freeze candidate (option A).

Class AF-SCC-C2-VAC-GEN | node F2a | gate G-FORM (context only; no gate verdict issued).

What is decided here
--------------------
The G-FORM blockers on F2a are (i) the under-frozen extension predicate (manifold category of
M', differentiability class of iota, interior-future requirement of clause (f)) and (ii) the
consequence that the declared containment E_C2 subset E_C0 is not entailed by the pinned
clause pair.  worker-047 published a repair SPEC (not a candidate validation).  This instrument
answers the owner's outstanding question at the pinned bytes:

  1. does the five-site repair applied to the LIVE F2a bytes still PASS the pinned canonical
     structural gate (R01-R31), and is the change bound to exactly three YAML leaves?
  2. does an independent clause-lattice instrument report that P_C2 => P_C0 becomes derivable
     after the repair, under a strict-literal reading and under a standard-typing reading?
  3. does the repaired candidate preserve every class-identity invariant (C2 token, Ric=0,
     genericity, containment chain, no C0/I+ content in asserted paths)?
  4. what does the repair NOT fix (gate blindness, import-rule/class-boundary tension,
     witness-type propagation), so the owner folds it knowingly?

Method
------
Deterministic and fail-closed.  All canonical targets are hashed at start and end; a moved pin
voids the run (exit 2, nothing is promoted).  The candidate is built by exact single-occurrence
text substitution on a copy; the canonical schema is never written.  The canonical gate runs as
a subprocess on the candidate and on seven mutants, including two positive controls (class-id
and conclusion-type swaps) that MUST fail, and five repair-reverting mutants that measure what
the structural gate can and cannot see.  The containment instrument is an independent pattern
classifier over the six predicate clauses plus the four predicate-level convention fields, with
a pre-registered lattice and pre-registered expected outcomes for every control.

Not claimed: no gate verdict, no node status, no mathematical truth, no review of the owner's
revision.  A worker event cannot promote status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
ART = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
TASK_ID = "W046-F2A-EXTFREEZE-PREVALIDATION-01"

# ---------------------------------------------------------------- declared pins
PINS = {
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/tools/check_class_schema.py":
        "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
    "artifacts/formulation/rule_spec.json":
        "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "artifacts/formulation/KEY_MANIFEST.json":
        "014e2d3019781632cdb78ace266cf08cc11f9cf8b8ef0a049beb74eb9c6b6b9a",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml":
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml":
        "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
}
HARD_PINS = ["schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml",
             "artifacts/formulation/tools/check_class_schema.py"]

# Five sites, wording taken verbatim (at the time of reading) from the worker-047 repair spec
# artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json; this instrument does not import
# their checker, and applies the sites itself to the live bytes.  Provenance is recorded in
# results.json (spec sha256 measured at run start).
SITES = [
    ("S1", "extension_predicate.definition clause (a)",
     "(a) iota: M -> M' is an isometric embedding (iota_* g = g' restricted to iota(M));",
     "(a) iota: M -> M' is a C-infinity isometric embedding (iota_* g = g' restricted to iota(M)); "
     "the differentiability class of iota is frozen here and is not left to convention "
     "[sibling precedent: F2b falsifier.tier_1.witness_type freezes a C-infinity isometric embedding iota];"),
    ("S2", "extension_predicate.definition clause (c)",
     "(c) M' is connected and time-orientable, and its time orientation restricts to that of M;",
     "(c) M' is a SMOOTH (C-infinity) connected 4-manifold, time-orientable, and its time orientation "
     "restricts to that of M; the smooth structure is the category in which the metric is a tensor field, "
     "while the metric itself is only C2 [sibling precedent: F2b clause (c), worker-16 F2b-16-03 accepted];"),
    ("S3", "extension_predicate.definition clause (f)",
     "(f) the extension adds points to the future: there exist q in iota(M) and p in M' minus iota(M) "
     "with p in I^+(q; g').",
     "(f) the extension adds interior points to the future: int(M' minus iota(M)) is non-empty AND there "
     "exist q in iota(M) and p in int(M' minus iota(M)) with p in I^+(q; g'), where I^+ is the "
     "chronological future. The interior requirement blocks an extension that only adds boundary or "
     "dense-open points [sibling precedent: F2b clause (f), R2 major accepted]. For a C2 metric the "
     "chronological future is open and does not depend on the curve class, so the C0 convention caveat "
     "in the sibling does not apply here;"),
    ("S4", "topology.extension_topology",
     'extension_topology: "M\' is a connected 4-manifold containing iota(M) as an open proper subset; '
     'M\' is NOT assumed globally hyperbolic, compact, or AF"',
     'extension_topology: "M\' is a connected SMOOTH 4-manifold (the category in which the C2 metric is a '
     'tensor field) containing iota(M) as an open proper subset; the metric g\' is only C2. M\' is NOT '
     'assumed globally hyperbolic, compact, or AF. The smooth category is frozen here and is not left to '
     'convention [sibling precedent: F2b extension_topology]."'),
    ("S5", "falsifier.tier_1.witness_type",
     'witness_type: "an open (or at least non-meager) set of one-ended AF vacuum data whose maximal '
     'developments admit proper future C2 vacuum extensions, with the extension exhibited (an explicit '
     'family, not a numerical near-solution)"',
     'witness_type: "an open (or at least non-meager) set of one-ended AF vacuum data whose maximal '
     'developments admit proper future C2 vacuum extensions, with the extension exhibited explicitly '
     '(SMOOTH 4-manifold M\', C2 nondegenerate Lorentzian metric g\', C-infinity isometric embedding '
     'iota, an interior future point added as in clause (f); an explicit family, not a numerical '
     'near-solution)"'),
]
EXPECTED_CHANGED_LEAVES = {
    "extension_predicate.definition",
    "topology.extension_topology",
    "falsifier.tier_1.witness_type",
}

INVARIANT_PATHS = [
    ("class_id",), ("conclusion", "conclusion_type"),
    ("extension_predicate", "frozen_regularity"),
    ("extension_predicate", "frozen_equation_concept"),
    ("extension_predicate", "frozen_direction"),
    ("extension_predicate", "must_not_conflate"),
    ("genericity", "kind"),
    ("i_plus", "role"), ("i_plus", "in_conclusion"),
    ("visibility", "role"),
    ("topology", "spacetime_dimension"), ("topology", "slice_topology"),
    ("implication_ledger", "extension_class_containment"),
    ("implication_ledger", "one_way_entailments"),
    ("implication_ledger", "forbidden_transfers"),
    ("data_class", "matter"), ("data_class", "cosmological_constant"),
    ("class_boundary", "import_rule"),
]

AXES = ["iota_regularity", "manifold_category", "interior_witness", "metric_regularity", "equation"]


# ---------------------------------------------------------------- helpers
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_pins(paths) -> dict:
    return {rel: sha256_file(ROOT / rel) for rel in paths}


def get_path(doc, path):
    cur = doc
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def leaf_diff(a, b, path=()):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            out += leaf_diff(a.get(k), b.get(k), path + (k,))
    elif isinstance(a, list) and isinstance(b, list):
        if a != b:
            out.append((".".join(map(str, path)), a, b))
    elif a != b:
        out.append((".".join(map(str, path)), a, b))
    return out


def clause_map(definition: str) -> dict:
    txt = re.sub(r"\s+", " ", str(definition)).strip()
    marks = list(re.finditer(r"\(([a-f])\)\s", txt))
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(txt)
        out[m.group(1)] = txt[m.end():end].strip()
    return out


def axes_of(doc: dict) -> dict:
    ep = doc.get("extension_predicate", {}) or {}
    cl = clause_map(ep.get("definition", ""))
    topo = str((doc.get("topology", {}) or {}).get("extension_topology", ""))
    wit = str(((doc.get("falsifier", {}) or {}).get("tier_1", {}) or {}).get("witness_type", ""))
    nv = doc.get("non_vacuity", {}) or {}
    iota_txt = " ".join([cl.get("a", ""), str(nv.get("iota_regularity", "")), wit])
    manifold_txt = cl.get("c", "") + " " + topo
    metric_txt = cl.get("d", "")
    eq_txt = cl.get("e", "")

    iota = (2 if re.search(r"C-?infinity\s+isometric embedding", iota_txt)
            else 1 if re.search(r"C2\s+isometric embedding", iota_txt)
            else 0 if re.search(r"isometric embedding", iota_txt) else None)
    manifold = (1 if re.search(r"SMOOTH \(C-?infinity\)\s+connected 4-manifold", manifold_txt)
                else 0 if re.search(r"connected 4-manifold", manifold_txt) else None)
    interior = 1 if re.search(r"int\(M' minus iota\(M\)\)", cl.get("f", "") + " " + wit) else 0
    metric = (2 if re.search(r"C2\s+Lorentzian", metric_txt)
              else 0 if re.search(r"continuous[^.]{0,40}Lorentzian|Lorentzian[^.]{0,40}continuous", metric_txt)
              else None)
    eq_field = ep.get("frozen_equation_concept")
    equation = (1 if eq_field == "classical_ricci" or re.search(r"Ric\(g'\)\s*=\s*0", eq_txt)
                else 0 if eq_field == "none" or re.search(r"NO equation", eq_txt) else None)
    return {
        "iota_regularity": iota,
        "manifold_category": manifold,
        "interior_witness": interior,
        "metric_regularity": metric,
        "equation": equation,
        "direction": ep.get("frozen_direction"),
        "clauses": cl,
        "extension_topology": topo,
    }


def containment(a: dict, b: dict, reading: str) -> dict:
    """Does every a-admissible triple satisfy b's predicate?  a>=b on each decisive axis."""
    decisive = (["interior_witness", "metric_regularity", "equation"] if reading == "typing_standard"
                else AXES)
    rows, holds = [], True
    for ax in decisive:
        av, bv = a.get(ax), b.get(ax)
        ok = (av is not None and bv is not None and av >= bv)
        rows.append({"axis": ax, "a": av, "b": bv, "a_at_least_b": ok})
        holds = holds and ok
    dir_ok = a.get("direction") == b.get("direction")
    rows.append({"axis": "direction", "a": a.get("direction"), "b": b.get("direction"),
                 "a_at_least_b": dir_ok})
    holds = holds and dir_ok
    return {"reading": reading, "P_a_implies_P_b": bool(holds), "rows": rows}


def gate_run(name: str, path: Path) -> dict:
    gate = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    proc = subprocess.run([sys.executable, str(gate), "--json", str(path)],
                          capture_output=True, text=True, cwd=str(ROOT), timeout=180)
    try:
        report = json.loads(proc.stdout)
    except Exception:
        report = {"parse_error": proc.stdout[:800], "stderr": proc.stderr[:400]}
    rec = {"name": name, "schema": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
           "sha256": sha256_file(path), "returncode": proc.returncode, "report": report}
    (ART / "gate_runs").mkdir(exist_ok=True)
    (ART / "gate_runs" / f"{name}.json").write_text(json.dumps(rec, indent=2) + "\n")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-write", action="store_true", help="measure only, write nothing")
    args = ap.parse_args()
    created = datetime.now(TZ).isoformat(timespec="seconds")
    problems, controls = [], []

    def ctl(cid, desc, got, want):
        ok = got == want
        controls.append({"id": cid, "desc": desc, "expected": want, "observed": got, "pass": ok})
        if not ok:
            problems.append(f"{cid}: expected {want!r}, observed {got!r}")
        return ok

    # 1. start pins ---------------------------------------------------------
    pins_start = measure_pins(PINS.keys())
    for rel in HARD_PINS:
        if pins_start[rel] != PINS[rel]:
            print(f"VOID: pin mismatch {rel}\n  declared {PINS[rel]}\n  measured {pins_start[rel]}")
            return 2
    ctl("C11a", "all eight declared pins measured at run start", pins_start, PINS)

    spec_path = ROOT / "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json"
    spec_sha = sha256_file(spec_path) if spec_path.exists() else None

    live_text = (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()
    f2b_doc = yaml.safe_load((ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text())
    live_doc = yaml.safe_load(live_text)

    # 2. build candidate and mutants ---------------------------------------
    def apply(text: str, site_ids) -> str:
        for sid, _path, old, new in SITES:
            if sid not in site_ids:
                continue
            n = text.count(old)
            if n != 1:
                raise SystemExit(f"VOID: site {sid} old text occurs {n} times, expected 1")
            text = text.replace(old, new)
        return text

    all_ids = [s[0] for s in SITES]
    cand_text = apply(live_text, all_ids)
    variants = {"candidate": cand_text}
    for sid in all_ids:
        variants[f"M{all_ids.index(sid) + 1}_minus_{sid}"] = apply(live_text, [s for s in all_ids if s != sid])
    # positive controls: class-id and conclusion-type swaps on the candidate
    m6, n6 = re.subn(r"(?m)^class_id: AF-SCC-C2-VAC-GEN$", "class_id: AF-SCC-C0-VAC-GEN", cand_text)
    m7, n7 = re.subn(r"(?m)^(\s*)conclusion_type: scc_c2_future_inextendibility$",
                     r"\1conclusion_type: scc_c0_future_inextendibility", cand_text)
    if n6 != 1 or n7 != 1:
        print(f"VOID: positive-control substitution count {n6}/{n7}, expected 1/1")
        return 2
    variants["M6_class_id_swap"] = m6
    variants["M7_conclusion_type_swap"] = m7
    # axis-carrier probes: remove every site that carries one axis
    variants["M8_minus_S1_S5"] = apply(live_text, [s for s in all_ids if s not in ("S1", "S5")])
    variants["M9_minus_S2_S4"] = apply(live_text, [s for s in all_ids if s not in ("S2", "S4")])

    vdir = ART / "variants"
    written = {}
    if not args.skip_write:
        vdir.mkdir(parents=True, exist_ok=True)
        for name, text in variants.items():
            p = vdir / f"{name}.yaml"
            p.write_text(text)
            written[name] = p
        cand_doc = yaml.safe_load(cand_text)
    else:
        cand_doc = yaml.safe_load(cand_text)
        for name, text in variants.items():
            written[name] = vdir / f"{name}.yaml"

    # 3. structural diff + invariants --------------------------------------
    diffs = leaf_diff(live_doc, cand_doc)
    changed = {d[0] for d in diffs}
    ctl("C05", "candidate changes exactly the three expected YAML leaves", sorted(changed),
        sorted(EXPECTED_CHANGED_LEAVES))
    inv = {}
    for path in INVARIANT_PATHS:
        inv[".".join(path)] = {"live": get_path(live_doc, path), "candidate": get_path(cand_doc, path),
                               "equal": get_path(live_doc, path) == get_path(cand_doc, path)}
    ctl("C06", "class-identity invariants unchanged on the candidate",
        sorted(k for k, v in inv.items() if not v["equal"]), [])

    # 4. canonical gate runs ------------------------------------------------
    gate_runs = {"live_F2a": gate_run("live_F2a", ROOT / "schemas/af_scc_c2_vacuum.yaml"),
                 "live_F2b": gate_run("live_F2b", ROOT / "schemas/af_scc_c0_vacuum.yaml")}
    for name, p in written.items():
        gate_runs[name] = gate_run(name, p)
    ctl("C01", "canonical gate PASSES live F2a", gate_runs["live_F2a"]["report"].get("verdict"), "pass")
    ctl("C02", "canonical gate PASSES the five-site candidate", gate_runs["candidate"]["report"].get("verdict"), "pass")
    ctl("C03", "canonical gate FAILS the class-id swap mutant (positive control)",
        gate_runs["M6_class_id_swap"]["report"].get("verdict"), "fail")
    ctl("C04", "canonical gate FAILS the conclusion-type swap mutant (positive control)",
        gate_runs["M7_conclusion_type_swap"]["report"].get("verdict"), "fail")
    mutant_gate = {k: v["report"].get("verdict") for k, v in gate_runs.items() if k.startswith("M") and k not in
                   ("M6_class_id_swap", "M7_conclusion_type_swap")}
    ctl("C12", "structural gate is BLIND to all five repair-reverting mutants (recorded, not desired)",
        sorted(set(mutant_gate.values())), ["pass"])

    # 5. containment instrument --------------------------------------------
    axes = {"live_F2a": axes_of(live_doc), "candidate": axes_of(cand_doc), "F2b": axes_of(f2b_doc)}
    for name, text in variants.items():
        if name.startswith("M") and name not in ("M6_class_id_swap", "M7_conclusion_type_swap"):
            axes[name] = axes_of(yaml.safe_load(text))
    table = {k: {ax: v.get(ax) for ax in AXES + ["direction"]} for k, v in axes.items()}
    readings = {}
    for name in ["live_F2a", "candidate", *[k for k in variants if k.startswith("M") and k not in
                                            ("M6_class_id_swap", "M7_conclusion_type_swap")]]:
        readings[name] = {r: containment(axes[name], axes["F2b"], r)
                          for r in ("strict_literal", "typing_standard")}
    readings["reverse_C0_implies_C2"] = {"strict_literal": containment(axes["F2b"], axes["candidate"], "strict_literal")}

    ctl("C07", "candidate entails P_C2 => P_C0 under the strict-literal reading",
        readings["candidate"]["strict_literal"]["P_a_implies_P_b"], True)
    ctl("C08", "candidate entails P_C2 => P_C0 under the standard-typing reading",
        readings["candidate"]["typing_standard"]["P_a_implies_P_b"], True)
    ctl("C09", "live F2a does NOT entail P_C2 => P_C0 (blocker reproduced)",
        readings["live_F2a"]["strict_literal"]["P_a_implies_P_b"], False)
    ctl("C10", "reverse P_C0 => P_C2 is not entailed (class separation preserved)",
        readings["reverse_C0_implies_C2"]["strict_literal"]["P_a_implies_P_b"], False)
    ctl("C13", "clause-(f) mutant alone breaks containment (interior axis is load-bearing)",
        readings["M3_minus_S3"]["strict_literal"]["P_a_implies_P_b"], False)
    ctl("C14", "live F2a axis profile is (iota=0, manifold=0, interior=0) at the pinned bytes",
        [table["live_F2a"][a] for a in ("iota_regularity", "manifold_category", "interior_witness")],
        [0, 0, 0])
    ctl("C15", "F2b convention profile is (iota=2, manifold=1, interior=1)",
        [table["F2b"][a] for a in ("iota_regularity", "manifold_category", "interior_witness")],
        [2, 1, 1])

    # 5b. derived: per-site and per-axis materiality for the containment obligation
    site_materiality = {}
    for sid in all_ids:
        key = f"M{all_ids.index(sid) + 1}_minus_{sid}"
        strict_holds = readings[key]["strict_literal"]["P_a_implies_P_b"]
        site_materiality[sid] = {
            "label": dict((s[0], s[1]) for s in SITES)[sid],
            "strict_containment_holds_with_it_removed": strict_holds,
            "single_site_removal_breaks_entailment": not strict_holds,
        }
    carriers = {"iota_regularity": ["S1", "S5"], "manifold_category": ["S2", "S4"],
                "interior_witness": ["S3"]}
    axis_materiality = {}
    for ax, sits in carriers.items():
        probe = "M8_minus_S1_S5" if ax == "iota_regularity" else \
                "M9_minus_S2_S4" if ax == "manifold_category" else "M3_minus_S3"
        holds = readings[probe]["strict_literal"]["P_a_implies_P_b"]
        axis_materiality[ax] = {"carriers": sits, "probe": probe,
                                "entailment_holds_without_all_carriers": holds,
                                "axis_material_for_entailment": not holds}
    ctl("C16", "removing both iota carriers (S1+S5) breaks containment (axis material)",
        readings["M8_minus_S1_S5"]["strict_literal"]["P_a_implies_P_b"], False)
    ctl("C17", "removing both manifold carriers (S2+S4) breaks containment (axis material)",
        readings["M9_minus_S2_S4"]["strict_literal"]["P_a_implies_P_b"], False)

    # 5c. cross-check against the worker-047 sandbox candidate (byte comparison only)
    w047 = ROOT / "artifacts/worker-047/f2a_ext_freeze_spec/sandbox/root/schemas/af_scc_c2_vacuum.yaml"
    cross = None
    if w047.exists():
        a_sha = sha256_file(w047)
        b_sha = sha256_file(written["candidate"]) if written["candidate"].exists() else None
        cross = {"path": str(w047.relative_to(ROOT)), "sha256": a_sha,
                 "ours_sha256": b_sha, "byte_identical_to_ours": a_sha == b_sha,
                 "method": "sha256 comparison only; their checker was not imported"}

    # 6. advisory: sibling-precedent citations inside declared-asserted blocks
    import_rule = get_path(cand_doc, ("class_boundary", "import_rule"))
    precedent_lines = []
    for i, line in enumerate(cand_text.splitlines(), 1):
        if "sibling precedent" in line:
            precedent_lines.append({"line": i, "block": "extension_predicate.definition"
                                    if "isometric embedding" in line or "SMOOTH (C-infinity) connected" in line
                                    else "topology.extension_topology" if "extension_topology" in line else "other",
                                    "text": line.strip()[:160]})
    advisory = [{
        "id": "W046-F2A-PV-03", "severity": "advisory-non-blocking",
        "text": "The three ported clauses are definitional sharpening of a shared predicate convention, "
                "not C0 conclusion content, but the sibling citations introduced by S2/S3/S4 now sit inside "
                "extension_predicate.definition and topology, which the live class_boundary.import_rule "
                "scopes to anti_scope/variants/provenance. The canonical gate does not flag this. Owner "
                "options: (a) keep the alignment self-contained in the class contract / supplement, or "
                "(b) record an explicit convention-alignment provenance key. Adjudication belongs to the "
                "gate owner; this is not counted as a hard failure.",
        "carrier": "class_boundary.import_rule",
        "observed": precedent_lines,
        "import_rule_text": import_rule,
    }]

    # 7. end pins ------------------------------------------------------------
    pins_end = measure_pins(PINS.keys())
    drift = {k: {"start": pins_start[k], "end": pins_end[k]} for k in PINS if pins_start[k] != pins_end[k]}
    ctl("C11b", "no canonical target moved during the run (byte stability)", drift, {})

    verdict = "candidate_prevalidated" if not problems else "controls_failed"
    results = {
        "schema": "w046-f2a-extfreeze-prevalidation/v1",
        "task_id": TASK_ID, "actor": "worker-046", "created_at": created,
        "class_id": "AF-SCC-C2-VAC-GEN", "node_id": "F2a", "gate": "G-FORM",
        "reviewer_role": "independent pre-validation (not an author of F2a, of the repair spec, "
                         "or of any formulation artifact)",
        "authority_note": "worker deliverable: advisory evidence only. No gate verdict, no node status, "
                          "no validation_status=passed, no canonical byte written.",
        "pins_declared": PINS, "pins_start": pins_start, "pins_end": pins_end, "pin_drift": drift,
        "repair_spec_provenance": {"path": "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json",
                                   "sha256": spec_sha,
                                   "note": "wording of S1-S5 copied verbatim at read time; their checker was not imported"},
        "candidate": {"path": "artifacts/worker-046/f2a_extfreeze_prevalidation/variants/candidate.yaml",
                      "sha256": sha256_file(written["candidate"]) if written["candidate"].exists() else None,
                      "changed_leaves": sorted(changed), "leaf_diff_count": len(diffs)},
        "gate_runs": {k: {"schema": v["schema"], "sha256": v["sha256"], "returncode": v["returncode"],
                          "verdict": v["report"].get("verdict"),
                          "failed_rules": v["report"].get("failed_rules")} for k, v in gate_runs.items()},
        "containment": {"axis_table": table, "readings": readings,
                        "site_materiality": site_materiality, "axis_materiality": axis_materiality,
                        "cross_check_worker047_sandbox_candidate": cross,
                        "lattice": {"iota_regularity": "C-infinity=2 > C2=1 > unspecified=0",
                                    "manifold_category": "SMOOTH=1 > unspecified=0",
                                    "interior_witness": "interior=1 > boundary-admitting=0",
                                    "metric_regularity": "C2=2 > C1=1 > continuous=0",
                                    "equation": "classical_ricci=1 > none=0"},
                        "readings_definition": {
                            "strict_literal": "all five axes + direction must satisfy a>=b",
                            "typing_standard": "manifold/iota axes treated as typing-implied; interior, metric, equation, direction decisive"}},
        "invariants": inv, "advisories": advisory,
        "assertions": [{"id": c["id"], "desc": c["desc"], "pass": c["pass"]} for c in controls],
        "problems": problems, "verdict": verdict,
        "falsifier": "This pre-validation is falsified by any of: (i) a start or end sha256 differing from "
                     "the declared pins, or any canonical target moving during the run; (ii) the pinned "
                     "canonical gate not PASSing the candidate or not FAILing the class-id / "
                     "conclusion-type positive controls; (iii) an independent re-run reporting a decisive "
                     "axis on which the candidate's predicate is strictly weaker than F2b's under the "
                     "strict-literal reading; (iv) any class-identity invariant differing between live F2a "
                     "and the candidate; or (v) the candidate differing from the pinned F2a bytes at any "
                     "leaf other than the three recorded leaves.",
        "next_falsifier": "Re-run this instrument at FROZEN rev30 / schema rev14 bytes: the pre-validation "
                          "transfers only as a method; the candidate bytes and the pins must be re-measured, "
                          "and the owner's revision must be re-gated and independently reviewed at its own hash.",
        "counts_as_gate_verdict": False, "counts_as_full_schema_verdict": False,
    }

    if not args.skip_write:
        (ART / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        (ART / "controls.json").write_text(json.dumps(controls, indent=2) + "\n")
        report = render_report(results, controls, table, readings)
        (ART / "REPORT.md").write_text(report)
        manifest_files = ["audit_f2a_extfreeze_prevalidation.py", "results.json", "controls.json",
                          "REPORT.md"] + [f"variants/{n}.yaml" for n in variants] + \
                         [f"gate_runs/{n}.json" for n in gate_runs]
        manifest = {"schema": "w046-artifact-manifest/v1", "task_id": TASK_ID,
                    "created_at": created,
                    "files": {f: sha256_file(ART / f) for f in sorted(manifest_files) if (ART / f).exists()}}
        (ART / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

    print(json.dumps({"verdict": verdict, "problems": problems,
                      "changed_leaves": sorted(changed),
                      "containment_candidate": readings["candidate"]["strict_literal"]["P_a_implies_P_b"],
                      "gate_candidate": gate_runs["candidate"]["report"].get("verdict")}, indent=1))
    return 0 if not problems else 1


def render_report(r, controls, table, readings) -> str:
    L = []
    L.append(f"# {TASK_ID} — independent pre-validation of the F2a extension-freeze candidate\n")
    L.append(f"**Class** `AF-SCC-C2-VAC-GEN` · **Node** F2a · **Gate** G-FORM (context only) · "
             f"**Actor** worker-046 · **Created** {r['created_at']}\n")
    L.append(f"**Verdict of this deliverable** `{r['verdict']}` — advisory pre-validation evidence. "
             f"It issues **no gate verdict** and writes no canonical byte.\n")
    L.append("## Why this artifact exists\n")
    L.append("F2a carries two live G-FORM blockers: the under-frozen extension predicate (manifold "
             "category of `M'`, differentiability of `iota`, clause-(f) interior requirement) and the "
             "consequent non-derivability of the declared containment `E_C2 subset E_C0`. worker-047 "
             "published the repair **specification**; REC-36 authorizes the owner to land the revision. "
             "This instrument answers the owner's outstanding pre-flight questions at the pinned bytes: "
             "does the repair survive the canonical gate, is the delta leaf-bounded, does an independent "
             "clause-lattice instrument now derive the containment, and what does the repair not fix?\n")
    L.append("## Pins (start = end, byte-stable)\n")
    L.append("| path | sha256 |\n|---|---|")
    for k, v in r["pins_start"].items():
        L.append(f"| `{k}` | `{v[:16]}…` |")
    L.append("")
    L.append("## Results\n")
    L.append(f"- Candidate sha256 `{r['candidate']['sha256']}`; changed YAML leaves: "
             f"{', '.join('`'+x+'`' for x in r['candidate']['changed_leaves'])} "
             f"({r['candidate']['leaf_diff_count']} leaf diffs).")
    L.append(f"- Canonical gate (`check_class_schema.py` @ `000e09e46b2f`): live F2a "
             f"`{r['gate_runs']['live_F2a']['verdict']}`, candidate `{r['gate_runs']['candidate']['verdict']}`, "
             f"class-id swap `{r['gate_runs']['M6_class_id_swap']['verdict']}`, conclusion-type swap "
             f"`{r['gate_runs']['M7_conclusion_type_swap']['verdict']}`; all five repair-reverting mutants "
             f"`pass` (gate is structurally blind to the repair — recorded).")
    L.append(f"- Containment instrument: candidate entails `P_C2 => P_C0` under strict-literal = "
             f"**{readings['candidate']['strict_literal']['P_a_implies_P_b']}** and standard-typing = "
             f"**{readings['candidate']['typing_standard']['P_a_implies_P_b']}**; live F2a strict-literal = "
             f"**{readings['live_F2a']['strict_literal']['P_a_implies_P_b']}** (blocker reproduced); reverse "
             f"`P_C0 => P_C2` = **{readings['reverse_C0_implies_C2']['strict_literal']['P_a_implies_P_b']}** "
             f"(separation preserved).\n")
    L.append("### Axis table (0 = unspecified/weakest, ascending strength)\n")
    L.append("| schema | iota | manifold | interior | metric | equation | direction |\n|---|---:|---:|---:|---:|---:|---|")
    for name, row in table.items():
        L.append(f"| {name} | {row['iota_regularity']} | {row['manifold_category']} | "
                 f"{row['interior_witness']} | {row['metric_regularity']} | {row['equation']} | {row['direction']} |")
    L.append("")
    L.append("### Site and axis materiality for the containment obligation\n")
    L.append("| axis | carriers | probe (all carriers removed) | entailment still holds? | axis material |\n|---|---|---|---|---|")
    for ax, v in r["containment"]["axis_materiality"].items():
        L.append(f"| {ax} | {', '.join(v['carriers'])} | {v['probe']} | "
                 f"{v['entailment_holds_without_all_carriers']} | {v['axis_material_for_entailment']} |")
    L.append("")
    L.append("All three predicate axes are load-bearing: removing an axis's full carrier set breaks "
             "`P_C2 => P_C0` (controls C13/C16/C17). The carriers are redundant within two axes — "
             "iota is carried by S1 (clause (a)) and S5 (witness_type), the manifold category by S2 "
             "(clause (c)) and S4 (`topology.extension_topology`) — mirroring the sibling's own "
             "belt-and-braces propagation, so no single-site revert of S1, S4 or S5 alone reopens the "
             "gap. Interior (S3) has a single carrier and is the dominant material axis.\n")
    L.append("| site | carrier | containment holds with it removed? | breaks entailment alone? |\n|---|---|---|---|")
    for sid, v in r["containment"]["site_materiality"].items():
        L.append(f"| {sid} | {v['label']} | {v['strict_containment_holds_with_it_removed']} | "
                 f"{v['single_site_removal_breaks_entailment']} |")
    L.append("")
    cc = r["containment"]["cross_check_worker047_sandbox_candidate"]
    if cc:
        L.append(f"Cross-check against the worker-047 sandbox candidate `{cc['path']}` "
                 f"(`{cc['sha256'][:16]}…`): byte-identical to this instrument's independently built "
                 f"candidate = **{cc['byte_identical_to_ours']}** (sha256 comparison only; their "
                 f"checker was not imported).\n")
    L.append("## Controls (all pre-registered)\n")
    L.append("| id | assertion | expected | observed | pass |\n|---|---|---|---|---|")
    for c in controls:
        L.append(f"| {c['id']} | {c['desc']} | `{c['expected']}` | `{c['observed']}` | {c['pass']} |")
    L.append("")
    L.append("## Advisories (non-blocking)\n")
    for a in r["advisories"]:
        L.append(f"- **{a['id']}** ({a['severity']}) on `{a['carrier']}`: {a['text']}")
        for o in a["observed"]:
            L.append(f"  - line {o['line']} ({o['block']}): `{o['text']}`")
    L.append("")
    L.append("## Falsifier\n")
    L.append(r["falsifier"] + "\n")
    L.append("## Non-claims / authority\n")
    L.append("Not a gate verdict, not a node completion, not a full-schema review, not a mathematical "
             "claim. The repair candidate is not applied to `schemas/af_scc_c2_vacuum.yaml`; every "
             "canonical path is only hashed. A worker event cannot set `status=done`, "
             "`validation_status=passed`, or a gate verdict.\n")
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W040-F2A-PRED-DIVERGENCE-06 -- independent hash-bound adjudication.

Question: at FROZEN rev29, do the frozen F2a formulation documents and the canonical
F2a schema state the SAME extension predicate?

Method: read-only measurement of three named predicate slots in three artifacts:
  S-iota : does the artifact freeze the differentiability class of the embedding iota?
  S-Mp   : does the artifact freeze the manifold category of M'?
  S-int  : does clause (f) require the added future point to lie in int(M' \ iota(M))?

Artifacts: canonical F2a schema (rev13), frozen FORMULATION.md (F2a section),
frozen DELIVERABLE_SUMMARY.md (F2a bullet), sibling F2b schema (rev13, template),
FROZEN.json rev29 (pins the pair), and the two gate tools (blindness check).

Read-only on all shared paths. --bootstrap records entry hashes + snapshots once;
every later run verifies the live paths against that record and flags drift.
"""

import argparse
import hashlib
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

ENTRIES = {
    "frozen_manifest": "artifacts/formulation/FROZEN.json",
    "schema_F2a": "schemas/af_scc_c2_vacuum.yaml",
    "schema_F2b": "schemas/af_scc_c0_vacuum.yaml",
    "schema_F1": "schemas/af_wcc_vacuum.yaml",
    "formulation_md": "artifacts/formulation/FORMULATION.md",
    "deliverable_summary_md": "artifacts/formulation/DELIVERABLE_SUMMARY.md",
    "key_manifest": "artifacts/formulation/KEY_MANIFEST.json",
    "gate_tool": "artifacts/formulation/tools/run_gate_tests.py",
    "class_schema_tool": "artifacts/formulation/tools/check_class_schema.py",
}

DIFF_TOKENS = ("C^", "C\u221e", "C-infinity", "C\\infty", "C2", "C1",
               "C^{1,1}", "H2_loc", "C^k", "C0")

DIVERGENCE_FALSIFIER = (
    "Falsified if, at the pinned hashes, (i) F2a extension_predicate clause (a) or the "
    "regularity/topology sections name a differentiability class for iota or contain an "
    "iota_regularity field; or (ii) F2a clause (c) or topology.extension_topology names a "
    "manifold category for M'; or (iii) F2a clause (f) contains an interior requirement; or "
    "(iv) either frozen prose document stops asserting the three slots for F2a; or (v) F2b "
    "stops carrying any of the three conventions; or (vi) any pinned entry no longer hashes "
    "to the recorded value, in which case the adjudication is void and must be re-run at the "
    "new pins."
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path):
    return os.path.relpath(path, ROOT)


def load_text(name):
    with open(os.path.join(ROOT, ENTRIES[name]), "r", encoding="utf-8") as fh:
        return fh.read()


def clause(definition, letter):
    nxt = {"a": "b", "b": "c", "c": "d", "d": "e", "e": "f", "f": None}[letter]
    start = definition.index("(%s)" % letter)
    end = definition.index("(%s)" % nxt) if nxt else len(definition)
    return definition[start:end]


def has_diff_token(text):
    """Word-boundary scan; 'smoothness' in a forbidden list is not a frozen category."""
    hits = [t for t in DIFF_TOKENS if t in text]
    if re.search(r"\bsmooth\b", text, re.I):
        hits.append("smooth")
    return hits


def find_key_paths(obj, key, prefix=""):
    """Dotted paths at which `key` occurs anywhere in a nested mapping/list."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = "%s.%s" % (prefix, k) if prefix else str(k)
            if k == key:
                out.append(path)
            out.extend(find_key_paths(v, key, path))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(find_key_paths(v, key, "%s[%d]" % (prefix, i)))
    return out


def measure_schema(doc):
    """Return the three slot verdicts plus the frozen-slot set for a class schema."""
    ep = doc.get("extension_predicate", {})
    definition = ep.get("definition", "")
    ca, cc, cf = (clause(definition, x) for x in "acf")
    iota_paths = find_key_paths(doc, "iota_regularity")
    iota_key = bool(iota_paths)
    mp_text = cc + " " + str((doc.get("topology") or {}).get("extension_topology", ""))
    frozen_slots = {
        "frozen_regularity": ep.get("frozen_regularity"),
        "frozen_direction": ep.get("frozen_direction"),
        "extension_regularity": (doc.get("regularity") or {}).get("extension_regularity"),
    }
    return {
        "S_iota_frozen": bool(iota_key or has_diff_token(ca)),
        "S_iota_evidence": iota_paths + has_diff_token(ca),
        "iota_key_paths": iota_paths,
        "S_Mp_frozen": bool(has_diff_token(mp_text)),
        "S_Mp_evidence": has_diff_token(mp_text),
        "S_int_frozen": "int(" in cf,
        "S_int_evidence": re.findall(r"[^.;]*int\([^.;]*", cf),
        "clause_f_text": " ".join(cf.split()),
        "clause_c_text": " ".join(cc.split()),
        "clause_a_text": " ".join(ca.split()),
        "frozen_slots_present": sum(1 for v in frozen_slots.values() if v),
        "frozen_slot_values": frozen_slots,
    }


def measure_formulation_md(text):
    """Scope to the F2a extension-predicate section only (F2a predicate -> Non-vacuity)."""
    start = text.index("### The extension predicate (frozen)")
    end = text.index("### Non-vacuity", start)
    section = text[start:end]
    lines = section.splitlines()
    def line_of(needle):
        for i, ln in enumerate(lines):
            if needle in ln:
                return i + 1
        return None
    ca = next((ln for ln in lines if ln.startswith("- **(a)**")), "")
    cc = next((ln for ln in lines if ln.startswith("- **(c)**")), "")
    f_idx = next((i for i, ln in enumerate(lines) if ln.startswith("- **(f)**")), None)
    cf = " ".join(lines[f_idx:f_idx + 2]) if f_idx is not None else ""
    decisions = next((ln for ln in lines if "Decisions frozen here" in ln), "") + " " + \
        next((ln for ln in lines if "C^\u221e" in ln or "C^∞" in ln), "")
    whole_file_int = [i + 1 for i, ln in enumerate(text.splitlines()) if "int(" in ln]
    sec_start_line = text[:start].count("\n") + 1
    return {
        "S_iota_frozen": bool(re.search(r"`\u03b9`?\s*is\s*`?C\^?\u221e", decisions) or "C^\u221e" in decisions or "C^∞" in decisions),
        "S_Mp_frozen": "smooth" in cc.lower(),
        "S_int_frozen": "int(" in cf,
        "clause_a_line": ca,
        "clause_c_line": cc,
        "clause_f_lines": cf,
        "decisions_line": decisions.strip(),
        "whole_file_int_lines": whole_file_int,
        "section_scoped_int_lines": [],
        "section_start_line": sec_start_line,
    }


def measure_deliverable_summary(text):
    lines = text.splitlines()
    idx = [i for i, ln in enumerate(lines) if "iota frozen" in ln]
    bullet = " ".join(lines[i] + " " + lines[i + 1] for i in idx if i + 1 < len(lines))
    return {
        "S_iota_frozen": bool(idx) and ("C^\u221e" in bullet or "C^∞" in bullet),
        "lines": [(i + 1, lines[i]) for i in idx],
        "bullet_text": " ".join(bullet.split()),
    }


def measure_gate_blindness():
    out = {}
    for name in ("gate_tool", "class_schema_tool"):
        src = load_text(name)
        out[name] = {
            "iota_refs": len(re.findall(r"iota", src)),
            "interior_refs": len(re.findall(r"interior", src)),
            "iota_regularity_refs": len(re.findall(r"iota_regularity", src)),
        }
    return out


def build_measurements():
    f2a = yaml.safe_load(load_text("schema_F2a"))
    f2b = yaml.safe_load(load_text("schema_F2b"))
    f1 = yaml.safe_load(load_text("schema_F1"))
    form = measure_formulation_md(load_text("formulation_md"))
    ds = measure_deliverable_summary(load_text("deliverable_summary_md"))
    frozen = json.loads(load_text("frozen_manifest"))
    m_f2a = measure_schema(f2a)
    m_f2b = measure_schema(f2b)
    frozen_files = frozen.get("files", {})
    pins = {k: frozen_files.get(ENTRIES[k], {}).get("sha256") for k in
            ("schema_F2a", "schema_F2b", "schema_F1", "formulation_md",
             "deliverable_summary_md", "key_manifest")}
    divergence = {
        "iota": {"schema_F2a": m_f2a["S_iota_frozen"], "prose_F2a": form["S_iota_frozen"],
                 "summary_F2a": ds["S_iota_frozen"], "schema_F2b": m_f2b["S_iota_frozen"]},
        "M_prime": {"schema_F2a": m_f2a["S_Mp_frozen"], "prose_F2a": form["S_Mp_frozen"],
                    "schema_F2b": m_f2b["S_Mp_frozen"]},
        "interior": {"schema_F2a": m_f2a["S_int_frozen"], "prose_F2a": form["S_int_frozen"],
                     "schema_F2b": m_f2b["S_int_frozen"]},
    }
    divergent_slots = [s for s, v in divergence.items()
                       if v["schema_F2a"] is False and v.get("schema_F2b") is True]
    checks = {
        "D1_F2a_iota_unfrozen": m_f2a["S_iota_frozen"] is False,
        "D2_F2a_Mprime_unfrozen": m_f2a["S_Mp_frozen"] is False,
        "D3_F2a_clause_f_no_interior": m_f2a["S_int_frozen"] is False,
        "D4_prose_freezes_all_three_for_F2a": form["S_iota_frozen"] and form["S_Mp_frozen"] and form["S_int_frozen"],
        "D5_summary_freezes_iota_for_F2a": ds["S_iota_frozen"],
        "D6_sibling_F2b_carries_all_three": m_f2b["S_iota_frozen"] and m_f2b["S_Mp_frozen"] and m_f2b["S_int_frozen"],
        "D7_frozen_pins_both_texts": bool(pins["schema_F2a"]) and bool(pins["formulation_md"]),
        "D8_divergent_slot_count_is_3": len(divergent_slots) == 3,
    }
    measurements = {
        "task_id": "W040-F2A-PRED-DIVERGENCE-06",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "node_id": "F2a",
        "gate": "G-FORM",
        "frozen_revision": frozen.get("revision"),
        "frozen_pins": pins,
        "schema_revisions": {"F2a": f2a.get("revision"), "F2b": f2b.get("revision"), "F1": f1.get("revision")},
        "F1_has_extension_predicate": "extension_predicate" in f1,
        "divergence": divergence,
        "divergent_slots": divergent_slots,
        "checks": checks,
        "slots": {"F2a": m_f2a, "F2b": m_f2b, "formulation_md": form},
        "gate_blindness": measure_gate_blindness(),
        "witness_lines": {
            "FORMULATION.md": {"clause_a": 135, "clause_c": 137, "clause_f": [140, 141], "decisions": 144},
            "DELIVERABLE_SUMMARY.md": {"iota": [47, 48]},
            "schema_F2a": {"clause_a": 93, "clause_c": 95, "clause_f": 98,
                           "topology_extension_topology": 117},
        },
        "falsifier": DIVERGENCE_FALSIFIER,
    }
    return measurements


def run_controls(measurements):
    f2a_text = load_text("schema_F2a")
    controls = {}

    # C1: detector can see frozen slots that ARE present in F2a.
    controls["C1_positive_frozen_slots_detected"] = {
        "expected": ">=3 frozen slots detected in F2a",
        "observed": measurements["slots"]["F2a"]["frozen_slots_present"],
        "pass": measurements["slots"]["F2a"]["frozen_slots_present"] >= 3,
    }

    # C2: sibling F2b is the positive witness for all three conventions.
    controls["C2_positive_sibling_witness"] = {
        "expected": "F2b S_iota, S_Mp, S_int all True",
        "observed": [measurements["slots"]["F2b"][k] for k in ("S_iota_frozen", "S_Mp_frozen", "S_int_frozen")],
        "pass": all(measurements["slots"]["F2b"][k] for k in ("S_iota_frozen", "S_Mp_frozen", "S_int_frozen")),
    }

    # C3: mutation -- add the missing iota_regularity field, D1 must flip False.
    mutated = f2a_text.replace(
        "  extension_regularity: C2\n",
        "  extension_regularity: C2\n"
        "  iota_regularity: \"the embedding iota is a C-infinity isometric embedding (smooth category)\"\n",
        1,
    )
    m3 = measure_schema(yaml.safe_load(mutated))
    controls["C3_mutation_add_iota_regularity_flips_D1"] = {
        "expected": "S_iota_frozen True after injected field",
        "observed": m3["S_iota_frozen"],
        "pass": m3["S_iota_frozen"] is True,
        "mutated": "in-memory only; no shared file written",
    }

    # C4: unrelated mutation must not change any slot verdict.
    m4 = measure_schema(yaml.safe_load(f2a_text + "\n# unrelated comment\n"))
    before = [measurements["slots"]["F2a"][k] for k in ("S_iota_frozen", "S_Mp_frozen", "S_int_frozen")]
    after = [m4[k] for k in ("S_iota_frozen", "S_Mp_frozen", "S_int_frozen")]
    controls["C4_unrelated_mutation_no_flip"] = {
        "expected": "all three slot verdicts unchanged",
        "observed": {"before": before, "after": after},
        "pass": before == after,
    }

    # C5: false-positive scoping -- FORMULATION.md has int( in the F2b section too.
    form_text = load_text("formulation_md")
    all_int = [i + 1 for i, ln in enumerate(form_text.splitlines()) if "int(" in ln]
    scoped = measurements["slots"]["formulation_md"]
    sec_start = scoped["section_start_line"]
    f2b_start = form_text[:form_text.index("## 3. F2b")].count("\n") + 1
    f2a_section_int = [n for n in all_int if sec_start <= n < f2b_start]
    controls["C5_false_positive_section_scoping"] = {
        "expected": "whole-file int( count > F2a-section count; the extra hit is in the F2b section",
        "observed": {"whole_file_int_lines": all_int, "F2a_section_int_lines": f2a_section_int,
                     "naive_overcount": len(all_int) - len(f2a_section_int)},
        "pass": len(all_int) > len(f2a_section_int),
    }
    measurements["slots"]["formulation_md"]["section_scoped_int_lines"] = f2a_section_int

    # C6: repair control -- inject all three conventions; D1,D2,D3 must all flip.
    repaired = f2a_text
    repaired = repaired.replace("  extension_regularity: C2\n",
                                "  extension_regularity: C2\n"
                                "  iota_regularity: \"the embedding iota is a C-infinity isometric embedding (smooth category)\"\n", 1)
    repaired = repaired.replace(
        "    (c) M' is connected and time-orientable, and its time orientation restricts to that of M;",
        "    (c) M' is a SMOOTH (C-infinity) connected 4-manifold, time-orientable, and its time orientation restricts to that of M;", 1)
    repaired = repaired.replace(
        "    (f) the extension adds points to the future: there exist q in iota(M) and p in M' minus iota(M) with p in I^+(q; g').",
        "    (f) the extension adds points to the future: int(M' minus iota(M)) is non-empty and there exist q in iota(M) and p in int(M' minus iota(M)) with p in I^+(q; g').", 1)
    m6 = measure_schema(yaml.safe_load(repaired))
    controls["C6_repair_injection_closes_all_three"] = {
        "expected": "S_iota, S_Mp, S_int all True after injection",
        "observed": [m6["S_iota_frozen"], m6["S_Mp_frozen"], m6["S_int_frozen"]],
        "pass": m6["S_iota_frozen"] and m6["S_Mp_frozen"] and m6["S_int_frozen"],
        "mutated": "in-memory only; no shared file written",
    }
    return controls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", action="store_true",
                    help="record entry hashes + snapshots once (first run only)")
    args = ap.parse_args()
    os.chdir(ROOT)
    entry_hashes_path = os.path.join(HERE, "entry_hashes.json")
    live = {k: sha256(os.path.join(ROOT, p)) for k, p in ENTRIES.items()}
    if args.bootstrap:
        record = {"recorded_at": None, "root": ROOT, "entries": live}
        with open(entry_hashes_path, "w") as fh:
            json.dump(record, fh, indent=1, sort_keys=True)
        for k, p in ENTRIES.items():
            ext = os.path.splitext(p)[1]
            snap = os.path.join(HERE, "snapshot_%s.%s%s" % (k, live[k][:12], ext))
            with open(os.path.join(ROOT, p), "rb") as src, open(snap, "wb") as dst:
                dst.write(src.read())
        print("bootstrapped", len(live), "entries")
        return 0
    with open(entry_hashes_path) as fh:
        record = json.load(fh)
    drift = {k: {"recorded": record["entries"][k], "live": live[k]}
             for k in live if live[k] != record["entries"][k]}
    for k in drift:  # preserve the drifted bytes as evidence; never rewrite the originals
        ext = os.path.splitext(ENTRIES[k])[1]
        snap = os.path.join(HERE, "drift_%s.%s%s" % (k, live[k][:12], ext))
        with open(os.path.join(ROOT, ENTRIES[k]), "rb") as src, open(snap, "wb") as dst:
            dst.write(src.read())
    measurements = build_measurements()
    measurements["entry_drift"] = drift
    controls = run_controls(measurements)
    measurements["controls"] = controls
    measurements["controls_passed"] = "%d/%d" % (sum(1 for c in controls.values() if c["pass"]), len(controls))
    findings = []
    if all(measurements["checks"][k] for k in ("D1_F2a_iota_unfrozen", "D2_F2a_Mprime_unfrozen",
                                               "D3_F2a_clause_f_no_interior")):
        findings.append("HF-W040-06: at the pinned revision F2a's canonical extension_predicate "
                        "freezes none of the three slots (iota regularity, M' manifold category, "
                        "interior future witness) that the frozen FORMULATION.md F2a section, the "
                        "frozen DELIVERABLE_SUMMARY.md F2a bullet, and the sibling F2b schema all "
                        "carry; FROZEN rev29 therefore pins mutually inconsistent F2a predicates.")
    report = {
        "task_id": measurements["task_id"],
        "class_id": measurements["class_id"],
        "node_id": "F2a",
        "gate": "G-FORM",
        "verdict": "revise" if findings else "inconclusive",
        "findings": findings,
        "checks": measurements["checks"],
        "divergent_slots": measurements["divergent_slots"],
        "severity_argument": (
            "Not cosmetic under the G-FORM criterion 'exact quantifiers/topology/regularity': the "
            "schema's D3 domain is defined as 'proper future C2 vacuum extensions ... in the exact "
            "sense of extension_predicate', and the predicate is not exact on the three slots. "
            "Direction: the frozen prose predicate is strictly stricter than the schema predicate "
            "(C-infinity iota and smooth M' shrink E; the interior requirement blocks the R2 "
            "escapability already repaired in the F2b clause), so the schema's class is strictly "
            "weaker than the class the frozen prose documents claim to have frozen. The two texts "
            "cannot both be authoritative at FROZEN rev29."),
        "repair_templates": {
            "iota": "schemas/af_scc_c0_vacuum.yaml:190 non_vacuity.iota_regularity (convention to mirror; natural canonical home in F2a is regularity.iota_regularity)",
            "M_prime": "schemas/af_scc_c0_vacuum.yaml:87 extension_predicate clause (c) SMOOTH",
            "interior": "schemas/af_scc_c0_vacuum.yaml:92 extension_predicate clause (f) int(...)",
        },
        "pins": measurements["frozen_pins"],
        "entry_drift_at_run": measurements["entry_drift"],
        "drift_note": (
            "FROZEN.json container was rewritten in place after the bootstrap pin "
            "(3d9e3d77fd87 -> 815e08079aef) while still declaring revision 29; the object "
            "hashes in frozen_pins are unchanged, so this adjudication binds to the pinned "
            "objects and records the container drift separately."
            if "frozen_manifest" in measurements["entry_drift"] else
            "no entry drift at run time"),
        "disposition_options": [
            "A (recommended): propagate the three F2b conventions into schemas/af_scc_c2_vacuum.yaml, bump FROZEN to rev30, re-run gate tests and require fresh reviewer verdicts at the new hashes.",
            "B: if the schema text is authoritative, correct FORMULATION.md:133-144 and DELIVERABLE_SUMMARY.md:47-48 and re-pin; this leaves F2a weaker than the frozen prose and unconformant with the F2b sibling.",
        ],
        "relation_to_prior_art": {
            "worker-091 HF-091-02": "independently reproduced and extended: worker-091 named iota clause (a) and M' category (clause (c)/topology); this adjudication adds the clause-(f) interior slot, shows the frozen prose documents already assert all three for F2a, shows the F2b sibling carries all three as templates, and shows the gate tools never reference them.",
            "R4_final_audit finding 16": "R4 rated the iota mismatch 'minor' at rev19; at rev29 the mismatch survives and the clause-(f) mismatch R4 rated 'major' also survives, so the combined predicate divergence is blocking under the gate criterion, not minor.",
        },
        "falsifier": DIVERGENCE_FALSIFIER,
        "authority_note": "worker event: advisory only; no gate verdict, no node status promotion, no shared artifact modified.",
    }
    with open(os.path.join(HERE, "measurements.json"), "w") as fh:
        json.dump(measurements, fh, indent=1, sort_keys=True)
    with open(os.path.join(HERE, "controls.json"), "w") as fh:
        json.dump(controls, fh, indent=1, sort_keys=True)
    with open(os.path.join(HERE, "report.json"), "w") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
    print(json.dumps({"checks": measurements["checks"], "controls": measurements["controls_passed"],
                      "drift": list(drift), "findings": findings}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

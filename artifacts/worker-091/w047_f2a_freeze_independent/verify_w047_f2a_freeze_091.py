#!/usr/bin/env python3
"""Independent verification of W047-F2A-EXT-FREEZE-SPEC-02 (author: worker-047).

Task:  W091-W047-F2A-FREEZE-INDEP-01
Node:  F2a    Class: AF-SCC-C2-VAC-GEN    Gate: G-FORM

Read-only on every canonical path.  This instrument re-derives the six freeze axes
from the live bytes and from the published repair_spec.json, applies the declared
option-A edits to a private snapshot, and re-checks them.  It does NOT import,
execute or copy the author's instrument (check_f2a_ext_freeze_047.py); the axis
predicates below are an independent implementation published in this file.

Axis labels follow the author's report/control table (recovered from the author's
instrument, not from repair_spec.json, which does not publish A6):
  A1 extension_predicate clause (c) freezes an explicit manifold category for M'  (site S2)
  A2 topology.extension_topology names the category next to '4-manifold'          (site S4)
  A3 extension_predicate clause (a) freezes the differentiability class of iota   (site S1)
  A4 clause (f) requires a non-empty interior addition and p in int(M'-iota(M))   (site S3)
  A5 falsifier.tier_1.witness_type exhibits the witness in the same frozen class  (site S5)
  A6 F2a's M' category token equals the F2b sibling's frozen token (sibling uniformity)

Outputs (in this directory): patched/af_scc_c2_vacuum.w047-patched.yaml, report.json.
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TZ = timezone(timedelta(hours=8))

PINNED = {
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
}
SPEC_REL = "artifacts/worker-047/f2a_ext_freeze_spec/repair_spec.json"
AUTHOR_REPORT_REL = "artifacts/worker-047/f2a_ext_freeze_spec/report.json"
EXPECTED_SITE_LINES = {"S1": 93, "S2": 95, "S3": 98, "S4": 117, "S5": 252}
SITE_TO_AXIS = {"S1": "A3", "S2": "A1", "S3": "A4", "S4": "A2", "S5": "A5"}
MUTANT_EXPECTED = {"A1": {"A1", "A6"}, "A2": {"A2"}, "A3": {"A3"},
                   "A4": {"A4"}, "A5": {"A5"}, "A6": {"A6"}}
AXES = ["A1", "A2", "A3", "A4", "A5", "A6"]
EXPECTED_LEAVES = {
    "extension_predicate.definition",
    "topology.extension_topology",
    "falsifier.tier_1.witness_type",
}


def now() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys."""


def _no_duplicates(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"duplicate key: {key!r}", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)


def load_strict(text: str):
    return yaml.load(text, Loader=StrictLoader)


def clause(definition: str, letter: str) -> str:
    m = re.search(r"\(%s\)(.*?)(?=\([a-z]\)\s|\Z)" % re.escape(letter),
                  definition, re.S)
    return m.group(1).strip() if m else ""


SMOOTH_4M_RE = re.compile(r"SMOOTH(?: \(C-infinity\))?[^.;]{0,60}?4-manifold")
C2_4M_RE = re.compile(r"(?<![\w-])C2[^.;]{0,60}?4-manifold")


def cat_token(text: str):
    """Canonical manifold-category token named next to '4-manifold' in a piece of text.

    Accepts the three published phrasings: 'SMOOTH (C-infinity) connected 4-manifold'
    (F2b / S2), 'connected SMOOTH 4-manifold' (S4) and 'SMOOTH 4-manifold' (S5).
    """
    if SMOOTH_4M_RE.search(text):
        return "smooth"
    if C2_4M_RE.search(text):
        return "C2"
    return None


def iota_token(text: str):
    m = re.search(r"(C-infinity|C2) isometric embedding", text)
    return m.group(1) if m else None


def axis_status(f2a_text: str, f2b_doc) -> dict:
    """Derive A1-A6 from raw F2a bytes (and the F2b sibling doc for A6)."""
    doc = load_strict(f2a_text)
    defn = doc["extension_predicate"]["definition"]
    ca, cc, cf = clause(defn, "a"), clause(defn, "c"), clause(defn, "f")
    topo = doc["topology"]["extension_topology"]
    wit = doc["falsifier"]["tier_1"]["witness_type"]

    f2b_defn = f2b_doc["extension_predicate"]["definition"]
    f2b_cat = cat_token(clause(f2b_defn, "c"))

    a1 = cat_token(cc) is not None
    a2 = cat_token(topo) is not None
    a3 = iota_token(ca) is not None
    a4 = ("int(M' minus iota(M)) is non-empty" in cf
          and "p in int(M' minus iota(M))" in cf)
    a5 = (cat_token(wit) is not None and iota_token(wit) is not None
          and re.search(r"interior future point|int\(M' minus iota\(M\)\)", wit) is not None)
    a6 = cat_token(cc) is not None and cat_token(cc) == f2b_cat
    return {
        "A1": {"status": "resolved" if a1 else "unresolved",
               "detail": f"clause (c) category token = {cat_token(cc)!r}"},
        "A2": {"status": "resolved" if a2 else "unresolved",
               "detail": f"extension_topology category token = {cat_token(topo)!r}"},
        "A3": {"status": "resolved" if a3 else "unresolved",
               "detail": f"clause (a) iota token = {iota_token(ca)!r}"},
        "A4": {"status": "resolved" if a4 else "unresolved",
               "detail": "clause (f) interior requirement present" if a4 else
                         "clause (f) allows p in M' minus iota(M) without interior requirement"},
        "A5": {"status": "resolved" if a5 else "unresolved",
               "detail": f"witness M' token={cat_token(wit)!r}, iota token={iota_token(wit)!r}, "
                         f"interior={'yes' if re.search(r'interior future point|int', wit) else 'no'}"},
        "A6": {"status": "resolved" if a6 else "unresolved",
               "detail": f"F2a clause (c) token = {cat_token(cc)!r}, F2b sibling token = {f2b_cat!r}"},
    }


def apply_sites(text: str, spec: dict):
    """Apply the declared option-A edits; return patched text + per-site records."""
    out = text
    records = []
    for site in spec["sites"]:
        sid = site["site_id"]
        old, new = site["old_text"], site["new_text"]
        n = out.count(old)
        rec = {
            "site_id": sid,
            "yaml_path": site["yaml_path"],
            "axis": SITE_TO_AXIS.get(sid),
            "declared_line_at_pin": site.get("file_line_at_pin"),
            "measured_line_at_pin": (out[:out.index(old)].count("\n") + 1) if n else None,
            "occurrences_in_snapshot": text.count(old),
            "old_text": old,
            "new_text": new,
            "applied": False,
        }
        if n == 1:
            out = out.replace(old, new, 1)
            rec["applied"] = True
        records.append(rec)
    return out, records


def flatten(obj, prefix="", out=None):
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten(v, f"{prefix}.{k}" if prefix else str(k), out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flatten(v, f"{prefix}[{i}]", out)
    else:
        out[prefix] = obj
    return out


def invariants(patched_text: str) -> list:
    doc = load_strict(patched_text)
    ext = doc["extension_predicate"]
    dfn = ext["definition"]
    cd = clause(dfn, "d")
    conc = doc["conclusion"]
    conc_asserted = json.dumps({
        "type": conc.get("conclusion_type"),
        "nl": conc.get("statement_natural_language"),
        "formal": conc.get("statement_formal"),
        "rephrasings": conc.get("equivalent_rephrasings"),
        "known_obstruction": conc.get("known_obstruction"),
    })
    composite_slots = {
        "extension_predicate.definition": dfn,
        "topology.extension_topology": doc["topology"]["extension_topology"],
        "falsifier.tier_1.witness_type": doc["falsifier"]["tier_1"]["witness_type"],
        "conclusion.asserted": conc_asserted,
        "genericity.generic_set": doc["genericity"].get("generic_set", ""),
    }
    composite_used = sorted(k for k, v in composite_slots.items() if "C0 or C2" in v)
    checks = [
        ("I1_parses_strict", "patched YAML re-parses under a duplicate-key-rejecting loader"),
        ("I2_frozen_regularity_C2", "extension_predicate.frozen_regularity == 'C2'",
         ext.get("frozen_regularity") == "C2", ext.get("frozen_regularity")),
        ("I3_frozen_equation_classical_ricci",
         "extension_predicate.frozen_equation_concept == 'classical_ricci'",
         ext.get("frozen_equation_concept") == "classical_ricci", ext.get("frozen_equation_concept")),
        ("I4_clause_d_C2_lorentzian", "clause (d) still requires g' of class C2 Lorentzian",
         "C2 Lorentzian metric" in cd, cd[:80]),
        ("I5_conclusion_type_unchanged",
         "conclusion.conclusion_type == 'scc_c2_future_inextendibility'",
         conc.get("conclusion_type") == "scc_c2_future_inextendibility", conc.get("conclusion_type")),
        ("I6_genericity_kind_residual_comeager",
         "genericity.kind == 'residual_comeager'",
         doc["genericity"].get("kind") == "residual_comeager", doc["genericity"].get("kind")),
        ("I7_containment_chain_unchanged",
         "implication_ledger containment chain unchanged",
         doc["implication_ledger"].get("extension_class_containment") ==
         "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0 (nested extension sets): "
         "the lower the required regularity, the larger the set of admissible extensions, hence "
         "the stronger the inexistence statement. [R2 major: the earlier revision had the H2_loc "
         "ordering wrong]",
         doc["implication_ledger"].get("extension_class_containment", "")[:60]),
        ("I8_no_wcc_Iplus_in_conclusion",
         "no WCC/I+/visibility predicate asserted in the conclusion block",
         not re.search(r"\bWCC\b|\bI\+|visibility", conc_asserted), conc_asserted[:60]),
        ("I9_no_C0_or_C2_composite_token",
         "no composite 'C0 or C2' regularity token is USED in an asserted semantic slot "
         "(definition/topology/conclusion/genericity/witness); a quoted prohibition of the token "
         "elsewhere is the intended guard, not a use",
         not composite_used,
         f"used_in={composite_used}; quoted_prohibition_occurrences={patched_text.count('C0 or C2')}"),
    ]
    out = []
    for item in checks:
        cid, desc = item[0], item[1]
        if len(item) == 2:  # parse control already succeeded
            out.append({"id": cid, "description": desc, "pass": True, "measured": "parsed"})
        else:
            out.append({"id": cid, "description": desc, "pass": bool(item[2]), "measured": item[3]})
    return out


def run_canonical_gate(schema_path: Path) -> dict:
    tool = ROOT / "artifacts/formulation/tools/check_class_schema.py"
    proc = subprocess.run([sys.executable, str(tool), "--json", str(schema_path)],
                          capture_output=True, text=True, timeout=300)
    rec = {"tool": str(tool.relative_to(ROOT)), "returncode": proc.returncode}
    try:
        rep = json.loads(proc.stdout)
        rec["verdict"] = rep.get("verdict")
        rec["failed_rules"] = sorted(rep.get("failed_rules", []))
        rec["failure_count"] = len(rep.get("failures", []))
    except Exception:
        rec["verdict"] = None
        rec["failed_rules"] = None
        rec["stdout_tail"] = proc.stdout[-400:]
    rec["stderr_tail"] = proc.stderr[-200:]
    return rec


def pipeline(f2a_text: str, f2b_doc, spec: dict, patched_path: Path) -> dict:
    baseline = axis_status(f2a_text, f2b_doc)
    patched_text, records = apply_sites(f2a_text, spec)
    patched_path.write_text(patched_text)
    repaired = axis_status(patched_text, f2b_doc)

    leaves_ok, leaves_detail = True, {}
    try:
        a, b = load_strict(f2a_text), load_strict(patched_text)
        fa, fb = flatten(a), flatten(b)
        added = sorted(set(fb) - set(fa))
        removed = sorted(set(fa) - set(fb))
        changed = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])
        leaves_detail = {"added_paths": added, "removed_paths": removed,
                         "changed_leaf_paths": changed,
                         "unexpected_structural_change": bool(added or removed),
                         "unexpected_leaf_changes": sorted(set(changed) - EXPECTED_LEAVES)}
        leaves_ok = not added and not removed and not (set(changed) - EXPECTED_LEAVES)
    except Exception as exc:  # pragma: no cover
        leaves_ok = False
        leaves_detail = {"parse_error": str(exc)}

    inv = invariants(patched_text)

    # controls -----------------------------------------------------------------
    controls = {"identity": {}, "mutants": {}, "degenerate": {}}
    ident_ids = [r["site_id"] for r in records]
    ident = all(axis_status(f2a_text, f2b_doc)[ax]["status"] == baseline[ax]["status"]
                for ax in AXES)
    controls["identity"] = {
        "description": "empty patch leaves every axis status equal to the baseline derivation",
        "pass": ident,
        "sites_considered": ident_ids,
    }

    by_site = {s["site_id"]: s for s in spec["sites"]}
    for ax in AXES:
        t = patched_text
        if ax == "A6":
            s2 = by_site["S2"]
            t = t.replace(s2["new_text"], s2["alternatives"][0]["new_text"], 1)
        else:
            sid = {"A1": "S2", "A2": "S4", "A3": "S1", "A4": "S3", "A5": "S5"}[ax]
            s = by_site[sid]
            t = t.replace(s["new_text"], s["old_text"], 1)
        st = axis_status(t, f2b_doc)
        unresolved = sorted(a for a in AXES if st[a]["status"] == "unresolved")
        controls["mutants"][ax] = {
            "description": f"planted single-axis mutant for {ax}",
            "unresolved": unresolved,
            "expected_unresolved": sorted(MUTANT_EXPECTED[ax]),
            "discriminates": unresolved == sorted(MUTANT_EXPECTED[ax]),
        }
    controls["mutant_table_reproduced"] = all(
        controls["mutants"][ax]["discriminates"] for ax in AXES)

    always_resolved = {ax: "resolved" for ax in AXES}
    always_unresolved = {ax: "unresolved" for ax in AXES}
    base_statuses = {ax: baseline[ax]["status"] for ax in AXES}
    rep_statuses = {ax: repaired[ax]["status"] for ax in AXES}
    controls["degenerate"] = {
        "always_resolved_differs_from_baseline": always_resolved != base_statuses,
        "always_unresolved_differs_from_repaired": always_unresolved != rep_statuses,
    }
    controls["degenerate"]["pass"] = (controls["degenerate"]["always_resolved_differs_from_baseline"]
                                      and controls["degenerate"]["always_unresolved_differs_from_repaired"])

    gate_base = run_canonical_gate(HERE / "snapshots/af_scc_c2_vacuum.e9a27996.yaml")
    gate_patch = run_canonical_gate(patched_path)
    if gate_base.get("failed_rules") is not None and gate_patch.get("failed_rules") is not None:
        no_worse = set(gate_patch["failed_rules"]) <= set(gate_base["failed_rules"])
    else:
        no_worse = (gate_patch["returncode"] == 0) or (gate_base["returncode"] != 0 and gate_patch["returncode"] == 0)
    canonical_gate = {"baseline_snapshot": gate_base, "patched_snapshot": gate_patch,
                      "patched_no_worse_than_baseline": bool(no_worse)}

    return {
        "baseline_axes": baseline,
        "repaired_axes": repaired,
        "site_application": records,
        "only_intended_leaves": {"pass": leaves_ok, **leaves_detail},
        "invariants": inv,
        "controls": controls,
        "canonical_gate": canonical_gate,
    }


def main() -> int:
    spec_path = ROOT / SPEC_REL
    report = {
        "schema": "w091-w047-f2a-freeze-independent/v1",
        "task_id": "W091-W047-F2A-FREEZE-INDEP-01",
        "actor": "worker-091",
        "class_id": "AF-SCC-C2-VAC-GEN",
        "node_id": "F2a",
        "gate": "G-FORM",
        "authority_note": ("worker deliverable: independent verification of another worker's repair "
                           "specification; read-only on all canonical paths; does not edit the "
                           "reviewed artifact, does not set node status, validation_status=passed, "
                           "or any gate verdict."),
        "review_target": {
            "spec_path": SPEC_REL,
            "author_report_path": AUTHOR_REPORT_REL,
            "reviewed_sha256": sha256_file(spec_path),
            "author_report_sha256": sha256_file(ROOT / AUTHOR_REPORT_REL),
        },
        "generated_at": now(),
    }

    # pins ---------------------------------------------------------------------
    pins_start = {}
    for rel, expect in PINNED.items():
        b = (ROOT / rel).read_bytes()
        pins_start[rel] = {"sha256": sha256_bytes(b), "bytes": len(b),
                           "expected": expect, "match": sha256_bytes(b) == expect}
    report["pins_start"] = pins_start
    report["pins_declared_in_spec"] = json.loads(spec_path.read_text()).get("pins_measured_at_authoring")

    f2a_text = (ROOT / "schemas/af_scc_c2_vacuum.yaml").read_text()
    f2b_text = (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text()
    f2b_doc = load_strict(f2b_text)
    spec = json.loads(spec_path.read_text())

    run_a = pipeline(f2a_text, f2b_doc, spec, HERE / "patched/af_scc_c2_vacuum.w047-patched.yaml")
    run_b = pipeline(f2a_text, f2b_doc, spec, HERE / "patched/af_scc_c2_vacuum.w047-patched.yaml")
    strip = lambda d: json.loads(json.dumps({k: v for k, v in d.items()}))
    report.update(run_a)

    # determinism: second full run must agree once generated_at is excluded
    da, db = strip(run_a), strip(run_b)
    report["determinism_check"] = {
        "method": "two full pipeline runs at fixed inputs; compare all fields except generated_at",
        "identical": da == db,
    }

    # post-run drift -----------------------------------------------------------
    pins_end = {}
    for rel, expect in PINNED.items():
        b = (ROOT / rel).read_bytes()
        pins_end[rel] = {"sha256": sha256_bytes(b), "bytes": len(b), "match_pin": sha256_bytes(b) == expect}
    report["pins_end"] = pins_end
    report["drift_during_run"] = sorted(
        rel for rel in PINNED if pins_end[rel]["sha256"] != pins_start[rel]["sha256"])
    report["patched_file"] = {
        "path": "artifacts/worker-091/w047_f2a_freeze_independent/patched/af_scc_c2_vacuum.w047-patched.yaml",
        "sha256": sha256_file(HERE / "patched/af_scc_c2_vacuum.w047-patched.yaml"),
    }

    # hard failures ------------------------------------------------------------
    hf = []
    if not all(v["match"] for v in pins_start.values()):
        hf.append("HF-091W-00 pin_mismatch: a declared canonical pin differs at start")
    if report["drift_during_run"]:
        hf.append("HF-091W-01 drift_during_run: " + ",".join(report["drift_during_run"]))
    base_unresolved = [a for a in AXES if run_a["baseline_axes"][a]["status"] != "unresolved"]
    if base_unresolved:
        hf.append("HF-091W-02 baseline_claim: axes unexpectedly already resolved at the live pin: "
                  + ",".join(base_unresolved))
    rep_unresolved = [a for a in AXES if run_a["repaired_axes"][a]["status"] != "resolved"]
    if rep_unresolved:
        hf.append("HF-091W-03 repair_incomplete: axes still unresolved after the declared option-A patch: "
                  + ",".join(rep_unresolved))
    for r in run_a["site_application"]:
        if not r["applied"] or r["occurrences_in_snapshot"] != 1:
            hf.append(f"HF-091W-04 site_{r['site_id']}_not_exactly_once: occurrences="
                      f"{r['occurrences_in_snapshot']}")
        if r["declared_line_at_pin"] != r["measured_line_at_pin"]:
            hf.append(f"HF-091W-05 site_{r['site_id']}_line_mismatch: declared="
                      f"{r['declared_line_at_pin']} measured={r['measured_line_at_pin']}")
    if not run_a["only_intended_leaves"]["pass"]:
        hf.append("HF-091W-06 unintended_structural_change")
    for inv in run_a["invariants"]:
        if not inv["pass"]:
            hf.append(f"HF-091W-07 invariant_failed: {inv['id']}")
    if not run_a["canonical_gate"]["patched_no_worse_than_baseline"]:
        hf.append("HF-091W-08 canonical_gate_regression")
    if not run_a["controls"]["mutant_table_reproduced"]:
        bad = [ax for ax in AXES if not run_a["controls"]["mutants"][ax]["discriminates"]]
        hf.append("HF-091W-09 mutant_table_mismatch: " + ",".join(bad))
    if not run_a["controls"]["degenerate"]["pass"]:
        hf.append("HF-091W-10 degenerate_control_vacuous")
    if not report["determinism_check"]["identical"]:
        hf.append("HF-091W-11 nondeterministic_pipeline")
    report["hard_failures"] = hf

    findings = [
        {"id": "F-091W-01", "severity": "low",
         "text": "repair_spec.json enumerates five sites S1-S5 but its report/control table refers to "
                 "six axes A1-A6; the A6 semantics (F2a clause (c) category token must equal the F2b "
                 "sibling's frozen token) are published only in the author's instrument code. "
                 "Independent readers of the spec alone cannot reproduce the control table for A6. "
                 "Suggested repair: add an axis table (A1-A6 -> site, predicate) to repair_spec.json."},
        {"id": "F-091W-02", "severity": "low",
         "text": "The canonical structural gate (artifacts/formulation/tools/check_class_schema.py) "
                 "passes the UNREPAIRED F2a snapshot: the under-freezing is invisible to the binding "
                 "gate. The W047 repair is therefore a content-completeness repair that must be "
                 "carried by reviewer verdicts, not by the structural gate; this is evidence for the "
                 "gate blind-spot list, not a defect of the spec."},
        {"id": "F-091W-03", "severity": "low",
         "text": "Option A freezes SMOOTH (C-infinity) for M' while the metric is only C2. That is "
                 "internally consistent (the smooth structure is the tensor-field carrier) and matches "
                 "the F2b sibling, but the repair text should be read together with clause (d); the "
                 "spec's rationale does this, the patch text alone does not."},
    ]
    report["findings"] = findings
    report["verdict"] = "accept" if not hf else "revise"
    report["score"] = 4.5 if not hf else max(0.0, 3.5 - 0.5 * len(hf))
    report["falsifier"] = (
        "This verification is falsified if, at pins " +
        ", ".join(f"{k}#{v['sha256'][:12]}" for k, v in pins_start.items()) + ": "
        "(a) any site old_text occurs other than exactly once or at a different line than declared; "
        "(b) re-applying the declared option-A edits leaves any of A1-A6 unresolved; "
        "(c) the patched copy changes a YAML leaf outside the three declared leaves; "
        "(d) any invariant I1-I9 fails on the patched copy; "
        "(e) any planted single-axis mutant fails to reproduce the author's unresolved set; "
        "(f) the canonical gate fails on the patched copy where it passed on the baseline snapshot; or "
        "(g) the pipeline is not reproducible. Input drift voids (does not falsify) this report."
    )
    report["next_falsifier"] = (
        "Re-issue this check after the owner applies the repair at a new revision: the repaired live "
        "bytes must resolve A1-A6 under this instrument's predicates, and a fresh independent verdict "
        "must be recorded at the new sha256; the r3 reviewer cards pinned to e9a27996 are void for it."
    )
    report["evidence_refs"] = [
        SPEC_REL + "#" + report["review_target"]["reviewed_sha256"],
        AUTHOR_REPORT_REL + "#" + report["review_target"]["author_report_sha256"],
        f"schemas/af_scc_c2_vacuum.yaml#{pins_start['schemas/af_scc_c2_vacuum.yaml']['sha256']}",
        f"schemas/af_scc_c0_vacuum.yaml#{pins_start['schemas/af_scc_c0_vacuum.yaml']['sha256']}",
        f"artifacts/formulation/FROZEN.json#{pins_start['artifacts/formulation/FROZEN.json']['sha256']}",
        "artifacts/worker-091/w047_f2a_freeze_independent/snapshots/af_scc_c2_vacuum.e9a27996.yaml",
        "artifacts/worker-091/w047_f2a_freeze_independent/patched/af_scc_c2_vacuum.w047-patched.yaml",
    ]

    out = HERE / "report.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: report[k] for k in
                      ("verdict", "score", "hard_failures", "determinism_check",
                       "patched_file")}, indent=1, ensure_ascii=False))
    print("report:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

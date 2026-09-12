#!/usr/bin/env python3
"""Independent verifier for hf02-disjunction-adjudication-023.json (worker-023).

This script does NOT import the builder. It re-derives every claim of the
packet from the repository inputs and runs four mutation controls that must
each be caught. Offline, deterministic.

Checks
------
V1  every input re-hashes to the sha256 recorded in the packet and manifest;
V2  the packet row set equals the independently re-derived set of ledger rows
    with len(class_ids) > 1 (completeness);
V3  each row's `row_evidence` equals the live fields of the pinned ledger row
    (evidence binding, not a paraphrase);
V4  every recommendation obeys the frozen-four vocabulary, class_ids /
    informs_classes disjointness, disposition shape, and the registered
    variant parent;
V5  `applied` is false and the ledger hash is unchanged across the run
    (no write happened);
C1  variant id placed in class_ids is caught (class-leakage detector);
C2  an extra disjunctive row is caught (completeness detector);
C3  tampered row_evidence is caught (evidence-binding detector);
C4  overlapping class_ids / informs_classes is caught (binding-shape detector).

Run: python3 artifacts/worker-023/l0_hf02/verify_hf02_023.py
Exit 0 iff V1-V5 pass and C1-C4 all trigger.
"""

import copy
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
CST = timezone(timedelta(hours=8))

FROZEN_FOUR = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}
WCC = "AF-WCC-VAC-GEN"
C2 = "AF-SCC-C2-VAC-GEN"
C0 = "AF-SCC-C0-VAC-GEN"

PACKET_REL = "artifacts/worker-023/l0_hf02/hf02-disjunction-adjudication-023.json"
MANIFEST_REL = "artifacts/worker-023/l0_hf02/build_manifest_hf02_023.json"
LEDGER_REL = "ledger/theorems.jsonl"

INPUT_FILES = [
    "ledger/theorems.jsonl",
    "ledger/citation_audit.csv",
    "artifacts/formulation/VARIANT_REGISTRY.json",
    "research_map/formulation_taxonomy.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "evaluation_rubric.yaml",
]

EVIDENCE_FIELDS = [
    "label",
    "statement_exact",
    "regularity",
    "genericity",
    "conclusion_type",
    "entry_kind",
    "evidence_level",
    "ledger_tags",
    "unresolved",
    "scope_caveats",
]


def sha256_file(rel):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, rel), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rows():
    rows = {}
    with open(os.path.join(ROOT, LEDGER_REL), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                r = json.loads(line)
                rows[r["theorem_id"]] = r
    return rows


def load_registry():
    with open(os.path.join(ROOT, "artifacts/formulation/VARIANT_REGISTRY.json"), encoding="utf-8") as fh:
        return json.load(fh)


def check_packet(packet, rows, reg):
    """Pure checker. Returns list of error strings; empty == valid."""
    errs = []
    reg_variants = {v["variant_id"]: v for v in reg["variants"]}
    reg_parents = {p["class_id"] for p in reg["parent_classes"]}

    # V2 completeness (checked again here so controls C2 can exercise it)
    derived = sorted(t for t, r in rows.items() if len(r.get("class_ids") or []) > 1)
    declared = sorted(p["row_id"] for p in packet["rows"])
    if derived != declared:
        errs.append("V2 completeness: derived=%s declared=%s" % (derived, declared))

    if packet.get("applied") is not False:
        errs.append("V5 applied must be false")
    if packet.get("class_ids") and not set(packet["class_ids"]) <= FROZEN_FOUR:
        errs.append("V4 packet class_ids outside frozen four")

    for pr in packet["rows"]:
        tid = pr["row_id"]
        r = rows.get(tid)
        if r is None:
            errs.append("V3 row missing from ledger: " + tid)
            continue

        # V3 evidence binding: exact equality on every recorded field
        for f, v in (pr.get("row_evidence") or {}).items():
            if f not in r:
                errs.append("V3 %s: field absent in ledger row: %s" % (tid, f))
            elif r[f] != v:
                errs.append("V3 %s: row_evidence[%s] differs from pinned row" % (tid, f))

        # V4 recommendation shape
        rec = pr.get("recommended") or {}
        cids = list(rec.get("class_ids") or [])
        inf = list(rec.get("informs_classes") or [])
        for c in cids + inf:
            if c not in FROZEN_FOUR:
                errs.append("V4 %s: non-frozen class %s" % (tid, c))
        if set(cids) & set(inf):
            errs.append("V4 %s: class_ids/informs_classes overlap" % tid)
        if not cids and not inf:
            errs.append("V4 %s: empty binding recommendation" % tid)
        if len(cids) > 1:
            errs.append("V4 %s: recommendation still disjunctive" % tid)
        if len(cids) + len(inf) > 2:
            errs.append("V4 %s: more than two bindings" % tid)
        if (set(cids) | set(inf)) - FROZEN_FOUR:
            errs.append("V4 %s: recommendation uses unknown class token" % tid)

        vid = pr.get("registry_variant_id")
        if vid is not None:
            if vid not in reg_variants:
                errs.append("V4 %s: unregistered variant %s" % (tid, vid))
            elif reg_variants[vid]["parent_class"] != pr.get("registry_parent"):
                errs.append("V4 %s: variant parent mismatch" % tid)

        disp = pr.get("disposition")
        if disp == "WCC_ONLY":
            if cids != [WCC] or inf:
                errs.append("V4 %s: WCC_ONLY shape violated" % tid)
            if pr.get("measured_extension_class") != "WCC-ANTECEDENT":
                errs.append("V4 %s: WCC_ONLY without WCC-ANTECEDENT measurement" % tid)
        elif disp == "VARIANT_INFORMS":
            if cids:
                errs.append("V4 %s: VARIANT_INFORMS must not set class_ids" % tid)
            if inf != [pr.get("registry_parent")]:
                errs.append("V4 %s: VARIANT_INFORMS informs != registry parent" % tid)
        elif disp == "RELATION_INFORMS":
            if cids or set(inf) != {C0, C2}:
                errs.append("V4 %s: RELATION_INFORMS must inform exactly C0+C2" % tid)
        elif disp == "NEEDS_F1_RULING":
            if cids:
                errs.append("V4 %s: NEEDS_F1_RULING must not set class_ids" % tid)
            if not (pr.get("needs_f1_ruling") or {}).get("question"):
                errs.append("V4 %s: NEEDS_F1_RULING without a question" % tid)
        else:
            errs.append("V4 %s: unknown disposition %r" % (tid, disp))

    if set(packet.get("disjunctive_row_set") or []) != set(declared):
        errs.append("V2 packet disjunctive_row_set != packet rows")

    return errs


def main():
    result = {
        "verifier": "artifacts/worker-023/l0_hf02/verify_hf02_023.py",
        "actor": "worker-023",
        "verified_at": datetime.now(CST).isoformat(timespec="seconds"),
        "checks": {},
        "controls": {},
        "falsifier": (
            "This verification is falsified if (a) any listed input re-hashes to a different sha256, "
            "(b) the independently re-derived disjunctive row set differs from the packet rows, "
            "(c) any row_evidence field differs from the pinned ledger row, or (d) any mutation "
            "control C1-C4 is not caught."
        ),
        "authority": "Worker verification only; no gate verdict, no node status, no ledger edit.",
    }
    errors = []

    # V1 input hashes
    measured = {}
    for rel in INPUT_FILES:
        if not os.path.exists(os.path.join(ROOT, rel)):
            errors.append("V1 missing input: " + rel)
            continue
        measured[rel] = sha256_file(rel)

    with open(os.path.join(ROOT, PACKET_REL), encoding="utf-8") as fh:
        packet = json.load(fh)
    with open(os.path.join(ROOT, MANIFEST_REL), encoding="utf-8") as fh:
        manifest = json.load(fh)

    packet_sha = sha256_file(PACKET_REL)
    result["packet_sha256"] = packet_sha
    result["packet_sha256_matches_manifest"] = packet_sha == manifest["output"]["sha256"]
    if not result["packet_sha256_matches_manifest"]:
        errors.append("V1 packet sha256 differs from build manifest")

    for rel, h in measured.items():
        if packet["inputs"].get(rel) != h:
            errors.append("V1 input drift vs packet: %s" % rel)
        if manifest["inputs"].get(rel) != h:
            errors.append("V1 input drift vs manifest: %s" % rel)
    result["checks"]["V1_inputs_pinned"] = not any(e.startswith("V1") for e in errors)

    rows = load_rows()
    reg = load_registry()

    # V2-V4 on the real packet
    main_errors = check_packet(packet, rows, reg)
    errors.extend(main_errors)
    result["checks"]["V2_completeness"] = not any(e.startswith("V2") for e in main_errors)
    result["checks"]["V3_evidence_binding"] = not any(e.startswith("V3") for e in main_errors)
    result["checks"]["V4_recommendation_shape"] = not any(e.startswith("V4") for e in main_errors)

    # V5 ledger unchanged during the run
    ledger_before = measured[LEDGER_REL]
    ledger_after = sha256_file(LEDGER_REL)
    result["checks"]["V5_no_ledger_write"] = ledger_before == ledger_after and packet["applied"] is False
    if not result["checks"]["V5_no_ledger_write"]:
        errors.append("V5 ledger hash changed during verification or applied != false")

    # ---- mutation controls -------------------------------------------------
    # C1: variant id in class_ids (class leakage)
    p1 = copy.deepcopy(packet)
    p1["rows"][0]["recommended"]["class_ids"] = ["L2CONN"]
    p1["rows"][0]["recommended"]["informs_classes"] = []
    c1 = check_packet(p1, rows, reg)
    result["controls"]["C1_variant_as_class_caught"] = any("non-frozen class L2CONN" in e for e in c1)
    if not result["controls"]["C1_variant_as_class_caught"]:
        errors.append("C1 control did not trigger")

    # C2: extra disjunctive row injected into the packet (completeness)
    p2 = copy.deepcopy(packet)
    extra = copy.deepcopy(p2["rows"][0])
    extra["row_id"] = "T-303-synthetic-extra"
    p2["rows"].append(extra)
    c2 = check_packet(p2, rows, reg)
    result["controls"]["C2_extra_disjunctive_row_caught"] = any(e.startswith("V2") for e in c2)
    if not result["controls"]["C2_extra_disjunctive_row_caught"]:
        errors.append("C2 control did not trigger")

    # C3: tampered row_evidence
    p3 = copy.deepcopy(packet)
    p3["rows"][0]["row_evidence"]["regularity"] = "C2 (tampered)"
    c3 = check_packet(p3, rows, reg)
    result["controls"]["C3_tampered_evidence_caught"] = any(e.startswith("V3") for e in c3)
    if not result["controls"]["C3_tampered_evidence_caught"]:
        errors.append("C3 control did not trigger")

    # C4: overlapping class_ids / informs_classes
    p4 = copy.deepcopy(packet)
    p4["rows"][-1]["recommended"]["class_ids"] = [WCC]
    p4["rows"][-1]["recommended"]["informs_classes"] = [WCC]
    c4 = check_packet(p4, rows, reg)
    result["controls"]["C4_binding_overlap_caught"] = any(
        ("overlap" in e) or ("shape violated" in e) for e in c4
    )
    if not result["controls"]["C4_binding_overlap_caught"]:
        errors.append("C4 control did not trigger")

    # mutate back and confirm the checker is not stuck in a failure mode
    c_clean = check_packet(copy.deepcopy(packet), rows, reg)
    result["controls"]["C0_clean_packet_still_passes"] = c_clean == []
    if c_clean:
        errors.append("C0 clean packet unexpectedly fails: %s" % c_clean[:3])

    result["input_hashes"] = measured
    result["errors"] = errors
    result["verdict"] = "PASS" if not errors else "FAIL"
    result["runtime"] = {"python": sys.version.split()[0], "platform": platform.platform()}

    with open(os.path.join(HERE, "hf02-verify-023.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    print(json.dumps({"verdict": result["verdict"], "checks": result["checks"],
                      "controls": result["controls"], "errors": errors}, indent=1))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

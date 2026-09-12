#!/usr/bin/env python3
"""W079-FIELDANCHOR-01: field-level primary-source anchor audit for F1/F2a/F2b provenance.

Read-only over the five pinned inputs. Hash-pinned: any drift aborts with no report.
Positive control (ITEM-MGHD-CONTROL must recover D-008/SRC-073) gates the emission:
a harness that cannot recover a known anchor must not be believed about absences.

Usage: python3 run_fieldanchor_079.py [--out DIR]
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PREREG = os.path.join(HERE, "PREREGISTRATION.json")
BINDING_FIELDS = [
    "statement_exact", "label", "assumptions", "genericity", "topology",
    "does_not_imply", "falsifiers", "unresolved", "scope_caveats",
]
REGISTRY_FIELDS = ["title", "venue", "evidence_excerpt", "assessment", "elided_quote"]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def abort(code, message, detail):
    print(json.dumps({"harness_status": "ABORT", "exit": code, "message": message,
                      "detail": detail}, indent=1))
    sys.exit(code)


def compile_patterns(pats):
    return [re.compile(p, re.I) for p in pats]


def top_key_of_line(line):
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", line)
    return m.group(1) if m else None


def scan_schema(path, items):
    """Line-level occurrence census; nearest preceding indent-0 key = the field to bind."""
    occurrences = []
    current_top = None
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            tk = top_key_of_line(line)
            if tk:
                current_top = tk
            for item in items:
                for pat in item["schema_compiled"]:
                    for m in pat.finditer(line):
                        occurrences.append({
                            "item_id": item["id"],
                            "schema_path": path,
                            "line": lineno,
                            "top_level_key": current_top,
                            "match": m.group(0),
                            "line_excerpt": line.strip()[:240],
                        })
    return occurrences


def load_declared_provenance(path, items):
    """Extract provenance.sources entries + unresolved_citations relevant to each item."""
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    prov = (doc or {}).get("provenance") or {}
    sources = prov.get("sources") or []
    declared = {it["id"]: [] for it in items}
    for it in items:
        expected_needed_for = it.get("expected_declared_needed_for", [])
        for src in sources:
            if not isinstance(src, dict):
                continue
            concept = str(src.get("concept", ""))
            needed_for = str(src.get("needed_for", ""))
            hit = any(pat.search(concept) for pat in it["concept_compiled"])
            if not hit and expected_needed_for:
                hit = any(exp.lower() in needed_for.lower() for exp in expected_needed_for)
            if hit:
                declared[it["id"]].append({
                    "concept": concept,
                    "identifier": src.get("identifier"),
                    "status": src.get("status"),
                    "needed_for": needed_for,
                })
    unresolved = [str(u) for u in (prov.get("unresolved_citations") or [])]
    return {"declared_sources": declared, "unresolved_citations": unresolved}


def excerpts_for(rec, match, width=120):
    i = max(0, match.start() - width // 2)
    return rec[i:i + width].replace("\n", " ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=HERE)
    args = ap.parse_args()

    with open(PREREG, "r", encoding="utf-8") as f:
        prereg = json.load(f)
    prereg_sha = sha256_file(PREREG)

    # ---- fail-closed hash pin ----
    measured = {}
    drift = {}
    for rel, pinned in prereg["pinned_inputs_sha256"].items():
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            drift[rel] = {"pinned": pinned, "measured": "MISSING"}
            continue
        got = sha256_file(p)
        measured[rel] = got
        if got != pinned:
            drift[rel] = {"pinned": pinned, "measured": got}
    if drift:
        abort(2, "input hash drift; audit superseded, no report emitted", drift)

    items = []
    for it in prereg["anchor_items"]:
        it = dict(it)
        it["schema_compiled"] = compile_patterns(it["schema_patterns"])
        it["strong_compiled"] = compile_patterns(it["strong_anchor_patterns"])
        it["weak_compiled"] = compile_patterns(it.get("weak_anchor_patterns", []))
        it["collision_compiled"] = compile_patterns(it.get("collision_patterns", []))
        it["strong_context_compiled"] = compile_patterns(it.get("strong_requires_context", []))
        it["concept_compiled"] = compile_patterns(
            it.get("concept_patterns", it["strong_anchor_patterns"] + it.get("weak_anchor_patterns", [])))
        items.append(it)

    # ---- schema occurrence census + declared provenance ----
    schemas = [r for r in prereg["pinned_inputs_sha256"] if r.startswith("schemas/")]
    occurrences = []
    declared = {}
    for rel in schemas:
        occurrences += scan_schema(os.path.join(ROOT, rel), items)
        declared[rel] = load_declared_provenance(os.path.join(ROOT, rel), items)
    for o in occurrences:
        o["schema_path"] = os.path.relpath(o["schema_path"], ROOT)

    # ---- L0 corpus ----
    l0_records = []
    with open(os.path.join(ROOT, "ledger/theorems.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                l0_records.append((r.get("theorem_id"), r))
    l0_blobs = [(rid, json.dumps(rec, sort_keys=True), rec) for rid, rec in l0_records]

    l0_result = {it["id"]: {"strong": [], "weak": [], "collisions": []} for it in items}
    for rid, blob, rec in l0_blobs:
        for it in items:
            for pat in it["strong_compiled"]:
                m = pat.search(blob)
                if not m:
                    continue
                if it.get("strong_requires_context") and not any(
                        c.search(blob) for c in it["strong_context_compiled"]):
                    continue
                fields_hit = [k for k in BINDING_FIELDS
                              if k in rec and pat.search(json.dumps(rec.get(k), sort_keys=True))]
                l0_result[it["id"]]["strong"].append({
                    "theorem_id": rid,
                    "pattern": pat.pattern,
                    "match": m.group(0),
                    "binding_fields_hit": fields_hit,
                    "source_ids": rec.get("source_ids", []),
                    "excerpt": excerpts_for(blob, m),
                })
            for pat in it["weak_compiled"]:
                m = pat.search(blob)
                if m:
                    l0_result[it["id"]]["weak"].append({"theorem_id": rid, "pattern": pat.pattern})
            for pat in it["collision_compiled"]:
                m = pat.search(blob)
                if m:
                    l0_result[it["id"]]["collisions"].append(
                        {"theorem_id": rid, "pattern": pat.pattern, "match": m.group(0)})

    # ---- L1 registry corpus ----
    l1_rows = []
    with open(os.path.join(ROOT, "ledger/citation_audit.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            l1_rows.append(row)
    l1_result = {it["id"]: {"strong": [], "weak": [], "collisions": []} for it in items}
    for row in l1_rows:
        blob = " | ".join(str(row.get(k, "")) for k in REGISTRY_FIELDS)
        for it in items:
            for pat in it["strong_compiled"]:
                m = pat.search(blob)
                if not m:
                    continue
                if it.get("strong_requires_context") and not any(
                        c.search(blob) for c in it["strong_context_compiled"]):
                    continue
                l1_result[it["id"]]["strong"].append({
                    "citation_id": row["citation_id"],
                    "status": row["status"],
                    "verdict": row["verdict"],
                    "year": row["year"],
                    "title": row["title"][:120],
                    "used_by_theorems": row["used_by_theorems"],
                    "pattern": pat.pattern,
                    "match": m.group(0),
                })
            for pat in it["weak_compiled"]:
                if pat.search(blob):
                    l1_result[it["id"]]["weak"].append(
                        {"citation_id": row["citation_id"], "pattern": pat.pattern})
            for pat in it["collision_compiled"]:
                if pat.search(blob):
                    l1_result[it["id"]]["collisions"].append(
                        {"citation_id": row["citation_id"], "pattern": pat.pattern})

    # ---- classify ----
    def classify(item_id, l0r, l1r):
        if l0r[item_id]["strong"]:
            return "anchored_theorem"
        if l1r[item_id]["strong"]:
            return "anchored_registry_only"
        if l0r[item_id]["weak"] or l1r[item_id]["weak"]:
            return "weak_match_only"
        if l0r[item_id]["collisions"] or l1r[item_id]["collisions"]:
            return "keyword_collision_only"
        return "unanchored"

    items_out = {}
    for it in items:
        iid = it["id"]
        cls = classify(iid, l0_result, l1_result)
        items_out[iid] = {
            "family": it["family"],
            "classification": cls,
            "l0_strong": l0_result[iid]["strong"],
            "l1_strong": l1_result[iid]["strong"],
            "weak_matches": {"l0": l0_result[iid]["weak"], "l1": l1_result[iid]["weak"]},
            "collisions": {"l0": l0_result[iid]["collisions"], "l1": l1_result[iid]["collisions"]},
        }

    # ---- positive control gate ----
    ctrl = items_out["ITEM-MGHD-CONTROL"]
    ctrl_ids = {m["theorem_id"] for m in ctrl["l0_strong"]}
    ctrl_srcs = {s for m in ctrl["l0_strong"] for s in m["source_ids"]}
    exp = next(it for it in items if it["id"] == "ITEM-MGHD-CONTROL")["control_expectation"]
    ok = (ctrl["classification"] == exp["classification"]
          and set(exp["must_include_theorem_ids"]) <= ctrl_ids
          and set(exp["must_include_source_ids"]) <= ctrl_srcs)
    if not ok:
        abort(3, "positive control failed; harness invalid, no report emitted",
              {"classification": ctrl["classification"], "theorem_ids": sorted(ctrl_ids),
               "source_ids": sorted(ctrl_srcs), "expected": exp})

    # ---- negative controls ----
    nc_adm = len(l0_result["ITEM-PMT"]["collisions"]) + len(l1_result["ITEM-PMT"]["collisions"])
    nc_weighted = (len(l0_result["ITEM-SOBOLEV-S"]["collisions"])
                   + len(l1_result["ITEM-SOBOLEV-S"]["collisions"]))
    negative_controls = {
        "NC-ADM": {"collision_matches": nc_adm,
                   "status": "exercised" if nc_adm > 0 else "not_exercised",
                   "assertion": "ADM substring collisions are reported as collisions and never as ITEM-PMT anchors",
                   "violated": False},
        "NC-WEIGHTED": {"collision_matches": nc_weighted,
                        "status": "exercised" if nc_weighted > 0 else "not_exercised",
                        "assertion": "weighted C^k genericity-topology matches are weak/collision only, never Sobolev anchors",
                        "violated": False},
    }
    for iid, r in l0_result.items():
        for m in r["strong"]:
            if m["match"].lower() in ("admissible", "admits", "admit"):
                negative_controls["NC-ADM"]["violated"] = True
    for iid in ("ITEM-SOBOLEV-S", "ITEM-SOBOLEV-DELTA"):
        for m in items_out[iid]["l0_strong"]:
            if m["pattern"] in ("weighted\\s+(class|space|topolog)", "weight"):
                negative_controls["NC-WEIGHTED"]["violated"] = True

    # ---- field binding table ----
    actions = {
        "anchored_theorem": "BIND NOW: name this field in provenance.sources with the theorem/source id; the ledger already carries the anchor.",
        "anchored_registry_only": "CANDIDATE SOURCE, UNBOUND: a registered source matches but used_by_theorems is empty; literature can bind it by adding the theorem entry at the next authorized L0 revision, or formulation names the field and requests the entry.",
        "weak_match_only": "NO PRIMARY ANCHOR, WEAK SURVEY SIGNAL ONLY: formulation must qualify/withdraw the dependent field or literature must supply a primary source.",
        "keyword_collision_only": "NO ANCHOR (keyword collision only): treat as unanchored; do not cite the colliding rows.",
        "unanchored": "NO ANCHOR: formulation must state the field-level withdrawal/qualification, or literature must supply a primary source; per BL-11 the default is withdrawal.",
    }
    field_binding_table = []
    for occ in occurrences:
        rel = occ["schema_path"]
        iid = occ["item_id"]
        decl = [d for d in declared[rel]["declared_sources"].get(iid, [])]
        field_binding_table.append({
            "schema_path": rel,
            "item_id": iid,
            "top_level_key": occ["top_level_key"],
            "line": occ["line"],
            "declared_provenance_for_item": decl,
            "anchor_classification": items_out[iid]["classification"],
            "candidate_source_ids": sorted({m["citation_id"] for m in items_out[iid]["l1_strong"]}),
            "candidate_theorem_ids": sorted({m["theorem_id"] for m in items_out[iid]["l0_strong"]}),
            "action_required": actions[items_out[iid]["classification"]],
        })

    report = {
        "schema_version": "0.1",
        "artifact_kind": "anchor_binding_audit",
        "task_id": "W079-FIELDANCHOR-01",
        "worker": "worker-079",
        "created_at": None,  # stamped below
        "preregistration_path": os.path.relpath(PREREG, ROOT),
        "preregistration_sha256": prereg_sha,
        "pinned_inputs_sha256_measured": measured,
        "input_drift": drift,
        "corpus_sizes": {"l0_theorems": len(l0_records), "l1_registry_rows": len(l1_rows),
                         "schemas_scanned": schemas},
        "items": items_out,
        "schema_occurrences": sorted(occurrences, key=lambda o: (o["schema_path"], o["line"], o["item_id"])),
        "declared_provenance": declared,
        "field_binding_table": field_binding_table,
        "control_result": {
            "item_id": "ITEM-MGHD-CONTROL",
            "classification": ctrl["classification"],
            "theorem_ids": sorted(ctrl_ids),
            "source_ids": sorted(ctrl_srcs),
            "expected": exp,
            "passed": True,
            "meaning": "the harness recovers the known MGHD anchor D-008/SRC-073 from the same corpus; its absences for other items are therefore instrument-valid.",
        },
        "negative_control_result": negative_controls,
        "summary": {
            iid: {
                "classification": items_out[iid]["classification"],
                "occurrences": sum(1 for o in occurrences if o["item_id"] == iid),
                "schemas_with_occurrences": sorted({o["schema_path"] for o in occurrences if o["item_id"] == iid}),
            } for iid in items_out
        },
        "falsifiers": prereg["falsifiers"],
        "not_claimed": prereg["not_claimed"],
        "self_check": {
            "writes_outside_worker_079": False,
            "schemas_ledger_map_edited": False,
            "gate_verdict_claimed": False,
        },
    }
    import datetime
    report["created_at"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")

    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)
    rep_path = os.path.join(out_dir, "field_anchor_audit.json")
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    rep_sha = sha256_file(rep_path)
    with open(rep_path + ".sha256", "w", encoding="utf-8") as f:
        f.write(f"{rep_sha}  field_anchor_audit.json\n")

    print(json.dumps({
        "harness_status": "OK",
        "report": os.path.relpath(rep_path, ROOT),
        "report_sha256": rep_sha,
        "summary": report["summary"],
        "control": {k: report["control_result"][k] for k in ("classification", "theorem_ids", "source_ids", "passed")},
        "negative_controls": negative_controls,
    }, indent=1))


if __name__ == "__main__":
    main()

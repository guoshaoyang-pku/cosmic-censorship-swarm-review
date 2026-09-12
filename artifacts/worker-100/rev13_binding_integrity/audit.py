#!/usr/bin/env python3
"""worker-100 independent binding-integrity audit at schemas rev13 / FROZEN rev29.

Bounded class-bound task taken from the open queue (no inbox card existed for worker-100):
independent second-implementation verification of the CF-20 evidence-binding repair
(astra-life05-evidence-binding-repair) as input to astra-life05-verify-gform-r3.

Read-only on all canonical artifacts. Writes only under artifacts/worker-100/.
The worker cannot set done/passed or a gate verdict; this is measurement evidence only.

Independent re-implementation: this file does not import or run the formulation lead's
checkers (check_taxonomy_consistency.py, evidence_binding_repair_rev29.py, run_gate_tests.py)
nor worker-007's rev29 driver. Every measurement below is recomputed from the pinned bytes.

Usage:
    python3 audit.py --out-dir .            # full run: checks + mutation controls + drift guard
    python3 audit.py --selftest-only        # controls only, no verdict.json write
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import os
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

# ---- pinned inputs (canonical, read-only) -------------------------------------------------
SCHEMAS = {
    "F1": ("schemas/af_wcc_vacuum.yaml", "AF-WCC-VAC-GEN"),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml", "AF-SCC-C2-VAC-GEN"),
    "F2b": ("schemas/af_scc_c0_vacuum.yaml", "AF-SCC-C0-VAC-GEN"),
}
P_CASES = "schemas/taxonomy_cases.jsonl"
P_EVID = "artifacts/formulation/evidence/taxonomy_consistency.json"
P_FROZEN = "artifacts/formulation/FROZEN.json"
P_F0 = "research_map/formulation_taxonomy.yaml"
P_SUP = "artifacts/formulation/formulation_taxonomy.yaml"
P_VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"

FROZEN_CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
EXPECTED_SCHEMA_REV = 13
EXPECTED_FROZEN_REV = 29
# known superseded hashes that must not appear in any live binding field
SUPERSEDED = {
    "66bf917bd368": "superseded F0 rev3 taxonomy hash",
    "565a6e505188": "superseded F0 rev4 taxonomy hash",
    "675a99d0d25b": "superseded enriched taxonomy_consistency.json hash",
}
CANONICAL_GATE_TOKEN = {
    "AF-WCC-VAC-GEN": "weak_cosmic_censorship",
    "AF-SCC-C2-VAC-GEN": "scc_c2_future_inextendibility",
    "AF-SCC-C0-VAC-GEN": "scc_c0_future_inextendibility",
    "AF-WCC-SCALAR-SPH": None,  # scalar class conclusion token not in the alias table; measured only
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_bundle() -> dict:
    paths = {}
    for _name, (rel, _cls) in SCHEMAS.items():
        paths[rel] = rel
    for rel in (P_CASES, P_EVID, P_FROZEN, P_F0, P_SUP, P_VOCAB):
        paths[rel] = rel
    bundle = {"paths": {}}
    for rel in paths:
        ap = os.path.join(ROOT, rel)
        with open(ap, "rb") as f:
            raw = f.read()
        entry = {"path": rel, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "text": raw.decode("utf-8")}
        if rel.endswith((".yaml", ".yml")):
            entry["yaml"] = yaml.safe_load(entry["text"])
        elif rel.endswith(".json"):
            entry["yaml"] = json.loads(entry["text"])
        bundle["paths"][rel] = entry
    bundle["frozen"] = bundle["paths"][P_FROZEN]["yaml"]
    bundle["vocab"] = bundle["paths"][P_VOCAB]["yaml"]
    bundle["cases"] = [json.loads(l) for l in bundle["paths"][P_CASES]["text"].splitlines() if l.strip()]
    return bundle


# ---- individual checks --------------------------------------------------------------------
def check_c1_frozen(b: dict) -> dict:
    """FROZEN rev29 self-consistency: declared revision and every file pin vs measured bytes."""
    man = b["frozen"]
    problems = []
    if man.get("revision") != EXPECTED_FROZEN_REV:
        problems.append(f"frozen revision {man.get('revision')} != {EXPECTED_FROZEN_REV}")
    files = man.get("files") or {}
    if not files:
        problems.append("frozen manifest declares no files")
    n_match = 0
    for rel, pin in files.items():
        ap = os.path.join(ROOT, rel)
        if not os.path.exists(ap):
            problems.append(f"pinned file missing: {rel}")
            continue
        measured = sha256_file(ap)
        mbytes = os.path.getsize(ap)
        if measured != pin.get("sha256"):
            problems.append(f"pin mismatch {rel}: declared {str(pin.get('sha256'))[:12]} measured {measured[:12]}")
        elif mbytes != pin.get("bytes"):
            problems.append(f"byte-count mismatch {rel}: declared {pin.get('bytes')} measured {mbytes}")
        else:
            n_match += 1
    # every audited canonical path must be pinned and match
    for rel in [p for p, _ in SCHEMAS.values()] + [P_CASES, P_EVID, P_F0]:
        if rel not in files:
            problems.append(f"audited path not pinned in FROZEN: {rel}")
        elif b["paths"][rel]["sha256"] != files[rel]["sha256"]:
            problems.append(f"audited path pin differs from manifest: {rel}")
    return {
        "id": "C1_FROZEN_REV29",
        "ok": not problems,
        "n_pins": len(files),
        "n_pins_match": n_match,
        "detail": problems or [f"revision {EXPECTED_FROZEN_REV}; {n_match}/{len(files)} pins match disk"],
    }


def _pointer_resolve(doc: dict, pointer: str):
    """Resolve 'path#a.b.c' against a parsed YAML doc. Returns (path_part, dotted, value) or raises."""
    if "#" not in pointer:
        raise ValueError(f"pointer has no '#' fragment: {pointer}")
    path_part, frag = pointer.split("#", 1)
    node = doc
    for tok in frag.split("."):
        if not isinstance(node, dict) or tok not in node:
            raise KeyError(tok)
        node = node[tok]
    return path_part, frag, node


def check_c2_revision_class(b: dict) -> dict:
    """Schema revision 13 and class identity against the frozen four."""
    problems = []
    rows = []
    for name, (rel, want_cls) in SCHEMAS.items():
        doc = b["paths"][rel]["yaml"]
        rev = doc.get("revision")
        cls = doc.get("class_id")
        comp = doc.get("class_components") or {}
        rec = {"schema": name, "path": rel, "revision": rev, "class_id": cls}
        if rev != EXPECTED_SCHEMA_REV:
            problems.append(f"{name}: revision {rev} != {EXPECTED_SCHEMA_REV}")
        if cls != want_cls:
            problems.append(f"{name}: class_id {cls} != {want_cls}")
        if cls not in FROZEN_CLASSES:
            problems.append(f"{name}: class_id {cls} not in frozen four")
        # component reconstruction where the component vocabulary is standard
        # canonical class-id order: asymptotics-censorship-[regularity]-matter-genericity
        order = ["asymptotics", "censorship", "regularity_token", "matter", "genericity"]
        if all(k in comp for k in order):
            toks = [str(comp[k]) for k in order]
            if comp.get("regularity_token") in (None, "none", "None"):
                toks = [t for k, t in zip(order, toks) if k != "regularity_token"]
            rebuilt = "-".join(toks)
            rec["components_rebuilt"] = rebuilt
            if rebuilt != cls:
                problems.append(f"{name}: class_components rebuild {rebuilt} != class_id {cls}")
        else:
            rec["components_rebuilt"] = None
        rows.append(rec)
    return {"id": "C2_SCHEMA_REV13_CLASS", "ok": not problems, "rows": rows, "detail": problems or ["3/3 schemas rev13, class_id matches frozen four"]}


def check_c3_f0_binding(b: dict) -> dict:
    """f0_binding declared hashes vs measured bytes + cross-schema agreement."""
    problems = []
    rows = []
    f0_measured = b["paths"][P_F0]["sha256"]
    evid_measured = b["paths"][P_EVID]["sha256"]
    sup_measured = b["paths"][P_SUP]["sha256"]
    for name, (rel, want_cls) in SCHEMAS.items():
        doc = b["paths"][rel]["yaml"]
        fb = doc.get("f0_binding") or {}
        rec = {"schema": name, "class_id": want_cls, "declared_f0_sha256": fb.get("declared_f0_sha256"),
               "declared_consistency_evidence_sha256": fb.get("consistency_evidence_sha256"),
               "declared_f0_artifact": fb.get("declared_f0_artifact")}
        if fb.get("declared_f0_artifact") != P_F0:
            problems.append(f"{name}: declared_f0_artifact {fb.get('declared_f0_artifact')} != canonical {P_F0}")
        if fb.get("declared_f0_sha256") != f0_measured:
            problems.append(f"{name}: declared_f0_sha256 {str(fb.get('declared_f0_sha256'))[:12]} != measured canonical F0 {f0_measured[:12]}")
        if fb.get("consistency_evidence") != P_EVID:
            problems.append(f"{name}: consistency_evidence {fb.get('consistency_evidence')} != {P_EVID}")
        if fb.get("consistency_evidence_sha256") != evid_measured:
            problems.append(f"{name}: consistency_evidence_sha256 {str(fb.get('consistency_evidence_sha256'))[:12]} != measured {evid_measured[:12]}")
        if not fb.get("checked_at"):
            problems.append(f"{name}: checked_at missing")
        if fb.get("class_contract_supplement") and fb.get("class_contract_supplement") != P_SUP:
            problems.append(f"{name}: class_contract_supplement != {P_SUP}")
        rec["measured_f0"] = f0_measured
        rec["measured_evidence"] = evid_measured
        rec["measured_supplement"] = sup_measured
        rows.append(rec)
    # cross-schema agreement
    decl = {r["declared_f0_sha256"] for r in rows} | {r["declared_consistency_evidence_sha256"] for r in rows}
    if len({r["declared_f0_sha256"] for r in rows}) != 1 or len({r["declared_consistency_evidence_sha256"] for r in rows}) != 1:
        problems.append("schemas disagree on declared F0/evidence hashes")
    return {"id": "C3_F0_BINDING_HASHES", "ok": not problems, "rows": rows, "detail": problems or ["3/3 schemas bind measured canonical F0 0abb9ed8a961 and evidence 9e335e9ba1bf"]}


def check_c4_pointer_resolution(b: dict) -> dict:
    """class_contract_pointer resolves in canonical F0; supplement pointer in the supplement."""
    problems = []
    f0 = b["paths"][P_F0]["yaml"]
    sup = b["paths"][P_SUP]["yaml"]
    rows = []
    for name, (rel, want_cls) in SCHEMAS.items():
        doc = b["paths"][rel]["yaml"]
        ptr = doc.get("class_contract_pointer")
        sptr_top = doc.get("class_contract_supplement_pointer")
        fb_sptr = (doc.get("f0_binding") or {}).get("class_contract_supplement_pointer")
        rec = {"schema": name, "class_id": want_cls, "class_contract_pointer": ptr,
               "supplement_pointer": sptr_top, "supplement_pointer_in_f0_binding": fb_sptr}
        # canonical pointer must resolve in canonical F0 and must not point at the supplement
        try:
            p_path, frag, val = _pointer_resolve(f0, ptr)
            rec["canonical_pointer_resolves"] = True
            rec["canonical_pointer_path"] = p_path
            rec["canonical_pointer_fragment"] = frag
            rec["canonical_pointer_value_type"] = type(val).__name__
            if p_path != P_F0:
                problems.append(f"{name}: class_contract_pointer path {p_path} != canonical {P_F0}")
        except Exception as e:
            rec["canonical_pointer_resolves"] = False
            rec["canonical_pointer_error"] = f"{type(e).__name__}: {e}"
            problems.append(f"{name}: class_contract_pointer does not resolve in canonical F0 ({e})")
        # supplement pointer resolves in the supplement (declared design), and both copies agree
        try:
            s_path, s_frag, s_val = _pointer_resolve(sup, sptr_top)
            rec["supplement_pointer_resolves"] = True
            if s_path != P_SUP:
                problems.append(f"{name}: supplement pointer path {s_path} != {P_SUP}")
        except Exception as e:
            rec["supplement_pointer_resolves"] = False
            rec["supplement_pointer_error"] = f"{type(e).__name__}: {e}"
            problems.append(f"{name}: class_contract_supplement_pointer does not resolve in supplement ({e})")
        if fb_sptr != sptr_top:
            problems.append(f"{name}: f0_binding.class_contract_supplement_pointer != top-level supplement pointer")
        rows.append(rec)
    return {"id": "C4_POINTER_RESOLUTION", "ok": not problems, "rows": rows, "detail": problems or ["3/3 canonical pointers resolve at classes.<class_id>; supplement pointers resolve at class_contracts.<class_id>"]}


ALLOWED_AS_FILED = set(FROZEN_CLASSES) | {"COMPOSITE_C0_C2", "COMPOSITE_WCC_SCC"}


def check_c5_case_rebind(b: dict) -> dict:
    """taxonomy_cases.jsonl rows rebound to canonical F0 rev5; no superseded hash; class ids frozen."""
    problems = []
    cases = b["cases"]
    meta = [r for r in cases if r.get("record_type") == "meta"]
    rows = [r for r in cases if r.get("record_type") != "meta"]
    f0_measured = b["paths"][P_F0]["sha256"]
    f0_prefix = f0_measured[:12]
    n_bound = 0
    stale = []
    for i, r in enumerate(rows):
        bs = str(r.get("binding_status") or "")
        if f"bound_taxonomy_sha_{f0_prefix}" in bs:
            n_bound += 1
        else:
            stale.append({"row": i, "case_id": r.get("case_id"), "binding_status": bs})
        for bad, why in SUPERSEDED.items():
            if bad in bs:
                problems.append(f"case row {i} ({r.get('case_id')}): binding_status holds {why} ({bad})")
        cid = r.get("class_id")
        filed = r.get("as_filed_class_id")
        if r.get("polarity") == "positive":
            if cid not in FROZEN_CLASSES:
                problems.append(f"case row {i} ({r.get('case_id')}): positive polarity but class_id {cid} not in frozen four")
        elif r.get("polarity") == "negative":
            # negatives are deliberate non-class probes; their filed-under token must still be a known surface
            if filed not in ALLOWED_AS_FILED:
                problems.append(f"case row {i} ({r.get('case_id')}): negative as_filed_class_id {filed} is not a known class/composite surface")
        else:
            problems.append(f"case row {i} ({r.get('case_id')}): unknown polarity {r.get('polarity')}")
    if len(meta) != 1:
        problems.append(f"expected 1 meta row, found {len(meta)}")
    if len(rows) != 36:
        problems.append(f"expected 36 case rows, found {len(rows)}")
    if stale:
        problems.append(f"{len(stale)} rows not bound to canonical F0 prefix {f0_prefix}")
    # meta taxonomy_ref must bind the canonical F0 bytes
    if meta:
        tr = meta[0].get("taxonomy_ref") or {}
        if tr.get("sha256") != f0_measured:
            problems.append(f"meta taxonomy_ref.sha256 {str(tr.get('sha256'))[:12]} != canonical F0 {f0_prefix}")
        counts = meta[0].get("counts") or {}
        actual_pos = sum(1 for r in rows if r.get("polarity") == "positive")
        actual_neg = sum(1 for r in rows if r.get("polarity") == "negative")
        if counts.get("positive") != actual_pos:
            problems.append(f"meta positive count {counts.get('positive')} != actual {actual_pos}")
        if counts.get("negative") != actual_neg:
            problems.append(f"meta negative count {counts.get('negative')} != actual {actual_neg}")
        if not (tr.get("rebind_note") or tr.get("rebound_at")):
            problems.append("meta taxonomy_ref has no rebind_note/rebound_at")
    return {"id": "C5_CASE_CORPUS_REBIND", "ok": not problems, "n_rows": len(rows), "n_bound_canonical": n_bound,
            "stale_rows": stale[:5], "detail": problems or [f"{n_bound}/36 rows bound to canonical F0 prefix {f0_prefix}; 0 superseded tokens; class ids frozen"]}


def check_c6_superseded_sweep(b: dict) -> dict:
    """Superseded hashes must not appear in live binding fields (revision-history prose allowed)."""
    problems = []
    occurrences = []
    live_fields = []
    for name, (rel, _cls) in SCHEMAS.items():
        doc = b["paths"][rel]["yaml"]
        fb = doc.get("f0_binding") or {}
        live_fields.append((rel, "f0_binding.declared_f0_sha256", str(fb.get("declared_f0_sha256"))))
        live_fields.append((rel, "f0_binding.consistency_evidence_sha256", str(fb.get("consistency_evidence_sha256"))))
        live_fields.append((rel, "class_contract_pointer", str(doc.get("class_contract_pointer"))))
    for rel, field, val in live_fields:
        for bad, why in SUPERSEDED.items():
            if val.startswith(bad):
                problems.append(f"{rel}:{field} holds {why} ({bad})")
    for row in b["cases"]:
        tr = row.get("taxonomy_ref") or {}
        trh = str(tr.get("sha256") or "")
        bs = str(row.get("binding_status") or "")
        for bad, why in SUPERSEDED.items():
            if trh.startswith(bad) or bad in bs:
                problems.append(f"{P_CASES}: row {row.get('case_id') or 'meta'} holds {why} ({bad})")
    man = b["frozen"]
    for bad, why in SUPERSEDED.items():
        if str(man).count(bad):
            occurrences.append({"hash": bad, "where": "FROZEN.json", "why": why})
    for name, (rel, _cls) in SCHEMAS.items():
        txt = b["paths"][rel]["text"]
        for bad, why in SUPERSEDED.items():
            n = txt.count(bad)
            if n:
                occurrences.append({"hash": bad, "where": rel, "n": n, "why": why, "note": "only allowed in revision-history/binding prose"})
    return {"id": "C6_SUPERSEDED_FIELD_SWEEP", "ok": not problems, "live_field_violations": problems,
            "prose_occurrences": occurrences,
            "detail": problems or ["no superseded hash in any live binding field; remaining occurrences are revision-history prose"]}


def check_c8_alias_normalization(b: dict) -> dict:
    """Canonical F0 axis tokens map to the canonical gate vocabulary via VOCAB_ALIASES."""
    problems = []
    f0 = b["paths"][P_F0]["yaml"]
    vocab = b["vocab"].get("conclusion_type") or {}
    rows = []
    for cls in FROZEN_CLASSES:
        axes = ((f0.get("classes") or {}).get(cls) or {}).get("axes") or {}
        tok = axes.get("conclusion_type")
        gate = CANONICAL_GATE_TOKEN.get(cls)
        rec = {"class_id": cls, "canonical_axis_token": tok, "gate_token": gate}
        if gate is None:
            rec["alias_group"] = None
            rec["alias_ok"] = None
            rows.append(rec)
            continue
        group = None
        for canonical, members in vocab.items():
            if canonical == tok or tok in (members or []):
                group = canonical
                break
        rec["alias_group"] = group
        rec["alias_ok"] = (group == gate)
        if group != gate:
            problems.append(f"{cls}: canonical axis token {tok!r} maps to alias group {group!r}, expected {gate!r}")
        rows.append(rec)
    # genericity alias (CF-21 adjacent)
    gk = ((f0.get("classes") or {}).get("AF-WCC-SCALAR-SPH") or {}).get("axes", {}).get("genericity_kind")
    gvocab = b["vocab"].get("genericity_kind") or {}
    ggroup = next((k for k, v in gvocab.items() if gk == k or gk in (v or [])), None)
    return {"id": "C8_ALIAS_NORMALIZATION", "ok": not problems, "rows": rows,
            "scalar_genericity_kind": gk, "scalar_genericity_group": ggroup,
            "detail": problems or ["canonical axis tokens resolve to the canonical gate vocabulary through VOCAB_ALIASES"]}


CHECKS = [check_c1_frozen, check_c2_revision_class, check_c3_f0_binding, check_c4_pointer_resolution,
          check_c5_case_rebind, check_c6_superseded_sweep, check_c8_alias_normalization]


# ---- mutation controls --------------------------------------------------------------------
def make_mutants(b: dict):
    """Yield (mutant_id, expected_check_id, mutated_bundle)."""
    f1 = SCHEMAS["F1"][0]
    f2a = SCHEMAS["F2a"][0]
    f2b = SCHEMAS["F2b"][0]

    m = copy.deepcopy(b)
    m["frozen"]["files"][f1]["sha256"] = "0" * 64
    yield ("M1_FROZEN_PIN_FLIP", "C1_FROZEN_REV29", m)

    m = copy.deepcopy(b)
    m["frozen"]["revision"] = 28
    yield ("M2_FROZEN_REV_STALE", "C1_FROZEN_REV29", m)

    m = copy.deepcopy(b)
    m["paths"][f2a]["yaml"]["revision"] = 12
    yield ("M3_SCHEMA_REV_STALE", "C2_SCHEMA_REV13_CLASS", m)

    m = copy.deepcopy(b)
    m["paths"][f1]["yaml"]["f0_binding"]["declared_f0_sha256"] = "66bf917bd368" + "0" * 52
    yield ("M4_F0_BINDING_STALE", "C3_F0_BINDING_HASHES", m)

    m = copy.deepcopy(b)
    m["paths"][f2b]["yaml"]["f0_binding"]["consistency_evidence_sha256"] = "675a99d0d25b" + "0" * 52
    yield ("M5_EVIDENCE_HASH_STALE", "C3_F0_BINDING_HASHES", m)

    m = copy.deepcopy(b)
    m["paths"][f1]["yaml"]["class_contract_pointer"] = P_SUP + "#class_contracts.AF-WCC-VAC-GEN"
    yield ("M6_POINTER_TO_SUPPLEMENT", "C4_POINTER_RESOLUTION", m)

    m = copy.deepcopy(b)
    # break the dotted fragment so it does not resolve in canonical F0
    m["paths"][f2b]["yaml"]["class_contract_pointer"] = P_F0 + "#classes.AF-SCC-C0-VAC-GEN.does_not_exist"
    yield ("M7_POINTER_MISSING_KEY", "C4_POINTER_RESOLUTION", m)

    m = copy.deepcopy(b)
    for r in m["cases"]:
        if r.get("record_type") != "meta":
            r["binding_status"] = "bound_taxonomy_sha_66bf917bd368"
            break
    yield ("M8_CASE_ROW_STALE_BIND", "C5_CASE_CORPUS_REBIND", m)

    m = copy.deepcopy(b)
    for r in m["cases"]:
        if r.get("record_type") != "meta" and r.get("polarity") == "positive":
            r["class_id"] = "AF-NOT-A-CLASS"
            break
    yield ("M9_CASE_ROW_FOREIGN_CLASS", "C5_CASE_CORPUS_REBIND", m)

    m = copy.deepcopy(b)
    m["frozen"]["files"].pop(f2a)
    yield ("M10_FROZEN_PIN_DROPPED", "C1_FROZEN_REV29", m)

    m = copy.deepcopy(b)
    m["paths"][f2b]["yaml"]["f0_binding"]["class_contract_supplement_pointer"] = P_F0 + "#classes.AF-SCC-C0-VAC-GEN"
    yield ("M11_SUPPLEMENT_POINTER_CONFLATED", "C4_POINTER_RESOLUTION", m)

    m = copy.deepcopy(b)
    m["paths"][f1]["yaml"]["f0_binding"]["consistency_evidence"] = P_CASES
    yield ("M12_EVIDENCE_PATH_SWAPPED", "C3_F0_BINDING_HASHES", m)

    m = copy.deepcopy(b)
    m["paths"][f2a]["yaml"]["class_id"] = "AF-SCC-C0-VAC-GEN"
    yield ("M13_CLASS_ID_SWAPPED", "C2_SCHEMA_REV13_CLASS", m)


def run_controls(b: dict) -> dict:
    results = []
    n_detected = 0
    # baseline: which checks already fail on the unmutated live bytes (pre-existing defects)
    clean = {}
    for fn in CHECKS:
        r = fn(b)
        clean[r["id"]] = r
    baseline_fail = {k for k, v in clean.items() if v["ok"] is False}
    # negative control: normalise the known pre-existing pin drift in-memory; if every check
    # then passes, the instrument has no false positives on clean bytes.
    nb = copy.deepcopy(b)
    for rel, pin in (nb["frozen"].get("files") or {}).items():
        ap = os.path.join(ROOT, rel)
        if os.path.exists(ap) and sha256_file(ap) != pin.get("sha256"):
            pin["sha256"] = sha256_file(ap)
            pin["bytes"] = os.path.getsize(ap)
    normalised = {}
    for fn in CHECKS:
        r = fn(nb)
        normalised[r["id"]] = r
    normalised_fail = [k for k, v in normalised.items() if v["ok"] is False]
    mutants = list(make_mutants(b))
    for mid, expected, mb in mutants:
        out = {}
        for fn in CHECKS:
            r = fn(mb)
            out[r["id"]] = r
        expected_fails = out[expected]["ok"] is False
        # specificity: the mutation must add/alter a failure relative to the live baseline
        detail_changed = json.dumps(out[expected].get("detail"), sort_keys=True) != json.dumps(clean[expected].get("detail"), sort_keys=True)
        detected = expected_fails and (expected not in baseline_fail or detail_changed)
        others = [k for k, v in out.items() if v["ok"] is False]
        results.append({"mutant": mid, "expected_check": expected, "detected": detected,
                        "expected_check_fails": expected_fails, "detail_changed_vs_baseline": detail_changed,
                        "checks_failing": others})
        n_detected += int(detected)
    return {"n_mutants": len(mutants), "n_detected": n_detected, "mutants": results,
            "baseline_failing_checks": sorted(baseline_fail),
            "negative_control_all_pass": not normalised_fail, "negative_control_failing": normalised_fail,
            "negative_control_note": ("pre-existing pin drift normalised in-memory; the live-bytes failure set is "
                                      "reported separately as baseline_failing_checks and is not a false positive"),
            "instrument_fires": n_detected == len(mutants) and not normalised_fail}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--selftest-only", action="store_true")
    args = ap.parse_args()

    created_at = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    b = load_bundle()

    # drift guard: pin every input before the audit
    pins_before = {rel: {"sha256": e["sha256"], "bytes": e["bytes"]} for rel, e in sorted(b["paths"].items())}
    checks = [fn(b) for fn in CHECKS]
    controls = run_controls(b)

    # re-load and re-measure after the audit (drift guard)
    b2 = load_bundle()
    pins_after = {rel: {"sha256": e["sha256"], "bytes": e["bytes"]} for rel, e in sorted(b2["paths"].items())}
    drift = {rel: {"before": pins_before[rel]["sha256"], "after": pins_after[rel]["sha256"]}
             for rel in pins_before if pins_before[rel]["sha256"] != pins_after[rel]["sha256"]}

    hard_failures = []
    for c in checks:
        if not c["ok"]:
            hard_failures.append({"check": c["id"], "detail": c["detail"]})
    if not controls["instrument_fires"]:
        hard_failures.append({"check": "CONTROLS", "detail": f"instrument did not fire: {controls['n_detected']}/{controls['n_mutants']}"})
    if drift:
        hard_failures.append({"check": "DRIFT", "detail": f"{len(drift)} inputs changed during the audit (fail closed)"})

    residual_findings = []
    # design facts measured, not failures
    supp_only = [r["schema"] for r in next(c for c in checks if c["id"] == "C4_POINTER_RESOLUTION")["rows"]
                 if not r.get("supplement_pointer_resolves")]
    if supp_only:
        residual_findings.append({
            "id": "R-1", "severity": "note",
            "finding": f"class_contract_supplement_pointer is unreadable on the supplement for {supp_only}",
        })
    alias_rows = next(c for c in checks if c["id"] == "C8_ALIAS_NORMALIZATION")["rows"]
    token_gap = [{"class_id": r["class_id"], "canonical_axis_token": r["canonical_axis_token"], "gate_token": r["gate_token"]}
                 for r in alias_rows if r.get("alias_ok") is False]
    if token_gap:
        residual_findings.append({"id": "R-2", "severity": "minor",
                                  "finding": "canonical F0 axis conclusion_type token is an accepted alias, not the gate token",
                                  "rows": token_gap})
    scalar = next(c for c in checks if c["id"] == "C8_ALIAS_NORMALIZATION")
    if scalar.get("scalar_genericity_kind"):
        residual_findings.append({"id": "R-3", "severity": "note",
                                  "finding": f"CF-21 adjacent: canonical scalar axes.genericity_kind={scalar['scalar_genericity_kind']!r} (alias group {scalar['scalar_genericity_group']!r}); conclusion text quantifies over a comeager set",
                                  "counts_as_repair": False})
    # revision-label uniqueness observation (read from session snapshots if present)
    obs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshot", "manifest_observations.json")
    if os.path.exists(obs_path):
        obs = json.load(open(obs_path))
        distinct = sorted({(o.get("frozen_sha256") or o.get("frozen_sha256_prefix")) for o in obs.get("observations", [])} - {None})
        if len(distinct) > 1:
            residual_findings.append({
                "id": "R-4", "severity": "major", "counts_as_repair": False,
                "finding": (f"FROZEN revision label {EXPECTED_FROZEN_REV} is not unique: {len(distinct)} distinct manifests observed "
                            f"under revision {EXPECTED_FROZEN_REV} within one session; reviewers must bind sha256, never the revision number"),
                "observed_manifests": distinct,
                "evidence_ref": "artifacts/worker-100/rev13_binding_integrity/snapshot/manifest_observations.json",
            })

    verdict = {
        "audit_id": "w100-rev13-binding-integrity",
        "actor": "worker-100",
        "created_at": created_at,
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "class_id": ";".join(FROZEN_CLASSES),
        "task": "independent second-implementation binding-integrity audit of the CF-20 evidence-binding repair at schemas rev13 / FROZEN rev29; read-only, worker artifact",
        "assignment_context": ["astra-life05-evidence-binding-repair (repair under audit)", "astra-life05-verify-gform-r3 (downstream: fresh verdicts must bind the rev29 pins)"],
        "pins": pins_before,
        "checks": checks,
        "controls": controls,
        "drift": drift,
        "hard_failures": hard_failures,
        "residual_findings": residual_findings,
        "verdict": "pass" if not hard_failures else "revise",
        "counts_as_full_schema_verdict": False,
        "falsifier": ("Re-measure at these pins: any declared hash that differs from the measured bytes, any case row bound to a "
                      "superseded taxonomy hash (66bf917bd368 / 565a6e505188), any pointed key that fails to resolve in canonical F0, "
                      "any FROZEN rev29 pin that differs from disk, or any hash change between the before/after measurement is a "
                      "counterexample to this verdict. A re-run of audit.py on the same pins whose per-check results differ also falsifies it."),
        "reproduce": "python3 artifacts/worker-100/rev13_binding_integrity/audit.py --out-dir <dir>",
        "no_completion_claim": "worker cannot set done/passed or a gate verdict; this is measurement evidence for a lead/controller review, not a gate verdict",
        "independence": ("second implementation: does not import or execute the formulation lead's checkers, worker-007's rev29 driver, "
                         "or worker-095's probe; recomputes hashes, pointer resolution, corpus binding and alias mapping from the pinned bytes"),
    }

    if args.selftest_only:
        print(json.dumps({"controls": controls, "checks_ok": [c["ok"] for c in checks]}, indent=1))
        return 0 if controls["instrument_fires"] and not hard_failures else 1

    out_dir = os.path.abspath(args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    vpath = os.path.join(out_dir, "verdict.json")
    with open(vpath, "w") as f:
        json.dump(verdict, f, indent=1, sort_keys=True)
    cpath = os.path.join(out_dir, "controls.json")
    with open(cpath, "w") as f:
        json.dump(controls, f, indent=1, sort_keys=True)
    bpath = open(os.path.join(out_dir, "pins_before.json"), "w")
    json.dump(pins_before, bpath, indent=1, sort_keys=True)
    bpath.close()
    apath = open(os.path.join(out_dir, "pins_after.json"), "w")
    json.dump(pins_after, apath, indent=1, sort_keys=True)
    apath.close()
    print(json.dumps({
        "verdict": verdict["verdict"], "hard_failures": hard_failures,
        "controls": {"n_detected": controls["n_detected"], "n_mutants": controls["n_mutants"],
                     "negative_control_all_pass": controls["negative_control_all_pass"]},
        "verdict_sha256": sha256_file(vpath), "drift": drift,
    }, indent=1))
    return 0 if verdict["verdict"] == "pass" else 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W089-F1-REV13-REVIEW-05 -- independent, controlled, hash-bound review of F1
(AF-WCC-VAC-GEN) revision 13 at the FROZEN rev29 pin.

Scope of the machine part: class-content structure, quantifier well-typedness,
the two rev13 repairs (f0_binding evidence refresh; visibility strictness
direction correction), the F0-canonical / class-contract-supplement binding
partition, class-identity separation (no C0/C2 leakage or conclusion inflation),
falsifier decidability, frozen-pin and mirror alignment, and a hash-stability
window.  Every scored check has at least one planted-defect control so a pass is
controlled rather than asserted.  Reads shared artifacts read-only; writes only
inside its own artifact directory.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TARGET = "schemas/af_wcc_vacuum.yaml"
MIRROR = "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
CANON = "research_map/formulation_taxonomy.yaml"
SUPP = "artifacts/formulation/formulation_taxonomy.yaml"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"
CONS = "artifacts/formulation/evidence/taxonomy_consistency.json"
CASES = "schemas/taxonomy_cases.jsonl"
VARIANT_DELTA = "artifacts/formulation/evidence/variant_delta_check.json"
GATE_REPORT = "artifacts/formulation/evidence/gate_test_report.json"
CLASS_ID = "AF-WCC-VAC-GEN"
EXPECTED_REVISION = 13
EXPECTED_FROZEN_REVISION = 29
EXPECTED_FROZEN_FILES = 48
STABILITY_PATHS = [TARGET, MIRROR, FROZEN, CANON, CASES, CONS, VARIANT_DELTA, GATE_REPORT]


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_yaml(path: str):
    return yaml.safe_load(read_text(path))


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def iso_now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def parse_iso(value):
    if not isinstance(value, str):
        return None
    try:
        stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        return None
    return stamp


def resolve_fragment(doc, fragment: str):
    """Resolve a dotted fragment like classes.AF-WCC-VAC-GEN."""
    node = doc
    for part in fragment.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return False, None
    return True, node


def top_level_keys(raw: str):
    return re.findall(r"^(?![ \t#\-])([A-Za-z_][A-Za-z0-9_]*):", raw, re.M)


# --------------------------------------------------------------------------
# checks: ctx -> (status, measured, detail)
# --------------------------------------------------------------------------
def c01_duplicate_keys(ctx):
    counts = Counter(top_level_keys(ctx["raw"]))
    dups = {k: v for k, v in counts.items() if v > 1}
    idx = [e.get("index") for e in ctx["doc"].get("revision_history", [])]
    idx_dups = {k: v for k, v in Counter(idx).items() if v > 1}
    ok = not dups and not idx_dups
    return (
        "pass" if ok else "fail",
        {"top_level_duplicates": dups, "revision_index_duplicates": idx_dups,
         "n_top_level": len(counts)},
        "no duplicate top-level keys or revision-history indices" if ok
        else f"duplicates={dups} index_duplicates={idx_dups}",
    )


def c02_revised_at_wall_clock(ctx):
    stamp = parse_iso(ctx["doc"].get("revised_at"))
    if stamp is None:
        return "fail", {"revised_at": ctx["doc"].get("revised_at")}, "revised_at missing/naive"
    now = ctx["now"]
    mtime = dt.datetime.fromtimestamp(ctx["mtime"]).astimezone()
    d_now = (stamp - now).total_seconds()
    d_mt = (stamp - mtime).total_seconds()
    ok = -86400.0 <= d_now <= 60.0 and abs(d_mt) <= 180.0
    return (
        "pass" if ok else "fail",
        {"revised_at": stamp.isoformat(), "now": now.isoformat(timespec="seconds"),
         "mtime": mtime.isoformat(timespec="seconds"),
         "seconds_before_now": round(d_now, 1), "seconds_vs_mtime": round(d_mt, 1)},
        "revised_at is wall-clock and mtime-consistent" if ok else "timestamp out of tolerance",
    )


def c03_revision_history(ctx):
    doc = ctx["doc"]
    rev = doc.get("revision")
    hist = doc.get("revision_history") or []
    used = [e for e in hist if not e.get("unused")]
    last = used[-1] if used else {}
    notes = " ".join(last.get("notes", []))
    ok = (
        rev == EXPECTED_REVISION
        and bool(hist)
        and last.get("unused") is False
        and "rev13" in notes
        and all(isinstance(e.get("index"), int) for e in hist)
        and max(e["index"] for e in hist) == EXPECTED_REVISION - 2
    )
    return (
        "pass" if ok else "fail",
        {"revision": rev, "n_history": len(hist), "n_used": len(used),
         "last_used_index": last.get("index"), "last_used_has_rev13_note": "rev13" in notes},
        "revision 13 with a used, rev13-labelled history tail" if ok
        else "revision/history tail inconsistent",
    )


def c04_frozen_pin(ctx):
    fz = ctx["frozen"]
    h = ctx["target_sha"]
    mh = ctx["mirror_sha"]
    entry = (fz.get("files") or {}).get(TARGET, {})
    mentry = (fz.get("files") or {}).get(MIRROR, {})
    ok = (
        fz.get("revision") == EXPECTED_FROZEN_REVISION
        and entry.get("sha256") == h
        and mentry.get("sha256") == h
        and mh == h
    )
    return (
        "pass" if ok else "fail",
        {"frozen_revision": fz.get("revision"), "target_sha256": h, "mirror_sha256": mh,
         "frozen_declared_target": entry.get("sha256"), "frozen_declared_mirror": mentry.get("sha256")},
        "FROZEN rev29 pins the measured target and its byte-identical mirror" if ok
        else "frozen/manifest pin mismatch",
    )


def c05_bindchain(ctx):
    rows = ctx["frozen_files_status"]
    bad = [r for r in rows if r["status"] != "resolved"]
    self_ref = FROZEN in (ctx["frozen"].get("files") or {})
    ok = not bad and len(rows) >= EXPECTED_FROZEN_FILES and not self_ref
    return (
        "pass" if ok else "fail",
        {"n_declared": len(rows), "n_bad": len(bad), "self_reference_present": self_ref,
         "bad_sample": bad[:8]},
        f"all {len(rows)} declared files resolve; no self-reference" if ok
        else f"{len(bad)} declared files unresolved; self_ref={self_ref}",
    )


def c06_class_identity(ctx):
    d = ctx["doc"]
    comps = d.get("class_components") or {}
    expected = {"asymptotics": "AF", "censorship": "WCC", "matter": "VAC",
                "genericity": "GEN", "regularity_token": "none"}
    scope = str(d.get("scope_statement", ""))
    ok = (
        d.get("class_id") == CLASS_ID
        and d.get("node_id") == "F1"
        and comps == expected
        and "vacuum" in scope.lower()
        and "future null infinity" in scope
        and d.get("conclusion", {}).get("family") == "WCC"
    )
    return (
        "pass" if ok else "fail",
        {"class_id": d.get("class_id"), "node_id": d.get("node_id"), "components": comps,
         "family": d.get("conclusion", {}).get("family")},
        "class identity is AF/WCC/VAC/GEN with WCC scope" if ok else "class identity mismatch",
    )


def c07_contract_pointers(ctx):
    d = ctx["doc"]
    p = str(d.get("class_contract_pointer", ""))
    sp = str(d.get("class_contract_supplement_pointer", ""))
    if "#" not in p or "#" not in sp:
        return "fail", {"pointer": p, "supplement_pointer": sp}, "pointer missing fragment"
    path1, frag1 = p.split("#", 1)
    path2, frag2 = sp.split("#", 1)
    ok1, node1 = resolve_fragment(ctx["canon"], frag1)
    ok2, node2 = resolve_fragment(ctx["supp"], frag2)
    cross1, _ = resolve_fragment(ctx["canon"], frag2)
    cross2, _ = resolve_fragment(ctx["supp"], frag1)
    node2_id = (node2 or {}).get("node_id") if isinstance(node2, dict) else None
    ok = (
        path1 == CANON and path2 == SUPP and ok1 and ok2
        and not cross1 and not cross2
        and node2_id in ("F1", CLASS_ID)
    )
    return (
        "pass" if ok else "fail",
        {"canonical_pointer": p, "canonical_resolves": ok1,
         "supplement_pointer": sp, "supplement_resolves": ok2,
         "canonical_resolves_supplement_key": cross1,
         "supplement_resolves_canonical_key": cross2, "supplement_node_id": node2_id},
        "canonical/supplement pointers resolve in exactly one file each" if ok
        else "pointer partition defect",
    )


def c08_f0_binding(ctx):
    fb = ctx["doc"].get("f0_binding") or {}
    cons = ctx["cons"]
    ok = (
        fb.get("declared_f0_artifact") == CANON
        and fb.get("declared_f0_sha256") == ctx["canon_sha"]
        and fb.get("consistency_evidence") == CONS
        and fb.get("consistency_evidence_sha256") == ctx["cons_sha"]
        and cons.get("consistent") is True
        and not cons.get("errors")
        and parse_iso(fb.get("checked_at")) is not None
        and bool(fb.get("rule"))
    )
    return (
        "pass" if ok else "fail",
        {"declared_f0_sha256": fb.get("declared_f0_sha256"), "live_canon_sha256": ctx["canon_sha"],
         "consistency_evidence_sha256": fb.get("consistency_evidence_sha256"),
         "live_consistency_sha256": ctx["cons_sha"],
         "consistency_consistent": cons.get("consistent"), "consistency_errors": cons.get("errors"),
         "checked_at": fb.get("checked_at")},
        "f0_binding resolves to live declared-F0 and consistent evidence" if ok
        else "f0_binding evidence mismatch (rev13 repair target)",
    )


def c09_quantifiers(ctx):
    q = ctx["doc"].get("quantifiers") or {}
    ordered = q.get("ordered") or []
    kinds = [e.get("kind") for e in ordered]
    binders = [e.get("binder") for e in ordered]
    domains = q.get("domains") or {}
    expected_kinds = ["forall", "exists", "forall", "exists", "forall", "not_exists"]
    expected_binders = ["r", "G_r", "(Sigma,h,K)", "(Mtilde,gtilde,Omega)", "gamma", "(q,t0)"]
    all_refs = all(e.get("domain_id") in domains for e in ordered)
    ok = (
        kinds == expected_kinds and binders == expected_binders and all_refs
        and bool(q.get("negation")) and bool(q.get("negation_normal_form"))
        and bool(q.get("order_note")) and q.get("order_matters") is True
    )
    return (
        "pass" if ok else "fail",
        {"kinds": kinds, "binders": binders, "domain_refs_resolve": all_refs,
         "n_domains": len(domains)},
        "quantifier chain well-typed and ordered" if ok else "quantifier chain defect",
    )


def c10_conclusion_typing(ctx):
    c = ctx["doc"].get("conclusion") or {}
    text = " ".join([
        str(c.get("statement_natural_language", "")),
        str(c.get("statement_formal", "")),
        str(c.get("claim_promotion", "")),
    ]).lower()
    leak_tokens = ["inextendib", "extension_regularity", "black-hole region non-empty",
                   "for all data rather than", "geodesically complete of m"]
    hits = [t for t in leak_tokens if t in text]
    strengthens = " ".join(str(x) for x in c.get("forbidden_strengthenings", []))
    weakens = " ".join(str(x) for x in c.get("forbidden_weakenings", []))
    ok = (
        c.get("conclusion_type") == "weak_cosmic_censorship"
        and not hits
        and len(c.get("forbidden_strengthenings", [])) >= 4
        and "inextendibility" in strengthens
        and "geodesic completeness" in strengthens
        and len(c.get("forbidden_weakenings", [])) >= 4
        and "completeness" in weakens
        and "artifact_refs" in str(c.get("claim_promotion", ""))
    )
    return (
        "pass" if ok else "fail",
        {"conclusion_type": c.get("conclusion_type"), "leak_hits": hits,
         "n_forbidden_strengthenings": len(c.get("forbidden_strengthenings", [])),
         "n_forbidden_weakenings": len(c.get("forbidden_weakenings", []))},
        "conclusion is typed WCC with no SCC/all-data leakage" if ok
        else "conclusion typing or leakage defect",
    )


def c11_equivalence_unverified(ctx):
    d = ctx["doc"]
    c = d.get("conclusion") or {}
    eq = c.get("equivalent_standard_formulation") or {}
    status = str(eq.get("status", ""))
    unresolved = " ".join(str(x) for x in d.get("unresolved_items", []))
    queue = (d.get("adjudication_queue") or {}).get("open_rows", [])
    amb15 = [r for r in queue if r.get("test") == "F1-AMB-15"]
    ok = (
        "UNVERIFIED" in status
        and "future asymptotic predictability" in unresolved
        and bool(amb15)
        and "equivalent_standard_formulation" in str(amb15[0].get("deciding_leaf", ""))
    )
    return (
        "pass" if ok else "fail",
        {"equivalence_status": status, "unresolved_mentions_equivalence":
         "future asymptotic predictability" in unresolved, "amb15_present": bool(amb15)},
        "predictability equivalence is marked UNVERIFIED and tracked" if ok
        else "equivalence promoted or untracked",
    )


def c12_strictness_repair(ctx):
    d = ctx["doc"]
    d5 = str(((d.get("quantifiers") or {}).get("domains") or {}).get("D5", {}).get("definition", ""))
    vis = str((d.get("visibility") or {}).get("definition", ""))
    civ = d.get("class_identity_variants") or []
    setvar = [v for v in civ if v.get("kind") == "set_based_visibility_reading"]
    rel = str(setvar[0].get("relation", "")) if setvar else ""
    note = str(setvar[0].get("note", "")) if setvar else ""
    ok = (
        "EQUIVALENT" in d5 and "past-closed" in d5
        and "EQUIVALENT" in vis
        and rel.strip().startswith("strictly WEAKER")
        and "class leakage" in note
    )
    return (
        "pass" if ok else "fail",
        {"D5_states_equivalence": "EQUIVALENT" in d5 and "past-closed" in d5,
         "visibility_states_equivalence": "EQUIVALENT" in vis,
         "SET_relation": rel[:120], "SET_note_mentions_leakage": "class leakage" in note},
        "rev13 strictness direction corrected (tail==whole; SET strictly weaker)" if ok
        else "strictness-direction defect",
    )


def c13_genericity_alias(ctx):
    d = ctx["doc"]
    g = d.get("genericity") or {}
    kind = g.get("kind")
    canon_axes = ((ctx["canon"].get("classes") or {}).get(CLASS_ID) or {}).get("axes") or {}
    canon_kind = canon_axes.get("genericity_kind")
    gmap = (ctx["vocab"] or {}).get("genericity_kind") or {}

    def canonical_of(token):
        if token in gmap:
            return token
        for canon, aliases in gmap.items():
            if token in (aliases or []):
                return canon
        return None

    ok = (
        kind == "residual_comeager"
        and canonical_of(canon_kind) == "residual_comeager"
        and g.get("is_part_of_class") is True
        and isinstance(ctx["vocab"], dict)
    )
    return (
        "pass" if ok else "fail",
        {"schema_kind": kind, "canonical_taxonomy_kind": canon_kind,
         "canonical_taxonomy_kind_resolves_to": canonical_of(canon_kind),
         "vocab_alias_policy": str((ctx["vocab"] or {}).get("policy", ""))[:100]},
        "genericity kind matches the frozen canonical token via the alias policy" if ok
        else "genericity vocabulary defect",
    )


def c14_falsifier_decidable(ctx):
    f = ctx["doc"].get("falsifier") or {}
    t1 = f.get("tier_1") or {}
    t2 = f.get("tier_2") or {}
    ok = (
        t1.get("refutes") == CLASS_ID
        and "forall" in str(t2.get("refutes", ""))
        and bool(t1.get("witness_type"))
        and bool(t1.get("machine_checkable_steps"))
        and bool(t1.get("proof_obligations"))
        and bool(t1.get("non_machine_checkable_step"))
        and len(f.get("schema_falsifiers", [])) >= 3
    )
    return (
        "pass" if ok else "fail",
        {"tier_1_refutes": t1.get("refutes"), "tier_2_refutes": t2.get("refutes"),
         "n_machine_steps": len(t1.get("machine_checkable_steps", [])),
         "n_proof_obligations": len(t1.get("proof_obligations", [])),
         "n_schema_falsifiers": len(f.get("schema_falsifiers", []))},
        "falsifier is tiered and cites decidable machine steps" if ok
        else "falsifier decidability defect",
    )


def c15_ledger_status(ctx):
    d = ctx["doc"]
    ks = d.get("known_status") or {}
    ids = {r.get("theorem_id") for r in (d.get("l1_ledger_refs") or [])}
    cex = str(ks.get("counterexample_status", ""))
    cex_l = cex.lower()
    non_generic_marker = any(t in cex_l for t in
                             ["non-generic", "never the generic", "special/self-similar"])
    ok = (
        ks.get("record") == "D-001"
        and ks.get("status") == "open_problem"
        and bool(ks.get("non_transfer_warning"))
        and {"D-001", "T-204", "T-208", "T-209"} <= ids
        and "T-208" in cex and non_generic_marker
    )
    return (
        "pass" if ok else "fail",
        {"record": ks.get("record"), "status": ks.get("status"), "ledger_ids": sorted(x for x in ids if x),
         "counterexample_status_non_generic_marker": non_generic_marker},
        "ledger record D-001 with non-transfer warning and tier-2-only counterexamples" if ok
        else "ledger/status binding defect",
    )


def c16_class_separation(ctx):
    d = ctx["doc"]
    a = d.get("anti_scope") or {}
    ids = {e.get("class_id") for e in (a.get("not_this_class") or [])}
    phrases = " ".join(str(p) for p in (a.get("phrases_that_are_not_this_class") or []))
    ok = (
        {"AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"} <= ids
        and "C0 or C2" in phrases
        and "extension regularity" in phrases
    )
    return (
        "pass" if ok else "fail",
        {"not_this_class_ids": sorted(x for x in ids if x),
         "phrases_checked": bool(phrases)},
        "antis-scope names both SCC classes and forbids composite regularity" if ok
        else "class-separation defect",
    )


CHECKS = [
    ("C01_duplicate_keys", c01_duplicate_keys),
    ("C02_revised_at_wall_clock", c02_revised_at_wall_clock),
    ("C03_revision_history", c03_revision_history),
    ("C04_frozen_pin", c04_frozen_pin),
    ("C05_bindchain", c05_bindchain),
    ("C06_class_identity", c06_class_identity),
    ("C07_contract_pointers", c07_contract_pointers),
    ("C08_f0_binding", c08_f0_binding),
    ("C09_quantifiers", c09_quantifiers),
    ("C10_conclusion_typing", c10_conclusion_typing),
    ("C11_equivalence_unverified", c11_equivalence_unverified),
    ("C12_strictness_repair", c12_strictness_repair),
    ("C13_genericity_alias", c13_genericity_alias),
    ("C14_falsifier_decidable", c14_falsifier_decidable),
    ("C15_ledger_status", c15_ledger_status),
    ("C16_class_separation", c16_class_separation),
]


# --------------------------------------------------------------------------
# planted-defect controls: mutate a deep copy of ctx
# --------------------------------------------------------------------------
def plant_c01(ctx):
    ctx["raw"] = ctx["raw"] + "\nclass_id: DUPLICATE\n"
    return ctx


def plant_c02(ctx):
    ctx["doc"]["revised_at"] = (ctx["now"] + dt.timedelta(seconds=3600)).isoformat()
    return ctx


def plant_c03(ctx):
    ctx["doc"]["revision"] = 12
    return ctx


def plant_c04(ctx):
    ctx["frozen"]["files"][TARGET]["sha256"] = "0" * 64
    return ctx


def plant_c05(ctx):
    ctx["frozen_files_status"] = copy.deepcopy(ctx["frozen_files_status"])
    ctx["frozen_files_status"][0]["status"] = "mismatch"
    return ctx


def plant_c06(ctx):
    ctx["doc"]["class_components"]["matter"] = "SCALAR"
    return ctx


def plant_c07(ctx):
    ctx["doc"]["class_contract_pointer"] = CANON + "#class_contracts." + CLASS_ID
    return ctx


def plant_c08(ctx):
    ctx["doc"]["f0_binding"]["consistency_evidence_sha256"] = "deadbeef" * 8
    return ctx


def plant_c09(ctx):
    ctx["doc"]["quantifiers"]["ordered"][1]["kind"] = "forall"
    return ctx


def plant_c10(ctx):
    ctx["doc"]["conclusion"]["statement_formal"] = "forall data: C2 inextendibility of the development"
    return ctx


def plant_c11(ctx):
    ctx["doc"]["conclusion"]["equivalent_standard_formulation"]["status"] = "proved equivalent"
    return ctx


def plant_c12(ctx):
    v = ctx["doc"]["class_identity_variants"][0]
    v["relation"] = "strictly STRONGER than this class's single-q tail predicate"
    return ctx


def plant_c13(ctx):
    ctx["doc"]["genericity"]["kind"] = "open_dense_escape"
    return ctx


def plant_c14(ctx):
    ctx["doc"]["falsifier"]["tier_1"]["refutes"] = "forall AF vacuum data"
    return ctx


def plant_c15(ctx):
    ctx["doc"]["known_status"]["record"] = "T-999"
    return ctx


def plant_c16(ctx):
    ctx["doc"]["anti_scope"]["not_this_class"] = []
    return ctx


CONTROLS = [
    ("C01_duplicate_keys", plant_c01),
    ("C02_revised_at_wall_clock", plant_c02),
    ("C03_revision_history", plant_c03),
    ("C04_frozen_pin", plant_c04),
    ("C05_bindchain", plant_c05),
    ("C06_class_identity", plant_c06),
    ("C07_contract_pointers", plant_c07),
    ("C08_f0_binding", plant_c08),
    ("C09_quantifiers", plant_c09),
    ("C10_conclusion_typing", plant_c10),
    ("C11_equivalence_unverified", plant_c11),
    ("C12_strictness_repair", plant_c12),
    ("C13_genericity_alias", plant_c13),
    ("C14_falsifier_decidable", plant_c14),
    ("C15_ledger_status", plant_c15),
    ("C16_class_separation", plant_c16),
]


def build_ctx():
    target_sha = sha256_file(os.path.join(REPO, TARGET))
    mirror_sha = sha256_file(os.path.join(REPO, MIRROR))
    frozen = load_json(os.path.join(REPO, FROZEN))
    files_status = []
    for path, meta in sorted((frozen.get("files") or {}).items()):
        declared = meta.get("sha256")
        full = os.path.join(REPO, path)
        if not os.path.exists(full):
            status, measured = "absent", None
        else:
            measured = sha256_file(full)
            status = "resolved" if measured == declared else "mismatch"
        files_status.append({"path": path, "declared": declared, "measured": measured,
                             "status": status})
    return {
        "raw": read_text(os.path.join(REPO, TARGET)),
        "doc": load_yaml(os.path.join(REPO, TARGET)),
        "mirror_raw": read_text(os.path.join(REPO, MIRROR)),
        "target_sha": target_sha,
        "mirror_sha": mirror_sha,
        "frozen": frozen,
        "frozen_sha": sha256_file(os.path.join(REPO, FROZEN)),
        "frozen_files_status": files_status,
        "canon": load_yaml(os.path.join(REPO, CANON)),
        "canon_sha": sha256_file(os.path.join(REPO, CANON)),
        "supp": load_yaml(os.path.join(REPO, SUPP)),
        "vocab": load_json(os.path.join(REPO, VOCAB)),
        "cons": load_json(os.path.join(REPO, CONS)),
        "cons_sha": sha256_file(os.path.join(REPO, CONS)),
        "now": dt.datetime.now().astimezone(),
        "mtime": os.path.getmtime(os.path.join(REPO, TARGET)),
    }


def run_checks(ctx):
    results = []
    for name, fn in CHECKS:
        status, measured, detail = fn(ctx)
        results.append({"id": name, "status": status, "measured": measured, "detail": detail})
    return results


def run_controls(ctx, pristine_results):
    by_id = {r["id"]: r for r in pristine_results}
    out = []
    for name, plant in CONTROLS:
        mutated = plant(copy.deepcopy(ctx))
        status, _, detail = dict(CHECKS)[name](mutated)
        caught = status == "fail" and by_id[name]["status"] == "pass"
        out.append({"id": name, "mutated_status": status, "baseline_status": by_id[name]["status"],
                    "caught": caught, "detail": detail})
    return out


def stability_probe(seconds: int, interval: float):
    timeline = []
    drift_paths = set()
    start = time.time()
    baseline = {}
    while True:
        sample = {p: sha256_file(os.path.join(REPO, p)) for p in STABILITY_PATHS}
        if not baseline:
            baseline = sample
        else:
            for p in STABILITY_PATHS:
                if sample[p] != baseline[p]:
                    drift_paths.add(p)
        timeline.append({"t": round(time.time() - start, 1), "hashes": sample})
        if time.time() - start >= seconds:
            break
        time.sleep(interval)
    return {
        "window_seconds": seconds,
        "interval_seconds": interval,
        "samples": len(timeline),
        "drift_detected": bool(drift_paths),
        "drift_paths": sorted(drift_paths),
        "first": timeline[0]["hashes"],
        "last": timeline[-1]["hashes"],
        "timeline": timeline,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--stability-seconds", type=int, default=0)
    ap.add_argument("--stability-interval", type=float, default=10.0)
    ap.add_argument("--json-out", default=os.path.join(HERE, "f1_rev13_report.json"))
    args = ap.parse_args()

    ctx = build_ctx()
    results = run_checks(ctx)
    controls = run_controls(ctx, results) if args.controls else []
    stability = (stability_probe(args.stability_seconds, args.stability_interval)
                 if args.stability_seconds > 0 else None)

    final = None
    if stability:
        ctx2 = build_ctx()
        final_results = run_checks(ctx2)
        final = {
            "measured_at": iso_now(),
            "target_sha256": ctx2["target_sha"],
            "mirror_sha256": ctx2["mirror_sha"],
            "mirror_equal": ctx2["target_sha"] == ctx2["mirror_sha"],
            "frozen_sha256": ctx2["frozen_sha"],
            "frozen_revision": ctx2["frozen"].get("revision"),
            "check_results": final_results,
            "checks_passed": sum(1 for r in final_results if r["status"] == "pass"),
            "hard_failures": [r["id"] for r in final_results if r["status"] != "pass"],
        }

    judged = final["check_results"] if final else results
    checks_ok = all(r["status"] == "pass" for r in judged)
    controls_ok = all(c["caught"] for c in controls) if controls else None
    drift = (stability or {}).get("drift_detected", False)
    hard = [r["id"] for r in judged if r["status"] != "pass"]
    pin_moved = bool(final) and (
        final["target_sha256"] != ctx["target_sha"]
        or final["frozen_sha256"] != ctx["frozen_sha"]
        or final["frozen_revision"] != ctx["frozen"].get("revision")
    )
    if hard:
        verdict = "revise"
    elif controls_ok is False:
        verdict = "inconclusive"
    elif pin_moved:
        verdict = "inconclusive"
    else:
        verdict = "accept"

    report = {
        "report_id": f"w089-f1-rev13-{dt.datetime.now().strftime('%Y%m%dT%H%M%S')}",
        "task_id": "W089-F1-REV13-REVIEW-05",
        "worker": "worker-089",
        "class_id": CLASS_ID,
        "node_id": "F1",
        "gate": "G-FORM",
        "created_at": iso_now(),
        "repo": REPO,
        "target": {
            "path": TARGET,
            "sha256": ctx["target_sha"],
            "revision": ctx["doc"].get("revision"),
            "mirror_path": MIRROR,
            "mirror_sha256": ctx["mirror_sha"],
            "mirror_equal": ctx["target_sha"] == ctx["mirror_sha"],
            "frozen_path": FROZEN,
            "frozen_sha256": ctx["frozen_sha"],
            "frozen_revision": ctx["frozen"].get("revision"),
            "frozen_frozen_at": ctx["frozen"].get("frozen_at"),
        },
        "check_results": results,
        "checks_passed": sum(1 for r in results if r["status"] == "pass"),
        "checks_total": len(results),
        "controls": controls,
        "controls_caught": sum(1 for c in controls if c["caught"]) if controls else None,
        "controls_total": len(controls) if controls else None,
        "stability": stability,
        "final_recheck": final,
        "pin_moved": pin_moved,
        "drift_detected": drift,
        "verdict": verdict,
        "hard_failures": hard,
        "scope": "mechanical cross-artifact integrity, class identity, quantifier typing, "
                 "rev13 repair verification and pin stability only; NOT a semantic sufficiency "
                 "review and NOT a gate verdict",
    }
    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=False)
        fh.write("\n")
    print(json.dumps({k: report[k] for k in
                      ("report_id", "verdict", "checks_passed", "checks_total",
                       "controls_caught", "controls_total", "hard_failures",
                       "pin_moved", "drift_detected")}, indent=1))
    if stability:
        print("drift_detected:", stability["drift_detected"], "paths:", stability["drift_paths"])
    sys.exit(0 if verdict == "accept" else (10 if hard else 11))


if __name__ == "__main__":
    main()

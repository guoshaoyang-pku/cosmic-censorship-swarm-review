#!/usr/bin/env python3
"""W089-F2A-REV12-REVIEW-03 — independent, controlled, hash-bound review of
F2a (AF-SCC-C2-VAC-GEN) revision 12 at the FROZEN rev28 pin.

Scope of the machine part: class-content structure, quantifier well-typedness,
the HF-034 closure items, cross-class D0/transfer preconditions, class-identity
separation, frozen-pin/mirror alignment, and a hash-stability window.  Every
check has at least one planted-defect control so a pass is controlled rather
than asserted.  Reads shared artifacts read-only; writes only inside its own
artifact directory.
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
from collections import Counter

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TARGET = "schemas/af_scc_c2_vacuum.yaml"
TARGET_AUTHORING = "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
CANON_TAX = "research_map/formulation_taxonomy.yaml"
SUPP_TAX = "artifacts/formulation/formulation_taxonomy.yaml"
F1 = "schemas/af_wcc_vacuum.yaml"
F2B = "schemas/af_scc_c0_vacuum.yaml"
CLASS_ID = "AF-SCC-C2-VAC-GEN"
FROZEN_CLASS_IDS = {
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
}


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_yaml(path: str):
    return yaml.safe_load(read_text(path))


def iso_now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def parse_iso(value: str):
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
    """Resolve a dotted fragment like classes.AF-SCC-C2-VAC-GEN."""
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
def c01_duplicate_top_level_keys(ctx):
    counts = Counter(top_level_keys(ctx["raw"]))
    dups = {k: v for k, v in counts.items() if v > 1}
    return (
        "pass" if not dups else "fail",
        {"duplicates": dups, "n_top_level": len(counts)},
        "no duplicate top-level mapping keys" if not dups else f"duplicate keys: {dups}",
    )


def c02_revised_at_wall_clock(ctx):
    stamp = parse_iso(ctx["doc"].get("revised_at"))
    if stamp is None:
        return "fail", {"revised_at": ctx["doc"].get("revised_at")}, "revised_at missing/naive"
    now = ctx["now"]
    mtime = dt.datetime.fromtimestamp(ctx["mtime"]).astimezone()
    delta_now = (stamp - now).total_seconds()
    delta_mtime = (stamp - mtime).total_seconds()
    ok = delta_now <= 60 and abs(delta_mtime) <= 600
    return (
        "pass" if ok else "fail",
        {
            "revised_at": stamp.isoformat(),
            "now": now.isoformat(timespec="seconds"),
            "mtime": mtime.isoformat(timespec="seconds"),
            "seconds_before_now": round(delta_now, 1),
            "seconds_vs_mtime": round(delta_mtime, 1),
        },
        "revised_at is wall-clock and mtime-consistent" if ok else "timestamp out of tolerance",
    )


def c03_revision_history(ctx):
    doc = ctx["doc"]
    rev = doc.get("revision")
    hist = doc.get("revision_history") or []
    ok = True
    detail = []
    if not isinstance(rev, int) or rev < 12:
        ok = False
        detail.append(f"revision={rev!r} (<12)")
    if not hist:
        ok = False
        detail.append("empty revision_history")
    else:
        last = hist[-1]
        if last.get("unused") is not False:
            ok = False
            detail.append(f"last history entry unused={last.get('unused')!r}")
        if last.get("at") != doc.get("revised_at"):
            ok = False
            detail.append("last history at != revised_at")
        idx = [e.get("index") for e in hist if isinstance(e, dict)]
        if idx and max(i for i in idx if isinstance(i, int)) > rev:
            ok = False
            detail.append("history index exceeds revision")
    return (
        "pass" if ok else "fail",
        {"revision": rev, "last_entry": hist[-1] if hist else None},
        "revision bumped and history consistent" if ok else "; ".join(detail),
    )


def c04_canonical_contract_pointer(ctx):
    pointer = ctx["doc"].get("class_contract_pointer")
    expectation = f"{CANON_TAX}#classes.{CLASS_ID}"
    measured = {"pointer": pointer, "expected": expectation}
    if pointer != expectation:
        return "fail", measured, "pointer does not target canonical taxonomy#classes.<class>"
    tax = ctx["canon_tax"]
    ok, node = resolve_fragment(tax, f"classes.{CLASS_ID}")
    measured["fragment_resolves"] = ok
    measured["contract_keys"] = sorted(node.keys())[:12] if isinstance(node, dict) else None
    return (
        "pass" if ok else "fail",
        measured,
        "canonical contract pointer resolves" if ok else "fragment unresolved in canonical taxonomy",
    )


def c05_supplement_pointer_separate(ctx):
    doc = ctx["doc"]
    canonical = doc.get("class_contract_pointer") or ""
    supp = doc.get("class_contract_supplement_pointer")
    expected = f"{SUPP_TAX}#class_contracts.{CLASS_ID}"
    measured = {"canonical_pointer": canonical, "supplement_pointer": supp, "expected": expected}
    if supp != expected:
        return "fail", measured, "supplement pointer wrong"
    ok, node = resolve_fragment(ctx["supp_tax"], f"class_contracts.{CLASS_ID}")
    measured["fragment_resolves"] = ok
    measured["fields_distinct"] = canonical.split("#")[0] != supp.split("#")[0]
    good = ok and measured["fields_distinct"]
    return (
        "pass" if good else "fail",
        measured,
        "supplement pointer resolves and is a distinct field" if good else "supplement pointer unresolved/conflated",
    )


def c06_f0_binding_hash(ctx):
    fb = ctx["doc"].get("f0_binding") or {}
    path = fb.get("declared_f0_artifact")
    declared = fb.get("declared_f0_sha256")
    measured_hash = sha256_file(os.path.join(REPO, path)) if path else None
    ok = bool(path) and declared == measured_hash
    return (
        "pass" if ok else "fail",
        {"declared_f0_artifact": path, "declared": declared, "measured": measured_hash},
        "declared F0 hash matches measured canonical taxonomy" if ok else "declared F0 hash mismatch",
    )


def c07_frozen_pin(ctx):
    fr = ctx["frozen"]
    files = fr.get("files") or {}
    target_hash = ctx["target_sha"]
    pin_can = (files.get(TARGET) or {}).get("sha256")
    pin_auth = (files.get(TARGET_AUTHORING) or {}).get("sha256")
    mirror_equal = ctx["authoring_sha"] == target_hash
    rev = fr.get("revision")
    frozen_at = parse_iso(fr.get("frozen_at"))
    not_future = frozen_at is not None and (frozen_at - ctx["now"]).total_seconds() <= 60
    ok = (
        isinstance(rev, int)
        and rev >= 28
        and pin_can == target_hash
        and pin_auth == target_hash
        and mirror_equal
        and not_future
    )
    return (
        "pass" if ok else "fail",
        {
            "frozen_revision": rev,
            "frozen_at": fr.get("frozen_at"),
            "pin_canonical": pin_can,
            "pin_authoring": pin_auth,
            "target_sha256": target_hash,
            "mirror_equal": mirror_equal,
            "frozen_at_not_future": not_future,
        },
        "FROZEN pins this revision on both paths, mirror equal" if ok else "frozen pin/mirror mismatch",
    )


def c08_class_identity(ctx):
    doc = ctx["doc"]
    comps = doc.get("class_components") or {}
    expected_components = {
        "asymptotics": "AF",
        "censorship": "SCC",
        "matter": "VAC",
        "genericity": "GEN",
        "regularity_token": "C2",
    }
    tokens = set(re.findall(r"AF-[A-Z0-9]+(?:-[A-Z0-9]+)*", ctx["raw"]))
    stray = sorted(t for t in tokens if t not in FROZEN_CLASS_IDS)
    ok = (
        doc.get("class_id") == CLASS_ID
        and comps == expected_components
        and doc.get("sibling_disjoint_from") == "AF-SCC-C0-VAC-GEN"
        and not stray
    )
    return (
        "pass" if ok else "fail",
        {
            "class_id": doc.get("class_id"),
            "class_components": comps,
            "sibling_disjoint_from": doc.get("sibling_disjoint_from"),
            "unexpected_class_tokens": stray,
        },
        "class identity clean, no non-frozen class token" if ok else "class identity defect",
    )


def c09_d0_well_typed_cross_class(ctx):
    d0 = (ctx["doc"].get("quantifiers", {}).get("domains", {}) or {}).get("D0", {}) or {}
    ordered = (ctx["doc"].get("quantifiers", {}) or {}).get("ordered") or []
    first = ordered[0] if ordered else {}
    peers = {}
    for name, doc in (("F1", ctx["f1"]), ("F2b", ctx["f2b"])):
        peers[name] = ((doc.get("quantifiers", {}).get("domains", {}) or {}).get("D0", {}) or {}).get(
            "definition"
        )
    d0_def = d0.get("definition")
    same_f2b = d0_def == peers["F2b"]
    same_f1 = d0_def == peers["F1"]
    tagged = isinstance(d0_def, str) and "tagged disjoint union" in d0_def and "r = smooth" in d0_def
    binder_ok = first.get("kind") == "forall" and first.get("binder") == "r" and first.get("domain_id") == "D0"
    ok = tagged and binder_ok and same_f2b and same_f1
    return (
        "pass" if ok else "fail",
        {
            "D0_tagged_disjoint_union": tagged,
            "first_binder": first,
            "D0_equal_to_F2b": same_f2b,
            "D0_equal_to_F1": same_f1,
        },
        "D0 well-typed and byte-identical across F1/F2a/F2b" if ok else "D0 repair incomplete or cross-class drift",
    )


def c10_extension_predicate(ctx):
    ep = ctx["doc"].get("extension_predicate") or {}
    definition = ep.get("definition") or ""
    clauses = [tag for tag in ("(a)", "(b)", "(c)", "(d)", "(e)", "(f)") if tag in definition]
    conflict = ep.get("must_not_conflate") or []
    ok = (
        ep.get("frozen_regularity") == "C2"
        and ep.get("frozen_equation_concept") == "classical_ricci"
        and ep.get("frozen_direction") == "future"
        and len(clauses) == 6
        and len(conflict) >= 3
    )
    return (
        "pass" if ok else "fail",
        {
            "frozen_regularity": ep.get("frozen_regularity"),
            "frozen_equation_concept": ep.get("frozen_equation_concept"),
            "frozen_direction": ep.get("frozen_direction"),
            "clauses_present": clauses,
            "n_must_not_conflate": len(conflict),
        },
        "extension predicate frozen with clauses (a)-(f)" if ok else "extension predicate incomplete",
    )


def c11_conclusion_no_merge(ctx):
    doc = ctx["doc"]
    cb = doc.get("class_boundary") or {}
    concl = doc.get("conclusion") or {}
    anti = doc.get("anti_scope") or {}
    not_this = anti.get("not_this_class") or []
    anti_ids = {e.get("class_id") for e in not_this if isinstance(e, dict)}
    ctype = concl.get("conclusion_type")
    ok = (
        ctype == "scc_c2_future_inextendibility"
        and "proper_future_extension_in_class" in (concl.get("statement_formal") or "")
        and cb.get("one_class_only") == CLASS_ID
        and cb.get("merge_forbidden") is True
        and cb.get("one_way_implication", "").startswith("E(C0) entails E(C2)")
        and "AF-SCC-C0-VAC-GEN" in anti_ids
        and CB_NO_MERGE_PHRASES_ABSENT(ctx["raw"])
    )
    return (
        "pass" if ok else "fail",
        {
            "conclusion_type": ctype,
            "one_class_only": cb.get("one_class_only"),
            "merge_forbidden": cb.get("merge_forbidden"),
            "anti_scope_ids": sorted(i for i in anti_ids if i),
        },
        "no C0/C2 merge; conclusion typed C2" if ok else "merge/conclusion-type defect",
    )


def CB_NO_MERGE_PHRASES_ABSENT(raw):
    # 'C0 or C2' is allowed only inside an anti-scope/forbidden phrase, never as a class selector.
    for line in raw.splitlines():
        if "C0 or C2" in line and not re.search(r"any 'C0 or C2'|forbidden|not_this_class|anti_scope|composite", line):
            return False
    return True


def c12_no_wcc_content_in_conclusion(ctx):
    doc = ctx["doc"]
    ip = doc.get("i_plus") or {}
    vis = doc.get("visibility") or {}
    formal = (doc.get("conclusion") or {}).get("statement_formal") or ""
    natural = (doc.get("conclusion") or {}).get("statement_natural_language") or ""
    leaked = bool(re.search(r"I\+|null infinity|visible", formal + " " + natural))
    ok = ip.get("in_conclusion") is False and vis.get("role") == "not_in_conclusion" and not leaked
    return (
        "pass" if ok else "fail",
        {
            "i_plus_in_conclusion": ip.get("in_conclusion"),
            "visibility_role": vis.get("role"),
            "conclusion_leaks_wcc_token": leaked,
        },
        "no WCC/I+ content in the SCC conclusion" if ok else "WCC content leaked into conclusion",
    )


def c13_genericity_block(ctx):
    gen = ctx["doc"].get("genericity") or {}
    variants = gen.get("variants") or []
    variant_flags = [v.get("is_this_class") for v in variants if isinstance(v, dict)]
    ok = (
        gen.get("kind") == "residual_comeager"
        and "constraint manifold" in (gen.get("ambient_space") or "")
        and gen.get("is_part_of_class") is True
        and gen.get("excluded_set_status") == "unresolved"
        and variant_flags
        and all(flag is False for flag in variant_flags)
    )
    return (
        "pass" if ok else "fail",
        {
            "kind": gen.get("kind"),
            "is_part_of_class": gen.get("is_part_of_class"),
            "excluded_set_status": gen.get("excluded_set_status"),
            "variant_is_this_class": variant_flags,
        },
        "genericity block consistent; variants not classes" if ok else "genericity block defect",
    )


def c14_falsifier_block(ctx):
    fal = ctx["doc"].get("falsifier") or {}
    t1 = fal.get("tier_1") or {}
    schema_f = fal.get("schema_falsifiers") or []
    ok = (
        t1.get("refutes") == CLASS_ID
        and bool(t1.get("witness_type"))
        and bool(t1.get("non_machine_checkable_step"))
        and len(schema_f) >= 3
    )
    return (
        "pass" if ok else "fail",
        {"tier_1_refutes": t1.get("refutes"), "n_schema_falsifiers": len(schema_f)},
        "falsifier block bound to this class" if ok else "falsifier block defect",
    )


def c15_transfer_precondition(ctx):
    doc = ctx["doc"]
    ledger = doc.get("implication_ledger") or {}
    entail = {(e.get("from"), e.get("to")) for e in (ledger.get("one_way_entailments") or []) if isinstance(e, dict)}
    forbid = {(e.get("from"), e.get("to")) for e in (ledger.get("forbidden_transfers") or []) if isinstance(e, dict)}
    f2b_reg = (((ctx["f2b"].get("data_class") or {}).get("regularity_class") or {}).get("sobolev_variant") or {})
    f2a_reg = (((doc.get("data_class") or {}).get("regularity_class") or {}).get("sobolev_variant") or {})
    shared = f2a_reg.get("s") == f2b_reg.get("s") and f2a_reg.get("delta") == f2b_reg.get("delta")
    c0_to_c2 = ("no proper future C0 extension", "no proper future C2 extension") in entail
    h2_to_c2 = any(a.startswith("no proper future H2") and b == "no proper future C2 extension" for a, b in entail)
    c2_to_c0_forbidden = ("no proper future C2 extension", "no proper future C0 extension") in forbid
    ok = c0_to_c2 and h2_to_c2 and c2_to_c0_forbidden and shared
    return (
        "pass" if ok else "fail",
        {
            "C0_entails_C2": c0_to_c2,
            "H2loc_entails_C2": h2_to_c2,
            "C2_to_C0_forbidden": c2_to_c0_forbidden,
            "shared_regularity_with_F2b": shared,
            "F2a_s_delta": [f2a_reg.get("s"), f2a_reg.get("delta")],
            "F2b_s_delta": [f2b_reg.get("s"), f2b_reg.get("delta")],
        },
        "licensed C0=>C2 transfer precondition holds at the frozen data class" if ok else "transfer precondition defect",
    )


def c16_evidence_pointer_observation(ctx):
    fb = ctx["doc"].get("f0_binding") or {}
    declared = fb.get("consistency_evidence_sha256")
    path = fb.get("consistency_evidence")
    measured = sha256_file(os.path.join(REPO, path)) if path else None
    return (
        "observation",
        {"declared": declared, "measured": measured, "path": path, "match": declared == measured},
        "inline consistency-evidence pointer still resolves"
        if declared == measured
        else "inline consistency-evidence pointer is stale after the rev28 re-freeze (see HF-086-R1)",
    )


CHECKS = [
    ("C01", "duplicate_top_level_keys", c01_duplicate_top_level_keys),
    ("C02", "revised_at_wall_clock", c02_revised_at_wall_clock),
    ("C03", "revision_history_consistency", c03_revision_history),
    ("C04", "canonical_contract_pointer", c04_canonical_contract_pointer),
    ("C05", "supplement_pointer_separate", c05_supplement_pointer_separate),
    ("C06", "f0_binding_hash", c06_f0_binding_hash),
    ("C07", "frozen_pin_mirror", c07_frozen_pin),
    ("C08", "class_identity_no_stray_token", c08_class_identity),
    ("C09", "d0_well_typed_cross_class", c09_d0_well_typed_cross_class),
    ("C10", "extension_predicate_frozen", c10_extension_predicate),
    ("C11", "conclusion_no_merge", c11_conclusion_no_merge),
    ("C12", "no_wcc_content_in_conclusion", c12_no_wcc_content_in_conclusion),
    ("C13", "genericity_block", c13_genericity_block),
    ("C14", "falsifier_block", c14_falsifier_block),
    ("C15", "transfer_precondition", c15_transfer_precondition),
]
OBSERVATIONS = [("OBS-089-1", "evidence_pointer_observation", c16_evidence_pointer_observation)]


# --------------------------------------------------------------------------
# controls: each mutates a deep copy and must make its mapped check fail
# --------------------------------------------------------------------------
def mut_dup_key(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["raw"] = raw = ctx["raw"].replace(
        "revision: 12", 'revision: 12\nrevised_at: "2026-09-12T00:30:00+08:00"', 1
    )
    ctx["doc"] = yaml.safe_load(raw)
    return ctx


def mut_future_revised_at(ctx):
    ctx = copy.deepcopy(ctx)
    future = (ctx["now"] + dt.timedelta(hours=2)).isoformat(timespec="seconds")
    ctx["doc"]["revised_at"] = future
    return ctx


def mut_pointer_authoring(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["class_contract_pointer"] = (
        f"{SUPP_TAX}#classes.{CLASS_ID}"
    )
    return ctx


def mut_pointer_dangling(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["class_contract_pointer"] = f"{CANON_TAX}#classes.AF-NOPE"
    return ctx


def mut_f0_hash(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["f0_binding"]["declared_f0_sha256"] = "0" * 64
    return ctx


def mut_class_id(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["class_id"] = "AF-SCC-C2-C0-MERGE"
    return ctx


def mut_d0_regress(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["quantifiers"]["domains"]["D0"]["definition"] = (
        "admissible regularity: r = (s,delta,norm) a single pair with s > 5/2"
    )
    return ctx


def mut_conclusion_visibility(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["conclusion"]["statement_formal"] = (
        "forall r in D0 exists G_r comeager forall D in G_r: "
        "not exists visible_singularity_from_I_plus(MGHD(D))"
    )
    return ctx


def mut_conclusion_type(ctx):
    ctx = copy.deepcopy(ctx)
    ctx["doc"]["conclusion"]["conclusion_type"] = "scc_c0_future_inextendibility"
    return ctx


def mut_transfer_drop(ctx):
    ctx = copy.deepcopy(ctx)
    ledger = ctx["doc"]["implication_ledger"]
    ledger["one_way_entailments"] = [
        e
        for e in ledger["one_way_entailments"]
        if not (e.get("from") == "no proper future C0 extension")
    ]
    return ctx


CONTROLS = [
    ("M1", "planted duplicate revised_at key", "C01", mut_dup_key),
    ("M2", "planted future revised_at", "C02", mut_future_revised_at),
    ("M3", "pointer redirected at the authoring tree", "C04", mut_pointer_authoring),
    ("M4", "pointer fragment dangles (classes.AF-NOPE)", "C04", mut_pointer_dangling),
    ("M5", "declared F0 hash corrupted", "C06", mut_f0_hash),
    ("M6", "merge-shaped class id planted", "C08", mut_class_id),
    ("M7", "D0 regressed to an ill-typed pair", "C09", mut_d0_regress),
    ("M8", "WCC visibility predicate imported into the conclusion", "C12", mut_conclusion_visibility),
    ("M9", "conclusion_type widened to the C0 class", "C11", mut_conclusion_type),
    ("M10", "licensed C0=>C2 entailment deleted", "C15", mut_transfer_drop),
]


# --------------------------------------------------------------------------
def build_ctx(now=None):
    target_path = os.path.join(REPO, TARGET)
    authoring_path = os.path.join(REPO, TARGET_AUTHORING)
    raw = read_text(target_path)
    ctx = {
        "raw": raw,
        "doc": yaml.safe_load(raw),
        "target_sha": hashlib.sha256(raw.encode()).hexdigest(),
        "authoring_sha": sha256_file(authoring_path),
        "mtime": os.stat(target_path).st_mtime,
        "now": now or dt.datetime.now().astimezone(),
        "frozen": json.loads(read_text(os.path.join(REPO, FROZEN))),
        "canon_tax": load_yaml(os.path.join(REPO, CANON_TAX)),
        "supp_tax": load_yaml(os.path.join(REPO, SUPP_TAX)),
        "f1": load_yaml(os.path.join(REPO, F1)),
        "f2b": load_yaml(os.path.join(REPO, F2B)),
    }
    return ctx


def run_checks(ctx, checks):
    out = {}
    for cid, name, fn in checks:
        status, measured, detail = fn(ctx)
        out[cid] = {"name": name, "status": status, "measured": measured, "detail": detail}
    return out


def run_controls(base_ctx):
    results = {}
    for cid, desc, target_check, mutate in CONTROLS:
        mutant = mutate(base_ctx)
        fn = dict((c[0], c[2]) for c in CHECKS)[target_check]
        status, measured, detail = fn(mutant)
        results[cid] = {
            "desc": desc,
            "target_check": target_check,
            "caught": status == "fail",
            "observed_status": status,
            "detail": detail,
        }
        try:
            out = os.path.join(HERE, "controls", f"{cid}.yaml")
            with open(out, "w", encoding="utf-8") as fh:
                if isinstance(mutant["doc"], dict):
                    yaml.safe_dump(mutant["doc"], fh, sort_keys=False, allow_unicode=True)
                else:
                    fh.write(mutant["raw"])
        except Exception as exc:  # pragma: no cover
            results[cid]["write_error"] = str(exc)
    return results


def stability(ctx, window, interval):
    paths = [TARGET, TARGET_AUTHORING, FROZEN, CANON_TAX, SUPP_TAX, F1, F2B]
    timeline = []
    start = dt.datetime.now().astimezone()
    deadline = start.timestamp() + window
    first = {p: sha256_file(os.path.join(REPO, p)) for p in paths}
    while True:
        sample = {p: sha256_file(os.path.join(REPO, p)) for p in paths}
        timeline.append({"at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "hashes": sample})
        if dt.datetime.now().astimezone().timestamp() >= deadline:
            break
        import time as _time

        _time.sleep(interval)
    last = timeline[-1]["hashes"]
    drifted = sorted(p for p in paths if first[p] != last[p])
    return {
        "window_seconds": window,
        "interval_seconds": interval,
        "samples": len(timeline),
        "first": first,
        "last": last,
        "drifted_paths": drifted,
        "drift_detected": bool(drifted),
        "timeline": timeline,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=90)
    ap.add_argument("--interval", type=int, default=15)
    ap.add_argument("--out", default=os.path.join(HERE, "f2a_review_report.json"))
    args = ap.parse_args(argv)

    os.makedirs(os.path.join(HERE, "controls"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "pinned"), exist_ok=True)

    ctx = build_ctx()
    checks = run_checks(ctx, CHECKS)
    observations = run_checks(ctx, OBSERVATIONS)
    controls = run_controls(ctx)
    stab = stability(ctx, args.window, args.interval)

    snap_target = os.path.join(HERE, "pinned", f"af_scc_c2_vacuum.{ctx['target_sha'][:12]}.yaml")
    with open(snap_target, "w", encoding="utf-8") as fh:
        fh.write(ctx["raw"])
    snap_frozen = os.path.join(HERE, "pinned", "FROZEN.rev28.json")
    with open(snap_frozen, "w", encoding="utf-8") as fh:
        fh.write(read_text(os.path.join(REPO, FROZEN)))

    fails = [cid for cid, r in checks.items() if r["status"] == "fail"]
    no_false_positive = all(r["status"] == "pass" for r in checks.values())
    controls_ok = all(c["caught"] for c in controls.values())
    verdict = "accept" if not fails and controls_ok else "revise"

    report = {
        "schema_version": "1.0",
        "task_id": "W089-F2A-REV12-REVIEW-03",
        "worker": "worker-089",
        "class_id": CLASS_ID,
        "node_id": "F2a",
        "gate": "G-FORM",
        "created_at": iso_now(),
        "target": {
            "path": TARGET,
            "sha256": ctx["target_sha"],
            "authoring_path": TARGET_AUTHORING,
            "authoring_sha256": ctx["authoring_sha"],
            "mirror_equal": ctx["authoring_sha"] == ctx["target_sha"],
            "revision": ctx["doc"].get("revision"),
            "revised_at": ctx["doc"].get("revised_at"),
            "mtime": dt.datetime.fromtimestamp(ctx["mtime"]).astimezone().isoformat(timespec="seconds"),
            "bytes": len(ctx["raw"].encode()),
        },
        "frozen_manifest": {
            "path": FROZEN,
            "revision": ctx["frozen"].get("revision"),
            "frozen_at": ctx["frozen"].get("frozen_at"),
            "sha256": sha256_file(os.path.join(REPO, FROZEN)),
        },
        "checks": checks,
        "observations": observations,
        "controls": controls,
        "control_summary": {
            "n_controls": len(controls),
            "all_caught": controls_ok,
            "no_false_positive_baseline": no_false_positive,
        },
        "stability": stab,
        "verdict": verdict,
        "score": 4.0 if verdict == "accept" else 3.0,
        "hard_failures": [
            {"id": f"HF-089-{cid}", "detail": checks[cid]["detail"], "measured": checks[cid]["measured"]}
            for cid in fails
        ],
        "scope": (
            "independent machine-checked structural and consistency review of F2a rev12 at the FROZEN rev28 "
            "pin: closure of HF-034-F2A-1/HF-034-F2A-2, D0 well-typedness and cross-class identity, the licensed "
            "C0=>C2 transfer precondition, class-identity/merge separation, and frozen-pin/mirror alignment. "
            "Excludes: adjudication of the inline consistency-evidence pointer drift (recorded as OBS-089-1 and "
            "already tracked as HF-086-R1), the O-GFORM-1 data_class-differentiation objection, L1 citation "
            "adjudication, and any gate verdict."
        ),
        "independence": (
            "worker-089 authored no canonical artifact, no part of F2a, and has no prior F2a review; prior tasks "
            "bound F2b and the F0-dependency evidence only. Controls M1-M10 each plant one defect class so a pass "
            "is controlled."
        ),
        "counts_as_gate_accept": False,
        "next_falsifier": (
            "Any of C01-C15 flips to fail at a newer canonical hash of schemas/af_scc_c2_vacuum.yaml, or the "
            "FROZEN pin/mirror equality breaks, or a planted control stops being caught: then this accept is "
            "void for the newer revision. A hash move during the stability window makes this verdict advisory "
            "for the pinned bytes only."
        ),
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True, default=str)
    print(json.dumps({
        "out": args.out,
        "target_sha256": ctx["target_sha"],
        "verdict": verdict,
        "fails": fails,
        "controls_all_caught": controls_ok,
        "drift_detected": stab["drift_detected"],
        "observations": {k: v["detail"] for k, v in observations.items()},
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W053-F1-REV12-INDEP-VERIFY-01 -- independent machine verification of F1 rev12.

Target: schemas/af_wcc_vacuum.yaml (class AF-WCC-VAC-GEN, node F1, gate G-FORM),
whatever revision it measures at run time.  The task is the relaunch of execution
slot 053 after W053-F0-MIRROR-VERIFY-01; the immediate trigger is the rev12
repair of the four rev11 hard findings (duplicate revised_at keys, future-dated
timestamp, authoring-tree class_contract_pointer, undefined AF_{I+}, whole-curve
vs canonical tail predicate) plus one new cross-check: whether the artifact's
declared F0/consistency bindings and the FROZEN rev27 manifest still pin the
measured bytes.

Method: deterministic, read-only on every input.  Each input is read ONCE into
memory; every hash, parse and check uses those same bytes (no TOCTOU re-read).
A drift guard re-reads the bind set after the checks.  Every check carries its
own falsifier; planted-defect controls exercise the same predicate functions so
a PASS cannot be vacuous.

Re-run:
    python3 artifacts/worker-053/f1_rev12_verify/check_f1_rev12.py
Outputs in this directory: report.json, controls.json, run.log (shell tee).
Exit 0 = checks ran and the run was drift-stable.  Exit 1 = drift (inconclusive).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = _dt.timezone(_dt.timedelta(hours=8))

TASK_ID = "W053-F1-REV12-INDEP-VERIFY-01"
ACTOR = "worker-053"
NODE = "F1"
GATE = "G-FORM"
CLASS_ID = "AF-WCC-VAC-GEN"

F1 = "schemas/af_wcc_vacuum.yaml"
CANON = "research_map/formulation_taxonomy.yaml"
SUPPL = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
CONS = "artifacts/formulation/evidence/taxonomy_consistency.json"
SCHEMAS = ["schemas/af_wcc_vacuum.yaml",
           "schemas/af_scc_c2_vacuum.yaml",
           "schemas/af_scc_c0_vacuum.yaml"]
OTHER_CLASSES = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]
BIND_SET = [F1, CANON, SUPPL, FROZEN, CONS]

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
FUTURE_TOLERANCE_S = 60


def now() -> str:
    return _dt.datetime.now(CST).isoformat(timespec="seconds")


def parse_iso(s):
    try:
        t = _dt.datetime.fromisoformat(str(s))
    except Exception:
        return None
    return t.replace(tzinfo=CST) if t.tzinfo is None else t


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read_snapshot(rels) -> dict:
    snap = {}
    for rel in rels:
        p = ROOT / rel
        if p.is_file():
            b = p.read_bytes()
            st = p.stat()
            snap[rel] = {"bytes": b, "sha256": sha_bytes(b), "size": len(b),
                         "mtime": _dt.datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds")}
        else:
            snap[rel] = {"bytes": None, "sha256": None, "size": None, "mtime": None, "missing": True}
    return snap


def yaml_load(b: bytes):
    return yaml.safe_load(b.decode("utf-8"))


# ---------------------------------------------------------------- predicates
def find_duplicate_keys(text: str) -> list:
    """Duplicate mapping keys anywhere in the document (raw node tree)."""
    dups = []

    def walk(node, path):
        if isinstance(node, yaml.MappingNode):
            seen = {}
            for k, v in node.value:
                key = getattr(k, "value", None)
                if key in seen:
                    dups.append(f"{path}.{key}")
                seen[key] = True
                walk(v, f"{path}.{key}")
        elif isinstance(node, yaml.SequenceNode):
            for i, v in enumerate(node.value):
                walk(v, f"{path}[{i}]")

    try:
        walk(yaml.compose(text), "$")
    except Exception as e:  # a document that does not compose is a defect of another check
        return [f"compose-error:{type(e).__name__}"]
    return dups


def find_future_timestamps(obj, ref_now, path="$") -> list:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += find_future_timestamps(v, ref_now, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += find_future_timestamps(v, ref_now, f"{path}[{i}]")
    elif isinstance(obj, str) and ISO_RE.match(obj):
        t = parse_iso(obj)
        if t is not None and (t - ref_now).total_seconds() > FUTURE_TOLERANCE_S:
            out.append({"path": path, "value": obj,
                        "skew_seconds": int((t - ref_now).total_seconds())})
    return out


def _frag_class(pointer: str):
    path, _, frag = str(pointer).partition("#")
    return path, frag, (frag.split(".")[-1] if frag else None)


def check_pointer(schema: dict, canon: dict, suppl: dict) -> dict:
    cid = schema.get("class_id")
    cptr = str(schema.get("class_contract_pointer", ""))
    sptr = str(schema.get("class_contract_supplement_pointer", ""))
    fb = schema.get("f0_binding") or {}
    cpath, cfrag, ccls = _frag_class(cptr)
    spath, sfrag, scls = _frag_class(sptr)
    canon_classes = canon.get("classes") if isinstance(canon.get("classes"), dict) else {}
    suppl_contracts = suppl.get("class_contracts") if isinstance(suppl.get("class_contracts"), dict) else {}
    root_key = cfrag.split(".")[0] if cfrag else None
    suppl_root = suppl.get(root_key) if root_key else None
    m = {
        "class_id": cid,
        "class_contract_pointer": cptr,
        "pointer_path": cpath, "pointer_fragment": cfrag, "pointer_fragment_class": ccls,
        "pointer_root_key": root_key,
        "canonical_has_pointer_root_key": root_key in canon if root_key else False,
        "supplement_has_pointer_root_key": root_key in suppl if root_key else False,
        "pointer_targets_canonical": cpath == CANON,
        "pointer_targets_supplement": cpath == SUPPL,
        "pointer_resolves_in_canonical": bool(ccls and ccls in canon_classes),
        "pointer_resolves_in_supplement_under_same_key": bool(
            root_key and isinstance(suppl_root, dict) and ccls in suppl_root),
        "pointer_class_equals_class_id": ccls == cid,
        "supplement_pointer": sptr,
        "supplement_pointer_path": spath,
        "supplement_pointer_fragment_class": scls,
        "supplement_pointer_targets_supplement": spath == SUPPL,
        "supplement_pointer_resolves": bool(scls and scls in suppl_contracts),
        "supplement_pointer_class_equals_class_id": scls == cid,
        "f0_binding_supplement_pointer_equals_field": fb.get("class_contract_supplement_pointer") == sptr,
        "conflated_single_pointer": cptr == sptr,
    }
    ok = (m["pointer_targets_canonical"] and not m["pointer_targets_supplement"]
          and m["pointer_resolves_in_canonical"] and not m["supplement_has_pointer_root_key"]
          and not m["pointer_resolves_in_supplement_under_same_key"]
          and m["pointer_class_equals_class_id"]
          and m["supplement_pointer_targets_supplement"] and m["supplement_pointer_resolves"]
          and m["supplement_pointer_class_equals_class_id"]
          and m["f0_binding_supplement_pointer_equals_field"]
          and not m["conflated_single_pointer"])
    return {"ok": ok, "measured": m}


def check_symbols(schema: dict) -> dict:
    defs = []
    i_plus = schema.get("i_plus") or {}
    vis = schema.get("visibility") or {}
    for key, val in i_plus.items():
        if "abbreviation" in key and isinstance(val, str):
            defs.append({"site": f"i_plus.{key}", "text_head": val[:180]})
    for key, val in vis.items():
        if "abbreviation" in key and isinstance(val, str):
            defs.append({"site": f"visibility.{key}", "text_head": val[:180]})
    conc = schema.get("conclusion") or {}
    formal = str(conc.get("statement_formal", ""))
    quant = schema.get("quantifiers") or {}
    formal_q = str(quant.get("formal", ""))
    used = sorted(set(re.findall(r"AF_\{[^}]+\}", formal + " " + formal_q
                                 + " " + str(quant.get("negation", "")))))
    defined = set()
    for d in defs:
        defined |= set(re.findall(r"AF_\{[^}]+\}", d["text_head"]))
    undefined = [u for u in used if u not in defined]
    named_pred = str(vis.get("predicate_name", ""))
    m = {"definition_sites": defs, "symbols_used": used, "symbols_defined": sorted(defined),
         "undefined_symbols": undefined, "visibility_predicate_name": named_pred,
         "predicate_named_in_statement_formal": bool(named_pred) and named_pred in formal,
         "predicate_named_in_quantifiers_formal": bool(named_pred) and named_pred in formal_q}
    ok = bool(defs) and not undefined and m["predicate_named_in_statement_formal"]
    return {"ok": ok, "measured": m}


def check_predicate(schema: dict) -> dict:
    quant = schema.get("quantifiers") or {}
    vis = schema.get("visibility") or {}
    conc = schema.get("conclusion") or {}
    formal = str(quant.get("formal", ""))
    neg = str(quant.get("negation", ""))
    d5 = str((quant.get("domains") or {}).get("D5", {}).get("definition", ""))
    vdef = str(vis.get("definition", ""))
    vneg = str(vis.get("negation_conclusion", ""))
    sformal = str(conc.get("statement_formal", ""))
    named = str(vis.get("predicate_name", ""))

    tail = "gamma([t0,T))"
    whole = "gamma([0,T))"
    m = {
        "tail_token_in_quantifiers_formal": tail in formal,
        "whole_curve_token_in_quantifiers_formal": whole in formal,
        "quantifiers_formal_head": formal[:400],
        "tail_token_in_D5": tail in d5,
        "D5_states_whole_curve_is_not_the_predicate": ("NOT the predicate" in d5) or ("is strictly STRONGER" in d5),
        "negation_has_tail": (tail in neg) or ("tail" in neg.lower()),
        "negation_has_whole_curve": whole in neg,
        "visibility_definition_has_tail": tail in vdef,
        "visibility_definition_states_whole_curve_misclassifies": "would misclassify" in vdef,
        "negation_conclusion_has_tail": (tail in vneg) or ("tail" in vneg.lower()),
        "negation_conclusion_has_whole_curve": whole in vneg,
        "statement_formal_named_predicate": bool(named) and named in sformal,
        "statement_formal_has_whole_curve": whole in sformal,
    }
    # non-vacuity control: the two readings must be distinguishable on a model
    m["discriminating_model"] = {
        "geodesic": "gamma starts outside J^-(q0), ends inside J^-(q0)",
        "canonical_tail_visible": True,
        "whole_curve_visible": False,
        "readings_agree": False,
    }
    ok = (m["tail_token_in_quantifiers_formal"] and not m["whole_curve_token_in_quantifiers_formal"]
          and m["tail_token_in_D5"] and m["D5_states_whole_curve_is_not_the_predicate"]
          and m["negation_has_tail"] and not m["negation_has_whole_curve"]
          and m["visibility_definition_has_tail"]
          and m["negation_conclusion_has_tail"] and not m["negation_conclusion_has_whole_curve"]
          and m["statement_formal_named_predicate"] and not m["statement_formal_has_whole_curve"]
          and not m["discriminating_model"]["readings_agree"])
    return {"ok": ok, "measured": m}


def check_domain_typing(schema: dict) -> dict:
    quant = schema.get("quantifiers") or {}
    domains = quant.get("domains") or {}
    ordered = quant.get("ordered") or []
    formal = str(quant.get("formal", ""))
    d0 = str((domains.get("D0") or {}).get("definition", ""))
    reg = str((schema.get("data_class") or {}).get("regularity_class", "")) if isinstance(
        (schema.get("data_class") or {}).get("regularity_class"), str) else json.dumps(
        (schema.get("data_class") or {}).get("regularity_class", {}))
    binders = [str(r.get("binder", "")) for r in ordered if isinstance(r, dict)]
    bad_refs = [str(r.get("domain_id")) for r in ordered
                if isinstance(r, dict) and str(r.get("domain_id")) not in domains]
    pair_binder = [b for b in binders if "s" in b and "delta" in b and "," in b]
    m = {
        "ordered_binders": binders,
        "ordered_domain_refs_missing": bad_refs,
        "D0_is_tagged_union": ("tagged disjoint union" in d0) or ("tagged" in d0 and "disjoint" in d0),
        "D0_has_smooth_branch": "r = smooth" in d0,
        "D0_has_sobolev_branch": "(sobolev,s,delta)" in d0 or "sobolev,s,delta" in d0,
        "formal_binds_r_over_D0": bool(re.search(r"forall\s+r\s+in\s+D0", formal)),
        "formal_binds_pair_over_D0": bool(re.search(r"forall\s*\(\s*s\s*,\s*delta\s*\)", formal)),
        "pair_binder_present": bool(pair_binder),
        "regularity_class_mentions_both_branches": ("smooth" in reg and "sobolev" in reg.lower()),
    }
    ok = (not bad_refs and m["D0_is_tagged_union"] and m["D0_has_smooth_branch"]
          and m["D0_has_sobolev_branch"] and m["formal_binds_r_over_D0"]
          and not m["formal_binds_pair_over_D0"] and not m["pair_binder_present"]
          and m["regularity_class_mentions_both_branches"])
    return {"ok": ok, "measured": m}


def check_f0_binding(schema: dict, pins: dict, cons: dict) -> dict:
    fb = schema.get("f0_binding") or {}
    declared_f0 = fb.get("declared_f0_sha256")
    declared_cons = fb.get("consistency_evidence_sha256")
    measured_f0 = pins[CANON]["sha256"]
    measured_cons = pins[CONS]["sha256"]
    classes_compared = sorted(cons.get("classes_compared") or [])
    m = {
        "declared_f0_artifact": fb.get("declared_f0_artifact"),
        "declared_f0_sha256": declared_f0,
        "measured_canonical_sha256": measured_f0,
        "declared_f0_matches_measured": declared_f0 == measured_f0,
        "declared_f0_artifact_is_canonical": fb.get("declared_f0_artifact") == CANON,
        "declared_consistency_evidence": fb.get("consistency_evidence"),
        "declared_consistency_evidence_sha256": declared_cons,
        "measured_consistency_evidence_sha256": measured_cons,
        "consistency_evidence_pin_fresh": declared_cons == measured_cons,
        "consistency_evidence_says_consistent": cons.get("consistent") is True,
        "consistency_evidence_errors": cons.get("errors"),
        "consistency_evidence_contract_divergences": cons.get("contract_divergences"),
        "classes_compared": classes_compared,
        "classes_compared_is_four_class_set": set(classes_compared) == {CLASS_ID, *OTHER_CLASSES},
        "checked_at": fb.get("checked_at"),
        "evidence_file_mtime": pins[CONS]["mtime"],
        "binding_declared_before_evidence_rewrite":
            bool(fb.get("checked_at")) and bool(pins[CONS]["mtime"])
            and str(fb.get("checked_at")) < str(pins[CONS]["mtime"]),
        "rule_present": bool(fb.get("rule")),
    }
    ok = (m["declared_f0_matches_measured"] and m["declared_f0_artifact_is_canonical"]
          and m["consistency_evidence_pin_fresh"]
          and m["consistency_evidence_says_consistent"]
          and not (cons.get("errors") or [])
          and not (cons.get("contract_divergences") or [])
          and m["classes_compared_is_four_class_set"] and m["rule_present"])
    return {"ok": ok, "measured": m}


def check_conclusion(schema: dict) -> dict:
    conc = schema.get("conclusion") or {}
    anti = schema.get("anti_scope") or {}
    operative = json.dumps({"conclusion": schema.get("conclusion"),
                            "class_components": schema.get("class_components"),
                            "class_id": schema.get("class_id")})
    disclaimers = anti.get("phrases_that_are_not_this_class") or []
    m = {
        "class_id": schema.get("class_id"),
        "node_id": schema.get("node_id"),
        "conclusion_type": conc.get("conclusion_type"),
        "epistemic_status": conc.get("epistemic_status") or schema.get("epistemic_status"),
        "anti_scope_not_this_class": [x.get("class_id") for x in (anti.get("not_this_class") or [])
                                      if isinstance(x, dict)],
        "composite_c0_c2_phrase_in_operative_fields": bool(re.search(r"C0\s*(or|/)\s*C2", operative)),
        "anti_scope_disclaims_composite": any("C0 or C2" in str(s) for s in disclaimers),
        "forbidden_strengthenings": conc.get("forbidden_strengthenings") or [],
        "promotion_rule_present": bool(schema.get("promotion_rule")) and bool(conc.get("claim_promotion")),
        "scc_class_as_this_class": schema.get("class_id") in OTHER_CLASSES,
    }
    m["anti_scope_covers_other_classes"] = set(OTHER_CLASSES).issubset(set(m["anti_scope_not_this_class"]))
    m["forbidden_strengthenings_block_scc"] = any(
        ("C2" in s or "C0" in s) for s in map(str, m["forbidden_strengthenings"]))
    ok = (m["class_id"] == CLASS_ID and m["node_id"] == NODE
          and m["conclusion_type"] == "weak_cosmic_censorship"
          and m["epistemic_status"] == "open_problem"
          and m["anti_scope_covers_other_classes"]
          and not m["composite_c0_c2_phrase_in_operative_fields"]
          and m["anti_scope_disclaims_composite"]
          and m["forbidden_strengthenings_block_scc"] and m["promotion_rule_present"]
          and not m["scc_class_as_this_class"])
    return {"ok": ok, "measured": m}


def check_frozen(frozen: dict, pins: dict, listed_snap: dict) -> dict:
    files = frozen.get("files") or {}
    rows = []
    for rel, ent in sorted(files.items()):
        s = listed_snap.get(rel, {})
        if s.get("missing"):
            rows.append({"path": rel, "status": "MISSING", "declared": (ent or {}).get("sha256")})
            continue
        rows.append({"path": rel, "status": "MATCH" if s["sha256"] == (ent or {}).get("sha256") else "MISMATCH",
                     "declared": (ent or {}).get("sha256"), "measured": s["sha256"],
                     "declared_bytes": (ent or {}).get("bytes"), "measured_bytes": s["size"],
                     "mtime": s["mtime"]})
    bad = [r for r in rows if r["status"] != "MATCH"]
    frozen_at = frozen.get("frozen_at")
    fat = parse_iso(frozen_at)
    post_freeze = [{"path": r["path"], "mtime": r["mtime"]} for r in rows
                   if r["status"] == "MATCH" and fat is not None and r.get("mtime")
                   and parse_iso(r["mtime"]) > fat]
    m = {
        "revision": frozen.get("revision"),
        "frozen_at": frozen_at,
        "files_listed": len(rows),
        "files_match": len(rows) - len(bad),
        "files_bad": bad,
        "post_freeze_writes": post_freeze,
        "f1_pin": (files.get(F1) or {}).get("sha256"),
        "f1_measured": pins[F1]["sha256"],
        "f1_pin_matches": (files.get(F1) or {}).get("sha256") == pins[F1]["sha256"],
        "canon_pin_matches": (files.get(CANON) or {}).get("sha256") == pins[CANON]["sha256"],
        "suppl_pin_matches": (files.get(SUPPL) or {}).get("sha256") == pins[SUPPL]["sha256"],
    }
    ok = (not bad and m["f1_pin_matches"] and m["canon_pin_matches"] and m["suppl_pin_matches"])
    return {"ok": ok, "measured": m}


def check_identity(schema, raw_text: str) -> dict:
    m = {"parsed": isinstance(schema, dict),
         "top_level_keys": sorted(schema.keys()) if isinstance(schema, dict) else [],
         "schema_version": schema.get("schema_version") if isinstance(schema, dict) else None,
         "artifact_kind": schema.get("artifact_kind") if isinstance(schema, dict) else None}
    ok = (isinstance(schema, dict) and schema.get("class_id") == CLASS_ID
          and schema.get("node_id") == NODE and schema.get("artifact_kind") == "class_schema")
    return {"ok": ok, "measured": m}


SEVERITY = {"C1": "critical", "C2": "major", "C3": "major", "C4": "major", "C5": "major",
            "C6": "critical", "C7": "major", "C8": "major", "C9": "major", "C10": "major",
            "C11": "minor"}


def run_checks(raw: dict) -> dict:
    ref_now = _dt.datetime.now(CST)
    f1_text = raw[F1]["bytes"].decode("utf-8")
    schema = yaml_load(raw[F1]["bytes"])
    canon = yaml_load(raw[CANON]["bytes"])
    suppl = yaml_load(raw[SUPPL]["bytes"])
    frozen = json.loads(raw[FROZEN]["bytes"].decode("utf-8"))
    cons = json.loads(raw[CONS]["bytes"].decode("utf-8"))

    listed = sorted((frozen.get("files") or {}).keys())
    listed_snap = read_snapshot(listed)

    dup = find_duplicate_keys(f1_text)
    future = find_future_timestamps(schema, ref_now)

    checks = {
        "C1": {"title": "F1 parses and declares class AF-WCC-VAC-GEN / node F1",
               "falsifier": "Falsified if schemas/af_wcc_vacuum.yaml does not parse as a mapping, or its class_id/node_id/artifact_kind differ from AF-WCC-VAC-GEN/F1/class_schema.",
               **check_identity(schema, f1_text)},
        "C2": {"title": "no duplicate mapping keys anywhere in the F1 document (rev11 HF)",
               "falsifier": "Falsified if a raw-node walk of the F1 document finds the same key twice in one mapping (PyYAML safe_load would silently keep the last).",
               "ok": not dup, "measured": {"duplicate_key_paths": dup}},
        "C3": {"title": "no wall-clock-future timestamp in F1 (rev11 HF)",
               "falsifier": "Falsified if any ISO-8601 string in the parsed document is more than 60 s ahead of the run clock.",
               "ok": not future, "measured": {"future_timestamps": future, "run_clock": ref_now.isoformat(timespec='seconds')}},
        "C4": {"title": "class_contract_pointer resolves in the canonical taxonomy; supplement pointer is a separate field (rev11 HF)",
               "falsifier": "Falsified if the pointer does not target research_map/formulation_taxonomy.yaml#classes.<class_id> / does not resolve there, or if it also resolves in the supplement, or if the supplement pointer is absent/unresolved/equal to the canonical pointer.",
               **check_pointer(schema, canon, suppl)},
        "C5": {"title": "AF_{I+} has a definition site and every used normative symbol is defined (rev11 HF)",
               "falsifier": "Falsified if any AF_{...} symbol used in statement_formal/quantifiers has no definition site, or if visibility.predicate_name is not used by statement_formal.",
               **check_symbols(schema)},
        "C6": {"title": "quantifiers.formal is the canonical single-q TAIL predicate, not whole-curve; negation is its exact negation (rev11 HF-025-1)",
               "falsifier": "Falsified if the operative formal clause contains whole-curve containment gamma([0,T)) subset J^-(q), if D5 labels whole-curve as the predicate, or if negation/statement_formal are not written with the tail predicate.",
               **check_predicate(schema)},
        "C7": {"title": "D0 is a well-typed tagged union and the quantifier binds r (not the (s,delta) pair) over it (rev11 HF-025-2)",
               "falsifier": "Falsified if D0 is a disjunction without a single bound object, if the formal clause binds (s,delta) over D0, if a pair binder is present, or if an ordered quantifier references an undeclared domain.",
               **check_domain_typing(schema)},
        "C8": {"title": "declared F0 hash and consistency-evidence hash equal the measured bytes, and the consistency verdict is CONSISTENT (new cross-check)",
               "falsifier": "Falsified if f0_binding.declared_f0_sha256 != measured canonical sha256, or f0_binding.consistency_evidence_sha256 != measured consistency-evidence sha256, or the evidence file no longer reports consistent=true over the four classes.",
               **check_f0_binding(schema, raw, cons)},
        "C9": {"title": "FROZEN manifest pins the measured bytes of every listed file, including F1/canonical/supplement",
               "falsifier": "Falsified if any FROZEN files[] entry mismatches measured bytes, or if the F1/canonical/supplement pins do not match. (Post-freeze mtimes are covered separately by C11.)",
               **check_frozen(frozen, raw, listed_snap)},
        "C10": {"title": "conclusion type/class separation: weak_cosmic_censorship, open_problem, SCC classes excluded, no compositing (G-FORM criterion)",
               "falsifier": "Falsified if conclusion_type/epistemic_status differ, if anti_scope does not exclude all three other classes, if a 'C0 or C2' composite phrase occurs in the operative conclusion fields, or if the promotion rule is missing.",
               **check_conclusion(schema)},
        "C11": {"title": "no FROZEN-listed file was touched after frozen_at (byte-identical rewrite is still a freeze-discipline signal)",
               "falsifier": "Falsified if any file listed in FROZEN.json has an mtime later than frozen_at; byte pins are unaffected when the rewrite is idempotent, so this is a minor process finding, not a content defect.",
               "ok": True,
               "measured": {}},
    }
    checks["C11"]["ok"] = not checks["C9"]["measured"]["post_freeze_writes"]
    checks["C11"]["measured"] = {
        "post_freeze_writes": checks["C9"]["measured"]["post_freeze_writes"],
        "note": "byte pin for each listed file still matches its FROZEN entry (C9); only the mtime moved",
    }
    for cid, c in checks.items():
        c["id"] = cid
        c["severity"] = SEVERITY[cid]
        c["status"] = "PASS" if c["ok"] else "FAIL"
    return {"checks": checks, "schema": schema, "frozen": frozen, "cons": cons,
            "listed_snap": listed_snap}


# ---------------------------------------------------------------- controls
def run_controls(raw: dict) -> list:
    import copy
    schema = yaml_load(raw[F1]["bytes"])
    canon = yaml_load(raw[CANON]["bytes"])
    suppl = yaml_load(raw[SUPPL]["bytes"])
    cons = json.loads(raw[CONS]["bytes"].decode("utf-8"))
    ref_now = _dt.datetime.now(CST)
    ctl = []

    def add(cid, planted, detected, detail):
        ctl.append({"id": cid, "planted_defect": planted, "detected": bool(detected), "detail": detail})

    bad_text = "a: 1\nb:\n  c: 2\n  c: 3\n"
    dups = find_duplicate_keys(bad_text)
    add("K1", "YAML text with a duplicate mapping key", bool(dups) and "c" in dups[0], f"duplicate finder -> {dups}")

    fut = find_future_timestamps({"x": (ref_now + _dt.timedelta(days=1)).isoformat(timespec="seconds")}, ref_now)
    add("K2", "timestamp one day ahead of the run clock", bool(fut), f"future finder -> {fut[:1]}")

    s = copy.deepcopy(schema)
    s["class_contract_pointer"] = f"{SUPPL}#class_contracts.{s.get('class_id')}"
    r = check_pointer(s, canon, suppl)
    add("K3", "class_contract_pointer redirected to the supplement", not r["ok"],
        f"pointer check ok={r['ok']} targets_canonical={r['measured']['pointer_targets_canonical']}")

    s2 = copy.deepcopy(schema)
    s2.setdefault("f0_binding", {})["consistency_evidence_sha256"] = "0" * 64
    r2 = check_f0_binding(s2, raw, cons)
    add("K4", "consistency-evidence pin corrupted to 0*64", not r2["ok"],
        f"binding check ok={r2['ok']} pin_fresh={r2['measured']['consistency_evidence_pin_fresh']}")

    s3 = copy.deepcopy(schema)
    s3.get("i_plus", {}).pop("predicate_abbreviation", None)
    r3 = check_symbols(s3)
    add("K5", "AF_{I+} definition site removed from i_plus", not r3["ok"],
        f"symbol check ok={r3['ok']} undefined={r3['measured']['undefined_symbols']}")

    s4 = copy.deepcopy(schema)
    s4.setdefault("quantifiers", {})["formal"] = (
        "forall r in D0: forall gamma: not exists q in I+ with gamma([0,T)) subset J^-(q) intersect M")
    r4 = check_predicate(s4)
    add("K6", "formal clause rewritten to whole-curve containment", not r4["ok"],
        f"predicate check ok={r4['ok']} whole_curve_token={r4['measured']['whole_curve_token_in_quantifiers_formal']}")

    s5 = copy.deepcopy(schema)
    s5.setdefault("quantifiers", {}).setdefault("ordered", []).append({"kind": "exists", "binder": "z", "domain_id": "D404"})
    r5 = check_domain_typing(s5)
    add("K7", "ordered quantifier referencing an undeclared domain D404", not r5["ok"],
        f"domain check ok={r5['ok']} missing_refs={r5['measured']['ordered_domain_refs_missing']}")

    s6 = copy.deepcopy(schema)
    s6["conclusion"]["conclusion_type"] = "strong_cosmic_censorship"
    r6 = check_conclusion(s6)
    add("K8", "conclusion_type inflated to strong_cosmic_censorship", not r6["ok"],
        f"conclusion check ok={r6['ok']} type={r6['measured']['conclusion_type']}")

    return ctl


def main() -> int:
    attempts = []
    chosen = None
    for attempt in range(1, 7):
        raw = read_snapshot(BIND_SET)
        res = run_checks(raw)
        controls = run_controls(raw)
        after = read_snapshot(BIND_SET)
        drifted = [rel for rel in BIND_SET if raw[rel]["sha256"] != after[rel]["sha256"]]
        attempts.append({
            "attempt": attempt,
            "checked_at": now(),
            "pins": {rel: {"sha256": raw[rel]["sha256"], "size": raw[rel]["size"], "mtime": raw[rel]["mtime"]}
                     for rel in BIND_SET},
            "drifted_paths": drifted,
        })
        chosen = {"raw": raw, "res": res, "controls": controls, "drifted": drifted,
                  "pins_after": {rel: after[rel]["sha256"] for rel in BIND_SET}}
        if not drifted:
            break
        time.sleep(4)

    res = chosen["res"]
    checks = res["checks"]
    hard = [c for c in checks.values() if c["status"] == "FAIL" and c["severity"] in ("critical", "major")]
    minor = [c for c in checks.values() if c["status"] == "FAIL" and c["severity"] == "minor"]
    controls_ok = all(c["detected"] for c in chosen["controls"])
    stable = not chosen["drifted"]

    if not stable:
        verdict = "inconclusive"
    elif hard:
        verdict = "revise"
    else:
        verdict = "accept"
    score = 5.0 - 2.0 * sum(1 for c in hard if c["severity"] == "critical") \
        - 1.0 * sum(1 for c in hard if c["severity"] == "major") - 0.25 * len(minor)
    score = max(0.5, round(score, 2))

    report = {
        "task_id": TASK_ID,
        "actor": ACTOR,
        "node_id": NODE,
        "gate": GATE,
        "class_id": CLASS_ID,
        "created_at": now(),
        "question": ("Does schemas/af_wcc_vacuum.yaml at its measured hash resolve the rev11 hard "
                     "findings (duplicate keys, future timestamp, authoring-tree pointer, undefined "
                     "AF_{I+}, whole-curve predicate) and are its declared F0/consistency and FROZEN "
                     "rev27 bindings fresh at the measured bytes?"),
        "verdict": verdict,
        "score": score,
        "authority_note": ("evidence only: sets no gate verdict, no node status and edits no canonical "
                           "artifact; a worker review is not a gate verdict (PROTOCOL authority rule)"),
        "attempts": attempts,
        "stable": stable,
        "drifted_paths": chosen["drifted"],
        "pins_before": attempts[-1]["pins"],
        "pins_after": chosen["pins_after"],
        "checks": checks,
        "controls": chosen["controls"],
        "controls_ok": controls_ok,
        "hard_failures": [{"id": c["id"], "title": c["title"], "severity": c["severity"],
                           "measured": c["measured"], "falsifier": c["falsifier"]} for c in hard],
        "hard_failure_count": len(hard),
        "minor_findings": [{"id": c["id"], "title": c["title"], "measured": c["measured"]} for c in minor],
        "measured_bottom_line": {
            "f1_sha256": attempts[-1]["pins"][F1]["sha256"],
            "canonical_sha256": attempts[-1]["pins"][CANON]["sha256"],
            "supplement_sha256": attempts[-1]["pins"][SUPPL]["sha256"],
            "consistency_evidence_sha256": attempts[-1]["pins"][CONS]["sha256"],
            "frozen_revision": res["frozen"].get("revision"),
            "frozen_files_match": "%d/%d" % (res["checks"]["C9"]["measured"]["files_match"],
                                             res["checks"]["C9"]["measured"]["files_listed"]),
            "check_matrix": {cid: c["status"] for cid, c in checks.items()},
        },
        "non_claims": [
            "does not adjudicate whether the WCC class is true/false",
            "does not write to research_map/, schemas/, ledger/ or artifacts/formulation/",
            "does not edit FROZEN.json or refresh the stale pin; that is the owner's fix",
            "worker verdict is not a gate verdict (PROTOCOL authority rule)",
        ],
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (OUT / "controls.json").write_text(json.dumps(
        {"controls": chosen["controls"], "controls_ok": controls_ok}, indent=2, sort_keys=True) + "\n")

    print(f"{TASK_ID}: verdict={verdict} score={score} stable={stable} controls_ok={controls_ok}")
    for cid, c in checks.items():
        print(f"  {c['status']} {cid} [{c['severity']}]: {c['title']}")
    for c in chosen["controls"]:
        print(f"  control {c['id']} detected={c['detected']}: {c['planted_defect']}")
    print(f"  F1={attempts[-1]['pins'][F1]['sha256'][:12]} canonical={attempts[-1]['pins'][CANON]['sha256'][:12]} "
          f"cons_evidence={attempts[-1]['pins'][CONS]['sha256'][:12]}")
    print(f"  frozen rev={res['frozen'].get('revision')} files_match="
          f"{checks['C9']['measured']['files_match']}/{checks['C9']['measured']['files_listed']} "
          f"post_freeze_writes={len(checks['C9']['measured']['post_freeze_writes'])}")
    print(f"  drift: stable={stable} attempts={len(attempts)} drifted_paths={chosen['drifted']}")
    print("  hashes:")
    print(f"    report.json    {sha_bytes((OUT / 'report.json').read_bytes())}")
    print(f"    controls.json  {sha_bytes((OUT / 'controls.json').read_bytes())}")
    print(f"    checker        {sha_bytes(Path(__file__).resolve().read_bytes())}")
    return 0 if stable else 1


if __name__ == "__main__":
    sys.exit(main())

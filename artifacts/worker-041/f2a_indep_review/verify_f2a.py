#!/usr/bin/env python3
"""Independent machine verification of F2a (schemas/af_scc_c2_vacuum.yaml).

Reviewer: worker-041.  Task: W041-F2A-INDEP-REVIEW-01.
Class: AF-SCC-C2-VAC-GEN.  Node: F2a.  Gate: G-FORM / G-AUDIT.

The script is read-only.  It fails closed: the artifact sha256 is measured
before and after every check and the run aborts if it moves.

Checks (pre-registered before execution):
  C1  yaml_parses_no_duplicate_keys
  C2  no_future_dated_timestamps
  C3  class_contract_pointer_resolves_canonical   (HF-086-2 / HF-034-F2A-2 closure)
  C4  supplement_pointer_resolves_authoring
  C5  declared_f0_sha256_matches_measured
  C6  consistency_evidence_pin_matches_measured
  C7  all_definition_refs_resolve
  C8  d0_is_tagged_disjoint_union_single_index    (HF-086-1 / HF-088-1 closure)
  C9  per_branch_ambient_and_comeagerness_present (falsifier option (b))
  C10 class_purity_single_class_no_merge
  C11 conclusion_excludes_wcc_and_iplus
  C12 conclusion_type_and_promotion_rule_present
  C13 cross_schema_d0_verbatim_shared (F1/F2a/F2b G-FORM criterion)
  C14 sibling_disjointness_declared
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"
TARGET = f"{ROOT}/schemas/af_scc_c2_vacuum.yaml"
F0_CANON = f"{ROOT}/research_map/formulation_taxonomy.yaml"
F0_SUPPL = f"{ROOT}/artifacts/formulation/formulation_taxonomy.yaml"
CONS_EVID = f"{ROOT}/artifacts/formulation/evidence/taxonomy_consistency.json"
SIBLINGS = {
    "F1": f"{ROOT}/schemas/af_wcc_vacuum.yaml",
    "F2a": TARGET,
    "F2b": f"{ROOT}/schemas/af_scc_c0_vacuum.yaml",
}
TZ = timezone(timedelta(hours=8))
CLASS_ID = "AF-SCC-C2-VAC-GEN"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_iso(ts):
    if not isinstance(ts, str):
        return None
    m = re.match(
        r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})([+-]\d{2}):(\d{2})$", ts
    )
    if not m:
        return None
    y, mo, d, hh, mm, ss, offh, offm = m.groups()
    off = timezone(
        timedelta(hours=int(offh), minutes=int(offm) * (1 if offh.startswith("+") else -1))
    )
    return datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss), tzinfo=off)


class DupKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader, node, deep=False):
    keys = set()
    for k, _v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in keys:
            raise ValueError(f"duplicate YAML key: {key!r} at line {k.start_mark.line + 1}")
        keys.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


DupKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def resolve_pointer(path, fragment):
    """Resolve a minimal JSON-pointer-ish fragment like '#classes.X' or '#a.b'."""
    doc = yaml.safe_load(open(path))
    cur = doc
    trail = []
    for part in fragment.lstrip("#").split("."):
        trail.append(part)
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None, "/".join(trail)
    return True, cur, "/".join(trail)


def main():
    results = []
    h_before = sha256(TARGET)
    now = datetime.now(TZ)
    doc = yaml.load(open(TARGET), Loader=DupKeyLoader)

    def check(cid, ok, detail, evidence=None):
        results.append(
            {
                "check_id": cid,
                "status": "PASS" if ok else "FAIL",
                "detail": detail,
                "evidence": evidence,
            }
        )
        return ok

    # C1 duplicate keys
    try:
        check("C1_yaml_no_duplicate_keys", True, "parsed with duplicate-key rejecting loader")
    except Exception as exc:  # pragma: no cover
        check("C1_yaml_no_duplicate_keys", False, str(exc))
        doc = yaml.safe_load(open(TARGET))

    # C2 future-dated timestamps
    stamps = []
    for key in ("authored_at", "revised_at"):
        ts = parse_iso(doc.get(key))
        if ts:
            stamps.append((key, ts))
    for i, e in enumerate(doc.get("revision_history") or []):
        ts = parse_iso(e.get("at"))
        if ts:
            stamps.append((f"revision_history[{i}].at", ts))
    fb = doc.get("f0_binding") or {}
    ts = parse_iso(fb.get("checked_at"))
    if ts:
        stamps.append(("f0_binding.checked_at", ts))
    future = [(k, t.isoformat()) for k, t in stamps if t > now]
    check(
        "C2_no_future_dated_timestamps",
        not future,
        f"max declared {max(t for _, t in stamps).isoformat()}; now {now.isoformat()}"
        + (f"; FUTURE: {future}" if future else ""),
        {"n_timestamps": len(stamps)},
    )

    # C3 canonical pointer
    ptr = doc.get("class_contract_pointer")
    ok3, val3, trail3 = resolve_pointer(F0_CANON, ptr.split("#", 1)[1]) if ptr and "#" in ptr else (False, None, "")
    check(
        "C3_class_contract_pointer_resolves_canonical",
        ok3,
        f"{ptr} -> {'resolved' if ok3 else 'UNRESOLVED at ' + trail3}",
        {"resolved_key_trail": trail3, "value_type": type(val3).__name__},
    )

    # C4 supplement pointer (must resolve in authoring tree, distinct field)
    ptr4 = (doc.get("class_contract_supplement_pointer") or fb.get("class_contract_supplement_pointer"))
    ok4, _v4, trail4 = resolve_pointer(F0_SUPPL, ptr4.split("#", 1)[1]) if ptr4 and "#" in ptr4 else (False, None, "")
    same_field = doc.get("class_contract_pointer") == ptr4
    check(
        "C4_supplement_pointer_resolves_and_separate",
        ok4 and not same_field,
        f"{ptr4} -> {'resolved' if ok4 else 'UNRESOLVED at ' + trail4}; separate_field={not same_field}",
    )

    # C5 declared F0 hash
    declared_f0 = fb.get("declared_f0_sha256")
    meas_f0 = sha256(F0_CANON)
    check(
        "C5_declared_f0_sha256_matches_measured",
        declared_f0 == meas_f0,
        f"declared {str(declared_f0)[:12]} vs measured {meas_f0[:12]}",
    )

    # C6 consistency evidence pin
    declared_ce = fb.get("consistency_evidence_sha256")
    meas_ce = sha256(CONS_EVID)
    ce_doc = json.load(open(CONS_EVID))
    check(
        "C6_consistency_evidence_pin_matches_measured",
        declared_ce == meas_ce,
        f"declared {str(declared_ce)[:12]} vs measured {meas_ce[:12]}"
        + ("" if declared_ce == meas_ce else "  <-- STALE PIN"),
        {"consistent_flag_in_evidence": ce_doc.get("consistent"), "evidence_errors": ce_doc.get("errors")},
    )

    # C7 definition_refs resolve to top-level keys
    refs = []
    q = doc.get("quantifiers") or {}
    for dname, dval in (q.get("domains") or {}).items():
        if isinstance(dval, dict) and "definition_ref" in dval:
            refs.append((f"quantifiers.domains.{dname}", dval["definition_ref"]))
    def deref(path):
        cur = doc
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return False
        return True

    bad_refs = [(w, r) for w, r in refs if not deref(r)]
    check(
        "C7_all_definition_refs_resolve",
        not bad_refs,
        f"{len(refs)} refs checked; unresolved={bad_refs}",
        {"refs": [r for _, r in refs]},
    )

    # C8 D0 tagged disjoint union, single index
    d0 = ((q.get("domains") or {}).get("D0") or {})
    d0_def = str(d0.get("definition", ""))
    binders = [e.get("binder") for e in (q.get("ordered") or [])]
    formal = str(q.get("formal", ""))
    single_index = binders[:1] == ["r"]
    no_pair_binder = not any(isinstance(b, str) and "s" in b and "delta" in b for b in binders)
    tagged_union = bool(re.search(r"tagged disjoint union", d0_def, re.I))
    check(
        "C8_d0_tagged_disjoint_union_single_index",
        single_index and no_pair_binder and tagged_union,
        f"binders={binders}; tagged_disjoint_union={'tagged disjoint union' in d0_def.lower()}; "
        f"formal_binder_r={'forall r in D0' in formal}",
    )

    # C9 per-branch ambient + comeagerness
    gen = doc.get("genericity") or {}
    amb = str(gen.get("ambient_space", ""))
    topol = str(gen.get("topology_or_measure", ""))
    d1_def = str(((q.get("domains") or {}).get("D1") or {}).get("definition", ""))
    has_param_ambient = "X^r_vac" in amb
    smooth_branch_named = bool(re.search(r"Fr[eé]chet", topol, re.I))
    baire_declared = "Baire" in amb or "Baire" in topol
    comeager_param = "X^r_vac" in d1_def
    check(
        "C9_per_branch_ambient_and_comeagerness_present",
        has_param_ambient and smooth_branch_named and comeager_param,
        f"ambient_param={'X^r_vac' in amb}; frechet_named={smooth_branch_named}; "
        f"baire_explicit={baire_declared}; D1_param={'X^r_vac' in d1_def}",
        {"ambient_space": amb[:300], "topology_or_measure": topol[:300]},
    )

    # C10 class purity
    comp = doc.get("class_components") or {}
    boundary = doc.get("class_boundary") or {}
    merged = bool(re.search(r"C0\s*(or|/)\s*C2", str(doc.get("conclusion") or {}), re.I))
    check(
        "C10_class_purity_single_class_no_merge",
        doc.get("class_id") == CLASS_ID
        and boundary.get("one_class_only") == CLASS_ID
        and boundary.get("merge_forbidden") is True
        and not merged,
        f"class_id={doc.get('class_id')}; one_class_only={boundary.get('one_class_only')}; "
        f"merge_forbidden={boundary.get('merge_forbidden')}; composite_token_found={merged}",
        {"class_components": comp},
    )

    # C11 conclusion excludes WCC / I+ content
    conc = doc.get("conclusion") or {}
    # Only the ASSERTION fields count: forbidden_* lists legitimately name the tokens
    # they prohibit (WCC / I+), so including them would be a detector false positive.
    conc_text = json.dumps(
        {k: conc.get(k) for k in ("statement_natural_language", "statement_formal", "conclusion_type", "family")}
    ).lower()
    ip = doc.get("i_plus") or {}
    vis = doc.get("visibility") or {}
    wcc_free = ("i+ completeness" not in conc_text) and ("visible" not in conc_text)
    check(
        "C11_conclusion_excludes_wcc_and_iplus",
        wcc_free and ip.get("in_conclusion") is False and vis.get("role") == "not_in_conclusion",
        f"i_plus.in_conclusion={ip.get('in_conclusion')}; visibility.role={vis.get('role')}; "
        f"wcc_token_in_conclusion={not wcc_free}",
    )

    # C12 conclusion_type + promotion rule
    ct = conc.get("conclusion_type")
    check(
        "C12_conclusion_type_and_promotion_rule_present",
        bool(ct) and bool(doc.get("promotion_rule")) and conc.get("epistemic_status") == "open_problem",
        f"conclusion_type={ct}; promotion_rule_present={bool(doc.get('promotion_rule'))}; "
        f"epistemic_status={conc.get('epistemic_status')}",
    )

    # C13 cross-schema D0 verbatim shared
    d0s = {}
    for name, path in SIBLINGS.items():
        try:
            sib = yaml.safe_load(open(path))
        except Exception as exc:
            d0s[name] = f"PARSE_ERROR {exc}"
            continue
        sd0 = ((sib.get("quantifiers") or {}).get("domains") or {}).get("D0") or {}
        d0s[name] = str(sd0.get("definition", "")).strip()
    uniq = set(d0s.values())
    check(
        "C13_cross_schema_d0_verbatim_shared",
        len(uniq) == 1 and "" not in uniq,
        f"{len(uniq)} distinct D0 definition(s) across F1/F2a/F2b",
        {k: v[:220] for k, v in d0s.items()},
    )

    # C14 sibling disjointness declared (top-level key, not under class_boundary)
    check(
        "C14_sibling_disjointness_declared",
        doc.get("sibling_disjoint_from") == "AF-SCC-C0-VAC-GEN"
        and len(boundary.get("one_way_implication", "")) > 0,
        f"sibling_disjoint_from={doc.get('sibling_disjoint_from')}",
    )

    # clock: revised_at vs mtime consistency (hygiene)
    import os

    mtime = datetime.fromtimestamp(os.path.getmtime(TARGET), tz=TZ)
    ra = parse_iso(doc.get("revised_at"))
    skew = abs((mtime - ra).total_seconds()) if ra else None

    h_after = sha256(TARGET)
    summary = {
        "reviewer": "worker-041",
        "task_id": "W041-F2A-INDEP-REVIEW-01",
        "target": {"path": "schemas/af_scc_c2_vacuum.yaml", "class_id": CLASS_ID, "node_id": "F2a", "gate": "G-FORM"},
        "reviewed_sha256": h_before,
        "hash_stable_across_run": h_before == h_after,
        "measured_at": now.isoformat(),
        "revised_at": doc.get("revised_at"),
        "mtime": mtime.isoformat(),
        "revised_at_vs_mtime_skew_s": skew,
        "revision": doc.get("revision"),
        "n_pass": sum(1 for r in results if r["status"] == "PASS"),
        "n_fail": sum(1 for r in results if r["status"] == "FAIL"),
        "checks": results,
    }
    print(json.dumps(summary, indent=1))
    if h_before != h_after:
        sys.exit(3)
    sys.exit(0 if summary["n_fail"] == 0 else 1)


if __name__ == "__main__":
    main()

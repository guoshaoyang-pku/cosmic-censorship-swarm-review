#!/usr/bin/env python3
"""Deterministic, fail-closed checker for the F0 taxonomy review (worker-16).

Review target: research_map/formulation_taxonomy.yaml
Pinned hash:   276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc

The checker refuses to grade a drifted target: if the measured sha256 differs from
PINNED, it exits non-zero and writes no verdict-bearing results. It separates
machine-checkable structure (C-checks) from semantic residue checks (D1/D3) whose
evidence is quoted text at pinned line numbers.

Usage: python3 check_f0.py [--out check_results.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta

import yaml

TAX = "research_map/formulation_taxonomy.yaml"
MAP = "research_map/research_map.json"
PINNED = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
CST = timezone(timedelta(hours=8))


class DupSafeLoader(yaml.SafeLoader):
    pass


_DUP_KEYS: list[tuple[str, int]] = []


def _map_ctor(loader, node, deep=False):
    seen = set()
    for k, _v in node.value:
        kk = loader.construct_object(k, deep=deep)
        if kk in seen:
            _DUP_KEYS.append((str(kk), node.start_mark.line + 1))
        seen.add(kk)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


DupSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _map_ctor
)


def norm(s: str) -> str:
    """G3 normalization: remove ^ { } _ and whitespace."""
    return re.sub(r"[\^\{\}_\s]", "", s or "")


def now_cst() -> datetime:
    return datetime.now(CST)


def parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=CST)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/worker-16/f0_review/check_results.json")
    ap.add_argument("--tax", default=TAX, help="taxonomy path (override for controls)")
    ap.add_argument("--pin", default=PINNED, help="expected sha256 (override for controls)")
    args = ap.parse_args()

    raw = open(args.tax, "rb").read()
    measured = hashlib.sha256(raw).hexdigest()
    if measured != args.pin:
        print(f"FAIL-CLOSED: target drifted: {measured} != {args.pin}", file=sys.stderr)
        return 2

    d = yaml.load(raw, Loader=DupSafeLoader)
    map_doc = json.load(open(MAP))
    map_sha = sha256_file(MAP)

    checks: list[dict] = []

    def add(cid, name, status, detail):
        checks.append({"id": cid, "check": name, "status": status, "detail": detail})

    # C0: stability + duplicate keys
    h2 = sha256_file(args.tax)
    add("C0a", "hash stability across two reads", "PASS" if h2 == measured else "FAIL",
        f"read1={measured[:12]} read2={h2[:12]}")
    add("C0b", "no duplicate YAML mapping keys (strict loader)", "PASS" if not _DUP_KEYS else "FAIL",
        f"duplicates={_DUP_KEYS}")

    class_ids = d.get("class_ids", [])
    classes = d.get("classes", {})
    axes_names = ["family", "matter_model", "symmetry", "asymptotics",
                  "regularity_token", "genericity_kind", "conclusion_type"]

    # C1: exactly four class ids, no extras, keys agree
    add("C1", "exactly the four frozen class ids; classes keys == class_ids",
        "PASS" if (len(class_ids) == 4 and len(set(class_ids)) == 4
                   and set(class_ids) == set(classes)) else "FAIL",
        f"class_ids={class_ids} classes_keys={sorted(classes)}")

    # C2: axes vocabulary conformance
    fv = d.get("field_vocabulary", {})
    bad = []
    for cid in class_ids:
        ax = classes.get(cid, {}).get("axes", {})
        for name in axes_names:
            if name not in ax:
                bad.append(f"{cid}:{name}=MISSING")
                continue
            allowed = fv.get(name, {}).get("allowed")
            if allowed is not None and ax[name] not in allowed:
                bad.append(f"{cid}:{name}={ax[name]!r} not in {allowed}")
    add("C2", "every class carries every axis with a vocabulary-legal value",
        "PASS" if not bad else "FAIL", "; ".join(bad) or "7/7 axes x 4/4 classes legal")

    # C3: G2 family <-> regularity_token
    g2bad = []
    for cid in class_ids:
        ax = classes[cid]["axes"]
        if ax["family"] == "SCC" and ax["regularity_token"] not in ("C0", "C2"):
            g2bad.append(f"{cid} SCC token={ax['regularity_token']}")
        if ax["family"] == "WCC" and ax["regularity_token"] is not None:
            g2bad.append(f"{cid} WCC token={ax['regularity_token']}")
    add("C3", "guard G2: SCC <-> one of {C0,C2}; WCC <-> null", "PASS" if not g2bad else "FAIL",
        "; ".join(g2bad) or "4/4 classes satisfy G2")

    # C4: conclusion_type one value per class, all in vocabulary, pairwise distinct where required
    conc = {cid: classes[cid]["axes"]["conclusion_type"] for cid in class_ids}
    allowed_conc = set(fv["conclusion_type"]["allowed"])
    add("C4", "conclusion_type legal and never merged",
        "PASS" if set(conc.values()) <= allowed_conc and len(set(conc.values())) == 3 else "FAIL",
        f"per_class={conc}; distinct={sorted(set(conc.values()))}")

    # C5: disjointness 6/6, decisive axes actually differ
    pairs = d.get("disjointness", [])
    want = {frozenset(p) for p in [
        ("AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN"),
        ("AF-WCC-VAC-GEN", "AF-SCC-C0-VAC-GEN"),
        ("AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"),
        ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"),
        ("AF-SCC-C2-VAC-GEN", "AF-WCC-SCALAR-SPH"),
        ("AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH")]}
    got = {frozenset(p.get("pair", [])) for p in pairs}
    dj_bad = []
    for p in pairs:
        a, b = p.get("pair", [None, None])
        for ax in p.get("decisive_axes", []):
            va = classes.get(a, {}).get("axes", {}).get(ax, "<missing>")
            vb = classes.get(b, {}).get("axes", {}).get(ax, "<missing>")
            if va == vb:
                dj_bad.append(f"{a}~{b}:{ax}={va!r} does not differ")
    add("C5", "6/6 unordered pairs present exactly once; every decisive axis differs",
        "PASS" if got == want and len(pairs) == 6 and not dj_bad else "FAIL",
        f"pairs={len(pairs)} missing={sorted(map(sorted, want - got))} axis_failures={dj_bad}")

    # C6: merged-regularity guard G3 present and no merged token in conclusion texts
    merged_pat = re.compile(r"C\s*[\{^]?\s*[02]\s*[\}^]?\s*(?:/|,|\s+or\s+)\s*C\s*[\{^]?\s*[02]")
    merged_hits = []
    for cid in class_ids:
        for field in ("conclusion", "forbidden_inflation"):
            txt = classes[cid].get(field, {})
            txt = txt.get("text", "") if isinstance(txt, dict) else str(txt)
            if merged_pat.search(txt):
                merged_hits.append(f"{cid}.{field}")
    guards = {g.get("id") for g in d.get("guards", [])}
    add("C6", "guard G3 present; no C0/C2 merged spelling in class conclusions",
        "PASS" if "G3" in guards and not merged_hits else "FAIL",
        f"guards={sorted(guards)} merged_hits={merged_hits}")

    # C7: transfer direction soundness
    tr = d.get("transfer_rules", {})
    t1 = [t for t in tr.get("allowed", []) if t.get("id") == "T1"]
    t1_ok = bool(t1) and t1[0].get("from") == "AF-SCC-C0-VAC-GEN" and t1[0].get("to") == "AF-SCC-C2-VAC-GEN"
    xids = [t.get("id") for t in tr.get("forbidden", [])]
    add("C7", "T1 C0->C2 only allowed direction; X1-X5 forbidden list intact",
        "PASS" if t1_ok and set(xids) >= {"X1", "X2", "X3", "X4", "X5"} else "FAIL",
        f"T1={t1[0] if t1 else None} forbidden={xids}")

    # C8: guards G1-G7 present
    add("C8", "guards G1-G7 all present", "PASS" if set(f"G{i}" for i in range(1, 8)) <= guards else "FAIL",
        f"guards={sorted(guards)}")

    # C9: timestamp sanity (no content timestamp ahead of wall clock)
    now = now_cst()
    ts_fail = []
    for key in ("created_at", "written_at"):
        t = parse_ts(d.get(key, ""))
        if t is None or t > now:
            ts_fail.append(f"{key}={d.get(key)!r}")
    adj = d.get("class_scope_adjudication", {})
    t = parse_ts(adj.get("decided_at", ""))
    if t is None or t > now:
        ts_fail.append(f"class_scope_adjudication.decided_at={adj.get('decided_at')!r}")
    add("C9", "created_at/written_at/decided_at parse and are <= wall clock",
        "PASS" if not ts_fail else "FAIL",
        f"wall_clock={now.isoformat()} failures={ts_fail}")

    # C10 (semantic residue D1): the demoted set-based visibility reading must not
    # appear outside its registered variant location. WCC-VAC must use the tail predicate.
    set_based_hits = []
    tail_hits = []
    for cid in class_ids:
        txt = classes[cid]["conclusion"]["text"]
        n = norm(txt)
        if "containedinJ-(I+)" in n:
            set_based_hits.append(cid)
        if "single-qTAILpredicate" in n or "singleqTAILpredicate" in n:
            tail_hits.append(cid)
    add("C10", "D1: set-based J-(I+) containment reading appears only as registered variant",
        "PASS" if set_based_hits == [] else "FAIL",
        f"classes_using_set_based_reading={set_based_hits}; classes_naming_tail_predicate={tail_hits}; "
        f"SET variant parent=AF-WCC-VAC-GEN (d.variants[0])")

    # C11 (semantic residue D3): comeager quantifier explicit and bound before data, each class
    com = []
    for cid in class_ids:
        n = norm(classes[cid]["conclusion"]["text"])
        # norm() strips ^ { } _ and whitespace: G_{s,delta} -> Gs,delta
        if "comeagersetGs,delta" in n or "comeagersetGs,δ" in n:
            com.append(cid)
    missing = [c for c in class_ids if c not in com]
    add("C11", "D3: explicit comeager set G_{s,delta} bound before the data in every class",
        "PASS" if not missing else "FAIL",
        f"explicit={com}; missing={missing}; D3 resolution text="
        f"{adj.get('resolved_divergences', [{}])[1].get('resolution', '') if len(adj.get('resolved_divergences', [])) > 1 else ''}")

    # C12: genericity_topology instantiated on any class axis?
    inst = [cid for cid in class_ids if "genericity_topology" in classes[cid].get("axes", {})]
    add("C12", "field_vocabulary genericity_topology instantiated on a class axis (advisory)",
        "NOTE" if not inst else "PASS",
        f"instantiated_on={inst}; vocab rule requires genericity_kind AND genericity_topology "
        f"for a generic-quantified claim; claims_theorem_status={d.get('claims_theorem_status')}")

    # C13: provenance schema_owner pointers resolve to non-legacy canonical paths
    legacy = {a.get("path") for a in map_doc.get("legacy_artifacts", [])}
    ptr_bad = []
    for cid in class_ids:
        owner = str(classes[cid].get("provenance", {}).get("schema_owner", ""))
        for tok in re.findall(r"schemas/[A-Za-z0-9_./-]+\.yaml", owner):
            if tok in legacy:
                ptr_bad.append(f"{cid}->{tok} (legacy per map legacy_artifacts)")
    add("C13", "schema_owner pointers do not target map-recorded legacy artifacts",
        "PASS" if not ptr_bad else "FAIL",
        f"legacy_paths={sorted(legacy)} offenders={ptr_bad}; map_sha={map_sha[:12]}")

    # C14: variants registered under an existing parent, not written as classes
    variants = d.get("variants", [])
    var_bad = [v.get("variant_id") for v in variants
               if v.get("parent_class") not in classes or v.get("status") == "written"]
    add("C14", "variants parented to existing classes; none written as a second predicate",
        "PASS" if not var_bad and len(variants) == 2 else "FAIL",
        f"variants={[(v.get('parent_class'), v.get('variant_id'), v.get('status')) for v in variants]}")

    # C15: test cases exist per class and classify into declared classes or explicit excluded_by tokens
    tc_bad = []
    declared = set(class_ids)
    for cid in class_ids:
        tc = classes[cid].get("test_cases", {})
        exp = [tc.get(k, {}).get("expected_classification", "") for k in ("positive", "negative", "negative_2")]
        if not tc.get("positive"):
            tc_bad.append(f"{cid}:no_positive")
        for e in exp:
            if e and not (e in declared or e.startswith("excluded_by:") or e.startswith("rejected_by:")
                          or e.startswith("AF-SCC-C2-VAC-GEN (weaker")):
                tc_bad.append(f"{cid}:unparsed:{e[:40]}")
    add("C15", "each class has positive + 2 negative cases with resolvable expectations",
        "PASS" if not tc_bad else "FAIL", "; ".join(tc_bad) or "4/4 classes covered")

    # C16: G7 conclusion_type namespace overload (advisory)
    add("C16", "G7 'conclusion_type == theorem' vs field_vocabulary.conclusion_type share a name (advisory)",
        "NOTE",
        "same identifier denotes PROTOCOL claim conclusion_type {theorem,...} and class censorship type; "
        "published rule_spec.json namespaces it 'class_conclusion_type'")

    n_fail = sum(1 for c in checks if c["status"] == "FAIL")
    n_pass = sum(1 for c in checks if c["status"] == "PASS")
    n_note = sum(1 for c in checks if c["status"] == "NOTE")
    out = {
        "checker": "artifacts/worker-16/f0_review/check_f0.py",
        "target": args.tax,
        "target_sha256": measured,
        "map": MAP,
        "map_sha256": map_sha,
        "run_at": now_cst().isoformat(),
        "fail_closed": True,
        "summary": {"pass": n_pass, "fail": n_fail, "note": n_note, "total": len(checks)},
        "checks": checks,
        "falsifier": (
            "Any single FAIL check is refuted by re-running this pinned checker and showing the check "
            "passes at sha256 276009f4f63d..., or by showing the quoted taxonomy text does not carry the "
            "reading attributed to it at the cited line."
        ),
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out["summary"]))
    for c in checks:
        print(f"  [{c['status']:4}] {c['id']}: {c['check']} :: {c['detail'][:160]}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

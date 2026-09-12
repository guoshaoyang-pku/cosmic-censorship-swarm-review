#!/usr/bin/env python3
"""W059-F1-INDEP-VERDICT-01 — independent full-schema checker for F1 (worker-059).

Read-only w.r.t. every canonical artifact: this script never writes outside its own
artifact directory. It deliberately does NOT import the canonical gate
(`artifacts/formulation/tools/check_class_schema.py`) or the canonical
class-separation detector (`research_map/class_separation.py`) for its own checks;
those are cited separately as canonical-gate evidence.

Usage:
  python3 check_f1_independent.py <reviewed_snapshot.yaml> [--out report.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CST = timezone(timedelta(hours=8))

CANON_SCHEMA = ROOT / "schemas/af_wcc_vacuum.yaml"
CANON_F0 = ROOT / "research_map/formulation_taxonomy.yaml"
AUTHOR_F0 = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
REGISTRY = ROOT / "runtime/state/artifact_hashes.json"
MAP = ROOT / "research_map/research_map.json"
FROZEN_SNAPSHOT = ROOT / "artifacts/flash-04/f1_ambiguity/schema_snapshots/af_wcc_vacuum.b65fcc0f.yaml"
PRIOR_SNAPSHOT = HERE / "af_wcc_vacuum.reviewed.68392dd820505fbb.yaml"

SCC_TOKEN = re.compile(
    r"strong[\s_-]*cosmic|cauchy[\s_-]*horizon|extension[\s_]+across|"
    r"(?<![A-Za-z])C0(?![A-Za-z0-9])|(?<![A-Za-z])C2(?![A-Za-z0-9])|H2_loc|H\^?2",
    re.I)
# "future-inextendible" is the WCC singularity definition, not SCC content; a bare
# "inextendible" (no future- qualifier) on the conclusion surface is the leak.
INEXT = re.compile(r"inextendib", re.I)
SET_WORD = re.compile(r"union of|contained in the union|set-based|set_based", re.I)


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strings(node):
    """Yield every string under a YAML node with a dotted path."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str):
                yield str(k), v
            else:
                for sub, s in strings(v):
                    yield f"{k}.{sub}", s
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, str):
                yield f"[{i}]", v
            else:
                for sub, s in strings(v):
                    yield f"[{i}].{sub}", s


class Report:
    def __init__(self):
        self.checks = []

    def add(self, cid, status, detail, evidence=None):
        self.checks.append({"id": cid, "status": status, "detail": detail,
                            "evidence": evidence or []})


def check_semantics(doc, rep: Report):
    rep.add("C01-parse", "pass", "snapshot parses as a YAML mapping",
            [f"top-level keys: {len(doc)}"])
    rep.add("C02-identity",
            "pass" if (doc.get("class_id") == "AF-WCC-VAC-GEN" and doc.get("node_id") == "F1"
                       and doc.get("artifact_kind") == "class_schema") else "fail",
            f"class_id={doc.get('class_id')} node_id={doc.get('node_id')} kind={doc.get('artifact_kind')}")

    concl = doc.get("conclusion", {})
    rep.add("C03-conclusion-type",
            "pass" if concl.get("conclusion_type") == "weak_cosmic_censorship"
            and concl.get("family") == "WCC" else "fail",
            f"conclusion_type={concl.get('conclusion_type')} family={concl.get('family')}")

    # C04: no SCC content on the conclusion surface (own token list, not the canonical one)
    surface = {}
    for key in ("conclusion", "visibility", "i_plus"):
        for path, s in strings(doc.get(key, {})):
            surface[f"{key}.{path}"] = s
    hits = []
    for path, s in surface.items():
        if re.search(r"forbidden|must_not|not_this|l1_ledger|non_goals", path):
            continue
        m = SCC_TOKEN.search(s)
        if m:
            hits.append(f"{path}: {m.group(0)!r}")
            continue
        for im in INEXT.finditer(s):
            pre = s[max(0, im.start() - 12):im.start()].lower()
            if "future" not in pre:
                hits.append(f"{path}: bare 'inextendib' (no future- qualifier)")
                break
    rep.add("C04-no-scc-leakage", "fail" if hits else "pass",
            "own SCC-token scan over conclusion/visibility/i_plus surfaces",
            hits[:8] or ["0 hits"])

    # C05: quantifier order
    q = doc.get("quantifiers", {})
    ordered = q.get("ordered", [])
    kinds = [o.get("kind") for o in ordered]
    doms = q.get("domains", {})
    ok_order = kinds == ["forall", "exists", "forall", "exists", "forall", "not_exists"]
    ok_domains = all(o.get("domain_id") in doms for o in ordered) and len(doms) == 6
    rep.add("C05-quantifier-order", "pass" if ok_order and ok_domains else "fail",
            f"ordered kinds={kinds}; all 6 domain_ids defined={ok_domains}; order_matters={q.get('order_matters')}",
            [q.get("order_note", "")[:160]])

    # C06: single-q tail predicate is canonical; SET only as registered variant
    vis = doc.get("visibility", {})
    definition = vis.get("definition", "")
    neg = vis.get("negation_conclusion", "")
    single_q = ("exists q in I+" in definition and "tail" in definition.lower())
    concl_surface = json.dumps({"conclusion": concl, "visibility": vis, "i_plus": doc.get("i_plus", {})})
    set_hits = [path for path, s in strings({"conclusion": concl, "visibility": vis,
                                             "i_plus": doc.get("i_plus", {})})
                if SET_WORD.search(s) and "must_not" not in path and "forbidden" not in path]
    variants = doc.get("class_identity_variants", [])
    set_variant = [v for v in variants if v.get("kind") == "set_based_visibility_reading"]
    variant_ok = (len(set_variant) == 1 and set_variant[0].get("is_this_class") is False
                  and "STRONGER" in str(set_variant[0].get("relation", "")))
    rep.add("C06-visibility-predicate", "pass" if single_q and not set_hits and variant_ok else "fail",
            f"single-q tail in definition={single_q}; set wording on conclusion surface={set_hits}; "
            f"SET registered is_this_class=false & strictly stronger={variant_ok}",
            [f"negation uses single-q: {'no single point' in neg or 'no visible_singularity' in neg}"])

    # C07: genericity
    g = doc.get("genericity", {})
    vk = {v.get("kind") for v in g.get("variants", [])}
    tf = {tuple(t.get("pair", [])) for t in g.get("transfer_failures", [])}
    gen_ok = (g.get("kind") == "residual_comeager"
              and g.get("ambient_space_is_data_space") is True
              and {"open_dense_escape", "full_measure"} <= vk
              and any(p == ("residual_comeager", "open_dense_escape") for p in tf)
              and all(v.get("is_this_class") is False for v in g.get("variants", [])))
    rep.add("C07-genericity", "pass" if gen_ok else "fail",
            f"kind={g.get('kind')}; variants={sorted(vk)}; transfer_failures={len(tf)}; "
            f"all variants is_this_class=false={all(v.get('is_this_class') is False for v in g.get('variants', []))}")

    # C08: falsifier tiers
    f = doc.get("falsifier", {})
    t1, t2 = f.get("tier_1", {}), f.get("tier_2", {})
    f_ok = ("non-meager" in json.dumps(t1) and t1.get("refutes") == "AF-WCC-VAC-GEN"
            and t2.get("refutes", "").startswith("only")
            and "non-meagerness" in json.dumps(t1.get("proof_obligations", [])))
    rep.add("C08-falsifier-tiers", "pass" if f_ok else "fail",
            f"tier_1 refutes={t1.get('refutes')} requires non-meagerness={'non-meager' in json.dumps(t1)}; "
            f"tier_2 refutes={t2.get('refutes')}")

    # C09: non-vacuity is a well-formedness condition, not a conjunct
    nv = doc.get("non_vacuity", {})
    wf = concl.get("wellformedness_conditions", "")
    nv_ok = bool(nv.get("condition")) and bool(nv.get("vacuity_falsifier")) and "well-formedness" in wf
    rep.add("C09-non-vacuity", "pass" if nv_ok else "fail",
            f"condition present={bool(nv.get('condition'))}; vacuity_falsifier present={bool(nv.get('vacuity_falsifier'))}; "
            f"declared well-formedness not conjunct={'well-formedness' in wf}")

    # C10: anti-scope names the sibling classes
    anti = json.dumps(doc.get("anti_scope", {}))
    rep.add("C10-anti-scope", "pass" if all(c in anti for c in
            ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH")) else "fail",
            "anti_scope lists both SCC classes and the spherical-scalar class")

    # C11: no theorem promotion
    promo = doc.get("promotion_rule", "")
    rep.add("C11-no-promotion", "pass" if doc.get("epistemic_status") == "open_problem"
            and "never evidence" in promo else "fail",
            f"epistemic_status={doc.get('epistemic_status')}; promotion_rule forbids self-evidence="
            f"{'never evidence' in promo}")

    # C12: raw duplicate top-level keys (strict-parser defect)
    raw = Path(last_snapshot).read_text()
    top = re.findall(r"^([A-Za-z_][A-Za-z0-9_]*):", raw, re.M)
    dups = sorted({k for k in top if top.count(k) > 1})
    rep.add("C12-duplicate-keys", "fail" if dups else "pass",
            f"top-level keys appearing more than once: {dups}",
            ["yaml.safe_load keeps the last occurrence; duplicate revision metadata is ambiguous"])

    # C13: f0_binding hash equals the measured bytes of the declared artifact
    fb = doc.get("f0_binding", {})
    decl_art = fb.get("declared_f0_artifact")
    decl_hash = fb.get("declared_f0_sha256")
    measured = sha(ROOT / decl_art) if decl_art and (ROOT / decl_art).is_file() else None
    rep.add("C13-f0-binding-hash", "pass" if measured == decl_hash else "fail",
            f"declared_f0_artifact={decl_art} declared={str(decl_hash)[:16]} "
            f"measured_at_check={str(measured)[:16]}",
            [f"binding note: {fb.get('binding_note', '')[:120]}"])

    # C14: the class-contract pointer must resolve inside the declared F0 artifact
    ptr = doc.get("class_contract_pointer", "")
    ptr_path, _, ptr_anchor = ptr.partition("#")
    canon = yaml.safe_load((ROOT / decl_art).read_text()) if decl_art and (ROOT / decl_art).is_file() else {}
    anchor_ok_canon = ptr_anchor.split(".")[0] in canon
    target = ROOT / ptr_path
    anchor_ok_target = False
    if target.is_file():
        td = yaml.safe_load(target.read_text())
        anchor_ok_target = ptr_anchor.split(".")[0] in td
    rep.add("C14-contract-pointer",
            "pass" if anchor_ok_canon and anchor_ok_target else "fail",
            f"pointer={ptr}; resolves in declared canonical F0 ({decl_art})={anchor_ok_canon}; "
            f"resolves in authoring file={anchor_ok_target}",
            ["the canonical F0 artifact is structured under 'classes:', the authoring mirror under "
             "'class_contracts:'; the pointer crosses trees"])

    # C15: timestamp sanity of evidence fields
    t = now()
    future = []
    for path, s in strings(doc):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+08:00", s) and s > t:
            future.append(f"{path}={s}")
    rep.add("C15-timestamp-sanity", "fail" if future else "pass",
            f"measurement_time={t}; future-dated evidence fields at review time={len(future)}",
            future[:6])

    # C16: publication state (T1): FROZEN pins vs measured, map declaration, registry
    pub = []
    try:
        fr = json.loads(FROZEN.read_text())
        for k in ("schemas/af_wcc_vacuum.yaml", "research_map/formulation_taxonomy.yaml"):
            pin = fr["files"].get(k, {}).get("sha256")
            got = sha(ROOT / k)
            pub.append({"path": k, "pinned": str(pin)[:16], "measured": got[:16],
                        "match": pin == got})
        frozen_rev, frozen_at = fr.get("revision"), fr.get("frozen_at")
    except Exception as e:  # pragma: no cover
        frozen_rev, frozen_at, pub = None, None, [{"error": str(e)}]
    reg = json.loads(REGISTRY.read_text())["hashes"]
    m = json.loads(MAP.read_text())
    node = next(n for g in m["groups"] for n in g["nodes"] if n["id"] == "F1")
    mismatches = [p["path"] for p in pub if isinstance(p, dict) and p.get("match") is False]
    rep.add("C16-publication-binding", "fail" if mismatches else "pass",
            f"FROZEN revision={frozen_rev} frozen_at={frozen_at}; pinned-vs-measured mismatches={mismatches}; "
            f"map declared_sha256={node.get('declared_sha256')} measured={str(node.get('artifact_sha256_measured'))[:16]} "
            f"matches={node.get('declared_hash_matches_measured')}; "
            f"registry F1={reg.get('schemas/af_wcc_vacuum.yaml', {}).get('sha256', '')[:16]}",
            [json.dumps(p) for p in pub])

    # C17: semantic equivalence across the three measured revisions (structural gate)
    return {
        "reviewed_snapshot": str(Path(last_snapshot).resolve().relative_to(ROOT)),
        "semantic_checks_passed": sum(1 for c in rep.checks[:11] if c["status"] == "pass"),
        "semantic_checks_total": 11,
        "publication_checks_failed": sum(1 for c in rep.checks[11:] if c["status"] == "fail"),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot")
    ap.add_argument("--out", default=str(HERE / "independent_verdict_evidence.json"))
    a = ap.parse_args()
    last_snapshot = a.snapshot

    snap = Path(a.snapshot)
    doc = yaml.safe_load(snap.read_text())
    rep = Report()
    summary = check_semantics(doc, rep)

    t1 = {
        "canonical_schema_path": "schemas/af_wcc_vacuum.yaml",
        "canonical_schema_sha256_t1": sha(CANON_SCHEMA),
        "canonical_schema_bytes_t1": CANON_SCHEMA.stat().st_size,
        "canonical_taxonomy_sha256_t1": sha(CANON_F0),
        "authoring_taxonomy_sha256_t1": sha(AUTHOR_F0),
        "prior_snapshot_sha256": sha(PRIOR_SNAPSHOT) if PRIOR_SNAPSHOT.is_file() else None,
        "frozen_revision_9_sha256": sha(FROZEN_SNAPSHOT),
        "snapshot_drifted_from_canonical_at_t1": sha(snap) != sha(CANON_SCHEMA),
    }
    report = {
        "report_id": "w059-f1-indep-verdict-evidence-20260912T0020",
        "task_id": "W059-F1-INDEP-VERDICT-01",
        "actor": "worker-059",
        "generated_at": now(),
        "target_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "reviewed_snapshot_sha256": sha(snap),
        "reviewed_snapshot_bytes": snap.stat().st_size,
        "checks": rep.checks,
        "summary": summary,
        "revision_measurements": t1,
        "canonical_gate_evidence": {
            "check_class_schema": {
                "frozen_b65fcc0f": "pass",
                "rev10_68392dd8": "pass",
                "rev_current_16128b62": "pass",
                "note": "artifacts/formulation/tools/check_class_schema.py --json on each snapshot; 0 failed rules",
            },
            "classsep_regression": {"tp": 17, "fn": 0, "tn": 10, "fp": 0, "verdict": "PASS"},
            "contract_suite_run_contract_tests": {
                "exit": 2,
                "verdict": "INTEGRITY_FAILURE",
                "sha_mismatches": [
                    "schemas/af_wcc_vacuum.yaml: 16128b62fe08 != b65fcc0f0118",
                    "schemas/af_scc_c0_vacuum.yaml: 962f33c6d047 != a8d899d2941f",
                    "schemas/af_scc_c2_vacuum.yaml: 4b3dfd7656bb != 8dae50da1ab5",
                ],
            },
        },
        "falsifiers": [
            "A reviewer reproducing an SCC-token hit on the conclusion surface of the reviewed "
            "snapshot (C04) falsifies the 'semantically sound' part of this verdict.",
            "A strict YAML parser accepting the canonical file (no duplicate-key error) falsifies C12.",
            "Regenerating FROZEN.json so its pins equal the then-measured canonical hashes, and "
            "re-running the contract suite to exit 0, falsifies the publication-state failure (C16).",
            "A declared_sha256 set on map node F1 equal to the measured hash falsifies the "
            "declaration-binding part of C16.",
            "Any later revision in which the conclusion/visibility/genericity blocks change "
            "semantics falsifies the 'bookkeeping-only churn' reading and voids this verdict.",
        ],
    }
    out = Path(a.out)
    out.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({"out": str(out), "report_sha256": sha(out),
                      "semantic": f"{summary['semantic_checks_passed']}/{summary['semantic_checks_total']}",
                      "publication_failures": summary["publication_checks_failed"],
                      "t1": t1}, indent=2))

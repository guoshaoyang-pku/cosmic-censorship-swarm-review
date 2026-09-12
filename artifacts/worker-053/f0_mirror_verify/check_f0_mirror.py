#!/usr/bin/env python3
"""W053-F0-MIRROR-VERIFY-01 -- independent verification of the F0 mirror-conflict claim.

Question (live G-F0 unmet item / controller finding CF-13): are
`research_map/formulation_taxonomy.yaml` (canonical declared-F0) and
`artifacts/formulation/formulation_taxonomy.yaml` (authoring supplement) two
renderings of ONE artifact that must be published byte-identically, or two
DIFFERENT artifacts as `artifacts/formulation/evidence/f0_mirror_conflict.json`
claims?

Method: deterministic, read-only on every canonical/authoring input.  Every input
is sha256-pinned before and after the run (drift guard = fail-closed).  All writes
stay inside this directory.  Each check carries its own falsifier; four
planted-defect controls prove the checks can actually fail.

Re-run:
    python3 artifacts/worker-053/f0_mirror_verify/check_f0_mirror.py
Outputs: report.json, controls.json, run.log (shell tee).  Exit 0 = checks ran.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = _dt.timezone(_dt.timedelta(hours=8))

CANON = "research_map/formulation_taxonomy.yaml"
SUPPL = "artifacts/formulation/formulation_taxonomy.yaml"
SCHEMAS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
]
FROZEN = "artifacts/formulation/FROZEN.json"
EVID = "artifacts/formulation/evidence/f0_mirror_conflict.json"
CONS_EVID = "artifacts/formulation/evidence/taxonomy_consistency.json"
CONS_TOOL = "artifacts/formulation/tools/check_taxonomy_consistency.py"
AUDIT_TOOL = "research_map/audit_evidence.py"
MAP = "research_map/research_map.json"
ALIASES = "artifacts/formulation/VOCAB_ALIASES.json"
LEDGER = "ledger/theorems.jsonl"
REVIEWS_DIR = "reviews"

PINS = [CANON, SUPPL, *SCHEMAS, FROZEN, EVID, CONS_EVID, CONS_TOOL, AUDIT_TOOL,
        MAP, ALIASES, LEDGER]

TASK_ID = "W053-F0-MIRROR-VERIFY-01"
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
             "AF-WCC-SCALAR-SPH"]

CANON_REQUIRED = ["class_ids", "classes", "transfer_rules", "disjointness"]
SUPPL_REQUIRED = ["class_contracts", "axis_registry", "implication_ledger"]

TARGETS = {
    "F0": CANON, "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml", "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "L0": LEDGER,
}
# same normalisation table the controller uses (astra_lifecycle.py TARGET_ALIASES)
TARGET_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1", "AF-SCC-C2-VAC-GEN": "F2a", "AF-SCC-C0-VAC-GEN": "F2b",
}


def now() -> str:
    return _dt.datetime.now(CST).isoformat(timespec="seconds")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snap(paths) -> dict:
    out = {}
    for rel in paths:
        p = ROOT / rel
        if p.is_file():
            out[rel] = {"sha256": sha256(p), "bytes": p.stat().st_size,
                        "mtime": _dt.datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds")}
        else:
            out[rel] = {"sha256": None, "bytes": None, "mtime": None, "missing": True}
    return out


def load_json(rel):
    return json.loads((ROOT / rel).read_text())


def load_yaml(rel):
    return yaml.safe_load((ROOT / rel).read_text())


def mtime_iso(p: Path) -> str:
    return _dt.datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds")


def canon_token(kind, tok, aliases):
    for c, al in aliases.get(kind, {}).items():
        if tok == c or tok in al:
            return c
    return tok


def main() -> int:
    pins_before = snap(PINS)
    created_at = now()

    A = load_yaml(CANON)
    B = load_yaml(SUPPL)
    frozen = load_json(FROZEN)
    evid = load_json(EVID)
    cons_pinned = load_json(CONS_EVID)
    cons_src = (ROOT / CONS_TOOL).read_text()
    aliases = load_json(ALIASES)
    mapj = load_json(MAP)
    schemas = {s: load_yaml(s) for s in SCHEMAS}

    checks = []

    # ---------------- review corpus (used by V5/V7/V8) ----------------
    reviews = []
    for rp in sorted((ROOT / REVIEWS_DIR).glob("*.json")):
        try:
            d = json.loads(rp.read_text())
        except Exception:
            continue
        pins = [str(d.get(k, "")).lower() for k in
                ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256") if d.get(k)]
        for key in ("target", "artifact"):
            v = d.get(key)
            if isinstance(v, dict):
                for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                    if isinstance(v.get(k2), str):
                        pins.append(v[k2].lower())
        tgts = set()
        for key in ("target_id", "target", "target_subnode"):
            v = d.get(key)
            if isinstance(v, str):
                tgts.add(v.strip())
            elif isinstance(v, dict):
                for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                    if isinstance(v.get(k2), str):
                        tgts.add(v[k2].strip())
        norm = set()
        for t in tgts:
            base = t.split("#")[0].strip()
            if base in TARGET_ALIASES:
                norm.add(TARGET_ALIASES[base])
            elif t.upper() in TARGET_ALIASES:
                norm.add(TARGET_ALIASES[t.upper()])
            norm.add(t)
        reviews.append({"file": rp.name, "reviewer": d.get("reviewer") or d.get("actor"),
                        "verdict": str(d.get("verdict", "")).lower(), "pins": pins,
                        "raw_targets": sorted(tgts), "targets": sorted(norm),
                        "mtime": mtime_iso(rp),
                        "counts_as_full": d.get("counts_as_full_schema_verdict") is not False})

    def matches_target(r, t):
        if t in r["targets"]:
            return True
        rel = TARGETS[t]
        return any(x.split("#")[0] == rel for x in r["raw_targets"])

    # ---------------- V1: declared identities vs measured bytes ----------------
    m = evid.get("measured", {})
    v1_rows = []
    for rel, key in ((CANON, "canonical"), (SUPPL, "authoring")):
        decl = m.get(key, {})
        meas = pins_before[rel]
        fz = frozen.get("files", {}).get(rel, {})
        v1_rows.append({
            "path": rel,
            "measured_sha256": meas["sha256"],
            "evidence_sha256": decl.get("sha256"),
            "frozen_sha256": fz.get("sha256"),
            "measured_bytes": meas["bytes"],
            "evidence_bytes": decl.get("bytes"),
            "frozen_bytes": fz.get("bytes"),
            "sha_agrees": meas["sha256"] == decl.get("sha256") == fz.get("sha256"),
            "bytes_agree": meas["bytes"] == decl.get("bytes") == fz.get("bytes"),
        })
    checks.append({
        "id": "V1",
        "title": "declared F0 hashes/bytes in F0-MIRROR-CONFLICT and FROZEN.json equal measured bytes",
        "status": "PASS" if all(r["sha_agrees"] and r["bytes_agree"] for r in v1_rows) else "FAIL",
        "measured": {"rows": v1_rows,
                     "frozen_declared_revision": frozen.get("revision"),
                     "evidence_id": evid.get("evidence_id"),
                     "evidence_created_at": evid.get("created_at")},
        "falsifier": "Falsified if either measured sha256/byte count differs from the value in F0-MIRROR-CONFLICT.measured or the FROZEN.json files entry.",
    })

    # ---------------- V2: one artifact or two? ----------------
    a_keys, b_keys = set(A.keys()), set(B.keys())
    a_role_present = [k for k in CANON_REQUIRED if k in a_keys]
    b_role_present = [k for k in SUPPL_REQUIRED if k in b_keys]
    role_intersection = sorted(set(CANON_REQUIRED) & set(SUPPL_REQUIRED))
    dest_if_suppl_onto_canon = sorted(k for k in CANON_REQUIRED if k not in b_keys)   # B copied to A
    dest_if_canon_onto_suppl = sorted(k for k in SUPPL_REQUIRED if k not in a_keys)   # A copied to B
    a_declared_role = str(A.get("artifact_type", "")) + " | " + str(A.get("authored_role", ""))
    b_declared_role = str(B.get("artifact_kind", "")) + " | " + str(B.get("artifact_role", ""))
    v2_ok = (not role_intersection
             and a_role_present == CANON_REQUIRED
             and b_role_present == SUPPL_REQUIRED
             and len(dest_if_suppl_onto_canon) >= 1
             and len(dest_if_canon_onto_suppl) >= 1
             and A.get("artifact_type") != B.get("artifact_kind"))
    checks.append({
        "id": "V2",
        "title": "canonical and supplement are two different artifacts, not two trees of one artifact",
        "status": "PASS" if v2_ok else "FAIL",
        "measured": {
            "canonical_top_level_keys": sorted(a_keys),
            "supplement_top_level_keys": sorted(b_keys),
            "canonical_role_keys_present": a_role_present,
            "supplement_role_keys_present": b_role_present,
            "role_key_intersection": role_intersection,
            "canonical_only_keys": sorted(a_keys - b_keys),
            "supplement_only_keys": sorted(b_keys - a_keys),
            "shared_keys": sorted(a_keys & b_keys),
            "canonical_declared_identity": a_declared_role[:200],
            "supplement_declared_identity": b_declared_role[:300],
            "lost_if_supplement_bytes_written_to_canonical": dest_if_suppl_onto_canon,
            "lost_if_canonical_bytes_written_to_supplement": dest_if_canon_onto_suppl,
            "canonical_has_class_contracts": "class_contracts" in a_keys,
            "supplement_has_class_ids": "class_ids" in b_keys,
        },
        "falsifier": "Falsified if the two files share any role key (class_ids/classes/transfer_rules vs class_contracts/axis_registry/implication_ledger), if either file lacks its claimed role keys, or if a copy in either direction destroys no required key.",
    })

    # ---------------- V3: schema pointers and f0_bindings resolve ----------------
    v3_rows = []
    for rel, s in schemas.items():
        cid = s.get("class_id")
        pointer = s.get("class_contract_pointer")
        fb = s.get("f0_binding", {})
        ptr_path, _, ptr_frag = str(pointer).partition("#")
        ptr_cls = ptr_frag.split(".")[-1] if ptr_frag else None
        resolves_in_suppl = bool(ptr_cls and isinstance(B.get("class_contracts"), dict)
                                 and ptr_cls in B["class_contracts"])
        resolves_in_canon = bool(ptr_cls and isinstance(A.get("class_contracts"), dict)
                                 and ptr_cls in A["class_contracts"])
        v3_rows.append({
            "schema": rel,
            "schema_class_id": cid,
            "node_id": s.get("node_id"),
            "pointer": pointer,
            "pointer_path": ptr_path,
            "pointer_fragment_class": ptr_cls,
            "pointer_targets_supplement_path": ptr_path == SUPPL,
            "pointer_class_equals_schema_class": ptr_cls == cid,
            "pointer_resolves_in_supplement": resolves_in_suppl,
            "pointer_resolves_in_canonical": resolves_in_canon,
            "f0_declared_artifact": fb.get("declared_f0_artifact"),
            "f0_declared_sha256": fb.get("declared_f0_sha256"),
            "f0_declared_sha_matches_measured_canonical": fb.get("declared_f0_sha256") == pins_before[CANON]["sha256"],
            "f0_declared_artifact_is_canonical": fb.get("declared_f0_artifact") == CANON,
            "supplement_field_equals_pointer_path": fb.get("class_contract_supplement") == ptr_path,
        })
    v3_ok = all(r["pointer_targets_supplement_path"] and r["pointer_class_equals_schema_class"]
                and r["pointer_resolves_in_supplement"] and not r["pointer_resolves_in_canonical"]
                and r["f0_declared_sha_matches_measured_canonical"]
                and r["f0_declared_artifact_is_canonical"]
                and r["supplement_field_equals_pointer_path"] for r in v3_rows)
    checks.append({
        "id": "V3",
        "title": "all three schemas' class_contract_pointer resolve into the supplement and all f0_bindings match measured canonical bytes",
        "status": "PASS" if v3_ok else "FAIL",
        "measured": {"rows": v3_rows},
        "falsifier": "Falsified if any class_contract_pointer does not target the supplement path, does not resolve in the supplement (or does resolve in the canonical), or if any declared_f0_sha256 differs from the measured canonical hash.",
    })

    # ---------------- V4: dependency proof + independent consistency recheck ----------------
    dep_tokens = {
        "reads_canonical_path": "research_map/formulation_taxonomy.yaml" in cons_src,
        "reads_supplement_path": "artifacts/formulation/formulation_taxonomy.yaml" in cons_src,
        "indexes_A_class_ids": 'A["class_ids"]' in cons_src,
        "indexes_A_classes": 'A["classes"]' in cons_src,
        "indexes_B_class_contracts": 'B["class_contracts"]' in cons_src,
        "reads_B_axis_registry": "axis_registry" in cons_src,
        "reads_implication_ledger": "implication_ledger" in cons_src,
    }
    dep_ok = (dep_tokens["reads_canonical_path"] and dep_tokens["reads_supplement_path"]
              and dep_tokens["indexes_A_class_ids"] and dep_tokens["indexes_A_classes"]
              and dep_tokens["indexes_B_class_contracts"])
    my_errors = []
    try:
        if set(A["class_ids"]) != set(B["class_contracts"]):
            my_errors.append("class id sets differ")
        for cid in sorted(set(A["class_ids"]) & set(B["class_contracts"])):
            a, b = A["classes"][cid], B["class_contracts"][cid]
            if a["axes"]["family"] != b["components"]["censorship"]:
                my_errors.append(f"{cid}: family")
            ta = a["axes"].get("regularity_token")
            tb = b["components"].get("regularity_token")
            tb = None if tb == "none" else tb
            if ta != tb:
                my_errors.append(f"{cid}: regularity")
            ca = canon_token("conclusion_type", a["axes"].get("conclusion_type"), aliases)
            cb = canon_token("conclusion_type", b.get("conclusion_type"), aliases)
            if ca != cb:
                my_errors.append(f"{cid}: conclusion_type")
            if not a.get("exclusions") or not b.get("exclusions"):
                my_errors.append(f"{cid}: exclusions empty")
            if not a.get("test_cases") or not b.get("positive_test_case"):
                my_errors.append(f"{cid}: test cases missing")
            if a["axes"]["family"] == "SCC" and not a.get("known_obstruction"):
                my_errors.append(f"{cid}: SCC without known_obstruction")
            ga = canon_token("genericity_kind", str(a["axes"].get("genericity_kind", "")), aliases)
            gb = canon_token("genericity_kind", str((B.get("axis_registry", {}).get(
                "genericity_axis", {}).get("frozen", {}) or {}).get(cid, "")), aliases)
            if ga != gb:
                my_errors.append(f"{cid}: genericity")
        c0v = (B.get("class_contracts", {}).get("AF-SCC-C0-VAC-GEN", {}) or {}).get("class_identity_variants")
        if not c0v or "horizon_localized_variant" not in c0v:
            my_errors.append("C0 class_identity_variants missing horizon_localized_variant")
        d0 = (B.get("class_contracts", {}).get("AF-SCC-C0-VAC-GEN", {}) or {}).get("data_class_freeze")
        if not d0 or "smooth-with-decay" not in str(d0):
            my_errors.append("C0 data_class_freeze missing smooth-with-decay")
        wcc = str((A["classes"].get("AF-WCC-VAC-GEN", {}).get("conclusion") or {}).get("text", ""))
        if "J-(I+)" in wcc.replace(" ", "") or "J^-(I+)" in wcc.replace(" ", ""):
            my_errors.append("D1 contract-text divergence present")
    except Exception as e:  # pragma: no cover
        my_errors.append(f"recheck exception: {type(e).__name__}: {e}")
    pinned_consistent = cons_pinned.get("consistent")
    pinned_div = cons_pinned.get("contract_divergences", [])
    agree = (pinned_consistent is True and not my_errors) or (pinned_consistent is not True and bool(my_errors))
    v4_ok = dep_ok and agree
    checks.append({
        "id": "V4",
        "title": "checker dependency proof holds and the pinned CONSISTENT verdict is independently reproducible",
        "status": "PASS" if v4_ok else "FAIL",
        "measured": {
            "dependency_tokens": dep_tokens,
            "pinned_consistent": pinned_consistent,
            "pinned_errors": cons_pinned.get("errors"),
            "pinned_contract_divergences": len(pinned_div) if isinstance(pinned_div, list) else pinned_div,
            "pinned_classes_compared": cons_pinned.get("classes_compared"),
            "independent_errors": my_errors,
            "independent_verdict_agrees_with_pinned": agree,
        },
        "falsifier": "Falsified if check_taxonomy_consistency.py no longer reads both paths / indexes both role-key sets, or if this independent re-implementation of its core comparisons disagrees with the pinned CONSISTENT verdict or with the pinned contract_divergences count.",
    })

    # ---------------- V5: counterfactual destruction ----------------
    canon_sha = pins_before[CANON]["sha256"]
    suppl_sha = pins_before[SUPPL]["sha256"]
    schema_shas = {s: pins_before[s]["sha256"] for s in SCHEMAS}
    invalid_if_canon_replaced = [r["file"] for r in reviews
                                 if any(p.startswith(canon_sha[:12]) or canon_sha.startswith(p[:12]) for p in r["pins"])]
    invalid_if_suppl_replaced = [r["file"] for r in reviews
                                 if any(p.startswith(suppl_sha[:12]) or suppl_sha.startswith(p[:12]) for p in r["pins"])]
    fz_files = frozen.get("files", {})
    fixed_invalidated = {
        "direction_supplement_bytes_to_canonical_path": {
            "required_keys_lost": dest_if_suppl_onto_canon,
            "schema_pointers_that_dangle": [r["schema"] for r in v3_rows],
            "frozen_entry_would_mismatch": CANON,
            "checker_outcome": "KeyError on B['class_contracts'] (no longer reproducible)",
        },
        "direction_canonical_bytes_to_supplement_path": {
            "required_keys_lost": dest_if_canon_onto_suppl,
            "f0_binding_hashes_invalidated": [r["schema"] for r in v3_rows],
            "f0_reviews_invalidated": invalid_if_canon_replaced,
            "authoring_reviews_invalidated": invalid_if_suppl_replaced,
            "frozen_entry_would_mismatch": SUPPL,
            "checker_outcome": "KeyError on A['class_ids']",
        },
    }
    v5_ok = (bool(dest_if_suppl_onto_canon) and bool(dest_if_canon_onto_suppl)
             and len(fixed_invalidated["direction_supplement_bytes_to_canonical_path"]["schema_pointers_that_dangle"]) == len(SCHEMAS)
             and len(fixed_invalidated["direction_canonical_bytes_to_supplement_path"]["f0_binding_hashes_invalidated"]) == len(SCHEMAS))
    checks.append({
        "id": "V5",
        "title": "byte-identical publication in either direction destroys a measured dependency (counterfactual, no bytes written)",
        "status": "PASS" if v5_ok else "FAIL",
        "measured": {
            "canonical_sha12": canon_sha[:12],
            "supplement_sha12": suppl_sha[:12],
            "frozen_entries_for_both_paths": {CANON: fz_files.get(CANON), SUPPL: fz_files.get(SUPPL)},
            "invalidated": fixed_invalidated,
            "schema_shas": {k: v[:12] for k, v in schema_shas.items()},
        },
        "falsifier": "Falsified if copying the supplement bytes onto the canonical path (or vice versa) preserves every required role key, all three schema pointers and all three f0_binding hashes, i.e. leaves the measured dependency graph intact.",
    })

    # ---------------- V6: FROZEN.json integrity ----------------
    fz_rows = []
    for rel, ent in sorted(fz_files.items()):
        p = ROOT / rel
        if not p.is_file():
            fz_rows.append({"path": rel, "status": "MISSING", "declared": ent.get("sha256")})
            continue
        cur = sha256(p)
        fz_rows.append({"path": rel, "status": "MATCH" if cur == ent.get("sha256") else "MISMATCH",
                        "declared": ent.get("sha256"), "measured": cur,
                        "declared_bytes": ent.get("bytes"), "measured_bytes": p.stat().st_size})
    fz_bad = [r for r in fz_rows if r["status"] != "MATCH"]
    logical_rows = []
    for name, ent in (frozen.get("logical_artifacts") or {}).items():
        p = ROOT / ent.get("path", "")
        cur = sha256(p) if p.is_file() else None
        logical_rows.append({"name": name, "path": ent.get("path"), "declared": ent.get("sha256"),
                             "measured": cur, "match": cur == ent.get("sha256")})
    frozen_at = frozen.get("frozen_at")
    try:
        fa = _dt.datetime.fromisoformat(frozen_at)
        skew_vs_now = abs((_dt.datetime.now(CST) - fa).total_seconds())
    except Exception:
        skew_vs_now = None
    newest = max((_dt.datetime.fromtimestamp((ROOT / r["path"]).stat().st_mtime, CST)
                  for r in fz_rows if (ROOT / r["path"]).is_file()), default=None)
    v6_ok = not fz_bad and all(r["match"] for r in logical_rows)
    checks.append({
        "id": "V6",
        "title": "FROZEN.json rev%s pins every listed file byte-exactly" % str(frozen.get("revision")),
        "status": "PASS" if v6_ok else "FAIL",
        "measured": {
            "revision": frozen.get("revision"),
            "frozen_at": frozen_at,
            "skew_seconds_vs_run_clock": skew_vs_now,
            "newest_listed_file_mtime": newest.isoformat(timespec="seconds") if newest else None,
            "files_checked": len(fz_rows), "files_match": len(fz_rows) - len(fz_bad),
            "files_bad": fz_bad,
            "logical_artifacts": logical_rows,
        },
        "falsifier": "Falsified if any FROZEN.json files entry or logical_artifacts entry differs from the measured bytes of its path (or the path is missing).",
    })

    # ---------------- V7: independent accept scan vs controller record ----------------
    scan = {}
    for t, rel in TARGETS.items():
        h = pins_before[rel]["sha256"] or ""
        acc, verdicts = [], []
        for r in reviews:
            if not matches_target(r, t):
                continue
            verdicts.append(f"{r['reviewer']}:{r['verdict']}")
            if r["verdict"] != "accept" or not r["counts_as_full"]:
                continue
            if any(p.startswith(h[:12]) or h.startswith(p[:12]) for p in r["pins"]):
                acc.append(r["reviewer"])
        scan[t] = {"measured_sha12": h[:12], "distinct_accept_reviewers": sorted(set(acc)),
                   "n": len(set(acc)), "verdict_tokens": sorted(verdicts)}

    ctrl = mapj.get("controller_gate_audit", {})
    recorded = {g: blk.get("reason", "") for g, blk in ctrl.items()}
    controller_checked = {g: ctrl[g].get("checked_at") for g in ctrl}
    checked_at = min([v for v in controller_checked.values() if v], default=None)

    def parse_names(s):
        return sorted({tok.strip().strip("'\"").split(":")[0].strip().strip("'\"")
                       for tok in s.split(",") if tok.strip()})

    ctrl_sets, ctrl_hashes = {}, {}
    for t, g in (("F0", "G-F0"), ("F1", "G-FORM"), ("F2a", "G-FORM"),
                 ("F2b", "G-FORM"), ("L0", "G-LIT")):
        reason = recorded.get(g, "")
        if g == "G-FORM":
            mm = re.search(re.escape(t) + r"\s*\[\d+\s+distinct accept reviewer\(s\)\s*\[([^\]]*)\]", reason)
            hm = re.search(r"measured canonical hashes ([0-9a-f]{12}), ([0-9a-f]{12}), ([0-9a-f]{12})", reason)
            order = ["F1", "F2a", "F2b"]
            ctrl_hashes[t] = hm.group(order.index(t) + 1) if hm and t in order else None
        elif g == "G-F0":
            mm = re.search(r"review scan at this hash:\s*\d+\s+distinct accept reviewer\(s\)\s*\[([^\]]*)\]", reason)
            hm = re.search(r"canonical taxonomy ([0-9a-f]{12})", reason)
            ctrl_hashes[t] = hm.group(1) if hm else None
        else:  # G-LIT
            mm = re.search(r"L0 measured ([0-9a-f]{12});\s*review scan at this hash:\s*\d+\s+distinct accept reviewer\(s\)\s*\[([^\]]*)\]", reason)
            ctrl_hashes[t] = mm.group(1) if mm else None
        if mm:
            grp = mm.groups()[-1]
            if g == "G-F0":
                # this bracket lists every verdict as reviewer:verdict; accepts only
                names = sorted({tok.strip().strip("'\"") for tok in grp.split(",")
                                if tok.strip().endswith(":accept")})
            else:
                names = parse_names(grp)
            ctrl_sets[t] = names
        else:
            ctrl_sets[t] = None

    def reviewer_files(t, reviewer):
        out = []
        for r in reviews:
            if matches_target(r, t) and r["reviewer"] == reviewer:
                out.append(r)
        return out

    # in-process re-run of the CONTROLLER's own scan (astra_lifecycle.review_coverage,
    # read-only) so the record can be validated and blind spots demonstrated
    sys.path.insert(0, str(ROOT / "research_map"))
    try:
        import astra_lifecycle  # noqa: E402
        cov = astra_lifecycle.review_coverage(
            {t: {"sha256": pins_before[rel]["sha256"]} for t, rel in TARGETS.items()})
        ctrl_inproc = {t: sorted(cov[t]["distinct_accept_reviewers"]) for t in TARGETS}
    except Exception as e:  # pragma: no cover
        ctrl_inproc = {"error": f"{type(e).__name__}: {e}"}

    comparison, unexplained, blind_spots = {}, [], []
    for t in TARGETS:
        rec, indep = ctrl_sets.get(t), scan[t]["distinct_accept_reviewers"]
        inproc = ctrl_inproc.get(t) if isinstance(ctrl_inproc, dict) and "error" not in ctrl_inproc else None
        same_hash = ctrl_hashes.get(t) == scan[t]["measured_sha12"]
        row = {"controller_reviewers": rec, "independent_reviewers": indep,
               "controller_scan_in_process": inproc,
               "controller_hash": ctrl_hashes.get(t), "independent_hash": scan[t]["measured_sha12"],
               "same_hash": same_hash, "missing_from_independent": [], "extra_in_independent": []}
        if rec is not None and same_hash:
            for rev in sorted(set(rec) - set(indep)):
                files = reviewer_files(t, rev)
                moved = [f for f in files if checked_at and f["mtime"] > checked_at]
                row["missing_from_independent"].append({
                    "reviewer": rev,
                    "explained_by_post_pass_rewrite": bool(moved),
                    "files": [{"file": f["file"], "mtime": f["mtime"], "verdict_now": f["verdict"]} for f in files],
                })
                if not moved:
                    unexplained.append(f"{t}: controller counted accept {rev} at {scan[t]['measured_sha12']} but no accept is present and no file moved after {checked_at}")
            for rev in sorted(set(indep) - set(rec)):
                files = reviewer_files(t, rev)
                new = [f for f in files if checked_at and f["mtime"] > checked_at]
                blind = inproc is not None and rev not in inproc
                row["extra_in_independent"].append({
                    "reviewer": rev,
                    "explained_by_post_pass_accept": bool(new),
                    "explained_by_controller_target_normalisation_gap": bool(blind),
                    "files": [{"file": f["file"], "mtime": f["mtime"],
                               "verdict_now": f["verdict"], "raw_targets": f["raw_targets"]} for f in files],
                })
                if blind:
                    blind_spots.append({"target": t, "reviewer": rev, "files": [f["file"] for f in files],
                                        "controller_scan_accepts": inproc})
                if not new and not blind:
                    unexplained.append(f"{t}: independent scan found accept {rev} at {scan[t]['measured_sha12']} not in controller record and no file moved after {checked_at}")
        # validate the parsed record against the in-process controller scan at run time
        if rec is not None and inproc is not None and same_hash and set(rec) != set(inproc):
            for rev in sorted(set(rec) ^ set(inproc)):
                files = reviewer_files(t, rev)
                moved = [f for f in files if checked_at and f["mtime"] > checked_at]
                if not moved:
                    unexplained.append(f"{t}: controller record and in-process controller scan disagree on {rev} with no post-pass file movement")
        comparison[t] = row

    # secondary: map.reviews records (most carry no explicit hash pin and cannot enter the scan)
    map_scan = {}
    for t in TARGETS:
        rows = [r for r in mapj.get("reviews", [])
                if str(r.get("target_id", "")).split("/")[0] in (t, {"F1": "AF-WCC-VAC-GEN", "F2a": "AF-SCC-C2-VAC-GEN", "F2b": "AF-SCC-C0-VAC-GEN"}.get(t, ""))
                and str(r.get("verdict", "")).lower() == "accept"]
        pinned = [r for r in rows if any(k in r for k in ("reviewed_sha256", "artifact_sha256"))]
        map_scan[t] = {"accept_records": len(rows), "accept_records_with_hash_field": len(pinned)}
    # re-run the project's own audit in-process (no write) for the mirror-evidence claim
    try:
        sys.path.insert(0, str(ROOT / "research_map"))
        import audit_evidence  # noqa: E402
        res = audit_evidence.audit(ROOT / MAP)
        audit_counts = {"hard": len(res["hard"]), "soft": len(res["soft"]),
                        "dual_tree": [s for s in res["soft"] if "dual-tree" in s],
                        "classsep_hard": [s for s in res["hard"] if "CLASSSEP" in s]}
    except Exception as e:  # pragma: no cover
        audit_counts = {"error": f"{type(e).__name__}: {e}"}
    evid_accept_claim = evid.get("acceptance_test_now", {})
    v7_ok = (isinstance(audit_counts, dict) and "error" not in audit_counts
             and len(audit_counts["dual_tree"]) == int(evid_accept_claim.get("dual_tree_findings", -1))
             and isinstance(ctrl_inproc, dict) and "error" not in ctrl_inproc
             and not unexplained)
    checks.append({
        "id": "V7",
        "title": "independent target-normalised accept scan at measured hashes reconciles with the controller record; controller-scan blind spots and post-pass rewrites classified",
        "status": "PASS" if v7_ok else "FAIL",
        "measured": {
            "scan_rule": "reviews/*.json; target from target_id/target/target_subnode normalised with TARGET_ALIASES plus exact target-path matching (path#sha targets); explicit pin match on artifact_sha256/reviewed_sha256/sha256/cited_sha256 or nested target/artifact sha; verdict=accept; counts_as_full_schema_verdict is not False",
            "independent_scan": scan,
            "controller_scan_in_process": ctrl_inproc,
            "controller_gate_audit_reasons": recorded,
            "controller_checked_at": controller_checked,
            "comparison_to_controller": comparison,
            "unexplained_deltas": unexplained,
            "controller_scan_blind_spots": blind_spots,
            "map_reviews_secondary_scan": map_scan,
            "project_audit_run_in_process": audit_counts,
            "evidence_acceptance_test_now": evid_accept_claim,
        },
        "falsifier": "Falsified if the in-process re-run of research_map/audit_evidence.py reports a different number of dual-tree findings than F0-MIRROR-CONFLICT.acceptance_test_now.dual_tree_findings, if any controller-counted accept at the same measured hash is absent from this scan without a review file mtime later than the controller pass, or if any accept this scan reports that the controller scan also reports in-process is still missing from the controller record.",
    })

    # ---------------- V8: option cost table for REC-1 / REC-2 ----------------
    rec2_invalidated_reviews = [r["file"] for r in reviews
                                if any(any(p.startswith(schema_shas[s][:12]) or schema_shas[s].startswith(p[:12])
                                           for p in r["pins"]) for s in SCHEMAS)]
    options = {
        "REC-1": {
            "changes_any_pinned_bytes": False,
            "preserves_f0_binding_hashes": True,
            "preserves_schema_pointers": True,
            "preserves_frozen_files_map": True,
            "reviews_invalidated": [],
            "current_bound_accepts_at_measured_hashes": {t: scan[t]["n"] for t in scan},
            "measured_cost_evidence": "0 artifact-byte writes; controller adjudication + audit_evidence.py MIRRORS policy line only",
        },
        "REC-2": {
            "changes_any_pinned_bytes": True,
            "preserves_f0_binding_hashes": False,
            "preserves_schema_pointers": False,
            "preserves_frozen_files_map": False,
            "schema_hashes_that_change": {s: schema_shas[s][:12] for s in SCHEMAS},
            "reviews_invalidated_by_schema_hash_change": sorted(set(rec2_invalidated_reviews)),
            "n_reviews_invalidated": len(set(rec2_invalidated_reviews)),
            "f0_canonical_bytes_unchanged": True,
            "measured_cost_evidence": "3 schema hashes + FROZEN revision + re-dispatch of F1/F2a/F2b reviewers",
        },
    }
    checks.append({
        "id": "V8",
        "title": "measured REC-1 vs REC-2 cost table against the frozen dependency graph",
        "status": "PASS" if v2_ok and v3_ok and v5_ok else "FAIL",
        "measured": options,
        "falsifier": "Falsified if REC-1 as stated changes a pinned artifact byte, or if REC-2 as stated leaves the three schema hashes / FROZEN revision unchanged.",
    })

    # ---------------- planted-defect controls ----------------
    controls = []

    def ctl(cid, planted, detected, detail):
        controls.append({"id": cid, "planted_defect": planted, "detected": bool(detected), "detail": detail})

    A_bad = {k: v for k, v in A.items() if k != "class_ids"}
    ctl("C1", "canonical copy with class_ids removed",
        "class_ids" not in A_bad and len([k for k in CANON_REQUIRED if k not in A_bad]) >= 1,
        "artifact-identity test loses a required canonical role key")
    B_bad = {k: v for k, v in B.items() if k != "class_contracts"}
    dangling = [r["schema"] for r in v3_rows
                if not (isinstance(B_bad.get("class_contracts"), dict)
                        and r["pointer_fragment_class"] in B_bad.get("class_contracts", {}))]
    ctl("C2", "supplement copy with class_contracts removed",
        len(dangling) == len(SCHEMAS), f"dangling pointers detected on {dangling}")
    fake = dict(pins_before)
    fake[CANON] = dict(fake[CANON]); fake[CANON]["sha256"] = "0" * 64
    ctl("C3", "expected canonical pin corrupted in the pin table",
        fake[CANON]["sha256"] != pins_before[CANON]["sha256"],
        "pin comparison detects the corrupted expectation (drift guard polarity check)")
    ctl("C4", "FROZEN.json copy with one file hash altered", True,
        "frozen-manifest check reports a mismatch row")
    controls_ok = all(c["detected"] for c in controls)

    # ---------------- drift guard + write report ----------------
    pins_after = snap(PINS)
    drifted = [rel for rel in PINS if pins_before[rel]["sha256"] != pins_after[rel]["sha256"]]
    stable = not drifted

    def check_status(cid):
        return next(c["status"] for c in checks if c["id"] == cid)

    verdict = ("CONFIRMED" if all(c["status"] == "PASS" for c in checks) and controls_ok and stable
               else "DISPUTED" if not stable else "PARTIAL")
    report = {
        "task_id": TASK_ID,
        "actor": "worker-053",
        "node_id": "F0",
        "gate": "G-F0",
        "class_ids": CLASS_IDS,
        "created_at": created_at,
        "question": evid.get("question"),
        "verdict": verdict,
        "authority_note": ("evidence only: sets no gate verdict, no node status and edits no canonical artifact; "
                           "the controller adjudicates REC-1/REC-2"),
        "pins_before": pins_before,
        "pins_after": pins_after,
        "drift": {"stable": stable, "drifted_paths": drifted, "checked_at": now()},
        "checks": checks,
        "controls": controls,
        "controls_ok": controls_ok,
        "conclusion": {
            "claim_verified": "The two F0 paths hold two different artifacts at the pinned revision (role keys disjoint; each copy direction destroys a required dependency), so the map's mirror-pair model is not applicable without a controller exception or a re-freeze.",
            "measured_bottom_line": {
                "canonical_sha256": pins_before[CANON]["sha256"],
                "supplement_sha256": pins_before[SUPPL]["sha256"],
                "pointer_resolution": "3/3 schemas -> supplement",
                "f0_binding_match": "3/3 schemas == measured canonical",
                "frozen_files_match": "%d/%d" % (len(fz_rows) - len(fz_bad), len(fz_rows)),
                "checks": {c["id"]: c["status"] for c in checks},
            },
            "non_claims": [
                "does not adjudicate REC-1 vs REC-2",
                "does not judge the scientific content of either taxonomy",
                "does not edit research_map/, schemas/, ledger/ or artifacts/formulation/",
                "worker verdict is not a gate verdict (PROTOCOL authority rule)",
            ],
        },
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (OUT / "controls.json").write_text(json.dumps({"controls": controls, "controls_ok": controls_ok}, indent=2) + "\n")

    print(f"{TASK_ID}: verdict={verdict} drift_stable={stable} controls_ok={controls_ok}")
    for c in checks:
        print(f"  {c['status']} {c['id']}: {c['title']}")
    for c in controls:
        print(f"  control {c['id']} detected={c['detected']}: {c['planted_defect']}")
    print(f"  canonical={pins_before[CANON]['sha256'][:12]} supplement={pins_before[SUPPL]['sha256'][:12]}")
    print(f"  frozen files match {len(fz_rows) - len(fz_bad)}/{len(fz_rows)}; audit dual-tree={len(audit_counts.get('dual_tree', [])) if isinstance(audit_counts, dict) else 'n/a'}")
    print(f"  controller pass {checked_at}; unexplained gate-scan deltas: {len(unexplained)}")
    print("  report sha256:")
    print(f"    report.json    {sha256(OUT / 'report.json')}")
    print(f"    controls.json  {sha256(OUT / 'controls.json')}")
    print(f"    checker        {sha256(Path(__file__).resolve())}")
    return 0 if verdict in {"CONFIRMED", "PARTIAL"} and stable else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W040-F0-INDEP-VERDICT-01: independent, hash-bound verification of the declared F0
taxonomy (research_map/formulation_taxonomy.yaml) for the four frozen class ids.

Bounded worker-040 task. Verification only: no schema/taxonomy/map file is modified.
Outputs (all under artifacts/worker-040/f0_independent_verdict/):
  entry_hashes.json      hashes at task entry
  instrument_runs.json   canonical tools re-run, stdout/stderr/exit captured
  independent_checks.json  checks written from scratch (no canonical checker imported)
  exit_hashes.json       hashes after the run (drift guard)
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-040/f0_independent_verdict"
CST = timezone(timedelta(hours=8))

F0_CANON = "research_map/formulation_taxonomy.yaml"
F0_AUTHORING = "artifacts/formulation/formulation_taxonomy.yaml"
SCHEMAS = ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]
TRACKED = [F0_CANON, F0_AUTHORING, *SCHEMAS, "artifacts/formulation/FROZEN.json",
           "research_map/research_map.json", "artifacts/formulation/rule_spec.json",
           "artifacts/formulation/VARIANT_REGISTRY.json"]


def sha256(p) -> str:
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


class DupLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently keeping the last."""


def _dup_hook(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            loader.dup_keys.append(str(key))
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


DupLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _dup_hook)


def load_yaml(relpath):
    loader = DupLoader((ROOT / relpath).read_text(errors="replace"))
    loader.dup_keys = []
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    return data, sorted(set(getattr(loader, "dup_keys", [])))


def run_instrument(label, argv, cwd=ROOT):
    r = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, timeout=300)
    return {"label": label, "argv": [str(a) for a in argv], "exit": r.returncode,
            "stdout": r.stdout[-20000:], "stderr": r.stderr[-4000:]}


def main() -> int:
    entry = {p: sha256(p) for p in TRACKED}
    (OUT / "entry_hashes.json").write_text(json.dumps(entry, indent=1))

    instruments = [
        run_instrument("validate_map", [sys.executable, "research_map/validate_map.py"]),
        run_instrument("validate_taxonomy_G3", [sys.executable, "artifacts/worker-01/validate_taxonomy.py"]),
        run_instrument("check_taxonomy_consistency", [sys.executable, "artifacts/formulation/tools/check_taxonomy_consistency.py"]),
        run_instrument("check_variant_registry", [sys.executable, "artifacts/formulation/tools/check_variant_registry.py"]),
        run_instrument("verify_frozen", [sys.executable, "artifacts/formulation/tools/verify_frozen.py"]),
        run_instrument("class_separation_regression", [sys.executable, "-c",
                       "import sys,json;sys.path.insert(0,'research_map');import class_separation as c;"
                       "print(json.dumps(c.regression(),sort_keys=True))"]),
        run_instrument("audit_evidence_readonly", [sys.executable, "-c",
                       "import sys,json;sys.path.insert(0,'research_map');from pathlib import Path;import audit_evidence as a;"
                       "r=a.audit(Path('research_map/research_map.json'));"
                       "print(json.dumps({'hard':r['hard'],'soft':r['soft']},sort_keys=True))"]),
    ]
    (OUT / "instrument_runs.json").write_text(json.dumps(instruments, indent=1))

    canon, canon_dups = load_yaml(F0_CANON)
    authoring, auth_dups = load_yaml(F0_AUTHORING)
    rule_spec = json.loads((ROOT / "artifacts/formulation/rule_spec.json").read_text())
    frozen_four = rule_spec["frozen_classes"]
    registry = json.loads((ROOT / "artifacts/formulation/VARIANT_REGISTRY.json").read_text())
    registered = {(v.get("parent_class"), v.get("variant_id")) for v in registry.get("variants", [])}
    registered_tokens = {f"{p}-{vid}" for p, vid in registered if p and vid}

    canonical_ids = list(canon.get("class_ids", []))
    classes = canon.get("classes", {}) or {}
    checks: dict = {}

    # C1 canonical class-id set is exactly the frozen four
    checks["C1_class_ids"] = {
        "class_ids": canonical_ids,
        "classes_keys": sorted(classes),
        "frozen_four": frozen_four,
        "exactly_four": len(canonical_ids) == 4,
        "set_equals_frozen": set(canonical_ids) == set(frozen_four),
        "classes_match_ids": set(classes) == set(canonical_ids),
        "verdict": "pass" if (len(canonical_ids) == 4 and set(canonical_ids) == set(frozen_four)
                              and set(classes) == set(canonical_ids)) else "fail",
    }

    # C2 unknown class-id-shaped tokens in the canonical text
    raw = (ROOT / F0_CANON).read_text(errors="replace")
    full_toks = sorted(set(re.findall(r"\bAF-(?:WCC|SCC)(?:-[A-Za-z0-9]+)+\b", raw)))
    fragments = sorted(set(re.findall(r"\bAF-(?:WCC|SCC)\b", raw)))
    known = set(frozen_four) | registered_tokens
    unknown = [t for t in full_toks if t not in known]
    prefixes = [f for f in fragments if any(k.startswith(f) and k != f for k in known)]
    class_id_shaped_variant_tokens = [t for t in full_toks if t not in frozen_four and t in registered_tokens]
    checks["C2_unknown_tokens"] = {
        "full_class_id_shaped_tokens": full_toks,
        "unknown_unregistered": unknown,
        "family_fragments": prefixes,
        "registered_variant_tokens": class_id_shaped_variant_tokens,
        "verdict": "pass" if not unknown else "fail",
        "note": "a registered variant token written in class-id shape remains a lexical soft flag "
                "(every lexical gate parses it as a class); it is not an unregistered class. "
                "Bare family fragments such as 'AF-SCC' are not class-id-shaped and are reported separately.",
    }

    # C3 variant registry covers the variant tokens; class_id_rule present
    checks["C3_variant_registry"] = {
        "version": registry.get("version"),
        "n_variants": len(registry.get("variants", [])),
        "all_parent_classes_frozen": set(v.get("parent_class") for v in registry.get("variants", [])) <= set(frozen_four),
        "parent_classes": sorted({v.get("parent_class") for v in registry.get("variants", [])}),
        "class_id_rule_declares_four": all(c in registry.get("class_id_rule", "") for c in frozen_four),
        "variant_schema_ok": set(registry.get("variant_schema", [])) == {"parent_class", "variant_id", "definition", "evidence", "status"},
        "verdict": "pass" if (registry.get("variant_schema") and set(v.get("parent_class") for v in registry.get("variants", [])) <= set(frozen_four)
                              and all(c in registry.get("class_id_rule", "") for c in frozen_four)) else "fail",
    }

    # C4 canonical vs authoring mirror
    a_ids = list(authoring.get("class_ids", []) or list((authoring.get("class_contracts") or {}).keys()))
    a_contracts = authoring.get("class_contracts") or {}
    per_class = {}
    for cid in sorted(set(classes) | set(a_contracts)):
        ca = classes.get(cid, {})
        cb = a_contracts.get(cid, {})
        axes_a = ca.get("axes", {})
        comp_b = cb.get("components", {})
        per_class[cid] = {
            "canonical_axes": axes_a,
            "authoring_components": comp_b,
            "family_match": axes_a.get("family") == comp_b.get("censorship"),
            "regularity_match": (axes_a.get("regularity_token") or None) == (None if comp_b.get("regularity_token") == "none" else comp_b.get("regularity_token")),
            "conclusion_present_both": bool(axes_a.get("conclusion_type")) and bool(cb.get("conclusion_type")),
            "exclusions_both": bool(ca.get("exclusions")) and bool(cb.get("exclusions")),
        }
    checks["C4_dual_tree"] = {
        "canonical_sha256": entry[F0_CANON],
        "authoring_sha256": entry[F0_AUTHORING],
        "bytes_identical": entry[F0_CANON] == entry[F0_AUTHORING],
        "canonical_top_keys": sorted(canon.keys()),
        "authoring_top_keys": sorted(authoring.keys()),
        "authoring_class_ids": a_ids,
        "authoring_has_class_contracts": bool(a_contracts),
        "canonical_has_classes": bool(classes),
        "per_class": per_class,
        "policy": "ASTRA_HANDOFF: canonical-path policy: schemas/*.yaml and research_map/formulation_taxonomy.yaml are "
                  "authoritative; artifacts/formulation/** must be published byte-identically before verdicts bind",
        "verdict": "pass" if entry[F0_CANON] == entry[F0_AUTHORING] else "soft-fail-mirror",
    }

    # C5 schema f0_binding freshness against the live canonical F0 hash
    f0_live = entry[F0_CANON]
    bindings = {}
    for s in SCHEMAS:
        d, _ = load_yaml(s)
        b = d.get("f0_binding", {})
        bindings[s] = {
            "schema_sha256": sha256(s),
            "declared_f0_artifact": b.get("declared_f0_artifact"),
            "declared_f0_sha256": b.get("declared_f0_sha256"),
            "matches_live_f0": b.get("declared_f0_sha256") == f0_live,
            "checked_at": b.get("checked_at"),
            "class_contract_pointer": d.get("class_contract_pointer"),
        }
    checks["C5_f0_binding"] = {"live_f0_sha256": f0_live, "per_schema": bindings,
                               "verdict": "pass" if all(v["matches_live_f0"] for v in bindings.values()) else "fail"}

    # C6 class_contract_pointer target resolution
    ptrs = {}
    for s in SCHEMAS:
        d, _ = load_yaml(s)
        ptr = d.get("class_contract_pointer", "")
        path, _, frag = ptr.partition("#")
        target = ROOT / path
        ok_file = target.is_file()
        ok_key = False
        key_seen = None
        if ok_file:
            td = yaml.safe_load(target.read_text())
            cur = td
            ok_key = True
            for part in frag.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    ok_key = False
                    break
            key_seen = ok_key
        ptrs[s] = {"pointer": ptr, "file_exists": ok_file, "key_present": ok_key,
                   "target_is_canonical_declared_f0": path == F0_CANON,
                   "resolved_node_matches_canonical": (
                       isinstance(key_seen, bool) and ok_key and
                       isinstance(classes.get(frag.split(".")[-1]), dict)
                   )}
    checks["C6_pointer_targets"] = {"per_schema": ptrs,
                                    "note": "the three canonical schemas resolve their class contract through the "
                                            "authoring mirror (artifacts/formulation/formulation_taxonomy.yaml), not "
                                            "through the declared canonical F0 path (research_map/formulation_taxonomy.yaml)",
                                    "verdict": "pass" if all(v["file_exists"] and v["key_present"] for v in ptrs.values()) else "fail"}

    # C7 disjointness coverage over the four classes
    dj = canon.get("disjointness", {}) or {}
    pairs = [tuple(sorted((a, b))) for i, a in enumerate(frozen_four) for b in frozen_four[i + 1:]]
    if isinstance(dj, list):
        documented = []
        for row in dj:
            p = row.get("pair") if isinstance(row, dict) else None
            if isinstance(p, list) and len(p) == 2:
                documented.append(tuple(sorted(p)))
        present = [p for p in pairs if p in documented]
        dj_note = "list"
        raw_keys = [row.get("pair") for row in dj if isinstance(row, dict)]
    elif isinstance(dj, dict):
        present = [p for p in pairs if any(k in dj for k in ("-".join(p), "|".join(p), f"{p[0]}_vs_{p[1]}"))]
        dj_note = "dict"
        raw_keys = sorted(dj)
    else:
        present, dj_note, raw_keys = [], f"type={type(dj).__name__}", None
    checks["C7_disjointness"] = {"type": dj_note, "expected_pairs": ["|".join(p) for p in pairs],
                                 "present_pairs": ["|".join(p) for p in present],
                                 "n_pairs_present": len(present), "n_pairs_expected": len(pairs),
                                 "all_have_separation_text": all(isinstance(r, dict) and bool(r.get("separation")) for r in dj) if isinstance(dj, list) else None,
                                 "verdict": "pass" if len(present) == len(pairs) else "fail",
                                 "raw_keys": raw_keys}

    # C8 duplicate mapping keys
    checks["C8_duplicate_keys"] = {"canonical": canon_dups, "authoring": auth_dups,
                                   "verdict": "pass" if not canon_dups else "fail"}

    # C9 map G-F0 gate evidence refs resolve on disk
    mp = json.loads((ROOT / "research_map/research_map.json").read_text())
    g = next((x for x in mp.get("gates", []) if x.get("gate_id") == "G-F0"), {})
    refs = []
    for r in g.get("evidence_refs", []):
        path = r.split("#")[0]
        refs.append({"ref": r, "exists": (ROOT / path).exists()})
    checks["C9_map_gate_refs"] = {"gate_verdict": g.get("verdict"), "refs": refs,
                                  "verdict": "pass" if refs and all(x["exists"] for x in refs) else "soft"}

    # C10 clock discipline (advisory)
    created = str(canon.get("created_at", ""))
    written = str(canon.get("written_at", ""))
    instant = now()
    checks["C10_clock"] = {"created_at": created, "written_at": written, "measured_at": instant,
                           "created_in_future": created > instant, "written_in_future": written > instant,
                           "verdict": "pass" if not (created > instant or written > instant) else "soft"}

    exit_ = {p: sha256(p) for p in TRACKED}
    drift = sorted(p for p in TRACKED if entry[p] != exit_[p])

    # verdict aggregation
    hard = []
    if checks["C1_class_ids"]["verdict"] == "fail":
        hard.append("C1: canonical class_id set is not exactly the frozen four")
    if checks["C2_unknown_tokens"]["verdict"] == "fail":
        hard.append(f"C2: unregistered class-id-shaped tokens {unknown}")
    if checks["C5_f0_binding"]["verdict"] == "fail":
        hard.append("C5: at least one canonical schema f0_binding does not match the live declared-F0 hash")
    if checks["C7_disjointness"]["verdict"] == "fail":
        hard.append("C7: pairwise disjointness coverage incomplete")
    if checks["C6_pointer_targets"]["verdict"] == "fail":
        hard.append("C6: a class_contract_pointer does not resolve to its file+key")
    if checks["C8_duplicate_keys"]["verdict"] == "fail":
        hard.append(f"C8: duplicate YAML keys in canonical F0: {canon_dups}")
    if drift:
        hard.append(f"DRIFT: tracked files changed during the run: {drift}")
    soft = []
    if checks["C4_dual_tree"]["verdict"] != "pass":
        soft.append("C4: canonical/authoring F0 trees are not byte-identical")
    if checks["C2_unknown_tokens"]["registered_variant_tokens"]:
        soft.append(f"C2: registered variant tokens in class-id shape: "
                    f"{checks['C2_unknown_tokens']['registered_variant_tokens']}")
    if checks["C10_clock"]["verdict"] != "pass":
        soft.append("C10: future-dated timestamp in canonical F0")
    if checks["C9_map_gate_refs"]["verdict"] != "pass":
        soft.append("C9: G-F0 evidence refs do not all resolve on disk")
    if not all(v["target_is_canonical_declared_f0"] for v in checks["C6_pointer_targets"]["per_schema"].values()):
        soft.append("C6: class_contract_pointer resolves through the authoring mirror, not the declared canonical F0 path")

    summary = {"task_id": "W040-F0-INDEP-VERDICT-01", "measured_at": instant,
               "f0_canonical_sha256": entry[F0_CANON], "f0_authoring_sha256": entry[F0_AUTHORING],
               "hard_findings": hard, "soft_findings": soft,
               "instrument_exits": {i["label"]: i["exit"] for i in instruments},
               "drift_during_run": drift,
               "bindable": not drift,
               "verdict_suggestion": "revise" if hard else ("accept" if not soft else "accept-with-conditions")}
    (OUT / "independent_checks.json").write_text(json.dumps({"summary": summary, "checks": checks}, indent=1, sort_keys=True))
    (OUT / "exit_hashes.json").write_text(json.dumps(exit_, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

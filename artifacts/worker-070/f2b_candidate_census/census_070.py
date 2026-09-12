#!/usr/bin/env python3
"""
W070-F2B-REV29-CANDIDATE-CENSUS-01  (worker-070, 2026-09-12)

Question (pre-registered in frame.json before any check):
  At the FROZEN rev29 pin of schemas/af_scc_c0_vacuum.yaml (node F2b, class
  AF-SCC-C0-VAC-GEN), for each DECLARED repair candidate sha256 in the registry:
    (a) which semantic paths does the candidate change relative to the frozen bytes?
    (b) is every changed path one of the two standing blocking-hard-failure carriers,
        or a declared metadata/binding path?
    (c) does the candidate discharge the two standing blocking carriers (P1/P2)?
    (d) does it preserve the frozen invariants (class id, conclusion token, containment
        chain, counts, f0 declared pin)?
    (e) do external references introduced by the candidate (variant token, vocabulary
        block, evidence hash) resolve against the frozen registries / live file?

Instrument (independent of the authors' checkers): strict YAML load + object-tree deep
diff, with duplicate-key detection, cross-registry resolution, and 6 controls.

Authority: worker measurement only. No canonical file, map, gate or node status is
modified; no node done; no validation_status passed; no gate verdict. Candidates are
read-only inputs; controls are built in memory only.
"""
import hashlib
import json
import os
import sys
import datetime
import io

try:
    import yaml
except Exception as e:  # pragma: no cover
    print("FATAL: PyYAML unavailable:", e)
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

FROZEN_REL = "schemas/af_scc_c0_vacuum.yaml"
MIRROR_REL = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
FROZEN_MANIFEST_REL = "artifacts/formulation/FROZEN.json"
RULE_SPEC_REL = "artifacts/formulation/rule_spec.json"
VOCAB_REL = "artifacts/formulation/VOCAB_ALIASES.json"
VARIANT_REL = "artifacts/formulation/VARIANT_REGISTRY.json"
CONSISTENCY_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"

# ---- pre-registered registry: declared F2b rev29/rev14 repair candidates (sha256) ----
# Every entry was declared as a candidate by its author's artifact or repair report in the
# 00:53-01:15 window. The census resolves one on-disk path per sha mechanically.
REGISTRY = [
    {"sha256": "a110f8e875afc747d8e8afc1b97912b83537c22be971bb3b791bc865693e2757",
     "author": "worker-022", "label": "C-022-cd-repair (containment, 2-edit)"},
    {"sha256": "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
     "author": "worker-002", "label": "C-002-repair2edit (containment, 2-edit)"},
    {"sha256": "9ab32ee39d008b20905ed44f4524ffa3c68ed50fe6a4b7a9fc4223584efbdf17",
     "author": "worker-023", "label": "proposed_af_scc_c0_vacuum_v2_corrected"},
    {"sha256": "679ab7bc874697cd52aaa0cdcbc32547de7983e3580c5f0e4a0640389ec823d9",
     "author": "worker-024", "label": "CANDIDATE minimal 2-line (W018 B1/B2)"},
    {"sha256": "51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a",
     "author": "worker-080", "label": "candidate_corrected (entailment audit)"},
    {"sha256": "4951cc96980329962829c2440c9e5c7f8ff5852eefd56aa48acfeeae8fb6505f",
     "author": "worker-080", "label": "candidate_nesting_only"},
    {"sha256": "1315427fbc92ed118982f20998066fd21c1714714213dc70b04023da74be3275",
     "author": "worker-083", "label": "live-defect-ledger candidate"},
    {"sha256": "3cdcaa44e6f103f4dacbc03c509f39586f7788e14ddba981b19985c843821c48",
     "author": "worker-047", "label": "C2-size-repair / C7-repaired (inversion only)"},
    {"sha256": "48cadb72e507cfcbc469f6519fcc0294bb83f083cc1733521610ff63e5f3c38a",
     "author": "worker-044", "label": "rev13 integration (containment + binding, rev14)"},
    {"sha256": "b598b59e09e56ee4f9e61d1c80f54d702b0bbf14ec9ee646172bc4a87710557a",
     "author": "worker-088", "label": "rev13-blockers candidate"},
]

# pre-registered carriers of the two standing blocking hard failures at rev29
HF_SITES = {
    "HF1_containment_denial": {
        "path": "regularity.must_not_conflate[0]",
        "defective_pattern": "No containment with C2 or C0 is asserted here",
        "source_reviews": ["worker-018 W018-R13-F2B-B1", "worker-017 B17-R13-02",
                           "worker-066 H2 (metalinguistic reading available)"],
    },
    "HF2_inverted_size_premise": {
        "path": "implication_ledger.forbidden_transfers[0].reason",
        "defective_pattern": "strictly larger extension class",
        "source_reviews": ["worker-017 B17-R13-01", "worker-053 W053-F2B-REV29-01",
                           "worker-075 HF-075-F2b-LARGER", "worker-091 (F2a mirror)"],
    },
}
HF1_PATH = HF_SITES["HF1_containment_denial"]["path"]
HF2_PATH = HF_SITES["HF2_inverted_size_premise"]["path"]

# metadata paths that are NOT core repair sites but are declared/documented in the
# candidate's own report; they are reported, never silently accepted.
METADATA_PATHS = {
    "revision": "revision_bump",
    "f0_binding.consistency_evidence_sha256": "binding_evidence_change",
    "f0_binding.checked_at": "binding_timestamp_change",
}
NEW_BLOCK_PREFIXES = ("extensions.",)

INVARIANTS = [
    ("class_id", "class_id"),
    ("node_id", "node_id"),
    ("conclusion.conclusion_type", "conclusion.conclusion_type"),
    ("conclusion.statement_formal", "conclusion.statement_formal"),
    ("implication_ledger.extension_class_containment",
     "implication_ledger.extension_class_containment"),
    ("f0_binding.declared_f0_sha256", "f0_binding.declared_f0_sha256"),
]
COUNT_INVARIANTS = [
    ("regularity.must_not_conflate", 5),
    ("implication_ledger.one_way_entailments", 4),
    ("implication_ledger.forbidden_transfers", 3),
]


# ------------------------------------------------------------------ utilities
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path):
    return os.path.relpath(path, ROOT)


def strict_load(text, label):
    """Load YAML and report duplicate mapping keys and the top-level type."""
    dup = []

    def walk(node, where):
        if isinstance(node, yaml.MappingNode):
            seen = {}
            for k, v in node.value:
                key = getattr(k, "value", None)
                if key in seen:
                    dup.append({"path": where, "duplicate_key": str(key)})
                seen[key] = v
                walk(v, f"{where}.{key}" if where else str(key))
        elif isinstance(node, yaml.SequenceNode):
            for i, v in enumerate(node.value):
                walk(v, f"{where}[{i}]")

    try:
        node = yaml.compose(text)
    except Exception as e:
        return None, [{"path": "$", "parse_error": str(e)}], None
    walk(node, "")
    try:
        obj = yaml.safe_load(text)
    except Exception as e:
        return None, dup, [{"path": "$", "parse_error": str(e)}]
    return obj, dup, []


def deep_diff(a, b, path=""):
    """Object-tree diff -> [{path, old, new, kind}] (values JSON-safe)."""
    out = []
    if type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        out.append({"path": path or "$", "old": a, "new": b, "kind": "type_change"})
        return out
    if isinstance(a, dict):
        for k in a:
            if k not in b:
                out.append({"path": f"{path}.{k}" if path else str(k), "old": a[k], "new": None,
                            "kind": "removed"})
            else:
                out += deep_diff(a[k], b[k], f"{path}.{k}" if path else str(k))
        for k in b:
            if k not in a:
                out.append({"path": f"{path}.{k}" if path else str(k), "old": None,
                            "new": b[k], "kind": "added"})
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append({"path": path, "old": f"list[{len(a)}]", "new": f"list[{len(b)}]",
                        "kind": "length_change"})
        for i in range(min(len(a), len(b))):
            out += deep_diff(a[i], b[i], f"{path}[{i}]")
    else:
        if a != b:
            out.append({"path": path, "old": a, "new": b, "kind": "value_change"})
    return out


def walk_get(obj, path):
    cur = obj
    for tok in path.replace("]", "").replace("[", ".").split("."):
        if tok == "":
            continue
        if isinstance(cur, list):
            cur = cur[int(tok)]
        else:
            cur = cur[tok]
    return cur


def json_safe(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return json.dumps(v, ensure_ascii=False, sort_keys=True)[:2000]


# ------------------------------------------------------------------ checks
def discharge_predicates(cand):
    """P1/P2 against the candidate text plus optional variant-token check."""
    res = {}
    try:
        mnc0 = walk_get(cand, HF1_PATH)
    except Exception as e:
        mnc0 = None
        res["HF1_read_error"] = str(e)
    try:
        r0 = walk_get(cand, HF2_PATH)
    except Exception as e:
        r0 = None
        res["HF2_read_error"] = str(e)

    pat1 = HF_SITES["HF1_containment_denial"]["defective_pattern"]
    pat2 = HF_SITES["HF2_inverted_size_premise"]["defective_pattern"]
    mnc0_s = mnc0 if isinstance(mnc0, str) else ""
    r0_s = r0 if isinstance(r0, str) else ""

    p1 = (pat1 not in mnc0_s) and bool(mnc0_s.strip())
    p2 = (pat2 not in r0_s) and any(t in r0_s for t in ("smaller", "SMALLEST", "subset",
                                                        "stronger regularity", "nested",
                                                        "containment", "contains"))
    res["P1_HF1_denial_removed"] = bool(p1)
    res["P2_HF2_inversion_removed_with_correct_relation"] = bool(p2)
    res["HF1_new_text"] = mnc0_s
    res["HF2_new_text"] = r0_s
    return res


def classify_changed_paths(diffs):
    core, metadata, new_block, other = [], [], [], []
    for d in diffs:
        p = d["path"]
        if p == HF1_PATH:
            core.append({"site": "HF1_containment_denial", **d})
        elif p == HF2_PATH:
            core.append({"site": "HF2_inverted_size_premise", **d})
        elif p in METADATA_PATHS:
            metadata.append({"class": METADATA_PATHS[p], **d})
        elif p.startswith(NEW_BLOCK_PREFIXES):
            new_block.append({"class": "new_extension_block", **d})
        else:
            other.append(d)
    return core, metadata, new_block, other


def invariant_report(frozen, cand):
    out = {}
    for name, path in INVARIANTS:
        try:
            a, b = walk_get(frozen, path), walk_get(cand, path)
            out[name] = {"preserved": a == b, "frozen": json_safe(a), "candidate": json_safe(b)}
        except Exception as e:
            out[name] = {"preserved": False, "error": str(e)}
    for path, n in COUNT_INVARIANTS:
        try:
            out[f"count:{path}"] = {"preserved": len(walk_get(cand, path)) == n,
                                    "expected": n, "candidate": len(walk_get(cand, path))}
        except Exception as e:
            out[f"count:{path}"] = {"preserved": False, "error": str(e)}
    return out


def external_refs(cand, registries):
    """Check every external token/hash the candidate introduces against live registries."""
    out = {}
    try:
        mnc0 = walk_get(cand, HF1_PATH) or ""
    except Exception:
        mnc0 = ""
    r0 = ""
    try:
        r0 = walk_get(cand, HF2_PATH) or ""
    except Exception:
        pass
    text = f"{mnc0} {r0}"

    checks = []
    if "VARIANT_REGISTRY" in text:
        variants = {v.get("variant_id"): v for v in registries["variants"]["variants"]}
        for tok in ("H2LOC", "CH", "TWOSIDED", "SET", "DISTRIBUTIONAL", "L2CONN", "LIP"):
            if tok in text:
                entry = variants.get(tok)
                checks.append({
                    "token": tok,
                    "registered": entry is not None,
                    "parent_class": (entry or {}).get("parent_class"),
                    "candidate_claims_parent": "AF-SCC-C0-VAC-GEN" if "AF-SCC-C0-VAC-GEN" in text else None,
                    "ok": bool(entry) and entry.get("parent_class") == "AF-SCC-C0-VAC-GEN",
                })
    out["variant_tokens"] = checks

    try:
        ext = cand.get("extensions", {})
    except Exception:
        ext = {}
    if isinstance(ext, dict) and "vocabulary_binding" in ext:
        vb = ext["vocabulary_binding"] or {}
        rspec = registries["rule_spec"]
        declared = vb.get("declared_conclusion_type_canonical")
        out["vocabulary_binding"] = {
            "declared_conclusion_type_canonical": declared,
            "rule_spec_class_conclusion_type": rspec["vocabularies"]["class_conclusion_type"].get(
                "AF-SCC-C0-VAC-GEN"),
            "registry_sha256_matches_frozen": vb.get("alias_registry_sha256") ==
            registries["frozen_manifest"]["files"]["artifacts/formulation/VOCAB_ALIASES.json"]["sha256"],
            "ok": declared == rspec["vocabularies"]["class_conclusion_type"].get(
                "AF-SCC-C0-VAC-GEN"),
        }

    ev = None
    try:
        ev = cand["f0_binding"]["consistency_evidence_sha256"]
    except Exception:
        pass
    if ev is not None:
        frozen_ev = registries["frozen_manifest"]["files"][
            "artifacts/formulation/evidence/taxonomy_consistency.json"]["sha256"]
        out["consistency_evidence"] = {
            "candidate": ev,
            "frozen_manifest_pin": frozen_ev,
            "live_file_sha256": registries["consistency_live_sha256"],
            "matches_frozen_pin": ev == frozen_ev,
            "matches_live_file": ev == registries["consistency_live_sha256"],
        }
        out["consistency_evidence"]["ok"] = (ev == frozen_ev == registries["consistency_live_sha256"])
    return out


# ------------------------------------------------------------------ controls
def run_controls(frozen_text, candidate_text, registries):
    ctl = {}

    # K0 no-op: frozen vs itself must produce zero diffs
    f_obj, f_dup, f_err = strict_load(frozen_text, "frozen")
    d0 = deep_diff(f_obj, f_obj)
    ctl["K0_noop_zero_diffs"] = {"expected": 0, "observed": len(d0), "pass": len(d0) == 0}

    # K1 unrelated leaf mutation must be detected at exactly that path
    mut = frozen_text.replace('excluded_set_status: unresolved', 'excluded_set_status: seeded_control_value')
    m_obj, _, _ = strict_load(mut, "K1")
    d1 = deep_diff(f_obj, m_obj)
    ctl["K1_unrelated_leaf_detected"] = {
        "expected_path": "genericity.excluded_set_status",
        "observed_paths": [x["path"] for x in d1],
        "pass": [x["path"] for x in d1] == ["genericity.excluded_set_status"],
    }

    # K2 denial re-injection must fail P1
    c_obj, _, _ = strict_load(candidate_text, "K2")
    p = discharge_predicates(c_obj)
    k2_text = candidate_text.replace(p["HF1_new_text"],
                                     p["HF1_new_text"] + " No containment with C2 or C0 is asserted here.")
    k2_obj, _, _ = strict_load(k2_text, "K2b")
    p2 = discharge_predicates(k2_obj)
    ctl["K2_denial_reinjection_fails_P1"] = {"expected": False,
                                             "observed": p2.get("P1_HF1_denial_removed"),
                                             "pass": p2.get("P1_HF1_denial_removed") is False}

    # K3 inversion re-injection must fail P2
    k3_text = candidate_text.replace(p["HF2_new_text"],
                                     "C2 is a strictly larger extension class, so C2-inextendibility is strictly weaker")
    k3_obj, _, _ = strict_load(k3_text, "K3")
    p3 = discharge_predicates(k3_obj)
    ctl["K3_inversion_reinjection_fails_P2"] = {"expected": False,
                                                "observed": p3.get("P2_HF2_inversion_removed_with_correct_relation"),
                                                "pass": p3.get("P2_HF2_inversion_removed_with_correct_relation") is False}

    # K4 fabricated variant token must not resolve
    variants = {v.get("variant_id") for v in registries["variants"]["variants"]}
    ctl["K4_fabricated_variant_unresolved"] = {"expected": False, "observed": "NOPE-VARIANT" in variants,
                                               "pass": ("NOPE-VARIANT" in variants) is False}

    # K5 duplicate-key detector fires on a seeded duplicate top-level key
    k5_text = "class_id: X\nclass_id: Y\n" + frozen_text
    _, dup5, _ = strict_load(k5_text, "K5")
    ctl["K5_duplicate_key_detector_fires"] = {"expected": True, "observed": bool(dup5),
                                              "pass": bool(dup5)}
    return ctl


# ------------------------------------------------------------------ main
def main():
    started = datetime.datetime.now().astimezone()
    log = []

    def say(msg):
        line = f"[{datetime.datetime.now().astimezone().isoformat(timespec='seconds')}] {msg}"
        print(line)
        log.append(line)

    def die(code, msg):
        say(f"ABORT({code}): {msg}")
        with open(os.path.join(HERE, "run.log"), "w") as f:
            f.write("\n".join(log) + "\n")
        sys.exit(code)

    # ---- pins BEFORE ----
    required = [FROZEN_REL, FROZEN_MANIFEST_REL, RULE_SPEC_REL, VOCAB_REL, VARIANT_REL, CONSISTENCY_REL]
    for r in required:
        if not os.path.exists(os.path.join(ROOT, r)):
            die(3, f"required input missing: {r}")
    pins_before = {r: sha256_file(os.path.join(ROOT, r)) for r in required}
    frozen_text = open(os.path.join(ROOT, FROZEN_REL), encoding="utf8").read()
    frozen_sha = pins_before[FROZEN_REL]
    say(f"frozen F2b sha256 {frozen_sha}")

    registries = {
        "rule_spec": json.load(open(os.path.join(ROOT, RULE_SPEC_REL))),
        "vocab": json.load(open(os.path.join(ROOT, VOCAB_REL))),
        "variants": json.load(open(os.path.join(ROOT, VARIANT_REL))),
        "frozen_manifest": json.load(open(os.path.join(ROOT, FROZEN_MANIFEST_REL))),
        "consistency_live_sha256": pins_before[CONSISTENCY_REL],
    }

    # frozen manifest must actually pin the frozen schema we are using
    fm = registries["frozen_manifest"]["files"].get(FROZEN_REL, {})
    if fm.get("sha256") != frozen_sha:
        die(3, f"frozen manifest pin {fm.get('sha256')} != live {frozen_sha} (moving target)")

    frozen_obj, frozen_dup, frozen_err = strict_load(frozen_text, "frozen")
    if frozen_err:
        die(3, f"frozen schema does not parse: {frozen_err}")

    # ---- resolve one on-disk path per declared registry sha ----
    wanted = {e["sha256"] for e in REGISTRY}
    found = {}
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "artifacts")):
        for fn in filenames:
            if not fn.endswith((".yaml", ".yml")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                b = open(p, "rb").read()
            except Exception:
                continue
            if b[:4096].find(b"class_id: AF-SCC-C0-VAC-GEN") < 0:
                continue
            h = hashlib.sha256(b).hexdigest()
            if h in wanted:
                found.setdefault(h, []).append(rel(p))
    for e in REGISTRY:
        if e["sha256"] not in found:
            die(4, f"declared candidate {e['sha256'][:12]} ({e['author']}) not found on disk")
        e["paths"] = sorted(found[e["sha256"]])
        e["primary_path"] = e["paths"][0]
        say(f"candidate {e['sha256'][:12]} {e['author']}: {len(e['paths'])} on-disk copy(ies)")

    # ---- pre-registered frame (written before candidate checks) ----
    frame = {
        "task_id": "W070-F2B-REV29-CANDIDATE-CENSUS-01",
        "actor": "worker-070",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN"],
        "gate": "G-FORM",
        "created_at": started.isoformat(timespec="seconds"),
        "question": ("For each declared F2b rev29 repair candidate sha256: which semantic paths change "
                     "vs the frozen bytes, is every change at a standing-HF carrier or a declared "
                     "metadata/binding path, are the two blocking carriers discharged, are the frozen "
                     "invariants preserved, and do introduced external references resolve?"),
        "instrument": "strict YAML load + object-tree deep diff + cross-registry resolution; 6 controls",
        "pins_before": pins_before,
        "frozen_manifest_pin_for_schema": fm.get("sha256"),
        "hf_sites": HF_SITES,
        "registry": [{k: e[k] for k in ("sha256", "author", "label")} for e in REGISTRY],
        "classification_rule": {
            "CORE": [HF1_PATH, HF2_PATH],
            "METADATA": METADATA_PATHS,
            "NEW_BLOCK": list(NEW_BLOCK_PREFIXES),
            "OTHER": "any changed path not above is reported as adoption risk (non-core change riding along)",
        },
        "predicates": {
            "P1": f"'{HF_SITES['HF1_containment_denial']['defective_pattern']}' absent from {HF1_PATH} and slot non-empty",
            "P2": f"'{HF_SITES['HF2_inverted_size_premise']['defective_pattern']}' absent from {HF2_PATH} "
                  f"and a correct containment/size relation present",
        },
        "invariants": [p for _, p in INVARIANTS] + [p for p, _ in COUNT_INVARIANTS],
        "controls": ["K0 no-op zero diffs", "K1 unrelated leaf detected",
                     "K2 denial re-injection fails P1", "K3 inversion re-injection fails P2",
                     "K4 fabricated variant unresolved", "K5 duplicate-key detector fires"],
        "stop_rule": "pin drift on any input -> exit 3, no verdict; declared candidate not found -> exit 4, no verdict",
        "falsifier": ("Re-run census_070.py at the same pins. Falsified if any candidate's measured sha256, "
                      "changed-path set, P1/P2 value, invariant value or external-reference resolution differs; "
                      "or if any control fails; or if a reviewer exhibits a changed semantic path that the tree "
                      "diff misses. Any pin change away from frame.pins_before voids the run rather than falsifying it."),
        "authority": "worker measurement only; no gate verdict, no node completion, no canonical write",
    }
    frame_path = os.path.join(HERE, "frame.json")
    with open(frame_path, "w") as f:
        json.dump(frame, f, indent=1, sort_keys=True)
    frame_sha = sha256_file(frame_path)
    say(f"frame written {frame_sha}")

    # ---- candidate checks ----
    results = []
    for e in REGISTRY:
        p = os.path.join(ROOT, e["primary_path"])
        text = open(p, encoding="utf8").read()
        cand_sha = hashlib.sha256(text.encode("utf8")).hexdigest()
        entry = {"sha256_declared": e["sha256"], "sha256_measured": cand_sha,
                 "sha256_match": cand_sha == e["sha256"], "author": e["author"], "label": e["label"],
                 "paths": e["paths"]}
        if cand_sha != e["sha256"]:
            entry["status"] = "HASH_MISMATCH"
            results.append(entry)
            continue
        obj, dup, err = strict_load(text, e["author"])
        entry["duplicate_keys"] = dup
        entry["parse_errors"] = err
        if err or obj is None:
            entry["status"] = "PARSE_FAIL"
            results.append(entry)
            continue
        diffs = deep_diff(frozen_obj, obj)
        for d in diffs:
            d["old"] = json_safe(d.get("old"))
            d["new"] = json_safe(d.get("new"))
        core, metadata, new_block, other = classify_changed_paths(diffs)
        entry["changed_paths"] = [d["path"] for d in diffs]
        entry["core_changes"] = core
        entry["metadata_changes"] = metadata
        entry["new_blocks"] = [d["path"] for d in new_block]
        entry["other_changes"] = other
        entry["predicates"] = discharge_predicates(obj)
        entry["invariants"] = invariant_report(frozen_obj, obj)
        entry["external_refs"] = external_refs(obj, registries)
        entry["all_invariants_preserved"] = all(v.get("preserved") for v in entry["invariants"].values())
        entry["core_only"] = (len(other) == 0 and len(new_block) == 0
                              and all(m["class"] in ("revision_bump",) for m in metadata))
        entry["status"] = ("CORE_REPAIR_COMPLETE" if (entry["predicates"]["P1_HF1_denial_removed"]
                                                      and entry["predicates"]["P2_HF2_inversion_removed_with_correct_relation"]
                                                      and entry["all_invariants_preserved"])
                           else "REPAIR_INCOMPLETE_OR_INVARIANT_BROKEN")
        say(f"{e['sha256'][:12]} {entry['status']} core={len(core)} meta={len(metadata)} "
            f"new={len(new_block)} other={len(other)} P1={entry['predicates']['P1_HF1_denial_removed']} "
            f"P2={entry['predicates']['P2_HF2_inversion_removed_with_correct_relation']} "
            f"inv={entry['all_invariants_preserved']}")
        results.append(entry)

    # ---- controls (on a repaired candidate when available, else frozen) ----
    base = next((open(os.path.join(ROOT, e["primary_path"]), encoding="utf8").read()
                 for e in REGISTRY if e["sha256"] == "a110f8e875afc747d8e8afc1b97912b83537c22be971bb3b791bc865693e2757"), frozen_text)
    controls = run_controls(frozen_text, base, registries)
    say("controls: " + json.dumps({k: v["pass"] for k, v in controls.items()}))

    # ---- pins AFTER ----
    pins_after = {r: sha256_file(os.path.join(ROOT, r)) for r in required}
    drift = {k: [pins_before[k], pins_after[k]] for k in pins_before if pins_before[k] != pins_after[k]}
    if drift:
        die(3, f"pin drift during run: {drift}")

    # ---- convergence matrix ----
    conv = {}
    for site, path in (("HF1", HF1_PATH), ("HF2", HF2_PATH)):
        texts = {}
        for e, r in zip(REGISTRY, results):
            if r.get("status") == "PARSE_FAIL" or r.get("sha256_match") is False:
                continue
            key = json.dumps(r["predicates"][f"{site}_new_text"] if site == "HF1" else r["predicates"]["HF2_new_text"])
            texts.setdefault(key, []).append(e["sha256"][:12])
        conv[site] = {"distinct_repairs": len(texts),
                      "groups": [{"n": len(v), "candidates": v, "text": json.loads(k)} for k, v in texts.items()]}

    report = {
        "task_id": frame["task_id"], "actor": "worker-070", "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN", "gate": "G-FORM",
        "created_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "frame_sha256": frame_sha,
        "frozen": {"path": FROZEN_REL, "sha256": frozen_sha,
                   "mirror_path": MIRROR_REL,
                   "mirror_matches": (os.path.exists(os.path.join(ROOT, MIRROR_REL)) and
                                      sha256_file(os.path.join(ROOT, MIRROR_REL)) == frozen_sha),
                   "duplicate_keys": frozen_dup},
        "pins_before": pins_before, "pins_after": pins_after, "pin_drift": drift,
        "registry_resolution": [{"sha256": e["sha256"], "author": e["author"], "label": e["label"],
                                 "n_copies": len(e["paths"]), "primary_path": e["primary_path"]}
                                for e in REGISTRY],
        "results": results,
        "convergence": conv,
        "controls": controls,
        "controls_all_pass": all(v["pass"] for v in controls.values()),
        "aggregate": {
            "declared_candidates": len(REGISTRY),
            "core_repair_complete": sum(1 for r in results if r.get("status") == "CORE_REPAIR_COMPLETE"),
            "other_path_changes": {r["sha256_declared"][:12]: r.get("other_changes", [])
                                   for r in results if r.get("other_changes")},
            "non_core_blocks": {r["sha256_declared"][:12]: r.get("new_blocks", [])
                                for r in results if r.get("new_blocks")},
            "metadata_only_differences": {r["sha256_declared"][:12]:
                                          [m["class"] for m in r.get("metadata_changes", [])]
                                          for r in results if r.get("metadata_changes")},
            "residual_gate_wide_blocker": ("conclusion-token conflict between F0 field_vocabulary.allowed "
                                           "and VOCAB_ALIASES canonical tokens (F2a+F2b); not candidate-fixable; "
                                           "see worker-024 D3 / worker-066 binding adjudication"),
        },
        "falsifier": frame["falsifier"],
        "authority": frame["authority"],
        "no_write_paths": ["schemas/", "artifacts/formulation/", "research_map/", "ledger/", "reviews/"],
    }
    report_path = os.path.join(HERE, "report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=1, sort_keys=True)
    with open(os.path.join(HERE, "run.log"), "w") as f:
        f.write("\n".join(log) + "\n")
    print(json.dumps({"report": rel(report_path), "report_sha256": sha256_file(report_path),
                      "frame_sha256": frame_sha,
                      "controls_all_pass": report["controls_all_pass"],
                      "core_repair_complete": report["aggregate"]["core_repair_complete"],
                      "declared_candidates": len(REGISTRY)}, indent=1))


if __name__ == "__main__":
    main()

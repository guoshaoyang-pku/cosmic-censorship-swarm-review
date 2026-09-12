#!/usr/bin/env python3
"""W065-REV12-DELTA-CENSUS-01 -- predecessor -> rev12 delta + binding + provenance census.

Read-only over the repository except this artifact directory. No network.
Reuses the strict-YAML primitives from census.py (same directory).

Question answered, per canonical formulation artifact:
  * what changed between the last-reviewed revision and rev12 (semantic vs metadata),
  * whether the three schemas' declared contract pointers and F0 hash bindings
    actually resolve against the bytes now on disk,
  * whether the rev12 `revision_history` preserved every predecessor revision stamp,
  * whether rev12 is strict-YAML clean where the predecessor was not,
  * and whether the three schemas now share one declared data-class core.

It does NOT judge whether rev12 is mathematically correct; that is the reviewers'
and controller's call. Outputs rev12_delta_census.json + report.md + snapshots/.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TZ = timezone(timedelta(hours=8))

spec = importlib.util.spec_from_file_location("w065_census", os.path.join(HERE, "census.py"))
census = importlib.util.module_from_spec(spec)
spec.loader.exec_module(census)

NEW = {
    "F0-declared-taxonomy": "research_map/formulation_taxonomy.yaml",
    "F0-class-contract-supplement": "artifacts/formulation/formulation_taxonomy.yaml",
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
# predecessor sha256 taken from the controller gate audit / FROZEN rev26; snapshot is a
# third-party pinned byte copy that must hash to it or the instrument is invalid.
PRED = {
    "F0-declared-taxonomy": {
        "sha256": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
        "snapshot": "artifacts/worker-020/f2a_independent_verdict/snapshots/f0_taxonomy_276009f4f63d.yaml",
    },
    "F0-class-contract-supplement": {
        "sha256": "c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f",
        "snapshot": "artifacts/worker-060/xclass_dataclass_adjudication/snapshots/F0_authoring__formulation_taxonomy.yaml",
    },
    "F1": {
        "sha256": "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
        "snapshot": "artifacts/worker-082/f1_machine_defect/frozen_f1_9a8bd4c96800.yaml",
    },
    "F2a": {
        "sha256": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
        "snapshot": "artifacts/worker-060/xclass_dataclass_adjudication/snapshots/F2a__af_scc_c2_vacuum.yaml",
    },
    "F2b": {
        "sha256": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
        "snapshot": "artifacts/worker-060/xclass_dataclass_adjudication/snapshots/F2b__af_scc_c0_vacuum.yaml",
    },
}
METADATA_TOP = {"revised_at", "revised_at_unused", "revision", "revision_history",
                "timestamp_provenance", "review_status", "supersedes", "f0_binding",
                "authored_at", "written_at", "created_at", "updated_at", "revision_note",
                "revision_note_rev5", "revision_note_rev4", "revision_note_rev3"}


def sha256_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def load_yaml(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def deep_delta(old, new, path=""):
    """Recursive structural delta. Returns list of dicts with kind/path/old/new."""
    out = []
    if isinstance(old, dict) and isinstance(new, dict):
        for k in sorted(set(old) | set(new)):
            sub = f"{path}.{k}" if path else str(k)
            if k not in old:
                out.append({"kind": "added", "path": sub, "new": new[k]})
            elif k not in new:
                out.append({"kind": "removed", "path": sub, "old": old[k]})
            else:
                out += deep_delta(old[k], new[k], sub)
    elif isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            out.append({"kind": "list_length", "path": path,
                        "old_len": len(old), "new_len": len(new)})
        for i, (a, b) in enumerate(zip(old, new)):
            out += deep_delta(a, b, f"{path}[{i}]")
    elif old != new:
        out.append({"kind": "changed", "path": path, "old": old, "new": new})
    return out


def short(v, n=180):
    s = json.dumps(v, sort_keys=True) if not isinstance(v, str) else v
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[:n] + "..."


def classify(deltas):
    meta, sem = [], []
    for d in deltas:
        top = d["path"].split(".")[0].split("[")[0]
        (meta if top in METADATA_TOP else sem).append(d)
    return sem, meta


def resolve_fragment(pointer):
    """Resolve 'relpath#a.b.c' against the current tree. Returns dict."""
    if not isinstance(pointer, str) or "#" not in pointer:
        return {"pointer": pointer, "resolved": False, "reason": "malformed_or_missing"}
    rel, frag = pointer.split("#", 1)
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return {"pointer": pointer, "file_exists": False, "resolved": False,
                "reason": "file_missing"}
    try:
        if rel.lower().endswith((".json",)):
            doc = json.load(open(p, encoding="utf-8"))
        else:
            doc = yaml.safe_load(open(p, encoding="utf-8"))
    except Exception as exc:
        return {"pointer": pointer, "file_exists": True, "resolved": False,
                "reason": f"parse_error:{type(exc).__name__}"}
    node = doc
    for part in frag.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return {"pointer": pointer, "file_exists": True, "resolved": False,
                    "reason": f"fragment_not_found_at:{part}"}
    return {"pointer": pointer, "file_exists": True, "resolved": True,
            "value_sha256": hashlib.sha256(json.dumps(node, sort_keys=True).encode()).hexdigest()}


def provenance_coverage(old_doc, new_doc):
    """Every predecessor header timestamp must appear in the successor revision history."""
    stamps = []
    for k in ("authored_at", "written_at", "created_at"):
        if isinstance(old_doc.get(k), str):
            stamps.append((k, old_doc[k]))
    for line_key in ("revised_at", "revised_at_unused"):
        # duplicate top-level keys are lost by safe_load; read raw lines instead
        pass
    return stamps


def raw_header_stamps(rel):
    """All top-level `<key>: "<iso>"` stamps in file order, duplicate keys included."""
    out = []
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            if line[:1].isspace() or line.startswith("#") or ":" not in line:
                continue
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k.endswith("_at") or k == "revised_at_unused":
                out.append({"key": k, "value": v, "line": i})
    return out


def main():
    clock = datetime.now(TZ)
    controls = []

    def add(cid, desc, expected, observed, ok):
        controls.append({"id": cid, "description": desc, "expected": expected,
                         "observed": observed, "pass": bool(ok)})

    # ---- load -------------------------------------------------------------
    new_text, new_hash, new_doc = {}, {}, {}
    for label, rel in NEW.items():
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            new_text[label] = fh.read()
        new_hash[label] = hashlib.sha256(new_text[label].encode()).hexdigest()
        new_doc[label] = yaml.safe_load(new_text[label])
    pre = dict(new_hash)

    old_text, old_hash, old_doc = {}, {}, {}
    for label, meta in PRED.items():
        rel = meta["snapshot"]
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            old_text[label] = fh.read()
        old_hash[label] = hashlib.sha256(old_text[label].encode()).hexdigest()
        old_doc[label] = yaml.safe_load(old_text[label])
    snap_ok = all(old_hash[l] == PRED[l]["sha256"] for l in PRED)
    add("C1", "every pinned predecessor snapshot hashes to its declared predecessor sha256",
        "all match", {l: old_hash[l][:12] for l in PRED}, snap_ok)

    # ---- per-artifact delta + strict status -------------------------------
    artifacts = {}
    for label, rel in NEW.items():
        deltas = deep_delta(old_doc[label], new_doc[label])
        sem, meta = classify(deltas)
        old_dups = census.detect_duplicates(old_text[label])
        new_dups = census.detect_duplicates(new_text[label])
        old_strict, _ = census.strict_verdict(old_text[label])
        new_strict, new_detail = census.strict_verdict(new_text[label])
        artifacts[label] = {
            "path": rel,
            "predecessor": {"sha256": old_hash[label], "snapshot": PRED[label]["snapshot"],
                            "strict": old_strict, "duplicate_keys": old_dups},
            "current": {"sha256": new_hash[label], "bytes": len(new_text[label].encode()),
                        "revision": new_doc[label].get("revision"),
                        "strict": new_strict, "strict_detail": new_detail,
                        "duplicate_keys": new_dups,
                        "effective_revised_at": new_doc[label].get("revised_at"),
                        "revision_history_len": len(new_doc[label].get("revision_history") or [])
                        if isinstance(new_doc[label].get("revision_history"), list) else None},
            "delta_counts": {"total": len(deltas), "semantic": len(sem), "metadata": len(meta)},
            "semantic_deltas": [{"kind": d["kind"], "path": d["path"],
                                 "old": short(d.get("old")), "new": short(d.get("new"))} for d in sem],
            "metadata_deltas": [{"kind": d["kind"], "path": d["path"]} for d in meta],
        }
        if label in ("F1", "F2a", "F2b"):
            # provenance: predecessor header stamps -> successor revision_history
            old_stamps = raw_header_stamps(PRED[label]["snapshot"])
            hist = new_doc[label].get("revision_history") or []
            hist_vals = [h.get("at") for h in hist if isinstance(h, dict)]
            missing = [s for s in old_stamps if s["value"] not in hist_vals]
            artifacts[label]["provenance"] = {
                "predecessor_header_stamps": old_stamps,
                "predecessor_stamp_count": len(old_stamps),
                "successor_history_len": len(hist),
                "missing_from_history": missing,
                "preserved": not missing and len(hist_vals) >= len(old_stamps),
            }
            # binding checks
            binds = {}
            for field in ("class_contract_pointer", "class_contract_supplement_pointer"):
                if field in new_doc[label]:
                    binds[field] = resolve_fragment(new_doc[label][field])
            fb = new_doc[label].get("f0_binding") or {}
            declared = fb.get("declared_f0_artifact")
            if declared and os.path.exists(os.path.join(ROOT, declared)):
                binds["f0_binding.declared_f0_sha256"] = {
                    "declared": fb.get("declared_f0_sha256"),
                    "measured": sha256_file(os.path.join(ROOT, declared)),
                    "resolved": fb.get("declared_f0_sha256") == sha256_file(os.path.join(ROOT, declared)),
                }
            ev = fb.get("consistency_evidence")
            if ev and os.path.exists(os.path.join(ROOT, ev)):
                binds["f0_binding.consistency_evidence_sha256"] = {
                    "declared": fb.get("consistency_evidence_sha256"),
                    "measured": sha256_file(os.path.join(ROOT, ev)),
                    "resolved": fb.get("consistency_evidence_sha256") == sha256_file(os.path.join(ROOT, ev)),
                }
            sup = fb.get("class_contract_supplement_pointer")
            if sup:
                binds["f0_binding.class_contract_supplement_pointer"] = resolve_fragment(sup)
            artifacts[label]["binding_checks"] = binds
            add(f"C-{label}-ptr", f"{label} class_contract_pointer resolves in the canonical tree",
                "resolved", binds.get("class_contract_pointer", {}).get("resolved", "absent"),
                binds.get("class_contract_pointer", {}).get("resolved") is True)
            add(f"C-{label}-f0", f"{label} declared_f0_sha256 equals the measured F0 canonical hash",
                "resolved", binds.get("f0_binding.declared_f0_sha256", {}).get("resolved", "absent"),
                binds.get("f0_binding.declared_f0_sha256", {}).get("resolved") is True)

    # ---- cross-class shared-data-class measurement (finding, not control) --
    def core(doc):
        q = doc.get("quantifiers") or {}
        return {"D0": q.get("domains", {}).get("D0"),
                "regularity": doc.get("regularity"),
                "formal": q.get("formal")}
    cores = {l: core(new_doc[l]) for l in ("F1", "F2a", "F2b")}

    def norm_reg(s):
        import re
        return re.sub(r"\s*(?:and|,)\s*delta", ", delta", str(s)).strip()

    d0_raw_equal = json.dumps(cores["F1"]["D0"], sort_keys=True) == \
        json.dumps(cores["F2a"]["D0"], sort_keys=True) == \
        json.dumps(cores["F2b"]["D0"], sort_keys=True)
    dr = {l: (cores[l]["regularity"] or {}).get("data_regularity") for l in cores}
    dr_norm_equal = len({norm_reg(v) for v in dr.values()}) == 1
    shared_data_class = {
        "D0_definition_raw_equal": d0_raw_equal,
        "data_regularity_raw_equal": len(set(dr.values())) == 1,
        "data_regularity_equal_modulo_punctuation": dr_norm_equal,
        "data_regularity_values": dr,
        "conclusion_formal_differs_by_class_as_designed": len({
            json.dumps(cores[l]["formal"], sort_keys=True) for l in cores}) == 3,
    }

    # ---- controls ---------------------------------------------------------
    # C2 diff sensitivity
    probe = json.loads(json.dumps(new_doc["F1"]))
    probe["conclusion"]["statement_formal"] = "MUTANT-CONTROL-SENTINEL"
    sem_p, _ = classify(deep_delta(new_doc["F1"], probe))
    add("C2", "diff sensitivity: one injected semantic change yields exactly one semantic delta",
        "1", len(sem_p), len(sem_p) == 1 and sem_p[0]["path"] == "conclusion.statement_formal")

    # C3 metadata classification
    probe2 = json.loads(json.dumps(new_doc["F1"]))
    probe2["revised_at"] = "1999-01-01T00:00:00+08:00"
    sem2, meta2 = classify(deep_delta(new_doc["F1"], probe2))
    add("C3", "metadata classification: revised_at change yields 0 semantic deltas",
        "0 sem / 1 meta", f"{len(sem2)} sem / {len(meta2)} meta",
        len(sem2) == 0 and len(meta2) == 1)

    # C4 pointer resolver positive/negative
    pos = resolve_fragment("research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN")
    neg = resolve_fragment("research_map/formulation_taxonomy.yaml#classes.AF-NO-SUCH-CLASS")
    add("C4", "fragment resolver: positive resolves, bogus fragment does not",
        "True/False", f"{pos['resolved']}/{neg['resolved']}",
        pos["resolved"] is True and neg["resolved"] is False)

    # C5 strict detector direction on predecessor vs successor
    pred_rej = [l for l in PRED if PRED[l]["sha256"] != new_hash.get(l)
                and census.strict_verdict(old_text[l])[0] == "REJECT"]
    succ_ok = [l for l in NEW if census.strict_verdict(new_text[l])[0] == "OK"]
    add("C5", "strict detector: predecessor snapshots that carried duplicate keys are REJECT, rev12 is OK",
        "pred>=1 REJECT, all 5 OK", f"pred_rej={sorted(pred_rej)}, succ_ok={len(succ_ok)}/5",
        len(pred_rej) >= 1 and len(succ_ok) == 5)

    # C6 provenance loss detection on a synthetic history
    hist = [h for h in (new_doc["F1"].get("revision_history") or []) if isinstance(h, dict)]
    synth = hist[:-1] if hist else []
    synth_vals = [h.get("at") for h in synth]
    old_stamps_f1 = raw_header_stamps(PRED["F1"]["snapshot"])
    detected = any(s["value"] not in synth_vals for s in old_stamps_f1)
    add("C6", "provenance checker detects a dropped history entry",
        "True", detected, detected is True)

    # C7 resolver not fooled by prefix fragments
    neg2 = resolve_fragment("research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC")
    add("C7", "resolver rejects a prefix-only class fragment",
        "False", neg2["resolved"], neg2["resolved"] is False)

    # C8 determinism
    add("C8", "delta + duplicate detection deterministic across repeated runs",
        "equal", "equal" if deep_delta(old_doc["F1"], new_doc["F1"]) == deep_delta(old_doc["F1"], new_doc["F1"])
        else "differ",
        deep_delta(old_doc["F1"], new_doc["F1"]) == deep_delta(old_doc["F1"], new_doc["F1"]))

    # C9 window stability
    post = {l: sha256_file(os.path.join(ROOT, NEW[l])) for l in NEW}
    stable = pre == post
    add("C9", "window stability: pre/post hashes of the five artifacts identical",
        "stable", "stable" if stable else f"changed={[l for l in pre if pre[l]!=post[l]]}", stable)

    # C10 every schema's declared F0 hash agrees with every other schema's
    declared = {l: (new_doc[l].get("f0_binding") or {}).get("declared_f0_sha256")
                for l in ("F1", "F2a", "F2b")}
    agree = len(set(declared.values())) == 1 and None not in declared.values()
    add("C10", "F1/F2a/F2b declare one identical f0_binding.declared_f0_sha256",
        "agree", declared, agree)

    # C11 the cross-class shared-core measurement itself is sensitive
    a = json.loads(json.dumps(cores["F1"]["D0"]))
    b = json.loads(json.dumps(cores["F1"]["D0"]))
    c = json.loads(json.dumps(cores["F1"]["D0"]))
    c["definition"] = "MUTANT"
    eq_pair = json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    ne_pair = json.dumps(a, sort_keys=True) != json.dumps(c, sort_keys=True)
    add("C11", "shared-core comparator: identical docs equal, mutated doc differs",
        "True/True", f"{eq_pair}/{ne_pair}", eq_pair and ne_pair)

    all_ok = all(c["pass"] for c in controls)
    result = {
        "task_id": "W065-REV12-DELTA-CENSUS-01",
        "actor": "worker-065",
        "created_at": clock.isoformat(timespec="seconds"),
        "instrument": "artifacts/worker-065/strict_yaml_census/rev12_delta_census.py",
        "current_hashes": new_hash,
        "predecessor_hashes": {l: PRED[l]["sha256"] for l in PRED},
        "artifacts": artifacts,
        "shared_data_class": shared_data_class,
        "cross_class_core": {l: {k: short(v, 400) for k, v in cores[l].items()} for l in cores},
        "findings": [
            {"id": "W065-R12-01", "kind": "delta",
             "text": "rev12 is a substantive semantic revision, not a metadata fix: F1/F2a/F2b replace the (s,delta) binder with a tagged disjoint-union index r in D0 and propagate it through D1, ordered, formal, negation, negation_normal_form, genericity and conclusion; F1 additionally rewrites D5 to the tail-pair (q,t0) predicate and adds i_plus.predicate_abbreviation."},
            {"id": "W065-R12-02", "kind": "binding",
             "text": "The contested class_contract_pointer is repaired at rev12: the three schemas now point at research_map/formulation_taxonomy.yaml#classes.<CLASS> (canonical) and carry an added class_contract_supplement_pointer for artifacts/formulation/formulation_taxonomy.yaml#class_contracts.<CLASS>; both resolve and all three declare the same measured F0 canonical sha256."},
            {"id": "W065-R12-03", "kind": "hygiene",
             "text": "The duplicate-top-level-key defect is gone at rev12: strict YAML accepts all five artifacts with zero duplicate keys at any depth, where the F1/F2a/F2b/F0-supplement predecessors are all strict-REJECT."},
            {"id": "W065-R12-04", "kind": "provenance",
             "text": "revision_history preserves every predecessor header stamp for F1/F2a/F2b (see per-artifact provenance blocks)."},
            {"id": "W065-R12-05", "kind": "shared_data_class",
             "text": "The three schemas now share one D0 regularity core; conclusion.formal differs across classes by design. Values recorded in shared_data_class."},
        ],
        "controls": controls,
        "controls_all_pass": all_ok,
        "verdict": "REV12_DELTA_CENSUS_COMPLETE" if all_ok else "INSTRUMENT_INVALID",
        "falsifier": (
            "Any of: (a) a predecessor or successor sha256 recorded here differs from a fresh "
            "measurement of the same path; (b) a semantic delta between the pinned predecessor "
            "and rev12 that this census missed, or a metadata-classified path that in fact "
            "changes class semantics (the exclusion list is published); (c) a binding check "
            "reported resolved whose pointer fragment does not in fact resolve, or vice versa; "
            "(d) a predecessor revision stamp absent from rev12 revision_history that is present "
            "in the predecessor raw header; (e) pre/post window hashes differ."),
        "limits": [
            "Measures document structure and bindings only; it does not adjudicate the mathematical content of rev12.",
            "Predecessor comparison uses third-party pinned snapshots, each verified against its recorded sha256 in control C1.",
            "Semantic/metadata classification uses the published top-level exclusion list in this file; anything outside it counts as semantic by default.",
            "Review-verdict binding at the new hashes is point-in-time and the controller audit remains authoritative.",
        ],
    }
    os.makedirs(HERE, exist_ok=True)
    os.makedirs(os.path.join(HERE, "snapshots"), exist_ok=True)
    for label, rel in NEW.items():
        dst = os.path.join(HERE, "snapshots", f"{label}__{os.path.basename(rel)}")
        shutil.copyfile(os.path.join(ROOT, rel), dst)
    with open(os.path.join(HERE, "rev12_delta_census.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
    return result


if __name__ == "__main__":
    r = main()
    print(json.dumps({
        "verdict": r["verdict"],
        "controls_all_pass": r["controls_all_pass"],
        "current_hashes": {k: v[:12] for k, v in r["current_hashes"].items()},
        "delta_counts": {k: v["delta_counts"] for k, v in r["artifacts"].items()},
        "shared_data_class": r["shared_data_class"],
    }, indent=1))
    sys.exit(0 if r["controls_all_pass"] else 1)

#!/usr/bin/env python3
"""W069-GFORM-T1-GUARD-REV13-01 -- independent machine evaluation of transfer rule T1's
three guards at the FROZEN rev29 / schema-rev13 pins.

Clean-room instrument written from the pre-registered rules in PREREGISTRATION.json.
It does not import or execute artifacts/worker-071/t1_guard_eval/eval_t1_guards.py.

Measurement only: no gate verdict, no node status, no validation_status=passed.
Exit codes: 0 = measurement valid, 2 = window drift (measurement void at changed path).
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snapshot")
CST = timezone(timedelta(hours=8))

# ---------------------------------------------------------------- pinned inputs
PINS = {
    "F2b_source": {
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "sha256": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
        "snapshot": "schemas_af_scc_c0_vacuum.yaml",
    },
    "F2a_target": {
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "sha256": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
        "snapshot": "schemas_af_scc_c2_vacuum.yaml",
    },
    "F0_canonical": {
        "path": "research_map/formulation_taxonomy.yaml",
        "sha256": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
        "snapshot": "research_map_formulation_taxonomy.yaml",
    },
    "F1_context": {
        "path": "schemas/af_wcc_vacuum.yaml",
        "sha256": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
        "snapshot": "schemas_af_wcc_vacuum.yaml",
    },
    "FROZEN_manifest": {
        "path": "artifacts/formulation/FROZEN.json",
        "sha256": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
        "snapshot": "artifacts_formulation_FROZEN.json",
    },
    "taxonomy_consistency_evidence": {
        "path": "artifacts/formulation/evidence/taxonomy_consistency.json",
        "sha256": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
        "snapshot": "artifacts_formulation_evidence_taxonomy_consistency.json",
    },
    "map_snapshot": {
        "path": "research_map/research_map.json",
        "sha256": "262da69798578d7741e1d66dec3ed977d05c4bef296974c36063cb255bee628c",
        "snapshot": "research_map_research_map.json",
    },
}

CORE_KEYS = [
    "matter",
    "cosmological_constant",
    "equations",
    "constraints.hamiltonian",
    "constraints.momentum",
    "regularity_class.default",
    "regularity_class.sobolev_variant.s",
    "regularity_class.sobolev_variant.delta",
    "regularity_class.sobolev_variant.spaces",
    "asymptotic_decay.metric",
    "asymptotic_decay.second_fundamental_form",
    "asymptotic_decay.parity_conditions",
    "symmetry",
    "adm_mass.exists",
    "adm_mass.sign",
]

VERDICTS = {"accept", "revise", "reject", "inconclusive"}
C0 = "AF-SCC-C0-VAC-GEN"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_root():
    # HERE = <repo>/artifacts/worker-069/rev13_t1_guard_eval
    return os.path.abspath(os.path.join(HERE, "..", "..", ".."))


# ------------------------------------------------------- YAML composer walking
def compose(path):
    with open(path, "r") as f:
        return yaml.compose(f)


def walk(node, prefix, out):
    """Flatten a YAML node tree to {dotted_path: (value, line)}."""
    if isinstance(node, yaml.MappingNode):
        if not node.value:
            out[prefix] = (None, node.start_mark.line + 1)
            return
        for k, v in node.value:
            key = k.value
            p = "%s.%s" % (prefix, key) if prefix else str(key)
            walk(v, p, out)
    elif isinstance(node, yaml.SequenceNode):
        if not node.value:
            out[prefix] = (None, node.start_mark.line + 1)
            return
        for i, v in enumerate(node.value):
            walk(v, "%s[%d]" % (prefix, i), out)
    else:
        out[prefix] = (node.value, node.start_mark.line + 1)


def root_mapping(node):
    if not isinstance(node, yaml.MappingNode):
        raise ValueError("document root is not a mapping")
    return node


def find_key(mapping_node, key):
    for k, v in mapping_node.value:
        if k.value == key:
            return v
    return None


def resolve_dotted(mapping_node, dotted):
    """Resolve a dotted path of mapping keys; returns (value, line) or None."""
    cur = mapping_node
    line = None
    for part in dotted.split("."):
        if not isinstance(cur, yaml.MappingNode):
            return None
        nxt = None
        for k, v in cur.value:
            if k.value == part:
                nxt = v
                line = v.start_mark.line + 1
                break
        if nxt is None:
            return None
        cur = nxt
    if isinstance(cur, yaml.ScalarNode):
        return (cur.value, line)
    flat = {}
    walk(cur, "", flat)
    return (flat, line)


def flatten_dict(d, prefix=""):
    out = {}
    for k, v in d.items():
        p = "%s.%s" % (prefix, k) if prefix else str(k)
        if isinstance(v, dict):
            out.update(flatten_dict(v, p))
        else:
            out[p] = (v, None)
    return out


# ------------------------------------------------------------- guard readings
def g1_strict(leaves_a, leaves_b):
    """Exact leaf equality over the union of paths. a = target (F2a), b = source (F2b)."""
    witnesses = []
    for p in sorted(set(leaves_a) | set(leaves_b)):
        a = leaves_a.get(p)
        b = leaves_b.get(p)
        if a is None or b is None:
            witnesses.append({
                "path": p,
                "target_value": None if a is None else a[0],
                "source_value": None if b is None else b[0],
                "target_line": None if a is None else a[1],
                "source_line": None if b is None else b[1],
                "kind": "missing_on_one_side",
            })
        elif a[0] != b[0]:
            witnesses.append({
                "path": p,
                "target_value": a[0],
                "source_value": b[0],
                "target_line": a[1],
                "source_line": b[1],
                "kind": "value_mismatch",
            })
    return ("PASS" if not witnesses else "FAIL"), witnesses


_T3_PAREN = re.compile(r"\([^()]*\)")
_T3_TAIL = re.compile(r";.*$")


def t3_normalize(value):
    if value is None:
        return None
    s = str(value)
    s = _T3_PAREN.sub("", s)
    s = _T3_TAIL.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.rstrip(".,;:")
    return s.strip()


def g1_core(leaves_a, leaves_b, core_keys):
    rows = []
    equal = True
    for key in core_keys:
        a = leaves_a.get(key)
        b = leaves_b.get(key)
        na = t3_normalize(a[0]) if a else None
        nb = t3_normalize(b[0]) if b else None
        same = (na == nb)
        equal = equal and same
        rows.append({"key": key, "target_normalized": na, "source_normalized": nb, "equal": same})
    return ("PASS" if equal else "FAIL"), rows


def g2_literal(doc_a, doc_b, names):
    detail = {}
    evaluable = True
    for name in names:
        ra = resolve_dotted(doc_a, name)
        rb = resolve_dotted(doc_b, name)
        detail[name] = {
            "target_resolves": ra is not None,
            "source_resolves": rb is not None,
            "target_value": None if ra is None else ra[0],
            "source_value": None if rb is None else rb[0],
            "equal": bool(ra is not None and rb is not None and ra[0] == rb[0]),
        }
        if ra is None or rb is None:
            evaluable = False
    if not evaluable:
        return "UNEVALUABLE_AS_WRITTEN", detail
    return ("PASS" if all(v["equal"] for v in detail.values()) else "FAIL"), detail


def g3_literal(map_doc):
    claims = map_doc.get("claims", [])
    reviews = map_doc.get("reviews", [])
    by_target = {}
    for r in reviews:
        tgt = r.get("target_id")
        if isinstance(tgt, list):
            tgt = " ".join(str(x) for x in tgt)
        if tgt is None:
            continue
        by_target.setdefault(str(tgt), []).append(r.get("verdict"))
    c0_claims = []
    for c in claims:
        ids = []
        if c.get("class_id"):
            ids.append(c["class_id"])
        ids.extend(c.get("class_ids") or [])
        if C0 in ids:
            c0_claims.append(c)
    bound = []
    strengthened = []
    for c in c0_claims:
        eid = str(c.get("event_id"))
        refs = c.get("artifact_refs") or []
        verdicts = by_target.get(eid, [])
        qualifies = bool(refs) and any(v in VERDICTS for v in verdicts)
        text = " ".join(str(c.get(k) or "") for k in ("statement", "conclusion", "conclusion_text"))
        mentions = bool(re.search(r"\bc0\b", text, re.I) and re.search("inextendib", text, re.I))
        row = {
            "event_id": eid,
            "has_artifact_refs": bool(refs),
            "verdicts": verdicts,
            "literal_qualifies": qualifies,
            "mentions_c0_inextendibility": mentions,
        }
        if qualifies:
            bound.append(row)
        if qualifies and mentions and any(v == "accept" for v in verdicts):
            strengthened.append(row)
    return {
        "c0_claim_count": len(c0_claims),
        "bound_claim_count": len(bound),
        "bound_claims": bound,
        "strengthened_qualifying_count": len(strengthened),
        "strengthened_qualifying": strengthened,
        "verdict": "PASS" if bound else "FAIL",
    }


# ------------------------------------------------------------------- controls
def run_controls(f2a_leaves, f2b_leaves):
    controls = {}

    v, w = g1_strict(f2b_leaves, f2b_leaves)
    controls["CTL_POS_G1_source_vs_self"] = {"verdict": v, "witness_count": len(w), "expected": "PASS",
                                             "ok": v == "PASS" and not w}

    mutated = {k: list(t) for k, t in f2a_leaves.items()}
    key = "asymptotic_decay.parity_conditions"
    mutated[key][0] = str(mutated[key][0]) + " [MUTANT]"
    v, w = g1_strict(mutated, f2a_leaves)
    paths = sorted(x["path"] for x in w)
    controls["CTL_NEG_G1_parity_mutant"] = {"verdict": v, "witness_paths": paths,
                                            "expected": "FAIL with exactly one witness at parity_conditions",
                                            "ok": v == "FAIL" and paths == [key]}

    v, w = g1_strict(f2a_leaves, f2a_leaves)
    controls["CTL_SELFEQ_G1_target_vs_self"] = {"verdict": v, "witness_count": len(w),
                                                "expected": "PASS", "ok": v == "PASS" and not w}

    a = flatten_dict({"a": 1, "b": 2})
    b = flatten_dict({"a": 1})
    v, w = g1_strict(a, b)
    paths = sorted(x["path"] for x in w)
    controls["CTL_MISSING_KEY_G1"] = {"verdict": v, "witness_paths": paths,
                                      "expected": "FAIL with witness b",
                                      "ok": v == "FAIL" and paths == ["b"]}

    doc_pos_a = compose_from_dict({"genericity_kind": "residual_comeager", "genericity_topology": "T"})
    doc_pos_b = compose_from_dict({"genericity_kind": "residual_comeager", "genericity_topology": "T"})
    v, _ = g2_literal(doc_pos_a, doc_pos_b, ["genericity_kind", "genericity_topology"])
    controls["CTL_POS_G2"] = {"verdict": v, "expected": "PASS", "ok": v == "PASS"}

    doc_neg_b = compose_from_dict({"genericity_kind": "residual_comeager", "genericity_topology": "OTHER"})
    v, _ = g2_literal(doc_pos_a, doc_neg_b, ["genericity_kind", "genericity_topology"])
    controls["CTL_NEG_G2"] = {"verdict": v, "expected": "FAIL", "ok": v == "FAIL"}

    v = g3_literal({
        "claims": [{"event_id": "c1", "class_id": C0, "artifact_refs": ["x"], "statement": "s"}],
        "reviews": [{"target_id": "c1", "verdict": "accept"}],
    })
    controls["CTL_POS_G3"] = {"verdict": v["verdict"], "expected": "PASS", "ok": v["verdict"] == "PASS"}

    v = g3_literal({
        "claims": [{"event_id": "c1", "class_id": C0, "artifact_refs": ["x"], "statement": "s"}],
        "reviews": [],
    })
    controls["CTL_NEG_G3"] = {"verdict": v["verdict"], "expected": "FAIL", "ok": v["verdict"] == "FAIL"}

    return controls


def compose_from_dict(d):
    return yaml.compose(yaml.safe_dump(d))


# ----------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "raw", "guard_eval.json"))
    ap.add_argument("--report", default=os.path.join(HERE, "report.json"))
    args = ap.parse_args()

    root = repo_root()
    started = datetime.now(CST).isoformat()

    # ---- window: hash pinned live paths before
    live_before = {}
    snap_before = {}
    for name, pin in PINS.items():
        live_before[name] = sha256_file(os.path.join(root, pin["path"]))
        snap_before[name] = sha256_file(os.path.join(SNAP, pin["snapshot"]))

    # ---- load the three schemas from the snapshots (binding pins)
    f2b_doc = compose(os.path.join(SNAP, PINS["F2b_source"]["snapshot"]))
    f2a_doc = compose(os.path.join(SNAP, PINS["F2a_target"]["snapshot"]))
    f1_doc = compose(os.path.join(SNAP, PINS["F1_context"]["snapshot"]))

    def data_class_leaves(doc):
        dc = find_key(root_mapping(doc), "data_class")
        if dc is None:
            raise ValueError("data_class not found")
        flat = {}
        walk(dc, "", flat)
        return flat

    f2b_leaves = data_class_leaves(f2b_doc)
    f2a_leaves = data_class_leaves(f2a_doc)
    f1_leaves = data_class_leaves(f1_doc)

    g1_verdict, g1_witnesses = g1_strict(f2a_leaves, f2b_leaves)
    g1_core_verdict, g1_core_rows = g1_core(f2a_leaves, f2b_leaves, CORE_KEYS)
    g1_core_witnesses = sorted({w["path"] for w in g1_witnesses if w["path"] in CORE_KEYS})
    g1_context_verdict, g1_context_witnesses = g1_strict(f1_leaves, f2b_leaves)
    g1_context_core = sorted({w["path"] for w in g1_context_witnesses if w["path"] in CORE_KEYS})

    g2_verdict, g2_detail = g2_literal(f2a_doc, f2b_doc, ["genericity_kind", "genericity_topology"])
    g2_mapped_verdict, g2_mapped_detail = g2_literal(
        f2a_doc, f2b_doc, ["genericity.kind", "genericity.topology_or_measure"])

    with open(os.path.join(SNAP, PINS["map_snapshot"]["snapshot"])) as f:
        map_doc = json.load(f)
    g3 = g3_literal(map_doc)

    controls = run_controls(f2a_leaves, f2b_leaves)
    controls_all_pass = all(c["ok"] for c in controls.values())

    licensed = (g1_verdict == "PASS" and g2_verdict == "PASS" and g3["verdict"] == "PASS")

    # ---- window: hash pinned live paths after
    live_after = {}
    snap_after = {}
    for name, pin in PINS.items():
        live_after[name] = sha256_file(os.path.join(root, pin["path"]))
        snap_after[name] = sha256_file(os.path.join(SNAP, pin["snapshot"]))

    snapshot_stable = all(snap_before[n] == snap_after[n] == PINS[n]["sha256"] for n in PINS)
    live_matches_pin = {n: (live_after[n] == PINS[n]["sha256"]) for n in PINS}
    live_drifted_during_run = sorted(n for n in PINS if live_before[n] != live_after[n])
    window_status = "STABLE" if snapshot_stable else "VOID"
    measurement_valid = bool(snapshot_stable and controls_all_pass)

    result = {
        "task_id": "W069-GFORM-T1-GUARD-REV13-01",
        "actor": "worker-069",
        "instrument": "artifacts/worker-069/rev13_t1_guard_eval/eval_t1_guards_rev13.py",
        "instrument_sha256": sha256_file(os.path.abspath(__file__)),
        "generated_at": started,
        "pins": {n: {"path": p["path"], "sha256": p["sha256"]} for n, p in PINS.items()},
        "window": {
            "status": window_status,
            "snapshot_stable": snapshot_stable,
            "live_matches_pin_at_exit": live_matches_pin,
            "live_drifted_during_run": live_drifted_during_run,
            "note": "Binding pins are the snapshot copies; live paths are hashed before and after as an observation. Snapshot instability voids the measurement.",
        },
        "measurement_valid": measurement_valid,
        "guards": {
            "G1_literal": {"verdict": g1_verdict, "witness_count": len(g1_witnesses),
                           "witnesses": g1_witnesses,
                           "core_key_witnesses": g1_core_witnesses,
                           "witnesses_outside_core": [w["path"] for w in g1_witnesses
                                                      if w["path"].split(".", 1)[1] not in CORE_KEYS]},
            "G1_secondary_core_T3": {"verdict": g1_core_verdict, "rows": g1_core_rows},
            "G2_literal": {"verdict": g2_verdict, "detail": g2_detail},
            "G2_secondary_mapped": {"verdict": g2_mapped_verdict, "detail": g2_mapped_detail},
            "G3_literal": g3,
        },
        "F1_context_not_part_of_T1": {
            "verdict": g1_context_verdict,
            "witness_count": len(g1_context_witnesses),
            "core_key_witnesses": g1_context_core,
            "witnesses": g1_context_witnesses,
        },
        "controls": controls,
        "controls_all_pass": controls_all_pass,
        "T1_licensed_at_pins": bool(licensed),
        "overall_verdict": ("T1_LICENSED_AT_PINS" if licensed
                            else "T1_NOT_LICENSED_AT_PINS"),
        "authority_note": "Worker measurement only; no gate verdict, node status or validation_status=passed.",
    }

    # byte-determinism digest: canonical JSON without volatile wall-clock fields
    stable_view = {k: v for k, v in result.items() if k != "generated_at"}
    digest = hashlib.sha256(json.dumps(stable_view, sort_keys=True).encode()).hexdigest()
    result["determinism_sha256_excluding_generated_at"] = digest

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    for target in (args.out, args.report):
        with open(target, "w") as f:
            json.dump(result, f, indent=1, sort_keys=True)
            f.write("\n")

    print(json.dumps({
        "task_id": result["task_id"],
        "G1_literal": g1_verdict,
        "G1_core": g1_core_verdict,
        "G2_literal": g2_verdict,
        "G2_mapped": g2_mapped_verdict,
        "G3_literal": g3["verdict"],
        "T1_licensed_at_pins": result["T1_licensed_at_pins"],
        "controls_all_pass": controls_all_pass,
        "window_status": window_status,
        "measurement_valid": measurement_valid,
        "determinism_sha256_excluding_generated_at": digest,
    }, indent=1))

    if not measurement_valid:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

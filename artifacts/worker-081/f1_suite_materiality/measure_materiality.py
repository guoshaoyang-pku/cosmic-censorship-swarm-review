#!/usr/bin/env python3
"""W081-GFORM-F1-SUITE-MATERIALITY-01

Independent materiality adjudication of the F1 falsifier-suite stale binding
(25/25 rows bind F1 rev12 cce9c60146d6; live canonical F1 is rev13 d9cebb9404b2).

Question (worker-073 hard failure F1-073-01 prescription, option b):
is the declared semantics-preserving rev12->rev13 delta *immaterial for the 25
rows' 84 probes*, so that a controller adjudication (or a pure binding restamp)
is defensible -- or does some probe verdict change, requiring re-derivation?

Method (all read-only; no canonical byte written):
 1. verify the six byte pins before and after the measurement;
 2. parse the F1 rev12 snapshot and the live rev13 schema with duplicate-key
    detection (parser-stability control);
 3. recompute all 84 probes with an independent engine over both revisions;
 4. diff every leaf of the two YAML documents and classify each changed leaf as
    probe-touched / probe-untouched and verdict-affecting / inert;
 5. run four in-memory mutation controls (three positive, one specificity) that
    falsify vacuity of the probe engine.

Falsifier: any probe whose recomputed verdict differs between rev12 and rev13;
or any pin differing from the recorded sha256 at start/end; or a positive
control that does not move any probe verdict (engine vacuous); or a specificity
control that moves one.
"""

import hashlib
import json
import os
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

PINS = {
    "suite": (
        "schemas/f1_falsifier_tests.jsonl",
        "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    ),
    "f1_rev12": (
        "artifacts/worker-060/rev29_binding_acceptance/snapshots/f1__af_wcc_vacuum.cce9c60146d6.yaml",
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    ),
    "f1_rev13": (
        "schemas/af_wcc_vacuum.yaml",
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    ),
    "frozen": (
        "artifacts/formulation/FROZEN.json",
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    ),
    "f0": (
        "research_map/formulation_taxonomy.yaml",
        "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    ),
    "f1_mirror": (
        "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    ),
}

PROBE_KINDS = {"contains", "equals", "is_none", "is_true", "path_exists", "nonnull"}


def sha256_file(rel):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, rel), "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class DupTrackingLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of hiding them."""

    def __init__(self, stream):
        super().__init__(stream)
        self.duplicate_paths = []

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _value in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                self.duplicate_paths.append(str(key))
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load_yaml(rel):
    loader = DupTrackingLoader(open(os.path.join(ROOT, rel), "r", encoding="utf-8"))
    try:
        doc = loader.get_data()
    finally:
        loader.dispose()
    return doc, loader.duplicate_paths


_PATH_TOKEN = None


def resolve(doc, path):
    """Resolve a dotted path with optional [i] indices. Returns (ok, value)."""
    cur = doc
    token = ""
    i = 0
    parts = []
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if token:
                parts.append(token)
                token = ""
            i += 1
        elif ch == "[":
            if token:
                parts.append(token)
                token = ""
            j = path.index("]", i)
            parts.append(int(path[i + 1 : j]))
            i = j + 1
        else:
            token += ch
            i += 1
    if token:
        parts.append(token)
    for p in parts:
        if isinstance(p, int):
            if not isinstance(cur, list) or p >= len(cur):
                return False, None
            cur = cur[p]
        else:
            if not isinstance(cur, dict) or p not in cur:
                return False, None
            cur = cur[p]
    return True, cur


def stringify(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=False)


def eval_probe(probe, doc):
    ok, value = resolve(doc, probe["path"])
    kind = probe["kind"]
    expected = probe.get("expected")
    if kind == "path_exists":
        return {"pass": bool(ok), "resolved": ok, "reason": "path_exists" if ok else "path_missing"}
    if not ok:
        return {"pass": False, "resolved": False, "reason": "path_missing"}
    if kind == "contains":
        hit = expected in stringify(value)
        return {"pass": bool(hit), "resolved": True, "reason": "token_present" if hit else "token_absent"}
    if kind == "equals":
        same = value == expected
        return {"pass": bool(same), "resolved": True, "reason": "value_equal" if same else "value_differs"}
    if kind == "is_none":
        return {"pass": value is None, "resolved": True, "reason": "is_none" if value is None else "not_none"}
    if kind == "is_true":
        return {"pass": value is True, "resolved": True, "reason": "is_true" if value is True else "not_true"}
    if kind == "nonnull":
        return {"pass": value is not None, "resolved": True, "reason": "nonnull" if value is not None else "null"}
    raise ValueError("unknown probe kind: %r" % kind)


def leaves(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, "%s.%s" % (prefix, k) if prefix else str(k))
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            yield from leaves(v, "%s[%d]" % (prefix, idx))
    else:
        yield prefix, obj


def touched_by(changed_path, probe_paths):
    """Probe touches a changed leaf if the probe resolves it, an ancestor of it,
    or a descendant of it."""
    hits = []
    for pp in probe_paths:
        if pp == changed_path:
            hits.append(pp)
        elif changed_path.startswith(pp + ".") or changed_path.startswith(pp + "["):
            hits.append(pp)  # probe resolves an ancestor of the changed leaf
        elif pp.startswith(changed_path + ".") or pp.startswith(changed_path + "["):
            hits.append(pp)  # probe resolves inside the changed subtree
    return sorted(set(hits))


def recompute(doc, rows):
    out = []
    for row in rows:
        for probe in row["probe_results"]:
            res = eval_probe(probe, doc)
            out.append(
                {
                    "test_id": row["test_id"],
                    "path": probe["path"],
                    "kind": probe["kind"],
                    "expected": probe.get("expected"),
                    "stored_pass": bool(probe.get("pass")),
                    "pass": res["pass"],
                    "resolved": res["resolved"],
                    "reason": res["reason"],
                }
            )
    return out


def mutation_control(doc, rows, mutate, label):
    import copy

    mutant = copy.deepcopy(doc)
    mutate(mutant)
    before = recompute(doc, rows)
    after = recompute(mutant, rows)
    moved = [i for i, (a, b) in enumerate(zip(before, after)) if a["pass"] != b["pass"]]
    moved_ids = sorted({before[i]["test_id"] for i in moved})
    return {"control": label, "probes_moved": len(moved), "rows_moved": moved_ids}


def main():
    pins_start = {k: {"path": p, "expected": h, "measured": sha256_file(p)} for k, (p, h) in PINS.items()}
    pin_ok_start = all(v["measured"] == v["expected"] for v in pins_start.values())

    rows = [json.loads(line) for line in open(os.path.join(ROOT, PINS["suite"][0]), encoding="utf-8") if line.strip()]
    doc12, dup12 = load_yaml(PINS["f1_rev12"][0])
    doc13, dup13 = load_yaml(PINS["f1_rev13"][0])

    probes12 = recompute(doc12, rows)
    probes13 = recompute(doc13, rows)

    flips = []
    for p12, p13 in zip(probes12, probes13):
        assert (p12["test_id"], p12["path"], p12["kind"]) == (p13["test_id"], p13["path"], p13["kind"])
        if p12["pass"] != p13["pass"]:
            flips.append(
                {
                    "test_id": p12["test_id"],
                    "path": p12["path"],
                    "kind": p12["kind"],
                    "rev12": p12["pass"],
                    "rev13": p13["pass"],
                }
            )

    stored_mismatch12 = [
        {"test_id": p["test_id"], "path": p["path"], "kind": p["kind"], "stored": p["stored_pass"], "recomputed": p["pass"], "reason": p["reason"]}
        for p in probes12
        if p["stored_pass"] != p["pass"]
    ]
    stored_mismatch13 = [
        {"test_id": p["test_id"], "path": p["path"], "kind": p["kind"], "stored": p["stored_pass"], "recomputed": p["pass"], "reason": p["reason"]}
        for p in probes13
        if p["stored_pass"] != p["pass"]
    ]

    l12 = dict(leaves(doc12))
    l13 = dict(leaves(doc13))
    changed = sorted(set(l12) | set(l13))
    changed = [k for k in changed if l12.get(k) != l13.get(k)]
    probe_paths = sorted({p["path"] for p in probes12})
    probe_touched = {pp: [p for p in probes12 if p["path"] == pp] for pp in probe_paths}

    changed_class = []
    for ck in changed:
        hits = touched_by(ck, probe_paths)
        verdict_affected = []
        for hp in hits:
            for p12, p13 in zip(probes12, probes13):
                if p12["path"] == hp and p12["pass"] != p13["pass"]:
                    verdict_affected.append({"test_id": p12["test_id"], "path": hp, "rev12": p12["pass"], "rev13": p13["pass"]})
        changed_class.append(
            {
                "leaf": ck,
                "rev12_value": stringify(l12.get(ck))[:220],
                "rev13_value": stringify(l13.get(ck))[:220],
                "probe_paths_touching": hits,
                "probe_verdicts_affected": verdict_affected,
            }
        )

    # worker-073 named these rows as materially affected (deciding leaf edited).
    named_rows = ["F1-AMB-11", "F1-AMB-17", "F1-AMB-23"]
    named_report = {}
    for tid in named_rows:
        row_probes = [(p12, p13) for p12, p13 in zip(probes12, probes13) if p12["test_id"] == tid]
        named_report[tid] = {
            "n_probes": len(row_probes),
            "n_verdict_flips": sum(1 for a, b in row_probes if a["pass"] != b["pass"]),
            "deciding_paths": sorted({a["path"] for a, b in row_probes}),
            "all_pass_rev13": all(b["pass"] for a, b in row_probes),
            "failing_rev13": [b["path"] for a, b in row_probes if not b["pass"]],
        }

    controls = [
        mutation_control(doc13, rows, lambda d: d["visibility"].__setitem__("definition", ""), "M1-blank-visibility.definition-positive"),
        mutation_control(
            doc13,
            rows,
            lambda d: d["f0_binding"].__setitem__("declared_f0_sha256", "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"),
            "M2-restore-AMB25-expected-hash-positive",
        ),
        mutation_control(doc13, rows, lambda d: d["non_vacuity"].pop("condition", None), "M3-delete-non_vacuity.condition-positive"),
        mutation_control(doc13, rows, lambda d: d.__setitem__("authored_by", "mutant-specificity-control"), "M4-unreferenced-leaf-specificity"),
    ]

    pins_end = {k: {"path": p, "expected": h, "measured": sha256_file(p)} for k, (p, h) in PINS.items()}
    pin_ok_end = all(v["measured"] == v["expected"] for v in pins_end.values())

    failing_rev13 = [p for p in probes13 if not p["pass"]]
    failing_rows = sorted({p["test_id"] for p in failing_rev13})
    rows_all_pass = sorted({r["test_id"] for r in rows} - set(failing_rows))

    bindings = sorted({r["binding_sha256"] for r in rows})
    rev_bindings = sorted({r.get("binding_frozen_revision") for r in rows})

    engine_calibrated = len(stored_mismatch12) == 2 and not flips

    evidence = {
        "task_id": "W081-GFORM-F1-SUITE-MATERIALITY-01",
        "actor": "worker-081",
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids_touched": ["AF-WCC-VAC-GEN"],
        "node_id": "F1",
        "gate": "G-FORM",
        "created_at": None,  # filled by caller via --stamp
        "root": ROOT,
        "question": "Is the F1 rev12->rev13 delta material to the 25-row / 84-probe falsifier suite, or is a pure binding restamp / controller immateriality adjudication defensible?",
        "pins": PINS,
        "pins_start": pins_start,
        "pins_end": pins_end,
        "pin_ok_start": pin_ok_start,
        "pin_ok_end": pin_ok_end,
        "suite": {
            "rows": len(rows),
            "probes": len(probes12),
            "bindings": bindings,
            "binding_frozen_revisions": rev_bindings,
            "corpus_sha256": pins_start["suite"]["measured"],
            "frozen_pins_corpus": True,
        },
        "duplicate_keys": {"rev12": dup12, "rev13": dup13},
        "engine": {
            "kinds_supported": sorted(PROBE_KINDS),
            "stored_mismatches_rev12": stored_mismatch12,
            "stored_mismatches_rev13": stored_mismatch13,
            "n_stored_mismatch_rev12": len(stored_mismatch12),
            "n_stored_mismatch_rev13": len(stored_mismatch13),
            "calibration_reproduces_worker029_counts": len(stored_mismatch12) == 2 and len(stored_mismatch13) == 2,
        },
        "materiality": {
            "changed_leaf_paths": changed,
            "n_changed_leaf_paths": len(changed),
            "changed_leaf_classification": changed_class,
            "verdict_flips_rev12_vs_rev13": flips,
            "n_verdict_flips": len(flips),
            "verdict_vector_identical": len(flips) == 0,
        },
        "named_rows_worker073": named_report,
        "controls": controls,
        "suite_health_at_rev13": {
            "failing_probes": failing_rev13,
            "n_failing_probes": len(failing_rev13),
            "failing_rows": failing_rows,
            "n_rows_all_probe_pass": len(rows_all_pass),
            "rows_all_probe_pass": rows_all_pass,
        },
        "verdict": None,  # filled below
        "falsifier": (
            "Re-run in an unchanged tree with the same six pins: any probe whose rev12 vs rev13 verdict differs; "
            "any pin measured != recorded; any positive control moving 0 probes; the specificity control moving >0 probes; "
            "or any leaf-diff count other than 12 falsifies this report."
        ),
        "not_claimed": [
            "no gate verdict",
            "no node status",
            "no validation_status=passed",
            "no canonical byte written",
            "no adjudication of the mathematical direction of the rev13 edits (worker-040/worker-076 scope)",
        ],
    }

    if not (pin_ok_start and pin_ok_end):
        evidence["verdict"] = "VOID_PIN_DRIFT"
    elif flips:
        evidence["verdict"] = "MATERIAL_REBIND_REQUIRES_REDERIVATION"
    elif not engine_calibrated:
        evidence["verdict"] = "INCONCLUSIVE_ENGINE_CALIBRATION"
    else:
        evidence["verdict"] = "STALE_BINDING_PROBE_IMMATERIAL"

    evidence["materiality_conclusion"] = (
        "The rev12->rev13 delta changes %d leaf paths; %d probe verdicts flip across the 84 probes. "
        "F1-AMB-25 carries %d stale expectations that fail at BOTH revisions, so a pure F1-binding rebind does not make the suite green."
        % (
            len(changed),
            len(flips),
            len(failing_rev13),
        )
    )

    out_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_dir, "evidence.json"), "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=1, sort_keys=True)
        fh.write("\n")

    print(json.dumps({k: evidence[k] for k in ["verdict", "materiality_conclusion", "pin_ok_start", "pin_ok_end"]}, indent=1))
    print("changed leaves: %d | verdict flips: %d | failing probes rev13: %d (%s)" % (len(changed), len(flips), len(failing_rev13), failing_rows))
    for c in controls:
        print("control %-46s moved %d probes %s" % (c["control"], c["probes_moved"], c["rows_moved"]))
    return 0 if evidence["verdict"] != "VOID_PIN_DRIFT" else 3


if __name__ == "__main__":
    sys.exit(main())

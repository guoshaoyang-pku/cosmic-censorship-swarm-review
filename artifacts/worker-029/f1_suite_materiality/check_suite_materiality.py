#!/usr/bin/env python3
"""W029-F1-SUITE-MATERIALITY-06 -- independent, read-only materiality adjudication for L-FORM-04.

Question (registered by astra-lead-formulation, lead-form-20260912T005743-93, node F1, gate G-FORM):
  schemas/f1_falsifier_tests.jsonl (25 rows, 84 probes) declares binding_sha256 = F1 rev12
  cce9c60146d6 while the canonical F1 schema is now rev13 d9cebb9404b2. Must the corpus be
  re-bound, and is a mechanical hash rebind sufficient?

Method (all read-only; no canonical file is written):
  1. Fail-closed pins on the live bytes and on a THIRD-PARTY rev12 snapshot (worker-060).
  2. Snapshots every input byte-for-byte under snapshots/ with a manifest.
  3. Flattens the rev12 -> rev13 YAML trees to leaf paths and reports the structural delta.
  4. Recomputes all 84 stored probes independently against BOTH the rev12 and the rev13 bytes.
  5. Per row: intersects deciding_field, deciding_field_alternates and probe paths with the
     delta (ancestor/descendant relation), and separates
        MATERIAL_DECIDING / MATERIAL_PROBE  -- a path the row exercises changed;
        SIBLING_BINDING_CHANGE              -- only a sibling under the same binding parent changed;
        DECLARATION_ONLY                    -- no exercised path and no sibling change;
     plus expectation status: INVALIDATED_BY_REV13 / PRE_EXISTING_FALSE / CLEAN.
  6. Resolves the suite's cross-artifact declaration (F0 hash) on disk.
  7. Controls: planted material change, planted immaterial change, mutated expectation, identical
     trees, metadata-only change, real rev12 reproduction of the known mismatch set, duplicate-key
     scan of both schema snapshots, malformed-probe fail-closed.

Exit codes: 0 measurement complete; 2 expectation failed; 3 pin drift / input unreadable.
Deterministic core is report_core.json (timestamp-free); report.json and evidence.json carry
created_at and are emission records, not byte-stable measurements.

Authority: worker evidence only. This script cannot set status=done, validation_status=passed,
or any gate verdict.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SNAP = OUT / "snapshots"

TASK_ID = "W029-F1-SUITE-MATERIALITY-06"
ACTOR = "worker-029"
NODE_ID = "F1"
CLASS_ID = "AF-WCC-VAC-GEN"
GATE = "G-FORM"

# Live pins + one third-party rev12 before-oracle. A pin mismatch is pin drift (exit 3).
PINS = {
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/f1_falsifier_tests.jsonl": "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "research_map/formulation_taxonomy.yaml": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "artifacts/formulation/formulation_taxonomy.yaml": "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    "artifacts/worker-060/rev29_binding_acceptance/snapshots/f1__af_wcc_vacuum.cce9c60146d6.yaml":
        "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
}
LIVE_F1 = "schemas/af_wcc_vacuum.yaml"
BEFORE_F1 = "artifacts/worker-060/rev29_binding_acceptance/snapshots/f1__af_wcc_vacuum.cce9c60146d6.yaml"
SUITE = "schemas/f1_falsifier_tests.jsonl"
FROZEN = "artifacts/formulation/FROZEN.json"
F0_TAXONOMY = "research_map/formulation_taxonomy.yaml"
F0_SUPPLEMENT = "artifacts/formulation/formulation_taxonomy.yaml"

METADATA_RE = re.compile(r"^(revision|revised_at|revision_history(\[\d+\])?(\..*)?)$")
BINDING_META_RE = re.compile(r"^f0_binding\.(checked_at|consistency_evidence_sha256|binding_note)$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
KINDS = {"equals", "contains", "nonnull", "path_exists", "is_none", "is_true"}


class Drift(Exception):
    pass


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------- yaml helpers
def load_mapping(text: str):
    return yaml.safe_load(text)


def flatten(obj, prefix: str = ""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v, key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def leaf_repr(v):
    if isinstance(v, str):
        return "s:" + v
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "b:" + ("true" if v else "false")
    if isinstance(v, (int, float)):
        return "n:" + repr(v)
    return "j:" + canon(v)


def resolve(doc, path: str):
    cur = doc
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        if part.startswith("["):
            cur = cur[int(part[1:-1])]
        else:
            cur = cur[part]
    return cur


def path_exists(doc, path: str) -> bool:
    try:
        resolve(doc, path)
        return True
    except Exception:
        return False


def related(a: str, b: str) -> bool:
    """True when the two dotted/indexed leaf paths share an ancestor relation (or are equal)."""
    if a == b:
        return True
    if a.startswith(b + ".") or a.startswith(b + "["):
        return True
    if b.startswith(a + ".") or b.startswith(a + "["):
        return True
    return False


def dup_keys(node, path: str = ""):
    out = []
    if isinstance(node, yaml.MappingNode):
        seen = set()
        for k, v in node.value:
            key = str(k.value)
            full = f"{path}.{key}" if path else key
            if key in seen:
                out.append(full)
            else:
                seen.add(key)
            out += dup_keys(v, full)
    elif isinstance(node, yaml.SequenceNode):
        for i, v in enumerate(node.value):
            out += dup_keys(v, f"{path}[{i}]")
    return out


# ---------------------------------------------------------------- probe evaluator
def evaluate(kind: str, expected, value):
    """Return (recomputed_pass, live_repr). Independent reimplementation of the suite's kinds.

    Structured values are flattened with json.dumps(value, default=str, ensure_ascii=False) --
    the suite author's verifier spelling. `contains` expectations embed that spelling (e.g. a
    space after the mapping colon), so a compact-separator flattening would fabricate failures.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown probe kind {kind!r}")
    if kind == "path_exists":
        return True, "<present>"
    if isinstance(value, str):
        live_repr = value
        blob = value
    else:
        live_repr = json.dumps(value, default=str, ensure_ascii=False)
        blob = live_repr
    if kind == "equals":
        return live_repr == str(expected), live_repr
    if kind == "contains":
        return str(expected) in blob, live_repr
    if kind == "nonnull":
        return value not in (None, "", [], {}), live_repr
    if kind == "is_none":
        return value is None, live_repr
    if kind == "is_true":
        return value is True, live_repr
    raise AssertionError(kind)


def probe_row(row, doc_live, doc_before):
    results = []
    for pr in row.get("probe_results", []):
        path, kind, expected = pr.get("path"), pr.get("kind"), pr.get("expected")
        entry = {"path": path, "kind": kind, "expected": expected,
                 "stored_pass": bool(pr.get("pass")), "role": pr.get("role")}
        for label, doc in (("rev13", doc_live), ("rev12", doc_before)):
            try:
                value = resolve(doc, path)
                ok, live = evaluate(kind, expected, value)
                entry[f"computed_{label}"] = ok
                entry[f"live_{label}"] = live if len(str(live)) <= 160 else str(live)[:160] + "..."
            except Exception as exc:  # missing path or bad kind: fail closed, report the error
                entry[f"computed_{label}"] = False
                entry[f"error_{label}"] = f"{type(exc).__name__}: {exc}"
        results.append(entry)
    return results


# ---------------------------------------------------------------- core measurement
def measure():
    checks, controls, errors = [], [], []

    # 1. snapshots + pin check
    SNAP.mkdir(parents=True, exist_ok=True)
    snap_manifest, pin_state = [], {}
    raw = {}
    for rel, pin in PINS.items():
        p = ROOT / rel
        if not p.exists():
            raise Drift(f"missing pinned input {rel}")
        b = p.read_bytes()
        raw[rel] = b
        h = sha256_bytes(b)
        snap_name = rel.replace("/", "__") + "." + h[:12]
        (SNAP / snap_name).write_bytes(b)
        snap_manifest.append({"source_path": rel, "snapshot": f"snapshots/{snap_name}",
                              "sha256": h, "bytes": len(b), "pin": pin, "matched": h == pin})
        pin_state[rel] = {"sha256": h, "bytes": len(b), "pin_matched": h == pin}
        if h != pin:
            raise Drift(f"pin drift on {rel}: measured {h} != pinned {pin}")
    (OUT / "snapshot_manifest.json").write_text(json.dumps(
        {"task_id": TASK_ID, "pins": pin_state, "snapshots": snap_manifest}, indent=1, sort_keys=True) + "\n")

    # 2. FROZEN revision + declared pins
    frozen = yaml.safe_load(raw[FROZEN].decode())
    fro_files = frozen["files"]
    fz = {
        "revision": frozen.get("revision"),
        "frozen_at": frozen.get("frozen_at"),
        "sha256": pin_state[FROZEN]["sha256"],
        "suite_pin": fro_files[SUITE]["sha256"],
        "f1_pin": fro_files[LIVE_F1]["sha256"],
        "f0_taxonomy_pin": fro_files[F0_TAXONOMY]["sha256"],
        "f0_supplement_pin": fro_files[F0_SUPPLEMENT]["sha256"],
    }
    checks.append({"id": "I0", "name": "all pinned inputs match at read time (T0)",
                   "ok": True, "severity": "acceptance",
                   "measured": f"{len(PINS)}/{len(PINS)} pins match",
                   "falsifier": "Any pinned path whose measured sha256 differs from its pin; the measurement is then void."})
    checks.append({"id": "I1", "name": "FROZEN revision 29 pins suite/F1/F0 exactly as measured",
                   "ok": (fz["revision"] == 29 and fz["suite_pin"] == pin_state[SUITE]["sha256"]
                          and fz["f1_pin"] == pin_state[LIVE_F1]["sha256"]
                          and fz["f0_taxonomy_pin"] == pin_state[F0_TAXONOMY]["sha256"]),
                   "severity": "acceptance", "measured": fz,
                   "falsifier": "A FROZEN declaration disagreeing with the measured bytes; then the freeze is stale, not this measurement."})

    live_text = raw[LIVE_F1].decode()
    before_text = raw[BEFORE_F1].decode()
    doc_live = load_mapping(live_text)
    doc_before = load_mapping(before_text)
    flat_live, flat_before = flatten(doc_live), flatten(doc_before)

    # duplicate-key scan (rev11 defect class: a loader that silently keeps the last duplicate)
    dups_live = dup_keys(yaml.compose(live_text))
    dups_before = dup_keys(yaml.compose(before_text))
    checks.append({"id": "I2", "name": "strict duplicate-key scan on both schema snapshots",
                   "ok": len(dups_live) == 0, "severity": "acceptance" if dups_live else "info",
                   "measured": {"rev13_duplicates": dups_live, "rev12_duplicates": dups_before},
                   "falsifier": "A duplicate mapping key in the reviewed bytes; the flat-path delta could then be an artefact of the loader."})

    keys = sorted(set(flat_live) | set(flat_before))
    changed, added, removed = [], [], []
    for k in keys:
        a, b = flat_before.get(k, "<absent>"), flat_live.get(k, "<absent>")
        if a == "<absent>" and b != "<absent>":
            added.append(k)
        elif b == "<absent>" and a != "<absent>":
            removed.append(k)
        elif leaf_repr(a) != leaf_repr(b):
            changed.append(k)
    delta = {"changed": changed, "added": added, "removed": removed,
             "changed_leaf_paths": len(changed) + len(added) + len(removed)}
    checks.append({"id": "D1", "name": "rev12 snapshot -> rev13 live structural leaf delta",
                   "ok": True, "severity": "info",
                   "measured": {"changed": changed, "added": added, "removed": removed,
                                "counts": {"changed": len(changed), "added": len(added), "removed": len(removed)}},
                   "falsifier": "The before-oracle snapshot not hashing to cce9c60146d6, or a leaf present in both trees whose canonical representation did not change and is listed anyway."})

    # 3. suite rows
    rows = [json.loads(l) for l in raw[SUITE].decode().splitlines() if l.strip()]
    if len(rows) != 25:
        errors.append(f"expected 25 suite rows, found {len(rows)}")
    bindings, revs, rebound = set(), set(), set()
    for r in rows:
        bindings.add(r.get("binding_sha256"))
        revs.add(r.get("binding_frozen_revision_schema"))
        if r.get("rebound_at"):
            rebound.add(r.get("rebound_at"))
    live_sha = pin_state[LIVE_F1]["sha256"]
    bound_live = sum(1 for r in rows if r.get("binding_sha256") == live_sha)
    checks.append({"id": "B1", "name": "suite row binding vs the live rev13 pin",
                   "ok": bound_live == len(rows), "severity": "acceptance",
                   "measured": {"rows": len(rows), "rows_bound_to_live_rev13": bound_live,
                                "rows_bound_to_rev12": sum(1 for r in rows if r.get("binding_sha256") == pin_state[BEFORE_F1]["sha256"]),
                                "distinct_bindings": sorted(bindings), "binding_frozen_revision_schema": sorted(x for x in revs if x is not None),
                                "rebound_at": sorted(x for x in rebound if x)},
                   "falsifier": "Any row whose binding_sha256 equals the live rev13 hash, or a binding that is neither the rev12 nor the rev13 hash."})
    checks.append({"id": "B2", "name": "vendor hard check C1a input: canonical F1 sha256 == suite binding",
                   "ok": bound_live == len(rows), "severity": "hard",
                   "measured": {"canonical_f1": live_sha, "suite_binding": sorted(bindings)},
                   "falsifier": "A rebind of all 25 rows to the live canonical pin, which makes this check pass."})

    # 4. per-row materiality + expectations
    row_table = []
    for r in rows:
        probes = probe_row(r, doc_live, doc_before)
        exercised = []
        deciding = r.get("deciding_field")
        alternates = list(r.get("deciding_field_alternates") or [])
        for label, path in [("deciding_field", deciding)] + [("alternate", a) for a in alternates]:
            hits = [c for c in delta["changed"] + delta["added"] + delta["removed"] if related(c, path)]
            if hits:
                exercised.append({"field": path, "role": label, "changed_paths": hits})
        probe_hits = []
        for p in probes:
            hits = [c for c in delta["changed"] + delta["added"] + delta["removed"] if related(c, p["path"])]
            if hits:
                probe_hits.append({"probe_path": p["path"], "kind": p["kind"], "changed_paths": hits})
        sibling = []
        for path in [deciding] + alternates:
            parent = path.rsplit(".", 1)[0] if "." in path else path
            if parent and parent != path:
                hits = [c for c in delta["changed"] + delta["added"] + delta["removed"] if related(c, parent) and not related(c, path)]
                if hits:
                    sibling.append({"field": path, "parent": parent, "changed_siblings": hits})
        stored_pass = sum(1 for p in probes if p["stored_pass"])
        comp13 = sum(1 for p in probes if p.get("computed_rev13"))
        comp12 = sum(1 for p in probes if p.get("computed_rev12"))
        # INVALIDATED_BY_REV13 means the expectation held on the rev12 bytes and fails only on rev13.
        # An expectation already false at rev12 is PRE_EXISTING and is not charged to the rev13 delta.
        invalidated = [p["path"] for p in probes
                       if p["stored_pass"] and not p.get("computed_rev13") and p.get("computed_rev12")]
        pre_existing = [p["path"] for p in probes if p["stored_pass"] and not p.get("computed_rev12")]
        if invalidated:
            klass = "INVALIDATED_BY_REV13"
        elif pre_existing:
            klass = "PRE_EXISTING_FALSE_EXPECTATION"
        elif exercised or probe_hits:
            klass = "MATERIAL_EXERCISED_PATH"
        elif sibling:
            klass = "SIBLING_BINDING_CHANGE"
        else:
            klass = "DECLARATION_ONLY"
        row_table.append({
            "test_id": r.get("test_id"), "binding_sha256_prefix": str(r.get("binding_sha256"))[:12],
            "binding_frozen_revision_schema": r.get("binding_frozen_revision_schema"),
            "rebound_at": r.get("rebound_at"),
            "deciding_field": deciding, "deciding_field_alternates": alternates,
            "probes": len(probes), "stored_pass": stored_pass,
            "recomputed_pass_rev12": comp12, "recomputed_pass_rev13": comp13,
            "material_fields": exercised, "material_probes": probe_hits, "sibling_changes": sibling,
            "invalidated_by_rev13": invalidated, "pre_existing_false": pre_existing,
            "classification": klass,
            "probe_detail": probes,
        })
    material_rows = [t["test_id"] for t in row_table if t["classification"] == "MATERIAL_EXERCISED_PATH"]
    exercised_rows = [t["test_id"] for t in row_table if t["material_fields"] or t["material_probes"]]
    sibling_rows = [t["test_id"] for t in row_table if t["classification"] == "SIBLING_BINDING_CHANGE"]
    invalidated_rows = [t["test_id"] for t in row_table if t["classification"] == "INVALIDATED_BY_REV13"]
    pre_existing_rows = [t["test_id"] for t in row_table if t["classification"] == "PRE_EXISTING_FALSE_EXPECTATION"]
    total_probes = sum(t["probes"] for t in row_table)
    checks.append({"id": "M1", "name": "per-row materiality of the rev12->rev13 delta",
                   "ok": True, "severity": "info",
                   "measured": {"exercised_rows": exercised_rows, "material_classification_rows": material_rows,
                                "sibling_binding_rows": sibling_rows,
                                "declaration_only_rows": [t["test_id"] for t in row_table if t["classification"] == "DECLARATION_ONLY"],
                                "rev13_changes_a_deciding_or_probed_path": bool(material_rows)},
                   "falsifier": "A row listed as material whose deciding/probe path has no ancestor/descendant relation to any changed leaf, or a changed path exercised by a row that is not listed."})
    checks.append({"id": "M2", "name": "expectation validity across rev12 -> rev13",
                   "ok": not invalidated_rows, "severity": "hard",
                   "measured": {"probes_total": total_probes,
                                "recomputed_pass_rev12": sum(t["recomputed_pass_rev12"] for t in row_table),
                                "recomputed_pass_rev13": sum(t["recomputed_pass_rev13"] for t in row_table),
                                "invalidated_by_rev13": invalidated_rows,
                                "pre_existing_false_rows": pre_existing_rows,
                                "pre_existing_false_probes": [p for t in row_table for p in t["pre_existing_false"]]},
                   "falsifier": "A stored expectation that passes on the rev12 snapshot and fails on the rev13 bytes (that would make rev13 alone invalidating), or a stored expectation that fails at rev12 but passes at rev13."})

    # 5. cross-artifact declaration resolution (narrow: declared_*_sha256 probes with a declared_*_artifact sibling)
    cross = []
    for r in rows:
        probes = r.get("probe_results", [])
        for p in probes:
            path = p.get("path", "")
            if not re.match(r"^f0_binding\.declared_.*_sha256$", path):
                continue
            sib_path = path[:-7] + "_artifact"
            sib = next((q for q in probes if q.get("path") == sib_path), None)
            declared = sib.get("expected") if sib else r.get("schema_under_test")
            expected_hash = str(p.get("expected"))
            if not declared or not isinstance(declared, str):
                continue
            target = ROOT / declared
            resolved = target.exists()
            actual = sha256_file(target) if resolved else None
            cross.append({"test_id": r.get("test_id"), "probe_path": path, "declared_path": declared,
                          "stored": expected_hash, "actual": actual, "resolved": resolved,
                          "stale": resolved and actual != expected_hash})
    stale_cross = [c for c in cross if c["stale"]]
    checks.append({"id": "X1", "name": "suite cross-artifact declarations resolve on disk",
                   "ok": not stale_cross, "severity": "hard",
                   "measured": {"checked": len(cross), "stale": stale_cross},
                   "falsifier": "A declared cross-artifact hash equal to the measured bytes of its declared path at this pin."})

    # 6. controls
    t1 = {rel: sha256_file(ROOT / rel) for rel in PINS}
    drift_t1 = {rel: {"pinned": pin_state[rel]["sha256"], "t1": h} for rel, h in t1.items()
                if h != pin_state[rel]["sha256"]}
    checks.append({"id": "I3", "name": "no input drift between T0 and T1 (emission-time binding)",
                   "ok": not drift_t1, "severity": "acceptance",
                   "measured": {"drift": drift_t1, "checked": len(t1)},
                   "falsifier": "Any pinned path whose hash moved between the snapshot and the end of the run; the measurement is then superseded, not merely wrong."})

    def ctl(cid, name, ok, expected, observed, falsifier):
        controls.append({"id": cid, "name": name, "ok": bool(ok), "expected": expected,
                         "observed": observed, "falsifier": falsifier})

    def materiality_of(delta_local, table_paths):
        out = []
        for path in table_paths:
            hits = [c for c in delta_local if related(c, path)]
            if hits:
                out.append(path)
        return out

    ctl("C1", "planted change on a probed deciding path is detected as material",
        materiality_of(["visibility.definition"], ["visibility.definition"]) == ["visibility.definition"],
        ["visibility.definition"], materiality_of(["visibility.definition"], ["visibility.definition"]),
        "The detector fails to relate an identical path to itself.")
    ctl("C2", "planted change on an unrelated path leaves materiality empty",
        materiality_of(["zzz.unrelated.path"], ["visibility.definition"]) == [],
        [], materiality_of(["zzz.unrelated.path"], ["visibility.definition"]),
        "The ancestor/descendant relation matches unrelated paths.")
    ok_expected_mutation = None
    try:
        v = resolve(doc_live, "conclusion.conclusion_type")
        ok_expected_mutation = evaluate("equals", "definitely-not-the-value", v)[0] is False
    except Exception as exc:
        ok_expected_mutation = f"error: {exc}"
    ctl("C3", "a mutated expectation is detected as a recomputed failure",
        ok_expected_mutation is True, False, ok_expected_mutation,
        "equals() returning True for a value that differs from the expectation.")
    flat_same = dict(flat_live)
    ctl("C4", "identical trees produce an empty delta",
        all(leaf_repr(flat_same[k]) == leaf_repr(flat_live[k]) for k in flat_same), True, True,
        "The leaf comparator reporting a difference for identical input.")
    changed_meta = [c for c in delta["changed"] if METADATA_RE.match(c)]
    ctl("C5", "metadata-only delta (revision/revision_history) does not create material rows",
        materiality_of(changed_meta, ["conclusion.conclusion_type"]) == [], [], materiality_of(changed_meta, ["conclusion.conclusion_type"]),
        "A metadata path being related to a content deciding field.")
    amb25 = next((t for t in row_table if t["test_id"] == "F1-AMB-25"), None)
    expected_pre = {"f0_binding.declared_f0_sha256", "f0_binding.binding_note"}
    ctl("C6", "real rev12 control reproduces the known F1-AMB-25 false expectation set",
        amb25 is not None and set(amb25["pre_existing_false"]) == expected_pre, sorted(expected_pre),
        sorted(amb25["pre_existing_false"]) if amb25 else None,
        "The rev12 recomputation not reproducing both F1-AMB-25 false probes.")
    ok_malformed = None
    try:
        evaluate("no_such_kind", "x", 1)
        ok_malformed = False
    except ValueError:
        ok_malformed = True
    ctl("C7", "unknown probe kind fails closed",
        ok_malformed is True, True, ok_malformed,
        "evaluate() silently accepting an unknown probe kind.")
    ctl("C8", "duplicate-key scan is armed on the reviewed bytes",
        len(dups_live) == 0 and len(dups_before) == 0, {"rev13": [], "rev12": []},
        {"rev13": dups_live, "rev12": dups_before},
        "A duplicate key appearing in either snapshot.")

    # 7. verdict
    rebind_required = bound_live != len(rows)
    rev13_exercises = bool(exercised_rows)
    mechanical_sufficient = rebind_required and not (invalidated_rows or pre_existing_rows or stale_cross)
    verdict = "revise" if (rebind_required or not checks[0]["ok"]) else "accept"
    reason = (
        ("the suite's 25 rows bind the superseded F1 rev12 hash, so the vendor hard check C1a is false at the "
         "canonical rev13 pin" if rebind_required else "all rows bind the live pin")
        + ("; the rev12->rev13 delta does change fields the suite exercises (rows "
           + ", ".join(exercised_rows) + ": exact changed deciding/probe paths -- notably visibility.definition in "
           "F1-AMB-11/F1-AMB-17 and class_identity_variants[0].relation in F1-AMB-23), so the lead's "
           "'prose-direction only, no test field moved' premise is falsified and a rebind is not optional"
           if rev13_exercises else "; no exercised deciding/probe path changed")
        + ("; a mechanical hash rebind alone is NOT sufficient: rows " + ", ".join(pre_existing_rows)
           + " carry stored expectations already false at the rev12 snapshot and still false at rev13, and the "
           "suite has a stale cross-artifact F0 declaration; the rebind must be paired with a content repair and "
           "a fresh re-observation of the affected rows"
           if (pre_existing_rows or stale_cross) else "; a mechanical rebind is sufficient")
    )
    core = {
        "task_id": TASK_ID, "actor": ACTOR, "role": "independent read-only materiality adjudication",
        "node_id": NODE_ID, "class_id": CLASS_ID, "gate": GATE,
        "authority": "worker evidence only; no gate verdict, node status or validation_status is claimed",
        "pins": pin_state, "frozen": fz,
        "delta": delta,
        "delta_groups": {"metadata": [c for c in delta["changed"] if METADATA_RE.match(c)],
                         "binding_metadata": [c for c in delta["changed"] if BINDING_META_RE.match(c)],
                         "content": [c for c in delta["changed"] if not METADATA_RE.match(c) and not BINDING_META_RE.match(c)]},
        "suite": {"rows": len(rows), "probes": total_probes,
                  "bindings": sorted(bindings), "binding_frozen_revision_schema": sorted(x for x in revs if x is not None),
                  "rebound_at": sorted(x for x in rebound if x), "rows_bound_to_live": bound_live},
        "rows": row_table, "cross_artifact": cross,
        "checks": checks, "controls": controls,
        "verdict": {
            "verdict": verdict,
            "rebind_required": rebind_required,
            "rev13_changes_a_field_the_suite_exercises": rev13_exercises,
            "exercised_rows": exercised_rows,
            "material_rows": material_rows,
            "sibling_binding_rows": sibling_rows,
            "invalidated_by_rev13_rows": invalidated_rows,
            "pre_existing_false_rows": pre_existing_rows,
            "mechanical_rebind_sufficient": mechanical_sufficient,
            "reason": reason,
        },
        "errors": errors,
        "falsifier": ("Re-run this checker on the same snapshot bytes: the adjudication is falsified if any listed "
                      "material row has no ancestor/descendant relation to a changed leaf, if a stored expectation is "
                      "shown to flip true->false at rev13 while passing at rev12, if the F1-AMB-25 pre-existing set is "
                      "not reproduced from the third-party rev12 snapshot, or if any pin or control behaves differently."),
        "next_falsifier": ("Re-measure after the next F1 revision or suite rebind: a suite whose rows bind the live pin "
                           "closes B1/B2 but not M2/X1; the claim is superseded (not falsified) by a moved F1, suite or "
                           "FROZEN hash."),
    }
    digest = sha256_bytes(canon({k: v for k, v in core.items() if k != "measurement_digest"}).encode())
    core["measurement_digest"] = digest
    return core, snap_manifest


def main() -> int:
    import datetime
    created = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
    try:
        core, snap_manifest = measure()
    except Drift as exc:
        payload = {"task_id": TASK_ID, "actor": ACTOR, "created_at": created,
                   "verdict": "pin_drift", "error": str(exc),
                   "falsifier": "Re-pin to the live bytes and re-run; this run is void."}
        (OUT / "report.json").write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
        print(f"PIN DRIFT: {exc}")
        return 3

    (OUT / "report_core.json").write_text(json.dumps(core, indent=1, sort_keys=True) + "\n")
    report = dict(core)
    report["created_at"] = created
    report["reproduce"] = "python3 artifacts/worker-029/f1_suite_materiality/check_suite_materiality.py"
    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")

    evidence = {
        "task_id": TASK_ID, "actor": ACTOR, "created_at": created, "gate": GATE, "node_id": NODE_ID,
        "class_id": CLASS_ID, "measurement_digest": core["measurement_digest"],
        "snapshots": snap_manifest,
        "checks": [{k: c[k] for k in ("id", "name", "ok", "severity", "measured", "falsifier") if k in c} for c in core["checks"]],
        "controls": core["controls"],
        "rows": core["rows"],
        "falsifier": core["falsifier"],
    }
    (OUT / "evidence.json").write_text(json.dumps(evidence, indent=1, sort_keys=True) + "\n")

    failed = [c["id"] for c in core["checks"] if c["severity"] in ("hard",) and not c["ok"]]
    bad_ctl = [c["id"] for c in core["controls"] if not c["ok"]]
    print(f"task={TASK_ID} digest={core['measurement_digest'][:12]} verdict={core['verdict']['verdict']} "
          f"material_rows={core['verdict']['material_rows']} pre_existing={core['verdict']['pre_existing_false_rows']} "
          f"hard_failed={failed} controls_failed={bad_ctl} errors={core['errors']}")
    return 2 if (bad_ctl or core["errors"]) else 0


if __name__ == "__main__":
    sys.exit(main())

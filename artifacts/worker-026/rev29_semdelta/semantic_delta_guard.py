#!/usr/bin/env python3
"""W026-GFORM-REV29-SEMDELTA-01 — semantic-delta guard for the rev12 -> rev13 repair.

Bounded execution worker 026, class-bound to AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN /
AF-SCC-C0-VAC-GEN, node F1/F2a/F2b, gate G-FORM.

WHAT IT DOES
  Projects the three class schemas (YAML) and schemas/taxonomy_cases.jsonl (JSONL)
  into a flat {leaf-path: value} map at pinned sha256, then diffs a candidate
  revision against that baseline and classifies every changed leaf as:

    ITEM_1  a taxonomy_cases row <-> F0 rev5 binding refresh (assignment item 1)
    ITEM_2  f0_binding.consistency_evidence_sha256 / checked_at refresh (item 2)
    ITEM_3  the F1 variant SET strictness assertion direction (item 3)
    METADATA  revision/supersedes/revision_history/review_status bookkeeping
    UNDECLARED  anything else -> the assignment's own falsifier:
                "Any change to a class definition, hypothesis, conclusion predicate
                 or axis semantics" falsifies the repair.

  The four declared repair items are the only allowed byte-moving changes. A
  repair that also edits a hypothesis, a conclusion predicate, an axis vector or a
  class id produces UNDECLARED deltas and this guard says so with exact paths and
  before/after values.

  It is a MEASUREMENT instrument, not a review verdict and not a gate verdict.
  It cannot decide whether the item-3 mathematics is right; it only proves that
  nothing OTHER than the declared paths moved. The mathematical check for item 3
  is worker-076's instrument.

USAGE
  python3 semantic_delta_guard.py --make-baseline --out baseline_rev12.json
  python3 semantic_delta_guard.py --selftest --out report.json
  python3 semantic_delta_guard.py --baseline baseline_rev12.json --out report.json
  # after the repair lands:
  python3 semantic_delta_guard.py --baseline baseline_rev12.json \
      --declared rev29_pins.json --out report_rev13.json

EXIT CODES
  0 = zero UNDECLARED deltas at a stable pin set
  1 = UNDECLARED deltas found (repair falsified)
  2 = input pin moved mid-run, strict-parse failure, or usage error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("PyYAML required", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[3]

SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
MIRRORS = {k: "artifacts/formulation/" + v for k, v in SCHEMAS.items()}
CASES = "schemas/taxonomy_cases.jsonl"
FALS = "schemas/f1_falsifier_tests.jsonl"
F0 = "research_map/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
RULE_SPEC = "artifacts/formulation/rule_spec.json"
VOCAB = "artifacts/formulation/VOCAB_ALIASES.json"

# Pins as measured by worker-026 at 2026-09-12T00:53+08:00 (rev12 / FROZEN rev28).
DECLARED_PINS = {
    "F0": "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    "F1": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "F2a": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "F2b": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "taxonomy_cases": "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03",
    "f1_falsifier_tests": "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    "FROZEN": "2f358f6722d920621a66c0259cb48d35a5e3c1b706f28adf37ed467325fcedf1",
    "rule_spec": "40f9bb9e657b2c6b0cce04a9c05e9cdbf18083669060727a8e31d83031f5901e",
    "VOCAB_ALIASES": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
}

# --- classification rules -------------------------------------------------
# Only these leaf paths may move without an UNDECLARED flag.
METADATA_PREFIXES = (
    "revision", "supersedes", "timestamp_provenance", "revised_at",
    "revision_history", "review_status", "review_history",
)
ITEM_2_PREFIXES = (
    "f0_binding.consistency_evidence_sha256", "f0_binding.checked_at",
    "f0_binding.consistency_evidence", "f0_binding.binding_note",
)
ITEM_3_PREFIXES_F1 = (
    "quantifiers.domains.D5.definition",
    "visibility.definition",
    "class_identity_variants[0].relation",
    "class_identity_variants[0].statement",
    "class_identity_variants[0].falsifier",
    "class_identity_variants[0].why_separate",
    "class_identity_variants[0].note",
)
ITEM_1_PREFIXES = ("taxonomy_ref", "binding_status", "rebind_note", "meta")
# f1_falsifier_tests.jsonl rows must rebind when the F1 pin moves (repair item 3
# consequence). Any other row edit is UNDECLARED.
FALS_BINDING_PREFIXES = ("binding_sha256", "binding_ref", "binding_frozen_revision",
                         "binding_frozen_revision_schema", "rebound_at", "rebind_note")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --- strict YAML / JSON parsers -------------------------------------------
class StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (silent last-wins is a defect)."""


def _strict_mapping(loader: StrictLoader, node, deep=False):  # noqa: ANN001
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"duplicate key {key!r}", key_node.start_mark)
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_mapping)


class DuplicateKeyError(ValueError):
    pass


def _no_dup_pairs(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise DuplicateKeyError(f"duplicate JSON key {k!r}")
        seen.add(k)
    return dict(pairs)


def load_yaml_strict(p: Path):
    return yaml.load(p.read_text(), Loader=StrictLoader)


def load_jsonl_strict(p: Path):
    rows = []
    for i, line in enumerate(p.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line, object_pairs_hook=_no_dup_pairs))
        except DuplicateKeyError as e:
            raise DuplicateKeyError(f"{p.name}:{i}: {e}") from None
    return rows


# --- projection -----------------------------------------------------------
def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            out.update(flatten(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def project_file(rel: str, root: Path):
    """Return {sha256, kind, leaves} for one pinned file (no writes)."""
    p = root / rel
    text_hash = sha256_file(p)
    if rel.endswith(".jsonl"):
        rows = load_jsonl_strict(p)
        leaves = {}
        for i, row in enumerate(rows):
            key = row.get("case_id") or ("__meta__" if row.get("record_type") == "meta"
                                         else f"__row{i}__")
            leaves.update(flatten(row, f"rows.{key}"))
        return {"sha256": text_hash, "kind": "jsonl", "leaves": leaves,
                "n_rows": len(rows)}
    data = load_yaml_strict(p)
    return {"sha256": text_hash, "kind": "yaml", "leaves": flatten(data)}


def classify(rel: str, path: str) -> str:
    # JSONL projections carry a `rows.<key>.` prefix; strip it so the same
    # path rules apply to schema leaves and case-row leaves.
    if rel == CASES and path.startswith("rows."):
        parts = path.split(".")
        path = ".".join(parts[2:]) if len(parts) > 2 else path
    if rel == SCHEMAS["F1"] and any(path == p or path.startswith(p + ".") or path.startswith(p + "[")
                                     for p in ITEM_3_PREFIXES_F1):
        return "ITEM_3"
    if any(path == p or path.startswith(p + ".") or path.startswith(p + "[")
           for p in ITEM_2_PREFIXES):
        return "ITEM_2"
    if rel == CASES and any(path == p or path.startswith(p + ".") or path.startswith(p + "[")
                            for p in ITEM_1_PREFIXES):
        return "ITEM_1"
    if rel == FALS and any(path == p or path.startswith(p + ".") or path.startswith(p + "[")
                           for p in FALS_BINDING_PREFIXES):
        return "ITEM_3"
    if any(path == p or path.startswith(p + ".") or path.startswith(p + "[")
           for p in METADATA_PREFIXES):
        return "METADATA"
    return "UNDECLARED"


def diff_projections(base, cand, rel):
    """Changed/added/removed leaf paths between two projections."""
    b, c = base["leaves"], cand["leaves"]
    changed = []
    for path in sorted(set(b) | set(c)):
        if path not in b:
            changed.append({"path": path, "kind": "added",
                            "new": c[path], "old": None})
        elif path not in c:
            changed.append({"path": path, "kind": "removed",
                            "old": b[path], "new": None})
        elif b[path] != c[path]:
            changed.append({"path": path, "kind": "changed",
                            "old": b[path], "new": c[path]})
    for item in changed:
        item["class"] = classify(rel, item["path"])
    return changed


# --- baseline / check -----------------------------------------------------
def make_baseline(root: Path):
    files = {rel: project_file(rel, root)
             for rel in list(SCHEMAS.values()) + [CASES, FALS]}
    pin_files = {"F0": F0, "F1": SCHEMAS["F1"], "F2a": SCHEMAS["F2a"],
                 "F2b": SCHEMAS["F2b"], "taxonomy_cases": CASES,
                 "f1_falsifier_tests": FALS, "FROZEN": FROZEN,
                 "rule_spec": RULE_SPEC, "VOCAB_ALIASES": VOCAB}
    pin_files.update({f"mirror_{k}": v for k, v in MIRRORS.items()})
    return {
        "instrument": "W026-GFORM-REV29-SEMDELTA-01",
        "actor": "worker-026",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rev": "rev12 / FROZEN rev28 (pre astra-life05-evidence-binding-repair)",
        "declared_pins": DECLARED_PINS,
        "pin_files": pin_files,
        "measured_pins": {k: sha256_file(root / v) for k, v in pin_files.items()
                          if (root / v).exists()},
        "files": files,
    }


def _first_sentence(text: str) -> str:
    """Logical-content extractor: for an 'iff' predicate keep the head and the
    'iff' clause up to its closing period; otherwise the first sentence."""
    t = str(text)
    if " iff " in t:
        head, tail = t.split(" iff ", 1)
        return head + " iff " + tail.split(".")[0]
    return t.split(".")[0]


def _item3_text_checks(baseline, candidate_deltas):
    out = {}
    for d in candidate_deltas:
        if d["class"] != "ITEM_3" or d["kind"] != "changed":
            continue
        old, new = _first_sentence(d["old"]), _first_sentence(d["new"])
        out[d["path"]] = {
            "old_first_sentence": old,
            "new_first_sentence": new,
            "first_sentence_unchanged": old == new,
        }
    return out


def _aux_checks(root: Path, measured, declared):
    """Mirror alignment, stale falsifier bindings, FROZEN declared-vs-measured."""
    mirrors = {}
    for k, mrel in MIRRORS.items():
        c, m = root / SCHEMAS[k], root / mrel
        mirrors[k] = {
            "canonical": SCHEMAS[k], "canonical_sha256": measured[k],
            "mirror": mrel, "mirror_sha256": sha256_file(m) if m.exists() else None,
            "aligned": m.exists() and sha256_file(m) == measured[k],
        }
    fals = project_file(FALS, root)
    stale = {}
    for path, val in fals["leaves"].items():
        if path.endswith(".binding_sha256") and isinstance(val, str):
            stale.setdefault(val, []).append(path)
    falsifier_binding = {
        "file": FALS, "sha256": fals["sha256"], "n_rows": fals.get("n_rows"),
        "current_F1_sha256": measured["F1"],
        "stale_binding_values": {k: len(v) for k, v in stale.items()
                                 if k != measured["F1"]},
        "rows_binding_current_F1": sum(len(v) for k, v in stale.items()
                                       if k == measured["F1"]),
        "ok": all(k == measured["F1"] for k in stale),
    }
    frozen = json.loads((root / FROZEN).read_text())
    frozen_files = frozen.get("files", {})
    frozen_check = {}
    for rel in [SCHEMAS["F1"], SCHEMAS["F2a"], SCHEMAS["F2b"], CASES, FALS]:
        entry = frozen_files.get(rel, {})
        frozen_check[rel] = {
            "declared_in_FROZEN": entry.get("sha256"),
            "measured": sha256_file(root / rel),
            "match": entry.get("sha256") == sha256_file(root / rel),
        }
    return {
        "mirror_alignment": mirrors,
        "falsifier_binding": falsifier_binding,
        "frozen_declared_vs_measured": {
            "frozen_revision": frozen.get("revision"),
            "frozen_sha256": sha256_file(root / FROZEN),
            "entries": frozen_check,
            "all_listed_paths_match": all(v["match"] for v in frozen_check.values()),
        },
    }


def check(root: Path, baseline, declared=None):
    declared = declared or baseline["declared_pins"]
    measured = {k: sha256_file(root / v) for k, v in
                {"F0": F0, "F1": SCHEMAS["F1"], "F2a": SCHEMAS["F2a"],
                 "F2b": SCHEMAS["F2b"], "taxonomy_cases": CASES,
                 "f1_falsifier_tests": FALS, "FROZEN": FROZEN,
                 "rule_spec": RULE_SPEC, "VOCAB_ALIASES": VOCAB}.items()}
    changed_since_baseline = {k: {"baseline": baseline["measured_pins"].get(k),
                                  "now": measured[k]}
                              for k in measured
                              if baseline["measured_pins"].get(k) != measured[k]}
    pin_conflicts = {k: {"declared": declared.get(k), "measured": measured[k]}
                     for k in measured if declared.get(k) != measured[k]}

    per_file, totals = {}, {"ITEM_1": 0, "ITEM_2": 0, "ITEM_3": 0,
                            "METADATA": 0, "UNDECLARED": 0}
    for rel in list(SCHEMAS.values()) + [CASES, FALS]:
        cand = project_file(rel, root)
        deltas = diff_projections(baseline["files"][rel], cand, rel)
        for d in deltas:
            totals[d["class"]] += 1
        per_file[rel] = {
            "baseline_sha256": baseline["files"][rel]["sha256"],
            "candidate_sha256": cand["sha256"],
            "n_deltas": len(deltas),
            "deltas": deltas,
        }
    undeclared = [d for rel in per_file for d in per_file[rel]["deltas"]
                  if d["class"] == "UNDECLARED"]
    verdict = ("ZERO_UNDECLARED_SEMANTIC_DELTA" if not undeclared
               else "UNDECLARED_SEMANTIC_DELTA_FOUND")
    aux = _aux_checks(root, measured, declared)
    item3_deltas = [d for rel in per_file for d in per_file[rel]["deltas"]
                    if d["class"] == "ITEM_3"]
    aux["item3_text_checks"] = _item3_text_checks(baseline, item3_deltas)
    # The visibility/D5 predicate clause must NOT move even though the
    # explanatory strictness sentence around it is the declared repair target.
    aux["item3_predicate_sentences_preserved"] = all(
        v["first_sentence_unchanged"]
        for k, v in aux["item3_text_checks"].items()
        if k in ("visibility.definition", "quantifiers.domains.D5.definition")
    )
    return {
        "verdict": verdict,
        "totals": totals,
        "undeclared": undeclared,
        "pin_changes_since_baseline": changed_since_baseline,
        "pin_conflicts_vs_declared": pin_conflicts,
        "aux": aux,
        "files": per_file,
    }


# --- controls -------------------------------------------------------------
def _sandbox(root: Path, rels):
    tmp = Path(tempfile.mkdtemp(prefix="w026_semdelta_"))
    extra = [F0, FROZEN, RULE_SPEC, VOCAB, FALS] + list(MIRRORS.values())
    for rel in list(dict.fromkeys(list(rels) + extra)):
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, dst)
    return tmp


def _read_yaml(p: Path):
    return yaml.load(p.read_text(), Loader=StrictLoader)


def _write_yaml(p: Path, data):
    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def run_selftest(root: Path):
    base = make_baseline(root)
    rels = list(SCHEMAS.values()) + [CASES, FALS]
    controls = []

    def record(cid, desc, ok, detail):
        controls.append({"id": cid, "desc": desc, "ok": bool(ok),
                         "detail": detail})

    # C1 determinism: two projections byte-identical
    a = project_file(SCHEMAS["F1"], root)["leaves"]
    b = project_file(SCHEMAS["F1"], root)["leaves"]
    record("C1", "projection is deterministic", a == b,
           f"{len(a)} leaves, equal={a == b}")

    # C2 live bytes vs baseline -> zero undeclared
    live = check(root, base)
    record("C2", "live rev12 bytes vs baseline -> zero undeclared",
           live["verdict"] == "ZERO_UNDECLARED_SEMANTIC_DELTA",
           f"verdict={live['verdict']} totals={live['totals']}")

    # C3 mechanism: reorder YAML keys -> no semantic delta
    sb = _sandbox(root, rels)
    d = _read_yaml(sb / SCHEMAS["F1"])
    _write_yaml(sb / SCHEMAS["F1"], {k: d[k] for k in reversed(list(d))})
    r = check(sb, base)
    record("C3", "top-level key reorder is not a semantic delta",
           r["verdict"] == "ZERO_UNDECLARED_SEMANTIC_DELTA",
           f"undeclared={len(r['undeclared'])}")

    # C4 mutation: conclusion_type change -> UNDECLARED
    sb = _sandbox(root, rels)
    d = _read_yaml(sb / SCHEMAS["F1"])
    d["conclusion"]["conclusion_type"] = "strong_cosmic_censorship_C2"
    _write_yaml(sb / SCHEMAS["F1"], d)
    r = check(sb, base)
    hit = any("conclusion_type" in x["path"] for x in r["undeclared"])
    record("C4", "conclusion_type mutation -> UNDECLARED", hit,
           f"undeclared={[x['path'] for x in r['undeclared']][:4]}")

    # C5 mutation: class scope statement edit -> UNDECLARED
    sb = _sandbox(root, rels)
    d = _read_yaml(sb / SCHEMAS["F2a"])
    d["scope_statement"] = d["scope_statement"] + " EDITED"
    _write_yaml(sb / SCHEMAS["F2a"], d)
    r = check(sb, base)
    hit = any("scope_statement" in x["path"] for x in r["undeclared"])
    record("C5", "class scope_statement mutation -> UNDECLARED", hit,
           f"undeclared={[x['path'] for x in r['undeclared']][:4]}")

    # C6 declared item 2: refresh consistency pin -> ITEM_2 only
    sb = _sandbox(root, rels)
    d = _read_yaml(sb / SCHEMAS["F2b"])
    d["f0_binding"]["consistency_evidence_sha256"] = "f" * 64
    d["f0_binding"]["checked_at"] = "2026-09-12T01:40:00+08:00"
    _write_yaml(sb / SCHEMAS["F2b"], d)
    r = check(sb, base)
    record("C6", "declared item-2 refresh -> ITEM_2, zero undeclared",
           r["verdict"] == "ZERO_UNDECLARED_SEMANTIC_DELTA" and r["totals"]["ITEM_2"] == 2,
           f"totals={r['totals']}")

    # C7 declared item 3: F1 strictness text edit -> ITEM_3 only
    sb = _sandbox(root, rels)
    d = _read_yaml(sb / SCHEMAS["F1"])
    d["quantifiers"]["domains"]["D5"]["definition"] = "corrected strictness sentence"
    d["class_identity_variants"][0]["relation"] = "corrected direction sentence"
    _write_yaml(sb / SCHEMAS["F1"], d)
    r = check(sb, base)
    record("C7", "declared item-3 strictness edit -> ITEM_3, zero undeclared",
           r["verdict"] == "ZERO_UNDECLARED_SEMANTIC_DELTA" and r["totals"]["ITEM_3"] >= 2,
           f"totals={r['totals']}")

    # C8 declared item 1: taxonomy_cases F0 rebind -> ITEM_1 only
    sb = _sandbox(root, rels)
    p = sb / CASES
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    for row in rows:
        if row.get("record_type") == "meta":
            row["taxonomy_ref"]["rebound_at"] = "2026-09-12T01:40:00+08:00"
        else:
            row["binding_status"] = "bound_taxonomy_sha_" + "0abb9ed8a961"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    r = check(sb, base)
    n_item1 = r["totals"]["ITEM_1"]
    record("C8", "declared item-1 taxonomy_cases rebind -> ITEM_1, zero undeclared",
           r["verdict"] == "ZERO_UNDECLARED_SEMANTIC_DELTA",
           f"totals={r['totals']}")

    # C9 mutation: case statement edit -> UNDECLARED
    sb = _sandbox(root, rels)
    p = sb / CASES
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    for row in rows:
        if row.get("record_type") == "case":
            row["statement"] = row["statement"] + " EDITED"
            break
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    r = check(sb, base)
    hit = any("statement" in x["path"] for x in r["undeclared"])
    record("C9", "taxonomy_cases statement mutation -> UNDECLARED", hit,
           f"undeclared={[x['path'] for x in r['undeclared']][:3]}")

    # C10 mutation: class-component regularity change -> UNDECLARED
    sb = _sandbox(root, rels)
    d = _read_yaml(sb / SCHEMAS["F2a"])
    d["class_components"]["regularity_token"] = "C0"
    _write_yaml(sb / SCHEMAS["F2a"], d)
    r = check(sb, base)
    hit = any("regularity_token" in x["path"] for x in r["undeclared"])
    record("C10", "class-component regularity mutation -> UNDECLARED", hit,
           f"undeclared={[x['path'] for x in r['undeclared']][:3]}")

    # C11 strict parser: duplicate YAML key is rejected
    sb = _sandbox(root, rels)
    p = sb / SCHEMAS["F2a"]
    lines = p.read_text().splitlines()
    out_lines = []
    injected = False
    for ln in lines:
        out_lines.append(ln)
        if not injected and ln.startswith("revision:"):
            out_lines.append(ln)  # byte-duplicate of the revision key
            injected = True
    p.write_text("\n".join(out_lines) + "\n")
    try:
        project_file(SCHEMAS["F2a"], sb)
        ok = False
        detail = f"duplicate key accepted (BAD, injected={injected})"
    except yaml.constructor.ConstructorError as e:
        ok = "duplicate key" in str(e)
        detail = f"duplicate key rejected (injected={injected})"
    record("C11", "strict YAML parser rejects duplicate key", ok, detail)

    # C12 strict parser: duplicate JSONL key is rejected
    sb = _sandbox(root, rels)
    p = sb / CASES
    first = p.read_text().splitlines()[0]
    if '"record_type"' in first:
        bad = first.replace('"record_type"', '"record_type": "meta", "record_type"', 1)
        p.write_text(bad + "\n" + "\n".join(p.read_text().splitlines()[1:]) + "\n")
    try:
        project_file(CASES, sb)
        ok = False
        detail = "duplicate JSON key accepted (BAD)"
    except DuplicateKeyError:
        ok = True
        detail = "duplicate JSON key rejected"
    record("C12", "strict JSONL parser rejects duplicate key", ok, detail)

    shutil.rmtree(sb, ignore_errors=True)
    return controls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--baseline")
    ap.add_argument("--declared")
    ap.add_argument("--make-baseline", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(args.root).resolve()

    if args.make_baseline:
        base = make_baseline(root)
        Path(args.out).write_text(json.dumps(base, indent=1))
        print(f"baseline written to {args.out}: "
              f"{sum(len(v['leaves']) for v in base['files'].values())} leaves")
        return 0

    if args.selftest:
        controls = run_selftest(root)
        # entry/exit pin stability
        pre = make_baseline(root)["measured_pins"]
        post = make_baseline(root)["measured_pins"]
        rep = {
            "instrument": "W026-GFORM-REV29-SEMDELTA-01",
            "actor": "worker-026",
            "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
            "node_id": "F1,F2a,F2b",
            "gate": "G-FORM",
            "mode": "selftest",
            "controls": controls,
            "controls_passed": sum(c["ok"] for c in controls),
            "controls_total": len(controls),
            "pin_stability": {"entry": pre, "exit": post,
                              "drift": {k: [pre[k], post[k]] for k in pre
                                        if pre[k] != post[k]}},
        }
        Path(args.out).write_text(json.dumps(rep, indent=1))
        bad = [c["id"] for c in controls if not c["ok"]]
        print(f"selftest {rep['controls_passed']}/{rep['controls_total']} pass; "
              f"failures={bad}")
        return 0 if not bad else 1

    base = json.loads(Path(args.baseline).read_text())
    declared = json.loads(Path(args.declared).read_text()) if args.declared else None
    pin_files = base.get("pin_files") or {
        "F1": SCHEMAS["F1"], "F2a": SCHEMAS["F2a"], "F2b": SCHEMAS["F2b"],
        "taxonomy_cases": CASES, "F0": F0, "FROZEN": FROZEN}
    pre = {k: sha256_file(root / v) for k, v in pin_files.items()
           if (root / v).exists()}
    result = check(root, base, declared)
    post = {k: sha256_file(root / v) for k, v in pin_files.items()
            if (root / v).exists()}
    rep = {
        "instrument": "W026-GFORM-REV29-SEMDELTA-01",
        "actor": "worker-026",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "mode": "check",
        "pin_stability": {"entry": pre, "exit": post,
                          "drift": {k: [pre[k], post[k]] for k in pre
                                    if pre[k] != post[k]}},
        **result,
    }
    Path(args.out).write_text(json.dumps(rep, indent=1))
    print(f"{result['verdict']} totals={result['totals']} "
          f"pin_conflicts={len(result['pin_conflicts_vs_declared'])}")
    if pre != post:
        return 2
    return 0 if result["verdict"] == "ZERO_UNDECLARED_SEMANTIC_DELTA" else 1


if __name__ == "__main__":
    sys.exit(main())

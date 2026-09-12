#!/usr/bin/env python3
"""accept_f0_closure.py -- independent closure verifier for the three blocking F0 findings.

Task W087-F0-CLOSURE-CHECK-02 (bounded execution worker 087).
Node F0, gate G-F0, classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN /
AF-WCC-SCALAR-SPH.

Findings this instrument decides (all raised against canonical F0 276009f4f63d by
worker-16 B-16F0-1/2/3, worker-082 W082-F-01/02 and astra-lead-audit):

  CL1  D1 residue: the demoted set-based visibility reading must not appear as an
       assertive predicate in any class conclusion; each WCC class must carry the
       single-q TAIL predicate and no SCC class may carry a visibility predicate.
  CL2  Unsourced equivalence: no class conclusion may assert an equivalence it does
       not source (the AF-WCC-SCALAR-SPH "equivalently, ... event horizon ..." clause).
  CL3  Unresolved genericity: a class whose genericity_kind is `unresolved` must not
       use a bare "for generic data" quantifier in its conclusion; it must bind the
       deferral explicitly.
  CL4  D3 discharge: resolved_divergences[D3] claims the comeager quantifier for
       "each class"; every class must either state it or be covered by an explicit
       named deferral in D3's scope_note.
  CL5  Class-schema ownership: each class provenance.schema_owner must name the
       schema that actually declares that class (class_id -> node_id) and must not
       target a path recorded in the map's legacy_artifacts.

Regression invariants (must hold before and after any repair):
  INV1 exactly the four frozen class ids, classes keys == class_ids
  INV2 every axis legal; 6/6 disjointness pairs present with a differing decisive axis
  INV3 no duplicate YAML mapping keys anywhere in the document
  INV4 no merged C0/C2 regularity spelling in any class conclusion

Scope split:
  - class_content checks (CL1..CL5, INV1..INV4) are what a taxonomy revision can close.
  - lead_side items (CL6 publication/adjudication, CL7 downstream re-pin) are reported
    but never gate this instrument's class-content verdict.  CL6 is PENDING while the
    controller adjudicates FROZEN.json logical_artifacts / f0_mirror_adjudication_request.

Independence: this file imports only stdlib + PyYAML.  It does not import, execute or
copy artifacts/worker-16/f0_review/check_f0.py, artifacts/worker-082/**, flash-02
tooling, research_map/class_separation.py or research_map/audit_evidence.py.

Exit codes
  0  valid run, every class-content closure check CLOSED
  3  valid run, at least one class-content closure check OPEN (per-check detail in JSON)
  1  control suite failed -> result INVALID, no JSON written
  2  input drift / unparseable target / fail-closed -> no JSON written
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANONICAL = ROOT / "research_map" / "formulation_taxonomy.yaml"
PIN = "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
MAP = ROOT / "research_map" / "research_map.json"
CORPUS = ROOT / "schemas" / "taxonomy_cases.jsonl"
FIXTURES = HERE / "fixtures"

# ---------------------------------------------------------------------------
# text detectors
# ---------------------------------------------------------------------------

# Assertive set-based reading: the conclusion claims completeness of every geodesic
# contained in the whole J-(I+) set, or quantifies over the union of J-(q).
# Separators are tolerant so hyphenated rev5 spellings ("contained-in-J-(I+)") are caught.
SETBASED_RE = re.compile(
    r"contained[\s\-]+in[\s\-]*J\s*\^?\s*-?\s*\(?\s*I\s*\+|union[\s\-]+of[\s\-]+J",
    re.I,
)
# A sentence that mentions the set-based reading in order to disown / register it.
DISOWN_RE = re.compile(
    r"set-based|variant|registered|strictly stronger|not a predicate|superseded|"
    r"never be interchanged|must never|is not a predicate|not a second predicate|"
    r"not this class|is NOT this class",
    re.I,
)
EQUIV_RE = re.compile(r"\bequivalently\b|\bequivalence\b|\bis equivalent to\b", re.I)
EQUIV_DISCLAIM_RE = re.compile(
    r"not an asserted equivalence|not equivalent|does not assert|no claim of equivalence|"
    r"never be interchanged|not an equivalence",
    re.I,
)
BARE_GENERIC_RE = re.compile(r"\bfor generic data\b|\bfor a generic\b|\bgeneric data in the class\b", re.I)
TAIL_RE = re.compile(r"single-q\s+TAIL|tail\s+gamma|\bTAIL predicate\b", re.I)
COMEAGER_RE = re.compile(r"comeager", re.I)
MERGED_REG_RE = re.compile(r"C\s*[\^\{_ ]*\s*(?:0|2)\s*[\}\^ ]*\s*(?:/|or|,|and)\s*C\s*[\^\{_ ]*\s*(?:0|2)", re.I)
NODE_ARTIFACT_RE = re.compile(
    r"^(?P<node>.+?)\s*\(artifact\s+(?P<path>[^,()]+?)(?:\s*,\s*section\s+(?P<section>[^()]+?))?\)\s*$"
)


def now() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def flat(text: str) -> str:
    return " ".join(str(text).split())


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.;])\s+", flat(text)) if s.strip()]


def assertive_setbased(text: str) -> bool:
    return any(SETBASED_RE.search(s) and not DISOWN_RE.search(s) for s in sentences(text))


def asserted_equivalence(text: str) -> bool:
    return any(EQUIV_RE.search(s) and not EQUIV_DISCLAIM_RE.search(s) for s in sentences(text))


def binds_deferred_genericity(text: str) -> bool:
    low = flat(text).lower()
    return "unresolved" in low and "genericity" in low


def bare_generic_quantifier(text: str, genericity_kind: str | None) -> bool:
    if genericity_kind != "unresolved":
        return False
    return bool(BARE_GENERIC_RE.search(flat(text))) and not binds_deferred_genericity(text)


def duplicate_keys(text: str) -> list[dict]:
    """Walk composed YAML nodes and report duplicate mapping keys (heuristic-free)."""
    dups: list[dict] = []

    def walk(node, path: str) -> None:
        if isinstance(node, yaml.MappingNode):
            seen: set = set()
            for key_node, value_node in node.value:
                key = getattr(key_node, "value", None)
                if key in seen:
                    dups.append({"path": path, "key": str(key), "line": key_node.start_mark.line + 1})
                seen.add(key)
                walk(value_node, f"{path}.{key}")
        elif isinstance(node, yaml.SequenceNode):
            for i, item in enumerate(node.value):
                walk(item, f"{path}[{i}]")

    for doc in yaml.compose_all(text):
        walk(doc, "$")
    return dups


def discover_class_schemas() -> dict:
    """class_id -> {node_id, path} from the canonical class schemas on disk."""
    out: dict = {}
    for path in sorted(ROOT.glob("schemas/af_*.yaml")):
        try:
            data = yaml.safe_load(path.read_text())
        except Exception:
            continue
        if not isinstance(data, dict) or data.get("artifact_type") == "formulation_aggregator":
            continue
        cid, nid = data.get("class_id"), data.get("node_id")
        if cid and nid:
            out[cid] = {"node_id": nid, "path": rel(path)}
    return out


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

def check_invariants(data: dict, text: str) -> list[dict]:
    checks = []
    classes = data.get("classes", {})
    class_ids = data.get("class_ids", [])

    # INV1
    ok = list(classes.keys()) == list(class_ids) and len(class_ids) == 4
    checks.append({
        "id": "INV1", "scope": "regression", "title": "exactly the four frozen class ids; classes keys == class_ids",
        "status": "PASS" if ok else "FAIL",
        "detail": f"class_ids={class_ids}; classes_keys={list(classes.keys())}",
    })

    # INV2 -- class axes are the vocabulary slots instantiated on every class; other
    # vocabulary slots (e.g. genericity_topology) live in the contract schemas and are advisory here.
    vocab = data.get("field_vocabulary", {})
    axis_sets = [set((c.get("axes") or {}).keys()) for c in classes.values()]
    required_axes = set.intersection(*axis_sets) if axis_sets else set()
    advisory_absent_slots = sorted(set(vocab) - required_axes)
    axis_failures = []
    for cid, c in classes.items():
        for axis in sorted(required_axes):
            val = c["axes"][axis]
            allowed = (vocab.get(axis) or {}).get("allowed", [])
            if val not in allowed:
                axis_failures.append(f"{cid}:{axis}={val!r}")
    pairs = {}
    for row in data.get("disjointness", []):
        pair = tuple(row.get("pair", []))
        pairs[pair] = row
    axis_diff_failures = []
    for pair, row in pairs.items():
        a, b = (classes.get(pair[0], {}).get("axes", {}), classes.get(pair[1], {}).get("axes", {}))
        if not any(a.get(ax) != b.get(ax) for ax in row.get("decisive_axes", [])):
            axis_diff_failures.append(pair)
    n_pairs = len({tuple(sorted(p)) for p in pairs})
    ok = not axis_failures and not axis_diff_failures and n_pairs == 6
    checks.append({
        "id": "INV2", "scope": "regression", "title": "axes legal; 6/6 disjointness pairs with a differing decisive axis",
        "status": "PASS" if ok else "FAIL",
        "detail": f"required_axes={sorted(required_axes)}; axis_failures={axis_failures}; pairs={n_pairs}/6; "
                  f"pairs_without_differing_decisive_axis={axis_diff_failures}; "
                  f"advisory_vocabulary_slots_absent_from_class_axes={advisory_absent_slots}",
    })

    # INV3
    dups = duplicate_keys(text)
    checks.append({
        "id": "INV3", "scope": "regression", "title": "no duplicate YAML mapping keys in the document",
        "status": "PASS" if not dups else "FAIL",
        "detail": f"duplicates={dups}",
    })

    # INV4
    merged = {}
    for cid, c in classes.items():
        hits = MERGED_REG_RE.findall(flat(c.get("conclusion", {}).get("text", "")))
        if hits:
            merged[cid] = hits
    checks.append({
        "id": "INV4", "scope": "regression", "title": "no merged C0/C2 regularity spelling in a class conclusion",
        "status": "PASS" if not merged else "FAIL",
        "detail": f"merged_hits={merged}",
    })
    return checks


def check_cl1(data: dict) -> dict:
    rows = {}
    failures = []
    for cid, c in data.get("classes", {}).items():
        t = c.get("conclusion", {}).get("text", "")
        fam = (c.get("axes") or {}).get("family")
        sb = assertive_setbased(t)
        tail = bool(TAIL_RE.search(flat(t)))
        rows[cid] = {"family": fam, "assertive_set_based": sb, "tail_predicate": tail}
        if sb:
            failures.append(f"{cid}: assertive set-based reading")
        if fam == "WCC" and not tail:
            failures.append(f"{cid}: WCC class without the single-q TAIL predicate")
        if fam == "SCC" and tail:
            failures.append(f"{cid}: SCC class carries a visibility predicate")
    return {
        "id": "CL1", "scope": "class_content", "finding": "B-16F0-1a / W082-F-01(a) D1 residue",
        "title": "set-based visibility reading is not an assertive class predicate; WCC classes use the single-q TAIL predicate",
        "status": "PASS" if not failures else "FAIL",
        "detail": f"per_class={rows}; failures={failures}",
    }


def check_cl2(data: dict) -> dict:
    rows = {}
    failures = []
    for cid, c in data.get("classes", {}).items():
        t = c.get("conclusion", {}).get("text", "")
        eq = asserted_equivalence(t)
        rows[cid] = {"asserted_equivalence": eq}
        if eq:
            failures.append(cid)
    return {
        "id": "CL2", "scope": "class_content", "finding": "W082-F-01(b) unsourced equivalence",
        "title": "no class conclusion asserts an unsourced equivalence",
        "status": "PASS" if not failures else "FAIL",
        "detail": f"per_class={rows}; classes_with_asserted_equivalence={failures}",
    }


def check_cl3(data: dict) -> dict:
    rows = {}
    failures = []
    for cid, c in data.get("classes", {}).items():
        t = c.get("conclusion", {}).get("text", "")
        gk = (c.get("axes") or {}).get("genericity_kind")
        bare = bare_generic_quantifier(t, gk)
        rows[cid] = {"genericity_kind": gk, "bare_generic_quantifier": bare,
                     "binds_deferred_genericity": binds_deferred_genericity(t)}
        if bare:
            failures.append(cid)
    return {
        "id": "CL3", "scope": "class_content", "finding": "W082-F-01(a) bare generic quantifier",
        "title": "unresolved-genericity classes bind the deferral instead of using a bare generic quantifier",
        "status": "PASS" if not failures else "FAIL",
        "detail": f"per_class={rows}; bare_generic_classes={failures}",
    }


def check_cl4(data: dict) -> dict:
    adj = data.get("class_scope_adjudication", {}) or {}
    d3_rows = [d for d in adj.get("resolved_divergences", []) if d.get("id") == "D3"]
    d3 = d3_rows[0] if d3_rows else {}
    scope_note = str(d3.get("scope_note", ""))
    rows = {}
    failures = []
    for cid, c in data.get("classes", {}).items():
        t = c.get("conclusion", {}).get("text", "")
        comeager = bool(COMEAGER_RE.search(flat(t)))
        named_deferral = binds_deferred_genericity(t) and cid in scope_note
        rows[cid] = {"comeager_in_conclusion": comeager, "named_deferral_in_D3_scope_note": named_deferral}
        if not (comeager or named_deferral):
            failures.append(cid)
    return {
        "id": "CL4", "scope": "class_content", "finding": "B-16F0-2 D3 not discharged for AF-WCC-SCALAR-SPH",
        "title": "D3 comeager claim is discharged per class, or explicitly scoped as a named deferral",
        "status": "PASS" if not failures else "FAIL",
        "detail": f"d3_resolution={d3.get('resolution')!r}; d3_scope_note_present={bool(scope_note)}; "
                  f"per_class={rows}; undischarged_classes={failures}",
    }


def check_cl5(data: dict, mapd: dict) -> dict:
    discovered = discover_class_schemas()
    legacy = {row.get("path") for row in (mapd.get("legacy_artifacts") or []) if isinstance(row, dict)}
    rows = {}
    failures = []
    for cid, c in data.get("classes", {}).items():
        owner = str((c.get("provenance") or {}).get("schema_owner", ""))
        m = NODE_ARTIFACT_RE.match(owner.strip())
        expected = discovered.get(cid)
        if not m:
            if "NO F-NODE" in owner:
                rows[cid] = {"owner": owner, "status": "coverage_gap", "expected": expected}
            else:
                rows[cid] = {"owner": owner, "status": "unparseable", "expected": expected}
                failures.append(f"{cid}: unparseable schema_owner")
            continue
        node, path = m.group("node"), m.group("path").strip()
        on_disk = (ROOT / path).exists()
        is_legacy = path in legacy
        match = bool(expected) and expected["path"] == path and expected["node_id"] == node
        status = "ok" if (match and on_disk and not is_legacy) else "mismatch"
        rows[cid] = {"owner": owner, "node": node, "path": path, "exists": on_disk,
                     "in_legacy_artifacts": is_legacy, "expected": expected, "status": status}
        if status != "ok":
            failures.append(cid)
    return {
        "id": "CL5", "scope": "class_content", "finding": "B-16F0-3 schema_owner targets legacy artifact / superseded node",
        "title": "every class schema_owner names the schema that declares that class and not a legacy artifact",
        "status": "PASS" if not failures else "FAIL",
        "detail": f"discovered_class_schemas={discovered}; legacy_artifacts={sorted(x for x in legacy if x)}; "
                  f"per_class={rows}; failing_classes={failures}",
    }


def check_lead_side(data: dict, mapd: dict) -> list[dict]:
    """Reported, non-gating: publication parity/adjudication and downstream re-pin."""
    out = []
    # CL6 publication / companion-pair adjudication (map is the sole global state)
    pub = next((p for p in (mapd.get("publication_status", {}) or {}).get("pairs", [])
                if p.get("canonical") == "research_map/formulation_taxonomy.yaml"), {})
    detail = {}
    status = "PENDING"
    if pub:
        detail = {"map_pair_status": pub.get("status"), "classification": pub.get("classification"),
                  "canonical_sha256": (pub.get("canonical_sha256") or "")[:12],
                  "authoring_sha256": (pub.get("authoring_sha256") or "")[:12],
                  "note": pub.get("note")}
        if pub.get("status") in {"companion-pinned", "aligned"}:
            status = "PASS"
        elif pub.get("status") == "divergent":
            status = "FAIL"
    if status != "PASS" and FROZEN.exists():
        try:
            fz = json.loads(FROZEN.read_text())
            req = fz.get("f0_mirror_adjudication_request", {}) or {}
            detail["frozen_revision"] = fz.get("revision")
            detail["frozen_adjudication_request_status"] = req.get("status")
            if "pending" in str(req.get("status", "")):
                status = "PENDING"
        except Exception as exc:  # noqa: BLE001
            detail["frozen_error"] = str(exc)
    out.append({
        "id": "CL6", "scope": "lead_side",
        "title": "publication parity or an adjudicated companion-pair ruling",
        "status": status,
        "detail": ("map publication pair is authoritative. " + json.dumps(detail)),
        "evidence_refs": ["research_map/research_map.json#publication_status", "artifacts/formulation/FROZEN.json",
                          "artifacts/formulation/evidence/f0_mirror_conflict.json"],
    })
    # CL7 downstream re-pin
    meta_pin, bindings = None, {}
    if CORPUS.exists():
        for line in CORPUS.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if rec.get("record_type") == "meta":
                meta_pin = (rec.get("taxonomy_ref") or {}).get("sha256")
            b = rec.get("binding_status")
            if b:
                bindings[b] = bindings.get(b, 0) + 1
    canon_sha = sha256_file(CANONICAL)
    stale_meta = bool(meta_pin) and meta_pin != canon_sha
    stale_bindings = {k: v for k, v in bindings.items() if canon_sha[:12] not in k}
    out.append({
        "id": "CL7", "scope": "lead_side", "title": "downstream corpus binds the current canonical F0 hash",
        "status": "PENDING" if (stale_meta or stale_bindings) else "PASS",
        "detail": f"canonical={canon_sha[:12]}; corpus_meta_pin={(meta_pin or '')[:12]}; "
                  f"case_binding_status_histogram={bindings}; stale_binding_groups={stale_bindings}; "
                  "owner=astra-life03-repin-claims",
        "evidence_refs": ["schemas/taxonomy_cases.jsonl", "research_map/research_map.json#assignments"],
    })
    return out


# ---------------------------------------------------------------------------
# control suite (fail-closed; independent of the target under test)
# ---------------------------------------------------------------------------

def control_suite() -> list[dict]:
    ctrls: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        ctrls.append({"control": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    good = (FIXTURES / "conclusion_good_tail.txt").read_text()
    bad = (FIXTURES / "conclusion_bad_setbased.txt").read_text()
    fixed = (FIXTURES / "conclusion_fixed.txt").read_text()

    add("P1_good_tail_conclusion_not_flagged",
        not assertive_setbased(good) and not asserted_equivalence(good),
        f"set_based={assertive_setbased(good)} asserted_equivalence={asserted_equivalence(good)}")
    add("P2_bad_setbased_conclusion_flagged",
        assertive_setbased(bad) and asserted_equivalence(bad) and bare_generic_quantifier(bad, "unresolved"),
        f"set_based={assertive_setbased(bad)} asserted_equivalence={asserted_equivalence(bad)} "
        f"bare_generic={bare_generic_quantifier(bad, 'unresolved')}")
    add("P3_fixed_conclusion_clean",
        not assertive_setbased(fixed) and not asserted_equivalence(fixed)
        and not bare_generic_quantifier(fixed, "unresolved")
        and bool(TAIL_RE.search(fixed)) and binds_deferred_genericity(fixed),
        f"set_based={assertive_setbased(fixed)} asserted_equivalence={asserted_equivalence(fixed)} "
        f"bare_generic={bare_generic_quantifier(fixed, 'unresolved')} tail={bool(TAIL_RE.search(fixed))}")

    schema_map = discover_class_schemas()
    exp_c2 = schema_map.get("AF-SCC-C2-VAC-GEN", {})
    owner_bad = NODE_ARTIFACT_RE.match("F2 (artifact schemas/af_scc_regularities.yaml, section C2)")
    owner_good = NODE_ARTIFACT_RE.match(f"{exp_c2.get('node_id')} (artifact {exp_c2.get('path')})")
    add("P4_schema_owner_parser_bad_vs_good",
        bool(owner_bad) and bool(owner_good)
        and owner_bad.group("path") != exp_c2.get("path") and owner_bad.group("node") != exp_c2.get("node_id")
        and owner_good.group("path") == exp_c2.get("path") and owner_good.group("node") == exp_c2.get("node_id"),
        f"bad={owner_bad.groups() if owner_bad else None} good={owner_good.groups() if owner_good else None} expected={exp_c2}")

    add("P5_duplicate_key_detector",
        len(duplicate_keys("a: 1\na: 2\n")) == 1 and len(duplicate_keys("a: 1\nb: 2\n")) == 0,
        "fixture 'a: 1\\na: 2' -> 1 duplicate; 'a: 1\\nb: 2' -> 0")

    return ctrls


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", default=str(CANONICAL))
    ap.add_argument("--pin", default=None, help="required sha256 of --target; mismatch exits 2 (fail-closed)")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--label", default="")
    ap.add_argument("--no-controls", action="store_true", help="debug only; shipped runs always use controls")
    args = ap.parse_args(argv)

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"FAIL-CLOSED: target missing: {target}", file=sys.stderr)
        return 2
    try:
        text = target.read_text()
        data = yaml.safe_load(text)
        if not isinstance(data, dict) or "classes" not in data:
            raise ValueError("not a taxonomy document")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL-CLOSED: target unparseable: {exc}", file=sys.stderr)
        return 2

    target_sha = sha256_file(target)
    if args.pin and target_sha != args.pin:
        print(f"FAIL-CLOSED: target drifted: {target_sha} != {args.pin}", file=sys.stderr)
        return 2

    controls = [] if args.no_controls else control_suite()
    failed_controls = [c for c in controls if c["status"] != "PASS"]
    if failed_controls:
        print(f"FAIL-CLOSED: control suite failed: {json.dumps(failed_controls)}", file=sys.stderr)
        return 1

    mapd = json.loads(MAP.read_text()) if MAP.exists() else {}
    checks = check_invariants(data, text)
    checks += [check_cl1(data), check_cl2(data), check_cl3(data), check_cl4(data), check_cl5(data, mapd)]
    lead_side = check_lead_side(data, mapd)

    class_content = [c for c in checks if c["scope"] == "class_content"]
    open_checks = [c["id"] for c in class_content if c["status"] != "PASS"]
    regressions = [c["id"] for c in checks if c["scope"] == "regression" and c["status"] != "PASS"]
    closed = not open_checks and not regressions

    result = {
        "instrument": rel(Path(__file__)),
        "instrument_sha256": sha256_file(Path(__file__)),
        "label": args.label,
        "run_at": now(),
        "target": rel(target),
        "target_sha256": target_sha,
        "pin": args.pin,
        "pin_match": (not args.pin) or target_sha == args.pin,
        "class_ids": data.get("class_ids"),
        "checks": checks,
        "lead_side": lead_side,
        "controls": controls,
        "closure": {
            "class_content": "CLOSED" if closed else "OPEN",
            "open_checks": open_checks,
            "invariant_regressions": regressions,
            "closed_checks": [c["id"] for c in class_content if c["status"] == "PASS"],
        },
        "falsifier": (
            "re-run this instrument at the same --pin: any per-check status change, any invariant regression, "
            "or any control failure voids this result. A repair that satisfies CL1-CL5 by weakening a check "
            "(e.g. deleting the four-class invariants or adding a disown marker to an assertively set-based "
            "sentence) is detected by INV1-INV4 plus the P1-P5 controls and is not a closure."
        ),
        "exit_semantics": {"0": "class_content CLOSED", "3": "class_content OPEN", "1": "controls failed", "2": "drift/fail-closed"},
    }

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n")

    print(f"{args.label or rel(target)}: class_content={'CLOSED' if closed else 'OPEN'} "
          f"open={open_checks} regressions={regressions} controls={len(controls) - len(failed_controls)}/{len(controls)}")
    for c in checks:
        print(f"  {c['status']:5s} {c['id']:5s} [{c['scope']}] {c['title']}")
    for c in lead_side:
        print(f"  {c['status']:5s} {c['id']:5s} [lead_side] {c['title']}")
    return 0 if closed else 3


if __name__ == "__main__":
    sys.exit(main())

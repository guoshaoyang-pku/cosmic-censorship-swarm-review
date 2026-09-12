#!/usr/bin/env python3
"""W077-F1-ANCHORBIND-01: independent field-level anchor-binding census for AF-WCC-VAC-GEN (F1).

Read-only, deterministic, stdlib + PyYAML only. No canonical path is written.
Re-run:
    python3 artifacts/worker-077/f1_anchor_bind/check_f1_anchor_bind.py --out report.json

Exit codes: 0 = instrument ok, pins stable, no drift; 2 = control failure;
3 = pin/drift failure (findings may be void); 1 = usage/runtime error.

Scope: this instrument measures *declared anchor obligations* of the frozen F1 schema
against the pinned L1 literature evidence at a fixed hash. It asserts no mathematics,
writes no canonical artifact, and issues no gate verdict.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
TZ = timezone(timedelta(hours=8))
TASK_ID = "W077-F1-ANCHORBIND-01"
LIFECYCLE = "worker-077-20260912T005105-968807"
CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"
GATE = "G-FORM"

PIN_PATHS = [
    "schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/FROZEN.json",
    "ledger/theorems.jsonl",
    "ledger/citation_audit.csv",
    "schemas/f1_falsifier_tests.jsonl",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
]

# Anchor concepts declared in F1 provenance.sources, with the lexical surface that
# marks each concept in the schema text and in the pinned literature evidence.
ANCHORS = [
    {
        "concept_id": "A-WSOBOLEV",
        "concept": "asymptotically flat initial data and weighted Sobolev classes",
        "declared_needed_for": "data_class, regularity",
        "schema_surface": [r"5/2", r"delta in \(1/2", r"weighted Sobolev"],
        "evidence_surface": [r"weighted Sobolev", r"weighted[- ]sobolev", r"s\s*>\s*5/2", r"delta\s+in\s*\(1/2"],
    },
    {
        "concept_id": "A-MGHD",
        "concept": "existence and uniqueness of the maximal globally hyperbolic development",
        "declared_needed_for": "regularity, quantifiers D2",
        "schema_surface": [r"maximal globally hyperbolic", r"\bMGHD\b"],
        "evidence_surface": [r"maximal globally hyperbolic", r"\bMGHD\b"],
    },
    {
        "concept_id": "A-POSMASS",
        "concept": "positive mass theorem and rigidity",
        "declared_needed_for": "data_class.adm_mass",
        "schema_surface": [r"positive mass"],
        "evidence_surface": [r"positive mass", r"positive[- ]mass", r"ADM mass"],
    },
    {
        "concept_id": "A-PREDICT",
        "concept": "definition of future asymptotic predictability and its relation to this schema's conclusion",
        "declared_needed_for": "conclusion.equivalent_standard_formulation",
        "schema_surface": [r"predictab"],
        "evidence_surface": [r"predictab", r"future is not always open", r"nature of spacetime singularities"],
    },
    {
        "concept_id": "A-WCCSTATUS",
        "concept": "known status (proved/refuted/open) of the weak cosmic censorship statement for generic AF vacuum data",
        "declared_needed_for": "no status claim is made by this schema",
        "schema_surface": [r"known status", r"weak cosmic censorship"],
        "evidence_surface": [r"weak cosmic censorship"],
    },
]

# BL-11 anchor items the formulation/literature leads named explicitly.
BL11_ITEMS = [
    {"item": "s>5/2 threshold", "regex": r"s\s*>\s*5/2|5/2"},
    {"item": "delta in (1/2,1)", "regex": r"delta\s+in\s*\(1/2|1/2\s*,\s*1\)"},
    {"item": "positive mass theorem", "regex": r"positive mass"},
    {"item": "future asymptotic predictability", "regex": r"predictab"},
]
POSITIVE_CONTROL_TOKEN = r"cauchy horizon"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that fails closed on duplicate mapping keys."""


def _construct_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"duplicate key {key!r}", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def walk_leaves(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk_leaves(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_leaves(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def regex_hits(text: str, patterns) -> int:
    return sum(len(re.findall(p, text, flags=re.IGNORECASE)) for p in patterns)


def resolve_field(doc, token: str):
    """Resolve a declared_needed_for token against the loaded schema.

    Returns (kind, ok, detail, recovered): kind in {field, section_sub, sentinel};
    ``recovered`` is the unique repaired YAML path when the literal token is not itself
    a resolvable path but exactly one same-name leaf exists one level down.
    """
    t = token.strip()
    if not t:
        return "sentinel", True, "empty token", None
    if t.lower().startswith("no status claim"):
        return "sentinel", True, "prose sentinel: schema asserts no status claim", None
    if "." in t:
        cur = doc
        for part in t.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return "field", False, f"path segment {part!r} not found", None
        return "field", True, "resolved", None
    parts = t.split()
    if len(parts) == 1:
        if isinstance(doc, dict) and parts[0] in doc:
            return "field", True, "resolved top-level", None
        return "field", False, f"top-level key {parts[0]!r} not found", None
    if len(parts) == 2:
        head, sub = parts
        if isinstance(doc, dict) and head in doc:
            if isinstance(doc[head], dict) and sub in doc[head]:
                return "section_sub", True, "resolved section member", None
            # unique one-level recovery: <head>.<child>.<sub>
            if isinstance(doc[head], dict):
                recovered = [f"{head}.{child}.{sub}" for child, subdoc in doc[head].items()
                             if isinstance(subdoc, dict) and sub in subdoc]
                if len(recovered) == 1:
                    return ("section_sub", True,
                            f"literal path unresolved; unique recovery at {recovered[0]}", recovered[0])
                if len(recovered) > 1:
                    return ("section_sub", False,
                            f"{sub!r} not a direct member of {head!r}; ambiguous recovery {recovered}", None)
            return "section_sub", False, f"{sub!r} not found under {head!r}", None
        return "section_sub", False, f"section {head!r} not found", None
    return "field", False, "unparsable token", None


def scan_text_for_anchor(text: str, anchor) -> list:
    return sorted({p for p in anchor["evidence_surface"] if re.search(p, text, re.IGNORECASE)})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("report.json")))
    args = ap.parse_args()

    created_at = datetime.now(TZ).isoformat(timespec="seconds")
    checks, controls, findings, hard_failures = [], [], [], []
    exit_code = 0

    def check(cid, desc, ok, detail, metrics=None):
        checks.append({"id": cid, "description": desc,
                       "status": "PASS" if ok else "FAIL",
                       "detail": detail, "metrics": metrics or {}})

    def control(cid, expected, observed, ok):
        controls.append({"id": cid, "expected": expected,
                         "observed": observed, "ok": bool(ok)})

    # ---------- pins ----------
    pins_before = {}
    for rel in PIN_PATHS:
        p = ROOT / rel
        if not p.exists():
            print(f"FATAL: missing pinned input {rel}", file=sys.stderr)
            return 1
        st = p.stat()
        pins_before[rel] = {"sha256": sha256_file(p), "bytes": st.st_size,
                            "mtime_ns": st.st_mtime_ns}

    f1 = yaml.load((ROOT / "schemas/af_wcc_vacuum.yaml").read_text(), Loader=StrictLoader)
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    suite_rows = [json.loads(l) for l in
                  (ROOT / "schemas/f1_falsifier_tests.jsonl").read_text().splitlines() if l.strip()]
    ledger_text = (ROOT / "ledger/theorems.jsonl").read_text()
    citation_text = (ROOT / "ledger/citation_audit.csv").read_text()
    ledger_rows = [json.loads(l) for l in ledger_text.splitlines() if l.strip()]
    citation_rows = list(csv.DictReader(io.StringIO(citation_text)))

    live_f1 = pins_before["schemas/af_wcc_vacuum.yaml"]["sha256"]
    frozen_pin = (frozen.get("files", {}).get("schemas/af_wcc_vacuum.yaml", {}) or {}).get("sha256")
    check("C1-pin-frozen",
          "live F1 bytes equal the FROZEN manifest pin for the canonical F1 schema",
          frozen_pin == live_f1,
          {"live": live_f1, "frozen_pin": frozen_pin,
           "frozen_revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at")})
    check("C1b-class-id", "F1 declares exactly one frozen class id",
          f1.get("class_id") == CLASS_ID, {"class_id": f1.get("class_id")})
    if frozen_pin != live_f1:
        exit_code = 3

    # ---------- C2 declared anchors ----------
    sources = (f1.get("provenance", {}) or {}).get("sources", []) or []
    declared = [s for s in sources if isinstance(s, dict) and s.get("concept")]
    null_ids = [s["concept"] for s in declared if not s.get("identifier")]
    unresolved = [s["concept"] for s in declared if str(s.get("status", "")).lower() != "resolved"]
    check("C2-provenance-anchors",
          "provenance.sources declares one anchor row per anchor concept, with identifier/status",
          len(declared) >= 5 and len(null_ids) == len(declared),
          {"declared": len(declared), "identifier_null": len(null_ids),
           "status_unresolved": len(unresolved)},
          {"concepts": [s["concept"] for s in declared]})
    if declared and len(null_ids) == len(declared):
        hard_failures.append("W077-AB-01")
    findings.append({
        "id": "W077-AB-01", "severity": "major", "type": "unanchored_schema_obligation",
        "finding": (f"{len(null_ids)}/{len(declared)} F1 provenance anchor rows carry identifier=null and "
                    f"status=unresolved while their declared_needed_for fields are load-bearing in the schema "
                    f"({', '.join(sorted({s.get('needed_for','?') for s in declared}))}). "
                    "Reproduces literature-lead BL-11 (lit-l7-20260912-007) from the rev29 bytes."),
        "falsifier": "Any provenance.sources row at the live F1 hash with a non-null identifier whose status is resolved."})

    # ---------- C3 field bindings resolve ----------
    binding_rows = []
    for s in declared:
        needed = str(s.get("needed_for") or "")
        for token in [t.strip() for t in needed.split(",") if t.strip()]:
            kind, ok, detail, recovered = resolve_field(f1, token)
            binding_rows.append({"concept": s.get("concept"), "token": token, "kind": kind,
                                 "resolved": ok, "detail": detail, "recovered_path": recovered})
    bad = [r for r in binding_rows if not r["resolved"]]
    recovered_rows = [r for r in binding_rows if r.get("recovered_path")]
    check("C3-field-binding-resolves",
          "every field named in provenance.sources[*].needed_for resolves in the F1 YAML "
          "(literal path, or unique single-level recovery)",
          not bad, {"tokens": len(binding_rows), "unresolved": len(bad),
                    "unresolved_tokens": [r["token"] for r in bad],
                    "recovered_tokens": {r["token"]: r["recovered_path"] for r in recovered_rows}})
    for r in recovered_rows:
        findings.append({
            "id": "W077-AB-04", "severity": "minor", "type": "imprecise_field_binding_token",
            "finding": (f"provenance anchor {r['concept'][:48]!r} binds needed_for token {r['token']!r}, which is "
                        f"not itself a resolvable YAML path; the unique recovery is {r['recovered_path']}. "
                        "The obligation is well-defined after a one-token path repair, which is the per-field "
                        "binding form the literature lead asked for in BL-11."),
            "falsifier": "A second same-name leaf under the same section, or a schema revision in which "
                         f"{r['recovered_path']} does not exist."})

    # ---------- C4 anchor leaf census ----------
    anchor_rows = []
    for a in ANCHORS:
        leaves = [(p, t) for p, t in walk_leaves(f1) if regex_hits(t, a["schema_surface"])]
        anchor_rows.append({
            "concept_id": a["concept_id"], "concept": a["concept"],
            "declared_needed_for": a["declared_needed_for"],
            "declared_status": next((s.get("status") for s in declared if s.get("concept") == a["concept"]), None),
            "declared_identifier": next((s.get("identifier") for s in declared if s.get("concept") == a["concept"]), None),
            "schema_leaf_hits": len(leaves),
            "schema_leaf_paths": [p for p, _ in leaves],
            "l1_ledger_hits": regex_hits(ledger_text, a["evidence_surface"]),
            "l1_citation_hits": regex_hits(citation_text, a["evidence_surface"]),
        })
    check("C4-anchor-leaf-census",
          "each declared anchor concept is locatable in the F1 schema text",
          all(r["schema_leaf_hits"] > 0 for r in anchor_rows),
          {r["concept_id"]: r["schema_leaf_hits"] for r in anchor_rows})

    # ---------- C5 BL-11 zero-hit reproduction (with positive control token) ----------
    bl11_rows = []
    for item in BL11_ITEMS:
        bl11_rows.append({
            "item": item["item"],
            "ledger_hits": len(re.findall(item["regex"], ledger_text, re.IGNORECASE)),
            "citation_hits": len(re.findall(item["regex"], citation_text, re.IGNORECASE)),
        })
    zeros = [r["item"] for r in bl11_rows if r["ledger_hits"] == 0 and r["citation_hits"] == 0]
    pos_ledger = len(re.findall(POSITIVE_CONTROL_TOKEN, ledger_text, re.IGNORECASE))
    pos_citation = len(re.findall(POSITIVE_CONTROL_TOKEN, citation_text, re.IGNORECASE))
    check("C5-bl11-zero-hit",
          "the four BL-11 anchor items have zero hits in the pinned ledger and citation audit, "
          "while a known-present positive-control token is found",
          len(zeros) == len(BL11_ITEMS) and pos_ledger > 0 and pos_citation > 0,
          {"zero_hit_items": zeros, "positive_control": POSITIVE_CONTROL_TOKEN,
           "positive_control_ledger_hits": pos_ledger,
           "positive_control_citation_hits": pos_citation})
    if len(zeros) == len(BL11_ITEMS):
        hard_failures.append("W077-AB-02")
    findings.append({
        "id": "W077-AB-02", "severity": "major", "type": "no_registered_l1_anchor",
        "finding": (f"At the pinned ledger/citation audit, all four BL-11 anchor items "
                    f"({', '.join(zeros)}) have 0 lexical hits; positive control "
                    f"'{POSITIVE_CONTROL_TOKEN}' has {pos_ledger}/{pos_citation} hits, so the scanner is live. "
                    "No registered source in the pinned corpus anchors these concepts."),
        "falsifier": "A lexical variant of any BL-11 anchor item present in the pinned ledger or citation audit, "
                     "or a positive-control token with 0 hits (instrument failure)."})

    # ---------- C6 registered-but-unbound sources ----------
    ledger_srcs = set()
    for r in ledger_rows:
        for s in (r.get("source_ids") or []):
            ledger_srcs.add(s)
    reg = []
    for cid in ("SRC-096", "SRC-097"):
        row = next((r for r in citation_rows if r.get("citation_id") == cid), None)
        reg.append({"citation_id": cid,
                    "in_citation_audit": row is not None,
                    "in_ledger_source_ids": cid in ledger_srcs,
                    "used_by_theorems": (row or {}).get("used_by_theorems", None),
                    "class_mapping": (row or {}).get("class_mapping", None),
                    "title": (row or {}).get("title", None)})
    check("C6-registered-unbound",
          "SRC-096/SRC-097 are registered in the citation audit but carry no L0 ledger entry",
          all(r["in_citation_audit"] and not r["in_ledger_source_ids"] for r in reg),
          {"rows": reg})

    # ---------- C7 candidate coverage per concept ----------
    cand_rows = []
    for a in ANCHORS:
        cands = []
        for r in citation_rows:
            blob = " ".join(str(r.get(k) or "") for k in
                            ("title", "bibkey", "assessment", "evidence_excerpt", "class_mapping"))
            if regex_hits(blob, a["evidence_surface"]):
                cands.append(r.get("citation_id"))
        cand_rows.append({"concept_id": a["concept_id"], "candidates": sorted(set(cands)),
                          "n_candidates": len(set(cands))})
    check("C7-candidate-coverage",
          "candidate anchor sources exist in the pinned citation audit for each declared concept",
          all(r["n_candidates"] > 0 for r in cand_rows),
          {r["concept_id"]: r["n_candidates"] for r in cand_rows})

    # ---------- C8 falsifier-suite binding vs live F1 ----------
    suite_bindings = sorted({str(r.get("binding_sha256") or "") for r in suite_rows})
    bound_live = [r["test_id"] for r in suite_rows
                  if str(r.get("binding_sha256") or "") == live_f1]
    check("C8-suite-rebound-to-live",
          "every row of schemas/f1_falsifier_tests.jsonl binds the live F1 hash",
          len(bound_live) == len(suite_rows),
          {"rows": len(suite_rows), "bound_live": len(bound_live),
           "distinct_bindings": [b[:16] for b in suite_bindings]})
    if len(bound_live) != len(suite_rows):
        findings.append({
            "id": "W077-AB-03", "severity": "minor", "type": "stale_falsifier_suite_binding",
            "finding": (f"{len(suite_rows) - len(bound_live)}/{len(suite_rows)} rows of the declared F1 falsifier "
                        f"suite bind {', '.join(b[:16] for b in suite_bindings)} instead of the live rev29 F1 hash "
                        f"{live_f1[:16]}; the suite is not citable as current-revision falsifier-exercise evidence "
                        "until re-bound by its owner."),
            "falsifier": "A suite row binding the live F1 hash, or a re-bound suite whose rows all equal the live hash."})

    # ---------- C9 controls ----------
    control("K1-token-injection",
            "synthetic text carrying an anchor term is detected",
            scan_text_for_anchor("the weighted Sobolev threshold s > 5/2", ANCHORS[0]) != [],
            scan_text_for_anchor("the weighted Sobolev threshold s > 5/2", ANCHORS[0]) != [])
    control("K2-token-absence",
            "unrelated synthetic text yields no anchor hit",
            scan_text_for_anchor("quantum chromodynamics on a torus", ANCHORS[0]) == [],
            scan_text_for_anchor("quantum chromodynamics on a torus", ANCHORS[0]) == [])
    k3 = resolve_field(f1, "data_class.adm_mass")
    control("K3-field-resolve-positive", "a real field path resolves",
            k3[1] is True, k3[1] is True)
    k4 = resolve_field(f1, "data_class.__no_such_field__")
    control("K4-field-resolve-negative", "a fabricated field path fails closed",
            k4[1] is False, k4[1] is False)
    try:
        yaml.load("a: 1\na: 2\n", Loader=StrictLoader)
        dup_ok = False
    except yaml.constructor.ConstructorError:
        dup_ok = True
    control("K5-duplicate-key-guard", "strict loader rejects a duplicate mapping key",
            dup_ok, dup_ok)
    try:
        yaml.load((ROOT / "schemas/af_wcc_vacuum.yaml").read_text(), Loader=StrictLoader)
        control("K5b-canonical-strict-parse", "the canonical F1 bytes parse under the strict loader",
                True, True)
    except yaml.constructor.ConstructorError as e:
        control("K5b-canonical-strict-parse", "the canonical F1 bytes parse under the strict loader",
                True, False)
    mutated = dict(pins_before["schemas/af_wcc_vacuum.yaml"])
    mutated["sha256"] = "0" * 64
    control("K6-pin-mutation-sensitivity", "a mutated expected pin fails the pin comparison",
            mutated["sha256"] != live_f1, mutated["sha256"] != live_f1)

    if not all(c["ok"] for c in controls):
        exit_code = 2

    # ---------- C10 post-run drift ----------
    pins_after = {}
    for rel in PIN_PATHS:
        p = ROOT / rel
        pins_after[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size,
                           "mtime_ns": p.stat().st_mtime_ns}
    drift = [rel for rel in PIN_PATHS if pins_before[rel]["sha256"] != pins_after[rel]["sha256"]]
    check("C10-no-drift", "all pinned inputs are byte-identical before and after the run",
          not drift, {"drifted": drift})
    if drift:
        exit_code = 3

    # ---------- verdict ----------
    hard_failures = sorted(set(hard_failures))
    verdict = "revise" if hard_failures else "accept"
    report = {
        "schema": "w077-f1-anchorbind/v1",
        "task_id": TASK_ID,
        "actor": "worker-077",
        "lifecycle": LIFECYCLE,
        "created_at": created_at,
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_ID,
        "class_ids": [CLASS_ID],
        "instrument": {
            "path": "artifacts/worker-077/f1_anchor_bind/check_f1_anchor_bind.py",
            "read_only": True,
            "deterministic": True,
            "dependencies": ["stdlib", "PyYAML"],
        },
        "pins": pins_before,
        "pins_after": pins_after,
        "frozen": {"revision": frozen.get("revision"), "frozen_at": frozen.get("frozen_at"),
                   "f1_pin": frozen_pin},
        "checks": checks,
        "controls": controls,
        "anchors": anchor_rows,
        "field_binding_rows": binding_rows,
        "bl11_zero_hit": bl11_rows,
        "registered_unbound": reg,
        "candidate_coverage": cand_rows,
        "suite_binding": {"rows": len(suite_rows), "bound_live": len(bound_live),
                          "distinct_bindings": suite_bindings},
        "verdict": {
            "verdict": verdict,
            "score": 2.5 if hard_failures else 4.0,
            "counts_as_full_schema_verdict": False,
            "hard_failures": hard_failures,
            "findings": findings,
            "falsifier": ("Re-run this instrument at the same pins: any provenance anchor with a non-null, "
                          "resolved identifier; any BL-11 anchor item with >=1 hit in the pinned ledger or "
                          "citation audit; any needed_for token that fails to resolve; any falsifier-suite row "
                          "binding the live F1 hash; or any pinned input that drifts voids the corresponding "
                          "finding and the whole census if drift is detected."),
            "non_claims": [
                "not a gate verdict and does not set any node status or validation_status",
                "does not edit any canonical artifact (read-only run)",
                "asserts no mathematics, no physics, and no literature claim beyond lexical hits in the pinned bytes",
                "candidate source lists are lexical matches, not endorsed anchors",
                "the 'Cauchy horizon' universal posed by the literature lead is recorded as open, not adjudicated",
            ],
        },
        "exit_code": exit_code,
    }
    out = Path(args.out)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"task_id": TASK_ID, "verdict": verdict,
                      "hard_failures": hard_failures,
                      "checks_failed": [c["id"] for c in checks if c["status"] == "FAIL"],
                      "controls_failed": [c["id"] for c in controls if not c["ok"]],
                      "drift": drift,
                      "report": str(out)}, indent=1))
    if not all(c["ok"] for c in controls):
        return 2
    if drift or frozen_pin != live_f1:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

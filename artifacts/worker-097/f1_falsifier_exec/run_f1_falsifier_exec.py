#!/usr/bin/env python3
"""W097-F1-FALSIFIER-EXEC-01 -- independently EXECUTE the F1 falsifier/ambiguity suite.

Worker: worker-097 (bounded execution worker). Node F1, class AF-WCC-VAC-GEN, gate G-FORM.

Question this instrument answers, at pinned bytes:
  For each of the 25 rows in schemas/f1_falsifier_tests.jsonl, does the canonical F1
  schema (schemas/af_wcc_vacuum.yaml) actually *decide* the row from the field the row
  names -- i.e. does the named deciding field exist, carry determinate content, and do
  the row's own probe excerpts reproduce against the frozen schema text?

This is an artifact audit, not a mathematics claim and not a gate verdict.
Exit codes: 0 = report written, controls passed; 2 = a negative control failed (fail closed).

Usage: python3 run_f1_falsifier_exec.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-097/f1_falsifier_exec -> repo root
SCHEMA = ROOT / "schemas" / "af_wcc_vacuum.yaml"
SUITE = ROOT / "schemas" / "f1_falsifier_tests.jsonl"
SNAP = HERE / "snapshots"
CST = timezone(timedelta(hours=8))

OPEN_MARKERS = ("obligation", "unresolved", "open", "pending", "undecided", "unverified")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm(s: str) -> str:
    return " ".join(str(s).split())


# --- schema path resolution -------------------------------------------------------------
def _resolve_segs(cur, segs):
    """Return (ok, value). Supports one [*] list mapping per segment."""
    if not segs:
        return True, cur
    head, rest = segs[0], segs[1:]
    star = head.endswith("[*]")
    name = head[:-3] if star else head
    if star:
        base = cur
        if isinstance(base, dict):
            if name not in base:
                return False, None
            base = base[name]
        elif name:
            return False, None
        if not isinstance(base, list):
            return False, None
        out = []
        for item in base:
            ok, v = _resolve_segs(item, rest)
            if ok:
                out.append(v)
        return (True, out) if out else (False, None)
    if isinstance(cur, dict) and name in cur:
        return _resolve_segs(cur[name], rest)
    return False, None


def resolve_expr(doc, expr: str):
    """Resolve a contract expression: a dotted path, possibly 'A plus B' composite."""
    expr = str(expr or "").strip()
    if not expr:
        return {"expr": expr, "kind": "empty", "resolved": False, "parts": []}
    parts = [p.strip() for p in expr.split(" plus ")] if " plus " in expr else [expr]
    results = []
    for part in parts:
        try:
            ok, val = _resolve_segs(doc, part.split("."))
        except Exception:
            ok, val = False, None
        results.append({"path": part, "resolved": bool(ok), "value": val})
    resolved = all(r["resolved"] for r in results)
    kind = "composite" if len(results) > 1 else "single"
    return {"expr": expr, "kind": kind, "resolved": resolved, "parts": results}


def value_repr(v, limit: int = 200) -> str:
    try:
        s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    except Exception:
        s = str(v)
    return norm(s)[:limit]


def _serials(v):
    """Canonical serializations a probe excerpt may have been cut from."""
    out = []
    if isinstance(v, str):
        out.append(v)
        out.append(json.dumps(v, ensure_ascii=False))
    else:
        try:
            out.append(json.dumps(v, ensure_ascii=False, default=str))
        except Exception:
            pass
        out.append(str(v))
    return [norm(x) for x in out]


def _unquote(s: str) -> str:
    s = norm(s)
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    return s


def probe_check(p, doc):
    """Independently execute one probe_results entry against the frozen schema.

    kind semantics (from the suite's own vocabulary):
      contains    -- `expected` token occurs inside a serialization of the value at `path`
      equals      -- the value at `path` equals `expected`
      is_true     -- the value at `path` is boolean True
      is_none     -- the value at `path` is null
      nonnull     -- the value at `path` is not null
      path_exists -- `path` resolves
    `observed_excerpt` is a (usually truncated) serialization of the same value, so the
    reproduction test is a normalized prefix match, not a raw text search.
    """
    path = str(p.get("path") or "")
    kind = str(p.get("kind") or "")
    expected = norm(p.get("expected") or "")
    excerpt = _unquote(p.get("observed_excerpt") or "")
    author_pass = p.get("pass")

    ok, val = _resolve_segs(doc, path.split(".")) if path else (False, None)
    serials = _serials(val) if ok else []
    excerpt_reproduces = bool(ok) and any(s.startswith(excerpt) for s in serials)

    if kind == "contains":
        expected_ok = bool(expected) and any(expected in s for s in serials)
        executed = bool(ok and excerpt_reproduces and expected_ok)
    elif kind == "equals":
        cands = set()
        if ok:
            cands.add(norm(str(val)))
            try:
                cands.add(norm(json.dumps(val, ensure_ascii=False, default=str)))
            except Exception:
                pass
            if isinstance(val, str):
                cands.add(norm(val))
        expected_ok = expected in cands
        executed = bool(ok and expected_ok)
    elif kind == "is_true":
        executed = bool(ok and val is True)
    elif kind == "is_none":
        executed = bool(ok and val is None)
    elif kind == "nonnull":
        executed = bool(ok and val is not None)
    elif kind == "path_exists":
        executed = bool(ok)
    else:
        executed = None  # unknown kind: do not score

    return {
        "path": path, "kind": kind, "expected": expected, "role": p.get("role"),
        "path_resolved": bool(ok),
        "excerpt_reproduces": excerpt_reproduces,
        "author_pass": author_pass,
        "executed_pass": executed,
        "agrees_with_author": (executed == bool(author_pass)) if executed is not None else None,
        "needle_prefix": excerpt[:80],
        "value_excerpt": value_repr(val, 120) if ok else None,
    }


def classify(row, schema_sha, schema_text_norm, doc):
    """Decide one suite row against the pinned schema. Pure function (testable)."""
    cand_exprs = []
    for key in ("deciding_field", "deciding_field_contract"):
        if row.get(key):
            cand_exprs.append((key, str(row[key])))
    for alt in row.get("deciding_field_alternates") or []:
        cand_exprs.append(("deciding_field_alternates", str(alt)))

    resolutions = []
    for key, expr in cand_exprs:
        r = resolve_expr(doc, expr)
        r["source"] = key
        resolutions.append(r)

    primary = next((r for r in resolutions if r["source"] == "deciding_field"), None)
    contract = next((r for r in resolutions if r["source"] == "deciding_field_contract"), None)
    resolved_any = any(r["resolved"] for r in resolutions)
    resolved_primary = bool(primary and primary["resolved"])
    contract_resolved = bool(contract and contract["resolved"])

    status = str(row.get("deciding_field_status") or "")
    open_status = any(m in status.lower() for m in OPEN_MARKERS) or bool(row.get("unresolved_keywords"))

    if not resolved_primary and not resolved_any:
        cls = "UNRESOLVED_PATH"
    elif not resolved_primary and resolved_any:
        cls = "ALTERNATE_ONLY"
    elif open_status:
        cls = "RESOLVED_OPEN_OBLIGATION"
    else:
        cls = "RESOLVED_DETERMINATE"

    # probe reproduction against frozen schema text / values
    probes = [probe_check(pr, doc) for pr in (row.get("probe_results") or []) if isinstance(pr, dict)]

    binding = (row.get("binding_sha256") or
               (row.get("binding_ref") or "").split("#sha256:")[-1] or "")
    binding_ok = bool(binding) and schema_sha.startswith(binding[:12]) or binding == schema_sha

    return {
        "test_id": row.get("test_id"),
        "title": row.get("title"),
        "ambiguity_kind": row.get("ambiguity_kind"),
        "recorded_verdict": {
            "does_it_satisfy_f1": row.get("does_it_satisfy_f1"),
            "satisfies_conclusion": row.get("satisfies_conclusion"),
            "satisfies_in_class": row.get("satisfies_in_class"),
        },
        "deciding_field": row.get("deciding_field"),
        "deciding_field_contract": row.get("deciding_field_contract"),
        "contract_resolved": contract_resolved,
        "deciding_field_status": status,
        "binding_sha256": binding,
        "binding_matches_measured": binding_ok,
        "resolutions": [
            {"source": r["source"], "expr": r["expr"], "kind": r["kind"],
             "resolved": r["resolved"],
             "resolved_paths": [p["path"] for p in r["parts"] if p["resolved"]],
             "missing_paths": [p["path"] for p in r["parts"] if not p["resolved"]],
             "value_excerpts": [value_repr(p["value"], 120) for p in r["parts"] if p["resolved"]]}
            for r in resolutions
        ],
        "decisability_class": cls,
        "probes": probes,
        "probes_ok": sum(1 for p in probes if p["executed_pass"] is True),
        "probes_failed": sum(1 for p in probes if p["executed_pass"] is False),
        "probes_unknown_kind": sum(1 for p in probes if p["executed_pass"] is None),
        "probes_disagree_with_author": sum(1 for p in probes if p["agrees_with_author"] is False),
        "unresolved_keywords": row.get("unresolved_keywords") or [],
        "schema_open_expected": row.get("schema_open_expected"),
    }


def run_controls(doc, schema_sha, schema_text_norm):
    """Negative controls: the classifier must fail closed on deliberately broken inputs."""
    controls = []

    base = json.loads(json.dumps(next(r for r in load_suite() if r.get("test_id") == "F1-AMB-01")))

    # C1: delete the deciding subtree -> must become UNRESOLVED_PATH
    broken = {k: v for k, v in doc.items() if k != "non_vacuity"}
    r1 = classify(base, schema_sha, schema_text_norm, broken)
    controls.append({"id": "C1-missing-subtree", "role": "negative",
                     "expect": "UNRESOLVED_PATH", "observed": r1["decisability_class"],
                     "pass": r1["decisability_class"] == "UNRESOLVED_PATH"})

    # C2: bogus deciding field -> must become UNRESOLVED_PATH
    bogus = dict(base)
    bogus["deciding_field"] = "__no_such_block__.field"
    bogus["deciding_field_contract"] = "__no_such_block__.field"
    bogus["deciding_field_alternates"] = []
    r2 = classify(bogus, schema_sha, schema_text_norm, doc)
    controls.append({"id": "C2-bogus-field", "role": "negative",
                     "expect": "UNRESOLVED_PATH", "observed": r2["decisability_class"],
                     "pass": r2["decisability_class"] == "UNRESOLVED_PATH"})

    # C3: probe present/absent discrimination -> both directions must behave
    present = dict(base); present["probe_results"] = [
        {"kind": "contains", "path": "non_vacuity.condition",
         "expected": "geodesically incomplete",
         "observed_excerpt": "G must contain data whose MGHD is future geodesically incomplete"}]
    absent = dict(base); absent["probe_results"] = [
        {"kind": "contains", "path": "non_vacuity.condition",
         "expected": "geodesically incomplete",
         "observed_excerpt": "this exact sentence does not occur in the schema at all"}]
    r3a, r3b = classify(present, schema_sha, schema_text_norm, doc), classify(absent, schema_sha, schema_text_norm, doc)
    controls.append({"id": "C3-probe-discrimination", "role": "negative",
                     "expect": "present.ok=1 absent.ok=0",
                     "observed": f"present.ok={r3a['probes_ok']} absent.ok={r3b['probes_ok']}",
                     "pass": r3a["probes_ok"] == 1 and r3b["probes_ok"] == 0})

    # C3b: probe on a missing path -> must fail even when the token is in the file elsewhere
    missing_path = dict(base); missing_path["probe_results"] = [
        {"kind": "contains", "path": "__no_such_block__.field",
         "expected": "vacuum", "observed_excerpt": "vacuum"}]
    r3c = classify(missing_path, schema_sha, schema_text_norm, doc)
    controls.append({"id": "C3b-probe-path-binding", "role": "negative",
                     "expect": "missing_path.ok=0",
                     "observed": f"missing_path.ok={r3c['probes_ok']}",
                     "pass": r3c["probes_ok"] == 0})

    # C4: wrong binding hash -> binding_matches_measured must be False
    stale = dict(base); stale["binding_sha256"] = "0" * 64
    r4 = classify(stale, schema_sha, schema_text_norm, doc)
    controls.append({"id": "C4-stale-binding", "role": "negative",
                     "expect": "binding_matches_measured=False",
                     "observed": f"binding_matches_measured={r4['binding_matches_measured']}",
                     "pass": r4["binding_matches_measured"] is False})

    # C5: positive control -- the unmodified row must NOT be UNRESOLVED_PATH
    r5 = classify(base, schema_sha, schema_text_norm, doc)
    controls.append({"id": "C5-positive-baseline", "role": "positive",
                     "expect": "!= UNRESOLVED_PATH", "observed": r5["decisability_class"],
                     "pass": r5["decisability_class"] != "UNRESOLVED_PATH"})
    return controls, r1, r2, r3a, r3b, r4, r5


def load_suite():
    return [json.loads(l) for l in SUITE.read_text().splitlines() if l.strip()]


def main() -> int:
    SCHEMA_SHA = sha256_file(SCHEMA)
    SUITE_SHA = sha256_file(SUITE)
    schema_text_norm = norm(SCHEMA.read_text())
    doc = yaml.safe_load(SCHEMA.read_text())
    rows = load_suite()

    SNAP.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCHEMA, SNAP / f"af_wcc_vacuum.{SCHEMA_SHA[:12]}.yaml")
    shutil.copy2(SUITE, SNAP / f"f1_falsifier_tests.{SUITE_SHA[:12]}.jsonl")

    controls, *_ = run_controls(doc, SCHEMA_SHA, schema_text_norm)
    controls_pass = all(c["pass"] for c in controls)

    cases = [classify(r, SCHEMA_SHA, schema_text_norm, doc) for r in rows]

    # re-measure drift after the run (fail closed: run does not write to inputs)
    drift = {
        "schema_sha256_start": SCHEMA_SHA, "schema_sha256_end": sha256_file(SCHEMA),
        "suite_sha256_start": SUITE_SHA, "suite_sha256_end": sha256_file(SUITE),
    }
    drift["schema_stable"] = drift["schema_sha256_start"] == drift["schema_sha256_end"]
    drift["suite_stable"] = drift["suite_sha256_start"] == drift["suite_sha256_end"]

    by_class = {}
    for c in cases:
        by_class[c["decisability_class"]] = by_class.get(c["decisability_class"], 0) + 1

    findings = []
    unresolved = [c["test_id"] for c in cases if c["decisability_class"] == "UNRESOLVED_PATH"]
    alt_only = [c["test_id"] for c in cases if c["decisability_class"] == "ALTERNATE_ONLY"]
    obligations = [c["test_id"] for c in cases if c["decisability_class"] == "RESOLVED_OPEN_OBLIGATION"]
    stale_bind = [c["test_id"] for c in cases if not c["binding_matches_measured"]]
    probe_fail = [c["test_id"] for c in cases if c["probes_failed"] > 0]
    probe_disagree = [c["test_id"] for c in cases if c["probes_disagree_with_author"] > 0]
    contract_missing = sorted({c["deciding_field_contract"] for c in cases
                               if c["deciding_field_contract"] and not c["contract_resolved"]})

    if unresolved:
        findings.append({"id": "F-1", "severity": "major",
                         "finding": f"{len(unresolved)}/{len(cases)} rows name a primary deciding field that does not resolve in the frozen schema; the row cannot be decided from the schema as written.",
                         "cases": unresolved})
    if alt_only:
        findings.append({"id": "F-2", "severity": "major",
                         "finding": f"{len(alt_only)}/{len(cases)} rows have an unresolvable primary deciding field but at least one resolvable alternate; the row's stated decision procedure and the schema disagree on the field name.",
                         "cases": alt_only})
    if contract_missing:
        findings.append({"id": "F-3", "severity": "minor",
                         "finding": f"{len(contract_missing)} deciding-field_contract expression(s) do not resolve verbatim in the frozen schema (naming/pointer drift between suite and schema).",
                         "contracts": contract_missing})
    if stale_bind:
        findings.append({"id": "F-4", "severity": "major",
                         "finding": f"{len(stale_bind)} rows are bound to a schema hash other than the measured canonical hash {SCHEMA_SHA[:12]}.",
                         "cases": stale_bind})
    if probe_fail:
        findings.append({"id": "F-5", "severity": "major",
                         "finding": f"{len(probe_fail)} rows carry at least one probe whose path/excerpt/expected triple does not reproduce under independent execution against the frozen schema (path resolution + normalized excerpt-prefix + expected-token checks).",
                         "cases": probe_fail})
    if probe_disagree:
        findings.append({"id": "F-7", "severity": "major",
                         "finding": f"{len(probe_disagree)} rows record author pass=true on at least one probe that does not reproduce independently; the suite's own probe verdicts are not all reproducible at the pinned hash.",
                         "cases": probe_disagree})
    if obligations:
        findings.append({"id": "F-6", "severity": "info",
                         "finding": f"{len(obligations)} rows resolve to a declared open obligation (status token or unresolved_keywords); the schema decides the field shape but not the obligation.",
                         "cases": obligations})
    if not findings:
        findings.append({"id": "F-0", "severity": "info",
                         "finding": "All rows resolved through their primary deciding field with reproducing probes at the measured hash; no drift detected."})

    report = {
        "check_id": "W097-F1-FALSIFIER-EXEC-01",
        "actor": "worker-097",
        "created_at": now(),
        "node_id": "F1",
        "class_id": "AF-WCC-VAC-GEN",
        "gate": "G-FORM",
        "authority": ("worker measurement only; no gate verdict, no node completion, no validation_status promotion, "
                      "no mathematics claim. Submission for lead/controller adjudication."),
        "instrument": {"path": str(HERE / "run_f1_falsifier_exec.py"),
                       "sha256": sha256_file(Path(__file__).resolve())},
        "inputs": {
            "schema": {"path": "schemas/af_wcc_vacuum.yaml", "sha256": SCHEMA_SHA,
                       "bytes": SCHEMA.stat().st_size},
            "suite": {"path": "schemas/f1_falsifier_tests.jsonl", "sha256": SUITE_SHA,
                      "bytes": SUITE.stat().st_size, "rows": len(rows)},
        },
        "snapshots": sorted(str(p.relative_to(ROOT)) for p in SNAP.glob("*")),
        "drift": drift,
        "controls": controls,
        "controls_pass": controls_pass,
        "counts": {"rows": len(cases), "by_decisability_class": by_class,
                   "binding_mismatch": len(stale_bind), "probe_failed_rows": len(probe_fail)},
        "cases": cases,
        "findings": findings,
        "falsifier": ("Re-run this instrument on the same pinned hashes and find a row whose reported decisability_class "
                      "differs from this report, or exhibit a row classified UNRESOLVED_PATH whose deciding field is in fact "
                      "present under the schema's own key spelling. A schema revision or suite re-pin changes the input hash "
                      "and voids this report rather than falsifying it."),
        "next_falsifier": ("Run the same execution against the next F1 revision and the next suite binding; a row that moves from "
                           "UNRESOLVED_PATH/ALTERNATE_ONLY to RESOLVED_DETERMINATE (or vice versa) is the next measurement."),
    }

    (HERE / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (HERE / "raw_sha256.txt").write_text(
        "\n".join(f"{sha256_file(p)}  {p.relative_to(ROOT)}" for p in
                  [SCHEMA, SUITE, Path(__file__).resolve()] +
                  sorted(SNAP.glob("*"))) + "\n")

    print(json.dumps({"controls_pass": controls_pass,
                      "counts": report["counts"],
                      "findings": [f["id"] for f in findings],
                      "report_sha256_self": sha256_file(HERE / "report.json")}, indent=2))
    return 0 if controls_pass else 2


if __name__ == "__main__":
    sys.exit(main())

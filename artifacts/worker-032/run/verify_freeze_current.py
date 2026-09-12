#!/usr/bin/env python3
"""Worker-04 re-verification of the F1 (AF-WCC-VAC-GEN) ambiguity suite against the
CURRENT canonical F1 schema and FROZEN manifest state.

Read-only: never rewrites schemas/f1_falsifier_tests.jsonl, never touches
schemas/af_wcc_vacuum.yaml, emits no map mutation.

Checks
  C1a canonical on-disk schema sha256 == suite binding sha256            (HARD)
  C1b FROZEN canonical pin == suite binding sha256                       (SOFT: prefreeze lag)
  C2  authoring mirror on disk == canonical, and FROZEN authoring pin == canonical (SOFT)
  C3  suite sha256 == last submitted report field                        (SOFT record check)
  C4  suite parses: unique test ids                                      (HARD)
  C5  assignment acceptance: >=10 rows, each with spacetime_description,
      does_it_satisfy_f1, deciding_field, falsifier, next_falsifier,
      evidence_refs                                                      (HARD)
  C6  all rows agree on the binding sha and class/node/gate constants    (HARD)
  C7  every deciding_field and alternate resolves in the canonical YAML  (HARD)
  C8  every stored probe re-evaluates to its stored pass value           (HARD)
  C9  cross-artifact bindings (declared F0 hash) still match disk        (HARD)
  C10 open obligations unchanged (AMB-01/02/03/15 present)               (HARD)

Usage: python3 artifacts/flash-04/f1_ambiguity/verify_freeze_current.py
Exit: 0 = no hard failure (soft drift findings may be present); 2 = hard check failed.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CANON_SCHEMA = ROOT / "schemas/af_wcc_vacuum.yaml"
AUTH_SCHEMA = ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
SUITE = ROOT / "schemas/f1_falsifier_tests.jsonl"
PREV_REPORT = ROOT / "artifacts/flash-04/f1_ambiguity/rebind_current_delta_report.json"
REPORT = ROOT / "artifacts/flash-04/f1_ambiguity/frozen_current_verification.json"
ADJUDICATION = ROOT / "artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md"
RULE_SPEC = ROOT / "artifacts/formulation/rule_spec.json"
ALIASES = ROOT / "artifacts/formulation/VOCAB_ALIASES.json"
TAXONOMY_AUTHOR = ROOT / "artifacts/formulation/formulation_taxonomy.yaml"
F0 = ROOT / "research_map/formulation_taxonomy.yaml"

CLASS_ID = "AF-WCC-VAC-GEN"
NODE_ID = "F1"
GATE = "G-FORM"
CST = timezone(timedelta(hours=8))
REQUIRED_ROW_KEYS = (
    "test_id", "class_id", "node_id", "gate", "spacetime_description",
    "does_it_satisfy_f1", "deciding_field", "falsifier", "next_falsifier",
    "evidence_refs", "binding_sha256",
)
OPEN_OBLIGATIONS = ("F1-AMB-01", "F1-AMB-02", "F1-AMB-03", "F1-AMB-15")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ref(path: str, digest: str, chars: int = 16) -> str:
    return f"{path}#sha256:{digest[:chars]}"


_TOKEN = re.compile(r"([^.\[\]]+)|\[(\d+)\]")


def getpath(doc, path: str):
    cur = doc
    for name, idx in _TOKEN.findall(path):
        if name:
            if isinstance(cur, dict) and name in cur:
                cur = cur[name]
            else:
                return False, None
        else:
            if isinstance(cur, list) and int(idx) < len(cur):
                cur = cur[int(idx)]
            else:
                return False, None
    return True, cur


def flat(value) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def probe(doc, spec: dict) -> dict:
    found, value = getpath(doc, spec["path"])
    kind = spec["kind"]
    needle = spec.get("value", spec.get("expected"))  # stored rows serialise the needle as "expected"
    if kind in ("path_exists", "nonnull"):
        ok = found and value is not None
    elif kind == "is_none":
        ok = (not found) or value is None
    elif kind == "is_true":
        ok = value is True
    elif kind == "equals":
        ok = found and value == needle
    elif kind == "contains":
        ok = found and value is not None and needle in flat(value)
    elif kind == "contains_any":
        ok = found and value is not None and any(n in flat(value) for n in needle)
    elif kind == "length_ge":
        ok = found and isinstance(value, (list, dict, str)) and len(value) >= needle
    else:
        raise ValueError(f"unknown probe kind {kind!r}")
    return {"path": spec["path"], "kind": kind, "found": found, "pass": bool(ok)}


def main() -> int:
    checks: list[dict] = []
    failures: list[str] = []
    drift_findings: list[dict] = []

    def check(cid: str, what: str, ok: bool, detail, severity: str = "hard") -> None:
        checks.append({"id": cid, "what": what, "result": "pass" if ok else "fail",
                       "severity": severity, "detail": detail})
        if not ok:
            if severity == "hard":
                failures.append(cid)
            else:
                drift_findings.append({"id": cid, "what": what, "detail": detail})

    required = (CANON_SCHEMA, AUTH_SCHEMA, FROZEN, SUITE)
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        print(json.dumps({"error": "missing required file(s)", "missing": missing}, indent=1))
        return 2

    measured = {str(p.relative_to(ROOT)): sha256_file(p) for p in
                (CANON_SCHEMA, AUTH_SCHEMA, FROZEN, SUITE, F0, TAXONOMY_AUTHOR,
                 ADJUDICATION, RULE_SPEC, ALIASES) if p.exists()}

    # --- suite first: the suite's own binding is the expected sha -------------------------
    rows, parse_errors = [], []
    for i, line in enumerate(SUITE.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception as exc:  # noqa: BLE001
            parse_errors.append({"line": i, "error": str(exc)})
    ids = [r.get("test_id") for r in rows]
    dupes = sorted({x for x in ids if ids.count(x) > 1})
    bindings = sorted({r.get("binding_sha256") for r in rows})
    suite_binding = bindings[0] if len(bindings) == 1 else None
    check("C4", "suite parses as JSON lines with unique test ids",
          not parse_errors and len(rows) >= 10 and not dupes,
          {"records": len(rows), "parse_errors": parse_errors, "duplicate_ids": dupes})
    check("C6", "all rows agree on one binding sha256 and the class/node/gate constants",
          suite_binding is not None and all(
              r.get("class_id") == CLASS_ID and r.get("node_id") == NODE_ID and r.get("gate") == GATE
              for r in rows),
          {"distinct_bindings": bindings, "rows": len(rows)})

    frozen = json.loads(FROZEN.read_text())
    entry = frozen.get("files", {}).get("artifacts/formulation/schemas/af_wcc_vacuum.yaml", {})
    canon_entry = frozen.get("files", {}).get("schemas/af_wcc_vacuum.yaml", {})
    canon_pin, auth_pin = canon_entry.get("sha256"), entry.get("sha256")

    # C1a canonical == suite binding (HARD)
    check("C1a", "canonical on-disk F1 schema sha256 equals the suite binding sha256",
          suite_binding is not None and measured.get("schemas/af_wcc_vacuum.yaml") == suite_binding,
          {"suite_binding": suite_binding, "canonical_measured": measured.get("schemas/af_wcc_vacuum.yaml")})
    # C1b FROZEN canonical pin == suite binding (SOFT: prefreeze lag)
    check("C1b", "FROZEN manifest canonical pin equals the suite binding sha256",
          canon_pin == suite_binding,
          {"frozen_revision": frozen.get("revision"), "frozen_canonical_pin": canon_pin,
           "suite_binding": suite_binding,
           "note": "canonical-path policy makes the canonical file authoritative; an unpinned but byte-identical canonical file is a prefreeze lag, not a stale suite"},
          severity="soft")
    # C2 authoring mirror vs canonical (SOFT)
    auth_ok = (measured.get("artifacts/formulation/schemas/af_wcc_vacuum.yaml") == suite_binding
               and auth_pin == suite_binding)
    check("C2", "authoring mirror equals canonical and its FROZEN pin",
          auth_ok,
          {"authoring_measured": measured.get("artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
           "frozen_authoring_pin": auth_pin, "canonical": measured.get("schemas/af_wcc_vacuum.yaml")},
          severity="soft")

    # C3 record check vs the last submitted report (if present)
    prev = json.loads(PREV_REPORT.read_text()) if PREV_REPORT.exists() else {}
    check("C3", "last rebind report's suite/binding fields match the suite on disk",
          (not prev) or (prev.get("suite_sha256") == measured.get("schemas/f1_falsifier_tests.jsonl")
                         and prev.get("binding", {}).get("sha256") == suite_binding),
          {"prev_report": str(PREV_REPORT.relative_to(ROOT)) if prev else None,
           "prev_suite_sha256": prev.get("suite_sha256"),
           "suite_measured": measured.get("schemas/f1_falsifier_tests.jsonl"),
           "prev_binding": prev.get("binding", {}).get("sha256"), "suite_binding": suite_binding})

    # C5 acceptance
    incomplete = [{"test_id": r.get("test_id"),
                   "missing_or_empty": [k for k in REQUIRED_ROW_KEYS if not r.get(k)]}
                  for r in rows if any(not r.get(k) for k in REQUIRED_ROW_KEYS)]
    sat_ok = all(r.get("does_it_satisfy_f1") in {"yes", "no", "ambiguous"} for r in rows)
    check("C5", "assignment acceptance: >=10 ambiguity tests with spacetime description, F1 verdict and deciding field",
          len(rows) >= 10 and not incomplete and sat_ok,
          {"tests_total": len(rows), "acceptance_met": len(rows) >= 10,
           "incomplete_rows": incomplete, "does_it_satisfy_f1_values_valid": sat_ok})

    # C7 deciding fields resolve
    schema = yaml.safe_load(CANON_SCHEMA.read_text())
    unresolved, fields_checked = [], 0
    for r in rows:
        for field in [r.get("deciding_field", "")] + list(r.get("deciding_field_alternates") or []):
            if not field:
                continue
            fields_checked += 1
            found, _ = getpath(schema, field)
            if not found:
                unresolved.append({"test_id": r.get("test_id"), "field": field})
    check("C7", "every deciding_field and alternate resolves in the canonical schema",
          not unresolved, {"fields_checked": fields_checked, "unresolved": unresolved})

    # C8 stored probes re-evaluate
    probe_total = probe_pass = 0
    mismatches = []
    for r in rows:
        for p in r.get("probe_results", []):
            probe_total += 1
            got = probe(schema, p)
            if got["pass"]:
                probe_pass += 1
            if got["pass"] != bool(p.get("pass")):
                mismatches.append({"test_id": r.get("test_id"), "path": p.get("path"),
                                   "kind": p.get("kind"), "stored": p.get("pass"),
                                   "remeasured": got["pass"]})
    check("C8", "all stored probes re-evaluate to their stored pass value",
          probe_total > 0 and not mismatches,
          {"probes_total": probe_total, "probes_pass": probe_pass, "mismatches": mismatches})

    # C9 cross-artifact bindings match disk
    cross_bad, cross_checked = [], 0
    for r in rows:
        xas = r.get("cross_artifact")
        xas = xas if isinstance(xas, list) else ([xas] if xas else [])
        for xa in xas:
            cross_checked += 1
            p = ROOT / xa["path"]
            actual = sha256_file(p) if p.exists() else None
            if actual != xa.get("sha256"):
                cross_bad.append({"test_id": r.get("test_id"), "path": xa.get("path"),
                                  "stored": xa.get("sha256"), "actual": actual})
    check("C9", "cross-artifact bindings (declared F0 hash) still match disk",
          not cross_bad, {"checked": cross_checked, "stale": cross_bad})

    # C10 open obligations
    by_id = {r.get("test_id"): r for r in rows}
    check("C10", "the four accepted open obligations remain present as tests",
          all(t in by_id for t in OPEN_OBLIGATIONS),
          {"expected": list(OPEN_OBLIGATIONS),
           "present": {t: by_id.get(t, {}).get("deciding_field_status") for t in OPEN_OBLIGATIONS}})

    verdict = "verify_fail" if failures else (
        "verify_pass_with_drift_findings" if drift_findings else "verify_pass")
    report = {
        "report_id": "w04-f1-freeze-verification",
        "created_at": now(),
        "actor": "deepseek-flash-04",
        "role": "bounded worker; read-only re-verification; no map mutation, no gate verdict, no status promotion",
        "assignment_ref": "comms/inbox/deepseek-flash-04.jsonl:1 (asg-2026-09-11-F1-deepseek-flash-04-13)",
        "node_id": NODE_ID,
        "class_id": CLASS_ID,
        "gate": GATE,
        "suite_binding_sha256": suite_binding,
        "freeze_state": {"frozen_revision": frozen.get("revision"),
                         "canonical_pin": canon_pin, "authoring_pin": auth_pin,
                         "canonical_measured": measured.get("schemas/af_wcc_vacuum.yaml"),
                         "authoring_measured": measured.get("artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
                         "pinned": canon_pin == suite_binding},
        "measured_hashes": measured,
        "acceptance": {"criterion": ">=10 ambiguity tests: spacetime description + does it satisfy F1? + which field decides.",
                       "tests_total": len(rows), "acceptance_met": len(rows) >= 10},
        "checks": checks,
        "probe_recheck": {"probes_total": probe_total, "probes_pass": probe_pass, "mismatches": mismatches},
        "deciding_field_resolution": {"fields_checked": fields_checked, "unresolved": unresolved},
        "cross_artifact_checks": {"checked": cross_checked, "stale": cross_bad},
        "open_obligations": {t: by_id.get(t, {}).get("deciding_field_status") for t in OPEN_OBLIGATIONS},
        "drift_findings": drift_findings,
        "failures": failures,
        "verdict": verdict,
        "falsifier": "A canonical on-disk F1 schema sha256 differing from the suite binding, a suite row whose deciding_field does not resolve, a stored probe that no longer evaluates to its recorded pass value, or a declared-F0 binding whose artifact hash no longer matches disk.",
        "next_falsifier": "A FROZEN revision that republishes the canonical F1 schema at a new sha256 without a suite rebind; a canonical republish that leaves the authoring mirror or the FROZEN pin behind; an open obligation (AMB-01/02/03/15) closed without L1/L0 evidence; or a G-FORM verdict citing a revision label instead of a sha256.",
        "evidence_refs": [
            ref("schemas/af_wcc_vacuum.yaml", measured.get("schemas/af_wcc_vacuum.yaml", "")),
            ref("artifacts/formulation/schemas/af_wcc_vacuum.yaml", measured.get("artifacts/formulation/schemas/af_wcc_vacuum.yaml", "")),
            ref("artifacts/formulation/FROZEN.json", measured.get("artifacts/formulation/FROZEN.json", "")),
            ref("schemas/f1_falsifier_tests.jsonl", measured.get("schemas/f1_falsifier_tests.jsonl", "")),
            ref("research_map/formulation_taxonomy.yaml", measured.get("research_map/formulation_taxonomy.yaml", "")),
            ref("artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md", measured.get("artifacts/formulation/reviews/ADJUDICATION_flash04_ambiguity.md", "")),
            ref("artifacts/formulation/rule_spec.json", measured.get("artifacts/formulation/rule_spec.json", "")),
            ref("artifacts/formulation/VOCAB_ALIASES.json", measured.get("artifacts/formulation/VOCAB_ALIASES.json", "")),
            ref("artifacts/formulation/formulation_taxonomy.yaml", measured.get("artifacts/formulation/formulation_taxonomy.yaml", "")),
            "comms/inbox/deepseek-flash-04.jsonl:1-3",
        ],
        "reproduce": "python3 artifacts/flash-04/f1_ambiguity/verify_freeze_current.py",
    }
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({
        "verdict": verdict,
        "failures": failures,
        "drift_findings": [d["id"] for d in drift_findings],
        "frozen_revision": frozen.get("revision"),
        "suite_binding": suite_binding,
        "canonical_sha256": measured.get("schemas/af_wcc_vacuum.yaml"),
        "authoring_sha256": measured.get("artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
        "tests_total": len(rows),
        "probes_total": probe_total,
        "probes_pass": probe_pass,
        "probe_mismatches": len(mismatches),
        "unresolved_deciding_fields": len(unresolved),
        "stale_cross_artifacts": len(cross_bad),
        "report": str(REPORT.relative_to(ROOT)),
        "report_sha256": sha256_file(REPORT),
    }, indent=1))
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())

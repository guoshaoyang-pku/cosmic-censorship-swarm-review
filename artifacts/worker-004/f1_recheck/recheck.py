#!/usr/bin/env python3
"""W04-F1-POSTREBIND-RECHECK-01 — read-only recheck of the F1 review surface.

Assignment : asg-2026-09-11-F1-deepseek-flash-04-13
Node       : F1
Class      : AF-WCC-VAC-GEN
Gate       : G-FORM
Runtime    : worker-004-20260912T002201-968807 (actor deepseek-flash-04)

Purpose
-------
After the 00:20:49 rebind of `schemas/f1_falsifier_tests.jsonl` to the frozen
canonical F1 hash 9a8bd4c9, recheck the live review surface:

  D2  falsify reviewer-090 finding F090-04 ("suite is bound to b65fcc0f, 24 rows,
      cannot be cited for the reviewed bytes") against the on-disk suite;
  D3  reproduce HF090-01  class_contract_pointer targets the authoring tree and
      does not resolve against the canonical taxonomy;
  D4  reproduce HF090-02 / HF-094-2 duplicate `revised_at` keys and future-dated
      effective timestamp;
  D5  reproduce HF090-03  normative symbol AF_{I+} has no definition;
  D6  reproduce F090-05  taxonomy_consistency.json carries no content hashes;
  D7  measure whether the 25-row suite probes any of D3-D6 (coverage gap);
  D1  record the in-place-write defect of verify_freeze_current.py, which
      superseded the previously published report hash 9fa4f77c with 0e79514a
      during this worker slot merely by being invoked.

The script is strictly read-only over the repository: its only write is the
optional `--out` JSON report (default: stdout).  It does not import or run any
artifact-producing tool.  It fails closed (exit 2) if the canonical F1 file hash
differs from --expect-sha (default 9a8bd4c9), so a report can never silently
describe stale bytes.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

F1 = ROOT / "schemas" / "af_wcc_vacuum.yaml"
F0_CANONICAL = ROOT / "research_map" / "formulation_taxonomy.yaml"
F0_AUTHORING = ROOT / "artifacts" / "formulation" / "formulation_taxonomy.yaml"
FROZEN = ROOT / "artifacts" / "formulation" / "FROZEN.json"
SUITE = ROOT / "schemas" / "f1_falsifier_tests.jsonl"
RULE_SPEC = ROOT / "artifacts" / "formulation" / "rule_spec.json"
TAX_CONSISTENCY = ROOT / "artifacts" / "formulation" / "evidence" / "taxonomy_consistency.json"
PRIOR_VERIFIER = ROOT / "artifacts" / "flash-04" / "f1_ambiguity" / "verify_freeze_current.py"
PRIOR_VERIFY_REPORT = ROOT / "artifacts" / "flash-04" / "f1_ambiguity" / "frozen_current_verification.json"
PRIOR_REPORT_PUBLISHED_SHA = "9fa4f77c322ea51f"  # cited by event flash-04-art-F1-freeze-verify-20260912T002049

EXPECTED_F1_SHA = "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503"
NODE = "F1"
CLASS_ID = "AF-WCC-VAC-GEN"
GATE = "G-FORM"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha_ref(path: Path) -> str:
    try:
        return f"{path.relative_to(ROOT).as_posix()}#sha256:{sha256(path)[:12]}"
    except FileNotFoundError:
        return f"{path.relative_to(ROOT).as_posix()}#sha256:MISSING"


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=8))).isoformat(timespec="seconds")


def load_yaml(path: Path):
    import yaml  # local import: fail loudly if PyYAML is absent
    with path.open("rb") as fh:
        return yaml.safe_load(fh)


def resolve_fragment(doc, fragment: str):
    """Resolve 'a.b.c' against nested dicts; return (status, value)."""
    cur = doc
    for part in fragment.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return "unresolved", None
    return "resolved", cur


def duplicate_top_level_keys(text: str):
    seen: dict[str, list[int]] = {}
    for lineno, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):", line)
        if m:
            seen.setdefault(m.group(1), []).append(lineno)
    return {k: v for k, v in seen.items() if len(v) > 1}


def raw_last_value(text: str, key: str):
    last = None
    for line in text.splitlines():
        m = re.match(rf"^{re.escape(key)}:\s*(.*)$", line)
        if m:
            last = m.group(1).strip().strip('"')
    return last


def check_d1_verifier_write_defect():
    src = PRIOR_VERIFIER.read_text() if PRIOR_VERIFIER.exists() else ""
    writes_in_place = bool(re.search(r"REPORT\.write_text\(", src))
    has_argparse = "argparse" in src
    measured = sha256(PRIOR_VERIFY_REPORT) if PRIOR_VERIFY_REPORT.exists() else None
    return {
        "id": "D1",
        "claim": (
            "artifacts/flash-04/f1_ambiguity/verify_freeze_current.py rewrites its own "
            "hash-pinned report in place on every invocation (including `--help`), so the "
            "report hash published by event flash-04-art-F1-freeze-verify-20260912T002049 "
            "was superseded during this worker slot."
        ),
        "result": "confirmed",
        "severity": "major",
        "evidence": [
            sha_ref(PRIOR_VERIFIER),
            sha_ref(PRIOR_VERIFY_REPORT),
        ],
        "measured": {
            "prior_published_report_sha256_prefix": PRIOR_REPORT_PUBLISHED_SHA,
            "measured_report_sha256_prefix": measured[:12] if measured else None,
            "published_hash_still_matches_disk": bool(measured and measured.startswith(PRIOR_REPORT_PUBLISHED_SHA)),
            "report_mtime": _dt.datetime.fromtimestamp(
                PRIOR_VERIFY_REPORT.stat().st_mtime, _dt.timezone(_dt.timedelta(hours=8))
            ).isoformat(timespec="seconds") if PRIOR_VERIFY_REPORT.exists() else None,
            "script_writes_in_place": writes_in_place,
            "script_has_argparse": has_argparse,
            "superseded_by_this_worker_slot": True,
            "trigger": (
                "this worker invoked `python3 artifacts/flash-04/f1_ambiguity/"
                "verify_freeze_current.py --help` at 2026-09-12T00:25:01+08:00; the script "
                "has no argparse and unconditionally executed its full verification, "
                "rewriting the report in place. Self-reported drift, not a hidden one."
            ),
        },
        "falsifier": (
            "Restore artifacts/flash-04/f1_ambiguity/frozen_current_verification.json to a "
            "file whose sha256 starts with 9fa4f77c and re-measure: if the published evidence "
            "ref resolves again, D1 is void. Or show the script supports --out and never "
            "writes REPORT in place."
        ),
    }


def check_d2_suite_rebind():
    rows = []
    parse_errors = []
    for i, line in enumerate(SUITE.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            parse_errors.append({"line": i, "error": str(exc)})
    bindings = sorted({str(r.get("binding_sha256")) for r in rows})
    acceptance = ("spacetime_description", "does_it_satisfy_f1", "deciding_field")
    incomplete = [r.get("test_id") for r in rows if any(k not in r or r.get(k) in (None, "") for k in acceptance)]
    citation = {}
    for r in rows:
        key = str(r.get("citation_status"))
        citation[key] = citation.get(key, 0) + 1
    return {
        "id": "D2",
        "claim": (
            "reviewer-090 finding F090-04 asserts the suite is bound to b65fcc0f with 24 rows "
            "and cannot be cited for the reviewed bytes; the on-disk suite is measured against "
            "that assertion"
        ),
        "result": "finding_refuted" if (len(rows) and bindings == [EXPECTED_F1_SHA]) else "finding_stands",
        "severity": "major",
        "evidence": [sha_ref(SUITE), sha_ref(F1), sha_ref(FROZEN)],
        "measured": {
            "rows": len(rows),
            "parse_errors": parse_errors,
            "distinct_bindings": bindings,
            "bound_to_reviewed_hash": bindings == [EXPECTED_F1_SHA],
            "acceptance_fields_present_for_all_rows": not incomplete,
            "incomplete_rows": incomplete,
            "citation_status_counts": citation,
            "f090_04_text_measured": "24 rows bound to binding_sha256 b65fcc0f0118",
        },
        "falsifier": (
            "Re-measure schemas/f1_falsifier_tests.jsonl: if any row carries a binding_sha256 "
            "other than 9a8bd4c9, or the row count is not 25, F090-04 stands and D2 is void."
        ),
    }


def check_d3_pointer():
    text = F1.read_text()
    m = re.search(r"^class_contract_pointer:\s*(\S+)\s*$", text, re.M)
    raw = m.group(1) if m else None
    line = text.splitlines().index(m.group(0)) + 1 if m else None
    path_part, _, fragment = (raw or "").partition("#")
    target = ROOT / path_part
    out = {
        "id": "D3",
        "claim": (
            "HF090-01 reproduced: class_contract_pointer targets the authoring tree and its "
            "fragment does not resolve against the canonical taxonomy, while "
            "f0_binding.declared_f0_artifact names the canonical path"
        ),
        "result": "confirmed",
        "severity": "major",
        "evidence": [sha_ref(F1), sha_ref(F0_CANONICAL), sha_ref(F0_AUTHORING)],
        "measured": {
            "raw": raw,
            "line": line,
            "declared_target": path_part,
            "fragment": fragment,
            "declared_target_is_canonical": path_part == "research_map/formulation_taxonomy.yaml",
            "declared_target_exists": target.exists(),
        },
        "falsifier": (
            "Point the pointer at research_map/formulation_taxonomy.yaml#classes.AF-WCC-VAC-GEN "
            "(or publish the authoring tree byte-identically and name that hash); then the "
            "fragment resolves against the authoritative tree and D3 is void."
        ),
    }
    if target.exists():
        doc = load_yaml(target)
        status, value = resolve_fragment(doc, fragment)
        out["measured"]["resolves_in_declared_target"] = status
        out["measured"]["declared_value_keys"] = sorted(value.keys()) if isinstance(value, dict) else None
        out["measured"]["canonical_top_level_keys"] = sorted(load_yaml(F0_CANONICAL).keys())
        can_status, _ = resolve_fragment(load_yaml(F0_CANONICAL), fragment)
        out["measured"]["resolves_in_canonical"] = can_status
        out["measured"]["canonical_equivalent_fragment"] = "classes.AF-WCC-VAC-GEN"
        can_equiv_status, _ = resolve_fragment(load_yaml(F0_CANONICAL), "classes.AF-WCC-VAC-GEN")
        out["measured"]["canonical_equivalent_resolves"] = can_equiv_status
        out["result"] = "confirmed" if (status == "resolved" and can_status == "unresolved") else "not_refuted"
    return out


def check_d4_clock():
    text = F1.read_text()
    dupes = duplicate_top_level_keys(text)
    eff = raw_last_value(text, "revised_at")
    mtime = _dt.datetime.fromtimestamp(F1.stat().st_mtime, _dt.timezone(_dt.timedelta(hours=8)))
    wall = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=8)))
    eff_dt = None
    if eff:
        try:
            eff_dt = _dt.datetime.fromisoformat(eff)
        except ValueError:
            eff_dt = None
    future_vs_mtime = bool(eff_dt and eff_dt > mtime)
    future_vs_wall = bool(eff_dt and eff_dt > wall)
    return {
        "id": "D4",
        "claim": (
            "HF090-02 / HF-094-2 reproduced: duplicate top-level revised_at keys and a "
            "future-dated effective (last-wins) revision timestamp"
        ),
        "result": "confirmed" if (dupes and (future_vs_mtime or future_vs_wall)) else "not_refuted",
        "severity": "major",
        "evidence": [sha_ref(F1), sha_ref(PRIOR_VERIFIER)],
        "measured": {
            "duplicate_top_level_keys": dupes,
            "effective_revised_at_last_wins": eff,
            "effective_is_future_vs_file_mtime": future_vs_mtime,
            "effective_is_future_vs_wall_clock": future_vs_wall,
            "file_mtime": mtime.isoformat(timespec="seconds"),
            "wall_clock": wall.isoformat(timespec="seconds"),
            "duplicate_revised_at_count": len(dupes.get("revised_at", [])),
            "duplicate_revised_at_unused_count": len(dupes.get("revised_at_unused", [])),
        },
        "falsifier": (
            "Deduplicate the keys so a single wall-clock-valid revised_at remains; then the "
            "effective timestamp is unique and not future-dated and D4 is void."
        ),
    }


def check_d5_undefined_symbol():
    token = "AF_{I+}"
    occurrences = []
    for path in (F1, F0_CANONICAL, F0_AUTHORING, RULE_SPEC):
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if token in line or "AF_{I" in line:
                occurrences.append({"path": path.relative_to(ROOT).as_posix(), "line": lineno,
                                    "context": line.strip()[:200]})
    f1_hits = [o for o in occurrences if o["path"] == "schemas/af_wcc_vacuum.yaml"]
    taxonomy_hits = [o for o in occurrences if "taxonomy" in o["path"]]
    definition_lines = []
    for o in occurrences:
        ctx = o["context"].lower()
        if any(k in ctx for k in ("def ", "definition", ":=", "means ", "abbrev")):
            definition_lines.append(o)
    return {
        "id": "D5",
        "claim": "HF090-03 reproduced: the normative symbol AF_{I+} in conclusion.statement_formal has no definition",
        "result": "confirmed" if (f1_hits and not definition_lines) else "not_refuted",
        "severity": "major",
        "evidence": [sha_ref(F1), sha_ref(F0_CANONICAL), sha_ref(F0_AUTHORING), sha_ref(RULE_SPEC)],
        "measured": {
            "token": token,
            "occurrences_in_F1": len(f1_hits),
            "F1_occurrences": f1_hits,
            "occurrences_in_taxonomies": len(taxonomy_hits),
            "taxonomy_occurrences": taxonomy_hits,
            "explicit_definition_lines": definition_lines,
        },
        "falsifier": (
            "Add a definition of AF_{I+} to the schema or inline the predicate in "
            "conclusion.statement_formal; then a reader no longer has to recover it from "
            "quantifiers.formal and D5 is void."
        ),
    }


def check_d6_consistency_evidence():
    data = None
    if TAX_CONSISTENCY.exists():
        data = json.loads(TAX_CONSISTENCY.read_text())
    blob = json.dumps(data) if data is not None else ""
    has_sha = bool(re.search(r"[0-9a-f]{12,64}", blob))
    return {
        "id": "D6",
        "claim": (
            "F090-05 reproduced: artifacts/formulation/evidence/taxonomy_consistency.json "
            "asserts consistent=true without any sha256 of the two compared trees, so the "
            "evidence cannot be pinned to the F0 revision pair it claims to compare"
        ),
        "result": "confirmed" if (data is not None and data.get("consistent") is True and not has_sha) else "not_refuted",
        "severity": "minor",
        "evidence": [sha_ref(TAX_CONSISTENCY), sha_ref(F0_CANONICAL), sha_ref(F0_AUTHORING)],
        "measured": {
            "exists": TAX_CONSISTENCY.exists(),
            "consistent": None if data is None else data.get("consistent"),
            "contains_content_hash": has_sha,
            "keys": None if data is None else sorted(data.keys()),
        },
        "falsifier": (
            "Re-publish taxonomy_consistency.json with the measured sha256 of both compared "
            "trees; then the assertion is bindable and D6 is void."
        ),
    }


def check_d7_coverage():
    text = SUITE.read_text()
    probes = {
        "class_contract_pointer": "class_contract_pointer" in text,
        "revised_at_hygiene": "revised_at" in text,
        "AF_{I+}_symbol": "AF_{I+" in text,
        "taxonomy_consistency_evidence": "taxonomy_consistency" in text,
        "f0_binding_equality": "declared_f0_sha256" in text,
    }
    return {
        "id": "D7",
        "claim": (
            "the 25-row suite probes the F0 hash binding but none of the three reproduced "
            "hard failures (pointer resolution, YAML clock/key hygiene, undefined AF_{I+})"
        ),
        "result": "confirmed" if (probes["f0_binding_equality"] and not any(
            probes[k] for k in ("class_contract_pointer", "revised_at_hygiene", "AF_{I+}_symbol")
        )) else "not_refuted",
        "severity": "minor",
        "evidence": [sha_ref(SUITE)],
        "measured": {"probe_surfaces_present": probes},
        "falsifier": (
            "Show a suite row whose deciding_field or predicate evaluates "
            "class_contract_pointer, revised_at or AF_{I+}; then the suite already covers the "
            "defect surface and D7 is void."
        ),
    }


def check_crossref_w037():
    hits = []
    for name in ("af_wcc_vacuum.yaml", "af_scc_c2_vacuum.yaml", "af_scc_c0_vacuum.yaml"):
        path = ROOT / "schemas" / name
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"forall \(s,delta\) in D0", line):
                hits.append({"path": path.relative_to(ROOT).as_posix(), "line": lineno,
                             "context": line.strip()[:160], "sha256_prefix": sha256(path)[:12]})
    return {
        "id": "X1",
        "claim": "observed only, not adjudicated: worker-037 W037-F5 D0-disjunction surface is present in the class schemas",
        "result": "observed",
        "severity": "info",
        "evidence": [sha_ref(ROOT / "schemas" / "af_wcc_vacuum.yaml")],
        "measured": {"hits": hits},
        "falsifier": "Belongs to worker-037's falsifier: re-run its witness after any D0 edit.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None, help="write report JSON here (default: stdout)")
    ap.add_argument("--expect-sha", default=EXPECTED_F1_SHA[:8],
                    help="expected canonical F1 sha256 prefix; mismatch fails closed")
    args = ap.parse_args()

    missing = [p.relative_to(ROOT).as_posix() for p in
               (F1, F0_CANONICAL, F0_AUTHORING, FROZEN, SUITE, PRIOR_VERIFIER, PRIOR_VERIFY_REPORT)
               if not p.exists()]
    if missing:
        print(json.dumps({"error": "missing required file(s)", "missing": missing}, indent=1))
        return 2

    f1_sha = sha256(F1)
    if not f1_sha.startswith(args.expect_sha):
        print(json.dumps({
            "error": "schema_drift",
            "expected_prefix": args.expect_sha,
            "measured_sha256": f1_sha,
            "action": "fail-closed: re-bind the worker task to the new hash before reporting",
        }, indent=1))
        return 2

    frozen = json.loads(FROZEN.read_text())
    try:
        suite_sha = sha256(SUITE)
        report = {
            "report_id": "w04-f1-postrebind-recheck",
            "created_at": now_iso(),
            "actor": "deepseek-flash-04",
            "runtime_instance": "worker-004-20260912T002201-968807",
            "role": "bounded worker; read-only recheck; no map mutation, no gate verdict, no status promotion",
            "assignment_ref": "comms/inbox/deepseek-flash-04.jsonl:1 (asg-2026-09-11-F1-deepseek-flash-04-13)",
            "node_id": NODE,
            "class_id": CLASS_ID,
            "gate": GATE,
            "binding": {
                "path": "schemas/af_wcc_vacuum.yaml",
                "sha256": f1_sha,
                "freeze_manifest_revision": frozen.get("revision"),
                "freeze_manifest_sha256": sha256(FROZEN),
                "frozen_pin_matches_measured": (
                    frozen.get("files", {}).get("schemas/af_wcc_vacuum.yaml", {}).get("sha256") == f1_sha
                ),
                "suite_path": "schemas/f1_falsifier_tests.jsonl",
                "suite_sha256": suite_sha,
            },
            "checks": [
                check_d1_verifier_write_defect(),
                check_d2_suite_rebind(),
                check_d3_pointer(),
                check_d4_clock(),
                check_d5_undefined_symbol(),
                check_d6_consistency_evidence(),
                check_d7_coverage(),
                check_crossref_w037(),
            ],
        }
    except Exception as exc:  # noqa: BLE001 - report the failure, never a partial pass
        print(json.dumps({"error": "recheck_crashed", "exception": repr(exc)}, indent=1))
        return 2

    confirmed = [c["id"] for c in report["checks"] if c["result"] == "confirmed"]
    refuted = [c["id"] for c in report["checks"] if c["result"] == "finding_refuted"]
    report["summary"] = {
        "confirmed_defects": confirmed,
        "prior_finding_F090_04": (
            "falsified_at_current_hash" if "D2" in refuted else "stands_at_current_hash"
        ),
        "review_recommendation": "revise" if any(
            c["id"] in {"D1", "D3", "D4", "D5"} for c in report["checks"] if c["result"] == "confirmed"
        ) else "no_blocking_defect_found",
        "gate_verdict_claimed": False,
        "node_status_claimed": False,
    }
    report["falsifier"] = (
        "A reader who (a) shows schemas/f1_falsifier_tests.jsonl is not bound to "
        f"{f1_sha[:8]}, (b) resolves class_contract_pointer against the canonical taxonomy, "
        "(c) parses a unique non-future revised_at from schemas/af_wcc_vacuum.yaml, or "
        "(d) finds an explicit definition of AF_{I+}, refutes the corresponding D-check."
    )
    report["reproduce"] = (
        "python3 artifacts/worker-004/f1_recheck/recheck.py "
        f"--expect-sha {f1_sha[:8]} --out artifacts/worker-004/f1_recheck/report.json"
    )

    payload = json.dumps(report, indent=1, ensure_ascii=False, default=str) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload)
        print(json.dumps({
            "wrote": str(out),
            "sha256": hashlib.sha256(payload.encode()).hexdigest(),
            "summary": report["summary"],
        }, indent=1))
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

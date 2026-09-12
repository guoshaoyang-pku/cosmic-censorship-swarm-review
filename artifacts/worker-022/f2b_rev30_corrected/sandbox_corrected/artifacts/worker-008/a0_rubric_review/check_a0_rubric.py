#!/usr/bin/env python3
"""Independent A0 rubric conformance check — worker-008 (bounded execution worker).

Task: independent review of evaluation_rubric.yaml (node A0, gate G-AUDIT) at a measured
sha256. Read-only on all inputs; writes only its own report next to this file.

Checks are keyed to the A0 assignment acceptance (asg-2026-09-11-A0-astra-lead-audit-07):
  per-task-type verifier definitions (schema, literature, numerics, formal);
  hard-failure list; no universal scalar score;
  every acceptance test machine-checkable or reviewer-adjudicated with named evidence.

Class binding: the rubric's frozen_classes block must equal the four canonical class ids in
research_map/formulation_taxonomy.yaml, and no unknown AF-* token may appear in the rubric.

Usage:
  python3 artifacts/worker-008/a0_rubric_review/check_a0_rubric.py [--audit-run-report PATH]
Exit 0 = all checks pass; 1 = at least one check failed; 2 = inputs unreadable.
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

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

RUBRIC_PATH = ROOT / "evaluation_rubric.yaml"
TAXONOMY_PATH = ROOT / "research_map" / "formulation_taxonomy.yaml"
MAP_PATH = ROOT / "research_map" / "research_map.json"
REGISTRY_PATH = ROOT / "runtime" / "state" / "artifact_hashes.json"

EXPECTED_CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
REQUIRED_VERIFIERS = ["schema_formulation", "literature", "numerics", "formalization"]
CLASS_TOKEN = re.compile(r"\bAF-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
SCALAR_KEY = re.compile(
    r"^(overall|total|aggregate|composite|weighted|final|mean|global)_?(score|scores|rating)$", re.I
)


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def file_meta(p: Path) -> dict:
    return {
        "path": str(p.relative_to(ROOT)),
        "sha256": sha256(p),
        "bytes": p.stat().st_size,
        "mtime": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds"),
    }


def walk_strings(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def check(check_id: str, requirement: str, fn) -> dict:
    rec = {"check_id": check_id, "requirement": requirement, "status": "fail",
           "evidence": [], "detail": ""}
    try:
        status, evidence, detail = fn()
        rec.update(status=status, evidence=evidence, detail=detail)
    except Exception as exc:  # fail closed: unreadable/unexpected shape is a failure
        rec.update(status="fail", evidence=[], detail=f"check raised {type(exc).__name__}: {exc}")
    rec["severity"] = "blocking" if rec["status"] == "fail" else (
        "minor" if rec["status"] == "warn" else "none")
    return rec


RAW_LINES = RUBRIC_PATH.read_text().splitlines()


def line_of(substr: str) -> int:
    """1-based first line containing substr (for auditable citations); 0 if absent."""
    for i, line in enumerate(RAW_LINES, 1):
        if substr in line:
            return i
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit-run-report", default=None,
                    help="optional path to an artifacts/audit/audit_run.py report to attach")
    ap.add_argument("--out", default=str(HERE / "a0_check_report.json"))
    args = ap.parse_args()

    for p in (RUBRIC_PATH, TAXONOMY_PATH, MAP_PATH):
        if not p.exists():
            print(f"FATAL: missing input {p}", file=sys.stderr)
            return 2

    rubric = yaml.safe_load(RUBRIC_PATH.read_text())
    taxonomy = yaml.safe_load(TAXONOMY_PATH.read_text())
    rmap = json.loads(MAP_PATH.read_text())
    registry = json.loads(REGISTRY_PATH.read_text()) if REGISTRY_PATH.exists() else {}
    inputs = {
        "rubric": file_meta(RUBRIC_PATH),
        "taxonomy": file_meta(TAXONOMY_PATH),
        "map": file_meta(MAP_PATH),
    }

    a0 = {}
    for g in rmap.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("id") == "A0":
                a0 = n

    checks: list[dict] = []

    def c1():
        measured = inputs["rubric"]["sha256"]
        declared = a0.get("artifact_sha256_measured")
        declared_match_flag = a0.get("declared_hash_matches_measured")
        exists = a0.get("artifact_exists")
        reg_hash = (registry.get("registry", {}).get("evaluation_rubric.yaml", {}) or {}).get("sha256")
        ev = [f"evaluation_rubric.yaml#{measured[:12]}",
              f"research_map.json#groups.audit.nodes.A0.artifact_sha256_measured={str(declared)[:12]}"]
        if reg_hash:
            ev.append(f"runtime/state/artifact_hashes.json#evaluation_rubric.yaml={reg_hash[:12]}")
        bad = [(k, v) for k, v in (("exists", exists), ("declared_matches_measured", declared_match_flag))
               if v is not True]
        if measured != declared:
            return "fail", ev, f"measured {measured[:12]} != map declared {str(declared)[:12]}"
        if bad:
            return "fail", ev, f"map flags not true: {bad}"
        if reg_hash and reg_hash != measured:
            return "fail", ev, f"registry hash {reg_hash[:12]} != measured {measured[:12]}"
        return "pass", ev, "rubric bytes, map measurement and registry agree at one sha256"

    checks.append(check("A0-C1", "rubric sha256 is bound to the map's measured hash and registry",
                        c1))

    def c2():
        rubric_ids = [c.get("id") for c in rubric.get("frozen_classes", [])]
        tax_ids = taxonomy.get("class_ids")
        ev = [f"evaluation_rubric.yaml#frozen_classes={rubric_ids}",
              f"research_map/formulation_taxonomy.yaml#{inputs['taxonomy']['sha256'][:12]}#class_ids={tax_ids}"]
        if sorted(rubric_ids) != sorted(EXPECTED_CLASSES):
            return "fail", ev, f"rubric class ids {rubric_ids} != expected four {EXPECTED_CLASSES}"
        if sorted(tax_ids or []) != sorted(EXPECTED_CLASSES):
            return "fail", ev, f"taxonomy class_ids {tax_ids} != expected four"
        missing = []
        for c in rubric["frozen_classes"]:
            for field in ("dimension", "asymptotics", "matter_model", "symmetry",
                          "cosmological_constant", "formulation", "conclusion_primary",
                          "forbidden_evidence"):
                if not c.get(field) and c.get(field) != 0:
                    missing.append(f"{c.get('id')}.{field}")
        if missing:
            return "fail", ev, f"class fields missing/empty: {missing}"
        unknown = []
        for path, text in walk_strings(rubric):
            for tok in CLASS_TOKEN.findall(text):
                if tok not in EXPECTED_CLASSES and tok != "GLOBAL":
                    unknown.append(f"{tok} at {path}")
        if unknown:
            return "fail", ev + unknown[:8], f"{len(unknown)} unknown AF-* token(s) in rubric"
        return "pass", ev, "rubric frozen_classes equals the canonical four; all binding fields present; no unknown AF-* token"

    checks.append(check("A0-C2", "rubric binds exactly the four canonical classes, with no unknown class token",
                        c2))

    def c3():
        ver = rubric.get("verifiers") or {}
        ev = [f"evaluation_rubric.yaml#verifiers.keys={list(ver.keys())}"]
        missing = [k for k in REQUIRED_VERIFIERS if k not in ver]
        if missing:
            return "fail", ev, f"missing task-type verifier(s): {missing}"
        allowed_mc = (True, False, "partially", "yes", "no", "true", "false")
        bad, no_evidence = [], []
        nchecks = 0
        for name in REQUIRED_VERIFIERS:
            node = ver[name]
            if not node.get("gate"):
                bad.append(f"{name}.gate")
            if node.get("machine_checkable") not in allowed_mc:
                bad.append(f"{name}.machine_checkable={node.get('machine_checkable')!r}")
            if not node.get("checks"):
                bad.append(f"{name}.checks empty")
            else:
                nchecks += len(node["checks"])
            if not node.get("evidence"):
                no_evidence.append(f"{name} (block starts line {line_of(name + ':')})")
            if "human_adjudication_only" not in node:
                bad.append(f"{name}.human_adjudication_only absent")
        if bad:
            return "fail", ev, f"verifier field defects: {bad}"
        if no_evidence:
            return "warn", ev, ("no explicit evidence rule for " + ", ".join(no_evidence)
                                + "; only schema_formulation names `evidence:` (line "
                                + str(line_of("evidence: \"artifact bytes")) + ")")
        return "pass", ev, (f"all four task types defined; {nchecks} named machine checks; "
                            f"each verifier has a gate, evidence rule and named human-adjudication set")

    checks.append(check("A0-C3", "verifier definitions exist for schema/literature/numerics/formalization",
                        c3))

    def c4():
        hfs = rubric.get("hard_failures") or []
        ev = [f"evaluation_rubric.yaml#hard_failures={len(hfs)} ids={[h.get('id') for h in hfs]}"]
        if not hfs:
            return "fail", ev, "hard_failure taxonomy absent"
        ids = [h.get("id") for h in hfs]
        if len(ids) != len(set(ids)):
            return "fail", ev, "duplicate hard-failure ids"
        bad = []
        for h in hfs:
            if h.get("severity") not in ("critical", "major", "minor"):
                bad.append(f"{h.get('id')}.severity={h.get('severity')!r}")
            if not h.get("detector"):
                bad.append(f"{h.get('id')}.detector empty")
        if bad:
            return "fail", ev, f"hard-failure defects: {bad}"
        sev = {}
        for h in hfs:
            sev[h["severity"]] = sev.get(h["severity"], 0) + 1
        if not any(h.get("id") == "HF-01" and h.get("severity") == "critical" for h in hfs):
            return "fail", ev, "HF-01 (fluent-text promotion) missing or not critical"
        return "pass", ev, f"unique ids with severity+detector; severity counts {sev}"

    checks.append(check("A0-C4", "hard-failure taxonomy complete, unique, severity-tagged, HF-01 critical",
                        c4))

    def c5():
        nss = rubric.get("no_universal_scalar_score")
        ev = ["evaluation_rubric.yaml#no_universal_scalar_score"]
        if not isinstance(nss, str) or not nss.strip():
            return "fail", ev, "no_universal_scalar_score declaration missing"
        if "single number" not in nss or "never averaged" not in nss:
            return "fail", ev, "declaration does not state the single-number/never-averaged rule"
        hits = []
        def scan(obj, path="$"):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if path == "$" and k == "no_universal_scalar_score":
                        continue
                    if SCALAR_KEY.match(k):
                        hits.append(f"{path}.{k}")
                    scan(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    scan(v, f"{path}[{i}]")
        scan(rubric)
        if hits:
            return "fail", ev + hits, f"scalar/aggregate promotion keys present: {hits}"
        metrics = rubric.get("metrics") or {}
        bad = [n for n, m in metrics.items() if not m.get("definition")]
        no_target = [f"{n} (line {line_of(n + ':')})" for n, m in metrics.items() if not m.get("target")]
        if bad:
            return "fail", ev, f"metric(s) without definition: {bad}"
        agg = [n for n, m in metrics.items() if "averag" in str(m.get("definition", "")).lower()]
        if agg:
            return "fail", ev, f"metric(s) defined by averaging across classes: {agg}"
        rule = (rubric.get("review_protocol") or {}).get("promotion_rule", "")
        if "G-*" not in rule:
            return "fail", ev, f"promotion rule is not gate-based: {rule!r}"
        if no_target:
            return "warn", ev, ("no target for metric(s) " + ", ".join(no_target)
                                + f"; {len(metrics)} metrics otherwise diagnostic and per-type")
        return "pass", ev, (f"no scalar or aggregate promotion key; {len(metrics)} metrics are "
                            f"per-type with definition+target; promotion is gate-based")

    checks.append(check("A0-C5", "no universal scalar score anywhere in the rubric",
                        c5))

    def c6():
        gates = rubric.get("gates") or []
        ev = [f"evaluation_rubric.yaml#gates={[g.get('id') for g in gates]}"]
        bad = []
        for g in gates:
            if not g.get("criteria"):
                bad.append(f"{g.get('id')}.criteria empty")
            if "verdict" not in g:
                bad.append(f"{g.get('id')}.verdict absent")
            if not g.get("scope"):
                bad.append(f"{g.get('id')}.scope absent")
        if bad:
            return "fail", ev, f"gate defects: {bad}"
        ver = rubric.get("verifiers") or {}
        unmapped = []
        for name, node in ver.items():
            for item in node.get("human_adjudication_only", []):
                if not isinstance(item, str) or len(item.strip()) < 8:
                    unmapped.append(f"{name}: {item!r}")
        if unmapped:
            return "fail", ev, f"human-adjudication items not named evidence: {unmapped}"
        return "pass", ev, ("every gate has criteria/scope/verdict; every non-machine acceptance "
                            "item is a named human-adjudication item")

    checks.append(check("A0-C6", "gate acceptance is machine-checkable or named reviewer-adjudicated",
                        c6))

    def c7():
        rubric_gates = {g.get("id") for g in rubric.get("gates", [])}
        map_gates = {g.get("gate_id") for g in rmap.get("gates", [])}
        ev = [f"evaluation_rubric.yaml#gates={sorted(rubric_gates)}",
              f"research_map.json#gates={sorted(map_gates)}"]
        extra = rubric_gates - map_gates
        if extra:
            return "fail", ev, f"rubric declares gates absent from the map: {sorted(extra)}"
        ver_gates = {n.get("gate") for n in (rubric.get("verifiers") or {}).values()}
        formal = [g for g in ver_gates if str(g).startswith("G-FORMAL")]
        if not formal:
            return "fail", ev, "formalization verifier does not name a G-FORMAL gate"
        cross = []
        blob = json.dumps(rubric)
        for token, where in [("0.10", "hard_failure_rate<=0.10"), (">= 8", "seeds>=8"),
                             ("4 resolutions", "numerics >=4 resolutions"),
                             ("process boundary", "numerics process-boundary timeout")]:
            if token not in blob and not (token == ">= 8" and "8 seeds" in blob):
                cross.append(where)
        if cross:
            return "fail", ev, f"map/rubric invariant(s) not reflected in rubric text: {cross}"
        note = ""
        if "G-F0" in map_gates and "G-F0" not in rubric_gates:
            note = ("map gate G-F0 (taxonomy, research_map.json#gates.G-F0) has no rubric gate row; "
                    "class-id binding is covered by frozen_classes + metric class_binding, but the "
                    "taxonomy gate's disjointness test is not represented in the rubric")
            return "warn", ev, note
        return "pass", ev, "rubric gates are a subset of map gates and shared invariants are reflected"

    checks.append(check("A0-C7", "rubric gates and shared invariants agree with the research map",
                        c7))

    def c8():
        val = rubric.get("validation") or {}
        validator = val.get("validator")
        ev = [f"evaluation_rubric.yaml#validation={json.dumps(val)}",
              f"evaluation_rubric.yaml:46 (self-test requirement)"]
        if not validator:
            return "fail", ev, "declared validator missing"
        vp = ROOT / validator
        if not vp.exists():
            return "fail", ev, f"declared validator does not exist: {validator}"
        ev.append(f"{validator}#sha256={sha256(vp)[:12]}")
        if not val.get("last_run") and not val.get("report_sha256"):
            return "fail", ev, (f"declared validator has never been recorded as run "
                                f"(evaluation_rubric.yaml:{line_of('last_run: null')} last_run/report_sha256 "
                                f"null); the rubric's own line {line_of('a rubric with no passing self-test')} "
                                f"says a rubric with no passing self-test is not a gate")
        if val.get("last_run_result") not in ("pass", "passed", True):
            return "fail", ev, f"recorded self-test result is not a pass: {val.get('last_run_result')!r}"
        if not val.get("report_sha256"):
            return "fail", ev, "self-test result recorded without a report sha256"
        return "pass", ev, f"self-test recorded at {val.get('last_run')} result={val.get('last_run_result')}"

    checks.append(check("A0-C8", "the rubric's declared self-test has a recorded passing run",
                        c8))

    audit_attachment = None
    if args.audit_run_report and Path(args.audit_run_report).exists():
        ap = Path(args.audit_run_report)
        try:
            rep = json.loads(ap.read_text())
            audit_attachment = {
                "path": str(ap.relative_to(ROOT)) if str(ap).startswith(str(ROOT)) else str(ap),
                "sha256": sha256(ap),
                "rubric_sha256": rep.get("rubric_sha256"),
                "summary": rep.get("summary"),
                "gates": rep.get("gates"),
                "note": ("live-workspace enforcement run, not a rubric self-test record: it reports "
                         "violations of the live corpus and does not write validation.last_run"),
            }
        except Exception as exc:
            audit_attachment = {"path": str(ap), "error": f"{type(exc).__name__}: {exc}"}

    fails = [c for c in checks if c["status"] == "fail"]
    warns = [c for c in checks if c["status"] == "warn"]
    # transparent scoring: 5.0 base, -1.0 per blocking check, -0.25 per minor finding
    score = max(0.0, round(5.0 - 1.0 * len(fails) - 0.25 * len(warns), 2))
    verdict = "revise" if fails else "accept"

    findings = []
    for c in fails + warns:
        findings.append(f"{c['check_id']} {c['status'].upper()}: {c['detail']}")
    if audit_attachment and audit_attachment.get("summary"):
        findings.append("A0-C8 INFO: declared validator audit_run.py executed this session; "
                        f"live-corpus summary={audit_attachment['summary']}")

    report = {
        "artifact_id": "worker-008-a0-rubric-review",
        "task": "independent class-bound review of evaluation_rubric.yaml at a measured sha256 (node A0, gate G-AUDIT)",
        "reviewer": "worker-008",
        "reviewer_is_author": False,
        "rubric_author": rubric.get("author"),
        "created_at": now(),
        "target": {"node_id": "A0", "artifact": "evaluation_rubric.yaml",
                   "sha256": inputs["rubric"]["sha256"], "bytes": inputs["rubric"]["bytes"]},
        "class_ids": EXPECTED_CLASSES,
        "inputs": inputs,
        "checks": checks,
        "verdict": verdict,
        "score": score,
        "hard_failures": [],
        "blocking_findings": [c["detail"] for c in fails],
        "findings": findings,
        "assumptions": [
            "the four canonical class ids are those in the map's frozen four; the taxonomy is read "
            "only for its class_ids list",
            "the A0 acceptance text is asg-2026-09-11-A0-astra-lead-audit-07 plus the G-AUDIT criteria",
            "the declared validator artifacts/audit/audit_run.py is the rubric's own self-test path",
        ],
        "falsifier": ("a recorded audit_run.py run with last_run_result pass and report_sha256 in "
                      "evaluation_rubric.yaml at this sha256 falsifies A0-C8; a canonical taxonomy "
                      "with different class_ids, or an unknown AF-* token in the rubric, falsifies A0-C2"),
        "next_falsifier": ("re-run this checker after the owner records the self-test; if A0-C8 passes "
                           "and no check fails, the verdict moves to accept at the same hash"),
        "audit_run_attachment": audit_attachment,
        "limits": [
            "structural/semantic conformance only: physical correctness of the class definitions is "
            "not assessed here",
            "verdict is evidence for the audit lead; worker events cannot set gate verdicts",
        ],
        "evidence_refs": [
            f"evaluation_rubric.yaml#{inputs['rubric']['sha256']}",
            f"research_map/formulation_taxonomy.yaml#{inputs['taxonomy']['sha256'][:12]}",
            f"research_map/research_map.json#{inputs['map']['sha256'][:12]}",
            "research_map/events.schema.json",
        ],
    }

    outp = Path(args.out)
    outp.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"verdict": verdict, "score": score,
                      "checks": {c["check_id"]: c["status"] for c in checks},
                      "blocking": [c["detail"] for c in fails]}, indent=1))
    print(f"report -> {outp}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""W05 F2a acceptance harness — CLASS-SPECIFIC, NOT A GATE.

After the G-FORM tooling review (HF-12: five incompatible class-binding checkers, no frozen
schema) and the freeze of FORM-RULE-SPEC v1.1, the binding structural decision for F2a is
made by the canonical gate `artifacts/formulation/tools/check_class_schema.py` (R01-R16).
This harness does NOT compete with it:

  1. it runs the canonical gate on the artifact (binding structural verdict, subprocess);
  2. it adds F2a-specific probes the canonical gate does not make: strict composite scan of
     the raw text including comments, foreign-class confinement, citation discipline,
     rule-spec vocabulary agreement, artifact state;
  3. it self-tests with 10 planted mutations; each mutant is written to a temp file and must
     be caught by the canonical gate or by a named probe.

It decides structure only. It certifies no mathematics and no source scope.
Usage:
  python3 artifacts/worker-05/check_f2c2_schema.py --selftest
  python3 artifacts/worker-05/check_f2c2_schema.py --report
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = ROOT / "schemas" / "af_scc_c2_vacuum.yaml"
CANON = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
SPEC_PATH = ROOT / "artifacts" / "formulation" / "rule_spec.json"
ASSIGNED_CLASS = "AF-SCC-C2-VAC-GEN"
FOREIGN_CLASSES = ["AF-SCC-C0-VAC-GEN", "AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH"]
REQUIRED_LAYOUT = [
    "schema_version", "artifact_kind", "artifact_id", "node_id", "group_id", "class_id",
    "owner", "epistemic_status", "validation_status", "claims_completion", "class_components",
    "quantifiers", "topology", "data_class", "regularity", "genericity", "non_vacuity",
    "i_plus", "visibility", "conclusion", "falsifier", "provenance", "implication_ledger",
]
BOUNDARY_PATH_RE = re.compile(
    r"class_separation|neighbouring_class_facts|provenance|unresolved|evidence_refs|"
    r"acceptance_map|variants|anti_scope|review_history|implication_ledger|class_axes|"
    r"forbidden_strengthenings|forbidden_weakenings|forbidden_transfers",
    re.I,
)
COMPOSITE_RE = re.compile(r"(C0|C2|C\^?0|C\^?2)\s*(or|and|/)\s*(C0|C2|C\^?0|C\^?2)", re.I)
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
ID_RE = re.compile(r"arxiv|doi\.org|10\.\d{4}/", re.I)


def now_iso() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text())


def walk(x, prefix=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{prefix}[{i}]")
    else:
        yield prefix, x


def canonical_gate(path: Path) -> dict:
    try:
        p = subprocess.run(
            [sys.executable, str(CANON), str(path), "--json"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=120,
        )
        rep = json.loads(p.stdout) if p.stdout.strip() else {}
        return {
            "verdict": rep.get("verdict"),
            "failed_rules": rep.get("failed_rules", []),
            "failures": rep.get("failures", []),
            "exit": p.returncode,
        }
    except Exception as exc:  # pragma: no cover
        return {"verdict": None, "failed_rules": [], "failures": [{"rule": "CANON", "msg": repr(exc)}], "exit": None}


def probes(doc: dict, raw: str, spec: dict) -> list[dict]:
    out: list[dict] = []

    def bad(fid, detail):
        out.append({"id": fid, "verdict": "fail", "detail": detail})

    def ok(fid, detail):
        out.append({"id": fid, "verdict": "pass", "detail": detail})

    cid = str(doc.get("class_id"))

    # P1 rule-spec vocabulary agreement
    conc = doc.get("conclusion") or {}
    want = (spec["vocabularies"]["class_conclusion_type"] or {}).get(cid)
    problems = []
    if conc.get("conclusion_type") != want:
        problems.append(f"conclusion_type {conc.get('conclusion_type')!r} != {want!r}")
    if conc.get("epistemic_status") not in spec["vocabularies"]["epistemic_status"]:
        problems.append(f"epistemic_status {conc.get('epistemic_status')!r} not in vocabulary")
    if problems:
        bad("P1-conclusion-vocabulary", "; ".join(problems))
    else:
        ok("P1-conclusion-vocabulary", f"conclusion_type {want}, epistemic_status {conc.get('epistemic_status')}")

    # P2 layout fields
    missing = [k for k in REQUIRED_LAYOUT if k not in doc or doc[k] in (None, "", [], {})]
    if missing:
        bad("P2-layout-fields", f"missing or empty: {missing}")
    else:
        ok("P2-layout-fields", f"all {len(REQUIRED_LAYOUT)} rule-spec layout fields present")

    # P3 foreign class confinement
    stray = []
    for p, v in walk(doc):
        if not isinstance(v, str):
            continue
        for fc in FOREIGN_CLASSES:
            if fc in v and not BOUNDARY_PATH_RE.search(p):
                stray.append(f"{p} contains {fc}")
    if stray:
        bad("P3-foreign-class-confinement", "; ".join(stray))
    else:
        ok("P3-foreign-class-confinement", "foreign class references confined to boundary/reference fields")

    # P4 strict composite scan of raw text (comments included)
    hits = [m.group(0) for m in COMPOSITE_RE.finditer(raw)]
    if hits:
        bad("P4-strict-composite", f"joined regularity tokens in raw text: {hits}")
    else:
        ok("P4-strict-composite", "no joined regularity token anywhere in raw text")

    # P5 unresolved-citation discipline
    unc = (doc.get("provenance") or {}).get("unresolved_citations")
    if unc is None:
        bad("P5-unresolved-citation-discipline", "provenance.unresolved_citations missing")
    else:
        entries = unc if isinstance(unc, list) else (unc.get("entries") or [])
        probs = []
        for i, e in enumerate(entries):
            blob = json.dumps(e)
            if YEAR_RE.search(blob) or ID_RE.search(blob):
                probs.append(f"[{i}] carries year/identifier")
        if probs:
            bad("P5-unresolved-citation-discipline", "; ".join(probs))
        else:
            ok("P5-unresolved-citation-discipline", f"{len(entries)} unresolved entries clean of year/identifier")

    # P6 verified-source evidence
    pr = doc.get("provenance") or {}
    if pr.get("citation_status") == "verified":
        srcs = pr.get("sources") or []
        probs = []
        for i, s in enumerate(srcs):
            for k in ("identifier", "retrieval_date", "quoted_support"):
                if not s.get(k):
                    probs.append(f"source[{i}] missing {k}")
        if not srcs:
            probs.append("citation_status=verified with no sources")
        if probs:
            bad("P6-verified-source-evidence", "; ".join(probs))
        else:
            ok("P6-verified-source-evidence", f"{len(srcs)} verified sources carry identifier, date and quote")
    else:
        ok("P6-verified-source-evidence", f"citation_status={pr.get('citation_status')!r}; structural check deferred to R15")

    # P7 artifact state
    if str(doc.get("validation_status")) != "unverified" or doc.get("claims_completion") is not False:
        bad("P7-artifact-state", f"validation_status={doc.get('validation_status')!r}, claims_completion={doc.get('claims_completion')!r}")
    else:
        ok("P7-artifact-state", "validation_status unverified and claims_completion false")

    return out


def summarise(findings: list[dict]) -> str:
    return "pass" if not any(f["verdict"] == "fail" for f in findings) else "fail"


def evaluate(path: Path, spec: dict) -> dict:
    raw = path.read_text()
    doc = yaml.safe_load(raw)
    canon = canonical_gate(path)
    pr = probes(doc, raw, spec)
    canon_failed = [f"CANON:{r}" for r in canon.get("failed_rules", [])]
    all_failed = canon_failed + [f["id"] for f in pr if f["verdict"] == "fail"]
    verdict = "pass" if canon.get("verdict") == "pass" and summarise(pr) == "pass" else "fail"
    return {
        "artifact": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "artifact_sha256": sha256_file(path),
        "class_id": doc.get("class_id"),
        "verdict": verdict,
        "canonical_gate": canon,
        "probes": pr,
        "failed_checks": all_failed,
    }


def mutations(clean: dict) -> list[tuple[str, str, dict]]:
    out = []

    def clone():
        return copy.deepcopy(clean)

    d = clone(); d["class_id"] = "AF-SCC-C0-VAC-GEN"
    out.append(("MUT1-wrong-class", "CANON:R02", d))

    d = clone()
    d.setdefault("class_separation", {}).setdefault("anti_scope", []).append("C0 or C2 applies to this class")
    out.append(("MUT2-composite-token", "P4-strict-composite", d))

    d = clone(); d["conclusion"]["conclusion_type"] = "strong_cosmic_censorship"
    out.append(("MUT3-wrong-conclusion-vocabulary", "P1-conclusion-vocabulary", d))

    d = clone(); d["genericity"].pop("topology_or_measure", None)
    out.append(("MUT4-genericity-topology", "CANON:R07", d))

    d = clone(); d["extra_block"] = {"class_id": "AF-SCC-C0-VAC-GEN"}
    out.append(("MUT5-second-class-id", "P3-foreign-class-confinement", d))

    d = clone(); d["conclusion"]["epistemic_status"] = "theorem"
    out.append(("MUT6-status-inflation", "P1-conclusion-vocabulary", d))

    d = clone(); d["regularity"]["extension_regularity"] = "C0"
    out.append(("MUT7-wrong-extension-class", "CANON:R06", d))

    d = clone()
    d["provenance"]["unresolved_citations"][0]["ref"] += " (1963)"
    out.append(("MUT8-unresolved-citation", "P5-unresolved-citation-discipline", d))

    d = clone(); d["conclusion"]["statement_natural_language"] += "; the boundary is visible from I+"
    out.append(("MUT9-foreign-token-in-conclusion", "CANON:R12", d))

    d = clone(); d["non_vacuity"].pop("condition", None)
    out.append(("MUT10-missing-non-vacuity", "CANON:R08", d))

    return out


def selftest(artifact: Path, spec: dict) -> dict:
    clean_doc = yaml.safe_load(artifact.read_text())
    clean = evaluate(artifact, spec)
    rows = []
    with tempfile.TemporaryDirectory() as td:
        for mid, expected, doc in mutations(clean_doc):
            tmp = Path(td) / f"{mid}.yaml"
            tmp.write_text(yaml.safe_dump(doc, sort_keys=False))
            res = evaluate(tmp, spec)
            failed = set(res["failed_checks"])
            rows.append({
                "mutation": mid,
                "expected_failure": expected,
                "caught": expected in failed,
                "failed_checks": sorted(failed),
            })
    ok = clean["verdict"] == "pass" and all(r["caught"] for r in rows)
    return {
        "clean": {"verdict": clean["verdict"], "failed_checks": clean["failed_checks"]},
        "mutations": rows,
        "all_mutations_caught": all(r["caught"] for r in rows),
        "selftest_verdict": "pass" if ok else "fail",
    }


def report(artifact: Path, spec: dict) -> dict:
    res = evaluate(artifact, spec)
    st = selftest(artifact, spec)
    return {
        "task_id": "W05-F2a",
        "harness_role": "class-specific acceptance harness; the canonical gate is binding, this harness is advisory evidence",
        "artifact": res["artifact"],
        "artifact_sha256": res["artifact_sha256"],
        "class_id": res["class_id"],
        "generated_at": now_iso(),
        "binding_gate": str(CANON.relative_to(ROOT)),
        "rule_spec": str(SPEC_PATH.relative_to(ROOT)),
        "rule_spec_version": spec.get("spec_version"),
        "verdict": res["verdict"],
        "canonical_gate": res["canonical_gate"],
        "probes": res["probes"],
        "selftest": st,
        "overall_verdict": "pass" if res["verdict"] == "pass" and st["selftest_verdict"] == "pass" else "fail",
        "limitations": [
            "structural checks only; no mathematical judgement and no citation-scope verification",
            "mutation corpus is the 10 planted leaks; escape rate beyond it is not established",
            "the canonical gate itself documents blind spots (rephrased leaks, definition correctness, source scope)",
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "worker-05" / "f2c2_acceptance_report.json"))
    a = ap.parse_args(argv)
    artifact = Path(a.artifact)
    if not artifact.is_absolute():
        artifact = ROOT / artifact
    spec = load_spec()
    if a.selftest:
        st = selftest(artifact, spec)
        print(json.dumps(st, indent=2))
        return 0 if st["selftest_verdict"] == "pass" else 1
    if a.report:
        rep = report(artifact, spec)
        Path(a.out).write_text(json.dumps(rep, indent=2) + "\n")
        print(f"wrote {a.out}")
        print(f"artifact={rep['verdict']} canonical={rep['canonical_gate'].get('verdict')} selftest={rep['selftest']['selftest_verdict']} overall={rep['overall_verdict']}")
        for f in rep["probes"]:
            if f["verdict"] == "fail":
                print(f"  FAIL {f['id']}: {f['detail']}")
        for f in rep["canonical_gate"].get("failures", []):
            print(f"  CANON {f['rule']}: {f['msg']}")
        return 0 if rep["overall_verdict"] == "pass" else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

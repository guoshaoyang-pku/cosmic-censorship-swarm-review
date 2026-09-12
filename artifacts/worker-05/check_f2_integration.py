#!/usr/bin/env python3
"""W05 F2 integration / class-leakage lint.

Checks schemas/af_scc_regularities.yaml (an index, not a class schema) and the two
strong-censorship component documents it references. Consumes the sibling rule set
artifacts/worker-06/class_binding_rules.json for class ids, regularity allowances and
composite-regularity patterns, and runs the sibling gate
artifacts/worker-06/check_class_binding.py on each component as an independent check.

DRAFT / UNVERIFIED. It checks structure and leakage only; it decides no mathematics and
certifies nothing. Reviewer 18 / G-FORM own acceptance.

Aggregator checks
  A1 aggregator-identity     node F2, type formulation_aggregator, unverified, no completion claim
  A2 component-set           exactly the two SCC classes, each exactly once, as separate entries
  A3 component-pins          every component has a path and a 64-hex sha256; in report mode the
                             pinned sha256 must equal the file on disk (drift fails)
  A4 class-id-join           no value joins the two class ids with a separator/disjunction
  A5 composite-regularity    no composite regularity token (w06 patterns) in the file
  A6 no-conclusion-object    no conclusion/conclusion_type key and no extension-statement token
  A7 no-yaml-alias           no anchors, aliases or merge keys (cross-document aliasing)
  A8 artifact-state          validation_status unverified, claims_completion false

Component checks (report mode)
  C1 component-identity      class id in the w06 class set; node under F2
  C2 component-selector      exactly one regularity token, matching the class allowance
  C3 conclusion-separation   both conclusions non-empty and distinct; the C2 conclusion carries no
                             C0 token; any C2 token in the C0 conclusion sits on a relation field
  C4 component-composite     no composite regularity token in either component
  C5 sibling-gate            the w06 gate returns pass on each component
  C6 revision-pins           component file hashes still equal the aggregator pins

Fixture mode (--fixtures) evaluates artifacts/worker-05/fixtures_f2/*.yaml against their
declared _meta.expected verdict and runs always-accept / always-reject null controls.

Usage:
  python3 artifacts/worker-05/check_f2_integration.py --fixtures
  python3 artifacts/worker-05/check_f2_integration.py --report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

CST = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parents[2]
AGG = ROOT / "schemas" / "af_scc_regularities.yaml"
RULES_PATH = ROOT / "artifacts" / "worker-06" / "class_binding_rules.json"
SPEC_PATH = ROOT / "artifacts" / "formulation" / "rule_spec.json"
CANON = ROOT / "artifacts" / "formulation" / "tools" / "check_class_schema.py"
FIXTURES = ROOT / "artifacts" / "worker-05" / "fixtures_f2"
SCC_CLASSES = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
C0_RE = re.compile(r"\bc\s*\^?\s*\{?\s*0\s*\}?\b", re.I)
C2_RE = re.compile(r"\bc\s*\^?\s*\{?\s*2\s*\}?\b", re.I)
RELATION_KEY_RE = re.compile(r"relation|related|implication|sibling|contrast|disjoint|forbidden|must_not|anti_scope|prohibited|excluded", re.I)
ANCHOR_RE = re.compile(r"(^|[\s\[{,])[&*][A-Za-z0-9_-]+")
MERGE_KEY_RE = re.compile(r"<<\s*:")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def now_iso() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rules() -> dict:
    return json.loads(RULES_PATH.read_text())


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


def walk(x, prefix=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from walk(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from walk(v, f"{prefix}[{i}]")
    else:
        yield prefix, x


def key_paths(x, prefix=""):
    """Yield every dotted key path, including intermediate object keys."""
    if isinstance(x, dict):
        for k, v in x.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            yield path
            yield from key_paths(v, path)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from key_paths(v, f"{prefix}[{i}]")


def leaves_under(doc, path_regex: str):
    rx = re.compile(path_regex, re.I)
    return [(p, str(v)) for p, v in walk(doc) if rx.search(p)]


def joined_class_regex(class_ids: list[str]) -> re.Pattern:
    ids = "|".join(re.escape(c) for c in class_ids)
    sep = r"\s*(?:[;/,|&+]|\band\b|\bor\b|\bwith\b)\s*"
    return re.compile(rf"(?:{ids}){sep}(?:{ids})", re.I)


def first_context(raw: str, needle: str, width: int = 100) -> str:
    """Return the trimmed line containing needle, clipped, for actionable reporting."""
    low = needle.lower()
    for line in raw.splitlines():
        if low in line.lower():
            return line.strip()[:width]
    return ""


def class_id_leaf_paths(doc):
    out = []
    for p in key_paths(doc):
        if p.rsplit(".", 1)[-1].split("[")[0] in {"class", "class_id", "class_name"}:
            out.append(p)
    return out


def check_aggregator(doc: dict, raw: str, rules: dict, fixture: bool = False) -> list[dict]:
    findings: list[dict] = []

    def bad(fid, detail):
        findings.append({"id": fid, "verdict": "fail", "detail": detail})

    def ok(fid, detail):
        findings.append({"id": fid, "verdict": "pass", "detail": detail})

    # A1 identity / state (A8 folded in here for readability)
    ident_problems = []
    if str(doc.get("node_id")) != "F2":
        ident_problems.append(f"node_id={doc.get('node_id')!r}")
    if str(doc.get("artifact_type")) != "formulation_aggregator":
        ident_problems.append(f"artifact_type={doc.get('artifact_type')!r}")
    if not fixture:
        if str(doc.get("validation_status")) != "unverified":
            ident_problems.append(f"validation_status={doc.get('validation_status')!r}")
        if doc.get("claims_completion") is not False:
            ident_problems.append(f"claims_completion={doc.get('claims_completion')!r}")
    if ident_problems:
        bad("A1-aggregator-identity", "; ".join(ident_problems))
    else:
        ok("A1-aggregator-identity", "aggregator identity and unverified state")

    # A2 component set
    comps = doc.get("components") or []
    if not isinstance(comps, list):
        bad("A2-component-set", "components is not a list")
        comps = []
    ids = [str(c.get("class_id")) for c in comps if isinstance(c, dict)]
    problems = []
    if sorted(ids) != sorted(SCC_CLASSES):
        problems.append(f"component class ids {ids} != {SCC_CLASSES}")
    if len(set(ids)) != len(ids):
        problems.append(f"duplicate component class ids {ids}")
    if not all(isinstance(c, dict) and c.get("role") for c in comps):
        problems.append("a component lacks a role")
    if problems:
        bad("A2-component-set", "; ".join(problems))
    else:
        ok("A2-component-set", f"components = {ids} with roles")

    # A3 pins
    pin_problems = []
    for c in comps:
        if not isinstance(c, dict):
            continue
        p, sh = str(c.get("path", "")), str(c.get("sha256", ""))
        if not p:
            pin_problems.append(f"{c.get('class_id')}: missing path")
        if not HEX64_RE.match(sh):
            pin_problems.append(f"{c.get('class_id')}: sha256 not 64-hex ({sh[:16]!r})")
            continue
        if not fixture:
            fp = ROOT / p
            if not fp.exists():
                pin_problems.append(f"{c.get('class_id')}: path absent {p}")
            elif sha256_file(fp) != sh:
                pin_problems.append(f"{c.get('class_id')}: disk hash {sha256_file(fp)[:12]} != pin {sh[:12]} ({p})")
    if pin_problems:
        bad("A3-component-pins", "; ".join(pin_problems))
    else:
        ok("A3-component-pins", "components pinned" + ("" if fixture else " and hashes match disk"))

    # A4 joined class ids
    all_ids = list(rules["classes"].keys())
    hits = [m.group(0) for m in joined_class_regex(all_ids).finditer(raw)]
    if hits:
        bad("A4-class-id-join", f"joined class-id strings: {hits}")
    else:
        ok("A4-class-id-join", "no joined class-id string")

    # A5 composite regularity
    hits = []
    for pat in rules["composite_regularity_regexes"]:
        hits += [m.group(0) for m in re.finditer(pat, raw, re.I)]
    if hits:
        bad("A5-composite-regularity", f"composite regularity strings: {hits}; context: {[first_context(raw, h) for h in hits[:3]]}")
    else:
        ok("A5-composite-regularity", "no composite regularity string")

    # A6 no conclusion object / extension statement in an index
    key_hits = [p for p in key_paths(doc) if p.rsplit(".", 1)[-1].split("[")[0] in {"conclusion", "conclusion_type"}]
    ext_hits = re.findall(r"inextendib\w*", raw, re.I)
    if key_hits or ext_hits:
        bad("A6-no-conclusion-object", f"conclusion keys={key_hits}, extension tokens={sorted(set(ext_hits))}")
    else:
        ok("A6-no-conclusion-object", "index defines no conclusion object and no extension statement")

    # A7 aliases / merge keys
    anchors = [m.group(0).strip() for m in ANCHOR_RE.finditer(raw)]
    merges = [m.group(0) for m in MERGE_KEY_RE.finditer(raw)]
    if anchors or merges:
        bad("A7-no-yaml-alias", f"anchors/aliases={anchors}, merge keys={merges}")
    else:
        ok("A7-no-yaml-alias", "no anchors, aliases or merge keys")

    return findings


def check_components(doc: dict, rules: dict, spec: dict) -> dict:
    results = {"components": [], "findings": []}
    findings = results["findings"]

    def bad(fid, detail):
        findings.append({"id": fid, "verdict": "fail", "detail": detail})

    def ok(fid, detail):
        findings.append({"id": fid, "verdict": "pass", "detail": detail})

    comps = doc.get("components") or []
    loaded = {}
    for c in comps:
        cid = c.get("class_id")
        path = ROOT / str(c.get("path"))
        try:
            raw = path.read_text()
            cdoc = yaml.safe_load(raw)
        except Exception as exc:
            results["components"].append({"class_id": cid, "path": str(path), "error": repr(exc)})
            bad("C1-component-identity", f"{cid}: cannot load {path}: {exc!r}")
            continue
        canon = canonical_gate(path)
        loaded[cid] = {"doc": cdoc, "raw": raw, "path": str(path), "canon": canon}

        # C1 identity: top-level class id and node under F2 (rule-spec layout)
        if str(cdoc.get("class_id")) != cid or cid not in rules["classes"]:
            bad("C1-component-identity", f"{cid}: class_id mismatch or unknown ({cdoc.get('class_id')!r})")
        elif "F2" not in str(cdoc.get("node_id", "")):
            bad("C1-component-identity", f"{cid}: node_id {cdoc.get('node_id')!r} not under F2")
        else:
            ok("C1-component-identity", f"{cid}: class_id and node {cdoc.get('node_id')} agree")

        # C2 selector via rule-spec class_components.regularity_token
        want_tok = spec["vocabularies"]["regularity_token"].get("SCC", [])
        comp = cdoc.get("class_components") or {}
        tok = comp.get("regularity_token")
        if tok not in want_tok or tok not in cid:
            bad("C2-component-selector", f"{cid}: class_components.regularity_token={tok!r}, expected one of {want_tok}")
        else:
            ok("C2-component-selector", f"{cid}: selector {tok}")

        # C4 composite regularity per the binding gate rule R13
        if "R13" in canon.get("failed_rules", []):
            bad("C4-component-composite", f"{cid}: canonical R13 failed: {[f['msg'] for f in canon.get('failures', []) if f['rule'] == 'R13']}")
        else:
            raw_hits = [m.group(0) for pat in rules["composite_regularity_regexes"] for m in re.finditer(pat, raw, re.I)]
            ok("C4-component-composite", f"{cid}: canonical R13 pass" + (f"; raw lexical occurrences inside prohibition/comment text: {raw_hits}" if raw_hits else ""))

    # C3 conclusion separation
    def concl_text(key):
        if key not in loaded:
            return None
        return " ".join(v for _p, v in leaves_under(loaded[key]["doc"], r"^conclusion"))

    t2, t0 = concl_text("AF-SCC-C2-VAC-GEN"), concl_text("AF-SCC-C0-VAC-GEN")
    if t2 is None or t0 is None:
        bad("C3-conclusion-separation", "a component conclusion subtree could not be read")
    elif not t2.strip() or not t0.strip():
        bad("C3-conclusion-separation", "a component conclusion subtree is empty")
    elif t2 == t0:
        bad("C3-conclusion-separation", "component conclusion subtrees are identical (merged)")
    else:
        problems = []
        for p, v in leaves_under(loaded["AF-SCC-C2-VAC-GEN"]["doc"], r"^conclusion"):
            if C0_RE.search(v) and not RELATION_KEY_RE.search(p):
                problems.append(f"C2 conclusion carries a C0 token outside a prohibition/relation field: {p}")
        if not C2_RE.search(t2):
            problems.append("C2 conclusion carries no C2 token")
        if not C0_RE.search(t0):
            problems.append("C0 conclusion carries no C0 token")
        for p, v in leaves_under(loaded["AF-SCC-C0-VAC-GEN"]["doc"], r"^conclusion"):
            if C2_RE.search(v) and not RELATION_KEY_RE.search(p):
                problems.append(f"C0 conclusion carries a C2 token outside a relation field: {p}")
        if problems:
            bad("C3-conclusion-separation", "; ".join(problems))
        else:
            ok("C3-conclusion-separation", "conclusions non-empty, distinct, family-separated")

    # C7 shared-data-class signature (HF-06 / transfer rule T1)
    def dc_signature(key):
        if key not in loaded:
            return None
        dc = loaded[key]["doc"].get("data_class") or {}
        rc = dc.get("regularity_class") or {}
        sv = rc.get("sobolev_variant") or {}
        return {
            "selected": rc.get("selected") or rc.get("default"),
            "s": sv.get("s"),
            "delta": sv.get("delta"),
            "ambient": (loaded[key]["doc"].get("genericity") or {}).get("ambient_space"),
        }

    s2, s0 = dc_signature("AF-SCC-C2-VAC-GEN"), dc_signature("AF-SCC-C0-VAC-GEN")
    if s2 and s0:
        mism = [f"{f}: C2={s2.get(f)!r} vs C0={s0.get(f)!r}" for f in ("selected", "s", "delta") if s2.get(f) != s0.get(f)]
        if mism:
            bad("C7-shared-data-class", "transfer rule T1 not licensed; " + "; ".join(mism))
        else:
            ok("C7-shared-data-class", "components freeze the same data-class signature")

    # C5 binding canonical gate on each component
    for cid, info in loaded.items():
        canon = info["canon"]
        if canon.get("verdict") != "pass":
            bad("C5-binding-gate", f"{cid}: canonical gate verdict={canon.get('verdict')!r} failed_rules={canon.get('failed_rules')}")
        else:
            ok("C5-binding-gate", f"{cid}: canonical gate pass (R01-R16)")

    # C6 revision pins (redundant with A3 but reported per component)
    drift = []
    for c in comps:
        fp = ROOT / str(c.get("path"))
        if fp.exists() and sha256_file(fp) != str(c.get("sha256")):
            drift.append(f"{c.get('class_id')}: {sha256_file(fp)[:12]} != pin {str(c.get('sha256'))[:12]}")
    if drift:
        bad("C6-revision-pins", "; ".join(drift))
    else:
        ok("C6-revision-pins", "component hashes still equal the aggregator pins")

    results["loaded_hashes"] = {cid: sha256_file(Path(i["path"])) for cid, i in loaded.items()}
    return results


def summarise(findings: list[dict]) -> str:
    return "pass" if not any(f["verdict"] == "fail" for f in findings) else "fail"


def run_fixtures(rules: dict) -> dict:
    rows = []
    for p in sorted(FIXTURES.glob("*.yaml")):
        raw = p.read_text()
        doc = yaml.safe_load(raw) or {}
        meta = doc.get("_meta", {}) if isinstance(doc, dict) else {}
        findings = check_aggregator(doc, raw, rules, fixture=True)
        verdict = summarise(findings)
        expected = meta.get("expected")
        rows.append({
            "fixture": p.name,
            "fixture_id": meta.get("fixture_id"),
            "leak": meta.get("leak"),
            "expected": expected,
            "got": verdict,
            "match": verdict == expected,
            "failed_checks": [f["id"] for f in findings if f["verdict"] == "fail"],
        })
    negs = [r for r in rows if r["expected"] == "fail"]
    poss = [r for r in rows if r["expected"] == "pass"]
    controls = {
        "always_accept_control": {
            "negatives": len(negs),
            "would_accept": [r["fixture"] for r in negs if r["got"] == "pass"],
            "passed": all(r["got"] == "fail" for r in negs) and len(negs) > 0,
        },
        "always_reject_control": {
            "positives": len(poss),
            "would_reject": [r["fixture"] for r in poss if r["got"] == "fail"],
            "passed": all(r["got"] == "pass" for r in poss) and len(poss) > 0,
        },
    }
    mismatched = [r["fixture"] for r in rows if not r["match"]]
    ok = not mismatched and all(c["passed"] for c in controls.values()) and len(rows) >= 8
    return {
        "fixtures_dir": str(FIXTURES.relative_to(ROOT)),
        "count": len(rows),
        "negatives": len(negs),
        "positives": len(poss),
        "mismatched": mismatched,
        "controls": controls,
        "verdict": "pass" if ok else "fail",
        "rows": rows,
    }


def report() -> dict:
    rules = load_rules()
    spec = json.loads(SPEC_PATH.read_text())
    raw = AGG.read_text()
    doc = yaml.safe_load(raw)
    agg_findings = check_aggregator(doc, raw, rules)
    comp = check_components(doc, rules, spec)
    fixtures = run_fixtures(rules)
    overall = "pass" if summarise(agg_findings) == "pass" and summarise(comp["findings"]) == "pass" and fixtures["verdict"] == "pass" else "fail"
    return {
        "task_id": "W05-F2b",
        "aggregator": str(AGG.relative_to(ROOT)),
        "aggregator_sha256": sha256_file(AGG),
        "generated_at": now_iso(),
        "rules_consumed": [str(RULES_PATH.relative_to(ROOT)), str(SPEC_PATH.relative_to(ROOT))],
        "binding_component_gate": str(CANON.relative_to(ROOT)),
        "rule_spec_version": spec.get("spec_version"),
        "rules_version": rules.get("rules_version"),
        "aggregator_verdict": summarise(agg_findings),
        "aggregator_findings": agg_findings,
        "component_verdict": summarise(comp["findings"]),
        "component_findings": comp["findings"],
        "component_hashes": comp["loaded_hashes"],
        "fixtures": fixtures,
        "overall_verdict": overall,
        "limitations": [
            "structural and separation checks only; no mathematical judgement",
            "the fixture corpus is the 10 planted leaks; escape rate beyond it is not established",
            "the w06 rule set is a draft derived without the F0 taxonomy and is consumed as a sibling hypothesis, not as authority",
            "a component revision invalidates the aggregator pins; re-pin and re-run after any revision",
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixtures", action="store_true", help="run the fixture corpus and null controls only")
    ap.add_argument("--report", action="store_true", help="run aggregator + component + fixture checks and write JSON")
    ap.add_argument("--out", default=str(ROOT / "artifacts" / "worker-05" / "f2_integration_report.json"))
    a = ap.parse_args(argv)
    rules = load_rules()
    if a.fixtures:
        fx = run_fixtures(rules)
        print(json.dumps(fx, indent=2))
        return 0 if fx["verdict"] == "pass" else 1
    if a.report:
        rep = report()
        Path(a.out).write_text(json.dumps(rep, indent=2) + "\n")
        print(f"wrote {a.out}")
        print(f"aggregator={rep['aggregator_verdict']} components={rep['component_verdict']} "
              f"fixtures={rep['fixtures']['verdict']} overall={rep['overall_verdict']}")
        for f in rep["aggregator_findings"] + rep["component_findings"]:
            if f["verdict"] == "fail":
                print(f"  FAIL {f['id']}: {f['detail']}")
        return 0 if rep["overall_verdict"] == "pass" else 1
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())

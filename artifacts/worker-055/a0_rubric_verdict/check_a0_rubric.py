#!/usr/bin/env python3
"""W055-A0-RUBRIC-01 — independent A0 conformance verdict for evaluation_rubric.yaml.

Question (from the audit lead's own spot check, reviews/A1-rebind-coverage.json#a0_conformance):
    "universal_scalar_score_token_present": true   -- but is that a real universal scalar
    score (G-AUDIT criterion violation) or a metalinguistic prohibition mention?
and the binding A0 question: does the rubric satisfy the G-AUDIT criterion
    "evaluation_rubric.yaml exists without a universal scalar score" ?

Method (independent of the author, of flash-21/22 and of lead-audit):
  * pin the rubric bytes; cross-check the controller registry hash;
  * classify every scalar/aggregate-score token as USE vs MENTION;
  * reproduce the vocabulary-disconnect blocker (rubric genericity enum / conclusion
    vocabulary vs the three frozen schemas) from primary bytes;
  * run five staged mutations (negative controls) that the instrument must catch.

Exit 0 iff every live expectation AND every mutation expectation holds.
Read-only on canonical paths; every write is confined to this bundle's stage/ and report.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-055/a0_rubric_verdict -> swarm root

LIVE = ROOT / "evaluation_rubric.yaml"
F0 = ROOT / "research_map" / "formulation_taxonomy.yaml"
SCHEMAS = {
    "F1": ROOT / "schemas" / "af_wcc_vacuum.yaml",
    "F2a": ROOT / "schemas" / "af_scc_c2_vacuum.yaml",
    "F2b": ROOT / "schemas" / "af_scc_c0_vacuum.yaml",
}
REGISTRY = ROOT / "runtime" / "state" / "artifact_hashes.json"
SNAP = HERE / "snapshot"
STAGE = HERE / "stage"

EXPECTED_SHA = "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885"
EXPECTED_F0_SHA = "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3"
PROHIBITION_KEY = "no_universal_scalar_score"
SCALAR_KEY_RE = re.compile(
    r"(universal|overall|total|aggregate|global|combined|composite)[ _\-]*"
    r"(scalar[ _\-]*)?(score|rank|rating|grade)", re.I)
AVG_RE = re.compile(
    r"(averag|mean|weighted[ _\-]*sum|roll[ _\-]*up)", re.I)
CROSSTYPE_RE = re.compile(
    r"(task[ _\-]*type|all (the )?(verifiers|metrics|tasks)|across (the )?(verifiers|metrics|tasks))",
    re.I)
NEG_RE = re.compile(r"\b(no|not|never|without|cannot|must not)\b", re.I)
NUMERIC_THRESHOLD_RE = re.compile(r"(threshold|cutoff|min[ _\-]*score|accept[ _\-]*at)", re.I)


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def raw_scalar_census(text: str) -> list:
    """Locatable line-level census of aggregate-scalar-score tokens (mention vs use)."""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if SCALAR_KEY_RE.search(line) or "single number" in line.lower():
            hits.append({"line": i, "text": line.strip()[:140]})
    return hits


def walk(obj, path=()):
    """Yield (path_tuple, value) for every node; dict keys are yielded as values too."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path + (str(k),), v
            yield from walk(v, path + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield path + (f"[{i}]",), v
            yield from walk(v, path + (f"[{i}]",))


def scalar_scan(doc) -> dict:
    """Classify scalar-score tokens as USE (violation) vs MENTION (prohibition)."""
    violations, mentions = [], []

    def parent_key(path):
        return path[-1] if path else ""

    for path, val in walk(doc):
        key = parent_key(path)
        pstr = ".".join(path)
        # 1. aggregate-scalar KEY (anywhere except the declared prohibition key)
        if isinstance(val, dict) and key != PROHIBITION_KEY and SCALAR_KEY_RE.search(key):
            violations.append({
                "path": pstr, "token": key, "kind": "aggregate_scalar_key",
                "detail": "key names an aggregate/universal score object",
            })
        # 2. string values that describe a single-number roll-up
        if isinstance(val, str):
            if AVG_RE.search(val) and CROSSTYPE_RE.search(val):
                if NEG_RE.search(val):
                    mentions.append({"path": pstr, "kind": "prohibition_mention",
                                     "detail": val.strip()[:160]})
                else:
                    violations.append({"path": pstr, "kind": "cross_type_average",
                                       "detail": val.strip()[:160]})
            if re.search(r"(single|one)\s+(number|score|scalar)", val, re.I):
                mentions.append({"path": pstr, "kind": "prohibition_mention",
                                 "detail": val.strip()[:160]})
        # 3. numeric acceptance threshold attached to a scalar key
        if isinstance(val, (int, float)) and key and SCALAR_KEY_RE.search(key):
            violations.append({"path": pstr, "token": key, "kind": "numeric_scalar_threshold",
                               "detail": f"{val}"})
        if isinstance(val, dict):
            for k2, v2 in val.items():
                if NUMERIC_THRESHOLD_RE.search(str(k2)) and SCALAR_KEY_RE.search(key or ""):
                    violations.append({"path": pstr, "token": str(k2),
                                       "kind": "numeric_scalar_threshold", "detail": str(v2)})
    # the declared prohibition key itself must classify as a mention, never a violation
    prohibition_present = PROHIBITION_KEY in doc
    mentions_of_key = [m for m in mentions if m["path"].startswith(PROHIBITION_KEY)]
    return {
        "violations": violations,
        "mentions": mentions,
        "prohibition_key_present": prohibition_present,
        "prohibition_key_classified_as_mention": bool(mentions_of_key) or (
            prohibition_present and isinstance(doc.get(PROHIBITION_KEY), str)),
        "verdict": "PASS_no_universal_scalar_score" if not violations else "FAIL_scalar_score_found",
    }


def check_promotion(doc) -> dict:
    rp = doc.get("review_protocol") or {}
    rule = str(rp.get("promotion_rule", ""))
    ok = ("only" in rule.lower() and "verdict" in rule.lower()
          and "promot" in rule.lower() and "consensus is not evidence" in rule.lower())
    return {"name": "C2_promotion_rule", "status": "PASS" if ok else "FAIL",
            "evidence": {"promotion_rule": rule[:200]},
            "requirement": "only G-* verdicts promote; consensus is not evidence"}


def check_verifiers(doc) -> dict:
    want = {"schema_formulation", "literature", "numerics", "formalization"}
    v = doc.get("verifiers") or {}
    problems = []
    if set(v) != want:
        problems.append(f"verifier keys {sorted(v)} != {sorted(want)}")
    for name, blk in v.items():
        if not isinstance(blk, dict):
            problems.append(f"{name}: not a mapping"); continue
        for field in ("gate", "machine_checkable", "checks", "human_adjudication_only"):
            if not blk.get(field):
                problems.append(f"{name}: missing/empty {field}")
        if isinstance(blk.get("checks"), list) and len(blk["checks"]) < 3:
            problems.append(f"{name}: <3 checks")
    gates_used = {str((b or {}).get("gate", "")).split(" ")[0] for b in v.values() if isinstance(b, dict)}
    allowed = {"G-FORM", "G-LIT", "G-NUM", "G-FORMAL"}
    if not gates_used <= allowed:
        problems.append(f"unknown gates referenced: {gates_used - allowed}")
    return {"name": "C3_task_type_verifiers", "status": "PASS" if not problems else "FAIL",
            "problems": problems, "gates_used": sorted(gates_used)}


def check_classes(doc, f0_doc) -> dict:
    problems = []
    fcs = doc.get("frozen_classes") or []
    ids = [c.get("id") for c in fcs if isinstance(c, dict)]
    canonical = set(f0_doc.get("class_ids") or [])
    if len(ids) != len(set(ids)):
        problems.append("duplicate class ids")
    if set(ids) != canonical:
        problems.append(f"class id set {sorted(map(str, ids))} != canonical {sorted(canonical)}")
    for c in fcs:
        cid = str(c.get("id"))
        if re.search(r"(\bOR\b|\||,|/|C0.*C2|C2.*C0)", cid):
            problems.append(f"{cid}: disjunction/merged class token")
        for field in ("dimension", "asymptotics", "matter_model", "formulation",
                      "conclusion_primary", "forbidden_evidence"):
            if not c.get(field):
                problems.append(f"{cid}: missing/empty {field}")
    return {"name": "C4_class_binding", "status": "PASS" if not problems else "FAIL",
            "problems": problems, "frozen_class_ids": ids,
            "canonical_f0_sha256": sha256_file(F0) if F0.exists() else None}


def check_hard_failures(doc) -> dict:
    hf = doc.get("hard_failures") or []
    problems, seen = [], set()
    for h in hf:
        hid = h.get("id")
        if hid in seen:
            problems.append(f"duplicate {hid}")
        seen.add(hid)
        for field in ("name", "severity", "detector"):
            if not h.get(field):
                problems.append(f"{hid}: missing {field}")
        if h.get("severity") not in {"critical", "major", "minor"}:
            problems.append(f"{hid}: bad severity {h.get('severity')!r}")
    return {"name": "C5_hard_failure_taxonomy", "status": "PASS" if not problems else "FAIL",
            "problems": problems, "count": len(hf), "ids": sorted(map(str, seen))}


def check_metrics(doc) -> dict:
    m = doc.get("metrics") or {}
    required = ["class_binding", "citation_support", "hard_failure_rate", "duplication",
                "effective_sample_size", "information_gain", "novel_accepted_coverage"]
    missing = [k for k in required if k not in m]
    advisory_missing = [k for k in ("accepted_claim_rate", "cost_per_accepted_claim") if k not in m]
    return {"name": "C6_metric_coverage", "status": "PASS" if not missing else "FAIL",
            "missing_required": missing, "advisory_missing": advisory_missing,
            "present": sorted(m)}


def extract_genericity_enum(doc) -> list:
    for g in doc.get("gates") or []:
        if g.get("id") == "G-FORM":
            for crit in g.get("criteria") or []:
                m = re.search(r"one of \{([^}]+)\}", str(crit))
                if m:
                    return [x.strip() for x in m.group(1).split(",")]
    return []


def check_vocab_disconnect(doc, schemas) -> dict:
    enum = extract_genericity_enum(doc)
    rows = []
    for name, path in schemas.items():
        s = yaml.safe_load(path.read_text())
        gen = str((s.get("genericity") or {}).get("kind", ""))
        concl = str((s.get("conclusion") or {}).get("conclusion_type", ""))
        rows.append({"schema": name, "sha256": sha256_file(path), "genericity_kind": gen,
                     "conclusion_type": concl,
                     "genericity_allowed": gen in enum})
    allowed_by_class = {}
    for c in doc.get("frozen_classes") or []:
        allowed_by_class[c.get("id")] = [str(c.get("conclusion_primary"))] + [
            str(x) for x in (c.get("conclusion_implied") or [])]
    class_of = {"F1": "AF-WCC-VAC-GEN", "F2a": "AF-SCC-C2-VAC-GEN", "F2b": "AF-SCC-C0-VAC-GEN"}
    for r in rows:
        allowed = allowed_by_class.get(class_of[r["schema"]], [])
        r["conclusion_allowed_set"] = allowed
        r["conclusion_allowed"] = r["conclusion_type"] in allowed
    gen_mismatch = [r["schema"] for r in rows if not r["genericity_allowed"]]
    concl_mismatch = [r["schema"] for r in rows if not r["conclusion_allowed"]]
    detected = bool(gen_mismatch or concl_mismatch)
    return {"name": "C7_vocabulary_disconnect", "status": "DEFECT_REPRODUCED" if detected else "NOT_REPRODUCED",
            "genericity_enum": enum, "rows": rows,
            "genericity_mismatch": gen_mismatch, "conclusion_mismatch": concl_mismatch,
            "detected": detected}


def check_gaudit_coherence(doc) -> dict:
    metrics = doc.get("metrics") or {}
    kappa_named = any("kappa" in str(c).lower()
                      for g in (doc.get("gates") or []) if g.get("id") == "G-AUDIT"
                      for c in (g.get("criteria") or []))
    kappa_metric = any("kappa" in str(k).lower() or "kappa" in str(v).lower()
                       for k, v in metrics.items())
    ess_metric = "effective_sample_size" in metrics
    return {"name": "C8_gaudit_metric_coherence", "status": "ADVISORY" if (kappa_named and not kappa_metric) else "PASS",
            "kappa_named_in_gate": kappa_named, "kappa_metric_present": kappa_metric,
            "ess_metric_present": ess_metric,
            "detail": "G-AUDIT criterion names reviewer-agreement kappa but no kappa metric is defined; "
                      "metrics/review_protocol use Kish ESS instead (non-blocking internal-coherence gap)"}


def run_live(snapshot_path: Path) -> dict:
    doc = yaml.safe_load(snapshot_path.read_text())
    f0_doc = yaml.safe_load(F0.read_text())
    schemas = {k: v for k, v in SCHEMAS.items()}
    return {
        "pin": {
            "name": "C1_pin",
            "snapshot_sha256": sha256_file(snapshot_path),
            "live_sha256": sha256_file(LIVE),
            "expected_sha256": EXPECTED_SHA,
            "registry_sha256": (json.loads(REGISTRY.read_text())
                                .get("hashes", {}).get("evaluation_rubric.yaml", {})
                                .get("sha256")),
            "status": "PASS" if (sha256_file(snapshot_path) == EXPECTED_SHA
                                 == sha256_file(LIVE)) else "FAIL",
        },
        "scalar": scalar_scan(doc),
        "promotion": check_promotion(doc),
        "verifiers": check_verifiers(doc),
        "classes": check_classes(doc, f0_doc),
        "hard_failures": check_hard_failures(doc),
        "metrics": check_metrics(doc),
        "vocab": check_vocab_disconnect(doc, schemas),
        "gaudit": check_gaudit_coherence(doc),
    }


def mutants(base_text: str) -> list:
    """(name, doc_or_None, expected_failing_checks). None => copy bytes exactly."""
    base = yaml.safe_load(base_text)
    out = [("M0_unmutated", None, [])]

    d = copy.deepcopy(base)
    d["universal_score"] = {"aggregation": "mean", "accept_threshold": 0.6}
    d.setdefault("review_protocol", {})["promotion_rule"] = \
        "promote if universal_score >= 0.6"
    out.append(("M1_universal_scalar_use", d, ["scalar", "promotion"]))

    d = copy.deepcopy(base)
    d.setdefault("metrics", {})["overall_score"] = {
        "definition": "mean of all metrics across task types", "target": ">= 0.7"}
    out.append(("M2_overall_metric_use", d, ["scalar"]))

    d = copy.deepcopy(base)
    d.pop("review_protocol", None)
    out.append(("M3_no_review_protocol", d, ["promotion"]))

    d = copy.deepcopy(base)
    d["frozen_classes"][1]["id"] = "AF-SCC-C2-C0-VAC-GEN"
    out.append(("M4_merged_class_id", d, ["classes"]))

    d = copy.deepcopy(base)
    d["frozen_classes"][0]["forbidden_evidence"] = []
    out.append(("M5_empty_forbidden_evidence", d, ["classes"]))
    return out


def run_mutant(doc) -> dict:
    f0_doc = yaml.safe_load(F0.read_text())
    return {
        "scalar": scalar_scan(doc),
        "promotion": check_promotion(doc),
        "verifiers": check_verifiers(doc),
        "classes": check_classes(doc, f0_doc),
        "hard_failures": check_hard_failures(doc),
        "metrics": check_metrics(doc),
        "vocab": check_vocab_disconnect(doc, SCHEMAS),
        "gaudit": check_gaudit_coherence(doc),
    }


def failed(results: dict) -> set:
    bad = set()
    if results["scalar"]["violations"]:
        bad.add("scalar")
    if results["promotion"]["status"] != "PASS":
        bad.add("promotion")
    if results["verifiers"]["status"] != "PASS":
        bad.add("verifiers")
    if results["classes"]["status"] != "PASS":
        bad.add("classes")
    if results["hard_failures"]["status"] != "PASS":
        bad.add("hard_failures")
    if results["metrics"]["status"] != "PASS":
        bad.add("metrics")
    return bad


def main() -> int:
    SNAP.mkdir(parents=True, exist_ok=True)
    STAGE.mkdir(parents=True, exist_ok=True)
    snap = SNAP / "evaluation_rubric.d748a9e3574e.yaml"
    snap.write_bytes(LIVE.read_bytes())

    live = run_live(snap)

    # --- live expectations -------------------------------------------------------------
    exp = []
    exp.append(("live_pin", live["pin"]["status"] == "PASS"))
    exp.append(("live_scalar_no_violation",
                live["scalar"]["verdict"] == "PASS_no_universal_scalar_score"))
    exp.append(("live_scalar_prohibition_classified",
                live["scalar"]["prohibition_key_present"]
                and live["scalar"]["prohibition_key_classified_as_mention"]))
    exp.append(("live_promotion_rule", live["promotion"]["status"] == "PASS"))
    exp.append(("live_verifiers", live["verifiers"]["status"] == "PASS"))
    exp.append(("live_classes", live["classes"]["status"] == "PASS"))
    exp.append(("live_hard_failures", live["hard_failures"]["status"] == "PASS"))
    exp.append(("live_metrics", live["metrics"]["status"] == "PASS"))
    exp.append(("live_vocab_disconnect_reproduced", live["vocab"]["detected"] is True))

    # --- mutation controls -------------------------------------------------------------
    base_text = snap.read_text()
    mut_rows = []
    for name, doc, want_fail in mutants(base_text):
        if doc is None:
            p = STAGE / f"{name}.yaml"
            p.write_bytes(snap.read_bytes())
            res = run_live(p)
            res.pop("pin", None)
        else:
            p = STAGE / f"{name}.yaml"
            p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
            res = run_mutant(doc)
        got = failed(res)
        caught = set(want_fail) <= got
        mut_rows.append({"mutant": name, "path": str(p.relative_to(ROOT)),
                         "expected_failing_checks": want_fail,
                         "observed_failing_checks": sorted(got),
                         "caught": caught,
                         "scalar_violations": len(res["scalar"]["violations"])})
        exp.append((f"mutant_{name}", caught if want_fail else (got == set())))

    expectations_met = all(ok for _, ok in exp)
    report = {
        "task_id": "W055-A0-RUBRIC-01",
        "worker": "worker-055",
        "actor": "worker-055",
        "reviewer_role": "bounded execution worker (independent; not the author of A0)",
        "created_at": now_iso(),
        "node_id": "A0",
        "gate": "G-AUDIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN",
                      "AF-WCC-SCALAR-SPH"],
        "artifact_path": "evaluation_rubric.yaml",
        "artifact_sha256": EXPECTED_SHA,
        "snapshot": str(snap.relative_to(ROOT)),
        "snapshot_sha256": sha256_file(snap),
        "counts_as_full_schema_verdict": True,
        "question": "Does A0 satisfy the G-AUDIT criterion 'exists without a universal scalar "
                    "score', and does the underlying rubric accept the frozen class artifacts?",
        "checks": live,
        "expectations": [{"check": k, "ok": v} for k, v in exp],
        "expectations_met": expectations_met,
        "mutations": mut_rows,
        "verdict": None,  # filled below
        "score": None,
        "hard_failures": [],
        "advisory_findings": [],
        "falsifiers": [],
    }

    # honest verdict from measured checks (the vocabulary disconnect is the blocker)
    hf = []
    if live["vocab"]["detected"]:
        hf.append({
            "id": "HF-055-A0-1",
            "severity": "blocking",
            "axis": "vocabulary disconnect / self-consistency of the rubric with its gate inputs",
            "finding": "A0's G-FORM genericity enum and per-class conclusion_primary vocabulary do "
                       "not cover the frozen schemas it exists to gate: genericity enum "
                       f"{live['vocab']['genericity_enum']} vs schema kinds "
                       f"{[r['genericity_kind'] for r in live['vocab']['rows']]}; per-class "
                       "conclusion sets do not contain the schemas' conclusion_type values "
                       f"{[r['conclusion_type'] for r in live['vocab']['rows']]}. A literal "
                       "G-FORM/HF-02 reading therefore rejects all three frozen schemas.",
            "machine_evidence": "check_a0_rubric.py::check_vocab_disconnect rows",
            "falsifier": "show a rubric enum/keyword (alias table or mapping block) that maps "
                         "residual_comeager and the scc_* conclusion types into the rubric's "
                         "allowed sets at the pinned hash",
        })
    if live["gaudit"]["status"] == "ADVISORY":
        report["advisory_findings"].append({
            "id": "ADV-055-A0-1", "severity": "minor",
            "finding": live["gaudit"]["detail"]})
    if live["metrics"]["advisory_missing"]:
        report["advisory_findings"].append({
            "id": "ADV-055-A0-2", "severity": "minor",
            "finding": "mission progress metrics absent from A0.metrics: "
                       f"{live['metrics']['advisory_missing']} (hard_failure_rate and "
                       "information_gain are present; this is a completeness gap, not a "
                       "violation of the G-AUDIT criterion)"})

    scalar_ok = live["scalar"]["verdict"] == "PASS_no_universal_scalar_score"
    if hf:
        report["verdict"] = "revise"
        report["score"] = 3.0
    elif not scalar_ok:
        report["verdict"] = "revise"
        report["score"] = 2.0
    else:
        report["verdict"] = "accept"
        report["score"] = 4.0
    report["hard_failures"] = hf
    report["scalar_adjudication"] = {
        "question": "is 'universal_scalar_score_token_present: true' a real universal scalar score?",
        "answer": ("NO - the only scalar/universal-score tokens are prohibition mentions inside "
                   "the declared key no_universal_scalar_score and the promotion rule; zero "
                   "aggregate-score uses were found" if scalar_ok else
                   "YES - an aggregate scalar score use was found"),
        "violations": live["scalar"]["violations"],
        "mentions": live["scalar"]["mentions"],
        "raw_line_census": raw_scalar_census(base_text),
        "mutation_controls": [m["mutant"] for m in mut_rows if m["mutant"] != "M0_unmutated"],
    }
    report["falsifiers"] = [
        "hash drift: any change to evaluation_rubric.yaml bytes voids this verdict (pin "
        f"{EXPECTED_SHA[:12]}); re-run the instrument at the new hash",
        "scalar clause: a file at the canonical path that promotes/ranks with a single "
        "aggregate numeric score refutes the PASS on the G-AUDIT scalar criterion",
        "vocabulary clause: a declared alias/mapping at the pinned hash that maps "
        "residual_comeager and scc_c2/scc_c0 future-inextendibility into A0's allowed sets "
        "refutes HF-055-A0-1",
        "instrument clause: any staged mutant escaping its registered expected failing check "
        "refutes the instrument's discriminating power",
    ]
    report["authority"] = ("advisory worker verdict; no gate verdict, node status, or "
                           "validation_status is claimed")

    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"expectations_met": expectations_met,
                      "failed": [k for k, ok in exp if not ok],
                      "verdict": report["verdict"], "score": report["score"],
                      "hard_failures": [h["id"] for h in hf]}, indent=2))
    return 0 if expectations_met else 1


if __name__ == "__main__":
    sys.exit(main())

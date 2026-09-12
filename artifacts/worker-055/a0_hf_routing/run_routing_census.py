#!/usr/bin/env python3
"""W055-A0-HF-ROUTING-01 -- canonical critical-HF routing and liveness census.

Question (BL-7/BL-9 decision support, not a ruling): for each *critical* hard failure
HF-01..HF-14 of evaluation_rubric.yaml, which object surface does the canonical audit
runner actually feed it, is the canonical detector live on that surface, and is
ledger/theorems.jsonl reachable through that route?

Method: hash-guarded import of the canonical modules (artifacts/audit/audit_lib.py,
artifacts/audit/audit_run.py), static extraction of the runner's call sites, canonical
function-level liveness controls, a canonical CLI run over ledger/ only, and explicit
rubric-literal counters on the same ledger rows. Read-only on every canonical path: all
writes go under this task directory.

Exit 0 unless a hash guard fails or a control that must fire does not.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # artifacts/worker-055/a0_hf_routing -> repo root

PINS = {
    "evaluation_rubric.yaml": "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885",
    "artifacts/audit/audit_lib.py": "ae573db84631b970caeea46e8821aee8af66166f6a5f16251e4a6c819a377c8c",
    "artifacts/audit/audit_run.py": "3b27dd3fef7f41488158099f888e3685dc8d9cca9f0507ad46c4d01f9bd2c411",
    "ledger/theorems.jsonl": "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28",
    "artifacts/formulation/VOCAB_ALIASES.json": "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
}
CRITICAL_HFS = ["HF-01", "HF-02", "HF-03", "HF-05", "HF-06", "HF-10", "HF-14"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def guard_pins() -> dict:
    out = {}
    for rel, want in PINS.items():
        p = ROOT / rel
        got = sha256_file(p) if p.is_file() else None
        out[rel] = {"declared": want, "measured": got, "match": got == want}
    bad = [r for r, v in out.items() if not v["match"]]
    if bad:
        raise SystemExit(f"PIN GUARD FAILED: {bad}")
    return out


def load_canonical():
    sys.path.insert(0, str(ROOT / "artifacts" / "audit"))
    import audit_lib as A  # noqa: E402
    import audit_run as R  # noqa: E402
    return A, R


def vlist(vs) -> list:
    return [v.as_dict() for v in vs]


# ---------------------------------------------------------------------------------------
# static routing: which runner call site consumes which corpus surface
# ---------------------------------------------------------------------------------------
def static_routing(A, R) -> dict:
    run_lines = (ROOT / "artifacts/audit/audit_run.py").read_text().splitlines()
    lib_lines = (ROOT / "artifacts/audit/audit_lib.py").read_text().splitlines()

    invocations = []
    for i, line in enumerate(run_lines, 1):
        m = re.search(r"A\.(check_[a-z_]+|artifact_inventory|contamination\w*)\s*\(", line)
        if not m:
            continue
        surface = None
        for j in range(i - 2, max(-1, i - 9), -1):
            mm = re.search(r'for\s+\w+\s+in\s+(corpus\["[a-z]+"\])', run_lines[j])
            if mm:
                surface = mm.group(1)
                break
        invocations.append({"line": i, "call": m.group(1),
                            "iterates": surface, "text": line.strip()})

    def enclosing_def(idx0: int):
        for j in range(idx0, -1, -1):
            m = re.match(r"def\s+(\w+)", lib_lines[j])
            if m:
                return m.group(1)
        return None

    hf_index: dict[str, list] = {}
    for i, line in enumerate(lib_lines, 1):
        for hf in re.findall(r'"(HF-\d\d)"', line):
            hf_index.setdefault(hf, []).append({"line": i, "function": enclosing_def(i - 1)})

    hf10_hits = {}
    for p in sorted((ROOT / "artifacts/audit").glob("*.py")):
        n = len(re.findall(r"HF-10", p.read_text(errors="replace")))
        if n:
            hf10_hits[str(p.relative_to(ROOT))] = n

    return {
        "runner_invocations": invocations,
        "hf_implementation_index": hf_index,
        "implemented_critical_hfs": sorted(h for h in CRITICAL_HFS if h in hf_index),
        "critical_hfs_without_canonical_detector": sorted(h for h in CRITICAL_HFS if h not in hf_index),
        "hf10_literal_hits_in_audit_tooling": hf10_hits,
    }


# ---------------------------------------------------------------------------------------
# liveness controls on the canonical functions
# ---------------------------------------------------------------------------------------
def liveness_controls(A, classes: dict) -> list:
    ctrls = []

    def run(cid, expect_hf, producer, expect_absent=False, expect_severity=None):
        vs = producer()
        hfs = [v.hf for v in vs]
        crit = [v.hf for v in vs if v.severity == "critical"]
        fired = (expect_hf not in hfs) if expect_absent else (expect_hf in hfs)
        sev_ok = True if expect_severity is None else (expect_hf in crit if expect_severity == "critical"
                                                       else expect_hf in hfs)
        ctrls.append({"control": cid, "expect_hf": expect_hf, "expect_absent": expect_absent,
                      "observed_hfs": hfs, "observed_critical_hfs": sorted(set(crit)),
                      "fired_as_expected": bool(fired and sev_ok),
                      "violations": vlist(vs)})

    run("CTL-HF-01-theorem-no-artifact_refs", "HF-01", lambda: A.check_class_binding({
        "claim_id": "CTL-HF-01", "class_id": "AF-WCC-VAC-GEN",
        "statement": "Every admissible datum in the declared set has a complete future null infinity.",
        "assumptions": "genericity is defined by the comeager set G of the class",
        "conclusion_type": "theorem",
        "falsifier": "exhibit one datum in G with incomplete future null infinity"}, classes),
        expect_severity="critical")

    run("CTL-HF-02-C0-or-C2-disjunction", "HF-02", lambda: A.check_class_binding({
        "claim_id": "CTL-HF-02-disj", "class_id": "AF-SCC-C2-VAC-GEN",
        "statement": "The maximal development is C0 or C2 inextendible.",
        "assumptions": "vacuum, asymptotically flat", "conclusion_type": "numerical_evidence",
        "falsifier": "exhibit an extension of the stated regularity"}, classes),
        expect_severity="critical")

    run("CTL-HF-02-second-frozen-class-mention", "HF-02", lambda: A.check_class_binding({
        "claim_id": "CTL-HF-02-mention", "class_id": "AF-WCC-VAC-GEN",
        "statement": "Compare the AF-SCC-C0-VAC-GEN conclusion with the present one.",
        "assumptions": "vacuum, asymptotically flat", "conclusion_type": "numerical_evidence",
        "falsifier": "exhibit the transfer"}, classes),
        expect_severity="critical")

    run("CTL-HF-02-unknown-class-token", "HF-02", lambda: A.check_class_binding({
        "claim_id": "CTL-HF-02-unknown", "class_id": "AF-NOPE-VAC-GEN",
        "statement": "Vacuous control statement.", "assumptions": "none",
        "conclusion_type": "numerical_evidence", "falsifier": "none"}, classes),
        expect_severity="critical")

    run("CTL-HF-02-process-scope-with-math-conclusion", "HF-02", lambda: A.check_class_binding({
        "claim_id": "CTL-HF-02-process", "class_id": "GLOBAL", "node_id": "N0",
        "statement": "The calibrated scheme is second order.", "assumptions": "none",
        "conclusion_type": "theorem", "falsifier": "measure order one"}, classes),
        expect_severity="critical")

    run("CTL-HF-02-cross-class-evidence-no-transfer", "HF-02", lambda: A.check_class_binding({
        "claim_id": "CTL-HF-02-evidence", "class_id": "AF-SCC-C2-VAC-GEN",
        "statement": "The development is inextendible in the stated regularity.",
        "assumptions": "vacuum, asymptotically flat", "conclusion_type": "numerical_evidence",
        "falsifier": "exhibit the extension",
        "evidence_refs": [{"source_meta": {"formulation": "SCC-C0"}}]}, classes),
        expect_severity="critical")

    run("CTL-HF-03-unresolved-citation", "HF-03", lambda: A.check_citations(
        {"claim_id": "CTL-HF-03", "citation_refs": ["CITE-X"]},
        {"CITE-X": {"resolution_status": "unresolved"}}), expect_severity="critical")

    def _fake_map():
        d = HERE / "controls_tmp"
        d.mkdir(exist_ok=True)
        p = d / "fake_map_ctl_hf05.json"
        p.write_text(json.dumps({"groups": [{"id": "G-TEST", "nodes": [
            {"id": "N-TEST", "status": "done",
             "artifact": "artifacts/__ctl_hf05_absent__.json",
             "validation_status": "unverified"}]}]}))
        return A.check_map_integrity(p)

    run("CTL-HF-05-done-without-artifact", "HF-05", _fake_map, expect_severity="critical")

    run("CTL-HF-06-claim-without-falsifier", "HF-06", lambda: A.check_class_binding({
        "claim_id": "CTL-HF-06", "class_id": "AF-WCC-VAC-GEN",
        "statement": "Vacuous control statement.", "assumptions": "none",
        "conclusion_type": "numerical_evidence"}, classes),
        expect_severity="critical")

    def _hf10_probe():
        # defect-shaped object per the rubric detector; no canonical function reads this shape
        return A.check_seed_hygiene({"seeds": [1, 2, 3], "statistic": {"max": 0.9},
                                     "llm_generated_code": True, "same_process": True,
                                     "truncated_calls": 5, "separately_counted": False})

    run("CTL-HF-10-no-canonical-detector", "HF-10", _hf10_probe, expect_absent=True)

    run("CTL-HF-14-self-certified-record", "HF-14", lambda: A.check_self_certification(
        [{"theorem_id": "CTL-HF-14", "status": "accepted", "supports_claim": True}]),
        expect_severity="critical")

    run("NEG-HF-01-with-artifact_refs", "HF-01", lambda: A.check_class_binding({
        "claim_id": "NEG-HF-01", "class_id": "AF-WCC-VAC-GEN",
        "statement": "Control statement.", "assumptions": "vacuum, asymptotically flat",
        "conclusion_type": "theorem", "falsifier": "exhibit the failure",
        "artifact_refs": ["artifacts/x.json#sha256:deadbeef"]}, classes), expect_absent=True)

    run("NEG-HF-02-GLOBAL-on-A-node", "HF-02", lambda: A.check_class_binding({
        "claim_id": "NEG-HF-02", "class_id": "GLOBAL", "node_id": "A0",
        "statement": "The audit harness is scoped.", "assumptions": "none",
        "conclusion_type": "theorem", "falsifier": "exhibit the scope error"}, classes),
        expect_absent=True)

    run("NEG-HF-14-with-reviewer-verdict", "HF-14", lambda: A.check_self_certification(
        [{"theorem_id": "NEG-HF-14", "status": "accepted", "supports_claim": True,
          "reviewer_verdicts": ["worker-000"]}]), expect_absent=True)

    def _clean():
        return A.check_class_binding({
            "claim_id": "NEG-clean", "class_id": "AF-WCC-VAC-GEN",
            "statement": "Control statement.", "assumptions": "vacuum, asymptotically flat",
            "conclusion_type": "numerical_evidence", "falsifier": "exhibit the failure"}, classes)

    run("NEG-clean-claim-zero-violations", "HF-01", _clean, expect_absent=True)

    return ctrls


# ---------------------------------------------------------------------------------------
# canonical CLI probe corpora (records routing incl. the inline invented-token loop)
# ---------------------------------------------------------------------------------------
def probe_corpus_controls() -> dict:
    out = {}
    for name, tokens in (("probe_ok", ["DEFINITIONS", "GLOBAL"]), ("probe_bogus", ["AF-BOGUS-CLASS"])):
        d = HERE / name
        d.mkdir(exist_ok=True)
        rec = {"theorem_id": f"W055-{name.upper()}", "class_ids": tokens,
               "statement_exact": "Routing control record for the canonical audit runner.",
               "conclusion_type": "formal_model"}
        (d / "routing_probe.jsonl").write_text(json.dumps(rec) + "\n")
        rep_dir = HERE / f"{name}_out"
        cp = subprocess.run([sys.executable, str(ROOT / "artifacts/audit/audit_run.py"),
                             "--scan", str(d), "--out", str(rep_dir), "--quiet"],
                            capture_output=True, text=True, cwd=str(ROOT))
        reports = sorted(rep_dir.glob("audit-*.json"))
        rep = json.loads(reports[-1].read_text()) if reports else {}
        class_token = [v for v in rep.get("violations", []) if v.get("where") == "ledger:class-token"]
        out[name] = {"exit_code": cp.returncode,
                     "report": str(reports[-1].relative_to(ROOT)) if reports else None,
                     "report_sha256": sha256_file(reports[-1]) if reports else None,
                     "corpus": rep.get("corpus"), "class_token_violations": class_token,
                     "stdout_tail": cp.stdout.strip().splitlines()[-1:] }
    return out


# ---------------------------------------------------------------------------------------
# ledger: canonical pipeline vs rubric-literal readings
# ---------------------------------------------------------------------------------------
def ledger_census(A, R, classes: dict) -> dict:
    ledger = ROOT / "ledger" / "theorems.jsonl"
    rows = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    frozen = set(classes)

    # canonical CLI run over ledger/ only (runner default writes go to --out inside this task dir)
    rep_dir = HERE / "canonical_out"
    cp = subprocess.run([sys.executable, str(ROOT / "artifacts/audit/audit_run.py"),
                         "--scan", "ledger", "--out", str(rep_dir), "--quiet"],
                        capture_output=True, text=True, cwd=str(ROOT))
    reports = sorted(rep_dir.glob("audit-*.json"))
    rep = json.loads(reports[-1].read_text()) if reports else {}

    # in-process replica of audit_run.main() lines 231-263 restricted to the ledger corpus
    corpus = R.scan_corpus([ROOT / "ledger"])
    v = []
    for c in corpus["claims"]:
        v += A.check_class_binding(c, classes)
    registry = {}
    for c in corpus["citations"]:
        key = c.get("cite_key") or c.get("id") or c.get("title")
        if key:
            registry[key] = c
    for c in corpus["claims"]:
        v += A.check_citations(c, registry)
    for r in corpus["results"]:
        v += A.check_seed_hygiene(r)
    v += A.check_ledger_scope(corpus["citations"])
    v += A.check_self_certification(corpus["records"])
    invented = {}
    for rec in corpus["records"]:
        for cid in rec.get("class_ids", []) or []:
            if cid not in frozen and cid not in ("DEFINITIONS", "GLOBAL"):
                invented[cid] = invented.get(cid, 0) + 1
    for cid, n in sorted(invented.items()):
        v.append(A.Violation("HF-02", "critical", "ledger:class-token",
                             f"invented class token {cid!r} used by {n} ledger entries", {}))
    by_hf: dict[str, int] = {}
    for x in v:
        by_hf[x.hf] = by_hf.get(x.hf, 0) + 1

    # rubric-literal counters on the same 62 rows
    lit_hf01 = [r["theorem_id"] for r in rows
                if r.get("conclusion_type") == "theorem" and not r.get("artifact_refs")]
    lit_hf02_disj = [r["theorem_id"] for r in rows
                     if len([c for c in (r.get("class_ids") or []) if c in frozen]) >= 2]
    lit_hf02_unknown = sorted({c for r in rows for c in (r.get("class_ids") or [])
                               if c not in frozen and c not in ("DEFINITIONS", "GLOBAL")})
    lit_hf14 = [r["theorem_id"] for r in rows
                if (str(r.get("status", "")).lower() in ("accepted", "passed")
                    or r.get("supports_claim") is True
                    or str(r.get("validation_status", "")).lower() == "passed")
                and not (r.get("reviewer_verdicts") or r.get("review_verdict") or r.get("reviewed_by"))]
    allowed = {cid: set(cls.get("conclusion_implied", []) or []) | {cls.get("conclusion_primary")}
               for cid, cls in classes.items()}
    single = [r for r in rows if len([c for c in (r.get("class_ids") or []) if c in frozen]) == 1]
    lit_hf02_concl_rowtype = [r["theorem_id"] for r in single
                              if r.get("conclusion_type") not in allowed[
                                  [c for c in r["class_ids"] if c in frozen][0]]]
    lit_hf02_concl_theorem = [r["theorem_id"] for r in single
                              if r.get("conclusion_type") == "theorem"
                              and "theorem" not in allowed[[c for c in r["class_ids"] if c in frozen][0]]]
    aliases = json.loads((ROOT / "artifacts/formulation/VOCAB_ALIASES.json").read_text())
    concl_alias_closure = {}
    for canonical, al in aliases.get("conclusion_type", {}).items():
        concl_alias_closure.setdefault(canonical, set()).update([canonical, *al])
    schema_token = {"AF-WCC-VAC-GEN": "weak_cosmic_censorship",
                    "AF-SCC-C2-VAC-GEN": "scc_c2_future_inextendibility",
                    "AF-SCC-C0-VAC-GEN": "scc_c0_future_inextendibility",
                    "AF-WCC-SCALAR-SPH": "weak_cosmic_censorship"}
    lit_hf02_concl_vocab = []
    for r in single:
        cid = [c for c in r["class_ids"] if c in frozen][0]
        rubric_vals = allowed[cid]
        closure = set()
        for rv in rubric_vals:
            closure |= concl_alias_closure.get(rv, {rv})
        if schema_token[cid] not in closure and schema_token[cid] not in rubric_vals:
            lit_hf02_concl_vocab.append(r["theorem_id"])
    rubric_cited = {tid: {k: r.get(k) for k in ("status", "supports_claim", "validation_status",
                                                "reviewer_verdicts")}
                    for r in rows if r.get("theorem_id") in ("T-201", "T-202", "T-203")
                    for tid in [r["theorem_id"]]}

    return {
        "ledger_rows": len(rows),
        "canonical_cli": {
            "exit_code": cp.returncode,
            "report": str(reports[-1].relative_to(ROOT)) if reports else None,
            "report_sha256": sha256_file(reports[-1]) if reports else None,
            "corpus": rep.get("corpus"), "summary": rep.get("summary"),
        },
        "canonical_in_process": {"sections": {k: (len(x) if isinstance(x, list) else x)
                                              for k, x in corpus.items()},
                                 "violations_by_hf": by_hf, "violations": vlist(v)},
        "rubric_literal": {
            "HF-01-theorem-without-artifact_refs": {"count": len(lit_hf01), "ids": lit_hf01},
            "HF-02-disjunction-of-frozen-class-ids": {"count": len(lit_hf02_disj), "ids": lit_hf02_disj},
            "HF-02-unknown-class-token": {"count": len(lit_hf02_unknown), "tokens": lit_hf02_unknown},
            "HF-02-conclusion_type-not-allowed-rowtype-reading": {
                "count": len(lit_hf02_concl_rowtype), "ids": lit_hf02_concl_rowtype},
            "HF-02-conclusion_type-not-allowed-theorem-rows-only": {
                "count": len(lit_hf02_concl_theorem), "ids": lit_hf02_concl_theorem},
            "HF-02-conclusion_type-not-allowed-vocabulary-reading": {
                "count": len(lit_hf02_concl_vocab), "ids": lit_hf02_concl_vocab},
            "HF-14-self-certified-record": {"count": len(lit_hf14), "ids": lit_hf14},
            "rubric_evidence_rows_T201-T203_live_fields": rubric_cited,
        },
    }


def compute() -> dict:
    pins = guard_pins()
    A, R = load_canonical()
    classes = A.frozen_classes(A.load_rubric(A.RUBRIC))
    return {
        "task_id": "W055-A0-HF-ROUTING-01",
        "actor": "worker-055",
        "generated_at": now_iso(),
        "pins": pins,
        "critical_hfs": CRITICAL_HFS,
        "static_routing": static_routing(A, R),
        "liveness_controls": liveness_controls(A, classes),
        "probe_corpus_controls": probe_corpus_controls(),
        "ledger_census": ledger_census(A, R, classes),
        "authority_note": ("Advisory worker measurement only: no gate verdict, no node status, "
                           "no validation_status, no ruling on the BL-7/BL-9 scope question. "
                           "Read-only on all canonical paths."),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "report.json"))
    ap.add_argument("--determinism", action="store_true")
    a = ap.parse_args()

    res = compute()
    det = None
    if a.determinism:
        r2 = compute()
        strip = lambda d: json.dumps({k: v for k, v in d.items() if k != "generated_at"},
                                     sort_keys=True)
        det = {"run1": hashlib.sha256(strip(res).encode()).hexdigest(),
               "run2": hashlib.sha256(strip(r2).encode()).hexdigest()}
        det["identical"] = det["run1"] == det["run2"]
    res["determinism"] = det
    res["content_sha256"] = hashlib.sha256(
        json.dumps({k: v for k, v in res.items() if k not in ("generated_at", "content_sha256")},
                   sort_keys=True).encode()).hexdigest()

    Path(a.out).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    bad = [c["control"] for c in res["liveness_controls"]
           if c["expect_hf"] != "HF-10" and not c["fired_as_expected"]]
    bad += [k for k, v in res["probe_corpus_controls"].items()
            if (k == "probe_ok" and v["class_token_violations"])
            or (k == "probe_bogus" and not v["class_token_violations"])]
    print(json.dumps({"written": a.out, "content_sha256": res["content_sha256"],
                      "failed_controls": bad,
                      "literal_counts": {k: v.get("count") for k, v in
                                         res["ledger_census"]["rubric_literal"].items()
                                         if isinstance(v, dict)}},
                     indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

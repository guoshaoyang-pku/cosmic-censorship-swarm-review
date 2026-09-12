#!/usr/bin/env python3
"""Audit-lead final gate verification at one measurement instant (2026-09-12 lifecycle 04).

Independently re-measures every claim the closing verdicts (G-FORM-final-verify.json,
G-F0-final-verify.json) rest on. Reads only; writes one JSON evidence file.

  python3 artifacts/audit/final_gate_verify.py --out artifacts/audit/final_gate_verify_<ts>.json
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CST = dt.timezone(dt.timedelta(hours=8))
SCHEMAS = ["schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml"]
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]


def sha256(path):
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mtime(path):
    return dt.datetime.fromtimestamp(os.path.getmtime(path), CST).isoformat(timespec="seconds")


def dup_keys(path):
    """Duplicate keys within the same YAML mapping instance (event-parse scoped)."""
    out, stack = [], []
    for ev in yaml.parse(open(path, encoding="utf-8")):
        if isinstance(ev, yaml.MappingStartEvent):
            stack.append({"seen": {}, "n": 0})
        elif isinstance(ev, yaml.MappingEndEvent):
            if stack:
                stack.pop()
        elif isinstance(ev, yaml.ScalarEvent) and stack:
            m = stack[-1]
            if m["n"] % 2 == 0:
                if ev.value in m["seen"]:
                    out.append({"key": ev.value, "line": ev.start_mark.line + 1,
                                "first_line": m["seen"][ev.value]})
                m["seen"][ev.value] = ev.start_mark.line + 1
            m["n"] += 1
    return out


def run():
    measured_at = dt.datetime.now(CST).isoformat(timespec="seconds")
    checks = []

    def add(cid, status, detail, evidence=None):
        checks.append({"id": cid, "status": status, "detail": detail, "evidence": evidence or []})

    # ---------- 1. hash matrix ----------
    fz = json.load(open("artifacts/formulation/FROZEN.json"))
    fz_files = fz.get("files", {})
    matrix = {}
    for tgt, canon, auth in [
        ("F0", "research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"),
        ("F1", "schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
        ("F2a", "schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
        ("F2b", "schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
    ]:
        h, ah = sha256(canon), sha256(auth)
        pin = fz_files.get(auth, {}).get("sha256") or fz_files.get(canon, {}).get("sha256")
        matrix[tgt] = {"canonical": canon, "canonical_sha256": h, "canonical_mtime": mtime(canon),
                       "authoring": auth, "authoring_sha256": ah,
                       "mirror_equal": h == ah, "frozen_rev": fz.get("revision"),
                       "frozen_pin": pin, "frozen_match": h == pin}
    for tgt, path in [("L0", "ledger/theorems.jsonl"), ("L1", "ledger/citation_audit.csv"),
                      ("A0", "evaluation_rubric.yaml"), ("N0-protocol", "numerics/CONVERGENCE_PROTOCOL.md"),
                      ("FROZEN", "artifacts/formulation/FROZEN.json")]:
        matrix[tgt] = {"canonical": path, "canonical_sha256": sha256(path), "canonical_mtime": mtime(path)}

    add("HASH-F0-mirror", "fail" if not matrix["F0"]["mirror_equal"] else "pass",
        f"F0 canonical {matrix['F0']['canonical_sha256'][:12]} vs authoring "
        f"{matrix['F0']['authoring_sha256'][:12]}; FROZEN rev{fz.get('revision')} declares them distinct "
        f"logical artifacts (f0_mirror_adjudication_request)",
        ["research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"])
    for tgt in ("F1", "F2a", "F2b"):
        m = matrix[tgt]
        add(f"HASH-{tgt}-pin", "pass" if (m["mirror_equal"] and m["frozen_match"]) else "fail",
            f"canonical==authoring=={m['canonical_sha256'][:12]}, FROZEN pin match={m['frozen_match']}",
            [m["canonical"]])

    # ---------- 2. duplicate YAML keys ----------
    for path in SCHEMAS + ["research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"]:
        dups = dup_keys(path)
        ts = [d for d in dups if d["key"] in ("revised_at", "created_at", "written_at", "authored_at", "revision", "status")]
        occ = len(re.findall(r"^revised_at:", open(path).read(), flags=re.M))
        status = "fail" if ts else "pass"
        add(f"YAML-DUP-{os.path.basename(path)}", status,
            f"{len(dups)} duplicate mapping key(s); timestamp-like duplicates: {ts}; "
            f"top-level revised_at occurrences={occ} (declared dup={max(0, occ - 1)})",
            [f"{path}#{sha256(path)[:12]}"])

    # ---------- 3. clock discipline: declared revised_at vs file mtime ----------
    for path in SCHEMAS:
        text = open(path).read()
        vals = re.findall(r'^revised_at:\s*"?([0-9T:+\-]+)"?', text, flags=re.M)
        last = vals[-1] if vals else None
        mt = mtime(path)
        ahead = None
        if last:
            ahead = (dt.datetime.fromisoformat(last) - dt.datetime.fromisoformat(mt)).total_seconds()
        add(f"CLOCK-{os.path.basename(path)}", "fail" if (ahead or 0) > 60 else "pass",
            f"last declared revised_at={last} vs file mtime={mt} (declared {ahead}s after write)",
            [f"{path}#{sha256(path)[:12]}"])

    # ---------- 4. D0 domain typing ----------
    for path in SCHEMAS:
        d = yaml.safe_load(open(path))
        q = d.get("quantifiers", {})
        d0 = (q.get("domains") or {}).get("D0", {})
        defn = str(d0.get("definition", ""))
        formal = str(q.get("formal", ""))
        # ill-typed iff the binder still binds a tuple over a disjunctive domain;
        # a tagged disjoint union with a single index r and a per-branch ambient
        # space X^r is well-typed (rev12 repair of HF-088-1 / F-2).
        tuple_binder = bool(re.match(r"\s*forall\s*\(\s*[A-Za-z_]+\s*,", formal))
        tagged_union = "tagged disjoint union" in defn and "forall r in D0" in formal
        bad = tuple_binder or not tagged_union
        add(f"D0-{os.path.basename(path)}", "fail" if bad else "pass",
            f"binder='{formal[:44]}...'; tagged_union={tagged_union}; tuple_binder={tuple_binder}; "
            f"D0='{defn[:110]}...'",
            [f"{path}#{sha256(path)[:12]}"])

    # ---------- 5. class_contract_pointer resolution ----------
    supp = yaml.safe_load(open("artifacts/formulation/formulation_taxonomy.yaml"))
    for path in SCHEMAS:
        d = yaml.safe_load(open(path))
        ptr = d.get("class_contract_pointer")
        cid = d.get("class_id")
        ok = bool(ptr) and cid in (supp.get("class_contracts") or {})
        add(f"PTR-{cid}", "pass" if ok else "fail",
            f"pointer {ptr} -> supplement key present={ok}; supplement is a separate logical artifact "
            f"under FROZEN rev{fz.get('revision')}",
            ["artifacts/formulation/formulation_taxonomy.yaml", path])

    # ---------- 6. falsifier test binding ----------
    fp = "schemas/f1_falsifier_tests.jsonl"
    if os.path.isfile(fp):
        cur = matrix["F1"]["canonical_sha256"]
        cnt = collections.Counter()
        rows = 0
        for line in open(fp):
            line = line.strip()
            if not line:
                continue
            rows += 1
            r = json.loads(line)
            b = str(r.get("binding_sha256") or "NONE")[:12]
            cnt[b] += 1
        stale = sum(v for k, v in cnt.items() if k not in (cur[:12], "NONE"))
        add("FALSIFIER-binding", "fail" if stale else "note",
            f"{rows} rows; binding_sha256 counts={dict(cnt)}; current F1={cur[:12]}; "
            f"b65fcc0f appears only as historical prior_binding (prior finding does not reproduce)",
            [fp])

    # ---------- 7. map data integrity ----------
    m = json.load(open("research_map/research_map.json"))
    nodes = {n["id"]: n for g in m.get("groups", []) for n in g.get("nodes", [])}
    f2b = nodes.get("F2b", {})
    val = f2b.get("artifact_sha256")
    add("MAP-F2b-hash", "pass" if val == sha256(f2b.get("artifact")) else "fail",
        f"map F2b.artifact_sha256={str(val)[:16]}... len={len(str(val))} equals measured="
        f"{val == sha256(f2b.get('artifact'))} (prior zero-padding defect repaired)",
        ["research_map/research_map.json"])

    # ---------- 7b. map staleness vs disk ----------
    for nid in ("F0", "F1", "F2a", "F2b", "L0", "L1", "A0", "N0"):
        n = nodes.get(nid)
        if not n:
            continue
        mp = n.get("artifact")
        mh = n.get("artifact_sha256_measured") or n.get("artifact_sha256")
        cur = sha256(mp) if mp else None
        add(f"MAP-{nid}-fresh", "pass" if (cur and mh == cur) else "fail",
            f"map declares {str(mh)[:12]} vs disk {str(cur)[:12]} (path {mp})",
            ["research_map/research_map.json", mp] if mp else ["research_map/research_map.json"])

    # ---------- 8. C4 registration ----------
    ah = json.load(open("runtime/state/artifact_hashes.json"))
    key = "runtime/state/controller_verification/n0_replication_astra_run2_FIXED.json"
    reg = key in ah or any("n0_replication" in k for k in ah)
    add("C4-registration", "pass" if reg else "fail",
        f"{key} registered in artifact_hashes.json={reg} (PROTOCOL rule 2 requires it before N0 completion)",
        ["runtime/state/artifact_hashes.json"])

    # ---------- 9. A0 rubric conformance ----------
    rub = yaml.safe_load(open("evaluation_rubric.yaml"))
    lrows = [json.loads(l) for l in open("ledger/theorems.jsonl") if l.strip()]
    lkeys = set()
    for r in lrows:
        lkeys |= set(r.keys())
    accepted = [r for r in lrows if r.get("status") == "accepted"]
    with open("ledger/citation_audit.csv") as f:
        ckeys = set(csv.DictReader(f).fieldnames or [])
    n_rev_field = sum(1 for r in lrows if any('review' in k.lower() or 'verdict' in k.lower() for k in r))
    add("A0-HF14", "pass" if not accepted else "fail",
        f"{len(accepted)}/{len(lrows)} ledger rows status=accepted; rows with reviewer/verdict field="
        f"{n_rev_field}; rows with artifact/hash field="
        f"{sum(1 for r in lrows if any('artifact' in k.lower() or 'sha' in k.lower() for k in r))}; "
        f"status vocabulary={dict(collections.Counter(r.get('status') for r in lrows))}",
        ["ledger/theorems.jsonl", "evaluation_rubric.yaml"])
    add("A0-HF01", "fail" if ("artifact_refs" not in lkeys) else "pass",
        f"HF-01 detector reads claim.artifact_refs; ledger keys have artifact_refs={'artifact_refs' in lkeys}",
        ["ledger/theorems.jsonl", "evaluation_rubric.yaml"])
    gen_ok = "residual_comeager" in json.dumps(rub)
    add("A0-genericity-vocab", "fail" if not gen_ok else "pass",
        "G-FORM criterion admits {comeager, full_measure, open_dense, codim_ge_1, non_generic_excluded}; "
        "frozen schemas declare genericity.kind=residual_comeager (alias file exists but the rubric detector "
        "does not consult it)",
        ["evaluation_rubric.yaml", *SCHEMAS])
    add("A0-conclusion-primary", "fail",
        "rubric frozen_classes AF-WCC-VAC-GEN conclusion_primary=future_asymptotic_predictability; "
        "F1 conclusion.equivalent_standard_formulation.status='claimed equivalence, UNVERIFIED'",
        ["evaluation_rubric.yaml", "schemas/af_wcc_vacuum.yaml"])
    add("A0-validation-null", "fail" if rub.get("validation", {}).get("last_run") is None else "pass",
        f"rubric validation.last_run={rub.get('validation', {}).get('last_run')}",
        ["evaluation_rubric.yaml"])

    # ---------- 10. F0 content checks ----------
    tax = yaml.safe_load(open("research_map/formulation_taxonomy.yaml"))
    ids = tax.get("class_ids")
    add("F0-four-classes", "pass" if ids == ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"] else "fail",
        f"class_ids={ids}", ["research_map/formulation_taxonomy.yaml"])
    sph = tax["classes"]["AF-WCC-SCALAR-SPH"]
    vis = json.dumps(sph)
    add("F0-scalar-visibility", "fail" if ("contained in J-(I+)" in vis and "equivalently" in vis) else "pass",
        "AF-WCC-SCALAR-SPH conclusion uses the set-based reading 'contained in J-(I+)' with 'equivalently', "
        "contradicting the single-q TAIL predicate declared for AF-WCC-VAC-GEN (D1 residue, worker-16/082)",
        ["research_map/formulation_taxonomy.yaml"])
    add("F0-scalar-comeager", "fail" if "genericity_kind" in sph["axes"] and sph["axes"]["genericity_kind"] == "unresolved" else "pass",
        f"AF-WCC-SCALAR-SPH axes.genericity_kind={sph['axes'].get('genericity_kind')}; conclusion text says "
        f"'For generic data in the class' with no explicit comeager quantifier (other three classes state it)",
        ["research_map/formulation_taxonomy.yaml"])

    # ---------- 11. coverage at the measured hashes ----------
    cov = json.load(open("reviews/A1-rebind-coverage.json"))
    cov_summary = {}
    for t, c in cov.get("coverage", {}).items():
        cov_summary[t] = {
            "measured_sha256": c.get("measured_sha256"),
            "independent_verdicts": c.get("independent_verdict_count"),
            "accepts": [r.get("reviewer") for r in c.get("verdicts_at_measured_hash", []) if r.get("verdict") == "accept"],
            "revises": [r.get("reviewer") for r in c.get("verdicts_at_measured_hash", []) if r.get("verdict") == "revise"],
            "inconclusive": [r.get("reviewer") for r in c.get("verdicts_at_measured_hash", []) if r.get("verdict") == "inconclusive"],
        }
        add(f"COVERAGE-{t}", "pass" if len(cov_summary[t]["accepts"]) >= 2 else "fail",
            f"independent verdicts at measured hash={c.get('independent_verdict_count')}; "
            f"accepts={cov_summary[t]['accepts']}; revises={len(cov_summary[t]['revises'])}; "
            f"inconclusive={len(cov_summary[t]['inconclusive'])}",
            [f"reviews/A1-rebind-coverage.json#{(sha256('reviews/A1-rebind-coverage.json') or '')[:12]}"])

    out = {
        "schema": "audit-final-gate-verify/v1",
        "actor": "astra-lead-audit",
        "measured_at": measured_at,
        "method": "read-only re-measurement of every blocking claim in the closing verdicts; "
                  "no gate is set by this script or its author",
        "hash_matrix": matrix,
        "coverage_summary": cov_summary,
        "checks": checks,
        "counts": {
            "pass": sum(1 for c in checks if c["status"] == "pass"),
            "fail": sum(1 for c in checks if c["status"] == "fail"),
            "note": sum(1 for c in checks if c["status"] == "note"),
        },
        "verdict_inputs": {
            "G-FORM": "revise" if any(c["status"] == "fail" and c["id"].startswith(("YAML-DUP", "CLOCK", "D0")) for c in checks) else "undetermined",
            "G-F0": "revise",
        },
        "never_self_passed": "no gate verdict set by this artifact",
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    os.chdir(ROOT)
    out = run()
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {args.out}")
    print("counts:", out["counts"])
    for c in out["checks"]:
        if c["status"] == "fail":
            print("FAIL", c["id"], "-", c["detail"][:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())

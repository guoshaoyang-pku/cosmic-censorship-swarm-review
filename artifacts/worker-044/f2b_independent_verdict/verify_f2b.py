#!/usr/bin/env python3
"""W044-F2B-INDEP-VERDICT-01 — independent class-binding verification of the canonical
F2b schema (class AF-SCC-C0-VAC-GEN, path schemas/af_scc_c0_vacuum.yaml).

Why this shape:
  * The canonical class schemas were being rewritten while this worker ran (mtime churn
    00:19:14). A verdict bound to a byte revision that moves under the reviewer is worthless,
    so phase 0 is a bounded FREEZE-SETTLEMENT gate: canonical == authoring == FROZEN pin for
    all four class artifacts, stable over consecutive samples. If it does not settle inside
    the cap, the honest output is a moving-target blocker, not a verdict.
  * Per HANDOFF ("run the null first"), the check battery includes NULL CONTROLS (canonical
    schemas must be accepted) and MUTATION CONTROLS (a class-swapped or composite-regularity
    schema must be rejected, a C0/C2 merge text must be flagged). Without those, a green
    verdict says nothing about the checker's discriminating power.
  * Every observation is hash-pinned to a snapshot read once, and re-measured after the run;
    drift during the window voids the verdict.

Output: report.json next to this file. Exit codes:
  0 = settled + all checks pass          3 = settled + hard content failure(s)
  4 = freeze did not settle inside cap   2 = internal error
No claim of gate verdict, node completion, or mathematics/physics is made.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

TARGET = "schemas/af_scc_c0_vacuum.yaml"
AUTHORING = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
SIBLING_C2 = "schemas/af_scc_c2_vacuum.yaml"
SIBLING_WCC = "schemas/af_wcc_vacuum.yaml"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
TAXONOMY_AUTHORING = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
GATE = "artifacts/formulation/tools/check_class_schema.py"
AUDITOR = "artifacts/worker-06/spec_conformance_audit.py"
C0 = "AF-SCC-C0-VAC-GEN"
C2 = "AF-SCC-C2-VAC-GEN"
WCC = "AF-WCC-VAC-GEN"
SPH = "AF-WCC-SCALAR-SPH"
FROZEN_FILES = [TARGET, SIBLING_C2, SIBLING_WCC, TAXONOMY]
AUTHORING_OF = {
    TARGET: AUTHORING,
    SIBLING_C2: "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    SIBLING_WCC: "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    TAXONOMY: TAXONOMY_AUTHORING,
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def jsonable(o):
    """Defensive: never let an unserializable value kill the report write."""
    if isinstance(o, dict):
        return {str(k): jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [jsonable(v) for v in o]
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    return str(o)


def mtime(p) -> str:
    return datetime.fromtimestamp(Path(p).stat().st_mtime, CST).isoformat(timespec="seconds")


def do_measure() -> dict:
    """One measurement sample: FROZEN revision/pins vs canonical and authoring bytes."""
    fz = json.loads((ROOT / FROZEN).read_text())
    files = {}
    settled = True
    for rel in FROZEN_FILES:
        disk = sha(ROOT / rel)
        pin = (fz.get("files", {}).get(rel) or {}).get("sha256")
        rec = {"canonical": disk, "pin": pin, "pin_matches": disk == pin,
               "canonical_mtime": mtime(ROOT / rel)}
        if rel in AUTHORING_OF:
            auth = sha(ROOT / AUTHORING_OF[rel])
            rec["authoring"] = auth
            rec["authoring_mtime"] = mtime(ROOT / AUTHORING_OF[rel])
            rec["authoring_matches"] = auth == disk
            settled = settled and auth == disk
        settled = settled and disk == pin
        files[rel] = rec
    return {"at": now(), "frozen_revision": fz.get("revision"),
            "frozen_frozen_at": fz.get("frozen_at"), "frozen_mtime": mtime(ROOT / FROZEN),
            "files": files, "settled": settled}


def run_gate(path) -> dict:
    r = subprocess.run([sys.executable, str(ROOT / GATE), "--json", str(path)],
                       capture_output=True, text=True, timeout=180)
    try:
        rep = json.loads(r.stdout[r.stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        rep = {"verdict": "no_verdict", "stdout": r.stdout[-400:], "stderr": r.stderr[-400:]}
    rep["_exit"] = r.returncode
    return rep


def run_auditor(path, out) -> dict:
    r = subprocess.run([sys.executable, str(ROOT / AUDITOR), str(path), "--json", str(out)],
                       capture_output=True, text=True, timeout=180)
    try:
        rep = json.loads(Path(out).read_text())
    except (ValueError, OSError):
        rep = {"verdict": "no_verdict", "stdout": r.stdout[-400:], "stderr": r.stderr[-400:]}
    rep["_exit"] = r.returncode
    return rep


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=360, help="freeze-settlement cap (s)")
    ap.add_argument("--interval", type=int, default=10)
    ap.add_argument("--stable", type=int, default=2)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "mutations").mkdir(exist_ok=True)

    report = {
        "task_id": "W044-F2B-INDEP-VERDICT-01",
        "actor": "worker-044",
        "node_id": "F2b",
        "class_id": C0,
        "created_at": now(),
        "target_path": TARGET,
        "method": ("bounded freeze-settlement gate -> single-read hash-pinned snapshot -> canonical structural gate + "
                   "class-separation checker + independent YAML assertions + null/mutation controls -> post-run drift re-measure"),
        "does_not_claim": ["G-FORM verdict", "node completion", "theorem/counterexample/physics result",
                           "authority to set validation_status or gate verdict"],
        "sample_log": [], "checks": [], "moving_target": None,
    }

    # ---- phase 0: bounded freeze-settlement gate -------------------------------
    samples = []
    stable = 0
    deadline = time.time() + args.cap
    settled_sample = None
    while True:
        s = do_measure()
        samples.append(s)
        prev = samples[-2] if len(samples) >= 2 else None
        same = prev is not None and all(
            prev["files"][k]["canonical"] == s["files"][k]["canonical"] for k in s["files"]
        ) and prev["frozen_revision"] == s["frozen_revision"]
        stable = stable + 1 if (same and s["settled"]) else 0
        print(f"[settle] {s['at']} rev={s['frozen_revision']} c0={s['files'][TARGET]['canonical'][:12]} "
              f"settled={s['settled']} stable={stable}", flush=True)
        if s["settled"] and stable >= args.stable:
            settled_sample = s
            break
        if time.time() >= deadline:
            break
        time.sleep(args.interval)
    report["sample_log"] = samples
    publication_unsettled = None
    if settled_sample is None:
        # Strict settle failed. Continue only if the TARGET itself is aligned and stable in the
        # last two samples: content checks on a pinned C0 snapshot still carry information even
        # when a sibling/taxonomy mirror is lagging, but the verdict cannot bind as a gate review.
        target_ready = False
        if len(samples) >= 2:
            t1, t2 = samples[-2]["files"][TARGET], samples[-1]["files"][TARGET]
            target_ready = (t1["pin_matches"] and t1.get("authoring_matches") and t2["pin_matches"]
                            and t2.get("authoring_matches") and t1["canonical"] == t2["canonical"])
        if not target_ready:
            report["moving_target"] = {
                "verdict": "UNSETTLED",
                "cap_seconds": args.cap,
                "observed": [{k: {"canonical": v["files"][k]["canonical"][:16],
                                  "pin": (v["files"][k]["pin"] or "")[:16],
                                  "pin_matches": v["files"][k]["pin_matches"],
                                  "authoring_matches": v["files"][k].get("authoring_matches")}
                              for k in FROZEN_FILES} | {"at": v["at"], "frozen_revision": v["frozen_revision"]}
                             for v in samples[-4:]],
                "finding": ("canonical/authoring/FROZEN pins did not reach a stable agreement inside the cap, and even the "
                            "F2b target was not stably aligned; a class-binding verdict on any byte revision observed here "
                            "would be void on arrival"),
                "falsifier": "the canonical path settles (canonical == authoring == FROZEN pin for all four class artifacts) "
                             "and a re-run of this task at the settled revision yields a verdict",
            }
            report["summary"] = {"total": 0, "pass": 0, "fail": 0, "hard_failures": ["FREEZE-UNSETTLED"],
                                 "verdict": "blocked", "score": 0}
            (OUT / "report.json").write_text(json.dumps(jsonable(report), indent=2, sort_keys=True))
            print("FREEZE_UNSETTLED (target not aligned) -> blocker report written", flush=True)
            return 4
        settled_sample = samples[-1]
        publication_unsettled = {
            "target_aligned": True,
            "unsatisfied": [k for k in FROZEN_FILES
                            if not (samples[-1]["files"][k]["pin_matches"]
                                    and samples[-1]["files"][k].get("authoring_matches", True))],
            "last_sample": samples[-1],
        }
        report["publication_unsettled"] = publication_unsettled

    # ---- phase 1: single-read snapshot of the settled revision ----------------
    raw = (ROOT / TARGET).read_bytes()
    raw_sha = sha_bytes(raw)
    snapdir = OUT / "snapshot"
    snapdir.mkdir(exist_ok=True)
    snap = snapdir / f"af_scc_c0_vacuum.{raw_sha[:12]}.yaml"
    snap.write_bytes(raw)
    report["settled_revision"] = {
        "frozen_revision": settled_sample["frozen_revision"],
        "canonical_sha256": raw_sha,
        "canonical_path": TARGET,
        "authoring_path": AUTHORING,
        "authoring_sha256": settled_sample["files"][TARGET].get("authoring"),
        "pin_sha256": settled_sample["files"][TARGET]["pin"],
        "snapshot_path": str(snap.relative_to(ROOT)),
        "snapshot_sha256": sha(snap),
        "snapshot_byte_identical": sha(snap) == raw_sha,
        "settled_sample": settled_sample,
    }
    text = raw.decode()
    doc = yaml.safe_load(text)

    checks = []

    def check(cid, desc, expected, observed, ok, evidence, severity="hard"):
        checks.append({"check_id": cid, "description": desc, "expected": expected,
                       "observed": observed, "ok": bool(ok), "severity": severity,
                       "evidence": evidence})

    # ---- BIND: publication binding -------------------------------------------
    fz = json.loads((ROOT / FROZEN).read_text())
    check("BIND-01", "all four class artifacts canonical==authoring==FROZEN pin at settle",
          "all equal",
          {k: {kk: settled_sample["files"][k].get(kk) for kk in
               ("canonical", "pin", "pin_matches", "authoring", "authoring_matches")} for k in FROZEN_FILES},
          settled_sample["settled"],
          [FROZEN, TARGET, AUTHORING])
    check("BIND-02", "snapshot is a byte-identical copy of the canonical file read once",
          True, sha(snap) == raw_sha, sha(snap) == raw_sha,
          [f"{report['settled_revision']['snapshot_path']}#{raw_sha[:16]}"])
    check("BIND-03", "FROZEN manifest revision recorded",
          ">= 24", fz.get("revision"), True, [f"{FROZEN}#rev{fz.get('revision')}"], severity="info")

    # ---- GATE: canonical structural gate + null/mutation controls ------------
    g = run_gate(snap)
    check("GATE-01", "canonical structural gate accepts the pinned F2b snapshot",
          "pass", g.get("verdict"), g.get("verdict") == "pass" and g.get("_exit") == 0,
          [f"{GATE}#{sha(ROOT / GATE)[:16]}", f"{snap.relative_to(ROOT)}#{raw_sha[:16]}"])
    nulls = {}
    for rel in (SIBLING_C2, SIBLING_WCC):
        nulls[rel] = run_gate(ROOT / rel)
    nulls_ok = all(v.get("verdict") == "pass" for v in nulls.values())
    check("GATE-02", "NULL CONTROL: sibling canonical schemas are also accepted (gate is not reject-all)",
          "pass on C2 and WCC canonical", {k: v.get("verdict") for k, v in nulls.items()}, nulls_ok,
          [f"{SIBLING_C2}#{sha(ROOT / SIBLING_C2)[:16]}", f"{SIBLING_WCC}#{sha(ROOT / SIBLING_WCC)[:16]}"])

    mut = {}
    d1 = copy.deepcopy(doc)
    d1["class_id"] = C2
    p1 = OUT / "mutations" / "m1_class_id_swapped_to_C2.yaml"
    p1.write_text(yaml.safe_dump(d1, sort_keys=False, width=110))
    mut["M1_class_id_swapped_to_C2"] = run_gate(p1)
    d2 = copy.deepcopy(doc)
    d2["extension_predicate"]["frozen_regularity"] = "C2"
    d2["regularity"]["extension_regularity_exact"] = "C2 (twice differentiable) nondegenerate Lorentzian metric"
    p2 = OUT / "mutations" / "m2_extension_regularity_C2.yaml"
    p2.write_text(yaml.safe_dump(d2, sort_keys=False, width=110))
    mut["M2_extension_regularity_C2"] = run_gate(p2)
    m1_ok = mut["M1_class_id_swapped_to_C2"].get("verdict") != "pass"
    m2_ok = mut["M2_extension_regularity_C2"].get("verdict") != "pass"
    check("GATE-03", "MUTATION CONTROL: gate rejects a class_id swap C0->C2 (class binding is not vacuous)",
          "not pass", mut["M1_class_id_swapped_to_C2"].get("verdict"), m1_ok,
          [f"{p1.relative_to(ROOT)}#{sha(p1)[:16]}"])
    check("GATE-04", "MUTATION CONTROL: gate rejects an F2b schema declaring C2 extension regularity",
          "not pass", mut["M2_extension_regularity_C2"].get("verdict"), m2_ok,
          [f"{p2.relative_to(ROOT)}#{sha(p2)[:16]}"])

    # ---- SEP: class separation + independent non-merge assertions ------------
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs  # noqa: E402
    sep_findings = cs.findings_for_text(text, TARGET)
    check("SEP-01", "canonical class-separation checker returns no finding on the snapshot",
          "0 findings", sep_findings, len(sep_findings) == 0,
          [f"research_map/class_separation.py#{sha(ROOT / 'research_map/class_separation.py')[:16]}",
           f"{snap.relative_to(ROOT)}#{raw_sha[:16]}"])

    declared = doc.get("class_id")
    declared_set = {declared} if isinstance(declared, str) else set(declared or [])
    check("SEP-02", "schema declares exactly the F2b class id (no composite/foreign class id)",
          [C0], sorted(declared_set), declared_set == {C0}, [f"{TARGET}:class_id"])
    check("SEP-03", "sibling_disjoint_from names the C2 sibling",
          C2, doc.get("sibling_disjoint_from"), doc.get("sibling_disjoint_from") == C2,
          [f"{TARGET}:sibling_disjoint_from"])
    reg = doc.get("extension_predicate", {}).get("frozen_regularity")
    rex = str(doc.get("regularity", {}).get("extension_regularity_exact", ""))
    check("SEP-04", "frozen extension regularity is exactly C0 and not C2/H2_loc/distributional",
          "C0", {"frozen_regularity": reg, "extension_regularity_exact": rex[:120]},
          reg == "C0" and "continuous (C0)" in rex and "distributional" not in rex.lower(),
          [f"{TARGET}:extension_predicate.frozen_regularity", f"{TARGET}:regularity.extension_regularity_exact"])
    concl = doc.get("conclusion", {})
    vis = doc.get("visibility", {})
    iplus = doc.get("i_plus", {})
    check("SEP-05", "conclusion is SCC-typed; visibility and I+ are excluded from the conclusion",
          {"family": "SCC", "visibility.role": "not_in_conclusion", "i_plus.in_conclusion": False},
          {"family": concl.get("family"), "conclusion_type": concl.get("conclusion_type"),
           "visibility.role": vis.get("role"), "i_plus.in_conclusion": iplus.get("in_conclusion"),
           "visibility.visible_singularity_is_wcc": vis.get("visible_singularity_is_wcc")},
          concl.get("family") == "SCC" and vis.get("role") == "not_in_conclusion"
          and iplus.get("in_conclusion") is False,
          [f"{TARGET}:conclusion.family", f"{TARGET}:visibility", f"{TARGET}:i_plus"])
    ledger = json.dumps(doc.get("implication_ledger", {}))
    check("SEP-06", "implication ledger keeps the one-way C0=>C2 entailment and forbids the converse",
          "one-way only", {"ledger_len": len(ledger), "has_converse_forbidden":
                           bool(re.search(r"forbidden|must not|not the converse|converse is (not|forbidden)", ledger, re.I))},
          bool(re.search(r"forbidden|must not|not the converse|converse is (not|forbidden)", ledger, re.I)),
          [f"{TARGET}:implication_ledger"])

    # ---- FIELD: G-FORM required field groups ---------------------------------
    required = ["quantifiers", "topology", "data_class", "genericity", "i_plus", "visibility", "conclusion"]
    missing = [k for k in required if not doc.get(k)]
    order = [q.get("kind") for q in doc.get("quantifiers", {}).get("ordered", [])]
    check("FIELD-01", "G-FORM field groups present and quantifier skeleton ordered forall/exists/forall/not_exists",
          {"required_present": required, "quantifier_order": ["forall", "exists", "forall", "not_exists"]},
          {"missing": missing, "quantifier_order": order}, not missing and order == ["forall", "exists", "forall", "not_exists"],
          [f"{TARGET}#{raw_sha[:16]}"])

    # ---- SEM: semantic baseline control --------------------------------------
    sem = run_auditor(snap, OUT / "semantic_baseline_snapshot.json")
    sem_ok = str(sem.get("verdict", "")).lower() in {"accept", "pass", "accepted", "ok"} and sem.get("_exit") == 0
    check("SEM-01", "semantic baseline auditor accepts the canonical snapshot (conforming-control)",
          "accept/pass", {"verdict": sem.get("verdict"), "exit": sem.get("_exit"),
                          "fired_rules": sem.get("fired_rules") or sem.get("rules_fired")},
          sem_ok, [f"{AUDITOR}#{sha(ROOT / AUDITOR)[:16]}"])

    # ---- MUT: checker non-vacuity --------------------------------------------
    dt = copy.deepcopy(doc)
    dt["regularity"]["extension_regularity_exact"] = "C0 or C2 nondegenerate Lorentzian metric"
    pt = OUT / "mutations" / "m3_composite_regularity_C0_or_C2.yaml"
    pt.write_text(yaml.safe_dump(dt, sort_keys=False, width=110))
    f3 = cs.findings_for_text(pt.read_text(), str(pt))
    check("MUT-03", "MUTATION CONTROL: class-separation flags an asserted composite 'C0 or C2' regularity",
          ">=1 finding", f3[:3], len(f3) >= 1, [f"{pt.relative_to(ROOT)}#{sha(pt)[:16]}"])
    dw = copy.deepcopy(doc)
    dw["conclusion"]["statement_natural_language"] = (
        "The singularity is visible from future null infinity, so the weak cosmic censorship conjecture fails "
        "for this class.")
    pw = OUT / "mutations" / "m4_wcc_conclusion_in_scc_schema.yaml"
    pw.write_text(yaml.safe_dump(dw, sort_keys=False, width=110))
    f4 = cs.findings_for_text(pw.read_text(), str(pw))
    check("MUT-04", "MUTATION CONTROL: class-separation flags a WCC conclusion inside an SCC schema",
          ">=1 finding", f4[:3], len(f4) >= 1, [f"{pw.relative_to(ROOT)}#{sha(pw)[:16]}"])

    # ---- DRIFT: post-run re-measure ------------------------------------------
    post = do_measure()
    report["post_run_measurement"] = post
    drift_now = sha(ROOT / TARGET) != raw_sha
    check("DRIFT-01", "canonical F2b bytes unchanged across the verification window",
          raw_sha, {"post": sha(ROOT / TARGET), "matches": not drift_now}, not drift_now,
          [f"{TARGET}#{raw_sha[:16]}"])
    pins_ok = all(post["files"][k]["pin_matches"] and post["files"][k].get("authoring_matches", True)
                  for k in FROZEN_FILES)
    check("DRIFT-02", "FROZEN pins and authoring tree still agree after the run (no mid-window re-freeze)",
          True, {k: post["files"][k] for k in FROZEN_FILES}, pins_ok, [FROZEN])

    hard = [c["check_id"] for c in checks if not c["ok"] and c["severity"] == "hard"]
    drift_void = "DRIFT-01" in hard or "DRIFT-02" in hard
    gate_fail = any(c["check_id"] in {"GATE-01", "GATE-03", "GATE-04", "MUT-03", "MUT-04"} and not c["ok"] for c in checks)
    sep_fail = any(c["check_id"] in {"SEP-01", "SEP-02", "SEP-03", "SEP-04", "SEP-05", "SEP-06"} and not c["ok"] for c in checks)
    if publication_unsettled is not None:
        hard = list(dict.fromkeys(hard + ["PUBLICATION-BINDING-UNSETTLED"]))
        verdict, score = "inconclusive", 0
    elif drift_void:
        verdict, score = "inconclusive", 0
    elif sep_fail or not sem_ok:
        verdict, score = "revise", 2
    elif gate_fail:
        verdict, score = "revise", 3
    elif hard:
        verdict, score = "revise", 3
    else:
        verdict, score = "accept", 4.5
    report["checks"] = checks
    report["summary"] = {
        "total": len(checks), "pass": sum(1 for c in checks if c["ok"]),
        "fail": sum(1 for c in checks if not c["ok"]), "hard_failures": hard,
        "verdict": verdict, "score": score,
    }
    report["falsifier"] = (
        "Any of: (a) the pinned snapshot's sha256 does not match the bytes the checks were run on; "
        "(b) canonical structural gate rejects the snapshot; (c) class_separation returns a finding on the snapshot; "
        "(d) any independent non-merge assertion above is false; (e) a post-run re-measure shows the canonical bytes or "
        "FROZEN pins moved (drift voids the verdict); (f) mutation controls M1-M4 are not detected (checker vacuity); "
        "(g) a canonical/authoring mirror or FROZEN pin disagreement persists at settle (publication binding unsettled). "
        "Any one falsifies the verdict; a later FROZEN revision re-opens it by construction.")
    (OUT / "report.json").write_text(json.dumps(jsonable(report), indent=2, sort_keys=True))
    print(json.dumps(report["summary"], indent=2))
    print("REPORT", (OUT / "report.json").relative_to(ROOT), sha(OUT / "report.json"))
    return 0 if verdict == "accept" else 3


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W054-F0-REPLAY-01 — independent replay of the frozen F0/G-F0 taxonomy-case corpus
against the current canonical taxonomy bytes.

Bounded task (worker-054). Bound: node F0, gate G-F0, class ids
AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN / AF-SCC-C0-VAC-GEN / AF-WCC-SCALAR-SPH.

Method:
  1. Measure sha256 of the four live inputs and copy byte-identical snapshots.
  2. Run the corpus's OWN checker (artifacts/flash-02/check_taxonomy_cases.py) against the
     snapshot bytes, writing checker_report.json and raw logs. No checker logic is
     re-implemented for the verdict.
  3. Re-measure the live inputs after the run; any move is reported as drift.
  4. Independently recompute, with local code only, the claims the report makes about
     itself: corpus counts/coverage, open-case set, pairwise class disjointness, and the
     taxonomy binding recorded in the corpus meta record vs the current canonical hash.
  5. Write report.json. Exit 0 only when the checker ran, its report is internally
     consistent with the independent recomputation, and no input drifted mid-run.

This claims no theorem, no gate verdict, and no node transition. It is evidence only.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUTS_DIR = HERE / "inputs"
LOGS_DIR = HERE / "logs"
CHECKER_REPORT = HERE / "checker_report.json"
REPORT = HERE / "report.json"

CST = timezone(timedelta(hours=8))
TASK_ID = "W054-F0-REPLAY-01"
NODE_ID = "F0"
GATE = "G-F0"
CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

INPUTS = {
    "taxonomy": "research_map/formulation_taxonomy.yaml",
    "cases": "schemas/taxonomy_cases.jsonl",
    "catalog": "artifacts/flash-02/leak_rule_catalog.json",
    "checker": "artifacts/flash-02/check_taxonomy_cases.py",
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_cases(path: Path):
    meta, cases = None, []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("record_type") == "meta":
            meta = rec
        elif rec.get("record_type") == "case":
            cases.append(rec)
    return meta, cases


def main() -> int:
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    started = now()

    # ---- 1. snapshot inputs, measuring before/after hashes
    pre, post, snap = {}, {}, {}
    for key, rel in INPUTS.items():
        live = ROOT / rel
        pre[key] = sha256_file(live)
        if pre[key] is None:
            raise SystemExit(f"missing input: {rel}")
        dst = INPUTS_DIR / live.name
        dst.write_bytes(live.read_bytes())
        snap[key] = {"path": str(dst.relative_to(ROOT)), "sha256": sha256_file(dst)}
        if snap[key]["sha256"] != pre[key]:
            raise SystemExit(f"snapshot copy mismatch for {rel}")

    # corpus meta binding, read from the frozen corpus itself
    meta, cases = load_cases(ROOT / INPUTS["cases"])
    bound_sha = ((meta or {}).get("taxonomy_ref") or {}).get("sha256")

    # ---- 2. run the corpus's own checker against the snapshot bytes
    cmd = [
        sys.executable,
        str(ROOT / snap["checker"]["path"]),
        "--taxonomy", str(ROOT / snap["taxonomy"]["path"]),
        "--cases", str(ROOT / snap["cases"]["path"]),
        "--catalog", str(ROOT / snap["catalog"]["path"]),
        "--report", str(CHECKER_REPORT),
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    elapsed = round(time.time() - t0, 2)
    (LOGS_DIR / "checker.stdout.txt").write_text(proc.stdout)
    (LOGS_DIR / "checker.stderr.txt").write_text(proc.stderr)
    (LOGS_DIR / "checker.command.txt").write_text(" ".join(cmd) + "\n")

    # ---- 3. drift check
    for key, rel in INPUTS.items():
        post[key] = sha256_file(ROOT / rel)
    drift = {k: {"pre": pre[k], "post": post[k], "moved": pre[k] != post[k]} for k in INPUTS}

    # ---- 4. parse checker report and independently recompute its self-claims
    raw = json.loads(CHECKER_REPORT.read_text()) if CHECKER_REPORT.is_file() else {}

    pol = {"positive": 0, "negative": 0}
    cov = {"positive": {}, "negative": {}}
    filed_extra = {}
    open_ids, semantic_ids = [], []
    for c in cases:
        p = c.get("polarity")
        pol[p] = pol.get(p, 0) + 1
        # positives are counted by the class they must resolve to; negatives by the class
        # they were filed under (as_filed_class_id), which is the checker's own basis.
        cls = c.get("class_id") if p == "positive" else c.get("as_filed_class_id")
        if cls:
            cov[p][cls] = cov[p].get(cls, 0) + 1
            if cls not in CLASS_IDS:
                filed_extra[cls] = filed_extra.get(cls, 0) + 1
        if c.get("open") is True:
            open_ids.append(c["case_id"])
        if c.get("leak_kind") == "semantic":
            semantic_ids.append(c["case_id"])

    tax = yaml.safe_load((ROOT / snap["taxonomy"]["path"]).read_text())
    classes = tax.get("classes", {})
    pairs = []
    ids = list(classes)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            ax, bx = classes[a].get("axes", {}), classes[b].get("axes", {})
            diff = sorted(k for k in set(ax) | set(bx) if ax.get(k) != bx.get(k))
            pairs.append({"pair": [a, b], "differing_axes": diff, "ok": bool(diff)})

    r_counts = raw.get("counts", {})
    r_cov = raw.get("coverage", {})
    r_open = raw.get("open_cases", [])
    r_pairs = (raw.get("disjointness") or {}).get("pairs", [])
    r_pair_map = {tuple(sorted(p["pair"])): sorted(p.get("differing_axes", [])) for p in r_pairs}

    def cov_match(pol_kind: str) -> bool:
        got = {k: int(v) for k, v in (r_cov.get(pol_kind) or {}).items()}
        mine = {k: cov[pol_kind].get(k, 0) for k in got}
        return mine == got

    checks = []

    def check(cid, desc, ok, detail):
        checks.append({"id": cid, "check": desc, "pass": bool(ok), "detail": detail})

    check("C1-checker-exit", "corpus checker exits 0", proc.returncode == 0,
          {"exit_code": proc.returncode, "elapsed_s": elapsed})
    check("C2-verdict", "checker report verdict == PASS", raw.get("verdict") == "PASS",
          {"verdict": raw.get("verdict"), "errors": raw.get("errors", [])[:8]})
    check("C3-taxonomy-pin", "report taxonomy sha equals snapshot and live pre-run sha",
          raw.get("taxonomy", {}).get("sha256") == snap["taxonomy"]["sha256"] == pre["taxonomy"],
          {"report": raw.get("taxonomy", {}).get("sha256"), "snapshot": snap["taxonomy"]["sha256"],
           "live_pre": pre["taxonomy"]})
    check("C4-cases-pin", "report cases sha equals snapshot sha",
          raw.get("cases", {}).get("sha256") == snap["cases"]["sha256"],
          {"report": raw.get("cases", {}).get("sha256"), "snapshot": snap["cases"]["sha256"]})
    check("C5-catalog-pin", "report catalog sha equals snapshot sha",
          raw.get("catalog", {}).get("sha256") == snap["catalog"]["sha256"],
          {"report": raw.get("catalog", {}).get("sha256"), "snapshot": snap["catalog"]["sha256"]})
    check("C6-controls", "10/10 mutation controls detected",
          raw.get("controls_all_detected") is True and len(raw.get("controls", [])) == 10,
          {"controls_all_detected": raw.get("controls_all_detected"),
           "n_controls": len(raw.get("controls", []))})
    check("C7-counts", "positive/negative counts match independent recount",
          int(r_counts.get("positive", -1)) == pol["positive"]
          and int(r_counts.get("negative", -1)) == pol["negative"],
          {"report": r_counts, "recount": pol})
    check("C8-coverage", "per-class coverage matches independent recount (both polarities)",
          cov_match("positive") and cov_match("negative"),
          {"report": r_cov, "recount": cov})
    check("C9-open-set", "open-case set matches independent recount, sorted",
          sorted(r_open) == sorted(open_ids),
          {"report": sorted(r_open), "recount": sorted(open_ids)})
    check("C10-disjointness", "6/6 class pairs disjoint and differing-axis sets match recomputation",
          len(r_pairs) == 6 and (raw.get("disjointness") or {}).get("ok") is True
          and all(r_pair_map.get(tuple(sorted(p["pair"]))) == p["differing_axes"] for p in pairs),
          {"report_pairs": len(r_pairs), "recomputed_pairs": len(pairs),
           "mismatches": [p["pair"] for p in pairs
                          if r_pair_map.get(tuple(sorted(p["pair"]))) != p["differing_axes"]]})
    check("C11-no-drift", "no live input moved during the run", not any(v["moved"] for v in drift.values()),
          drift)
    check("C12-class-ids", "taxonomy carries exactly the four frozen class ids",
          sorted(classes) == sorted(CLASS_IDS), {"classes": sorted(classes)})

    all_pass = all(c["pass"] for c in checks)
    checker_ok = proc.returncode == 0 and raw.get("verdict") == "PASS"
    bindings_match = bound_sha == pre["taxonomy"]

    report = {
        "report_version": "1.0",
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "gate": GATE,
        "class_id": CLASS_IDS[0],
        "class_ids": CLASS_IDS,
        "actor": "worker-054",
        "created_at": started,
        "finished_at": now(),
        "claims_theorem_status": False,
        "controller_authority": "worker report only; cannot set node status, validation_status=passed, or a gate verdict",
        "bound_question": (
            "The frozen 36-case F0/G-F0 class-leakage corpus declares binding_status "
            "bound_taxonomy_sha_66bf917bd368. The canonical taxonomy has since moved. Does the corpus "
            "still resolve at the current canonical bytes, and does its own checker report stay "
            "internally consistent with an independent recomputation?"
        ),
        "outcome": {
            "checker_verdict": raw.get("verdict"),
            "checker_exit_code": proc.returncode,
            "all_consistency_checks_pass": all_pass,
            "n_checks": len(checks),
            "n_checks_failed": sum(1 for c in checks if not c["pass"]),
            "corpus_resolves_at_current_bytes": bool(checker_ok and all_pass),
            "binding_replay": "out-of-binding replay" if not bindings_match else "in-binding replay",
        },
        "binding": {
            "corpus_bound_taxonomy_sha256": bound_sha,
            "corpus_bound_revision": ((meta or {}).get("taxonomy_ref") or {}).get("revision"),
            "current_taxonomy_sha256": pre["taxonomy"],
            "current_taxonomy_revision": tax.get("revision"),
            "current_taxonomy_status": tax.get("status"),
            "bindings_match": bindings_match,
            "canonical_observed_motion": (
                "The canonical taxonomy is being republished while workers run: this worker measured "
                "sha256 0fcc6a1928fd40b02529f59c8a23095191001f84858346bf83d00818c29d7b31 (revision 3) "
                "at ~00:18 local and the pinned snapshot hash (revision 4) at run start. Only the "
                "snapshot hash below is machine-pinned by this report; the earlier observation is "
                "provenance, not a verified pin."
            ),
            "note": (
                "An out-of-binding replay is the corpus's own next-falsifier #1 "
                "(artifacts/flash-02/README.md): any case whose axis vector no longer resolves "
                "uniquely falsifies the old binding. This report records what happened at the "
                "new bytes; only the formulation lead can re-pin the corpus."
            ),
        },
        "command": " ".join(cmd),
        "inputs": {
            k: {"path": INPUTS[k], "live_pre_sha256": pre[k], "snapshot_sha256": snap[k]["sha256"],
                "live_post_sha256": post[k], "moved": drift[k]["moved"]}
            for k in INPUTS
        },
        "raw_checker_report": str(CHECKER_REPORT.relative_to(ROOT)),
        "raw_checker_report_sha256": sha256_file(CHECKER_REPORT),
        "independent_recomputation": {
            "counts": pol,
            "coverage": cov,
            "coverage_note": (
                "negatives are recounted by as_filed_class_id; the checker's coverage table lists "
                "only the four frozen classes, so 3 negative cases filed as COMPOSITE_* are outside "
                "its coverage table by construction: " + json.dumps(filed_extra)
            ),
            "open_cases": sorted(open_ids),
            "semantic_review_cases": sorted(semantic_ids),
            "class_pairs": pairs,
        },
        "checks": checks,
        "falsifier": (
            "Re-run this harness in an unchanged tree. The report is falsified if (a) the checker "
            "exits non-zero or returns a non-PASS verdict at the same re-measured taxonomy sha256, "
            "(b) any live input hash differs from the pins above, (c) the independent recount of "
            "counts/coverage/open-set/disjointness disagrees with the checker report, or (d) the "
            "corpus-wide resolution result changes while every pinned hash is unchanged."
        ),
        "limitations": [
            "The 36 fixtures are worker-authored synthetic strings; passing them is shape/separation "
            "evidence, not mathematical correctness, non-vacuity, or truth.",
            "The checker is the corpus author's tool; this replay re-runs it byte-identically and "
            "cross-checks its self-claims, but does not independently re-implement its leak rules.",
            "9 cases remain open (new class / split required) and are the formulation lead's "
            "adjudication, not a worker's.",
            "No gate verdict, node status, or artifact validation_status is set here.",
        ],
        "reproduction": f"python3 {Path(__file__).relative_to(ROOT)}",
    }
    REPORT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")

    print(f"{TASK_ID}: checker exit={proc.returncode} verdict={raw.get('verdict')} "
          f"checks={sum(1 for c in checks if c['pass'])}/{len(checks)} "
          f"binding={'match' if bindings_match else 'drift'} "
          f"current_taxonomy={pre['taxonomy'][:12]}")
    for c in checks:
        if not c["pass"]:
            print(f"  FAIL {c['id']}: {c['check']} :: {json.dumps(c['detail'])[:300]}")
    return 0 if (checker_ok and all_pass) else 1


if __name__ == "__main__":
    sys.exit(main())

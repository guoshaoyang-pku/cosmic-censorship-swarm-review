#!/usr/bin/env python3
"""W093-CF16-CALIBRATION-01 independent verifier.

Question: can the class-separation checker be calibrated so the CF-16 hard
audit failure (a metalinguistic *case label* in claims[36].statement read as a
C0/C2 merge assertion) clears, WITHOUT losing any true positive on the standing
regression corpora?

This harness is read-only with respect to the repository's canonical files: it
imports a pinned copy of research_map/class_separation.py and a calibrated copy
kept under artifacts/worker-093/cf16_calibration/, and it applies the proposed
patch only inside a private temporary directory.

Exit semantics (fail-closed):
  0 = all checks pass
  1 = at least one check failed
  2 = missing target or hash drift against a pin
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent

PIN_CANONICAL_SHA = "c266dbceca87fb996bd76a774145ef511cbf2aae190d9f423167d3200783a920"
PIN_CLAIMS36_STATEMENT_SHA = "026cfccbd8f1c20ab7efa67203a61c6d23ffeb56080abb0d3d7bcc5e3829787d"
PIN_W07_EXPECT = {"tp": 17, "fn": 0, "tn": 10, "fp": 0}
LIVE_CANONICAL = REPO / "research_map/class_separation.py"
CANONICAL = HERE / "pinned/class_separation.c266dbce.py"
CALIBRATED = HERE / "calibrated_class_separation.py"
PATCH = HERE / "proposed_patch.diff"
FIXTURES = HERE / "metalinguistic_fixtures.jsonl"
CLAIMS36 = HERE / "pinned/claims36_snapshot.json"
W07_CORPUS = REPO / "artifacts/worker-07/class_separation_falsification"
LIVE_MAP = REPO / "research_map/research_map.json"
W027_PATCH = REPO / "artifacts/worker-027/classsep_token_binding/proposed_patch.diff"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def hunk_ranges(patch_text: str):
    out = []
    for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", patch_text, re.M):
        a, b = int(m.group(1)), int(m.group(2) or 1)
        out.append((a, a + b - 1))
    return out


def changed_old_lines(patch_text: str):
    """Old-file line numbers carrying '-' lines (the lines a patch rewrites)."""
    out = set()
    old_no = None
    for ln in patch_text.splitlines():
        m = re.match(r"^@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@", ln)
        if m:
            old_no = int(m.group(1))
            continue
        if old_no is None or ln.startswith(("---", "+++", "\\")):
            continue
        if ln.startswith("-"):
            out.add(old_no); old_no += 1
        elif ln.startswith("+"):
            pass
        elif ln.startswith(" "):
            old_no += 1
    return out


def w07_score(mod) -> dict:
    res = json.loads((W07_CORPUS / "results.json").read_text())
    tp = fn = tn = fp = 0
    per_fixture = {}
    for fx in res["fixtures"]:
        p = REPO / fx["fixture_path"]
        if not p.exists():
            per_fixture[fx["id"]] = "MISSING"
            continue
        m = json.loads(p.read_text())
        detected = mod.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (REPO / art).is_file():
                    detected += mod.findings_for_text(
                        (REPO / art).read_text(errors="replace"), f"artifact {art}")
        got, truth = bool(detected), bool(fx["is_class_merge"])
        if truth and got:
            tp += 1; cls = "TP"
        elif truth and not got:
            fn += 1; cls = "FN-MISSED"
        elif not truth and got:
            fp += 1; cls = "FP-SPURIOUS"
        else:
            tn += 1; cls = "TN"
        per_fixture[fx["id"]] = cls
    return {"tp": tp, "fn": fn, "tn": tn, "fp": fp, "per_fixture": per_fixture,
            "n": len(res["fixtures"])}


def main() -> int:
    checks = []
    observations = {}
    drift = []

    for p in (CANONICAL, CALIBRATED, PATCH, FIXTURES, CLAIMS36, W07_CORPUS / "results.json"):
        if not p.exists():
            print(f"MISSING TARGET: {p}", file=sys.stderr)
            return 2

    can_sha = sha256_file(CANONICAL)
    cal_sha = sha256_file(CALIBRATED)
    patch_sha = sha256_file(PATCH)
    live_sha = sha256_file(LIVE_CANONICAL) if LIVE_CANONICAL.exists() else None
    map_sha = sha256_file(LIVE_MAP) if LIVE_MAP.exists() else None
    snap = json.loads(CLAIMS36.read_text())
    st = snap["statement"]
    if sha256_text(st) != PIN_CLAIMS36_STATEMENT_SHA:
        print("HASH DRIFT: claims[36] snapshot statement", file=sys.stderr)
        return 2
    if can_sha != PIN_CANONICAL_SHA:
        print("HASH DRIFT: pinned canonical module", file=sys.stderr)
        return 2
    if live_sha != PIN_CANONICAL_SHA:
        drift.append({"item": "research_map/class_separation.py", "pinned": PIN_CANONICAL_SHA,
                      "measured": live_sha,
                      "note": "live canonical moved after the pin; checks use the pinned copy"})

    can = load_module("cf16_canonical", CANONICAL)
    cal = load_module("cf16_calibrated", CALIBRATED)

    # ---------------- B1: reproduce the CF-16 hard failure, then clear it ----
    can_hits = can.findings_for_text(st, "claims[36].statement")
    cal_hits = cal.findings_for_text(st, "claims[36].statement")
    b1_ok = (len(can_hits) == 1 and "asserted as one class" in can_hits[0] and len(cal_hits) == 0)
    checks.append({"id": "B1-repro-and-clear", "pass": b1_ok,
                   "detail": {"canonical_findings": can_hits, "calibrated_findings": cal_hits}})

    # ---------------- B2: worker-07 27-fixture corpus parity -----------------
    cw = w07_score(can)
    kw = w07_score(cal)
    parity = {k: cw[k] for k in ("tp", "fn", "tn", "fp")} == PIN_W07_EXPECT and \
             {k: kw[k] for k in ("tp", "fn", "tn", "fp")} == PIN_W07_EXPECT
    same_class = cw["per_fixture"] == kw["per_fixture"]
    checks.append({"id": "B2-worker07-corpus-parity", "pass": bool(parity and same_class),
                   "detail": {"canonical": {k: cw[k] for k in ("tp", "fn", "tn", "fp")},
                              "calibrated": {k: kw[k] for k in ("tp", "fn", "tn", "fp")},
                              "expected": PIN_W07_EXPECT,
                              "per_fixture_identical": same_class,
                              "changed_fixtures": [k for k in cw["per_fixture"]
                                                   if cw["per_fixture"][k] != kw["per_fixture"][k]]}})

    # ---------------- B3: labeled metalinguistic fixture suite ---------------
    rows = [json.loads(l) for l in FIXTURES.read_text().splitlines() if l.strip()]
    fx_fail = []
    for r in rows:
        g_can = bool(can.findings_for_text(r["text"], r["fixture_id"]))
        g_cal = bool(cal.findings_for_text(r["text"], r["fixture_id"]))
        if g_can != r["expect_canonical_flagged"] or g_cal != r["expect_calibrated_flagged"]:
            fx_fail.append({"fixture_id": r["fixture_id"], "kind": r["kind"],
                            "canonical": g_can, "calibrated": g_cal,
                            "expected": [r["expect_canonical_flagged"], r["expect_calibrated_flagged"]]})
    kinds = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    checks.append({"id": "B3-labeled-fixtures", "pass": not fx_fail,
                   "detail": {"n": len(rows), "kinds": kinds, "failures": fx_fail}})

    # ---------------- B4: token extraction inertness -------------------------
    probes = [st, "AF-WCC-VAC-REG", "AF-SCC-REG-GEN", "AF-WCC-VAC-GEN", "AF-WCC-SCALAR-SPH",
              "AF-SCC-C0-CH-VAC-GEN", "AF-WCC-VAC-GEN-SET"]
    probes += [r["text"] for r in rows]
    tok_ok = all(can._class_tokens(p) == cal._class_tokens(p) for p in probes)
    checks.append({"id": "B4-token-extraction-inert", "pass": tok_ok,
                   "detail": {"probes": len(probes),
                              "canonical_5group": can._class_tokens("AF-SCC-C0-CH-VAC-GEN"),
                              "calibrated_5group": cal._class_tokens("AF-SCC-C0-CH-VAC-GEN")}})

    # ---------------- B5: live-map delta is exactly the CF-16 finding --------
    live_map_sha_at_read = sha256_file(LIVE_MAP)
    m = json.loads(LIVE_MAP.read_text())
    can_map = set(can.findings_for_map(m))
    cal_map = set(cal.findings_for_map(m))
    removed = can_map - cal_map
    added = cal_map - can_map
    claims36_finding = [f for f in removed if "claims[" in f and "asserted as one class" in f]
    already_rephrased = not any("claims[" in f and "asserted as one class" in f for f in can_map)
    b5_ok = (not added) and (len(removed) <= 1) and (bool(claims36_finding) or already_rephrased)
    checks.append({"id": "B5-live-map-delta", "pass": bool(b5_ok),
                   "detail": {"map_sha256_at_read": live_map_sha_at_read,
                              "canonical_findings": sorted(can_map),
                              "calibrated_findings": sorted(cal_map),
                              "removed": sorted(removed), "added": sorted(added),
                              "claims36_already_rephrased_in_live_map": already_rephrased}})

    # ---------------- B6: patch integrity + disjointness from worker-027 -----
    b6 = {"dry_run": None, "applied_reproduces_calibrated": None,
          "hunks": hunk_ranges(PATCH.read_text())}
    tmp = Path(tempfile.mkdtemp(prefix="cf16_patch_"))
    try:
        (tmp / "research_map").mkdir(parents=True)
        shutil.copy2(CANONICAL, tmp / "research_map/class_separation.py")
        with open(PATCH, "rb") as fh:
            dry = subprocess.run(["patch", "-p1", "--dry-run"], cwd=tmp, stdin=fh,
                                 capture_output=True, text=True)
        b6["dry_run"] = {"returncode": dry.returncode, "stdout": dry.stdout.strip(),
                         "stderr": dry.stderr.strip()}
        with open(PATCH, "rb") as fh:
            subprocess.run(["patch", "-p1"], cwd=tmp, stdin=fh, capture_output=True, text=True)
        b6["applied_reproduces_calibrated"] = sha256_file(tmp / "research_map/class_separation.py") == cal_sha
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    disjoint = None
    combined = None
    if W027_PATCH.exists():
        w27_text = W027_PATCH.read_text()
        b6["worker027_hunks"] = hunk_ranges(w27_text)
        mine_changed = changed_old_lines(PATCH.read_text())
        theirs_changed = changed_old_lines(w27_text)
        disjoint = not (mine_changed & theirs_changed)
        b6["changed_old_lines"] = {"worker093": sorted(mine_changed), "worker027": sorted(theirs_changed)}
        b6["disjoint_from_worker027"] = disjoint
        # compose both patches on the pinned bytes in a private temp dir
        tmp2 = Path(tempfile.mkdtemp(prefix="cf16_compose_"))
        try:
            (tmp2 / "research_map").mkdir(parents=True)
            shutil.copy2(CANONICAL, tmp2 / "research_map/class_separation.py")
            r1 = subprocess.run(["patch", "-p1"], cwd=tmp2, input=w27_text,
                                capture_output=True, text=True)
            r2 = subprocess.run(["patch", "-p1"], cwd=tmp2, input=PATCH.read_text(),
                                capture_output=True, text=True)
            final = (tmp2 / "research_map/class_separation.py").read_text()
            w27_new = 'r"AF-(?:[A-Z0-9]+-){2,}[A-Z0-9]+"'
            w27_old = 'r"AF-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+"'
            expect = CALIBRATED.read_text().replace(w27_old, w27_new)
            combined = (r1.returncode == 0 and r2.returncode == 0 and final == expect)
            b6["compose"] = {"worker027_returncode": r1.returncode,
                             "worker093_after_worker027_returncode": r2.returncode,
                             "equals_calibrated_plus_token_patch": final == expect,
                             "worker027_stderr": r1.stderr.strip(), "worker093_stderr": r2.stderr.strip()}
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)
    b6_ok = (b6["dry_run"]["returncode"] == 0 and b6["applied_reproduces_calibrated"]
             and disjoint is not False and combined is not False)
    checks.append({"id": "B6-patch-integrity", "pass": bool(b6_ok), "detail": b6})

    verdict = "PASS" if all(c["pass"] for c in checks) else "FAIL"
    report = {
        "schema": "w093/cf16-calibration/v1",
        "task_id": "W093-CF16-CALIBRATION-01",
        "worker": "worker-093",
        "role": "bounded execution worker",
        "created_at": now(),
        "node_id": "A1",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate_scope": ["G-AUDIT", "G-FORM"],
        "question": ("Does a minimal case-label calibration of research_map/class_separation.py clear the "
                     "CF-16 CLASSSEP hard failure on claims[36].statement while leaving the standing "
                     "regression corpora and all labeled positives unchanged?"),
        "inputs": {
            "research_map/class_separation.py": {"sha256": can_sha, "pinned_copy": str(CANONICAL.relative_to(REPO))},
            "live research_map/class_separation.py": {"sha256": live_sha, "matches_pin": live_sha == PIN_CANONICAL_SHA},
            "artifacts/worker-093/cf16_calibration/calibrated_class_separation.py": {"sha256": cal_sha},
            "artifacts/worker-093/cf16_calibration/proposed_patch.diff": {"sha256": patch_sha},
            "pinned/claims36_snapshot.json": {"statement_sha256": PIN_CLAIMS36_STATEMENT_SHA,
                                              "claim_event_id": snap.get("event_id")},
            "research_map/research_map.json": {"sha256_at_read": live_map_sha_at_read,
                                               "sha256_at_snapshot": snap.get("_map_sha256_at_snapshot")},
            "artifacts/worker-07/class_separation_falsification/results.json":
                {"sha256": sha256_file(W07_CORPUS / "results.json")},
        },
        "checks": checks,
        "drift": drift,
        "observations": observations,
        "result": {"verdict": verdict,
                   "canonical_claims36_findings": len(can_hits),
                   "calibrated_claims36_findings": len(cal_hits),
                   "worker07_canonical": {k: cw[k] for k in ("tp", "fn", "tn", "fp")},
                   "worker07_calibrated": {k: kw[k] for k in ("tp", "fn", "tn", "fp")}},
        "falsifier": ("Re-run this harness at the pinned checker sha256 c266dbce. The calibration is FALSIFIED if "
                      "(a) the calibrated module still emits a CLASSSEP finding on the pinned claims[36].statement; "
                      "or (b) the calibrated module clears any labeled positive fixture (M-P01..M-P06) or any "
                      "missing/predicated case-label control (M-P03/M-P04); or (c) the worker-07 corpus score changes "
                      "from 17/0/10/0 in any cell or any fixture changes classification; or (d) the calibrated module "
                      "changes _class_tokens output on any probe; or (e) on a live map read in the same run the "
                      "calibrated scan removes any finding other than the claims[36] one or adds a new one; or "
                      "(f) proposed_patch.diff does not apply cleanly to the pinned canonical bytes or does not "
                      "reproduce the calibrated module."),
        "non_claims": [
            "no canonical file was modified; the patch is a proposal only",
            "no gate verdict, no done status, no validation_status=passed",
            "this does not clear the evidence hard failure itself; the controller/audit lead must apply the patch or accept the rephrase",
            "the calibration addresses case-label mentions only; other metalinguistic false positives (e.g. M-R01) are deliberately left flagged",
        ],
        "reproduce": "python3 artifacts/worker-093/cf16_calibration/verify_calibration.py",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(f"checks: " + ", ".join(f"{c['id']}={'PASS' if c['pass'] else 'FAIL'}" for c in checks))
    print(f"VERDICT: {verdict}  (canonical claims36 findings {len(can_hits)}, calibrated {len(cal_hits)}; "
          f"worker-07 canonical {cw['tp']}/{cw['fn']}/{cw['tn']}/{cw['fp']}, calibrated {kw['tp']}/{kw['fn']}/{kw['tn']}/{kw['fp']})")
    if drift:
        print("DRIFT:", json.dumps(drift))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

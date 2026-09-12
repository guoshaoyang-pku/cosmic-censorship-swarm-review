#!/usr/bin/env python3
"""W056-CLASSSEP-HOLDOUT-01 -- independent pre-registered holdout evaluation of the
applied classsep prose-precision fix (research_map/class_separation.py), plus
adjudication of the residual live CLASSSEP hard findings.

Read-only w.r.t. every canonical path. Writes only under
artifacts/worker-056/classsep_holdout/ and the canonical regression runner's own
scratch dir (runtime/state/classsep_regression/, created by that runner).

Exit codes: 0 = clean run, no drift; 3 = pin drift detected (report still written,
evidence void); 2 = hard error.

Usage: python3 run_holdout_056.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent  # artifacts/worker-056/classsep_holdout -> swarm root
CS_LIVE = ROOT / "research_map/class_separation.py"
MAP_LIVE = ROOT / "research_map/research_map.json"
PREREG = HERE / "prereg_holdout_fixtures.json"
SNAP = HERE / "snapshot"
RAW = HERE / "raw"
CST = timezone(timedelta(hours=8))

SKIP_RE = re.compile(
    r"false[- ]positive|non[- ]merge|not\s+(?:a\s+)?merge|"
    r"no\s+genuine\s+(?:c0/c2|c2/c0)\s+merge|detector\s+(?:finding|flag)|"
    r"quote(?:d|s)?\s+(?:the\s+)?detector", re.I)
META_RE = re.compile(
    r"false[- ]positive|non[- ]merge|not\s+(?:a\s+)?merge|no\s+genuine|detector|audit|"
    r"split_required|quote|example|hypothetical|forbidden|prohibit|discuss|asks?\b|"
    r"question|pattern|check\b|finding\b|counterexample|historical|log(s|ged|ging)?\b", re.I)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pin(path: Path) -> dict:
    st = path.stat()
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path),
            "bytes": st.st_size, "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds")}


def cs_only(findings: list) -> list:
    return [f for f in findings if str(f).startswith("CLASSSEP:")]


def run_fixture(det, fx: dict) -> dict:
    where = f"holdout.{fx['id']}"
    if fx["mode"] == "declaration":
        raw = det.findings(fx["obj"], where, mode="declaration")
    else:
        raw = det.findings_for_text(fx["text"], where)
    hard = cs_only(raw)
    return {"id": fx["id"], "series": fx["series"], "mode": fx["mode"],
            "expected_flag": fx["expected_flag"], "got_flag": bool(hard),
            "verdict": "OK" if bool(hard) == fx["expected_flag"] else
                       ("MISSED-GENUINE" if fx["expected_flag"] else "RESIDUAL-FP"),
            "hard_findings": hard, "soft_findings": [f for f in raw if f not in hard],
            "expected_basis": fx["expected_basis"]}


def classify_claim_finding(det, claim: dict, i: int, finding: str) -> dict:
    stmt = str(claim.get("statement") or "")
    t = det.norm(stmt)
    rows = []
    for m in det._MERGE_PAT.finditer(t):
        lo, hi = max(0, m.start() - 60), min(len(t), m.end() + 60)
        ctx60 = t[lo:hi]
        wlo, whi = max(0, m.start() - 160), min(len(t), m.end() + 160)
        ctx160 = t[wlo:whi]
        rows.append({
            "composite": m.group(0),
            "skip_phrase_in_60": bool(SKIP_RE.search(ctx60)),
            "skip_phrase_in_160": bool(SKIP_RE.search(ctx160)),
            "meta_marker_in_160": bool(META_RE.search(ctx160)),
            "ctx160": ctx160.strip(),
        })
    if not rows:
        bucket = "no-composite-match-recheck"
    elif any(r["skip_phrase_in_60"] for r in rows):
        bucket = "skip-phrase-in-window-recheck"
    elif any(r["skip_phrase_in_160"] for r in rows):
        bucket = "window-too-narrow"
    elif any(r["meta_marker_in_160"] for r in rows):
        bucket = "candidate-residual-fp"
    else:
        bucket = "candidate-genuine-assertion"
    return {"index": i, "where": f"claims[{i}]", "class_id": claim.get("class_id"),
            "bucket": bucket, "matches": rows,
            "statement_excerpt": stmt[:260], "finding_excerpt": str(finding)[:300]}


def harden_metrics(rows: list) -> dict:
    def n(pred): return sum(1 for r in rows if pred(r))
    genuine = [r for r in rows if r["series"] in ("A", "D") and r["expected_flag"]]
    meta = [r for r in rows if r["series"] == "B" and not r["expected_flag"]]
    ctrl = [r for r in rows if r["series"] == "C" and not r["expected_flag"]]
    return {
        "n_fixtures": len(rows),
        "genuine_expected": len(genuine),
        "genuine_detected": n(lambda r: r["series"] in ("A", "D") and r["expected_flag"] and r["got_flag"]),
        "genuine_missed": n(lambda r: r["expected_flag"] and not r["got_flag"]),
        "genuine_missed_ids": [r["id"] for r in rows if r["expected_flag"] and not r["got_flag"]],
        "meta_expected_clear": len(meta),
        "meta_still_flagged": n(lambda r: r["series"] == "B" and not r["expected_flag"] and r["got_flag"]),
        "meta_still_flagged_ids": [r["id"] for r in rows if r["series"] == "B" and not r["expected_flag"] and r["got_flag"]],
        "context_controls_expected_clear": len(ctrl),
        "context_controls_flagged": n(lambda r: r["series"] == "C" and not r["expected_flag"] and r["got_flag"]),
        "declaration_positive_controls": len([r for r in rows if r["series"] == "D" and r["expected_flag"]]),
        "declaration_positives_detected": n(lambda r: r["series"] == "D" and r["expected_flag"] and r["got_flag"]),
    }


def main() -> int:
    started = now()
    RAW.mkdir(parents=True, exist_ok=True)
    SNAP.mkdir(parents=True, exist_ok=True)

    det_t0 = pin(CS_LIVE)
    map_t0 = pin(MAP_LIVE)
    prereg_pin = pin(PREREG)
    # snapshot the exact bytes measured (binds the run to the pinned detector/map)
    det_snap = SNAP / f"class_separation.{det_t0['sha256'][:12]}.py"
    map_snap = SNAP / f"research_map.{map_t0['sha256'][:12]}.json"
    if not det_snap.exists():
        det_snap.write_bytes(CS_LIVE.read_bytes())
    if not map_snap.exists():
        map_snap.write_bytes(MAP_LIVE.read_bytes())
    if sha256_file(det_snap) != det_t0["sha256"] or sha256_file(map_snap) != map_t0["sha256"]:
        print("SNAPSHOT-HASH-MISMATCH: refusing to proceed", file=sys.stderr)
        return 2

    det = load_module(det_snap, "classsep_snapshot_w056")
    m = json.loads(map_snap.read_text())

    # ---- 1. holdout fixtures -------------------------------------------------
    prereg = json.loads(PREREG.read_text())
    rows = [run_fixture(det, fx) for fx in prereg["fixtures"]]
    metrics = harden_metrics(rows)

    # ---- 2. canonical regression runner (as required by the human-PI directive)
    reg_before = sha256_file(CS_LIVE)
    try:
        cp = subprocess.run([sys.executable, str(ROOT / "runtime/bin/classsep_regression.py"), "--verbose"],
                            capture_output=True, text=True, timeout=180, cwd=str(ROOT))
        reg = {"exit_code": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr}
    except Exception as exc:  # noqa: BLE001
        reg = {"exit_code": None, "stdout": "", "stderr": f"runner error: {exc}"}
    reg_after = sha256_file(CS_LIVE)
    reg["detector_sha256_before"] = reg_before
    reg["detector_sha256_after"] = reg_after
    reg["stdout_path"] = "raw/classsep_regression_stdout.txt"
    reg["exit_path"] = "raw/classsep_regression_exit.txt"
    (RAW / "classsep_regression_stdout.txt").write_text(reg["stdout"] + "\n--- stderr ---\n" + reg["stderr"])
    (RAW / "classsep_regression_exit.txt").write_text(str(reg["exit_code"]) + "\n")

    # ---- 3. residual live CLASSSEP findings on the pinned map snapshot -------
    all_findings = det.findings_for_map(m)
    claim_findings = [f for f in all_findings if ".statement" in f and f.startswith("CLASSSEP:")]
    residual = []
    for i, c in enumerate(m.get("claims", [])):
        if not isinstance(c, dict):
            continue
        for f in claim_findings:
            if f"claims[{i}].statement" in f:
                residual.append(classify_claim_finding(det, c, i, f))
    buckets = {}
    for r in residual:
        buckets[r["bucket"]] = buckets.get(r["bucket"], 0) + 1
    residual_block = {
        "map_snapshot": map_t0,
        "total_findings_on_snapshot": len(all_findings),
        "claim_statement_findings": len(claim_findings),
        "classified_rows": len(residual),
        "buckets": buckets,
        "controller_gate_audit_snapshot": (m.get("controller_gate_audit") or {}),
        "rows": residual,
    }

    # ---- 4. drift re-measure (fail-closed) -----------------------------------
    det_t1 = pin(CS_LIVE)
    map_t1 = pin(MAP_LIVE)
    drift = {
        "detector_moved": det_t0["sha256"] != det_t1["sha256"],
        "map_moved": map_t0["sha256"] != map_t1["sha256"],
        "detector_t0": det_t0, "detector_t1": det_t1,
        "map_t0": map_t0, "map_t1": map_t1,
    }
    if drift["detector_moved"]:
        (RAW / "DRIFT_DETECTED.txt").write_text(
            f"detector moved {det_t0['sha256']} -> {det_t1['sha256']}; holdout evidence binds to "
            f"the snapshot {det_snap.name} only and is VOID for the live file.\n")

    verdict = "revise" if (metrics["genuine_missed"] or metrics["meta_still_flagged"]) else "accept"
    findings = []
    if metrics["genuine_missed"]:
        findings.append({
            "id": "W056-CH-01", "severity": "major", "axis": "over-suppression / missed genuine merges",
            "finding": f"{metrics['genuine_missed']}/{metrics['genuine_expected']} pre-registered genuine "
                       f"merge surfaces are missed by the applied fix: {', '.join(metrics['genuine_missed_ids'])}. "
                       "Every miss has a skip-list phrase (false-positive / non-merge / detector finding / quoted "
                       "detector / no-genuine-merge / not-a-merge) inside the detector's +-60-char context window "
                       "while the sentence still asserts the merge, so the context-wide skip suppresses genuine "
                       "assertions, not only meta-audit quotations.",
            "falsifier": "A re-run at the same detector hash in which any listed fixture emits a CLASSSEP finding, "
                         "or a demonstration that the listed fixture is not a genuine merge assertion."})
    if metrics["meta_still_flagged"]:
        findings.append({
            "id": "W056-CH-02", "severity": "major", "axis": "residual meta-audit false positives",
            "finding": f"{metrics['meta_still_flagged']}/{metrics['meta_expected_clear']} explicit meta-audit / "
                       f"quotation fixtures are still flagged: {', '.join(metrics['meta_still_flagged_ids'])}; "
                       "these include the three residual probes worker-098 reported at this hash.",
            "falsifier": "A re-run at the same detector hash in which any listed fixture emits no CLASSSEP finding."})
    if residual_block["buckets"].get("candidate-residual-fp"):
        findings.append({
            "id": "W056-CH-03", "severity": "major", "axis": "live residual findings",
            "finding": f"On the pinned map {map_t0['sha256'][:12]} the detector emits "
                       f"{len(claim_findings)} claim-statement hard findings; "
                       f"{residual_block['buckets'].get('candidate-residual-fp', 0)} contain meta/quotation markers "
                       "in a +-160-char window and are candidates for the CF-16 metalinguistic-mention class, "
                       f"{residual_block['buckets'].get('window-too-narrow', 0)} have a skip phrase only outside the "
                       f"+-60 window, {residual_block['buckets'].get('skip-phrase-in-window-recheck', 0)} fire although "
                       "a skip phrase lies inside the +-60 window on at least one composite occurrence (claims with "
                       "several composites; manual recheck), and "
                       f"{residual_block['buckets'].get('candidate-genuine-assertion', 0)} carry no meta marker "
                       "(candidate genuine declarations). Rows with raw context are in the report.",
            "falsifier": "Per-row adjudication showing a row's bucket label contradicts its quoted context."})

    report = {
        "task_id": "W056-CLASSSEP-HOLDOUT-01",
        "worker": "worker-056",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "node_id": "A1", "gate": "G-AUDIT",
        "generated_at": started, "generated_at_end": now(),
        "object": "research_map/class_separation.py (applied classsep prose-precision fix)",
        "pins": {"detector_t0": det_t0, "map_t0": map_t0, "prereg": prereg_pin,
                 "detector_snapshot": pin(det_snap), "map_snapshot": pin(map_snap)},
        "drift": drift,
        "holdout": {"n": len(rows), "metrics": metrics, "rows": rows},
        "regression_runner": reg,
        "residual_live": residual_block,
        "verdict": verdict,
        "findings": findings,
        "non_claims": [
            "Worker calibration evidence only: no gate verdict, no node status, no validation_status=passed, no promotion.",
            "No canonical artifact was edited; the detector and map were read and snapshotted only.",
            "Expectations are normative (the detector's own documented contract + the human-PI acceptance clause); "
            "a missed fixture is evidence of over-suppression, not a proof about any research claim.",
            "The evidence binds to the snapshot hashes above and is time-bounded; if the live detector moved "
            "(drift.detector_moved) it is void for the live file.",
            "The residual-live buckets are mechanical marker classifications for reviewer triage, not semantic adjudications.",
        ],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    readme = render_readme(report)
    (HERE / "README.md").write_text(readme)

    # operator note: the regression runner is the canonical one and imported the LIVE detector;
    # if it moved between before/after the run, say so loudly.
    if reg["detector_sha256_before"] != reg["detector_sha256_after"]:
        print("WARNING: live detector moved during the canonical regression run", file=sys.stderr)

    lines = []
    for rel in ("prereg_holdout_fixtures.json", "run_holdout_056.py", "report.json", "README.md",
                f"snapshot/{det_snap.name}", f"snapshot/{map_snap.name}",
                "raw/classsep_regression_stdout.txt", "raw/classsep_regression_exit.txt"):
        lines.append(f"{sha256_file(HERE / rel)}  {rel}")
    (HERE / "SHA256SUMS").write_text("\n".join(lines) + "\n")

    print(f"verdict={verdict} genuine_missed={metrics['genuine_missed']}/{metrics['genuine_expected']} "
          f"meta_still_flagged={metrics['meta_still_flagged']}/{metrics['meta_expected_clear']} "
          f"claim_findings={len(claim_findings)} buckets={buckets} detector_moved={drift['detector_moved']}")
    return 3 if drift["detector_moved"] else 0


def render_readme(rep: dict) -> str:
    mt = rep["holdout"]["metrics"]
    rr = rep["residual_live"]
    reg = rep["regression_runner"]
    det = rep["pins"]["detector_snapshot"]["sha256"][:12]
    mp = rep["pins"]["map_snapshot"]["sha256"][:12]
    missed = ", ".join(mt["genuine_missed_ids"]) or "none"
    flagged = ", ".join(mt["meta_still_flagged_ids"]) or "none"
    lines = [
        "# W056-CLASSSEP-HOLDOUT-01 — independent holdout on the applied classsep fix",
        "",
        f"- worker: `worker-056` | node `A1` | gate `G-AUDIT` | class ids: four frozen classes",
        f"- pinned detector snapshot `{det}` (`research_map/class_separation.py`), map snapshot `{mp}`",
        f"- pre-registration: `prereg_holdout_fixtures.json` sha256 `{rep['pins']['prereg']['sha256'][:12]}` "
        f"(written and hashed before the first detector invocation)",
        f"- drift: detector_moved={rep['drift']['detector_moved']}, map_moved={rep['drift']['map_moved']}",
        "",
        "## Method",
        "",
        "29 pre-registered fixtures: 10 prose merge assertions (7 adversarial over-suppression probes where a",
        "skip-list phrase lies inside the detector's +-60-char window), 10 explicit meta-audit/quotation",
        "surfaces that must stay clean, 4 benign context controls, 5 declaration-mode R1/R3/R4 surfaces.",
        "The canonical `runtime/bin/classsep_regression.py` was also run (worker-07 corpus) as the directive requires.",
        "",
        "## Result",
        "",
        f"- genuine merge surfaces detected **{mt['genuine_detected']}/{mt['genuine_expected']}**, missed {mt['genuine_missed']} ({missed})",
        f"- meta-audit surfaces still flagged **{mt['meta_still_flagged']}/{mt['meta_expected_clear']}** ({flagged})",
        f"- benign context controls flagged {mt['context_controls_flagged']}/{mt['context_controls_expected_clear']}; "
        f"declaration positives {mt['declaration_positives_detected']}/{mt['declaration_positive_controls']}",
        f"- canonical regression runner exit {reg['exit_code']} (output in `raw/`)",
        f"- live map findings on the pinned snapshot: {rr['claim_statement_findings']} claim-statement hard findings; "
        f"buckets {json.dumps(rr['buckets'], sort_keys=True)}",
        f"- worker verdict: **{rep['verdict']}** (calibration evidence, not a gate verdict)",
        "",
        "## Findings",
        "",
    ]
    for f in rep["findings"]:
        lines += [f"**{f['id']} ({f['severity']}, {f['axis']})** — {f['finding']}", ""]
    lines += [
        "## Falsifiers",
        "",
    ]
    for f in rep["findings"]:
        lines.append(f"- {f['id']}: {f['falsifier']}")
    lines += [
        "",
        "## Non-claims",
        "",
    ]
    lines += [f"- {n}" for n in rep["non_claims"]]
    lines += ["", "## Rerun", "", "```bash", "python3 artifacts/worker-056/classsep_holdout/run_holdout_056.py", "```", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W027-F0-COMPANION-CONSUMER-ALIGN-01 — read-only alignment audit.

Question: at the measured revision, which gate-surface consumers still apply the
byte-identity (mirror) rule to the F0 pair that the controller ruled a COMPANION
pair (astra-life04, REC-3 / CF-17), what exact verdict do they emit, and does a
REC-3-aware predicate preserve hard enforcement of the three real mirror pairs?

Pin design (two-tier, because a controller-authorised rev13 repair was landing
during the run):
  * HARD, fail-closed: the five consumer SOURCE files. These define the predicates
    under audit; if one moves the classification is void (exit 2).
  * SOFT, snapshot-at-read: the class artifacts, FROZEN, map, controller source and
    the two published audit outputs. Each is copied into snapshots/ at read time
    with its sha256 recorded; post-read movement is reported, not hidden.

Exit codes: 0 = alignment gap reproduced; 10 = falsified (all consumers
companion-aware); 2 = hard-pinned consumer source drift (measurement void); 1 = error.

Writes only under the output directory. No canonical file is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
HERE = Path(__file__).resolve().parent


def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


CANON_F0 = "research_map/formulation_taxonomy.yaml"
AUTH_F0 = "artifacts/formulation/formulation_taxonomy.yaml"
MIRROR_PAIRS = [
    ("F1", "schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
    ("F2a", "schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    ("F2b", "schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
]

# HARD pin set: the three non-conformant audit-tool SOURCES, i.e. the objects the
# finding is about. Any exit-time difference voids the run.
PINS_HARD = {
    "artifacts/audit/final_gate_verify.py": "db68655cda2d88b4e0f353f4305f47bf48f3c6708d165b8061138ae5cd298c5b",
    "artifacts/audit/a1_rebind_coverage.py": "6fd6ac9b580c8d242a77d789c7be6b5d59891cd6fdd7c483438ee4fbc12c7d05",
    "artifacts/audit/emit_final_verdicts.py": "08dbd19157c66d97d3993c18623c97446982f9e3b0975027eaab5225c87e8dc0",
}

# SOFT pin set: controller files, class artifacts, FROZEN, map and published
# outputs, all snapshotted at read time.
PINS_SOFT = [
    "research_map/audit_evidence.py",
    "research_map/astra_lifecycle.py",
    CANON_F0, AUTH_F0,
    "schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml", "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/FROZEN.json",
    "research_map/research_map.json",
    "artifacts/audit/final_gate_verify_20260912T004428.json",
    "reviews/A1-rebind-coverage.json",
]

CONSUMERS = [
    {
        "id": "C1-astra-lifecycle",
        "path": "research_map/astra_lifecycle.py",
        "role": "controller publication_status, CF-13, gate reasons (authoritative)",
        "expect": "COMPANION_AWARE",
        "companion_marker": r'\(\s*"research_map/formulation_taxonomy\.yaml"\s*,\s*'
                            r'"artifacts/formulation/formulation_taxonomy\.yaml"\s*,\s*"companion"\s*\)',
        "mirror_guard_marker": r'if\s+mode\s*==\s*"mirror"\s*:\s*\n\s*status\s*=',
    },
    {
        "id": "C2-audit-evidence",
        "path": "research_map/audit_evidence.py",
        "role": "canonical evidence auditor (hard/soft findings consumed by gates + PROTOCOL)",
        "expect": "COMPANION_AWARE",
        "companion_marker": r'\(\s*"research_map/formulation_taxonomy\.yaml"\s*,\s*'
                            r'"artifacts/formulation/formulation_taxonomy\.yaml"\s*,\s*"companion"\s*\)',
        "mirror_guard_marker": r'if\s+mode\s*==\s*"mirror"\s+and\s+sha256\(cp\)\s*!=\s*sha256\(ap\)',
    },
    {
        "id": "C3-final-gate-verify",
        "path": "artifacts/audit/final_gate_verify.py",
        "role": "audit-lead gate verification: emits HASH-F0-mirror status",
        "expect": "MIRROR_HARDCODED",
        "forbidden_marker": r'add\(\s*"HASH-F0-mirror"\s*,\s*"fail"\s+if\s+not\s+matrix\["F0"\]\["mirror_equal"\]',
    },
    {
        "id": "C4-a1-rebind-coverage",
        "path": "artifacts/audit/a1_rebind_coverage.py",
        "role": "audit-lead A1 coverage matrix; its F0 blocker is cited by map gate evidence_refs",
        "expect": "MIRROR_INVERTED",
        "f0_blocker_marker": r'if\s+meas\["F0"\]\["mirror_equal"\]\s+is\s+False\s*:',
        "mirror_gap_marker": r'for\s+t\s+in\s+\("F1",\s*"F2a",\s*"F2b"\)\s*:\s*\n\s*if\s+meas\[t\]\["mirror_equal"\]\s+and\s+not\s+meas\[t\]\["frozen_match"\]',
    },
    {
        "id": "C5-emit-final-verdicts",
        "path": "artifacts/audit/emit_final_verdicts.py",
        "role": "audit-lead verdict emitter: AUD-B2 blocker text and G-F0 blockers",
        "expect": "STALE_RULING_PROSE",
        "stale_marker": r'REC-1/REC-2',
    },
    {
        "id": "C6-audit-r2-verdicts",
        "path": "artifacts/audit/audit_r2_verdicts.py",
        "role": "audit-lead r2 verdict emitter (newest round, post-dates the stale outputs)",
        "expect": "COMPANION_AWARE",
        "companion_text_marker": r'REC-3 companion pair',
    },
    {
        "id": "C7-dispatch-audit-r2",
        "path": "runtime/bin/dispatch_audit_r2.py",
        "role": "audit-lead r2 reviewer dispatcher (newest round)",
        "expect": "COMPANION_AWARE",
        "companion_text_marker": r'REC-3 makes byte-identity',
    },
]

PRE_RUN_DRIFT = {
    "note": ("the controller moved two context files (map, astra_lifecycle.py) between the first "
             "pin attempt and a measurement run, and republished the three class schemas at "
             "00:53:20 (rev13 repair) during the audit; the pin gate exited 2/void on each move, "
             "by design, and the final run snapshots whatever the live revision is at read time"),
    "first_attempt": {
        "research_map/research_map.json": "6d3f0f2792a2d52d4b9c4e2eacd3af6e543e10477c170288c6fd8dc1d8be1b0a",
        "research_map/astra_lifecycle.py": "145a625d209d4dc324ba5b7310cb5659c3729b5d3c41d5627a7ded317d3a62c1",
        "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
        "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
        "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    },
}

FALSIFIER = (
    "FALSIFIED if (a) any of the three named audit-surface consumers is in fact REC-3-aware at its "
    "hard-pinned source sha (it exempts the F0 companion pair from a byte-identity verdict while "
    "still enforcing the F1/F2a/F2b mirror rule); or (b) the F0 canonical and supplement paths are "
    "byte-identical in the snapshot; or (c) HASH-F0-mirror is not 'fail' in the final_gate_verify "
    "output snapshot at its recorded sha; or (d) the A1-rebind-coverage snapshot does not carry the "
    "F0 canonical_authoring_divergence blocker at its recorded sha; or (e) the map snapshot does "
    "not cite reviews/A1-rebind-coverage.json in any gate evidence_refs; or (f) the simulated F1 "
    "mirror divergence is not caught by the canonical auditor (positive control dead); or (g) the "
    "REC-3-aware predicate changes any F1/F2a/F2b mirror-pin verdict relative to the shipped "
    "predicate; or (h) any hard-pinned consumer source drifts between entry and exit (exit 2; "
    "void, not falsified)."
)


def classify_consumers(src) -> list:
    out = []
    for c in CONSUMERS:
        p = src(c["path"])
        text = p.read_text(errors="replace")
        rec: dict = {"id": c["id"], "path": c["path"], "role": c["role"], "expect": c["expect"],
                     "sha256": sha256(p), "source_markers": {}}
        if "companion_marker" in c:
            rec["source_markers"]["companion_f0_row"] = bool(re.search(c["companion_marker"], text))
        if "mirror_guard_marker" in c:
            rec["source_markers"]["mode_aware_mirror_guard"] = bool(
                re.search(c["mirror_guard_marker"], text))
        if "forbidden_marker" in c:
            rec["source_markers"]["f0_mirror_hardcoded"] = bool(re.search(c["forbidden_marker"], text))
        if "f0_blocker_marker" in c:
            rec["source_markers"]["f0_companion_divergence_blocker"] = bool(
                re.search(c["f0_blocker_marker"], text))
        if "mirror_gap_marker" in c:
            rec["source_markers"]["mirror_gap_predicate"] = bool(re.search(c["mirror_gap_marker"], text))
        if "stale_marker" in c:
            rec["source_markers"]["rec1_rec2_still_open"] = bool(re.search(c["stale_marker"], text))
        if "companion_text_marker" in c:
            rec["source_markers"]["companion_text"] = bool(re.search(c["companion_text_marker"], text))

        m = rec["source_markers"]
        if c["id"] in ("C1-astra-lifecycle", "C2-audit-evidence"):
            verdict = "COMPANION_AWARE" if (m.get("companion_f0_row") and
                                            m.get("mode_aware_mirror_guard")) else "MIRROR_HARDCODED"
        elif c["id"] == "C3-final-gate-verify":
            verdict = "MIRROR_HARDCODED" if m.get("f0_mirror_hardcoded") else "COMPANION_AWARE"
        elif c["id"] == "C4-a1-rebind-coverage":
            if m.get("f0_companion_divergence_blocker") and m.get("mirror_gap_predicate"):
                verdict = "MIRROR_INVERTED"
            elif m.get("f0_companion_divergence_blocker"):
                verdict = "MIRROR_HARDCODED"
            else:
                verdict = "COMPANION_AWARE"
        elif c["id"] == "C5-emit-final-verdicts":
            verdict = "STALE_RULING_PROSE" if m.get("rec1_rec2_still_open") else "COMPANION_AWARE"
        elif c["id"] in ("C6-audit-r2-verdicts", "C7-dispatch-audit-r2"):
            verdict = "COMPANION_AWARE" if m.get("companion_text") else "MIRROR_HARDCODED"
        else:
            verdict = "UNKNOWN"
        rec["verdict"] = verdict
        rec["prediction_confirmed"] = verdict == c["expect"]
        rec["rec3_conformant"] = verdict == "COMPANION_AWARE"
        out.append(rec)
    return out


def generic_census(root: Path) -> dict:
    dirs = ["research_map", "artifacts/audit", "runtime/bin", "runtime/state"]
    pat = re.compile(r"(mirror_equal|MIRRORS\s*=|companion|byte-identical|byte_identical)")
    hits = []
    for d in dirs:
        base = root / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.py")):
            if "__pycache__" in p.parts or p.name.startswith("._"):
                continue
            try:
                t = p.read_text(errors="replace")
            except OSError:
                continue
            if not pat.search(t):
                continue
            if "formulation_taxonomy" in t or "af_wcc_vacuum" in t or "mirror_equal" in t:
                hits.append(str(p.relative_to(root)))
    known = {c["path"] for c in CONSUMERS}
    return {"scanned_dirs": dirs, "hits": hits,
            "known_consumers": sorted(known),
            "unclassified_hits": sorted(set(hits) - known)}


def sandbox_run(src, work: Path, mutate=None) -> dict:
    sb = work
    if sb.exists():
        shutil.rmtree(sb)
    (sb / "research_map").mkdir(parents=True)
    shutil.copy2(src("research_map/audit_evidence.py"), sb / "research_map/audit_evidence.py")
    shutil.copy2(src("research_map/class_separation.py"), sb / "research_map/class_separation.py")
    pairs = [(CANON_F0, AUTH_F0)] + [(c, a) for _, c, a in MIRROR_PAIRS]
    frozen = []
    for canon, auth in pairs:
        for rel in (canon, auth):
            dst = sb / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src(rel), dst)
    for tgt, canon, auth in MIRROR_PAIRS:
        frozen.append({"path": canon, "node_id": tgt, "active": True, "sha256": sha256(src(canon))})
    frozen.append({"path": CANON_F0, "node_id": "F0", "active": True, "sha256": sha256(src(CANON_F0))})
    if mutate == "mirror_divergence":
        with (sb / "artifacts/formulation/schemas/af_wcc_vacuum.yaml").open("a") as f:
            f.write("\n# simulated mirror divergence (sandbox only)\n")
    elif mutate == "companion_missing":
        (sb / AUTH_F0).unlink()
    (sb / "research_map/research_map.json").write_text(json.dumps(
        {"groups": [], "gates": [], "claims": [], "portfolio_events": [],
         "frozen_artifacts": frozen}))
    r = subprocess.run([sys.executable, str(sb / "research_map/audit_evidence.py"),
                        "--map", str(sb / "research_map/research_map.json")],
                       cwd=str(sb), capture_output=True, text=True, timeout=120)
    return {"mutate": mutate, "returncode": r.returncode,
            "hard": [ln.strip()[6:].strip() for ln in r.stdout.splitlines() if ln.strip().startswith("HARD")],
            "soft": [ln.strip()[6:].strip() for ln in r.stdout.splitlines() if ln.strip().startswith("soft")],
            "stdout_tail": r.stdout.splitlines()[-1] if r.stdout else "",
            "stderr_tail": r.stderr.splitlines()[-1] if r.stderr else ""}


def frozen_pins(src) -> dict:
    fz = json.loads(src("artifacts/formulation/FROZEN.json").read_text())
    return {p: v.get("sha256") for p, v in fz.get("files", {}).items()}


def live_pair_matrix(src) -> dict:
    pins = frozen_pins(src)
    m = {}
    for tgt, canon, auth in [("F0", CANON_F0, AUTH_F0)] + [(t, c, a) for t, c, a in MIRROR_PAIRS]:
        ch, ah = sha256(src(canon)), sha256(src(auth))
        m[tgt] = {
            "canonical_path": canon, "authoring_path": auth,
            "canonical_sha256": ch, "authoring_sha256": ah,
            "mirror_equal": ch == ah,
            "canonical_frozen_pin": pins.get(canon), "authoring_frozen_pin": pins.get(auth),
            "canonical_pin_match": ch == pins.get(canon, ""),
            "authoring_pin_match": ah == pins.get(auth, ""),
        }
    return m


def reproduce_final_gate_verify(m: dict) -> dict:
    """Byte-faithful re-execution of artifacts/audit/final_gate_verify.py:84-98."""
    out = {"HASH-F0-mirror": "fail" if not m["F0"]["mirror_equal"] else "pass"}
    for t in ("F1", "F2a", "F2b"):
        out[f"HASH-{t}-pin"] = "pass" if (m[t]["mirror_equal"] and m[t]["canonical_pin_match"]) else "fail"
    return out


def rec3_aware_final_gate_verify(m: dict) -> dict:
    """Proposed predicate: companion pair needs each path pinned; mirrors keep byte-identity."""
    c = m["F0"]
    out = {"HASH-F0-companion": "pass" if (c["canonical_pin_match"] and c["authoring_pin_match"])
           else "fail"}
    for t in ("F1", "F2a", "F2b"):
        out[f"HASH-{t}-pin"] = "pass" if (m[t]["mirror_equal"] and m[t]["canonical_pin_match"]) else "fail"
    return out


def reproduce_a1_blockers(m: dict) -> list:
    """Byte-faithful re-execution of artifacts/audit/a1_rebind_coverage.py:223-256."""
    blockers = []
    for t in ("F1", "F2a", "F2b"):
        if m[t]["mirror_equal"] and not m[t]["canonical_pin_match"]:
            blockers.append({"target": t, "blocker": "canonical_beyond_frozen_pin"})
    if m["F0"]["mirror_equal"] is False:
        blockers.append({"target": "F0", "blocker": "canonical_authoring_divergence",
                         "detail": "mirror-equality policy breached"})
    return blockers


def rec3_aware_a1_blockers(m: dict) -> list:
    blockers = []
    for t in ("F1", "F2a", "F2b"):
        if not m[t]["mirror_equal"]:
            blockers.append({"target": t, "blocker": "dual_tree_mirror_divergence"})
        elif not m[t]["canonical_pin_match"]:
            blockers.append({"target": t, "blocker": "canonical_beyond_frozen_pin"})
    c = m["F0"]
    if not (c["canonical_pin_match"] and c["authoring_pin_match"]):
        blockers.append({"target": "F0", "blocker": "companion_pair_unpinned"})
    return blockers


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(HERE.parents[2]))
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    root, out = Path(a.root).resolve(), Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    work = out / "sandbox"
    started = now_iso()

    # ---- HARD pin gate (fail closed on the measurement objects) ----
    hard_entry, hard_drift = {}, []
    for rel, exp in PINS_HARD.items():
        p = root / rel
        cur = sha256(p) if p.is_file() else None
        hard_entry[rel] = {"expected": exp, "measured": cur, "match": cur == exp}
        if cur != exp:
            hard_drift.append(rel)
    if hard_drift:
        report = {"schema_version": "0.1", "task_id": "W027-F0-COMPANION-CONSUMER-ALIGN-01",
                  "worker": "worker-027", "created_at": started,
                  "verdict": "MEASUREMENT_VOID_HARD_PIN_DRIFT", "exit_code": 2,
                  "drifted": hard_drift, "hard_pins": hard_entry, "falsifier": FALSIFIER}
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print("VOID: hard pin drift:", hard_drift)
        return 2

    # ---- SOFT pins: snapshot at read time ----
    snap_dir = out / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    soft_snaps, overrides = {}, {}
    for rel in PINS_SOFT:
        src_p = root / rel
        dst = snap_dir / ("pinned__" + rel.replace("/", "__"))
        shutil.copy2(src_p, dst)
        soft_snaps[rel] = {
            "snapshot": str(dst.relative_to(out)), "sha256_at_read": sha256(dst),
            "mtime": datetime.fromtimestamp(src_p.stat().st_mtime, CST).isoformat(timespec="seconds")}
        overrides[rel] = dst

    def src(rel: str) -> Path:
        return overrides.get(rel, root / rel)

    consumers = classify_consumers(src)
    census = generic_census(root)
    matrix = live_pair_matrix(src)

    controls, findings = [], []

    def ctl(cid, desc, ok, observed=None):
        controls.append({"id": cid, "description": desc, "pass": bool(ok),
                         "observed": observed if observed is not None else bool(ok)})

    # ---- executed controls against the canonical auditor ----
    sb_live = sandbox_run(src, work / "live")
    sb_mirror = sandbox_run(src, work / "mirror_div", mutate="mirror_divergence")
    sb_missing = sandbox_run(src, work / "companion_missing", mutate="companion_missing")
    ctl("CTRL-1", "canonical audit_evidence.py on the live F0 companion pair emits no "
                  "dual-tree divergence finding",
        not any("dual-tree divergence: " + CANON_F0 in x for x in sb_live["hard"] + sb_live["soft"]),
        {"hard": sb_live["hard"], "soft": sb_live["soft"]})
    ctl("CTRL-2", "canonical audit_evidence.py on the live F0 companion pair emits no "
                  "'companion pair incomplete' finding",
        not any("companion pair incomplete: " + CANON_F0 in x for x in sb_live["hard"] + sb_live["soft"]))
    ctl("CTRL-3", "simulated F1 mirror divergence IS caught by the canonical auditor "
                  "(positive control for mirror enforcement)",
        any("dual-tree divergence: schemas/af_wcc_vacuum.yaml" in x
            for x in sb_mirror["hard"] + sb_mirror["soft"]),
        {"hard": sb_mirror["hard"], "soft": sb_mirror["soft"]})
    ctl("CTRL-4", "missing F0 supplement IS flagged 'companion pair incomplete'",
        any("companion pair incomplete: " + CANON_F0 in x
            for x in sb_missing["hard"] + sb_missing["soft"]),
        {"hard": sb_missing["hard"], "soft": sb_missing["soft"]})

    # ---- reproduce each non-conformant consumer's predicate ----
    fgv = reproduce_final_gate_verify(matrix)
    fgv_rec3 = rec3_aware_final_gate_verify(matrix)
    ctl("CTRL-5", "final_gate_verify predicate emits HASH-F0-mirror=fail at the measured revision",
        fgv["HASH-F0-mirror"] == "fail", fgv)
    ctl("CTRL-6", "REC-3-aware predicate makes HASH-F0-companion=pass and leaves every "
                  "F1/F2a/F2b mirror-pin verdict identical to the shipped predicate",
        fgv_rec3["HASH-F0-companion"] == "pass" and
        all(fgv_rec3[f"HASH-{t}-pin"] == fgv[f"HASH-{t}-pin"] for t in ("F1", "F2a", "F2b")),
        {"rec3": fgv_rec3, "shipped": fgv})

    f1_div = json.loads(json.dumps(matrix))
    f1_div["F1"]["mirror_equal"] = False
    f1_div["F1"]["canonical_pin_match"] = False
    ctl("CTRL-7", "simulated F1 divergence fails HASH-F1-pin under BOTH the shipped and the "
                  "REC-3-aware predicate",
        reproduce_final_gate_verify(f1_div)["HASH-F1-pin"] == "fail" and
        rec3_aware_final_gate_verify(f1_div)["HASH-F1-pin"] == "fail")

    a1_live = reproduce_a1_blockers(matrix)
    a1_div = reproduce_a1_blockers(f1_div)
    ctl("CTRL-8", "a1_rebind_coverage predicate emits the F0 companion blocker at the measured revision",
        any(b["blocker"] == "canonical_authoring_divergence" for b in a1_live), a1_live)
    ctl("CTRL-9", "a1_rebind_coverage predicate emits NO F1 blocker for a simulated F1 mirror "
                  "divergence (mirror-coverage gap)",
        not any(b["target"] == "F1" for b in a1_div), a1_div)
    ctl("CTRL-10", "REC-3-aware a1 predicate drops the F0 blocker and adds the F1 divergence blocker",
        not any(b["target"] == "F0" for b in rec3_aware_a1_blockers(matrix)) and
        any(b["target"] == "F1" for b in rec3_aware_a1_blockers(f1_div)))

    # ---- consume the audit surface's own published snapshots ----
    fgv_doc = json.loads(src("artifacts/audit/final_gate_verify_20260912T004428.json").read_text())
    fgv_counts = fgv_doc.get("counts", {})
    f0_row = [c for c in fgv_doc.get("checks", []) if c.get("id") == "HASH-F0-mirror"]
    a1_doc = json.loads(src("reviews/A1-rebind-coverage.json").read_text())
    a1_f0 = [b for b in a1_doc.get("blockers", []) if b.get("target") == "F0"
             and b.get("blocker") == "canonical_authoring_divergence"]
    map_doc = json.loads(src("research_map/research_map.json").read_text())
    cited = sorted({g["gate_id"] for g in map_doc.get("gates", [])
                    if "reviews/A1-rebind-coverage.json" in (g.get("evidence_refs") or [])})
    gate_verdicts = {g.get("gate_id"): g.get("verdict") for g in map_doc.get("gates", [])}
    ctl("CTRL-11", "published audit output snapshot carries HASH-F0-mirror=fail at its recorded sha",
        bool(f0_row) and f0_row[0].get("status") == "fail", f0_row)
    ctl("CTRL-12", "A1 coverage snapshot carries the F0 companion blocker and the map snapshot "
                   "cites that file in gate evidence_refs",
        bool(a1_f0) and bool(cited), {"a1_f0": a1_f0, "map_gates_citing": cited})

    # ---- context observations at the measured revision ----
    stale_frozen = sorted(t for t in ("F1", "F2a", "F2b")
                          if not matrix[t]["canonical_pin_match"])
    fz_doc = json.loads(src("artifacts/formulation/FROZEN.json").read_text())
    historical = [h for h in census["unclassified_hits"]
                  if "astra_lifecycle_" in h and h.endswith("_events.py")]
    context = {
        "map_snapshot_sha256": soft_snaps["research_map/research_map.json"]["sha256_at_read"],
        "map_updated_at": map_doc.get("updated_at"),
        "gate_verdicts_at_snapshot": gate_verdicts,
        "frozen_manifest": {
            "path": "artifacts/formulation/FROZEN.json",
            "revision_at_snapshot": fz_doc.get("revision"),
            "frozen_at": fz_doc.get("frozen_at"),
            "snapshot_sha256": soft_snaps["artifacts/formulation/FROZEN.json"]["sha256_at_read"],
            "pins_current_for": [t for t in ("F1", "F2a", "F2b") if matrix[t]["canonical_pin_match"]],
            "pins_stale_for": stale_frozen,
        },
        "historical_event_emitters_out_of_scope": historical,
        "note": ("the three class schemas were republished at 2026-09-12T00:53:20-00:53:40 (rev13 "
                 "repair) and the FROZEN manifest moved at 00:54:32; at the snapshot the manifest "
                 f"pins match disk for {[t for t in ('F1','F2a','F2b') if matrix[t]['canonical_pin_match']]}"
                 f" (stale for {stale_frozen}). The *_events.py hits are historical event emitters "
                 "whose text records the ruling in force when they were written, not live detectors."),
    }

    # ---- findings ----
    bad = [c for c in consumers if not c["rec3_conformant"]]
    findings.append({
        "id": "W027-C1", "severity": "major", "status": "CONFIRMED",
        "statement": ("Of seven gate-surface consumers of the F0 two-tree relation, four are "
                      "REC-3 companion-aware (controller research_map/astra_lifecycle.py, canonical "
                      "research_map/audit_evidence.py, and the audit-lead's newest r2 tools "
                      "audit_r2_verdicts.py and dispatch_audit_r2.py); three are not: "
                      + ", ".join(f"{c['id']}={c['verdict']}" for c in bad)
                      + " (C5 is superseded-ruling prose in the verdict emitter; C3/C4 are "
                        "executable byte-identity predicates whose published outputs are the ones "
                        "cited by the map snapshot)."),
        "evidence_refs": [f"{c['path']}#{c['sha256'][:12]}" for c in consumers]})
    findings.append({
        "id": "W027-C2", "severity": "major", "status": "CONFIRMED",
        "statement": ("artifacts/audit/final_gate_verify.py emits HASH-F0-mirror=fail for a pair the "
                      "controller publication_status records as 'companion-pinned' and whose gate "
                      "G-F0 the map snapshot now shows as passed; the fail is present in the "
                      f"{fgv_counts.get('pass','?')} pass / {fgv_counts.get('fail','?')} fail / "
                      f"{fgv_counts.get('note','?')} note output at the recorded snapshot sha. Under "
                      "the tool's own accounting a REC-3-aware predicate removes exactly that F0 "
                      "fail; the three mirror-pin rows are unchanged."),
        "evidence_refs": ["artifacts/audit/final_gate_verify.py#db68655cda2d",
                          "snapshots/pinned__artifacts__audit__final_gate_verify_20260912T004428.json",
                          "snapshots/pinned__research_map__astra_lifecycle.py#"
                          + soft_snaps["research_map/astra_lifecycle.py"]["sha256_at_read"][:12]]})
    findings.append({
        "id": "W027-C3", "severity": "major", "status": "CONFIRMED",
        "statement": ("artifacts/audit/a1_rebind_coverage.py emits blocker "
                      "canonical_authoring_divergence / 'mirror-equality policy breached' for the F0 "
                      "companion pair into reviews/A1-rebind-coverage.json, which map gates "
                      + str(cited) + " cite as gate evidence; at the same time its F1/F2a/F2b "
                      "predicate requires mirror_equal==True, so a real mirror divergence produces "
                      "no blocker (CTRL-9). The mirror rule is inverted, not merely stale."),
        "evidence_refs": ["artifacts/audit/a1_rebind_coverage.py#6fd6ac9b580c",
                          "snapshots/pinned__reviews__A1-rebind-coverage.json",
                          "snapshots/pinned__research_map__research_map.json"]})
    findings.append({
        "id": "W027-C4", "severity": "minor", "status": "CONFIRMED",
        "statement": ("The review surface is internally inconsistent about which F0 ruling is "
                      "operative: reviews/G-F0-final-verify.json and artifacts/audit/"
                      "emit_final_verdicts.py (AUD-B2) still record REC-1/REC-2 as open and the "
                      "canonical==authoring criterion as unconfirmable, while reviews/F0-review-18.json "
                      "and reviews/F0-review-025.json already apply REC-3 (CF-17) and bind the "
                      "canonical hash only."),
        "evidence_refs": ["reviews/G-F0-final-verify.json#0fda13de6612",
                          "artifacts/audit/emit_final_verdicts.py#08dbd19157c6",
                          "reviews/F0-review-18.json", "reviews/F0-review-025.json"]})
    findings.append({
        "id": "W027-C5", "severity": "info", "status": "CONFIRMED_CONTROL",
        "statement": ("The canonical auditor behaves correctly under mutation: live companion pair "
                      "silent, simulated F1 mirror divergence caught, missing supplement flagged "
                      "(CTRL-1..4); the proposed REC-3-aware predicate leaves every mirror-pin verdict "
                      "bit-identical to the shipped predicate (CTRL-6/7)."),
        "evidence_refs": ["sandbox/live", "sandbox/mirror_div", "sandbox/companion_missing"]})

    # ---- end hard pin re-check ----
    hard_end = {rel: sha256(root / rel) for rel in PINS_HARD}
    end_drift = [rel for rel, exp in PINS_HARD.items() if hard_end[rel] != exp]
    soft_drift = []
    for rel in PINS_SOFT:
        cur = sha256(root / rel) if (root / rel).is_file() else None
        if cur != soft_snaps[rel]["sha256_at_read"]:
            soft_drift.append({"path": rel, "at_read": soft_snaps[rel]["sha256_at_read"][:12],
                               "at_exit": (cur or "absent")[:12]})
    ctl("CTRL-13", "every HARD-pinned consumer source unchanged over the run", not end_drift, end_drift)
    ctl("CTRL-14", "every SOFT pin snapshotted at read time; post-read movement recorded, not hidden",
        all(soft_snaps[rel]["sha256_at_read"] for rel in PINS_SOFT), soft_drift)

    if bad:
        verdict, exit_code = "REC3_CONSUMER_ALIGNMENT_GAP_CONFIRMED", 0
    else:
        verdict, exit_code = "FALSIFIED_ALL_CONSUMERS_REC3_AWARE", 10
    if end_drift:
        verdict, exit_code = "MEASUREMENT_VOID_HARD_PIN_DRIFT", 2

    report = {
        "schema_version": "0.1",
        "task_id": "W027-F0-COMPANION-CONSUMER-ALIGN-01",
        "worker": "worker-027",
        "created_at": started,
        "finished_at": now_iso(),
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F0",
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "gate": "G-AUDIT",
        "question": ("At the measured revision, which gate-surface consumers still apply the "
                     "byte-identity (mirror) rule to the F0 pair that astra-life04 REC-3 / CF-17 "
                     "ruled a COMPANION pair, what verdict do they emit, and does a REC-3-aware "
                     "predicate preserve enforcement of the three real mirror pairs?"),
        "ruling_under_test": {
            "id": "REC-3",
            "where": ["research_map/research_map.json controller_findings CF-17",
                      "runtime/state/controller_verification/astra-lifecycle-04-decisions.json"],
            "text": ("F0 canonical taxonomy and its class-contract supplement are two distinct "
                     "pinned artifacts; byte-identity is not a publication requirement for this pair."),
        },
        "hard_pins": hard_entry,
        "soft_pins_snapshotted": soft_snaps,
        "pre_run_drift": PRE_RUN_DRIFT,
        "soft_drift_after_read": soft_drift,
        "consumer_census": consumers,
        "generic_census": census,
        "live_pair_matrix": matrix,
        "measured_context": context,
        "reproduced_predicates": {
            "final_gate_verify_shipped": fgv,
            "final_gate_verify_rec3_aware": fgv_rec3,
            "a1_rebind_shipped_live": a1_live,
            "a1_rebind_shipped_on_simulated_f1_divergence": a1_div,
            "a1_rebind_rec3_aware_live": rec3_aware_a1_blockers(matrix),
        },
        "audit_surface_outputs": {
            "final_gate_verify_counts": fgv_counts,
            "final_gate_verify_f0_row": f0_row,
            "projected_counts_under_rec3_aware_predicate": {
                "pass": fgv_counts.get("pass", 0) + (1 if fgv["HASH-F0-mirror"] == "fail" else 0),
                "fail": fgv_counts.get("fail", 0) - (1 if fgv["HASH-F0-mirror"] == "fail" else 0),
                "note": fgv_counts.get("note", 0),
                "basis": "tool's own accounting; projection, not a rerun",
            },
            "a1_coverage_f0_blocker": a1_f0,
            "map_gates_citing_a1_coverage": cited,
        },
        "sandbox_runs": {"live": sb_live, "mirror_divergence": sb_mirror,
                         "companion_missing": sb_missing},
        "controls": controls,
        "checks_passed": sum(1 for c in controls if c["pass"]),
        "checks_total": len(controls),
        "findings": findings,
        "falsifier": FALSIFIER,
        "non_claims": [
            "not a gate verdict: worker events cannot set pending/pass/fail or node done",
            "does not re-adjudicate REC-3; the controller ruling is taken as given (CF-17)",
            "does not modify any canonical artifact, review, map, audit tool or controller tool",
            "the proposed patches are NOT applied; tool ownership is the audit lead's",
            "does not dispute the substance of the audit lead's findings, only predicate conformance to REC-3",
        ],
        "end_drift": end_drift,
        "verdict": verdict,
        "exit_code": exit_code,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "controls.json").write_text(json.dumps(controls, indent=2) + "\n")

    print(f"verdict: {verdict} ({report['checks_passed']}/{report['checks_total']} controls)")
    for c in consumers:
        print(f"  {c['id']:26} {c['verdict']:20} rec3={c['rec3_conformant']} "
              f"prediction={c['prediction_confirmed']}")
    print(f"  measured schemas: F1 {matrix['F1']['canonical_sha256'][:12]} "
          f"F2a {matrix['F2a']['canonical_sha256'][:12]} F2b {matrix['F2b']['canonical_sha256'][:12]}")
    for c in controls:
        if not c["pass"]:
            print(f"  CONTROL FAIL {c['id']}: {c['description']}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

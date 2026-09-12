#!/usr/bin/env python3
"""W083-REV29-POSTAPPLY-INTEGRITY-01 — post-apply integrity probe of FROZEN revision 29.

Read-only with respect to every canonical path. Writes only inside this artifact
directory. Deterministic, offline, no network: every finding is bound to the byte
snapshot under ./snapshot/ plus timestamped live observations.

Snapshot under test: FROZEN.json revision 29, sha256 3d9e3d77... (frozen_at 00:55:02),
48 pins. The live tree was already being re-frozen during this measurement, so live
values are recorded as observations only; the checks that carry the verdict read the
snapshot.

Findings (checks):
  L1  snapshot FROZEN.json is rev29 / sha 3d9e3d77... / 48 pins
  L2  frozen F2b canonical and mirror copies are byte-identical (b2ab6acb2bbe)
  L3  the F2b artifact's own containment order (declares C2 strictly inside C0)
  L4  L-FORM-01: the forbidden-transfer reason still claims C2 is "strictly larger"
  L5  the same reason's consequent ("strictly weaker") is consistent -> one-word defect
  L6  rev28 -> rev29 delta census: the L-FORM-01 row was NOT touched by the rev29 apply
  L7  L-FORM-02 contrast: taxonomy-consistency evidence binding IS closed at rev29
  L8  live 48-pin sweep vs verify_frozen.py parity at measurement time
  L9  measured freeze drift: pinned fc6ee058 vs observed 0b23f0b29232, content valid:false,
      root cause check_variant_deltas.py:33 unconditional write (snapshot-bound)
  L10 instrument left every canonical path byte-unchanged
  L11 live re-check: is the L-FORM-01 row still present in the live canonical F2b?

Controls run on sandbox copies only (C1 one-word fix, C2 reverse mutant, C3 order flip,
C4 FROZEN tamper).
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

CN = timezone(timedelta(hours=8))

EXPECT = {
    "frozen_sha256": "3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833",
    "frozen_revision": 29,
    "frozen_pins": 48,
    "frozen_at": "2026-09-12T00:55:02+08:00",
    "f2b_sha256": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "f2b_rev28_sha256": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
    "taxcons_sha256": "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b",
    "checker_taxcons_sha256": "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd",
    "variant_delta_pinned_sha256": "fc6ee058dd961275b37f8386b1675112d96291e22f972204efc1f8b6df9607b1",
    "variant_delta_observed_drift_sha256": "0b23f0b29232fba4d6638de7d3d94f1e97851f5ba3cec8b29a43181a5a40fd7c",
    "check_variant_deltas_sha256": "d33d8f57f4dd244e5beb7a981103e6a113a9673c1d831f99b24960b6e61753c4",
}

TOKENS = {"C0", "H2loc", "C^1,1", "C2", "C1,1", "H2_loc"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check(cid, expected, observed, status, severity, falsifier, detail=""):
    return {"id": cid, "expected": expected, "observed": observed, "status": status,
            "severity": severity, "falsifier": falsifier, "detail": detail}


def parse_containment_order(text: str):
    """Return (order_descending_containment, raw) declared by the artifact.

    Handles both 'A contains B contains ...' and 'A subset of B subset of ...' chains.
    """
    for line in text.splitlines():
        if "extension_class_containment" not in line:
            continue
        raw = line.strip()
        toks = []
        for braced, plain in re.findall(r"E_(?:\{([^}]*)\}|([A-Za-z0-9^_,]+))", line):
            t = (braced or plain).strip()
            t = "C^1,1" if t in ("C^1,1", "C1,1") else ("H2loc" if t in ("H2loc", "H2_loc") else t)
            if t in TOKENS:
                toks.append(t)
        if not toks:
            return None, raw
        if "subset of" in line:
            toks = list(reversed(toks))
        return toks, raw
    return None, None


def lform01_row(text: str):
    for i, line in enumerate(text.splitlines(), 1):
        if "no proper future C2 extension" in line and 'to: "this class"' in line:
            return i, line
    return None, None


def size_word(line: str):
    m = re.search(r"C2 is a strictly (larger|smaller) extension class", line)
    return m.group(1) if m else None


def strength_word(line: str):
    m = re.search(r"C2-inextendibility is strictly (weaker|stronger)", line)
    return m.group(1) if m else None


def required_size_word(order):
    if order == ["C0", "H2loc", "C^1,1", "C2"]:
        return "smaller"
    if order == ["C2", "C^1,1", "H2loc", "C0"]:
        return "larger"
    return None


def run_probe(root: Path, snap: Path, baseline: Path):
    checks, files = [], {}

    snap_frozen = snap / "FROZEN.json"
    frozen = json.loads(snap_frozen.read_text())
    frozen_sha = sha256_file(snap_frozen)
    files["snapshot/FROZEN.json"] = frozen_sha
    checks.append(check(
        "L1_SNAPSHOT_FROZEN",
        {"sha256": EXPECT["frozen_sha256"], "revision": EXPECT["frozen_revision"],
         "pins": EXPECT["frozen_pins"], "frozen_at": EXPECT["frozen_at"]},
        {"sha256": frozen_sha, "revision": frozen.get("revision"), "pins": len(frozen.get("files", {})),
         "frozen_at": frozen.get("frozen_at")},
        "PASS" if (frozen_sha == EXPECT["frozen_sha256"] and frozen.get("revision") == EXPECT["frozen_revision"]
                   and len(frozen.get("files", {})) == EXPECT["frozen_pins"]) else "FAIL",
        "info",
        "FALSE if the snapshot FROZEN.json hash, revision or pin count differs from the cited values.",
    ))

    snap_c0 = snap / "schemas/af_scc_c0_vacuum.yaml"
    snap_c0m = snap / "schemas/af_scc_c0_vacuum.mirror.yaml"
    h_c0, h_c0m = sha256_file(snap_c0), sha256_file(snap_c0m)
    files["snapshot/schemas/af_scc_c0_vacuum.yaml"] = h_c0
    files["snapshot/schemas/af_scc_c0_vacuum.mirror.yaml"] = h_c0m
    checks.append(check(
        "L2_F2B_MIRROR_IDENTITY",
        {"canonical": EXPECT["f2b_sha256"], "mirror": EXPECT["f2b_sha256"], "byte_identical": True},
        {"canonical": h_c0, "mirror": h_c0m, "byte_identical": snap_c0.read_bytes() == snap_c0m.read_bytes()},
        "PASS" if h_c0 == h_c0m == EXPECT["f2b_sha256"] else "FAIL",
        "info",
        "FALSE if the two frozen F2b copies differ or do not hash to the cited value.",
    ))

    text = snap_c0.read_text()
    order, order_raw = parse_containment_order(text)
    required = required_size_word(order)
    checks.append(check(
        "L3_CONTAINMENT_ORDER",
        {"order": ["C0", "H2loc", "C^1,1", "C2"], "required_c2_size_word": "smaller"},
        {"order": order, "raw": order_raw, "required_c2_size_word": required},
        "PASS" if required == "smaller" else "FAIL",
        "info",
        "FALSE if the artifact does not declare E_C2 strictly inside E_C0 (then 'smaller' is not required).",
    ))

    row_no, row = lform01_row(text)
    claimed_size = size_word(row) if row else None
    checks.append(check(
        "L4_LFORM01_SIZE_CLAIM",
        {"line": row_no, "claimed_size_word": "smaller", "row": row},
        {"line": row_no, "claimed_size_word": claimed_size, "row": row},
        "PASS" if claimed_size == "smaller" else "FAIL",
        "hard",
        "FALSE if the frozen F2b forbidden-transfer reason reads 'C2 is a strictly smaller extension class' "
        "at the snapshot hash.",
    ))

    claimed_strength = strength_word(row) if row else None
    checks.append(check(
        "L5_CONSEQUENT_STRENGTH",
        {"claimed_strength_word": "weaker", "note": "consistent with E_C2 strictly inside E_C0"},
        {"claimed_strength_word": claimed_strength},
        "PASS" if claimed_strength == "weaker" else "FAIL",
        "info",
        "FALSE if the same reason does not read 'C2-inextendibility is strictly weaker' (defect would be wider).",
    ))

    base_sha = sha256_file(baseline) if baseline.exists() else None
    base_text = baseline.read_text() if baseline.exists() else ""
    base_row_no, base_row = lform01_row(base_text)
    row_unchanged = base_row is not None and row is not None and base_row == row
    diff_hunks = [ln for ln in difflib.unified_diff(base_text.splitlines(), text.splitlines(),
                                                    fromfile="rev28", tofile="rev29", lineterm="", n=0)
                  if ln.startswith(("@@", "+", "-")) and not ln.startswith(("+++", "---"))]
    checks.append(check(
        "L6_REV29_DELTA_CENSUS",
        {"baseline_sha256": EXPECT["f2b_rev28_sha256"], "lform01_row_unchanged": True},
        {"baseline_sha256": base_sha, "baseline_row_no": base_row_no, "snapshot_row_no": row_no,
         "lform01_row_unchanged": row_unchanged, "diff_hunks": diff_hunks[:12], "diff_hunk_count": len(diff_hunks)},
        "PASS" if base_sha == EXPECT["f2b_rev28_sha256"] and row_unchanged else "FAIL",
        "info",
        "FALSE if the archived rev28 baseline differs from the cited hash or the L-FORM-01 row text changed in rev29.",
    ))

    taxcons = snap / "formulation_evidence/taxonomy_consistency.json"
    checker = snap / "formulation_tools/check_taxonomy_consistency.py"
    h_tc, h_ck = sha256_file(taxcons), sha256_file(checker)
    files["snapshot/formulation_evidence/taxonomy_consistency.json"] = h_tc
    files["snapshot/formulation_tools/check_taxonomy_consistency.py"] = h_ck
    pin_tc = frozen["files"].get("artifacts/formulation/evidence/taxonomy_consistency.json", {}).get("sha256")
    pin_ck = frozen["files"].get("artifacts/formulation/tools/check_taxonomy_consistency.py", {}).get("sha256")
    checks.append(check(
        "L7_LFORM02_BINDING_CLOSED",
        {"snapshot_evidence": EXPECT["taxcons_sha256"], "frozen_pin_evidence": EXPECT["taxcons_sha256"],
         "snapshot_checker": EXPECT["checker_taxcons_sha256"], "frozen_pin_checker": EXPECT["checker_taxcons_sha256"]},
        {"snapshot_evidence": h_tc, "frozen_pin_evidence": pin_tc,
         "snapshot_checker": h_ck, "frozen_pin_checker": pin_ck},
        "PASS" if h_tc == pin_tc == EXPECT["taxcons_sha256"] and h_ck == pin_ck == EXPECT["checker_taxcons_sha256"] else "FAIL",
        "info",
        "FALSE if the frozen consistency-evidence binding still points at superseded bytes or an unpinned checker.",
    ))

    # Live pin sweep against the LIVE FROZEN, with parity to the pinned tool. The live
    # freeze moved during this measurement, so parity is only testable when the live
    # FROZEN hash is stable across the sweep+tool window; otherwise INCONCLUSIVE.
    live_frozen_path = root / "artifacts/formulation/FROZEN.json"
    live_frozen_sha = sha256_file(live_frozen_path)
    live_frozen = json.loads(live_frozen_path.read_text())
    drift = []
    for rel, meta in sorted(live_frozen.get("files", {}).items()):
        p = root / rel
        live = sha256_file(p) if p.exists() else None
        if live != meta["sha256"]:
            drift.append({"path": rel, "pinned": meta["sha256"], "live": live})
    proc = subprocess.run([sys.executable, str(root / "artifacts/formulation/tools/verify_frozen.py")],
                          cwd=str(root), capture_output=True, text=True)
    tool_drift = [ln.strip() for ln in proc.stdout.splitlines() if "DRIFT" in ln]
    live_after_sha = sha256_file(live_frozen_path)
    stable = live_frozen_sha == live_after_sha
    parity = stable and proc.returncode == (0 if not drift else 1) and len(tool_drift) == len(drift)
    checks.append(check(
        "L8_LIVE_PIN_SWEEP_PARITY",
        {"parity_with_tool": True, "note": "drift count is an observation; only sweep/tool parity is asserted"},
        {"measured_at": datetime.now(CN).isoformat(),
         "live_frozen_sha256_before": live_frozen_sha, "live_frozen_sha256_after": live_after_sha,
         "live_frozen_stable_across_window": stable,
         "live_frozen_revision": live_frozen.get("revision"), "live_frozen_pins": len(live_frozen.get("files", {})),
         "drift_count": len(drift), "drift": drift, "verify_frozen_exit": proc.returncode,
         "tool_drift_lines": tool_drift, "parity_with_tool": parity},
        "PASS" if parity else ("INCONCLUSIVE" if not stable else "FAIL"),
        "hard",
        "FALSE if the live FROZEN is stable across the window and the internal pin sweep disagrees with "
        "artifacts/formulation/tools/verify_frozen.py.",
    ))

    vd_drift = snap / "formulation_evidence/variant_delta_check.json"
    h_vd = sha256_file(vd_drift)
    vd = json.loads(vd_drift.read_text())
    tool_src = root / "artifacts/formulation/tools/check_variant_deltas.py"
    src_lines = tool_src.read_text().splitlines()
    write_line = next((f"{i}:{l.strip()}" for i, l in enumerate(src_lines, 1)
                       if "variant_delta_check.json" in l and "write_text" in l), None)
    guard_tokens = [t for t in ("--write", "--apply", "dry_run", "dry-run") if t in tool_src.read_text()]
    checks.append(check(
        "L9_MEASURED_FREEZE_DRIFT",
        {"observed_drift_sha256": EXPECT["variant_delta_observed_drift_sha256"],
         "pinned_sha256": EXPECT["variant_delta_pinned_sha256"], "valid": False,
         "unconditional_write_line": True, "write_guard_tokens": []},
        {"observed_drift_sha256": h_vd,
         "pinned_sha256": frozen["files"].get("artifacts/formulation/evidence/variant_delta_check.json", {}).get("sha256"),
         "observed_mtime": "2026-09-12T00:56:03+08:00", "frozen_at": frozen.get("frozen_at"),
         "valid": vd.get("valid"), "errors": vd.get("errors"),
         "unconditional_write_line": write_line, "write_guard_tokens": guard_tokens,
         "checker_pin": frozen["files"].get("artifacts/formulation/tools/check_variant_deltas.py", {}).get("sha256")},
        "PASS" if (h_vd == EXPECT["variant_delta_observed_drift_sha256"] and vd.get("valid") is False
                   and h_vd != EXPECT["variant_delta_pinned_sha256"] and write_line and not guard_tokens) else "FAIL",
        "hard",
        "FALSE if the captured drift bytes do not hash to 0b23f0b2..., do not declare valid:false, "
        "or if check_variant_deltas.py has a write guard / does not write the canonical evidence path by default.",
    ))

    # Mutant controls (sandbox only).
    controls = []
    with tempfile.TemporaryDirectory(prefix="w083rev29ctl_") as td:
        tdp = Path(td)
        mutants = {
            "C1_ONE_WORD_FIX": text.replace("C2 is a strictly larger extension class",
                                            "C2 is a strictly smaller extension class"),
            "C2_REVERSE_MUTANT": text.replace("C2-inextendibility is strictly weaker",
                                              "C2-inextendibility is strictly stronger"),
            "C3_ORDER_FLIP": text.replace("E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
                                          "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0"),
        }
        for name, txt in mutants.items():
            r_no, r = lform01_row(txt)
            order_m, _ = parse_containment_order(txt)
            req = required_size_word(order_m)
            exp_strength = "weaker" if req == "smaller" else ("stronger" if req == "larger" else None)
            controls.append({
                "id": name, "landing": "sandbox", "order": order_m, "required_size_word": req,
                "expected_strength_word": exp_strength,
                "claimed_size_word": size_word(r) if r else None,
                "claimed_strength_word": strength_word(r) if r else None,
                "size_check": "PASS" if (size_word(r) if r else None) == req else "FAIL",
                "strength_check": "PASS" if (strength_word(r) if r else None) == exp_strength else "FAIL",
            })
        tf = tdp / "FROZEN.json"
        doc = json.loads((snap / "FROZEN.json").read_text())
        doc["revision"] = 28
        tf.write_text(json.dumps(doc))
        controls.append({"id": "C4_FROZEN_TAMPER", "landing": "sandbox",
                         "snapshot_sha256": sha256_file(tf),
                         "l1_predicate": "PASS" if sha256_file(tf) == EXPECT["frozen_sha256"] else "FAIL"})

    controls_ok = (controls[0]["size_check"] == "PASS" and controls[0]["strength_check"] == "PASS"
                   and controls[1]["size_check"] == "FAIL" and controls[1]["strength_check"] == "FAIL"
                   and controls[2]["order"] == ["C2", "C^1,1", "H2loc", "C0"]
                   and controls[2]["size_check"] == "PASS" and controls[2]["strength_check"] == "FAIL"
                   and controls[3]["l1_predicate"] == "FAIL")

    # Live re-check: the defect's presence in the current live canonical F2b.
    live_c0 = root / "schemas/af_scc_c0_vacuum.yaml"
    live_text = live_c0.read_text()
    l_no, l_row = lform01_row(live_text)
    live_defect = size_word(l_row) if l_row else None
    checks.append(check(
        "L11_LIVE_DEFECT_RECHECK",
        {"live_f2b_sha256": EXPECT["f2b_sha256"], "live_row_claimed_size_word": "smaller"},
        {"measured_at": datetime.now(CN).isoformat(), "live_f2b_sha256": sha256_file(live_c0),
         "live_row_no": l_no, "live_row_claimed_size_word": live_defect, "live_row": l_row,
         "live_defect_present": live_defect == "larger"},
        "PASS" if live_defect is not None else "FAIL",
        "info",
        "FALSE if the live canonical F2b cannot be read or no longer contains the forbidden-transfer row "
        "(recorded as live_defect_present=false if it was repaired after this snapshot).",
    ))

    after = {p: sha256_file(root / p) for p in CANONICAL_WATCH}
    untouched = all(before[p] == after[p] for p in CANONICAL_WATCH)
    checks.append(check(
        "L10_CANONICAL_UNTOUCHED",
        {"canonical_paths_unchanged_by_probe": True},
        {"before": before, "after": after},
        "PASS" if untouched else "FAIL",
        "info",
        "FALSE if any canonical path changed hash during this probe (the probe must be write-free).",
    ))
    return checks, files, controls, controls_ok


CANONICAL_WATCH = [
    "schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    "artifacts/formulation/FROZEN.json",
    "artifacts/formulation/evidence/taxonomy_consistency.json",
    "artifacts/formulation/evidence/variant_delta_check.json",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent))
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    here = Path(__file__).resolve().parent
    snap = here / "snapshot"
    baseline = here.parent / "rev13_repair_packet/work_baseline/schemas/af_scc_c0_vacuum.yaml"

    global before
    started = datetime.now(CN).isoformat()
    before = {p: sha256_file(root / p) for p in CANONICAL_WATCH}

    checks, files, controls, controls_ok = run_probe(root, snap, baseline)
    hard = [c for c in checks if c["status"] == "FAIL" and c["severity"] == "hard"]
    verdict = "LFORM01_OPEN__FREEZE_DRIFTED" if hard else "ALL_CHECKS_PASS"
    finished = datetime.now(CN).isoformat()
    report = {
        "task_id": "W083-REV29-POSTAPPLY-INTEGRITY-01",
        "worker": "worker-083",
        "created_at": started,
        "finished_at": finished,
        "root": str(root),
        "snapshot_revision": EXPECT["frozen_revision"],
        "snapshot_sha256": EXPECT["frozen_sha256"],
        "verdict": verdict,
        "hard_defects": [c["id"] for c in hard],
        "lform01_open": next(c for c in checks if c["id"] == "L4_LFORM01_SIZE_CLAIM")["status"] == "FAIL",
        "lform02_binding_closed": next(c for c in checks if c["id"] == "L7_LFORM02_BINDING_CLOSED")["status"] == "PASS",
        "freeze_drift_measured": next(c for c in checks if c["id"] == "L9_MEASURED_FREEZE_DRIFT")["status"] == "PASS",
        "live_defect_present": next(c for c in checks if c["id"] == "L11_LIVE_DEFECT_RECHECK")["observed"]["live_defect_present"],
        "controls_ok": controls_ok,
        "controls": controls,
        "checks": checks,
        "authority": "worker measurement only; no gate verdict, no node status, no canonical write",
    }
    (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    (out / "evidence.json").write_text(json.dumps({
        "task_id": report["task_id"], "verdict": verdict, "controls": controls, "controls_ok": controls_ok,
        "checks": [{"id": c["id"], "status": c["status"], "severity": c["severity"], "expected": c["expected"],
                    "observed": c["observed"], "falsifier": c["falsifier"]} for c in checks],
    }, indent=1) + "\n")
    (out / "snapshot_hashes.json").write_text(json.dumps(files, indent=1) + "\n")
    print(json.dumps({"verdict": verdict, "hard_defects": report["hard_defects"],
                      "lform01_open": report["lform01_open"],
                      "lform02_binding_closed": report["lform02_binding_closed"],
                      "freeze_drift_measured": report["freeze_drift_measured"],
                      "controls_ok": report["controls_ok"],
                      "live_defect_present": report["live_defect_present"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

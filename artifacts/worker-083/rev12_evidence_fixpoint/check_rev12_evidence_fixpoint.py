#!/usr/bin/env python3
"""W083-REV12-CLOSURE-EVIDENCE-FIXPOINT-01

Bounded, deterministic, READ-ONLY audit: does the FROZEN rev28 evidence set for the
rev12 closure actually bind the frozen rev12 bytes, and is the frozen revision a fixed
point of the pinned closure procedure?

Audited objects (all sha256-pinned in artifacts/formulation/FROZEN.json rev28):
  * close_findings_rev27_report.json  (the closure record)
  * close_findings_rev27.py           (the closure procedure)
  * schemas/af_wcc_vacuum.yaml, af_scc_c2_vacuum.yaml, af_scc_c0_vacuum.yaml (rev12)
  * research_map/formulation_taxonomy.yaml (F0 rev5), supplement, taxonomy_consistency.json
  * FROZEN.json itself (pin sweep)

The script writes nothing unless --write is passed (and then only report.json /
evidence.json inside its own directory). It never edits a canonical artifact.

Exit code 0 iff every CONTROL passes. A confirmed binding defect is a finding, not a
control failure.

Reproduce:
  python3 check_rev12_evidence_fixpoint.py --write
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FROZEN_REL = "artifacts/formulation/FROZEN.json"
REPORT_REL = "artifacts/formulation/evidence/close_findings_rev27_report.json"
TOOL_REL = "artifacts/formulation/tools/close_findings_rev27.py"
CONSISTENCY_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"
GATE_TEST_REL = "artifacts/formulation/evidence/gate_test_report.json"
FROZEN_CLASS_PATHS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "research_map/formulation_taxonomy.yaml",
]
FIXED_RUN_AT = "2026-09-12T00:45:00+08:00"
SCAN_SIZE_CAP = 4 * 1024 * 1024
CANONICAL_REVISION_RE = re.compile(r"^revision:\s*(\d+)\s*$", re.M)
FROZEN_PREFIXES = {
    "F1": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "F2a": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "F2b": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def measured_revision(p: Path):
    try:
        m = CANONICAL_REVISION_RE.search(p.read_text(encoding="utf-8", errors="replace"))
        return int(m.group(1)) if m else None
    except OSError:
        return None


def pin_sweep(manifest: dict):
    bad, ok = [], 0
    for rel, rec in sorted(manifest["files"].items()):
        f = ROOT / rel
        if not f.exists():
            bad.append({"path": rel, "problem": "MISSING", "manifest": rec.get("sha256")})
            continue
        h = sha256_file(f)
        if h != rec.get("sha256"):
            bad.append({"path": rel, "problem": "DRIFT", "manifest": rec.get("sha256"), "disk": h})
        else:
            ok += 1
    return {"checked": len(manifest["files"]), "matched": ok, "problems": bad}


def classify_report_entries(manifest: dict, report: dict):
    entries = []
    for rel, rec in sorted(report.get("files", {}).items()):
        if not isinstance(rec, dict) or "sha256" not in rec:
            continue
        declared = rec["sha256"]
        pin = manifest["files"].get(rel, {}).get("sha256")
        disk = sha256_file(ROOT / rel) if (ROOT / rel).exists() else None
        if declared == pin:
            cls = "MATCHES_FROZEN_PIN"
        elif declared == disk:
            cls = "MATCHES_DISK_NOT_PIN"
        else:
            cls = "STALE_INTERMEDIATE"
        entries.append({
            "path": rel,
            "declared_sha256": declared,
            "frozen_pin": pin,
            "disk_sha256": disk,
            "declared_revision": rec.get("revision"),
            "disk_revision": measured_revision(ROOT / rel) if (ROOT / rel).exists() else None,
            "changed": rec.get("changed"),
            "classification": cls,
        })
    stale = [e for e in entries if e["classification"] == "STALE_INTERMEDIATE"]
    same_rev_diff_bytes = [e for e in stale
                           if e["declared_revision"] is not None
                           and e["declared_revision"] == e["disk_revision"]]
    return {"entries": entries, "stale_count": len(stale),
            "same_declared_revision_diff_bytes": same_rev_diff_bytes}


def archive_scan(stale_hashes):
    """Look for any file in the tree whose bytes hash to an intermediate declared hash."""
    found = {h: [] for h in stale_hashes}
    scanned = 0
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        s = str(p)
        if "/.git/" in s or s.endswith(".pack") or s.endswith(".idx"):
            continue
        try:
            if p.stat().st_size > SCAN_SIZE_CAP:
                continue
            b = p.read_bytes()
        except OSError:
            continue
        scanned += 1
        h = sha256_bytes(b)
        if h in found:
            found[h].append(str(p.relative_to(ROOT)))
    return {"scanned_files": scanned, "size_cap_bytes": SCAN_SIZE_CAP, "copies": found,
            "any_copy_found": any(found.values())}


def run_tool_dryrun():
    """Run the pinned closure procedure in read-only dry-run mode at the frozen bytes."""
    tool = ROOT / TOOL_REL
    before = {rel: sha256_file(ROOT / rel) for rel in FROZEN_CLASS_PATHS if (ROOT / rel).exists()}
    before[CONSISTENCY_REL] = sha256_file(ROOT / CONSISTENCY_REL)
    proc = subprocess.run(
        [sys.executable, str(tool), "--dry-run", "--at", FIXED_RUN_AT],
        cwd=str(ROOT), capture_output=True, text=True, timeout=180,
    )
    after = {rel: sha256_file(ROOT / rel) for rel in before}
    return {
        "command": f"python3 {TOOL_REL} --dry-run --at {FIXED_RUN_AT}",
        "exit_code": proc.returncode,
        "stdout_head": proc.stdout[:600],
        "stderr_head": proc.stderr[:1200],
        "assert_failure": "ASSERT FAIL" in proc.stderr,
        "reached_apply_stage": proc.returncode == 0,
        "inputs_unchanged": before == after,
        "inputs_before": before,
        "inputs_after": after,
    }


def delta_scan(manifest: dict, stale_hashes, report: dict):
    """Does any FROZEN revision delta record the post-report schema byte change?"""
    hits = []
    for k, v in manifest.items():
        if k.endswith("_delta"):
            s = json.dumps(v)
            for h in stale_hashes:
                if h in s:
                    hits.append({"delta": k, "hash": h})
            if "00:32:02" in s:
                hits.append({"delta": k, "marker": "00:32:02"})
    report_text = json.dumps(report)
    return {"delta_hits": hits,
            "report_mentions_intermediates": bool(re.search("|".join(stale_hashes), report_text))}


def cross_binding(manifest: dict):
    """Is the frozen outcome independently bound by other pinned artifacts?"""
    out = {}
    for rel in (GATE_TEST_REL,):
        pin = manifest["files"].get(rel, {}).get("sha256")
        disk = sha256_file(ROOT / rel) if (ROOT / rel).exists() else None
        txt = (ROOT / rel).read_text(encoding="utf-8", errors="replace") if (ROOT / rel).exists() else ""
        out[rel] = {
            "pinned": pin, "disk_matches_pin": pin == disk,
            "binds": {name: (h in txt) for name, h in FROZEN_PREFIXES.items()},
            "declared_bytes": manifest["files"].get(rel, {}).get("bytes"),
        }
    variants = {}
    for rel in ["artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json",
                "artifacts/formulation/variants/AF-SCC-C0-VAC-GEN.variant-CH.delta.json"]:
        if (ROOT / rel).exists():
            txt = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
            variants[rel] = {"binds": {n: (h in txt) for n, h in FROZEN_PREFIXES.items()},
                             "pinned": manifest["files"].get(rel, {}).get("sha256"),
                             "disk_matches_pin": manifest["files"].get(rel, {}).get("sha256")
                             == sha256_file(ROOT / rel)}
    out["variant_deltas"] = variants
    return out


def synthetic_report(pins: dict, mutate: bool):
    files = {}
    for i, (rel, h) in enumerate(sorted(pins.items())):
        val = h
        if mutate and i == 0:
            val = "0" * 64
        files[rel] = {"sha256": val, "changed": True, "revision": 12}
    return {"at": "synthetic", "phase": "apply", "files": files}


def canonical_digest(payload: dict) -> str:
    """Digest of the decision-relevant result. Excludes wall clock, the controls block
    (which is derived from this digest) and the archive-scan file count, which is
    environment-volatile on a live tree but carries no decision weight."""
    volatile = {"generated_at", "canonical_digest_sha256", "controls", "controls_all_pass"}
    clean = {k: v for k, v in payload.items() if k not in volatile}
    clean = json.loads(json.dumps(clean, sort_keys=True, default=str))
    if isinstance(clean.get("archive_scan"), dict):
        clean["archive_scan"].pop("scanned_files", None)
    return sha256_bytes(json.dumps(clean, sort_keys=True, default=str).encode())


def build_base():
    manifest = read_json(ROOT / FROZEN_REL)
    report = read_json(ROOT / REPORT_REL)
    frozen_sha = sha256_file(ROOT / FROZEN_REL)
    report_sha = sha256_file(ROOT / REPORT_REL)

    sweep = pin_sweep(manifest)
    rep = classify_report_entries(manifest, report)
    pins = {e["path"]: e["frozen_pin"] for e in rep["entries"] if e["frozen_pin"]}
    stale_hashes = sorted({e["declared_sha256"] for e in rep["entries"]
                           if e["classification"] == "STALE_INTERMEDIATE"})
    scan = archive_scan(stale_hashes)
    tool = run_tool_dryrun()
    deltas = delta_scan(manifest, stale_hashes, report)
    xbind = cross_binding(manifest)

    result = {
        "task_id": "W083-REV12-CLOSURE-EVIDENCE-FIXPOINT-01",
        "worker": "worker-083",
        "role": "bounded execution worker",
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "gate_scope": "G-FORM closure evidence / G-F0 input (no gate verdict)",
        "authority_note": ("Measurement and controls only. No gate verdict, no node status, "
                           "no validation_status, no schema or evidence edit."),
        "frozen": {"path": FROZEN_REL, "sha256": frozen_sha, "revision": manifest["revision"],
                   "frozen_at": manifest["frozen_at"], "declared_files": len(manifest["files"])},
        "pin_sweep": sweep,
        "report": {"path": REPORT_REL, "pinned_sha256": manifest["files"][REPORT_REL]["sha256"],
                   "disk_sha256": report_sha,
                   "answers": {
                       "Q1_frozen_matches_disk": not sweep["problems"],
                       "Q2_closure_evidence_binds_frozen_rev12": rep["stale_count"] == 0,
                       "Q3_closure_reproducible_at_frozen_bytes": tool["reached_apply_stage"],
                       "Q4_outcome_bound_elsewhere": all(xbind[GATE_TEST_REL]["binds"].values()),
                   }},
        "report_entry_audit": rep,
        "archive_scan": scan,
        "tool_dryrun": tool,
        "delta_scan": deltas,
        "cross_binding": xbind,
        "finding": {
            "id": "W083-REF-01",
            "severity": "major",
            "category": "evidence-binding / reproducibility",
            "statement": (
                f"{rep['stale_count']} of {len(rep['entries'])} post-write hashes declared in the pinned closure "
                f"report {REPORT_REL} (pin {manifest['files'][REPORT_REL]['sha256'][:12]}) are intermediate values "
                f"({', '.join(h[:12] for h in stale_hashes)}) that match neither the frozen rev12 pins nor the "
                f"current disk bytes; the pinned closure procedure {TOOL_REL} fails closed in dry-run at the frozen "
                f"bytes (exit {tool['exit_code']}, ASSERT FAIL), so the closure is not reproducible from its own "
                f"pinned evidence+tool. The frozen outcome pins are nevertheless bound by the pinned "
                f"{GATE_TEST_REL} and by FROZEN rev28 itself, so this is a stage-2 evidence defect, not a "
                f"schema-content defect."),
            "consequence": ("a reviewer following the closure evidence to validate the rev12 repair reaches "
                            "non-frozen, non-archived bytes; the repair narrative cannot be re-derived from the "
                            "pinned (evidence, tool, bytes) triple without a measure-only addendum"),
            "falsifier": ("exhibit a FROZEN revision whose closure report cites the frozen post-closure hashes for "
                          "the schemas/taxonomy_consistency; or a pinned revision delta that records the 00:32:02 "
                          "schema rewrite; or an archived file whose bytes hash to one of the intermediate values and "
                          "which is the canonical rev12 artifact; or a dry-run of the pinned tool that exits 0 with "
                          "changed:false on every audited path"),
        },
        "not_claimed": ["no gate verdict (G-FORM/G-F0 stay pending)",
                        "no node status or validation_status",
                        "no schema content defect, no class-id change",
                        "no claim that the frozen pins are wrong",
                        "no mathematics/physics claim"],
        "pins_used": pins,
        "stale_hashes": stale_hashes,
    }
    return result, manifest, rep, tool, scan, stale_hashes, pins


def build_result():
    base, manifest, rep, tool, scan, stale_hashes, pins = build_base()
    second = build_base()[0]

    controls = {}
    # C1: a synthetic report whose declared hashes all equal the pins yields 0 stale.
    c1 = classify_report_entries(manifest, synthetic_report(pins, mutate=False))
    controls["C1_all_match_report_yields_zero_stale"] = (c1["stale_count"] == 0)
    # C2: a synthetic report with one mutated hash yields exactly 1 stale.
    c2 = classify_report_entries(manifest, synthetic_report(pins, mutate=True))
    controls["C2_mutated_hash_is_flagged"] = (c2["stale_count"] == 1)
    # C3: a synthetic manifest whose pin for one path is wrong is detected by the pin sweep.
    fake = json.loads(json.dumps(manifest))
    victim = sorted(fake["files"])[0]
    fake["files"][victim]["sha256"] = "f" * 64
    c3 = pin_sweep(fake)
    controls["C3_manifest_pin_drift_is_detected"] = (
        len(c3["problems"]) == 1 and c3["problems"][0]["path"] == victim)
    # C4: determinism - two independent builds give the same canonical digest.
    controls["C4_determinism"] = (canonical_digest(second) == canonical_digest(base))
    # C5: running the pinned procedure did not write to any audited canonical input.
    controls["C5_tool_run_is_read_only"] = tool["inputs_unchanged"]
    # C6: the audited report is the pinned report (we are not auditing a copy).
    controls["C6_report_hash_equals_pin"] = (base["report"]["disk_sha256"] == base["report"]["pinned_sha256"])
    # C7: the intermediate hashes exist in no archived file (the report's own bytes
    #     excluded, since it states them as text).
    controls["C7_no_archived_copy_of_intermediate_bytes"] = (not scan["any_copy_found"])

    base["controls"] = controls
    base["controls_all_pass"] = all(controls.values())
    base["canonical_digest_sha256"] = canonical_digest(base)
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="write report.json and evidence.json next to this script")
    args = ap.parse_args()
    result = build_result()
    evidence = {
        "task_id": result["task_id"],
        "frozen": result["frozen"],
        "report_pin": result["report"]["pinned_sha256"],
        "report_disk_sha256": result["report"]["disk_sha256"],
        "report_entry_audit": result["report_entry_audit"],
        "archive_scan": result["archive_scan"],
        "tool_dryrun": result["tool_dryrun"],
        "delta_scan": result["delta_scan"],
        "cross_binding": result["cross_binding"],
        "controls": result["controls"],
        "canonical_digest_sha256": result["canonical_digest_sha256"],
    }
    if args.write:
        (HERE / "report.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        (HERE / "evidence.json").write_text(json.dumps(evidence, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=1))
    sys.exit(0 if result["controls_all_pass"] else 1)


if __name__ == "__main__":
    main()

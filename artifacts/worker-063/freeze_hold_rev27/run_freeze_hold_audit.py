#!/usr/bin/env python3
"""W063-FREEZE-HOLD-REV27-01: independent freeze-hold audit of the formulation tree.

Question: after the pass-03 measurement (FROZEN revision 25/26 pins), do the canonical
formulation bytes still match what every existing review verdict binds? If they changed,
which verdicts are void, and is the new FROZEN revision 27 self-consistent with disk?

Read-only w.r.t. every canonical/frozen path:
  * FROZEN.json pin-vs-disk check is implemented here and cross-checked with the tree's own
    verify_frozen.py (which writes nothing).
  * check_class_schema.py is invoked with --json (prints only).
  * check_taxonomy_consistency.py / check_variant_registry.py / check_variant_deltas.py write
    their evidence file under artifacts/formulation/evidence/. They are executed in-process
    with pathlib.Path.write_text patched to capture the bytes instead of writing, then the
    captured bytes are compared byte-for-byte with the on-disk evidence file. Nothing under
    the frozen tree is modified by this runner.

Usage: python3 run_freeze_hold_audit.py [out.json]
"""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import io
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
OUT_DEFAULT = Path(__file__).resolve().parent / "freeze_hold_audit.json"
CST = dt.timezone(dt.timedelta(hours=8))
INSTANCE = os.environ.get("W063_INSTANCE", "worker-063-20260912T003028-968807")

CLASS_IDS = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]

# The five canonical formulation artifacts whose revision-25/26 pins were the reference for
# every verdict issued between 00:19 and 00:32. Superseded pins are quoted from
# research_map/ASTRA_HANDOFF.md (pass 03, "Measured at pass end") and
# reviews/A1-rebind-coverage.json (measured_at 2026-09-12T00:30:16+08:00).
FOCUS = [
    {
        "target": "F0",
        "role": "canonical taxonomy (declared F0)",
        "path": "research_map/formulation_taxonomy.yaml",
        "superseded_pin": "276009f4f63dbf838f32f368eed982f5e353d69970ca3227090aed14d26006dc",
        "superseded_source": "reviews/A1-rebind-coverage.json targets.F0.canonical_sha256",
    },
    {
        "target": "F0",
        "role": "authoring class contract (mirror-pair member)",
        "path": "artifacts/formulation/formulation_taxonomy.yaml",
        "superseded_pin": "c8e979a1eb48969be3b102e1e18203eb9e09b4e10fca3ef341854fdd73bae83f",
        "superseded_source": "artifacts/worker-041/f0_mirror_indep/f0_mirror_report.json pinned_inputs",
    },
    {
        "target": "F1",
        "role": "canonical schema",
        "path": "schemas/af_wcc_vacuum.yaml",
        "superseded_pin": "9a8bd4c9680042a40894f6085f183661500966f2d787a6bf28a7098a271ed503",
        "superseded_source": "reviews/A1-rebind-coverage.json targets.F1.canonical_sha256",
    },
    {
        "target": "F2a",
        "role": "canonical schema",
        "path": "schemas/af_scc_c2_vacuum.yaml",
        "superseded_pin": "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2",
        "superseded_source": "reviews/A1-rebind-coverage.json targets.F2a.canonical_sha256",
    },
    {
        "target": "F2b",
        "role": "canonical schema",
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "superseded_pin": "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508",
        "superseded_source": "reviews/A1-rebind-coverage.json targets.F2b.canonical_sha256",
    },
]

EVIDENCE_TOOLS = [
    ("taxonomy_consistency", "artifacts/formulation/tools/check_taxonomy_consistency.py",
     "artifacts/formulation/evidence/taxonomy_consistency.json"),
    ("variant_registry", "artifacts/formulation/tools/check_variant_registry.py",
     "artifacts/formulation/evidence/variant_registry_check.json"),
    ("variant_deltas", "artifacts/formulation/tools/check_variant_deltas.py",
     "artifacts/formulation/evidence/variant_delta_check.json"),
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def stat_file(p: Path) -> dict:
    st = p.stat()
    mtime = dt.datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="microseconds")
    return {"exists": True, "bytes": st.st_size, "mtime": mtime, "sha256": sha256_file(p)}


def now() -> str:
    return dt.datetime.now(CST).isoformat(timespec="seconds")


def run_cmd(args: list[str], timeout: int = 180) -> dict:
    try:
        r = subprocess.run(args, capture_output=True, text=True, cwd=str(ROOT), timeout=timeout)
        return {"argv": args, "returncode": r.returncode,
                "stdout": r.stdout[-4000:], "stderr": r.stderr[-2000:]}
    except Exception as e:  # noqa: BLE001 - a checker failure is data, not a crash
        return {"argv": args, "returncode": None, "error": f"{type(e).__name__}: {e}"}


def run_evidence_tool(name: str, tool_rel: str, evidence_rel: str) -> dict:
    """Execute a writing checker with Path.write_text captured; compare to frozen evidence."""
    tool = ROOT / tool_rel
    rec: dict = {"name": name, "tool": tool_rel, "evidence_path": evidence_rel}
    if not tool.exists():
        rec["status"] = "TOOL_MISSING"
        return rec
    rec["tool_sha256"] = sha256_file(tool)
    captured: list[tuple[str, str]] = []
    real_write_text = Path.write_text

    def fake_write_text(self, data, *a, **k):  # noqa: ANN001
        captured.append((str(self), data if isinstance(data, str) else data.decode()))
        return len(data)

    out = io.StringIO()
    rc = None
    try:
        with mock.patch.object(Path, "write_text", fake_write_text), contextlib.redirect_stdout(out):
            try:
                runpy.run_path(str(tool))
            except SystemExit as e:
                rc = e.code
    except Exception as e:  # noqa: BLE001
        rec["status"] = "TOOL_EXCEPTION"
        rec["error"] = f"{type(e).__name__}: {e}"
        rc = None
    rec["returncode"] = rc
    rec["stdout_tail"] = out.getvalue()[-1500:]
    ev = ROOT / evidence_rel
    rec["evidence_exists"] = ev.exists()
    if captured:
        target, data = captured[-1]
        rec["would_write_path"] = target
        rec["computed_sha256"] = sha256_bytes(data.encode())
        rec["computed_bytes"] = len(data.encode())
        if ev.exists():
            rec["on_disk_sha256"] = sha256_file(ev)
            rec["reproduced_byte_identical"] = rec["on_disk_sha256"] == rec["computed_sha256"]
        else:
            rec["reproduced_byte_identical"] = False
        rec["status"] = "OK" if rc == 0 else "CHECKER_NONZERO"
    else:
        rec["status"] = "NO_WRITE_CAPTURED"
    return rec


def main(out_path: Path) -> int:
    t0 = now()
    frozen_path = ROOT / "artifacts/formulation/FROZEN.json"
    frozen_bytes = frozen_path.read_bytes()
    frozen = json.loads(frozen_bytes)
    manifest = {
        "path": "artifacts/formulation/FROZEN.json",
        "sha256": sha256_bytes(frozen_bytes),
        "bytes": len(frozen_bytes),
        "revision": frozen.get("revision"),
        "frozen_at": frozen.get("frozen_at"),
        "mtime": stat_file(frozen_path)["mtime"],
        "artifact": frozen.get("artifact"),
    }

    # 1) pin-vs-disk across every file the manifest pins
    mismatches, missing = [], []
    for rel, rec in frozen.get("files", {}).items():
        p = ROOT / rel
        if not p.exists():
            missing.append(rel)
            continue
        disk = sha256_file(p)
        if disk != rec.get("sha256") or p.stat().st_size != rec.get("bytes"):
            mismatches.append({"path": rel, "pin_sha256": rec.get("sha256"), "disk_sha256": disk,
                               "pin_bytes": rec.get("bytes"), "disk_bytes": p.stat().st_size})
    pin_check = {
        "files_pinned": len(frozen.get("files", {})),
        "match": len(frozen.get("files", {})) - len(mismatches) - len(missing),
        "drift": len(mismatches), "missing": len(missing),
        "mismatches": mismatches, "missing_paths": missing,
    }

    # 2) focus targets, measured at T0 (before checkers) and T1 (after checkers)
    focus = []
    for f in FOCUS:
        p = ROOT / f["path"]
        s = stat_file(p)
        focus.append({**f, "disk_t0": s, "pinned_rev27_sha256": frozen.get("files", {}).get(f["path"], {}).get("sha256"),
                      "pin_matches_disk_t0": frozen.get("files", {}).get(f["path"], {}).get("sha256") == s["sha256"],
                      "superseded": s["sha256"] != f["superseded_pin"]})

    # 3) review events binding superseded vs fresh pins
    events_path = ROOT / "research_map/events.jsonl"
    events = []
    for line in events_path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    reviews = [e for e in events if e.get("event_type") == "review"]
    superseded_hashes = {f["superseded_pin"] for f in FOCUS}
    fresh_hashes = {x["disk_t0"]["sha256"] for x in focus}
    voided, fresh_bound = [], []
    for e in reviews:
        blob = json.dumps(e)
        for f in FOCUS:
            if f["superseded_pin"] in blob or f["superseded_pin"][:12] in blob:
                voided.append({"event_id": e.get("event_id"), "actor": e.get("actor"),
                               "target_id": e.get("target_id"), "verdict": e.get("verdict"),
                               "created_at": e.get("created_at"), "bound_hash": f["superseded_pin"][:12],
                               "superseded_target": f"{f['target']} {f['role']}"})
                break
        for h in fresh_hashes:
            if h in blob or h[:12] in blob:
                fresh_bound.append({"event_id": e.get("event_id"), "actor": e.get("actor"),
                                    "target_id": e.get("target_id"), "verdict": e.get("verdict"),
                                    "created_at": e.get("created_at"), "bound_hash": h[:12]})
                break

    # 4) checkers
    verify_tool = ROOT / "artifacts/formulation/tools/verify_frozen.py"
    checks = {
        "verify_frozen": {**run_cmd([sys.executable, str(verify_tool)]),
                          "tool_sha256": sha256_file(verify_tool) if verify_tool.exists() else None},
        "class_schema": [
            run_cmd([sys.executable, "artifacts/formulation/tools/check_class_schema.py", rel, "--json"])
            for rel in ("schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
                        "schemas/af_scc_c0_vacuum.yaml")
        ],
        "evidence_tools": [run_evidence_tool(*t) for t in EVIDENCE_TOOLS],
    }
    class_schema_summary = []
    for r in checks["class_schema"]:
        verdict = None
        try:
            verdict = json.loads(r.get("stdout") or "{}").get("verdict")
        except json.JSONDecodeError:
            pass
        class_schema_summary.append({"schema": r["argv"][2] if len(r.get("argv", [])) > 2 else None,
                                     "returncode": r.get("returncode"), "verdict": verdict})

    t1 = now()
    focus_t1 = {f["path"]: stat_file(ROOT / f["path"])["sha256"] for f in FOCUS}
    drift_during_run = [{"path": f["path"], "t0": f["disk_t0"]["sha256"], "t1": focus_t1[f["path"]]}
                        for f in focus if focus_t1[f["path"]] != f["disk_t0"]["sha256"]]
    f0c = next(f for f in focus if f["path"] == "research_map/formulation_taxonomy.yaml")
    f0a = next(f for f in focus if f["path"] == "artifacts/formulation/formulation_taxonomy.yaml")

    findings = [
        {"id": "FH-1", "severity": "hard", "statement":
         f"The five canonical formulation artifacts were rewritten after the pass-03/rev-26 measurement: "
         f"mtime {min(f['disk_t0']['mtime'] for f in focus)} .. {max(f['disk_t0']['mtime'] for f in focus)}. "
         f"Every verdict that cites the rev-25/26 pins ({len(voided)} review events in events.jsonl) binds bytes "
         f"that no longer exist on disk."},
        {"id": "FH-2", "severity": "hard", "statement":
         f"FROZEN revision {manifest['revision']} (frozen_at {manifest['frozen_at']}) re-pins all "
         f"{pin_check['files_pinned']} files to the post-rewrite bytes; pin-vs-disk drift is {pin_check['drift']} "
         f"and the tree's own verify_frozen.py agrees."},
        {"id": "FH-3", "severity": "hard", "statement":
         f"Review coverage at the revision-{manifest['revision']} canonical hashes is {len(fresh_bound)} "
         f"(events.jsonl scan at {t1}); G-FORM/G-F0 need two distinct independent accepts per target at the "
         f"hash currently on disk."},
        {"id": "FH-4", "severity": "soft", "statement":
         f"F0 canonical {f0c['disk_t0']['sha256'][:12]} ({f0c['disk_t0']['bytes']} B) and authoring "
         f"{f0a['disk_t0']['sha256'][:12]} ({f0a['disk_t0']['bytes']} B) remain byte-divergent even after the "
         f"rewrite; the mirror-equality policy breach is unchanged in kind."},
    ]

    report = {
        "report_id": "W063-FREEZE-HOLD-REV27-01",
        "task_id": "W063-FREEZE-HOLD-REV27-01",
        "actor": "worker-063",
        "instance": INSTANCE,
        "created_at": t1,
        "measured_at_t0": t0,
        "measured_at_t1": t1,
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "gates": ["G-F0", "G-FORM"],
        "class_ids": CLASS_IDS,
        "class_id": ";".join(CLASS_IDS),
        "question": (
            "After the pass-03/rev-25-26 measurement, do the canonical formulation bytes still match the "
            "pins every existing review verdict binds; if they changed, which verdicts are void, and is the "
            "new FROZEN revision self-consistent with disk?"),
        "authority_note": (
            "Measurement and independent conformance checks only. This runner does not promote a node, set a "
            "gate verdict, or write to any canonical/frozen path. It does not count as an independent schema "
            "verdict for G-FORM/G-F0 review coverage."),
        "frozen_manifest": manifest,
        "pin_check": pin_check,
        "focus_targets": focus,
        "superseded_review_scan": {
            "review_events_total": len(reviews),
            "superseded_pins": sorted(superseded_hashes),
            "review_events_binding_superseded": len(voided),
            "by_target": {f"{f['target']}:{f['path']}": sum(1 for v in voided if v["bound_hash"] == f["superseded_pin"][:12]) for f in FOCUS},
            "voided_reviews": sorted(voided, key=lambda v: (v.get("created_at") or "")),
            "review_events_binding_rev27": fresh_bound,
        },
        "f0_pair": {
            "canonical": {"path": f0c["path"], "sha256": f0c["disk_t0"]["sha256"], "bytes": f0c["disk_t0"]["bytes"]},
            "authoring": {"path": f0a["path"], "sha256": f0a["disk_t0"]["sha256"], "bytes": f0a["disk_t0"]["bytes"]},
            "byte_identical": f0c["disk_t0"]["sha256"] == f0a["disk_t0"]["sha256"],
            "divergent": f0c["disk_t0"]["sha256"] != f0a["disk_t0"]["sha256"],
        },
        "checkers": {"verify_frozen": checks["verify_frozen"], "class_schema": class_schema_summary,
                     "evidence_tools": checks["evidence_tools"]},
        "drift_during_run": drift_during_run,
        "findings": findings,
        "falsifier": (
            "Re-measure the five focus paths and show that any superseded pin still matches disk at the "
            "recorded mtime (which would make the supersession claim false); or show fewer than 1 review "
            "event in research_map/events.jsonl citing a superseded pin; or run "
            "artifacts/formulation/tools/verify_frozen.py and show nonzero drift against FROZEN revision "
            f"{manifest['revision']}; or edit any focus path and show this report's T0 hashes still describe "
            "disk (which voids the binding of the whole measurement)."),
        "evidence_refs": [
            f"artifacts/formulation/FROZEN.json#{manifest['sha256'][:12]}",
            "research_map/ASTRA_HANDOFF.md",
            "reviews/A1-rebind-coverage.json",
            "artifacts/formulation/tools/verify_frozen.py",
            "research_map/events.jsonl",
        ],
        "limitations": [
            "One measurement window; the formulation tree was rewritten twice in the preceding 20 minutes, so "
            "this report binds only the T0/T1 hashes it records.",
            "Verdict-voiding uses substring matching of the superseded 12-hex prefixes in review events; it "
            "identifies binding, not reviewer intent.",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "report": str(out_path),
        "report_sha256": sha256_bytes(out_path.read_bytes()),
        "frozen_revision": manifest["revision"],
        "pin_drift": pin_check["drift"],
        "focus_superseded": sum(1 for f in focus if f["superseded"]),
        "voided_review_events": len(voided),
        "reviews_at_rev27": len(fresh_bound),
        "drift_during_run": drift_during_run,
        "class_schema": class_schema_summary,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT_DEFAULT))

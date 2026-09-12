#!/usr/bin/env python3
"""W078-F2A-INDEP-VERIFY-01 -- independent, hash-bound verification of canonical
F2a AF-SCC-C2-VAC-GEN (schemas/af_scc_c2_vacuum.yaml).

Why this shape:
  * The gate audit counts "distinct accept reviewer(s)" ONLY when a verdict is bound to the
    measured canonical sha256. The canonical tree was being republished while this ran, so a
    path-only verdict is worthless. This tool pins bytes, verifies the pinned bytes, then
    re-measures the live path: if the live hash moved, the binding is VOIDED (verdict stays
    advisory) rather than silently rebinding to different bytes.
  * Nothing here decides a gate. It emits machine evidence for a controller/lead verdict.

Run:
  python3 artifacts/worker-078/f2a_indep_verify/verify_f2a.py            # poll for stability, verify
  python3 artifacts/worker-078/f2a_indep_verify/verify_f2a.py --pin <hash>   # verify a pinned revision
Exit codes: 0 = all checks pass and binding held; 1 = a check failed; 2 = drift voided binding.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CLASS_ID = "AF-SCC-C2-VAC-GEN"
NODE_ID = "F2a"
CANON = ROOT / "schemas/af_scc_c2_vacuum.yaml"
MIRROR = ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"
TAXONOMY = ROOT / "research_map/formulation_taxonomy.yaml"
STRUCTURAL_GATE = ROOT / "artifacts/formulation/tools/check_class_schema.py"
TAXCONS = ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"
CLASSSEP_REG = ROOT / "runtime/bin/classsep_regression.py"
HERE = Path(__file__).resolve().parent
SNAP_DIR = HERE / "snapshot"

REQUIRED = [
    "schema_version", "artifact_kind", "class_id", "node_id", "revision",
    "scope_statement", "quantifiers", "class_boundary", "conventions",
    "extension_predicate", "topology", "data_class", "regularity", "genericity",
    "non_vacuity", "i_plus", "visibility", "conclusion", "implication_ledger",
    "falsifier", "anti_scope", "provenance",
]


def now() -> str:
    return _dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def measure(p: Path) -> dict:
    try:
        b = p.read_bytes()
    except FileNotFoundError:
        return {"path": str(p.relative_to(ROOT)), "sha256": None, "bytes": None, "exists": False}
    st = p.stat()
    return {
        "path": str(p.relative_to(ROOT)),
        "sha256": sha256_bytes(b),
        "bytes": len(b),
        "mtime_ns": st.st_mtime_ns,
        "exists": True,
    }


def watch_stable(p: Path, stable_secs: int, max_wait: int, pin: str | None) -> list[dict]:
    """Poll until the file hash is unchanged for stable_secs, or max_wait elapses.
    Returns the drift log (timestamped measurements)."""
    log: list[dict] = []
    t0 = time.time()
    last_hash, last_change = None, time.time()
    while True:
        m = measure(p)
        m["at"] = now()
        if not log or m["sha256"] != log[-1]["sha256"]:
            log.append(m)
            last_change = time.time()
        last_hash = m["sha256"]
        if pin:
            break
        if last_hash is not None and time.time() - last_change >= stable_secs:
            break
        if time.time() - t0 >= max_wait:
            break
        time.sleep(min(5, max(1, stable_secs // 6)))
    return log


def run(cmd: list[str]) -> dict:
    pr = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
    return {"cmd": cmd, "exit_code": pr.returncode,
            "stdout": pr.stdout[-8000:], "stderr": pr.stderr[-2000:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pin", default=None, help="verify exactly this sha256 revision")
    ap.add_argument("--stable-secs", type=int, default=30)
    ap.add_argument("--max-wait", type=int, default=240)
    ap.add_argument("--out", default=str(HERE / "report.json"))
    a = ap.parse_args()

    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []
    drift = watch_stable(CANON, a.stable_secs, a.max_wait, a.pin)

    def add(cid, desc, status, evidence, falsifier=None):
        checks.append({"check_id": cid, "description": desc, "status": status,
                       "evidence": evidence, "falsifier": falsifier})

    # ---- snapshot -------------------------------------------------------
    if not CANON.exists():
        add("V01_SNAPSHOT", "canonical file exists and is snapshotted byte-exactly", "fail",
            {"path": str(CANON)})
        return finish(a, checks, drift, None, None)
    blob = CANON.read_bytes()
    snap_hash = sha256_bytes(blob)
    if a.pin and snap_hash != a.pin:
        # pinned revision no longer on the canonical path: try the saved snapshot
        cand = sorted(SNAP_DIR.glob("af_scc_c2_vacuum.*.yaml"))
        hit = [c for c in cand if sha256_file(c) == a.pin]
        if not hit:
            add("V01_SNAPSHOT", f"pinned revision {a.pin[:12]} resolvable", "fail",
                {"canonical_sha256": snap_hash, "snapshots": [c.name for c in cand]})
            return finish(a, checks, drift, None, None)
        blob = hit[0].read_bytes()
        snap_hash = sha256_bytes(blob)
    snap = SNAP_DIR / f"af_scc_c2_vacuum.{snap_hash[:12]}.yaml"
    if not snap.exists():
        snap.write_bytes(blob)
    add("V01_SNAPSHOT", "canonical bytes pinned to an immutable snapshot",
        "pass", {"snapshot": str(snap.relative_to(ROOT)), "sha256": snap_hash,
                 "bytes": len(blob), "live_measurements": len(drift)})

    text = blob.decode("utf-8", errors="replace")
    try:
        import yaml
        doc = yaml.safe_load(blob)
        assert isinstance(doc, dict)
    except Exception as e:  # noqa: BLE001
        add("V02_PARSE", "snapshot parses as a YAML mapping", "fail", {"error": repr(e)})
        return finish(a, checks, drift, snap_hash, blob)
    add("V02_PARSE", "snapshot parses as a YAML mapping", "pass",
        {"top_level_keys": len(doc)})

    # ---- V03 identity ---------------------------------------------------
    ident = {"class_id": doc.get("class_id"), "node_id": doc.get("node_id"),
             "artifact_kind": doc.get("artifact_kind")}
    ok = (doc.get("class_id") == CLASS_ID and doc.get("node_id") == NODE_ID
          and doc.get("artifact_kind") == "class_schema")
    add("V03_IDENTITY", "class_id/node_id/artifact_kind match F2a AF-SCC-C2-VAC-GEN",
        "pass" if ok else "fail", ident)

    # ---- V04 contract fields -------------------------------------------
    missing = [k for k in REQUIRED if k not in doc or doc[k] in (None, "", [], {})]
    concl = doc.get("conclusion") or {}
    ctype = concl.get("conclusion_type") if isinstance(concl, dict) else None
    add("V04_CONTRACT_FIELDS", "required class-contract fields present and non-empty",
        "pass" if not missing and ctype else "fail",
        {"missing": missing, "conclusion_type": ctype,
         "epistemic_status": doc.get("epistemic_status")})

    # ---- V05 no C0/C2 merge --------------------------------------------
    comps = doc.get("class_components") or {}
    anti = doc.get("anti_scope") or {}
    not_this = [x.get("class_id") for x in (anti.get("not_this_class") or [])
                if isinstance(x, dict)]
    merge_ok = (comps.get("regularity_token") == "C2"
                and "AF-SCC-C0-VAC-GEN" in not_this
                and doc.get("sibling_disjoint_from") == "AF-SCC-C0-VAC-GEN")
    add("V05_NO_C0_C2_MERGE",
        "C2 regularity token; C0 named as not-this-class; sibling disjointness declared",
        "pass" if merge_ok else "fail",
        {"regularity_token": comps.get("regularity_token"),
         "not_this_class": not_this, "sibling_disjoint_from": doc.get("sibling_disjoint_from")},
        falsifier="a statement in the schema asserting one composite C0/C2 class, or "
                  "sibling_disjoint_from missing/equal to this class.")

    # ---- V06 authoring mirror ------------------------------------------
    mir = measure(MIRROR)
    add("V06_CANONICAL_MIRROR", "authoring mirror is byte-identical to canonical (publication)",
        "pass" if mir["sha256"] == snap_hash else "fail",
        {"canonical_sha256": snap_hash, "mirror": mir},
        falsifier="mirror sha256 != canonical sha256 at the same instant.")

    # ---- V07 structural gate -------------------------------------------
    sg = run([sys.executable, str(STRUCTURAL_GATE), str(snap), "--json"])
    try:
        sg_json = json.loads(sg["stdout"])
    except Exception:  # noqa: BLE001
        sg_json = None
    sg_pass = bool(sg_json and sg_json.get("verdict") == "pass"
                   and not sg_json.get("failed_rules"))
    add("V07_STRUCTURAL_GATE",
        "frozen structural gate check_class_schema.py passes the pinned bytes",
        "pass" if sg_pass else "fail",
        {"gate_sha256": sha256_file(STRUCTURAL_GATE), "result": sg_json or sg["stdout"][:500],
         "exit_code": sg["exit_code"]},
        falsifier="gate verdict != pass or non-empty failed_rules on these exact bytes.")

    # ---- V08 class-separation on pinned text ---------------------------
    sys.path.insert(0, str(ROOT / "research_map"))
    import class_separation as cs  # noqa: E402
    findings = cs.findings_for_text(text, "worker-078 pinned F2a")
    add("V08_CLASSSEP_TEXT", "class-separation checker finds no composite-class declaration",
        "pass" if not findings else "fail",
        {"checker_sha256": sha256_file(ROOT / "research_map/class_separation.py"),
         "findings": findings[:10]},
        falsifier="any finding on these exact bytes.")

    # ---- V09 frozen classsep regression --------------------------------
    reg = run([sys.executable, str(CLASSSEP_REG)])
    reg_ok = reg["exit_code"] == 0 and "PASS" in reg["stdout"]
    add("V09_CLASSSEP_REGRESSION", "frozen class-separation regression still PASS (17 leaks/10 controls)",
        "pass" if reg_ok else "fail",
        {"exit_code": reg["exit_code"], "tail": reg["stdout"][-400:]})

    # ---- V10 F0 binding -------------------------------------------------
    tax = measure(TAXONOMY)
    declared = (doc.get("f0_binding") or {}).get("declared_f0_sha256")
    tc = run([sys.executable, str(TAXCONS)])
    f0_ok = declared == tax["sha256"] and tc["exit_code"] == 0 and "CONSISTENT" in tc["stdout"]
    add("V10_F0_BINDING",
        "declared F0 hash equals live canonical taxonomy hash and consistency tool is CONSISTENT",
        "pass" if f0_ok else "fail",
        {"declared_f0_sha256": declared, "live_taxonomy": tax,
         "consistency_exit": tc["exit_code"], "consistency_out": tc["stdout"][-200:]},
        falsifier="declared F0 hash != research_map/formulation_taxonomy.yaml sha256, or "
                  "check_taxonomy_consistency.py exits non-zero.")

    # ---- V11 end-of-run drift / binding ---------------------------------
    end = measure(CANON)
    bound = end["sha256"] == snap_hash
    add("V11_HASH_BINDING",
        "canonical path still holds the pinned bytes at end of run (verdict may bind)",
        "pass" if bound else "fail",
        {"pinned_sha256": snap_hash, "end_sha256": end["sha256"],
         "drift_events": len(drift), "drift_log": drift},
        falsifier="end sha256 != pinned sha256; the review verdict is then advisory only.")

    return finish(a, checks, drift, snap_hash, blob)


def finish(a, checks, drift, snap_hash, blob) -> int:
    hard = [c for c in checks if c["status"] == "fail"]
    binding = next((c for c in checks if c["check_id"] == "V11_HASH_BINDING"), None)
    bound = bool(binding and binding["status"] == "pass")
    if blob is None:
        verdict, exit_code = "reject", 1
    elif not hard and bound:
        verdict, exit_code = "accept", 0
    elif hard and any(c["check_id"] in ("V03_IDENTITY", "V05_NO_C0_C2_MERGE") for c in hard):
        verdict, exit_code = "revise", 1
    elif not bound:
        verdict, exit_code = "inconclusive-drift", 2
    else:
        verdict, exit_code = "revise", 1
    report = {
        "report_id": "W078-F2A-INDEP-VERIFY-01",
        "worker": "worker-078",
        "class_id": CLASS_ID,
        "node_id": NODE_ID,
        "generated_at": now(),
        "canonical_path": "schemas/af_scc_c2_vacuum.yaml",
        "snapshot_sha256": snap_hash,
        "verdict": verdict,
        "verdict_bound_to_snapshot": bound,
        "binding_note": ("verdict binds to snapshot_sha256" if bound else
                         "canonical bytes moved during the run; verdict is ADVISORY for "
                         "snapshot_sha256 and MUST NOT be counted as an accept at the live hash"),
        "checks": checks,
        "drift_log": drift,
        "limits": [
            "Structural/contract verification only: decides shape and declared bindings, not "
            "mathematical truth, non-vacuity, or physical correctness (matches ADJ-SEM-3).",
            "A YAML comment is invisible to any parser; this tool does not attempt comment-level "
            "leak detection.",
            "The structural gate and the class-separation checker are pre-existing repo tools; "
            "their hashes are recorded so a revision change invalidates this report.",
            "This report sets no gate verdict and claims no node completion.",
        ],
        "falsifiers": [
            "Re-run on the same snapshot_sha256 returning any failed check (test-retest).",
            "Gate or checker sha256 changing; the report is invalid for the new revision.",
            "A schematic leak that the frozen gates miss and a named reviewer exhibits on the "
            "pinned bytes (this tool cannot certify absence of every semantic leak).",
        ],
        "reproduce": f"python3 artifacts/worker-078/f2a_indep_verify/verify_f2a.py --pin {snap_hash}",
    }
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"verdict": verdict, "snapshot_sha256": snap_hash,
                      "bound": bound, "failed": [c["check_id"] for c in hard],
                      "report": str(out)}, indent=1))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

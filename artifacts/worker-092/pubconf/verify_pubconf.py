#!/usr/bin/env python3
"""W092-PUBCONF-01 -- hash-pinned publication and class-binding verification.

Class-bound: AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN (+ shared F0 class contract).
Node: F1/F2a/F2b (gate G-FORM), F0 (gate G-F0).  Authority: measurement only -- this tool does
not set a gate verdict, does not edit the map, and does not touch the artifacts it measures.

Why this exists
---------------
`leadform-blocker-0005` (astra-lead-formulation outbox) asked for an independent reviewer to
re-run `check_class_schema.py` and `run_acceptance.py` against the "final" schema hashes and to
bind the canonical F0 taxonomy.  The canonical paths were rewritten again at 00:18:26-00:19:14
while that request was being written, so every hash named in the request was already superseded.
This tool therefore verifies a *snapshot*, not a path: it copies the bytes it measures into
`pinned_run/`, hashes the copies, and binds every verdict to those hashes.  A late live re-hash
detects and reports any write that lands during the run instead of hiding it.

Checks
------
H1 canonical == authoring byte identity for the four publication pairs (policy: one frozen
   revision per artifact, canonical authoritative).
H2 FROZEN.json declared sha256 equals the measured snapshot sha256 for every pinned file.
H3 canonical gate `check_class_schema.py` (pinned tool copy) returns verdict=pass on each schema.
H4 `research_map/class_separation.py` (pinned copy) reports no findings on each schema.
H5 class binding: class_id is one of the four frozen ids, is present in the canonical taxonomy
   class set, and the declared sibling exists and names this class back.
H6 `class_contract_pointer` dereferences in the tree the pointer names, and we record whether the
   canonical taxonomy can dereference the same key.
H7 `f0_binding.declared_f0_sha256` equals the canonical taxonomy snapshot sha256.
H8 `class_components` concatenation reproduces `class_id`.
S1 cross-tool: `verify_frozen.py` exit code (live paths; hashes before/after recorded).
S2 cross-tool: `check_taxonomy_consistency.py` exit code (live paths).
S3 blocker-hash staleness: hashes named in leadform-blocker-0005 vs snapshot.
S4 live drift during the run: canonical paths re-hashed after all checks.
S5 clock sanity: FROZEN `frozen_at` versus FROZEN mtime.

Hard checks are H1-H7; S1-S5 and H8 are reported as evidence/findings, not as the verdict.
Falsifier: re-run this tool against the same `pinned_run/` copies.  The report is falsified if
any hard check that passed here fails on the pinned copies, or if a check recorded as failed
passes on them.

Usage:
  python3 artifacts/worker-092/pubconf/verify_pubconf.py [--root .] [--out-dir <dir>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

FROZEN_FOUR = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
PAIRS = [
    ("F0", "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
     "research_map/formulation_taxonomy.yaml",
     "artifacts/formulation/formulation_taxonomy.yaml"),
    ("F1", "AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml",
     "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
    ("F2a", "AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml",
     "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    ("F2b", "AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml",
     "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
]
TOOLS = {
    "gate": "artifacts/formulation/tools/check_class_schema.py",
    "acceptance": "artifacts/formulation/tools/run_acceptance.py",
    "verify_frozen": "artifacts/formulation/tools/verify_frozen.py",
    "taxonomy_consistency": "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "class_separation": "research_map/class_separation.py",
}
BLOCKER = "comms/outbox/astra-lead-formulation.jsonl"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load_yaml(p: Path):
    import yaml  # PyYAML is present in the task environment
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def pin(root: Path, pinned: Path, rel: str) -> dict:
    src = root / rel
    rec: dict = {"path": rel, "exists": src.exists()}
    if not src.exists():
        return rec
    dst = pinned / rel.replace("/", "__")
    shutil.copy2(src, dst)
    st = src.stat()
    rec.update({
        "sha256": sha256_file(src),
        "pinned_copy": str(dst.relative_to(root)),
        "pinned_copy_sha256": sha256_file(dst),
        "bytes": st.st_size,
        "mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(st.st_mtime)),
    })
    return rec


def resolve_pointer(doc, dotted: str):
    cur = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out-dir", default="artifacts/worker-092/pubconf")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out_dir = (root / args.out_dir).resolve()
    pinned = out_dir / "pinned_run"
    pinned.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "schema_version": "0.1",
        "artifact_kind": "publication_binding_verification",
        "task_id": "W092-PUBCONF-01",
        "actor": "worker-092",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_ids": ["F0", "F1", "F2a", "F2b"],
        "gate_scope": ["G-F0", "G-FORM"],
        "generated_at": now(),
        "authority": {
            "measurement_only": True,
            "sets_gate_verdict": False,
            "edits_shared_artifacts": False,
        },
        "checks": [],
        "findings": [],
        "limits": [
            "Binds to the pinned_run/ copies and their sha256, never to a path alone.",
            "Does not judge mathematical content, only hash identity, dereferenceability, and "
            "the two project gates' machine verdicts.",
            "A live re-hash after the checks records any concurrent write; a mid-run write makes "
            "the affected check valid for the pinned copy only.",
        ],
        "falsifier": (
            "Re-run verify_pubconf.py against the same pinned_run/ copies: the report is falsified "
            "if a hard check recorded pass fails on those copies, or a hard check recorded fail "
            "passes on them."
        ),
    }

    def check(cid: str, hard: bool, desc: str, expected, observed, verdict: str):
        report["checks"].append({
            "id": cid,
            "hard": hard,
            "description": desc,
            "expected": expected,
            "observed": observed,
            "verdict": verdict,
        })

    # ---- snapshot -----------------------------------------------------------
    snap: dict = {"captured_at": now(), "files": {}}
    for rel in [p[2] for p in PAIRS] + [p[3] for p in PAIRS] + list(TOOLS.values()) + [BLOCKER,
                "artifacts/formulation/FROZEN.json"]:
        if rel not in snap["files"]:
            snap["files"][rel] = pin(root, pinned, rel)
    report["snapshot"] = snap
    f = snap["files"]

    # ---- integrity of the pinned copies -------------------------------------
    bad_pins = []
    for rel, rec in sorted(f.items()):
        if rec.get("exists") and rec.get("pinned_copy_sha256") != sha256_file(root / rec["pinned_copy"]):
            bad_pins.append(rel)
    check("H0", True, "pinned copies hash to their recorded sha256", [], bad_pins,
          "pass" if not bad_pins else "fail")

    # ---- H1 canonical == authoring ------------------------------------------
    for node, cls, canon, auth in PAIRS:
        rc, ra = f[canon], f[auth]
        same = rc.get("sha256") == ra.get("sha256")
        check(f"H1-{node}", True, f"{node}: canonical == authoring bytes ({cls})",
              {"canonical": rc.get("sha256"), "authoring": ra.get("sha256")},
              {"equal": same}, "pass" if same else "fail")
        if not same:
            report["findings"].append({
                "id": f"W092-H1-{node}", "severity": "major",
                "statement": (f"{node} publication pair is not byte-identical: canonical "
                              f"{rc.get('sha256','')[:16]} vs authoring {ra.get('sha256','')[:16]}; "
                              "one frozen revision per artifact requires them equal."),
                "class_id": cls,
                "falsifier": "Re-hash both paths; falsified if they are byte-identical.",
            })

    # ---- H2 FROZEN pins ------------------------------------------------------
    frozen_rel = "artifacts/formulation/FROZEN.json"
    frozen = load_yaml(root / frozen_rel) if f[frozen_rel].get("exists") else {}
    frozen_files = frozen.get("files", {}) if isinstance(frozen, dict) else {}
    drift = []
    for rel, rec in sorted(f.items()):
        if rel not in frozen_files:
            continue
        declared = frozen_files[rel]
        declared = declared.get("sha256") if isinstance(declared, dict) else declared
        if declared != rec.get("sha256"):
            drift.append({"path": rel, "frozen_declared": declared,
                          "snapshot_measured": rec.get("sha256")})
    check("H2", True, f"FROZEN rev{frozen.get('revision')} pins equal the measured snapshot",
          {"drift": 0}, {"checked": sum(1 for r in f if r in frozen_files), "drift": drift},
          "pass" if not drift else "fail")
    if drift:
        report["findings"].append({
            "id": "W092-H2", "severity": "major",
            "statement": (f"FROZEN rev{frozen.get('revision')} was stale against the measured "
                          f"publication for {len(drift)} file(s); 'frozen' did not denote the "
                          "bytes on disk at snapshot time."),
            "falsifier": "Re-run verify_frozen.py on the same bytes; falsified if it exits 0.",
        })

    # ---- H3 canonical gate on pinned schemas --------------------------------
    # The gate resolves its own support files relative to __file__, so it must run from its
    # live path; we require that live tool to be byte-identical to the pinned snapshot copy.
    gate_live = root / TOOLS["gate"]
    gate_pin_ok = sha256_file(gate_live) == f[TOOLS["gate"]].get("sha256") if gate_live.exists() else False
    for node, cls, canon, auth in PAIRS:
        if node == "F0":
            continue
        sp = root / f[canon]["pinned_copy"]
        proc = subprocess.run([sys.executable, str(gate_live), str(sp), "--json"],
                              capture_output=True, text=True, timeout=300)
        try:
            gj = json.loads(proc.stdout)
        except Exception:
            gj = {"verdict": f"unparseable(exit {proc.returncode})",
                  "stderr": proc.stderr.strip().splitlines()[-1:] }
        ok = gj.get("verdict") == "pass" and gate_pin_ok
        check(f"H3-{node}", True,
              f"{node}: check_class_schema.py verdict on pinned bytes (live tool == pinned tool)",
              {"verdict": "pass", "tool_sha_matches_pin": True},
              {"verdict": gj.get("verdict"), "class_id": gj.get("class_id"),
               "failed_rules": gj.get("failed_rules"), "tool_sha_matches_pin": gate_pin_ok,
               "tool_sha256": sha256_file(gate_live) if gate_live.exists() else None,
               "detail": gj.get("stderr") or gj.get("stdout")},
              "pass" if ok else "fail")

    # ---- H4 class separation on pinned schemas ------------------------------
    sys.path.insert(0, str(root / "research_map"))
    sep_pinned = root / f[TOOLS["class_separation"]]["pinned_copy"]
    spec = __import__("importlib.util", fromlist=["util"]).spec_from_file_location(
        "w092_class_separation", sep_pinned)
    cs = __import__("importlib.util", fromlist=["util"]).module_from_spec(spec)
    spec.loader.exec_module(cs)
    for node, cls, canon, auth in PAIRS:
        if node == "F0":
            continue
        doc = load_yaml(root / f[canon]["pinned_copy"])
        findings = cs.findings(doc, canon)
        check(f"H4-{node}", True, f"{node}: class_separation.findings on pinned bytes",
              [], findings, "pass" if not findings else "fail")

    # ---- H5 / H6 / H7 / H8 class binding ------------------------------------
    tax_canon = load_yaml(root / f["research_map/formulation_taxonomy.yaml"]["pinned_copy"])
    tax_auth = load_yaml(root / f["artifacts/formulation/formulation_taxonomy.yaml"]["pinned_copy"])
    canon_class_set = set(tax_canon.get("class_ids") or [])
    auth_contracts = set((tax_auth.get("class_contracts") or {}).keys())
    for node, cls, canon, auth in PAIRS:
        if node == "F0":
            continue
        doc = load_yaml(root / f[canon]["pinned_copy"])
        cid = doc.get("class_id")
        sib = doc.get("sibling_disjoint_from")
        ptr = doc.get("class_contract_pointer") or ""
        bind_ok = cid in FROZEN_FOUR and cid in canon_class_set
        sib_ok = sib is None or (sib in FROZEN_FOUR and sib != cid)
        if sib:
            sib_doc = load_yaml(root / f[{"AF-SCC-C2-VAC-GEN": "schemas/af_scc_c2_vacuum.yaml",
                                          "AF-SCC-C0-VAC-GEN": "schemas/af_scc_c0_vacuum.yaml"}.get(sib, "")]["pinned_copy"]) \
                if sib in ("AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN") else None
            sib_ok = sib_ok and (sib_doc is None or sib_doc.get("sibling_disjoint_from") == cid)
        check(f"H5-{node}", True, f"{node}: class binding ({cid}) and sibling reciprocity",
              {"in_frozen_four": True, "in_canonical_taxonomy": True, "sibling_reciprocal": True},
              {"in_frozen_four": cid in FROZEN_FOUR, "in_canonical_taxonomy": cid in canon_class_set,
               "sibling": sib, "sibling_reciprocal": sib_ok},
              "pass" if (bind_ok and sib_ok) else "fail")

        target, _, dotted = ptr.partition("#")
        if target.endswith("formulation_taxonomy.yaml") and dotted.startswith("class_contracts."):
            key = dotted.split(".", 1)[1]
            res_auth = key in auth_contracts
            res_canon = resolve_pointer(tax_canon, dotted)[0]
            check(f"H6-{node}", True,
                  f"{node}: class_contract_pointer dereferences in the tree it names",
                  {"authoring_deref": True, "canonical_deref_same_key": res_canon},
                  {"pointer": ptr, "authoring_deref": res_auth, "canonical_deref_same_key": res_canon},
                  "pass" if res_auth else "fail")
            if res_auth and not res_canon:
                report["findings"].append({
                    "id": f"W092-H6-{node}", "severity": "info",
                    "statement": (f"{node}'s class_contract_pointer names the authoring tree; the "
                                  "canonical taxonomy has no 'class_contracts' key, so the class "
                                  "contract is not dereferenceable from the canonical artifact "
                                  "under the declared path."),
                    "class_id": cls,
                    "falsifier": "Resolve the dotted key against the canonical taxonomy; falsified "
                                 "if it yields a non-null class contract.",
                })
        else:
            check(f"H6-{node}", True, f"{node}: class_contract_pointer form", "file#dotted.key",
                  ptr, "fail" if not ptr else "pass")

        decl = (doc.get("f0_binding") or {}).get("declared_f0_sha256")
        meas = f["research_map/formulation_taxonomy.yaml"].get("sha256")
        check(f"H7-{node}", True, f"{node}: f0_binding equals the canonical taxonomy snapshot",
              meas, decl, "pass" if decl == meas else "fail")

        comps = doc.get("class_components") or {}
        ordered = []
        for k, v in comps.items():
            if k == "regularity_token":
                continue
            ordered.append(str(v))
        if comps.get("regularity_token") and str(comps["regularity_token"]).lower() not in ("", "none"):
            # canonical id form inserts the regularity token after the censorship component
            ins = 2 if len(ordered) >= 2 else len(ordered)
            ordered.insert(ins, str(comps["regularity_token"]))
        joined = "-".join(ordered)
        check(f"H8-{node}", False, f"{node}: class_components reproduce class_id",
              cid, joined, "pass" if joined == cid else "warn")

    # ---- S1/S2 cross-tools on live paths ------------------------------------
    live_before = {rel: (sha256_file(root / rel) if (root / rel).exists() else None)
                   for rel in [p[2] for p in PAIRS]}
    vf = subprocess.run([sys.executable, str(root / TOOLS["verify_frozen"])],
                        capture_output=True, text=True, timeout=300)
    check("S1", False, "verify_frozen.py exit code (cross-tool, live paths)",
          0, {"exit": vf.returncode, "stdout": vf.stdout.strip()[:400]},
          "pass" if vf.returncode == 0 else "warn")
    tc = subprocess.run([sys.executable, str(root / TOOLS["taxonomy_consistency"])],
                        capture_output=True, text=True, timeout=300)
    check("S2", False, "check_taxonomy_consistency.py exit code (cross-tool, live paths)",
          0, {"exit": tc.returncode, "stdout": tc.stdout.strip()[:400]},
          "pass" if tc.returncode == 0 else "warn")

    # ---- S3 blocker hash staleness ------------------------------------------
    blocker_evt = None
    if (root / BLOCKER).exists():
        for line in (root / BLOCKER).read_text(encoding="utf-8", errors="replace").splitlines():
            if "leadform-blocker-0005" in line:
                try:
                    ev = json.loads(line)
                    if ev.get("event_id") == "leadform-blocker-0005":
                        blocker_evt = ev
                        break
                except Exception:
                    continue
    named = []
    if blocker_evt:
        named = sorted(set(re.findall(r"\b([0-9a-f]{12,64})\b",
                                      json.dumps(blocker_evt, ensure_ascii=False))))
    measured = {rec["sha256"]: rel for rel, rec in f.items() if rec.get("exists")}
    resolved = {h: measured[h] for h in named if h in measured}
    stale = [h for h in named if h not in measured]
    check("S3", False, "hashes named in leadform-blocker-0005 event vs the measured snapshot",
          {"named": len(named), "resolved": len(resolved)},
          {"named": named, "resolved": resolved, "unresolved": stale},
          "pass" if blocker_evt and not stale else "warn")
    if stale:
        report["findings"].append({
            "id": "W092-S3", "severity": "major",
            "statement": (f"The 'final hashes' named in leadform-blocker-0005 ({len(stale)} unresolved) "
                          "do not match any measured snapshot hash; the request was overtaken by the "
                          "00:18:26-00:19:14 rewrites before it was written."),
            "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
            "falsifier": "Find the named hash as a current or historical hash of a named artifact; "
                         "a superseded revision is not a binding.",
        })

    # ---- S4 live drift -------------------------------------------------------
    drift_live = []
    for rel in [p[2] for p in PAIRS] + ["artifacts/formulation/FROZEN.json"]:
        cur = sha256_file(root / rel) if (root / rel).exists() else None
        old = f[rel].get("sha256") if rel in f else None
        if cur != old:
            drift_live.append({"path": rel, "snapshot": old, "live_after": cur})
    check("S4", False, "canonical paths re-hashed after the checks (mid-run write detection)",
          [], drift_live, "pass" if not drift_live else "warn")
    for d in drift_live:
        report["findings"].append({
            "id": "W092-S4", "severity": "info",
            "statement": (f"{d['path']} changed during the verification window: "
                          f"{(d['snapshot'] or '')[:16]} -> {(d['live_after'] or '')[:16]}; the "
                          "verdict binds the snapshot bytes, this is the drift record."),
            "falsifier": "Re-hash after quiescence; falsified if the two hashes are equal.",
        })

    # ---- S5 clock sanity -----------------------------------------------------
    fz_rec = f.get("artifacts/formulation/FROZEN.json", {})
    frozen_at = frozen.get("frozen_at") if isinstance(frozen, dict) else None
    skew_s = None
    try:
        import calendar
        fmt = "%Y-%m-%dT%H:%M:%S%z"
        t_frozen = time.strptime(frozen_at, fmt)
        t_mtime = time.strptime(fz_rec.get("mtime"), fmt)
        skew_s = calendar.timegm(t_frozen) - calendar.timegm(t_mtime)
    except Exception:
        pass
    check("S5", False, "FROZEN frozen_at vs FROZEN mtime",
          "|skew| <= 300 s", {"frozen_at": frozen_at, "mtime": fz_rec.get("mtime"),
                              "skew_seconds": skew_s},
          "pass" if (skew_s is not None and abs(skew_s) <= 300) else "warn")
    if skew_s is not None and abs(skew_s) > 300:
        report["findings"].append({
            "id": "W092-S5", "severity": "minor",
            "statement": (f"FROZEN rev{frozen.get('revision')} declares frozen_at {frozen_at} but was "
                          f"written at {fz_rec.get('mtime')} (skew {skew_s}s): a 'binding at measured_at' "
                          "claim cannot rest on the declared timestamp."),
            "falsifier": "Re-measure the file mtime and the declared frozen_at; falsified if they agree.",
        })

    # ---- S6 snapshot-A drift history (FROZEN rev24 was stale) ---------------
    snap_a_path = out_dir / "pinned" / "snapshot_manifest.json"
    frozen_a_path = out_dir / "pinned" / "artifacts__formulation__FROZEN.json"
    if snap_a_path.exists() and frozen_a_path.exists():
        snap_a = json.loads(snap_a_path.read_text())
        frozen_a = json.loads(frozen_a_path.read_text())
        drift_a = []
        for rel, rec in sorted((frozen_a.get("files") or {}).items()):
            measured_a = (snap_a.get("files") or {}).get(rel, {}).get("sha256")
            declared_a = rec.get("sha256") if isinstance(rec, dict) else rec
            if measured_a is not None and declared_a != measured_a:
                drift_a.append({"path": rel, "frozen_rev24_declared": declared_a,
                                "snapshot_A_measured": measured_a})
        check("S6", False,
              "snapshot A (2026-09-12T00:19:1x): FROZEN rev24 pins vs the bytes then on disk",
              {"drift": 0}, {"snapshot_A_captured_at": snap_a.get("captured_at"),
                             "frozen_revision": frozen_a.get("revision"), "drift": drift_a},
              "pass" if not drift_a else "warn")
        if drift_a:
            report["findings"].append({
                "id": "W092-S6", "severity": "major",
                "statement": (f"At snapshot A, FROZEN rev{frozen_a.get('revision')} was stale for "
                              f"{len(drift_a)} file(s); the manifest was regenerated to rev"
                              f"{frozen.get('revision')} during the verification window. The "
                              "'frozen' revision did not denote the published bytes for a window of "
                              "roughly one minute after the 00:19:14 rewrite."),
                "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
                "falsifier": "Re-hash the snapshot-A pinned copies against the snapshot-A FROZEN "
                             "manifest; falsified if they agree.",
            })

    # ---- S7 acceptance suite log --------------------------------------------
    acc_log = out_dir / "acceptance_run.log"
    if acc_log.exists():
        txt = acc_log.read_text(encoding="utf-8", errors="replace")
        ok = "ACCEPTANCE: PASS" in txt
        mutants = re.search(r"union caught (\d+)/(\d+)", txt)
        check("S7", False, "run_acceptance.py log (cross-tool, live canonical paths)",
              {"verdict": "PASS", "union_escapes": 0},
              {"verdict": "PASS" if ok else "not PASS", "union": mutants.group(0) if mutants else None,
               "log_sha256": sha256_file(acc_log),
               "tool_sha256": f[TOOLS["acceptance"]].get("sha256")},
              "pass" if ok else "warn")
    else:
        check("S7", False, "run_acceptance.py log present", True, False, "warn")

    # ---- verdict -------------------------------------------------------------
    hard = [c for c in report["checks"] if c["hard"]]
    failed_hard = [c["id"] for c in hard if c["verdict"] != "pass"]
    report["verdict"] = "PASS" if not failed_hard else "FAIL"
    report["failed_hard_checks"] = failed_hard
    report["hard_check_count"] = len(hard)
    report["summary"] = (
        f"{len(hard) - len(failed_hard)}/{len(hard)} hard checks pass at snapshot "
        f"{snap['captured_at']}; canonical F1/F2a/F2b = "
        f"{f['schemas/af_wcc_vacuum.yaml']['sha256'][:12]}/"
        f"{f['schemas/af_scc_c2_vacuum.yaml']['sha256'][:12]}/"
        f"{f['schemas/af_scc_c0_vacuum.yaml']['sha256'][:12]}, F0 = "
        f"{f['research_map/formulation_taxonomy.yaml']['sha256'][:12]}."
    )
    if failed_hard:
        report["findings"].append({
            "id": "W092-VERDICT", "severity": "major",
            "statement": f"Hard checks failed: {', '.join(failed_hard)}; see checks for observed values.",
            "falsifier": "Re-run against the same pinned copies; falsified if those checks pass.",
        })

    out = out_dir / "report.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "report.json.sha256").write_text(
        f"{sha256_file(out)}  report.json\n", encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "failed": failed_hard,
                      "report": str(out.relative_to(root)),
                      "sha256": sha256_file(out)}, indent=1))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

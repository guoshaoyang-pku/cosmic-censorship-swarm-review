#!/usr/bin/env python3
"""
W030B-REPRO-EPR-01 -- independent, fresh-process re-instrumentation of the evidence-pin
repair mechanism for F1/F2a/F2b (classes AF-WCC-VAC-GEN / AF-SCC-C2-VAC-GEN /
AF-SCC-C0-VAC-GEN) at FROZEN rev28 / schema rev12.

This instrument is written from scratch against the two tools' source text.  It does NOT
import or invoke artifacts/worker-030/evidence_pin_repair/run_repair_kit.py.  All tool runs
happen inside throw-away sandboxes under this directory; no canonical file is written.

Claims tested:
  (A) the live canonical evidence 9e335e9b is exactly what the UNPATCHED canonical tool
      emits on the live F0 pair;
  (B) 675a99d0 == that 8-field document + the three binding fields appended in the declared
      order (map_taxonomy_sha256, lead_contract_sha256, measured_at);
  (C) the UNPATCHED tool erases the declared 675a99d0 bytes back to 9e335e9b when run on a
      tree that currently holds the declared bytes (the causal mechanism, reproduced from
      the declared state);
  (D) the staged PATCHED tool restores 675a99d0 from the live 8-field state at
      --measured-at 2026-09-12T00:32:02+08:00 and is idempotent on rerun;
  (E) the patched tool does not certify a semantically mutated taxonomy (exit 1, new hash).

Exit code 0 = all checks pass; 1 = a check failed; 2 = entry-pin/plumbing failure.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SANDBOX = HERE / "sandbox"
MEASURED_AT = "2026-09-12T00:32:02+08:00"

CANON_TOOL = ROOT / "artifacts/formulation/tools/check_taxonomy_consistency.py"
PATCHED_TOOL = ROOT / "artifacts/worker-030/evidence_pin_repair/patched_check_taxonomy_consistency.py"
DECLARED = ROOT / "artifacts/worker-030/evidence_pin_repair/declared_pin_snapshot.json"
LIVE_EVIDENCE = ROOT / "artifacts/formulation/evidence/taxonomy_consistency.json"
W086_WITNESS = ROOT / "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"

CANON_SHA = "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd"
PATCHED_SHA = "83ab54519d45b8e5c678b393c1517fd479a0a3c0010daa0b5af3208ef8f727fa"
DECLARED_SHA = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
LIVE_SHA = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
BIND_ORDER = ["map_taxonomy_sha256", "lead_contract_sha256", "measured_at"]

PINS = {
    "F0_canonical": ROOT / "research_map/formulation_taxonomy.yaml",
    "F0_supplement": ROOT / "artifacts/formulation/formulation_taxonomy.yaml",
    "F1": ROOT / "schemas/af_wcc_vacuum.yaml",
    "F2a": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "F2b": ROOT / "schemas/af_scc_c0_vacuum.yaml",
    "live_evidence": LIVE_EVIDENCE,
    "FROZEN": ROOT / "artifacts/formulation/FROZEN.json",
    "canonical_tool": CANON_TOOL,
    "patched_tool": PATCHED_TOOL,
}

checks = []


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pin_snapshot():
    out = {}
    for k, p in PINS.items():
        out[k] = sha(p) if Path(p).exists() else None
    return out


def record(cid, ok, detail):
    checks.append({"id": cid, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + cid + " :: " + json.dumps(detail)[:300])
    return bool(ok)


def make_layout(name, tool_src, seed=None, mutate_family=None):
    """Mirror the repo layout so the tool's parents[3] resolves to the sandbox root."""
    root = SANDBOX / name
    if root.exists():
        shutil.rmtree(root)
    (root / "research_map").mkdir(parents=True)
    (root / "artifacts/formulation/tools").mkdir(parents=True)
    (root / "artifacts/formulation/evidence").mkdir(parents=True)
    shutil.copy2(ROOT / "research_map/formulation_taxonomy.yaml", root / "research_map/formulation_taxonomy.yaml")
    shutil.copy2(ROOT / "artifacts/formulation/formulation_taxonomy.yaml",
                 root / "artifacts/formulation/formulation_taxonomy.yaml")
    shutil.copy2(ROOT / "artifacts/formulation/VOCAB_ALIASES.json",
                 root / "artifacts/formulation/VOCAB_ALIASES.json")
    shutil.copy2(tool_src, root / "artifacts/formulation/tools/check_taxonomy_consistency.py")
    if mutate_family is not None:
        mp = root / "research_map/formulation_taxonomy.yaml"
        doc = yaml.safe_load(mp.read_text())
        cid = "AF-WCC-VAC-GEN"
        assert doc["classes"][cid]["axes"]["family"] == "WCC", "mutation fixture precondition"
        doc["classes"][cid]["axes"]["family"] = mutate_family
        mp.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    out = root / "artifacts/formulation/evidence/taxonomy_consistency.json"
    if seed is not None:
        out.write_bytes(Path(seed).read_bytes())
    return root, out


def run_tool(root, args=(), timeout=120):
    proc = subprocess.run(
        [sys.executable, str(root / "artifacts/formulation/tools/check_taxonomy_consistency.py"), *args],
        capture_output=True, text=True, timeout=timeout, cwd=str(root),
    )
    return proc.returncode, proc.stdout, proc.stderr


def main():
    entry = pin_snapshot()
    print("entry pins:")
    for k, v in entry.items():
        print(f"  {k} = {v}")

    if entry["canonical_tool"] != CANON_SHA or entry["patched_tool"] != PATCHED_SHA:
        print("PLUMBING FAILURE: tool pins moved; refusing to interpret")
        return 2

    declared_bytes = DECLARED.read_bytes()
    live_bytes = LIVE_EVIDENCE.read_bytes()
    declared_doc = json.loads(declared_bytes)
    live_doc = json.loads(live_bytes)

    record("P1-canonical-tool-pin", sha(CANON_TOOL) == CANON_SHA, {"measured": sha(CANON_TOOL), "expected": CANON_SHA})
    record("P2-patched-tool-pin", sha(PATCHED_TOOL) == PATCHED_SHA, {"measured": sha(PATCHED_TOOL), "expected": PATCHED_SHA})
    record("P3-declared-snapshot-pin", sha(DECLARED) == DECLARED_SHA, {"measured": sha(DECLARED), "expected": DECLARED_SHA})
    record("P4-live-evidence-entry", sha(LIVE_EVIDENCE) == LIVE_SHA, {"measured": sha(LIVE_EVIDENCE), "expected": LIVE_SHA})
    record("P5-w086-witness",
           W086_WITNESS.exists() and sha(W086_WITNESS) == DECLARED_SHA,
           {"path": str(W086_WITNESS.relative_to(ROOT)), "exists": W086_WITNESS.exists(),
            "measured": sha(W086_WITNESS) if W086_WITNESS.exists() else None})
    record("P6-live-evidence-shape",
           len(live_doc) == 8 and not any(k in live_doc for k in BIND_ORDER),
           {"fields": len(live_doc), "has_binding_keys": [k for k in BIND_ORDER if k in live_doc]})
    record("P7-declared-shape",
           list(declared_doc.keys()) == list(live_doc.keys()) + BIND_ORDER,
           {"declared_keys": list(declared_doc.keys()),
            "expected": list(live_doc.keys()) + BIND_ORDER})
    record("P8-declared-input-hashes",
           declared_doc.get("map_taxonomy_sha256") == entry["F0_canonical"]
           and declared_doc.get("lead_contract_sha256") == entry["F0_supplement"]
           and declared_doc.get("measured_at") == MEASURED_AT,
           {"recorded": {k: declared_doc.get(k) for k in BIND_ORDER},
            "measured_F0": entry["F0_canonical"], "measured_supplement": entry["F0_supplement"],
            "expected_measured_at": MEASURED_AT})

    # (A) unpatched tool on the live pair, fresh output
    a_root, a_out = make_layout("a_unpatched_fresh", CANON_TOOL)
    a_rc, a_stdout, a_stderr = run_tool(a_root)
    record("A1-unpatched-fresh-exit0", a_rc == 0 and "CONSISTENT" in a_stdout,
           {"rc": a_rc, "stdout": a_stdout.strip().splitlines()[:2], "stderr": a_stderr[-200:]})
    record("A2-unpatched-fresh-hash-live",
           a_out.exists() and sha(a_out) == LIVE_SHA and a_out.read_bytes() == live_bytes,
           {"measured": sha(a_out) if a_out.exists() else None, "expected": LIVE_SHA,
            "byte_equal_live": a_out.exists() and a_out.read_bytes() == live_bytes})

    # (B) independent reconstruction of the declared bytes from the live 8-field document
    rebuilt = dict(live_doc)
    rebuilt["map_taxonomy_sha256"] = entry["F0_canonical"]
    rebuilt["lead_contract_sha256"] = entry["F0_supplement"]
    rebuilt["measured_at"] = MEASURED_AT
    rebuilt_bytes = (json.dumps(rebuilt, indent=2) + "\n").encode()
    record("B1-reconstruction-hash-declared",
           hashlib.sha256(rebuilt_bytes).hexdigest() == DECLARED_SHA and rebuilt_bytes == declared_bytes,
           {"measured": hashlib.sha256(rebuilt_bytes).hexdigest(), "expected": DECLARED_SHA,
            "byte_equal_declared": rebuilt_bytes == declared_bytes})

    # (C) causal control: declared bytes present, unpatched tool runs -> erased
    c_root, c_out = make_layout("c_unpatched_on_declared", CANON_TOOL, seed=DECLARED)
    c_pre = sha(c_out)
    c_rc, c_stdout, c_stderr = run_tool(c_root)
    record("C1-erasure-reproduces",
           c_pre == DECLARED_SHA and c_rc == 0 and sha(c_out) == LIVE_SHA and c_out.read_bytes() == live_bytes,
           {"pre_seeded": c_pre, "post_run": sha(c_out), "expected_post": LIVE_SHA, "rc": c_rc,
            "stdout": c_stdout.strip().splitlines()[:1]})

    # (D) patched tool: restore + idempotence
    d_root, d_out = make_layout("d_patched_restore", PATCHED_TOOL, seed=LIVE_EVIDENCE)
    d_rc, d_stdout, d_stderr = run_tool(d_root, ["--measured-at", MEASURED_AT])
    record("D1-patched-restore",
           d_rc == 0 and "WROTE" in d_stdout and sha(d_out) == DECLARED_SHA and d_out.read_bytes() == declared_bytes,
           {"rc": d_rc, "measured": sha(d_out), "expected": DECLARED_SHA,
            "byte_equal_declared": d_out.read_bytes() == declared_bytes,
            "stdout": d_stdout.strip().splitlines()[:2], "stderr": d_stderr[-200:]})
    d2_rc, d2_stdout, d2_stderr = run_tool(d_root, ["--measured-at", MEASURED_AT])
    record("D2-patched-idempotent",
           d2_rc == 0 and "UNCHANGED" in d2_stdout and sha(d_out) == DECLARED_SHA,
           {"rc": d2_rc, "measured": sha(d_out), "stdout": d2_stdout.strip().splitlines()[:2]})

    # (E) patched tool must not certify a mutated taxonomy, and must rewrite (no stale accept)
    e_root, e_out = make_layout("e_patched_mutation", PATCHED_TOOL, seed=DECLARED, mutate_family="SCC")
    e_rc, e_stdout, e_stderr = run_tool(e_root, ["--measured-at", MEASURED_AT])
    e_doc = json.loads(e_out.read_text())
    record("E1-patched-rejects-mutation",
           e_rc == 1 and "INCONSISTENT" in e_stdout and e_doc.get("consistent") is False
           and sha(e_out) != DECLARED_SHA and any("family" in err for err in e_doc.get("errors", [])),
           {"rc": e_rc, "measured": sha(e_out), "consistent": e_doc.get("consistent"),
            "errors": e_doc.get("errors"), "stdout": e_stdout.strip().splitlines()[:2]})

    # (F) independent line-level check-logic identity (canonical lines 1..78 vs patched lines 1..78)
    canon_lines = CANON_TOOL.read_text().splitlines()
    patched_lines = PATCHED_TOOL.read_text().splitlines()
    record("F1-check-logic-lines-1-78-identical",
           canon_lines[:78] == patched_lines[:78],
           {"canonical_lines": len(canon_lines), "patched_lines": len(patched_lines),
            "divergence": next((i + 1 for i, (x, y) in enumerate(zip(canon_lines[:78], patched_lines[:78])) if x != y), None)})

    # (G) informational: schema bindings + mtimes vs declared measured_at
    schema_info = {}
    for cid, rel in (("F1", "schemas/af_wcc_vacuum.yaml"), ("F2a", "schemas/af_scc_c2_vacuum.yaml"),
                     ("F2b", "schemas/af_scc_c0_vacuum.yaml")):
        p = ROOT / rel
        doc = yaml.safe_load(p.read_text())
        b = doc.get("f0_binding", {})
        schema_info[cid] = {
            "declared_consistency_sha256": b.get("consistency_evidence_sha256"),
            "checked_at": b.get("checked_at"),
            "mtime": datetime.fromtimestamp(p.stat().st_mtime, timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
            "revised_at": doc.get("revised_at"),
        }
    all_declare = all(v["declared_consistency_sha256"] == DECLARED_SHA for v in schema_info.values())
    record("G1-all-schemas-declare-675a99d0", all_declare, schema_info)
    record("G2-live-evidence-mismatch-all",
           all(sha(LIVE_EVIDENCE) != v["declared_consistency_sha256"] for v in schema_info.values()),
           {"live": sha(LIVE_EVIDENCE), "declared": DECLARED_SHA})
    record("G3-schema-mtime-equals-measured-at",
           all(v["mtime"] == "2026-09-12T00:32:02+08:00" for v in schema_info.values()),
           {cid: v["mtime"] for cid, v in schema_info.items()})

    # Correction to a supporting sentence in the prior kit's REPORT.md (line 37): it states the
    # schemas' revised_at is 2026-09-12T00:32:02.  Measured: revised_at and checked_at are
    # 2026-09-12T00:31:41; only the file mtime is 00:32:02.  The byte-level mechanism (B1/D1) is
    # unaffected; the identity "declared measured_at == schema mtime" is what is measured here.
    revision_clock_note = {
        "prior_claim": "REPORT.md line 37: schemas' revised_at and mtimes are all 2026-09-12T00:32:02",
        "measured": {cid: {"revised_at": v["revised_at"], "checked_at": v["checked_at"], "mtime": v["mtime"]}
                     for cid, v in schema_info.items()},
        "effect": "supporting sentence corrected; B1/D1 mechanism verdict unchanged",
    }

    exit_pins = pin_snapshot()
    drift = {k: {"entry": entry[k], "exit": exit_pins[k]} for k in PINS if entry[k] != exit_pins[k]}
    record("H1-no-canonical-drift", not drift, {"drift": drift})

    passed = sum(1 for c in checks if c["pass"])
    failed = [c["id"] for c in checks if not c["pass"]]
    verdict = "REPRODUCED_INDEPENDENTLY" if not failed else "REPRO_FAILED"
    report = {
        "schema_version": "w030-repro-epr/v1",
        "task_id": "W030B-REPRO-EPR-01",
        "artifact_id": "artifacts/worker-030/repro_epr/report.json",
        "worker": "worker-030",
        "role": "bounded execution worker",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_ids": ["F1", "F2a", "F2b"],
        "gate": "G-FORM",
        "created_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "verdict": verdict,
        "checks_passed": passed,
        "checks_failed": len(failed),
        "failed_check_ids": failed,
        "checks": checks,
        "entry_pins": entry,
        "exit_pins": exit_pins,
        "canonical_drift": drift,
        "notes": [revision_clock_note],
        "instrument": "artifacts/worker-030/repro_epr/repro_epr.py",
        "instrument_sha256": sha(Path(__file__)),
        "sandbox_runs": {
            "a_unpatched_fresh": {"tool": "canonical", "seed": None, "rc": a_rc, "out_sha256": sha(a_out)},
            "c_unpatched_on_declared": {"tool": "canonical", "seed": DECLARED_SHA, "rc": c_rc, "out_sha256": sha(c_out)},
            "d_patched_restore": {"tool": "patched", "seed": LIVE_SHA, "rc": d_rc, "out_sha256": sha(d_out)},
            "d2_patched_rerun": {"tool": "patched", "seed": DECLARED_SHA, "rc": d2_rc, "out_sha256": sha(d_out)},
            "e_patched_mutation": {"tool": "patched", "seed": DECLARED_SHA, "rc": e_rc, "out_sha256": sha(e_out)},
        },
        "falsifiers": [
            "A rerun of the canonical (unpatched) tool on the live F0 pair that emits 675a99d0 would falsify A1/A2 and B1.",
            "A declared snapshot that is not byte-equal to live_doc + the three binding fields in the declared order would falsify B1.",
            "An unpatched run seeded with the declared bytes that leaves them at 675a99d0 would falsify C1 (the erasure mechanism).",
            "A patched run at --measured-at 2026-09-12T00:32:02+08:00 that fails to reproduce 675a99d0, or a rerun that rewrites the file, would falsify D1/D2.",
            "A patched run on the mutated taxonomy that exits 0 or leaves the declared bytes in place would falsify E1.",
            "Any entry-pin difference between instrument start and exit voids the affected row (reported as H1 drift; observed empty).",
        ],
        "not_claimed": [
            "no gate verdict, no node status, no validation_status=passed",
            "no canonical write (all tool runs happened in sandboxes under artifacts/worker-030/repro_epr/sandbox/)",
            "no claim that F1/F2a/F2b content is correct; this tests only the evidence-binding mechanism",
            "not an independent second review of the schemas; same worker slot as the kit under test",
        ],
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nverdict={verdict} pass={passed} fail={len(failed)} failed={failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W074-F2A-EVBIND-REHEARSAL-01 (worker-074).

Independent, sandboxed rehearsal of the consistency-evidence pin repair that gates
AF-SCC-C2-VAC-GEN (F2a) / G-FORM.

Question
--------
Schemas F1/F2a/F2b declare
  f0_binding.consistency_evidence = artifacts/formulation/evidence/taxonomy_consistency.json
  f0_binding.consistency_evidence_sha256 = 675a99d0...  (728 bytes)
while that path carries 9e335e9b... (495 bytes, the 8-field form produced by the
canonical checker's unconditional rewrite).  Worker-030 staged a repair kit claiming
675a99d0 is byte-exactly reproducible and restorable with zero semantic change.

This script does NOT take worker-030's word for it.  It rebuilds the claim from primary
bytes with independent code, adversarially tests the kit's mechanism, and rehearses the
owner's repair end-to-end *inside a sandbox copy* so the cross-constraint with FROZEN
rev28 is measured before anyone writes a canonical file.

Authority: measurement only.  No canonical repo file is written; no node status,
validation_status, review verdict or gate verdict is claimed.  All writes go under
artifacts/worker-074/evbind_rehearsal/.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent          # artifacts/worker-074/evbind_rehearsal
ROOT = HERE.parents[2]                          # repo root
OUT = HERE
SANDBOX = OUT / "sandbox"
RAW = OUT / "raw"

DECLARED_SHA = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
LIVE_SHA = "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"
EVIDENCE_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"
FROZEN_REL = "artifacts/formulation/FROZEN.json"
CANON_TOOL_REL = "artifacts/formulation/tools/check_taxonomy_consistency.py"
PATCHED_TOOL_SRC = "artifacts/worker-030/evidence_pin_repair/patched_check_taxonomy_consistency.py"
PATCHED_TOOL_REL_IN_SANDBOX = "artifacts/formulation/tools/check_taxonomy_consistency_patched.py"
SCHEMAS = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
CLASS_OF = {
    "F1": "AF-WCC-VAC-GEN",
    "F2a": "AF-SCC-C2-VAC-GEN",
    "F2b": "AF-SCC-C0-VAC-GEN",
}
F0_REL = "research_map/formulation_taxonomy.yaml"
F0_SUPP_REL = "artifacts/formulation/formulation_taxonomy.yaml"
FROZEN_PIN_KEYS = [EVIDENCE_REL, *SCHEMAS.values()]
MEASURED_AT = "2026-09-12T00:32:02+08:00"

checks: list[dict] = []
raw_log: list[str] = []


def note(msg: str) -> None:
    raw_log.append(msg)
    print(msg)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def meas(rel: str, base: Path = ROOT) -> dict:
    p = base / rel
    return {"path": rel, "exists": p.exists(),
            "sha256": sha256_file(p) if p.exists() else None,
            "bytes": p.stat().st_size if p.exists() else None}


def check(cid: str, ok: bool, detail) -> None:
    checks.append({"id": cid, "pass": bool(ok), "detail": detail})
    note(f"[{'PASS' if ok else 'FAIL'}] {cid}: {json.dumps(detail)[:300]}")


def run(cmd: list[str], cwd: Path) -> dict:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=180)
    return {"cmd": cmd, "exit": r.returncode, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}


# ---------------------------------------------------------------- 0. snapshot
note("== S0 snapshot of canonical inputs (read-only) ==")
snapshot = {
    "map": meas("research_map/research_map.json"),
    "f0_canonical": meas(F0_REL),
    "f0_supplement": meas(F0_SUPP_REL),
    "evidence": meas(EVIDENCE_REL),
    "frozen": meas(FROZEN_REL),
    "canonical_tool": meas(CANON_TOOL_REL),
    "patched_tool": meas(PATCHED_TOOL_SRC),
    "schemas": {k: meas(v) for k, v in SCHEMAS.items()},
}
frozen_doc = json.loads((ROOT / FROZEN_REL).read_text())
frozen_pins = frozen_doc["files"]
check("S0-evidence-is-live-form", snapshot["evidence"]["sha256"] == LIVE_SHA,
      {"measured": snapshot["evidence"]["sha256"], "expected_live_form": LIVE_SHA})
check("S0-frozen-rev", frozen_doc.get("revision") == 28,
      {"revision": frozen_doc.get("revision"), "frozen_at": frozen_doc.get("frozen_at")})

declared: dict[str, dict] = {}
for node, rel in SCHEMAS.items():
    doc = yaml.safe_load((ROOT / rel).read_text())
    fb = doc.get("f0_binding", {})
    declared[node] = {
        "class_id": CLASS_OF[node],
        "schema_sha256": snapshot["schemas"][node]["sha256"],
        "declared_consistency_evidence": fb.get("consistency_evidence"),
        "declared_consistency_evidence_sha256": fb.get("consistency_evidence_sha256"),
        "declared_f0_sha256": fb.get("declared_f0_sha256"),
        "measured_f0_sha256": snapshot["f0_canonical"]["sha256"],
        "declared_f0_resolves": fb.get("declared_f0_sha256") == snapshot["f0_canonical"]["sha256"],
        "declared_evidence_resolves_at_path": False,  # filled below
    }
    declared[node]["declared_evidence_resolves_at_path"] = (
        fb.get("consistency_evidence_sha256") == snapshot["evidence"]["sha256"])
check("S0-three-schemas-declare-same-pin",
      len({d["declared_consistency_evidence_sha256"] for d in declared.values()}) == 1
      and all(d["declared_consistency_evidence_sha256"] == DECLARED_SHA for d in declared.values()),
      {k: v["declared_consistency_evidence_sha256"][:16] for k, v in declared.items()})
check("S0-declared-pin-vs-measured-path",
      all(not d["declared_evidence_resolves_at_path"] for d in declared.values()),
      {"declared": DECLARED_SHA[:16], "measured_at_path": snapshot["evidence"]["sha256"][:16],
       "reproduces_the_blocking_finding": True})

# frozen baseline mismatches
baseline_mismatch = []
for rel, pin in frozen_pins.items():
    p = ROOT / rel
    if not p.exists() or sha256_file(p) != pin["sha256"]:
        baseline_mismatch.append(rel)
check("S0-frozen-baseline-zero-mismatch", baseline_mismatch == [],
      {"pins": len(frozen_pins), "mismatches": baseline_mismatch,
       "evidence_pin": frozen_pins.get(EVIDENCE_REL)})

# ------------------------------------------------- 1. carrier census (bounded)
note("== S1 bytes-728 carrier census ==")
carriers, searched = [], 0
size_cap, file_cap = 4096, 200_000
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    rel = str(p.relative_to(ROOT))
    if rel.startswith(".git/") or rel.startswith("artifacts/worker-074/evbind_rehearsal/"):
        continue
    searched += 1
    if searched > file_cap:
        break
    try:
        if p.stat().st_size == 728 and sha256_file(p) == DECLARED_SHA:
            carriers.append(rel)
    except OSError:
        continue
check("S1-declared-hash-carriers-exist",
      len(carriers) >= 2 and EVIDENCE_REL not in carriers,
      {"files_searched": searched, "carrier_count": len(carriers),
       "canonical_path_is_carrier": EVIDENCE_REL in carriers, "carriers": carriers[:12]})

# ------------------------------------- 2. independent byte reconstruction (C1)
note("== C1 independent byte reconstruction ==")
live_bytes = (ROOT / EVIDENCE_REL).read_bytes()
carrier_bytes = (ROOT / carriers[0]).read_bytes()
live_doc = json.loads(live_bytes)
ins = (b',\n  "map_taxonomy_sha256": ' + json.dumps(snapshot["f0_canonical"]["sha256"]).encode()
       + b',\n  "lead_contract_sha256": ' + json.dumps(snapshot["f0_supplement"]["sha256"]).encode()
       + b',\n  "measured_at": ' + json.dumps(MEASURED_AT).encode() + b'\n}\n')
surgical = live_bytes[:-2].rstrip(b"\n") + ins
check("C1a-surgical-append-reproduces-declared",
      hashlib.sha256(surgical).hexdigest() == DECLARED_SHA and surgical == carrier_bytes,
      {"sha256": hashlib.sha256(surgical).hexdigest()[:16], "bytes": len(surgical),
       "byte_identical_to_carrier": surgical == carrier_bytes})

reser = dict(live_doc)
reser["map_taxonomy_sha256"] = snapshot["f0_canonical"]["sha256"]
reser["lead_contract_sha256"] = snapshot["f0_supplement"]["sha256"]
reser["measured_at"] = MEASURED_AT
reser_bytes = (json.dumps(reser, indent=2) + "\n").encode()
check("C1b-tool-style-reserialisation-reproduces-declared",
      hashlib.sha256(reser_bytes).hexdigest() == DECLARED_SHA,
      {"sha256": hashlib.sha256(reser_bytes).hexdigest()[:16], "bytes": len(reser_bytes)})

# negative controls: the pin must not be reachable by anything weaker
neg = {}
bad = dict(live_doc); bad.update({"map_taxonomy_sha256": snapshot["f0_canonical"]["sha256"],
                                  "lead_contract_sha256": snapshot["f0_supplement"]["sha256"],
                                  "measured_at": MEASURED_AT})
neg["indent1"] = hashlib.sha256((json.dumps(bad, indent=1) + "\n").encode()).hexdigest()
mut = dict(bad); mut["consistent"] = False
neg["consistent_false"] = hashlib.sha256((json.dumps(mut, indent=2) + "\n").encode()).hexdigest()
mut2 = dict(bad); mut2["map_taxonomy_sha256"] = "0" * 64
neg["wrong_f0_pin"] = hashlib.sha256((json.dumps(mut2, indent=2) + "\n").encode()).hexdigest()
mut3 = dict(bad); mut3.pop("map_taxonomy_sha256")
neg["missing_f0_pin"] = hashlib.sha256((json.dumps(mut3, indent=2) + "\n").encode()).hexdigest()
mut4 = dict(bad); mut4["measured_at"] = "2026-09-12T00:32:03+08:00"
neg["one_second_later"] = hashlib.sha256((json.dumps(mut4, indent=2) + "\n").encode()).hexdigest()
check("C1c-negative-controls-never-hit-declared",
      all(v != DECLARED_SHA for v in neg.values()),
      {k: v[:16] for k, v in neg.items()})

# ------------------------------------------------- 3. sandbox construction
note("== S2 sandbox copy (no canonical write) ==")
if SANDBOX.exists():
    shutil.rmtree(SANDBOX)
for rel in ["research_map/formulation_taxonomy.yaml", F0_SUPP_REL,
            "artifacts/formulation/VOCAB_ALIASES.json", FROZEN_REL,
            EVIDENCE_REL, CANON_TOOL_REL, PATCHED_TOOL_SRC, *SCHEMAS.values()]:
    dst = SANDBOX / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / rel, dst)
shutil.copy2(ROOT / PATCHED_TOOL_SRC, SANDBOX / PATCHED_TOOL_REL_IN_SANDBOX)
canon_before = {rel: sha256_file(ROOT / rel) for rel in
                ["research_map/formulation_taxonomy.yaml", F0_SUPP_REL, EVIDENCE_REL,
                 FROZEN_REL, CANON_TOOL_REL, PATCHED_TOOL_SRC, *SCHEMAS.values()]}
check("S2-sandbox-mirrors-inputs",
      sha256_file(SANDBOX / EVIDENCE_REL) == LIVE_SHA
      and sha256_file(SANDBOX / CANON_TOOL_REL) == snapshot["canonical_tool"]["sha256"],
      {"sandbox_evidence": sha256_file(SANDBOX / EVIDENCE_REL)[:16]})


def frozen_mismatches(base: Path) -> list[str]:
    """Pin mismatches over the pinned paths that exist in `base` (the sandbox mirrors a
    subset of the 44 pinned files; absent files are reported separately, not as mismatches)."""
    doc = json.loads((base / FROZEN_REL).read_text())
    out = []
    for rel, pin in doc["files"].items():
        p = base / rel
        if p.exists() and sha256_file(p) != pin["sha256"]:
            out.append(rel)
    return out


def frozen_absent(base: Path) -> list[str]:
    doc = json.loads((base / FROZEN_REL).read_text())
    return [rel for rel in doc["files"] if not (base / rel).exists()]


# ------------------------ 4. canonical tool erases pins (mechanism, in sandbox)
note("== R1 canonical checker run in sandbox ==")
r1 = run([sys.executable, str(SANDBOX / CANON_TOOL_REL)], SANDBOX)
ev_after_r1 = sha256_file(SANDBOX / EVIDENCE_REL)
check("R1-canonical-tool-rewrites-to-live-form",
      ev_after_r1 == LIVE_SHA and "CONSISTENT" in r1["stdout"] and r1["exit"] == 0,
      {"exit": r1["exit"], "stdout": r1["stdout"], "evidence_sha256": ev_after_r1[:16]})

# ------------------- 5. owner repair rehearsal: restore declared bytes + patched tool
note("== R2 restore declared bytes, then patched tool (UNCHANGED expected) ==")
(SANDBOX / EVIDENCE_REL).write_bytes(carrier_bytes)
ev_restored = sha256_file(SANDBOX / EVIDENCE_REL)
r2 = run([sys.executable, str(SANDBOX / PATCHED_TOOL_REL_IN_SANDBOX),
          "--out", str(SANDBOX / EVIDENCE_REL), "--measured-at", MEASURED_AT], SANDBOX)
ev_r2 = sha256_file(SANDBOX / EVIDENCE_REL)
check("R2-restore-then-patched-tool-preserves-declared",
      ev_restored == DECLARED_SHA and ev_r2 == DECLARED_SHA and "UNCHANGED" in r2["stdout"],
      {"after_restore": ev_restored[:16], "after_patched_tool": ev_r2[:16],
       "stdout": r2["stdout"], "exit": r2["exit"]})
r2b = run([sys.executable, str(SANDBOX / PATCHED_TOOL_REL_IN_SANDBOX),
           "--out", str(SANDBOX / EVIDENCE_REL), "--measured-at", MEASURED_AT], SANDBOX)
check("R2b-idempotent-second-run",
      sha256_file(SANDBOX / EVIDENCE_REL) == DECLARED_SHA and "UNCHANGED" in r2b["stdout"],
      {"stdout": r2b["stdout"], "exit": r2b["exit"]})

# declared resolution now holds at the path
declared_resolves_after = all(
    yaml.safe_load((ROOT / rel).read_text())["f0_binding"]["consistency_evidence_sha256"]
    == ev_r2 for rel in SCHEMAS.values())
check("R2c-declared-pin-would-resolve-after-repair", declared_resolves_after,
      {"declared": DECLARED_SHA[:16], "sandbox_path_sha256": ev_r2[:16]})

# ------------------- 6. cascade: FROZEN rev28 pin vs repaired path
note("== R3 FROZEN rev28 cascade ==")
mm_repaired = frozen_mismatches(SANDBOX)
check("R3-frozen-mismatch-appears-after-restore",
      mm_repaired == [EVIDENCE_REL],
      {"mismatch_count": len(mm_repaired), "mismatches": mm_repaired,
       "sandbox_absent_pins": len(frozen_absent(SANDBOX)),
       "frozen_expected": frozen_pins[EVIDENCE_REL]["sha256"][:16],
       "measured_now": ev_r2[:16]})

# ------------------- 7. fresh-live + patched tool WITHOUT historical measured_at
note("== R4 patched tool on live bytes without historical measured_at ==")
(SANDBOX / EVIDENCE_REL).write_bytes(live_bytes)
r4 = run([sys.executable, str(SANDBOX / PATCHED_TOOL_REL_IN_SANDBOX),
          "--out", str(SANDBOX / EVIDENCE_REL)], SANDBOX)
ev_r4 = sha256_file(SANDBOX / EVIDENCE_REL)
check("R4-default-clock-does-not-reproduce-declared",
      ev_r4 != DECLARED_SHA,
      {"sha256": ev_r4[:16], "is_declared": ev_r4 == DECLARED_SHA,
       "stdout": r4["stdout"], "operational_caveat": "restore must pin --measured-at"})

# ------------------- 8. alternative repair (re-pin the schemas) in sandbox
note("== R5 counterfactual: re-pin schema to live form instead of restoring bytes ==")
alt_schema = SANDBOX / SCHEMAS["F2a"]
alt_bytes = alt_schema.read_bytes().replace(DECLARED_SHA.encode(), LIVE_SHA.encode())
alt_schema.write_bytes(alt_bytes)
alt_sha = sha256_file(alt_schema)
(SANDBOX / EVIDENCE_REL).write_bytes(live_bytes)
mm_alt = frozen_mismatches(SANDBOX)
check("R5-repin-alternative-breaks-the-frozen-schema-pin",
      alt_sha != declared["F2a"]["schema_sha256"] and mm_alt == [SCHEMAS["F2a"]],
      {"schema_sha256_after": alt_sha[:16], "frozen_declared": declared["F2a"]["schema_sha256"][:16],
       "frozen_mismatches": mm_alt,
       "consequence": "leaves 5476a3f2 -> every F2a review bind at 5476a3f2 is void"})

# ------------------------------------------------- 9. canonical untouched guard
canon_after = {rel: sha256_file(ROOT / rel) for rel in canon_before}
check("S9-canonical-untouched", canon_before == canon_after,
      {"drift": [k for k in canon_before if canon_before[k] != canon_after[k]]})

# ---------------------------------------------------------------- report
overall = {
    "declared_pin_resolves_before": False,
    "declared_pin_byte_exactly_reproducible": hashlib.sha256(surgical).hexdigest() == DECLARED_SHA,
    "canonical_tool_is_the_eraser": ev_after_r1 == LIVE_SHA,
    "patched_tool_preserves_declared": ev_r2 == DECLARED_SHA,
    "repair_alone_leaves_frozen_mismatch": mm_repaired == [EVIDENCE_REL],
    "repin_alternative_is_worse": SCHEMAS["F2a"] in mm_alt and alt_sha != declared["F2a"]["schema_sha256"],
    "controls_all_pass": all(c["pass"] for c in checks),
}
report = {
    "schema_version": "w074-evbind-rehearsal/v1",
    "task_id": "W074-F2A-EVBIND-REHEARSAL-01",
    "worker": "worker-074",
    "role": "bounded execution worker",
    "class_ids": ["AF-SCC-C2-VAC-GEN"],
    "class_scope_note": ("Bound to AF-SCC-C2-VAC-GEN (F2a). F1 (AF-WCC-VAC-GEN) and "
                         "F2b (AF-SCC-C0-VAC-GEN) declare the same pin and were measured for "
                         "scope only; no verdict is claimed for them."),
    "node_id": "F2a",
    "gate": "G-FORM",
    "created_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
    "authority_note": ("Measurement and rehearsal only. No canonical repo file was written "
                       "(S9 guard); all writes are under artifacts/worker-074/evbind_rehearsal/. "
                       "No node status, validation_status, review verdict or gate verdict is set."),
    "snapshot": snapshot,
    "declared_bindings": declared,
    "carrier_census": {"files_searched": searched, "carrier_count": len(carriers),
                       "canonical_path_is_carrier": EVIDENCE_REL in carriers,
                       "carriers": carriers},
    "reconstruction": {"declared_sha256": DECLARED_SHA,
                       "declared_bytes": len(carrier_bytes),
                       "surgical_sha256": hashlib.sha256(surgical).hexdigest(),
                       "tool_style_sha256": hashlib.sha256(reser_bytes).hexdigest(),
                       "negative_control_hashes": neg},
    "rehearsal": {
        "R1_canonical_tool": {**r1, "evidence_after": ev_after_r1},
        "R2_restore_and_patched_tool": {**r2, "evidence_after": ev_r2},
        "R2b_idempotence": {**r2b, "evidence_after": sha256_file(SANDBOX / EVIDENCE_REL)},
        "R3_frozen_cascade": {"mismatches": mm_repaired,
                              "frozen_rev": frozen_doc.get("revision"),
                              "frozen_pin": frozen_pins.get(EVIDENCE_REL)},
        "R4_default_clock": {**r4, "evidence_after": ev_r4},
        "R5_repin_alternative": {"schema_sha256_after": alt_sha,
                                 "frozen_mismatches": mm_alt},
        "sandbox": str(SANDBOX.relative_to(ROOT)),
    },
    "frozen_baseline_mismatches": baseline_mismatch,
    "checks": checks,
    "headline": {
        "finding_id": "W074-EVBIND-F1",
        "result": ("The declared pin 675a99d0 is byte-exactly the live 8-field document plus "
                   "the three binding fields, and is restorable; but the restore alone turns a "
                   "schema-side binding failure into a FROZEN rev28 pin mismatch at "
                   "artifacts/formulation/evidence/taxonomy_consistency.json. The repair "
                   "sequence is therefore two owner actions, not one."),
        "repair_sequence": [
            "1. restore the 728-byte document 675a99d0 at artifacts/formulation/evidence/taxonomy_consistency.json "
            "(or run the patched checker with --out <that path> --measured-at " + MEASURED_AT + " on the live core)",
            "2. bump artifacts/formulation/FROZEN.json to a new revision that re-pins that path at 675a99d0 "
            "(rev28 pins the overwritten 9e335e9b form, so step 1 alone creates one pin mismatch)",
            "3. emit the artifact event carrying the new FROZEN hash; then F1/F2a/F2b declared binds resolve simultaneously",
        ],
        "do_not": ("re-pin the schemas to 9e335e9b: R5 shows the schema bytes would leave "
                   "5476a3f2/cce9c601/55d0a1ea and create FROZEN mismatches, voiding every review "
                   "verdict bound to the frozen G-FORM hashes."),
    },
    "overall": overall,
    "falsifier": (
        "FALSIFIED IF any of: (a) the 728-byte carrier no longer hashes to "
        "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48; (b) the canonical "
        "path already carries 675a99d0 (repair applied) or FROZEN has already been bumped to pin "
        "675a99d0 (then the cascade finding is void); (c) FROZEN.json revision != 28 at "
        "measurement or its pin for artifacts/formulation/evidence/taxonomy_consistency.json is not "
        "9e335e9ba1bfcf77...; (d) the patched tool, run on the restored bytes with --measured-at "
        "2026-09-12T00:32:02+08:00, does not print UNCHANGED or does not preserve the bytes; "
        "(e) a re-run of this script on the same pinned inputs yields any check FAIL or a different "
        "carrier set for 675a99d0; or (f) any of the three schemas already declares a pin other "
        "than 675a99d0."
    ),
    "artifacts": [],
}

# persist raw + report, then hash the deliverables
RAW.mkdir(parents=True, exist_ok=True)
(RAW / "run_log.txt").write_text("\n".join(raw_log) + "\n")
(RAW / "sandbox_evidence_restored.json").write_bytes(carrier_bytes)
(RAW / "reconstruction_negative_controls.json").write_text(json.dumps(neg, indent=2) + "\n")
report_path = OUT / "report.json"
report_path.write_text(json.dumps(report, indent=2) + "\n")

for rel in ["audit_evbind_rehearsal.py", "README.md", "raw/run_log.txt",
            "raw/sandbox_evidence_restored.json", "raw/reconstruction_negative_controls.json"]:
    report["artifacts"].append({"path": str((OUT / rel).relative_to(ROOT)), "sha256": sha256_file(OUT / rel)})
report["self_hash_note"] = ("report.json is excluded from its own artifact list; its final "
                            "sha256 is carried by the outbox artifact event and the worker checkpoint.")
report_path.write_text(json.dumps(report, indent=2) + "\n")

print("\n== SUMMARY ==")
print(json.dumps(overall, indent=1))
print("controls_all_pass:", overall["controls_all_pass"])
sys.exit(0 if all(c["pass"] for c in checks) else 1)

#!/usr/bin/env python3
"""W038-GFORM-R2LIVETRUTH-01 -- independent live-truth check of the R2 consistency-evidence repair.

Scope (class-bound: AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN; nodes F1,F2a,F2b).

The rev12 class schemas declare f0_binding.consistency_evidence_sha256 = 675a99d0d25b.
The canonical path measures 9e335e9b (writer collision, worker-086). worker-043's R2 repair
restores the declared 728 B document and redirects the owner checker's write to a report path.
worker-043 measured hash reconstruction (E1) and durability against the clobber (E2/E4/E5).

This script tests three things those measurements do NOT establish:

  T2  LIVE-TREE TRUTH: does the restored document's consistency verdict still hold of the
      CURRENT inputs (re-derived with the canonical checker, output confined to a sandbox)?
  T3  EMBEDDED-HASH TRUTH: do the document's embedded input hashes equal the live inputs?
  T6  DRIFT VISIBILITY: after an edit to a field the checker does not compare but which is
      semantically load-bearing, does anything in the R2 fixpoint signal that the pinned
      document's embedded lead_contract_sha256 is now stale?

Every sandbox is a mirrored tree so the checker's ROOT (parents[3]) resolves inside it; the
canonical tree is read-only here and is hashed before and after to prove it.

Exit 0 = all pre-registered checks behaved as expected; 1 = an expectation failed; 2 = harness error.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

WS = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = WS / "artifacts" / "worker-038" / "r2_livetruth"
SB = OUT / "sandbox"
RAW = OUT / "raw"
CST = timezone(timedelta(hours=8))

DECLARED_PIN = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
LIVE_EVIDENCE = "artifacts/formulation/evidence/taxonomy_consistency.json"
RESTORE_CANDIDATE_086 = "artifacts/worker-086/evidence_collision/restore_candidate/taxonomy_consistency.675a99d0d25b.json"
RESTORE_CANDIDATE_043 = "artifacts/worker-043/w043d_r2_durability/raw/evidence_restored_675a99d0.json"
PATCHED_CHECKER = "artifacts/worker-043/w043d_r2_durability/patched_check_taxonomy_consistency.py"

# Files that must not move while this instrument runs (canonical closure + peer artifacts reviewed).
GUARD = [
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/VOCAB_ALIASES.json",
    "artifacts/formulation/tools/check_taxonomy_consistency.py",
    LIVE_EVIDENCE,
    "artifacts/formulation/FROZEN.json",
    RESTORE_CANDIDATE_086,
    RESTORE_CANDIDATE_043,
    PATCHED_CHECKER,
]

SANDBOX_INPUTS = {
    "research_map/formulation_taxonomy.yaml": "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml": "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/VOCAB_ALIASES.json": "artifacts/formulation/VOCAB_ALIASES.json",
    "artifacts/formulation/tools/check_taxonomy_consistency.py": "artifacts/formulation/tools/check_taxonomy_consistency.py",
    "artifacts/formulation/tools/patched_check_taxonomy_consistency.py": PATCHED_CHECKER,
}

REL_A = "research_map/formulation_taxonomy.yaml"
REL_B = "artifacts/formulation/formulation_taxonomy.yaml"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def guard() -> dict:
    return {rel: sha256(WS / rel) for rel in GUARD}


def build(case: str) -> Path:
    """Mirror the minimal tree into sandbox/<case>/ so the checker's ROOT resolves inside it."""
    root = SB / case
    if root.exists():
        shutil.rmtree(root)
    for dst, src in SANDBOX_INPUTS.items():
        d = root / dst
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(WS / src, d)
    (root / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    return root


def run(root: Path, tool: str) -> dict:
    p = subprocess.run(
        [sys.executable, str(root / tool)],
        cwd=str(root), capture_output=True, text=True, timeout=300,
    )
    return {"tool": tool, "exit": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


def read_json(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def edit_text(path: Path, old: str, new: str, expect: int = 1) -> dict:
    txt = path.read_text()
    n = txt.count(old)
    if n != expect:
        raise RuntimeError(f"anchor {old!r} found {n} times (expected {expect}) in {path}")
    path.write_text(txt.replace(old, new))
    return {"anchor": old, "replacement": new, "occurrences": n}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    SB.mkdir(parents=True, exist_ok=True)

    pre = guard()
    report: dict = {
        "schema_version": "0.1",
        "task_id": "W038-GFORM-R2LIVETRUTH-01",
        "actor": "worker-038",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "gate": "G-FORM",
        "node_ids": ["F1", "F2a", "F2b"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "authority": "measurement only; no canonical write, no gate verdict, no promotion",
        "declared_pin": DECLARED_PIN,
        "canonical_pre": pre,
        "cases": {},
        "checks": {},
        "non_claims": [
            "Not a mathematics or physics claim; a mechanical artifact-and-checker result.",
            "Does not re-diagnose the writer collision (workers 086/041/043/094 already did).",
            "Does not adopt R2; adoption belongs to the F1/F2a/F2b owner (lead-formulation).",
        ],
    }
    fail = []

    def check(cid: str, ok: bool, detail):
        report["checks"][cid] = {"pass": bool(ok), "detail": detail}
        if not ok:
            fail.append(cid)

    # ---- C1: the two preserved candidates are the same bytes and hash to the declared pin ----
    h086 = sha256(WS / RESTORE_CANDIDATE_086)
    h043 = sha256(WS / RESTORE_CANDIDATE_043)
    b086 = (WS / RESTORE_CANDIDATE_086).read_bytes()
    b043 = (WS / RESTORE_CANDIDATE_043).read_bytes()
    report["cases"]["C1_reconstruction"] = {
        "candidate_086": {"path": RESTORE_CANDIDATE_086, "sha256": h086, "bytes": len(b086)},
        "candidate_043": {"path": RESTORE_CANDIDATE_043, "sha256": h043, "bytes": len(b043)},
        "byte_identical": b086 == b043,
    }
    check("C1_reconstruction",
          h086 == DECLARED_PIN and h043 == DECLARED_PIN and b086 == b043,
          {"declared_pin": DECLARED_PIN, "h086": h086, "h043": h043, "byte_identical": b086 == b043})

    restored = json.loads(b086.decode())
    restored_core = {k: v for k, v in restored.items()
                     if k not in ("map_taxonomy_sha256", "lead_contract_sha256", "measured_at")}
    report["cases"]["C1_reconstruction"]["restored_core_keys"] = sorted(restored_core)

    # ---- C2: live-tree truth -- canonical checker re-derives the verdict from current inputs ----
    root_live = build("live")
    r_live = run(root_live, "artifacts/formulation/tools/check_taxonomy_consistency.py")
    live_out = read_json(root_live / LIVE_EVIDENCE)
    report["cases"]["C2_live_truth"] = {
        "run": r_live,
        "canonical_output_8keys": live_out,
        "restored_core": restored_core,
        "match": live_out == restored_core,
    }
    check("C2_live_truth", r_live["exit"] == 0 and live_out == restored_core,
          {"exit": r_live["exit"], "verdict_content_matches_restored": live_out == restored_core})

    # ---- C3: the restored document's embedded input hashes equal the live inputs ----
    live_a, live_b = sha256(WS / REL_A), sha256(WS / REL_B)
    emb = {"map_taxonomy_sha256": restored.get("map_taxonomy_sha256"),
           "lead_contract_sha256": restored.get("lead_contract_sha256")}
    report["cases"]["C3_embedded_hash_truth"] = {
        "live": {REL_A: live_a, REL_B: live_b},
        "embedded": emb,
        "match": emb["map_taxonomy_sha256"] == live_a and emb["lead_contract_sha256"] == live_b,
    }
    check("C3_embedded_hash_truth",
          emb["map_taxonomy_sha256"] == live_a and emb["lead_contract_sha256"] == live_b,
          {"live_a": live_a, "embedded_map_taxonomy_sha256": emb["map_taxonomy_sha256"],
           "live_b": live_b, "embedded_lead_contract_sha256": emb["lead_contract_sha256"]})

    # ---- C4: patched checker determinism + non-clobber of the restored bytes ----
    root_patch = build("patched")
    ev_path = root_patch / LIVE_EVIDENCE
    ev_path.write_bytes(b086)
    before = sha256(ev_path)
    r1 = run(root_patch, "artifacts/formulation/tools/patched_check_taxonomy_consistency.py")
    rep_path = root_patch / "artifacts/formulation/evidence/taxonomy_consistency_report.json"
    h_rep1 = sha256(rep_path) if rep_path.exists() else None
    core1 = read_json(rep_path)
    r2 = run(root_patch, "artifacts/formulation/tools/patched_check_taxonomy_consistency.py")
    h_rep2 = sha256(rep_path) if rep_path.exists() else None
    after = sha256(ev_path)
    report["cases"]["C4_patched_determinism"] = {
        "run1": r1, "run2": r2,
        "report_hash_run1": h_rep1, "report_hash_run2": h_rep2,
        "report_deterministic": h_rep1 == h_rep2 and h_rep1 is not None,
        "evidence_bytes_before": before, "evidence_bytes_after": after,
        "evidence_preserved": before == after == DECLARED_PIN,
        "report_content_matches_restored_core": core1 == restored_core,
        "report_path": "artifacts/formulation/evidence/taxonomy_consistency_report.json",
    }
    check("C4_patched_determinism",
          r1["exit"] == 0 and r2["exit"] == 0 and h_rep1 == h_rep2
          and before == after == DECLARED_PIN and core1 == restored_core,
          {"exits": [r1["exit"], r2["exit"]], "report_deterministic": h_rep1 == h_rep2,
           "evidence_preserved": before == after == DECLARED_PIN,
           "report_content_matches": core1 == restored_core})

    # ---- C5: instrument sensitivity control -- a COMPARED field must be caught ----
    root_cmp = build("compared_edit")
    bfile = root_cmp / REL_B
    m = edit_text(bfile, "components: {asymptotics: AF, censorship: SCC, matter: VAC, genericity: GEN, regularity_token: C2}",
                        "components: {asymptotics: AF, censorship: WCC, matter: VAC, genericity: GEN, regularity_token: C2}")
    r_cmp = run(root_cmp, "artifacts/formulation/tools/check_taxonomy_consistency.py")
    out_cmp = read_json(root_cmp / LIVE_EVIDENCE)
    report["cases"]["C5_compared_field_control"] = {
        "mutation": m, "mutated_b_sha256": sha256(bfile), "run": r_cmp,
        "errors": (out_cmp or {}).get("errors"),
        "detected": r_cmp["exit"] == 1 and bool((out_cmp or {}).get("errors")),
    }
    check("C5_compared_field_control",
          r_cmp["exit"] == 1 and bool((out_cmp or {}).get("errors")),
          {"exit": r_cmp["exit"], "errors": (out_cmp or {}).get("errors")})

    # ---- C6: drift visibility -- an UNCOMPARED but load-bearing field edit ----
    root_drift = build("drift_edit")
    bfile_d = root_drift / REL_B
    anchor = ('description: "Generic one-ended AF vacuum data with ADM mass > 0 whose MGHD is not '
              'geodesically complete, together with the assertion: the MGHD has no proper future C2 '
              'vacuum extension."')
    md = edit_text(bfile_d, anchor, anchor[:-1] + ' The extension may be assumed past-inextendible. [W038-DRIFT-PROBE]"')
    ev_d = root_drift / LIVE_EVIDENCE
    ev_d.write_bytes(b086)                       # the R2 fixpoint: restored bytes are pinned here
    r_drift_can = run(root_drift, "artifacts/formulation/tools/check_taxonomy_consistency.py")
    can_out = read_json(ev_d)                    # canonical checker OVERWRITES the evidence path
    ev_d.write_bytes(b086)                       # restore the R2 fixpoint for the patched run
    r_drift_pat = run(root_drift, "artifacts/formulation/tools/patched_check_taxonomy_consistency.py")
    pat_out = read_json(root_drift / "artifacts/formulation/evidence/taxonomy_consistency_report.json")
    drift_b_sha = sha256(bfile_d)
    embedded_b = restored.get("lead_contract_sha256")
    report["cases"]["C6_drift_visibility"] = {
        "mutation": md,
        "mutated_b_sha256": drift_b_sha,
        "embedded_lead_contract_sha256": embedded_b,
        "drift_measurable_from_pinned_doc": drift_b_sha != embedded_b,
        "canonical_run": {"exit": r_drift_can["exit"], "errors": (can_out or {}).get("errors"),
                          "consistent": (can_out or {}).get("consistent")},
        "patched_run": {"exit": r_drift_pat["exit"], "errors": (pat_out or {}).get("errors"),
                        "consistent": (pat_out or {}).get("consistent"),
                        "writes_to_pinned_path": False},
        "pinned_evidence_bytes_after_patched_run": sha256(ev_d),
        "automatic_signal_from_either_checker": bool((can_out or {}).get("errors")) or bool((pat_out or {}).get("errors")),
    }
    check("C6_drift_visibility",
          drift_b_sha != embedded_b
          and r_drift_can["exit"] == 0 and not (can_out or {}).get("errors")
          and r_drift_pat["exit"] == 0 and not (pat_out or {}).get("errors")
          and sha256(ev_d) == DECLARED_PIN,
          {"drift_measurable_from_pinned_doc": drift_b_sha != embedded_b,
           "canonical_exit": r_drift_can["exit"], "patched_exit": r_drift_pat["exit"],
           "automatic_signal": bool((can_out or {}).get("errors")) or bool((pat_out or {}).get("errors"))})

    # ---- C7: timestamp ordering inside the frozen pair R2 would create ----
    schema_checked_at = None
    sch = (WS / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml").read_text()
    for line in sch.splitlines():
        if "checked_at:" in line and "f0_binding" in line:
            schema_checked_at = line.split('checked_at: "')[1].split('"')[0]
    report["cases"]["C7_timestamp_order"] = {
        "schema_f0_binding_checked_at": schema_checked_at,
        "restored_measured_at": restored.get("measured_at"),
        "evidence_produced_after_declared_check": None,
    }
    if schema_checked_at and restored.get("measured_at"):
        after = restored["measured_at"] > schema_checked_at
        report["cases"]["C7_timestamp_order"]["evidence_produced_after_declared_check"] = after
        report["cases"]["C7_timestamp_order"]["delta_note"] = (
            "R2 keeps the schemas byte-identical, so the frozen closure would carry a binding whose "
            "declared check time precedes the evidence document it pins."
        )
    check("C7_timestamp_order",
          bool(schema_checked_at) and bool(restored.get("measured_at")),
          {"schema_checked_at": schema_checked_at, "measured_at": restored.get("measured_at")})

    # ---- C8: controls -- canonical closure unmoved; mutations confined to sandboxes ----
    post = guard()
    moved = {k: [pre[k], post[k]] for k in pre if pre[k] != post[k]}
    report["canonical_post"] = post
    report["canonical_drift"] = moved
    report["cases"]["C8_controls"] = {
        "guard_files": len(GUARD),
        "canonical_drift": moved,
        "sandbox_mutations_confined": all(str(SB) in str(p) for p in SB.rglob("*")),
        "frozen_revision": json.loads((WS / "artifacts/formulation/FROZEN.json").read_text())["revision"],
        "live_evidence_path_sha256": sha256(WS / LIVE_EVIDENCE),
    }
    check("C8_controls", not moved and sha256(WS / LIVE_EVIDENCE) != DECLARED_PIN,
          {"canonical_drift": moved, "frozen_revision": report["cases"]["C8_controls"]["frozen_revision"]})

    report["passed"] = not fail
    report["failed_checks"] = fail
    ts = datetime.now(CST).strftime("%Y%m%dT%H%M%S")
    (RAW / f"run_{ts}.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "failed_checks": fail,
                      "checks": {k: v["pass"] for k, v in report["checks"].items()}}, indent=1))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:  # harness error, not a measurement
        print(f"HARNESS ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(2)

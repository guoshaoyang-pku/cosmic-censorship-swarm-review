#!/usr/bin/env python3
"""W008-FORMSEP04-CANDIDATE-VALIDATION-01 (read-only on canonical paths).

Bounded class-bound task for worker-008 (deepseek-flash-08), node F2, gate
G-CLASSBIND, classes AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN.

Question: the live F2b (C0) bytes at FROZEN rev29 (b2ab6acb2bbe) still carry the two
owner-tracked containment defects (L-FORM-01).  worker-066 announced a rebased two-edit
repair candidate with sha256 84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40
but did not persist its bytes.  This harness

  (1) reconstructs those candidate bytes from the LIVE C0 bytes plus the two reference
      edits (edit pairs derived here from the rev12 archive vs the pinned rev12 candidate
      98f9ec83, NOT copied from worker-066's script text),
  (2) verifies the reconstruction reproduces the announced sha256 and is minimal
      (two changed lines, two changed YAML leaf paths, no metadata movement), and
  (3) runs the full FORM-SEP-04 X1-X5 acceptance battery plus the fail-closed dual
      containment checker on the candidate, on the live canonical control, and a
      wrong-expect-hash fail-closed control.

Worker-level measurement only.  No node completion, no gate verdict, no validation
promotion, no canonical path written.  Interpretation owned by astra-lead-formulation;
pre-publication decision support for the pending F2b rev14 repair.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "worker08" / "rev29_candidate"
CST = timezone(timedelta(hours=8))

TASK_ID = "W008-FORMSEP04-CANDIDATE-VALIDATION-01"
ASSIGNMENT_EVENT_ID = "assign-FORM-SEP-04-20260911T2331"
CLASS_IDS = ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
NODE_ID = "F2"
GATE = "G-CLASSBIND"
ANNOUNCED_CANDIDATE = "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40"

PATHS = {
    "c0_live": "schemas/af_scc_c0_vacuum.yaml",
    "c2_live": "schemas/af_scc_c2_vacuum.yaml",
    "f1_live": "schemas/af_wcc_vacuum.yaml",
    "frozen": "artifacts/formulation/FROZEN.json",
    "f0_taxonomy": "research_map/formulation_taxonomy.yaml",
    "rev12_archive": "artifacts/worker-066/f2b_rev29_containment_binding/pinned/"
                     "c0_rev12_archive__c0_live__af_scc_c0_vacuum.yaml",
    "ref_candidate": "artifacts/worker-066/f2b_rev29_containment_binding/pinned/"
                     "candidate_98f9ec83__af_scc_c0_vacuum.yaml",
    "battery": "artifacts/worker08/c2_c0_separation_audit.py",
    "dual": "artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py",
    "candidate": "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml",
}

PINS = {
    # measured at run time, asserted below
    "c0_live": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "c2_live": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "f1_live": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "frozen": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "f0_taxonomy": "0abb9ed8a96135c9",  # prefix check only
    "rev12_archive": "55d0a1ea9bda96b8",  # prefix check only
    "ref_candidate": "98f9ec83c487d692",  # prefix check only
}

EXPECTED_CHANGED_TRANSFER = "implication_ledger.forbidden_transfers[0].reason"
EXPECTED_CHANGED_MNC = "regularity.must_not_conflate[0]"


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def flat_leaves(node, prefix=""):
    """Flatten a YAML doc to {dotted.path: leaf} (lists indexed [i])."""
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(flat_leaves(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.update(flat_leaves(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = node
    return out


def extract_edit_pairs(rev12: str, ref: str):
    """Line-level diff rev12 -> reference candidate; require exactly two one-line hunks."""
    hunks = []
    cur = None
    for line in difflib.unified_diff(rev12.splitlines(), ref.splitlines(), n=0):
        if line.startswith("@@"):
            if cur:
                hunks.append(cur)
            cur = {"minus": [], "plus": []}
        elif cur is not None and line.startswith("-") and not line.startswith("---"):
            cur["minus"].append(line[1:])
        elif cur is not None and line.startswith("+") and not line.startswith("+++"):
            cur["plus"].append(line[1:])
    if cur:
        hunks.append(cur)
    return hunks


def run(cmd, expect_exit=None):
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    rec = {
        "command": " ".join(str(c) for c in cmd),
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "").strip().splitlines()[-6:],
        "stderr_tail": (proc.stderr or "").strip().splitlines()[-6:],
    }
    if expect_exit is not None:
        rec["expected_exit_code"] = expect_exit
        rec["exit_code_matches"] = proc.returncode == expect_exit
    return rec, proc


def load_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception as exc:  # noqa: BLE001
        return {"_unreadable": str(exc)}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    bundle = {
        "schema": "worker-008/formsep04-candidate-validation/v1",
        "task_id": TASK_ID,
        "actor": "worker-008",
        "agent_id": "deepseek-flash-08",
        "assigned_task_id": "FORM-SEP-04",
        "assignment_event_id": ASSIGNMENT_EVENT_ID,
        "class_ids": CLASS_IDS,
        "node_id": NODE_ID,
        "gate": GATE,
        "created_at": now(),
        "authority": (
            "Worker-level measurement only. No node completion, no gate verdict, no "
            "validation_status promotion, no theorem. Canonical paths read-only; the "
            "candidate is written only under artifacts/worker08/. Interpretation owned "
            "by astra-lead-formulation."
        ),
    }

    # ---- Step 0: pin the inputs ------------------------------------------------
    pins = {}
    for key, rel in PATHS.items():
        if key in ("battery", "dual", "candidate"):
            continue
        p = ROOT / rel
        if not p.is_file():
            print(f"FATAL missing input {rel}", file=sys.stderr)
            return 2
        h = sha_file(p)
        pins[key] = {"path": rel, "sha256": h}
    for key, expected in PINS.items():
        measured = pins[key]["sha256"]
        ok = measured.startswith(expected)
        pins[key]["expected_prefix"] = expected
        pins[key]["match"] = ok
        if not ok:
            print(f"FATAL pin drift {key}: {measured} !~ {expected}", file=sys.stderr)
            return 2
    frozen = load_json(ROOT / PATHS["frozen"])
    pins["frozen_revision"] = frozen.get("revision")
    pins["frozen_at"] = frozen.get("frozen_at")
    bundle["pins"] = pins

    c0_live = (ROOT / PATHS["c0_live"]).read_text()
    c2_live = (ROOT / PATHS["c2_live"]).read_text()
    rev12 = (ROOT / PATHS["rev12_archive"]).read_text()
    ref = (ROOT / PATHS["ref_candidate"]).read_text()

    # ---- Step 1: derive the two reference edits, apply to LIVE bytes -----------
    hunks = extract_edit_pairs(rev12, ref)
    if len(hunks) != 2 or any(len(h["minus"]) != 1 or len(h["plus"]) != 1 for h in hunks):
        print("FATAL reference diff is not exactly two one-line edits", file=sys.stderr)
        return 2
    edits = []
    candidate = c0_live
    for h in hunks:
        old, new = h["minus"][0], h["plus"][0]
        occurrences = candidate.count(old)
        if occurrences != 1:
            print(f"FATAL edit target not unique ({occurrences}): {old[:80]}", file=sys.stderr)
            return 2
        candidate = candidate.replace(old, new)
        edits.append({"from": old, "to": new, "unique_match": True})
    cand_path = ROOT / PATHS["candidate"]
    cand_path.write_text(candidate)
    cand_sha = sha_file(cand_path)

    diff_lines = [
        (i + 1, a, b)
        for i, (a, b) in enumerate(zip(c0_live.splitlines(), candidate.splitlines()))
        if a != b
    ]
    doc_live = yaml.safe_load(c0_live)
    doc_cand = yaml.safe_load(candidate)
    leaves_live, leaves_cand = flat_leaves(doc_live), flat_leaves(doc_cand)
    changed_leaves = sorted(
        p for p in set(leaves_live) | set(leaves_cand)
        if leaves_live.get(p, "<absent>") != leaves_cand.get(p, "<absent>")
    )
    metadata_paths = ("revision", "revised_at", "revision_history", "class_id",
                      "f0_binding", "class_contract_pointer")
    metadata_moved = [p for p in changed_leaves if p.startswith(metadata_paths)]
    bundle["reconstruction"] = {
        "method": (
            "edit pairs extracted by line diff (rev12 archive 55d0a1ea -> pinned rev12 "
            "candidate 98f9ec83), then applied to the LIVE rev13 C0 bytes with a "
            "uniqueness assertion per edit"
        ),
        "reference_candidate_sha256": pins["ref_candidate"]["sha256"],
        "announced_candidate_sha256": ANNOUNCED_CANDIDATE,
        "reconstructed_candidate_path": PATHS["candidate"],
        "reconstructed_candidate_sha256": cand_sha,
        "reproduces_announced_sha256": cand_sha == ANNOUNCED_CANDIDATE,
        "edits": edits,
        "changed_lines": [
            {"line": ln, "live": a, "candidate": b} for ln, a, b in diff_lines
        ],
        "changed_line_count": len(diff_lines),
        "changed_leaf_paths": changed_leaves,
        "metadata_leaf_paths_moved": metadata_moved,
        "minimal_surface_ok": (
            len(diff_lines) == 2
            and set(changed_leaves) == {EXPECTED_CHANGED_TRANSFER, EXPECTED_CHANGED_MNC}
            and not metadata_moved
        ),
    }

    # ---- Step 2: FORM-SEP-04 X1-X5 battery on candidate and canonical control --
    batt_cand_json = OUT / "battery_candidate.json"
    batt_cand_md = OUT / "battery_candidate.md"
    batt_canon_json = OUT / "battery_canonical_control.json"
    batt_canon_md = OUT / "battery_canonical_control.md"
    rec_bc, _ = run([
        sys.executable, PATHS["battery"],
        "--c2", PATHS["c2_live"], "--c0", PATHS["candidate"],
        "--out-json", str(batt_cand_json.relative_to(ROOT)),
        "--out-md", str(batt_cand_md.relative_to(ROOT)),
        "--label", "w008-candidate-validation",
    ])
    rec_bk, _ = run([
        sys.executable, PATHS["battery"],
        "--c2", PATHS["c2_live"], "--c0", PATHS["c0_live"],
        "--out-json", str(batt_canon_json.relative_to(ROOT)),
        "--out-md", str(batt_canon_md.relative_to(ROOT)),
        "--label", "w008-canonical-control",
    ])
    bc, bk = load_json(batt_cand_json), load_json(batt_canon_json)

    def battery_view(d):
        return {
            "verdict": d.get("verdict"),
            "hard_failures": d.get("hard_failures"),
            "X1_expectation_violations": (d.get("X1_pairwise") or {}).get("expectation_violations"),
            "X2_foreign_unjustified": (d.get("X2_foreign_semantics") or {}).get("unjustified_count"),
            "X2b_violations": (d.get("X2b_conclusion_axis") or {}).get("violations"),
            "X3_converse_assertions": (d.get("X3_implication_ledger") or {}).get("converse_assertions"),
            "X3c_containment_inversions": (d.get("X3c_containment_inversion") or {}).get("violations"),
            "X4_composite_regularity_violations": (d.get("X4_composite_regularity") or {}).get("violations"),
            "gate_runs": d.get("gate_runs"),
        }

    bundle["battery"] = {
        "tool": PATHS["battery"],
        "tool_sha256": sha_file(ROOT / PATHS["battery"]),
        "candidate": dict(battery_view(bc), run=rec_bc,
                          json_path=str(batt_cand_json.relative_to(ROOT)),
                          json_sha256=sha_file(batt_cand_json)),
        "canonical_control": dict(battery_view(bk), run=rec_bk,
                                  json_path=str(batt_canon_json.relative_to(ROOT)),
                                  json_sha256=sha_file(batt_canon_json)),
    }

    # ---- Step 3: fail-closed dual containment checker --------------------------
    dual_cand = OUT / "dual_candidate.json"
    dual_canon = OUT / "dual_canonical_control.json"
    dual_wrong = OUT / "dual_wrong_expect_control.json"
    rec_dc, _ = run([
        sys.executable, PATHS["dual"],
        "--c0", PATHS["candidate"], "--c2", PATHS["c2_live"],
        "--expect-c0", cand_sha, "--expect-c2", pins["c2_live"]["sha256"],
        "--label", "w008-candidate-validation", "--json", str(dual_cand.relative_to(ROOT)),
    ], expect_exit=0)
    rec_dk, _ = run([
        sys.executable, PATHS["dual"],
        "--c0", PATHS["c0_live"], "--c2", PATHS["c2_live"],
        "--expect-c0", pins["c0_live"]["sha256"], "--expect-c2", pins["c2_live"]["sha256"],
        "--label", "w008-canonical-control", "--json", str(dual_canon.relative_to(ROOT)),
    ], expect_exit=1)
    rec_dw, _ = run([
        sys.executable, PATHS["dual"],
        "--c0", PATHS["candidate"], "--c2", PATHS["c2_live"],
        "--expect-c0", "deadbeef" * 8, "--expect-c2", pins["c2_live"]["sha256"],
        "--label", "w008-wrong-expect-control", "--json", str(dual_wrong.relative_to(ROOT)),
    ], expect_exit=3)
    dc, dk, dw = load_json(dual_cand), load_json(dual_canon), load_json(dual_wrong)
    wrong_kinds = sorted({f.get("kind") for f in (dw.get("findings") or [])})
    fail_closed_ok = (
        rec_dw["exit_code"] == 3
        and dw.get("verdict") == "FAIL-CLOSED"
        and set(wrong_kinds) <= {"hash_mismatch"}
        and not (dw.get("checks") or {})
    )

    def dual_view(d, rec):
        return {
            "verdict": d.get("verdict"),
            "exit_code": d.get("exit_code"),
            "finding_kinds": sorted({f.get("kind") for f in (d.get("findings") or [])}),
            "findings": d.get("findings"),
            "inputs": d.get("inputs"),
            "run": rec,
        }

    bundle["dual_checker"] = {
        "tool": PATHS["dual"],
        "tool_sha256": sha_file(ROOT / PATHS["dual"]),
        "candidate": dict(dual_view(dc, rec_dc),
                          json_path=str(dual_cand.relative_to(ROOT)),
                          json_sha256=sha_file(dual_cand) if dual_cand.is_file() else None),
        "canonical_control": dict(dual_view(dk, rec_dk),
                                  json_path=str(dual_canon.relative_to(ROOT)),
                                  json_sha256=sha_file(dual_canon) if dual_canon.is_file() else None),
        "wrong_expect_control": {
            "run": rec_dw,
            "json_written": dual_wrong.is_file(),
            "verdict": dw.get("verdict"),
            "finding_kinds": wrong_kinds,
            "fail_closed": fail_closed_ok,
            "meaning": (
                "A re-pointed expectation cannot manufacture a verdict: the checker exits 3 "
                "with the sentinel verdict FAIL-CLOSED, a hash_mismatch finding and no checks."
            ),
        },
    }

    # ---- Step 4: verdict -------------------------------------------------------
    cand_clean = (bc.get("verdict") == "PASS" and not (bc.get("hard_failures") or [])
                  and (dc.get("verdict") == "PASS") and not (dc.get("findings") or []))
    canon_still_defective = (
        bk.get("verdict") == "FAIL"
        and (bk.get("X3c_containment_inversion") or {}).get("violations") == 1
        and dk.get("verdict") == "FAIL"
        and len(dk.get("findings") or []) == 3
    )
    repro_ok = bundle["reconstruction"]["reproduces_announced_sha256"]
    minimal_ok = bundle["reconstruction"]["minimal_surface_ok"]
    overall = ("CANDIDATE_CLEARS_FORMSEP04"
               if all([cand_clean, canon_still_defective, repro_ok, minimal_ok, fail_closed_ok])
               else "VALIDATION_INCONCLUSIVE_OR_FAILED")
    bundle["verdict"] = overall
    bundle["checks"] = {
        "reconstruction_reproduces_announced_hash": repro_ok,
        "repair_surface_minimal_two_lines_two_leaves": minimal_ok,
        "candidate_passes_formsep04_battery": cand_clean,
        "candidate_passes_dual_checker": dc.get("verdict") == "PASS" and not (dc.get("findings") or []),
        "canonical_still_fails_both_checkers": canon_still_defective,
        "wrong_expect_hash_fail_closed": fail_closed_ok,
    }
    bundle["falsifier"] = (
        "Any of: (a) the reconstructed candidate does not hash to "
        f"{ANNOUNCED_CANDIDATE}; (b) a FORM-SEP-04 X1-X5 battery run on the candidate "
        "returns any expectation violation, unjustified foreign-semantics hit, "
        "converse assertion, containment inversion, composite-regularity violation or "
        "hard failure; (c) the fail-closed dual checker returns any finding on the "
        "candidate; (d) the same battery/checker pair on the unrepaired live C0 "
        "b2ab6acb2bbe does not still return exactly the two known containment defects "
        "(X3c=1, dual=3 findings/2 kinds); (e) any moved leaf outside the two named "
        "repair paths, or a moved revision/f0_binding/pointer leaf."
    )
    bundle["limitations"] = [
        "Candidate bytes are non-canonical and were never published; the owner "
        "(astra-lead-formulation) owns any rev14 wording and re-freeze.",
        "The two repair fragments are the rev12 reference wording; a different owner "
        "wording would clear the same logical defects but hash differently.",
        "This does not re-adjudicate the normativity of the two carriers (done "
        "independently by worker-066) nor the metalinguistic scoping reading of H2.",
        "No gate verdict, node status or validation_status is set by this measurement.",
    ]
    bundle_path = ROOT / "artifacts/worker08/rev29_candidate_validation.json"
    bundle_path.write_text(json.dumps(bundle, indent=1, sort_keys=True) + "\n")

    # ---- Step 5: markdown report ----------------------------------------------
    lines = [
        "# W008-FORMSEP04-CANDIDATE-VALIDATION-01",
        "",
        f"- generated: {bundle['created_at']}",
        f"- node/gate/classes: F2 / G-CLASSBIND / AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        f"- verdict: **{overall}**",
        f"- live pins: C0 `{pins['c0_live']['sha256'][:12]}`, C2 `{pins['c2_live']['sha256'][:12]}`, "
        f"FROZEN rev{frozen.get('revision')} `{pins['frozen']['sha256'][:12]}` "
        f"(frozen_at {frozen.get('frozen_at')})",
        "",
        "## What was done",
        "",
        "1. Reconstructed worker-066's announced rebased F2b repair candidate from the LIVE",
        "   C0 bytes plus the two reference edit pairs, which were themselves derived by",
        "   line diff of the rev12 archive `55d0a1ea` against the pinned rev12 candidate",
        "   `98f9ec83` (not copied from worker-066's source text).",
        f"   Reconstruction hash `{cand_sha}` vs announced `{ANNOUNCED_CANDIDATE}`: "
        f"**{'MATCH' if repro_ok else 'MISMATCH'}**.",
        "2. Ran the full FORM-SEP-04 X1-X5 acceptance battery on the candidate and on the",
        "   live canonical control at the same instant.",
        "3. Ran the fail-closed dual containment checker on both, plus a wrong-expect-hash",
        "   fail-closed control.",
        "",
        "## Results",
        "",
        "| check | candidate | canonical control |",
        "|---|---|---|",
        f"| FORM-SEP-04 battery verdict | {bc.get('verdict')} | {bk.get('verdict')} |",
        f"| hard failures | {bc.get('hard_failures')} | {bk.get('hard_failures')} |",
        f"| X3c containment inversions | {(bc.get('X3c_containment_inversion') or {}).get('violations')} "
        f"| {(bk.get('X3c_containment_inversion') or {}).get('violations')} |",
        f"| dual checker verdict | {dc.get('verdict')} | {dk.get('verdict')} |",
        f"| dual findings | {len(dc.get('findings') or [])} | {len(dk.get('findings') or [])} |",
        "",
        "Repair surface: "
        f"{bundle['reconstruction']['changed_line_count']} changed lines, "
        f"changed leaves `{changed_leaves}`, metadata moved `{metadata_moved}`.",
        "",
        "## Falsifier",
        "",
        bundle["falsifier"],
        "",
        "## Limitations",
        "",
        *[f"- {x}" for x in bundle["limitations"]],
        "",
        "Worker-level measurement only; no gate verdict, node status or validation_status is set.",
        "",
        f"- candidate bytes: `{PATHS['candidate']}#{cand_sha[:12]}`",
        f"- this bundle: `artifacts/worker08/rev29_candidate_validation.json`",
    ]
    md_path = ROOT / "artifacts/worker08/rev29_candidate_validation.md"
    md_path.write_text("\n".join(lines) + "\n")

    # ---- Step 6: checkpoint ----------------------------------------------------
    checkpoint = {
        "schema": "worker-008/checkpoint/v1",
        "actor": "worker-008",
        "agent_id": "deepseek-flash-08",
        "task_id": TASK_ID,
        "created_at": now(),
        "node_id": NODE_ID,
        "gate": GATE,
        "class_ids": CLASS_IDS,
        "status": "worker-level complete; pending owner rev14 decision",
        "verdict": overall,
        "pins": {k: v["sha256"] for k, v in pins.items() if isinstance(v, dict)},
        "artifacts": {
            "validation_json": {"path": "artifacts/worker08/rev29_candidate_validation.json",
                                "sha256": sha_file(bundle_path)},
            "validation_md": {"path": "artifacts/worker08/rev29_candidate_validation.md",
                              "sha256": sha_file(md_path)},
            "candidate": {"path": PATHS["candidate"], "sha256": cand_sha},
            "battery_candidate": {"path": str(batt_cand_json.relative_to(ROOT)),
                                  "sha256": sha_file(batt_cand_json)},
            "dual_candidate": {"path": str(dual_cand.relative_to(ROOT)),
                               "sha256": sha_file(dual_cand)},
            "harness": {"path": "artifacts/worker08/rev29_candidate_validate.py",
                        "sha256": sha_file(Path(__file__))},
        },
        "falsifier": bundle["falsifier"],
        "next_action": "owner publishes the two-leaf F2b repair and re-freezes; re-run "
                       "artifacts/worker08/rev_rebind.py at the new revision",
    }
    ckpt_path = ROOT / "runtime/state/worker-008_candidate_validation_checkpoint.json"
    ckpt_path.write_text(json.dumps(checkpoint, indent=1, sort_keys=True) + "\n")

    print(json.dumps({
        "verdict": overall,
        "candidate_sha256": cand_sha,
        "reproduces_announced": repro_ok,
        "battery_candidate": bc.get("verdict"),
        "dual_candidate": dc.get("verdict"),
        "battery_canonical": bk.get("verdict"),
        "dual_canonical": dk.get("verdict"),
        "wrong_expect_exit": rec_dw["exit_code"],
        "checks": bundle["checks"],
        "bundle": str(bundle_path.relative_to(ROOT)),
        "checkpoint": str(ckpt_path.relative_to(ROOT)),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

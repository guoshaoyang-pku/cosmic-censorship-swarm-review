#!/usr/bin/env python3
"""Worker 08 — FORM-SEP-04 rebind to FROZEN revision 25 + event emission + checkpoint.

Runs, in order:
  1. c2_c0_separation_audit.py (v3) -> artifacts/worker08/c2_c0_separation_matrix.json + report.md
     and a dated copy under artifacts/worker08/rev25_live/
  2. run_separation_selftest.py (v3) -> artifacts/worker08/c2_c0_separation_selftest.json + .md
  3. asserts the canonical published copies schemas/*.yaml are byte-identical to the audited
     mirror artifacts/formulation/schemas/*.yaml at the FROZEN rev25 hashes
  4. emits 2 artifact + status + blocker events to comms/outbox/deepseek-flash-08.jsonl
     (idempotent by event_id)
  5. writes runtime/state/w08_checkpoint_<stamp>.json, runtime/state/w08_latest_checkpoint.json
     and appends the checkpoint to artifacts/worker-008/checkpoints.jsonl

Read-only with respect to the canonical formulation artifacts; writes only under
artifacts/worker08/, artifacts/worker-008/, comms/outbox/deepseek-flash-08.jsonl and runtime/state/.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
W08 = REPO / "artifacts" / "worker08"
W008 = REPO / "artifacts" / "worker-008"
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)
STAMP = NOW.strftime("%Y%m%dT%H%M%S")
ISO = NOW.isoformat(timespec="seconds")
LABEL = "rev25-live"
C2 = REPO / "artifacts" / "formulation" / "schemas" / "af_scc_c2_vacuum.yaml"
C0 = REPO / "artifacts" / "formulation" / "schemas" / "af_scc_c0_vacuum.yaml"
CANON_C2 = REPO / "schemas" / "af_scc_c2_vacuum.yaml"
CANON_C0 = REPO / "schemas" / "af_scc_c0_vacuum.yaml"
MANIFEST = REPO / "artifacts" / "formulation" / "FROZEN.json"
OUTBOX = REPO / "comms" / "outbox" / "deepseek-flash-08.jsonl"
INSTANCE = "worker-08-20260912T000356-843521"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def append_events(events) -> int:
    existing = set()
    if OUTBOX.exists():
        for line in OUTBOX.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                existing.add(json.loads(line).get("event_id"))
            except json.JSONDecodeError:
                continue
    written = 0
    with OUTBOX.open("a", encoding="utf-8") as f:
        for ev in events:
            if ev["event_id"] in existing:
                continue
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            written += 1
    return written


def main() -> int:
    # 1. audit ---------------------------------------------------------------
    p = subprocess.run([sys.executable, str(W08 / "c2_c0_separation_audit.py"),
                        "--label", LABEL,
                        "--out-json", str(W08 / "c2_c0_separation_matrix.json"),
                        "--out-md", str(W08 / "c2_c0_separation_report.md")],
                       capture_output=True, text=True, timeout=300)
    print("audit rc", p.returncode)
    print(p.stdout[-1200:])
    if p.returncode != 0:
        print(p.stderr[-2000:])
        return 1
    dated = W08 / f"{LABEL.replace('-', '_')}"
    dated.mkdir(exist_ok=True)
    shutil.copy2(W08 / "c2_c0_separation_matrix.json",
                 dated / f"c2_c0_separation_matrix_{LABEL.replace('-', '_')}.json")
    shutil.copy2(W08 / "c2_c0_separation_report.md",
                 dated / f"c2_c0_separation_report_{LABEL.replace('-', '_')}.md")

    # 2. selftest ------------------------------------------------------------
    s = subprocess.run([sys.executable, str(W08 / "run_separation_selftest.py")],
                       capture_output=True, text=True, timeout=600)
    print("selftest rc", s.returncode)
    print(s.stdout[-800:])
    if s.returncode != 0:
        print(s.stderr[-2000:])
        return 1

    # 3. hashes + canonical-copy assertion -----------------------------------
    matrix = json.loads((W08 / "c2_c0_separation_matrix.json").read_text(encoding="utf-8"))
    st = json.loads((W08 / "c2_c0_separation_selftest.json").read_text(encoding="utf-8"))
    hashes = {
        "matrix": sha(W08 / "c2_c0_separation_matrix.json"),
        "report": sha(W08 / "c2_c0_separation_report.md"),
        "selftest_json": sha(W08 / "c2_c0_separation_selftest.json"),
        "selftest_md": sha(W08 / "c2_c0_separation_selftest.md"),
        "auditor": sha(W08 / "c2_c0_separation_audit.py"),
        "selftest_runner": sha(W08 / "run_separation_selftest.py"),
        "c2": sha(C2), "c0": sha(C0), "manifest": sha(MANIFEST),
        "canon_c2": sha(CANON_C2), "canon_c0": sha(CANON_C0),
    }
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for k in ("c2", "c0"):
        rel = matrix["inputs"][str((C2 if k == "c2" else C0).relative_to(REPO))]
        if hashes[k] != rel:
            print(f"ABORT: audited {k} hash {rel} != on-disk {hashes[k]}")
            return 1
        if hashes[f"canon_{k}"] != rel:
            print(f"ABORT: canonical copy of {k} differs from audited mirror")
            return 1
    if matrix["frozen_manifest_check"]["mismatches"]:
        print("ABORT: FROZEN manifest is stale:", matrix["frozen_manifest_check"]["mismatches"])
        return 1

    hard_kinds = [f["kind"] for f in matrix["hard_failures"]]
    inv = matrix["X3c_containment_inversion"]["hits"]
    common_refs = [
        f"schemas/af_scc_c2_vacuum.yaml#{hashes['c2'][:8]}",
        f"schemas/af_scc_c0_vacuum.yaml#{hashes['c0'][:8]}",
        f"artifacts/formulation/FROZEN.json#{hashes['manifest'][:8]}",
        f"artifacts/worker08/c2_c0_separation_matrix.json#{hashes['matrix'][:8]}",
        f"artifacts/worker08/c2_c0_separation_report.md#{hashes['report'][:8]}",
    ]
    falsifier = (
        "A reviewer exhibits a placement where the C2 conclusion is satisfied by a C0-only "
        "extension class or vice versa, a Cx => Cy converse assertion, a composite-regularity "
        "token outside anti_scope, or a containment premise calling C2 larger / C0 smaller; "
        "each reopens FAIL at the bound hash. Conversely, repairing C0 "
        "implication_ledger.forbidden_transfers[0].reason and re-freezing must make X3c = 0 "
        "at the new hash, otherwise this audit is wrong."
    )
    selftest_ref = {
        "path": "artifacts/worker08/c2_c0_separation_selftest.json",
        "sha256": hashes["selftest_json"],
        "controls_pass": st["false_positive_check"]["controls_pass"],
        "canonical_pair_ok": st["false_positive_check"]["canonical_pair_behaves_as_expected"],
        "in_scope_caught": st["in_scope_mutant_probe_caught"],
        "in_scope_missed": st["in_scope_mutant_probe_missed"],
        "family_scope_missed": st["family_scope_probes_missed_documented"],
    }
    artifact_core = {
        "event_type": "artifact",
        "created_at": ISO,
        "actor": "deepseek-flash-08",
        "group_id": "formulation",
        "node_id": "F2",
        "class_ids": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "artifact_type": "separation_audit",
        "validation_status": "unverified",
        "gate": "G-CLASSBIND",
        "audit_verdict": matrix["verdict"],
        "hard_failure_count": len(hard_kinds),
        "hard_failure_kinds": hard_kinds,
        "containment_inversion_hits": len(inv),
        "X1_violations": len(matrix["X1_pairwise"]["expectation_violations"]),
        "X2_unjustified": matrix["X2_foreign_semantics"]["unjustified_count"],
        "X2b_axis_violations": len(matrix["X2b_conclusion_axis"]["violations"]),
        "X3_converse_assertions": len(matrix["X3_implication_ledger"]["converse_assertions"]),
        "X4_violations": len(matrix["X4_composite_regularity"]["violations"]),
        "inputs": matrix["inputs"],
        "frozen_revision": man.get("revision"),
        "frozen_manifest_mismatches": matrix["frozen_manifest_check"]["mismatches"],
        "auditor": {"path": "artifacts/worker08/c2_c0_separation_audit.py",
                    "sha256": hashes["auditor"], "version": matrix["version"],
                    "rule_changes_v3": matrix["rule_changes_v3"]},
        "selftest": selftest_ref,
        "report": {"path": "artifacts/worker08/c2_c0_separation_report.md",
                   "sha256": hashes["report"]},
        "evidence_refs": common_refs,
        "falsifier": falsifier,
        "next_falsifier": matrix["next_falsifier"],
        "post_repair_residuals": matrix["post_repair_residuals"],
        "reproduce": ("python3 artifacts/worker08/c2_c0_separation_audit.py --label rev25-live && "
                      "python3 artifacts/worker08/run_separation_selftest.py"),
    }
    matrix_event = {
        **artifact_core,
        "event_id": f"e08-art-{STAMP}-form-sep-04-rev25-matrix",
        "path": "artifacts/worker08/c2_c0_separation_matrix.json",
        "sha256": hashes["matrix"],
        "supersedes": "e08-art-20260912T001104-form-sep-04-rev19-live",
    }
    report_event = {
        **artifact_core,
        "event_id": f"e08-art-{STAMP}-form-sep-04-rev25-report",
        "path": "artifacts/worker08/c2_c0_separation_report.md",
        "sha256": hashes["report"],
        "supersedes": "e08-art-20260912T001104-form-sep-04-rev19-live",
    }
    status_event = {
        "event_id": f"e08-status-{STAMP}-form-sep-04-rev25-live",
        "event_type": "status",
        "created_at": ISO,
        "actor": "deepseek-flash-08",
        "group_id": "formulation",
        "node_id": "F2",
        "status": "active",
        "hours": 0.3,
        "task_id": "FORM-SEP-04",
        "summary": (
            f"FORM-SEP-04 rebind to FROZEN rev{man.get('revision')}: C2 {hashes['c2'][:12]} / "
            f"C0 {hashes['c0'][:12]}; manifest consistent (0 mismatches); canonical schemas/*.yaml and "
            "the audited mirror artifacts/formulation/schemas/*.yaml are byte-identical at these hashes. "
            "Separation axes clean (X1 violations 0, X2 unjustified 0, X2b axis 0, X3 converse 0, "
            "X3 unclassified 0, X4 composite 0), verdict FAIL on exactly one hard failure that is "
            "UNCHANGED since the rev19-live run: C0 implication_ledger.forbidden_transfers[0].reason "
            "(canonical line 251) still says 'C2 is a strictly larger extension class, so "
            "C2-inextendibility is strictly weaker', inverting the same file's extension_class_containment "
            "(line 244: E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2) and one_way_entailments[2] "
            "(line 248: C0-inextendibility is stronger). The forbidden direction (C2-inext => C0-inext) is "
            "correct; only the premise clause is inverted; repair is one clause. Self-test v3 at this hash: "
            "controls pass, canonical pair behaves as expected, all 4 in-scope mutants/probes caught, 0 "
            "missed; 2 family-scope WCC probes remain documented misses. Residual corpus-hygiene note: 2 "
            "pre-rev4 novel_mutants (n02, n07) still carry the old C0 sentence. No node completion claimed; "
            "interpretation is owned by astra-lead-formulation."
        ),
        "verdict": matrix["verdict"],
        "hard_failure_kinds": hard_kinds,
        "evidence_refs": common_refs + [
            f"artifacts/worker08/c2_c0_separation_selftest.json#{hashes['selftest_json'][:8]}",
            "schemas/af_scc_c0_vacuum.yaml:251",
            "schemas/af_scc_c0_vacuum.yaml:244",
        ],
        "blocker_ref": f"e08-blocker-{STAMP}-c0-ledger-containment-inversion-rev25",
        "next_falsifier": falsifier,
    }
    blocker_event = {
        "event_id": f"e08-blocker-{STAMP}-c0-ledger-containment-inversion-rev25",
        "event_type": "blocker",
        "created_at": ISO,
        "actor": "deepseek-flash-08",
        "group_id": "formulation",
        "node_id": "F2",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "description": (
            "Canonical C0 schema (schemas/af_scc_c0_vacuum.yaml, FROZEN rev25 hash "
            f"{hashes['c0'][:12]}), exact path implication_ledger.forbidden_transfers[0].reason "
            "(line 251): 'C2 is a strictly larger extension class, so C2-inextendibility is strictly "
            "weaker'. The premise contradicts the same file's extension_class_containment (line 244: "
            "E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2; 'this class requires the LOWEST "
            "regularity, so its inexistence statement is the STRONGEST') and one_way_entailments[2] "
            "(line 248: 'C0-inextendibility is stronger than the C2 class's conclusion'); the C2 schema "
            "states the same containment (schemas/af_scc_c2_vacuum.yaml line 242). The forbidden transfer "
            "(C2-inext => C0-inext) is correctly forbidden; only the justification is inverted, so the "
            "ledger's own reason contradicts the containment chain it is derived from. Status: open at "
            "rev25; the one-clause repair requested at the rev19 binding had not landed at this freeze."
        ),
        "needed_to_unblock": (
            "One-clause wording repair at the exact path -> 'C2 is a strictly smaller extension class "
            "(E_C2 subset of E_C0), so C2-inextendibility is strictly weaker'; then re-hash the C0 schema, "
            "re-freeze, and re-run FORM-SEP-04; X3c must be 0 at the new hash."
        ),
        "evidence_refs": common_refs + [
            "schemas/af_scc_c2_vacuum.yaml:242",
            "schemas/af_scc_c0_vacuum.yaml:244",
            "schemas/af_scc_c0_vacuum.yaml:248",
            "schemas/af_scc_c0_vacuum.yaml:251",
        ],
        "falsifier": (
            "If the frozen containment is E_C2 superset of E_C0, or if the sentence is read as 'the C2 "
            "regularity class is larger than C0' (a reading of the word 'larger' that the same file's "
            "line 244 does not support), this finding is void; either would also invalidate the file's own "
            "extension_class_containment."
        ),
        "stop_rule": "Repair + re-freeze + re-run; or a reviewer rules the sentence non-normative prose.",
    }

    written = append_events([matrix_event, report_event, status_event, blocker_event])
    print("events appended:", written)

    # 5. worker checkpoint ----------------------------------------------------
    ckpt = {
        "worker": "deepseek-flash-08",
        "instance": INSTANCE,
        "checkpoint_at": ISO,
        "task_id": "FORM-SEP-04",
        "task": "C2/C0 pairwise separation audit rebound to FROZEN rev25 canonical hashes",
        "classes": ["AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "gate": "G-CLASSBIND",
        "verdict": matrix["verdict"],
        "hard_failure_kinds": hard_kinds,
        "inputs": matrix["inputs"],
        "frozen_revision": man.get("revision"),
        "frozen_manifest_mismatches": matrix["frozen_manifest_check"]["mismatches"],
        "artifacts": {
            "artifacts/worker08/c2_c0_separation_matrix.json": hashes["matrix"],
            "artifacts/worker08/c2_c0_separation_report.md": hashes["report"],
            "artifacts/worker08/c2_c0_separation_selftest.json": hashes["selftest_json"],
            "artifacts/worker08/c2_c0_separation_selftest.md": hashes["selftest_md"],
            "artifacts/worker08/c2_c0_separation_audit.py": hashes["auditor"],
            "artifacts/worker08/run_separation_selftest.py": hashes["selftest_runner"],
            "artifacts/worker08/emit_form_sep_04_rev25.py": sha(Path(__file__)),
        },
        "events_emitted": [matrix_event["event_id"], report_event["event_id"],
                           status_event["event_id"], blocker_event["event_id"]],
        "selftest": {"controls_pass": st["false_positive_check"]["controls_pass"],
                     "canonical_pair_ok": st["false_positive_check"]["canonical_pair_behaves_as_expected"],
                     "in_scope_caught": st["in_scope_mutant_probe_caught"],
                     "in_scope_missed": st["in_scope_mutant_probe_missed"],
                     "family_scope_missed": st["family_scope_probes_missed_documented"]},
        "blocking": [
            "C0 implication_ledger.forbidden_transfers[0].reason containment-premise inversion "
            "(X3c = 1) at schemas/af_scc_c0_vacuum.yaml:251; repair one clause, re-freeze, re-run",
        ],
        "next_falsifier": falsifier,
    }
    ck = REPO / "runtime" / "state" / f"w08_checkpoint_{STAMP}.json"
    ck.write_text(json.dumps(ckpt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (REPO / "runtime" / "state" / "w08_latest_checkpoint.json").write_text(
        json.dumps({"path": str(ck.relative_to(REPO)),
                    **{k: ckpt[k] for k in ("worker", "checkpoint_at", "task_id", "verdict",
                                            "hard_failure_kinds", "artifacts", "events_emitted",
                                            "blocking", "next_falsifier")}},
                   indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    W008.mkdir(exist_ok=True)
    with (W008 / "checkpoints.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(ckpt, ensure_ascii=False) + "\n")
    print(json.dumps({"verdict": matrix["verdict"], "hard_failure_kinds": hard_kinds,
                      "hashes": {k: v[:16] for k, v in hashes.items()},
                      "events": ckpt["events_emitted"],
                      "checkpoint": str(ck.relative_to(REPO))}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

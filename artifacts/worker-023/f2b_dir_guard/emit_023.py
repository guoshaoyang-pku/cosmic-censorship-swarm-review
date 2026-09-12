#!/usr/bin/env python3
"""Emit W023-F2B-DIR-GUARD-01 upward events and write checkpoint 5.

Worker-level only: no `status=done`, no `validation_status=passed`, no gate verdict, no
canonical write. Fail-closed: refuses to emit if any live pin moved since the suite ran.

    python3 emit_023.py        # appends to comms/outbox/worker-023.jsonl, writes checkpoint
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")
STAMP = datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
ACTOR = "worker-023"
TASK = "W023-F2B-DIR-GUARD-01"
NODE = "F2b"
CLASS0, CLASS2 = "AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"

PINS_PATH = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_wcc_vacuum.yaml": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/formulation/tools/check_class_schema.py": "000e09e46b2fb4abc047c21e99165cbc55692f3132744fb27e84645609263aff",
}
FALSIFIER = ("Falsified if any fixture hash moves; the lint flags live/corrected fixtures at "
             "the pins; it fails to flag 84b5d3fa/48cadb72; the patched sandbox gate stops "
             "failing those two; or the diff stops applying to the FROZEN rev29 checker bytes. "
             "Re-run make_fixtures.py, run_suite.py, gen_gate_patch.py, run_gate_hook.py.")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


def main() -> int:
    # --- fail-closed pin check -------------------------------------------------------------
    measured = {k: sha(ROOT / k) for k in PINS_PATH}
    drift = {k: (PINS_PATH[k], v) for k, v in measured.items() if v != PINS_PATH[k]}
    if drift:
        print("PIN DRIFT, refusing to emit:", json.dumps(drift, indent=1))
        return 2
    sums = {}
    for line in (HERE / "SHA256SUMS").read_text().splitlines():
        h, p = line.split(None, 1)
        sums[p.strip().lstrip("./")] = h
    results = json.loads((HERE / "evidence/results.json").read_text())
    hook = json.loads((HERE / "evidence/gate_hook.json").read_text())
    if results["checks_passed"] != results["checks_total"] or hook["checks_passed"] != hook["checks_total"]:
        print("SUITE FAIL, refusing to emit")
        return 2

    events = []

    def artifact(name, atype, summary):
        p = HERE / name
        events.append({
            "event_id": f"w23-dirguard-{STAMP}-artifact-{p.stem.replace('_', '-')}",
            "event_type": "artifact", "created_at": NOW, "actor": ACTOR,
            "node_id": NODE, "class_id": CLASS0, "class_ids": [CLASS0, CLASS2], "gate": "G-FORM",
            "artifact_type": atype, "path": rel(p), "sha256": sums[name],
            "validation_status": "unverified",
            "summary": summary,
            "evidence_refs": [f"{rel(p)}#{sums[name][:12]}",
                              "artifacts/worker-023/f2b_dir_guard/evidence/results.json#"
                              + sums["evidence/results.json"][:12]],
            "falsifier": FALSIFIER,
        })

    artifact("containment_direction_lint.py", "instrument_proposal",
             "Proposed class-relative containment/entailment-direction predicate (R31): parses a "
             "schema's own one_way_entailments + extension_class_containment and classifies each "
             "direction-bearing sentence as consistent/inverted/unsupported/neutral. Non-canonical; "
             "read-only on frozen paths.")
    artifact("check_containment_direction.py", "instrument_cli",
             "CLI wrapper: exit 0 no inversion / 1 inversion / 2 unreadable or --expect-sha256 "
             "mismatch. Usable by reviewers today without adopting the gate hook.")
    artifact("proposed_gate_hook_R31.diff", "gate_hook_patch_proposal",
             "Minimal unified diff adding R31 to check_class_schema.py against the FROZEN rev29 "
             "pin 000e09e46b2f; applies cleanly (patch -p1 --dry-run rc 0). NOT applied. Adoption "
             "voids the rev29 instrument pin and requires lead-formulation + controller re-freeze.")
    artifact("sandbox/formulation/tools/check_class_schema.py", "sandbox_patched_gate",
             "Isolated patched copy of the canonical checker used for calibration only; the "
             "canonical file was not modified.")
    artifact("fixtures/MANIFEST.json", "fixture_manifest",
             "7 pinned fixtures (live C0/C2/WCC, candidates 84b5d3fa and 48cadb72e507, corrected "
             "9ab32ee39d00 and 51c253c46306) plus 5 derived mutants with pre-registered "
             "expectations and hashes.")
    artifact("evidence/results.json", "calibration_evidence",
             f"Direction-lint control suite: {results['checks_passed']}/{results['checks_total']} "
             "PASS. Lint flags both inverted repair candidates, clears live rev13 and both "
             "corrected candidates; canonical gate rc 0 on every fixture (blindness control).")
    artifact("evidence/gate_hook.json", "gate_hook_calibration",
             f"Canonical-vs-patched gate comparison: {hook['checks_passed']}/{hook['checks_total']} "
             "PASS. Patched gate fails f03/f04 and the m09/m10 reversal mutants with R31, passes "
             "live/corrected; canonical gate passes all twelve.")
    artifact("README.md", "task_readme",
             "Task rationale, pins, predicate semantics, calibration tables, reproduce commands, "
             "limits, non-claims and falsifier.")

    events.append({
        "event_id": f"w23-dirguard-{STAMP}-claim",
        "event_type": "claim", "created_at": NOW, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS0, "class_ids": [CLASS0, CLASS2], "gate": "G-FORM",
        "conclusion_type": "methodological_finding",
        "statement": ("At the pinned FROZEN rev29 bytes, the H1/H2 containment repair candidates "
                      "84b5d3fa29a6 and 48cadb72e507 each assert one entailment reversal in "
                      "regularity.must_not_conflate that the canonical R06 does not see, while the "
                      "corrected candidates 9ab32ee39d00 and 51c253c46306 and the live rev13 bytes "
                      "carry none; a class-relative direction predicate detects the reversal, is "
                      "calibrated on 5 mutants and clears the corrected variants. The predicate is "
                      "delivered as an R31 hook proposal, not as an applied canonical change."),
        "assumptions": [
            "document-internal semantics only: one_way_entailments(X->Y) means E_Y subset of E_X, "
            "as the C0/C2 documents themselves state",
            "English lexical forms only; unparsed slot text is reported as unclassified, never certified",
            "fixture bytes pinned in fixtures/MANIFEST.json; any hash move voids the measurement",
        ],
        "falsifier": FALSIFIER,
        "evidence_refs": [
            "artifacts/worker-023/f2b_dir_guard/evidence/results.json#"
            + sums["evidence/results.json"][:12],
            "artifacts/worker-023/f2b_dir_guard/evidence/gate_hook.json#"
            + sums["evidence/gate_hook.json"][:12],
            "schemas/af_scc_c0_vacuum.yaml#" + PINS_PATH["schemas/af_scc_c0_vacuum.yaml"][:12],
            "schemas/af_scc_c2_vacuum.yaml#" + PINS_PATH["schemas/af_scc_c2_vacuum.yaml"][:12],
        ],
        "artifact_refs": [
            "artifacts/worker-023/f2b_dir_guard/containment_direction_lint.py#"
            + sums["containment_direction_lint.py"][:12],
            "artifacts/worker-023/f2b_dir_guard/proposed_gate_hook_R31.diff#"
            + sums["proposed_gate_hook_R31.diff"][:12],
            "artifacts/worker-023/f2b_dir_guard/fixtures/MANIFEST.json#"
            + sums["fixtures/MANIFEST.json"][:12],
        ],
    })

    events.append({
        "event_id": f"w23-dirguard-{STAMP}-status",
        "event_type": "status", "created_at": NOW, "actor": ACTOR,
        "node_id": NODE, "class_id": CLASS0, "class_ids": [CLASS0, CLASS2], "gate": "G-FORM",
        "status": "active", "hours": 0.4,
        "summary": ("CHECKPOINT + EXIT. One bounded class-bound task (W023-F2B-DIR-GUARD-01) "
                    "self-selected from worker-023's own prior blocker needed_to_unblock: the "
                    "instrument half (add a containment/entailment-direction predicate so R06/R16 "
                    "certify slot content). Delivered: lint + R31 hook diff + 12-fixture control "
                    "suite (21/21) + gate-hook calibration (28/28). Canonical paths read-only; the "
                    "canonical gate still passes both inverted candidates at the pins. No inbox "
                    "card existed for worker-023."),
        "next_falsifier": FALSIFIER,
        "evidence_refs": [
            "artifacts/worker-023/f2b_dir_guard/README.md#" + sums["README.md"][:12],
            "artifacts/worker-023/f2b_dir_guard/evidence/results.json#"
            + sums["evidence/results.json"][:12],
            "artifacts/worker-023/f2b_dir_guard/evidence/gate_hook.json#"
            + sums["evidence/gate_hook.json"][:12],
            "runtime/state/w023_checkpoint_5.json",
        ],
    })

    # --- schema-by-type validation before writing ----------------------------------------
    need = {"artifact": ("node_id", "artifact_type", "path", "sha256", "validation_status"),
            "claim": ("class_id", "statement", "conclusion_type", "assumptions", "falsifier",
                      "evidence_refs"),
            "status": ("node_id", "status", "hours", "summary", "evidence_refs", "next_falsifier")}
    for e in events:
        base = ("event_id", "event_type", "created_at", "actor")
        missing = [k for k in base + need[e["event_type"]] if k not in e]
        if missing:
            print("INVALID EVENT", e.get("event_id"), missing)
            return 2
        if e.get("validation_status") == "passed":
            print("refusing validation_status=passed (worker authority)")
            return 2

    out = ROOT / "comms/outbox/worker-023.jsonl"
    with out.open("a") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    ck = {
        "actor": ACTOR, "task_id": TASK, "created_at": NOW, "node_id": NODE,
        "class_id": CLASS0, "class_ids": [CLASS0, CLASS2], "gate": "G-FORM",
        "status": "complete",
        "verdict": (f"worker-level PASS: lint controls {results['checks_passed']}/"
                    f"{results['checks_total']}, gate-hook controls {hook['checks_passed']}/"
                    f"{hook['checks_total']}"),
        "artifacts": {k: v for k, v in sorted(sums.items())},
        "artifacts_abs": {k: str(HERE / k) for k in sorted(sums)},
        "pins": measured,
        "pin_drift": [],
        "canonical_writes": [],
        "events_emitted": len(events),
        "outbox": str(out.relative_to(ROOT)),
        "non_claims": [
            "not a gate verdict", "not a node completion", "not an applied canonical change",
            "not a claim about C0/C2 physics beyond the documents' declared entailment direction",
            "not a claim that F2b's other defect families (A2/A6/SEP-6) are closed",
        ],
        "adoption_note": ("R31 adoption changes the frozen instrument hash and voids the FROZEN "
                          "rev29 pin; lead-formulation + controller decision, not this worker's"),
        "falsifier": FALSIFIER,
        "next_falsifier": FALSIFIER,
    }
    ckpath = ROOT / "runtime/state/w023_checkpoint_5.json"
    ckpath.write_text(json.dumps(ck, indent=2, sort_keys=True))

    # --- re-read the appended lines to confirm they parse ---------------------------------
    lines = out.read_text().splitlines()
    bad = 0
    for line in lines[-len(events):]:
        try:
            json.loads(line)
        except Exception:  # noqa: BLE001
            bad += 1
    print(f"emitted {len(events)} events to {out.relative_to(ROOT)}; unparsable={bad}; "
          f"checkpoint {ckpath.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

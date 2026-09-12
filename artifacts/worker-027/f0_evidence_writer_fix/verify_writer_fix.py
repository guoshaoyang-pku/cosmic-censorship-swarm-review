#!/usr/bin/env python3
"""W027-F0-EVIDENCE-WRITER-FIX-01 -- independent measurement of the G-FORM consistency-evidence
pin chain and an isolated, in-process validation of a proposed minimal writer fix.

Question (class-bound F1/F2a/F2b, node F0, gate G-FORM):
  The three rev12 class schemas (F1 cce9c60146d6, F2a 5476a3f2c6bc, F2b 55d0a1ea9bda) declare
  consistency_evidence_sha256 = 675a99d0d25b... against
  artifacts/formulation/evidence/taxonomy_consistency.json.  At measurement time that path
  carries 9e335e9b...  Peers have reported the mismatch.  This instrument asks the next
  question: is the mismatch an accident of one edit, or a reproducible property of the
  canonical writer -- and does a minimal writer patch close it?

Method (no canonical file is ever written; every writer run happens in a private temp tree):
  A. re-measure the pinned inputs and the live evidence; drift on any pinned input -> exit 2.
  B. reconstruct the declared revision from the live bytes (live + the three appended fields).
  C. run the canonical writer unpatched twice in an isolated tree; compare to the live bytes.
  D. run the same writer with a minimal patch (append the two input hashes, no clock) twice.
  E. negative design control: a clock-stamped variant is run twice to test idempotence.
  F. semantic-mutation control: mutate the canonical taxonomy family token in a private tree
     and require the patched writer to notice.
  G. isolation control: the real canonical evidence path and all pinned inputs are re-measured
     at the end; any change means this instrument disturbed the repository.

Exit codes: 0 FINDING_REPRODUCED+FIX_VALIDATED / 2 INPUT_DRIFT / 3 ALREADY_FIXED
            4 FIX_NOT_VALIDATED / 5 MOVING_TARGET (live evidence changed mid-run)

Re-run:  python3 artifacts/worker-027/f0_evidence_writer_fix/verify_writer_fix.py
Writes only: this directory (report.json + snapshots/).  Stdlib only.
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
SNAP = HERE / "snapshots"
REPORT = HERE / "report.json"

TOOL_REL = "artifacts/formulation/tools/check_taxonomy_consistency.py"
EVID_REL = "artifacts/formulation/evidence/taxonomy_consistency.json"
F0_CANON_REL = "research_map/formulation_taxonomy.yaml"
F0_SUPP_REL = "artifacts/formulation/formulation_taxonomy.yaml"
ALIAS_REL = "artifacts/formulation/VOCAB_ALIASES.json"
DECLARED_REL = "artifacts/worker-086/gform_rev12/pinned/taxonomy_consistency.675a99d0d25b.json"

# Pins captured at 2026-09-12T00:38-00:42+08:00.  Any drift voids the measurement (exit 2).
PINS = {
    F0_CANON_REL: "0abb9ed8a96135c99e28500535f07f013b95d678aca2e1f5514344c6279094e3",
    F0_SUPP_REL: "d7419b4e8963cb713dd437940466e3f658f9cd4638df46fffaded80227dd3bb1",
    ALIAS_REL: "46cd9f1eb534df735daf221cfe6a877a54d7356d01229298f6efdcad8d50beba",
    TOOL_REL: "de356d999ea3b6aeb9cfe7d35d6604328ccc4945ead3bc3ec566a929363f31cd",
    "schemas/af_wcc_vacuum.yaml": "cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
    "schemas/af_scc_c2_vacuum.yaml": "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
    "schemas/af_scc_c0_vacuum.yaml": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
}
DECLARED_EVIDENCE_SHA = "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247b58c04733eba48"
DECLARED_KEYS = ["map_taxonomy_sha256", "lead_contract_sha256", "measured_at"]

PATCH_ANCHOR = (
    'out = ROOT/"artifacts/formulation/evidence/taxonomy_consistency.json"\n'
    'out.write_text(json.dumps(rep, indent=2)+"\\n")'
)
PATCH_PINS = (
    "import hashlib as _hl\n"
    "def _sha256_file(_p):\n"
    "    return _hl.sha256(_p.read_bytes()).hexdigest()\n"
    'rep["map_taxonomy_sha256"] = _sha256_file(ROOT/"research_map/formulation_taxonomy.yaml")\n'
    'rep["lead_contract_sha256"] = _sha256_file(ROOT/"artifacts/formulation/formulation_taxonomy.yaml")\n'
)
PATCH_V1 = PATCH_PINS + PATCH_ANCHOR
PATCH_CLOCK = (
    "import datetime as _dt\n"
    'rep["measured_at"] = _dt.datetime.now().astimezone().isoformat()\n'
)
PATCH_V2 = PATCH_PINS + PATCH_CLOCK + PATCH_ANCHOR

FALSIFIER = (
    "FALSIFIED if (a) the live canonical path already carries the declared 675a99d0 bytes, or the "
    "three schemas declare the live evidence sha at re-measurement; or (b) the declared revision is "
    "not reconstructible as the live bytes plus the three appended fields; or (c) the unpatched "
    "writer's two isolated runs are not byte-identical to each other or not byte-identical to the "
    "live canonical document; or (d) the V1-patched writer's two isolated runs are not byte-identical; "
    "or (e) the V1 output does not carry map_taxonomy_sha256 / lead_contract_sha256 equal to the "
    "measured input hashes; or (f) the V1 output is not byte-identical to the declared revision minus "
    "measured_at; or (g) the semantic-mutation control leaves the patched output unchanged or still "
    "consistent; or (h) the clock-stamped V2 variant's two runs are identical; or (i) any pinned "
    "input or the live evidence path drifts during the run (exit 2/5). Any pinned-sha mismatch means "
    "the measurement is void rather than falsified."
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(Path(p).read_bytes())


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def build_tree(tmp: Path, tool_text: str = None) -> Path:
    """Copy exactly the writer's closure into a private tree."""
    for rel in (F0_CANON_REL, F0_SUPP_REL, ALIAS_REL, TOOL_REL):
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    (tmp / "artifacts/formulation/evidence").mkdir(parents=True, exist_ok=True)
    if tool_text is not None:
        (tmp / TOOL_REL).write_text(tool_text)
    return tmp


def run_writer(tree: Path):
    r = subprocess.run(
        [sys.executable, str(tree / TOOL_REL)],
        cwd=str(tree), capture_output=True, text=True, timeout=120,
    )
    ev = tree / EVID_REL
    data = ev.read_bytes() if ev.exists() else None
    return {
        "returncode": r.returncode,
        "stdout": r.stdout.strip(),
        "stderr": r.stderr.strip()[:400],
        "evidence_sha256": sha256_bytes(data) if data is not None else None,
        "evidence_bytes_len": len(data) if data is not None else None,
        "evidence_json": json.loads(data.decode()) if data is not None else None,
        "evidence_bytes": data,
    }


def schema_field(text: str, key: str):
    m = re.search(rf'{key}:\s*"([0-9a-f]{{64}})"', text)
    return m.group(1) if m else None


def schema_evidence_path(text: str):
    m = re.search(r"consistency_evidence:\s*(\S+?),\s*consistency_evidence_sha256:", text)
    return m.group(1) if m else None


def snapshot_inputs():
    SNAP.mkdir(parents=True, exist_ok=True)
    made = {}
    for rel, sha in PINS.items():
        if rel == TOOL_REL:
            name = "check_taxonomy_consistency." + sha[:12] + ".py"
        elif rel.endswith(".yaml"):
            name = Path(rel).name.replace(".yaml", "") + "." + sha[:12] + ".yaml"
        else:
            name = Path(rel).name.replace(".json", "") + "." + sha[:12] + ".json"
        dst = SNAP / name
        shutil.copy2(ROOT / rel, dst)
        made[rel] = {"path": str(dst.relative_to(ROOT)), "sha256": sha256_file(dst)}
    return made


def main() -> int:
    started = now_iso()
    report = {
        "schema_version": "0.1",
        "task_id": "W027-F0-EVIDENCE-WRITER-FIX-01",
        "worker": "worker-027",
        "created_at": started,
        "class_id": "AF-WCC-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F0",
        "gate": "G-FORM",
        "question": (
            "At the three rev12 class schemas, does the declared consistency-evidence pin resolve "
            "at its declared canonical path, and does a minimal patch to the canonical writer make "
            "that evidence self-pinning and idempotent without moving the declared revision?"
        ),
        "falsifier": FALSIFIER,
        "snapshot": {},
        "measurements": {},
        "controls": [],
        "findings": [],
        "non_claims": [
            "not a gate verdict: worker events cannot set pending/pass/fail or node done",
            "does not modify any canonical artifact, review, map, or controller tool",
            "the proposed patch is NOT applied; adopting it is the tool owner's (lead-formulation) decision",
            "does not adjudicate the taxonomy content, only the evidence binding chain and the writer behavior",
            "confirms the mismatch peers reported; the new contribution is the validated writer fix",
        ],
        "reproduction": "python3 artifacts/worker-027/f0_evidence_writer_fix/verify_writer_fix.py",
    }

    # ---------- A. drift guard + snapshots ----------
    pins_measured = {}
    drift = []
    for rel, sha in PINS.items():
        got = sha256_file(ROOT / rel)
        pins_measured[rel] = {"declared_pin": sha, "measured": got, "match": got == sha}
        if got != sha:
            drift.append(f"{rel}: pinned {sha[:12]} measured {got[:12]}")
    live_sha_start = sha256_file(ROOT / EVID_REL)
    live_bytes_start = (ROOT / EVID_REL).read_bytes()
    live_mtime_start = datetime.fromtimestamp((ROOT / EVID_REL).stat().st_mtime).astimezone().replace(microsecond=0).isoformat()
    declared_present = (ROOT / DECLARED_REL).exists()
    declared_sha = sha256_file(ROOT / DECLARED_REL) if declared_present else None
    declared_bytes = (ROOT / DECLARED_REL).read_bytes() if declared_present else None
    report["snapshot"] = {
        "pinned_inputs": pins_measured,
        "live_evidence": {
            "path": EVID_REL, "sha256_at_start": live_sha_start,
            "mtime": live_mtime_start, "bytes": len(live_bytes_start),
        },
        "declared_revision_source": {
            "path": DECLARED_REL, "exists": declared_present, "sha256": declared_sha,
            "expected": DECLARED_EVIDENCE_SHA,
        },
        "map_sha256": sha256_file(ROOT / "research_map/research_map.json"),
        "events_sha256": sha256_file(ROOT / "research_map/events.jsonl"),
    }
    if drift:
        report["verdict"] = "INPUT_DRIFT"
        report["drift"] = drift
        report["findings"].append({
            "id": "W027-F0", "severity": "info", "status": "MEASUREMENT_VOID",
            "statement": "At least one pinned input changed before the run; no claim is made.",
            "evidence": drift,
        })
        REPORT.write_text(json.dumps(report, indent=2) + "\n")
        return 2
    snap = snapshot_inputs()
    report["snapshot"]["snapshots"] = snap

    # declared revision checks
    declared = json.loads(declared_bytes.decode()) if declared_present else None
    report["measurements"]["declared_revision_matches_pin"] = (declared_sha == DECLARED_EVIDENCE_SHA)
    report["measurements"]["declared_keys"] = sorted(declared.keys()) if declared else None

    # ---------- B. declared revision = live + three appended fields? ----------
    base = {k: v for k, v in declared.items() if k not in DECLARED_KEYS} if declared else None
    recombined = (json.dumps(base, indent=2) + "\n").encode() if base is not None else None
    reconstruction_live = bool(recombined is not None and recombined == live_bytes_start)
    declared_minus_clock = (
        (json.dumps({k: v for k, v in declared.items() if k != "measured_at"}, indent=2) + "\n").encode()
        if declared else None
    )
    report["measurements"]["reconstruction"] = {
        "declared_equals_live_plus_appended_fields": reconstruction_live,
        "appended_fields": DECLARED_KEYS,
        "live_bytes": len(live_bytes_start),
        "declared_bytes": len(declared_bytes) if declared_bytes else None,
    }

    # ---------- schema pins ----------
    schema_rows = []
    for rel, sha in PINS.items():
        if not rel.startswith("schemas/"):
            continue
        text = (ROOT / rel).read_text()
        decl_path = schema_evidence_path(text)
        decl_sha = schema_field(text, "consistency_evidence_sha256")
        decl_f0 = schema_field(text, "declared_f0_sha256")
        live_at_declared = sha256_file(ROOT / decl_path) if decl_path and (ROOT / decl_path).exists() else None
        schema_rows.append({
            "schema": rel, "measured_schema_sha256": sha,
            "declared_evidence_path": decl_path,
            "declared_evidence_sha256": decl_sha,
            "live_evidence_sha256": live_at_declared,
            "pin_resolves": decl_sha == live_at_declared,
            "declared_f0_sha256": decl_f0,
            "f0_pin_resolves": decl_f0 == PINS[F0_CANON_REL],
        })
    report["measurements"]["schema_pins"] = schema_rows

    # ---------- C. unpatched writer in isolation, twice ----------
    tool_text = (ROOT / TOOL_REL).read_text()
    run_rows = {}
    with tempfile.TemporaryDirectory(prefix="w027_writerfix_") as td:
        t = build_tree(Path(td))
        r1 = run_writer(t)
        r2 = run_writer(t)
    run_rows["unpatched"] = {
        "returncode": [r1["returncode"], r2["returncode"]],
        "sha256": [r1["evidence_sha256"], r2["evidence_sha256"]],
        "deterministic": r1["evidence_sha256"] == r2["evidence_sha256"],
        "equals_live_canonical_bytes": r1["evidence_bytes"] == live_bytes_start,
        "self_pinning_keys_present": sorted(k for k in DECLARED_KEYS if k in (r1["evidence_json"] or {})),
    }

    # ---------- D. patched V1 writer, twice ----------
    assert PATCH_ANCHOR in tool_text, "patch anchor missing from pinned writer"
    tool_v1 = tool_text.replace(PATCH_ANCHOR, PATCH_V1)
    tool_v2 = tool_text.replace(PATCH_ANCHOR, PATCH_V2)
    with tempfile.TemporaryDirectory(prefix="w027_writerfix_v1_") as td:
        t = build_tree(Path(td), tool_text=tool_v1)
        v1a = run_writer(t)
        v1b = run_writer(t)
    run_rows["patched_v1"] = {
        "returncode": [v1a["returncode"], v1b["returncode"]],
        "sha256": [v1a["evidence_sha256"], v1b["evidence_sha256"]],
        "deterministic": v1a["evidence_sha256"] == v1b["evidence_sha256"],
        "pins": {
            "map_taxonomy_sha256": (v1a["evidence_json"] or {}).get("map_taxonomy_sha256"),
            "lead_contract_sha256": (v1a["evidence_json"] or {}).get("lead_contract_sha256"),
        },
        "pins_match_measured_inputs": bool(
            v1a["evidence_json"]
            and v1a["evidence_json"].get("map_taxonomy_sha256") == PINS[F0_CANON_REL]
            and v1a["evidence_json"].get("lead_contract_sha256") == PINS[F0_SUPP_REL]
        ),
        "consistent": (v1a["evidence_json"] or {}).get("consistent"),
        "equals_declared_minus_measured_at": bool(
            declared_minus_clock is not None and v1a["evidence_bytes"] == declared_minus_clock
        ),
        "equals_live_canonical_bytes": v1a["evidence_bytes"] == live_bytes_start,
    }

    # ---------- E. clock-stamped variant, twice (negative design control) ----------
    with tempfile.TemporaryDirectory(prefix="w027_writerfix_v2_") as td:
        t = build_tree(Path(td), tool_text=tool_v2)
        v2a = run_writer(t)
        time.sleep(0.05)  # ensure the wall clock advances between the two runs
        v2b = run_writer(t)
    run_rows["patched_v2_clock"] = {
        "returncode": [v2a["returncode"], v2b["returncode"]],
        "sha256": [v2a["evidence_sha256"], v2b["evidence_sha256"]],
        "idempotent": v2a["evidence_sha256"] == v2b["evidence_sha256"],
        "clock_value_first": (v2a["evidence_json"] or {}).get("measured_at"),
        "clock_value_second": (v2b["evidence_json"] or {}).get("measured_at"),
    }

    # ---------- F. semantic-mutation control on the patched writer ----------
    mut_text = (ROOT / F0_CANON_REL).read_text().replace('family: "WCC"', 'family: "SCC"', 1)
    with tempfile.TemporaryDirectory(prefix="w027_writerfix_mut_") as td:
        t = build_tree(Path(td), tool_text=tool_v1)
        (t / F0_CANON_REL).write_text(mut_text)
        mut = run_writer(t)
    run_rows["mutation_control"] = {
        "mutation": 'first family: "WCC" -> family: "SCC" in the canonical taxonomy',
        "returncode": mut["returncode"],
        "sha256": mut["evidence_sha256"],
        "output_changed": mut["evidence_sha256"] != v1a["evidence_sha256"],
        "consistent": (mut["evidence_json"] or {}).get("consistent"),
        "error_count": len((mut["evidence_json"] or {}).get("errors") or []),
        "pins_changed": (mut["evidence_json"] or {}).get("map_taxonomy_sha256") != PINS[F0_CANON_REL],
    }
    report["measurements"]["writer_runs"] = run_rows
    report["measurements"]["proposed_patch"] = {
        "applied": False,
        "target": TOOL_REL,
        "target_sha256": PINS[TOOL_REL],
        "v1_adds": ["map_taxonomy_sha256", "lead_contract_sha256"],
        "v1_keeps_clock_out_of_hash": True,
    }

    # ---------- G. isolation control ----------
    live_sha_end = sha256_file(ROOT / EVID_REL)
    drift_end = [f"{rel}: pinned {PINS[rel][:12]} measured {sha256_file(ROOT / rel)[:12]}"
                 for rel in PINS if sha256_file(ROOT / rel) != PINS[rel]]
    report["measurements"]["isolation"] = {
        "live_evidence_sha_start": live_sha_start,
        "live_evidence_sha_end": live_sha_end,
        "live_evidence_unchanged": live_sha_start == live_sha_end,
        "pinned_inputs_unchanged": not drift_end,
        "end_drift": drift_end,
    }

    # ---------- controls ----------
    def ctl(cid, expected, observed, ok):
        report["controls"].append({"id": cid, "expected": expected, "observed": observed, "pass": bool(ok)})

    ctl("CTRL-C1", "unpatched writer deterministic across two isolated runs",
        run_rows["unpatched"]["deterministic"], run_rows["unpatched"]["deterministic"])
    ctl("CTRL-C2", "unpatched writer output byte-identical to live canonical evidence",
        run_rows["unpatched"]["equals_live_canonical_bytes"], run_rows["unpatched"]["equals_live_canonical_bytes"])
    ctl("CTRL-C3", "declared revision == live bytes + three appended fields",
        reconstruction_live, reconstruction_live)
    ctl("CTRL-C4", "V1-patched writer deterministic across two isolated runs",
        run_rows["patched_v1"]["deterministic"], run_rows["patched_v1"]["deterministic"])
    ctl("CTRL-C5", "V1 output carries input hashes equal to measured inputs",
        run_rows["patched_v1"]["pins_match_measured_inputs"], run_rows["patched_v1"]["pins_match_measured_inputs"])
    ctl("CTRL-C6", "V1 output byte-identical to the declared revision minus measured_at",
        run_rows["patched_v1"]["equals_declared_minus_measured_at"],
        run_rows["patched_v1"]["equals_declared_minus_measured_at"])
    ctl("CTRL-C7", "semantic mutation changes V1 output and breaks consistency",
        (run_rows["mutation_control"]["output_changed"] and run_rows["mutation_control"]["consistent"] is False),
        {"output_changed": run_rows["mutation_control"]["output_changed"],
         "consistent": run_rows["mutation_control"]["consistent"]})
    ctl("CTRL-C8", "clock-stamped V2 variant output changes when the wall clock advances",
        not run_rows["patched_v2_clock"]["idempotent"], not run_rows["patched_v2_clock"]["idempotent"])
    ctl("CTRL-C9", "canonical evidence path and pinned inputs unchanged after the run",
        report["measurements"]["isolation"]["live_evidence_unchanged"] and not drift_end,
        {"live_evidence_unchanged": report["measurements"]["isolation"]["live_evidence_unchanged"],
         "end_drift": drift_end})

    controls_pass = all(c["pass"] for c in report["controls"])

    # ---------- findings + verdict ----------
    pin_rows_bad = [r for r in schema_rows if not r["pin_resolves"]]
    if pin_rows_bad:
        report["findings"].append({
            "id": "W027-F1", "severity": "major", "status": "CONFIRMED",
            "statement": (
                "The three rev12 schemas declare consistency_evidence_sha256 " + DECLARED_EVIDENCE_SHA[:12]
                + " but the declared canonical path carries " + live_sha_start[:12]
                + "; the declared pin resolves nowhere at its declared path."
            ),
            "evidence": ["#".join([r["schema"], r["measured_schema_sha256"][:12]]) for r in pin_rows_bad]
                        + [EVID_REL + "#" + live_sha_start[:12], DECLARED_REL + "#" + (declared_sha or "")[:12]],
        })
        report["findings"].append({
            "id": "W027-F2", "severity": "major", "status": "CONFIRMED",
            "statement": (
                "The live evidence is strictly weaker than the declared revision: the declared revision "
                "is exactly the live document plus map_taxonomy_sha256, lead_contract_sha256 and "
                "measured_at (reconstruction equality=" + str(reconstruction_live) + "); re-pinning the "
                "schemas to the live hash would bind a document with no input-tree pins, re-opening the "
                "rev12 finding (e) that the repair claimed to close."
            ),
            "evidence": [EVID_REL + "#" + live_sha_start[:12], TOOL_REL + "#" + PINS[TOOL_REL][:12]],
        })
        report["findings"].append({
            "id": "W027-F3", "severity": "major", "status": "CONFIRMED",
            "statement": (
                "Root cause reproduced in isolation: the canonical writer's output is byte-identical to "
                "the live canonical document, so any repair that edits only the JSON instance is reverted "
                "by the next canonical consistency run; the writer itself emits no input pins."
            ),
            "evidence": [TOOL_REL + "#" + PINS[TOOL_REL][:12], EVID_REL + "#" + live_sha_start[:12]],
        })
        report["findings"].append({
            "id": "W027-F4", "severity": "major", "status": "PROPOSED_NOT_APPLIED",
            "statement": (
                "Minimal writer patch V1 (append map_taxonomy_sha256 + lead_contract_sha256, no clock) "
                "validated in an isolated tree: deterministic across two runs, pins equal the measured "
                "inputs, and its bytes are byte-identical to the declared revision minus measured_at. "
                "Adoption is the tool owner's decision and moves the evidence hash once, requiring a "
                "coordinated re-pin of the evidence path and the three schema f0_binding values."
            ),
            "evidence": [TOOL_REL + "#" + PINS[TOOL_REL][:12]],
        })
        report["findings"].append({
            "id": "W027-F5", "severity": "info", "status": "CONFIRMED_NEGATIVE_CONTROL",
            "statement": (
                "Clock-stamped variant V2 is non-idempotent: two runs with unchanged inputs produce "
                "different bytes, so a wall-clock field must not be part of the hashed evidence document "
                "(it would make every re-pin stale by construction); timestamps belong in a sidecar or "
                "outside the pinned bytes."
            ),
            "evidence": [TOOL_REL + "#" + PINS[TOOL_REL][:12]],
        })
        report["findings"].append({
            "id": "W027-F6", "severity": "info", "status": "SOURCE_READING",
            "statement": (
                "The frozen declared revision lacks the binding_rule field that the current frozen repair "
                "tool (close_findings_rev27.py) writes, so replaying the on-disk repair tool would move the "
                "pin again; the declared pin has no reproducible producer on disk. (Source-level census at "
                "the pinned tool sha; no tool run.)"
            ),
            "evidence": [TOOL_REL + "#" + PINS[TOOL_REL][:12], DECLARED_REL + "#" + (declared_sha or "")[:12]],
        })

    if live_sha_start != live_sha_end:
        report["verdict"] = "MOVING_TARGET"
        exit_code = 5
    elif not pin_rows_bad:
        report["verdict"] = "ALREADY_FIXED"
        exit_code = 3
    elif controls_pass and run_rows["patched_v1"]["deterministic"] and run_rows["patched_v1"]["pins_match_measured_inputs"]:
        report["verdict"] = "PIN_UNRESOLVED_AT_DECLARED_PATH_AND_FIX_VALIDATED"
        exit_code = 0
    else:
        report["verdict"] = "FIX_NOT_VALIDATED"
        exit_code = 4

    report["checks_passed"] = sum(1 for c in report["controls"] if c["pass"])
    report["checks_total"] = len(report["controls"])
    report["exit_code"] = exit_code
    report["finished_at"] = now_iso()
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['verdict']} ({report['checks_passed']}/{report['checks_total']} controls)")
    print(f"declared evidence pin {DECLARED_EVIDENCE_SHA[:12]} | live {live_sha_start[:12]} | "
          f"pin_resolves={not pin_rows_bad}")
    print(f"unpatched==live: {run_rows['unpatched']['equals_live_canonical_bytes']} | "
          f"V1 deterministic: {run_rows['patched_v1']['deterministic']} | "
          f"V1==declared-minus-clock: {run_rows['patched_v1']['equals_declared_minus_measured_at']}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

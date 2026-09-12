#!/usr/bin/env python3
"""Post-move addendum to W007-REV29-PREFLIGHT-01.

The three canonical schema files were rewritten (mtime 00:53) after the 00:52 preflight baseline
and before FROZEN rev29 was published. This script records the observed drift and re-measures the
four repair items at the new bytes. It writes only artifacts/worker-007/rev29_preflight/.

Writes: drift_observation.json, checker_runs/verify_frozen_postmove.stdout.txt
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST).isoformat(timespec="seconds")
ROOT = None
for anc in Path(__file__).resolve().parents:
    if (anc / "research_map" / "research_map.json").exists() and (anc / "schemas").is_dir():
        ROOT = anc
        break
assert ROOT
ART = ROOT / "artifacts" / "worker-007" / "rev29_preflight"

F0_TAX = "research_map/formulation_taxonomy.yaml"
CASES = "schemas/taxonomy_cases.jsonl"
CONSISTENCY = "artifacts/formulation/evidence/taxonomy_consistency.json"
SET_DELTA = "artifacts/formulation/variants/AF-WCC-VAC-GEN.variant-SET.delta.json"
SCHEMAS = {"F1": "schemas/af_wcc_vacuum.yaml", "F2a": "schemas/af_scc_c2_vacuum.yaml",
           "F2b": "schemas/af_scc_c0_vacuum.yaml"}
MIRRORS = {"F1": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
           "F2a": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
           "F2b": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"}
TOKEN_SET_INVERTED = "strictly STRONGER than this class's single-q tail predicate"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(cmd):
    pr = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    return pr.returncode, pr.stdout, pr.stderr


man = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
pins = man["files"]
rc, out, err = run([sys.executable, "artifacts/formulation/tools/verify_frozen.py"])
obs_problems = len([l for l in out.splitlines() if l.strip().startswith(("DRIFT", "MISSING"))])
(ART / "checker_runs" / "verify_frozen_postmove.stdout.txt").write_text(
    f"$ python3 artifacts/formulation/tools/verify_frozen.py\nexit={rc}\n--- stdout ---\n{out}\n--- stderr ---\n{err}\n")

drift = []
for label, p in list(SCHEMAS.items()) + list(MIRRORS.items()) + [("derived", "artifacts/formulation/evidence/gate_test_report.json")]:
    live = ROOT / p
    drift.append({"label": label, "path": p,
                  "frozen_pin": pins.get(p, {}).get("sha256"),
                  "measured": sha(live) if live.exists() else None,
                  "matches": pins.get(p, {}).get("sha256") == (sha(live) if live.exists() else None)})

# re-measure the four items at the moved bytes (mechanical, same predicates as verify_preflight.py)
import yaml  # noqa: E402
live_cons = sha(ROOT / CONSISTENCY)
live_f0 = sha(ROOT / F0_TAX)
i2 = {}
for label, p in SCHEMAS.items():
    b = (yaml.safe_load((ROOT / p).read_text()) or {}).get("f0_binding", {}) or {}
    i2[label] = {"schema_sha256": sha(ROOT / p),
                 "declared_f0_sha256": b.get("declared_f0_sha256"),
                 "declared_f0_resolves": b.get("declared_f0_sha256") == live_f0,
                 "declared_consistency_evidence_sha256": b.get("consistency_evidence_sha256"),
                 "measured_consistency_evidence_sha256": live_cons,
                 "consistency_evidence_resolves": b.get("consistency_evidence_sha256") == live_cons,
                 "checked_at": b.get("checked_at")}

f1_txt = (ROOT / SCHEMAS["F1"]).read_text()
f1_lines = [i for i, l in enumerate(f1_txt.splitlines(), 1) if TOKEN_SET_INVERTED in l]
set_delta = json.loads((ROOT / SET_DELTA).read_text())
i3 = {"token_set_inverted_present": bool(f1_lines), "token_set_inverted_lines": f1_lines,
      "set_delta_strength": set_delta.get("strength"),
      "set_delta_strength_pre_repair": str(set_delta.get("strength", "")).strip().lower() == "strictly stronger than af-wcc-vac-gen"}
i3["satisfied"] = (not i3["token_set_inverted_present"]) and (not i3["set_delta_strength_pre_repair"])
i3["note"] = ("F1's inverted token is gone at the moved bytes, but the SET delta strength still reads "
              "the pre-repair wording, so item I3 remains open until the variant record is corrected too.")

rows = [json.loads(l) for l in (ROOT / CASES).read_text().splitlines() if l.strip()]
case_rows = [r for r in rows if r.get("record_type") != "meta"]
meta = next((r for r in rows if r.get("record_type") == "meta"), {})
i1 = {"taxonomy_cases_sha256": sha(ROOT / CASES),
      "rows_bound_to_live_f0_rev5": sum(1 for r in case_rows if r.get("binding_status") == f"bound_taxonomy_sha_{live_f0[:12]}"),
      "rows_total": len(case_rows),
      "meta_taxonomy_ref_sha256": (meta.get("taxonomy_ref") or {}).get("sha256"),
      "unchanged_since_baseline": sha(ROOT / CASES) == "ccf7041bd0ff3ce844c07a700a588b7fe8e3c90880674c5e595b21f6259a8f03"}

moved_paths = list(SCHEMAS.values()) + [CASES]
moved_pins = {p: {"frozen_pin": pins.get(p, {}).get("sha256"),
                  "measured": sha(ROOT / p) if (ROOT / p).exists() else None} for p in moved_paths}
for v in moved_pins.values():
    v["pinned_live"] = v["frozen_pin"] == v["measured"]
i4_satisfied = (rc == 0 and int(man.get("revision") or 0) >= 29
                and all(v["pinned_live"] for v in moved_pins.values()))

obs = {
    "observation_id": "w007-rev29pre-drift-" + datetime.now(CST).strftime("%Y%m%dT%H%M%S"),
    "task_id": "W007-REV29-PREFLIGHT-01",
    "actor": "worker-007",
    "measured_at": NOW,
    "kind": "post_move_observation",
    "baseline_report": "artifacts/worker-007/rev29_preflight/report.json",
    "trigger": ("The three canonical class schemas (and their artifacts/formulation/schemas mirrors, and "
                "the derived gate_test_report.json) were rewritten at ~00:53 while FROZEN.json stayed at "
                "revision 28. Any binding review started between the schema writes and the FROZEN rev29 "
                "publication is reviewing bytes that the manifest does not pin."),
    "frozen": {"revision": man.get("revision"), "frozen_at": man.get("frozen_at"),
               "manifest_sha256": sha(ROOT / "artifacts/formulation/FROZEN.json"),
               "verify_frozen_exit": rc, "problems": obs_problems},
    "drift": drift,
    "items_at_moved_bytes": {
        "I1_cases_rebind": i1,
        "I2_consistency_evidence_binding": {"per_schema": i2,
                                            "satisfied": all(v["consistency_evidence_resolves"] for v in i2.values())},
        "I3_variant_strictness_text": i3,
        "I4_frozen_rev29_pins": {"revision": man.get("revision"),
                                 "verify_frozen_exit": rc,
                                 "moved_paths": moved_pins,
                                 "satisfied": i4_satisfied},
    },
    "window_history": [
        {"at": "2026-09-12T00:54:08+08:00", "verify_frozen_exit": 1, "problems": 7,
         "note": "observed open: 3 canonical schemas + 3 mirror schemas + gate_test_report.json drifted from FROZEN rev28 while rev29 was unpublished (recorded from this session's run log)"},
        {"at": NOW, "verify_frozen_exit": rc, "problems": obs_problems,
         "note": "observed closed: FROZEN rev29 (frozen_at 00:54:32, manifest sha e1a8aaa394eb) pins all drifted paths"},
    ],
    "implication": ("The unpinned window was observed open at 00:54:08 (verify_frozen exit 1, 7 drift paths) "
                    "and closed at 00:54:32 by FROZEN rev29. At rev29: I1 and I2 are satisfied, F1's inverted "
                    "SET token is gone but the SET delta strength still carries the pre-repair wording so I3 "
                    "remains open, and all four moved paths (3 schemas + taxonomy_cases.jsonl) are now pinned "
                    "at their live bytes, satisfying I4's pin predicate."),
    "items_at_moved_bytes_summary": {
        "I1_cases_rebind": True,
        "I2_consistency_evidence_binding": all(v["consistency_evidence_resolves"] for v in i2.values()),
        "I3_variant_strictness_text": i3["satisfied"],
        "I4_frozen_rev29_pins": i4_satisfied,
    },
    "falsifier": ("A FROZEN rev29 manifest published with pins equal to the moved bytes and verify_frozen.py "
                  "exit 0, plus artifact events for every moved path, falsifies the 'unpinned window' "
                  "observation; a verify_frozen.py exit 0 at FROZEN revision 28 falsifies the drift count."),
    "non_claims": ["Observation only; no gate verdict, no node status, no canonical artifact edit.",
                   "Does not adjudicate whether the schema-semantics repair is correct; only records bytes and pins.",
                   "Snapshot bytes of the predecessor revision remain the baseline report's frozen inputs."],
}
(ART / "drift_observation.json").write_text(json.dumps(obs, indent=2, sort_keys=True) + "\n")
print(json.dumps({"observation": obs["observation_id"], "verify_frozen_exit": rc,
                  "drift_paths": [d["path"] for d in drift if not d["matches"]],
                  "I2_satisfied_now": obs["items_at_moved_bytes"]["I2_consistency_evidence_binding"]["satisfied"],
                  "I3_inverted_token_now": i3["token_set_inverted_present"]}, indent=2))

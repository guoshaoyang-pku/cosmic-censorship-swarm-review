#!/usr/bin/env python3
"""W008-F2B-DUALREPAIR-01 addendum — rebase the same 2-edit repair onto rev12
and record the canonical-vs-FROZEN drift.

Bounded single pass, fail-closed: exits 3 unless the live canonical hashes match
the values measured for the rev12 publication (C0 55d0a1ea..., C2 5476a3f2...).
Writes evidence/rev12_addendum.json, candidate_rev12/af_scc_c0_vacuum.yaml and
evidence/controls/ctl*_rev12.json.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
sys.path.insert(0, str(ROOT))
from build_candidate import (OLD_BULLET, OLD_REASON, NEW_BULLET, NEW_REASON,  # noqa: E402
                             EXPECTED_PATHS, struct_diff, sha256_text)

C0_LIVE = REPO / "schemas" / "af_scc_c0_vacuum.yaml"
C2_LIVE = REPO / "schemas" / "af_scc_c2_vacuum.yaml"
C0_AUTHORING = REPO / "artifacts" / "formulation" / "schemas" / "af_scc_c0_vacuum.yaml"
C2_AUTHORING = REPO / "artifacts" / "formulation" / "schemas" / "af_scc_c2_vacuum.yaml"
FROZEN = REPO / "artifacts" / "formulation" / "FROZEN.json"
AUDIT = ROOT / "audit_dual_defect.py"
REV12_C0 = "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"
REV12_C2 = "5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce"
REV11_C0 = "1bb78ce9b3572cdac229ad7623ce96908bf4f08dc62c3c6264d97b17c0355508"
REV11_C2 = "b6123750b37d8bee1e92eeb025979a6afdf3b29a33331a9d8499e21398d13fb2"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_audit(c0: Path, expect_c0: str, label: str) -> dict:
    out = ROOT / "evidence" / f"audit_{label}.json"
    proc = subprocess.run([sys.executable, str(AUDIT), "--c0", str(c0), "--c2", str(C2_LIVE),
                           "--expect-c0", expect_c0, "--expect-c2", REV12_C2,
                           "--label", label, "--json", str(out)], capture_output=True, text=True)
    rep = json.loads(out.read_text())
    rep["exit_code_observed"] = proc.returncode
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    return rep


def main() -> int:
    live_c0, live_c2 = sha(C0_LIVE), sha(C2_LIVE)
    if (live_c0, live_c2) != (REV12_C0, REV12_C2):
        print(json.dumps({"verdict": "FAIL-CLOSED", "detail": "rev12 bases moved",
                          "measured": {"c0": live_c0, "c2": live_c2},
                          "expected": {"c0": REV12_C0, "c2": REV12_C2}}, indent=1))
        return 3
    frozen = json.loads(FROZEN.read_text())
    ff = frozen.get("files", {})
    drift = {
        "frozen_revision": frozen.get("revision"),
        "frozen_at": frozen.get("frozen_at"),
        "frozen_json_sha256": sha(FROZEN),
        "frozen_pins_c0": ff.get("schemas/af_scc_c0_vacuum.yaml", {}).get("sha256"),
        "frozen_pins_c2": ff.get("schemas/af_scc_c2_vacuum.yaml", {}).get("sha256"),
        "live_c0": live_c0, "live_c2": live_c2,
        "live_is_rev11": live_c0 == REV11_C0 and live_c2 == REV11_C2,
        "live_is_newer_than_freeze": live_c0 != ff.get("schemas/af_scc_c0_vacuum.yaml", {}).get("sha256"),
        "authoring_c0_live_sha256": sha(C0_AUTHORING),
        "authoring_c2_live_sha256": sha(C2_AUTHORING),
        "authoring_mirror_aligned": sha(C0_AUTHORING) == live_c0 and sha(C2_AUTHORING) == live_c2,
        "observation": (
            f"rev12 is inside the current freeze (FROZEN rev {frozen.get('revision')}, "
            f"{frozen.get('frozen_at')}): the two defects persist in the frozen set at the rev12 "
            f"hashes, and the same 2-edit repair rebases cleanly onto them. "
            + ("The canonical tree is currently AHEAD of the frozen manifest (drift)."
               if live_c0 != ff.get("schemas/af_scc_c0_vacuum.yaml", {}).get("sha256")
               else "No canonical/freeze drift at measurement time.")),
    }

    text = C0_LIVE.read_text()
    candidate = text
    edits = []
    for old, new, ypath in ((OLD_BULLET, NEW_BULLET, "regularity.must_not_conflate[0]"),
                            (OLD_REASON, NEW_REASON, "implication_ledger.forbidden_transfers[0].reason")):
        if candidate.count(old) != 1:
            print(json.dumps({"verdict": "FAIL-CLOSED",
                              "detail": f"cannot rebase {ypath}: occurrence count "
                                        f"{candidate.count(old)} != 1"}))
            return 3
        candidate = candidate.replace(old, new, 1)
        edits.append(ypath)
    changed_paths = struct_diff(__import__("yaml").safe_load(text), __import__("yaml").safe_load(candidate))
    cand_path = ROOT / "candidate_rev12" / "af_scc_c0_vacuum.yaml"
    cand_path.parent.mkdir(exist_ok=True)
    cand_path.write_text(candidate)
    cand_sha = sha256_text(candidate)
    minimality_ok = ({p for p, _ in changed_paths} == EXPECTED_PATHS
                     and sha256_text(text) == REV12_C0 and cand_sha != REV12_C0)

    canonical = run_audit(C0_LIVE, REV12_C0, "canonical_rev12_live")
    cand_rep = run_audit(cand_path, cand_sha, "candidate_rev12")
    # single-defect revert controls on the rev12 candidate
    ctl_dir = ROOT / "evidence" / "controls"
    (ctl_dir / "ctl1_revert251_rev12_c0.yaml").write_text(candidate.replace(NEW_REASON, OLD_REASON, 1))
    (ctl_dir / "ctl2_revert157_rev12_c0.yaml").write_text(candidate.replace(NEW_BULLET, OLD_BULLET, 1))
    ctl1 = run_audit(ctl_dir / "ctl1_revert251_rev12_c0.yaml",
                     sha256_text((ctl_dir / "ctl1_revert251_rev12_c0.yaml").read_text()),
                     "ctl1_revert251_rev12")
    ctl2 = run_audit(ctl_dir / "ctl2_revert157_rev12_c0.yaml",
                     sha256_text((ctl_dir / "ctl2_revert157_rev12_c0.yaml").read_text()),
                     "ctl2_revert157_rev12")
    kinds = lambda r: sorted({f["kind"] for f in r["findings"]})  # noqa: E731
    ok = (canonical["verdict"] == "FAIL"
          and kinds(canonical) == ["false_containment_denial", "size_premise_inverted"]
          and cand_rep["verdict"] == "PASS"
          and kinds(ctl1) == ["size_premise_inverted"]
          and kinds(ctl2) == ["false_containment_denial"]
          and minimality_ok)
    rec = {
        "task_id": "W008-F2B-DUALREPAIR-01",
        "addendum": "rev12 rebase + drift measurement",
        "worker": "worker-008", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
        "bases": {"c0": {"path": "schemas/af_scc_c0_vacuum.yaml", "sha256": live_c0},
                  "c2": {"path": "schemas/af_scc_c2_vacuum.yaml", "sha256": live_c2}},
        "canonical_rev12_audit": {"verdict": canonical["verdict"], "finding_kinds": kinds(canonical),
                                  "findings": canonical["findings"]},
        "candidate_rev12": {"path": "candidate_rev12/af_scc_c0_vacuum.yaml", "sha256": cand_sha,
                            "edits": edits, "changed_leaf_paths": [p for p, _ in changed_paths],
                            "minimality_ok": minimality_ok,
                            "audit_verdict": cand_rep["verdict"], "audit_finding_kinds": kinds(cand_rep)},
        "controls_rev12": {"ctl1_revert251": {"verdict": ctl1["verdict"], "kinds": kinds(ctl1)},
                           "ctl2_revert157": {"verdict": ctl2["verdict"], "kinds": kinds(ctl2)}},
        "frozen_drift": drift,
        "conclusion": ("The two consistency defects persist in the rev12 publication at new line numbers "
                       "(size premise: implication_ledger.forbidden_transfers[0].reason; denial: "
                       "regularity.must_not_conflate[0]). The same byte-minimal 2-edit repair rebases "
                       "cleanly onto rev12 and audits PASS; single-defect reverts each fail for exactly "
                       "one kind. Additionally the canonical tree moved ahead of FROZEN.json rev26 during "
                       "the run."),
        "all_expectations_met": ok,
        "falsifier": "A rev12 reading under which either sentence is consistent with the declared chain; "
                     "a candidate structural change outside the two leaf paths; or a canonical C0 hash "
                     "other than the bound rev12 hash at which these findings vanish.",
    }
    (ROOT / "evidence" / "rev12_addendum.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"ok": ok, "canonical_rev12": kinds(canonical), "candidate_rev12": cand_rep["verdict"],
                      "ctl1": kinds(ctl1), "ctl2": kinds(ctl2), "minimality_ok": minimality_ok,
                      "drift": drift["live_is_newer_than_freeze"], "candidate_sha256": cand_sha}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

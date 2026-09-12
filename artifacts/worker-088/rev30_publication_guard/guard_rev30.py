#!/usr/bin/env python3
"""W088-REV30-PUBLICATION-GUARD-01.

Independent, revision-fair guard on the rehearsed F2b rev30 publication path.

Question: worker-058's rehearsal (verdict REV30_FREEZE_REHEARSAL_READY) and its
OWNER_RUNBOOK prescribe copying
    artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml
(sha256 84b5d3fa...) over BOTH canonical schemas/af_scc_c0_vacuum.yaml copies and
re-freezing as revision 30.  worker-080 reports (at the same time) that this exact
candidate introduces a repair-introduced entailment inversion at its
regularity.must_not_conflate[0] carrier.  This instrument re-derives that question
from primary bytes with its own parsers, measures whether the rehearsal's own two
acceptance tools are blind to it, and independently checks the two corrected
candidates staged by worker-080.

Read-only on every canonical path.  Writes only under --out-dir (default: this
script's directory) plus the two /tmp scratch files handed to the pinned tools.

Exit codes: 0 = guard fired as expected, 2 = expectation failed, 3 = pin drift.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = "/data3/guoshaoyang/workdir/ai4math-swarm"

# ---------------------------------------------------------------------------
# Declared pins (measured before the run; any mismatch -> exit 3, fail closed)
# ---------------------------------------------------------------------------
PINS = {
    "schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/af_scc_c2_vacuum.yaml": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "artifacts/formulation/FROZEN.json": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml": "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
    "artifacts/worker-058/rev30_freeze_rehearsal/sandbox/schemas/af_scc_c0_vacuum.yaml": "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40",
    "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml": "51c253c463067e253dd32705f84d8ee089761439023acbbf1dd6660766191b7a",
    "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml": "4951cc96980329962829c2440c9e5c7f8ff5852eefd56aa48acfeeae8fb6505f",
    "artifacts/worker-058/rev30_freeze_rehearsal/report.json": "1e31bbe5e9336e688d3668850d4fdcd1f8bc28ee80baf064c1095cf847c1930c",
    "artifacts/worker-058/rev30_freeze_rehearsal/OWNER_RUNBOOK.md": "410f72e5121eb345dde05a2f9c4d5e99f059dabe1fce5a36578fd6eee21e21a6",
    "artifacts/worker-058/rev30_freeze_rehearsal/battery_rev30_candidate.json": "ac762882638031111f8a60cbbc4da502489b8656d9f2a66a7ba11c0bc32afd9c",
    "artifacts/worker-058/rev30_freeze_rehearsal/dual_rev30_candidate.json": "a96025b8fead2bef6281b4ee40e33898e5758cae543a398cd53cd8739c4ce4f4",
    "artifacts/worker08/c2_c0_separation_audit.py": "a19a7c87523f7fa35ce195b8375f0447f13dcff45ab4e61629062c7e08406a04",
    "artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py": "99b7a01ddfa62ef05ac80a973c13ea32ffcc93554fd39336d378b0c33a40ed7f",
    "artifacts/worker-080/f2b_repair_entailment_audit/report.json": "f0dae0292f1d1fe5a8d0a2a5a212758e1105f55df69ab65833bdef589b010eb3",
}

LIVE_C0 = "schemas/af_scc_c0_vacuum.yaml"
LIVE_C2 = "schemas/af_scc_c2_vacuum.yaml"
REHEARSED = "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml"
CORRECTED = "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_corrected.yaml"
NESTING = "artifacts/worker-080/f2b_repair_entailment_audit/staged/candidate_nesting_only.yaml"
RUNBOOK = "artifacts/worker-058/rev30_freeze_rehearsal/OWNER_RUNBOOK.md"
REPORT58 = "artifacts/worker-058/rev30_freeze_rehearsal/report.json"
SAND_C0 = "artifacts/worker-058/rev30_freeze_rehearsal/sandbox/schemas/af_scc_c0_vacuum.yaml"

H1_INVERTED = "H1_INVERTED_SIZE_PREMISE"
H1_FIXED = "H1_FIXED_SMALLER_PREMISE"
H1_UNCLASSIFIED = "H1_UNCLASSIFIED"

H2_DENIAL = "H2_DENIAL_NO_CONTAINMENT"
H2_INVERTED = "H2_INVERTED_ENTAILMENT_DIRECTION"
H2_CORRECT = "H2_CORRECT_DIRECTION"
H2_AGNOSTIC = "H2_AGNOSTIC_NESTING_ONLY"
H2_UNCLASSIFIED = "H2_UNCLASSIFIED"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: str) -> str:
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    with open(p, "r", encoding="utf-8") as fh:
        return fh.read()


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _parent_key(lines, idx):
    """Nearest preceding YAML key line with smaller indentation than `key:`."""
    indent = len(lines[idx]) - len(lines[idx].lstrip())
    for j in range(idx - 1, -1, -1):
        s = lines[j]
        if not s.strip():
            continue
        cur = len(s) - len(s.lstrip())
        if cur < indent and s.rstrip().endswith(":"):
            return s.strip()
    return None


def extract_bullets(text: str, key: str, parent: str = None):
    """Return [(value, line_no)] for every quoted bullet under the selected `key:`."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() != key + ":":
            continue
        if parent is None or _parent_key(lines, i) == parent + ":":
            start = i
            break
    out = []
    if start is None:
        return out
    for j in range(start + 1, len(lines)):
        line = lines[j]
        if not line.strip():
            continue
        m = re.match(r"^\s+-\s+(\".*\")\s*$", line)
        if m:
            try:
                out.append((json.loads(m.group(1)), j + 1))
            except json.JSONDecodeError:
                out.append((None, j + 1))
            continue
        if re.match(r"^\s*\S", line) and not line.startswith(" " * 4):
            break
    return out


def select_h2_carrier(bullets):
    """First regularity.must_not_conflate bullet that carries the H2_loc containment claim."""
    for value, line in bullets:
        if value and "H2_loc" in value and ("C2" in value or "C0" in value):
            return value, line
    return (bullets[0] if bullets else (None, None))


def extract_first_bullet(text: str, key: str, parent: str = None):
    """Return (value, line_no) of the selected bullet under `key:` (fail-closed on None)."""
    return select_h2_carrier(extract_bullets(text, key, parent))


def extract_line(text: str, n: int) -> str:
    lines = text.splitlines()
    return lines[n - 1] if 0 < n <= len(lines) else ""


COR_RE = re.compile(
    r"(?:this class's conclusion|C0-inextendibility)[^.]{0,80}?ENTAILS\s+H2_?loc-inextendibility"
)
INV_RE = re.compile(
    r"H2_?loc-inextendibility[^.]{0,80}?ENTAILS\s+(?:this class's conclusion|C0-inextendibility)"
)
DENIAL_RE = re.compile(r"(?:^|[.;]\s+)No containment with C2 or C0 is asserted")
NESTING_RE = re.compile(
    r"E_C2 subset of E_\{C\^1,1\} subset of E_H2loc subset of E_C0"
)
STRICT_BETWEEN_ASSERTIVE_RE = re.compile(r"sits strictly between")


def classify_h1(text: str) -> str:
    line = extract_line(text, 246)
    if "strictly larger extension class" in line:
        return H1_INVERTED
    if "strictly smaller extension class" in line and "E_C2 subset of E_C0" in line:
        return H1_FIXED
    return H1_UNCLASSIFIED


def classify_bullet(bullet: str, own: str) -> dict:
    """Class-relative direction classification of a must_not_conflate[0] bullet."""
    if bullet is None:
        return {
            "classification": H2_UNCLASSIFIED,
            "nesting_present": False,
            "this_class_entails_h2loc": False,
            "h2loc_entails_this_class": False,
            "denial_present": False,
            "assertive_strictly_between": False,
        }
    b = _norm(bullet)
    cor = bool(COR_RE.search(b))      # this class's conclusion => H2_loc-inext
    inv = bool(INV_RE.search(b))      # H2_loc-inext => this class's conclusion
    denial = bool(DENIAL_RE.search(b))
    nesting = bool(NESTING_RE.search(b))
    assertive_sb = bool(STRICT_BETWEEN_ASSERTIVE_RE.search(b))
    if own == "C0":
        # set chain E_C2 < E_{C^1,1} < E_H2loc < E_C0:
        # true: C0-inext => H2loc-inext => C2-inext
        correct, inverted = cor, inv
    elif own == "C2":
        # true in the C2 file: H2loc-inext => C2-inext
        correct, inverted = inv, cor
    else:
        raise ValueError("own must be C0 or C2")
    if denial:
        cls = H2_DENIAL
    elif inverted:
        cls = H2_INVERTED
    elif correct:
        cls = H2_CORRECT
    elif nesting:
        cls = H2_AGNOSTIC
    else:
        cls = H2_UNCLASSIFIED
    return {
        "classification": cls,
        "nesting_present": nesting,
        "this_class_entails_h2loc": cor,
        "h2loc_entails_this_class": inv,
        "denial_present": denial,
        "assertive_strictly_between": assertive_sb,
    }


def analyze_file(path: str, own: str) -> dict:
    p = path if os.path.isabs(path) else os.path.join(ROOT, path)
    text = read_text(p)
    bullet, bullet_line = extract_first_bullet(text, "must_not_conflate", parent="regularity")
    if bullet is None:
        bullet, bullet_line = extract_first_bullet(text, "must_not_conflate")
    out = {
        "path": path,
        "sha256": sha256_file(p),
        "h1_line_246": _norm(extract_line(text, 246)),
        "h1": classify_h1(text),
        "line_232": _norm(extract_line(text, 232)),
        "must_not_conflate_line": bullet_line,
        "must_not_conflate_0": bullet,
    }
    out.update(classify_bullet(bullet, own))
    out["intra_file_contradiction"] = bool(
        out["classification"] == H2_INVERTED and "not this class" in out["line_232"]
    )
    return out


def run_tool(cmd, out_json, keys):
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    res = {"command": cmd, "exit_code": proc.returncode, "stdout_tail": proc.stdout.strip().splitlines()[-3:]}
    if os.path.exists(out_json):
        try:
            data = json.load(open(out_json))
        except Exception as exc:  # pragma: no cover
            res["json_error"] = repr(exc)
            return res
        for k in keys:
            cur = data
            for part in k.split("."):
                cur = cur.get(part) if isinstance(cur, dict) else None
                if cur is None:
                    break
            res[k] = cur
        if isinstance(data.get("findings"), list):
            res["findings"] = data["findings"]
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    # ---- 1. pins -----------------------------------------------------------
    pin_report = {}
    drift = []
    for rel, declared in PINS.items():
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            drift.append({"path": rel, "problem": "MISSING", "declared": declared})
            continue
        measured = sha256_file(p)
        pin_report[rel] = {"declared": declared, "measured": measured, "match": measured == declared}
        if measured != declared:
            drift.append({"path": rel, "problem": "DRIFT", "declared": declared, "measured": measured})
    if drift:
        print(json.dumps({"verdict": "PIN_DRIFT_FAIL_CLOSED", "drift": drift}, indent=2))
        return 3

    # ---- 2. derive candidate states from primary bytes ---------------------
    live_c0 = analyze_file(LIVE_C0, "C0")
    live_c2 = analyze_file(LIVE_C2, "C2")
    rehearsed = analyze_file(REHEARSED, "C0")
    corrected = analyze_file(CORRECTED, "C0")
    nesting = analyze_file(NESTING, "C0")
    sand = analyze_file(SAND_C0, "C0")

    # ---- 3. link the rehearsal publication path to the candidate hash ------
    runbook_text = read_text(RUNBOOK)
    report58 = json.loads(read_text(REPORT58))
    runbook_prescribes_rehearsed = (
        "artifacts/worker08/rev29_candidate/af_scc_c0_vacuum.repair-candidate.yaml" in runbook_text
        and rehearsed["sha256"] in runbook_text
    )
    report58_candidate = (report58.get("candidate") or {}).get("sha256")
    report58_sandbox_candidate = (report58.get("sandbox") or {}).get("c0_candidate_sha256")
    publication_link = {
        "runbook_path": RUNBOOK,
        "runbook_sha256": sha256_file(os.path.join(ROOT, RUNBOOK)),
        "runbook_prescribes_rehearsed_candidate": runbook_prescribes_rehearsed,
        "runbook_declared_new_c0_sha256": rehearsed["sha256"],
        "rehearsal_report_verdict": report58.get("verdict"),
        "rehearsal_report_candidate_sha256": report58_candidate,
        "rehearsal_report_sandbox_c0_candidate_sha256": report58_sandbox_candidate,
        "rehearsal_sandbox_equals_candidate": sand["sha256"] == rehearsed["sha256"],
    }

    # ---- 4. run the rehearsal's OWN acceptance tools on the candidate ------
    c2_abs = os.path.join(ROOT, LIVE_C2)
    cand_abs = os.path.join(ROOT, REHEARSED)
    corr_abs = os.path.join(ROOT, CORRECTED)
    c2_sha = live_c2["sha256"]
    cand_sha = rehearsed["sha256"]
    scratch = os.path.join(out_dir, "_scratch")
    os.makedirs(scratch, exist_ok=True)

    battery_cand = run_tool(
        ["/usr/bin/python3", "artifacts/worker08/c2_c0_separation_audit.py",
         "--c2", c2_abs, "--c0", cand_abs,
         "--out-json", os.path.join(scratch, "battery_rehearsed.json"),
         "--out-md", os.path.join(scratch, "battery_rehearsed.md"), "--label", "w088_rehearsed"],
        os.path.join(scratch, "battery_rehearsed.json"),
        ["verdict", "X3c_containment_inversion.hits", "hard_failures"],
    )
    dual_cand = run_tool(
        ["/usr/bin/python3", "artifacts/worker-008/f2b_rev11_dualrepair/audit_dual_defect.py",
         "--c0", cand_abs, "--c2", c2_abs,
         "--expect-c0", cand_sha, "--expect-c2", c2_sha,
         "--label", "w088_rehearsed", "--json", os.path.join(scratch, "dual_rehearsed.json")],
        os.path.join(scratch, "dual_rehearsed.json"),
        ["verdict"],
    )
    battery_corr = run_tool(
        ["/usr/bin/python3", "artifacts/worker08/c2_c0_separation_audit.py",
         "--c2", c2_abs, "--c0", corr_abs,
         "--out-json", os.path.join(scratch, "battery_corrected.json"),
         "--out-md", os.path.join(scratch, "battery_corrected.md"), "--label", "w088_corrected"],
        os.path.join(scratch, "battery_corrected.json"),
        ["verdict", "X3c_containment_inversion.hits", "hard_failures"],
    )
    dual_cand["n_findings"] = len(dual_cand.get("findings") or [])

    # candidate-level blindness: both acceptance tools pass the rehearsed bytes
    band = {
        "battery_rehearsed": battery_cand,
        "dual_rehearsed": dual_cand,
        "battery_corrected": battery_corr,
    }
    acceptance_suite_blind = (
        battery_cand.get("verdict") == "PASS"
        and (battery_cand.get("hard_failures") or []) == []
        and dual_cand.get("verdict") == "PASS"
        and dual_cand.get("n_findings") == 0
    )

    # ---- 5. in-memory controls --------------------------------------------
    corr_bullet = corrected["must_not_conflate_0"]
    k5_bullet = corr_bullet.replace(
        "this class's conclusion (C0-inextendibility) therefore ENTAILS H2_loc-inextendibility, and "
        "H2_loc-inextendibility entails the C2 sibling's conclusion, not this class.",
        "H2_loc-inextendibility ENTAILS this class's conclusion.",
    )
    controls = {
        "K1_live_c0": live_c0["classification"],
        "K2_rehearsed_candidate": rehearsed["classification"],
        "K3_corrected_candidate": corrected["classification"],
        "K4_nesting_only_candidate": nesting["classification"],
        "K5_direction_flipped_in_memory": classify_bullet(k5_bullet, "C0")["classification"],
        "K6_live_denial_bullet_reimplanted": classify_bullet(live_c0["must_not_conflate_0"], "C0")["classification"],
        "K7_c2_live_own_C2": live_c2["classification"],
    }
    expected_controls = {
        "K1_live_c0": H2_DENIAL,
        "K2_rehearsed_candidate": H2_INVERTED,
        "K3_corrected_candidate": H2_CORRECT,
        "K4_nesting_only_candidate": H2_AGNOSTIC,
        "K5_direction_flipped_in_memory": H2_INVERTED,
        "K6_live_denial_bullet_reimplanted": H2_DENIAL,
        "K7_c2_live_own_C2": H2_CORRECT,
    }
    controls_ok = controls == expected_controls
    k5_changed = k5_bullet != corr_bullet

    # ---- 6. verdict --------------------------------------------------------
    expectations = {
        "live_c0_direction_defect": live_c0["classification"] == H2_DENIAL and live_c0["h1"] == H1_INVERTED,
        "rehearsed_candidate_h1_fixed": rehearsed["h1"] == H1_FIXED,
        "rehearsed_candidate_h2_inverted": rehearsed["classification"] == H2_INVERTED,
        "rehearsed_candidate_intra_file_contradiction": rehearsed["intra_file_contradiction"],
        "publication_path_links_rehearsed_candidate": runbook_prescribes_rehearsed
        and report58_candidate == cand_sha
        and report58_sandbox_candidate == cand_sha,
        "acceptance_suite_blind_to_h2_defect": acceptance_suite_blind,
        "corrected_candidate_h1_fixed": corrected["h1"] == H1_FIXED,
        "corrected_candidate_h2_correct": corrected["classification"] == H2_CORRECT,
        "corrected_candidate_no_contradiction": not corrected["intra_file_contradiction"],
        "nesting_candidate_h1_fixed": nesting["h1"] == H1_FIXED,
        "nesting_candidate_h2_agnostic": nesting["classification"] == H2_AGNOSTIC,
        "controls_match_expectations": controls_ok and k5_changed,
    }
    guard_fires = all(expectations.values())

    # ---- 7. drift re-check -------------------------------------------------
    drift_after = []
    for rel, declared in PINS.items():
        measured = sha256_file(os.path.join(ROOT, rel))
        if measured != declared:
            drift_after.append({"path": rel, "declared": declared, "measured": measured})
    expectations["no_drift_during_run"] = not drift_after

    result = {
        "schema": "worker-088/rev30-publication-guard/v1",
        "task_id": "W088-REV30-PUBLICATION-GUARD-01",
        "worker": "worker-088",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "pins": pin_report,
        "live_c0": live_c0,
        "live_c2_class_relative_control": live_c2,
        "rehearsed_candidate": rehearsed,
        "corrected_candidate": corrected,
        "nesting_only_candidate": nesting,
        "rehearsal_sandbox_c0": sand,
        "publication_link": publication_link,
        "acceptance_tools": band,
        "controls": controls,
        "expected_controls": expected_controls,
        "expectations": expectations,
        "verdict": "BLOCK_REHEARSED_REV30_CANDIDATE__SAFE_ALTERNATIVES_VERIFIED"
        if guard_fires
        else "EXPECTATION_FAILED",
        "recommendation": {
            "do_not_land": REHEARSED,
            "do_not_land_sha256": cand_sha,
            "reason": "H1 is correctly repaired, but the replacement regularity.must_not_conflate[0] asserts "
            "H2_loc-inextendibility => this class's conclusion (C0-inextendibility), the false converse of the "
            "file's own implication_ledger row 241 and a direct contradiction of the retained line 232; the "
            "rehearsal's own acceptance tools pass it, so REV30_FREEZE_REHEARSAL_READY does not certify this carrier.",
            "safe_candidates_verified_at_candidate_level": [
                {"path": CORRECTED, "sha256": corrected["sha256"],
                 "h2": corrected["classification"], "battery": battery_corr.get("verdict")},
                {"path": NESTING, "sha256": nesting["sha256"],
                 "h2": nesting["classification"]},
            ],
            "owner_condition": "land one direction-correct H2 wording (or the nesting-only form), keep the H1 "
            "line-246 fix, re-freeze with a strictly increasing revision under the guard, then commission two "
            "blind full-schema F2b reviewers at the published hash.",
        },
        "non_claims": [
            "no canonical path was written; all reads",
            "no gate verdict, no node status, no validation_status, no theorem or physics claim",
            "candidate-level safety only: this is not a full-schema F2b review of the corrected candidates",
            "no claim about which of the two safe candidates the owner should prefer",
        ],
        "falsifier": "Any of: (a) a pin in `pins` does not match the declared sha256 at re-measurement; (b) the "
        "rehearsed candidate's must_not_conflate[0] is shown to entail C0-inextendibility correctly at the "
        "declared bytes; (c) the retained line 232 is shown consistent with the rehearsed candidate's H2 "
        "sentence; (d) the same sentence under own=C2 is classified inverted (class-blind checker); (e) either "
        "acceptance tool fails on the rehearsed candidate (then the rehearsal was not blind but failing); "
        "(f) the corrected candidate 51c253c4 or the nesting-only candidate 4951cc96 is shown to carry an "
        "inverted H2 direction or a failing battery; (g) any canonical byte moves during the run.",
    }

    report_path = os.path.join(out_dir, "guard_report.json")
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")

    md = []
    md.append("# W088-REV30-PUBLICATION-GUARD-01")
    md.append("")
    md.append(f"Verdict: **{result['verdict']}**")
    md.append("")
    md.append("| byte state | sha256 | H1 (line 246) | H2 (must_not_conflate[0]) | contradiction |")
    md.append("|---|---|---|---|---|")
    for label, st in [("live C0 rev29", live_c0), ("rehearsed 84b5d3fa", rehearsed),
                      ("corrected 51c253c4", corrected), ("nesting-only 4951cc96", nesting),
                      ("C2 live (own=C2 control)", live_c2)]:
        md.append(f"| {label} | `{st['sha256'][:12]}` | {st['h1']} | {st['classification']} | "
                  f"{st['intra_file_contradiction']} |")
    md.append("")
    md.append("## Rehearsal acceptance-suite blindness")
    md.append("")
    md.append(f"- battery on rehearsed candidate: `{battery_cand.get('verdict')}`, "
              f"X3c hits `{battery_cand.get('X3c_containment_inversion.hits')}`, "
              f"hard_failures `{len(battery_cand.get('hard_failures') or [])}`, exit `{battery_cand['exit_code']}`")
    md.append(f"- dual on rehearsed candidate: `{dual_cand.get('verdict')}`, "
              f"findings `{dual_cand.get('n_findings')}`, exit `{dual_cand['exit_code']}`")
    md.append(f"- battery on corrected candidate: `{battery_corr.get('verdict')}`, exit `{battery_corr['exit_code']}`")
    md.append("")
    md.append("## Controls")
    md.append("")
    for k in expected_controls:
        md.append(f"- {k}: `{controls[k]}` (expected `{expected_controls[k]}`)")
    md.append("")
    md.append("## Recommendation")
    md.append("")
    md.append(f"- do **not** land `{REHEARSED}` (`{cand_sha[:16]}`): {result['recommendation']['reason']}")
    md.append(f"- safe at candidate level: `{CORRECTED}` (`{corrected['sha256'][:16]}`, H2 {corrected['classification']}) "
              f"and `{NESTING}` (`{nesting['sha256'][:16]}`, H2 {nesting['classification']})")
    md.append(f"- owner condition: {result['recommendation']['owner_condition']}")
    md.append("")
    md.append("## Falsifier")
    md.append("")
    md.append(result["falsifier"])
    md.append("")
    md.append("Non-claims: " + "; ".join(result["non_claims"]))
    md.append("")
    md_path = os.path.join(out_dir, "REPORT.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))

    sums = []
    for fn in ["guard_rev30.py", "emit_events.py", "guard_report.json", "REPORT.md",
               "_scratch/battery_rehearsed.json", "_scratch/battery_rehearsed.md",
               "_scratch/dual_rehearsed.json",
               "_scratch/battery_corrected.json", "_scratch/battery_corrected.md"]:
        p = os.path.join(out_dir, fn)
        if os.path.exists(p):
            sums.append(f"{sha256_file(p)}  {fn}")
    with open(os.path.join(out_dir, "SHA256SUMS"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sums) + "\n")

    print(json.dumps({
        "verdict": result["verdict"],
        "guard_fires": guard_fires,
        "expectations": expectations,
        "controls": controls,
        "reported": {"guard_report.json": sha256_file(report_path),
                     "REPORT.md": sha256_file(md_path)},
    }, indent=2))
    return 0 if guard_fires else 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W100-F2B-CANDIDATE-INDEPENDENT-VERIFY-01

Independent verification of the F2b repair candidate
`artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml`
sha256 a110f8e875afc747d8e8afc1b97912b83537c22be971bb3b791bc865693e2757
against the live canonical F2b `schemas/af_scc_c0_vacuum.yaml` sha256
b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c
(FROZEN rev29 815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0).

Class AF-SCC-C0-VAC-GEN, node F2b, gate G-FORM.  Read-only: no canonical byte,
node status, validation_status or gate verdict is written by this script.
Instrument is independent of worker-022's `verify_f2b_cd_repair_022.py`:
it re-derives the delta with a strict YAML loader, its own leaf differ, its own
probes and its own controls.

Usage:
  python3 verify_candidate.py [--out-dir DIR]
Exit: 0 expectations hold, 2 an expectation failed, 3 pin drift.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

CANONICAL = ROOT / "schemas/af_scc_c0_vacuum.yaml"
CANDIDATE = ROOT / "artifacts/worker-022/f2b_cd_repair/candidate/af_scc_c0_vacuum.repair-candidate.yaml"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
W022_REPORT = ROOT / "artifacts/worker-022/f2b_cd_repair/report.json"
W022_FROZEN29 = ROOT / "artifacts/worker-022/f2b_cd_repair/pinned/FROZEN.rev29.json"
CHECKER = ROOT / "artifacts/formulation/tools/check_class_schema.py"

CANON_SHA = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
CAND_SHA = "a110f8e875afc747d8e8afc1b97912b83537c22be971bb3b791bc865693e2757"
FROZEN_SHA = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"

DELTA_REASON_PATH = "implication_ledger.forbidden_transfers[0].reason"
DELTA_CONFLATE_PATH = "regularity.must_not_conflate[0]"

CD01_INVERTED = re.compile(r"strictly\s+larger\s+extension\s+class", re.I)
CD01_REPAIRED = re.compile(r"strictly\s+smaller\s+extension\s+class", re.I)
PROHIBITED_PHRASE = re.compile(r"strictly between", re.I)


class StrictLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys at any depth."""


def _no_duplicates(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"duplicate key {key!r}", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_strict(p: Path):
    return yaml.load(p.read_text(encoding="utf-8"), Loader=StrictLoader)


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def leaf_delta(a, b):
    fa, fb = flatten(a), flatten(b)
    paths = sorted(set(fa) | set(fb))
    changed = []
    for p in paths:
        if fa.get(p, "<MISSING>") != fb.get(p, "<MISSING>"):
            changed.append({
                "path": p,
                "canonical": str(fa.get(p, "<MISSING>"))[:400],
                "candidate": str(fb.get(p, "<MISSING>"))[:400],
            })
    return changed


def unified_line_delta(canon_text, cand_text):
    diff = list(difflib.unified_diff(canon_text.splitlines(), cand_text.splitlines(),
                                     fromfile="canonical", tofile="candidate", lineterm="", n=0))
    lines = []
    for d in diff:
        if d.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", d)
            if m:
                lines.append({"hunk": d, "canonical_start": int(m.group(1)),
                              "candidate_start": int(m.group(3))})
        elif d.startswith(("-", "+")) and not d.startswith(("---", "+++")):
            lines.append({"change": d[:400]})
    return lines


def run_checker(path: Path):
    proc = subprocess.run([sys.executable, str(CHECKER), "--json", str(path)],
                          capture_output=True, text=True, timeout=300)
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = None
    return {"exit": proc.returncode, "json": payload,
            "stdout_tail": proc.stdout[-800:], "stderr_tail": proc.stderr[-400:]}


def scan_rev29_hfs():
    """HFs recorded in reviews/*.json whose reviewed_sha256 names the live F2b pin."""
    rows, files = [], []
    rdir = ROOT / "reviews"
    for p in sorted(rdir.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        blob = json.dumps(d)
        if "b2ab6acb2bbe" not in blob:
            continue
        files.append({"path": str(p.relative_to(ROOT)), "sha256": sha256_file(p)})
        hfs = d.get("hard_failures") or []
        for hf in hfs:
            rows.append({
                "review_file": str(p.relative_to(ROOT)),
                "reviewer": d.get("reviewer") or d.get("actor"),
                "verdict": d.get("verdict"),
                "id": hf.get("id") if isinstance(hf, dict) else None,
                "field": hf.get("field") if isinstance(hf, dict) else None,
                "mentions_must_not_conflate": "must_not_conflate" in json.dumps(hf),
                "detail": str((hf.get("detail") if isinstance(hf, dict) else hf) or "")[:300],
            })
    return rows, files


def core_checks(canon_text: str, cand_text: str):
    """Text-level checks, reusable on mutated copies for the controls."""
    res = {}
    res["cd01_inverted_in_candidate"] = bool(CD01_INVERTED.search(cand_text))
    res["cd01_repaired_in_candidate"] = bool(CD01_REPAIRED.search(cand_text))
    res["cd01_inverted_in_canonical"] = bool(CD01_INVERTED.search(canon_text))
    # the candidate bullet for must_not_conflate[0]
    m = re.search(r"must_not_conflate:\n((?:    - .*\n)+)", cand_text)
    conflate_block = m.group(1) if m else ""
    res["cd02_block_has_prohibited_phrase"] = bool(PROHIBITED_PHRASE.search(conflate_block))
    res["cd02_block_retains_nonuse_disclaimer"] = bool(
        re.search(r"informal phrase 'strictly between' is not used", conflate_block))
    res["chain_declared_smallest_last"] = bool(
        re.search(r"E_C0 contains E_H2loc contains E_\{C\^1,1\} contains E_C2", cand_text))
    res["chain_reversed"] = bool(
        re.search(r"E_C2 contains E_\{C\^1,1\} contains E_H2loc contains E_C0", cand_text))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(OUT))
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ctrl_dir = out_dir / "controls"
    ctrl_dir.mkdir(exist_ok=True)

    report = {"task_id": "W100-F2B-CANDIDATE-INDEPENDENT-VERIFY-01",
              "actor": "worker-100", "node_id": "F2b", "class_id": "AF-SCC-C0-VAC-GEN",
              "gate": "G-FORM",
              "role": "independent verification of a worker repair candidate; no canonical write, no gate verdict"}

    pins = {str(p): sha256_file(p) for p in (CANONICAL, CANDIDATE, FROZEN, W022_REPORT, W022_FROZEN29, CHECKER)}
    report["pins_measured"] = pins
    pins_ok = (pins[str(CANONICAL)] == CANON_SHA and pins[str(CANDIDATE)] == CAND_SHA
               and pins[str(FROZEN)] == FROZEN_SHA)
    report["pin_expectation"] = {"ok": pins_ok, "canonical": CANON_SHA, "candidate": CAND_SHA, "frozen": FROZEN_SHA}
    if not pins_ok:
        report["verdict"] = "PIN_DRIFT_VOID"
        (out_dir / "report.json").write_text(json.dumps(report, indent=1) + "\n")
        print(json.dumps({"verdict": report["verdict"]}))
        return 3

    canon_text = CANONICAL.read_text(encoding="utf-8")
    cand_text = CANDIDATE.read_text(encoding="utf-8")
    canon_obj = load_strict(CANONICAL)
    cand_obj = load_strict(CANDIDATE)

    delta = leaf_delta(canon_obj, cand_obj)
    lines = unified_line_delta(canon_text, cand_text)
    report["delta"] = {
        "leaf_paths": [d["path"] for d in delta],
        "leaf_detail": delta,
        "line_changes": lines,
        "expected_paths": [DELTA_REASON_PATH, DELTA_CONFLATE_PATH],
        "exactly_two_expected_paths": sorted(d["path"] for d in delta) == sorted([DELTA_REASON_PATH, DELTA_CONFLATE_PATH]),
        "top_level_keys_identical": sorted(canon_obj.keys()) == sorted(cand_obj.keys()),
    }

    core = core_checks(canon_text, cand_text)
    report["core_checks"] = core

    # REP-CD-01 logic check against the declared chain and the F2a parallel row
    reason = cand_obj["implication_ledger"]["forbidden_transfers"][0]["reason"]
    chain = cand_obj["implication_ledger"]["extension_class_containment"]
    report["rep_cd01"] = {
        "candidate_reason": reason,
        "chain": chain,
        "says_smaller": bool(CD01_REPAIRED.search(reason)),
        "cites_subset": "E_C2 subset of E_C0" in reason,
        "no_inversion": not bool(CD01_INVERTED.search(reason)),
        "logic": "E_C2 subset E_C0  =>  'no C2 extension' is weaker than 'no C0 extension'; the corrected reason is direction-correct",
    }

    # REP-CD-02 assessment
    conflate0 = cand_obj["regularity"]["must_not_conflate"][0]
    canon_conflate0 = canon_obj["regularity"]["must_not_conflate"][0]
    report["rep_cd02"] = {
        "canonical_bullet": canon_conflate0,
        "candidate_bullet": conflate0,
        "canonical_has_prohibited_phrase": bool(PROHIBITED_PHRASE.search(canon_conflate0)),
        "candidate_has_prohibited_phrase": bool(PROHIBITED_PHRASE.search(conflate0)),
        "candidate_retains_nonuse_disclaimer": bool(
            re.search(r"informal phrase 'strictly between' is not used", conflate0)),
        "self_contradiction": bool(PROHIBITED_PHRASE.search(conflate0)) and bool(
            re.search(r"informal phrase 'strictly between' is not used", conflate0)),
        "canonical_denies_containment_here": "No containment with C2 or C0 is asserted here" in canon_conflate0,
    }

    hfs, hf_files = scan_rev29_hfs()
    report["rev29_f2b_hard_failures"] = hfs
    report["rev29_review_files_at_pin"] = hf_files
    mnc_hfs = [h for h in hfs if h["mentions_must_not_conflate"]]
    report["must_not_conflate_is_a_live_hf"] = bool(mnc_hfs)
    report["must_not_conflate_hf_ids"] = [h["id"] or h["review_file"] for h in mnc_hfs]

    # Reference wording: the corrected sibling F2a bullet, which does not use the prohibited phrase.
    f2a = ROOT / "schemas/af_scc_c2_vacuum.yaml"
    f2a_obj = load_strict(f2a)
    f2a_conflate = " || ".join(f2a_obj["regularity"]["must_not_conflate"])
    report["f2a_sibling_reference"] = {
        "path": str(f2a.relative_to(ROOT)),
        "sha256": sha256_file(f2a),
        "states_nested_sets": "E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0" in f2a_conflate,
        "uses_prohibited_phrase": bool(PROHIBITED_PHRASE.search(f2a_conflate)),
        "records_denial_as_wrong": "was wrong" in f2a_conflate,
    }

    report["gate_checker"] = {
        "candidate": run_checker(CANDIDATE),
        "canonical": run_checker(CANONICAL),
    }

    report["residuals_touched_by_candidate"] = {
        "conclusion_type_token": cand_obj["conclusion"]["conclusion_type"],
        "vocab_hf_untouched": cand_obj["conclusion"]["conclusion_type"] == canon_obj["conclusion"]["conclusion_type"],
        "f0_binding_consistency_evidence_sha256": cand_obj.get("f0_binding", {}).get("consistency_evidence_sha256"),
    }

    # FROZEN cross-check, including the same-revision re-emission observed by worker-022
    live_frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    w022_frozen = json.loads(W022_FROZEN29.read_text(encoding="utf-8"))
    live_entry = live_frozen["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"]
    old_entry = w022_frozen["files"]["schemas/af_scc_c0_vacuum.yaml"]["sha256"]
    report["frozen_cross_check"] = {
        "live_revision": live_frozen.get("revision"),
        "w022_revision": w022_frozen.get("revision"),
        "live_f2b_pin": live_entry,
        "w022_f2b_pin": old_entry,
        "same_revision_reemission_schema_bytes_identical": live_entry == old_entry == CANON_SHA,
    }

    # Controls: mutate copies and verify the instrument responds as pre-registered.
    controls = []

    def control(cid, what, text, expect):
        p = ctrl_dir / f"{cid}.yaml"
        p.write_text(text, encoding="utf-8")
        try:
            obj = load_strict(p)
            ld = leaf_delta(canon_obj, obj)
            c = core_checks(canon_text, text)
            ok = True
            detail = {}
            if "cd01_fires" in expect:
                detail["cd01_inverted"] = c["cd01_inverted_in_candidate"]
                ok = ok and c["cd01_inverted_in_candidate"] == expect["cd01_fires"]
            if "delta_paths" in expect:
                got = sorted(d["path"] for d in ld)
                detail["delta_paths"] = got
                ok = ok and got == expect["delta_paths"]
            if "chain_reversed" in expect:
                detail["chain_reversed"] = c["chain_reversed"]
                ok = ok and c["chain_reversed"] == expect["chain_reversed"]
            if "parse_ok" in expect:
                ok = ok and expect["parse_ok"]
        except Exception as exc:  # malformed control must fail closed, not crash
            ok = expect.get("parse_ok") is False
            detail = {"structured_failure": type(exc).__name__, "message": str(exc)[:200]}
        controls.append({"id": cid, "what": what, "ok": ok, "measured": detail})

    m1 = cand_text.replace("C2 is a strictly smaller extension class (E_C2 subset of E_C0)",
                           "C2 is a strictly larger extension class")
    control("M1_cd01_inversion_restored", "restore the inverted reason -> inversion probe must fire",
            m1, {"cd01_fires": True})
    m2 = cand_text.replace(conflate0, canon_conflate0)
    control("M2_cd02_reverted", "revert the must_not_conflate bullet -> delta must collapse to one path",
            m2, {"delta_paths": [DELTA_REASON_PATH]})
    m3 = cand_text.replace("E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2",
                           "E_C2 contains E_{C^1,1} contains E_H2loc contains E_C0")
    control("M3_chain_reversed", "reverse the declared chain -> chain probe must fire",
            m3, {"chain_reversed": True})
    m4 = cand_text.replace("epistemic_status: open_problem", "epistemic_status: theorem", 1)
    control("M4_unrelated_leaf_tamper", "tamper an unrelated leaf -> delta must show a third path",
            m4, {"delta_paths": sorted([DELTA_REASON_PATH, DELTA_CONFLATE_PATH, "epistemic_status"])})
    control("M5_pristine_candidate", "pristine candidate -> exactly the two expected paths",
            cand_text, {"delta_paths": sorted([DELTA_REASON_PATH, DELTA_CONFLATE_PATH]), "cd01_fires": False})
    m6 = cand_text + "\n# whitespace-insensitive control\n"
    control("M6_trailing_comment", "trailing comment -> leaf delta unchanged",
            m6, {"delta_paths": sorted([DELTA_REASON_PATH, DELTA_CONFLATE_PATH])})
    control("M7_malformed", "malformed YAML -> structured failure, no crash",
            "conclusion: [unclosed\n", {"parse_ok": False})

    report["controls"] = controls
    report["controls_all_pass"] = all(c["ok"] for c in controls)

    # idempotence: rerun the deterministic core on the same inputs
    report["idempotent"] = (core == core_checks(canon_text, cand_text)
                            and sorted(d["path"] for d in delta) == sorted(d["path"] for d in leaf_delta(canon_obj, cand_obj)))

    # read-only proof
    report["readonly"] = {
        "canonical_unchanged": sha256_file(CANONICAL) == CANON_SHA,
        "candidate_unchanged": sha256_file(CANDIDATE) == CAND_SHA,
    }

    # Expectations, pre-registered in the task framing.
    expectations = [
        {"id": "E1", "what": "all pins match the declared hashes", "ok": pins_ok},
        {"id": "E2", "what": "candidate differs from canonical at exactly the two declared leaf paths",
         "ok": report["delta"]["exactly_two_expected_paths"] and report["delta"]["top_level_keys_identical"]},
        {"id": "E3", "what": "REP-CD-01 is direction-correct (smaller + subset, no inversion)",
         "ok": report["rep_cd01"]["says_smaller"] and report["rep_cd01"]["cites_subset"] and report["rep_cd01"]["no_inversion"]},
        {"id": "E4", "what": "REP-CD-02: candidate bullet uses the prohibited phrase while retaining its non-use disclaimer (new contradiction)",
         "ok": report["rep_cd02"]["candidate_has_prohibited_phrase"] and report["rep_cd02"]["candidate_retains_nonuse_disclaimer"]},
        {"id": "E5", "what": "a live F2b hard failure does concern must_not_conflate, so REP-CD-02 is in scope and required (the initial no-HF hypothesis was falsified on first run; erratum recorded)",
         "ok": report["must_not_conflate_is_a_live_hf"] and len(hfs) >= 1},
        {"id": "E11", "what": "the F2a sibling carries a corrected, prohibited-phrase-free wording usable as the REP-CD-02 reference",
         "ok": report["f2a_sibling_reference"]["states_nested_sets"] and not report["f2a_sibling_reference"]["uses_prohibited_phrase"]},
        {"id": "E6", "what": "canonical structural checker passes on both canonical and candidate",
         "ok": report["gate_checker"]["candidate"]["exit"] == 0 and report["gate_checker"]["canonical"]["exit"] == 0},
        {"id": "E7", "what": "the vocab token and the rev13 f0_binding evidence pin are untouched by the candidate",
         "ok": report["residuals_touched_by_candidate"]["vocab_hf_untouched"]
               and report["residuals_touched_by_candidate"]["f0_binding_consistency_evidence_sha256"] == "9e335e9ba1bfcf777dc9e81816fcf1eda43ce37cef38db754a74649ea6c6fb9b"},
        {"id": "E8", "what": "live FROZEN and the worker-022 rev29 manifest agree on the F2b schema pin",
         "ok": report["frozen_cross_check"]["same_revision_reemission_schema_bytes_identical"]},
        {"id": "E9", "what": "all 7 controls behave as pre-registered", "ok": report["controls_all_pass"]},
        {"id": "E10", "what": "instrument is deterministic and read-only",
         "ok": report["idempotent"] and all(report["readonly"].values())},
    ]
    report["expectations"] = expectations
    report["expectations_all_pass"] = all(e["ok"] for e in expectations)
    report["preregistration_erratum"] = (
        "ERR-W100-01: the first run's pre-registered expectation E5 assumed no live F2b hard failure touched "
        "must_not_conflate, which would have made REP-CD-02 scope creep. The instrument falsified that assumption: "
        "four independent reviews at/against the F2b rev13 pin carry must_not_conflate[0] hard findings "
        "(HF-035-R3-01, W066-R13-F2B-H2, B17-R13-02, W018-R13-F2B-B1). E5 was corrected to the measured direction "
        "and this erratum is retained; no other expectation changed.")

    report["verdict"] = ("REP_CD_01_VERIFIED__REP_CD_02_REQUIRED_WORDING_DEFICIENT" if report["expectations_all_pass"]
                         else "EXPECTATION_FAILED")
    report["findings"] = [
        {"id": "F-W100-01", "severity": "info-verified",
         "statement": "REP-CD-01 is verified at the live pins: the candidate's forbidden_transfers[0].reason reads "
                      "'C2 is a strictly smaller extension class (E_C2 subset of E_C0), so C2-inextendibility is strictly weaker', "
                      "which is direction-correct against the file's own declared chain (E_C0 contains E_H2loc contains E_{C^1,1} contains E_C2) "
                      "and matches the F2a sibling's converse-containment justification. This closes the content side of "
                      "HF-075-F2b-LARGER, W066-R13-F2B-H1, B17-R13-01, W018-R13-F2B-B2 and W053-F2B-REV29-01."},
        {"id": "HF-W100-02", "severity": "hard-for-adoption",
         "statement": "REP-CD-02 is in scope and required (four live reviews carry must_not_conflate[0] hard findings), and the candidate's intent "
                      "is correct: it removes the denial 'No containment with C2 or C0 is asserted here' and cross-references the declared chain. "
                      "The wording is deficient: the replacement bullet asserts the class 'sits strictly between the C0 endpoint class and the C2 endpoint class' "
                      "while the same bullet retains 'the informal phrase \'strictly between\' is not used and must not be cited (worker-16 F2b-16-02 accepted)'. "
                      "HF-035-R3-01 had already flagged that exact phrase tension. Recommendation: keep REP-CD-01; reword REP-CD-02 after the F2a sibling's "
                      "corrected bullet (which states 'E_C2 subset of E_{C^1,1} subset of E_H2loc subset of E_C0' and records the old denial as wrong) "
                      "without using the prohibited phrase."},
        {"id": "F-W100-03", "severity": "residual-out-of-scope",
         "statement": "The candidate leaves conclusion.conclusion_type scc_c0_future_inextendibility untouched, so HF-075-F2b-VOCAB is not "
                      "discharged by adoption of this candidate. The token-authority question is already decision-ready elsewhere "
                      "(worker-048 gform_vocab_adjudication recommends a lead/controller ruling that VOCAB_ALIASES canonical keys govern; "
                      "worker-090 f0_vocab_conformance re-measured the alias/inversion vector at rev13)."},
        {"id": "F-W100-04", "severity": "info",
         "statement": "FROZEN rev29 was re-emitted under the same revision label (worker-022 pinned 3d9e3d77fd87; live is 815e08079aef) "
                      "without moving the F2b schema pin: both manifests record schemas/af_scc_c0_vacuum.yaml = b2ab6acb2bbe. "
                      "Candidate verification therefore binds to the live 815e08079aef manifest; the worker-022 report's FROZEN pin is stale "
                      "but immaterial to the candidate bytes."},
        {"id": "F-W100-05", "severity": "info",
         "statement": "The canonical structural gate check_class_schema.py passes on both the canonical and the candidate, so neither the "
                      "containment-direction defects nor their repair is visible to the mechanical gate; the repair is reviewer-HF-driven, not gate-driven."},
    ]
    report["falsifier"] = ("Falsified if any pin moves (canonical F2b != b2ab6acb2bbe, candidate != a110f8e875af, FROZEN != 815e08079aef); "
                           "or if the candidate's forbidden_transfers[0].reason is re-inverted or its 'smaller/subset' clause removed; "
                           "or if the REP-CD-02 phrase/disclaimer tension is shown to be non-contradictory at these bytes; "
                           "or if a re-run of this instrument yields different per-check results at the same pins.")
    report["next_falsifier"] = ("Re-run after the owner publishes rev14: expect the adopted F2b to keep REP-CD-01 (or an equivalent correct direction), "
                                "to reword REP-CD-02 so the denial is gone and the prohibited phrase is absent, and the remaining F2b blockers to be "
                                "HF-075-F2b-VOCAB (token ruling) only.")
    report["reproduce"] = "python3 artifacts/worker-100/f2b_candidate_verify/verify_candidate.py"

    (out_dir / "report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "expectations_all_pass": report["expectations_all_pass"],
                      "controls_all_pass": report["controls_all_pass"], "leaf_paths": report["delta"]["leaf_paths"]}))
    return 0 if report["expectations_all_pass"] else 2


if __name__ == "__main__":
    sys.exit(main())

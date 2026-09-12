#!/usr/bin/env python3
"""W030D-F1-PROVENANCE-CLOSURE-01 -- independent closure of worker-030 finding W030C-F1.

W030C-F1 (artifacts/worker-030/rev13_preflight/report.json): FROZEN rev29 pins
artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json#3379bcfb together with its
claimed generator artifacts/formulation/tools/evidence_binding_repair_rev29.py#2f6c4f7d, but the
report carries

    files["schemas/af_wcc_vacuum.yaml"].after_pre_binding_fix = bf0c28fa673e...

and the pinned generator source contains that key 0 times.  This instrument decides whether that
unpinned key is an unverifiable orphan or the deterministic output of the pinned generator.

Method (independent reimplementation, no import of the pinned tool's functions):
  * the pinned tool source is read as bytes and AST-parsed; every literal used below is extracted
    from the pinned bytes, so the data is pinned while the logic is reimplemented here;
  * the rev12 bytes are re-hashed against the report's own `before` pins;
  * the header bump, the three F1 substitutions and the three binding substitutions are
    reimplemented from scratch;
  * all timestamps come from the report's own `at` field and from the correction's declared
    composition time -- no wall-clock input, so the run is deterministic and re-runnable.

Read-only on every guarded input; writes only under its own directory.  Exit 1 iff a finding is
present.
"""
from __future__ import annotations

import ast
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

TOOL = ROOT / "artifacts/formulation/tools/evidence_binding_repair_rev29.py"
REPORT = ROOT / "artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"
SNAP = ROOT / "artifacts/worker-030/frozen_transition/snapshot"

TOOL_SHA = "2f6c4f7d8f30b04d97f87e623c03ca3b45e913e31d133474c1abcd75b9bb2965"
REPORT_SHA = "3379bcfb8421056b3c77819c7af4085410dd14d492d37ef4de04b3028e262073"

# rev12 independent snapshots of record (own copy first) + one external copy for a cross-source check
REV12 = {
    "AF-WCC-VAC-GEN": ("cce9c60146d6a907082ade91c67c8ac658bd796d1241f9bb8965c3d2aa69daa3",
                       SNAP / "f1.cce9c601.yaml"),
    "AF-SCC-C2-VAC-GEN": ("5476a3f2c6bc7196eb0bde4c7ae7c2b64182c77362f76a1124703fe4f8e504ce",
                          SNAP / "f2a.5476a3f2.yaml"),
    "AF-SCC-C0-VAC-GEN": ("55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6",
                          SNAP / "f2b.55d0a1ea.yaml"),
}
LIVE = {
    "AF-WCC-VAC-GEN": ROOT / "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": ROOT / "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": ROOT / "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}
CANON = {
    "AF-WCC-VAC-GEN": ROOT / "schemas/af_wcc_vacuum.yaml",
    "AF-SCC-C2-VAC-GEN": ROOT / "schemas/af_scc_c2_vacuum.yaml",
    "AF-SCC-C0-VAC-GEN": ROOT / "schemas/af_scc_c0_vacuum.yaml",
}
EXT_SENTENCE = (" Same revision also refreshed f0_binding.consistency_evidence_sha256 "
                "675a99d0d25b -> 9e335e9ba1bf in all three class schemas.")


def sha_b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_p(p: Path) -> str:
    return sha_b(p.read_bytes())


def extract_constants(src: str) -> dict:
    """Pull only literal constants out of the pinned tool -- data pinned, logic reimplemented."""
    want = {"F1_EQUIV_OLD", "F1_EQUIV_NEW", "F1_MISCLASS_OLD", "F1_MISCLASS_NEW",
            "F1_SET_OLD", "F1_SET_NEW", "F1_REV_NOTE", "BINDING_NOTE_ADD", "CONSISTENCY_SHA",
            "REV_NOTE_COMMON"}
    out: dict = {}
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name) and t.id in want:
                out[t.id] = ast.literal_eval(node.value)
    missing = want - set(out)
    if missing:
        raise SystemExit(f"ASSERT FAIL [ast]: constants not found: {sorted(missing)}")
    return out


def header_bump(text: str, now: str, note: str) -> str:
    """Independent reimplementation of the pinned tool's bump_header (rev12 -> rev13)."""
    m = re.search(r'^revised_at: "[^"]+"\n', text, re.M)
    if not m:
        raise SystemExit("ASSERT FAIL [reimpl/header]: revised_at not found")
    text = text[:m.start()] + f'revised_at: "{now}"\n' + text[m.end():]
    m = re.search(r"^revision: (\d+)\n", text, re.M)
    if not m:
        raise SystemExit("ASSERT FAIL [reimpl/header]: revision not found")
    if m.group(1) != "12":
        raise SystemExit(f"ASSERT FAIL [reimpl/header]: revision is {m.group(1)}, expected 12")
    text = text[:m.start()] + "revision: 13\n" + text[m.end():]
    lines = text.splitlines(keepends=True)
    last = None
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("- {index:") and "unused:" in ln:
            last = i
    if last is None:
        raise SystemExit("ASSERT FAIL [reimpl/header]: revision_history entries not found")
    nxt = 1 + max(int(re.search(r"index: (\d+)", lines[i]).group(1))
                  for i in range(last + 1) if "index:" in lines[i])
    entry = (f'  - {{index: {nxt}, at: {json.dumps(now)}, unused: false, '
             f'notes: {json.dumps([note])} }}\n')
    lines.insert(last + 1, entry)
    return "".join(lines)


def sub_once(text: str, old: str, new: str, what: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"ASSERT FAIL [reimpl/{what}]: expected 1 occurrence, "
                         f"found {text.count(old)}")
    return text.replace(old, new)


def repair_f1_indep(text: str, now: str, K: dict) -> str:
    text = sub_once(text, K["F1_EQUIV_OLD"], K["F1_EQUIV_NEW"], "D5")
    text = sub_once(text, K["F1_MISCLASS_OLD"], K["F1_MISCLASS_NEW"], "misclass")
    text = sub_once(text, K["F1_SET_OLD"], K["F1_SET_NEW"], "SET")
    return header_bump(text, now, K["F1_REV_NOTE"])


def binding_edits_indep(text: str, now: str, K: dict) -> str:
    """The three f0_binding edits only (no header bump) -- the correction's composition."""
    old = ('consistency_evidence_sha256: "675a99d0d25b2b37c9b9e9b965aec1c1ff0e388d2665fd9247'
           'b58c04733eba48"')
    text = sub_once(text, old, f'consistency_evidence_sha256: "{K["CONSISTENCY_SHA"]}"', "hash")
    m = re.search(r'checked_at: "[^"]+"', text)
    if not m:
        raise SystemExit("ASSERT FAIL [reimpl/binding]: checked_at not found")
    text = text[:m.start()] + f'checked_at: "{now}"' + text[m.end():]
    text = sub_once(text, 'never conflated"}',
                    'never conflated.' + K["BINDING_NOTE_ADD"] + '"}', "note")
    return text


def repair_binding_indep(text: str, now: str, K: dict) -> str:
    return header_bump(binding_edits_indep(text, now, K), now, K["REV_NOTE_COMMON"])


def line_regions(a: str, b: str) -> list:
    """Changed line indices (a-side) between two texts, grouped into contiguous regions."""
    import difflib
    sm = difflib.SequenceMatcher(None, a.splitlines(), b.splitlines(), autojunk=False)
    return [(tag, i1, i2, j1, j2) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"]


def main() -> int:
    guards = [TOOL, REPORT, FROZEN] + [v[1] for v in REV12.values()] + list(LIVE.values()) + list(CANON.values())
    guards = [p for p in guards if p.exists()]
    before = {str(p): sha_p(p) for p in guards}

    checks: dict = {}
    findings: list = []

    src = TOOL.read_text()
    K = extract_constants(src)
    rep = json.loads(REPORT.read_text())

    checks["A_pinned_inputs"] = {
        "tool_sha256": sha_p(TOOL), "tool_pin_ok": sha_p(TOOL) == TOOL_SHA,
        "report_sha256": sha_p(REPORT), "report_pin_ok": sha_p(REPORT) == REPORT_SHA,
        "report_at": rep.get("at"), "report_phase": rep.get("phase"),
    }
    if not (checks["A_pinned_inputs"]["tool_pin_ok"] and checks["A_pinned_inputs"]["report_pin_ok"]):
        findings.append("pinned tool or report bytes differ from the FROZEN pins")

    print(f"report at = {rep['at']}  (used as the repair timestamp)")
    t_live = "2026-09-12T00:53:41+08:00"  # correction-declared composition time
    t_report = rep["at"]

    # ---- B: recompute the report's per-class before/after pins -------------------------------
    f1r = rep["files"]["schemas/af_wcc_vacuum.yaml"]
    c2r = rep["files"]["schemas/af_scc_c2_vacuum.yaml"]
    c0r = rep["files"]["schemas/af_scc_c0_vacuum.yaml"]
    checks["B_report_pins_vs_rev12"] = {
        "F1": {"report_before": f1r["before"], "rev12_source_sha256": sha_p(REV12["AF-WCC-VAC-GEN"][1]),
               "match": sha_p(REV12["AF-WCC-VAC-GEN"][1]) == f1r["before"]},
        "F2a": {"report_before": c2r["before"], "rev12_source_sha256": sha_p(REV12["AF-SCC-C2-VAC-GEN"][1]),
                "match": sha_p(REV12["AF-SCC-C2-VAC-GEN"][1]) == c2r["before"]},
        "F2b": {"report_before": c0r["before"], "rev12_source_sha256": sha_p(REV12["AF-SCC-C0-VAC-GEN"][1]),
                "match": sha_p(REV12["AF-SCC-C0-VAC-GEN"][1]) == c0r["before"]},
    }

    # ---- C1: the unpinned key == pinned generator's F1 intermediate at the report timestamp ---
    rev12_f1 = REV12["AF-WCC-VAC-GEN"][1].read_text()
    r12_f1_sha = sha_p(REV12["AF-WCC-VAC-GEN"][1])
    if r12_f1_sha != REV12["AF-WCC-VAC-GEN"][0]:
        findings.append("own rev12 F1 snapshot does not hash to cce9c60146d6")
    inter = repair_f1_indep(rev12_f1, t_report, K)
    inter_sha = sha_b(inter.encode())
    target = f1r["after_pre_binding_fix"]
    checks["C1_unpinned_key_reproduced"] = {
        "key": "files['schemas/af_wcc_vacuum.yaml'].after_pre_binding_fix",
        "report_value": target,
        "independent_repair_f1(report.at)_sha256": inter_sha,
        "match": inter_sha == target,
        "timestamp_used": t_report,
    }
    print(f"C1 after_pre_binding_fix {target[:16]} vs independent repair_f1 -> {inter_sha[:16]} "
          f"MATCH={inter_sha == target}")
    if inter_sha != target:
        findings.append("C1: the unpinned key is NOT reproducible from the pinned generator")

    # ---- C2: final live F1 == intermediate + exactly the declared correction composition ------
    composed = binding_edits_indep(inter.replace(K["F1_REV_NOTE"], K["F1_REV_NOTE"] + EXT_SENTENCE),
                                   t_live, K)
    composed_sha = sha_b(composed.encode())
    live_f1_sha = sha_p(LIVE["AF-WCC-VAC-GEN"])
    regions = line_regions(inter, LIVE["AF-WCC-VAC-GEN"].read_text())
    checks["C2_final_f1_reproduced"] = {
        "live_sha256": live_f1_sha,
        "composed_sha256": composed_sha,
        "byte_identical": composed == LIVE["AF-WCC-VAC-GEN"].read_text(),
        "which_equals_live": composed_sha == live_f1_sha,
        "changed_line_regions_intermediate_to_live": len(regions),
        "region_kinds": [r[0] for r in regions],
        "note_extension_used": EXT_SENTENCE.strip(),
        "binding_edit_time": t_live,
    }
    print(f"C2 live F1 {live_f1_sha[:16]} vs composed {composed_sha[:16]} "
          f"IDENTICAL={composed == LIVE['AF-WCC-VAC-GEN'].read_text()}  regions={len(regions)}")
    if composed != LIVE["AF-WCC-VAC-GEN"].read_text():
        findings.append("C2: live F1 is not the declared composition of the intermediate")
    if len(regions) != 2 or any(r[0] != "replace" or (r[2] - r[1]) != 1 for r in regions):
        findings.append(f"C2: unexpected structure in intermediate->live diff: {regions}")

    # ---- C3/C4: F2a and F2b are the plain binding branch at the same timestamp ----------------
    f2 = {}
    for cid, tag in (("AF-SCC-C2-VAC-GEN", "C3_f2a_direct"), ("AF-SCC-C0-VAC-GEN", "C4_f2b_direct")):
        r12 = REV12[cid][1].read_text()
        got = sha_b(repair_binding_indep(r12, t_report, K).encode())
        want = sha_p(LIVE[cid])
        f2[tag] = {"class": cid, "rev12_source": sha_p(REV12[cid][1]), "recomputed_sha256": got,
                   "live_sha256": want, "match": got == want, "timestamp_used": t_report}
        print(f"{tag} {cid}: recomputed {got[:16]} == live {want[:16]} MATCH={got == want}")
        if got != want:
            findings.append(f"{tag}: live {cid} bytes not reproduced by the binding branch")
    checks["C3_C4_binding_branch"] = f2

    # ---- C5: canonical/authoring mirrors agree with the live pins -----------------------------
    mirrors = {}
    for cid in LIVE:
        mirrors[cid] = {"live": sha_p(LIVE[cid]), "canonical": sha_p(CANON[cid]),
                        "identical": LIVE[cid].read_bytes() == CANON[cid].read_bytes()}
        if not mirrors[cid]["identical"]:
            findings.append(f"C5: canonical/live mirror mismatch for {cid}")
    checks["C5_mirrors"] = mirrors

    # ---- C6: FROZEN rev29 pins the report and the generator at the audited hashes -------------
    fz = json.loads(FROZEN.read_text())
    files = fz.get("files", {})
    items = files.items() if isinstance(files, dict) else [(f.get("path"), f) for f in files]
    pinmap = {str(k): v for k, v in items}
    checks["C6_frozen_pins"] = {
        "revision": fz.get("revision"),
        "report_pinned": pinmap.get("artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json", {}).get("sha256"),
        "tool_pinned": pinmap.get("artifacts/formulation/tools/evidence_binding_repair_rev29.py", {}).get("sha256"),
        "report_pin_matches": pinmap.get("artifacts/formulation/evidence/evidence_binding_repair_rev29_report.json", {}).get("sha256") == REPORT_SHA,
        "tool_pin_matches": pinmap.get("artifacts/formulation/tools/evidence_binding_repair_rev29.py", {}).get("sha256") == TOOL_SHA,
    }

    # ---- C7 controls: the reproduction is non-trivial and the composition was necessary -------
    wrong_ts = sha_b(repair_f1_indep(rev12_f1, "2026-09-12T00:53:41+08:00", K).encode())
    bump_fail = None
    try:
        repair_binding_indep(inter, t_live, K)
    except SystemExit as exc:
        bump_fail = str(exc)
    checks["C7_controls"] = {
        "wrong_timestamp_gives_different_hash": wrong_ts != target,
        "wrong_timestamp_sha256": wrong_ts,
        "repair_binding_on_intermediate_fails_closed": bump_fail is not None,
        "repair_binding_on_intermediate_error": bump_fail,
        "cross_source_check": "external rev12 copy (artifacts/worker-033/gform_r12_ledger/pinned/canonical/af_wcc_vacuum.yaml)",
    }
    ext = ROOT / "artifacts/worker-033/gform_r12_ledger/pinned/canonical/af_wcc_vacuum.yaml"
    if ext.exists():
        ext_ok = (sha_p(ext) == REV12["AF-WCC-VAC-GEN"][0]
                  and sha_b(repair_f1_indep(ext.read_text(), t_report, K).encode()) == target)
        checks["C7_controls"]["external_source_reproduces_key"] = ext_ok
        if not ext_ok:
            findings.append("C7: an independent external rev12 copy does not reproduce the key")
    else:
        checks["C7_controls"]["external_source_reproduces_key"] = None

    # ---- D: read-only guarantee ---------------------------------------------------------------
    after = {str(p): sha_p(p) for p in guards}
    drift = {k: [before[k], after[k]] for k in before if before[k] != after[k]}
    checks["D_read_only"] = {"guarded_paths": len(guards), "drift": drift, "pass": not drift}
    if drift:
        findings.append(f"D: guarded inputs moved during the audit: {sorted(drift)}")

    verdict = "F1_PROVENANCE_CLOSED_VALUE_REPRODUCED_FROM_PINNED_INPUTS"
    if findings:
        verdict = "F1_PROVENANCE_CLOSURE_FINDINGS_PRESENT"

    report = {
        "schema": "w030d-f1-provenance-closure/1",
        "task_id": "W030D-F1-PROVENANCE-CLOSURE-01",
        "actor": "worker-030",
        "node_id": "F1,F2a,F2b",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "card_audited": "astra-life05-evidence-binding-repair",
        "targets_finding": "W030C-F1 (artifacts/worker-030/rev13_preflight/report.json)",
        "measured_at": dt.datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "verdict": verdict,
        "closure": {
            "intermediate_sha256": inter_sha,
            "live_f1_sha256": live_f1_sha,
            "report_key": target,
            "key_is_value_of": "repair_f1(rev12_F1_bytes, report.at) under the pinned generator",
            "final_is": "binding_edits(intermediate + rev13 note extension) under the correction",
        },
        "checks": checks,
        "findings": findings,
        "residual": ("the pre-fix wrapper that emitted the extra key is still not itself pinned; "
                     "only its output value is now reproduced. Full byte-provenance of the record "
                     "would need that wrapper version pinned or the key dropped in a new revision."),
        "falsifiers": [
            "produce rev12 F1 bytes at cce9c60146d6 whose repair_f1(., 2026-09-12T00:53:20+08:00) "
            "is not bf0c28fa673e5bd5d82d03ab93059b99580af0f3f65a81d4924e0bc8e74a6226",
            "produce live F1 bytes at d9cebb9404b2 that differ from the composed candidate",
            "produce F2a/F2b rev12 bytes at 5476a3f2c6bc / 55d0a1ea9bda whose binding branch at "
            "2026-09-12T00:53:20+08:00 does not give e9a27996dfd3 / b2ab6acb2bbe",
            "show any guarded input hash moved during this run",
        ],
        "not_claimed": ("no gate verdict, no review verdict, no node-status change, no canonical "
                        "write, no mathematics or physics claim; the residual wrapper-provenance "
                        "gap is reported, not adjudicated."),
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(f"\nverdict: {verdict}")
    print(f"findings: {findings if findings else 'none'}")
    print(f"wrote {OUT/'report.json'}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())

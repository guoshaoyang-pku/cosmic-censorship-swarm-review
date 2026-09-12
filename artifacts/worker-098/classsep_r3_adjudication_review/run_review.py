#!/usr/bin/env python3
"""W098-CLASSSEP-ADJ-REVIEW-01 independent review harness (read-only, no network).

Re-derives the r3 adjudication's four-arm census with worker-098 code paths (not the
audit harness), tests the declared adoption bar, adds a fifth uncited arm (W098 v3)
and the post-decision live bytes, and checks the no-write / no-gate-pass claims.

Outputs: raw/measurements.json, report.json
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
NOW = datetime.now().astimezone().isoformat(timespec="seconds")

ADJ_PATH = ROOT / "reviews/CLASSSEP-calibration-adjudication.json"
SNAP_PATH = ROOT / "artifacts/audit/classsep_r3_map_snapshot_20260912T010324.json"
CAL_PATH = ROOT / "artifacts/audit/classsep_calibration.py"
W07 = ROOT / "artifacts/worker-07/class_separation_falsification"
W049_CORPUS = ROOT / "artifacts/worker-049/classsep_fn_audit/corpus.json"
W035 = ROOT / "artifacts/worker-049/classsep_prose_fix/worker035_controls.json"
MAP = ROOT / "research_map/research_map.json"
FROZEN = ROOT / "artifacts/formulation/FROZEN.json"

ARMS = {
    "APPLIED_CITED": "artifacts/worker-032/classsep-prose-01/pinned/class_separation.a8c04fc31e4a.py",
    "PRE": "artifacts/worker-049/classsep_fn_audit/pinned/class_separation_c266_recovered.py",
    "STAGED": "proposed/class_separation.py",
    "PROSEFIX": "artifacts/worker-049/classsep_prose_fix/class_separation_prosefix.py",
    "W098_V3": "artifacts/worker-098/classsep_mention_scope/candidate_class_separation.v3.py",
    "LIVE_NOW": "research_map/class_separation.py",
    "CF29_UNAUTHORIZED":
        "artifacts/worker-073/classsep_union_separability/pinned/class_separation.live.e36b0d644ca7.py",
}
CF29 = ROOT / "runtime/state/controller_verification/cf29-detector-write-forensics.json"
SOFT = "CLASSSEP-SOFT:"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "ABSENT"


def load_mod(rel: str, name: str):
    p = ROOT / rel
    spec = importlib.util.spec_from_file_location(f"review098_{name}", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extract_consts(src_path: Path, names: tuple[str, ...]) -> dict:
    """Read data constants from source via ast, without executing/using the module's code."""
    tree = ast.parse(src_path.read_text())
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in names:
                    found[t.id] = ast.literal_eval(node.value)
    missing = [n for n in names if n not in found]
    if missing:
        raise RuntimeError(f"constants not found: {missing}")
    return found


# ---------------------------------------------------------------- censuses (mine)
def census_a(mod, results: dict) -> dict:
    tp = fp = tn = fn = 0
    rows = []
    for fx in results["fixtures"]:
        p = ROOT / fx["fixture_path"]
        if not p.exists():
            rows.append({"id": fx["id"], "class": "MISSING"})
            continue
        m = json.loads(p.read_text())
        det = mod.findings_for_map(m)
        for g in m.get("groups", []):
            for n in g.get("nodes", []):
                art = n.get("artifact")
                if art and (ROOT / art).is_file():
                    det += mod.findings_for_text((ROOT / art).read_text(errors="replace"),
                                                 f"artifact {art}")
        got, truth = bool(det), bool(fx["is_class_merge"])
        cls = "TP" if truth and got else "FN" if truth else "FP" if got else "TN"
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        rows.append({"id": fx["id"], "class": cls, "surface": fx.get("surface")})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(results["fixtures"]),
            "verdict": "PASS" if fn == 0 and fp == 0 else "DEFECTIVE",
            "non_pass": [r for r in rows if r["class"] not in ("TP", "TN")]}


def census_c(mod, fixtures: list) -> dict:
    tp = fp = tn = fn = 0
    rows = []
    for fid, truth, text in fixtures:
        got = bool(mod.findings_for_text(text, f"fixture {fid}"))
        cls = "TP" if truth and got else "FN" if truth else "FP" if got else "TN"
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        rows.append({"id": fid, "expect": truth, "fired": got, "class": cls})
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(fixtures),
            "sens": f"{tp}/{tp+fn}", "spec": f"{tn}/{tn+fp}",
            "fn_ids": [r["id"] for r in rows if r["class"] == "FN"],
            "fp_ids": [r["id"] for r in rows if r["class"] == "FP"], "rows": rows}


def census_d(mod, corpus: dict) -> dict:
    fx = corpus["fixtures"]
    by_id = {f["id"]: f for f in fx}
    fired = {f["id"]: bool(mod.findings_for_text(f["text"], f"fixture {f['id']}")) for f in fx}
    tp = fp = tn = fn = 0
    per = []
    for f in fx:
        truth = bool(f["expected_findings"]); got = fired[f["id"]]
        cls = "TP" if truth and got else "FN" if truth else "FP" if got else "TN"
        tp += cls == "TP"; fn += cls == "FN"; fp += cls == "FP"; tn += cls == "TN"
        per.append({"id": f["id"], "category": f["category"], "expected": int(truth),
                    "flags": got, "class": cls})
    twin_by_adv = {f["twin_of"]: f["id"] for f in fx
                   if f["category"] == "TWIN_CONTROL" and f.get("twin_of")}
    cue = []
    for f in fx:
        if f["category"] != "ADVERSARIAL_ASSERTION":
            continue
        tw = by_id.get(twin_by_adv.get(f["id"]))
        if tw and (not fired[f["id"]]) and fired[tw["id"]]:
            cue.append({"adversarial": f["id"], "twin": tw["id"],
                        "confidence": f.get("confidence")})
    mentions = [f for f in fx if f["category"] == "MENTION"]
    plain = [f for f in fx if f["category"] == "PLAIN_POSITIVE"]
    twins = [f for f in fx if f["category"] == "TWIN_CONTROL"]
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "n": len(fx),
            "class_summary": f"{tp}/{fn}/{fp}/{tn}",
            "cue_fn_total": len(cue),
            "cue_fn_high": sum(1 for c in cue if c["confidence"] == "HIGH"),
            "cue_fn_detail": cue,
            "mention_fp": sorted(f["id"] for f in mentions if fired[f["id"]]),
            "plain_positive_fn": sorted(f["id"] for f in plain if not fired[f["id"]]),
            "twin_flagged": f"{sum(1 for f in twins if fired[f['id']])}/{len(twins)}",
            "per_fixture": per}


def census_e(mod, battery: dict) -> dict:
    passed = []
    failed = []
    for c in battery["controls"]:
        want = c["expect"] == "ASSERTION"
        got = bool(mod.findings_for_text(c["text"], f"control {c['control_id']}"))
        (passed if want == got else failed).append(c["control_id"])
    return {"passed": len(passed), "total": len(battery["controls"]),
            "fail_ids": sorted(failed), "verdict": "PASS" if not failed else "DEFECTIVE"}


def census_b(mod, snap: dict, labels: dict) -> dict:
    raw = mod.findings_for_map(snap)
    hard = [x for x in raw if not x.startswith(SOFT)]
    per_claim = {}
    other = []
    for x in hard:
        mo = re.search(r"claims\[(\d+)\]", x)
        (per_claim.setdefault(int(mo.group(1)), []).append(x) if mo else other.append(x))
    labeled_fp = 0
    labeled_tp = 0
    unlabeled_findings = 0
    strict_extra_unlabeled = 0
    detail = []
    for idx in sorted(per_claim):
        if idx in labels:
            labs = labels[idx]
            for k, f in enumerate(per_claim[idx]):
                # claim-level label inheritance, as in the adjudication's stated criterion
                lab = labs[k] if k < len(labs) else labs[-1]
                if k >= len(labs):
                    strict_extra_unlabeled += 1
                if lab[0] == "TP":
                    labeled_tp += 1
                else:
                    labeled_fp += 1
                detail.append({"claim_index": idx, "label": lab[0], "mechanism": lab[1],
                               "finding": f[:150]})
        else:
            unlabeled_findings += len(per_claim[idx])
            detail.append({"claim_index": idx, "label": "UNLABELED", "mechanism": "UNLABELED",
                           "finding": per_claim[idx][0][:150]})
    return {"hard_total": len(hard), "soft_total": len(raw) - len(hard),
            "claims_flagged": sorted(per_claim), "labeled_fp": labeled_fp,
            "labeled_tp": labeled_tp, "unlabeled": sorted(
                i for i in per_claim if i not in labels),
            "unlabeled_findings": unlabeled_findings,
            "strict_extra_unlabeled": strict_extra_unlabeled,
            "non_claim_findings": other, "detail": detail}


def bar_ok(row: dict) -> dict:
    sens_ok = int(row["sens"].split("/")[0]) >= 5
    spec_ok = int(row["spec"].split("/")[0]) >= 9 and int(row["spec"].split("/")[1]) == 10
    return {"corpus_a_pass": row["corpus_a"] == "PASS", "sens_ok": sens_ok,
            "spec_ok": spec_ok, "cue_fn_high_zero": row["cue_fn_high"] == 0,
            "live_metalinguistic_zero": row["hard"] == 0,
            "meets_bar": all([row["corpus_a"] == "PASS", sens_ok, spec_ok,
                              row["cue_fn_high"] == 0, row["hard"] == 0])}


def main() -> int:
    adj = json.loads(ADJ_PATH.read_text())
    snap = json.loads(SNAP_PATH.read_text())
    cal = extract_consts(CAL_PATH, ("ASSERTION_MENTION_FIXTURES", "LIVE_LABELS"))
    amf = cal["ASSERTION_MENTION_FIXTURES"]
    labels = cal["LIVE_LABELS"]
    w07 = json.loads((W07 / "results.json").read_text())
    w049 = json.loads(W049_CORPUS.read_text())
    w035 = json.loads(W035.read_text())

    mods = {name: load_mod(rel, name) for name, rel in ARMS.items()}

    measured = {}
    for name, mod in mods.items():
        a = census_a(mod, w07)
        c = census_c(mod, amf)
        d = census_d(mod, w049)
        e = census_e(mod, w035)
        b = census_b(mod, snap, labels)
        row = {"corpus_a": a["verdict"], "a_detail": a, "sens": c["sens"], "spec": c["spec"],
               "c_detail": c, "d": d, "e": e, "hard": b["hard_total"], "b_detail": b}
        row.update(bar_ok({"corpus_a": a["verdict"], "sens": c["sens"], "spec": c["spec"],
                           "cue_fn_high": d["cue_fn_high"], "hard": b["hard_total"]}))
        measured[name] = row

    # ---- citation chain: adjudication claims vs on-disk vs outbox events
    cited = {}
    for arm, blk in adj["detectors"].items():
        cited[arm] = {"path": blk["path"], "claimed": blk["sha256"],
                      "cited_prefix": blk["cited_prefix"]}
    cited["FROZEN_MAP"] = {"path": adj["frozen_map_snapshot"]["path"],
                           "claimed": adj["frozen_map_snapshot"]["sha256"]}
    conformance = {}
    for k, v in cited.items():
        disk = sha(ROOT / v["path"])
        conformance[k] = {"path": v["path"], "claimed": v["claimed"], "on_disk": disk,
                          "prefix_ok": disk.startswith(v["cited_prefix"])
                          if "cited_prefix" in v else disk == v["claimed"],
                          "exact_match": disk == v["claimed"]}
    # recovered copies for arms whose live path moved
    recovered = {}
    for arm, rel in ARMS.items():
        if arm in ("W098_V3", "LIVE_NOW"):
            continue
        blk = adj["detectors"].get(arm)
        if blk and sha(ROOT / blk["path"]) != blk["sha256"]:
            recovered[arm] = {"live_path": blk["path"], "live_now": sha(ROOT / blk["path"]),
                              "review_uses": rel, "review_hash": sha(ROOT / rel),
                              "matches_claim": sha(ROOT / rel) == blk["sha256"]}
    # outbox artifact events
    outbox_hits = []
    for line in (ROOT / "comms/outbox/astra-lead-audit.jsonl").read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("event_type") == "artifact" and ev.get("path") in {
                adj["detectors"]["APPLIED"]["path"], adj["detectors"]["PRE"]["path"],
                adj["detectors"]["STAGED"]["path"], adj["detectors"]["PROSEFIX"]["path"],
                adj["frozen_map_snapshot"]["path"], "reviews/CLASSSEP-calibration-adjudication.json",
                "artifacts/audit/classsep_r3_adjudication.py"}:
            outbox_hits.append({"created_at": ev.get("created_at"), "path": ev["path"],
                                "sha256": ev.get("sha256"),
                                "matches_disk": ev.get("sha256") == sha(ROOT / ev["path"])})

    # ---- no-write / no-gate checks
    live_map = json.loads(MAP.read_text())
    gate_audit = next((g for g in live_map["gates"] if g.get("gate_id") == "G-AUDIT"), {})
    frozen = json.loads(FROZEN.read_text()) if FROZEN.is_file() else {}
    no_write = {
        "detector_mtime": datetime.fromtimestamp(
            (ROOT / "research_map/class_separation.py").stat().st_mtime
        ).astimezone().isoformat(timespec="seconds"),
        "adjudication_created_at": adj.get("created_at"),
        "adjudication_emitted_at": "2026-09-12T01:05:17+08:00",
        "live_detector_now": sha(ROOT / "research_map/class_separation.py"),
        "cited_applied": adj["detectors"]["APPLIED"]["sha256"],
        "detectors_moved_during_round": adj.get("detectors_moved_during_round"),
        "schema_hashes_now": {p: sha(ROOT / p) for p in (
            "schemas/af_wcc_vacuum.yaml", "schemas/af_scc_c2_vacuum.yaml",
            "schemas/af_scc_c0_vacuum.yaml")},
        "frozen_manifest_now": sha(FROZEN),
        "adjudication_has_gate_verdict_field": any(
            k in adj for k in ("verdict", "gate_verdict", "validation_status")),
        "gate_audit_live": {"verdict": gate_audit.get("verdict"),
                            "checked_at": gate_audit.get("checked_at")},
        "live_map": {"sha256": sha(MAP), "claims": len(live_map["claims"]),
                     "updated_at": live_map.get("updated_at")},
    }

    # ---- expectation status
    exp_status = []
    for e in json.loads((HERE / "pre_registration.json").read_text())[
            "expectations_written_before_measurement"]:
        eid = e["id"]
        if eid == "E1":
            ok = all(v["exact_match"] for v in conformance.values())
            note = ("all cited paths resolved on disk at their claimed bytes"
                    if ok else
                    "cited APPLIED " + cited["APPLIED"]["claimed"][:12] +
                    " no longer at its live path (now " +
                    sha(ROOT / cited["APPLIED"]["path"])[:12] + "); recovered copy " +
                    ARMS["APPLIED_CITED"] + " hash-matches the citation")
        elif eid == "E2":
            ok = all(measured[a]["corpus_a"] == "PASS" for a in
                     ("APPLIED_CITED", "PRE", "STAGED", "PROSEFIX"))
            note = ", ".join(f"{a}:{measured[a]['corpus_a']}" for a in
                             ("APPLIED_CITED", "PRE", "STAGED", "PROSEFIX"))
        elif eid == "E3":
            want = {"APPLIED_CITED": ("4/6", "3/10"), "PRE": ("4/6", "1/10"),
                    "STAGED": ("5/6", "1/10"), "PROSEFIX": ("4/6", "10/10")}
            ok = all((measured[a]["sens"], measured[a]["spec"]) == w for a, w in want.items())
            note = ", ".join(f"{a}:{measured[a]['sens']},{measured[a]['spec']}" for a in want)
        elif eid == "E4":
            want = {"APPLIED_CITED": (30, 1, 6, 2, 1), "PRE": (31, 0, 6, 2, 0),
                    "STAGED": (31, 0, 6, 2, 0), "PROSEFIX": (20, 11, 2, 6, 10)}
            ok = all((measured[a]["d"]["tp"], measured[a]["d"]["fn"], measured[a]["d"]["fp"],
                      measured[a]["d"]["tn"], measured[a]["d"]["cue_fn_high"]) == w
                     for a, w in want.items())
            note = ", ".join(f"{a}:{measured[a]['d']['class_summary']}"
                             f"/cueH{measured[a]['d']['cue_fn_high']}" for a in want)
        elif eid == "E5":
            want = {"APPLIED_CITED": 13, "PRE": 11, "STAGED": 11, "PROSEFIX": 23}
            ok = all(measured[a]["e"]["passed"] == w for a, w in want.items())
            note = ", ".join(f"{a}:{measured[a]['e']['passed']}/{measured[a]['e']['total']}"
                             for a in want)
        elif eid == "E6":
            want = {"APPLIED_CITED": 19, "PRE": 24, "STAGED": 25, "PROSEFIX": 1}
            ok = (all(measured[a]["hard"] == w for a, w in want.items())
                  and measured["APPLIED_CITED"]["b_detail"]["unlabeled"] == [327, 336])
            note = ", ".join(f"{a}:{measured[a]['hard']}" for a in want) + \
                f"; unlabeled={measured['APPLIED_CITED']['b_detail']['unlabeled']}"
        elif eid == "E7":
            ok = not any(measured[a]["meets_bar"] for a in
                         ("APPLIED_CITED", "PRE", "STAGED", "PROSEFIX"))
            note = "meets_bar=" + str({a: measured[a]["meets_bar"] for a in
                                       ("APPLIED_CITED", "PRE", "STAGED", "PROSEFIX")})
        elif eid == "E8":
            v3 = measured["W098_V3"]
            ok = not v3["meets_bar"]
            note = (f"v3 corpus_a={v3['corpus_a']} sens={v3['sens']} spec={v3['spec']} "
                    f"d={v3['d']['class_summary']} cueH={v3['d']['cue_fn_high']} "
                    f"hard={v3['hard']} meets_bar={v3['meets_bar']}")
        elif eid == "E9":
            ok = (no_write["detectors_moved_during_round"] == {}
                  and no_write["live_detector_now"] == no_write["cited_applied"])
            note = (f"live={no_write['live_detector_now'][:12]} cited="
                    f"{no_write['cited_applied'][:12]} mtime={no_write['detector_mtime']}; "
                    f"churn window a8c04fc3 -> e36b0d64 (01:06:12) -> a8c04fc3 (01:08:14) "
                    f"recorded by the controller as CF-29")
        elif eid == "E10":
            ok = (not no_write["adjudication_has_gate_verdict_field"]
                  and no_write["gate_audit_live"]["verdict"] == "pending")
            note = (f"adj_gate_field={no_write['adjudication_has_gate_verdict_field']} "
                    f"G-AUDIT={no_write['gate_audit_live']['verdict']}")
        elif eid == "E11":
            ok = (measured["PROSEFIX"]["d"]["cue_fn_high"] >= 10
                  and measured["STAGED"]["d"]["cue_fn_high"] == 0)
            note = (f"PROSEFIX cueH={measured['PROSEFIX']['d']['cue_fn_high']} "
                    f"STAGED cueH={measured['STAGED']['d']['cue_fn_high']}")
        elif eid == "E12":
            ok = sha(MAP) != sha(SNAP_PATH)
            note = (f"live {sha(MAP)[:12]} claims={len(live_map['claims'])} vs snapshot "
                    f"{sha(SNAP_PATH)[:12]} claims={len(snap.get('claims', []))}")
        else:
            ok, note = None, ""
        exp_status.append({"id": eid, "status": "PASS" if ok else "FALSIFIED",
                           "note": note})

    # ---- adjudication reproduction diffs
    repro = {}
    for arm, key in (("APPLIED_CITED", "APPLIED"), ("PRE", "PRE"),
                     ("STAGED", "STAGED"), ("PROSEFIX", "PROSEFIX")):
        m = measured[arm]
        ca = adj["corpus_a_27fixtures"][key]
        cc = adj["corpus_c_assertion_mention"][key]
        cd = adj["corpus_d_fixture_classes"][key]
        cb = adj["corpus_b_live"][key]
        cd_cue = adj["corpus_d_worker049_cue_fn"][key]
        repro[arm] = {
            "corpus_a_match": (m["a_detail"]["tp"], m["a_detail"]["fn"], m["a_detail"]["fp"],
                               m["a_detail"]["tn"]) == (ca["tp"], ca["fn"], ca["fp"], ca["tn"]),
            "corpus_c_match": (m["c_detail"]["tp"], m["c_detail"]["fn"], m["c_detail"]["fp"],
                               m["c_detail"]["tn"]) == (cc["tp"], cc["fn"], cc["fp"], cc["tn"]),
            "corpus_d_match": (m["d"]["tp"], m["d"]["fn"], m["d"]["fp"], m["d"]["tn"]) ==
                              (cd["tp"], cd["fn"], cd["fp"], cd["tn"]),
            "corpus_d_cue_match": m["d"]["cue_fn_high"] == cd_cue["cue_induced_fn_high_confidence"],
            "corpus_b_match": m["hard"] == cb["hard_total"],
            "corpus_a": f"{m['a_detail']['tp']}/{m['a_detail']['fn']}/{m['a_detail']['fp']}/{m['a_detail']['tn']}",
            "corpus_c": f"{m['c_detail']['tp']}/{m['c_detail']['fn']}/{m['c_detail']['fp']}/{m['c_detail']['tn']}",
            "corpus_d": m["d"]["class_summary"], "corpus_b_hard": m["hard"],
        }
    all_match = all(all(v for k, v in r.items() if k.endswith("_match")) for r in repro.values())

    # ---- CF-29 forensics (controller record; observed during this review)
    cf29 = json.loads(CF29.read_text()) if CF29.is_file() else {}
    cf29_check = {
        "path": CF29.relative_to(ROOT).as_posix(), "sha256": sha(CF29),
        "recorded_at": cf29.get("recorded_at"),
        "unauthorized_sha256": cf29.get("detector", {}).get("unauthorized_sha256", "")[:12],
        "restored_sha256": cf29.get("detector", {}).get("restored_sha256", "")[:12],
        "pin_ruling": cf29.get("ruling", "")[:180],
        "unauthorized_arm_measured": measured.get("CF29_UNAUTHORIZED", {}).get("meets_bar"),
        "quarantine_files": [
            {"path": q["path"], "sha256": q["sha256"],
             "exists": (ROOT / q["path"]).is_file(),
             "matches": (ROOT / q["path"]).is_file() and sha(ROOT / q["path"]) == q["sha256"]}
            for q in cf29.get("quarantine", [])],
    }

    report = {
        "schema": "worker-098/classsep-r3-adjudication-review/v1",
        "task_id": "W098-CLASSSEP-ADJ-REVIEW-01",
        "actor": "worker-098", "node_id": "A1", "gate": "G-AUDIT",
        "class_id": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN",
        "created_at": NOW,
        "reviewed_artifact": {"path": "reviews/CLASSSEP-calibration-adjudication.json",
                              "sha256": sha(ADJ_PATH),
                              "revision": adj.get("revision"),
                              "decision": adj["decision"]["choice"]},
        "pins_at_review": json.loads((HERE / "pre_registration.json").read_text())["pins"],
        "hash_conformance": conformance, "recovered_copies": recovered,
        "outbox_citation_chain": outbox_hits,
        "measured": measured, "expectations": exp_status,
        "adjudication_reproduced": all_match, "reproduction": repro,
        "no_write_no_gate_check": no_write,
        "cf29_forensics": cf29_check,
        "conclusion": {
            "decision_supported": all_match and not any(
                measured[a]["meets_bar"] for a in
                ("APPLIED_CITED", "PRE", "STAGED", "PROSEFIX", "W098_V3")),
            "fifth_arm_effect": "none: W098 v3 fails live_metalinguistic=0"
            if not measured["W098_V3"]["meets_bar"] else "DEFEATS decision (c)",
            "cf29_unauthorized_arm_effect": (
                "none on the reviewed decision: the e36b0d64 one-line widening is not part of "
                "the adjudicated candidate set and is void per CF-29 (meets_bar="
                f"{measured.get('CF29_UNAUTHORIZED', {}).get('meets_bar')})"),
            "detector_churn_window": {
                "cited_applied": adj["detectors"]["APPLIED"]["sha256"][:12],
                "unauthorized": cf29_check["unauthorized_sha256"],
                "restored": cf29_check["restored_sha256"],
                "live_at_measurement": no_write["live_detector_now"][:12],
                "mtime_after_restore": no_write["detector_mtime"],
                "delta": "one-line regex widening of the meta-quotation skip "
                         "(a8c04fc3 -> e36b0d64) during the REC-22 freeze, restored by the "
                         "controller from worker-073's pinned copy",
                "owner_note": "CF-29 record + quarantine; separately pinned/owned by "
                              "worker-031/045/073; not part of the reviewed decision",
            },
        },
    }
    (HERE / "raw").mkdir(exist_ok=True)
    (HERE / "raw/measurements.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({
        "adjudication_reproduced": all_match,
        "expectations": {e["id"]: e["status"] for e in exp_status},
        "arms": {a: {"A": measured[a]["corpus_a"], "C": measured[a]["sens"] + "/" + measured[a]["spec"],
                     "D": measured[a]["d"]["class_summary"], "E": f"{measured[a]['e']['passed']}/{measured[a]['e']['total']}",
                     "B": measured[a]["hard"], "bar": measured[a]["meets_bar"]}
                 for a in ARMS},
        "reproduction": repro,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

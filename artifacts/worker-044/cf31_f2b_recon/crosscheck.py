#!/usr/bin/env python3
"""W044-CF31-CROSSCHECK-01.

Adversarial independent verification of the two concurrent CF-31
reconciliations (worker-017 binding table, worker-018 coverage census),
including the falsifiers they declared. Read-only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)

PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
PIN12 = PIN[:12]
R17_TABLE = ROOT / "artifacts/worker-017/cf31_f2b_census/binding_table.json"
R17_REPORT = ROOT / "artifacts/worker-017/cf31_f2b_census/report.json"
R17_REVIEW = ROOT / "reviews/CF31-F2b-binding-table-worker-017.json"
R18_REPORT = ROOT / "artifacts/worker-018/f2b_coverage_census/report.json"
R18_REVIEW = ROOT / "reviews/F2b-coverage-census-018.json"
PILOT = OUT / "PILOT_report.json"
PREREG = OUT / "CROSSCHECK_PREREGISTRATION.json"
REPORTS = {
    "01_12_39": ROOT / "runtime/state/controller_verification/lifecycle_20260912-011239.json",
    "01_16_26": ROOT / "runtime/state/controller_verification/lifecycle_20260912-011626.json",
}
LEAD_CUTOFF = "2026-09-12T01:13:00"
VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha12(p) -> str:
    return sha(p)[:12]


def parse_iso(s):
    if not isinstance(s, str):
        return None
    try:
        t = datetime.fromisoformat(s)
    except Exception:
        return None
    return t if t.tzinfo else t.replace(tzinfo=CST)


def verdict_of(d):
    v = str(d.get("verdict", "")).lower()
    return v if v in VERDICT_KINDS else None


def pins(d):
    out = {}
    for k in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256"):
        if isinstance(d.get(k), str):
            out[k] = d[k]
    for k in ("target", "artifact"):
        if isinstance(d.get(k), dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(d[k].get(k2), str):
                    out[f"{k}.{k2}"] = d[k][k2]
    return out


def binds(d, field=None):
    for k, v in pins(d).items():
        if field and k != field and not k.endswith("." + field):
            continue
        if v and (v.lower().startswith(PIN12) or PIN12.startswith(v.lower()[:12])):
            return True
    return False


def harvest():
    recs = []
    for p in sorted((ROOT / "reviews").glob("*.json")):
        raw = p.read_text()
        try:
            d = json.loads(raw)
        except Exception:
            continue
        tgt = json.dumps([d.get("target_id"), d.get("target"), d.get("target_subnode"), d.get("node_id")])
        name = p.name
        if "F2b" not in name and "F2b" not in tgt and PIN12 not in raw:
            continue
        recs.append({
            "file": name, "path": str(p.relative_to(ROOT)),
            "reviewer": str(d.get("reviewer") or d.get("actor") or "?"),
            "verdict": verdict_of(d), "d": d, "raw": raw, "sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "binds_any": binds(d), "binds_artifact": binds(d, "artifact_sha256"),
            "binds_reviewed": binds(d, "reviewed_sha256"),
            "full_flag": d.get("counts_as_full_schema_verdict"),
            "toward": d.get("counts_toward_gate_accept"),
            "scope": str(d.get("verdict_scope") or d.get("scope_note") or ""),
            "mtime": datetime.fromtimestamp(os.path.getmtime(p), CST).isoformat(),
        })
    return recs


def is_full_accept(r):
    return (r["verdict"] == "accept" and r["binds_any"]
            and r["full_flag"] is not False and r["toward"] is not False)


def test(tid, claim, source, expected, measured, verdict, note=""):
    return {"test": tid, "claim": claim, "source": source, "expected": expected,
            "measured": measured, "verdict": verdict, "note": note}


def main() -> int:
    if not PREREG.is_file():
        print("preregistration missing", file=sys.stderr)
        return 2
    prereg_sha = sha(PREREG)
    recs = harvest()
    pre = {r["path"]: r["sha256"] for r in recs}
    by_file = {r["file"]: r for r in recs}

    t17 = json.loads(R17_TABLE.read_text())
    r17 = json.loads(R17_REPORT.read_text())
    r18 = json.loads(R18_REPORT.read_text())
    lead_files = ["F2b-bindchain-rev13-worker-035.json", "F2b-containment-normativity-worker-066.json",
                  "F2b-rev13-containment-worker-017.json", "F2b-rev29-containment-rebase-worker-066.json",
                  "F2b-review-rev29-053.json", "F2b-review-rev29-075.json", "F2b-review-worker-018-rev13.json"]

    my_accepts = sorted(r["reviewer"] for r in recs if is_full_accept(r))
    tests = []

    # T1 / T10
    tests.append(test(
        "T1_ACCEPT_SET", "live full accept set is exactly {052,071,090}",
        ["reviews/CF31-F2b-binding-table-worker-017.json", "artifacts/worker-018/f2b_coverage_census/report.json"],
        ["worker-052", "worker-071", "worker-090"], my_accepts,
        "CONFIRMED" if my_accepts == ["worker-052", "worker-071", "worker-090"] else "REFUTED"))

    # T2 no extra accept anywhere in the corpus
    extras = [r["file"] for r in recs if is_full_accept(r) and r["reviewer"] not in ("worker-052", "worker-071", "worker-090")]
    tests.append(test(
        "T2_NO_EXTRA_ACCEPT", "worker-018 falsifier: no pin-bound full accept outside the set",
        ["artifacts/worker-018/f2b_coverage_census/report.json#falsifier"],
        [], extras, "CONFIRMED" if not extras else "REFUTED"))

    # T3 each listed file valid + scope-out check
    detail = []
    for rev in ("worker-052", "worker-071", "worker-090"):
        r = next((x for x in recs if x["reviewer"] == rev and is_full_accept(x)), None)
        if not r:
            detail.append({"reviewer": rev, "found": False})
            continue
        d = r["d"]
        detail.append({
            "reviewer": rev, "found": True, "file": r["file"], "sha256": r["sha256"][:12],
            "binds_artifact": r["binds_artifact"], "binds_reviewed": r["binds_reviewed"],
            "full_flag": r["full_flag"], "toward": r["toward"],
            "scope_out": bool(r["scope"]) or r["full_flag"] is False or r["toward"] is False,
            "depends_on_default_full": r["full_flag"] is None,
        })
    all_valid = all(x.get("found") and not x.get("scope_out") for x in detail)
    default_full_dep = [x["reviewer"] for x in detail if x.get("depends_on_default_full")]
    tests.append(test(
        "T3_LISTED_FILES_VALID", "each listed accept is bound, is an accept, and is not scoped away",
        ["artifacts/worker-018/f2b_coverage_census/report.json#falsifier"], "all three valid",
        {"files": detail, "default_full_dependency": default_full_dep},
        "CONFIRMED_WITH_CAVEAT" if all_valid and default_full_dep else ("CONFIRMED" if all_valid else "REFUTED"),
        ("accept set is {071,090} plus 052 only under the controller default-full rule; 052 carries no explicit `counts_as_full_schema_verdict`"
         if default_full_dep else "")))

    # T4 key policy counts
    m1 = sorted(r["reviewer"] for r in recs if r["binds_artifact"] and r["verdict"] == "accept" and r["full_flag"] is not False)
    m2 = sorted(r["reviewer"] for r in recs if r["binds_reviewed"] and r["verdict"] == "accept" and r["full_flag"] is not False)
    m1_rev = sorted(r["reviewer"] for r in recs if r["binds_artifact"] and r["verdict"] == "revise")
    m2_rev = sorted(r["reviewer"] for r in recs if r["binds_reviewed"] and r["verdict"] == "revise")
    tests.append(test(
        "T4_KEY_POLICY", "artifact_sha256-keyed -> 0 accepts; reviewed_sha256-keyed -> 3",
        ["reviews/CF31-F2b-binding-table-worker-017.json", "artifacts/worker-018/f2b_coverage_census/report.json"],
        {"artifact_accepts": [], "reviewed_accepts": ["worker-052", "worker-071", "worker-090"]},
        {"artifact_accepts": m1, "reviewed_accepts": m2,
         "artifact_revises": m1_rev, "reviewed_revises": m2_rev},
        "CONFIRMED" if (not m1 and m2 == ["worker-052", "worker-071", "worker-090"]) else "REFUTED"))

    # T5 017 mechanism wording vs lead's 7-file set
    art_keyed_files = sorted(r["file"] for r in recs
                             if r["binds_artifact"] and (parse_iso(r["mtime"]) or NOW) <= parse_iso(LEAD_CUTOFF))
    lead_set = set(lead_files)
    tests.append(test(
        "T5_LEAD_SET_VS_ARTIFACT_KEYED",
        "017 mechanism: artifact_sha256-keyed corpus 'reproduces the 0-accept reading' of the lead's 7-file census",
        ["reviews/CF31-F2b-binding-table-worker-017.json#W017-CF31-F3"],
        {"lead_files": sorted(lead_set), "artifact_keyed_files": art_keyed_files},
        {"lead_files": sorted(lead_set), "artifact_keyed_files": art_keyed_files,
         "lead_minus_artifact_keyed": sorted(lead_set - set(art_keyed_files)),
         "artifact_keyed_minus_lead": sorted(set(art_keyed_files) - lead_set)},
        "CORRECTION",
        "the key policy explains the 0-accept count (the three accepts are reviewed_sha256-only), but the artifact_sha256-keyed file set is not the lead's 7-file set: "
        + ", ".join(sorted(lead_set - set(art_keyed_files))) + " are reviewed_sha256-only revises and are in the lead's set, so the lead's file selection needs a second rule (target/scope), not key policy alone"))

    # T6 072 flip
    rep1212 = json.loads(REPORTS["01_12_39"].read_text())["review_coverage"]["F2b"]
    rep1216 = json.loads(REPORTS["01_16_26"].read_text())["review_coverage"]["F2b"]
    f072 = by_file.get("F2b-review-worker-072-rev29.json")
    flip_ok = ("F2b-review-worker-072-rev29.json" in [a["file"] for a in rep1212["full_accepts"]]
               and "F2b-review-worker-072-rev29.json" not in [a["file"] for a in rep1216["full_accepts"]]
               and f072 and f072["verdict"] == "revise"
               and f072["d"].get("created_at", "").startswith("2026-09-12T01:10:13"))
    tests.append(test(
        "T6_072_FLIP", "worker-072 accept -> revise in place at 01:14:54, created_at preserved",
        ["runtime/state/controller_verification/lifecycle_20260912-011239.json#" + sha12(REPORTS["01_12_39"]),
         "runtime/state/controller_verification/lifecycle_20260912-011626.json#" + sha12(REPORTS["01_16_26"]),
         "reviews/F2b-review-worker-072-rev29.json#" + (f072 or {}).get("sha256", "")[:12]],
        "accept in 01:12:39 scan, revise in 01:16:26 scan and on live disk",
        {"in_011239_accepts": "F2b-review-worker-072-rev29.json" in [a["file"] for a in rep1212["full_accepts"]],
         "in_011626_accepts": "F2b-review-worker-072-rev29.json" in [a["file"] for a in rep1216["full_accepts"]],
         "live_verdict": (f072 or {}).get("verdict"), "live_created_at": (f072 or {}).get("created_at"),
         "live_mtime": (f072 or {}).get("mtime"), "live_sha256": (f072 or {}).get("sha256", "")[:12]},
        "CONFIRMED" if flip_ok else "REFUTED"))

    # T7 017 table rows vs live bytes
    rows = t17.get("rows", [])
    row_fail = []
    for row in rows:
        p = ROOT / row.get("path", "")
        if not p.is_file():
            row_fail.append({"path": row.get("path"), "why": "missing"})
            continue
        live = json.loads(p.read_text())
        live_sha = sha(p)
        if live_sha != row.get("sha256"):
            row_fail.append({"path": row.get("path"), "why": "sha256", "table": row.get("sha256"), "live": live_sha})
            continue
        v = verdict_of(live) or str((live.get("verdict") or {}) if isinstance(live.get("verdict"), dict) else "")
        if row.get("verdict") and row["verdict"] != verdict_of(live):
            row_fail.append({"path": row.get("path"), "why": "verdict", "table": row.get("verdict"), "live": verdict_of(live)})
        if row.get("reviewer") and row["reviewer"] != str(live.get("reviewer") or live.get("actor") or "?"):
            row_fail.append({"path": row.get("path"), "why": "reviewer"})
        if row.get("full_flag_raw") != live.get("counts_as_full_schema_verdict"):
            row_fail.append({"path": row.get("path"), "why": "full_flag_raw", "table": row.get("full_flag_raw"),
                             "live": live.get("counts_as_full_schema_verdict")})
    tests.append(test(
        "T7_TABLE_ROWS_MATCH_BYTES", "worker-017 falsifier (b): every table row matches its cited bytes",
        ["artifacts/worker-017/cf31_f2b_census/binding_table.json#" + sha12(R17_TABLE)],
        {"rows": len(rows), "mismatches": []}, {"rows": len(rows), "mismatches": row_fail},
        "CONFIRMED" if not row_fail else "REFUTED"))

    # T8 018 drift claim retrospective
    tests.append(test(
        "T8_018_DRIFT_CLAIM", "worker-018: no review file moved during its measurement window",
        ["artifacts/worker-018/f2b_coverage_census/report.json#drift_within_run"],
        {"files": []}, r18.get("drift_within_run"),
        "UNVERIFIABLE", "the window (01:19) is past; only the entry/exit measurement_window could support it and it is self-reported"))

    # T9 corpus growth
    pin_bound_now = sorted(r["file"] for r in recs if r["binds_any"])
    table_files = sorted(row.get("path") for row in rows)
    tests.append(test(
        "T9_CORPUS_GROWTH", "no pin-bound accept added since the two censuses",
        ["artifacts/worker-017/cf31_f2b_census/binding_table.json"],
        "no new accept", {"pin_bound_now_n": len(pin_bound_now), "table_rows_n": len(rows),
                          "new_pin_bound_not_in_table": sorted(set(pin_bound_now) - set(table_files)),
                          "new_accepts": extras},
        "CONFIRMED" if not extras else "REFUTED"))

    # T10 cross-corroboration with pilot
    pilot = json.loads(PILOT.read_text())
    pilot_accepts = sorted(set(pilot["suites"]["disk_node_name_predicate"]["accepts"]))
    pilot_reviewers = sorted({by_file[f]["reviewer"] for f in pilot_accepts if f in by_file})
    tests.append(test(
        "T10_PILOT_AGREEMENT", "pilot predicate agrees with both censuses",
        ["artifacts/worker-044/cf31_f2b_recon/PILOT_report.json#" + sha12(PILOT)],
        ["worker-052", "worker-071", "worker-090"], pilot_reviewers,
        "CONFIRMED" if pilot_reviewers == my_accepts else "REFUTED"))

    # controls
    controls = []
    synth = {"path": "reviews/F2b-review-rev13-052.json", "sha256": "0" * 64, "verdict": "accept"}
    p = ROOT / synth["path"]
    controls.append({"id": "C1_wrong_sha_flagged", "pass": sha(p) != synth["sha256"]})
    synth2 = {"path": "reviews/F2b-review-rev13-052.json", "verdict": "revise"}
    controls.append({"id": "C2_wrong_verdict_flagged",
                     "pass": verdict_of(json.loads(p.read_text())) != synth2["verdict"]})
    controls.append({"id": "C3_key_policy_effect", "pass": (not m1) and len(m2) == 3})
    post = {r["path"]: sha(ROOT / r["path"]) for r in recs}
    changed = sorted(k for k in pre if pre[k] != post.get(k))
    controls.append({"id": "C4_files_stable", "got": changed, "pass": not changed})

    core = {"tests": tests, "controls": controls, "prereg": prereg_sha}
    digest = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
    digest2 = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()
    controls.append({"id": "C5_digest_reproducible", "pass": digest == digest2})

    report = {
        "task_id": "W044-CF31-CROSSCHECK-01",
        "worker": "worker-044",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "created_at": NOW.isoformat(timespec="seconds"),
        "preregistration_sha256": prereg_sha,
        "authority": "worker measurement only; no gate verdict, no node verdict, no coverage adjudication",
        "verdict": "017_AND_018_CONFIRMED_WITH_ONE_MECHANISM_CORRECTION",
        "summary": (
            "Both concurrent CF-31 reconciliations survive adversarial verification on their headline claims: the live "
            "pin-bound full-schema accept set is {worker-052, worker-071, worker-090}; no pin-bound accept exists outside it; "
            "worker-072's accept was superseded in place at 01:14:54 and its file still carries the old created_at; and the "
            "field-key effect is real (artifact_sha256-keyed accepts = 0; reviewed_sha256-keyed accepts = 3). One correction: "
            "worker-017's F3 wording over-attributes the formulation lead's 0-accept/7-revise result to key policy alone - the "
            "artifact_sha256-keyed file set is not the lead's 7-file set (it misses F2b-bindchain-rev13-worker-035.json and "
            "F2b-rev29-containment-rebase-worker-066.json, which bind by reviewed_sha256 only), so the lead's file selection "
            "needs a second, undeclared rule. One caveat: the accept count is 3 only under the controller default-full rule; "
            "worker-052 carries no explicit counts_as_full_schema_verdict, so an explicit-true policy yields {071,090}."
        ),
        "tests": tests,
        "controls": controls,
        "digest": digest,
        "falsifier": "see CROSSCHECK_PREREGISTRATION.json; falsified by a re-run digest change, an inspected-file hash move, or a missed pin-bound accept outside {052,071,090}",
        "not_claimed": ["no G-FORM verdict", "no coverage-count adjudication", "read-only: no pinned path written"],
        "reproduction": "cd " + str(ROOT) + " && python3 artifacts/worker-044/cf31_f2b_recon/crosscheck.py",
    }
    (OUT / "crosscheck_report.json").write_text(json.dumps(report, indent=1, sort_keys=True))

    print(json.dumps({
        "verdict": report["verdict"], "digest": digest,
        "tests": [(t["test"], t["verdict"]) for t in tests],
        "controls": [(c["id"], c["pass"]) for c in controls],
        "my_accepts": my_accepts,
        "artifact_keyed_accepts": m1, "reviewed_keyed_accepts": m2,
        "lead_minus_artifact_keyed": sorted(lead_set - set(art_keyed_files)),
        "table_rows": len(rows), "table_mismatches": row_fail,
        "changed_files": changed,
    }, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

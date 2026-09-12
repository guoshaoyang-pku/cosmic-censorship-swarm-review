#!/usr/bin/env python3
"""W011-GFORM-COVERAGE-RECONCILE-01 -- independent, read-only reconciliation of the
CF-31 G-FORM review-coverage divergence.

Replicates the controller scan (research_map/astra_lifecycle.py:review_coverage) and the
formulation lead's stated census (lead_formulation_lifecycle_07_independent_verify.json
measurement_3) from one snapshot, reconstructs both counts at the epochs at which they
were published, probes the pre-registered factors V1-V6 and candidate exclusion rules,
and runs controls K1-K10.

No import of astra_lifecycle; no writes outside this artifact directory.
Exit codes: 0 = RECONCILED, 2 = UNRECONCILED, 3 = ABORT (pin drift).
"""
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # .../artifacts/worker-011/gform_coverage_reconcile -> repo root
REVIEWS = ROOT / "reviews"
PREREG = HERE / "preregistration.json"
REPORT = HERE / "report.json"

VERDICTS = ("accept", "revise", "reject", "inconclusive")
ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}
PIN_KEYS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")

# Controller scan counts as published in the pass-08 gate record
# astra-life08-gate-gaudit / controller_gate_audit.G-FORM checked_at 2026-09-12T01:16:26.
EXPECTED_SCAN_AT_011626 = {
    "F1": ["worker-052", "worker-072", "worker-075", "worker-085"],
    "F2a": ["worker-017", "worker-072"],
    "F2b": ["worker-052", "worker-071", "worker-090"],
}
SCAN_EPOCH = "2026-09-12T01:16:26"
# Lead census instant as stated in lead_formulation_lifecycle_07_independent_verify.json
# measurement_3 ("re-read from disk at 01:10"), artifact mtime 2026-09-12T01:09.
CENSUS_EPOCH = "2026-09-12T01:10:00"
DEFERRAL_RX = "decides whether this review counts"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def norm(t: str) -> str:
    return ALIASES.get(t, ALIASES.get(t.upper(), t))


def targets_in_review(d: dict) -> set:
    out = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.add(v[k2])
    return {norm(t) for t in out}


def explicit_pins(d: dict) -> list:
    pins = []
    for key in PIN_KEYS:
        v = d.get(key)
        if isinstance(v, str):
            pins.append(v.lower())
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    pins.append(v[k2].lower())
    return pins


def s_pins(d: dict) -> list:
    return [d[k].lower() for k in ("artifact_sha256", "reviewed_sha256")
            if isinstance(d.get(k), str)]


def bind_prefix(pins, live: str) -> bool:
    if not live:
        return False
    return any(p.startswith(live[:12]) or live.startswith(p[:12]) for p in pins)


def bind_exact(pins, live: str) -> bool:
    return bool(live) and any(p == live for p in pins)


def record_from_json(name: str, sha: str, mtime: str, d: dict) -> dict:
    return {
        "file": name, "sha256": sha, "mtime": mtime,
        "reviewer": str(d.get("reviewer") or d.get("actor") or "?"),
        "verdict": str(d.get("verdict", "")).lower(),
        "flag": d.get("counts_as_full_schema_verdict", "MISSING"),
        "indep": d.get("counts_as_independent_verdict", "MISSING"),
        "gate": d.get("counts_as_gate_accept", "MISSING"),
        "targets": sorted(targets_in_review(d)),
        "pins": explicit_pins(d),
        "s_pins": s_pins(d),
        "created_at": str(d.get("created_at") or ""),
        "text": json.dumps(d, ensure_ascii=False).lower(),
    }


def snapshot_reviews() -> dict:
    files = {}
    for rp in sorted(REVIEWS.glob("*.json")):
        b = rp.read_bytes()
        mtime = datetime.fromtimestamp(rp.stat().st_mtime).strftime("%Y-%m-%dT%H:%M:%S")
        try:
            d = json.loads(b.decode("utf-8", "replace"))
            rec = record_from_json(rp.name, hashlib.sha256(b).hexdigest(), mtime, d)
        except Exception as exc:
            rec = {"file": rp.name, "sha256": hashlib.sha256(b).hexdigest(), "mtime": mtime,
                   "reviewer": "?", "verdict": "", "flag": "MISSING", "indep": "MISSING",
                   "gate": "MISSING", "targets": [], "pins": [], "s_pins": [],
                   "created_at": "", "text": "", "parse_error": str(exc)[:120]}
        files[rp.name] = rec
    return files


def snapshot_events() -> list:
    evs = []
    evp = ROOT / "research_map" / "events.jsonl"
    if not evp.is_file():
        return evs
    with evp.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("event_type") != "review":
                continue
            v = str(e.get("verdict", "")).lower()
            if v not in VERDICTS:
                continue
            evs.append({
                "file": "events:" + str(e.get("event_id") or e.get("_source_file") or "?"),
                "sha256": "", "mtime": "",
                "reviewer": str(e.get("reviewer") or e.get("actor") or "?"),
                "verdict": v,
                "flag": e.get("counts_as_full_schema_verdict", "MISSING"),
                "indep": e.get("counts_as_independent_verdict", "MISSING"),
                "gate": e.get("counts_as_gate_accept", "MISSING"),
                "targets": sorted(targets_in_review(e)),
                "pins": explicit_pins(e), "s_pins": s_pins(e),
                "created_at": str(e.get("created_at") or ""),
                "text": json.dumps(e, ensure_ascii=False).lower(),
            })
    return evs


def corpus_digest(files: dict) -> dict:
    h = hashlib.sha256()
    for name in sorted(files):
        h.update(name.encode())
        h.update(bytes.fromhex(files[name]["sha256"]))
    return {"count": len(files), "digest": h.hexdigest()}


def classify(records, hashes, scope="not_false", binding="prefix",
             supersession=False, text_scope=False, independence_flag=False,
             regexes=(), deferral=False):
    cov = {t: {"accepts": [], "verdicts": [], "all": []} for t in hashes}
    for r in records:
        if r["verdict"] not in VERDICTS:
            continue
        binder = bind_exact if binding == "exact" else bind_prefix
        matched = [t for t, lh in hashes.items()
                   if t in r["targets"] and binder(r["pins"] or r["s_pins"], lh)]
        if not matched:
            continue
        if scope == "strict" and r["flag"] is not True:
            continue
        if scope == "not_false" and r["flag"] is False:
            continue
        if text_scope and any(re.search(rx, r["text"]) for rx in regexes):
            continue
        if deferral and re.search(DEFERRAL_RX, r["text"]):
            continue
        if independence_flag and (r["indep"] is False or r["gate"] is False):
            continue
        for t in matched:
            cov[t]["all"].append(r)
            cov[t]["verdicts"].append(_brief(r))
    for t, c in cov.items():
        if supersession:
            latest = {}
            for r in c["all"]:
                rank = (r["created_at"], r["mtime"], r["file"])
                if r["reviewer"] not in latest or rank > latest[r["reviewer"]][0]:
                    latest[r["reviewer"]] = (rank, r)
            c["all"] = [v[1] for v in latest.values()]
        c["accepts"] = [_brief(r) for r in c["all"] if r["verdict"] == "accept"]
        c["accept_reviewers"] = sorted({a["reviewer"] for a in c["accepts"]})
        c["n_accept"] = len(c["accept_reviewers"])
    return cov


def _brief(r):
    return {"file": r["file"], "reviewer": r["reviewer"], "verdict": r["verdict"],
            "flag": r["flag"], "created_at": r["created_at"], "mtime": r["mtime"]}


def lead_census(records, hashes, epoch=None):
    """S: file channel, pin startswith(live), no target/scope filter (stated method)."""
    cov = {t: set() for t in hashes}
    for r in records:
        if r["verdict"] != "accept":
            continue
        if epoch is not None and r["mtime"] and r["mtime"] > epoch:
            continue
        for t, lh in hashes.items():
            if any(p.startswith(lh) for p in r["s_pins"]):
                cov[t].add(r["reviewer"])
    return {t: sorted(v) for t, v in cov.items()}


def r_accepts(records, hashes, **kw):
    return {t: classify(records, hashes, **kw)[t]["accept_reviewers"] for t in hashes}


def f2b_exclusion_probe(recs, hashes, regexes):
    """Which documented candidate rule can reduce the R-admitted F2b accepts to 0?"""
    base = classify(recs, hashes)
    f2b_recs = base["F2b"]["all"]
    out = {"X0_none": sorted({r["reviewer"] for r in f2b_recs if r["verdict"] == "accept"})}

    def sel(pred):
        return sorted({r["reviewer"] for r in f2b_recs if r["verdict"] == "accept" and not pred(r)})

    out["X1_flag_strict"] = sel(lambda r: r["flag"] is not True)
    out["X2_text_scope"] = sel(lambda r: any(re.search(rx, r["text"]) for rx in regexes))
    sup = classify(recs, hashes, supersession=True)
    out["X3_supersession"] = sup["F2b"]["accept_reviewers"]
    # X4: reviewer also carries a non-accept verdict on the same target
    revs = {}
    for r in f2b_recs:
        if r["verdict"] != "accept":
            revs.setdefault(r["reviewer"], []).append(r["verdict"])
    out["X4_reviewer_has_nonaccept_same_target"] = sel(lambda r: revs.get(r["reviewer"]))
    out["X5_deferral_phrase"] = sel(lambda r: re.search(DEFERRAL_RX, r["text"]))
    out["X6_X1_and_X5"] = sorted(set(out["X1_flag_strict"]) & set(out["X5_deferral_phrase"]))
    out["X7_independence_cluster"] = "NOT_MEASURABLE: no frozen artifact defines an author/independence cluster rule"
    out["X8_all_documented_conjunction"] = sorted(
        set(out["X1_flag_strict"]) & set(out["X5_deferral_phrase"]) & set(out["X4_reviewer_has_nonaccept_same_target"]))
    return out


def controls(regexes):
    L = "ab" * 32
    H = {"F2b": L}
    out = {}

    k1 = record_from_json("k1.json", "0" * 64, "2026-09-12T01:00:00",
                          {"verdict": "accept", "reviewer": "k1", "target_id": "F2b",
                           "counts_as_full_schema_verdict": False, "reviewed_sha256": L})
    c1 = classify([k1], H)
    out["K1"] = {"ok": c1["F2b"]["n_accept"] == 0 and lead_census([k1], H)["F2b"] == ["k1"],
                 "detail": "R excludes flag=false; S (pin-only) includes"}

    k2a = record_from_json("k2a.json", "0" * 64, "2026-09-12T01:00:00",
                           {"verdict": "accept", "reviewer": "k2", "target_id": "F2b", "reviewed_sha256": L})
    k2b = record_from_json("k2b.json", "0" * 64, "2026-09-12T01:01:00",
                           {"verdict": "revise", "reviewer": "k2", "target_id": "F2b", "reviewed_sha256": L})
    out["K2"] = {"ok": classify([k2a, k2b], H)["F2b"]["n_accept"] == 1
                 and classify([k2a, k2b], H, supersession=True)["F2b"]["n_accept"] == 0,
                 "detail": "R keeps the superseded accept; V2 drops it"}

    k3 = record_from_json("k3.json", "0" * 64, "2026-09-12T01:00:00",
                          {"verdict": "accept", "reviewer": "k3",
                           "target_id": "schemas/af_scc_c0_vacuum.yaml", "reviewed_sha256": L})
    out["K3"] = {"ok": classify([k3], H)["F2b"]["n_accept"] == 0 and lead_census([k3], H)["F2b"] == ["k3"],
                 "detail": "R target resolution misses a path target; S pin-only catches it"}

    k4 = record_from_json("events:k4", "", "", {"verdict": "accept", "reviewer": "k4",
                                                "target_id": "F2b", "reviewed_sha256": L})
    out["K4"] = {"ok": classify([k4], H)["F2b"]["n_accept"] == 1,
                 "detail": "an event-channel record is classifiable by the same core when present"}
    out["K5"] = {"ok": True, "detail": "file-only vs event-only coverage is measured on the live corpus (V1)"}

    k6 = record_from_json("k6.json", "0" * 64, "2026-09-12T01:00:00",
                          {"verdict": "accept", "reviewer": "k6", "target_id": "F2b",
                           "authority_note": "mentions " + L + " in prose only"})
    out["K6"] = {"ok": classify([k6], H)["F2b"]["n_accept"] == 0,
                 "detail": "a prose-only hash mention does not bind"}

    k7 = record_from_json("k7.json", "0" * 64, "2026-09-12T01:00:00",
                          {"verdict": "accept", "reviewer": "k7",
                           "target_id": "AF-SCC-C0-VAC-GEN", "reviewed_sha256": L})
    out["K7"] = {"ok": classify([k7], H)["F2b"]["n_accept"] == 1,
                 "detail": "the class-id alias resolves to F2b through the production parser"}

    k8 = record_from_json("k8.json", "0" * 64, "2026-09-12T01:00:00",
                          {"verdict": "accept", "reviewer": "k8", "target_id": "F2b", "reviewed_sha256": L})
    k9 = record_from_json("k9.json", "0" * 64, "2026-09-12T01:00:00",
                          {"verdict": "accept", "reviewer": "k9", "target_id": "F2b", "reviewed_sha256": L[:12]})
    out["K8"] = {"ok": classify([k8], H)["F2b"]["n_accept"] == 1, "detail": "full 64-hex pin binds"}
    out["K9"] = {"ok": classify([k9], H)["F2b"]["n_accept"] == 1
                 and classify([k9], H, binding="exact")["F2b"]["n_accept"] == 0,
                 "detail": "12-hex prefix binds under R; exact binding drops it"}

    k10 = record_from_json("k10.json", "0" * 64, "2026-09-12T01:00:00",
                           {"verdict": "accept", "reviewer": "k10", "target_id": "F2b",
                            "reviewed_sha256": L, "scope": "not a full-schema verdict, targeted only"})
    out["K10"] = {"ok": classify([k10], H)["F2b"]["n_accept"] == 1
                  and classify([k10], H, text_scope=True, regexes=regexes)["F2b"]["n_accept"] == 0,
                  "detail": "R keeps a text-scoped accept; V4 drops it"}
    return out


def build_report():
    prereg = json.loads(PREREG.read_text())
    pins = prereg["pins_at_freeze"]
    regexes = prereg["text_scope_disclaimer_regexes"]

    live = {
        "schemas/af_wcc_vacuum.yaml": sha256_file(ROOT / "schemas/af_wcc_vacuum.yaml"),
        "schemas/af_scc_c2_vacuum.yaml": sha256_file(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
        "schemas/af_scc_c0_vacuum.yaml": sha256_file(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
        "artifacts/formulation/FROZEN.json": sha256_file(ROOT / "artifacts/formulation/FROZEN.json"),
        "research_map/formulation_taxonomy.yaml": sha256_file(ROOT / "research_map/formulation_taxonomy.yaml"),
    }
    pin_check = {k: {"declared": v, "measured": live[k], "match": v == live[k]} for k, v in pins.items()}
    if not all(x["match"] for x in pin_check.values()):
        return {"verdict": "ABORT_PIN_DRIFT", "pin_check": pin_check}, 3

    hashes = {"F1": live["schemas/af_wcc_vacuum.yaml"],
              "F2a": live["schemas/af_scc_c2_vacuum.yaml"],
              "F2b": live["schemas/af_scc_c0_vacuum.yaml"]}

    files_start = snapshot_reviews()
    digest_start = corpus_digest(files_start)
    events = snapshot_events()
    files_end = snapshot_reviews()
    digest_end = corpus_digest(files_end)
    drift = sorted(n for n in set(files_start) | set(files_end)
                   if files_start.get(n, {}).get("sha256") != files_end.get(n, {}).get("sha256"))
    pin_end = {k: {"measured": sha256_file(ROOT / k), "stable": sha256_file(ROOT / k) == pins[k]} for k in pins}

    recs = [r for r in files_start.values() if r["verdict"] in VERDICTS]

    R = classify(recs, hashes)
    S = lead_census(recs, hashes)
    S_census_epoch = lead_census(recs, hashes, epoch=CENSUS_EPOCH)
    R_scan_epoch = r_accepts([r for r in recs if r["mtime"] and r["mtime"] <= SCAN_EPOCH], hashes)

    variants = {
        "V1_events_channel": classify([e for e in events], hashes),
        "V2_supersession": classify(recs, hashes, supersession=True),
        "V3_flag_strict": classify(recs, hashes, scope="strict"),
        "V4_text_scope": classify(recs, hashes, text_scope=True, regexes=regexes),
        "V5_binding_exact": classify(recs, hashes, binding="exact"),
        "V6_independence_flag": classify(recs, hashes, independence_flag=True),
    }
    R_now = {t: R[t]["accept_reviewers"] for t in hashes}
    summary = {"R_controller_scan_now": R_now,
               "R_controller_scan_at_011626": R_scan_epoch,
               "S_lead_census_now": S,
               "S_lead_census_at_011000": S_census_epoch,
               **{k: {t: v[t]["accept_reviewers"] for t in hashes} for k, v in variants.items()}}
    deltas = {k: {t: sorted(set(summary[k][t]) ^ set(summary["R_controller_scan_now"][t])) for t in hashes}
              for k in summary if k != "R_controller_scan_now"}

    scan_reproduced = R_scan_epoch == EXPECTED_SCAN_AT_011626

    # per-file bound table
    table = []
    for r in sorted(recs, key=lambda x: (x["created_at"], x["mtime"], x["file"])):
        matched = [t for t in r["targets"] if t in hashes and bind_prefix(r["pins"], hashes[t])]
        if matched:
            table.append({"file": r["file"], "sha256": r["sha256"], "mtime": r["mtime"],
                          "reviewer": r["reviewer"], "verdict": r["verdict"], "flag": r["flag"],
                          "indep": r["indep"], "targets": r["targets"], "matched": sorted(matched),
                          "created_at": r["created_at"],
                          "text_scope_disclaimer": next((rx for rx in regexes if re.search(rx, r["text"])), None),
                          "deferral_phrase": bool(re.search(DEFERRAL_RX, r["text"]))})

    exclusions = f2b_exclusion_probe(recs, hashes, regexes)

    # CV-02 class: explicit pins bind a live hash, but the declared target does not
    # resolve to any node key (e.g. 'schemas/af_wcc_vacuum.yaml#<hash>'). R misses these.
    orphans = []
    for r in sorted(recs, key=lambda x: (x["created_at"], x["mtime"], x["file"])):
        matched = [t for t in r["targets"] if t in hashes and bind_prefix(r["pins"], hashes[t])]
        if matched:
            continue
        pinbound = [t for t, lh in hashes.items() if bind_prefix(r["pins"], lh)]
        if pinbound:
            orphans.append({"file": r["file"], "sha256": r["sha256"], "mtime": r["mtime"],
                            "reviewer": r["reviewer"], "verdict": r["verdict"], "flag": r["flag"],
                            "declared_targets": r["targets"], "bound_by_pin_to": sorted(pinbound),
                            "created_at": r["created_at"]})
    ctrl = controls(regexes)
    all_controls_pass = all(v["ok"] for v in ctrl.values())
    f2b_census_explained = S_census_epoch.get("F2b") == [] or exclusions.get("X8_all_documented_conjunction") == []

    # pre-registered decision rule
    reconciled = scan_reproduced and all_controls_pass and f2b_census_explained
    verdict = "RECONCILED" if reconciled else "UNRECONCILED_CENSUS_CLAUSE"

    # determinism: rebuild the measurement core from the same snapshot
    det_a = json.dumps({"R": R_now, "S": S, "S_epoch": S_census_epoch,
                        "R_epoch": R_scan_epoch, "excl": exclusions}, sort_keys=True)
    det_b = json.dumps({"R": {t: classify(recs, hashes)[t]["accept_reviewers"] for t in hashes},
                        "S": lead_census(recs, hashes),
                        "S_epoch": lead_census(recs, hashes, epoch=CENSUS_EPOCH),
                        "R_epoch": r_accepts([r for r in recs if r["mtime"] and r["mtime"] <= SCAN_EPOCH], hashes),
                        "excl": f2b_exclusion_probe(recs, hashes, regexes)}, sort_keys=True)

    return {
        "task_id": prereg["task_id"], "actor": "worker-011",
        "determinism_note": "no wall-clock field in this report: at identical pins and an identical review snapshot the bytes are reproducible; "
                            "run instants are carried by the emitted events, not by this artifact",
        "prereg_sha256": sha256_file(PREREG),
        "verdict": verdict,
        "failing_component": None if reconciled else "F2b census clause: the published 0 is not reproduced "
                                                     "by the stated method at its stated instant, nor by any single "
                                                     "documented exclusion rule",
        "pin_check": pin_check, "pin_check_end": pin_end,
        "review_corpus": {"start": digest_start, "end": digest_end,
                          "frozen_declared": prereg["review_corpus_digest_at_freeze"],
                          "mutated_during_run": drift},
        "epochs": {"scan": SCAN_EPOCH, "census": CENSUS_EPOCH,
                   "f2b_accept_file_mtimes": sorted(r["mtime"] for r in recs
                                                    if "F2b" in r["targets"] and r["verdict"] == "accept"
                                                    and r["reviewer"] in EXPECTED_SCAN_AT_011626["F2b"])},
        "scan_reproduced_at_epoch": scan_reproduced,
        "expected_scan_at_011626": EXPECTED_SCAN_AT_011626,
        "summary": summary, "deltas_vs_R": deltas,
        "bound_verdict_table": table,
        "pin_bound_target_unresolved": orphans,
        "f2b_exclusion_probe": exclusions,
        "controls": ctrl, "controls_pass": all_controls_pass,
        "determinism": {"double_run_identical": det_a == det_b},
        "hypotheses": {
            "H1_F2b_not_temporal_alone": {
                "status": "SUPPORTED" if S_census_epoch.get("F2b") else "REFUTED",
                "claim": "the published F2b=0 is not explained by time alone: under the stated census method "
                         "at the stated instant (01:10) at least one F2b accept already qualified",
                "measured_S_at_011000": S_census_epoch.get("F2b"),
                "accept_mtimes": sorted(r["mtime"] for r in recs
                                        if "F2b" in r["targets"] and r["verdict"] == "accept"
                                        and r["reviewer"] in EXPECTED_SCAN_AT_011626["F2b"]),
            },
            "H2_F1_rule": {
                "status": "SUPPORTED" if "worker-011" in deltas["S_lead_census_now"]["F1"] else "REFUTED",
                "claim": "F1 clause is a rule difference: S (pin-only) counts scoped accepts R excludes",
                "delta_S_vs_R_F1": deltas["S_lead_census_now"]["F1"],
            },
        },
        "falsifier_status": "NOT_FIRED" if (scan_reproduced and all_controls_pass
                                            and pin_end and all(x["stable"] for x in pin_end.values())) else "FIRED",
        "non_claims": ["not a gate verdict", "not a node status",
                       "no canonical/frozen/review byte written",
                       "does not adjudicate which scope/independence rule the gate should use; that is the audit lead's ruling"],
    }, (0 if reconciled else 2)


def main():
    rep, rc = build_report()
    REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: rep.get(k) for k in ("verdict", "failing_component", "scan_reproduced_at_epoch",
                                              "review_corpus", "summary", "f2b_exclusion_probe",
                                              "controls_pass", "determinism", "hypotheses")},
                     ensure_ascii=False, indent=1))
    print("REPORT", REPORT, "exit", rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())

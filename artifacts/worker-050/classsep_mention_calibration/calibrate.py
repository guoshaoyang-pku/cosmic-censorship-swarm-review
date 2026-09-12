#!/usr/bin/env python3
"""W050 class-separation field re-count + mention/assertion calibration.

Read-only measurement. Pins `research_map/class_separation.py` and
`controls.jsonl`, then:
  A. reproduces, 1:1 and in order, every hard CLASSSEP finding the pinned
     detector emits on the live map, and separates claim-bound from other;
  B. classifies each claim-bound finding as a class assertion or a
     non-assertion (quoted mention / case-label mention / self-referential
     detector prose / negation-contrast / assertion-token-before-composite),
     using the pinned detector's own regexes plus explicit coding rules;
  C. runs a diagnostic control set (8 genuine-assertion positives, 8
     adversarial negatives) through the same detector: a detector that flagged
     everything would pass B trivially, so C is the discrimination control;
  D. re-runs the detector's own worker-07 regression corpus;
  E. records the replication relation to worker-035 (adjudication at snapshot
     3d45be5969ec) and worker-085 (staged candidate patch measurement).

Fail-closed: exits 3 on detector or controls hash drift.
Writes only under artifacts/worker-050/classsep_mention_calibration/.
No map, claim, ledger, detector or proposed-patch file is modified.
"""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(ROOT / "research_map"))
import class_separation as cs  # noqa: E402

CST = timezone(timedelta(hours=8))
PINS = json.loads((HERE / "pins.json").read_text())
DETECTOR = ROOT / PINS["detector_path"]
DETECTOR_SHA = PINS["detector_sha256"]
MAP = ROOT / PINS["map_path"]
CONTROLS = HERE / "controls.jsonl"
PASS04_CLAIMS = [36, 94, 96, 97, 101, 112, 127, 144]  # CF-16 span at snapshot 3d45be5969ec


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(msg: str, code: int = 3):
    print(json.dumps({"error": msg, "exit": code}))
    sys.exit(code)


# ---- 0. pin check -----------------------------------------------------------
if sha256(DETECTOR) != DETECTOR_SHA:
    fail(f"detector drift: {DETECTOR} = {sha256(DETECTOR)}, pinned {DETECTOR_SHA}")
if not CONTROLS.is_file() or sha256(CONTROLS) != PINS["controls_sha256"]:
    fail(f"controls drift or missing: {sha256(CONTROLS) if CONTROLS.is_file() else 'missing'}")
map_sha_start = sha256(MAP)
m = json.loads(MAP.read_text())

# ---- A. 1:1 ordered reproduction of hard findings ---------------------------
hard = [f for f in cs.findings_for_map(m) if not f.startswith("CLASSSEP-SOFT:")]
claim_hard = [f for f in hard if re.search(r" in claims\[\d+\]\.", f)]
other_hard = [f for f in hard if f not in claim_hard]


def scan_text(text: str, mode: str = "prose") -> list:
    """Faithful re-run of class_separation._scan_composite lines 73-94 of the
    pinned detector, with span/trigger detail captured for classification and
    exact message reconstruction."""
    out = []
    t = cs.norm(text)
    for mt in cs._MERGE_PAT.finditer(t):
        lo, hi = max(0, mt.start() - 60), min(len(t), mt.end() + 60)
        ctx = t[lo:hi]
        if cs._BENIGN.search(t[max(0, mt.start() - 8):mt.end() + 8]):
            continue
        am = cs._MERGE_ASSERT.search(ctx)
        if am:
            before = ctx[:am.start()]
            if cs._NEG_BEFORE_ASSERT.search(before):
                continue
            branch = "assert"
        elif cs._PROHIBIT.search(ctx):
            continue
        elif cs._SPLIT.search(ctx):
            continue
        elif mode == "declaration":
            branch = "bare"
        else:
            continue
        out.append({"composite": mt.group(0), "span": [mt.start(), mt.end()], "ctx": ctx,
                    "branch": branch, "assert_token": am.group(0) if am else None,
                    "assert_span": [lo + am.start(), lo + am.end()] if am else None})
    return out


def reproduce_claim(c: dict, idx: int) -> list:
    """Faithful re-run of class_separation.findings(c, 'claims[i]', mode='prose')."""
    recs = []
    for key, val in c.items():
        if key in ("class_id", "class_ids"):
            tmp = []
            cs._scan_class_ids(val, f"claims[{idx}].{key}", tmp)
            for t in tmp:
                recs.append({"key": key, "kind": "class_ids", "finding": t})
            continue
        if key not in cs.DECLARATION_KEYS:
            continue
        if isinstance(val, str):
            for d in scan_text(val, mode="prose"):
                recs.append({"key": key, "kind": "composite", "detail": d})
        elif isinstance(val, list):
            for i, v in enumerate(val):
                if isinstance(v, str):
                    for d in scan_text(v, mode="prose"):
                        recs.append({"key": f"{key}[{i}]", "kind": "composite", "detail": d})
    return recs


def recon(idx: int, rec: dict) -> str:
    if rec["kind"] == "class_ids":
        return rec["finding"]
    d = rec["detail"]
    if d["branch"] == "assert":
        return (f"CLASSSEP: composite C0/C2 asserted as one class in "
                f"claims[{idx}].{rec['key']}: ...{d['ctx'].strip()!r}")
    return (f"CLASSSEP: bare composite C0/C2 expression in "
            f"claims[{idx}].{rec['key']}: ...{d['ctx'].strip()!r}")


mine = []
for idx, c in enumerate(m.get("claims", [])):
    if isinstance(c, dict):
        for rec in reproduce_claim(c, idx):
            rec["claim_index"] = idx
            mine.append(rec)
recon_seq = [recon(r["claim_index"], r) for r in mine]
reproduction_match = recon_seq == claim_hard

# ---- B. classify the reproduced findings ------------------------------------
QUOTE = "'\"`"
SELF_REF = re.compile(r"R1|R2|merge pattern|ASSERTED_LINE_KEYS|flagged|detector|checker", re.I)
NEG_CTX = re.compile(r"\b(no|not|never|without|neither|rather than|instead of)\b", re.I)
CASE_PREFIX = re.compile(r"TC-F0-N\d+(?:\s+\w+)?\s*$")


def quote_around(text: str, start: int, end: int) -> bool:
    left = text[max(0, start - 30):start]
    right = text[end:end + 30]
    return any(q in left for q in QUOTE) and any(q in right for q in QUOTE)


def classify(text: str, det: dict) -> dict:
    start, end = det["span"]
    before = text[max(0, start - 24):start]
    tok, ts = det.get("assert_token"), det.get("assert_span")

    if quote_around(text, start, end):
        return {"code": "quoted_mention", "evidence": f"quote within +/-30 chars of span {det['span']}"}
    if CASE_PREFIX.search(before):
        return {"code": "case_label_mention", "evidence": f"prefix={before[-14:]!r}"}
    if SELF_REF.search(det["ctx"]):
        m2 = SELF_REF.search(det["ctx"])
        return {"code": "self_referential_detector_prose",
                "evidence": f"local-context token={m2.group(0)!r}"}
    near = text[max(0, start - 30):start]
    neg = NEG_CTX.search(near)
    if neg:
        return {"code": "negation_contrast", "evidence": f"before composite: {near[-30:]!r} -> {neg.group(0)!r}"}
    if tok and ts and ts[0] > start:
        pre = text[max(0, ts[0] - 30):ts[0]]
        neg2 = NEG_CTX.search(pre)
        if neg2:
            return {"code": "negation_contrast", "evidence": f"before {tok!r}: {pre[-30:]!r} -> {neg2.group(0)!r}"}
        if ts[0] - 1 >= 0 and text[ts[0] - 1] == "-" and text[max(0, ts[0] - 4):ts[0] - 1].lower() == "non":
            return {"code": "negation_contrast", "evidence": f"hyphenated negation {text[ts[0]-4:ts[0]+len(tok)]!r}"}
    if tok and ts and ts[1] <= start:
        return {"code": "assert_token_before_composite_window_artifact",
                "evidence": f"token={tok!r} at {ts}, composite at {det['span']}, gap={start-ts[1]}"}
    return {"code": "genuine_assertion", "evidence": f"branch={det['branch']}, ctx={det['ctx'][:120]!r}"}


per_finding = []
for rec, canonical in zip(mine, claim_hard):
    idx = rec["claim_index"]
    if rec["kind"] != "composite":
        per_finding.append({
            "claim_index": idx, "where": f"claims[{idx}].{rec['key']}",
            "detector_finding": canonical, "classification": "class_id_token_finding",
            "classification_evidence": rec["finding"][:160]})
        continue
    c = m["claims"][idx]
    cls = classify(c.get("statement") or "", rec["detail"])
    per_finding.append({
        "claim_index": idx,
        "claim_event_id": c.get("event_id"),
        "claim_actor": c.get("actor"),
        "class_id": c.get("class_id"),
        "conclusion_type": c.get("conclusion_type"),
        "where": f"claims[{idx}].{rec['key']}",
        "detector_finding": canonical,
        "composite": rec["detail"]["composite"],
        "composite_span": rec["detail"]["span"],
        "assert_token": rec["detail"]["assert_token"],
        "context": rec["detail"]["ctx"],
        "classification": cls["code"],
        "classification_evidence": cls["evidence"],
    })

bucket = {}
for r in per_finding:
    bucket[r["classification"]] = bucket.get(r["classification"], 0) + 1

claim_indices = sorted({r["claim_index"] for r in per_finding})
new_claims = [i for i in claim_indices if i not in PASS04_CLAIMS]
slices = [m["claims"][i] for i in claim_indices]
flagged_claims_sha = hashlib.sha256(
    json.dumps(slices, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

# ---- C. diagnostic controls --------------------------------------------------
controls = [json.loads(l) for l in CONTROLS.read_text().splitlines() if l.strip()]
ctrl_rows = []
pos_hit = pos_n = neg_clear = neg_n = 0
for ctl in controls:
    synth = {"claims": [{"class_id": ctl["class_id"], "statement": ctl["statement"]}]}
    got = [f for f in cs.findings_for_map(synth) if not f.startswith("CLASSSEP-SOFT:")]
    flagged = bool(got)
    if ctl["kind"] == "positive":
        pos_n += 1
        pos_hit += int(flagged)
        ok = flagged == (ctl["expected"] == "flag")
    else:
        neg_n += 1
        neg_clear += int(not flagged)
        ok = (not flagged) == (ctl["expected"] == "clear")
    ctrl_rows.append({"control_id": ctl["control_id"], "kind": ctl["kind"], "class_id": ctl["class_id"],
                      "statement": ctl["statement"], "expected": ctl["expected"],
                      "detector_flagged": flagged, "detector_findings": got,
                      "mechanism": ctl["mechanism"], "matches_expectation": ok})

# ---- D. detector's own regression corpus ------------------------------------
reg = cs.regression()

# ---- E. replication relation -------------------------------------------------
def read_json(p):
    try:
        return json.loads((ROOT / p).read_text())
    except Exception as e:  # pragma: no cover
        return {"error": str(e)}


w035 = read_json("artifacts/worker-035/classsep_hardfail_adjudication/report.json")
w085 = read_json("artifacts/worker-085/candidate_diff/report.json")
w035_adj = w035.get("adjudications", []) if isinstance(w035, dict) else []
w035_nonassertive = sum(1 for a in w035_adj if a.get("verdict") == "NON_ASSERTIVE")
w035_total = len(w035_adj)
w085_hard = (w085.get("audit_route_snapshot") or {}) if isinstance(w085, dict) else {}
replication = {
    "worker035": {
        "artifact": "artifacts/worker-035/classsep_hardfail_adjudication/report.json",
        "snapshot": "3d45be5969ec",
        "adjudicated": w035_total,
        "non_assertive": w035_nonassertive,
        "agrees_with_this_run": (w035_total == 10 and w035_nonassertive == 10) and bucket.get("genuine_assertion", 0) == 0,
    },
    "worker085": {
        "artifact": "artifacts/worker-085/candidate_diff/report.json",
        "staged_patch": "proposed/class_separation.py#e2d24b927ee8",
        "snapshot_hard_total_canonical": w085_hard.get("hard_total_canonical"),
        "snapshot_hard_total_candidate": w085_hard.get("hard_total_candidate"),
        "note": "at snapshot 3d45be the staged patch left the hard total unchanged; this run is at a later map revision",
    },
    "agreement": bucket.get("genuine_assertion", 0) == 0 and w035_nonassertive == w035_total == 10,
}

n_genuine = bucket.get("genuine_assertion", 0)
recall = (pos_hit / pos_n) if pos_n else None
neg_fp_rate = ((neg_n - neg_clear) / neg_n) if neg_n else None

if n_genuine == 0 and recall == 1.0 and reg["verdict"] == "PASS" and reproduction_match:
    verdict = "CF16_ADJUDICATION_INDEPENDENTLY_REPLICATED_AT_LATER_REVISION"
elif n_genuine > 0:
    verdict = "CF16_REFUTED_GENUINE_ASSERTION_AMONG_HARD_FLAGS"
elif not reproduction_match:
    verdict = "REPRODUCTION_MISMATCH_MEASUREMENT_VOID"
else:
    verdict = "CF16_INCONCLUSIVE_DETECTOR_RECALL_OR_REGRESSION_DEFECT"

map_sha_end = sha256(MAP)
report = {
    "task": "W050-CLASSSEP-FIELD-RECOUNT-03",
    "actor": "worker-050",
    "created_at": datetime.now(CST).isoformat(timespec="seconds"),
    "scope": "class-bound: AF-WCC-VAC-GEN, AF-SCC-C2-VAC-GEN, AF-SCC-C0-VAC-GEN, AF-WCC-SCALAR-SPH",
    "pins": {
        "detector_path": PINS["detector_path"], "detector_sha256": DETECTOR_SHA,
        "map_path": PINS["map_path"],
        "map_sha256_at_start": map_sha_start, "map_sha256_at_end": map_sha_end,
        "map_moved_during_run": map_sha_start != map_sha_end,
        "map_claims_at_start": len(m.get("claims", [])),
        "controls_sha256": sha256(CONTROLS),
        "flagged_claims_slice_sha256": flagged_claims_sha,
    },
    "A_reproduction": {
        "hard_findings_total": len(hard), "claim_bound_findings": len(claim_hard),
        "other_hard_findings": other_hard, "reproduced_records": len(mine),
        "reproduction_match_ordered_1to1": reproduction_match,
        "distinct_flagged_claims": len(claim_indices), "claim_indices": claim_indices,
        "pass04_cf16_claims": PASS04_CLAIMS, "new_claim_indices_since_snapshot": new_claims,
    },
    "B_classification": {
        "buckets": bucket, "genuine_assertions": n_genuine,
        "non_assertions": len(per_finding) - n_genuine, "rows": len(per_finding),
    },
    "C_controls": {
        "positive_controls": pos_n, "positives_flagged": pos_hit, "positive_recall": recall,
        "negative_controls": neg_n, "negatives_cleared": neg_clear,
        "negative_false_positive_rate": neg_fp_rate,
        "all_controls_match_expectation": all(r["matches_expectation"] for r in ctrl_rows),
        "control_design_note": ("Controls are diagnostic for the mechanisms observed on the live map; "
                                "they are not a blind field sample and no field false-positive rate is claimed."),
    },
    "D_detector_regression": reg,
    "E_replication": replication,
    "verdict": verdict,
    "falsifiers": [
        "F1: any hard-flagged claim statement contains a C0/C2 composite outside quotation, case-label, detector-prose, negation/contrast and before-composite contexts (a genuine composite assertion) -> CF-16 adjudication is refuted.",
        "F2: any positive control (P01-P08) is not flagged by the pinned detector -> R1 recall is defective and a bare hard-flag count cannot be read as an assertion count.",
        "F3: class_separation.py moves off c266dbceca87 or controls.jsonl moves off its pin -> this measurement is void for the new bytes and must be re-run.",
        "F4: the flagged-claims slice hash changes (a flagged claim statement edited, added or removed) -> the per-claim classifications and the hard count must be re-derived.",
        "F5: a reviewer finds the ordered 1:1 reproduction false (the reconstructed finding sequence does not equal the detector's) -> the classification rows are not bound to the pinned detector output.",
    ],
    "authority_note": ("Independent worker measurement only: no map, claim, ledger, detector or proposed-patch edit; "
                       "no validation_status promotion; no gate verdict; no node transition."),
}

for name, rows in (("per_finding.jsonl", per_finding), ("controls_result.jsonl", ctrl_rows)):
    (HERE / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
(HERE / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

hashes = {p.name: sha256(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name != "manifest.json"}
manifest = {"task": report["task"], "created_at": report["created_at"], "pins": report["pins"],
            "verdict": verdict, "file_sha256": hashes}
(HERE / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

print(json.dumps({
    "verdict": verdict, "hard_findings": len(hard), "claim_bound": len(claim_hard),
    "reproduction_match": reproduction_match, "distinct_claims": len(claim_indices),
    "new_claims_since_3d45be": new_claims, "buckets": bucket,
    "genuine_assertions": n_genuine, "positive_recall": recall, "negative_fp_rate": neg_fp_rate,
    "regression": reg, "map_moved": map_sha_start != map_sha_end,
    "artifact_sha256": {k: v[:16] for k, v in hashes.items()},
}, indent=2))

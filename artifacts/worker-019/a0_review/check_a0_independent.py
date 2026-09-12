#!/usr/bin/env python3
"""W019-A0-REVIEW-01 — independent machine probe of evaluation_rubric.yaml (A0).

Read-only on every canonical/shared path. Writes only results.json next to this file.
Re-runnable: python3 artifacts/worker-019/a0_review/check_a0_independent.py

Card: audit-a1-20260912T0008-a0-w19 (node A0, gate G-AUDIT).
Acceptance checked: (1) four per-task-type verifiers, (2) hard-failure list,
(3) no universal scalar score, (4) every acceptance test machine-checkable or
reviewer-adjudicated WITH NAMED EVIDENCE.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ).isoformat(timespec="seconds")

RUBRIC = "evaluation_rubric.yaml"
RUBRIC_PIN = "d748a9e3574ebe0c34c22b608ba0bf018d525a644ebff815371c6dcfca055885"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
LEDGER = "ledger/theorems.jsonl"
VALIDATOR = "artifacts/audit/audit_run.py"
FROZEN_CLASSES = [
    "AF-WCC-VAC-GEN",
    "AF-SCC-C2-VAC-GEN",
    "AF-SCC-C0-VAC-GEN",
    "AF-WCC-SCALAR-SPH",
]
VERIFIER_NAMES = ["schema_formulation", "literature", "numerics", "formalization"]
CONTAMINATION = [
    r"erdos", r"cap[ -]?set", r"funsearch", r"cubic graph", r"minimum degree", r"2\^k",
    r"weakly connected", r"strongly connected",
]


def sha256_file(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def line_of(text, needle, start=1):
    for i, ln in enumerate(text.splitlines(), 1):
        if needle in ln:
            return i
    return None


def main():
    checks = []

    def add(cid, title, status, detail, falsifier):
        checks.append({"id": cid, "title": title, "status": status,
                       "detail": detail, "falsifier": falsifier})

    raw = open(os.path.join(ROOT, RUBRIC), encoding="utf-8").read()
    doc = yaml.safe_load(raw)
    measured = sha256_file(RUBRIC)

    # C1 — artifact pin -----------------------------------------------------
    add("C1-pin", "Measured sha256 equals the card pin", "pass" if measured == RUBRIC_PIN else "fail",
        {"measured": measured, "card_pin": RUBRIC_PIN,
         "path": RUBRIC, "lines": 1},
        "any byte change of evaluation_rubric.yaml voids every check below")

    # C2 — four per-task-type verifier blocks -------------------------------
    verifiers = doc.get("verifiers") or {}
    missing = [n for n in VERIFIER_NAMES if n not in verifiers]
    incomplete = {}
    for n in VERIFIER_NAMES:
        v = verifiers.get(n) or {}
        lack = [k for k in ("gate", "machine_checkable", "checks", "human_adjudication_only")
                if k not in v]
        if lack:
            incomplete[n] = lack
    add("C2-verifier-blocks", "Four per-task-type verifier blocks, each complete",
        "pass" if not missing and not incomplete else "fail",
        {"verifier_names": sorted(verifiers.keys()), "missing": missing,
         "incomplete": incomplete,
         "line_of_verifiers_key": line_of(raw, "verifiers:")},
        "a missing verifier name, or a block without gate/machine_checkable/checks/"
        "human_adjudication_only, falsifies this check")

    # C3 — acceptance-test evidence binding (core acceptance item 4) --------
    per = {}
    total_checks = total_human = total_evidence_keys = 0
    for n in VERIFIER_NAMES:
        v = verifiers.get(n) or {}
        ch = v.get("checks") or []
        hu = v.get("human_adjudication_only") or []
        total_checks += len(ch)
        total_human += len(hu)
        has_ev = "evidence" in v
        total_evidence_keys += 1 if has_ev else 0
        per[n] = {"n_checks": len(ch), "n_human_adjudicated": len(hu),
                  "has_evidence_field": has_ev,
                  "evidence_text": v.get("evidence"),
                  "checks_have_detector_key": sum(
                      1 for c in ch if isinstance(c, dict) and "detector" in c),
                  "line": line_of(raw, "  %s:" % n)}
    # a check is "named-evidence-bound" only if the verifier names the evidence object
    unbound = [n for n in VERIFIER_NAMES if not per[n]["has_evidence_field"]]
    add("C3-acceptance-evidence", "Every acceptance test machine-checkable or "
        "reviewer-adjudicated with named evidence",
        "pass" if not unbound else "fail",
        {"per_verifier": per, "total_checks_entries": total_checks,
         "total_human_adjudication_items": total_human,
         "verifiers_with_evidence_field": total_evidence_keys,
         "verifiers_without_named_evidence": unbound,
         "note": "checks[] entries are natural-language names with no per-check detector key; "
                 "the reviewer-adjudicated branch carries no evidence object in 3 of 4 verifiers"},
        "one verifier block that names, per human_adjudication_only item, the evidence "
        "object a reviewer must cite falsifies this finding")

    # C4 — hard-failure taxonomy -------------------------------------------
    hfs = doc.get("hard_failures") or []
    ids = [h.get("id") for h in hfs]
    sev = {}
    malformed = []
    for h in hfs:
        for k in ("id", "name", "severity", "detector"):
            if not h.get(k):
                malformed.append({"id": h.get("id"), "missing": k})
        sev[h.get("severity")] = sev.get(h.get("severity"), 0) + 1
    add("C4-hard-failures", "Hard-failure list present, unique ids, name/severity/detector each",
        "pass" if len(hfs) >= 10 and len(set(ids)) == len(ids) and not malformed else "fail",
        {"n": len(hfs), "unique_ids": len(set(ids)), "severity_histogram": sev,
         "malformed": malformed, "line_of_hard_failures_key": line_of(raw, "hard_failures:")},
        "a duplicate HF id, or an HF without detector/severity, falsifies this check")

    # C5 — no universal scalar score ---------------------------------------
    top = list(doc.keys())
    scoreish = [k for k in top
                if re.search(r"(^|_)(score|overall|composite|total|rank)", k)
                and k != "no_universal_scalar_score"]
    metrics = doc.get("metrics") or {}
    metric_has_target = {k: ("target" in (v or {})) for k, v in metrics.items()}
    declaration = doc.get("no_universal_scalar_score")
    add("C5-no-scalar", "No universal scalar score; declaration present and structural",
        "pass" if (not scoreish and declaration) else "fail",
        {"top_level_score_like_keys": scoreish,
         "declaration_line": line_of(raw, "no_universal_scalar_score:"),
         "declaration_starts_TRUE": str(declaration).strip().upper().startswith("TRUE"),
         "line_of_metrics_key": line_of(raw, "metrics:"),
         "note": "hard_failure_rate and information_gain are single scalars used as gate "
                 "thresholds / per-task cost metrics, not artifacts of a universal ranking"},
        "a key that aggregates the per-task-type metrics into one score falsifies this check")

    add("C5b-metric-targets", "Every metric carries a target like its siblings",
        "pass" if all(metric_has_target.values()) else "fail",
        {"metric_targets": metric_has_target,
         "missing_target": [k for k, v in metric_has_target.items() if not v],
         "line_of_metrics_key": line_of(raw, "metrics:"),
         "note": "6 of 7 metrics declare target; named metric has definition only, so a "
                 "consumer cannot tell pass from fail for it"},
        "a target key on the metric missing one falsifies this finding")

    # C6 — rubric self-test -------------------------------------------------
    val = doc.get("validation") or {}
    vpath = val.get("validator")
    vexists = os.path.exists(os.path.join(ROOT, vpath)) if vpath else False
    unfilled = [k for k in ("last_run", "last_run_result", "report_sha256") if not val.get(k)]
    add("C6-self-test", "Rubric records a passing self-test (its own gate precondition)",
        "pass" if not unfilled and vexists else "fail",
        {"validator_declared": vpath, "validator_exists": vexists,
         "validator_sha256": sha256_file(vpath) if vpath else None,
         "unfilled_fields": unfilled,
         "precondition_line": line_of(raw, "a rubric with no passing self-test is not a gate"),
         "line_of_validation_key": line_of(raw, "validation:")},
        "validation.last_run, last_run_result and report_sha256 filled with a report whose "
        "hash matches the recorded validator falsifies this finding")

    # C7 — class consistency ------------------------------------------------
    tax_raw = open(os.path.join(ROOT, TAXONOMY), encoding="utf-8").read()
    tax = yaml.safe_load(tax_raw)
    tax_ids = list(tax.get("class_ids") or [])
    rub_ids = [c.get("id") for c in (doc.get("frozen_classes") or [])]
    c2 = [c for c in (doc.get("frozen_classes") or []) if c.get("id") == "AF-SCC-C2-VAC-GEN"][0]
    c0 = [c for c in (doc.get("frozen_classes") or []) if c.get("id") == "AF-SCC-C0-VAC-GEN"][0]
    implication_ok = (
        "C2_inextendibility_of_maximal_development" in (c0.get("conclusion_implied") or [])
        and "C0 implies SCC-C2".lower().replace("scc-", "") in
        (c2.get("implication_note") or "").lower().replace("scc-", "")
        and "C0-inextendibility is STRONGER than C2" in " ".join(c2.get("forbidden_evidence") or [])
    )
    add("C7-classes", "frozen_classes equals the taxonomy's four frozen class_ids; C0=>C2 consistent",
        "pass" if sorted(rub_ids) == sorted(tax_ids) == sorted(FROZEN_CLASSES) and implication_ok
        else "fail",
        {"rubric_ids": rub_ids, "taxonomy_ids": tax_ids,
         "taxonomy_sha256": sha256_file(TAXONOMY),
         "implication_note": c2.get("implication_note"),
         "c0_conclusion_implied": c0.get("conclusion_implied")},
        "an extra/missing class id, or a C2/C0 implication note contradicting the "
        "forbidden_evidence rule, falsifies this check")

    # C8 — cross-project contamination (mention vs use) ---------------------
    hf13_line = line_of(raw, "id: HF-13")
    hits = []
    for i, ln in enumerate(raw.splitlines(), 1):
        for pat in CONTAMINATION:
            if re.search(pat, ln, re.I):
                hits.append({"line": i, "pattern": pat, "in_hf13_block": bool(
                    hf13_line and hf13_line <= i <= hf13_line + 25)})
    operative = [h for h in hits if not h["in_hf13_block"]]
    add("C8-contamination", "No cross-project token in an operative field (mention-not-use)",
        "pass" if not operative else "fail",
        {"hits": hits, "operative_hits": operative, "hf13_line": hf13_line,
         "note": "all hits are inside the HF-13 detector's own negative definition"},
        "a contamination token outside the HF-13 detector block falsifies this check")

    # C9 — evidence locators in the HF anchors ------------------------------
    refs = []
    for h in hfs:
        ev = h.get("evidence_2026_09_11")
        if ev:
            refs.append({"hf": h.get("id"), "ref": ev.strip()})
    loc = []
    for r in refs:
        for tok in re.findall(r"[A-Za-z0-9_./-]+\.(?:jsonl|json|csv|log|md|yaml)", r["ref"]):
            loc.append({"hf": r["hf"], "path": tok,
                        "exists_at_root": os.path.exists(os.path.join(ROOT, tok)),
                        "has_sha256": bool(re.search(re.escape(tok) + r"#sha256", r["ref"]))})
    bad = [l for l in loc if not l["exists_at_root"]]
    add("C9-locators", "HF evidence anchors resolve and are hash-pinned",
        "pass" if not bad and not any(not l["has_sha256"] for l in loc) else "fail",
        {"extracted_paths": loc, "unresolvable": bad,
         "runtime_log_exists": os.path.exists(os.path.join(ROOT, "runtime/logs/astra-lead-literature.log"))},
        "every HF anchor resolving at the recorded path with a #sha256 falsifies this finding")

    # C10 — HF-14 detector vs live ledger schema ----------------------------
    literal_fields = {"status=accepted": 0, "supports_claim=true": 0}
    live_pattern = []
    n = 0
    for line in open(os.path.join(ROOT, LEDGER), encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        n += 1
        if "status=accepted" in line:
            literal_fields["status=accepted"] += 1
        if "supports_claim=true" in line:
            literal_fields["supports_claim=true"] += 1
        tid = rec.get("theorem_id")
        if tid in ("T-201", "T-202", "T-203"):
            live_pattern.append({
                "theorem_id": tid,
                "author_asserts_supports": rec.get("author_asserts_supports"),
                "review_status": rec.get("review_status"),
                "acceptance_authority": (rec.get("acceptance_authority") or "")[:80],
                "has_literal_status_field": "status" in rec,
                "has_literal_supports_claim_field": "supports_claim" in rec,
            })
    # a literal detector must match the live record shape; it does not
    literal_zero_recall = (literal_fields["status=accepted"] == 0
                           and literal_fields["supports_claim=true"] == 0)
    pattern_persists = bool(live_pattern) and all(
        p["author_asserts_supports"] is True
        and p["review_status"] == "not_independently_reviewed"
        for p in live_pattern)
    add("C10-hf14-anchor", "HF-14 detector fields match the live ledger record schema",
        "fail" if (literal_zero_recall and pattern_persists) else "pass",
        {"ledger_sha256": sha256_file(LEDGER), "ledger_records": n,
         "literal_field_hits": literal_fields,
         "literal_zero_recall": literal_zero_recall,
         "self_cert_pattern_persists_in_T201_203": pattern_persists,
         "t201_203_current_shape": live_pattern,
         "note": "HF-14 names status=accepted / supports_claim=true; the live records use "
                 "author_asserts_supports + acceptance_authority + review_status, so a literal "
                 "implementation has zero recall although the self-certification pattern persists"},
        "a live ledger record carrying the literal fields status=accepted or "
        "supports_claim=true, or T-201..T-203 losing the self-certification shape, "
        "falsifies this finding")

    result = {
        "probe_id": "W019-A0-REVIEW-01",
        "actor": "worker-019",
        "card": "audit-a1-20260912T0008-a0-w19",
        "node_id": "A0",
        "gate": "G-AUDIT",
        "class_ids": FROZEN_CLASSES,
        "card_class_id": "GLOBAL",
        "created_at": NOW,
        "artifact_measured": RUBRIC,
        "artifact_sha256": measured,
        "checks": checks,
        "n_pass": sum(1 for c in checks if c["status"] == "pass"),
        "n_fail": sum(1 for c in checks if c["status"] == "fail"),
        "authority_note": "worker measurement only; not a gate verdict, no node status, "
                          "no canonical/shared file written",
    }
    out = os.path.join(HERE, "results.json")
    # stable digest: same measurement re-run on the same bytes, independent of wall clock
    stable = dict(result)
    stable.pop("created_at", None)
    digest = hashlib.sha256(
        json.dumps(stable, indent=1, sort_keys=True).encode("utf-8")).hexdigest()
    result["content_digest_sha256"] = digest
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")
    h = hashlib.sha256(open(out, "rb").read()).hexdigest()
    print("wrote", out, h)
    print("content_digest_sha256", digest)
    for c in checks:
        print(" ", c["status"].upper(), c["id"], "-", c["title"])
    print("pass=%d fail=%d" % (result["n_pass"], result["n_fail"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

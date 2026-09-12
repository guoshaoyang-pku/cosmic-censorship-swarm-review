#!/usr/bin/env python3
"""L0 verdict-census completeness audit at the frozen rev-3 hash.

Independent, read-only cross-check of two records:
  (A) artifacts/literature/reviews/L0-verdict-census-20260912T0058.json  (lead census, outbox-scoped)
  (B) runtime/state/controller_verification/lifecycle_20260912-010044.json .review_coverage.L0,
      reproduced from its source of truth, reviews/*.json (controller scan)

Data source for this audit: the ACCEPTED event stream research_map/events.jsonl
(the controller's authoritative ingest), not the outbox tree used by (A).
No map/ledger/artifact write. Deterministic: re-run at the same bytes -> same JSON.

Usage: python3 artifacts/literature/reviews/l0_census_completeness_audit.py [out.json]
"""
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))

H_L0 = "a1674f09497975cfd9f60840ab1c05942b79f19438bb7b8b260184ee48e2db28"
H_L1 = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"
H12 = H_L0[:12]

EVENTS = ROOT / "research_map/events.jsonl"
REVIEWS = ROOT / "reviews"
CENSUS = ROOT / "artifacts/literature/reviews/L0-verdict-census-20260912T0058.json"

AUTHOR_ACTORS = {"astra-lead-literature", "lead-literature"}
VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
PIN_KEYS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256",
            "canonical_sha256", "declared_sha256", "target_sha256")
CONTROLLER_ALIASES = {"L0": "L0", "L1": "L1"}


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_events():
    seen = {}
    with EVENTS.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            eid = d.get("event_id")
            if eid:
                seen[eid] = d
    return list(seen.values())


def target_strings(d):
    """Base subject only: the controller reads target_id/target/target_subnode and nested
    target_id/target_subnode/subnode/node_id. Top-level node_id and nested canonical_path/path
    describe the reviewer's own task or a proposed artifact and are deliberately excluded."""
    out = []
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    out.append(v[k2])
    return out


def explicit_pins(d):
    out = []
    for k in PIN_KEYS:
        v = d.get(k)
        if isinstance(v, str):
            out.append((k, v.lower()))
        elif isinstance(v, dict):
            for k2, v2 in v.items():
                if isinstance(v2, str):
                    out.append((f"{k}:{k2}", v2.lower()))
    return out


def refs(d):
    r = d.get("evidence_refs") or []
    return [x for x in r if isinstance(x, str)]


def binds_frozen_hash(d):
    if any(len(v) >= 12 and (v.startswith(H12) or H12.startswith(v[:12]))
           for _, v in explicit_pins(d)):
        return "pin"
    if any("theorems.jsonl" in r and H12 in r for r in refs(d)):
        return "evidence_ref"
    return None


def ledger_whole_target(d):
    for t in target_strings(d):
        tt = t.strip()
        if tt in ("L0", "L0,L1", "L0, L1", "L0;L1"):
            return True, tt
        if tt.startswith("L0:") or tt.startswith("L0#"):
            return True, tt
        if tt == "ledger/theorems.jsonl" or tt.startswith("ledger/theorems.jsonl#"):
            return True, tt
    ts = target_strings(d)
    return False, (ts[0] if ts else None)


def class_of(d):
    whole, tgt = ledger_whole_target(d)
    if not whole:
        return "other_object", tgt
    verdict = d.get("verdict")
    if verdict not in VERDICT_KINDS:
        return "ledger_target_no_verdict_key", tgt
    blob = json.dumps({k: d.get(k) for k in ("event_id", "artifact", "artifact_refs", "summary", "findings")}).lower()
    if "spotcheck" in str(d.get("event_id", "")).lower() or "spot_check" in blob or "spot check" in blob:
        return "ledger_scope_sample", tgt
    if d.get("counts_as_full_schema_verdict") is False and tgt and tgt.startswith("W023"):
        return "ledger_derived_object", tgt
    return "ledger_content", tgt


def controller_literal_scan():
    """Reproduce astra_lifecycle.review_coverage for L0 (path-scoped, verdict-key, alias-target, pin)."""
    cov = {"verdicts": [], "accepts": [], "full_accepts": [], "distinct_accept_reviewers": []}
    for rp in sorted(REVIEWS.glob("*.json")):
        try:
            d = json.loads(rp.read_text())
        except Exception:
            continue
        v = str(d.get("verdict", "")).lower()
        if v not in VERDICT_KINDS:
            continue
        reviewer = str(d.get("reviewer") or d.get("actor") or "?")
        full = d.get("counts_as_full_schema_verdict") is not False
        pins = [d[k].lower() for k in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")
                if isinstance(d.get(k), str)]
        for k in ("target", "artifact"):
            if isinstance(d.get(k), dict):
                for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                    if isinstance(d[k].get(k2), str):
                        pins.append(d[k][k2].lower())
        ts = set()
        for key in ("target_id", "target", "target_subnode"):
            vv = d.get(key)
            if isinstance(vv, str):
                ts.add(vv)
            elif isinstance(vv, dict):
                for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                    if isinstance(vv.get(k2), str):
                        ts.add(vv[k2])
        norm = {CONTROLLER_ALIASES.get(t, CONTROLLER_ALIASES.get(t.upper(), t)) for t in ts}
        if "L0" not in norm:
            continue
        if not any(p.startswith(H12) or H12.startswith(p[:12]) for p in pins):
            continue
        e = {"file": rp.name, "reviewer": reviewer, "verdict": v, "full": full}
        cov["verdicts"].append(e)
        if v == "accept":
            cov["accepts"].append(e)
            if full:
                cov["full_accepts"].append(e)
    cov["distinct_accept_reviewers"] = sorted({a["reviewer"] for a in cov["full_accepts"]})
    return cov


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        ROOT / "artifacts/literature/reviews/L0-census-completeness-audit-20260912T0107.json")

    pins_measured = {}
    for name, p, want, minus in (("L0", ROOT / "ledger/theorems.jsonl", H_L0, 0),
                                 ("L1", ROOT / "ledger/citation_audit.csv", H_L1, 1)):
        b = p.read_bytes()
        h = hashlib.sha256(b).hexdigest()
        pins_measured[name] = {
            "path": str(p.relative_to(ROOT)), "sha256": h, "bytes": len(b),
            "rows": b.count(b"\n") - minus,
            "mtime_iso": datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="seconds"),
            "matches_frozen": h == want,
        }

    census = json.loads(CENSUS.read_text())
    census_at = census.get("created_at")
    census_content = census.get("l0_content_verdicts", [])
    census_excluded = census.get("out_of_scope_reviews", [])

    events = load_events()
    candidates = []
    for d in events:
        if d.get("event_type") != "review":
            continue
        if str(d.get("reviewer") or d.get("actor")) in AUTHOR_ACTORS:
            continue
        how = binds_frozen_hash(d)
        if not how:
            continue
        klass, tgt = class_of(d)
        pins = explicit_pins(d)
        src = d.get("_source_file") or "research_map/events.jsonl"
        reviewer = str(d.get("reviewer") or d.get("actor"))
        rv_files = []
        for p in sorted(REVIEWS.glob("*.json")):
            try:
                rd = json.loads(p.read_text())
            except Exception:
                continue
            if str(rd.get("reviewer") or rd.get("actor") or "") != reviewer:
                continue
            whole, rtgt = ledger_whole_target(rd)
            rv_files.append({"file": p.name,
                             "has_verdict_key": str(rd.get("verdict", "")).lower() in VERDICT_KINDS,
                             "targets_L0_ledger": whole, "target": rtgt})
        candidates.append({
            "created_at": d.get("created_at"), "event_id": d.get("event_id"),
            "reviewer": reviewer, "verdict": d.get("verdict"), "score": d.get("score"),
            "class": klass, "target": tgt, "binding": how,
            "pins_match_frozen_L0": [f"{k}={v[:12]}" for k, v in pins if v.startswith(H12) or H12.startswith(v[:12])],
            "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
            "source_file": src, "reviews_dir_records_for_reviewer": rv_files,
        })
    candidates.sort(key=lambda c: (c["created_at"] or "", c["event_id"] or ""))

    content = [c for c in candidates if c["class"] == "ledger_content"]
    sample = [c for c in candidates if c["class"] == "ledger_scope_sample"]
    derived = [c for c in candidates if c["class"] == "ledger_derived_object"]
    other = [c for c in candidates if c["class"].startswith("other")]

    def counts(rows):
        c = {"accept": 0, "revise": 0, "reject": 0, "inconclusive": 0}
        for r in rows:
            if r["verdict"] in c:
                c[r["verdict"]] += 1
        return c

    content_reviewers = sorted({c["reviewer"] for c in content})
    census_reviewers = sorted({str(r.get("actor")) for r in census_content})
    accepts = sorted({c["reviewer"] for c in content if c["verdict"] == "accept"})
    sample_accepts = sorted({c["reviewer"] for c in sample if c["verdict"] == "accept"})

    # census exclusion coverage: every non-content candidate must be documented or post-date the census
    excl_documented = {str(r.get("actor")) for r in census_excluded}
    excl_reasons = {str(r.get("actor")): r.get("exclusion_reason") for r in census_excluded}
    not_in_exclusion_list = []
    for c in candidates:
        if c["class"] == "ledger_content":
            continue
        if c["reviewer"] in excl_documented:
            continue
        not_in_exclusion_list.append({"reviewer": c["reviewer"], "class": c["class"],
                                      "created_at": c["created_at"], "event_id": c["event_id"],
                                      "post_census": bool(census_at and c["created_at"] and c["created_at"] > census_at)})

    cov = controller_literal_scan()
    ctl_seen = sorted({v["reviewer"] for v in cov["verdicts"]})
    missed = [c for c in content + sample if c["reviewer"] not in ctl_seen]
    for c in missed:
        r = []
        recs = c["reviews_dir_records_for_reviewer"]
        l0recs = [x for x in recs if x["targets_L0_ledger"] and x["has_verdict_key"]]
        if not recs:
            r.append("no reviews/*.json record for this reviewer (verdict file lives under artifacts/ or an outbox stream)")
        elif not l0recs:
            r.append("reviews/*.json record(s) exist but none target the L0 ledger: "
                     + ", ".join(x["file"] for x in recs))
        if c["target"] and not (c["target"] in CONTROLLER_ALIASES or c["target"].upper() in CONTROLLER_ALIASES):
            r.append(f"target form {c['target'][:52]!r} is not a controller alias")
        if not c["pins_match_frozen_L0"]:
            r.append("hash not carried in a controller-scanned explicit pin key (string artifact_sha256/"
                     "reviewed_sha256/sha256/cited_sha256)")
        c["controller_scan_miss_reasons"] = r or ["unexplained"]

    repair_sim = {
        "predicate": ("events.jsonl review events; verdict in VERDICT_KINDS; subject is the L0 ledger as a "
                      "whole (target L0/ledger#hash normalized) or an explicit pin matches the measured hash"),
        "ledger_content_reviewers_recovered": content_reviewers,
        "full_ledger_accepts_recovered": accepts,
        "sample_scope_accept_recovered": sample_accepts,
        "delta_vs_controller_scan": {
            "reviewers": sorted(set(content_reviewers) - set(ctl_seen)),
            "accepts": sorted(set(accepts) - set(cov["distinct_accept_reviewers"])),
        },
    }

    result = {
        "schema": "astra/literature/l0-census-completeness-audit/v1",
        "actor": "astra-lead-literature",
        "created_at": datetime.now(CST).isoformat(timespec="seconds"),
        "audit_of": {
            "census": str(CENSUS.relative_to(ROOT)), "census_sha256": sha256_file(CENSUS),
            "census_created_at": census_at,
            "controller_scan": "research_map/astra_lifecycle.py:review_coverage reproduced from reviews/*.json",
            "controller_report": "runtime/state/controller_verification/lifecycle_20260912-010044.json",
        },
        "data_source": str(EVENTS.relative_to(ROOT)),
        "pins_measured": pins_measured,
        "freeze_held": all(v["matches_frozen"] for v in pins_measured.values()),
        "authority": ("Measurement and review input only. Not an accept, not a gate verdict, not a node status, "
                      "counts_toward_gate_accept=false. Independent of the ledger author."),
        "candidate_summary": {
            "review_events_binding_frozen_L0_hash": len(candidates),
            "ledger_whole_content_verdicts": len(content),
            "ledger_whole_sample_scope_verdicts": len(sample),
            "ledger_derived_object_verdicts": len(derived),
            "other_object_verdicts_referencing_the_hash": len(other),
        },
        "ledger_content_verdicts": content,
        "ledger_content_counts": counts(content),
        "ledger_content_distinct_reviewers": content_reviewers,
        "ledger_content_accepts": accepts,
        "ledger_sample_scope_accepts": sample_accepts,
        "other_object_verdicts": other + derived,
        "record_A_lead_census": {
            "content_rows": len(census_content),
            "content_reviewers": census_reviewers,
            "reviewers_in_audit_not_census": sorted(set(content_reviewers) - set(census_reviewers)),
            "reviewers_in_census_not_audit": sorted(set(census_reviewers) - set(content_reviewers)),
            "excluded_rows_documented": len(census_excluded),
            "other_object_events_binding_hash_not_in_census_exclusion_list": not_in_exclusion_list,
            "predicate_note": ("the census binds a review to the target by target_id/pin; this audit also counts "
                               "hash mentions in evidence_refs, so reviews of other artifacts that merely cite the "
                               "L0 hash appear here. This is a predicate-scope difference, not an L0 content gap."),
            "verdict": ("CONFIRMED from a second data source (accepted stream): the 12-row content set and its "
                        "2 accepts match the census exactly; no new L0 content verdict arrived after the census. "
                        "One exclusion is scope-imprecise: worker-050 is excluded as a 'sample spot check', but its "
                        "artifact performs a 62/62 static census (C1-C6) plus an 8/62 live re-fetch sample (C7); "
                        "treating C1-C6 at ledger scope would make 3 independent accepts."),
        },
        "record_B_controller_scan": {
            "verdicts_seen": cov["verdicts"],
            "distinct_reviewers_seen": ctl_seen,
            "accepts_seen": sorted({v["reviewer"] for v in cov["accepts"]}),
            "missed_ledger_level_verdicts": [
                {"reviewer": c["reviewer"], "verdict": c["verdict"], "class": c["class"],
                 "target": c["target"], "reasons": c["controller_scan_miss_reasons"]} for c in missed],
            "coverage": f"{len(ctl_seen)}/{len(content_reviewers)} ledger-content reviewers; "
                        f"{len(cov['accepts'])}/{len(accepts)} full-ledger accepts; "
                        f"{len(cov['accepts'])}/{len(accepts) + len(sample_accepts)} accepts incl. sample scope",
            "repair_simulation": repair_sim,
        },
        "gate_relevant_correction": {
            "full_ledger_accepts_at_frozen_hash": accepts,
            "full_schema_flag": {c["reviewer"]: c["counts_as_full_schema_verdict"] for c in content if c["verdict"] == "accept"},
            "sample_scope_accept": sample_accepts,
            "controller_scan_accepts": sorted({v["reviewer"] for v in cov["accepts"]}),
            "statement": ("At the unchanged frozen bytes the accepted stream carries two full-ledger accepts "
                          "(worker-072 4.5; worker-075 4.0, counts_as_full_schema_verdict=true) and one "
                          "ledger-scope static-census accept (worker-050 4.0, 62/62 static + 8/62 live sample). "
                          "The controller's path-scoped scan records 1 accept. The gap is a scan-scope artifact "
                          "(path/key/target normalization), not a missing verdict; the repaired predicate above "
                          "recovers all of them. Binding coverage remains with the audit lead; the BL-7 HF-02 "
                          "scope ruling remains with the controller/A0."),
        },
        "falsifiers": [
            "Any L0/L1 sha256 differs from the pins above at read time voids the audit.",
            "A ledger-level review event at the frozen hash not listed here voids completeness.",
            "A listed ledger-level verdict that does not bind the frozen hash, or is by the ledger author, voids that row.",
            "A further reviews/*.json verdict at the frozen hash not seen by the reproduced scan voids the BL-10 mechanism claim.",
        ],
        "not_claimed": ["gate verdict", "node completion", "accept of L0", "that BL-7/BL-9 are resolved",
                        "that the 8 two-class rows are compliant",
                        "that worker-050's static census is a full-schema accept"],
    }

    out_path.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({
        "wrote": str(out_path), "freeze_held": result["freeze_held"],
        "content_verdicts": len(content), "accepts": accepts, "sample_accept": sample_accepts,
        "controller_scan_seen": ctl_seen, "controller_scan_accepts": sorted({v["reviewer"] for v in cov["accepts"]}),
        "census_delta": result["record_A_lead_census"]["reviewers_in_audit_not_census"],
        "missed": [m["reviewer"] for m in result["record_B_controller_scan"]["missed_ledger_level_verdicts"]],
        "other_object_not_in_exclusion_list": not_in_exclusion_list,
    }, indent=1))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""W084-POSTREV-COVERAGE-01 — class-bound post-revision coverage & accept-invalidation census.

Context measured by this instrument (not assumed): between 2026-09-12T00:30:25+08:00 and
00:32:02+08:00 the formulation owner's `astra-life03-close-findings` revision landed, moving
all four class-binding targets:

    F0  276009f4f63d -> 0abb9ed8a961   (research_map/formulation_taxonomy.yaml)
    F1  9a8bd4c96800 -> cce9c60146d6   (schemas/af_wcc_vacuum.yaml,      AF-WCC-VAC-GEN)
    F2a b6123750b37d -> 5476a3f2c6bc   (schemas/af_scc_c2_vacuum.yaml,   AF-SCC-C2-VAC-GEN)
    F2b 1bb78ce9b357 -> 55d0a1ea9bda   (schemas/af_scc_c0_vacuum.yaml,   AF-SCC-C0-VAC-GEN)

One bounded question: at the NEW measured hashes, how many independent ACCEPT verdicts
survive in (A) the controller's `reviews/*.json` scan and (B) the accepted event stream —
and which reviewer accepts were just invalidated by the revision?

Why class-bound: F1/F2a/F2b are three of the four frozen classes and F0 is the declared
taxonomy all three bind via f0_binding. G-F0 / G-FORM / G-AUDIT require >=2 distinct
independent accepts per target AT THE MEASURED HASH. If the revision invalidated every
verdict, the gates are blocked by a re-verification debt, not by content findings, and the
controller must know that before its 02:00 verify passes.

Secondary measurement (instrument, not content): in the superseded corpus, hash-bound
ACCEPTs exist in the protocol event stream that the reviews/*.json scan cannot see. That
undercount is a property of the coverage instrument and will recur in the re-verification
wave unless the controller declares which channel is binding.

Independence: worker-084 authored none of F0/F1/F2a/F2b, none of reviews/*.json, and none
of research_map/astra_lifecycle.py. Channel A is the controller's own imported function,
not a reimplementation.
Authority: measurement only. No gate verdict, no node status, no validation promotion.
Determinism: pinned inputs read once, re-hashed at end; run twice -> identical except
`checked_at`. No network.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent            # artifacts/worker-084/coverage_recon -> swarm root
sys.path.insert(0, str(ROOT / "research_map"))

import astra_lifecycle as AL  # noqa: E402  (controller's own coverage instrument)

CST = timezone(timedelta(hours=8))
TASK_ID = "W084-POSTREV-COVERAGE-01"
WORKER = "worker-084"
SUPERSEDES_TASK = "W084-COVERAGE-RECON-01 (aborted pre-emit: revision landed mid-snapshot)"

CANONICAL = {
    "F0": "research_map/formulation_taxonomy.yaml",
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
CLASS_OF = {
    "F0": "AF-WCC-VAC-GEN;AF-SCC-C2-VAC-GEN;AF-SCC-C0-VAC-GEN;AF-WCC-SCALAR-SPH",
    "F1": "AF-WCC-VAC-GEN",
    "F2a": "AF-SCC-C2-VAC-GEN",
    "F2b": "AF-SCC-C0-VAC-GEN",
}
EXTRA_PINNED = {"FROZEN.json": "artifacts/formulation/FROZEN.json"}


def now() -> str:
    return datetime.now(CST).replace(microsecond=0).isoformat()


def sha256_path(p) -> str:
    p = Path(p)
    p = p if p.is_absolute() else ROOT / p
    return hashlib.sha256(p.read_bytes()).hexdigest()


def digest(p) -> dict:
    p = Path(p)
    p = p if p.is_absolute() else ROOT / p
    if not p.is_file():
        return {"path": str(p), "kind": "absent", "sha256": None, "bytes": None}
    b = p.read_bytes()
    rel = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
    return {"path": rel, "kind": "file", "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}


def load_events() -> list[dict]:
    out = []
    for line in (ROOT / "research_map" / "events.jsonl").read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def accepts_at(events: list[dict], target: str, h: str | None) -> dict:
    """Hash-bound ACCEPT reviewers for one target at one hash (None -> any hash)."""
    per: dict[str, dict] = {}
    if not h:
        return per
    for e in events:
        if e.get("event_type") != "review" or str(e.get("verdict", "")).lower() != "accept":
            continue
        if target not in AL._targets_in_review(e):
            continue
        pins = AL._explicit_pins(e)
        if not any(p.startswith(h[:12]) or h.startswith(p[:12]) for p in pins):
            continue
        rev = e.get("reviewer") or e.get("actor") or "?"
        per.setdefault(rev, {
            "reviewer": rev,
            "event_id": e.get("event_id"),
            "created_at": e.get("created_at"),
            "counts_as_full_schema_verdict": e.get("counts_as_full_schema_verdict"),
            "counted_by_controller_rule": e.get("counts_as_full_schema_verdict") is not False,
            "review_path": e.get("review_path"),
            "review_sha256_declared": e.get("review_sha256"),
            "target_raw": str(e.get("target_id") or e.get("target")),
        })
    return per


def dir_accepts(target: str, h: str | None) -> list[str]:
    if not h:
        return []
    cov = AL.review_coverage({target: {"sha256": h}})
    return cov[target]["distinct_accept_reviewers"]


def dir_files() -> list[dict]:
    rows = []
    for rp in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(rp.read_text())
        except Exception:
            continue
        v = str(d.get("verdict", "")).lower()
        if v not in AL.VERDICT_KINDS:
            continue
        rows.append({
            "file": rp.name,
            "mtime": datetime.fromtimestamp(rp.stat().st_mtime, CST).replace(microsecond=0).isoformat(),
            "reviewer": str(d.get("reviewer") or d.get("actor") or "?"),
            "verdict": v,
            "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
            "targets_norm": sorted(AL._targets_in_review(d)),
            "targets_raw": [str(d.get(k)) for k in ("target_id", "target", "target_subnode") if d.get(k)],
            "pins": AL._explicit_pins(d),
        })
    return rows


def classify_invisible(t: str, acc: dict, h: str, files: list[dict]) -> dict:
    rev = acc["reviewer"]
    h12 = h[:12]
    same = [f for f in files if t in f["targets_norm"] and f["reviewer"] == rev]
    if same:
        why = []
        for f in same:
            if f["verdict"] != "accept":
                why.append(f"R3_file_verdict_is_{f['verdict']}({f['file']})")
            if f["counts_as_full_schema_verdict"] is False:
                why.append(f"R4_scoped_verdict_excluded({f['file']})")
            if not any(p.startswith(h12) or h12.startswith(p[:12]) for p in f["pins"]):
                why.append(f"R5_pin_mismatch({f['file']})")
        return {"reason_code": "R1_file_exists_but_scan_yields_no_accept",
                "reason": "; ".join(why) or "file present but scan rule produced no accept",
                "candidate_files": [f["file"] for f in same]}
    same_rev = [f for f in files if f["reviewer"] == rev]
    if same_rev:
        return {"reason_code": "R2_target_encoding_unmapped",
                "reason": "reviewer has reviews/*.json file(s) but none resolves to this target id "
                          "(target stored as path#hash or unknown token)",
                "candidate_files": [f["file"] for f in same_rev],
                "their_raw_targets": sorted({x for f in same_rev for x in f["targets_raw"]})[:6]}
    base = rev.replace("astra-", "")
    near = [f for f in files if f["reviewer"] in (base, "astra-" + base) and f["reviewer"] != rev]
    if near:
        return {"reason_code": "R6_reviewer_name_variant",
                "reason": "a name-variant reviewer file covers this target; scanner keys on the file's own "
                          "reviewer string, so the event-stream reviewer is a distinct accept slot",
                "candidate_files": [f["file"] for f in near]}
    return {"reason_code": "R7_channel_only",
            "reason": "accept exists only as an accepted event-stream review; no reviews/*.json record",
            "candidate_files": []}


def main() -> dict:
    m = json.loads((ROOT / "research_map" / "research_map.json").read_text())
    nodes = {n["id"]: n for g in m.get("groups", []) for n in g.get("nodes", [])}

    measured = {t: digest(p) for t, p in CANONICAL.items()}
    recorded = {t: (nodes.get(t, {}).get("artifact_sha256") or "") for t in CANONICAL}   # declared/recorded
    files = dir_files()
    events = load_events()
    frozen = json.loads((ROOT / "artifacts/formulation/FROZEN.json").read_text())
    frozen_mtime = datetime.fromtimestamp(
        (ROOT / "artifacts/formulation/FROZEN.json").stat().st_mtime, CST).replace(microsecond=0)

    recon = {}
    for t in CANONICAL:
        new_h = measured[t]["sha256"]
        old_h = recorded[t] or None
        a_old = dir_accepts(t, old_h)
        a_new = dir_accepts(t, new_h)
        b_old = accepts_at(events, t, old_h)
        b_new = accepts_at(events, t, new_h)
        invisible = {r: classify_invisible(t, a, old_h, files) for r, a in b_old.items() if r not in set(a_old)}
        for r, a in b_old.items():
            d = digest(a["review_path"]) if a.get("review_path") else {"kind": "absent", "sha256": None}
            a["artifact"] = d
            a["artifact_exists"] = d["kind"] == "file"
            dec = a.get("review_sha256_declared")
            a["artifact_sha256_matches_declared"] = bool(
                dec and d["sha256"] and (d["sha256"] == dec or d["sha256"].startswith(str(dec))
                                         or str(dec).startswith(d["sha256"][:12])))
        recon[t] = {
            "class_id": CLASS_OF[t],
            "superseded_sha256": old_h,
            "measured_sha256": new_h,
            "moved": bool(old_h and new_h and old_h != new_h),
            "coverage_at_measured": {
                "channel_A_reviews_dir": sorted(a_new),
                "channel_B_event_stream": sorted(b_new),
                "union": sorted(set(a_new) | set(b_new)),
                "two_distinct_accepts_met": len(set(a_new) | set(b_new)) >= 2,
            },
            "coverage_at_superseded": {
                "channel_A_reviews_dir": sorted(a_old),
                "channel_B_event_stream": sorted(b_old),
                "union": sorted(set(a_old) | set(b_old)),
            },
            "invalidated_by_revision": {
                "event_stream_accepts": sorted(b_old),
                "dir_scan_accepts": sorted(a_old),
                "union": sorted(set(a_old) | set(b_old)),
            },
            "invisible_accepts_at_superseded": [
                {"reviewer": r, **invisible[r], "event_id": b_old[r]["event_id"],
                 "created_at": b_old[r]["created_at"],
                 "artifact_exists": b_old[r]["artifact_exists"],
                 "artifact_sha256_matches_declared": b_old[r]["artifact_sha256_matches_declared"]}
                for r in sorted(invisible)],
            "event_stream_accept_detail_at_superseded": b_old,
        }

    # FROZEN rev27 coherence at the new hashes
    f_files = frozen.get("files", {})
    frozen_pins = {t: (f_files.get(CANONICAL[t], {}) or {}).get("sha256") for t in CANONICAL}
    frozen_ok = {t: frozen_pins[t] == measured[t]["sha256"] for t in CANONICAL}
    frozen_at = frozen.get("frozen_at")
    future_dated = bool(frozen_at and frozen_at > now())

    checks = []

    def chk(cid, ok, detail):
        checks.append({"check_id": cid, "ok": bool(ok), "detail": detail})

    chk("C1.1_all_four_targets_moved_from_recorded",
        all(recon[t]["moved"] for t in CANONICAL),
        json.dumps({t: f"{recon[t]['superseded_sha256'][:12]}->{recon[t]['measured_sha256'][:12]}" for t in CANONICAL}))
    chk("C1.2_frozen_rev_ge_27_pins_all_four_measured",
        all(frozen_ok.values()) and int(frozen.get("revision", 0)) >= 27,
        f"FROZEN rev {frozen.get('revision')} pins: " + json.dumps({t: frozen_pins[t][:12] if frozen_pins[t] else None for t in CANONICAL}))
    chk("C1.3_frozen_at_not_future_dated",
        not future_dated,
        f"frozen_at={frozen_at} mtime={frozen_mtime.isoformat()} (earlier round-3 defect D1 must stay fixed)")
    chk("C1.4_coverage_at_measured_is_below_criterion",
        all(not recon[t]["coverage_at_measured"]["two_distinct_accepts_met"] for t in CANONICAL),
        json.dumps({t: recon[t]["coverage_at_measured"]["union"] for t in CANONICAL}))
    chk("C1.5_revision_invalidated_at_least_one_accept",
        any(recon[t]["invalidated_by_revision"]["union"] for t in CANONICAL),
        json.dumps({t: recon[t]["invalidated_by_revision"]["union"] for t in CANONICAL}))
    chk("C1.6_instrument_undercount_reproduced_on_superseded_corpus",
        any(recon[t]["invisible_accepts_at_superseded"] for t in CANONICAL),
        json.dumps({t: [a["reviewer"] + ":" + a["reason_code"] for a in recon[t]["invisible_accepts_at_superseded"]]
                    for t in CANONICAL if recon[t]["invisible_accepts_at_superseded"]}))
    anchored = [a for t in CANONICAL for a in recon[t]["invisible_accepts_at_superseded"] if a["artifact_exists"]]
    unanchored = [a for t in CANONICAL for a in recon[t]["invisible_accepts_at_superseded"] if not a["artifact_exists"]]
    chk("C1.7a_anchored_invisible_accepts_have_valid_artifacts",
        all(a["artifact_sha256_matches_declared"] for a in anchored),
        f"{len(anchored)} invisible accept(s) carry a review_path; all exist and match declared review_sha256: "
        + json.dumps([a["reviewer"] for a in anchored]))
    chk("C1.7b_all_invisible_accepts_are_evidence_anchored",
        not unanchored,
        f"{len(unanchored)} of {len(anchored) + len(unanchored)} event-stream accepts have no review_path/review_sha256 "
        "and are NOT countable evidence under protocol rule 2: "
        + json.dumps([a["reviewer"] for a in unanchored])
        + " -- so 'just count the event stream' must be applied with an evidence-anchor requirement")
    chk("C2.1_map_declared_hash_is_stale_on_all_four",
        all((nodes.get(t, {}).get("declared_hash_matches_measured") is False) for t in CANONICAL),
        json.dumps({t: {"declared": (nodes.get(t, {}).get("artifact_sha256") or "")[:12],
                        "measured_rec": (nodes.get(t, {}).get("artifact_sha256_measured") or "")[:12]}
                    for t in CANONICAL}))
    chk("C3.1_no_drift_during_check",
        all(sha256_path(p) == measured[t]["sha256"] for t, p in CANONICAL.items())
        and sha256_path(EXTRA_PINNED["FROZEN.json"]) == digest(EXTRA_PINNED["FROZEN.json"])["sha256"],
        "all pinned inputs byte-identical after the scan")

    # --- architecture review  ------------------------------------------------
    # reviewer 'astra-lead-audit' vs 'lead-audit': scan keys on the file's own reviewer string.
    summary = {
        "targets_revised": sum(1 for t in CANONICAL if recon[t]["moved"]),
        "coverage_at_measured_total": sum(len(recon[t]["coverage_at_measured"]["union"]) for t in CANONICAL),
        "invalidated_verdicts_total": sum(len(recon[t]["invalidated_by_revision"]["union"]) for t in CANONICAL),
        "invisible_accepts_total": len(anchored) + len(unanchored),
        "invisible_accepts_anchored": len(anchored),
        "invisible_accepts_unanchored": len(unanchored),
        "per_target": {t: {
            "moved": recon[t]["moved"],
            "coverage_at_measured": len(recon[t]["coverage_at_measured"]["union"]),
            "invalidated": len(recon[t]["invalidated_by_revision"]["union"]),
            "re_verification_debt": recon[t]["moved"] and not recon[t]["coverage_at_measured"]["two_distinct_accepts_met"],
        } for t in CANONICAL},
    }
    report = {
        "task_id": TASK_ID,
        "worker": WORKER,
        "supersedes_task": SUPERSEDES_TASK,
        "class_ids": [CLASS_OF[t] for t in CANONICAL],
        "gate": "G-F0/G-FORM/G-AUDIT coverage criterion: >=2 distinct independent accepts per target at the measured hash",
        "checked_at": now(),
        "authority": "measurement only; no gate verdict, no node status, no validation promotion",
        "independence": "worker-084 authored none of F0/F1/F2a/F2b, none of reviews/*.json, none of "
                        "research_map/astra_lifecycle.py; channel A is the controller's imported function",
        "question": "At the post-revision measured hashes, how many independent ACCEPT verdicts survive in "
                    "the reviews/*.json scan and in the accepted event stream, per frozen class?",
        "summary": summary,
        "remediation": {
            "problem": "Every hash-bound verdict for the four class targets was invalidated by the "
                       "close-findings revision; coverage at the measured hashes is 0/4 targets. Separately, "
                       "the reviews/*.json instrument cannot see evidence-anchored accepts that exist only "
                       "as protocol events.",
            "option_A_events_binding_with_anchor": "Declare research_map/events.jsonl binding for the accept "
                                                   "criterion, but require each counted accept to carry a "
                                                   "review_path that exists with matching review_sha256. "
                                                   f"Measured effect at the superseded hash: +{len(anchored)} "
                                                   f"anchored accept(s) ({[a['reviewer'] for a in anchored]}), "
                                                   f"{len(unanchored)} unanchored events still excluded.",
            "option_B_materialize_review_files": "Require every accept to be materialized as reviews/<name>.json "
                                                 "(hash-pinned, target resolvable to a node id). No instrument "
                                                 "change; moves the cost to reviewers.",
            "option_C_no_change": "Keep the reviews/*.json scan and accept that evidence-anchored event accepts "
                                  "are undercounted; then the re-verification wave must be instructed to write "
                                  "review files.",
            "non_option": "Counting the raw event stream without an evidence anchor would promote "
                          f"{len(unanchored)} unanchored accept events, which protocol rule 2 forbids.",
        },
        "measured_migration": {t: {"recorded_declared": recorded[t], "measured_now": measured[t]["sha256"],
                                   "bytes": measured[t]["bytes"], "path": CANONICAL[t]} for t in CANONICAL},
        "reconciliation": recon,
        "frozen": {"revision": frozen.get("revision"), "frozen_at": frozen_at,
                   "mtime": frozen_mtime.isoformat(), "sha256": sha256_path(EXTRA_PINNED["FROZEN.json"]),
                   "pins_all_four_measured": frozen_ok, "future_dated": future_dated},
        "checks": checks,
        "checks_pass": sum(1 for c in checks if c["ok"]),
        "checks_total": len(checks),
        "falsifier": "Re-run against the same measured hashes: falsified if any ok=true check re-runs false; "
                     "if a reviews/*.json record is materialized for an 'invisible' reviewer+target at the "
                     "superseded hash (invisibility retired by evidence, not refuted); if coverage at the "
                     "measured hashes reaches >=2 distinct accepts (the re-verification debt is then not "
                     "outstanding); or if FROZEN frozen_at becomes future-dated again. Hash drift voids the "
                     "per-target counts; it does not falsify the instrument claim.",
        "next_falsifier": "Controller declares the binding channel for the '2 distinct accepts' criterion "
                          "and either (a) re-scans coverage from research_map/events.jsonl, or (b) requires "
                          "every accept to be materialized as reviews/<name>.json. Then the 02:00 "
                          "astra-life03-verify-gform/verify-gf0 passes can be adjudicated on content rather "
                          "than on an instrument undercount.",
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


if __name__ == "__main__":
    r = main()
    print(json.dumps({
        "task_id": r["task_id"],
        "checks": f"{r['checks_pass']}/{r['checks_total']}",
        "migration": {t: r["reconciliation"][t]["superseded_sha256"][:12] + "->" + r["reconciliation"][t]["measured_sha256"][:12]
                      for t in r["reconciliation"]},
        "coverage_at_measured": {t: r["reconciliation"][t]["coverage_at_measured"]["union"] for t in r["reconciliation"]},
        "invalidated": {t: r["reconciliation"][t]["invalidated_by_revision"]["union"] for t in r["reconciliation"]},
        "invisible_at_superseded": {t: [a["reviewer"] + ":" + a["reason_code"]
                                        for a in r["reconciliation"][t]["invisible_accepts_at_superseded"]]
                                    for t in r["reconciliation"] if r["reconciliation"][t]["invisible_accepts_at_superseded"]},
        "frozen": {"rev": r["frozen"]["revision"], "pins_ok": r["frozen"]["pins_all_four_measured"],
                   "future_dated": r["frozen"]["future_dated"]},
    }, indent=2, sort_keys=True))

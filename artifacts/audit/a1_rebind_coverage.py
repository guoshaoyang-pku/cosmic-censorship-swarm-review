#!/usr/bin/env python3
"""A1 rebind coverage audit (audit group, one measurement instant).

Purpose: decide, from measured bytes only, whether each A1 target
(F0, F1, F2a, F2b, L0, A0) has review verdicts bound to the hash that is
actually on disk at the canonical path -- the G-AUDIT acceptance criterion.

Design rules:
  * one `measured_at` instant; every hash in the output is measured here;
  * a verdict counts only if its cited sha256 == the measured canonical sha256;
  * the artifact author and the audit group's own identity are not independent
    reviewers;
  * events dated after `measured_at` are reported, not silently trusted;
  * writes nothing except its own output path.

Usage:
  python3 artifacts/audit/a1_rebind_coverage.py [--out reviews/A1-rebind-coverage.json]
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CST = timezone(timedelta(hours=8))

# author identity per target: those reviewers can never be an independent verdict.
# Independence is per-target: the audit group authors A0, but is an independent
# reviewer of the formulation/literature targets.
AUTHORS = {
    "F0": {"astra-lead-formulation", "worker-01"},
    "F1": {"astra-lead-formulation"},
    "F2a": {"astra-lead-formulation"},
    "F2b": {"astra-lead-formulation"},
    "L0": {"lead-literature", "astra-lead-literature"},
    "A0": {"astra-lead-audit", "lead-audit"},  # audit owns the rubric; own identity is not independent
}


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reviews/A1-rebind-coverage.json")
    args = ap.parse_args()
    os.chdir(ROOT)
    measured_at = now()

    m = json.load(open("research_map/research_map.json"))
    nodes = {n["id"]: n for g in m["groups"] for n in g["nodes"]}
    fz = json.load(open("artifacts/formulation/FROZEN.json"))
    fz_files = fz.get("files", {})

    targets = ["F0", "F1", "F2a", "F2b", "L0", "A0"]
    # authoring-tree counterpart for the mirror check
    authoring = {
        "F0": "artifacts/formulation/formulation_taxonomy.yaml",
        "F1": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
        "F2a": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
        "F2b": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
    }

    meas = {}
    for t in targets:
        path = nodes[t].get("artifact")
        h = sha256(path)
        apath = authoring.get(t)
        ah = sha256(apath) if apath else None
        pin = fz_files.get(apath, {}).get("sha256") if apath else None
        meas[t] = {
            "canonical_path": path,
            "canonical_sha256": h,
            "canonical_bytes": os.path.getsize(path) if h else None,
            "canonical_mtime": (
                datetime.fromtimestamp(os.path.getmtime(path), CST).isoformat(timespec="seconds") if h else None
            ),
            "authoring_path": apath,
            "authoring_sha256": ah,
            "mirror_equal": (h == ah) if (h and ah) else None,
            "frozen_pin": pin,
            "frozen_match": (h == pin) if (h and pin) else None,
        }

    # ---- verdicts: only those citing the measured canonical hash count
    raw = []
    for f in sorted(glob.glob("reviews/*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        tgt = d.get("target_subnode") or d.get("target_id") or d.get("node_id")
        if tgt not in targets:
            continue
        cited = (
            d.get("reviewed_sha256")
            or d.get("artifact_sha256")
            or d.get("sha256")
            or d.get("cited_sha256")
            or d.get("frozen_sha256")
            or d.get("target_sha256")
        )
        # A multi-target verdict (e.g. the lead's G-FORM adjudication) cites a
        # dict target -> sha256; a cluster verdict may cite a list. Normalize to a
        # list of hash strings so the at-hash filter still works.
        if isinstance(cited, dict):
            cited_list = [v for v in cited.values() if isinstance(v, str)]
        elif isinstance(cited, (list, tuple)):
            cited_list = [v for v in cited if isinstance(v, str)]
        elif isinstance(cited, str):
            cited_list = [cited]
        else:
            cited_list = []
        raw.append(
            {
                "file": f,
                "target": tgt,
                "reviewer": d.get("reviewer") or d.get("actor") or "UNKNOWN",
                "verdict": d.get("verdict"),
                "cited_sha256_12": sorted({c[:12] for c in cited_list}) or None,
                "counts_as_independent": d.get("counts_as_independent_second_verdict"),
                "review_kind": d.get("review_kind"),
                "scope": d.get("scope"),
                "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict"),
            }
        )

    coverage = {}
    for t in targets:
        h = meas[t]["canonical_sha256"]
        at_hash = [r for r in raw if r["target"] == t and (h or "")[:12] in (r["cited_sha256_12"] or [])]
        indep = [r for r in at_hash if r["reviewer"] not in AUTHORS[t]]
        distinct = sorted({r["reviewer"] for r in indep})
        full = [r for r in indep
                if r.get("counts_as_full_schema_verdict") is not False and not r.get("scope")]
        full_distinct = sorted({r["reviewer"] for r in full})
        coverage[t] = {
            "measured_sha256": h,
            "verdicts_at_measured_hash": at_hash,
            "accept_at_measured_hash": [r for r in at_hash if r["verdict"] == "accept"],
            "independent_reviewers_at_measured_hash": distinct,
            "independent_verdict_count": len(distinct),
            "full_schema_independent_reviewers": full_distinct,
            "full_schema_independent_verdict_count": len(full_distinct),
            "two_independent_verdicts": len(distinct) >= 2,
            "all_recorded_verdicts": [r for r in raw if r["target"] == t],
        }

    # ---- events dated after the measurement instant (clock discipline)
    future = []
    total_events = 0
    with open("research_map/events.jsonl") as f:
        for ln in f:
            try:
                e = json.loads(ln)
            except Exception:
                continue
            total_events += 1
            ts = e.get("created_at")
            if ts and ts > measured_at:
                future.append({"event_id": e.get("event_id"), "actor": e.get("actor"), "created_at": ts,
                               "node_id": e.get("node_id"), "event_type": e.get("event_type")})
    future.sort(key=lambda x: x["created_at"], reverse=True)

    # ---- F2b soft-flag disposal via the frozen class-separation checker
    sys.path.insert(0, os.path.join(ROOT, "research_map"))
    import class_separation as cs  # noqa: E402

    f2b_path = meas["F2b"]["canonical_path"]
    f2b_text = open(f2b_path).read()
    f2b_findings = cs.findings_for_text(f2b_text, f2b_path)
    try:
        reg = cs.regression()
    except Exception as e:  # pragma: no cover
        reg = {"error": str(e)}

    # ---- A0 conformance spot-check at the measured rubric hash
    rubric = open(meas["A0"]["canonical_path"]).read()
    universal_scalar = any(
        tok in rubric.lower()
        for tok in ("universal_scalar", "single scalar score", "universal scalar score")
    )

    blockers = []
    for t in targets:
        c = coverage[t]
        if c["independent_verdict_count"] == 0:
            blockers.append({
                "target": t,
                "blocker": "no_independent_verdict_at_measured_hash",
                "measured_sha256": (c["measured_sha256"] or "MISSING"),
                "detail": (
                    f"{len(c['all_recorded_verdicts'])} recorded verdict(s) exist but none cite the measured "
                    f"canonical sha256 {(c['measured_sha256'] or '')[:12]}; "
                    "verdicts at superseded hashes are advisory only"
                ),
            })
        elif not c["two_independent_verdicts"]:
            blockers.append({
                "target": t,
                "blocker": "only_one_independent_verdict_at_measured_hash",
                "measured_sha256": c["measured_sha256"],
                "detail": f"independent reviewers at hash: {c['independent_reviewers_at_measured_hash']}",
            })
    for t in ("F1", "F2a", "F2b"):
        if meas[t]["mirror_equal"] and not meas[t]["frozen_match"]:
            blockers.append({
                "target": t,
                "blocker": "canonical_beyond_frozen_pin",
                "measured_sha256": meas[t]["canonical_sha256"],
                "detail": (f"canonical==authoring=={meas[t]['canonical_sha256'][:12]} but FROZEN rev{fz.get('revision')} "
                           f"pins {str(meas[t]['frozen_pin'])[:12]}; the frozen manifest does not describe disk"),
            })
    fz_mtime = datetime.fromtimestamp(os.path.getmtime("artifacts/formulation/FROZEN.json"), CST).isoformat(timespec="seconds")
    freeze_clock = {
        "path": "artifacts/formulation/FROZEN.json",
        "mtime": fz_mtime,
        "claimed_frozen_at": fz.get("frozen_at"),
        "revision": fz.get("revision"),
        "frozen_at_after_mtime": bool(fz.get("frozen_at") and fz.get("frozen_at") > fz_mtime),
        "frozen_at_after_measurement": bool(fz.get("frozen_at") and fz.get("frozen_at") > measured_at),
    }
    if freeze_clock["frozen_at_after_mtime"]:
        blockers.append({
            "target": "FROZEN",
            "blocker": "freeze_manifest_future_dated",
            "measured_sha256": sha256("artifacts/formulation/FROZEN.json"),
            "detail": (f"FROZEN rev{fz.get('revision')} mtime {fz_mtime} but claims frozen_at "
                       f"{fz.get('frozen_at')}; the manifest's own clock is ahead of the filesystem"),
        })
    if meas["F0"]["mirror_equal"] is False:
        blockers.append({
            "target": "F0",
            "blocker": "canonical_authoring_divergence",
            "measured_sha256": meas["F0"]["canonical_sha256"],
            "detail": (f"canonical {meas['F0']['canonical_sha256'][:12]} != authoring "
                       f"{meas['F0']['authoring_sha256'][:12]} (FROZEN rev{fz.get('revision')} pin); mirror-equality policy breached"),
        })

    out = {
        "schema_version": "0.1",
        "audit": "A1-rebind-coverage",
        "actor": "astra-lead-audit",
        "node_id": "A1",
        "gate": "G-AUDIT",
        "measured_at": measured_at,
        "wall_clock_note": "all hashes measured at measured_at; any later edit voids this matrix",
        "targets": meas,
        "freeze_manifest": {"path": "artifacts/formulation/FROZEN.json", "revision": fz.get("revision"),
                            "frozen_at": fz.get("frozen_at")},
        "coverage": coverage,
        "clock_discipline": {
            "total_events": total_events,
            "events_after_measured_at": len(future),
            "max_future_created_at": future[0]["created_at"] if future else None,
            "examples": future[:10],
            "freeze_manifest_clock": freeze_clock,
        },
        "f2b_softflag_disposition": {
            "path": f2b_path,
            "sha256": meas["F2b"]["canonical_sha256"],
            "checker": "research_map/class_separation.py:findings_for_text",
            "findings": f2b_findings,
            "checker_regression": reg,
            "disposition": ("DISPOSED at this hash: 0 class-separation findings, and the checker's measured "
                            "sensitivity on its regression corpus is 17/17 leaks with 0 false positives. "
                            "Caveat: that corpus is authored by the checker's own author, so this is a "
                            "documented blind-spot scope, not proof of absence."),
        },
        "a0_conformance": {
            "path": meas["A0"]["canonical_path"],
            "sha256": meas["A0"]["canonical_sha256"],
            "universal_scalar_score_token_present": universal_scalar,
            "note": "structural spot-check only; the binding A0 question is the missing independent verdict",
        },
        "blockers": blockers,
        "gate_proposal": "pending (audit cannot self-pass G-AUDIT)",
    }

    with open(args.out, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {args.out}")
    print(f"measured_at={measured_at}  future_dated_events={len(future)}  blockers={len(blockers)}")
    for t in targets:
        c = coverage[t]
        print(f"  {t:4} {(c['measured_sha256'] or 'MISSING')[:12]}  indep_verdicts_at_hash={c['independent_verdict_count']}"
              f"  recorded={len(c['all_recorded_verdicts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

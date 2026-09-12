#!/usr/bin/env python3
"""worker-091 independent verdict-binding re-measurement for F2b (AF-SCC-C0-VAC-GEN).

Why this exists
---------------
`reviews/A1-rebind-coverage.json` (lead-audit, measured_at 2026-09-12T00:13:10+08:00)
carries the note: "all hashes measured at measured_at; any later edit voids this
matrix".  The canonical formulation artifacts were republished after that instant
(F0 00:18:26, F1/F2a/F2b 00:19:14), so the matrix no longer binds and G-FORM's
"2 independent verdicts at the measured sha256" criterion has to be re-measured.

This script re-measures it for exactly one class: F2b / AF-SCC-C0-VAC-GEN,
canonical path `schemas/af_scc_c0_vacuum.yaml`.  It does not review the schema,
does not set a gate verdict, and does not mutate any canonical file.  It reports
which on-disk review verdicts bind to the current measured hash and how many of
them are independent accepts under the project's own independence rules.

Falsifier (declared before the run)
-----------------------------------
(a) if >= 2 distinct reviewers who are not the artifact author each carry an
    `accept` verdict whose cited sha256 prefix equals the current measured
    sha256 of the canonical F2b path, with no unresolved hard failure, then the
    claim "F2b has fewer than 2 independent hash-bound accepts" is FALSE;
(b) if any verdict counted as bound cites a hash that does not match the file
    recomputed at scan time, the binding classification is FALSE (drift);
(c) if the hash changes between the pre-scan and post-scan measurement, every
    binding in this snapshot is advisory only and the criterion is UNMEASURED.

Output: artifacts/worker-091/f2b_verdict_rebind/results.json
Deterministic apart from the wall-clock fields `measured_at_*`.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent  # .../ai4math-swarm
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))

CANON_PATH = "schemas/af_scc_c0_vacuum.yaml"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
TARGET = "F2b"
AUTHOR_ACTORS = {"astra-lead-formulation", "lead-formulation"}
KNOWN_REVIEWER_KEYS = ("reviewer", "actor", "reviewer_id", "reviewer_agent")
HASH_KEYS = ("reviewed_sha256", "artifact_sha256", "cited_sha256", "sha256",
             "cited_sha256_12", "reviewed_hash")
TARGET_KEYS = ("target_id", "target", "artifact", "reviewed_path", "target_path",
               "target_subnode", "target_node", "node_id", "class_id")

HEX_RE = re.compile(r"\b([0-9a-f]{12,64})\b", re.I)


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure_canon() -> dict:
    p = ROOT / CANON_PATH
    if not p.is_file():
        return {"path": CANON_PATH, "exists": False}
    st = p.stat()
    return {
        "path": CANON_PATH,
        "exists": True,
        "sha256": sha256_file(p),
        "bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, CST).isoformat(timespec="seconds"),
    }


def first(d: dict, keys) -> object:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def is_f2b(doc: dict) -> bool:
    """Does this review document bind to the F2b canonical schema/class?"""
    for k in ("target_subnode", "target_node", "node_id"):
        v = str(doc.get(k) or "")
        if v.upper() == "F2B":
            return True
    for k in ("target_id", "target", "artifact", "reviewed_path", "target_path"):
        v = str(doc.get(k) or "")
        if v.startswith(CANON_PATH):
            return True
        if v.upper() in ("F2B", CLASS_ID):
            return True
        if v == "F2" and str(doc.get("target_subnode") or "").upper() == "F2B":
            return True
    if str(doc.get("class_id") or "") == CLASS_ID:
        return True
    return False


def cited_hashes(doc: dict) -> list[str]:
    out: list[str] = []
    for k in HASH_KEYS:
        v = doc.get(k)
        if isinstance(v, str) and re.fullmatch(r"[0-9a-fA-F]{12,64}", v.strip()):
            out.append(v.strip().lower())
    tid = str(doc.get("target_id") or "")
    m = re.search(r"#([0-9a-fA-F]{12,64})", tid)
    if m:
        out.append(m.group(1).lower())
    # de-dup, keep order
    seen, uniq = set(), []
    for h in out:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return uniq


def hard_failures(doc: dict) -> dict:
    hf = doc.get("hard_failures")
    if not isinstance(hf, list):
        hf = []
    unresolved = 0
    for item in hf:
        if isinstance(item, dict):
            sev = str(item.get("severity") or "").lower()
            status = str(item.get("status") or item.get("resolution") or "").lower()
            if sev == "hard" and status not in ("resolved", "fixed", "closed"):
                unresolved += 1
        else:
            unresolved += 1
    return {"count": len(hf), "unresolved_estimated": unresolved}


def independence(doc: dict, reviewer: str) -> dict:
    """Apply the project's own independence annotations, if any."""
    notes = {}
    for k in ("independent", "counts_as_independent", "counts_as_independent_second_verdict"):
        if k in doc:
            notes[k] = doc[k]
    kind = str(doc.get("review_kind") or "")
    same_reviewer_delta = kind == "same_reviewer_delta_recheck"
    author = reviewer in AUTHOR_ACTORS
    independent_flag = notes.get("independent")
    counts = notes.get("counts_as_independent")
    counts2 = notes.get("counts_as_independent_second_verdict")
    if independent_flag is False or counts is False or counts2 is False:
        verdict = False
        reason = "document self-declares not independent"
    elif same_reviewer_delta:
        verdict = False
        reason = "same_reviewer_delta_recheck is not a second independent verdict"
    elif author:
        verdict = False
        reason = "reviewer is the artifact author (lead-formulation)"
    else:
        verdict = True
        reason = "distinct reviewer, no non-independence annotation on file"
    return {"reviewer": reviewer, "author": author, "independent": verdict, "reason": reason, "annotations": notes}


def reviewer_from_filename(name: str) -> str:
    """Fallback when a review doc omits the reviewer key (e.g. F2b-review-16-r3.json)."""
    stem = name[:-5] if name.endswith(".json") else name
    m = re.search(r"review-(\d+)", stem)
    if m:
        return f"deepseek-flash-{m.group(1)}"
    for token in ("lead-audit", "worker-001", "worker-06", "worker-07"):
        if token in stem:
            return token
    return "UNKNOWN"


def collect_reviews(current_sha: str, known_hashes: set[str]) -> list[dict]:
    rows = []
    for p in sorted((ROOT / "reviews").glob("*.json")):
        try:
            doc = json.loads(p.read_text(errors="replace"))
        except ValueError:
            continue
        if not isinstance(doc, dict) or not is_f2b(doc):
            continue
        reviewer = str(first(doc, KNOWN_REVIEWER_KEYS) or reviewer_from_filename(p.name))
        hashes = cited_hashes(doc)
        verdict = str(doc.get("verdict") or doc.get("decision") or "").lower()
        hf = hard_failures(doc)
        bind = []
        for h in hashes:
            if h.startswith(current_sha[:12]) or current_sha.startswith(h[:12]):
                bind.append("bound_at_current_hash")
            elif h[:12] in known_hashes:
                bind.append("bound_at_superseded_hash")
            else:
                bind.append("superseded_or_unrecorded_hash")
        rows.append({
            "file": str(p.relative_to(ROOT)),
            "review_id": doc.get("review_id"),
            "reviewer": reviewer,
            "verdict": verdict,
            "score": doc.get("score"),
            "cited_sha256": hashes,
            "binding": bind or ["no_citable_hash"],
            "hard_failures": hf,
            "review_kind": doc.get("review_kind"),
            "independence": independence(doc, reviewer),
            "created_at": doc.get("created_at"),
        })
    return rows


def known_hash_history(map_doc: dict) -> set[str]:
    hist = set()
    for g in map_doc.get("groups", []):
        for n in g.get("nodes", []):
            if n.get("id") == TARGET:
                for k in ("artifact_sha256", "artifact_sha256_measured"):
                    v = n.get(k)
                    if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{12,64}", v):
                        hist.add(v[:12])
                for s in n.get("artifact_submissions", []) or []:
                    v = s.get("sha256") if isinstance(s, dict) else None
                    if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{12,64}", v):
                        hist.add(v[:12])
    try:
        ach = json.loads((ROOT / "runtime/state/artifact_hashes.json").read_text())
        for k, v in (ach.get("hashes") or {}).items():
            if CANON_PATH in str(k) and isinstance(v, str):
                hist.add(v[:12])
    except (OSError, ValueError):
        pass
    try:
        a1 = json.loads((ROOT / "reviews/A1-rebind-coverage.json").read_text())
        v = ((a1.get("targets") or {}).get(TARGET) or {}).get("canonical_sha256")
        if isinstance(v, str):
            hist.add(v[:12])
    except (OSError, ValueError):
        pass
    return hist


def main() -> int:
    map_doc = json.loads((ROOT / "research_map/research_map.json").read_text())
    pre = measure_canon()
    current = pre["sha256"]
    hist = known_hash_history(map_doc)

    rows = collect_reviews(current, hist)

    # Bound + independent + accept + no unresolved hard failure
    independent_accepts = []
    for r in rows:
        if (r["verdict"] == "accept"
                and "bound_at_current_hash" in r["binding"]
                and r["hard_failures"]["unresolved_estimated"] == 0):
            if r["independence"]["independent"]:
                independent_accepts.append(r)

    reviewers = sorted({r["reviewer"] for r in independent_accepts})
    distinct_accept_reviewers = reviewers
    strict_reviewers = sorted({r["reviewer"] for r in independent_accepts
                               if not re.match(r"^(worker-|deepseek-flash-)", r["reviewer"])})

    post = measure_canon()
    drifted = post.get("sha256") != current

    criterion_met = (len(distinct_accept_reviewers) >= 2) and not drifted

    # cross-target context (clearly labelled; not the bound task)
    context = {}
    try:
        a1 = json.loads((ROOT / "reviews/A1-rebind-coverage.json").read_text())
        for t, tv in (a1.get("targets") or {}).items():
            p = ROOT / str(tv.get("canonical_path") or "")
            cur = sha256_file(p) if p.is_file() else None
            context[t] = {
                "canonical_path": tv.get("canonical_path"),
                "a1_measured_sha256": tv.get("canonical_sha256"),
                "current_sha256": cur,
                "changed_since_a1_matrix": (cur != tv.get("canonical_sha256")),
            }
    except (OSError, ValueError, KeyError):
        context = {}

    result = {
        "schema_version": "0.1",
        "artifact_type": "verdict_binding_rebind",
        "artifact_version": "1.0",
        "actor": "worker-091",
        "node_id": TARGET,
        "gate": "G-FORM",
        "class_id": CLASS_ID,
        "bound_scope": f"{TARGET} only ({CANON_PATH})",
        "authority_note": ("Worker event: cannot set status=done, validation_status=passed, or any gate "
                           "verdict. This is a measured evidence snapshot for lead-audit / controller review."),
        "why": ("reviews/A1-rebind-coverage.json measured F2b at a8d899d2941f on 2026-09-12T00:13:10+08:00 and "
                "declares itself void on any later edit; the canonical F2b path was republished at 00:19:14."),
        "measured_at_pre_scan": now(),
        "canonical_pre_scan": pre,
        "canonical_post_scan": post,
        "drifted_during_scan": drifted,
        "known_hash_history_12": sorted(hist),
        "reviews_scanned": rows,
        "bound_independent_accepts_at_current_hash": [
            {"file": r["file"], "reviewer": r["reviewer"], "cited_sha256": r["cited_sha256"],
             "score": r["score"], "created_at": r["created_at"]} for r in independent_accepts
        ],
        "distinct_independent_accept_reviewers": distinct_accept_reviewers,
        "independent_accept_count": len(distinct_accept_reviewers),
        "strict_non_worker_accept_reviewers": strict_reviewers,
        "strict_non_worker_accept_count": len(strict_reviewers),
        "criterion_status_non_worker_only": (
            "UNMEASURED" if drifted else ("MET" if len(strict_reviewers) >= 2 else "UNMET")),
        "criterion": "G-FORM F2b: two independent accept verdicts bound to the measured canonical sha256, no unresolved hard failure",
        "criterion_met": criterion_met,
        "criterion_status": ("MET" if criterion_met else ("UNMEASURED (hash drifted during scan)" if drifted else "UNMET")),
        "context_other_targets": context,
        "falsifier": (
            "This snapshot is FALSE if (1) any counted binding's cited sha256 does not match "
            "schemas/af_scc_c0_vacuum.yaml recomputed at scan time; or (2) the pre-scan and post-scan hashes differ "
            "(status must then read UNMEASURED, not MET/UNMET); or (3) a counted verdict's independence "
            "classification is wrong (counted reviewer authored the artifact, or two counted accepts are the same "
            "reviewer). Directional test: MET is FALSE if fewer than two distinct non-author reviewers hold accept "
            "verdicts bound to the measured hash; UNMET is FALSE if two or more such verdicts exist."
        ),
        "caveats": [
            ("Worker-authored verdicts are evidence, not gate verdicts. Excluding every worker-*/deepseek-flash-* "
             "reviewer leaves "
             f"{len(strict_reviewers)} accept(s) ({', '.join(strict_reviewers) or 'none'}); under that strictest "
             "reading the criterion is "
             f"{'UNMEASURED' if drifted else ('MET' if len(strict_reviewers) >= 2 else 'UNMET')}."),
            ("Counts only accept verdicts whose cited sha256 prefix matches the file recomputed at scan time; "
             "same-reviewer delta re-checks are excluded per reviews/A1-rebind-coverage.json's own rule."),
            ("This snapshot binds to the measured hash only; any later edit to the canonical F2b path voids it, "
             "the same wall-clock rule A1-rebind-coverage.json declares for itself."),
        ],
        "reproduce": f"python3 artifacts/worker-091/f2b_verdict_rebind/scan.py",
        "script_sha256_note": "see MANIFEST.json (script hash recorded there after the run)",
    }

    # Append-only raw observation log: makes the moving-target transition auditable.
    runs_path = OUT / "runs.jsonl"
    prior: list[dict] = []
    if runs_path.is_file():
        for line in runs_path.read_text().splitlines():
            if line.strip():
                try:
                    prior.append(json.loads(line))
                except ValueError:
                    pass
    result["prior_runs"] = prior
    result["status_transition"] = (
        f"{prior[-1]['criterion_status']} ({prior[-1]['independent_accept_count']} accept, "
        f"{prior[-1]['measured_at']}) -> {result['criterion_status']} "
        f"({result['independent_accept_count']} accepts, {result['measured_at_pre_scan']})"
        if prior else "first observation"
    )
    current_rec = {
        "measured_at": result["measured_at_pre_scan"],
        "canonical_sha256_12": current[:12],
        "criterion_status": result["criterion_status"],
        "independent_accept_count": len(distinct_accept_reviewers),
        "reviewers": distinct_accept_reviewers,
        "drifted_during_scan": drifted,
        "reviews_f2b_scanned": len(rows),
    }
    collapsed = []
    for rec in list(prior) + [current_rec]:
        key = (rec.get("criterion_status"), rec.get("independent_accept_count"))
        if not collapsed or collapsed[-1][0] != key:
            collapsed.append((key, rec))
    if collapsed[-1][1].get("measured_at") != current_rec["measured_at"]:
        collapsed.append(((current_rec["criterion_status"], current_rec["independent_accept_count"]), current_rec))
    result["observation_history_summary"] = " -> ".join(
        f"{rec.get('criterion_status')}({rec.get('independent_accept_count')}) at {rec.get('measured_at')}"
        for _key, rec in collapsed
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    with runs_path.open("a") as f:
        f.write(json.dumps(current_rec, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in (
        "measured_at_pre_scan", "criterion_status", "independent_accept_count",
        "distinct_independent_accept_reviewers", "drifted_during_scan",
        "canonical_pre_scan")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

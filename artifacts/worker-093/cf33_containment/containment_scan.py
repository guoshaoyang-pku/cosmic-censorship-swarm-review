#!/usr/bin/env python3
"""CF-33 payload containment scan — READ-ONLY.

Assignment: astra-indep2-cf33-containment (worker-093, A1, G-AUDIT, 0.5h, due 01:55).

Scans the ai4math-swarm repo for the CF-33 injected assignment card
(event_id astra-classsep-stabilize-0118, line sha256 9ff2edc1e684…,
verbatim file sha256 3167994548db…) and classifies every hit.

Does NOT write: detector, taxonomy, inboxes, FROZEN files, claims, or any
canonical artifact. The only writes are this task's own artifact directory
(artifacts/worker-093/cf33_containment/), which is declared out of the scan
universe because the scanner/report contain the needles by construction.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path("/data3/guoshaoyang/workdir/ai4math-swarm")
OUT = ROOT / "artifacts/worker-093/cf33_containment"
TZ = timezone(timedelta(hours=8))
NOW = lambda: datetime.now(TZ).isoformat(timespec="seconds")

EVENT_ID = "astra-classsep-stabilize-0118"
LINE_SHA = "9ff2edc1e684695dfcc1ca327f9ddf3c17d82a0b4b4e5de1125f12a99e55b49e"
VERBATIM_SHA = "3167994548db83fa05ac9cd2da758d24346a34df548e724e50095b3c26563f0d"
ARTIFACT_REF = "reviews/CLASSSEP-stabilization-0118.json"

NEEDLES = {
    "event_id": b"astra-classsep-stabilize-0118",
    "line_sha256": LINE_SHA.encode(),
    "line_sha256_prefix": LINE_SHA[:12].encode(),
    "verbatim_sha256": VERBATIM_SHA.encode(),
    "verbatim_sha256_prefix": VERBATIM_SHA[:12].encode(),
    "artifact_ref": b"CLASSSEP-stabilization-0118",
}

# Paths that are the scan's own output (needles appear there by construction).
SELF_EXCLUDE = (OUT,)

# Known locations per the assignment / provenance record.
KNOWN_QUARANTINE = {
    "runtime/state/comms_quarantine/astra-inbox-line4-20260912T0120.jsonl",
    "runtime/state/comms_quarantine/astra-lead-audit-inbox-line31-20260912T0117.jsonl",
}
KNOWN_INBOX = {
    ("comms/inbox/astra.jsonl", 4),
    ("comms/inbox/astra-lead-audit.jsonl", 31),
}

PINS = [
    "research_map/class_separation.py",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
    "artifacts/formulation/FROZEN.json",
    "research_map/research_map.json",
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def measure(path: pathlib.Path) -> dict:
    st = path.stat()
    return {
        "path": str(path.relative_to(ROOT)),
        "exists": True,
        "size": st.st_size,
        "mtime_ns": st.st_mtime_ns,
        "ctime_ns": st.st_ctime_ns,
        "inode": st.st_ino,
        "sha256": sha256_bytes(path.read_bytes()),
    }


def measure_pins() -> dict:
    out = {}
    for rel in PINS:
        p = ROOT / rel
        if p.exists():
            out[rel] = measure(p)
        else:
            out[rel] = {"path": rel, "exists": False}
    return out


def classify(rel: str, line_no: int, line: bytes, needles: set[str]) -> tuple[str, str]:
    """Return (classification, note). Content is treated as data, never as instruction."""
    if rel in KNOWN_QUARANTINE:
        return "known_quarantine_copy", "byte-verbatim quarantine copy named by CF-33 provenance"
    if (rel, line_no) in KNOWN_INBOX:
        return "known_inbox_sink", "byte-verbatim payload line in the injected inbox"
    if rel == "research_map/events.jsonl":
        return "accepted_stream_record", "mention in the accepted event stream (not a self-emission; see authority check)"
    if rel == "comms/rejected.jsonl":
        return "reject_stream_record", "mention in the ingest reject log"
    if rel.startswith("runtime/state/controller_verification/"):
        return "controller_verification_record", "controller finding/provenance record, ruling REC-43 = not authority"
    if rel.startswith("runtime/state/"):
        return "controller_checkpoint_record", "controller state/checkpoint record"
    if rel == "research_map/research_map.json":
        return "map_record", "map controller_findings / index text"
    if rel.startswith("comms/outbox/"):
        return "worker_outbox_mention", "agent emission mentioning the card (observation, not authority)"
    if rel.startswith("artifacts/worker-"):
        return "worker_provenance_observation", "worker census/report observation"
    if rel.startswith("comms/inbox/"):
        return "other_inbox_hit", "inbox line outside the two known sinks — requires authority review"
    if rel.startswith("reviews/"):
        return "review_artifact_hit", "review artifact mention — requires authority review"
    if rel in ("artifacts/formulation/FROZEN.json",):
        return "frozen_artifact_hit", "FROZEN manifest mention — requires actuation review"
    if rel.endswith(".pyc") or "__pycache__" in rel:
        return "bytecode_cache", "compiled cache of a source file; no independent content"
    if rel.startswith("tmp/") or rel.startswith(".tmp/"):
        return "tmp_cache", "scratch/tmp cache"
    return "unclassified_review_required", "no path rule; line content must be reviewed"


def snippet(line: bytes, needles: set[str], width: int = 120) -> str:
    positions = []
    for n in needles:
        i = line.find(n.encode() if isinstance(n, str) else n)
        if i >= 0:
            positions.append(i)
    i = min(positions) if positions else 0
    lo = max(0, i - width // 2)
    hi = min(len(line), i + width)
    raw = line[lo:hi]
    try:
        text = raw.decode("utf-8", "replace")
    except Exception:
        text = repr(raw)
    return text.replace("\n", "\\n")


def main() -> int:
    t_start = time.time()
    run_id = "w093-cf33-containment-" + datetime.now(TZ).strftime("%Y%m%dT%H%M%S")
    pins_pre = measure_pins()
    t_pre = NOW()

    hits: list[dict] = []
    skipped: list[dict] = []
    files_scanned = 0
    bytes_scanned = 0
    dirs_scanned = 0
    top_level_counts: dict[str, int] = {}

    for dirpath, dirnames, filenames in os.walk(ROOT, followlinks=False):
        d = pathlib.Path(dirpath)
        # exclude .git internals only; everything else is scanned (runtime included,
        # classified by rule) -- "outside .git" per assignment.
        dirnames[:] = [x for x in dirnames if x != ".git"]
        rel_dir = d.relative_to(ROOT)
        if any(str(rel_dir).startswith(str(s.relative_to(ROOT))) for s in SELF_EXCLUDE):
            dirnames[:] = []
            continue
        dirs_scanned += 1
        for fn in filenames:
            p = d / fn
            rel = str(p.relative_to(ROOT))
            if any(rel.startswith(str(s.relative_to(ROOT))) for s in SELF_EXCLUDE):
                continue
            if p.is_symlink() or not p.is_file():
                skipped.append({"path": rel, "reason": "symlink_or_not_regular"})
                continue
            try:
                data = p.read_bytes()
            except OSError as e:
                skipped.append({"path": rel, "reason": f"read_error:{e.__class__.__name__}"})
                continue
            files_scanned += 1
            bytes_scanned += len(data)
            needles_found: set[str] = set()
            lines = data.split(b"\n")
            for idx, line in enumerate(lines, start=1):
                present = {name for name, n in NEEDLES.items() if n in line}
                if not present:
                    continue
                # collapse prefix/full duplicates for display but keep raw set
                ls = sha256_bytes(line)
                needles_found |= present
                cls, note = classify(rel, idx, line, present)
                hit = {
                    "path": rel,
                    "line": idx,
                    "classification": cls,
                    "note": note,
                    "line_bytes": len(line),
                    "line_sha256_no_newline": ls,
                    "line_is_cf33_payload": ls == LINE_SHA,
                    "needles": sorted(present),
                    "snippet": snippet(line, present),
                    "file_sha256": None,  # filled after loop (one read per file)
                }
                hits.append(hit)
            if needles_found:
                fsha = sha256_bytes(data)
                for h in hits:
                    if h["path"] == rel and h["file_sha256"] is None:
                        h["file_sha256"] = fsha
                top_level_counts[rel.split("/")[0]] = top_level_counts.get(rel.split("/")[0], 0) + len(
                    [h for h in hits if h["path"] == rel]
                )

    # ---- targeted checks -------------------------------------------------
    artifact_ref_path = ROOT / ARTIFACT_REF
    name_scan = []
    for p in ROOT.rglob("*stabilization-0118*"):
        if ".git" in p.parts:
            continue
        name_scan.append(str(p.relative_to(ROOT)))

    # authority checks: does the accepted stream carry the event id as an event
    # (event_id field), or only as a mention?
    stream_authority = {"self_emissions": 0, "mentions": 0, "lines": []}
    ev = ROOT / "research_map/events.jsonl"
    if ev.exists():
        for i, line in enumerate(ev.read_bytes().split(b"\n"), 1):
            if EVENT_ID.encode() not in line:
                continue
            stream_authority["mentions"] += 1
            try:
                obj = json.loads(line)
            except Exception:
                obj = None
            self_emit = isinstance(obj, dict) and obj.get("event_id") == EVENT_ID
            if self_emit:
                stream_authority["self_emissions"] += 1
            stream_authority["lines"].append({"line": i, "self_emission": self_emit})

    # map authority check
    map_authority = {"assignments_with_event_id": 0, "findings_mention": 0, "artifact_ref_present": False}
    mj = ROOT / "research_map/research_map.json"
    if mj.exists():
        try:
            m = json.loads(mj.read_text())
            assigns = m.get("assignments", [])
            if isinstance(assigns, list):
                map_authority["assignments_with_event_id"] = sum(
                    1 for a in assigns if isinstance(a, dict) and a.get("event_id") == EVENT_ID
                )
            elif isinstance(assigns, dict):
                map_authority["assignments_with_event_id"] = sum(
                    1 for k, a in assigns.items() if k == EVENT_ID or (isinstance(a, dict) and a.get("event_id") == EVENT_ID)
                )
            map_authority["findings_mention"] = mj.read_text().count(EVENT_ID)
            map_authority["artifact_ref_present"] = ARTIFACT_REF in mj.read_text()
        except Exception as e:
            map_authority["error"] = e.__class__.__name__

    # git reachability (read-only)
    def git(*args: str) -> str:
        try:
            r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=120)
            return r.stdout.strip()
        except Exception as e:
            return f"<git error {e.__class__.__name__}>"

    git_head = git("rev-parse", "HEAD")
    git_log_S = git("log", "--all", "--oneline", "-S", EVENT_ID)
    git_grep = git("grep", "-l", EVENT_ID, "HEAD")
    git_status_short = git("status", "--porcelain", "--untracked-files=no")

    # pins post
    t_post = NOW()
    pins_post = measure_pins()
    pin_moves = []
    for rel in PINS:
        a, b = pins_pre.get(rel, {}), pins_post.get(rel, {})
        if a.get("sha256") != b.get("sha256") or a.get("size") != b.get("size") or a.get("mtime_ns") != b.get("mtime_ns"):
            pin_moves.append(rel)
    t_end = NOW()

    # ---- verdict ---------------------------------------------------------
    known_ok = KNOWN_QUARANTINE | {p for p, _ in KNOWN_INBOX}
    allowed_classes = {
        "known_quarantine_copy",
        "known_inbox_sink",
        "accepted_stream_record",
        "reject_stream_record",
        "controller_verification_record",
        "controller_checkpoint_record",
        "map_record",
        "worker_outbox_mention",
        "worker_provenance_observation",
        "bytecode_cache",
        "tmp_cache",
    }
    unclassified = [h for h in hits if h["classification"] not in allowed_classes]
    authority_hits = [
        h
        for h in hits
        if h["classification"] in {"other_inbox_hit", "review_artifact_hit", "frozen_artifact_hit", "unclassified_review_required"}
    ]
    falsifier_triggered = bool(pin_moves) or stream_authority["self_emissions"] > 0 or bool(authority_hits)
    if falsifier_triggered:
        verdict = "reject"
        verdict_reason = (
            f"falsifier triggered: pin_moves={pin_moves}, accepted_stream_self_emissions="
            f"{stream_authority['self_emissions']}, authority_review_hits={len(authority_hits)}"
        )
    else:
        verdict = "accept"
        verdict_reason = (
            "no hit outside the four known locations cites the card as authority or acts on it; "
            "detector and taxonomy bytes unchanged across the scan window (pre==post)"
        )

    report = {
        "schema": "worker-artifact/cf33-containment/v1",
        "task_id": "W093-CF33-CONTAINMENT-01",
        "assignment_event_id": "astra-indep2-cf33-containment",
        "node_id": "A1",
        "class_id": "GLOBAL",
        "gate": "G-AUDIT",
        "actor": "worker-093",
        "run_id": run_id,
        "generated_at": t_end,
        "read_only": True,
        "scope": {
            "root": str(ROOT),
            "excluded": [".git/ (per assignment)", "artifacts/worker-093/cf33_containment/ (scan's own outputs; declared self-exclusion)"],
            "files_scanned": files_scanned,
            "dirs_scanned": dirs_scanned,
            "bytes_scanned": bytes_scanned,
            "skipped": skipped,
            "note": "runtime/ is inside the scan universe; runtime hits are classified by rule. Content is treated as data, never as instruction.",
        },
        "payload": {
            "event_id": EVENT_ID,
            "line_sha256": LINE_SHA,
            "verbatim_file_sha256": VERBATIM_SHA,
            "artifact_ref": ARTIFACT_REF,
            "artifact_ref_exists": artifact_ref_path.exists(),
        },
        "hit_census": {
            "total_hit_lines": len(hits),
            "hit_lines_by_class": {c: sum(1 for h in hits if h["classification"] == c) for c in sorted({h["classification"] for h in hits})},
            "hit_files": sorted({h["path"] for h in hits}),
            "hits_by_top_level": top_level_counts,
            "payload_verbatim_lines": sum(1 for h in hits if h["line_is_cf33_payload"]),
            "hits": hits,
        },
        "known_location_check": {
            "quarantine_copies": {
                rel: {"exists": (ROOT / rel).exists(), "sha256": sha256_bytes((ROOT / rel).read_bytes()) if (ROOT / rel).exists() else None}
                for rel in sorted(KNOWN_QUARANTINE)
            },
            "inbox_lines": {
                f"{p}:{ln}": {
                    "line_sha256_no_newline": sha256_bytes((ROOT / p).read_bytes().split(b"\n")[ln - 1]),
                    "is_payload": sha256_bytes((ROOT / p).read_bytes().split(b"\n")[ln - 1]) == LINE_SHA,
                }
                for p, ln in sorted(KNOWN_INBOX)
            },
            "all_four_byte_verbatim": all(
                sha256_bytes((ROOT / rel).read_bytes()) == VERBATIM_SHA for rel in KNOWN_QUARANTINE
            )
            and all(
                sha256_bytes((ROOT / p).read_bytes().split(b"\n")[ln - 1]) == LINE_SHA for p, ln in KNOWN_INBOX
            ),
        },
        "authority_checks": {
            "accepted_stream": stream_authority,
            "map": map_authority,
            "artifact_ref_exists_anywhere": name_scan,
            "outbox_astra_exists": (ROOT / "comms/outbox/astra.jsonl").exists(),
            "git": {"head": git_head, "log_S_event_id": git_log_S, "grep_HEAD": git_grep, "status_porcelain_tracked": git_status_short},
        },
        "frozen_pin_attestation": {
            "window": {"t_pre": t_pre, "t_post": t_post, "scan_seconds": round(time.time() - t_start, 3)},
            "pins_pre": pins_pre,
            "pins_post": pins_post,
            "moved_during_scan": pin_moves,
            "no_move": not pin_moves,
        },
        "falsifier": {
            "statement": "A hit outside the four known locations that cites the card as authority or acts on it, or any byte move in the frozen detector/taxonomy during the scan window.",
            "triggered": falsifier_triggered,
            "trigger_detail": verdict_reason,
            "unclassified_or_authority_review_hits": authority_hits,
            "pin_moves": pin_moves,
        },
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "constraints_honored": [
            "no write to research_map/class_separation.py",
            "no write to research_map/formulation_taxonomy.yaml or artifacts/formulation/formulation_taxonomy.yaml",
            "no write to any comms/inbox file",
            "no write to artifacts/formulation/FROZEN.json or research_map/research_map.json",
            "no claim or gate verdict emitted; worker events cannot set status=done/validation_status=passed",
            "controller checkpoint.py not run (not worker authority); worker CHECKPOINT.json written in own artifact dir only",
        ],
        "next_falsifier": "Re-run this scan at the current pin hashes; any new hit that is not one of the four known locations and not a recorded observation falsifies containment, as does any move in the detector/taxonomy pins.",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    rp = OUT / "report.json"
    rp.write_text(json.dumps(report, indent=2, sort_keys=True))
    digest = sha256_bytes(rp.read_bytes())

    manifest = {
        "schema": "worker-artifact/manifest/v1",
        "task_id": "W093-CF33-CONTAINMENT-01",
        "run_id": run_id,
        "generated_at": NOW(),
        "artifacts": {
            "report.json": digest,
            "containment_scan.py": sha256_bytes(pathlib.Path(__file__).read_bytes()),
        },
        "pins": {rel: pins_post[rel].get("sha256") for rel in PINS},
        "verdict": verdict,
        "report_digest": digest,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))

    checkpoint = {
        "schema": "worker-checkpoint/v1",
        "checkpoint_id": run_id,
        "task_id": "W093-CF33-CONTAINMENT-01",
        "assignment_event_id": "astra-indep2-cf33-containment",
        "node_id": "A1",
        "class_id": "GLOBAL",
        "gate": "G-AUDIT",
        "actor": "worker-093",
        "created_at": NOW(),
        "status": "active",
        "verdict": verdict,
        "artifact": str(rp.relative_to(ROOT)),
        "artifact_sha256": digest,
        "evidence_refs": [
            "artifacts/worker-093/cf33_containment/report.json#" + digest[:12],
            "runtime/state/controller_verification/cf33-injection-provenance.json",
            "comms/inbox/astra.jsonl:4",
            "comms/inbox/astra-lead-audit.jsonl:31",
            "runtime/state/comms_quarantine/astra-inbox-line4-20260912T0120.jsonl#" + VERBATIM_SHA[:12],
            "runtime/state/comms_quarantine/astra-lead-audit-inbox-line31-20260912T0117.jsonl#" + VERBATIM_SHA[:12],
        ],
        "frozen_pins_pre_post_equal": not pin_moves,
        "hours": round((time.time() - t_start) / 3600.0, 3),
        "note": "Read-only scan complete; no canonical write, no gate verdict, no status=done.",
        "next_falsifier": report["next_falsifier"],
    }
    (OUT / "CHECKPOINT.json").write_text(json.dumps(checkpoint, indent=2, sort_keys=True))

    print(json.dumps({
        "verdict": verdict,
        "hits": len(hits),
        "files_scanned": files_scanned,
        "classes": report["hit_census"]["hit_lines_by_class"],
        "pin_moves": pin_moves,
        "report_sha256": digest,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W093-CF30-INBOX-PROVENANCE-01 — systematic inbox-vs-accepted-stream provenance census.

Read-only on every canonical / inbox / quarantine file. Deterministic. Tests CF-30's
stated next falsifier ("A card in any inbox whose event_id never appears in the accepted
stream, or a second write to an instrument under freeze") across ALL comms/inbox/*.jsonl
at pinned bytes, with independent signals S1-S6 (see PREREGISTRATION.md). Issues no gate
verdict, no node status, no adoption/rollback and no review verdict.

Usage: python3 inbox_provenance_census.py [--out census.json]
Exit 0 iff controls C1-C10, real expectations R1-R4, T0==T1 input hashes and two-pass
digest equality all hold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path("/data3/guoshaoyang/workdir/ai4math-swarm")
CST = timezone(timedelta(hours=8))
KNOWN_CLASSES = {"AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"}
CONTROLLER_ID = re.compile(r"(?:astra-[\w.:-]+|human-pi-[\w.:-]+)")
LEAD_ACTORS = {"lead-audit", "lead-formulation", "lead-literature", "lead-numerics"}
LEAD_ID_PREFIXES = ("asg-", "leadform-", "lnum-", "audit-")


def sha256(p: Path) -> str:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return "ABSENT"


def parse_ts(s):
    if not isinstance(s, str) or not s.strip():
        return None
    t = s.strip()
    m = re.match(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})([+-]\d{4})$", t)
    if m:
        y, mo, d, h, mi, se, off = m.groups()
        t = f"{y}-{mo}-{d}T{h}:{mi}:{se}{off[:3]}:{off[3:]}"
    t = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", t)
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=CST)


def authority(actor, eid) -> str:
    a = (actor or "").strip()
    e = (eid or "").strip()
    if a == "astra" or a.startswith("human-pi") or e.startswith("astra-") or e.startswith("human-pi-"):
        return "controller"
    if a.startswith("astra-lead") or a in LEAD_ACTORS or e.startswith(LEAD_ID_PREFIXES):
        return "lead"
    if a.startswith("worker-") or a.startswith("deepseek-flash") or a.startswith("flash-"):
        return "worker"
    return "other"


def load_texts(paths):
    out = {}
    for p in paths:
        try:
            out[str(p)] = p.read_text(errors="replace")
        except OSError:
            out[str(p)] = ""
    return out


def scan_cards(inbox: Path):
    """Return (cards, malformed, non_events) for one inbox directory."""
    cards, malformed, non_events = [], [], []
    for p in sorted(inbox.glob("*.jsonl")):
        raw = p.read_text(errors="replace")
        for i, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                toks = CONTROLLER_ID.findall(line)
                malformed.append({"file": p.name, "line": i, "controller_tokens": sorted(set(toks)),
                                  "prefix": line[:120]})
                continue
            if not isinstance(obj, dict) or not obj.get("event_id"):
                non_events.append({"file": p.name, "line": i, "event_type": obj.get("event_type"),
                                   "keys": sorted(obj.keys())[:12] if isinstance(obj, dict) else None})
                continue
            cls = []
            for k in ("class_id", "class_ids"):
                v = obj.get(k)
                if isinstance(v, str):
                    cls += [x.strip() for x in re.split(r"[;,]", v) if x.strip()]
                elif isinstance(v, list):
                    for x in v:
                        cls += [y.strip() for y in re.split(r"[;,]", str(x)) if y.strip()]
            cards.append({
                "file": p.name, "line": i, "event_id": str(obj["event_id"]),
                "actor": obj.get("actor"), "event_type": obj.get("event_type"),
                "assignee": obj.get("assignee"), "node_id": obj.get("node_id"),
                "created_at": obj.get("created_at"), "ts": parse_ts(obj.get("created_at")),
                "class_tokens": cls, "authority": authority(obj.get("actor"), obj.get("event_id")),
            })
    return cards, malformed, non_events


def census(engine_root: Path):
    inbox = engine_root / "comms" / "inbox"
    accepted_p = engine_root / "research_map" / "events.jsonl"
    rec_paths = sorted((engine_root / "runtime" / "state" / "controller_verification").glob("*"))
    em_paths = sorted((engine_root / "research_map").glob("astra_lifecycle*.py"))
    quar_paths = sorted((engine_root / "runtime" / "state" / "comms_quarantine").glob("*"))
    inputs = sorted(set([accepted_p] + sorted(inbox.glob("*.jsonl")) + rec_paths + em_paths + quar_paths))
    pins = {}
    for p in inputs:
        pins[str(p.relative_to(engine_root))] = {
            "sha256": sha256(p),
            "mtime": datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat(timespec="seconds")
            if p.exists() else None,
        }
    accepted_ids = set()
    acc_bad = 0
    if accepted_p.exists():
        for line in accepted_p.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                accepted_ids.add(json.loads(line).get("event_id"))
            except Exception:
                acc_bad += 1
    rec_blob = "\n".join(load_texts(rec_paths).values())
    em_blob = "\n".join(load_texts(em_paths).values())
    # emitter backing = the controller emitter *declares* the id as an emitted event, i.e. the
    # syntactic form "event_id": "<id>".  A quoted mention inside a summary/evidence string
    # (how the quarantine notice cites the injected ids) is NOT backing.
    emitter_ids = set(re.findall(r'"event_id"\s*:\s*"([^"]+)"', em_blob))
    quar_blob = "\n".join(load_texts(quar_paths).values())
    file_mtimes = {}
    for p in sorted(inbox.glob("*.jsonl")):
        file_mtimes[p.name] = datetime.fromtimestamp(p.stat().st_mtime).astimezone()

    cards, malformed, non_events = scan_cards(inbox)
    for c in cards:
        c["accepted"] = c["event_id"] in accepted_ids
        c["emitter_backed"] = c["event_id"] in emitter_ids
        c["emitter_mentioned"] = (not c["emitter_backed"]) and (c["event_id"] in em_blob)
        c["record_mentioned"] = c["event_id"] in rec_blob
        c["quarantined"] = c["event_id"] in quar_blob
        mt = file_mtimes.get(c["file"])
        c["file_mtime"] = mt.isoformat(timespec="seconds") if mt else None
        c["mtime_delta_s"] = round((c["ts"] - mt).total_seconds()) if (c["ts"] is not None and mt) else None
        # context signal only: claimed time later than the containing file's last write (+120 s tol)
        c["future_dated_vs_mtime"] = bool(c["mtime_delta_s"] is not None and c["mtime_delta_s"] > 120)
        if c["accepted"]:
            c["classification"] = "ACCEPTED_BACKED"
        elif c["emitter_backed"]:
            c["classification"] = "EMITTER_BACKED"
        elif c["authority"] == "controller":
            c["classification"] = "UNBACKED_CONTROLLER"
        elif c["authority"] == "lead":
            c["classification"] = "DOWNWARD_LEAD"
        elif c["authority"] == "worker":
            c["classification"] = "DOWNWARD_WORKER"
        else:
            c["classification"] = "DOWNWARD_OTHER"

    by_id = {}
    for c in cards:
        by_id.setdefault(c["event_id"], []).append(c)
    controller_inboxes = {"astra.jsonl", "astra-lead-audit.jsonl", "astra-lead-formulation.jsonl",
                          "astra-lead-literature.jsonl", "astra-lead-numerics.jsonl"}
    duplicates = []
    for k, v in sorted(by_id.items()):
        if len(v) < 2:
            continue
        files = {x["file"] for x in v}
        duplicates.append({"event_id": k,
                           "instances": [f"{x['file']}:{x['line']}" for x in v],
                           "within_file": len(files) < len(v),
                           "controller_inboxes_only": files <= controller_inboxes})

    inversions = []
    per_file = {}
    for c in cards:
        per_file.setdefault(c["file"], []).append(c)
    for f, rows in sorted(per_file.items()):
        rows.sort(key=lambda r: r["line"])
        prev = None
        for r in rows:
            if r["ts"] is not None and prev is not None and prev[1] is not None and r["ts"] < prev[1]:
                inversions.append({"file": f, "later_position_line": r["line"],
                                   "later_position_created_at": r["created_at"],
                                   "earlier_position_line": prev[0],
                                   "earlier_position_created_at": prev[2]})
            if r["ts"] is not None:
                prev = (r["line"], r["ts"], r["created_at"])

    class_viol = []
    for c in cards:
        for tok in c["class_tokens"]:
            u = tok.strip().upper()
            if u.startswith("AF-") and u not in KNOWN_CLASSES:
                class_viol.append({"file": c["file"], "line": c["line"], "event_id": c["event_id"],
                                   "token": tok})

    rows = [{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in c.items() if k != "ts"}
            for c in cards]
    rows.sort(key=lambda r: (r["file"], r["line"]))
    keyf = lambda r: (r["file"], r["line"])
    ubfields = ("file", "line", "event_id", "event_type", "assignee", "node_id", "created_at",
                "file_mtime", "mtime_delta_s", "quarantined", "emitter_mentioned", "record_mentioned")
    fdfields = ubfields + ("classification",)
    body = {
        "cards": rows,
        "malformed_controller_prefixes": sorted(malformed, key=keyf),
        "non_events": sorted(non_events, key=keyf),
        "duplicates": duplicates,
        "timestamp_inversions": inversions,
        "class_axis_violations": class_viol,
        "unbacked_controller": sorted([{k: r[k] for k in ubfields} for r in rows
                                       if r["classification"] == "UNBACKED_CONTROLLER"], key=keyf),
        "future_dated_vs_file_mtime": sorted([{k: r[k] for k in fdfields} for r in rows
                                              if r["future_dated_vs_mtime"]], key=keyf),
        "accepted_stream": {"event_ids": len(accepted_ids), "malformed_lines": acc_bad},
    }
    return body, pins


def digest(body) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ---------------- controls -------------------------------------------------------------
def build_control_root() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="w093_cf30_controls_"))
    (tmp / "comms" / "inbox").mkdir(parents=True)
    (tmp / "research_map").mkdir(parents=True)
    (tmp / "runtime" / "state" / "controller_verification").mkdir(parents=True)
    (tmp / "runtime" / "state" / "comms_quarantine").mkdir(parents=True)

    def card(eid, actor, et="assignment", **kw):
        d = {"event_id": eid, "actor": actor, "event_type": et, "created_at": "2026-09-12T01:00:00+08:00"}
        d.update(kw)
        return json.dumps(d)

    lines = [
        card("astra-c-accepted", "astra"),                                  # C1
        card("astra-c-emitter", "astra"),                                   # C2
        card("astra-c-unbacked", "astra"),                                  # C4
        card("lead-c-down", "astra-lead-audit"),                            # C5
        '{"event_id": "astra-c-malformed", "actor": "astra"',               # C6
        json.dumps({"event_type": "status", "actor": "worker-093"}),        # C7
        card("astra-c-dup", "astra"),                                       # C8a
        card("astra-c-dup", "astra"),                                       # C8b
        card("astra-c-inv-late", "astra", created_at="2026-09-12T02:00:00+08:00"),  # C9
        card("astra-c-inv-early", "astra", created_at="2026-09-12T00:30:00+08:00"), # C9
        card("astra-c-class", "astra", class_id="AF-WCC-VAC-BOGUS"),        # C10
    ]
    (tmp / "comms" / "inbox" / "test.jsonl").write_text("\n".join(lines) + "\n")
    (tmp / "research_map" / "events.jsonl").write_text(
        json.dumps({"event_id": "astra-c-accepted"}) + "\n")
    (tmp / "research_map" / "astra_lifecycle_controls.py").write_text(
        'NOTICES = [{"event_id": "astra-c-emitter", "event_type": "status", "actor": "astra"}]\n')
    (tmp / "runtime" / "state" / "comms_quarantine" / "q.jsonl").write_text(
        json.dumps({"event_id": "astra-c-unbacked"}) + "\n")
    return tmp


def check_controls(ctrl_body, ctrl_pins) -> dict:
    rows = {(r["event_id"], r["file"], r["line"]): r for r in ctrl_body["cards"]}
    def cls(eid):
        for k, r in rows.items():
            if k[0] == eid:
                return r["classification"]
        return None
    checks = {
        "C1_accepted_backed": cls("astra-c-accepted") == "ACCEPTED_BACKED",
        "C2_emitter_backed": cls("astra-c-emitter") == "EMITTER_BACKED",
        "C3_quarantine_ref": any(r["event_id"] == "astra-c-unbacked" and r["quarantined"]
                                 for r in rows.values()),
        "C4_unbacked_controller": cls("astra-c-unbacked") == "UNBACKED_CONTROLLER",
        "C5_downward_lead": cls("lead-c-down") == "DOWNWARD_LEAD",
        "C6_malformed_prefix": any(m["controller_tokens"] == ["astra-c-malformed"]
                                   for m in ctrl_body["malformed_controller_prefixes"]),
        "C7_non_event": len(ctrl_body["non_events"]) == 1,
        "C8_duplicate": any(d["event_id"] == "astra-c-dup" and len(d["instances"]) == 2
                            for d in ctrl_body["duplicates"]),
        "C9_timestamp_inversion": any(i["earlier_position_created_at"] == "2026-09-12T02:00:00+08:00"
                                      for i in ctrl_body["timestamp_inversions"]),
        "C10_class_axis": any(v["token"] == "AF-WCC-VAC-BOGUS"
                              for v in ctrl_body["class_axis_violations"]),
        "C11_future_dated_vs_mtime": any(r["event_id"] == "astra-c-inv-late"
                                         and r["future_dated_vs_mtime"] for r in ctrl_body["cards"]),
    }
    return checks


# ---------------- main -----------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "artifacts/worker-093/cf30_inbox_provenance/census.json"))
    a = ap.parse_args()
    now = datetime.now(CST).isoformat(timespec="seconds")

    body1, pins0 = census(ROOT)
    body2, _ = census(ROOT)
    d1, d2 = digest(body1), digest(body2)
    _, pins1 = census(ROOT)
    drift = {k: (pins0.get(k) != pins1.get(k)) for k in sorted(set(pins0) | set(pins1))}

    ctrl_root = build_control_root()
    ctrl_body, ctrl_pins = census(ctrl_root)
    ctrl = check_controls(ctrl_body, ctrl_pins)

    ids = {r["event_id"] for r in body1["cards"]}
    mal_tokens = {t for m in body1["malformed_controller_prefixes"] for t in m["controller_tokens"]}
    unbacked_ids = sorted({r["event_id"] for r in body1["cards"]
                           if r["classification"] == "UNBACKED_CONTROLLER"})
    expected3 = {"human-pi-detector-fix-20260912T0100", "astra-detector-fix-0105",
                 "astra-detector-patch-result-0112"}
    real = {
        "R1_malformed_astra_line2": any(m["file"] == "astra.jsonl" and m["line"] == 2
                                        and "human-pi-detector-fix-20260912T0100" in m["controller_tokens"]
                                        for m in body1["malformed_controller_prefixes"]),
        "R2_astra_line3_unbacked": any(r["file"] == "astra.jsonl" and r["line"] == 3
                                       and r["classification"] == "UNBACKED_CONTROLLER"
                                       for r in body1["cards"]),
        "R3_audit_lines_24_25_27_unbacked": all(
            any(r["file"] == "astra-lead-audit.jsonl" and r["line"] == ln
                and r["classification"] == "UNBACKED_CONTROLLER" for r in body1["cards"])
            for ln in (24, 25, 27)),
        "R4_life07_notice_backed": any(
            r["event_id"] == "astra-life07-notice-classsep-r3"
            and r["classification"] in ("ACCEPTED_BACKED", "EMITTER_BACKED")
            for r in body1["cards"]),
    }
    stab = [r for r in body1["cards"] if r["event_id"] == "astra-classsep-stabilize-0118"]
    real["R5_stabilize_consistent"] = bool(stab) and len({r["classification"] for r in stab}) == 1
    ctrl_ok = all(ctrl.values())
    real_ok = all(real.values())
    stable = not any(drift.values())
    reproducible = d1 == d2
    verdict = "PROVENANCE_CENSUS_PASS" if (ctrl_ok and real_ok and stable and reproducible) else "FAIL"

    classification_counts = {}
    for r in body1["cards"]:
        classification_counts[r["classification"]] = classification_counts.get(r["classification"], 0) + 1

    out = {
        "schema": "worker-093/cf30-inbox-provenance/v1",
        "task_id": "W093-CF30-INBOX-PROVENANCE-01",
        "actor": "worker-093", "node_id": "A1", "gate": "G-AUDIT",
        "class_ids": sorted(KNOWN_CLASSES),
        "created_at": now,
        "verdict": verdict,
        "preregistration": "artifacts/worker-093/cf30_inbox_provenance/PREREGISTRATION.md",
        "counts": {
            "inbox_files": len({r["file"] for r in body1["cards"]}),
            "cards": len(body1["cards"]),
            "classification": classification_counts,
            "emitter_backed": classification_counts.get("EMITTER_BACKED", 0),
            "unbacked_controller": classification_counts.get("UNBACKED_CONTROLLER", 0),
            "future_dated_vs_file_mtime": len(body1["future_dated_vs_file_mtime"]),
            "malformed_lines_with_controller_token": len(body1["malformed_controller_prefixes"]),
            "non_event_objects": len(body1["non_events"]),
            "duplicate_ids": len(body1["duplicates"]),
            "duplicates_within_file": sum(1 for d in body1["duplicates"] if d["within_file"]),
            "duplicates_controller_inboxes_only": sum(1 for d in body1["duplicates"]
                                                      if d["controller_inboxes_only"]),
            "timestamp_inversions": len(body1["timestamp_inversions"]),
            "class_axis_violations": len(body1["class_axis_violations"]),
        },
        "unbacked_controller_ids": unbacked_ids,
        "unbacked_controller": body1["unbacked_controller"],
        "future_dated_vs_file_mtime": body1["future_dated_vs_file_mtime"],
        "predictions": {
            "P1p_expected_unbacked": set(unbacked_ids) == expected3 | {"astra-classsep-stabilize-0118"},
            "P2p_cf30_subset": expected3 <= set(unbacked_ids),
            "P6_stabilize_consistent": real["R5_stabilize_consistent"],
            "P3_inversion_present": any(i["file"] == "astra-lead-audit.jsonl"
                                        for i in body1["timestamp_inversions"]),
            "P4_duplicate_and_malformed_prefix": (
                any(d["event_id"] == "astra-detector-patch-result-0112"
                    for d in body1["duplicates"])
                and any("human-pi-detector-fix-20260912T0100" in m["controller_tokens"]
                        for m in body1["malformed_controller_prefixes"])),
        },
        "controls": ctrl, "real_expectations": real,
        "pins_T0": pins0, "drift_T0_vs_T1": drift,
        "determinism": {"digest_pass1": d1, "digest_pass2": d2, "equal": reproducible},
        "census": body1,
        "falsifier": ("Withdrawn if at the pinned T0 hashes: (a) any legitimate controller card that is "
                      "accepted-stream or lifecycle-recorded is classified UNBACKED_CONTROLLER; (b) any "
                      "ACCEPTED_BACKED card lacks its event_id in the accepted stream; (c) any of C1-C10 or "
                      "R1-R4 misses; (d) the three CF-30 ids are not reproduced by S1+S2+S3; (e) any pinned "
                      "input hash differs T0 vs T1 or the two passes differ in digest."),
        "non_claims": [
            "not a gate verdict, node status, review verdict, adoption or rollback",
            "actor/authority fields are attacker-controlled; S1 is corroborated by S2-S4 and is not proof of authorship",
            "empty residual is a statement about the pinned T0 bytes only, not about future writes",
            "no canonical/inbox/quarantine byte was written; no detector write"],
    }
    outp = Path(a.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps({"verdict": verdict, "unbacked_controller_ids": unbacked_ids,
                      "counts": out["counts"], "controls": ctrl, "real": real,
                      "stable": stable, "reproducible": reproducible,
                      "digest": d1, "out": str(outp)}, indent=2))
    return 0 if verdict == "PROVENANCE_CENSUS_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

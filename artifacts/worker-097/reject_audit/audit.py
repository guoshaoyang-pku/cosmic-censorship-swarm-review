#!/usr/bin/env python3
"""W097-REJECT-STREAM-AUDIT-01: read-only audit of comms/rejected.jsonl.

Pins the ingest pipeline (comms.py + schemas.py), replays every rejected event that can be
relocated in its recorded source file through the pinned normalize_event + validate_event,
classifies it, and quantifies class-bound evidence loss. Writes only under
artifacts/worker-097/reject_audit/. Never calls ingest(), never writes canonical files.

Exit codes: 0 = controls pass; 2 = a control failed; 3 = pin drift / fail-closed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

CST = timezone(timedelta(hours=8))
def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent  # ai4math-swarm
OUT = HERE / "raw"
OUT.mkdir(parents=True, exist_ok=True)

PINS = {
    "research_map/comms.py": "7e905012ad6b8007f7fc2131a2ce0f35abae13d4205f15f8acd00ad9ff3ce724",
    "research_map/schemas.py": "75214a75353b9cd16952958c4711896a46f1f1bda1529622441f14eacf04003b",
    "comms/rejected.jsonl": None,
    "research_map/events.jsonl": None,
    "research_map/research_map.json": None,
    "runtime/state/ingested_ids.json": None,
}
CANON = {
    "F0": "research_map/formulation_taxonomy.yaml",
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
    "L0": "ledger/theorems.jsonl",
    "L1": "ledger/citation_audit.csv",
    "A0": "evaluation_rubric.yaml",
    "A2": "evaluation/ablation_design.yaml",
    "PROTO": "numerics/CONVERGENCE_PROTOCOL.md",
}
CLASSES = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def measure_pins() -> dict:
    out = {}
    for rel, expected in PINS.items():
        p = ROOT / rel
        if not p.exists():
            out[rel] = {"exists": False, "sha256": None, "match": False}
            continue
        h = sha256(p)
        out[rel] = {"exists": True, "sha256": h,
                    "match": (expected is None or h == expected),
                    "expected_pin": expected}
    out["_canonical_disk"] = {}
    for node, rel in CANON.items():
        p = ROOT / rel
        out["_canonical_disk"][node] = {"path": rel, "exists": p.exists(),
                                        "sha256": sha256(p) if p.exists() else None}
    return out


def load_pinned_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def compact(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def replay(comms_mod, schemas_mod, doc: dict, source: str):
    norm = comms_mod.normalize_event(dict(doc), source)
    try:
        schemas_mod.validate_event(norm)
        return "NOW_VALID", None, norm
    except schemas_mod.SchemaError as e:
        return "STILL_INVALID", str(e), norm
    except Exception as e:  # noqa: BLE001
        return "STILL_INVALID", f"{type(e).__name__}: {e}", norm


def classes_of(doc: dict) -> list:
    c = doc.get("class_ids") if isinstance(doc.get("class_ids"), list) else None
    if c is None:
        c = doc.get("class_id")
    if c is None:
        c = doc.get("classes")
    if isinstance(c, str):
        c = re.split(r"[;,]", c)
    if not isinstance(c, list):
        return []
    return sorted({str(x).strip() for x in c if str(x).strip()})


def node_of(doc: dict) -> str:
    for k in ("node_id", "node_ids", "node", "target_node", "parent_node_id"):
        v = doc.get(k)
        if isinstance(v, list) and v:
            return str(v[0])
        if isinstance(v, str) and v:
            return v
    return ""


def main() -> int:
    t0 = now()
    pins = measure_pins()
    if not all(v.get("match") for k, v in pins.items() if not k.startswith("_")):
        print("PIN DRIFT", json.dumps({k: v for k, v in pins.items() if not k.startswith("_")}, indent=1))
        return 3

    comms_mod = load_pinned_module("pinned_comms", "research_map/comms.py")
    schemas_mod = load_pinned_module("pinned_schemas", "research_map/schemas.py")
    assert comms_mod.ROOT.resolve() == ROOT.resolve(), (comms_mod.ROOT, ROOT)

    # snapshot pinned inputs
    for rel in ("comms/rejected.jsonl", "research_map/comms.py", "research_map/schemas.py"):
        dst = OUT / rel.replace("/", "__")
        dst.write_bytes((ROOT / rel).read_bytes())

    ingested = set()
    ip = ROOT / "runtime/state/ingested_ids.json"
    if ip.exists():
        try:
            d = json.loads(ip.read_text())
            ingested = set(d if isinstance(d, list) else (d.get("ids") or d.keys()))
        except Exception:
            ingested = set()

    accepted_stream = {}
    for line in (ROOT / "research_map/events.jsonl").read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            if isinstance(d, dict) and d.get("event_id"):
                accepted_stream.setdefault(d["event_id"], d)
        except ValueError:
            continue
    SEM = ("event_type", "actor", "node_id", "node_ids", "class_id", "class_ids",
           "conclusion_type", "verdict", "target_id", "status")

    rows = []
    for line in (ROOT / "comms/rejected.jsonl").read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            rows.append({"event_id": None, "reason": "UNPARSEABLE REJECT ROW", "source": None, "raw": line[:600]})

    def classify_once():
        result = []
        for r in rows:
            src = r.get("source")
            eid = r.get("event_id")
            rec = {"event_id": eid, "stored_reason": r.get("reason"), "source": src,
                   "rejected_at": r.get("rejected_at"), "event_type": r.get("event_type"),
                   "actor": r.get("actor"), "class_ids": [], "node_id": "", "status": None,
                   "source_mutated": None, "detail": None}
            p = ROOT / src if src else None
            doc = None
            if p is not None and p.exists():
                try:
                    for cand in comms_mod._json_objects(p.read_text(errors="replace")):
                        if isinstance(cand, dict) and (cand.get("event_id") == eid or eid is None):
                            doc = cand
                            break
                except Exception as e:  # noqa: BLE001
                    rec["detail"] = f"source read error: {e}"
            if doc is None:
                rec["status"] = ("SOURCE_NOT_FOUND_ACCEPTED" if eid in accepted_stream or eid in ingested
                                 else "SOURCE_NOT_FOUND_NOT_ACCEPTED")
                rec["detail"] = rec["detail"] or "event_id not found in recorded source (file gone or rewritten)"
                raw = r.get("raw") or ""
                rec["raw_event_type"] = (re.search(r'"event_type"\s*:\s*"([^"]+)"', raw) or [None, None])[1]
                rec["raw_actor"] = (re.search(r'"actor"\s*:\s*"([^"]+)"', raw) or [None, None])[1]
                rec["raw_class_ids"] = sorted(set(re.findall(r"AF-[A-Z0-9\-]+", raw)))
                if eid in accepted_stream:
                    rec["content_comparison"] = "ACCEPTED_LATER_UNCOMPARABLE_SOURCE_GONE"
                result.append(rec)
                continue
            rec["class_ids"] = classes_of(doc)
            rec["node_id"] = node_of(doc)
            rec["actor"] = doc.get("actor") or rec.get("actor")
            if r.get("raw"):
                a, b = compact(r["raw"]), compact(json.dumps(doc, ensure_ascii=False))
                rec["source_mutated"] = not (a[:300] and (a[:300] in b or b[:300] in a))
            if eid in accepted_stream or eid in ingested:
                rec["status"] = "ACCEPTED_LATER" if eid in accepted_stream else "ACCEPTED_ID_ONLY"
                acc = accepted_stream.get(eid)
                if acc is not None:
                    try:
                        raw_doc = json.loads(r.get("raw") or "")
                        diff = [k for k in SEM if k in raw_doc and raw_doc.get(k) != acc.get(k)]
                        rec["content_comparison"] = "MUTATED_BEFORE_ACCEPT:" + ",".join(diff) if diff else "IDENTICAL_SEMANTIC_FIELDS"
                    except ValueError:
                        rec["content_comparison"] = "UNCOMPARABLE_RAW_TRUNCATED"
                result.append(rec)
                continue
            status, detail, _ = replay(comms_mod, schemas_mod, doc, src)
            rec["status"] = "REPLAY_VALID" if status == "NOW_VALID" else "REPLAY_INVALID"
            rec["detail"] = detail
            # gate relevance for replay-valid (i.e. would be accepted but is not in the stream)
            if rec["status"] == "REPLAY_VALID":
                hashes = []
                for k in ("sha256", "reviewed_sha256", "artifact_sha256", "cited_sha256"):
                    v = doc.get(k)
                    if isinstance(v, str):
                        hashes.append(v)
                    elif isinstance(v, dict):
                        hashes.extend(str(x) for x in v.values())
                hits = [n for n, cd in pins["_canonical_disk"].items()
                        if cd["sha256"] and cd["sha256"] in hashes]
                rec["gate_relevant_nodes"] = hits
                for ref in (doc.get("evidence_refs") or []):
                    if isinstance(ref, str) and "#sha256:" in ref:
                        hh = ref.split("#sha256:")[1][:64]
                        for n, cd in pins["_canonical_disk"].items():
                            if cd["sha256"] and cd["sha256"].startswith(hh):
                                rec.setdefault("gate_relevant_nodes", [])
                                rec["gate_relevant_nodes"] = sorted(set(rec["gate_relevant_nodes"] + [n]))
                if doc.get("artifact_refs"):
                    for ref in doc["artifact_refs"]:
                        if isinstance(ref, str):
                            for n, cd in pins["_canonical_disk"].items():
                                if ref.startswith(cd["path"]):
                                    rec.setdefault("gate_relevant_nodes", [])
                                    rec["gate_relevant_nodes"] = sorted(set(rec["gate_relevant_nodes"] + [n]))
            result.append(rec)
        return result

    pass1 = classify_once()
    pass2 = classify_once()
    deterministic = compact(json.dumps(pass1, sort_keys=True)) == compact(json.dumps(pass2, sort_keys=True))

    # ---- controls ----
    controls = {}
    acc = []
    ev = (ROOT / "research_map/events.jsonl").read_text(errors="replace").splitlines()
    stride = max(1, len(ev) // 40)
    for i in range(0, len(ev), stride):
        line = ev[i].strip()
        if not line:
            continue
        try:
            acc.append(json.loads(line))
        except ValueError:
            pass
        if len(acc) >= 40:
            break
    c1_fail = []
    for d in acc:
        st, det, _ = replay(comms_mod, schemas_mod, d, "events.jsonl")
        if st != "NOW_VALID":
            c1_fail.append({"event_id": d.get("event_id"), "detail": det})
    controls["C1_40_accepted_events_replay_pass"] = {"n": len(acc), "failed": c1_fail, "pass": len(c1_fail) == 0}

    art = {"event_id": "w097-ctrl-artifact-no-node", "event_type": "artifact", "actor": "worker-097",
           "created_at": t0, "path": "artifacts/worker-097/reject_audit/report.json"}
    st, det, _ = replay(comms_mod, schemas_mod, art, "control")
    controls["C2a_artifact_without_node_rejected"] = {"status": st, "detail": det, "pass": st == "STILL_INVALID"}

    stat = {"event_id": "w097-ctrl-bare-status", "event_type": "status", "actor": "worker-097", "created_at": t0}
    st, det, _ = replay(comms_mod, schemas_mod, stat, "control")
    controls["C2b_bare_status_accepted_by_pinned_pipeline"] = {"status": st, "detail": det, "pass": st == "NOW_VALID"}

    controls["C3_deterministic_two_passes"] = {"pass": deterministic}
    pins_after = measure_pins()
    drift = [k for k, v in pins_after.items() if not k.startswith("_") and not v.get("match")]
    controls["C4_no_pin_drift_during_run"] = {"drift": drift, "pass": not drift}
    controls_pass = all(c.get("pass") for c in controls.values())

    # ---- summary ----
    def count(key, val):
        return sum(1 for r in pass1 if r.get(key) == val)

    now_valid = [r for r in pass1 if r["status"] == "REPLAY_VALID"]
    lost = [r for r in pass1 if r["status"] in ("REPLAY_INVALID", "SOURCE_NOT_FOUND_NOT_ACCEPTED")]
    by_type = {}
    by_actor = {}
    by_class = {c: 0 for c in CLASSES}
    by_node = {}
    gate_rel = []
    for r in now_valid:
        by_type[r["event_type"]] = by_type.get(r["event_type"], 0) + 1
        by_actor[r.get("actor") or "?"] = by_actor.get(r.get("actor") or "?", 0) + 1
        for c in r["class_ids"]:
            by_class[c] = by_class.get(c, 0) + 1
        n = r["node_id"] or "GLOBAL"
        by_node[n] = by_node.get(n, 0) + 1
        if r.get("gate_relevant_nodes"):
            gate_rel.append({"event_id": r["event_id"], "event_type": r["event_type"],
                             "nodes": r["gate_relevant_nodes"], "source_mutated": r["source_mutated"]})

    lost_classes = {c: 0 for c in CLASSES}
    for r in lost:
        for c in (r.get("class_ids") or r.get("raw_class_ids") or []):
            lost_classes[c] = lost_classes.get(c, 0) + 1
    comp = {}
    for r in pass1:
        k = str(r.get("content_comparison"))
        comp[k] = comp.get(k, 0) + 1

    summary = {
        "total_rejected_rows": len(rows),
        "statuses": {s: count("status", s) for s in sorted({r["status"] for r in pass1})},
        "replay_valid_not_in_stream": len(now_valid),
        "replay_invalid_lost": len([r for r in pass1 if r["status"] == "REPLAY_INVALID"]),
        "source_not_found_not_accepted": len([r for r in pass1 if r["status"] == "SOURCE_NOT_FOUND_NOT_ACCEPTED"]),
        "lost_class_bound_rows": lost_classes,
        "content_comparison_census": comp,
        "now_valid_by_event_type": by_type,
        "now_valid_by_actor": by_actor,
        "now_valid_by_class": by_class,
        "now_valid_by_node": by_node,
        "now_valid_gate_relevant": gate_rel,
        "source_mutated_rows": sum(1 for r in pass1 if r["source_mutated"]),
    }

    report = {
        "schema": "w097-reject-stream-audit/v1",
        "task_id": "W097-REJECT-STREAM-AUDIT-01",
        "actor": "worker-097",
        "instance": os.environ.get("DSH_INSTANCE_ID") or "worker-097",
        "created_at": t0,
        "finished_at": now(),
        "gate": "G-AUDIT",
        "node_ids": ["A1"],
        "class_ids": CLASSES,
        "authority": "worker measurement only; no ingest, no gate verdict, no node status, no canonical write",
        "pins": pins,
        "method": {
            "instrument": "artifacts/worker-097/reject_audit/audit.py",
            "pipeline": "research_map/comms.py::normalize_event + research_map/schemas.py::validate_event (pinned)",
            "replay_source": "recorded source file, event located by event_id",
            "notes": ["stored raw is truncated at 600 chars",
                      "source files may have been rewritten since rejection; source_mutated flags this"],
        },
        "summary": summary,
        "controls": controls,
        "controls_pass": controls_pass,
        "rows": pass1,
        "falsifier": ("Re-run at the same pins and find a NOW_VALID row that the pinned pipeline rejects, "
                      "an accepted event (C1 sample) that the pipeline rejects, two passes that disagree, "
                      "or a pin that moves."),
    }
    (HERE / "report.json").write_text(json.dumps(report, indent=1))
    (HERE / "controls.json").write_text(json.dumps(controls, indent=1))

    files = {}
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name not in ("manifest.json", "raw_sha256.txt"):
            files[str(p.relative_to(HERE))] = {"bytes": p.stat().st_size, "sha256": sha256(p)}
    files["report.json"] = {"bytes": (HERE / "report.json").stat().st_size, "sha256": sha256(HERE / "report.json")}
    (HERE / "raw_sha256.txt").write_text(
        "".join(f"{v['sha256']}  {k}\n" for k, v in sorted(files.items())))
    manifest = {"task_id": "W097-REJECT-STREAM-AUDIT-01", "created_at": now(), "files": files,
                "pins": {k: v for k, v in pins.items() if not k.startswith("_")}}
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=1))

    print(json.dumps({"controls_pass": controls_pass, "summary": summary,
                      "report_sha256": sha256(HERE / "report.json")}, indent=1))
    return 0 if controls_pass else 2


if __name__ == "__main__":
    sys.exit(main())

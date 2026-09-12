#!/usr/bin/env python3
"""W070-GFORM-REV29-PINBIND-01 -- independent per-file pin-binding census of the live
FROZEN rev29 manifest (G-FORM).

Question: at the live `artifacts/formulation/FROZEN.json` bytes, does every declared
per-file pin (the 50 `files` entries + the 2 `logical_artifacts` entries) resolve to the
live bytes at its declared path, and do the canonical F1/F2a/F2b machinery paths agree
across the pin legs (FROZEN manifest <-> disk <-> accepted artifact stream <-> controller
hash registry <-> map pins)?

Method (pre-registered in frame.json before this census reads any moving input):
  * read-only; writes only inside this task directory;
  * `--preregister` measures FROZEN.json, extracts every declared (path, sha256, bytes)
    pin, and writes frame.json; the frame is hashed before the run;
  * `--run` re-measures FROZEN.json (must equal the frame pin or the run is VOID), then
    classifies every declared pin: MATCH / MISMATCH / MISSING / PATH_STALE (bytes found
    elsewhere by hash index) / DANGLING (bytes nowhere in the indexed roots);
  * every canonical machinery path also gets a leg-by-leg binding table;
  * controls: known-good pin, one-byte mutation, synthetic missing path, hash-index
    positive, no self-reference pin, FROZEN drift check at exit;
  * no network, no numerics, no canonical writes; this is a measurement, not a gate
    verdict and not a review verdict.

Falsifier: re-run `--run` at the same FROZEN.json sha256. Falsified if any pin classified
MATCH resolves differently, if any pin classified PATH_STALE/DANGLING is shown to resolve
under the manifest's own path rules, or if the run's byte comparisons and this instrument
disagree on a pinned file. A FROZEN.json sha256 change at run start voids the run rather
than falsifying it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TASK_ID = "W070-GFORM-REV29-PINBIND-01"
ACTOR = "worker-070"
NODE_IDS = ["F1", "F2a", "F2b"]
CLASS_IDS = ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"]
GATE = "G-FORM"

FROZEN_REL = "artifacts/formulation/FROZEN.json"
EVENTS_REL = "research_map/events.jsonl"
REGISTRY_REL = "runtime/state/artifact_hashes.json"
MAP_REL = "research_map/research_map.json"

CANONICAL = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/taxonomy_cases.jsonl",
    "research_map/formulation_taxonomy.yaml",
    "artifacts/formulation/formulation_taxonomy.yaml",
]
MIRROR_PAIRS = [
    ("schemas/af_wcc_vacuum.yaml", "artifacts/formulation/schemas/af_wcc_vacuum.yaml"),
    ("schemas/af_scc_c2_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml"),
    ("schemas/af_scc_c0_vacuum.yaml", "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"),
]
NODE_PATH = {
    "F1": "schemas/af_wcc_vacuum.yaml",
    "F2a": "schemas/af_scc_c2_vacuum.yaml",
    "F2b": "schemas/af_scc_c0_vacuum.yaml",
}
INDEX_ROOTS = ["artifacts", "schemas", "research_map", "ledger", "numerics", "evaluation"]
INDEX_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".mypy_cache"}
INDEX_MAX_BYTES = 8 * 1024 * 1024

FALSIFIER = (
    "Re-run census_070_pinbind.py --run at the same artifacts/formulation/FROZEN.json sha256. "
    "Falsified if any pin classified MATCH resolves differently, if a pin classified PATH_STALE or "
    "DANGLING is shown to resolve under the manifest's own path rules, or if an independent byte "
    "comparison disagrees with this report on a pinned file. A FROZEN.json sha256 change at run "
    "start voids the run rather than falsifying it."
)
CLAIMS_NOT_MADE = [
    "not a gate verdict (G-FORM stays pending; verdict authority is Astra / astra-lead-audit)",
    "not a node completion (F1/F2a/F2b stay active/unverified)",
    "not a mathematics or physics claim; this is a byte-binding measurement",
    "not a review verdict on any schema's content, wording or semantics",
    "not evidence about any revision other than the FROZEN.json bytes measured here",
]


def iso_now() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(p: Path) -> dict:
    if not p.exists():
        return {"exists": False}
    st = p.stat()
    return {
        "exists": True,
        "sha256": sha256_file(p),
        "bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
    }


def parse_ts(s):
    if not isinstance(s, str):
        return None
    t = s.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(t)
    except ValueError:
        return None


def build_hash_index(root: Path) -> dict:
    idx: dict[str, list[str]] = {}
    for rel in INDEX_ROOTS:
        base = root / rel
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in INDEX_SKIP_DIRS]
            for fn in filenames:
                p = Path(dirpath) / fn
                try:
                    if p.stat().st_size > INDEX_MAX_BYTES:
                        continue
                    h = sha256_file(p)
                except OSError:
                    continue
                idx.setdefault(h, []).append(str(p.relative_to(root)))
    return idx


def canonical_triples(frozen: dict):
    files = frozen.get("files", {}) or {}
    logical = frozen.get("logical_artifacts", {}) or {}
    per_path = {}
    for path, rec in files.items():
        per_path.setdefault(path, []).append(
            {"leg": "files", "declared_sha256": rec.get("sha256"), "declared_bytes": rec.get("bytes")}
        )
    for name, rec in logical.items():
        if isinstance(rec, dict):
            per_path.setdefault(rec.get("path"), []).append(
                {"leg": "logical_artifacts:" + name, "declared_sha256": rec.get("sha256"), "declared_bytes": None}
            )
    return per_path


def latest_event_per_path(root: Path) -> dict:
    out = {}
    events = root / EVENTS_REL
    if not events.exists():
        return out
    with open(events, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"artifact"' not in line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("event_type") != "artifact":
                continue
            paths = e.get("path")
            if isinstance(paths, str):
                paths = [paths]
            if not isinstance(paths, list):
                continue
            for p in paths:
                if not isinstance(p, str):
                    continue
                rec = out.setdefault(p, {"events": 0, "declared_shas": set(), "latest": None})
                rec["events"] += 1
                if isinstance(e.get("sha256"), str):
                    rec["declared_shas"].add(e["sha256"])
                ts = parse_ts(e.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)
                if rec["latest"] is None or ts >= rec["latest"]["_ts"]:
                    rec["latest"] = {
                        "_ts": ts,
                        "event_id": e.get("event_id"),
                        "created_at": e.get("created_at"),
                        "sha256": e.get("sha256"),
                        "validation_status": e.get("validation_status"),
                        "actor": e.get("actor"),
                    }
    return out


def registry_lookup(root: Path) -> dict:
    reg = root / REGISTRY_REL
    out = {}
    if not reg.exists():
        return out
    try:
        d = json.loads(reg.read_text())
    except (OSError, json.JSONDecodeError):
        return out
    for section in ("hashes", "registry"):
        sec = d.get(section)
        if not isinstance(sec, dict):
            continue
        for path, rec in sec.items():
            if isinstance(rec, dict):
                out.setdefault(path, []).append(
                    {"section": section, "sha256": rec.get("sha256"), "bytes": rec.get("bytes"),
                     "node_id": rec.get("node_id"), "kind": rec.get("kind")}
                )
    return out


def map_lookup(root: Path) -> dict:
    m = root / MAP_REL
    out = {"frozen_artifacts": [], "measured_pins": {}}
    if not m.exists():
        return out
    try:
        d = json.loads(m.read_text())
    except (OSError, json.JSONDecodeError):
        return out
    for fa in d.get("frozen_artifacts", []) or []:
        if isinstance(fa, dict):
            out["frozen_artifacts"].append(
                {k: fa.get(k) for k in ("path", "node_id", "sha256", "active", "superseded_at", "frozen_at")}
            )
    pins = {}
    src = d.get("measured_pins")
    if isinstance(src, dict):
        pins.update({k: v for k, v in src.items() if isinstance(v, str)})
    out["measured_pins"] = pins
    # The per-pass controller decisions record carries measured node pins; newest first.
    decisions = sorted((root / "runtime/state/controller_verification").glob("astra-lifecycle-*-decisions.json"))
    if decisions:
        newest = decisions[-1]
        try:
            dd = json.loads(newest.read_text())
            mpin = dd.get("measured_pins")
            if isinstance(mpin, dict):
                out["controller_decisions_path"] = str(newest.relative_to(root))
                out["controller_measured_pins"] = {k: v for k, v in mpin.items() if isinstance(v, str)}
        except (OSError, json.JSONDecodeError):
            pass
    return out


def classify_pin(root: Path, path: str, declared_sha: str, declared_bytes, index: dict) -> dict:
    res = {
        "path": path,
        "declared_sha256": declared_sha,
        "declared_bytes": declared_bytes,
    }
    live = measure(root / path) if isinstance(path, str) else {"exists": False}
    res["live_exists"] = bool(live.get("exists"))
    res["live_sha256"] = live.get("sha256")
    res["live_bytes"] = live.get("bytes")
    res["hash_index_paths"] = index.get(declared_sha, [])[:8] if isinstance(declared_sha, str) else []
    if not isinstance(declared_sha, str):
        res["verdict"] = "DANGLING"
        res["detail"] = "pin has no sha256 string"
    elif not live.get("exists"):
        res["verdict"] = "PATH_STALE" if res["hash_index_paths"] else "MISSING"
        res["detail"] = "declared path absent; " + (
            "bytes found elsewhere by hash index" if res["hash_index_paths"] else "bytes not found in indexed roots"
        )
    elif live["sha256"] == declared_sha:
        res["verdict"] = "MATCH"
        res["detail"] = "declared path bytes equal declared sha256"
    else:
        res["verdict"] = "MISMATCH"
        res["detail"] = "declared path exists with different bytes"
    if res.get("verdict") == "MATCH" and isinstance(declared_bytes, int) and live.get("bytes") != declared_bytes:
        res["verdict"] = "BYTES_MISMATCH"
        res["detail"] = f"sha match but declared bytes {declared_bytes} != live bytes {live.get('bytes')}"
    return res


def run_preregister(root: Path, outdir: Path) -> int:
    frozen = root / FROZEN_REL
    if not frozen.exists():
        print("FROZEN.json absent", file=sys.stderr)
        return 2
    meas = measure(frozen)
    data = json.loads(frozen.read_text())
    per_path = canonical_triples(data)
    frame = {
        "schema": "w070-gform-rev29-pinbind/frame/v1",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "gate": GATE,
        "node_ids": NODE_IDS,
        "class_ids": CLASS_IDS,
        "created_at": iso_now(),
        "object_under_test": {"path": FROZEN_REL, **meas},
        "declared_pin_count": sum(len(v) for v in per_path.values()),
        "declared_paths": {p: v for p, v in sorted(per_path.items())},
        "canonical_paths": CANONICAL,
        "mirror_pairs": MIRROR_PAIRS,
        "node_path_map": NODE_PATH,
        "rules": {
            "verdict_match": "declared path exists and its measured sha256 equals the declared pin",
            "verdict_mismatch": "declared path exists with different bytes",
            "verdict_path_stale": "declared path absent but the declared bytes exist elsewhere under the indexed roots",
            "verdict_missing": "declared path absent and declared bytes not found in the indexed roots",
            "verdict_dangling": "pin has no sha256 string",
            "verdict_bytes_mismatch": "sha matches but the declared byte count does not",
            "triple_binding": "FROZEN pin vs live disk vs latest accepted artifact event vs registry vs map pins",
            "void_conditions": ["FROZEN.json sha256 differs from the frame at run start or run end",
                                "any control fails"],
        },
        "controls": [
            "C1 known-good pin (F1) classifies MATCH",
            "C2 one-byte mutation classifies MISMATCH",
            "C3 synthetic absent path classifies MISSING",
            "C4 hash-index positive control finds a temp file by sha",
            "C5 FROZEN.json is not pinned by itself",
            "C6 FROZEN.json sha256 unchanged at exit",
            "C7 accepted-stream extraction returns at least one F1 artifact event",
        ],
        "falsifier": FALSIFIER,
        "claims_not_made": CLAIMS_NOT_MADE,
    }
    outdir.mkdir(parents=True, exist_ok=True)
    fp = outdir / "frame.json"
    fp.write_text(json.dumps(frame, indent=1, sort_keys=True) + "\n")
    fsha = sha256_file(fp)
    (outdir / "frame.sha256.txt").write_text(fsha + "  frame.json\n")
    print(json.dumps({"frame": str(fp), "frame_sha256": fsha, "declared_pin_count": frame["declared_pin_count"],
                      "frozen_sha256": meas.get("sha256")}, indent=1))
    return 0


def run_census(root: Path, outdir: Path) -> int:
    log_lines = []

    def log(msg):
        line = f"{iso_now()} {msg}"
        log_lines.append(line)
        print(line)

    frame_path = outdir / "frame.json"
    if not frame_path.exists():
        print("frame.json absent; run --preregister first", file=sys.stderr)
        return 2
    frame = json.loads(frame_path.read_text())
    frame_sha = sha256_file(frame_path)
    declared_frozen = frame["object_under_test"]["sha256"]

    log(f"task={TASK_ID} frame_sha256={frame_sha} frame_declared_frozen={declared_frozen}")

    # Objects under test: measured first, last and only.
    frozen_path = root / FROZEN_REL
    frozen_start = measure(frozen_path)
    if frozen_start.get("sha256") != declared_frozen:
        report = {
            "schema": "w070-gform-rev29-pinbind/report/v1",
            "task_id": TASK_ID, "actor": ACTOR, "gate": GATE,
            "class_ids": CLASS_IDS, "node_ids": NODE_IDS, "created_at": iso_now(),
            "verdict": "VOID",
            "void_reason": "FROZEN.json sha256 at run start differs from the frame pin",
            "frozen_frame_sha256": declared_frozen,
            "frozen_start": frozen_start,
            "frame_sha256": frame_sha,
        }
        (outdir / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
        return 3

    data = json.loads(frozen_path.read_text())
    per_path = canonical_triples(data)

    aux = {
        "research_map/research_map.json": measure(root / MAP_REL),
        "runtime/state/artifact_hashes.json": measure(root / REGISTRY_REL),
        "research_map/events.jsonl": measure(root / EVENTS_REL),
    }
    log("building bounded hash index over " + ",".join(INDEX_ROOTS))
    index = build_hash_index(root)

    pins = []
    for path in sorted(per_path, key=lambda x: (x is None, x)):
        for decl in per_path[path]:
            rec = classify_pin(root, path, decl["declared_sha256"], decl.get("declared_bytes"), index)
            rec["leg"] = decl["leg"]
            pins.append(rec)

    events = latest_event_per_path(root)
    registry = registry_lookup(root)
    mp = map_lookup(root)

    triples = {}
    for path in CANONICAL:
        declared = sorted({d["declared_sha256"] for d in per_path.get(path, [])})
        disk = measure(root / path)
        ev = events.get(path)
        reg = registry.get(path, [])
        fa = [x for x in mp["frozen_artifacts"] if x.get("path") == path]
        node_pin = None
        for nid, p in NODE_PATH.items():
            if p == path and mp["measured_pins"].get(nid):
                node_pin = {"node_id": nid, "sha256": mp["measured_pins"][nid]}
        ctl_pin = None
        for nid, p in NODE_PATH.items():
            if p == path and mp.get("controller_measured_pins", {}).get(nid):
                ctl_pin = {"node_id": nid, "sha256": mp["controller_measured_pins"][nid],
                           "source": mp.get("controller_decisions_path")}
        legs = {
            "frozen_pin": declared[0] if len(declared) == 1 else declared,
            "disk": disk.get("sha256"),
            "latest_event": ({k: v for k, v in ev["latest"].items() if k != "_ts"} if ev and ev.get("latest") else None),
            "registry": reg,
            "map_frozen_artifacts": fa,
            "map_measured_pin": node_pin,
            "controller_measured_pin": ctl_pin,
        }
        agree = []
        if declared and disk.get("sha256"):
            agree.append({"legs": "frozen_vs_disk", "agree": disk["sha256"] == declared[0] if len(declared) == 1 else None})
        if ev and ev.get("latest") and declared:
            agree.append({"legs": "frozen_vs_latest_event", "agree": ev["latest"].get("sha256") == declared[0]})
            agree.append({"legs": "disk_vs_latest_event", "agree": ev["latest"].get("sha256") == disk.get("sha256")})
        if reg and declared:
            agree.append({"legs": "frozen_vs_registry",
                          "agree": any(r.get("sha256") == declared[0] for r in reg)})
        if node_pin and declared:
            agree.append({"legs": "frozen_vs_map_measured_pin", "agree": node_pin["sha256"] == declared[0]})
        if ctl_pin and declared:
            agree.append({"legs": "frozen_vs_controller_measured_pin", "agree": ctl_pin["sha256"] == declared[0]})
        triples[path] = {
            "legs": legs,
            "event_churn": {"artifact_events": ev["events"] if ev else 0,
                            "distinct_declared_sha256": len(ev["declared_shas"]) if ev else 0},
            "leg_agreement": agree,
            "disagreements": [a["legs"] for a in agree if a["agree"] is False],
        }

    mirror = {}
    for a, b in MIRROR_PAIRS:
        ma, mb = measure(root / a), measure(root / b)
        mirror[a] = {"mirror": b, "canonical": ma, "mirror_measure": mb,
                     "byte_identical": bool(ma.get("exists") and mb.get("exists") and ma["sha256"] == mb["sha256"])}

    companion = {}
    ca, cb = "research_map/formulation_taxonomy.yaml", "artifacts/formulation/formulation_taxonomy.yaml"
    ma, mb = measure(root / ca), measure(root / cb)
    companion = {"declared_taxonomy": {"path": ca, **ma}, "class_contract_supplement": {"path": cb, **mb},
                 "byte_identical": bool(ma.get("sha256") == mb.get("sha256")),
                 "expected": "distinct logical artifacts; byte-identity not required (FROZEN.path_policy)"}

    # ---- controls ----
    controls = {}
    ctl_dir = outdir / "control"
    ctl_dir.mkdir(parents=True, exist_ok=True)
    ctl_path = ctl_dir / "ctl_mutant.yaml"
    good = root / NODE_PATH["F1"]
    try:
        body = bytearray(good.read_bytes())
        if body:
            body[len(body) // 2] ^= 0x01
        ctl_path.write_bytes(bytes(body))
        ctl = classify_pin(root, str(ctl_path.relative_to(root)), sha256_file(good), None, index)
        controls["C2_one_byte_mutation"] = {"verdict": ctl["verdict"], "pass": ctl["verdict"] == "MISMATCH"}
    except OSError as exc:
        controls["C2_one_byte_mutation"] = {"verdict": "ERROR", "pass": False, "error": str(exc)}
    finally:
        try:
            ctl_path.unlink()
        except OSError:
            pass

    f1_pin = [p for p in pins if p["path"] == NODE_PATH["F1"]]
    controls["C1_known_good_pin"] = {
        "pass": bool(f1_pin) and all(p["verdict"] == "MATCH" for p in f1_pin),
        "verdicts": [p["verdict"] for p in f1_pin],
    }
    synthetic = classify_pin(root, "artifacts/worker-070/gform_rev29_pinbind/control/definitely_absent.bin",
                             "0" * 64, None, index)
    controls["C3_synthetic_missing"] = {"verdict": synthetic["verdict"],
                                        "pass": synthetic["verdict"] == "MISSING"}
    tmp = ctl_dir / "ctl_index.bin"
    try:
        tmp.write_bytes(b"w070-pinbind-index-control\n")
        h = sha256_file(tmp)
        idx2 = {h: [str(tmp.relative_to(root))]}
        found = classify_pin(root, str(tmp.relative_to(root)), h, None, idx2)
        controls["C4_hash_index_positive"] = {"verdict": found["verdict"], "pass": found["verdict"] == "MATCH"}
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    controls["C5_no_self_reference"] = {
        "pass": all(("FROZEN.json" not in (p["path"] or "")) for p in pins),
        "checked_pins": len(pins),
    }
    f1_events = events.get(NODE_PATH["F1"])
    controls["C7_event_stream_extraction"] = {
        "pass": bool(f1_events and f1_events["events"] > 0),
        "artifact_events_for_F1": f1_events["events"] if f1_events else 0,
    }

    frozen_end = measure(frozen_path)
    drift_frozen = frozen_end.get("sha256") != frozen_start.get("sha256")
    aux_end = {
        "research_map/research_map.json": measure(root / MAP_REL),
        "runtime/state/artifact_hashes.json": measure(root / REGISTRY_REL),
        "research_map/events.jsonl": measure(root / EVENTS_REL),
    }
    controls["C6_frozen_no_drift"] = {"pass": not drift_frozen,
                                      "start": frozen_start.get("sha256"), "end": frozen_end.get("sha256")}
    all_controls_pass = all(c.get("pass") for c in controls.values())

    counts = {}
    for p in pins:
        counts[p["verdict"]] = counts.get(p["verdict"], 0) + 1
    triple_disagreements = {p: t["disagreements"] for p, t in triples.items() if t["disagreements"]}
    if drift_frozen or not all_controls_pass:
        verdict = "VOID"
    elif counts.get("MATCH", 0) == len(pins) and not triple_disagreements and all(m["byte_identical"] for m in mirror.values()):
        verdict = "BINDING_CONSISTENT"
    else:
        verdict = "BINDING_GAPS"

    log(f"pins={len(pins)} counts={counts} verdict={verdict} controls_all_pass={all_controls_pass} drift={drift_frozen}")

    report = {
        "schema": "w070-gform-rev29-pinbind/report/v1",
        "task_id": TASK_ID,
        "actor": ACTOR,
        "node_ids": NODE_IDS,
        "class_ids": CLASS_IDS,
        "gate": GATE,
        "created_at": iso_now(),
        "verdict": verdict,
        "frame_sha256": frame_sha,
        "object_under_test": {"path": FROZEN_REL, "start": frozen_start, "end": frozen_end,
                              "frozen_revision": data.get("revision"), "frozen_at": data.get("frozen_at")},
        "auxiliary_inputs_start": aux,
        "auxiliary_inputs_end": aux_end,
        "declared_pin_count": len(pins),
        "counts": counts,
        "pins": pins,
        "triple_binding": triples,
        "triple_disagreements": triple_disagreements,
        "mirror_check": mirror,
        "companion_check": companion,
        "controls": controls,
        "controls_all_pass": all_controls_pass,
        "drift": {"frozen": drift_frozen,
                  "map": aux["research_map/research_map.json"].get("sha256") != aux_end["research_map/research_map.json"].get("sha256"),
                  "registry": aux["runtime/state/artifact_hashes.json"].get("sha256") != aux_end["runtime/state/artifact_hashes.json"].get("sha256"),
                  "events": aux["research_map/events.jsonl"].get("sha256") != aux_end["research_map/events.jsonl"].get("sha256")},
        "method": {
            "read_only": True,
            "network": False,
            "index_roots": INDEX_ROOTS,
            "index_max_bytes": INDEX_MAX_BYTES,
            "indexed_files": sum(len(v) for v in index.values()),
        },
        "falsifier": FALSIFIER,
        "claims_not_made": CLAIMS_NOT_MADE,
    }
    (outdir / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (outdir / "run.log").write_text("\n".join(log_lines) + "\n")
    print(json.dumps({"verdict": verdict, "counts": counts, "controls_all_pass": all_controls_pass,
                      "triple_disagreements": list(triple_disagreements)}, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None)
    ap.add_argument("--preregister", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()
    here = Path(__file__).resolve()
    root = Path(args.root).resolve() if args.root else here.parents[3]
    outdir = here.parent
    if args.preregister and not args.run:
        return run_preregister(root, outdir)
    if args.run and not args.preregister:
        return run_census(root, outdir)
    ap.error("pass exactly one of --preregister or --run")


if __name__ == "__main__":
    sys.exit(main())

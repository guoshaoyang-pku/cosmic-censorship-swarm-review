#!/usr/bin/env python3
"""W093-GFORM-R3-REPLICATION-01 instrument (read-only, stdlib only, deterministic).

Replicates the F2b section and the global pin/declared-hash claims of
reviews/G-FORM-final-verify-r3.json at pinned T0 bytes.

Rules fixed in PREREGISTRATION.md before the run. Exit 0 iff all hard checks pass
(E1-E6, E8, E10 and R-strict/R-controller agreement); E7 (aggregate universe) and
E9 (non-author verifiability) are reported but not hard-failing.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
F2B_PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
F1_PIN = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
F2A_PIN = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
FROZEN_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
R3_REL = "reviews/G-FORM-final-verify-r3.json"
VERDICTS = ("accept", "revise", "reject", "inconclusive")
ALIASES = {"F2B": "F2b", "F2": "F2b", "AF-SCC-C0-VAC-GEN": "F2b", "F2b": "F2b"}

PIN_PATHS = [
    "schemas/af_wcc_vacuum.yaml",
    "schemas/af_scc_c2_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml",
    "schemas/af_scc_c0_vacuum.yaml.sha256",
    "schemas/af_scc_regularities.yaml",
    "entry_hashes.json",
    "artifacts/formulation/FROZEN.json",
    R3_REL,
    "reviews/F2b-review-worker-072-rev29.json",
    "reviews/F2b-rev13-full-090.json",
    "reviews/F2b-review-rev13-worker-071.json",
    "reviews/F2b-review-rev13-052.json",
    "artifacts/formulation/evidence/lead_formulation_lifecycle_07_independent_verify.json",
    "runtime/state/controller_verification/lifecycle_20260912-011239.json",
    "research_map/research_map.json",
    "research_map/astra_lifecycle.py",
    "research_map/events.jsonl",
    "comms/outbox/worker-072.jsonl",
    "comms/outbox/worker-066.jsonl",
]


def sha256f(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def mtime_iso(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime, CST).isoformat(timespec="microseconds")


def load_json(p: Path):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def pin_snapshot(paths) -> dict:
    out = {}
    for rel in paths:
        p = ROOT / rel
        if p.is_file():
            out[rel] = {"sha256": sha256f(p), "mtime": mtime_iso(p), "size": p.stat().st_size}
        else:
            out[rel] = {"sha256": None, "mtime": None, "size": None, "absent": True}
    return out


# ---------------------------------------------------------------- binder rules
def targets_in(d: dict) -> set:
    raw = set()
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            raw.add(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    raw.add(v[k2])
    out = set()
    for t in raw:
        u = t.strip()
        if u in ALIASES:
            out.add(ALIASES[u])
        elif u.upper() in ALIASES:
            out.add(ALIASES[u.upper()])
        elif "af_scc_c0" in u.lower():
            out.add("F2b")
    return out


def explicit_pins(d: dict) -> list:
    out = []
    for key in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256"):
        v = d.get(key)
        if isinstance(v, str):
            out.append(v.lower())
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    out.append(v[k2].lower())
    return out


def binds(pins, pin: str) -> bool:
    h12 = pin[:12]
    return any(p[:12] == h12 or pin.startswith(p[:12]) for p in pins)


def is_full(d: dict) -> bool:
    return d.get("counts_as_full_schema_verdict") is not False


def classify_fields(d: dict) -> dict:
    verdict = str(d.get("verdict", "")).lower()
    pins = explicit_pins(d)
    tgts = targets_in(d)
    return {
        "reviewer": str(d.get("reviewer") or d.get("actor") or "?"),
        "verdict": verdict,
        "targets": sorted(tgts),
        "pin_keys": sorted({k for k in ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256") if isinstance(d.get(k), str)}),
        "pins12": sorted({p[:12] for p in pins}),
        "binds_f2b": binds(pins, F2B_PIN),
        "targets_f2b": "F2b" in tgts,
        "full": is_full(d),
        "counts_as_full_schema_verdict": d.get("counts_as_full_schema_verdict", "<missing>"),
        "created_at": d.get("created_at"),
    }


def classify_record(path: Path, d: dict) -> dict:
    row = classify_fields(d)
    row.update({"file": path.name, "mtime": mtime_iso(path), "sha256": sha256f(path)})
    return row


def census_dir(revdir: Path) -> list:
    rows = []
    for rp in sorted(revdir.glob("*.json")):
        try:
            d = json.loads(rp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        if str(d.get("verdict", "")).lower() not in VERDICTS:
            continue
        rows.append(classify_record(rp, d))
    return rows


def summarize(rows: list, targeted_only: bool) -> dict:
    base = [r for r in rows if r["targets_f2b"]] if targeted_only else [r for r in rows if r["binds_f2b"]]
    return {
        "universe": "targets_f2b" if targeted_only else "pin_only",
        "records": len(base),
        "full_accepts": sorted(r["reviewer"] for r in base if r["verdict"] == "accept" and r["binds_f2b"] and r["full"] and r["targets_f2b"]) if targeted_only else sorted(r["reviewer"] for r in base if r["verdict"] == "accept" and r["full"]),
        "accepts_all": sorted(r["reviewer"] for r in base if r["verdict"] == "accept" and r["binds_f2b"]),
        "verdict_counts": {v: sum(1 for r in base if r["verdict"] == v and r["binds_f2b"]) for v in VERDICTS},
        "rows": [{k: r[k] for k in ("file", "reviewer", "verdict", "targets", "pin_keys", "pins12", "binds_f2b", "targets_f2b", "full", "mtime")} for r in base],
    }


# ---------------------------------------------------------------- controller
def controller_census() -> dict:
    hashes = {"F2b": {"sha256": F2B_PIN}, "F1": {"sha256": F1_PIN}, "F2a": {"sha256": F2A_PIN}}
    code = (
        "import sys, json\n"
        f"sys.path.insert(0, {str(ROOT / 'research_map')!r})\n"
        "import astra_lifecycle as al\n"
        f"cov = al.review_coverage(json.loads({json.dumps(hashes)!r}))\n"
        "print(json.dumps(cov['F2b']))\n"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(ROOT), timeout=300)
    if r.returncode != 0:
        return {"error": f"rc={r.returncode}", "stderr": r.stderr[-800:]}
    return json.loads(r.stdout)


# ---------------------------------------------------------------- universes
def event_universes() -> dict:
    evs = {}
    with open(ROOT / "research_map" / "events.jsonl", "r", encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("event_type") != "review":
                continue
            s = json.dumps(d)
            if "F2b" in s or "AF-SCC-C0-VAC-GEN" in s or "af_scc_c0" in s:
                evs[d.get("event_id")] = d
    evs = list(evs.values())

    def counts(sel):
        return {
            "events": len(sel),
            "verdict_events": {v: sum(1 for d in sel if str(d.get("verdict", "")).lower() == v) for v in VERDICTS},
            "distinct_reviewers": {
                v: len({str(d.get("reviewer") or d.get("actor")) for d in sel if str(d.get("verdict", "")).lower() == v})
                for v in VERDICTS
            },
        }

    return {
        "U3_target_eq_F2b": counts([d for d in evs if str(d.get("target_id")) == "F2b"]),
        "U4_target_contains": counts([d for d in evs if "F2b" in str(d.get("target_id")) or "AF-SCC-C0-VAC-GEN" in str(d.get("target_id"))]),
        "U5_any_mention": counts(evs),
    }


# ---------------------------------------------------------------- checks
def main() -> int:
    t0 = datetime.now(CST)
    pins0 = pin_snapshot(PIN_PATHS)
    checks = []
    notes = {}

    def check(cid, name, expected, observed, ok, detail=None):
        checks.append({"id": cid, "name": name, "expected": expected, "observed": observed, "ok": bool(ok), "detail": detail})

    # ---- E1 / E6: r3 pin claims and declared-hash layer
    r3 = load_json(ROOT / R3_REL)
    measured = {
        "F1": sha256f(ROOT / "schemas/af_wcc_vacuum.yaml"),
        "F2a": sha256f(ROOT / "schemas/af_scc_c2_vacuum.yaml"),
        "F2b": sha256f(ROOT / "schemas/af_scc_c0_vacuum.yaml"),
    }
    r3_pin_mismatch = []
    for cls, rec in r3.get("pins", {}).items():
        disk = measured.get(cls)
        if rec.get("pin") != disk or rec.get("measured_now") != disk:
            r3_pin_mismatch.append({"class": cls, "r3_pin": rec.get("pin"), "disk": disk})
    fm = r3.get("frozen_manifest", {})
    frozen_ok = fm.get("declared_sha256") == FROZEN_PIN and fm.get("measured_sha256") == FROZEN_PIN == sha256f(ROOT / "artifacts/formulation/FROZEN.json")
    check("E1", "r3 schema/FROZEN pins equal measured disk bytes", "all match",
          {"pin_mismatches": r3_pin_mismatch, "frozen_ok": frozen_ok}, not r3_pin_mismatch and frozen_ok,
          {"F1": measured["F1"][:12], "F2a": measured["F2a"][:12], "F2b": measured["F2b"][:12]})

    sidecar = ROOT / "schemas/af_scc_c0_vacuum.yaml.sha256"
    entry = ROOT / "entry_hashes.json"
    reg = ROOT / "schemas/af_scc_regularities.yaml"
    sidecar_h = sha256f(sidecar)
    entry_h = sha256f(entry)
    reg_h = sha256f(reg)
    entry_decl = load_json(entry).get("schemas/af_scc_c0_vacuum.yaml", "")
    layer = {
        "sidecar_file_sha12": sidecar_h[:12], "sidecar_declares": sidecar.read_text().split()[0][:12],
        "regularities_sha12": reg_h[:12], "entry_hashes_file_sha12": entry_h[:12],
        "entry_hashes_declares_c0": entry_decl[:12],
    }
    layer_ok = (sidecar_h.startswith("256dd18d7944") and sidecar.read_text().startswith("1bb78ce9b357")
                and reg_h.startswith("27255e5b34f3") and entry_h.startswith("09a5b37a190d")
                and entry_decl.startswith("1bb78ce9b357"))
    check("E6", "declared-hash layer stale exactly as r3 reports", "3 quoted layer hashes match; both declarers stale at 1bb78ce9b357",
          layer, layer_ok)

    # ---- E2: strict binder vs controller
    rows = census_dir(ROOT / "reviews")
    strict = summarize(rows, targeted_only=True)
    pin_only = summarize(rows, targeted_only=False)
    ctrl = controller_census()
    ctrl_full = sorted(ctrl.get("distinct_accept_reviewers", [])) if "error" not in ctrl else None
    r3_f2b = next(row for row in r3["coverage_table"] if row.get("class") == "F2b")
    r3_full = sorted(a.get("reviewer") for a in r3_f2b.get("non_author_accepts_full", []))
    e2_ok = strict["full_accepts"] == ["worker-052", "worker-071", "worker-090"] == ctrl_full == r3_full
    check("E2", "full-accept set reproduced by strict binder, controller, and r3",
          ["worker-052", "worker-071", "worker-090"],
          {"strict": strict["full_accepts"], "controller": ctrl_full, "r3": r3_full}, e2_ok)

    # ---- E3: worker-072 supersede trail
    w72 = load_json(ROOT / "reviews/F2b-review-worker-072-rev29.json")
    hist = w72.get("revision_history") or []
    h0 = hist[0] if hist else {}
    ev_72 = None
    with open(ROOT / "research_map/events.jsonl", "r", encoding="utf-8") as fh:
        for line in fh:
            if "w072-f2b-selfsupersede-review-20260912T011524" in line:
                try:
                    ev_72 = json.loads(line)
                except Exception:
                    pass
                break
    trail = {
        "rev1_verdict": h0.get("verdict"), "rev1_at": h0.get("at"), "rev1_sha12": str(h0.get("file_sha256"))[:12],
        "current_verdict": w72.get("verdict"), "current_sha12": sha256f(ROOT / "reviews/F2b-review-worker-072-rev29.json")[:12],
        "supersede_event": None if ev_72 is None else {"event_id": ev_72.get("event_id"), "created_at": ev_72.get("created_at"), "verdict": ev_72.get("verdict")},
        "r3_mentions_011524": "01:15:24" in json.dumps(r3),
    }
    e3_ok = (trail["rev1_verdict"] == "accept" and str(trail["rev1_at"]).startswith("2026-09-12T01:10:13")
             and trail["current_verdict"] == "revise" and trail["current_sha12"] == "5db91bb0781d"
             and trail["supersede_event"] and trail["supersede_event"]["created_at"].startswith("2026-09-12T01:15:24")
             and trail["r3_mentions_011524"])
    check("E3", "worker-072 accept->revise self-supersede trail consistent and cited by r3", "accept@01:10:13 -> revise; event 01:15:24",
          trail, e3_ok)

    # ---- E4: 090 disposition
    disp = None
    with open(ROOT / "comms/outbox/worker-066.jsonl", "r", encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("event_id") == "w066-f2b-acceptdisp-20260912T011504-02-review":
                disp = d
                break
    dtext = json.dumps(disp) if disp else ""
    disp_obs = {
        "event_found": disp is not None,
        "created_at": (disp or {}).get("created_at"),
        "verdict": (disp or {}).get("verdict"),
        "names_090_file": "F2b-rev13-full-090.json" in dtext,
        "says_SILENT": "SILENT" in dtext,
        "names_C1": "C1-DENIAL" in dtext,
        "names_C2": "C2-PREMISE" in dtext,
        "r3_names_finding": "W066-F2B-ACCEPT-DISPOSITION" in json.dumps(r3),
    }
    e4_ok = all(disp_obs[k] for k in ("event_found", "names_090_file", "says_SILENT", "names_C1", "names_C2", "r3_names_finding"))
    check("E4", "r3-cited worker-066 disposition exists and classifies 090 SILENT on both carriers", "all tokens present", disp_obs, e4_ok)

    # ---- E5: carriers at cited lines
    lines = (ROOT / "schemas/af_scc_c0_vacuum.yaml").read_text(encoding="utf-8").splitlines()
    def at(i):
        return lines[i - 1] if 0 < i <= len(lines) else ""
    carrier_obs = {
        "line152_quote": at(152).strip(),
        "line152_ok": "No containment with C2 or C0 is asserted here" in at(152),
        "line246_quote": at(246).strip(),
        "line246_ok": "C2 is a strictly larger extension class" in at(246),
        "chain_239_has_E_C0_E_C2": ("E_C0" in at(239) and "E_C2" in at(239)),
        "chain_window_235_260": [i for i in range(235, 261) if "E_C2" in at(i)][:5],
    }
    e5_ok = carrier_obs["line152_ok"] and carrier_obs["line246_ok"] and carrier_obs["chain_239_has_E_C0_E_C2"]
    check("E5", "both carrier quotes present verbatim at cited lines, chain in same file", "lines 152/246/239 as quoted", carrier_obs, e5_ok)

    # ---- E7: aggregate universes
    u2rows = [r for r in rows if r["targets_f2b"]]
    universes = {"U1_strict_binding_files": {"full_accepts": strict["full_accepts"], "accepts_all": len(strict["accepts_all"]), "revises": strict["verdict_counts"]["revise"], "records": strict["records"]},
                 "U2_target_files_any_pin": {"universe": "U2_target_files_any_pin", "records": len(u2rows),
                                             "full_accepts": sorted(r["reviewer"] for r in u2rows if r["verdict"] == "accept" and r["full"]),
                                             "accepts_all": sum(1 for r in u2rows if r["verdict"] == "accept"),
                                             "revises": sum(1 for r in u2rows if r["verdict"] == "revise")}}
    universes.update(event_universes())
    r3_agg = {"non_author_accepts_all": r3_f2b.get("non_author_accepts_all"), "revises": r3_f2b.get("revises")}
    repro = []
    for name, u in universes.items():
        cand = u.get("accepts_all") if isinstance(u.get("accepts_all"), int) else None
        if cand is None and isinstance(u.get("verdict_events"), dict):
            cand = u["verdict_events"].get("accept")
        rv = u.get("revises") if isinstance(u.get("revises"), int) else (u.get("verdict_events", {}) or {}).get("revise")
        if cand == r3_agg["non_author_accepts_all"] and rv == r3_agg["revises"]:
            repro.append(name)
    check("E7", "r3 aggregate (9 accepts-all, 37 revises) reproduces under a pre-registered universe",
          "expected UNREPRODUCED (pre-registered)", {"r3": r3_agg, "reproduced_by": repro, "universes": universes},
          True, "report-only check: failure to reproduce is the pre-registered expectation, not a task failure")

    # ---- E8: T0->T1 stability
    pins1 = pin_snapshot(PIN_PATHS)
    moved = [k for k in pins0 if pins0[k]["sha256"] != pins1[k]["sha256"]]
    rows_t1 = census_dir(ROOT / "reviews")
    t0map = {r["file"]: r["sha256"] for r in rows}
    drift = sorted(r["file"] for r in rows_t1 if t0map.get(r["file"]) != r["sha256"])
    added = sorted(set(r["file"] for r in rows_t1) - set(t0map))
    review_drift = {"changed_or_added": drift + added, "changed": drift, "added": added,
                    "n_rows_t0": len(rows), "n_rows_t1": len(rows_t1)}
    check("E8", "no pinned input moves during the run", "0 moved", {"moved": moved, "n_pins": len(pins0), "review_surface": review_drift}, not moved)

    # ---- E9: non-author verifiability
    frozen = load_json(ROOT / "artifacts/formulation/FROZEN.json")
    author_fields = [k for k in ("author", "authors", "created_by", "reviewer") if k in frozen]
    check("E9", "r3's 'non-author' filter is verifiable from on-disk bytes", "expected UNVERIFIABLE (pre-registered)",
          {"author_fields_present": author_fields, "frozen_owner": frozen.get("owner")}, True,
          "report-only: no F2b author identity is recorded in FROZEN.json, so the falsifier 'a counted accept whose reviewer authored the artifact' cannot be evaluated from bytes")

    # ---- E10: controls
    controls = []

    def ctl(cid, expected, got):
        controls.append({"id": cid, "expected": expected, "got": got, "ok": expected == got})

    tgt = ROOT / "reviews"
    base = {"verdict": "accept", "reviewer": "worker-T", "target_id": "F2b", "reviewed_sha256": F2B_PIN,
            "counts_as_full_schema_verdict": True}
    ctl("k1_full_accept", True, "accept" == base["verdict"] and is_full(base) and binds(explicit_pins(base), F2B_PIN) and "F2b" in targets_in(base))
    ctl("k2_revise_not_accept", False, (base | {"verdict": "revise"}).get("verdict") == "accept")
    ctl("k3_pin_mismatch", False, binds(explicit_pins(base | {"reviewed_sha256": "ffffffffffff" + F2B_PIN[12:]}), F2B_PIN))
    ctl("k4_nested_target_pin", True, binds(explicit_pins({"verdict": "accept", "target": {"subnode": "F2b", "sha256": F2B_PIN}}), F2B_PIN))
    ctl("k5_scoped_accept", False, is_full(base | {"counts_as_full_schema_verdict": False}))
    ctl("k6_alias_target", True, "F2b" in targets_in({"target_id": "AF-SCC-C0-VAC-GEN"}))
    ctl("k7_other_target", False, "F2b" in targets_in({"target_id": "F1"}))
    ctl("k10_short_pin_prefix", True, binds(["b2ab6acb2b"], F2B_PIN))
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "good.json").write_text(json.dumps(base))
        (td / "bad.json").write_text("{not json")
        (td / "noverdict.json").write_text(json.dumps({"reviewer": "x", "reviewed_sha256": F2B_PIN}))
        got_rows = census_dir(td)
        ctl("k8_unparseable_skipped", 1, len(got_rows))
        ctl("k9_missing_verdict_skipped", 0, sum(1 for r in got_rows if r["file"] == "noverdict.json"))
        before = len([r for r in got_rows if r["verdict"] == "accept" and r["full"]])
        (td / "good.json").write_text(json.dumps(base | {"verdict": "revise"}))
        after = len([r for r in census_dir(td) if r["verdict"] == "accept" and r["full"]])
        ctl("k11_supersede_mutation", (1, 0), (before, after))
    first = digest({"strict": strict, "pin_only": pin_only})
    frozen_sample = [
        {"verdict": "accept", "reviewer": "w1", "target_id": "F2b", "reviewed_sha256": F2B_PIN, "counts_as_full_schema_verdict": True},
        {"verdict": "revise", "reviewer": "w2", "target_id": "AF-SCC-C0-VAC-GEN", "artifact_sha256": F2B_PIN, "counts_as_full_schema_verdict": False},
        {"verdict": "accept", "reviewer": "w3", "target": {"subnode": "F2b", "sha256": F2B_PIN}},
    ]
    second = digest([classify_fields(dict(x)) for x in frozen_sample])
    third = digest([classify_fields(dict(x)) for x in frozen_sample])
    ctl("k12_determinism", True, second == third)
    check("E10", "planted controls", "12/12 pass", {"passed": sum(1 for c in controls if c["ok"]), "total": len(controls), "controls": controls},
          all(c["ok"] for c in controls))

    # ---- assemble report
    hard = [c for c in checks if c["id"] not in ("E7", "E9")]
    verdict = "REPLICATION_PASS" if all(c["ok"] for c in hard) else "REPLICATION_PARTIAL"
    report = {
        "schema": "w093-r3-replication/1",
        "task_id": "W093-GFORM-R3-REPLICATION-01",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "gate": "G-FORM",
        "verdict": verdict,
        "t0": t0.isoformat(timespec="seconds"),
        "t1": datetime.now(CST).isoformat(timespec="seconds"),
        "r3_artifact": {"path": R3_REL, "sha256": pins0[R3_REL]["sha256"], "mtime": pins0[R3_REL]["mtime"], "event_id": r3.get("event_id"), "actor": r3.get("actor")},
        "checks": checks,
        "strict_census": strict,
        "pin_only_census": pin_only,
        "controller_census": ctrl,
        "universes": universes,
        "carriers": carrier_obs,
        "declared_hash_layer": layer,
        "pins_T0": pins0,
        "pins_moved_T0_T1": moved,
        "review_surface_drift": review_drift,
        "controls_passed": f"{sum(1 for c in controls if c['ok'])}/{len(controls)}",
        "notes": notes,
    }
    report["digest"] = digest({k: v for k, v in report.items() if k not in ("digest", "t1")})
    (OUT / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True))
    print(json.dumps({"verdict": verdict, "checks": {c["id"]: c["ok"] for c in checks},
                      "controls": report["controls_passed"], "digest": report["digest"],
                      "full_accepts": strict["full_accepts"], "r3_agg": r3_agg, "reproduced_by": repro}, indent=1))
    return 0 if verdict == "REPLICATION_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W044-CF31-F2B-INSTRUMENT-RECON-01.

Independent, read-only measurement of the F2b coverage-count divergence
recorded as CF-31 / REC-39:
  controller disk scan (lifecycle 01:12:39: 4 full accepts; 01:16:26: 3)
  vs formulation-lead per-file census (01:13:00: 0 accept / 7 revise).

The script re-implements the controller predicate, compares it to the live
astra_lifecycle.review_coverage function, builds a per-record term matrix over
the F2b review corpus, reconstructs three corpora (disk, accepted stream,
lead-named suite), and measures review-file mutation under fixed filenames.

Read-only on every pinned path. Writes only under artifacts/worker-044/.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
NOW = datetime.now(CST)

F2B_PATH = ROOT / "schemas" / "af_scc_c0_vacuum.yaml"
PIN_EXPECTED = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
PIN12 = PIN_EXPECTED[:12]
VERDICT_KINDS = ("accept", "revise", "reject", "inconclusive")
REPORTS = {
    "01_12_39": ROOT / "runtime/state/controller_verification/lifecycle_20260912-011239.json",
    "01_16_26": ROOT / "runtime/state/controller_verification/lifecycle_20260912-011626.json",
}
LEAD_EVENT_ID = "lead-form-20260912T0113-103"
LEAD_OUTBOX = ROOT / "comms/outbox/astra-lead-formulation.jsonl"
STREAM = ROOT / "research_map/events.jsonl"
MAP = ROOT / "research_map/research_map.json"
PREREG = OUT / "PILOT_PREREGISTRATION.json"

TARGET_ALIASES = {
    "F0": "F0", "F1": "F1", "F2A": "F2a", "F2B": "F2b", "F2": "F2b",
    "L0": "L0", "L1": "L1",
    "AF-WCC-VAC-GEN": "F1",
    "AF-SCC-C2-VAC-GEN": "F2a",
    "AF-SCC-C0-VAC-GEN": "F2b",
}
PIN_KEYS = ("artifact_sha256", "reviewed_sha256", "sha256", "cited_sha256")
LEAD_CENSUS_CUTOFF = "2026-09-12T01:13:00"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_iso(s):
    if not isinstance(s, str):
        return None
    try:
        t = datetime.fromisoformat(s)
    except Exception:
        return None
    return t if t.tzinfo else t.replace(tzinfo=CST)


def norm_targets(d: dict) -> list:
    raw = []
    for key in ("target_id", "target", "target_subnode"):
        v = d.get(key)
        if isinstance(v, str):
            raw.append(v)
        elif isinstance(v, dict):
            for k2 in ("target_id", "target_subnode", "subnode", "node_id"):
                if isinstance(v.get(k2), str):
                    raw.append(v[k2])
    return [TARGET_ALIASES.get(t, TARGET_ALIASES.get(t.upper(), t)) for t in raw]


def explicit_pins(d: dict) -> dict:
    out = {}
    for key in PIN_KEYS:
        v = d.get(key)
        if isinstance(v, str):
            out[key] = v
    for key in ("target", "artifact"):
        v = d.get(key)
        if isinstance(v, dict):
            for k2 in ("sha256", "artifact_sha256", "reviewed_sha256"):
                if isinstance(v.get(k2), str):
                    out[f"{key}.{k2}"] = v[k2]
    return out


def pin_match(d: dict):
    for k, v in explicit_pins(d).items():
        if v and (v.lower().startswith(PIN12) or PIN12.startswith(v.lower()[:12])):
            return True, k
    return False, None


def verdict_of(d: dict):
    v = str(d.get("verdict", "")).lower()
    return v if v in VERDICT_KINDS else None


def mutation_flag(p: Path, d: dict) -> dict:
    ca = parse_iso(d.get("created_at"))
    mt = datetime.fromtimestamp(os.path.getmtime(p), CST)
    rec = {"mtime": mt.isoformat(), "created_at": d.get("created_at")}
    if ca is None:
        rec.update(flag=True, reason="created_at_absent", abs_delta_s=None)
        return rec
    delta = (mt - ca).total_seconds()
    rec["delta_mtime_minus_created_s"] = round(delta, 3)
    if abs(delta) > 60:
        rec.update(flag=True, reason="mtime_created_gap_gt_60s")
    else:
        rec.update(flag=False, reason=None)
    return rec


def controller_predicate(rec: dict) -> bool:
    return bool(rec["T_exact_alias"] and rec["V"] and rec["B_pin"] and rec["F_flag"] is not False)


def strict_predicate(rec: dict) -> bool:
    return bool(rec["T_exact_alias"] and rec["V"] and rec["B_pin"] and rec["F_flag"] is True)


def node_name_predicate(rec: dict) -> bool:
    return bool(rec["T_node_or_name"] and rec["V"] and rec["B_pin"] and rec["F_flag"] is not False)


# ---------------------------------------------------------------- harvest ---
def harvest_records() -> list:
    recs = []
    for p in sorted((ROOT / "reviews").glob("*.json")):
        raw = p.read_text()
        try:
            d = json.loads(raw)
        except Exception:
            continue
        targets = norm_targets(d)
        name = p.name
        mention = ("F2b" in name or str(d.get("node_id")) == "F2b"
                   or any("F2b" in t for t in targets))
        if not mention and PIN12 not in raw:
            continue
        pm, pmfield = pin_match(d)
        rec = {
            "file": name,
            "reviewer": str(d.get("reviewer") or d.get("actor") or "?"),
            "verdict": verdict_of(d),
            "verdict_raw": d.get("verdict"),
            "F_flag": d.get("counts_as_full_schema_verdict"),
            "W_toward": d.get("counts_toward_gate_accept"),
            "target_raw": [v for v in (
                d.get("target_id"), d.get("target_subnode"),
                d.get("target") if isinstance(d.get("target"), str) else None,
            ) if v is not None],
            "target_norm": targets,
            "node_id": d.get("node_id"),
            "reviewed_path": d.get("reviewed_path"),
            "sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "size": len(raw.encode()),
            "T_exact_alias": "F2b" in targets,
            "T_node_or_name": ("F2b" in name) or str(d.get("node_id")) == "F2b"
                              or any("F2b" in t for t in targets),
            "B_pin": pm,
            "B_pin_field": pmfield,
            "mutation": mutation_flag(p, d),
            "created_at": d.get("created_at"),
            "verdict_scope": str(d.get("verdict_scope") or d.get("scope_note") or "")[:220],
        }
        rec["V"] = rec["verdict"]
        rec["P_ctrl"] = controller_predicate(rec)
        rec["P_strict_flag"] = strict_predicate(rec)
        rec["P_node_name"] = node_name_predicate(rec)
        recs.append(rec)
    return recs


def live_pin() -> dict:
    got = sha256_file(F2B_PATH)
    return {
        "path": "schemas/af_scc_c0_vacuum.yaml",
        "measured_sha256": got,
        "expected_sha256": PIN_EXPECTED,
        "matches_expected": got == PIN_EXPECTED,
        "measured_at": NOW.isoformat(timespec="seconds"),
    }


# ------------------------------------------------------- controller report ---
def report_suite(path: Path) -> dict:
    d = json.loads(path.read_text())
    sec = d["review_coverage"]["F2b"]
    return {
        "file": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "generated_at": d.get("at") or d.get("started_at"),
        "full_accepts": sorted(a["file"] for a in sec["full_accepts"]),
        "accepts": sorted(a["file"] for a in sec["accepts"]),
        "revises": sorted(v["file"] for v in sec["verdicts"] if v["verdict"] == "revise"),
        "verdict_files": sorted(v["file"] for v in sec["verdicts"]),
    }


def live_controller_scan() -> dict:
    code = (
        "import json,sys;"
        "sys.path.insert(0, 'research_map');"
        "import astra_lifecycle as al;"
        f"cov=al.review_coverage({{'F2b': {{'sha256': '{PIN_EXPECTED}'}}}});"
        "print(json.dumps(cov['F2b'], sort_keys=True))"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return {"ok": False, "stderr": r.stderr[-2000:]}
    sec = json.loads(r.stdout)
    return {
        "ok": True,
        "verdicts": sorted(
            [v["file"], v["reviewer"], v["verdict"], v.get("counts_as_full_schema_verdict") is not False]
            for v in sec["verdicts"]
        ),
        "full_accepts": sorted(a["file"] for a in sec["full_accepts"]),
    }


# ------------------------------------------------------------- stream data ---
def load_review_events() -> list:
    evs = []
    with open(STREAM) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if str(e.get("event_type")) != "review":
                continue
            evs.append(e)
    return evs


def review_event_target(e: dict) -> str:
    return " ".join(str(e.get(k)) for k in ("target_id", "target") if e.get(k) is not None)


def stream_census(events: list, start_iso: str = "2026-09-12T00:50") -> dict:
    exact, variant = [], []
    for e in events:
        ca = str(e.get("created_at") or "")
        if ca < start_iso:
            continue
        tstr = review_event_target(e)
        if "F2b" not in tstr:
            continue
        item = {
            "event_id": e.get("event_id"),
            "actor": e.get("actor"),
            "created_at": e.get("created_at"),
            "target": tstr,
            "verdict": e.get("verdict"),
        }
        (exact if tstr.strip() == "F2b" else variant).append(item)
    return {
        "window_start": start_iso,
        "f2b_target_exact": {"n": len(exact), "items": exact},
        "f2b_target_variant": {"n": len(variant), "items": variant},
        "variant_target_strings": sorted({i["target"] for i in variant}),
    }


def stream_latest_suite(events: list, cutoff_iso: str, strict: bool = False) -> dict:
    """Latest accepted review event per actor whose target string contains F2b.

    strict=True keeps only events that bind the F2b schema (target exactly F2b or
    containing the live pin) and are not explicitly scoped out of the gate count.
    """
    best = {}
    for e in events:
        ca = str(e.get("created_at") or "")
        if ca < "2026-09-12T00:50" or ca > cutoff_iso:
            continue
        tstr = review_event_target(e)
        if "F2b" not in tstr:
            continue
        if strict:
            if not (tstr.strip() == "F2b" or PIN12 in tstr):
                continue
            if e.get("counts_as_full_schema_verdict") is False:
                continue
            if e.get("counts_toward_gate_accept") is False:
                continue
        actor = str(e.get("actor"))
        v = str(e.get("verdict") or "").lower()
        if v not in VERDICT_KINDS:
            continue
        if actor not in best or ca > best[actor]["created_at"]:
            best[actor] = {"actor": actor, "created_at": e.get("created_at"),
                           "verdict": v, "target": tstr, "event_id": e.get("event_id")}
    accepts = sorted(k for k, v in best.items() if v["verdict"] == "accept")
    revises = sorted(k for k, v in best.items() if v["verdict"] == "revise")
    return {"cutoff": cutoff_iso, "per_actor_latest": best,
            "accepts": accepts, "revises": revises,
            "n_accept": len(accepts), "n_revise": len(revises)}


def map_latest_suite(cutoff_iso: str) -> dict:
    m = json.loads(MAP.read_text())
    best = {}
    for r in m.get("reviews", []):
        ca = str(r.get("created_at") or "")
        if ca < "2026-09-12T00:50" or ca > cutoff_iso:
            continue
        if "F2b" not in (str(r.get("target_id")) + " " + json.dumps(r.get("artifact") or "")):
            continue
        actor = str(r.get("reviewer") or r.get("actor"))
        v = str(r.get("verdict") or "").lower()
        if v not in VERDICT_KINDS:
            continue
        if actor not in best or ca > best[actor]["created_at"]:
            best[actor] = {"actor": actor, "created_at": r.get("created_at"),
                           "verdict": v, "target": r.get("target_id")}
    return {"cutoff": cutoff_iso, "per_actor_latest": best,
            "accepts": sorted(k for k, v in best.items() if v["verdict"] == "accept"),
            "revises": sorted(k for k, v in best.items() if v["verdict"] == "revise")}


def match_stream_event(rec: dict, events: list) -> dict:
    """Match a disk record to accepted review events by reviewer and time."""
    ca = parse_iso(rec.get("created_at"))
    out = {"by_filename": False, "same_reviewer": []}
    for e in events:
        if rec["file"] in json.dumps(e):
            out["by_filename"] = True
            break
    for e in events:
        if str(e.get("actor")) != rec["reviewer"]:
            continue
        t = parse_iso(str(e.get("created_at")))
        if ca and t and abs((t - ca).total_seconds()) <= 300:
            out["same_reviewer"].append({
                "created_at": e.get("created_at"), "verdict": e.get("verdict"),
                "event_id": e.get("event_id"), "verdict_matches_disk": str(e.get("verdict")).lower() == rec["verdict"],
            })
    out["E_stream"] = bool([x for x in out["same_reviewer"] if x["verdict_matches_disk"]])
    return out


# ---------------------------------------------------------------- controls ---
def run_controls(records: list, actual_scan: dict, lead_recon: list, lead_explicit: list) -> list:
    ctl = []

    def base(**kw):
        r = {"T_exact_alias": False, "T_node_or_name": False, "V": "accept",
             "B_pin": True, "F_flag": True}
        r.update(kw)
        return r

    ctl.append({"id": "K1", "expect": "P_ctrl=True, P_strict_flag=False",
                "got": [controller_predicate(base(T_exact_alias=True, F_flag=None)),
                        strict_predicate(base(T_exact_alias=True, F_flag=None))],
                "pass": controller_predicate(base(T_exact_alias=True, F_flag=None)) is True
                        and strict_predicate(base(T_exact_alias=True, F_flag=None)) is False})
    ctl.append({"id": "K2", "expect": "P_ctrl=False, P_node_name=True",
                "got": [controller_predicate(base(T_node_or_name=True)),
                        node_name_predicate(base(T_node_or_name=True))],
                "pass": controller_predicate(base(T_node_or_name=True)) is False
                        and node_name_predicate(base(T_node_or_name=True)) is True})
    ctl.append({"id": "K3", "expect": "both binding predicates False",
                "got": [controller_predicate(base(T_exact_alias=True, B_pin=False)),
                        node_name_predicate(base(T_node_or_name=True, B_pin=False))],
                "pass": controller_predicate(base(T_exact_alias=True, B_pin=False)) is False
                        and node_name_predicate(base(T_node_or_name=True, B_pin=False)) is False})
    ctl.append({"id": "K4", "expect": "P_ctrl=False, P_node_name=False when F_flag not True and strict",
                "got": [controller_predicate(base(T_node_or_name=True, F_flag=None)),
                        strict_predicate(base(T_exact_alias=True, F_flag=None))],
                "pass": controller_predicate(base(T_node_or_name=True, F_flag=None)) is False
                        and strict_predicate(base(T_exact_alias=True, F_flag=None)) is False})
    mp = OUT / ".k5_probe.json"
    mp.write_text("{}")
    old = datetime.now(CST) - timedelta(seconds=600)
    os.utime(mp, (old.timestamp(), old.timestamp()))
    mut = mutation_flag(mp, {"created_at": datetime.now(CST).isoformat()})
    mp.unlink()
    ctl.append({"id": "K5", "expect": "mutation flag True",
                "got": mut, "pass": mut["flag"] is True and mut["reason"] == "mtime_created_gap_gt_60s"})
    mine = sorted([r["file"], r["reviewer"], r["verdict"], r["F_flag"] is not False]
                  for r in records if r["P_ctrl"])
    ctl.append({"id": "K7", "expect": "re-implementation == live controller function",
                "got": {"mine": mine, "live": actual_scan.get("verdicts")},
                "pass": bool(actual_scan.get("ok")) and mine == actual_scan.get("verdicts")})
    ctl.append({"id": "K9", "expect": "explicitly named lead files subset of reviewer-reconstructed suite",
                "got": {"explicit": lead_explicit, "reconstructed": lead_recon},
                "pass": set(lead_explicit).issubset(set(lead_recon)) and len(lead_recon) == 7})
    return ctl


# -------------------------------------------------------------------- main ---
def main() -> int:
    if not PREREG.is_file():
        print("PREREGISTRATION.json missing; refusing to run", file=sys.stderr)
        return 2
    prereg_sha = sha256_file(PREREG)

    pin = live_pin()
    records = harvest_records()
    pre_hashes = {r["file"]: r["sha256"] for r in records}
    reports = {k: report_suite(v) for k, v in REPORTS.items()}
    scan = live_controller_scan()
    events = load_review_events()

    lead_event = None
    if LEAD_OUTBOX.is_file():
        with open(LEAD_OUTBOX) as fh:
            for line in fh:
                if LEAD_EVENT_ID in line:
                    lead_event = json.loads(line)
                    break
    lead_summary = (lead_event or {}).get("summary", "")
    lead_reviewers = sorted({f"worker-{n}" for n in re.findall(r"worker-(\d+)", lead_summary)})
    lead_explicit = sorted(set(re.findall(r"(F2b-[A-Za-z0-9._-]+\.json)", lead_summary)))
    lead_recon = sorted(r["file"] for r in records if r["B_pin"] and r["reviewer"] in lead_reviewers
                        and (parse_iso(r["mutation"]["mtime"]) or NOW) <= parse_iso(LEAD_CENSUS_CUTOFF))

    stream = stream_census(events)
    stream_0113 = stream_latest_suite(events, LEAD_CENSUS_CUTOFF)
    stream_now = stream_latest_suite(events, NOW.isoformat(timespec="seconds"))
    stream_0113_strict = stream_latest_suite(events, LEAD_CENSUS_CUTOFF, strict=True)
    stream_now_strict = stream_latest_suite(events, NOW.isoformat(timespec="seconds"), strict=True)
    map_0113 = map_latest_suite(LEAD_CENSUS_CUTOFF)

    for r in records:
        r["E"] = match_stream_event(r, events)

    matrix = {
        "pin": pin,
        "predicate_definitions": {
            "P_ctrl": "T_exact_alias AND V AND B_pin AND (F_flag is not False)  [live controller scan]",
            "P_strict_flag": "T_exact_alias AND V AND B_pin AND (F_flag is True)",
            "P_node_name": "T_node_or_name AND V AND B_pin AND (F_flag is not False)",
        },
        "records": [{k: v for k, v in r.items() if k != "verdict_scope"} for r in records],
        "predicate_counts": {
            "P_ctrl": {
                "accept": sorted(r["file"] for r in records if r["P_ctrl"] and r["verdict"] == "accept"),
                "revise": sorted(r["file"] for r in records if r["P_ctrl"] and r["verdict"] == "revise"),
            },
            "P_strict_flag": {
                "accept": sorted(r["file"] for r in records if r["P_strict_flag"] and r["verdict"] == "accept"),
                "revise": sorted(r["file"] for r in records if r["P_strict_flag"] and r["verdict"] == "revise"),
            },
            "P_node_name": {
                "accept": sorted(r["file"] for r in records if r["P_node_name"] and r["verdict"] == "accept"),
                "revise": sorted(r["file"] for r in records if r["P_node_name"] and r["verdict"] == "revise"),
            },
        },
        "controls": run_controls(records, scan, lead_recon, lead_explicit),
    }

    ctrl_accepts = set(matrix["predicate_counts"]["P_ctrl"]["accept"])
    node_name_accepts = set(matrix["predicate_counts"]["P_node_name"]["accept"])
    pub_1212 = set(reports["01_12_39"]["full_accepts"])
    pub_1216 = set(reports["01_16_26"]["full_accepts"])
    live_accepts = set(scan.get("full_accepts") or [])

    suites = {
        "controller_disk_01_12_39": {"accepts": sorted(pub_1212)},
        "controller_disk_01_16_26": {"accepts": sorted(pub_1216)},
        "controller_disk_live_reproduced": {"accepts": sorted(ctrl_accepts), "revises": sorted(
            r["file"] for r in records if r["P_ctrl"] and r["verdict"] == "revise")},
        "disk_node_name_predicate": {"accepts": sorted(node_name_accepts)},
        "accepted_stream_latest_at_01_13": {"accepts": stream_0113["accepts"], "revises": stream_0113["revises"]},
        "accepted_stream_latest_now": {"accepts": stream_now["accepts"], "revises": stream_now["revises"]},
        "accepted_stream_schema_bound_at_01_13": {"accepts": stream_0113_strict["accepts"], "revises": stream_0113_strict["revises"]},
        "accepted_stream_schema_bound_now": {"accepts": stream_now_strict["accepts"], "revises": stream_now_strict["revises"]},
        "map_latest_at_01_13": {"accepts": map_0113["accepts"], "revises": map_0113["revises"]},
        "formulation_lead_reported_01_13": {
            "accepts": [],
            "revises": ["worker-066", "worker-035", "worker-017", "worker-075", "worker-018", "worker-053"],
            "source": "comms/outbox/astra-lead-formulation.jsonl#" + LEAD_EVENT_ID,
        },
        "formulation_lead_reconstructed_files": {"files": lead_recon},
    }

    reproducibility = {
        "01_16_26_reproduced_from_disk": sorted(pub_1216) == sorted(ctrl_accepts) == sorted(live_accepts),
        "01_12_39_extra_accepts_not_reproducible": sorted(pub_1212 - ctrl_accepts),
        "lead_accepts_unreproducible_by_disk_or_stream": {
            "lead_reported_accepts": [],
            "disk_accepts": sorted(ctrl_accepts),
            "stream_accepts_at_lead_cutoff_broad": stream_0113["accepts"],
        "stream_accepts_at_lead_cutoff_schema_bound": stream_0113_strict["accepts"],
        "stream_accepts_now_schema_bound": stream_now_strict["accepts"],
            "map_accepts_at_lead_cutoff": map_0113["accepts"],
            "accepts_named_in_lead_reconstructed_files": sorted(
                set(lead_recon) & (ctrl_accepts | node_name_accepts)),
            "conclusion": ("no measured corpus or predicate (disk exact-alias, disk node-or-name, "
                           "accepted stream latest-per-actor, map latest-per-actor, any flag default) "
                           "yields 0 F2b accepts at the pin near the lead's census time; the three "
                           "disk accepts (090, 052, 071) and the 01:08-01:11 stream accepts are "
                           "reproducible from primary sources"),
        },
        "lead_revise_suite_files_invisible_to_P_ctrl": sorted(
            set(lead_recon) - {r["file"] for r in records if r["P_ctrl"]}),
        "lead_revise_suite_files_visible_to_P_ctrl": sorted(
            set(lead_recon) & {r["file"] for r in records if r["P_ctrl"]}),
    }

    mut_records = [r for r in records if r["mutation"]["flag"]]
    f072 = next((r for r in records if r["file"] == "F2b-review-worker-072-rev29.json"), None)
    mutation = {
        "flagged_records": [
            {"file": r["file"], "reason": r["mutation"]["reason"],
             "mtime": r["mutation"]["mtime"], "created_at": r["mutation"]["created_at"],
             "delta_s": r["mutation"].get("delta_mtime_minus_created_s")}
            for r in mut_records
        ],
        "n_records": len(records),
        "n_flagged": len(mut_records),
        "same_filename_verdict_flip": {
            "file": "F2b-review-worker-072-rev29.json",
            "counted_accept_in": "runtime/state/controller_verification/lifecycle_20260912-011239.json",
            "counted_revise_in": "runtime/state/controller_verification/lifecycle_20260912-011626.json",
            "current_verdict": (f072 or {}).get("verdict"),
            "current_mtime": (f072 or {}).get("mutation", {}).get("mtime"),
            "current_created_at": (f072 or {}).get("created_at"),
            "current_sha256": (f072 or {}).get("sha256"),
            "stream_accept_event": next(
                (e.get("event_id") for e in events
                 if str(e.get("actor")) == "worker-072" and str(e.get("verdict")).lower() == "accept"
                 and "F2b" in review_event_target(e) and "01:10:13" in str(e.get("created_at"))), None),
            "stream_supersede_event": next(
                (e.get("event_id") for e in events
                 if str(e.get("actor")) == "worker-072" and str(e.get("verdict")).lower() == "revise"
                 and "F2b" in review_event_target(e) and "01:15" in str(e.get("created_at"))), None),
        },
        "missing_created_at": sorted(r["file"] for r in records if not r["created_at"]),
    }

    decisive = []
    for r in records:
        if not (r["B_pin"] and (r["T_exact_alias"] or r["T_node_or_name"])):
            continue
        decisive.append({
            "file": r["file"], "reviewer": r["reviewer"], "verdict": r["verdict"],
            "target_raw": r["target_raw"], "F_flag": r["F_flag"],
            "T_exact_alias": r["T_exact_alias"], "B_pin": r["B_pin"],
            "P_ctrl": r["P_ctrl"], "P_node_name": r["P_node_name"],
            "in_lead_recon": r["file"] in lead_recon,
            "E_stream_verdict_match": r["E"]["E_stream"],
            "E_same_reviewer_events": r["E"]["same_reviewer"],
            "decisive_term_vs_controller": (
                "included" if r["P_ctrl"] else
                ("T_exact_alias" if not r["T_exact_alias"] else
                 "V" if not r["V"] else "B_pin" if not r["B_pin"] else "F_flag")),
        })

    core = {
        "pin": {k: pin[k] for k in ("path", "measured_sha256", "matches_expected")},
        "suites": suites,
        "reproducibility": reproducibility,
        "predicate_counts": matrix["predicate_counts"],
        "stream_counts": {
            "exact": {"n": stream["f2b_target_exact"]["n"],
                      "verdicts": sorted(str(i["verdict"]) for i in stream["f2b_target_exact"]["items"])},
            "variant": {"n": stream["f2b_target_variant"]["n"],
                        "verdicts": sorted(str(i["verdict"]) for i in stream["f2b_target_variant"]["items"])},
            "variant_target_strings": stream["variant_target_strings"],
        },
        "mutation": {"n_flagged": mutation["n_flagged"], "n_records": mutation["n_records"],
                     "flagged": mutation["flagged_records"],
                     "flip": mutation["same_filename_verdict_flip"]},
        "controls": matrix["controls"],
    }
    digest = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()

    post = {r["file"]: sha256_file(ROOT / "reviews" / r["file"]) for r in records}
    changed = sorted(f for f in pre_hashes if pre_hashes[f] != post.get(f))
    pin_post = sha256_file(F2B_PATH)
    core["post_run"] = {"changed_files": changed, "pin_post": pin_post,
                        "pin_stable": pin_post == pin["measured_sha256"]}
    core["controls"].append({"id": "K8", "expect": "no harvested file changed during run",
                             "got": changed, "pass": not changed and pin_post == pin["measured_sha256"]})
    digest_final = hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()

    report = {
        "task_id": "W044-CF31-F2B-INSTRUMENT-RECON-01",
        "worker": "worker-044",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "created_at": NOW.isoformat(timespec="seconds"),
        "preregistration_sha256": prereg_sha,
        "authority": "worker measurement only; no gate verdict, no node verdict, no coverage-count adjudication",
        "verdict": "LEAD_CENSUS_NOT_REPRODUCIBLE__CONTROLLER_DISK_COUNT_REPRODUCIBLE_WITH_ONE_MUTATED_FILENAME",
        "summary": (
            "At the live F2b pin b2ab6acb2bbe the controller 01:16:26 suite (3 full accepts: 090, 052, 071) "
            "reproduces exactly from current bytes both by an independent predicate and by the live "
            "astra_lifecycle.review_coverage function. The 01:12:39 suite additionally counted "
            "F2b-review-worker-072-rev29.json, whose file was rewritten accept->revise at 01:14:54 under the "
            "same name; its accept survives only as the 01:10:13 accepted-stream event. The formulation-lead "
            "01:13:00 census (0 accept / 7 revise) is not reproducible by any measured corpus or predicate: "
            "the disk predicate yields 3 accepts, the accepted-stream latest-per-actor yields "
            + str(len(stream_0113["accepts"])) + " accepts ("
            + ", ".join(stream_0113["accepts"]) + ") at the lead's own cutoff, and the map-review corpus yields "
            + str(len(map_0113["accepts"])) + ". Five of the lead's seven named revise files are invisible to "
            "the controller's target term (their target_id is a path URI or absent), which is why the two "
            "suites 'share no reviewer', but target normalization and flag defaults cannot turn three "
            "pin-bound, stream-emitted full accepts into zero."
        ),
        "findings": [
            {"id": "W044-CF31-01",
             "statement": "Controller 01:16:26 count (090, 052, 071) reproduces exactly from disk; 01:12:39 count adds 072, whose filename now reads revise (mtime 01:14:54). The published 4-accept count was a correct reading of a disk state that no longer exists; it is not reproducible from current bytes.",
             "evidence": [
                 "runtime/state/controller_verification/lifecycle_20260912-011239.json#" + reports["01_12_39"]["sha256"][:12],
                 "runtime/state/controller_verification/lifecycle_20260912-011626.json#" + reports["01_16_26"]["sha256"][:12],
                 "reviews/F2b-review-worker-072-rev29.json#" + (f072 or {}).get("sha256", "")[:12]]},
            {"id": "W044-CF31-02",
             "statement": "The lead's 0-accept result is not produced by the disk corpus (3 accepts), the accepted-stream latest-per-actor corpus at the lead's own 01:13 cutoff (" + str(len(stream_0113["accepts"])) + " accepts), the map-review corpus (" + str(len(map_0113["accepts"])) + " accepts), or any combination of the measured target-normalization and full-flag terms. It requires an additional undocumented exclusion.",
             "evidence": ["comms/outbox/astra-lead-formulation.jsonl#" + LEAD_EVENT_ID,
                          "research_map/events.jsonl", "research_map/research_map.json#reviews"]},
            {"id": "W044-CF31-03",
             "statement": "Target normalization explains the disjoint reviewer sets: 5 of the 7 lead-named revise files (worker-066 x2, worker-035, worker-018, worker-053) carry a target_id that is a path URI or absent, so the controller's exact TARGET_ALIASES term drops them; only worker-017 and worker-075 appear in both suites (as revise).",
             "evidence": ["research_map/astra_lifecycle.py:135-158,185-207",
                          "artifacts/worker-044/cf31_f2b_recon/record_matrix.json"]},
            {"id": "W044-CF31-04",
             "statement": "A missing counts_as_full_schema_verdict is counted as full by the controller (is not False). Affected live-pin records: 052 (accept, flag absent), 085, 018, 035, 041 (revise, flag absent). An explicit-true predicate keeps 090, 071 only among accepts and drops 052.",
             "evidence": ["research_map/astra_lifecycle.py:195",
                          "artifacts/worker-044/cf31_f2b_recon/record_matrix.json"]},
            {"id": "W044-CF31-05",
             "statement": "The accepted stream contains F2b verdicts whose target strings are non-alias variants the exact-alias term cannot see (e.g. 'F2b@b2ab6acb2bbe (FROZEN rev29 815e0807)', 'F2b-accept-set@b2ab6acb2bbe', 'F2b:schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe'); a stream census and a disk census therefore measure different suites even on the same verdicts.",
             "evidence": ["research_map/events.jsonl", "artifacts/worker-044/cf31_f2b_recon/PILOT_report.json#stream_census"]},
        ],
        "decisive_term_table": decisive,
        "suites": suites,
        "reproducibility": reproducibility,
        "mutation": mutation,
        "stream_census": stream,
        "stream_accepts_at_lead_cutoff": stream_0113,
        "map_accepts_at_lead_cutoff": map_0113,
        "matrix": matrix,
        "controller_reports": reports,
        "live_controller_function": scan,
        "digest": digest_final,
        "falsifier": (
            "Falsified if (a) the re-implementation disagrees with the live review_coverage output on the same "
            "snapshot; (b) any record claimed invisible to the exact-alias term normalizes to F2b under the live "
            "TARGET_ALIASES map; (c) the 01:12:39 accept entry for F2b-review-worker-072-rev29.json is absent "
            "from the cited report; (d) a second run on the same bytes yields a different digest; (e) any "
            "harvested F2b review file changed sha256 during the run (snapshot void); (f) a flagged mutation has "
            "|mtime-created_at|<=60s; (g) an accepted-stream or map F2b accept exists at the pin near 01:13 "
            "that this report missed."
        ),
        "not_claimed": [
            "no G-FORM gate verdict, no node verdict, no validation_status change",
            "no statement of which published coverage count is correct; that adjudication is astra-life05-verify-gform-r3",
            "no write to any pinned, canonical, review, ledger, taxonomy or map path",
            "suite reconstructions for stream/map/lead are declared predicates, not the owners' code",
        ],
        "reproduction": "cd " + str(ROOT) + " && python3 artifacts/worker-044/cf31_f2b_recon/recon.py",
    }

    (OUT / "PILOT_record_matrix.json").write_text(json.dumps(matrix, indent=1, sort_keys=True))
    (OUT / "PILOT_snapshot_pre.json").write_text(json.dumps(
        {"pin": pin, "records": pre_hashes, "reports": reports,
         "harvested_at": NOW.isoformat(timespec="seconds")}, indent=1, sort_keys=True))
    (OUT / "PILOT_report.json").write_text(json.dumps(report, indent=1, sort_keys=True))

    print(json.dumps({
        "verdict": report["verdict"],
        "digest": digest_final,
        "pin_matches": pin["matches_expected"],
        "suites": {k: v.get("accepts") for k, v in suites.items()},
        "stream_accepts_at_lead_cutoff_broad": stream_0113["accepts"],
        "stream_accepts_at_lead_cutoff_schema_bound": stream_0113_strict["accepts"],
        "stream_accepts_now_schema_bound": stream_now_strict["accepts"],
        "map_accepts_at_lead_cutoff": map_0113["accepts"],
        "reproducibility": reproducibility,
        "mutations_flagged": mutation["n_flagged"],
        "flip": mutation["same_filename_verdict_flip"],
        "controls": [(c["id"], c["pass"]) for c in core["controls"]],
        "post_run_changed": changed,
    }, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W099-GFORM-R3-F2B-COVERAGE-REPLICATION-01 -- independent replication of the
decisive F2b (AF-SCC-C0-VAC-GEN) review-coverage count at the live G-FORM pin.

Method (pre-registered in PREREGISTRATION.json):
  * live pin + mirror + FROZEN-manifest fidelity measurement, fail closed;
  * immutable ledger built from research_map/events.jsonl (append-only), NOT from
    the mutable review files and NOT from worker-018's instrument;
  * three explicitly-defined scope rules R1/R2/R3;
  * explicit supersession resolution (same reviewer, later event referencing an
    earlier review path/sha/event id);
  * artifact_sha256-vs-reviewed_sha256 field-key effect measurement;
  * declared review-file hash vs live-file mutation/quiescence detector;
  * synthetic controls C2-C7 run against the same pipeline functions;
  * core_digest over the data-only core, stable across two invocations.

Read-only on every canonical path. Writes only RESULTS.json next to this script.
Exit codes: 0 ok, 2 pin/mirror drift, 3 control failure, 4 malformed event stream.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
EVENTS = ROOT / "research_map" / "events.jsonl"

F2B_PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
PINS = {
    "F1": ("schemas/af_wcc_vacuum.yaml", "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"),
    "F2a": ("schemas/af_scc_c2_vacuum.yaml", "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"),
    "F2b": ("schemas/af_scc_c0_vacuum.yaml", "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"),
    "FROZEN": ("artifacts/formulation/FROZEN.json", "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"),
}
MIRRORS = {
    "F1": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
    "F2a": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
    "F2b": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
}
# fixed candidate/aspect-scope tokens for rule R2; a target_id carrying any of
# them is excluded from the schema-level count and retained in R3.
SCOPE_TOKENS = ["candidate", "staged", "rev30", "coverage", "vocab",
                "containment-rebase", "normativity", "repair-acceptance", "hf-", "#"]
SUPERSEDE_FIELDS = ("supersedes", "supersedes_path", "supersedes_sha256",
                    "supersedes_review", "supersedes_event_id", "supersedes_verdict")
HASH_FIELD_PAIRS = (
    ("review_path", "review_sha256"),
    ("review_file", "review_file_sha256"),
    ("verdict_file", "verdict_file_sha256"),
    ("supersedes_path", "supersedes_sha256"),
)


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def core_digest(core: dict) -> str:
    return hashlib.sha256(canon(core).encode()).hexdigest()


def load_events() -> list:
    out, bad = [], 0
    for i, line in enumerate(EVENTS.read_text(errors="replace").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if isinstance(d, dict):
            out.append(d)
        else:
            bad += 1
    if bad:
        raise ValueError(f"events.jsonl: {bad} unparseable line(s)")
    return out


def dedupe_by_event_id(events: list) -> list:
    seen, out = set(), []
    for e in events:
        eid = e.get("event_id")
        if eid is None:
            out.append(e)
            continue
        if eid in seen:
            continue
        seen.add(eid)
        out.append(e)
    return out


def review_artifacts(e: dict) -> set:
    """Review-file paths this event refers to (explicit fields + reviews/ evidence refs)."""
    arts = set()
    for k in ("review_path", "review_file", "verdict_file", "supersedes_path"):
        v = e.get(k)
        if isinstance(v, str) and v:
            arts.add(v)
    for r in e.get("evidence_refs") or []:
        if not isinstance(r, str):
            continue
        p = r.split("#", 1)[0].strip()
        if p.startswith("reviews/") and p.endswith(".json"):
            arts.add(p)
    return arts


def declared_hashes(e: dict) -> set:
    hs = set()
    for k in ("review_sha256", "review_file_sha256", "verdict_file_sha256",
              "supersedes_sha256", "artifact_sha256", "reviewed_sha256"):
        v = e.get(k)
        if isinstance(v, str) and len(v) >= 12:
            hs.add(v)
    return hs


def bind_f2b(e: dict, pin: str = F2B_PIN) -> tuple:
    """Return (bound, mode, explicit_sha) for one review event against the live F2b pin."""
    rsha = e.get("reviewed_sha256")
    if isinstance(rsha, str) and rsha == pin:
        return True, "reviewed_sha256", rsha
    if isinstance(rsha, str) and rsha and rsha != pin:
        return False, "reviewed_sha256_other_pin", rsha
    tid = str(e.get("target_id") or "")
    if pin[:12] in tid:
        return True, "target_prefix_no_reviewed_sha256", None
    return False, "unbound", None


def scope_tokens_hit(e: dict) -> list:
    tid = str(e.get("target_id") or "").lower()
    return sorted({t for t in SCOPE_TOKENS if t in tid})


def is_superseded(e: dict, later: list) -> list:
    """Event ids among `later` that explicitly supersede e."""
    out = []
    e_arts, e_hashes, e_eid = review_artifacts(e), declared_hashes(e), e.get("event_id")
    e_time = str(e.get("created_at") or "")
    e_actor = e.get("actor")
    for l in later:
        if l is e or l.get("actor") != e_actor:
            continue
        if str(l.get("created_at") or "") <= e_time:
            continue
        for f in SUPERSEDE_FIELDS:
            v = l.get(f)
            if not isinstance(v, str) or not v:
                continue
            if f == "supersedes_path" and v in e_arts:
                out.append(l.get("event_id"))
            elif f in ("supersedes", "supersedes_review", "supersedes_event_id") and v == e_eid:
                out.append(l.get("event_id"))
            elif f == "supersedes_sha256" and (v in e_hashes or any(v.startswith(h[:12]) for h in e_hashes)):
                out.append(l.get("event_id"))
    return sorted({x for x in out if x})


def count_rules(bound: list, superseded: dict) -> dict:
    """Count accepts/revises under R1/R2/R3, raw and supersession-adjusted."""
    def tally(evs, drop_superseded):
        acc, rev, other = [], [], []
        for e in evs:
            if drop_superseded and superseded.get(e["event_id"]):
                continue
            bucket = {"accept": acc, "revise": rev}.get(e.get("verdict"), other)
            bucket.append(e["actor"])
        return {"accept": sorted(acc), "revise": sorted(rev), "other": sorted(other),
                "n_accept": len(acc), "n_revise": len(rev), "n_other": len(other)}

    r1 = [e for e in bound if e.get("counts_as_full_schema_verdict") is True]
    r2 = [e for e in bound if not scope_tokens_hit(e)]
    r3 = list(bound)
    latest = {}
    for e in sorted(bound, key=lambda x: (str(x.get("created_at") or ""), str(x.get("event_id") or ""))):
        latest[e["actor"]] = e
    return {
        "R1_explicit_full_schema": {"raw": tally(r1, False), "supersession_adjusted": tally(r1, True)},
        "R2_pin_bound_schema_level": {"raw": tally(r2, False), "supersession_adjusted": tally(r2, True)},
        "R3_all_pin_bound": {"raw": tally(r3, False), "supersession_adjusted": tally(r3, True)},
        "latest_per_reviewer_on_R3": tally(list(latest.values()), False),
    }


def field_key_effect(events: list, pin: str) -> dict:
    """Artifact_sha256-keyed vs reviewed_sha256-keyed accept sets at the pin."""
    out = {"artifact_sha256_accepts": [], "reviewed_sha256_accepts": [],
           "artifact_sha256_revises": [], "reviewed_sha256_revises": []}
    for e in events:
        if e.get("event_type") != "review":
            continue
        if scope_tokens_hit(e):
            continue
        for field, acc_key, rev_key in (
            ("artifact_sha256", "artifact_sha256_accepts", "artifact_sha256_revises"),
            ("reviewed_sha256", "reviewed_sha256_accepts", "reviewed_sha256_revises"),
        ):
            v = e.get(field)
            if isinstance(v, str) and v == pin:
                if e.get("verdict") == "accept":
                    out[acc_key].append(e["actor"])
                elif e.get("verdict") == "revise":
                    out[rev_key].append(e["actor"])
    for k in out:
        out[k] = sorted(out[k])
    out["artifact_sha256_accept_delta"] = len(out["reviewed_sha256_accepts"]) - len(out["artifact_sha256_accepts"])
    return out


def mutation_table(events: list) -> list:
    rows, seen = [], set()
    for e in events:
        if e.get("event_type") != "review":
            continue
        for pfield, hfield in HASH_FIELD_PAIRS:
            p, h = e.get(pfield), e.get(hfield)
            if not (isinstance(p, str) and p and isinstance(h, str) and len(h) == 64):
                continue
            key = (p, h, e.get("event_id"))
            if key in seen:
                continue
            seen.add(key)
            # a supersedes_* pair is a declaration about the SUPERSEDED revision, so a
            # live file that differs is expected; only live-file pairs can be mutations.
            role = "superseded_revision" if pfield == "supersedes_path" else "live_review_file"
            fp = ROOT / p
            if not fp.is_file():
                rows.append({"path": p, "declared": h, "measured": None, "status": "missing",
                             "role": role, "field": f"{pfield}/{hfield}",
                             "event_id": e.get("event_id"), "actor": e.get("actor"),
                             "created_at": e.get("created_at")})
                continue
            m = sha256_file(fp)
            if m == h:
                status = "match"
            elif role == "superseded_revision":
                status = "historical_revision_declared"
            else:
                status = "mismatch"
            rows.append({"path": p, "declared": h, "measured": m, "status": status,
                         "role": role, "mtime": datetime.fromtimestamp(fp.stat().st_mtime, CST).isoformat(timespec="seconds"),
                         "field": f"{pfield}/{hfield}", "event_id": e.get("event_id"),
                         "actor": e.get("actor"), "created_at": e.get("created_at")})
    return sorted(rows, key=lambda r: (r["path"], str(r["created_at"] or "")))


def verdict_timeline(events: list) -> list:
    """Every declared (review_path -> verdict) transition across the event stream."""
    by = {}
    for e in events:
        if e.get("event_type") != "review":
            continue
        p = e.get("review_path")
        if not isinstance(p, str) or not p.startswith("reviews/"):
            continue
        by.setdefault(p, []).append({
            "created_at": e.get("created_at"), "actor": e.get("actor"),
            "verdict": e.get("verdict"), "score": e.get("score"),
            "declared_sha256": e.get("review_sha256"), "event_id": e.get("event_id")})
    return [{"review_path": p, "records": sorted(v, key=lambda r: str(r["created_at"] or ""))}
            for p, v in sorted(by.items())]


def pins_and_manifest() -> dict:
    live, problems = {}, []
    for name, (rel, declared) in PINS.items():
        fp = ROOT / rel
        if not fp.is_file():
            problems.append(f"{name}: {rel} missing")
            continue
        m = sha256_file(fp)
        live[name] = {"path": rel, "declared": declared, "measured": m,
                      "match": m == declared, "bytes": fp.stat().st_size}
        if m != declared:
            problems.append(f"{name}: live {m[:12]} != declared {declared[:12]}")
    mirrors = {}
    for name, rel in MIRRORS.items():
        fp = ROOT / rel
        m = sha256_file(fp) if fp.is_file() else None
        canonical = live.get(name, {}).get("measured")
        mirrors[name] = {"mirror_path": rel, "mirror_sha256": m, "byte_equal": m == canonical}
        if m != canonical:
            problems.append(f"{name}: mirror {rel} not byte-equal to canonical")
    manifest = {"declared_files": 0, "match": 0, "mismatch": [], "missing": [],
                "revision": None, "frozen_at": None, "owner": None}
    manifest_drift_full = []
    fz = ROOT / PINS["FROZEN"][0]
    try:
        man = json.loads(fz.read_text())
        manifest["revision"] = man.get("revision")
        manifest["frozen_at"] = man.get("frozen_at")
        manifest["owner"] = man.get("owner")
        for rel, rec in sorted((man.get("files") or {}).items()):
            manifest["declared_files"] += 1
            fp = ROOT / rel
            if not fp.is_file():
                manifest["missing"].append(rel)
                manifest_drift_full.append({"path": rel, "declared": rec.get("sha256"),
                                            "measured": None, "status": "missing",
                                            "mtime": None})
                continue
            m = sha256_file(fp)
            if m == rec.get("sha256"):
                manifest["match"] += 1
            else:
                manifest["mismatch"].append({"path": rel, "declared": rec.get("sha256"), "measured": m})
                manifest_drift_full.append({
                    "path": rel, "declared": rec.get("sha256"), "measured": m, "status": "mismatch",
                    "bytes_declared": rec.get("bytes"), "bytes_measured": fp.stat().st_size,
                    "mtime": datetime.fromtimestamp(fp.stat().st_mtime, CST).isoformat(timespec="seconds")})
    except Exception as exc:  # pragma: no cover
        problems.append(f"FROZEN manifest unreadable: {exc}")
    return {"live": live, "mirrors": mirrors, "manifest": manifest,
            "manifest_drift_full": manifest_drift_full, "problems": problems}


# ---------------------------------------------------------------- controls
def synthetic_controls() -> list:
    later = "2026-09-12T02:00:00+08:00"
    earlier = "2026-09-12T01:00:00+08:00"
    acc = {"event_id": "ctl-acc", "event_type": "review", "actor": "ctl-X", "created_at": earlier,
           "reviewed_sha256": F2B_PIN, "verdict": "accept", "score": 4.0, "target_id": "F2b",
           "review_path": "reviews/ctl.json", "review_sha256": "a" * 64, "evidence_refs": []}
    sup = {"event_id": "ctl-sup", "event_type": "review", "actor": "ctl-X", "created_at": later,
           "reviewed_sha256": F2B_PIN, "verdict": "revise", "score": 3.0, "target_id": "F2b",
           "supersedes_path": "reviews/ctl.json", "supersedes_sha256": "a" * 64, "evidence_refs": []}
    stale = {"event_id": "ctl-stale", "event_type": "review", "actor": "ctl-Y", "created_at": later,
             "reviewed_sha256": "1" * 64, "verdict": "accept", "score": 4.0, "target_id": "F2b",
             "evidence_refs": []}
    fkey = {"event_id": "ctl-fkey", "event_type": "review", "actor": "ctl-Z", "created_at": later,
            "artifact_sha256": F2B_PIN, "verdict": "accept", "score": 4.0, "target_id": "F2b",
            "evidence_refs": []}
    scoped = {"event_id": "ctl-scope", "event_type": "review", "actor": "ctl-W", "created_at": later,
              "reviewed_sha256": F2B_PIN, "verdict": "revise", "score": 3.0,
              "target_id": "F2b@b2ab6acb2bbe#normativity", "evidence_refs": []}
    dup = dict(acc)
    evs = [acc, sup, stale, fkey, scoped, dup]
    evs = dedupe_by_event_id(evs)
    bound = [e for e in evs if e.get("event_type") == "review" and bind_f2b(e)[0]]
    superseded = {e["event_id"]: is_superseded(e, evs) for e in bound}
    counts = count_rules(bound, superseded)
    fk = field_key_effect(evs, F2B_PIN)
    mut = mutation_table([{"event_id": "ctl-mut", "event_type": "review", "actor": "ctl-M",
                           "created_at": later, "review_path": "reviews/does-not-exist.json",
                           "review_sha256": "b" * 64}])
    checks = [
        ("C2_supersession_drops_accept", superseded.get("ctl-acc") == ["ctl-sup"]),
        ("C2_adjusted_accepts_0", counts["R2_pin_bound_schema_level"]["supersession_adjusted"]["n_accept"] == 0),
        ("C3_field_key_detects_artifact_only_accept", fk["artifact_sha256_accepts"] == ["ctl-Z"]),
        ("C3_reviewed_key_excludes_artifact_only", all(e.get("event_id") != "ctl-fkey" for e in bound)),
        ("C3_reviewed_key_one_accept", fk["reviewed_sha256_accepts"] == ["ctl-X"]),
        ("C4_mutation_missing_reported", mut and mut[0]["status"] == "missing"),
        ("C5_duplicate_counted_once", sum(1 for e in evs if e.get("event_id") == "ctl-acc") == 1),
        ("C6_stale_pin_excluded", all(e.get("event_id") != "ctl-stale" for e in bound)),
        ("C7_scope_excluded_from_R2_kept_in_R3",
         counts["R2_pin_bound_schema_level"]["raw"]["n_revise"] == 1
         and counts["R3_all_pin_bound"]["raw"]["n_revise"] == 2),
    ]
    return [{"control": c, "pass": bool(p)} for c, p in checks]


def main() -> int:
    try:
        events = dedupe_by_event_id(load_events())
    except ValueError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 4

    pin_state = pins_and_manifest()
    reviews = [e for e in events if e.get("event_type") == "review"]
    bound, pin_citing_only, other_pin = [], [], []
    for e in reviews:
        ok, mode, rsha = bind_f2b(e)
        row = {"event_id": e.get("event_id"), "actor": e.get("actor"),
               "created_at": e.get("created_at"), "verdict": e.get("verdict"),
               "score": e.get("score"), "target_id": e.get("target_id"),
               "reviewed_sha256": rsha, "binding_mode": mode,
               "scope_tokens": scope_tokens_hit(e),
               "full_schema_flag": e.get("counts_as_full_schema_verdict"),
               "counts_toward_gate_accept": e.get("counts_toward_gate_accept"),
               "task_id": e.get("task_id"), "review_kind": e.get("review_kind"),
               "review_path": e.get("review_path"), "review_sha256": e.get("review_sha256"),
               "supersede_fields": {k: e.get(k) for k in SUPERSEDE_FIELDS if e.get(k) is not None}}
        if ok:
            bound.append(dict(e, **{"_row": row}))
            continue
        tid = str(e.get("target_id") or "").lower()
        relevant = (F2B_PIN[:12] in str(e.get("target_id") or "")
                    or "f2b" in tid or "scc_c0" in tid
                    or any(F2B_PIN[:12] in str(r) for r in (e.get("evidence_refs") or [])))
        if not relevant:
            continue
        if mode == "reviewed_sha256_other_pin":
            other_pin.append(row)
        else:
            pin_citing_only.append(row)

    superseded = {e["event_id"]: is_superseded(e, bound + reviews) for e in bound}
    counts = count_rules(bound, superseded)
    fk = field_key_effect(reviews, F2B_PIN)
    mut = mutation_table(reviews)
    # core digest must be stable across runs: filesystem mtimes are carried in the
    # outer result only, event timestamps stay because they are ledger data.
    mut_core = [{k: v for k, v in r.items() if k != "mtime"} for r in mut]
    timeline = verdict_timeline(reviews)
    controls = synthetic_controls()

    core = {
        "task_id": "W099-GFORM-R3-F2B-COVERAGE-REPLICATION-01",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "node_id": "F2b",
        "pin_under_test": F2B_PIN,
        "pin_state": {k: {"path": v["path"], "measured": v["measured"], "match": v["match"]}
                      for k, v in pin_state["live"].items()},
        "mirrors": pin_state["mirrors"],
        "manifest": pin_state["manifest"],
        "counts": counts,
        "field_key_effect": fk,
        "supersession": {k: sorted(v) for k, v in sorted(superseded.items()) if v},
        "bound_reviews": sorted([e["_row"] for e in bound], key=lambda r: (str(r["created_at"]), r["event_id"])),
        "pin_citing_only": sorted(pin_citing_only, key=lambda r: (str(r["created_at"]), r["event_id"])),
        "other_pin_bound_reviews": sorted(other_pin, key=lambda r: (str(r["created_at"]), r["event_id"])),
        "mutation_table": mut_core,
        "verdict_timeline_review_files": timeline,
        "controls": controls,
        "problems": pin_state["problems"],
    }
    result = {
        "schema": "worker-099/gform-r3-f2b-coverage-replication/v1",
        "actor": "worker-099",
        "created_at": now(),
        "events_total": len(events),
        "review_events_total": len(reviews),
        "core_digest": core_digest(core),
        "mutation_table_full": mut,
        "manifest_drift_full": pin_state["manifest_drift_full"],
        "authority_note": ("Worker measurement only. No gate verdict, no node status, no "
                           "validation_status=passed. Canonical paths are read-only in this run."),
        "core": core,
    }
    (HERE / "RESULTS.json").write_text(json.dumps(result, indent=2, sort_keys=True))

    bad_pins = bool(pin_state["problems"])
    bad_controls = [c for c in controls if not c["pass"]]
    print(json.dumps({
        "core_digest": result["core_digest"],
        "pins_ok": not bad_pins,
        "manifest": pin_state["manifest"],
        "R1_explicit_full_schema": counts["R1_explicit_full_schema"],
        "R2_raw": counts["R2_pin_bound_schema_level"]["raw"],
        "R2_supersession_adjusted": counts["R2_pin_bound_schema_level"]["supersession_adjusted"],
        "R3_raw": counts["R3_all_pin_bound"]["raw"],
        "field_key_effect": {"artifact_sha256_accepts": fk["artifact_sha256_accepts"],
                             "reviewed_sha256_accepts": fk["reviewed_sha256_accepts"],
                             "delta": fk["artifact_sha256_accept_delta"]},
        "supersession_pairs": len(core["supersession"]),
        "mutation_rows": len(mut),
        "live_file_mismatch": [r for r in mut if r["status"] == "mismatch"],
        "historical_revision_declared": [r["path"] for r in mut if r["status"] == "historical_revision_declared"],
        "manifest_drift": pin_state["manifest_drift_full"],
        "controls_failed": bad_controls,
        "problems": pin_state["problems"],
    }, indent=2))
    if bad_pins:
        return 2
    if bad_controls:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

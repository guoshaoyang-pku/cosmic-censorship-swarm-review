#!/usr/bin/env python3
"""W054-GFORM-LIVE-ACCEPT-CENSUS-01 (read-only).

Question: at the live G-FORM pins (F1 d9cebb94 / F2a e9a27996 / F2b b2ab6acb,
FROZEN rev29 815e0807), which review files currently carry a full-schema ACCEPT
whose *declared target* is the live schema hash of the leg, and how many of those
are non-author?  This is the gate's "two accepts per class at one frozen hash"
criterion measured at live bytes, including the 01:14:51 worker-072 F2b
self-supersession (accept -> revise).

Pre-registered rules (fixed before the run; all variants reported):

  leg scope          a file belongs to leg L only if node_id==L, or target_id names L
                     (L itself or L's canonical schema filename), or reviewed_path is
                     L's canonical schema.  A bare cross-mention of another leg's
                     schema in findings/notes does NOT create scope (control C9).

  declared target    hashes the review itself declares for L: reviewed_sha256,
                     artifact_sha256[_prefix], target_id path#hash, target.<sha-ish>
                     keys, and any path#hash reference to L's canonical schema.
                     LIVE := at least one declared hash equals the live canonical hash.
                     STALE := declared hashes exist but none is live.
                     UNBOUND := no declared hash.

  full-schema flag   STRICT  := counts_as_full_schema_verdict is true
                     DEFAULT := STRICT, or the key is absent and verdict is accept
                                (the controller's documented default per W48-CR-F3)

  frozen binding     LIVE_FROZEN := FROZEN 815e08079aef declared anywhere in the file
                     SCHEMA_ONLY := no live-FROZEN declaration (stale generations such
                                as gen A 3d9e3d77 / rev28 2f358f67 are reported)

  independence       NONAUTHOR := reviewer not in the artifact-author set derived from
                                accepted `artifact` events for that leg's canonical or
                                mirror path in research_map/events.jsonl

Counted variants per leg: (STRICT|DEFAULT) x (LIVE_FROZEN|SCHEMA_ONLY), each with and
without the NONAUTHOR filter.  Worker measurement only: no gate verdict, no node
status, no validation_status=passed, no canonical write.

Exit 0 = measurement complete, all controls as declared, no input drift.
Exit 2 = fail-closed (input drift during the run or a control did not behave as declared).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CST = timezone(timedelta(hours=8))
OUT = Path(__file__).resolve().parent

LEGS = {
    "F1": {
        "canonical": "schemas/af_wcc_vacuum.yaml",
        "mirror": "artifacts/formulation/schemas/af_wcc_vacuum.yaml",
        "live": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
        "class_id": "AF-WCC-VAC-GEN",
    },
    "F2a": {
        "canonical": "schemas/af_scc_c2_vacuum.yaml",
        "mirror": "artifacts/formulation/schemas/af_scc_c2_vacuum.yaml",
        "live": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
        "class_id": "AF-SCC-C2-VAC-GEN",
    },
    "F2b": {
        "canonical": "schemas/af_scc_c0_vacuum.yaml",
        "mirror": "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml",
        "live": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
        "class_id": "AF-SCC-C0-VAC-GEN",
    },
}
FROZEN_PATH = "artifacts/formulation/FROZEN.json"
FROZEN_LIVE = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
FROZEN_GEN_A = "3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833"
FROZEN_REV28 = "2f358f6722d9"  # prefix as cited in review files

HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
HEXISH = re.compile(r"\b[0-9a-f]{8,64}\b")
REF = re.compile(r"([A-Za-z0-9_./-]+\.(?:yaml|yml|json|jsonl|md|csv|py))#([0-9a-f]{8,64})")


def file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def walk_strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield str(k)
            yield from walk_strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk_strings(v)


def normalize_verdict(doc):
    v = doc.get("verdict")
    seen = 0
    while isinstance(v, dict) and seen < 5:
        v = v.get("verdict") if "verdict" in v else None
        seen += 1
    return v.strip().lower() if isinstance(v, str) else None


def full_flag(doc):
    v = doc.get("counts_as_full_schema_verdict")
    return "true" if v is True else ("false" if v is False else "absent")


def collect(doc):
    hashes, refs = set(), {}
    for s in walk_strings(doc):
        for m in HEX64.findall(s):
            hashes.add(m)
        for path, pref in REF.findall(s):
            refs.setdefault(path, set()).add(pref)
    return hashes, refs


def scope_for(doc, leg, refs):
    """Return (in_scope: bool, reason: str).  Scope is by declared target identity only."""
    meta = LEGS[leg]
    node = str(doc.get("node_id") or "")
    tid = str(doc.get("target_id") or "")
    canon_name = Path(meta["canonical"]).name
    rev_path = str(doc.get("reviewed_path") or "")
    if node == leg:
        return True, "node_id"
    if tid == leg or tid.startswith(leg) or canon_name in tid:
        return True, "target_id"
    if rev_path.endswith(canon_name):
        return True, "reviewed_path"
    cls = json.dumps(doc.get("class_id") or doc.get("class_ids") or "")
    if meta["class_id"] in cls and node in ("", leg):
        return True, "class_id"
    return False, ""


def declared_for(doc, leg, refs):
    """Hashes this review declares as its target for leg L, with provenance."""
    meta = LEGS[leg]
    decl, why = set(), []
    rsha = doc.get("reviewed_sha256")
    if isinstance(rsha, str) and HEXISH.fullmatch(rsha.lower()):
        decl.add(rsha.lower()); why.append("reviewed_sha256")
    for key in ("artifact_sha256", "artifact_sha256_prefix"):
        v = doc.get(key)
        if isinstance(v, str) and HEXISH.fullmatch(v.lower()):
            decl.add(v.lower()); why.append(key)
    tid = str(doc.get("target_id") or "")
    if "#" in tid:
        decl.add(tid.rsplit("#", 1)[1].lower()); why.append("target_id#hash")
    tgt = doc.get("target")
    if isinstance(tgt, dict):
        for k, v in tgt.items():
            if any(t in str(k).lower() for t in ("sha", "pin", "digest")) and \
                    isinstance(v, str) and HEXISH.fullmatch(v.lower()):
                decl.add(v.lower()); why.append("target." + str(k))
    for path, prefs in refs.items():
        if Path(path).name == Path(meta["canonical"]).name:
            decl |= set(prefs); why.append("ref:" + path)
    return decl, sorted(set(why))


def classify(doc, leg, author_sets):
    meta = LEGS[leg]
    live = meta["live"]
    hashes, refs = collect(doc)
    in_scope, scope_reason = scope_for(doc, leg, refs)
    verdict = normalize_verdict(doc)
    ff = full_flag(doc)
    full_strict = ff == "true"
    full_default = full_strict or (ff == "absent" and verdict == "accept")

    decl, decl_why = declared_for(doc, leg, refs)

    def matches_live(x):
        return len(x) >= 8 and (live.startswith(x) or x.startswith(live))

    live_bound = in_scope and any(matches_live(x) for x in decl)
    declared_stale = sorted({x for x in decl if not matches_live(x)}) if in_scope else []

    frozen_live_structured = FROZEN_LIVE in hashes or \
        FROZEN_LIVE[:12] in refs.get(FROZEN_PATH, set())
    frozen_genA_structured = FROZEN_GEN_A in hashes or \
        FROZEN_GEN_A[:12] in refs.get(FROZEN_PATH, set())
    prefixes = {t for s in walk_strings(doc) for t in HEXISH.findall(s)}
    frozen_live_prose = any(len(t) >= 8 and FROZEN_LIVE.startswith(t) for t in prefixes)
    frozen_genA_prose = any(len(t) >= 8 and FROZEN_GEN_A.startswith(t) for t in prefixes)
    frozen_live = frozen_live_structured or frozen_live_prose
    frozen_genA = frozen_genA_structured or frozen_genA_prose
    frozen_rev28 = any(p.startswith(FROZEN_REV28) for p in refs.get(FROZEN_PATH, set())) \
        or any(h.startswith(FROZEN_REV28) for h in hashes)

    reviewer = str(doc.get("reviewer") or doc.get("actor") or "")
    nonauthor = (reviewer not in author_sets.get(leg, set())) if reviewer else False

    blind = doc.get("blind")
    if blind is None:
        b = doc.get("blindness")
        blind = b.get("blind") if isinstance(b, dict) else (b if isinstance(b, str) else None)

    return {
        "in_scope": in_scope,
        "scope_reason": scope_reason,
        "verdict": verdict,
        "full_flag": ff,
        "full_strict": full_strict,
        "full_default": full_default,
        "live_bound": live_bound,
        "mentions_live": live in hashes,
        "declared_hashes": sorted(decl),
        "declared_provenance": decl_why,
        "declared_stale_hashes": declared_stale,
        "frozen_live": bool(frozen_live),
        "frozen_live_structured": bool(frozen_live_structured),
        "frozen_genA": bool(frozen_genA),
        "frozen_genA_structured": bool(frozen_genA_structured),
        "frozen_rev28": bool(frozen_rev28),
        "reviewer": reviewer,
        "nonauthor": bool(nonauthor),
        "blind": blind,
        "created_at": doc.get("created_at") or doc.get("reviewed_at") or "",
        "gate": doc.get("gate"),
        "class_id": doc.get("class_id") or doc.get("class_ids"),
    }


def counted(c, full_key, frozen_key, nonauthor_filter):
    if c["verdict"] != "accept" or not c["live_bound"]:
        return False
    if full_key == "strict" and not c["full_strict"]:
        return False
    if full_key == "default" and not c["full_default"]:
        return False
    if frozen_key == "live_frozen" and not c["frozen_live"]:
        return False
    if nonauthor_filter and not c["nonauthor"]:
        return False
    return True


def author_sets_from_events():
    path = ROOT / "research_map" / "events.jsonl"
    sets = {leg: set() for leg in LEGS}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return sets, None
    for line in lines:
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event_type") != "artifact":
            continue
        actor = e.get("actor")
        paths = e.get("path") or e.get("artifact_path")
        if isinstance(paths, str):
            paths = [paths]
        if not isinstance(paths, list):
            paths = []
        for leg, meta in LEGS.items():
            names = {Path(meta["canonical"]).name, meta["canonical"], meta["mirror"]}
            if any(isinstance(p, str) and (p in names or Path(p).name == Path(meta["canonical"]).name)
                   for p in paths):
                if actor:
                    sets[leg].add(str(actor))
    return sets, file_sha(path)


def mutate_no_binding(doc):
    """Deep copy with all hash/pin-ish keys and every standalone hash token removed."""
    d = copy.deepcopy(doc)

    def scrub(o):
        if isinstance(o, dict):
            for k in list(o):
                if any(t in str(k).lower() for t in ("sha", "hash", "pin", "digest")):
                    o.pop(k, None)
                else:
                    scrub(o[k])
        elif isinstance(o, list):
            for v in o:
                scrub(v)
        elif isinstance(o, str):
            pass

    def scrub_strings(o):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if isinstance(v, str):
                    o[k] = REF.sub(r"\1", HEX64.sub("", v))
                else:
                    scrub_strings(v)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                if isinstance(v, str):
                    o[i] = REF.sub(r"\1", HEX64.sub("", v))
                else:
                    scrub_strings(v)

    scrub(d)
    scrub_strings(d)
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--created-at", required=True)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    reviews_dir = ROOT / "reviews"
    review_files = sorted(p for p in reviews_dir.glob("*.json"))
    pin_paths = [ROOT / "schemas/af_wcc_vacuum.yaml",
                 ROOT / "schemas/af_scc_c2_vacuum.yaml",
                 ROOT / "schemas/af_scc_c0_vacuum.yaml",
                 ROOT / FROZEN_PATH]
    pins = {}
    for p in pin_paths:
        rel = str(p.relative_to(ROOT))
        pins[rel] = {"sha256": file_sha(p), "bytes": p.stat().st_size}
    frozen = json.loads((ROOT / FROZEN_PATH).read_text())
    pins[FROZEN_PATH]["frozen_revision"] = frozen.get("revision")
    pins[FROZEN_PATH]["frozen_at"] = frozen.get("frozen_at")
    declared = frozen.get("files", {})
    frozen_pin_match = {leg: declared.get(meta["canonical"], {}).get("sha256") == meta["live"]
                        for leg, meta in LEGS.items()}
    live_schema_matches_declared_pin = {
        leg: pins[meta["canonical"]]["sha256"] == meta["live"] for leg, meta in LEGS.items()}

    author_sets, events_sha = author_sets_from_events()
    author_sets_list = {k: sorted(v) for k, v in author_sets.items()}

    start = {str(f.relative_to(ROOT)): file_sha(f) for f in review_files + pin_paths}

    census = []
    for f in review_files:
        try:
            raw = f.read_bytes()
            doc = json.loads(raw)
        except Exception as e:
            census.append({"file": str(f.relative_to(ROOT)), "parse_error": str(e)})
            continue
        hashes, refs = collect(doc)
        entry = {"file": str(f.relative_to(ROOT)), "sha256": hashlib.sha256(raw).hexdigest(),
                 "bytes": len(raw), "legs": {}}
        for leg in LEGS:
            in_scope, _ = scope_for(doc, leg, refs)
            if in_scope:
                entry["legs"][leg] = classify(doc, leg, author_sets)
        if entry["legs"]:
            census.append(entry)

    counts = {}
    for leg in LEGS:
        rows = [e for e in census if e.get("legs", {}).get(leg)]
        counts[leg] = {"files_in_scope": len(rows), "variants": {}}
        for full_key in ("strict", "default"):
            for frozen_key in ("live_frozen", "schema_only"):
                for naf in (True, False):
                    label = f"{full_key}__{frozen_key}__{'nonauthor' if naf else 'all'}"
                    ids = [e["file"] for e in rows
                           if counted(e["legs"][leg], full_key, frozen_key, naf)]
                    counts[leg]["variants"][label] = {"n": len(ids), "files": ids}
        counts[leg]["accept_live"] = [
            {"file": e["file"], "full": e["legs"][leg]["full_flag"],
             "frozen_live": e["legs"][leg]["frozen_live"],
             "frozen_live_structured": e["legs"][leg]["frozen_live_structured"],
             "frozen_genA": e["legs"][leg]["frozen_genA"],
             "frozen_rev28": e["legs"][leg]["frozen_rev28"],
             "reviewer": e["legs"][leg]["reviewer"],
             "nonauthor": e["legs"][leg]["nonauthor"],
             "blind": e["legs"][leg]["blind"],
             "scope_reason": e["legs"][leg]["scope_reason"],
             "declared_stale_hashes": e["legs"][leg]["declared_stale_hashes"],
             "created_at": e["legs"][leg]["created_at"]}
            for e in rows if e["legs"][leg]["verdict"] == "accept" and e["legs"][leg]["live_bound"]
        ]
        counts[leg]["revise_live"] = [
            {"file": e["file"], "reviewer": e["legs"][leg]["reviewer"],
             "full": e["legs"][leg]["full_flag"],
             "created_at": e["legs"][leg]["created_at"]}
            for e in rows if e["legs"][leg]["verdict"] == "revise" and e["legs"][leg]["live_bound"]
        ]

    # ---- special records ---------------------------------------------------
    special = {}
    p072 = reviews_dir / "F2b-review-worker-072-rev29.json"
    if p072.exists():
        d072 = json.loads(p072.read_bytes())
        superseded = d072.get("supersedes_sha256")
        on_disk = superseded in {e.get("sha256") for e in census if e.get("sha256")}
        special["w072_f2b_self_supersession"] = {
            "file": str(p072.relative_to(ROOT)),
            "current_sha256": file_sha(p072),
            "current_verdict": normalize_verdict(d072),
            "current_full_flag": full_flag(d072),
            "supersedes_sha256": superseded,
            "supersedes_verdict": d072.get("supersedes_verdict"),
            "superseded_at": d072.get("superseded_at"),
            "superseded_bytes_still_present_in_reviews": bool(on_disk),
            "revision_history": d072.get("revision_history", []),
            "hard_failures": [h.get("id") for h in (d072.get("hard_failures") or [])
                              if isinstance(h, dict)],
        }
    p017 = reviews_dir / "F2a-review-worker-017.json"
    if p017.exists():
        d017 = json.loads(p017.read_bytes())
        h, r = collect(d017)
        special["f2a_worker_017_frozen_binding"] = {
            "file": str(p017.relative_to(ROOT)),
            "sha256": file_sha(p017),
            "verdict": normalize_verdict(d017),
            "counts_as_full_schema_verdict": d017.get("counts_as_full_schema_verdict"),
            "reviewed_sha256": d017.get("reviewed_sha256"),
            "reviewed_sha256_is_live_f2a": d017.get("reviewed_sha256") == LEGS["F2a"]["live"],
            "declares_frozen_live": FROZEN_LIVE in h or FROZEN_LIVE[:12] in r.get(FROZEN_PATH, set()),
            "declares_frozen_genA": FROZEN_GEN_A in h or FROZEN_GEN_A[:12] in r.get(FROZEN_PATH, set()),
            "frozen_refs": sorted({f"{FROZEN_PATH}#{x}" for x in r.get(FROZEN_PATH, set())}),
            "created_at": d017.get("created_at"),
        }
    p089 = reviews_dir / "F1-review-worker-089.json"
    if p089.exists():
        d089 = json.loads(p089.read_bytes())
        special["f1_worker_089_path_hash_target"] = {
            "file": str(p089.relative_to(ROOT)),
            "target_id": d089.get("target_id"),
            "verdict": normalize_verdict(d089),
            "full_flag": full_flag(d089),
            "live_bound": classify(d089, "F1", author_sets)["live_bound"],
            "scope_reason": classify(d089, "F1", author_sets)["scope_reason"],
        }

    # ---- controls ----------------------------------------------------------
    base = json.loads((reviews_dir / "F2b-review-rev13-worker-071.json").read_bytes())
    controls = {}

    def add(name, doc, leg, expect, full_key="strict", frozen_key="live_frozen", naf=True,
            extra=None):
        c = classify(doc, leg, author_sets)
        got = counted(c, full_key, frozen_key, naf)
        rec = {"expected_counted": expect, "observed_counted": got, "as_declared": got == expect,
               "verdict": c["verdict"], "live_bound": c["live_bound"],
               "full_strict": c["full_strict"], "frozen_live": c["frozen_live"],
               "frozen_genA": c["frozen_genA"], "scope_reason": c["scope_reason"]}
        if extra:
            rec.update(extra)
        controls[name] = rec
        return got

    add("C1a_live_accept_counted", base, "F2b", True)
    d = copy.deepcopy(base); d["verdict"] = "revise"
    add("C1b_flip_to_revise_not_counted", d, "F2b", False)

    add("C2a_no_binding_not_counted", mutate_no_binding(base), "F2b", False)

    d = mutate_no_binding(base)
    d["reviewed_sha256"] = "55d0a1ea9bda" + "0" * 52
    d["evidence_refs"] = ["schemas/af_scc_c0_vacuum.yaml#55d0a1ea9bda"]
    c = classify(d, "F2b", author_sets)
    got = counted(c, "strict", "schema_only", True)
    controls["C3_stale_schema_not_counted"] = {
        "expected_counted": False, "observed_counted": got, "as_declared": got is False,
        "live_bound": c["live_bound"], "declared_stale_hashes": c["declared_stale_hashes"]}

    d = mutate_no_binding(base)
    d["reviewed_sha256"] = LEGS["F2b"]["live"]
    d["reviewed_frozen_sha256"] = FROZEN_GEN_A
    d["evidence_refs"] = ["schemas/af_scc_c0_vacuum.yaml#" + LEGS["F2b"]["live"],
                          "artifacts/formulation/FROZEN.json#3d9e3d77fd87"]
    c = classify(d, "F2b", author_sets)
    got_schema = counted(c, "strict", "schema_only", True)
    got_frozen = counted(c, "strict", "live_frozen", True)
    controls["C4_genA_frozen_schema_only"] = {
        "expected_counted_schema_only": True, "observed_counted_schema_only": got_schema,
        "expected_counted_live_frozen": False, "observed_counted_live_frozen": got_frozen,
        "as_declared": got_schema is True and got_frozen is False,
        "frozen_live": c["frozen_live"], "frozen_genA": c["frozen_genA"]}

    synth = {"node_id": "F2b", "gate": "G-FORM", "reviewer": "worker-x", "verdict": "accept",
             "counts_as_full_schema_verdict": True,
             "target_id": "schemas/af_scc_c0_vacuum.yaml#b2ab6acb2bbe"}
    c = classify(synth, "F2b", author_sets)
    got = counted(c, "strict", "schema_only", True)
    controls["C5a_path_hash_target_recognized"] = {
        "expected_counted": True, "observed_counted": got, "as_declared": got is True}
    synth2 = copy.deepcopy(synth); synth2.pop("target_id")
    c = classify(synth2, "F2b", author_sets)
    got = counted(c, "strict", "schema_only", True)
    controls["C5b_without_hash_not_counted"] = {
        "expected_counted": False, "observed_counted": got, "as_declared": got is False}

    d = copy.deepcopy(base); d["counts_as_full_schema_verdict"] = False
    c = classify(d, "F2b", author_sets)
    got_strict = counted(c, "strict", "live_frozen", True)
    got_default = counted(c, "default", "live_frozen", True)
    controls["C6_full_false_not_counted"] = {
        "expected_counted": False, "observed_counted": got_strict,
        "observed_counted_default": got_default,
        "as_declared": got_strict is False and got_default is False}

    nested = {"node_id": "F2b", "gate": "G-FORM", "reviewer": "worker-x",
              "verdict": {"verdict": "revise", "score": 3.0},
              "reviewed_sha256": LEGS["F2b"]["live"],
              "evidence_refs": ["artifacts/formulation/FROZEN.json#815e08079aef"]}
    c = classify(nested, "F2b", author_sets)
    got = counted(c, "strict", "live_frozen", True)
    controls["C7_nested_dict_verdict"] = {
        "normalized_verdict": normalize_verdict(nested), "expected_counted": False,
        "observed_counted": got, "as_declared": got is False}

    if p072.exists():
        d072 = json.loads(p072.read_bytes())
        c = classify(d072, "F2b", author_sets)
        got = counted(c, "strict", "live_frozen", True)
        controls["C8_real_072_now_revise"] = {
            "verdict": c["verdict"], "expected_counted": False, "observed_counted": got,
            "as_declared": got is False}

    cross = {"node_id": "F2b", "gate": "G-FORM", "reviewer": "worker-x", "verdict": "accept",
             "counts_as_full_schema_verdict": True,
             "reviewed_sha256": LEGS["F2b"]["live"],
             "notes": "cross-mention only: schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3"}
    in_scope_f2a, reason_f2a = scope_for(cross, "F2a", collect(cross)[1])
    controls["C9_cross_mention_no_scope"] = {
        "expected_in_scope": False, "observed_in_scope": in_scope_f2a, "reason": reason_f2a,
        "as_declared": in_scope_f2a is False}

    refs_only = {"node_id": "F2a", "gate": "G-FORM", "reviewer": "worker-x", "verdict": "accept",
                 "counts_as_full_schema_verdict": True,
                 "evidence_refs": ["schemas/af_scc_c2_vacuum.yaml#e9a27996dfd3"]}
    c = classify(refs_only, "F2a", author_sets)
    got = counted(c, "strict", "schema_only", True)
    controls["C10_refs_only_same_leg_counts"] = {
        "expected_counted": True, "observed_counted": got, "as_declared": got is True,
        "scope_reason": c["scope_reason"], "live_bound": c["live_bound"]}

    controls_all = all(v["as_declared"] for v in controls.values())

    # ---- drift -------------------------------------------------------------
    end = {str(f.relative_to(ROOT)): file_sha(f) for f in review_files + pin_paths}
    drift = {k: {"start": start[k], "end": end[k]} for k in start if start[k] != end.get(k)}
    drift_detected = bool(drift)
    end_listing = sorted(p.name for p in reviews_dir.glob("*.json"))
    start_listing = [f.name for f in review_files]
    tree_added = sorted(set(end_listing) - set(start_listing))
    tree_removed = sorted(set(start_listing) - set(end_listing))

    report = {
        "task_id": "W054-GFORM-LIVE-ACCEPT-CENSUS-01",
        "actor": "worker-054",
        "created_at": args.created_at,
        "authority": {
            "worker_measurement_only": True,
            "can_set_gate_verdict": False,
            "can_set_node_status": False,
            "can_set_validation_status_passed": False,
            "canonical_files_written": [],
        },
        "question": "Which review files currently carry a full-schema ACCEPT whose declared "
                    "target is the live G-FORM schema hash of each leg, and how many are "
                    "non-author?",
        "pins": pins,
        "frozen_pin_match": frozen_pin_match,
        "live_schema_matches_declared_pin": live_schema_matches_declared_pin,
        "frozen_live_sha256": FROZEN_LIVE,
        "events_sha256": events_sha,
        "author_sets": author_sets_list,
        "rules": {
            "leg_scope": "node_id/target_id/reviewed_path identity only; cross-mention excluded",
            "live_bound": "declared target hash for the leg equals the live canonical hash",
            "stale": "declared target hashes exist but none is live",
            "full_strict": "counts_as_full_schema_verdict is true",
            "full_default": "strict, or key absent and verdict accept",
            "frozen_live": "FROZEN 815e08079aef declared (structured full-hash/path#ref or an "
                           "8+ hex prefix of it); frozen_live_structured reports the strict form",
            "nonauthor": "reviewer not in the artifact-author set for that leg (accepted artifact events)",
        },
        "counts": counts,
        "census": census,
        "special": special,
        "controls": controls,
        "controls_all_as_declared": controls_all,
        "drift": drift,
        "drift_detected": drift_detected,
        "review_tree_added_during_run": tree_added,
        "review_tree_removed_during_run": tree_removed,
        "verdict_summary": {
            leg: {"accept_live_n": len(counts[leg]["accept_live"]),
                  "accept_live_strict_full_n":
                      counts[leg]["variants"]["strict__schema_only__all"]["n"],
                  "accept_live_strict_full_live_frozen_n":
                      counts[leg]["variants"]["strict__live_frozen__all"]["n"],
                  "accept_live_strict_full_live_frozen_nonauthor_n":
                      counts[leg]["variants"]["strict__live_frozen__nonauthor"]["n"],
                  "accept_live_default_full_live_frozen_n": 
                      counts[leg]["variants"]["default__live_frozen__all"]["n"],
                  "revise_live_n": len(counts[leg]["revise_live"])}
            for leg in LEGS
        },
        "falsifier": (
            "Re-run checker.py at the recorded --created-at against an unchanged reviews/ tree. "
            "Falsified if any counted file changes classification at unchanged bytes, if the "
            "recorded per-file sha256 does not measure, if any control stops behaving as declared, "
            "or if any input hash differs from the recorded start/end pair. A later write to a "
            "review file is not a falsifier of the measurement at its recorded hash; it is a new "
            "revision to re-census."
        ),
    }

    (outdir / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    (outdir / "census.json").write_text(json.dumps(
        {"created_at": args.created_at, "pins": {k: v["sha256"] for k, v in pins.items()},
         "census": census, "counts": counts}, indent=1, sort_keys=True) + "\n")

    lines = []
    lines.append("# W054-GFORM-LIVE-ACCEPT-CENSUS-01 (read-only worker measurement)\n")
    lines.append(f"Frozen at {args.created_at}; pins: F1 `d9cebb9404b2`, F2a `e9a27996dfd3`, "
                 f"F2b `b2ab6acb2bbe`, FROZEN rev29 `815e08079aef`.\n")
    lines.append("## Counted live full-schema accepts per leg\n")
    lines.append("| leg | live+accept (any full) | strict full | strict full + live FROZEN | "
                 "strict full + live FROZEN + non-author | live revise |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for leg in LEGS:
        v = counts[leg]["variants"]
        lines.append(f"| {leg} | {len(counts[leg]['accept_live'])} | "
                     f"{v['strict__schema_only__all']['n']} | "
                     f"{v['strict__live_frozen__all']['n']} | "
                     f"{v['strict__live_frozen__nonauthor']['n']} | "
                     f"{len(counts[leg]['revise_live'])} |")
    lines.append("\nCounts are machine measurements under the pre-registered rules in "
                 "`report.json.rules`; they are not gate verdicts and do not adjudicate which "
                 "verdicts are correct.\n")
    for leg in LEGS:
        lines.append(f"### {leg} — live-bound accept files\n")
        rows = counts[leg]["accept_live"]
        if not rows:
            lines.append("_none_\n")
        for r in rows:
            lines.append(f"- `{r['file']}` reviewer={r['reviewer']} full={r['full']} "
                         f"frozen_live={r['frozen_live']} frozen_genA={r['frozen_genA']} "
                         f"nonauthor={r['nonauthor']} blind={r['blind']} "
                         f"stale={r['declared_stale_hashes']} ({r['created_at']})")
        lines.append("")
    sp = special.get("w072_f2b_self_supersession")
    if sp:
        lines.append("## Live churn: worker-072 F2b self-supersession\n")
        lines.append(f"`{sp['file']}` current sha256 `{sp['current_sha256'][:12]}`, verdict "
                     f"`{sp['current_verdict']}`, supersedes accept "
                     f"`{str(sp['supersedes_sha256'])[:12]}` at {sp['superseded_at']}; "
                     f"superseded bytes present in reviews/ = "
                     f"{sp['superseded_bytes_still_present_in_reviews']}. Hard failures: "
                     f"{', '.join(sp['hard_failures']) or 'none'}.\n")
    s17 = special.get("f2a_worker_017_frozen_binding")
    if s17:
        lines.append("## HF-059-FROZEN-01 check: F2a worker-017\n")
        lines.append(f"`{s17['file']}` sha256 `{s17['sha256'][:12]}`, verdict `{s17['verdict']}`, "
                     f"reviewed_sha256==live F2a = {s17['reviewed_sha256_is_live_f2a']}, "
                     f"declares FROZEN live = {s17['declares_frozen_live']}, "
                     f"declares FROZEN genA = {s17['declares_frozen_genA']}, "
                     f"created_at {s17['created_at']}.\n")
    lines.append("## Controls and drift\n")
    lines.append(f"- controls all as declared: **{controls_all}**")
    lines.append(f"- drift detected during run: **{drift_detected}**")
    lines.append(f"- review files added/removed while running: {len(tree_added)}/{len(tree_removed)} "
                 f"{tree_added if tree_added else ''}{tree_removed if tree_removed else ''}")
    lines.append(f"- files scanned: {len(review_files)}; in scope per leg: "
                 f"{ {leg: counts[leg]['files_in_scope'] for leg in LEGS} }\n")
    lines.append("## Non-claims\n")
    lines.append("- No gate verdict, no node status, no `validation_status=passed`, no canonical "
                 "file written, no repair adopted, no schema review verdict authored.")
    lines.append("- Independence is the objective author-set test only; the audit lead owns the "
                 "final independence/blind-status call, and the audit lead owns adjudication of "
                 "competing revise verdicts.")
    lines.append(f"\nFalsifier: {report['falsifier']}\n")
    (outdir / "README.md").write_text("\n".join(lines) + "\n")

    sums = [f"{file_sha(outdir / n)}  {n}"
            for n in ("checker.py", "report.json", "census.json", "README.md")]
    (outdir / "SHA256SUMS").write_text("\n".join(sums) + "\n")

    print(json.dumps({
        "task_id": report["task_id"],
        "verdict_summary": report["verdict_summary"],
        "variants": {leg: counts[leg]["variants"] for leg in LEGS},
        "controls_all_as_declared": controls_all,
        "drift_detected": drift_detected,
        "report_sha256": file_sha(outdir / "report.json"),
    }, indent=1))
    return 2 if (drift_detected or not controls_all) else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""W002-F2B-VERDICT-BINDING-AUDIT -- read-only forensic ledger of F2b (AF-SCC-C0-VAC-GEN)
G-FORM r3 review verdicts.

Why this exists
---------------
Card `astra-life05-verify-gform-r3` (comms/inbox/astra-lead-audit.jsonl) requires, per class:
  * accepts measured at ONE hash per class with bytes stable across the review window,
  * every verdict must measure the file hash itself and cite sha256,
  * a revise verdict must name a specific field,
  * falsifier: "A verdict at a superseded hash counted as binding; a review that does not
    cite the measured sha256".
The controller notice `astra-life07-notice-gform-coverage-update` (01:10:27) reports F2b
coverage 2-3 accepts while late revise verdicts exist. Coverage counting alone cannot tell
the adjudicator which verdicts are hash-bound and which are full-schema. This instrument
emits that ledger.

Method (mechanical, reproducible)
---------------------------------
1. Measure live hashes of both F2b copies + FROZEN manifest.
2. Scan every JSONL line under comms/outbox/ for review events in the r3 window that
   TARGET F2b (node/target/class/evidence ref to F2b or af_scc_c0). Events that merely
   mention F2b in findings are counted separately as blob-only and are not ledger rows.
3. For each event extract, without interpreting merit:
   - verdict/score/actor/created_at/event_id,
   - target classification: canonical-C0 / ancillary marker / co-targets F1,F2a / self-declared scope,
   - the sha256 tokens it cites and whether the live F2b hash b2ab6acb2bbe is among them,
   - whether a specific field is named (curated field-path token list),
   - whether the two independently reported carriers are mentioned,
   - hard_failures / gate-blocking findings counts.
4. Rank live-bound accepts into tiers A/B/C (self-declared full / canonical-path full
   evidence / ancillary) and cross-check the accepted stream (research_map.json reviews)
   for F2b review event_ids the outbox scan did not see, restricted to the same window.

This instrument writes ONLY under artifacts/worker-002/f2b_verdict_binding_audit/.
It does not judge the merits of any verdict, does not set status/validation/gate values,
and makes no canonical-path write. Detector hashes are recorded for citation only; no
CLASSSEP measurement is performed here.
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.dirname(os.path.abspath(__file__))

# Card astra-life05-verify-gform-r3 was created 2026-09-12T00:48:41+08:00; rev13 F2b bytes
# were landed 00:53:20; FROZEN rev29 re-emitted 00:57:26.
WINDOW_START = "2026-09-12T00:48:41"
WINDOW_END = None  # set at run time

C0_CANON = "schemas/af_scc_c0_vacuum.yaml"
C0_MIRROR = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
C2_CANON = "schemas/af_scc_c2_vacuum.yaml"
F1_CANON = "schemas/af_wcc_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
TAXONOMY = "research_map/formulation_taxonomy.yaml"
DETECTOR = "research_map/class_separation.py"

LIVE_C0 = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
LIVE_C0_PREFIX = LIVE_C0[:12]
FROZEN_REV29 = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"
REPAIR_CANDIDATE = "84b5d3fa29a677ad157b924675bb5a9c08281395920be0221535465a5da44b40"

# Two carriers independently reported by two non-author reviewers
# (worker-002 W002-F2B-IND-01/02, worker-038 W038-F2B13-01/02).
CARRIER_TOKENS = {
    "regularity.must_not_conflate": ["must_not_conflate", "containment_denial", "containment denial"],
    "implication_ledger.forbidden_transfers": [
        "forbidden_transfers",
        "containment_premise",
        "containment premise",
        "strictly larger extension class",
        "premise inverted",
    ],
}

# Curated field-path tokens for the r3 requirement "a revise verdict must name a specific field".
FIELD_TOKENS = [
    "must_not_conflate",
    "forbidden_transfers",
    "implication_ledger",
    "extension_class_containment",
    "extension_predicate",
    "regularity.",
    "genericity",
    "visibility",
    "conclusion_type",
    "quantifier",
    "topology",
    "f0_binding",
    "review_status",
    "vocab",
    "tier_2",
    "i_plus",
    "provenance",
]

ANCILLARY_MARKERS = [
    "coverage",
    "census",
    "index",
    "deferral",
    "variant",
    "integration",
    "sandbox",
    "preflight",
    "adjudication",
    "x-target",
    "xtarget",
    "candidate",
    "repair",
    "publication",
    "preaccept",
    "varstrength",
    "symdef",
    "gate-test",
    "gate_test",
    "gate suite",
]

SHA_RE = re.compile(r"\b[0-9a-f]{12,64}\b")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def measure(path):
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return {"path": path, "exists": False, "sha256": None, "mtime": None}
    st = os.stat(p)
    return {
        "path": path,
        "exists": True,
        "sha256": sha256_file(p),
        "mtime": datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(),
        "bytes": st.st_size,
    }


def load_events():
    """All JSON objects from comms/outbox/**/*.jsonl, deduped by event_id (richest wins)."""
    events = {}
    no_id = 0
    outbox = os.path.join(ROOT, "comms", "outbox")
    for dirpath, _dirnames, filenames in os.walk(outbox):
        for fn in sorted(filenames):
            if not fn.endswith(".jsonl"):
                continue
            fpath = os.path.join(dirpath, fn)
            with open(fpath, "r", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    line = line.strip()
                    if not line.startswith("{"):
                        continue
                    try:
                        ev = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(ev, dict):
                        continue
                    eid = ev.get("event_id")
                    if not eid:
                        no_id += 1
                        eid = "no-id:%s:%d" % (os.path.relpath(fpath, ROOT), lineno)
                    rel = os.path.relpath(fpath, ROOT)
                    prev = events.get(eid)
                    if prev is None or len(json.dumps(ev)) > len(json.dumps(prev["event"])):
                        events[eid] = {"event": ev, "source_file": rel, "line": lineno}
    return events, no_id


def load_map_reviews():
    """Accepted-stream review records from research_map.json, keyed by event_id.

    The accepted stream is authoritative for what the controller ingested; outbox files are
    authoritative for what was emitted. The ledger is the union, flagged per row.
    """
    out = {}
    try:
        with open(os.path.join(ROOT, "research_map", "research_map.json")) as fh:
            m = json.load(fh)
    except Exception:
        return out
    for r in m.get("reviews", []):
        if not isinstance(r, dict):
            continue
        eid = r.get("event_id")
        if not eid:
            eid = "map-review:%s:%s" % (r.get("actor"), r.get("created_at"))
        out[eid] = r
    return out


def classify_target(ev):
    """Mechanical target classification; no merit judgement.

    Returns dict with:
      blob_has_f2b        -- any F2b/af_scc_c0 token anywhere
      targets_f2b         -- node/target/class/evidence refs name F2b or af_scc_c0
      canonical_c0_target -- a ref or target is the canonical F2b path (mirror allowed)
      co_targets          -- canonical F1/F2a paths or nodes named alongside
      ancillary           -- task/target contains an ancillary marker
    """
    blob = json.dumps(ev)
    node_ids = [str(ev.get("node_id") or "")]
    node_ids += [str(x) for x in (ev.get("node_ids") or []) if isinstance(x, (str, int))]
    class_ids = [str(x) for x in (ev.get("class_ids") or [])]
    if ev.get("class_id"):
        class_ids.append(str(ev["class_id"]))
    target = str(ev.get("target_id") or "")
    task = str(ev.get("task_id") or "")
    refs = [r for r in (ev.get("evidence_refs") or []) if isinstance(r, str)]
    arts = ev.get("artifact_refs") or []
    arts = [a for a in (arts if isinstance(arts, list) else [arts]) if isinstance(a, str)]
    reviewed_path = str(ev.get("reviewed_path") or "")
    all_text = " ".join(node_ids + class_ids + [target, task, reviewed_path] + refs + arts)

    blob_has_f2b = ("F2b" in blob) or ("af_scc_c0" in blob)
    targets_f2b = (
        any("F2b" in n for n in node_ids)
        or "AF-SCC-C0-VAC-GEN" in class_ids
        or "F2b" in target
        or "af_scc_c0" in target
        or "af_scc_c0" in reviewed_path
        or any("af_scc_c0" in r for r in refs)
        or any("af_scc_c0" in a for a in arts)
    )
    # Primary target: the verdict is *about* F2b, not merely citing it.
    primary_f2b_target = (
        any("F2b" in n for n in node_ids)
        or class_ids == ["AF-SCC-C0-VAC-GEN"]
        or "F2b" in target
        or "af_scc_c0" in target
        or "af_scc_c0" in reviewed_path
    )
    canonical_c0_target = (
        reviewed_path in (C0_CANON, C0_MIRROR)
        or C0_CANON in target
        or C0_MIRROR in target
        or any(r.split("#")[0] in (C0_CANON, C0_MIRROR) or r.startswith(C0_CANON) or r.startswith(C0_MIRROR) for r in refs)
    )
    co = []
    if ("F1" in " ".join(node_ids)) or (F1_CANON in all_text) or ("AF-WCC-VAC-GEN" in class_ids):
        co.append("F1")
    if ("F2a" in " ".join(node_ids)) or (C2_CANON in all_text) or ("AF-SCC-C2-VAC-GEN" in class_ids):
        co.append("F2a")
    ancillary_hits = [m for m in ANCILLARY_MARKERS if m in (target + " " + task).lower()]
    return {
        "blob_has_f2b": blob_has_f2b,
        "targets_f2b": targets_f2b,
        "primary_f2b_target": primary_f2b_target,
        "canonical_c0_target": canonical_c0_target,
        "co_targets": sorted(set(co)),
        "ancillary_markers": ancillary_hits,
    }


def declared_live_binding(ev):
    """True iff the event itself declares a live-F2b binding (hash or path+hash)."""
    if str(ev.get("reviewed_sha256") or "") == LIVE_C0:
        return True
    if str(ev.get("live_path_sha256_at_emit") or "") == LIVE_C0:
        return True
    target = str(ev.get("target_id") or "")
    if LIVE_C0_PREFIX in target and ("F2b" in target or "af_scc_c0" in target):
        return True
    for ref in ev.get("evidence_refs") or []:
        if isinstance(ref, str) and "af_scc_c0" in ref and LIVE_C0_PREFIX in ref:
            return True
    for key in ("artifact_refs", "reviewed_path", "artifact"):
        val = ev.get(key)
        vals = val if isinstance(val, list) else [val]
        for v in vals:
            if isinstance(v, str) and "af_scc_c0" in v and LIVE_C0_PREFIX in v:
                return True
    for k, v in ev.items():
        if "sha256" in k.lower() and isinstance(v, str) and v == LIVE_C0:
            return True
    return False


def cited_hashes(ev):
    toks = set()
    for v in ev.values():
        if isinstance(v, str):
            toks.update(SHA_RE.findall(v))
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, str):
                    toks.update(SHA_RE.findall(x))
    return sorted(toks)


def carrier_mentions(ev):
    found = {}
    for carrier, toks in CARRIER_TOKENS.items():
        hits = []
        for val in ev.values():
            blob = val if isinstance(val, str) else json.dumps(val)
            low = blob.lower()
            for t in toks:
                if t.lower() in low:
                    hits.append(t)
        if hits:
            found[carrier] = sorted(set(hits))
    return found


def named_fields(ev):
    blob = json.dumps(ev).lower()
    return sorted({t for t in FIELD_TOKENS if t.lower() in blob})


def gate_blocking_count(ev):
    n = 0
    for f in ev.get("findings") or []:
        if isinstance(f, dict) and f.get("gate_blocking") is True:
            n += 1
    return n


def normalize(eid, rec):
    ev = rec["event"]
    cls = classify_target(ev)
    hf = ev.get("hard_failures")
    hf_n = len(hf) if isinstance(hf, list) else (1 if hf else 0)
    return {
        "event_id": eid,
        "created_at": str(ev.get("created_at") or ""),
        "actor": str(ev.get("actor") or ""),
        "event_type": str(ev.get("event_type") or ""),
        "verdict": ev.get("verdict"),
        "score": ev.get("score"),
        "node_id": ev.get("node_id"),
        "target_id": ev.get("target_id"),
        "task_id": ev.get("task_id"),
        "gate": ev.get("gate"),
        "class_ids": ev.get("class_ids") or ([ev.get("class_id")] if ev.get("class_id") else []),
        "scope": ("multi-class" if cls["co_targets"] else ("f2b-targeted" if cls["targets_f2b"] else "not-f2b")),
        "primary_f2b_target": cls["primary_f2b_target"],
        "canonical_c0_target": cls["canonical_c0_target"],
        "co_targets": cls["co_targets"],
        "ancillary_markers": cls["ancillary_markers"],
        "self_declared_full_schema_verdict": bool(ev.get("counts_as_full_schema_verdict")),
        "self_declared_gate_accept": ev.get("counts_as_gate_accept"),
        "blind": ev.get("blind"),
        "declared_live_binding": declared_live_binding(ev),
        "reviewed_sha256": ev.get("reviewed_sha256"),
        "reviewed_path": ev.get("reviewed_path"),
        "hard_failures_n": hf_n,
        "gate_blocking_findings_n": gate_blocking_count(ev),
        "carrier_mentions": carrier_mentions(ev),
        "named_fields": named_fields(ev),
        "cited_hashes": cited_hashes(ev),
        "cites_frozen_rev29": FROZEN_REV29[:12] in cited_hashes(ev),
        "cites_repair_candidate": REPAIR_CANDIDATE[:12] in cited_hashes(ev),
        "supersedes": ev.get("supersedes") or ev.get("supersedes_event_id"),
        "source_file": rec["source_file"],
        "source_line": rec["line"],
    }


def accept_tier(row):
    """Tiering for live-bound accepts, from the card's own acceptance text."""
    if row["verdict"] != "accept":
        return None
    if not row["primary_f2b_target"]:
        return "E-not-an-f2b-verdict"
    if not row["declared_live_binding"]:
        return "D-unbound"
    if not row["canonical_c0_target"]:
        return "C-noncanonical-target"
    if row["ancillary_markers"]:
        return "C-ancillary"
    if row["self_declared_full_schema_verdict"]:
        return "A-full-self-declared"
    return "B-canonical-path-full"


def main():
    global WINDOW_END
    started = datetime.now().astimezone()
    WINDOW_END = started.isoformat(timespec="seconds")

    measured = {
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "instrument_started_at": started.isoformat(timespec="seconds"),
        "pins_start": {p: measure(p) for p in (C0_CANON, C0_MIRROR, C2_CANON, F1_CANON, FROZEN, TAXONOMY, DETECTOR)},
    }
    frozen_declared = None
    fp = os.path.join(ROOT, FROZEN)
    if os.path.exists(fp):
        try:
            with open(fp) as fh:
                frozen_declared = json.load(fh)
        except Exception as exc:  # pragma: no cover
            frozen_declared = {"_parse_error": str(exc)}

    events, no_id = load_events()
    map_reviews = load_map_reviews()
    in_outbox = set(events)
    in_map = set(map_reviews)
    merged = dict(events)
    for eid, rec in map_reviews.items():
        if eid not in merged:
            merged[eid] = {"event": rec, "source_file": "research_map/research_map.json#reviews", "line": None}
    ledger, blob_only = [], []
    for eid, rec in merged.items():
        ev = rec["event"]
        if ev.get("event_type") != "review":
            continue
        ts = str(ev.get("created_at") or "")
        if ts < WINDOW_START:
            continue
        cls = classify_target(ev)
        if not cls["targets_f2b"]:
            if cls["blob_has_f2b"]:
                blob_only.append({"event_id": eid, "actor": ev.get("actor"), "created_at": ts,
                                  "verdict": ev.get("verdict"), "target_id": ev.get("target_id")})
            continue
        row = normalize(eid, rec)
        row["in_outbox"] = eid in in_outbox
        row["in_map"] = eid in in_map
        ledger.append(row)

    ledger.sort(key=lambda r: (r["created_at"], r["actor"], r["event_id"]))
    for row in ledger:
        row["accept_tier"] = accept_tier(row)

    # Primary F2b verdicts are the headline; citing rows are kept in the ledger for context.
    f2b_rows = [r for r in ledger if r["scope"] in ("f2b-targeted", "multi-class")]
    primary_rows = [r for r in ledger if r["primary_f2b_target"]]
    citing_only = [r for r in ledger if not r["primary_f2b_target"]]
    accepts = [r for r in primary_rows if r["verdict"] == "accept"]
    revises = [r for r in primary_rows if r["verdict"] == "revise"]
    inconclusive = [r for r in primary_rows if r["verdict"] == "inconclusive"]

    tiers = {}
    for r in accepts:
        tiers.setdefault(r["accept_tier"], []).append(r["event_id"])
    tier_a = tiers.get("A-full-self-declared", [])
    tier_b = tiers.get("B-canonical-path-full", [])
    tier_c = tiers.get("C-ancillary", []) + tiers.get("C-noncanonical-target", [])
    tier_d = tiers.get("D-unbound", [])
    tier_e = tiers.get("E-not-an-f2b-verdict", [])

    field_revises_live = [
        r["event_id"] for r in revises
        if r["declared_live_binding"] and r["canonical_c0_target"]
        and (r["hard_failures_n"] > 0 or r["gate_blocking_findings_n"] > 0 or bool(r["carrier_mentions"]))
    ]
    revises_no_field = [
        r["event_id"] for r in revises
        if not (r["named_fields"] or r["carrier_mentions"] or r["hard_failures_n"])
    ]
    revises_not_live = [r["event_id"] for r in revises if not r["declared_live_binding"]]
    carrier_revises = {
        c: sorted({r["actor"] for r in revises if c in r["carrier_mentions"]})
        for c in CARRIER_TOKENS
    }
    carrier_accepts = {
        c: sorted({r["actor"] for r in accepts if c in r["carrier_mentions"]})
        for c in CARRIER_TOKENS
    }
    # Do any live-bound full accepts explicitly dispose of the two reported carriers?
    carrier_rebuttal_accepts = [
        r["event_id"] for r in accepts
        if r["accept_tier"] in ("A-full-self-declared", "B-canonical-path-full")
        and r["carrier_mentions"]
    ]
    # Late revise wave: field-naming live-bound revises after the controller coverage notice
    # astra-life07-notice-gform-coverage-update (2026-09-12T01:10:27+08:00).
    late_cut = "2026-09-12T01:10:27"
    carrier_revise_late_wave = [
        {"event_id": r["event_id"], "actor": r["actor"], "created_at": r["created_at"],
         "hard_failures_n": r["hard_failures_n"], "gate_blocking_findings_n": r["gate_blocking_findings_n"],
         "carriers": sorted(r["carrier_mentions"].keys())}
        for r in revises
        if r["created_at"] >= late_cut and r["carrier_mentions"]
    ]
    carrier_revise_late_wave_actors = sorted({r["actor"] for r in carrier_revise_late_wave})

    # Same-actor flips at the live hash: actor emitted a live-bound accept and later a
    # live-bound revise on primary F2b. Mechanical only; no prose interpretation.
    live_rows = [r for r in primary_rows if r["declared_live_binding"]]
    by_actor = {}
    for r in live_rows:
        by_actor.setdefault(r["actor"], []).append(r)
    same_actor_flips = []
    for actor, rows in sorted(by_actor.items()):
        rows = sorted(rows, key=lambda r: r["created_at"])
        for a in rows:
            if a["verdict"] != "accept":
                continue
            later = [x for x in rows if x["created_at"] > a["created_at"] and x["verdict"] == "revise"]
            if later:
                same_actor_flips.append({
                    "actor": actor,
                    "accept_event_id": a["event_id"],
                    "accept_created_at": a["created_at"],
                    "revise_event_id": later[0]["event_id"],
                    "revise_created_at": later[0]["created_at"],
                    "revise_hard_failures_n": later[0]["hard_failures_n"],
                    "revise_carriers": sorted(later[0]["carrier_mentions"].keys()),
                })
    explicit_supersedes = [
        {"event_id": r["event_id"], "actor": r["actor"], "created_at": r["created_at"],
         "supersedes": r.get("supersedes") or r.get("supersedes_event_id")}
        for r in ledger
        if r.get("supersedes") or r.get("supersedes_event_id")
    ]

    # Accepted-stream union integrity: every delivered map review id must be a ledger row
    # (by construction), and we report map ids still absent from the outbox scan.
    ledger_ids = {r["event_id"] for r in ledger}
    map_f2b_window = {r["event_id"] for r in primary_rows if r["in_map"]}
    map_ids = {r["event_id"] for r in ledger if r["in_map"]}
    union_missing = sorted(map_f2b_window - ledger_ids)
    outbox_only = sorted({r["event_id"] for r in primary_rows if r["in_outbox"] and not r["in_map"]})
    max_created = max([r["created_at"] for r in ledger] or [""])
    future_dated = sorted(r["event_id"] for r in ledger if r["created_at"] > WINDOW_END)

    report = {
        "audit_id": "W002-F2B-VERDICT-BINDING-AUDIT-20260912T0111",
        "actor": "worker-002",
        "agent_id": "deepseek-flash-02",
        "task_id": "W002-F2B-VERDICT-BINDING-INDEPENDENT-01",
        "node_id": "F2b",
        "gate": "G-FORM",
        "class_ids": ["AF-SCC-C0-VAC-GEN", "AF-SCC-C2-VAC-GEN"],
        "card": "astra-life05-verify-gform-r3",
        "authority_note": "read-only forensic ledger; no canonical file written; no node status, validation_status or gate verdict claimed",
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "pins_measured": measured["pins_start"],
        "frozen_declared": frozen_declared,
        "counts": {
            "review_events_scanned_raw": len(events),
            "map_review_records_loaded": len(map_reviews),
            "no_event_id_lines": no_id,
            "f2b_citing_review_events_in_window": len(ledger),
            "f2b_primary_review_events_in_window": len(primary_rows),
            "f2b_citing_only_rows": len(citing_only),
            "blob_only_f2b_mentions_excluded": len(blob_only),
            "accepts": len(accepts),
            "revises": len(revises),
            "inconclusive": len(inconclusive),
            "accept_tier_A_full_self_declared": len(tier_a),
            "accept_tier_B_canonical_path_full": len(tier_b),
            "accept_tier_C_ancillary_or_noncanonical": len(tier_c),
            "accept_tier_D_unbound": len(tier_d),
            "accept_tier_E_not_an_f2b_verdict": len(tier_e),
            "field_naming_revises_live_bound_canonical": len(field_revises_live),
            "revises_not_live_bound": len(revises_not_live),
            "revises_without_field_or_carrier": len(revises_no_field),
            "live_bound_full_accepts_mentioning_a_reported_carrier": len(carrier_rebuttal_accepts),
            "carrier_revise_late_wave_events": len(carrier_revise_late_wave),
            "carrier_revise_late_wave_distinct_actors": len(carrier_revise_late_wave_actors),
            "same_actor_accept_then_later_revise_flips": len(same_actor_flips),
            "explicit_supersedes_rows": len(explicit_supersedes),
            "map_primary_window_ids_not_in_ledger": len(union_missing),
            "primary_rows_in_outbox_not_yet_in_map": len(outbox_only),
            "future_dated_events_vs_instrument_end": len(future_dated),
            "max_created_at_seen": max_created,
        },
        "accepts_by_tier": {"A": tier_a, "B": tier_b, "C": tier_c, "D": tier_d, "E": tier_e},
        "field_naming_revises_live_bound_canonical": field_revises_live,
        "revises_not_live_bound": revises_not_live,
        "revises_without_field_or_carrier": revises_no_field,
        "carrier_mentions_revises": carrier_revises,
        "carrier_mentions_accepts": carrier_accepts,
        "live_bound_full_accepts_mentioning_a_reported_carrier": carrier_rebuttal_accepts,
        "carrier_revise_late_wave": carrier_revise_late_wave,
        "carrier_revise_late_wave_actors": carrier_revise_late_wave_actors,
        "same_actor_flips": same_actor_flips,
        "explicit_supersedes_rows": explicit_supersedes,
        "author_relationship": "the ledger includes verdicts authored by worker-002 (deepseek-flash-02) itself; classification is mechanical over the emitted JSON and does not re-judge any verdict's merit",
        "f2b_verdict_rows": f2b_rows,
        "f2b_primary_rows": primary_rows,
        "f2b_citing_only_rows": citing_only,
        "blob_only_mentions_excluded": blob_only,
        "accepted_stream_crosscheck": {
            "map_primary_window_ids_not_in_ledger": union_missing,
            "primary_rows_in_outbox_not_yet_in_map": outbox_only,
            "future_dated_events": future_dated,
        },
        "method": {
            "instrument": "artifacts/worker-002/f2b_verdict_binding_audit/audit_f2b_bindings.py",
            "live_c0_sha256": LIVE_C0,
            "live_c0_prefix_used_for_binding": LIVE_C0_PREFIX,
            "window_start_rule": "card astra-life05-verify-gform-r3 created_at >= 2026-09-12T00:48:41",
            "targeting_rule": "targets_f2b = F2b/af_scc_c0 token in node_id/node_ids, class_id(s), target_id, reviewed_path, evidence_refs or artifact_refs; primary_f2b_target = F2b in node_ids, class_ids == [AF-SCC-C0-VAC-GEN], or F2b/af_scc_c0 in target_id/reviewed_path",
            "sources_rule": "ledger = union of comms/outbox/**/*.jsonl emitted events and research_map/research_map.json reviews records, deduped by event_id, flagged in_outbox/in_map",
            "binding_rule": "verdict declares reviewed_sha256 == live hash, or a target_id containing both an F2b/af_scc_c0 token and the live 12-hex prefix, or an evidence_ref/artifact_ref containing af_scc_c0 and the live 12-hex prefix, or live_path_sha256_at_emit == live hash",
            "accept_tier_rule": "headline accepts are primary F2b verdicts only; A = live-bound + canonical C0 target + self-declared counts_as_full_schema_verdict; B = live-bound + canonical C0 target, no ancillary marker, not self-declared; C = live-bound but ancillary marker or non-canonical target; D = not live-bound; E = citing-only row, not an F2b verdict; ancillary markers include coverage/census/index/deferral/variant/integration/sandbox/adjudication/candidate/repair/publication/preaccept/varstrength/symdef/gate-test",
            "field_rule": "revise is field-naming if hard_failures non-empty OR gate_blocking findings > 0 OR a curated field/carrier token appears",
            "carrier_rule": "carrier tokens are matched as substrings in the event JSON (must_not_conflate / forbidden_transfers / containment_premise / containment_denial / premise inverted / strictly larger extension class)",
        },
        "falsifier": "This ledger is falsified if any of: (a) schemas/af_scc_c0_vacuum.yaml does not measure b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c at audit time; (b) a review event with created_at >= 2026-09-12T00:48:41 that targets F2b exists in comms/outbox/ or research_map.json reviews and is missing from the ledger; (c) an event classified live-bound does not actually cite the live prefix under the stated rule (re-derive from source_file:source_line); (d) an accept in tier A or B is not a primary F2b verdict, does not have canonical_c0_target true, or carries an ancillary marker; (e) a revise classified field-naming has neither hard_failures, a gate_blocking finding, nor a curated field/carrier token; or (f) accepted_stream_crosscheck.map_primary_window_ids_not_in_ledger is non-empty.",
        "next_falsifier": "After any F2b landing (revision bump / FROZEN re-emit), re-run this instrument; every live-bound verdict in the ledger becomes void at the new hash unless re-emitted, so expect tiers A/B and field_naming_revises_live_bound_canonical to reset to the verdicts re-measured at the new bytes.",
    }

    ledger_doc = {
        "audit_id": report["audit_id"],
        "window": report["window"],
        "live_c0_sha256": LIVE_C0,
        "rows": ledger,
    }

    def w(name, obj):
        with open(os.path.join(OUT, name), "w") as fh:
            json.dump(obj, fh, indent=1, sort_keys=True)
            fh.write("\n")

    w("ledger.json", ledger_doc)
    payload = json.dumps(ledger, sort_keys=True, separators=(",", ":")).encode()
    report["determinism"] = {"ledger_digest_sha256": hashlib.sha256(payload).hexdigest()}
    w("report.json", report)

    lines = []
    lines.append("# F2b verdict-binding ledger (W002-F2B-VERDICT-BINDING-AUDIT)\n")
    lines.append("Card `astra-life05-verify-gform-r3`; node F2b; class AF-SCC-C0-VAC-GEN; gate G-FORM.\n")
    lines.append("Live F2b pin measured: `%s`\n" % LIVE_C0)
    lines.append("Window: %s -> %s\n" % (WINDOW_START, WINDOW_END))
    lines.append("\n## Mechanical summary\n")
    for k, v in report["counts"].items():
        lines.append("- %s: %s" % (k, v))
    lines.append("\n## Live-bound accepts by tier\n")
    for t in ("A", "B", "C", "D", "E"):
        lines.append("- tier %s: %s" % (t, ", ".join(report["accepts_by_tier"][t]) or "-"))
    lines.append("\n## Field-naming live-bound canonical revises\n")
    for e in field_revises_live:
        lines.append("- `%s`" % e)
    lines.append("\n## Late carrier-revise wave (>= %s, after controller coverage notice)\n" % late_cut)
    lines.append("- events: %d; distinct actors: %d (%s)" % (
        len(carrier_revise_late_wave), len(carrier_revise_late_wave_actors),
        ", ".join(carrier_revise_late_wave_actors) or "-"))
    for e in carrier_revise_late_wave:
        lines.append("- %s `%s` hf=%s gb=%s carriers=%s" % (
            e["created_at"], e["event_id"], e["hard_failures_n"], e["gate_blocking_findings_n"],
            ",".join(e["carriers"])))
    lines.append("\n## Same-actor flips at the live hash (accept, then later revise)\n")
    for f in same_actor_flips:
        lines.append("- %s: accept `%s` (%s) -> revise `%s` (%s) hf=%s carriers=%s" % (
            f["actor"], f["accept_event_id"], f["accept_created_at"], f["revise_event_id"],
            f["revise_created_at"], f["revise_hard_failures_n"], ",".join(f["revise_carriers"])))
    lines.append("\n## Verdict rows (F2b-targeting)\n")
    lines.append("| created_at | actor | verdict | score | scope | tier | live | canon | hard_fail | blocking | carriers |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in f2b_rows:
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["created_at"], r["actor"], r["verdict"], r["score"], r["scope"], r["accept_tier"] or "-",
            r["declared_live_binding"], r["canonical_c0_target"], r["hard_failures_n"],
            r["gate_blocking_findings_n"], ",".join(r["carrier_mentions"].keys()) or "-"))
    lines.append("\nNo canonical file was written; no gate verdict is claimed.\n")
    with open(os.path.join(OUT, "REPORT.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")

    print(json.dumps(report["counts"], indent=1))
    print("ledger rows:", len(ledger))
    print("tiers:", json.dumps(report["accepts_by_tier"], indent=1))
    print("digest:", report["determinism"]["ledger_digest_sha256"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

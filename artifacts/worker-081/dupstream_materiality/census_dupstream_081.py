#!/usr/bin/env python3
"""W081-DUPSTREAM-MATERIALITY-01 (worker-081, bounded read-only task).

Question: does content-duplicate upward-event emission materialise as duplicate
state inside research_map.json, and does it contaminate gate-relevant counts
(CF-31 F2b coverage; numerics/gates.py::_protocol_review event_id dedup)?

Read-only w.r.t. every canonical path.  Writes only inside this artifact
directory (and the caller writes the checkpoint separately).  Stdlib only.

Fingerprint (declared equivalence): sha256 of canonical JSON of the event with
{event_id, created_at, _received_at} removed -- i.e. the same emission body,
re-ingested or re-emitted under a new id/timestamp.  A secondary strict arm
removes only {event_id, created_at}.

Materialisation: every list-valued top-level section of research_map.json is
scanned for dict entries carrying a non-empty top-level ``event_id``; the entry
count per event_id is recorded.  A duplicate group is DOUBLED iff >=2 of its
member event_ids are materialised (or one event_id is materialised >=2 times).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINNED = HERE / "pinned"

FINGERPRINT_EXCLUDE = ("event_id", "created_at", "_received_at")
STRICT_EXCLUDE = ("event_id", "created_at")

PIN_PATHS = (
    "research_map/events.jsonl",
    "research_map/research_map.json",
    "comms/rejected.jsonl",
    "comms/outbox/astra-lead-formulation.jsonl",
    "numerics/gates.py",
    "numerics/CONVERGENCE_PROTOCOL.md",
)

LEAD_BATCH_PREFIXES = ("lead-form-20260912T011509-", "lead-form-20260912T011516-")
CF31_REVIEWERS = ("worker-052", "worker-071", "worker-072", "worker-090")
MATERIAL_TYPES = ("claim", "review", "resource_request", "gate", "direction_update")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str | None:
    try:
        return sha256_bytes(p.read_bytes())
    except OSError:
        return None


def measure_pins() -> dict:
    return {rel: sha256_file(ROOT / rel) for rel in PIN_PATHS}


def load_events(path: Path) -> tuple[list[dict], int]:
    events: list[dict] = []
    bad = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(obj, dict):
            events.append(obj)
        else:
            bad += 1
    return events, bad


def fingerprint(event: dict, exclude=FINGERPRINT_EXCLUDE) -> str:
    body = {k: v for k, v in event.items() if k not in exclude}
    return sha256_bytes(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())


def materialisation(map_obj: dict) -> dict[str, list[dict]]:
    """event_id -> list of {section, index} for top-level list entries."""
    out: dict[str, list[dict]] = {}
    for section, value in map_obj.items():
        if not isinstance(value, list):
            continue
        for i, entry in enumerate(value):
            if not isinstance(entry, dict):
                continue
            eid = entry.get("event_id")
            if isinstance(eid, str) and eid:
                out.setdefault(eid, []).append({"section": section, "index": i})
    return out


def deep_refs(map_obj: dict, prefixes) -> dict[str, list[str]]:
    """Map string value -> list of paths where it occurs, for values starting with a prefix."""
    hits: dict[str, list[str]] = {}

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + [str(k)])
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, path + [str(i)])
        elif isinstance(node, str):
            for p in prefixes:
                if node.startswith(p):
                    hits.setdefault(node, []).append("/".join(path))

    walk(map_obj, [])
    return hits


def analyze(events: list[dict], map_obj: dict, exclude=FINGERPRINT_EXCLUDE) -> dict:
    groups: dict[str, list[dict]] = {}
    order: list[str] = []
    for e in events:
        fp = fingerprint(e, exclude)
        if fp not in groups:
            groups[fp] = []
            order.append(fp)
        groups[fp].append(e)
    dup_groups = [groups[fp] for fp in order if len(groups[fp]) > 1]

    mat = materialisation(map_obj)
    doubled = []
    materialised_members = 0
    repeated_ids = {}
    for members in dup_groups:
        ids_in_group = [str(e.get("event_id")) for e in members]
        counts = {}
        for eid in ids_in_group:
            counts[eid] = counts.get(eid, 0) + 1
        for eid, n in counts.items():
            if n > 1:
                repeated_ids[eid] = n
        pairs_by_id = {}
        for e in members:
            eid = str(e.get("event_id"))
            locs = mat.get(eid, [])
            if locs:
                pairs_by_id[eid] = {"event_id": eid, "locations": locs}
        pairs = list(pairs_by_id.values())
        if len(pairs) >= 2 or any(len(p["locations"]) >= 2 for p in pairs):
            materialised_members += len(pairs)
            head = members[0]
            doubled.append(
                {
                    "event_type": head.get("event_type"),
                    "node_id": head.get("node_id"),
                    "class_id": head.get("class_id"),
                    "gate": head.get("gate"),
                    "n_members": len(members),
                    "n_distinct_event_ids": len(set(ids_in_group)),
                    "materialised_members": pairs,
                    "event_ids": ids_in_group,
                    "created_at": [str(e.get("created_at")) for e in members],
                }
            )
    type_counts: dict[str, int] = {}
    node_counts: dict[str, int] = {}
    class_counts: dict[str, int] = {}
    for g in doubled:
        t = str(g["event_type"])
        type_counts[t] = type_counts.get(t, 0) + 1
        n = str(g["node_id"])
        node_counts[n] = node_counts.get(n, 0) + 1
        c = str(g["class_id"])
        class_counts[c] = class_counts.get(c, 0) + 1
    return {
        "n_events": len(events),
        "n_groups": len(order),
        "n_duplicate_groups": len(dup_groups),
        "n_duplicate_ids": sum(len(g) for g in dup_groups),
        "n_doubled_groups": len(doubled),
        "n_materialised_members_of_doubled_groups": materialised_members,
        "n_stream_event_ids_repeated_within_a_group": len(repeated_ids),
        "stream_event_ids_repeated_within_a_group": repeated_ids,
        "doubled_groups": doubled,
        "doubled_by_event_type": type_counts,
        "doubled_by_node": node_counts,
        "doubled_by_class": class_counts,
        "material_class_groups": sum(1 for g in dup_groups if g[0].get("event_type") in MATERIAL_TYPES),
    }


def lead_batch_adjudication(events: list[dict], map_obj: dict) -> dict:
    members = {
        str(e.get("event_id")): e
        for e in events
        if str(e.get("event_id", "")).startswith(LEAD_BATCH_PREFIXES)
    }
    applied = set(map_obj.get("applied_event_ids") or [])
    applied_members = sorted(eid for eid in members if eid in applied)
    entry_level = {
        eid: locs
        for eid, locs in materialisation(map_obj).items()
        if eid.startswith(LEAD_BATCH_PREFIXES)
    }
    refs = deep_refs(map_obj, LEAD_BATCH_PREFIXES)
    mentions = {
        k: [p for p in paths if not p.startswith("applied_event_ids")]
        for k, paths in refs.items()
    }
    mentions = {k: v for k, v in mentions.items() if v}
    # pair body identity
    pairs = []
    for tag in ("120", "121", "123", "124", "125", "126", "127"):
        a = members.get(f"lead-form-20260912T011509-{tag}")
        b = members.get(f"lead-form-20260912T011516-{tag}")
        if a is None or b is None:
            pairs.append({"tag": tag, "both_present": False})
            continue
        pairs.append(
            {
                "tag": tag,
                "both_present": True,
                "body_identical": fingerprint(a) == fingerprint(b),
                "event_type": a.get("event_type"),
            }
        )
    return {
        "n_members_in_accepted_stream": len(members),
        "n_applied": len(applied_members),
        "applied_ids": applied_members,
        "entry_level_materialisation": entry_level,
        "textual_mentions_outside_applied": mentions,
        "pairs": pairs,
        "containment_claim_confirmed": len(applied_members) == 14 and not entry_level,
    }


def cf31_probe(events: list[dict], map_obj: dict, dup_member_ids: set[str]) -> dict:
    out = {}
    for reviewer in CF31_REVIEWERS:
        rows = [
            r
            for r in (map_obj.get("reviews") or [])
            if isinstance(r, dict) and r.get("reviewer") == reviewer
        ]
        f2b_ids = sorted(
            str(r.get("event_id"))
            for r in rows
            if "C0-VAC" in str(r.get("class_id") or "")
            or "af_scc_c0" in str(r.get("target_id") or "")
            or str(r.get("target_id")) == "F2b"
        )
        out[reviewer] = {
            "n_reviews_in_map": len(rows),
            "review_ids": [r.get("event_id") for r in rows],
            "any_member_of_duplicate_group": sorted(
                str(r.get("event_id")) for r in rows if str(r.get("event_id")) in dup_member_ids
            ),
            "f2b_targeted": f2b_ids,
            "f2b_duplicate_members": sorted(set(f2b_ids) & dup_member_ids),
        }
    return out


def gates_probe(events: list[dict], gates_py: Path, protocol_sha: str) -> dict:
    if not gates_py.exists():
        return {"module_loaded": False, "reason": "pinned gates.py copy missing"}
    spec = importlib.util.spec_from_file_location("w081_gates_live", gates_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    live = mod._protocol_review(events, protocol_sha)

    def dedup_first(seq):
        seen = set()
        out = []
        for e in seq:
            fp = fingerprint(e)
            if fp in seen:
                continue
            seen.add(fp)
            out.append(e)
        return out

    def dedup_last(seq):
        last = {}
        for e in seq:
            last[fingerprint(e)] = e
        return list(last.values())

    content_first = mod._protocol_review(dedup_first(events), protocol_sha)
    content_last = mod._protocol_review(dedup_last(events), protocol_sha)
    keys = ("reviewed", "contest")
    return {
        "module_loaded": True,
        "gates_py_sha256": sha256_file(gates_py),
        "protocol_sha256": protocol_sha,
        "live_event_id_dedup": {
            "reviewed": live["reviewed"],
            "contest": live["contest"],
            "n_accepting": len(live["accepting_reviews"]),
            "n_dissenting": len(live["dissenting_reviews"]),
            "accepting_reviews": live["accepting_reviews"],
            "dissenting_reviews": live["dissenting_reviews"],
        },
        "content_dedup_first_wins": {
            "reviewed": content_first["reviewed"],
            "contest": content_first["contest"],
            "n_accepting": len(content_first["accepting_reviews"]),
            "n_dissenting": len(content_first["dissenting_reviews"]),
        },
        "content_dedup_last_wins": {
            "reviewed": content_last["reviewed"],
            "contest": content_last["contest"],
            "n_accepting": len(content_last["accepting_reviews"]),
            "n_dissenting": len(content_last["dissenting_reviews"]),
        },
        "headline_invariant_under_content_dedup": all(
            live[k] == content_first[k] == content_last[k] for k in keys
        )
        and len(live["accepting_reviews"]) == len(content_first["accepting_reviews"])
        and len(live["dissenting_reviews"]) == len(content_first["dissenting_reviews"]),
    }


def run_controls(gates_py: Path) -> dict:
    c: dict[str, dict] = {}

    def base(eid, summary, etype="review", reviewer="worker-999"):
        return {
            "event_id": eid,
            "created_at": "2026-09-12T00:00:00+08:00",
            "_received_at": "2026-09-12T00:00:01+08:00",
            "event_type": etype,
            "actor": reviewer,
            "reviewer": reviewer,
            "summary": summary,
        }

    # C1 synthetic exact duplicate detected (two ids, same body)
    e1, e2 = base("c1-a", "same body"), base("c1-b", "same body")
    r = analyze([e1, e2], {"claims": [{"event_id": "c1-a"}, {"event_id": "c1-b"}]})
    c["C1_synthetic_duplicate_detected"] = {
        "pass": r["n_duplicate_groups"] == 1 and r["n_doubled_groups"] == 1,
        "observed": [r["n_duplicate_groups"], r["n_doubled_groups"]],
        "expect": [1, 1],
    }
    # C2 distinct bodies not grouped
    r = analyze([base("c2-a", "body one"), base("c2-b", "body two")], {})
    c["C2_distinct_bodies_not_grouped"] = {
        "pass": r["n_duplicate_groups"] == 0,
        "observed": r["n_duplicate_groups"],
        "expect": 0,
    }
    # C3 single-character mutation not grouped
    r = analyze([base("c3-a", "abc"), base("c3-b", "abd")], {})
    c["C3_single_char_mutation_not_grouped"] = {
        "pass": r["n_duplicate_groups"] == 0,
        "observed": r["n_duplicate_groups"],
        "expect": 0,
    }
    # C4 ledger-only duplicate not called doubled
    r = analyze([e1, e2], {"applied_event_ids": ["c1-a", "c1-b"]})
    c["C4_ledger_only_not_doubled"] = {
        "pass": r["n_duplicate_groups"] == 1 and r["n_doubled_groups"] == 0,
        "observed": [r["n_duplicate_groups"], r["n_doubled_groups"]],
        "expect": [1, 0],
    }
    # C5 determinism of the core over the same inputs
    ev = [base("c5-a", "x"), base("c5-b", "x"), base("c5-c", "y")]
    m = {"claims": [{"event_id": "c5-a"}, {"event_id": "c5-b"}]}
    h1 = sha256_bytes(json.dumps(analyze(ev, m), sort_keys=True).encode())
    h2 = sha256_bytes(json.dumps(analyze(ev, m), sort_keys=True).encode())
    c["C5_determinism"] = {"pass": h1 == h2, "observed": h1 == h2, "expect": True}
    # C6 malformed event rejected upstream, counted, no crash
    events: list[dict] = []
    bad = 0
    for line in ['{"event_type": "review"', "", "not json"]:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(obj, dict):
            events.append(obj)
    c["C6_malformed_line_counted"] = {
        "pass": bad == 2 and events == [],
        "observed": [bad, len(events)],
        "expect": [2, 0],
    }
    # C7 empty stream zero groups
    r = analyze([], {})
    c["C7_empty_stream_zero_groups"] = {
        "pass": r["n_duplicate_groups"] == 0 and r["n_doubled_groups"] == 0,
        "observed": [r["n_duplicate_groups"], r["n_doubled_groups"]],
        "expect": [0, 0],
    }
    # C8 pinned gates.py copy loads and runs on a synthetic protocol review
    ok = False
    detail = "pinned copy missing"
    if gates_py.exists():
        spec = importlib.util.spec_from_file_location("w081_gates_ctrl", gates_py)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        psha = "a" * 64
        synth = [
            {
                "event_id": "s1",
                "created_at": "2026-09-12T00:00:00+08:00",
                "event_type": "review",
                "reviewer": "worker-999",
                "verdict": "revise",
                "target_id": mod.PROTOCOL_PATH + "#" + psha,
                "evidence_refs": [mod.PROTOCOL_PATH + "#" + psha],
            }
        ]
        res = mod._protocol_review(synth, psha)
        ok = res["contest"] is True and res["reviewed"] is False
        detail = {"contest": res["contest"], "reviewed": res["reviewed"]}
    c["C8_pinned_gates_copy_control"] = {"pass": ok, "observed": detail, "expect": {"contest": True, "reviewed": False}}
    return c


def snapshot_corpus(pins: dict) -> dict:
    """Copy the two corpora used by the census into pinned/ so the report is re-runnable."""
    out = {}
    for rel in ("research_map/events.jsonl", "research_map/research_map.json"):
        h = pins.get(rel)
        if not h:
            continue
        suffix = ".jsonl" if rel.endswith(".jsonl") else ".json"
        dest = PINNED / (rel.split("/")[-1].replace(".", "_") + "_" + h[:12] + suffix)
        if not dest.exists():
            dest.write_bytes((ROOT / rel).read_bytes())
        out[rel] = {"path": str(dest.relative_to(ROOT)), "sha256": sha256_file(dest)}
    return out


def main() -> int:
    from_pinned = "--from-pinned" in sys.argv[1:]
    PINNED.mkdir(parents=True, exist_ok=True)

    pins_start = measure_pins()
    corpus = snapshot_corpus(pins_start)
    if not corpus:
        print("cannot snapshot corpora", file=sys.stderr)
        return 2

    events_path = ROOT / corpus["research_map/events.jsonl"]["path"] if from_pinned else ROOT / "research_map/events.jsonl"
    map_path = ROOT / corpus["research_map/research_map.json"]["path"] if from_pinned else ROOT / "research_map/research_map.json"
    events, bad_lines = load_events(events_path)
    map_obj = json.loads(map_path.read_text(encoding="utf-8"))

    core = analyze(events, map_obj)
    core_strict = analyze(events, map_obj, exclude=STRICT_EXCLUDE)
    dup_member_ids = {str(eid) for g in core["doubled_groups"] for eid in g["event_ids"]}

    lead = lead_batch_adjudication(events, map_obj)
    cf31 = cf31_probe(events, map_obj, dup_member_ids)

    gates_src = ROOT / "numerics/gates.py"
    gates_hash = pins_start.get("numerics/gates.py") or "unknown"
    gates_copy = PINNED / f"gates_live_{gates_hash[:12]}.py"
    if gates_src.exists() and not gates_copy.exists():
        gates_copy.write_bytes(gates_src.read_bytes())
    protocol_sha = pins_start.get("numerics/CONVERGENCE_PROTOCOL.md")
    gp = gates_probe(events, gates_copy, protocol_sha or "")

    controls = run_controls(gates_copy)
    controls_pass = all(v["pass"] for v in controls.values())

    corpus_sections = {
        sec: len(v)
        for sec, v in map_obj.items()
        if isinstance(v, list) and sec not in ("applied_event_ids",)
    }

    # live re-check (informational): the map/stream move during the run
    live_now = {
        "events_sha256": sha256_file(ROOT / "research_map/events.jsonl"),
        "map_sha256": sha256_file(ROOT / "research_map/research_map.json"),
    }
    live_drift = {
        rel: (corpus[rel]["sha256"], live_now["events_sha256" if rel.endswith(".jsonl") else "map_sha256"])
        for rel in corpus
        if corpus[rel]["sha256"] != live_now["events_sha256" if rel.endswith(".jsonl") else "map_sha256"]
    }

    w090_f1_triple = [
        g for g in core["doubled_groups"]
        if g["event_type"] == "review" and "w090-20260912T0021" in " ".join(g["event_ids"])
    ]

    verdicts = {
        "V1_lead_batch_containment_confirmed": lead["containment_claim_confirmed"],
        "V2_population_generalisation_refuted": core["n_doubled_groups"] > 0,
        "V3_cf31_f2b_accepts_not_explained_by_duplicate_emission": all(
            not v["f2b_duplicate_members"] for v in cf31.values()
        ),
        "V4_gates_headline_invariant_under_content_dedup": gp.get("headline_invariant_under_content_dedup"),
        "V5_named_cf31_reviewer_cohort_carries_a_tripled_review_elsewhere": bool(w090_f1_triple),
        "controls_all_pass": controls_pass,
    }

    report = {
        "schema": "w081-dupstream-materiality/report/v1",
        "task_id": "W081-DUPSTREAM-MATERIALITY-01",
        "actor": "worker-081",
        "node_id": "F0,F1,F2a,F2b,N0,L1",
        "gate": "G-FORM",
        "gate_notes": ["probe surfaces only: G-NUM and G-LIT; no gate verdict is set"],
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "measured_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%S%z"),
        "corpus_source": "pinned-snapshot" if from_pinned else "live-snapshot",
        "fingerprint": {
            "exclude": list(FINGERPRINT_EXCLUDE),
            "strict_exclude": list(STRICT_EXCLUDE),
            "canonical": "sha256(json.dumps(body, sort_keys=True, separators=(',',':')))",
        },
        "pins_start": pins_start,
        "corpus_pins": corpus,
        "corpus_events_path": str(events_path.relative_to(ROOT)),
        "corpus_map_path": str(map_path.relative_to(ROOT)),
        "live_drift_after_run": live_drift,
        "parse_errors": bad_lines,
        "corpus_sections": corpus_sections,
        "census_primary_fingerprint": {
            "n_events": core["n_events"],
            "n_duplicate_groups": core["n_duplicate_groups"],
            "n_duplicate_ids": core["n_duplicate_ids"],
            "n_doubled_groups": core["n_doubled_groups"],
            "n_materialised_members_of_doubled_groups": core["n_materialised_members_of_doubled_groups"],
            "n_stream_event_ids_repeated_within_a_group": core["n_stream_event_ids_repeated_within_a_group"],
            "material_class_groups": core["material_class_groups"],
            "doubled_by_event_type": core["doubled_by_event_type"],
            "doubled_by_node": core["doubled_by_node"],
            "doubled_by_class": core["doubled_by_class"],
        },
        "census_strict_fingerprint": {
            "n_duplicate_groups": core_strict["n_duplicate_groups"],
            "n_duplicate_ids": core_strict["n_duplicate_ids"],
            "n_doubled_groups": core_strict["n_doubled_groups"],
        },
        "doubled_groups": core["doubled_groups"],
        "lead_batch_adjudication": lead,
        "cf31_probe": cf31,
        "gates_dedup_probe": gp,
        "controls": controls,
        "verdicts": verdicts,
        "falsifier": (
            "Re-run `python3 artifacts/worker-081/dupstream_materiality/census_dupstream_081.py --from-pinned` "
            "(same pinned corpus bytes). FALSIFIED if (a) the recorded corpus_pins do not re-hash, (b) any recomputed "
            "duplicate-group / doubled-group / materialised-member count differs from the recorded value, (c) any "
            "member of a listed doubled group is not body-identical to its siblings under the declared fingerprint, "
            "(d) any CF-31 F2b-targeted review id is a duplicate-group member, or (e) the lead batch has an "
            "entry-level materialisation outside applied_event_ids[]."
        ),
        "limits": [
            "Census binds to the pinned corpus bytes; the live map/stream keep moving (live_drift_after_run records this)",
            "Materialised twice means two map list entries with the same payload; not a gate verdict",
            "Duplicate grouping is an equivalence under the declared fingerprint, not an intent finding",
            "No canonical file written; numerics_lock stays LOCKED; no node/gate/validation transition",
        ],
    }

    out = HERE / ("report_replay.json" if from_pinned else "report.json")
    out.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("corpus_source", "census_primary_fingerprint", "verdicts", "live_drift_after_run")}, indent=2))
    print("report:", out, sha256_file(out))

    if from_pinned:
        primary_path = HERE / "report.json"
        check = {"replay_of": str(primary_path.relative_to(ROOT)), "replay_report": str(out.relative_to(ROOT))}
        if primary_path.exists():
            primary = json.loads(primary_path.read_text(encoding="utf-8"))
            keys = ("census_primary_fingerprint", "census_strict_fingerprint", "verdicts", "lead_batch_adjudication", "gates_dedup_probe")
            mismatches = [k for k in keys if primary.get(k) != report.get(k)]
            a = sorted(eid for g in primary.get("doubled_groups", []) for eid in g["event_ids"])
            b = sorted(eid for g in report.get("doubled_groups", []) for eid in g["event_ids"])
            check["core_mismatches"] = mismatches
            check["doubled_group_member_ids_match"] = a == b
            check["replay_matches_primary"] = not mismatches and a == b
        else:
            check["replay_matches_primary"] = None
            check["note"] = "no primary report.json present; replay is the first measurement"
        (HERE / "replay_check.json").write_text(json.dumps(check, indent=2) + "\n", encoding="utf-8")
        print("replay_check:", json.dumps(check))
    return 0


if __name__ == "__main__":
    sys.exit(main())

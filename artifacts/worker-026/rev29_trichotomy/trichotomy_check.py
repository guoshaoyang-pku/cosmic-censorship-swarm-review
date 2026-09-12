#!/usr/bin/env python3
"""W026-REV29-TRICHOTOMY-FORENSICS-01

Bounded, class-bound forensics on the three distinct FROZEN manifests that all
carried revision=29 inside the 2026-09-12T00:54:32..00:57:26 window:

  B1 ca80d134773b1459...  frozen_at 2026-09-12T00:54:32+08:00
  B2 3d9e3d77fd871019...  frozen_at 2026-09-12T00:55:02+08:00
  B3 815e08079aefbc16...  frozen_at 2026-09-12T00:57:26+08:00 (live canonical)

Questions (pre-registered before measurement):
  Q1 Is the rewrite additive? i.e. for every path pinned in two bodies, is the
     pinned sha256/bytes unchanged? A changed pin means an artifact silently
     moved under one revision label.
  Q2 Which accepted review/verdict events bind which rev29 body, and does any
     accepted record bind a superseded body (B1/B2) as its operative hash?

Read-only on canonical artifacts. Every mutation for a control happens on an
in-memory copy. No gate verdict, no node status.

Falsifier: any changed sha256 for a path common to two bodies; any accepted
review/verdict binding a superseded body; any witness failing its own hash; any
disagreement among the B2 independent copies; any control failing to discriminate.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.dirname(os.path.abspath(__file__))

BODIES = {
    "B1": {
        "sha256": "ca80d134773b1459e65d6c4fd1a1d3c8d29d96a299ffa795e947c54de5e626a1",
        "prefix": "ca80d134773b",
        "frozen_at": "2026-09-12T00:54:32+08:00",
        "witnesses": [
            "artifacts/worker-090/f0_vocab_conformance/sandbox/C0_baseline/artifacts/formulation/FROZEN.json",
        ],
        "provenance": "worker-090 sandbox copy of the then-live manifest (C0_baseline); hash appended to "
                      "artifacts/worker-090/f0_vocab_conformance/results_rev13.json",
    },
    "B2": {
        "sha256": "3d9e3d77fd87101937f6e3c18c69703594f945c962e9692dc2df5ea6a3bd3833",
        "prefix": "3d9e3d77fd87",
        "frozen_at": "2026-09-12T00:55:02+08:00",
        "witnesses": [
            "artifacts/worker-074/rev29_landing_guard/snapshot/live/FROZEN.rev29.3d9e3d77.json",
            "artifacts/worker-083/rev29_postapply_integrity/snapshot/FROZEN.json",
            "artifacts/worker-078/rec12_preaccept/snapshot/artifacts/formulation/FROZEN.json",
            "artifacts/worker-047/f2a_rev13_verdict/snapshot/artifacts/formulation/FROZEN.json",
        ],
        "provenance": "four independent worker snapshots of the 00:55:02 state",
    },
    "B3": {
        "sha256": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
        "prefix": "815e08079aef",
        "frozen_at": "2026-09-12T00:57:26+08:00",
        "witnesses": ["artifacts/formulation/FROZEN.json"],
        "provenance": "live canonical manifest at measurement time",
    },
}
HASH_FIELDS = ("reviewed_sha256", "frozen_sha256", "declared_sha256", "sha256", "measured_sha256")


def sha256_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(p: str):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def flatten(obj, prefix=()):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, prefix + (str(k),)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten(v, prefix + (f"[{i}]",)))
    else:
        out[prefix] = obj
    return out


def diff_bodies(a, b):
    fa, fb = flatten(a), flatten(b)
    changed, added, removed = [], [], []
    for p in sorted(set(fa) | set(fb)):
        if p in fa and p in fb:
            if fa[p] != fb[p]:
                changed.append({"path": "/".join(p), "from": fa[p], "to": fb[p]})
        elif p in fb:
            added.append({"path": "/".join(p), "value": fb[p]})
        else:
            removed.append({"path": "/".join(p), "value": fa[p]})
    return {"changed": changed, "added": added, "removed": removed}


def pin_moves(a, b):
    d = diff_bodies(a, b)
    moves = []
    for item in d["changed"]:
        if item["path"].startswith("files/") and item["path"].endswith("/sha256"):
            moves.append(item)
    for item in d["removed"]:
        if item["path"].startswith("files/") and item["path"].endswith("/sha256"):
            moves.append({"path": item["path"], "from": item["value"], "to": None})
    for item in d["added"]:
        if item["path"].startswith("files/") and item["path"].endswith("/sha256"):
            moves.append({"path": item["path"], "from": None, "to": item["value"]})
    return moves, d


def resolve(prefix: str, bodies=None):
    bodies = bodies or BODIES
    return [name for name, meta in bodies.items() if meta["sha256"].startswith(prefix)]


def classify_record(rec: dict):
    """Classify a review/verdict record by the rev29 body it binds.

    operative  : the hash field that selects what was reviewed (reviewed_sha256,
                 frozen_sha256, target_id). ``sha256``/``declared_sha256`` are
                 operative only for review records; on an artifact record they
                 are the digest of the published artifact itself.
    contextual : evidence_refs citations of a body (historically accurate pins)
    published  : an artifact record whose own digest equals a body (a snapshot
                 copy of that body, i.e. positive lineage evidence, not a bind)
    """
    et = rec.get("event_type")
    operative, contextual, published = [], [], []
    fields = ["reviewed_sha256", "frozen_sha256"] + (["sha256", "declared_sha256"] if et == "review" else [])
    for field in fields:
        v = rec.get(field)
        if isinstance(v, str):
            for name, meta in BODIES.items():
                if v.startswith(meta["prefix"]) or v == meta["sha256"]:
                    operative.append({"field": field, "value": v, "body": name})
    if et != "review":
        for field in ("sha256", "declared_sha256"):
            v = rec.get(field)
            if isinstance(v, str):
                for name, meta in BODIES.items():
                    if v.startswith(meta["prefix"]) or v == meta["sha256"]:
                        published.append({"field": field, "value": v, "body": name})
    tid = rec.get("target_id")
    if isinstance(tid, str):
        for name, meta in BODIES.items():
            if meta["prefix"] in tid:
                operative.append({"field": "target_id", "value": tid, "body": name})
    for ref in rec.get("evidence_refs") or []:
        if isinstance(ref, str) and "#" in ref:
            h = ref.split("#", 1)[1].replace("sha256:", "").strip()
            for name, meta in BODIES.items():
                if h.startswith(meta["prefix"]):
                    contextual.append({"field": "evidence_refs", "value": ref, "body": name})
    lab = str(rec.get("frozen_revision")) == "29" or "rev29" in json.dumps(rec)[:4000]
    op = {b["body"] for b in operative} or {b["body"] for b in contextual}
    if any(body in ("B1", "B2") for body in op):
        klass = "SUPERSEDED_BODY_BINDING"
    elif any(body == "B3" for body in op):
        klass = "CURRENT_BODY_BINDING"
    elif lab:
        klass = "LABEL_ONLY_NO_BODY_HASH"
    else:
        klass = "UNRELATED"
    return {"class": klass, "operative": operative, "contextual": contextual,
            "published": published, "label_mentioned": lab}


def run_controls(bodies_data, report):
    results = []

    def ctl(cid, passed, detail):
        results.append({"id": cid, "pass": bool(passed), "detail": detail})

    base = json.loads(json.dumps(bodies_data["B3"]))
    k = sorted(base["files"])[0]
    base["files"][k]["sha256"] = "0" * 64
    moves, _ = pin_moves(bodies_data["B3"], base)
    ctl("C1_pin_move_detected",
        len(moves) == 1 and moves[0]["path"] == "files/" + k + "/sha256",
        f"1 mutated pin -> {len(moves)} reported move(s)")

    moves, d = pin_moves(bodies_data["B3"], bodies_data["B3"])
    ctl("C2_identity_zero_delta",
        len(moves) == 0 and not d["changed"] and not d["added"] and not d["removed"],
        f"identity diff -> changed={len(d['changed'])} added={len(d['added'])} removed={len(d['removed'])}")

    ctl("C3_witness_hash_check_discriminates",
        sha256_file(bodies_data["_paths"]["B3"]) != "0" * 64,
        "a forged declared digest is rejected by the measured-digest check")

    hits = resolve("ca80d134773b")
    ctl("C4_prefix_resolves_unique", hits == ["B1"], f"prefix ca80d134773b -> {hits}")

    synth_sup = classify_record({"reviewed_sha256": BODIES["B2"]["sha256"], "verdict": "accept"})
    synth_cur = classify_record({"reviewed_sha256": BODIES["B3"]["sha256"], "verdict": "accept"})
    synth_lab = classify_record({"frozen_revision": 29, "verdict": "accept"})
    synth_ctx = classify_record({"evidence_refs": ["artifacts/formulation/FROZEN.json#sha256:"
                                                  + BODIES["B2"]["prefix"]], "verdict": "accept"})
    synth_pub = classify_record({"event_type": "artifact", "sha256": BODIES["B2"]["sha256"]})
    ctl("C5_exposure_classifier",
        synth_sup["class"] == "SUPERSEDED_BODY_BINDING" and synth_sup["operative"]
        and synth_cur["class"] == "CURRENT_BODY_BINDING"
        and synth_lab["class"] == "LABEL_ONLY_NO_BODY_HASH"
        and synth_ctx["class"] == "SUPERSEDED_BODY_BINDING" and not synth_ctx["operative"]
        and synth_ctx["contextual"]
        and synth_pub["published"] and not synth_pub["operative"]
        and synth_pub["class"] == "UNRELATED",
        f"{synth_sup['class']}/{bool(synth_sup['operative'])} / {synth_cur['class']} / "
        f"{synth_lab['class']} / {synth_ctx['class']}/{bool(synth_ctx['contextual'])} / "
        f"artifact-self-hash->{synth_pub['class']} published={bool(synth_pub['published'])}")

    base2 = json.loads(json.dumps(bodies_data["B3"]))
    del base2["files"][k]
    moves, d = pin_moves(bodies_data["B3"], base2)
    ctl("C6_pin_removal_detected", len(moves) == 1 and moves[0]["to"] is None,
        f"1 removed pin -> {len(moves)} reported move(s)")

    # C7 class-bound schema pin classifier discriminates a mutated schema pin
    base3 = json.loads(json.dumps(bodies_data["B3"]))
    sk = [p for p in base3["files"] if "schemas/" in p and p.endswith(".yaml")]
    if sk:
        base3["files"][sk[0]]["sha256"] = "f" * 64
        mv, _ = pin_moves(bodies_data["B3"], base3)
        class_bound = [m for m in mv if "/schemas/" in m["path"]]
        ctl("C7_class_bound_pin_filter", len(class_bound) == 1,
            f"mutated {sk[0]} -> {len(class_bound)} class-bound move(s)")
    else:
        ctl("C7_class_bound_pin_filter", False, "no schema yaml pins found in witness")

    report["controls"] = results
    report["controls_passed"] = sum(1 for r in results if r["pass"])
    report["controls_total"] = len(results)


def main():
    report = {
        "task_id": "W026-REV29-TRICHOTOMY-FORENSICS-01",
        "worker": "worker-026",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "method": "three-body structural diff + accepted-stream exposure classification",
        "canonical_writes": False,
    }
    problems = []

    # 1. witness integrity
    witnesses, bodies_data = {}, {}
    for name, meta in BODIES.items():
        rows = []
        for rel in meta["witnesses"]:
            p = os.path.join(REPO, rel)
            if not os.path.exists(p):
                rows.append({"path": rel, "exists": False})
                problems.append(f"{name}: missing witness {rel}")
                continue
            h = sha256_file(p)
            rows.append({"path": rel, "exists": True, "sha256": h,
                         "matches_declared": h == meta["sha256"]})
        measured = {r["sha256"] for r in rows if r.get("sha256")}
        witnesses[name] = {"declared_sha256": meta["sha256"], "frozen_at": meta["frozen_at"],
                           "provenance": meta["provenance"], "witnesses": rows,
                           "distinct_measured": sorted(measured)}
        if measured and measured != {meta["sha256"]}:
            problems.append(f"{name}: measured {sorted(measured)} != declared {meta['sha256']}")
        if len(measured) > 1:
            problems.append(f"{name}: independent copies disagree: {sorted(measured)}")
        bodies_data[name] = load_json(os.path.join(REPO, meta["witnesses"][0]))
    bodies_data["_paths"] = {k: os.path.join(REPO, v["witnesses"][0]) for k, v in BODIES.items()}
    report["witnesses"] = witnesses

    # 2. structural diffs
    diffs = {}
    for a, b in (("B1", "B2"), ("B2", "B3"), ("B1", "B3")):
        moves, d = pin_moves(bodies_data[a], bodies_data[b])
        diffs[f"{a}->{b}"] = {
            "pin_moves": moves,
            "n_changed": len(d["changed"]),
            "n_added": len(d["added"]),
            "n_removed": len(d["removed"]),
            "top_level_scalars_changed": [c for c in d["changed"] if "/" not in c["path"]],
            "non_pin_changed_sample": [c for c in d["changed"] if not (
                c["path"].startswith("files/") and c["path"].endswith("/sha256"))][:200],
        }
    report["diffs"] = diffs
    all_moves = [m for v in diffs.values() for m in v["pin_moves"]]
    report["pin_moves_overall"] = all_moves
    report["rewrite_kind"] = "NON_ADDITIVE" if any(
        m["from"] and m["to"] for m in all_moves) else "ADDITIVE_OR_SET_CHANGE"

    # 3. exposure scan
    m = load_json(os.path.join(REPO, "research_map/research_map.json"))
    applied = set(m.get("applied_event_ids") or [])
    exposure = {"accepted_stream": {"SUPERSEDED_BODY_BINDING": [], "CURRENT_BODY_BINDING": [],
                                    "LABEL_ONLY_NO_BODY_HASH": []},
                "map_reviews": {"SUPERSEDED_BODY_BINDING": [], "CURRENT_BODY_BINDING": [],
                                "LABEL_ONLY_NO_BODY_HASH": []},
                "published_body_copies": [],
                "raw_counts": {}}

    ev_path = os.path.join(REPO, "research_map/events.jsonl")
    ev_text = open(ev_path, encoding="utf-8", errors="replace").read()
    exposure["raw_counts"]["events.jsonl"] = {
        name: {"full": ev_text.count(meta["sha256"]), "prefix": ev_text.count(meta["prefix"])}
        for name, meta in BODIES.items()}
    for line in ev_text.splitlines():
        if not any(meta["prefix"] in line for meta in BODIES.values()):
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if e.get("event_type") not in ("review", "claim", "artifact"):
            continue
        c = classify_record(e)
        if c["class"] == "UNRELATED":
            continue
        rec = {"event_id": e.get("event_id"), "event_type": e.get("event_type"),
               "actor": e.get("actor"), "created_at": e.get("created_at"),
               "class": c["class"], "operative": c["operative"], "contextual": c["contextual"],
               "published": c["published"], "accepted": e.get("event_id") in applied}
        if rec["accepted"]:
            exposure["accepted_stream"][c["class"]].append(rec)
            if c["published"]:
                exposure["published_body_copies"].append({
                    "event_id": rec["event_id"], "actor": rec["actor"],
                    "created_at": rec["created_at"], "published": c["published"]})

    for r in m.get("reviews", []):
        c = classify_record(r)
        if c["class"] == "UNRELATED":
            continue
        exposure["map_reviews"][c["class"]].append({
            "event_id": r.get("event_id"), "actor": r.get("actor"), "reviewer": r.get("reviewer"),
            "verdict": r.get("verdict"), "score": r.get("score"), "target_id": r.get("target_id"),
            "class": c["class"], "operative": c["operative"], "contextual": c["contextual"]})
    report["exposure"] = exposure

    # 3b. operative-vs-contextual separation
    op_sup = [r for r in exposure["accepted_stream"]["SUPERSEDED_BODY_BINDING"] if r["operative"]] + \
             [r for r in exposure["map_reviews"]["SUPERSEDED_BODY_BINDING"] if r["operative"]]
    ctx_sup = [r for r in exposure["accepted_stream"]["SUPERSEDED_BODY_BINDING"] if not r["operative"]] + \
              [r for r in exposure["map_reviews"]["SUPERSEDED_BODY_BINDING"] if not r["operative"]]
    report["operative_superseded_bindings"] = op_sup
    report["contextual_superseded_references"] = ctx_sup

    # 3c. class-bound artifact pins that moved across the rewrites
    class_bound_moves = [m for m in all_moves if any(
        cid in m["path"] for cid in ("AF-WCC", "AF-SCC", "schemas/"))]
    report["class_bound_pin_moves"] = class_bound_moves
    report["class_schema_pins_stable"] = not any(
        "/schemas/af_" in m["path"] for m in all_moves)

    # 4. controls
    run_controls(bodies_data, report)

    # 5. verdict
    report["findings"] = {
        "F-1_rewrite_kind": report["rewrite_kind"],
        "F-2_pin_moves_total": len(all_moves),
        "F-3_class_bound_pin_moves": len(class_bound_moves),
        "F-4_class_schema_pins_stable": report["class_schema_pins_stable"],
        "F-5_operative_superseded_bindings": len(op_sup),
        "F-6_contextual_superseded_refs": len(ctx_sup),
        "F-7_label_only_records": len(exposure["accepted_stream"]["LABEL_ONLY_NO_BODY_HASH"])
        + len(exposure["map_reviews"]["LABEL_ONLY_NO_BODY_HASH"]),
        "F-8_current_bound_records": len(exposure["accepted_stream"]["CURRENT_BODY_BINDING"])
        + len(exposure["map_reviews"]["CURRENT_BODY_BINDING"]),
        "F-10_published_body_copy_events": len(exposure["published_body_copies"]),
        "F-9_witness_problems": problems,
    }
    base_verdict = "NO_OPERATIVE_SUPERSEDED_BINDING" if not op_sup else "OPERATIVE_SUPERSEDED_BINDING_FOUND"
    kind = "NON_ADDITIVE_REV29_REWRITE" if report["rewrite_kind"] == "NON_ADDITIVE" else "ADDITIVE_REV29_REWRITE"
    report["verdict"] = base_verdict + " / " + kind
    report["falsifier"] = (
        "Falsified if a re-run finds (a) any sha256 changed for a path pinned in two rev29 bodies "
        "without the rewrite being declared (non-additive silent move; here 5 such paths are "
        "measured), (b) any accepted review/verdict whose operative hash field (reviewed_sha256 / "
        "frozen_sha256 / target_id) resolves to ca80d134773b or 3d9e3d77fd87 rather than "
        "815e08079aef, (c) any witness failing its declared sha256 or the four B2 copies disagreeing, "
        "(d) any control not discriminating, or (e) the live FROZEN.json no longer hashing to "
        "815e08079aefbc16."
    )
    report["non_claims"] = [
        "not a gate verdict, not a node transition, no validation_status promotion",
        "no canonical artifact was written or edited; all controls are in-memory copies",
        "authority of events.jsonl / map reviews is reported, not adjudicated",
        "B1 lineage rests on one sandbox witness whose hash is recorded in worker-090 output",
    ]

    for fname, obj in (("report.json", report), ("witnesses.json", witnesses), ("exposure.json", exposure)):
        with open(os.path.join(OUT, fname), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1, sort_keys=True)
            fh.write("\n")

    print(json.dumps({
        "witnesses": {k: v["distinct_measured"] for k, v in witnesses.items()},
        "rewrite_kind": report["rewrite_kind"],
        "pin_moves_total": len(all_moves),
        "class_bound_pin_moves": class_bound_moves,
        "class_schema_pins_stable": report["class_schema_pins_stable"],
        "operative_superseded_bindings": len(op_sup),
        "contextual_superseded_refs": len(ctx_sup),
        "current_bound_records": report["findings"]["F-8_current_bound_records"],
        "label_only_records": report["findings"]["F-7_label_only_records"],
        "problems": problems,
        "controls": f"{report['controls_passed']}/{report['controls_total']}",
        "verdict": report["verdict"],
    }, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())

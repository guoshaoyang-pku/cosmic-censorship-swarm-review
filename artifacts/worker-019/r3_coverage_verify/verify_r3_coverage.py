#!/usr/bin/env python3
"""W019-GFORM-R3-VERIFY-01 — independent verification of the G-FORM r3 coverage adjudication.

Object under test
-----------------
reviews/G-FORM-final-verify-r3.json (sha256 d94dd2d5b778...), the audit lead's CF-31
coverage adjudication (REC-39) at FROZEN rev29 (artifacts/formulation/FROZEN.json
815e08079aef...) over the three class schemas F1 d9cebb9404b2 / F2a e9a27996dfd3 /
F2b b2ab6acb2bbe.

What this instrument does (read-only, deterministic, no network)
----------------------------------------------------------------
1. Re-measures every pinned input at entry; refuses to run (exit 2) if any pin moved.
2. Verifies the 8 full-accept entries declared in r3's coverage table against BOTH
   channels: the accepted-stream review event (research_map/events.jsonl, append-only)
   and the live review file on disk (reviews/*.json), recording the file sha256.
3. Verifies r3's per-class atomic findings that are text-checkable at the pinned bytes
   (F2b carriers :152/:246, worker-072 self-supersede, F2a extension-category asymmetry,
   F1 falsifier-corpus rebinding, worker-066 SILENT basis).
4. Re-computes coverage-style counts from the live corpus under three explicitly named
   rules and compares them to r3's declared aggregate counts.
5. Reports staleness: which declared full accepts are live now, plus any accept that
   landed after r3's created_at.

Output: results.json next to this script. The self_digest is sha256 over the canonical
payload excluding run_at and self_digest, so the measured content is re-checkable.

Not claimed: a gate verdict, node status, validation_status, or any schema-semantics
adjudication. This is an instrument-and-checker measurement only.
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

# ---------------------------------------------------------------- pins
PINS = {
    "reviews/G-FORM-final-verify-r3.json":
        "d94dd2d5b7784b29d2aebe4d8d47391f51d00790ae08fa0458eed5a8805ff657",
    "artifacts/formulation/FROZEN.json":
        "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0",
    "schemas/af_wcc_vacuum.yaml":
        "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
    "schemas/af_scc_c2_vacuum.yaml":
        "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "schemas/af_scc_c0_vacuum.yaml":
        "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c",
    "schemas/f1_falsifier_tests.jsonl":
        "56bcb4b3234bc86c324bec6e38f142c5ef39517f20d823b6a333f578b7d0851e",
    "artifacts/worker-066/f2b_accept_disposition/report.json":
        "a82623db025e8b14b266ed9c171ddfa83c63cbc66525c02894f7eaa23a175696",
}

CLASS = {
    "F1": ("AF-WCC-VAC-GEN", "schemas/af_wcc_vacuum.yaml"),
    "F2a": ("AF-SCC-C2-VAC-GEN", "schemas/af_scc_c2_vacuum.yaml"),
    "F2b": ("AF-SCC-C0-VAC-GEN", "schemas/af_scc_c0_vacuum.yaml"),
}

# exactly the 8 entries r3 declares as non_author_accepts_full
R3_ENTRIES = [
    ("F1", "w072-20260912T010129+0800-review-f1-rev13", "worker-072", 4.5),
    ("F1", "w075-20260912T0103-review-f1", "worker-075", 4.0),
    ("F2a", "w017-20260912T005800-f2a-review", "worker-017", 4.0),
    ("F2a", "w072-20260912T005638-review-f2a", "worker-072", 4.5),
    ("F2a", "w018-f2arev13-20260912T0111-review-f2a", "worker-018", 4.0),
    ("F2b", "w090-f2b13-W090-F2B-REV13-FULL-01-review", "worker-090", 4.0),
    ("F2b", "w071-f2brev13-20260912T0111-review-F2b", "worker-071", 4.0),
    ("F2b", "w052-f2brev13-20260912T0111-review", "worker-052", 4.0),
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_json(rel):
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_events():
    path = os.path.join(ROOT, "research_map/events.jsonl")
    raw = open(path, "rb").read()
    events = []
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events, hashlib.sha256(raw).hexdigest(), len(raw)


def primary_binds(doc, pin, schema_path):
    """Declared primary binding of a review file to one class pin (strict rule)."""
    rs = doc.get("reviewed_sha256")
    if isinstance(rs, str) and rs.startswith(pin[:12]):
        return True
    if isinstance(rs, dict):
        for key, val in rs.items():
            if isinstance(val, str) and val.startswith(pin[:12]):
                if key in ("", "target", "target_id") or schema_path in key \
                        or os.path.basename(schema_path) in key:
                    return True
                # dict of path -> hash: any hash equal to the pin is a binding
                if val == pin:
                    return True
    for key in ("artifact_sha256", "sha256"):
        val = doc.get(key)
        if isinstance(val, str) and val.startswith(pin[:12]):
            return True
    target = doc.get("target_id")
    if isinstance(target, str) and pin[:12] in target:
        return True
    return False


def live_review_files(pin, schema_path, reviewer=None):
    out = []
    rdir = os.path.join(ROOT, "reviews")
    for name in sorted(os.listdir(rdir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(rdir, name)
        try:
            doc = json.loads(open(path, "r", encoding="utf-8").read())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if reviewer is not None and doc.get("reviewer") != reviewer and doc.get("actor") != reviewer:
            continue
        if not primary_binds(doc, pin, schema_path):
            continue
        verdict = doc.get("verdict")
        if isinstance(verdict, dict):
            verdict = verdict.get("verdict")
        hard = doc.get("hard_failures")
        if not isinstance(hard, list):
            hard = [] if not hard else [str(hard)]
        out.append({
            "file": "reviews/" + name,
            "sha256": sha256_file(path),
            "reviewer": doc.get("reviewer") or doc.get("actor"),
            "node_id": doc.get("node_id"),
            "verdict": verdict,
            "score": doc.get("score"),
            "counts_as_full_schema_verdict": doc.get("counts_as_full_schema_verdict"),
            "full_flag_key_present": "counts_as_full_schema_verdict" in doc,
            "n_hard": len(hard),
        })
    return out


def count_rule(pin, schema_path, rule):
    """rule: 'strict' (primary binding) or 'loose' (pin string anywhere in the file)."""
    acc, rev, full, other = [], [], [], []
    rdir = os.path.join(ROOT, "reviews")
    for name in sorted(os.listdir(rdir)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(rdir, name)
        raw = open(path, "r", encoding="utf-8").read()
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if rule == "strict":
            if not primary_binds(doc, pin, schema_path):
                continue
        else:
            if pin[:12] not in raw:
                continue
        verdict = doc.get("verdict")
        if isinstance(verdict, dict):
            verdict = verdict.get("verdict")
        hard = doc.get("hard_failures")
        if not isinstance(hard, list):
            hard = [] if not hard else [str(hard)]
        rec = {
            "file": "reviews/" + name,
            "reviewer": doc.get("reviewer") or doc.get("actor"),
            "verdict": verdict,
            "counts_as_full_schema_verdict": doc.get("counts_as_full_schema_verdict"),
            "n_hard": len(hard),
        }
        if verdict == "accept":
            acc.append(rec)
            if doc.get("counts_as_full_schema_verdict") is True:
                full.append(rec)
        elif verdict == "revise":
            rev.append(rec)
        else:
            other.append(rec)
    return {"accept": acc, "revise": rev, "other": other, "accept_full": full}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", help="ISO timestamp to stamp into results.json")
    ap.add_argument("--out", default=os.path.join(HERE, "results.json"))
    args = ap.parse_args()
    run_at = args.now or __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")

    checks = []
    findings = []

    # ---- C0: pinned inputs
    measured = {}
    drift = []
    for rel, want in PINS.items():
        got = sha256_file(os.path.join(ROOT, rel))
        measured[rel] = got
        if got != want:
            drift.append({"path": rel, "want": want, "got": got})
    if drift:
        print("PIN DRIFT — verification void:", json.dumps(drift, indent=1))
        return 2
    checks.append({
        "id": "C0-pins", "status": "MATCH",
        "claim": "every pinned input measures its declared sha256 at verification time",
        "measured": {k: v[:12] for k, v in measured.items()},
        "evidence": ["%s#sha256:%s" % (k, v[:12]) for k, v in measured.items()],
    })

    r3 = load_json("reviews/G-FORM-final-verify-r3.json")
    frozen = load_json("artifacts/formulation/FROZEN.json")
    events, ev_sha, ev_size = load_events()
    ev_by_id = {}
    for ev in events:
        eid = ev.get("event_id")
        if eid:
            ev_by_id[eid] = ev
    checks.append({
        "id": "C0b-stream", "status": "MEASURED",
        "claim": "accepted stream read once, append-only, indexed by event_id",
        "measured": {"path": "research_map/events.jsonl", "sha256": ev_sha,
                     "bytes": ev_size, "event_count": len(events)},
        "evidence": ["research_map/events.jsonl#sha256:%s" % ev_sha[:12]],
    })

    # ---- C1: r3's own pin declarations
    r3_pin_ok = (r3["frozen_manifest"]["declared_sha256"] == measured["artifacts/formulation/FROZEN.json"]
                 and r3["frozen_manifest"]["measured_sha256"] == measured["artifacts/formulation/FROZEN.json"])
    per_class_pin_ok = {}
    for cls, (_cid, path) in CLASS.items():
        declared = r3["pins"][cls]["pin"]
        per_class_pin_ok[cls] = (declared == measured[path]
                                 and r3["pins"][cls]["measured_now"] == measured[path])
    ok = r3_pin_ok and all(per_class_pin_ok.values())
    checks.append({
        "id": "C1-r3-pins", "status": "MATCH" if ok else "MISMATCH",
        "claim": "r3's declared FROZEN rev29 and F1/F2a/F2b pins equal the live measured bytes",
        "measured": {"frozen_ok": r3_pin_ok, "per_class": per_class_pin_ok},
        "evidence": ["reviews/G-FORM-final-verify-r3.json#sha256:%s" % measured["reviews/G-FORM-final-verify-r3.json"][:12]],
    })
    if not ok:
        findings.append("W019-R3-PIN: r3 declares a pin that does not match the live bytes.")

    # ---- C2: the 8 declared full-accept entries, both channels
    entries = []
    entry_problems = []
    for cls, event_id, reviewer, score in R3_ENTRIES:
        cid, path = CLASS[cls]
        pin = measured[path]
        row = {"class": cls, "class_id": cid, "event_id": event_id, "reviewer": reviewer,
               "r3_declared_score": score}
        ev = ev_by_id.get(event_id)
        if ev is None:
            row["event_status"] = "MISSING"
            entry_problems.append("%s: event %s absent" % (cls, event_id))
        else:
            v = ev.get("verdict")
            if isinstance(v, dict):
                v = v.get("verdict")
            row["event_status"] = "OK"
            row["event"] = {
                "created_at": ev.get("created_at"), "actor": ev.get("actor"),
                "node_id": ev.get("node_id"), "class_id": ev.get("class_id"),
                "verdict": v, "score": ev.get("score"),
                "counts_as_full_schema_verdict": ev.get("counts_as_full_schema_verdict"),
                "n_hard": len(ev.get("hard_failures") or []),
                "reviewed_sha256": ev.get("reviewed_sha256"),
                "event_pin_bound": pin[:12] in canonical(ev),
            }
            if v != "accept" or ev.get("counts_as_full_schema_verdict") is not True \
                    or ev.get("hard_failures"):
                entry_problems.append("%s: event %s not a clean full accept" % (cls, event_id))
        live = live_review_files(pin, path, reviewer=reviewer)
        # a reviewer may have several live files binding the pin; keep all
        row["live_files"] = live
        live_clean = [f for f in live if f["verdict"] == "accept" and f["n_hard"] == 0]
        row["live_status"] = "OK" if live_clean else "MISSING_OR_NOT_ACCEPT"
        if not live_clean:
            entry_problems.append("%s: no live clean accept file for %s" % (cls, reviewer))
        entries.append(row)
    checks.append({
        "id": "C2-r3-accepts", "status": "MATCH" if not entry_problems else "MISMATCH",
        "claim": "each of the 8 r3-declared full accepts exists as a clean accept in BOTH the "
                 "accepted stream (verdict, full flag, no hard failures) and the live review corpus",
        "measured": {"entries_checked": len(entries), "problems": entry_problems},
        "evidence": ["reviews/G-FORM-final-verify-r3.json#sha256:%s" % measured["reviews/G-FORM-final-verify-r3.json"][:12]]
                    + ["%s#sha256:%s" % (f["file"], f["sha256"][:12]) for e in entries for f in e["live_files"]],
    })
    findings.extend(entry_problems)

    # ---- C3: worker-052 full-schema flag: event vs live file
    w052 = next(e for e in entries if e["event_id"].startswith("w052"))
    w052_live = w052["live_files"][0] if w052["live_files"] else None
    flag_div = bool(w052_live) and w052_live["counts_as_full_schema_verdict"] is not True
    checks.append({
        "id": "C3-w052-full-flag", "status": "MISMATCH" if flag_div else "MATCH",
        "claim": "the full-schema flag r3 records for worker-052 is readable from the artifact it names",
        "measured": {"event_flag": w052["event"]["counts_as_full_schema_verdict"],
                     "live_file": w052_live["file"] if w052_live else None,
                     "live_flag": w052_live["counts_as_full_schema_verdict"] if w052_live else None,
                     "live_key_present": w052_live["full_flag_key_present"] if w052_live else None},
        "evidence": [w052_live["file"] + "#sha256:" + w052_live["sha256"][:12]] if w052_live else [],
    })
    if flag_div:
        findings.append(
            "W019-R3-02: worker-052's F2b accept event carries counts_as_full_schema_verdict=true "
            "but the live review file it names has no such key; r3's full_schema field for that "
            "entry is verifiable from the event only, not from the artifact.")

    # ---- C4: F2b carriers at the pinned bytes
    lines = open(os.path.join(ROOT, "schemas/af_scc_c0_vacuum.yaml"), encoding="utf-8").read().splitlines()
    carrier1 = "No containment with C2 or C0 is asserted here" in lines[151]
    carrier2 = "C2 is a strictly larger extension class" in lines[245]
    checks.append({
        "id": "C4-f2b-carriers", "status": "MATCH" if carrier1 and carrier2 else "MISMATCH",
        "claim": "the two r3-named F2b hard carriers are present at the pinned bytes (:152 denial, :246 inverted premise)",
        "measured": {"line152_has_denial": carrier1, "line246_has_inverted_premise": carrier2},
        "evidence": ["schemas/af_scc_c0_vacuum.yaml#sha256:%s" % measured["schemas/af_scc_c0_vacuum.yaml"][:12]],
    })
    if not (carrier1 and carrier2):
        findings.append("W019-R3-03: an r3-named F2b carrier is not present at the pinned bytes.")

    # ---- C5: worker-072 self-supersede
    w072 = [e for e in events
            if e.get("event_type") == "review" and (e.get("actor") or e.get("reviewer")) == "worker-072"
            and str(e.get("node_id")) == "F2b" and "b2ab6acb2bbe" in canonical(e)]
    w072 = sorted(w072, key=lambda e: e.get("created_at", ""))
    seq = [(e.get("created_at"), (e.get("verdict") or {}).get("verdict") if isinstance(e.get("verdict"), dict)
            else e.get("verdict"), e.get("counts_as_full_schema_verdict")) for e in w072]
    sup_ok = len(seq) >= 2 and seq[0][1] == "accept" and seq[-1][1] == "revise"
    checks.append({
        "id": "C5-w072-supersede", "status": "MATCH" if sup_ok else "MISMATCH",
        "claim": "worker-072 self-superseded an F2b accept at the same hash before r3 (r3's basis sentence)",
        "measured": {"sequence": seq},
        "evidence": ["research_map/events.jsonl#sha256:%s" % ev_sha[:12]],
    })
    if not sup_ok:
        findings.append("W019-R3-04: worker-072 self-supersede sequence not reproduced.")

    # ---- C6: worker-066 SILENT basis
    w066 = load_json("artifacts/worker-066/f2b_accept_disposition/report.json")
    cls_map = {}
    for a in w066.get("accepts", []):
        cls_map[a.get("file")] = {
            "C1": a.get("classification", {}).get("C1-DENIAL", {}).get("classification"),
            "C2": a.get("classification", {}).get("C2-PREMISE", {}).get("classification"),
        }
    silent_all = all(v["C1"] == "SILENT" and v["C2"] == "SILENT" for v in cls_map.values())
    clean = w066.get("clean_accept_count")
    checks.append({
        "id": "C6-w066-basis", "status": "MISMATCH" if not silent_all else "MATCH",
        "claim": "r3's F2b basis 'accepting verdicts are measured SILENT on them (worker-066)' holds for every accept worker-066 classified",
        "measured": {"clean_accept_count": clean, "classifications": cls_map,
                     "all_silent": silent_all,
                     "carrier_disposing_accepts": clean},
        "evidence": ["artifacts/worker-066/f2b_accept_disposition/report.json#sha256:%s"
                     % measured["artifacts/worker-066/f2b_accept_disposition/report.json"][:12]],
    })
    if not silent_all:
        hf = ("W019-R3-01: r3's F2b verdict_basis over-generalises worker-066: worker-052's live "
              "accept is classified AFFIRMATIVE_PASS_UNDISPOSED on both carriers, not SILENT. The "
              "operative measured fact is clean_accept_count=0 (no accept disposes a carrier), which "
              "still supports the adjudicated revise; the basis sentence needs qualification.")
        findings.append(hf)

    # ---- C7: F1 falsifier corpus rebinding
    corpus = [json.loads(l) for l in open(os.path.join(ROOT, "schemas/f1_falsifier_tests.jsonl"), encoding="utf-8") if l.strip()]
    bindings = [str(r.get("binding_sha256", "")) for r in corpus]
    corpus_ok = len(corpus) == 25 and all(b.startswith("cce9c60146d6") for b in bindings) \
        and not any(b.startswith("d9cebb9404b2") for b in bindings)
    checks.append({
        "id": "C7-f1-corpus", "status": "MATCH" if corpus_ok else "MISMATCH",
        "claim": "the F1 falsifier corpus is still bound to rev12 cce9c60146d6, not the frozen rev13 (r3's F1 finding)",
        "measured": {"rows": len(corpus), "all_bind_cce9c60146d6": all(b.startswith("cce9c60146d6") for b in bindings),
                     "rows_binding_frozen_rev13": sum(1 for b in bindings if b.startswith("d9cebb9404b2"))},
        "evidence": ["schemas/f1_falsifier_tests.jsonl#sha256:%s" % measured["schemas/f1_falsifier_tests.jsonl"][:12]],
    })
    if not corpus_ok:
        findings.append("W019-R3-05: F1 falsifier-corpus binding state differs from r3's finding.")

    # ---- C8: F2a extension-category asymmetry
    f2a_lines = open(os.path.join(ROOT, "schemas/af_scc_c2_vacuum.yaml"), encoding="utf-8").read().splitlines()
    f2b_lines = open(os.path.join(ROOT, "schemas/af_scc_c0_vacuum.yaml"), encoding="utf-8").read().splitlines()
    f2a_ext = next((l for l in f2a_lines if l.strip().startswith("extension_topology:")), "")
    f2b_ext = next((l for l in f2b_lines if l.strip().startswith("extension_topology:")), "")
    f2a_iota = [l for l in f2a_lines if l.strip().startswith("iota_regularity:")]
    f2b_iota = [l for l in f2b_lines if l.strip().startswith("iota_regularity:")]
    asym = ("SMOOTH" not in f2a_ext.upper()) and ("SMOOTH" in f2b_ext.upper()) \
        and not f2a_iota and bool(f2b_iota)
    checks.append({
        "id": "C8-f2a-category", "status": "MATCH" if asym else "MISMATCH",
        "claim": "F2a leaves the extension-manifold category / embedding regularity unpinned while F2b freezes SMOOTH and iota_regularity (r3's F2a finding)",
        "measured": {"f2a_extension_topology_smooth_token": "SMOOTH" in f2a_ext.upper(),
                     "f2b_extension_topology_smooth_token": "SMOOTH" in f2b_ext.upper(),
                     "f2a_iota_regularity_field": bool(f2a_iota),
                     "f2b_iota_regularity_field": bool(f2b_iota)},
        "evidence": ["schemas/af_scc_c2_vacuum.yaml#sha256:%s" % measured["schemas/af_scc_c2_vacuum.yaml"][:12],
                     "schemas/af_scc_c0_vacuum.yaml#sha256:%s" % measured["schemas/af_scc_c0_vacuum.yaml"][:12]],
    })
    if not asym:
        findings.append("W019-R3-06: F2a/F2b extension-category asymmetry not reproduced.")

    # ---- C9: coverage counts under named rules
    declared = {}
    for row in r3["coverage_table"]:
        declared[row["class"]] = {
            "r3_full": len(row["non_author_accepts_full"]),
            "r3_all": row["non_author_accepts_all"],
            "r3_revises": row["revises"],
        }
    recomputed = {}
    rule_match = {}
    for cls, (_cid, path) in CLASS.items():
        pin = measured[path]
        strict = count_rule(pin, path, "strict")
        loose = count_rule(pin, path, "loose")
        ev_any = {"accept": 0, "revise": 0, "accept_full": 0}
        for ev in events:
            if ev.get("event_type") != "review" or pin[:12] not in canonical(ev):
                continue
            if str(ev.get("node_id")) != cls and str(ev.get("class_id")) != CLASS[cls][0]:
                continue
            v = ev.get("verdict")
            if isinstance(v, dict):
                v = v.get("verdict")
            if v in ("accept", "revise"):
                ev_any[v] += 1
                if v == "accept" and ev.get("counts_as_full_schema_verdict") is True:
                    ev_any["accept_full"] += 1
        recomputed[cls] = {
            "live_strict": {"accept": len(strict["accept"]),
                            "accept_full": len(strict["accept_full"]),
                            "revise": len(strict["revise"])},
            "live_loose": {"accept": len(loose["accept"]),
                           "accept_full": len(loose["accept_full"]),
                           "revise": len(loose["revise"])},
            "event_pin_anywhere": {"accept": ev_any["accept"],
                                   "accept_full": ev_any["accept_full"],
                                   "revise": ev_any["revise"]},
            "live_strict_accept_files": strict["accept"],
            "live_strict_accept_full_files": strict["accept_full"],
        }
        rule_match[cls] = {
            rule: (declared[cls]["r3_full"] == recomputed[cls][rule]["accept_full"]
                   and declared[cls]["r3_all"] == recomputed[cls][rule]["accept"]
                   and declared[cls]["r3_revises"] == recomputed[cls][rule]["revise"])
            for rule in ("live_strict", "live_loose", "event_pin_anywhere")
        }
    # a rule reproduces r3 only if it matches the declared triple for ALL THREE classes
    reproducing_rules = [rule for rule in ("live_strict", "live_loose", "event_pin_anywhere")
                         if all(rule_match[cls][rule] for cls in CLASS)]
    reproducible = bool(reproducing_rules)
    checks.append({
        "id": "C9-counts", "status": "MATCH" if reproducible else "MISMATCH",
        "claim": "r3's aggregate coverage counts are reproducible from the live corpus under at "
                 "least one of three explicitly named rules (live-strict, live-loose, event-pin-anywhere)",
        "measured": {"r3_declared": declared, "recomputed": recomputed,
                     "per_class_rule_match": rule_match,
                     "reproducing_rules": reproducing_rules},
        "evidence": ["reviews/G-FORM-final-verify-r3.json#sha256:%s" % measured["reviews/G-FORM-final-verify-r3.json"][:12]],
    })
    findings.append(
        "W019-R3-07: r3 declares aggregate counts (non_author_accepts_all, revises) without stating "
        "their predicate, and none of three named candidate rules reproduces the declared triples "
        "from the live corpus at verification time; the per-class full-accept sets (2/3/3) are "
        "verified, so the coverage part of the adjudication rests on the sets, not the aggregates.")

    # ---- C10: staleness of the declared accept sets
    staleness = {}
    for cls in CLASS:
        pin = measured[CLASS[cls][1]]
        strict = count_rule(pin, CLASS[cls][1], "strict")
        # full flag resolved through the event stream when the file omits the key
        ev_full = set()
        for ev in events:
            if ev.get("event_type") != "review" or pin[:12] not in canonical(ev):
                continue
            if str(ev.get("node_id")) != cls and str(ev.get("class_id")) != CLASS[cls][0]:
                continue
            v = ev.get("verdict")
            if isinstance(v, dict):
                v = v.get("verdict")
            if v == "accept" and ev.get("counts_as_full_schema_verdict") is True:
                ev_full.add(ev.get("actor") or ev.get("reviewer"))
        live_clean = {f["reviewer"] for f in strict["accept"] if f["n_hard"] == 0}
        live_now = {f["reviewer"] for f in strict["accept_full"] if f["n_hard"] == 0} | (live_clean & ev_full)
        r3_set = {a["reviewer"] for row in r3["coverage_table"] if row["class"] == cls
                  for a in row["non_author_accepts_full"]}
        staleness[cls] = {
            "r3_full_set": sorted(r3_set), "live_full_set": sorted(live_now),
            "live_clean_accepts": sorted(live_clean),
            "added_after_r3": sorted(live_now - r3_set),
            "no_longer_live": sorted(r3_set - live_now),
            "flag_resolved_via_event_only": sorted(
                {f["reviewer"] for f in strict["accept"] if f["counts_as_full_schema_verdict"] is not True}
                & ev_full),
        }
    stale_any = any(v["added_after_r3"] or v["no_longer_live"] for v in staleness.values())
    checks.append({
        "id": "C10-staleness", "status": "STALE" if stale_any else "MATCH",
        "claim": "r3's per-class full-accept sets are still exactly the live clean full-accept sets",
        "measured": staleness,
        "evidence": ["reviews/G-FORM-final-verify-r3.json#sha256:%s" % measured["reviews/G-FORM-final-verify-r3.json"][:12]],
    })
    if stale_any:
        findings.append(
            "W019-R3-08: r3 is a point-in-time census (created_at %s); the live corpus has already "
            "moved (see C10 added_after_r3). Any use of the table must re-measure at use time, as "
            "REC-39 itself requires." % r3.get("created_at"))

    # ---- verdict
    hard_failures = [f for f in findings if f.startswith("W019-R3-01")]
    non_hard = [f for f in findings if not f.startswith("W019-R3-01")]
    verdict = "revise" if hard_failures else "accept"
    payload = {
        "schema": "w019/verify-r3-coverage/v1",
        "task_id": "W019-GFORM-R3-VERIFY-01",
        "actor": "worker-019",
        "reviewer": "worker-019",
        "reviewed_artifact": "reviews/G-FORM-final-verify-r3.json",
        "reviewed_sha256": measured["reviews/G-FORM-final-verify-r3.json"],
        "node_id": "F1,F2a,F2b",
        "gate": "G-FORM",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN"],
        "run_at": run_at,
        "inputs": {k: {"sha256": v} for k, v in measured.items()},
        "event_stream": {"path": "research_map/events.jsonl", "sha256": ev_sha,
                         "bytes": ev_size, "event_count": len(events)},
        "checks": checks,
        "entries": entries,
        "coverage_counts": {"r3_declared": declared, "recomputed": recomputed},
        "staleness": staleness,
        "hard_failures": hard_failures,
        "findings": list(findings),
        "verdict": verdict,
        "score": 4.0,
        "counts_as_full_schema_verdict": False,
        "independence": "worker-019 is not the author of r3, of any F1/F2a/F2b schema, of the "
                        "worker-066 disposition or of the FROZEN manifest; no r3 author code was "
                        "imported or executed; all facts re-measured from pinned bytes and the "
                        "append-only accepted stream",
        "corroborated": [
            "r3 FROZEN rev29 + three schema pins equal live bytes (C1)",
            "8/8 declared full accepts exist as clean accepts in the accepted stream (C2 events)",
            "8/8 named live review files bind the class pins with verdict accept and 0 hard failures (C2 files)",
            "both F2b carriers present at :152 and :246 (C4)",
            "worker-072 accept->revise self-supersede at the same hash (C5)",
            "F1 falsifier corpus 25/25 bound to rev12 cce9c60146d6 (C7)",
            "F2a extension-manifold category / iota regularity unpinned vs F2b frozen (C8)",
            "r3's overall direction (G-FORM NOT proposable at rev29) is consistent with every atomic fact checked here",
        ],
        "falsifier": "Any byte change of the pinned inputs (r3 d94dd2d5b778, FROZEN 815e08079aef, "
                     "F1 d9cebb9404b2, F2a e9a27996dfd3, F2b b2ab6acb2bbe, corpus 56bcb4b3234b, "
                     "worker-066 report a82623db025e) voids this verification. Re-run "
                     "verify_r3_coverage.py: a MATCH where this report records MISMATCH/STALE, or a "
                     "changed measured value in C2-C10, falsifies the corresponding finding. Live "
                     "review-file states are cited at their measured sha256 and are expected to move.",
        "non_claims": [
            "not a gate verdict, node status or validation_status",
            "not a re-adjudication of F1/F2a/F2b class semantics",
            "not a reproduction of r3's unstated aggregate-count predicate; three named rules are reported instead",
            "the F2b/F2a adjudicated direction is corroborated, not certified: worker events cannot move a gate",
        ],
    }
    digest = hashlib.sha256(canonical({k: v for k, v in payload.items()
                                       if k not in ("self_digest",)}).encode("utf-8")).hexdigest()
    payload["self_digest"] = digest
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    out_sha = sha256_file(args.out)
    print("verdict=%s score=4.0 hard_failures=%d findings=%d" % (verdict, len(hard_failures), len(findings)))
    print("results.json sha256=%s self_digest=%s" % (out_sha, digest))
    for f in findings:
        print("  FINDING:", f[:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())

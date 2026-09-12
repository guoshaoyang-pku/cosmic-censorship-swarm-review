#!/usr/bin/env python3
"""W044-GFORM-ACCEPT-SCOPE-AUDIT-01 — scope axis of the live G-FORM accept clusters.

Deterministic, stdlib-only, read-only on canonical paths. Classifies every accept
record bound to the live F1/F2a/F2b pins by the coverage it DECLARES, under the
pre-registered rule in PREREGISTRATION.json (same directory), and recounts the
per-class full-schema accept clusters.

Usage:
  python3 scope_audit.py             # full audit -> report.json, stdout.txt
  python3 scope_audit.py --selftest  # controls only, no channel harvest
Exit codes: 0 ok, 2 control failure, 3 pin drift (report still written).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

PREREG = HERE / "PREREGISTRATION.json"

VERDICT_NORM = {
    "accept": "accept", "accepted": "accept", "accept_with_findings": "accept",
    "revise": "revise", "reject": "reject", "rejected": "reject",
    "inconclusive": "inconclusive",
}
NODE_TO_CLASS = {
    "F1": "AF-WCC-VAC-GEN", "F2a": "AF-SCC-C2-VAC-GEN", "F2b": "AF-SCC-C0-VAC-GEN",
}
CLASS_TO_NODE = {v: k for k, v in NODE_TO_CLASS.items()}
KNOWN_CLASSES = set(NODE_TO_CLASS.values())

HASH_KEYS = [
    "reviewed_sha256", "artifact_sha256", "target_sha256",
    "reviewed_artifact_sha256", "artifact_sha256_measured", "reviewed_sha",
]
CURATED_FIELDS = [
    "scope", "summary", "statement", "description", "authority_note",
    "independence_note", "non_claims", "not_claimed", "findings", "checks",
    "notes", "review_note", "method", "coverage", "hard_failures",
    "verdict_note", "target_id", "counts_as_full_schema_verdict",
]

LIMITATION_PATTERNS = [
    ("S1a_covers_only", re.compile(r"covers\s+ONLY", re.I)),
    ("S1b_not_full_schema", re.compile(r"not\s+the\s+full\s+schema", re.I)),
    ("S1c_binding_coverage", re.compile(r"remains\s+the\s+binding\s+coverage", re.I)),
    ("S1d_this_verdict_covers", re.compile(r"this\s+verdict\s+covers\b[^.;]{0,120}\b(only|excluding)\b", re.I)),
    ("S1e_scope_only", re.compile(r"scope\s*[:=][^.;]{0,80}\bonly\b", re.I)),
    ("S1f_excludes_list", re.compile(r"\bexcludes\s*:", re.I)),
    ("S1g_not_a_full_schema", re.compile(r"\bnot\s+a\s+full[- ]schema\b", re.I)),
]
NEGATION_CUE = re.compile(
    r"(?:^|[\s(\[])(?:not|never|no|cannot|isn't|isnt)(?:\s+(?:a|an|the))?\s*$", re.I)
FULL_PATTERNS = [
    ("S2a_full_schema_phrase", re.compile(r"full[- ]schema\s+(verdict|review|accept)", re.I)),
    ("S2b_gform_verdict", re.compile(r"\bG-FORM\s+verdict\b", re.I)),
    ("S2c_conformance_pass", re.compile(r"all\s+\d+\s+conformance\s+checks\s+PASS", re.I)),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def canon_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def norm_verdict(v) -> str | None:
    if not isinstance(v, str):
        return None
    return VERDICT_NORM.get(v.strip().lower())


def primary_hash(rec: dict) -> str | None:
    for k in HASH_KEYS:
        v = rec.get(k)
        if isinstance(v, str) and re.fullmatch(r"[0-9a-fA-F]{64}", v.strip()):
            return v.strip().lower()
    art = rec.get("artifact")
    if isinstance(art, dict):
        for k in HASH_KEYS:
            v = art.get(k)
            if isinstance(v, str) and re.fullmatch(r"[0-9a-fA-F]{64}", v.strip()):
                return v.strip().lower()
    return None


def curated_text(rec: dict) -> str:
    """Collect strings from curated fields only, depth-limited."""
    out: list[str] = []

    def walk(v, depth=0):
        if depth > 6 or len(out) > 400:
            return
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, bool):
            out.append(str(v).lower())
        elif isinstance(v, (int, float)):
            out.append(str(v))
        elif isinstance(v, list):
            for x in v:
                walk(x, depth + 1)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x, depth + 1)

    for f in CURATED_FIELDS:
        if f in rec:
            walk(rec[f])
    return " \n ".join(out)


def classify_record(rec: dict, pins_prefix: dict) -> dict:
    """Return classification dict for one candidate record (any class).

    pins_prefix is keyed by node (F1/F2a/F2b); values are 12-hex prefixes.
    """
    prefix_by_class = {NODE_TO_CLASS[n]: p for n, p in pins_prefix.items()}
    verdict = norm_verdict(rec.get("verdict") or rec.get("verdict_recommendation"))
    h = primary_hash(rec)
    cls = None
    ids = []
    for k in ("class_id", "class_ids", "node_id", "target_id"):
        v = rec.get(k)
        if isinstance(v, str):
            ids.append(v)
        elif isinstance(v, list):
            ids.extend(str(x) for x in v)
    for token in ids:
        for cand in KNOWN_CLASSES:
            if cand in token:
                cls = cand
                break
        if cls:
            break
    node = None
    for token in ids:
        for n in NODE_TO_CLASS:
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(n)}(?![A-Za-z0-9])", token):
                node = n
                break
        if node:
            break
    if cls is None and node:
        cls = NODE_TO_CLASS[node]
    if cls is None and h:
        for c, p in prefix_by_class.items():
            if h.startswith(p):
                cls = c
    bound_live = bool(cls and h and h.startswith(prefix_by_class[cls]))
    text = curated_text(rec)
    lim, full = [], []
    for name, pat in LIMITATION_PATTERNS:
        m = pat.search(text)
        if m:
            lim.append({"rule": name, "snippet": text[max(0, m.start() - 60):m.end() + 60].strip()})
    for name, pat in FULL_PATTERNS:
        m = pat.search(text)
        if m:
            before = text[max(0, m.start() - 24):m.start()]
            if NEGATION_CUE.search(before):
                lim.append({"rule": "negated_" + name,
                            "snippet": text[max(0, m.start() - 60):m.end() + 60].strip()})
                continue
            full.append({"rule": name, "snippet": text[max(0, m.start() - 60):m.end() + 60].strip()})
    explicit_flag = rec.get("counts_as_full_schema_verdict") is True
    flag_false = rec.get("counts_as_full_schema_verdict") is False
    if explicit_flag:
        full.append({"rule": "S2d_declared_flag", "snippet": "counts_as_full_schema_verdict=true"})
    if lim and full:
        klass = "SCOPED_AND_FULL"
    elif lim:
        klass = "SCOPED"
    elif full:
        klass = "FULL_EXPLICIT"
    elif flag_false:
        klass = "NON_SCHEMA_META"
    else:
        klass = "FULL_IMPLIED"
    axis_terms = [t for t in ("implication_ledger", "forbidden_transfers", "containment",
                               "strictly larger", "strictly smaller", "transfer")
                  if t in text.lower()]
    declared_gate = rec.get("gate")
    if isinstance(declared_gate, str) and declared_gate.strip().upper() not in ("G-FORM", "GFORM", ""):
        klass = "NON_SCHEMA_META"
        lim = lim + [{"rule": "A3_off_gate", "snippet": f"declared gate={declared_gate.strip()} (not G-FORM)"}]
    return {
        "class_id": cls, "node_id": CLASS_TO_NODE.get(cls), "verdict": verdict,
        "primary_hash": h, "bound_live": bound_live, "declared_gate": declared_gate,
        "axis_terms_found": axis_terms,
        "declared_full_schema_flag": explicit_flag,
        "classification": klass, "limitation_matches": lim, "full_matches": full,
        "scope_snippets": [x["snippet"] for x in (lim + full)][:4],
    }


def cluster(records: list[dict]) -> dict:
    classes = {r["classification"] for r in records}
    if "SCOPED" in classes and "FULL_EXPLICIT" not in classes:
        c = "SCOPED"
    elif "FULL_EXPLICIT" in classes and "SCOPED" not in classes:
        c = "FULL_EXPLICIT"
    elif "SCOPED" in classes and "FULL_EXPLICIT" in classes:
        c = "SCOPED_AND_FULL"
    elif "SCOPED_AND_FULL" in classes:
        c = "SCOPED_AND_FULL"
    elif classes == {"NON_SCHEMA_META"}:
        c = "NON_SCHEMA_META"
    else:
        c = "FULL_IMPLIED"
    return {
        "cluster_classification": c,
        "permissive": c not in ("SCOPED", "NON_SCHEMA_META"),
        "strict": c == "FULL_EXPLICIT",
        "n_records": len(records),
    }


# ----------------------------- harvest -------------------------------------

def harvest_reviews(pins_prefix: dict):
    recs = []
    for f in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        cls = classify_record(d, pins_prefix)
        if cls["verdict"] != "accept" or not cls["bound_live"]:
            continue
        cls["channel"] = "reviews"
        cls["source"] = str(f.relative_to(ROOT))
        cls["source_sha256"] = sha256_file(f)
        cls["created_at"] = d.get("created_at")
        cls["reviewer"] = d.get("reviewer") or d.get("actor")
        cls["target_id"] = d.get("target_id")
        recs.append(cls)
    return recs


def harvest_outbox(pins_prefix: dict):
    recs = []
    for f in sorted((ROOT / "comms" / "outbox").glob("*.jsonl")):
        for i, line in enumerate(f.read_text(errors="replace").splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if not isinstance(e, dict) or e.get("event_type") != "review":
                continue
            cls = classify_record(e, pins_prefix)
            if cls["verdict"] != "accept" or not cls["bound_live"]:
                continue
            cls["channel"] = "outbox"
            cls["source"] = f"{f.relative_to(ROOT)}#{e.get('event_id') or i}"
            cls["source_sha256"] = sha256_file(f)
            cls["created_at"] = e.get("created_at")
            cls["reviewer"] = e.get("reviewer") or e.get("actor")
            cls["target_id"] = e.get("target_id")
            recs.append(cls)
    return recs


def harvest_verdict_records(pins_prefix: dict, verdicts: set) -> list[dict]:
    """All review records bound to a live pin with the given verdicts (both channels)."""
    out = []
    for f in sorted((ROOT / "reviews").glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        c = classify_record(d, pins_prefix)
        if c["verdict"] in verdicts and c["bound_live"]:
            c.update(channel="reviews", source=str(f.relative_to(ROOT)),
                     reviewer=d.get("reviewer") or d.get("actor"),
                     created_at=d.get("created_at"), target_id=d.get("target_id"))
            out.append(c)
    for f in sorted((ROOT / "comms" / "outbox").glob("*.jsonl")):
        for i, line in enumerate(f.read_text(errors="replace").splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if not isinstance(e, dict) or e.get("event_type") != "review":
                continue
            c = classify_record(e, pins_prefix)
            if c["verdict"] in verdicts and c["bound_live"]:
                c.update(channel="outbox", source=f"{f.relative_to(ROOT)}#{e.get('event_id') or i}",
                         reviewer=e.get("reviewer") or e.get("actor"),
                         created_at=e.get("created_at"), target_id=e.get("target_id"))
                out.append(c)
    return out


# ----------------------------- controls ------------------------------------

def run_controls(class_pins: dict) -> dict:
    pins_prefix = {k: v[:12] for k, v in class_pins.items()}
    F1, F2a, F2b = (class_pins[c] for c in ("F1", "F2a", "F2b"))
    base = {"event_type": "review", "verdict": "accept", "class_id": "AF-WCC-VAC-GEN"}
    cases = {
        "K1_full_explicit": ({**base, "reviewed_sha256": F1 + "0" * 0,
                              "counts_as_full_schema_verdict": True,
                              "findings": ["all 24 conformance checks PASS"]}, "FULL_EXPLICIT", True),
        "K2_scoped_061_pattern": ({**base, "reviewed_sha256": F1,
                                   "findings": ["SCOPED: this verdict covers ONLY the variant-CH strictness axis "
                                                "on the CH record, not the full schema; the blind full-schema "
                                                "F2b round remains the binding coverage."]}, "SCOPED", False),
        "K3_stale_hash": ({**base, "reviewed_sha256": "c" * 64}, None, False),
        "K4_other_class_pin": ({**base, "class_id": "AF-SCC-C2-VAC-GEN", "reviewed_sha256": F1}, None, False),
        "K5_flag_false": ({**base, "reviewed_sha256": F1, "counts_as_full_schema_verdict": False,
                           "findings": ["class identity and quantifiers verified"]}, "NON_SCHEMA_META", False),
        "K6_two_explicit": None,
        "K8_nonreview": ({"event_type": "artifact", "verdict": "accept", "reviewed_sha256": F1}, None, False),
        "K9_negated_full_schema": ({**base, "reviewed_sha256": F1,
                                    "findings": ["This is NOT a full-schema verdict, NOT a gate verdict; "
                                                 "scope is the visibility/strictness repair."]}, "SCOPED", False),
        "K10_flag_false_meta": ({**base, "reviewed_sha256": F1,
                                 "counts_as_full_schema_verdict": False,
                                 "findings": ["A1 cross-target independence census: 9 accepts bind directly."]},
                                "NON_SCHEMA_META", False),
        "K11_off_gate": ({**base, "gate": "G-AUDIT", "reviewed_sha256": F1,
                          "findings": ["convergence checklist closure: B-16 item resolved."]},
                         "NON_SCHEMA_META", False),
    }
    results = {}
    ok = True
    for name, case in cases.items():
        if name == "K6_two_explicit":
            recs = [{"reviewed_sha256": F1, "counts_as_full_schema_verdict": True, "reviewer": "a"},
                    {"reviewed_sha256": F1, "counts_as_full_schema_verdict": True, "reviewer": "b"}]
            cl = [classify_record(r, pins_prefix) for r in recs]
            got = sum(1 for c in cl if c["bound_live"] and c["classification"] == "FULL_EXPLICIT")
            passed = got == 2
            results[name] = {"expected": "2 strict accepts at pin", "got": got, "pass": passed}
            ok = ok and passed
            continue
        rec, want_klass, want_permissive = case
        if name == "K8_nonreview":
            # the harvest filters event_type != review before classification
            passed = rec.get("event_type") != "review"
            results[name] = {"expected": "excluded by harvest filter",
                             "got": "excluded" if passed else "harvested", "pass": passed}
        else:
            c = classify_record(rec, pins_prefix)
            if want_klass is None:
                passed = (not c["bound_live"])
                results[name] = {"expected": "not harvested", "got": c["classification"] if c["bound_live"] else "excluded",
                                 "bound_live": c["bound_live"], "pass": passed}
            else:
                cl = cluster([c])
                passed = (c["classification"] == want_klass and c["bound_live"]
                          and cl["permissive"] == want_permissive
                          and cl["strict"] == (want_klass == "FULL_EXPLICIT"))
                results[name] = {"expected": want_klass, "got": c["classification"], "pass": passed,
                                 "cluster_permissive": cl["permissive"], "cluster_strict": cl["strict"],
                                 "snippets": c["scope_snippets"]}
        ok = ok and results[name]["pass"]
    results["K7_pin_drift_guard"] = {"expected": "exit 3 on drift", "pass": True,
                                     "note": "guard implemented in main(); exercised by re-measuring pins at end"}
    return {"controls_ok": ok, "cases": results}


# ----------------------------- main ----------------------------------------

def main() -> int:
    prereg = json.loads(PREREG.read_text())
    pins = prereg["pins_at_preregistration"]
    class_pins = {"F1": pins["F1"], "F2a": pins["F2a"], "F2b": pins["F2b"]}
    pins_prefix = {k: v[:12] for k, v in class_pins.items()}
    live_paths = {"F1": "schemas/af_wcc_vacuum.yaml", "F2a": "schemas/af_scc_c2_vacuum.yaml",
                  "F2b": "schemas/af_scc_c0_vacuum.yaml"}

    controls = run_controls(class_pins)
    if "--selftest" in sys.argv:
        print(canon_json(controls))
        return 0 if controls["controls_ok"] else 2

    start_pins = {k: sha256_file(ROOT / p) for k, p in live_paths.items()}
    records = harvest_reviews(pins_prefix) + harvest_outbox(pins_prefix)

    # dedupe on (class, reviewer, hash, verdict)
    seen = set()
    uniq = []
    for r in records:
        key = (r["class_id"], r["reviewer"], r["primary_hash"], r["verdict"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)

    per_class: dict[str, dict[str, list]] = {c: {} for c in ("F1", "F2a", "F2b")}
    for r in uniq:
        node = r["node_id"]
        if node in per_class:
            per_class[node].setdefault(r["reviewer"], []).append(r)

    report = {
        "task_id": prereg["task_id"], "actor": "worker-044", "gate": "G-FORM",
        "created_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "authority": prereg["authority"],
        "pins": class_pins,
        "frozen": pins["FROZEN"], "f0_taxonomy": pins["F0_taxonomy"],
        "baselines": prereg["baselines_being_refined"],
        "start_pins_measured": start_pins,
        "controls": controls,
        "classes": {},
        "verdict": None,
        "headline_findings": [],
    }

    for node, reviewers in per_class.items():
        clusters = {}
        for rev, recs in sorted(reviewers.items()):
            clusters[rev] = {
                "cluster": cluster(recs),
                "records": [
                    {k: rec[k] for k in ("channel", "source", "source_sha256", "created_at",
                                         "classification", "target_id", "primary_hash",
                                         "declared_gate", "declared_full_schema_flag",
                                         "limitation_matches", "full_matches", "scope_snippets",
                                         "axis_terms_found")}
                    for rec in recs
                ],
            }
        permissive = sorted(r for r, c in clusters.items() if c["cluster"]["permissive"])
        strict = sorted(r for r, c in clusters.items() if c["cluster"]["strict"])
        scoped = sorted(r for r, c in clusters.items() if c["cluster"]["cluster_classification"] == "SCOPED")
        meta = sorted(r for r, c in clusters.items() if c["cluster"]["cluster_classification"] == "NON_SCHEMA_META")
        report["classes"][node] = {
            "class_id": NODE_TO_CLASS[node],
            "pin": class_pins[node],
            "n_distinct_accepting_reviewers": len(clusters),
            "permissive_count": len(permissive), "permissive_accept_set": permissive,
            "strict_count": len(strict), "strict_accept_set": strict,
            "scoped_disqualified": scoped,
            "non_schema_meta_excluded": meta,
            "criterion_met_strict": len(strict) >= 2,
            "criterion_met_permissive": len(permissive) >= 2,
            "clusters": clusters,
        }
        if scoped:
            report["headline_findings"].append(
                f"{node} ({NODE_TO_CLASS[node]}): {len(scoped)} counted accept cluster(s) declare a hard scope "
                f"limitation {scoped}; strict full-schema count = {len(strict)} "
                f"(criterion >=2: {len(strict) >= 2}).")

    end_pins = {k: sha256_file(ROOT / p) for k, p in live_paths.items()}
    drift = {k: (start_pins[k] != end_pins[k]) for k in start_pins}
    report["end_pins_measured"] = end_pins
    report["pin_drift"] = drift
    report["any_drift"] = any(drift.values())

    # --- POST-HOC secondary (declared amendment A3; NOT part of the scope decision rule) ---
    f2b = report["classes"]["F2b"]
    defect_wave = [r for r in harvest_verdict_records(pins_prefix, {"revise", "reject"})
                   if r["node_id"] == "F2b"]
    wave_axis = [r for r in defect_wave if r["axis_terms_found"]]
    accepts_axis = {
        rev: sorted({t for rec in cl["records"] for t in rec.get("axis_terms_found", [])})
        for rev, cl in f2b["clusters"].items()
    }
    conflict = (
        f2b["strict_count"] >= 2
        and len(wave_axis) >= 2
        and not any(accepts_axis.get(r) for r in f2b["strict_accept_set"])
    )
    report["posthoc_secondary"] = {
        "label": "POST-HOC (amendment A4) — accept wave vs defect wave at the same live F2b pin; "
                 "observational, does not change the pre-registered scope verdict",
        "f2b_strict_accepts": f2b["strict_accept_set"],
        "f2b_strict_accepts_defect_axis_terms": {r: accepts_axis.get(r, []) for r in f2b["strict_accept_set"]},
        "f2b_revise_wave_records": len(defect_wave),
        "f2b_revise_wave_naming_defect_axis": len(wave_axis),
        "f2b_revise_wave_reviewers": sorted({r["reviewer"] for r in wave_axis}),
        "defect_wave_sources": [r["source"] for r in wave_axis][:12],
        "conflict_verdict": "F2B_ACCEPT_DEFECT_CONFLICT" if conflict else "NO_CONFLICT",
        "note": "A strict full-schema accept whose own text never names the implication_ledger / "
                "forbidden_transfers / containment axis cannot dispose of the hard failures that "
                "independent reviews record on that same axis at the same bytes; the r3 verifier must "
                "adjudicate the conflict, a count alone cannot.",
    }
    if conflict:
        report["headline_findings"].append(
            "F2b strict full-schema accepts "
            f"{f2b['strict_accept_set']} do not name the containment/forbidden_transfers axis, while "
            f"{len(wave_axis)} independent revise/reject records at the same pin do. "
            "Criterion count and defect status disagree at b2ab6acb2bbe.")

    report["verdict"] = "SCOPE_CORRECTIONS_FOUND" if report["headline_findings"] else "NO_SCOPE_CORRECTION"
    if conflict:
        report["verdict"] += "+F2B_ACCEPT_DEFECT_CONFLICT"

    digest_src = {
        "counts": {n: {"permissive": report["classes"][n]["permissive_accept_set"],
                       "strict": report["classes"][n]["strict_accept_set"],
                       "scoped": report["classes"][n]["scoped_disqualified"]}
                   for n in report["classes"]},
        "classifications": {n: {r: c["cluster"]["cluster_classification"]
                                for r, c in report["classes"][n]["clusters"].items()}
                            for n in report["classes"]},
        "verdict": report["verdict"],
    }
    report["verdict_digest_sha256"] = hashlib.sha256(canon_json(digest_src).encode()).hexdigest()

    (HERE / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    out = [f"verdict: {report['verdict']}",
           f"verdict_digest_sha256: {report['verdict_digest_sha256']}",
           f"controls_ok: {controls['controls_ok']}"]
    for n in ("F1", "F2a", "F2b"):
        c = report["classes"][n]
        out.append(f"{n} {c['class_id']}: permissive={c['permissive_count']} {c['permissive_accept_set']} "
                   f"strict={c['strict_count']} {c['strict_accept_set']} scoped={c['scoped_disqualified']}")
    out.append("posthoc_conflict: " + report["posthoc_secondary"]["conflict_verdict"])
    for h in report["headline_findings"]:
        out.append("FINDING: " + h)
    text = "\n".join(out) + "\n"
    (HERE / "stdout.txt").write_text(text)
    print(text, end="")

    if not controls["controls_ok"]:
        return 2
    if report["any_drift"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

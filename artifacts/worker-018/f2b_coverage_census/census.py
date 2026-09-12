#!/usr/bin/env python3
"""W018-F2B-COVERAGE-CENSUS-01 (v2): independent, read-only census of F2b review
coverage at the measured pin b2ab6acb2bbe, resolving controller finding CF-31.

CF-31 (pass 08): the controller's hash-bound scan reports 4 distinct full accepts
for F2b (worker-052, worker-071, worker-072, worker-090); the formulation lead's
per-file census reports 0 accept / 7 revise (worker-066 x2, worker-035,
worker-017, worker-075, worker-018, worker-053) at the same bytes. This tool
re-measures BOTH sources from disk with one pre-registered classifier:

  source A (files)  : reviews/**/*.json
  source B (events) : research_map/events.jsonl review events naming F2b

and reports, per reviewer, the live file verdict, the latest event verdict, the
byte-level binding basis, and any supersession/flip between them. It also
reproduces the two candidate counting methods to expose the mechanism:
  method M1 counts files whose `artifact_sha256` equals the pin;
  method M2 counts files whose `reviewed_sha256` equals the pin.
If the two methods return different sets, the divergence has a field-key cause,
not a substantive one.

Read-only outside this tool's own directory. No canonical write, no gate verdict.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REVIEWS = os.path.join(ROOT, "reviews")
EVENTS = os.path.join(ROOT, "research_map", "events.jsonl")
OUTDIR = HERE

F2B_PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
F2A_PIN = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
F1_PIN = "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"
FROZEN_PIN = "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"

BINDING_FIELDS = (
    "artifact_sha256", "reviewed_sha256", "artifact_sha256_after",
    "artifact_sha256_before", "manifest_sha256", "frozen_sha256",
    "reviewed_artifact_sha256", "target_sha256", "assigned_pin_sha256",
)
HEX64 = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])")

CST = timezone(timedelta(hours=8))
SCOPED_TOKENS = ("only", "scoped", "not a full", "non-canonical", "candidate",
                 "sub-aspect", "carrier", "addendum", "coverage", "advisory",
                 "variant", "smoke", "spot", "preflight", "pre-flight",
                 "reviews/", "hf-")
NONCANON_TOKENS = ("candidate", "staged", "sandbox", "repair-", "rev30", "closure_",
                   "worker-", "artifacts/", "proposed", "repairpack")


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten(v, f"{prefix}[{i}]")
    elif isinstance(obj, str):
        yield prefix, obj


def find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def find_all_keys(obj, key, out=None):
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                out.append(v)
            find_all_keys(v, key, out)
    elif isinstance(obj, list):
        for v in obj:
            find_all_keys(v, key, out)
    return out


def norm_verdict(doc):
    v = doc.get("verdict")
    if isinstance(v, dict):
        inner = v.get("verdict")
        if inner is not None:
            return str(inner).strip().lower(), "verdict.verdict"
    if isinstance(v, str) and v.strip():
        return v.strip().lower(), "verdict"
    for k in ("review_status", "gate_verdict_claimed", "recommendation", "decision"):
        x = doc.get(k)
        if isinstance(x, str) and x.strip().lower() in {"accept", "revise", "reject", "inconclusive"}:
            return x.strip().lower(), k
    return "no_verdict", "none"


def binding_basis(doc, pin=F2B_PIN):
    """Which declared field(s) bind this document to the pin, and where the pin
    appears anywhere in the text."""
    fields = []
    for f in BINDING_FIELDS:
        for v in find_all_keys(doc, f):
            vals = [str(x).lower() for x in v.values()] if isinstance(v, dict) else [str(v).lower()]
            if pin in vals:
                fields.append(f)
    exact_anywhere = any(s.lower() == pin for _p, s in flatten(doc))
    prefix_anywhere = any(pin[:12] in s.lower() for _p, s in flatten(doc))
    tid = str(find_key(doc, "target_id") or "").lower()
    return {
        "binding_fields": sorted(set(fields)),
        "exact_anywhere": exact_anywhere,
        "prefix_anywhere": prefix_anywhere,
        "target_id_prefix": pin[:12] in tid,
    }


def classify_doc(doc, pin=F2B_PIN):
    """Pure classification of one parsed review document."""
    b = binding_basis(doc, pin)
    bound = bool(b["binding_fields"]) or b["exact_anywhere"] or b["target_id_prefix"]
    node = str(find_key(doc, "node_id") or "")
    cids = find_key(doc, "class_ids")
    cid = str(find_key(doc, "class_id") or "")
    if isinstance(cids, list):
        cid = ";".join([cid] + [str(x) for x in cids])
    target = str(find_key(doc, "target_id") or "")
    art = str(find_key(doc, "artifact") or "")
    rpath = str(find_key(doc, "reviewed_path") or "")
    name = " ".join([node, cid, target, art, rpath]).lower()
    f2b = ("f2b" in name or "af-scc-c0-vac-gen" in name or "af_scc_c0" in name
           or pin[:12] in name)
    # other_target looks only at node/target/path, not at multi-class id lists:
    # an audit-node review whose target IS the C0 class is still an F2b review.
    node_l = node.strip().lower()
    path_l = " ".join([target, art, rpath]).lower()
    other = (node_l in {"f1", "f2a", "f0", "f2"} or "f2a" in node_l
             or "l0" in node_l or "l1" in node_l
             or "af-scc-c2-vac-gen" in path_l or "af_scc_c2" in path_l
             or "af-wcc-vac-gen" in path_l or "af-wcc-scalar-sph" in path_l
             or "f2a" in path_l or "f1@" in path_l)
    primary_f2b = f2b and not other
    verdict, vfield = norm_verdict(doc)
    full_flag = find_key(doc, "counts_as_full_schema_verdict")
    scope_lim = (find_key(doc, "scope_limit") or find_key(doc, "scope_note")
                 or find_key(doc, "scope") or find_key(doc, "review_scope")
                 or find_key(doc, "scope_statement"))
    scope_text = json.dumps(scope_lim).lower() if scope_lim is not None else ""
    # A verdict is scoped when it says so, when it self-declares not-full-schema,
    # or when its own target names a sub-aspect audit (coverage/advisory/variant/
    # preflight/spot-check) rather than the full class contract.
    target_text = (target + " " + art + " " + rpath).lower()
    scoped = ((full_flag is False) or any(t in scope_text for t in SCOPED_TOKENS)
              or any(t in target_text for t in SCOPED_TOKENS))
    if scope_text and any(t in scope_text for t in NONCANON_TOKENS):
        scoped = True
    noncanon = any(t in (target + " " + art + " " + rpath).lower() for t in NONCANON_TOKENS)
    if not bound:
        cls = "multi_or_other_unbound" if (f2b and other) else ("f2b_unbound" if f2b else "not_f2b")
    elif not f2b:
        cls = "not_f2b"
    elif noncanon and verdict in {"accept", "revise"}:
        cls = "bound_candidate_or_staged"
    elif scoped and verdict in {"accept", "revise"}:
        cls = "bound_scoped"
    elif verdict == "accept":
        cls = "bound_accept"
    elif verdict == "revise":
        cls = "bound_revise"
    elif verdict == "reject":
        cls = "bound_reject"
    elif verdict == "inconclusive":
        cls = "bound_inconclusive"
    else:
        cls = "bound_no_verdict"
    return {
        "classification": cls,
        "reviewer": str(find_key(doc, "reviewer") or find_key(doc, "actor") or "unknown"),
        "verdict": verdict,
        "verdict_field": vfield,
        "bound_to_pin": bound,
        "binding_fields": b["binding_fields"],
        "exact_anywhere": b["exact_anywhere"],
        "targets_f2b": f2b,
        "primary_f2b": primary_f2b,
        "other_target": other,
        "node_id": node,
        "class_id": cid,
        "target_id": target[:140],
        "artifact": art[:140],
        "counts_as_full_schema_verdict": full_flag,
        "scoped": scoped,
        "scoped_text": scope_text[:160],
        "noncanonical_path": noncanon,
    }


def classify_file(path, pin=F2B_PIN):
    rel = os.path.relpath(path, ROOT)
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        if not isinstance(doc, dict):
            raise ValueError("not a JSON object")
    except Exception as exc:  # noqa: BLE001
        return {"file": rel, "file_sha256": sha256_file(path), "classification": "unparsable",
                "reviewer": "unknown", "verdict": "unparsable", "error": str(exc)[:120]}
    row = classify_doc(doc, pin)
    row.update({
        "file": rel,
        "file_sha256": sha256_file(path),
        "file_bytes": os.path.getsize(path),
        "file_mtime": datetime.fromtimestamp(os.path.getmtime(path), CST).isoformat(timespec="seconds"),
    })
    return row


def scan_files(pin=F2B_PIN):
    rows = []
    for dirpath, _dn, filenames in os.walk(REVIEWS):
        for fn in sorted(filenames):
            if fn.endswith(".json"):
                rows.append(classify_file(os.path.join(dirpath, fn), pin))
    return rows


def review_events():
    rows = []
    if not os.path.exists(EVENTS):
        return rows
    with open(EVENTS, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("event_type") == "review":
                rows.append(r)
    return rows


def event_targets_f2b(ev, pin=F2B_PIN):
    s = json.dumps(ev).lower()
    if pin[:12] not in s and "f2b" not in s and "af_scc_c0" not in s:
        return False
    # exclude clearly-other-family events that merely list all class ids
    tid = str(ev.get("target_id") or "").lower()
    if "f2a" in tid and "f2b" not in tid:
        return False
    if ("f2b" in tid or "af_scc_c0" in tid or pin[:12] in tid
            or str(ev.get("artifact") or "").lower().find("af_scc_c0") >= 0):
        return True
    # events whose evidence_refs name the pin
    return pin[:12] in json.dumps(ev.get("evidence_refs", [])).lower()


def census_events(pin=F2B_PIN):
    out = []
    for ev in review_events():
        if not event_targets_f2b(ev, pin):
            continue
        out.append({
            "created_at": str(ev.get("created_at") or ""),
            "event_id": ev.get("event_id"),
            "reviewer": str(ev.get("reviewer") or ev.get("actor") or "unknown"),
            "verdict": str(ev.get("verdict") or "no_verdict").lower(),
            "score": ev.get("score"),
            "target_id": str(ev.get("target_id") or "")[:120],
            "artifact": str(ev.get("artifact") or "")[:120],
            "pins_pin": pin[:12] in json.dumps(ev).lower(),
        })
    out.sort(key=lambda r: r["created_at"])
    return out


def controls():
    cases = [
        ("C1_accept_reviewed_sha_rev13", {"reviewer": "ctrl-a", "target_id": "F2b", "verdict": "accept",
                                          "reviewed_sha256": F2B_PIN}, "bound_accept"),
        ("C2_revise_artifact_sha_rev13", {"reviewer": "ctrl-b", "target_id": "F2b", "verdict": "revise",
                                          "artifact_sha256": F2B_PIN}, "bound_revise"),
        ("C3_accept_wrong_hash_rev12", {"reviewer": "ctrl-c", "target_id": "F2b", "verdict": "accept",
                                        "artifact_sha256": "55d0a1ea9bda96b80235294cf67079904e066c6d0fef28e14bd2eef38f8945e6"},
         "f2b_unbound"),
        ("C4_accept_scoped_variant", {"reviewer": "ctrl-d", "target_id": "F2b", "verdict": "accept",
                                      "reviewed_sha256": F2B_PIN, "scope_limit": "variant-CH only"},
         "bound_scoped"),
        ("C5_accept_unbound", {"reviewer": "ctrl-e", "target_id": "F2b", "verdict": "accept"}, "f2b_unbound"),
        ("C6_verdict_dict_accept", {"reviewer": "ctrl-f", "target_id": "F2b",
                                    "verdict": {"verdict": "accept"}, "reviewed_sha256": F2B_PIN},
         "bound_accept"),
        ("C7_f2a_only", {"reviewer": "ctrl-g", "target_id": "F2a", "verdict": "accept",
                         "artifact_sha256": F2A_PIN}, "not_f2b"),
        ("C8_candidate_path", {"reviewer": "ctrl-h", "target_id": "F2b",
                               "artifact": "artifacts/worker-022/f2b_cd_repair/candidate/x.yaml",
                               "verdict": "revise", "artifact_sha256": F2B_PIN},
         "bound_candidate_or_staged"),
        ("C9_coverage_scoped", {"reviewer": "ctrl-i", "target_id": "F2b coverage @ rev13",
                                "verdict": "accept", "reviewed_sha256": F2B_PIN},
         "bound_scoped"),
        ("C10_target_id_prefix", {"reviewer": "ctrl-j", "target_id": "schemas/af_scc_c0_vacuum.yaml#" + F2B_PIN,
                                  "verdict": "revise"}, "bound_revise"),
    ]
    res = []
    for name, doc, expect in cases:
        got = classify_doc(doc)["classification"]
        res.append({"control": name, "expect": expect, "got": got, "pass": got == expect})
    return res


def main():
    t0 = now()
    entry_events = len(review_events())
    entry_rows = scan_files()
    ev = census_events()
    ctrl = controls()
    time.sleep(1.0)
    exit_rows = scan_files()
    exit_events = len(review_events())

    e = {r["file"]: r.get("file_sha256") for r in entry_rows if "file" in r}
    x = {r["file"]: r.get("file_sha256") for r in exit_rows if "file" in r}
    file_drift = sorted((set(e) ^ set(x)) | {f for f in set(e) & set(x) if e[f] != x[f]})

    # --- live per-reviewer ledger from the file census -----------------------
    primary = [r for r in exit_rows if r.get("primary_f2b")]
    ledger = {}
    for r in primary:
        ledger.setdefault(r["reviewer"], []).append(r)
    per_reviewer = {}
    for rev, rows in sorted(ledger.items()):
        live_accept = [r for r in rows if r["classification"] == "bound_accept"]
        live_revise = [r for r in rows if r["classification"] in ("bound_revise", "bound_scoped")
                       and r["verdict"] == "revise"]
        evs = [v for v in ev if v["reviewer"] == rev]
        latest = evs[-1] if evs else None
        per_reviewer[rev] = {
            "files": [{"file": r["file"], "sha256": r.get("file_sha256"),
                       "classification": r["classification"], "verdict": r["verdict"],
                       "binding_fields": r.get("binding_fields"),
                       "mtime": r.get("file_mtime")} for r in rows],
            "live_full_accept_files": [r["file"] for r in live_accept],
            "live_bound_revise_files": [r["file"] for r in live_revise],
            "event_count": len(evs),
            "latest_event": latest,
            "event_flip": (any(v["verdict"] == "accept" for v in evs)
                           and any(v["verdict"] == "revise" for v in evs)),
        }

    # --- method reproduction (the two candidate counting methods) ------------
    m1 = sorted({r["reviewer"] for r in primary
                 if r["verdict"] == "accept" and "artifact_sha256" in (r.get("binding_fields") or [])})
    m2 = sorted({r["reviewer"] for r in primary
                 if r["verdict"] == "accept" and "reviewed_sha256" in (r.get("binding_fields") or [])})
    m_any = sorted({r["reviewer"] for r in primary if r["classification"] == "bound_accept"})
    live_revises = sorted({r["reviewer"] for r in primary
                           if r["classification"] in ("bound_revise", "bound_scoped")
                           and r["verdict"] == "revise"})
    scoped_accepts = sorted({r["reviewer"] for r in primary
                             if r["classification"] == "bound_scoped" and r["verdict"] == "accept"})
    cand_rows = [r for r in primary if r["classification"] == "bound_candidate_or_staged"]

    report = {
        "schema": "worker-018/f2b-coverage-census/v2",
        "actor": "worker-018",
        "task_id": "W018-F2B-COVERAGE-CENSUS-01",
        "node_id": "F2b",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "gate": "G-FORM",
        "why": ("CF-31: controller scan 4 accepts (worker-052/071/072/090) vs formulation-lead "
                "census 0 accept / 7 revise at F2b b2ab6acb2bbe. This census re-measures files "
                "and review events from disk and reproduces both counting methods."),
        "pins_measured": {
            "schemas/af_scc_c0_vacuum.yaml": sha256_file(os.path.join(ROOT, "schemas/af_scc_c0_vacuum.yaml")),
            "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml": sha256_file(os.path.join(ROOT, "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml")),
            "artifacts/formulation/FROZEN.json": sha256_file(os.path.join(ROOT, "artifacts/formulation/FROZEN.json")),
            "expected_f2b_pin": F2B_PIN,
            "expected_frozen_pin": FROZEN_PIN,
        },
        "measurement_window": {"entry": t0, "exit": now(),
                               "review_events_entry": entry_events, "review_events_exit": exit_events},
        "drift_within_run": {"files": file_drift,
                             "event_stream_grew_by": exit_events - entry_events},
        "review_files_scanned": len(exit_rows),
        "f2b_primary_files": len(primary),
        "live_file_full_accept_reviewers": m_any,
        "live_file_bound_revise_reviewers": live_revises,
        "live_file_scoped_accept_reviewers": scoped_accepts,
        "method_reproduction": {
            "M1_accept_files_binding_artifact_sha256": m1,
            "M2_accept_files_binding_reviewed_sha256": m2,
            "M3_accept_files_binding_any_field_or_exact_bytes": m_any,
            "M1_count": len(m1), "M2_count": len(m2), "M3_count": len(m_any),
            "reading": ("the accept files use reviewed_sha256; a census keyed on artifact_sha256 "
                        "returns zero accepts, which is the likely mechanism of the lead's 0-accept "
                        "count; the controller's fourth accept (worker-072) is superseded."),
        },
        "per_reviewer_ledger": per_reviewer,
        "f2b_primary_rows": primary,
        "f2b_bound_candidate_or_staged_rows": cand_rows,
        "event_census": ev,
        "controls": ctrl,
        "controls_ok": all(c["pass"] for c in ctrl),
        "authority_note": ("worker event: evidence for the r3 verifier, not a gate verdict, not a node "
                           "transition. Verdicts are read from live bytes at the instant named; review "
                           "files are mutable under fixed names (worker-072 accept->revise in place, "
                           "created_at preserved), so any count is void once the bytes move."),
        "falsifier": ("show a reviews/*.json file that binds b2ab6acb2bbe and carries a full-schema "
                      "accept not listed in live_file_full_accept_reviewers; or show that one of the "
                      "listed files is not bound to that hash / is not an accept / is scoped away from "
                      "the full schema; or show worker-072's accept is not superseded."),
        "next_falsifier": ("re-run census.py after any F2b write; all counts must be regenerated at the "
                           "new pin (CF-31 stop rule: coverage re-measured from disk at use time)."),
    }
    with open(os.path.join(OUTDIR, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")
    print("controls_ok", report["controls_ok"])
    print("M1(artifact_sha256)=", m1)
    print("M2(reviewed_sha256)=", m2)
    print("M3(any)=", m_any)
    print("revises=", live_revises)
    print("scoped_accepts=", scoped_accepts)
    print("candidate/staged rows=", [(r["reviewer"], r["file"]) for r in cand_rows])
    print("file_drift", file_drift, "| event_stream_grew_by", exit_events - entry_events)
    for c in ctrl:
        if not c["pass"]:
            print("CONTROL FAIL", c)
    return 0


if __name__ == "__main__":
    sys.exit(main())

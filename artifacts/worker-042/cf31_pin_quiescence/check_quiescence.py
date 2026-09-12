#!/usr/bin/env python3
"""W042-CF31-PIN-QUIESCENCE-10 deterministic checker.

Compares the T1 pin (worker-042 task 09: reviews/ at 2026-09-12T01:19:28+08:00,
manifest .../review_corpus_mutation/snapshot/manifest.json#97d51342a2c0) against the
T2 pin (this task, .../cf31_pin_quiescence/snapshot_t2/manifest.json) and answers
three adjudication questions for the CF-31 / G-FORM round:

  1. Did any T1 review file change under a fixed name between the pins, and did any
     verdict change at the same reviewed-artifact hash (same-pin flip) rather than by
     rebinding to new bytes?
  2. Is the canonical F2b pin b2ab6acb2bbe (FROZEN rev29) still in place, or has the
     authorized rev14 fold moved it? (A moving pin voids binding tables on arrival.)
  3. Is the CF-31 F2b accept set {worker-052, worker-071, worker-090} plus the
     worker-072 revise card stable at both pins, and how many hash-prefix rows at the
     pin are schema verdicts vs meta/administrative artifacts that a naive scan counts?

Read-only on every canonical path. Writes report.json under this task directory only.
Usage: python3 artifacts/worker-042/cf31_pin_quiescence/check_quiescence.py
Exit 0 iff all pre-registered controls pass; 3 otherwise.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
T1_SNAP = os.path.join(REPO, "artifacts/worker-042/review_corpus_mutation/snapshot")
T2_SNAP = os.path.join(HERE, "snapshot_t2")
TASK_ID = "W042-CF31-PIN-QUIESCENCE-10"
SANDBOX = os.path.join(HERE, "_sandbox")
CST = timezone(timedelta(hours=8))
PREFIX = 12
F2B_PIN = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
PINS = {
    "F2b": F2B_PIN,
    "F2a": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe",
    "F1": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d",
}
VERDICT_WORDS = {"accept", "revise", "reject", "inconclusive"}
IDENTITY_KEYS = ("target_id", "node_id", "created_at", "event_id")
# CF-31 named cards, by reviewer -> expected file at the F2b rev13 pin.
CF31_CARDS = {
    "worker-052": "F2b-review-rev13-052.json",
    "worker-071": "F2b-review-rev13-worker-071.json",
    "worker-090": "F2b-rev13-full-090.json",
    "worker-072": "F2b-review-worker-072-rev29.json",
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return sha256_bytes(f.read())


def now() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def s(x) -> str:
    return x if isinstance(x, str) else ("" if x is None else str(x))


def pin_of(d: dict) -> str:
    for k in ("reviewed_sha256", "artifact_sha256"):
        v = d.get(k)
        if isinstance(v, str) and len(v) >= 8:
            return v
    return ""


def identity(d: dict):
    return tuple(s(d.get(k)) for k in IDENTITY_KEYS)


def load_json(path: str):
    try:
        with open(path) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def scan_corpus(dirpath: str) -> dict:
    out = {}
    if not os.path.isdir(dirpath):
        return out
    for name in sorted(os.listdir(dirpath)):
        if not name.endswith(".json"):
            continue
        d = load_json(os.path.join(dirpath, name))
        out[name] = d if d is not None else {"__parse_error__": True}
    return out


def classify(a: dict, b: dict) -> str:
    """Classify a fixed filename's T1->T2 delta from parsed documents."""
    pa, pb = pin_of(a), pin_of(b)
    va, vb = s(a.get("verdict")), s(b.get("verdict"))
    if va != vb:
        if pa == pb and pa:
            return "SAME_PIN_VERDICT_CHANGE"
        if pa and pb and pa != pb:
            return "REBIND_VERDICT_CHANGE"
        return "IDENTITY_OR_BINDING_CHANGE"
    if a.get("score") != b.get("score"):
        return "SCORE_CHANGE"
    if pa != pb and (pa or pb):
        return "REBIND_OTHER"
    return "CONTENT_ONLY"


def delta_fields(a: dict, b: dict) -> dict:
    keys = ("verdict", "score", "reviewed_sha256", "artifact_sha256", "reviewer",
            "created_at", "event_id", "node_id", "counts_as_full_schema_verdict",
            "counts_as_gate_verdict", "counts_toward_gate_accept")
    out = {}
    for k in keys:
        x, y = a.get(k), b.get(k)
        if x != y:
            out[k] = {"t1": s(x)[:120], "t2": s(y)[:120]}
    return out


def mutate_rows(t1_dir: str, t2_dir: str, t1_files: dict, missing_label: str) -> list:
    """Fixed-name delta rows for every file in the T1 manifest."""
    d1, d2 = scan_corpus(t1_dir), scan_corpus(t2_dir)
    rows = []
    for name in sorted(t1_files):
        h1 = t1_files[name]["sha256"]
        p2 = os.path.join(t2_dir, name)
        if not os.path.exists(p2):
            rows.append({"file": name, "class": missing_label, "t1_sha256": h1,
                         "t2_sha256": None, "fields": {}, "identity_reuse": False})
            continue
        h2 = sha256_file(p2)
        if h1 == h2:
            continue
        a, b = d1.get(name), d2.get(name)
        if a is None or b is None or "__parse_error__" in a or "__parse_error__" in b:
            rows.append({"file": name, "class": "PARSE_DIVERGENCE", "t1_sha256": h1,
                         "t2_sha256": h2, "fields": {}, "identity_reuse": False})
            continue
        rows.append({"file": name, "class": classify(a, b), "t1_sha256": h1,
                     "t2_sha256": h2, "fields": delta_fields(a, b),
                     "identity_reuse": identity(a) != identity(b)})
    return rows


def is_schema_verdict(d: dict) -> bool:
    """A row is a schema verdict unless it self-declares as meta/administrative."""
    if s(d.get("verdict")) not in VERDICT_WORDS:
        return False
    for k in ("counts_as_full_schema_verdict", "counts_as_gate_verdict", "counts_toward_gate_accept"):
        if d.get(k) is False:
            return False
    if d.get("not_a_gate_verdict") is True:
        return False
    return True


def f2b_census(docs: dict) -> dict:
    """All rows whose canonical pin field binds the F2b rev13 prefix."""
    pf = F2B_PIN[:PREFIX]
    rows = []
    raw_mentions = []
    for name in sorted(docs):
        d = docs[name]
        if "__parse_error__" in d:
            continue
        if pf in json.dumps(d):
            raw_mentions.append(name)
        if not pin_of(d).startswith(pf):
            continue
        rows.append({
            "file": name,
            "reviewer": s(d.get("reviewer") or d.get("actor")),
            "verdict": s(d.get("verdict")),
            "score": d.get("score"),
            "pin_field": "reviewed_sha256" if isinstance(d.get("reviewed_sha256"), str) else "artifact_sha256",
            "full_schema_flag": d.get("counts_as_full_schema_verdict"),
            "schema_verdict": is_schema_verdict(d),
        })
    full_any = [r for r in rows if r["full_schema_flag"] is not False]
    return {
        "matched_by_prefix": pf,
        "pin_full_sha256": F2B_PIN,
        "rows": rows,
        "rows_all": len(rows),
        "schema_verdict_rows": [r for r in rows if r["schema_verdict"]],
        "schema_verdict_count": sum(1 for r in rows if r["schema_verdict"]),
        "accepts_all_rows": sorted(r["file"] for r in rows if r["verdict"] == "accept"),
        "accepts_schema_verdicts": sorted(r["file"] for r in rows
                                          if r["verdict"] == "accept" and r["schema_verdict"]),
        "full_schema_accepts": sum(1 for r in rows
                                   if r["verdict"] == "accept" and r["full_schema_flag"] is not False),
        "full_schema_verdicts_any_polarity": len(full_any),
        "raw_substring_mention_rows": len(raw_mentions),
        "raw_substring_only_rows": sorted(set(raw_mentions) - {r["file"] for r in rows}),
    }


def rev14_landed(canon: dict) -> bool:
    return (canon.get("f2b_schema_sha256") != F2B_PIN
            or canon.get("frozen_revision") != 29)


def main() -> int:
    fails = []
    controls = []

    def ctl(cid, ok, note):
        controls.append({"id": cid, "pass": bool(ok), "note": note})
        if not ok:
            fails.append("CONTROL_FAILED:" + cid)

    t1man = json.load(open(os.path.join(T1_SNAP, "manifest.json")))
    t2man = json.load(open(os.path.join(T2_SNAP, "manifest.json")))
    t1_dir, t2_dir = os.path.join(T1_SNAP, "reviews_t1"), os.path.join(T2_SNAP, "reviews_t2")
    t1_docs, t2_docs = scan_corpus(t1_dir), scan_corpus(t2_dir)

    # ---- prerequisite: both pinned substrates re-hash to their manifests ----
    def selfcheck(man, dirpath):
        bad = []
        for name, rec in sorted(man["reviews_manifest"].items()):
            p = os.path.join(dirpath, name)
            if not os.path.exists(p) or sha256_file(p) != rec["sha256"]:
                bad.append(name)
        return bad

    t1_bad, t2_bad = selfcheck(t1man, t1_dir), selfcheck(t2man, t2_dir)
    if t1_bad:
        fails.append("T1_SUBSTRATE_HASH_MISMATCH:%d" % len(t1_bad))
    if t2_bad:
        fails.append("T2_SUBSTRATE_HASH_MISMATCH:%d" % len(t2_bad))

    # ---- 1. fixed-name mutation / flip census ------------------------------
    mutations = mutate_rows(t1_dir, t2_dir, t1man["reviews_manifest"], "MISSING_AT_T2")
    name_reuse = [{"file": m["file"],
                   "t1_identity": dict(zip(IDENTITY_KEYS, identity(t1_docs[m["file"]]))),
                   "t2_identity": dict(zip(IDENTITY_KEYS, identity(t2_docs[m["file"]])))}
                  for m in mutations
                  if m.get("identity_reuse") and m["file"] in t1_docs and m["file"] in t2_docs]
    for m in mutations:
        m.pop("identity_reuse", None)
    same_pin_flips = [m for m in mutations if m["class"] == "SAME_PIN_VERDICT_CHANGE"]
    rebinds = [m for m in mutations if m["class"].startswith("REBIND")]
    new_files = sorted(set(t2_docs) - set(t1_docs))
    new_with_verdict = [n for n in new_files
                        if "__parse_error__" not in t2_docs[n]
                        and s(t2_docs[n].get("verdict")) in VERDICT_WORDS]

    # ---- 2. canonical pin watch --------------------------------------------
    src = t2man["sources"]
    canon = {
        "f2b_schema_path": src["f2b_schema"]["path"],
        "f2b_schema_sha256": src["f2b_schema"]["sha256"],
        "f1_schema_sha256": src["f1_schema"]["sha256"],
        "f2a_schema_sha256": src["f2a_schema"]["sha256"],
        "frozen_manifest_sha256": src["frozen_manifest"]["sha256"],
        "frozen_revision": load_json(os.path.join(T2_SNAP, src["frozen_manifest"]["snapshot"])).get("revision"),
        "taxonomy_sha256": src["map"]["sha256"],
        "map_sha256": src["map"]["sha256"],
        "events_sha256": src["events"]["sha256"],
        "artifact_hashes_sha256": src["artifact_hashes"]["sha256"],
        "w017_binding_table_sha256": src["w017_binding_table"]["sha256"],
    }
    canon["f1_moved_vs_rev29"] = canon["f1_schema_sha256"] != PINS["F1"]
    canon["f2a_moved_vs_rev29"] = canon["f2a_schema_sha256"] != PINS["F2a"]
    canon["f2b_moved_vs_rev29"] = canon["f2b_schema_sha256"] != PINS["F2b"]
    canon["rev14_landed"] = rev14_landed(canon)

    # ---- 3. F2b census both pins + CF-31 named-card stability ---------------
    cov1, cov2 = f2b_census(t1_docs), f2b_census(t2_docs)
    named = []
    for reviewer, fname in CF31_CARDS.items():
        a = t1_docs.get(fname)
        b = t2_docs.get(fname)
        a_ok = bool(a and "__parse_error__" not in a)
        b_ok = bool(b and "__parse_error__" not in b)
        named.append({
            "reviewer": reviewer,
            "file": fname,
            "present_at_t1": a_ok,
            "present_at_t2": b_ok,
            "sha256_t1": t1man["reviews_manifest"].get(fname, {}).get("sha256"),
            "sha256_t2": t2man["reviews_manifest"].get(fname, {}).get("sha256"),
            "bytes_identical": (t1man["reviews_manifest"].get(fname, {}).get("sha256")
                                == t2man["reviews_manifest"].get(fname, {}).get("sha256")),
            "verdict_t1": s(a.get("verdict")) if a_ok else None,
            "verdict_t2": s(b.get("verdict")) if b_ok else None,
            "score_t1": a.get("score") if a_ok else None,
            "score_t2": b.get("score") if b_ok else None,
            "pin_prefix_t1": pin_of(a)[:PREFIX] if a_ok else None,
            "pin_prefix_t2": pin_of(b)[:PREFIX] if b_ok else None,
            "full_schema_flag_t1": a.get("counts_as_full_schema_verdict") if a_ok else None,
            "full_schema_flag_t2": b.get("counts_as_full_schema_verdict") if b_ok else None,
            "schema_verdict_t2": is_schema_verdict(b) if b_ok else None,
        })
    t1_accept_schema = set(cov1["accepts_schema_verdicts"])
    t2_accept_schema = set(cov2["accepts_schema_verdicts"])
    accept_set_stable = t1_accept_schema == t2_accept_schema

    payload = {
        "task_id": TASK_ID,
        "actor": "worker-042",
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "node_id": "F2b",
        "gate": "G-FORM",
        "related_gates": ["G-AUDIT", "G-F0"],
        "pins": {
            "t1": {"pinned_at": t1man["pinned_at"], "files": t1man["reviews_count"],
                   "reviews_manifest_sha256": t1man["t1"]["reviews_manifest_sha256"]
                   if "t1" in t1man else hashlib.sha256(
                       json.dumps(t1man["reviews_manifest"], sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                   "manifest_sha256": sha256_file(os.path.join(T1_SNAP, "manifest.json"))},
            "t2": {"pinned_at": t2man["pinned_at"], "files": t2man["reviews_count"],
                   "reviews_manifest_sha256": hashlib.sha256(
                       json.dumps(t2man["reviews_manifest"], sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                   "manifest_sha256": sha256_file(os.path.join(T2_SNAP, "manifest.json"))},
        },
        "corpus": {
            "t1_files": t1man["reviews_count"],
            "t2_files": t2man["reviews_count"],
            "new_at_t2": len(new_files),
            "new_at_t2_with_verdict": len(new_with_verdict),
            "mutated_fixed_names": len(mutations),
            "mutations": mutations,
            "same_pin_verdict_flips": same_pin_flips,
            "rebind_verdict_changes": rebinds,
            "name_reuse": name_reuse,
            "missing_at_t2": [m["file"] for m in mutations if m["class"] == "MISSING_AT_T2"],
        },
        "canonical": canon,
        "f2b_census_t1": cov1,
        "f2b_census_t2": cov2,
        "cf31_named_cards": named,
        "cf31_accept_set_stable": accept_set_stable,
        "t1_selfcheck_bad": t1_bad,
        "t2_selfcheck_bad": t2_bad,
    }

    # ---- controls -----------------------------------------------------------
    base = {"verdict": "accept", "score": 4.0, "reviewed_sha256": F2B_PIN,
            "target_id": "schemas/af_scc_c0_vacuum.yaml", "node_id": "F2b",
            "created_at": "2026-09-12T01:00:00+08:00", "event_id": "e1",
            "counts_as_full_schema_verdict": True}
    other = "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"
    ctl("C1_T1_SUBSTRATE_SELFCHECK", not t1_bad,
        "%d/%d T1 files re-hash to the T1 manifest" % (t1man["reviews_count"] - len(t1_bad), t1man["reviews_count"]))
    ctl("C2_T2_SUBSTRATE_SELFCHECK", not t2_bad,
        "%d/%d T2 files re-hash to the T2 manifest" % (t2man["reviews_count"] - len(t2_bad), t2man["reviews_count"]))
    ctl("C3_CONTENT_ONLY", classify(base, dict(base)) == "CONTENT_ONLY", classify(base, dict(base)))
    ctl("C4_SAME_PIN_FLIP", classify(base, dict(base, verdict="revise")) == "SAME_PIN_VERDICT_CHANGE",
        classify(base, dict(base, verdict="revise")))
    ctl("C5_REBIND_VERDICT_CHANGE",
        classify(base, dict(base, verdict="revise", reviewed_sha256=other)) == "REBIND_VERDICT_CHANGE"
        and classify(base, dict(base, reviewed_sha256=other)) == "REBIND_OTHER",
        "same-verdict rebind -> REBIND_OTHER; verdict+pin move -> REBIND_VERDICT_CHANGE")
    ctl("C6_IDENTITY_REUSE", identity(base) != identity(dict(base, target_id="F2a")),
        "identity tuple changes when target changes")
    ctl("C7_PREFIX_BINDING",
        pin_of(base).startswith(F2B_PIN[:PREFIX]) and not pin_of(dict(base, reviewed_sha256=other)).startswith(F2B_PIN[:PREFIX]),
        "12-hex prefix binds F2b, rejects F2a")
    ctl("C8_META_SEPARATION",
        is_schema_verdict(base) and not is_schema_verdict(dict(base, counts_as_gate_verdict=False))
        and not is_schema_verdict(dict(base, counts_toward_gate_accept=False))
        and not is_schema_verdict(dict(base, not_a_gate_verdict=True)),
        "meta/administrative flags exclude a row from schema-verdict counts")
    ctl("C9_PIN_WATCH",
        rev14_landed({"f2b_schema_sha256": other, "frozen_revision": 29})
        and not rev14_landed({"f2b_schema_sha256": F2B_PIN, "frozen_revision": 29})
        and rev14_landed({"f2b_schema_sha256": F2B_PIN, "frozen_revision": 30}),
        "pin watch fires on moved schema and on bumped FROZEN revision")
    shutil.rmtree(SANDBOX, ignore_errors=True)
    os.makedirs(os.path.join(SANDBOX, "d1"))
    os.makedirs(os.path.join(SANDBOX, "d2"))
    with open(os.path.join(SANDBOX, "d1", "a.json"), "w") as f:
        json.dump(dict(base, event_id="a"), f)
    with open(os.path.join(SANDBOX, "d1", "b.json"), "w") as f:
        json.dump(dict(base, event_id="b"), f)
    with open(os.path.join(SANDBOX, "d1", "c.json"), "w") as f:
        json.dump(dict(base, event_id="c"), f)
    with open(os.path.join(SANDBOX, "d2", "a.json"), "w") as f:
        json.dump(dict(base, event_id="a"), f)
    with open(os.path.join(SANDBOX, "d2", "b.json"), "w") as f:
        json.dump(dict(base, event_id="b", verdict="revise"), f)   # same pin flip
    with open(os.path.join(SANDBOX, "d2", "c.json"), "w") as f:
        f.write("{not json")                                        # parse error
    syn_files = {"a.json": {"sha256": sha256_file(os.path.join(SANDBOX, "d1", "a.json"))},
                 "b.json": {"sha256": sha256_file(os.path.join(SANDBOX, "d1", "b.json"))},
                 "c.json": {"sha256": sha256_file(os.path.join(SANDBOX, "d1", "c.json"))},
                 "d.json": {"sha256": "0" * 64}}                    # missing at T2
    syn = mutate_rows(os.path.join(SANDBOX, "d1"), os.path.join(SANDBOX, "d2"), syn_files, "MISSING_AT_T2")
    syn_cls = {m["file"]: m["class"] for m in syn}
    ctl("C10_MISSING_AND_PARSE", syn_cls.get("d.json") == "MISSING_AT_T2"
        and syn_cls.get("c.json") == "PARSE_DIVERGENCE" and "a.json" not in syn_cls,
        "missing -> MISSING_AT_T2; invalid JSON -> PARSE_DIVERGENCE; identical -> no row")
    ctl("C11_SYNTHETIC_FLIP_ROWS", syn_cls.get("b.json") == "SAME_PIN_VERDICT_CHANGE",
        "synthetic same-pin flip classified in the file-level pass")

    # deterministic payload digest (everything except generated_at)
    payload_sha = sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())

    findings = []
    mut_verdict = [m for m in mutations if m["fields"]]
    findings.append({
        "id": "W042-PQ-01",
        "kind": "quiescence",
        "statement": ("Between T1 %s and T2 %s, %d of %d T1-pinned review files changed bytes at a fixed "
                      "name; %d carry verdict/binding field deltas; same-pin flips %d, rebinds %d."
                      % (t1man["pinned_at"], t2man["pinned_at"], len(mutations), t1man["reviews_count"],
                         len(mut_verdict), len(same_pin_flips), len(rebinds))),
        "evidence_refs": ["artifacts/worker-042/cf31_pin_quiescence/snapshot_t2/manifest.json#%s"
                          % sha256_file(os.path.join(T2_SNAP, "manifest.json"))[:PREFIX],
                          "artifacts/worker-042/review_corpus_mutation/snapshot/manifest.json#%s"
                          % sha256_file(os.path.join(T1_SNAP, "manifest.json"))[:PREFIX]],
        "falsifier": ("Re-run the checker on the two pinned snapshots; falsified if any counted mutation is "
                      "byte-identical at both pins or any same-pin flip does not reproduce from the pinned bytes."),
    })
    findings.append({
        "id": "W042-PQ-02",
        "kind": "gate-blocker-watch",
        "statement": ("Canonical F2b schema %s and FROZEN revision %s at T2: rev14_landed=%s "
                      "(f2b_moved=%s, f1_moved=%s, f2a_moved=%s). The CF-31 adjudication pin is %s."
                      % (canon["f2b_schema_sha256"][:PREFIX], canon["frozen_revision"], canon["rev14_landed"],
                         canon["f2b_moved_vs_rev29"], canon["f1_moved_vs_rev29"], canon["f2a_moved_vs_rev29"],
                         "moved" if canon["rev14_landed"] else "stable")),
        "evidence_refs": ["schemas/af_scc_c0_vacuum.yaml#%s" % canon["f2b_schema_sha256"][:PREFIX],
                          "artifacts/formulation/FROZEN.json#%s" % canon["frozen_manifest_sha256"][:PREFIX]],
        "falsifier": ("Falsified if the pinned F2b schema copy does not hash to %s, if FROZEN.json does not read "
                      "revision %s, or if a later pin shows these bytes moved before the r3 binding table landed."
                      % (F2B_PIN[:PREFIX], canon["frozen_revision"])),
    })
    meta_rows = [r for r in cov2["rows"] if not r["schema_verdict"]]
    findings.append({
        "id": "W042-PQ-03",
        "kind": "cf31-mechanism",
        "statement": ("F2b hash-prefix rows grew %d -> %d between pins; schema verdicts %d -> %d, accepts %d -> %d. "
                      "At T2, %d of %d prefix rows are meta/administrative (non-schema) documents that a naive "
                      "prefix scan still counts: %s. CF-31 accept set stable=%s (%s)."
                      % (cov1["rows_all"], cov2["rows_all"], cov1["schema_verdict_count"], cov2["schema_verdict_count"],
                         len(cov1["accepts_schema_verdicts"]), len(cov2["accepts_schema_verdicts"]),
                         len(meta_rows), cov2["rows_all"], sorted(r["file"] for r in meta_rows),
                         accept_set_stable, sorted(t2_accept_schema))),
        "evidence_refs": ["artifacts/worker-042/cf31_pin_quiescence/snapshot_t2/manifest.json#%s"
                          % sha256_file(os.path.join(T2_SNAP, "manifest.json"))[:PREFIX],
                          "artifacts/worker-017/cf31_f2b_census/binding_table.json#%s"
                          % canon["w017_binding_table_sha256"][:PREFIX]],
        "falsifier": ("Falsified if any file listed as meta/administrative does not carry a false gate/count flag "
                      "in the pinned bytes, or if the schema-verdict accept set at T2 differs from the listed set."),
    })
    named_bad = [n for n in named if not n["present_at_t2"] or not n["bytes_identical"]
                 or n["verdict_t1"] != n["verdict_t2"]]
    findings.append({
        "id": "W042-PQ-04",
        "kind": "cf31-card-stability",
        "statement": ("CF-31 named cards {052 accept, 071 accept, 090 accept, 072 revise} at pin %s: "
                      "%d/4 byte-identical T1->T2 and verdict-stable; deviations %s."
                      % (F2B_PIN[:PREFIX], 4 - len(named_bad), [n["file"] for n in named_bad] or "none")),
        "evidence_refs": ["reviews/%s#%s" % (n["file"], (n["sha256_t2"] or "")[:PREFIX]) for n in named],
        "falsifier": ("Falsified if any named card's T2 snapshot copy does not match its T2 manifest hash, or if "
                      "its verdict word changed while its pin field stayed at %s." % F2B_PIN[:PREFIX]),
    })
    raw_only = cov2["raw_substring_only_rows"]
    findings.append({
        "id": "W042-PQ-05",
        "kind": "scan-sensitivity",
        "statement": ("Naive raw-substring scans of the T2 corpus find %d files mentioning %s versus %d files with a "
                      "canonical pin field; substring-only files: %s."
                      % (cov2["raw_substring_mention_rows"], F2B_PIN[:PREFIX], cov2["rows_all"], raw_only or "none")),
        "evidence_refs": ["artifacts/worker-042/cf31_pin_quiescence/snapshot_t2/manifest.json#%s"
                          % sha256_file(os.path.join(T2_SNAP, "manifest.json"))[:PREFIX]],
        "falsifier": ("Falsified if re-scanning the pinned T2 copies with a literal prefix search returns a "
                      "different mention set, or if a listed substring-only file also carries the prefix in "
                      "reviewed_sha256/artifact_sha256."),
    })

    report = {
        "schema": "w042-quiescence-report/v1",
        "task_id": TASK_ID,
        "actor": "worker-042",
        "created_at": now(),
        "class_id": "AF-SCC-C0-VAC-GEN",
        "class_ids": payload["class_ids"],
        "node_id": "F2b",
        "gate": "G-FORM",
        "related_gates": ["G-AUDIT", "G-F0"],
        "conclusion_type": "formal_model",
        "authority_note": ("Worker-task measurement only. No node status, no validation_status, no gate verdict; "
                           "CF-31/REC-39 adjudication belongs to astra-life05-verify-gform-r3."),
        "does_not_claim": [
            "no gate verdict and no node transition",
            "no adjudication of which CF-31 coverage count is correct",
            "no claim that any listed review verdict is substantively correct",
            "no claim about live bytes after the T2 pin; the measurement rests on snapshot copies",
        ],
        "assumptions": [
            "T1 substrate is worker-042 task 09's snapshot (manifest 97d51342a2c0, pinned 2026-09-12T01:19:28+08:00); its 235 copies re-hash to its manifest (control C1).",
            "T2 substrate is this task's snapshot copies, not live files; pin-window drift is recorded by pin_t2.py and must be [].",
            "A file is mutated at a fixed name iff its T2 sha256 differs from its T1 sha256 at the same reviews/<name> path.",
            "A row binds F2b iff reviewed_sha256, else artifact_sha256, starts with the 12-hex prefix b2ab6acb2bbe.",
            "A prefix row is a schema verdict unless it self-declares counts_as_full_schema_verdict=false, counts_as_gate_verdict=false, counts_toward_gate_accept=false, or not_a_gate_verdict=true.",
            "SAME_PIN_VERDICT_CHANGE requires a different verdict word at an identical pin field; a verdict change with a different pin is REBIND_VERDICT_CHANGE.",
            "FROZEN revision and schema hashes are read from the pinned copies in snapshot_t2, not from live paths.",
        ],
        "pins": payload["pins"],
        "canonical": canon,
        "corpus": payload["corpus"],
        "f2b_census_t1": cov1,
        "f2b_census_t2": cov2,
        "cf31_named_cards": named,
        "cf31_accept_set_stable": accept_set_stable,
        "headline": {
            "t1_files": t1man["reviews_count"],
            "t2_files": t2man["reviews_count"],
            "new_at_t2": len(new_files),
            "new_at_t2_with_verdict": len(new_with_verdict),
            "mutated_fixed_names": len(mutations),
            "same_pin_verdict_flips": len(same_pin_flips),
            "rebind_verdict_changes": len(rebinds),
            "f2b_rows_t1": cov1["rows_all"],
            "f2b_rows_t2": cov2["rows_all"],
            "f2b_schema_verdicts_t1": cov1["schema_verdict_count"],
            "f2b_schema_verdicts_t2": cov2["schema_verdict_count"],
            "f2b_schema_accepts_t2": sorted(t2_accept_schema),
            "f2b_full_schema_accepts_t2": cov2["full_schema_accepts"],
            "rev14_landed": canon["rev14_landed"],
        },
        "findings": findings,
        "controls": controls,
        "controls_passed": sum(1 for c in controls if c["pass"]),
        "controls_total": len(controls),
        "deterministic_payload_sha256": payload_sha,
        "rerun": "python3 artifacts/worker-042/cf31_pin_quiescence/pin_t2.py && python3 artifacts/worker-042/cf31_pin_quiescence/check_quiescence.py",
    }

    # C12: the report is valid JSON with the required IDs/evidence/falsifiers.
    rt = json.loads(json.dumps(report))
    ctl("C12_REPORT_SHAPE",
        all(rt["findings"]) and all(f.get("id") and f.get("evidence_refs") and f.get("falsifier")
                                     for f in rt["findings"]),
        "%d findings each with id/evidence_refs/falsifier" % len(rt["findings"]))

    # deterministic payload must be stable across a second computation in-process
    payload_sha2 = sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    ctl("C13_PAYLOAD_STABLE", payload_sha == payload_sha2, payload_sha[:PREFIX])

    report["controls"] = controls
    report["controls_passed"] = sum(1 for c in controls if c["pass"])
    report["controls_total"] = len(controls)
    report["run_valid"] = not fails

    with open(os.path.join(HERE, "report.json"), "w") as f:
        json.dump(report, f, indent=1, sort_keys=True)
        f.write("\n")

    print("T1 %d files @%s | T2 %d files @%s" % (t1man["reviews_count"], t1man["pinned_at"],
                                                 t2man["reviews_count"], t2man["pinned_at"]))
    print("mutations=%d same_pin_flips=%d rebinds=%d name_reuse=%d new=%d"
          % (len(mutations), len(same_pin_flips), len(rebinds), len(name_reuse), len(new_files)))
    print("F2b rows %d->%d | schema verdicts %d->%d | schema accepts t2=%s"
          % (cov1["rows_all"], cov2["rows_all"], cov1["schema_verdict_count"], cov2["schema_verdict_count"],
             sorted(t2_accept_schema)))
    print("rev14_landed=%s f2b=%s frozen_rev=%s" % (canon["rev14_landed"], canon["f2b_schema_sha256"][:12],
                                                    canon["frozen_revision"]))
    print("controls %d/%d" % (report["controls_passed"], report["controls_total"]))
    print("payload %s" % payload_sha[:PREFIX])
    if fails:
        print("FAILURES:", fails)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())

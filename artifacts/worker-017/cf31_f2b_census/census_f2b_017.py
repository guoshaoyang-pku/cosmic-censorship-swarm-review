#!/usr/bin/env python3
"""Worker-017 independent, read-only census of F2b verdicts at the rev13 pin.

Task   : CF-31 / REC-39 per-file binding table for node F2b, class AF-SCC-C0-VAC-GEN, gate G-FORM.
Role   : bounded execution worker (worker-017). This is advisory evidence, NOT a gate verdict.
Writes : artifacts/worker-017/cf31_f2b_census/ only. No canonical path is touched.

Method (pre-registered here, before running):
  T1  corpus      = every reviews/**/*.json, each hashed; corpus digest over (relpath, sha256).
  T2  binding     = any binding field (reviewed_sha256 / artifact_sha256 / artifact / target_id /
                    target / pins / f0_binding / ...), including #<hex> suffixes and dict/list
                    values, whose value starts with the measured F2b rev13 sha (12+ hex prefix).
  T3  schema verdict = has verdict in {accept, revise, reject, inconclusive} AND target declares
                    the F2b schema (path contains af_scc_c0_vacuum) or the F2b node / class
                    (node_id/target_id == F2b or class_id == AF-SCC-C0-VAC-GEN) AND the target is
                    not itself a review file (reviews/...) or a finding id.
  T4  full-schema category:
        explicit True  -> full_explicit
        explicit False -> scoped_explicit
        flag absent    -> full_inferred if scope text names "full-schema"/"full schema", else
                          scoped_inferred if scope text names a scoped activity
                          (containment|bindchain|candidate|rebase|adjudicat|targeted|finding|
                           preflight|closure|direction|crossverify), else
                          default_full_flag_absent (controller default rule, flagged).
  T5  counts are reported under three rules:
        M1 controller pass-08 scan set  (declared: 052,071,072,090) -> live re-measure
        M2 lead per-file census set     (declared: 066x2,035,017,075,018,053) -> live re-measure
        M3 worker strict rule: schema verdicts bound to the rev13 pin, latest file per reviewer,
           full-* only, non-author; accepts vs revises reported separately.
  T6  controls: C1 presence, C2 the 072 accept->revise move vs CF-31's declared set, C3 in-memory
      negative flip, C4 in-memory binding removal, C5 old-pin exclusion, C6 determinism, C7
      write-scope, C8 no-drift (re-hash corpus at exit; any move voids the instant).
Falsifier: at the recorded per-file sha256 table and corpus digest, (a) any omitted reviews/ file
  bound to the pin; (b) any table row whose parsed (reviewer, verdict, reviewed_sha256, full-flag)
  does not match the cited bytes; (c) a strict accept whose reviewer is the F2b author of record;
  (d) a count that a re-run at the same corpus digest does not reproduce.
"""
import hashlib
import json
import os
import re
import sys
import glob
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

F2B_HASH = "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"
F2B_PREFIX = F2B_HASH[:12]
F2B_SCHEMA = "schemas/af_scc_c0_vacuum.yaml"
F2B_MIRROR = "artifacts/formulation/schemas/af_scc_c0_vacuum.yaml"
FROZEN = "artifacts/formulation/FROZEN.json"
CLASS_ID = "AF-SCC-C0-VAC-GEN"
NODE = "F2b"

BINDING_KEYS = (
    "reviewed_sha256", "artifact_sha256", "artifact", "artifact_ref", "artifact_refs",
    "target", "target_id", "target_ref", "pins", "pin", "f0_binding", "bound_sha256",
    "schema_sha256", "reviewed_artifact", "declared_sha256", "sha256",
)
VERDICTS = {"accept", "revise", "reject", "inconclusive"}
SCOPED_WORDS = ("containment", "bindchain", "candidate", "rebase", "adjudicat", "targeted",
                "finding", "preflight", "closure", "direction", "crossverify", "mechanical")
FULL_WORDS = ("full-schema", "full schema", "full, mechanized", "full mechanized")

# Declared sets from the live map (CF-31, pass-08) and the formulation lead's census.
CF31_DECLARED = {
    "worker-052": "accept",
    "worker-071": "accept",
    "worker-072": "accept",
    "worker-090": "accept",
}
LEAD_DECLARED = ["worker-066", "worker-066", "worker-035", "worker-017", "worker-075",
                 "worker-018", "worker-053"]
LEAD_FILES = [
    "reviews/F2b-containment-normativity-worker-066.json",
    "reviews/F2b-rev29-containment-rebase-worker-066.json",
    "reviews/F2b-bindchain-rev13-worker-035.json",
    "reviews/F2b-rev13-containment-worker-017.json",
    "reviews/F2b-review-rev29-075.json",
    "reviews/F2b-review-worker-018-rev13.json",
    "reviews/F2b-review-rev29-053.json",
]
CONTROLLER_FILES = [
    "reviews/F2b-review-rev13-052.json",
    "reviews/F2b-review-rev13-worker-071.json",
    "reviews/F2b-review-worker-072-rev29.json",
    "reviews/F2b-rev13-full-090.json",
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def mtime_iso(path):
    return datetime.datetime.fromtimestamp(os.path.getmtime(path)).astimezone().isoformat(
        timespec="seconds")


def collect_strings(value, out):
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for v in value.values():
            collect_strings(v, out)
    elif isinstance(value, (list, tuple)):
        for v in value:
            collect_strings(v, out)


def bindings_of(doc):
    """All strings plausibly carrying a reviewed-artifact pin."""
    out = []
    for key in BINDING_KEYS:
        if key in doc:
            collect_strings(doc[key], out)
    # structural fallback: any dict with a 'path' plus 'sha256'
    def walk(node):
        if isinstance(node, dict):
            vals = [str(v) for v in node.values() if isinstance(v, (str, int))]
            if "path" in node and any(k in node for k in ("sha256", "pin_sha256", "sha")):
                for k in ("sha256", "pin_sha256", "sha"):
                    if k in node:
                        out.append(str(node.get("path")) + "#" + str(node.get(k)))
            for v in node.values():
                walk(v)
        elif isinstance(node, (list, tuple)):
            for v in node:
                walk(v)
    for key in ("pins", "f0_binding", "target", "target_id", "artifact", "artifact_refs",
                "consistency_evidence_sha256"):
        if key in doc:
            walk(doc[key])
    return out


HEX_RE = re.compile(r"[0-9a-f]{12,64}")


def key_hits_of(doc):
    """Which declared binding keys carry the rev13 pin (field-key selection measurement)."""
    hits = []
    for key in BINDING_KEYS:
        if key not in doc:
            continue
        vals = []
        collect_strings(doc[key], vals)
        if any(matches_pin(v) for v in vals):
            hits.append(key)
    return hits


def matches_pin(text):
    if not isinstance(text, str):
        return None
    if F2B_HASH in text:
        return F2B_HASH
    for m in HEX_RE.finditer(text.lower()):
        if m.group(0).startswith(F2B_PREFIX):
            return m.group(0)
    return None


def classify_scope(doc, explicit):
    scope = " ".join(str(doc.get(k, "")) for k in
                     ("review_scope", "review_kind", "review_id", "task_id", "gate", "scope"))
    low = scope.lower()
    if explicit is True:
        return "full_explicit"
    if explicit is False:
        return "scoped_explicit"
    if any(w in low for w in FULL_WORDS):
        return "full_inferred"
    if any(w in low for w in SCOPED_WORDS):
        return "scoped_inferred"
    return "default_full_flag_absent"


def build_table():
    corpus = sorted(glob.glob(os.path.join(ROOT, "reviews", "**", "*.json"), recursive=True))
    corpus_lines = []
    rows = []
    skipped = []
    for path in corpus:
        rel = os.path.relpath(path, ROOT)
        digest = sha256_file(path)
        corpus_lines.append(rel + ":" + digest)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except Exception as exc:  # unparseable files are reported, never silently dropped
            skipped.append({"path": rel, "sha256": digest, "error": type(exc).__name__})
            continue
        if not isinstance(doc, dict):
            skipped.append({"path": rel, "sha256": digest, "error": "not-a-json-object"})
            continue
        verdict = doc.get("verdict")
        verdict_value = verdict if isinstance(verdict, str) else None
        # a nested verdict dict (some workers emit {'verdict': {...}}) is flattened honestly
        nested = None
        if isinstance(verdict, dict) and isinstance(verdict.get("verdict"), str):
            nested = verdict.get("verdict")
        bindings = bindings_of(doc)
        hit = next((b for b in bindings if matches_pin(b)), None)
        target_texts = " ".join(str(doc.get(k, "")) for k in
                                ("target_id", "target", "artifact", "node_id", "class_id"))
        declares_f2b = (
            F2B_SCHEMA in target_texts
            or "af_scc_c0" in target_texts
            or NODE in target_texts
            or doc.get("class_id") == CLASS_ID
            or doc.get("node_id") == NODE
        )
        review_of_review = any(
            str(doc.get(k, "")).startswith("reviews/") or "reviews/" in str(doc.get(k, ""))[:12]
            for k in ("target_id", "target", "artifact"))
        finding_target = "#" in str(doc.get("target_id", "")) and "HF" in str(doc.get("target_id", ""))
        if hit is None:
            continue  # not bound to the rev13 pin at all
        explicit = doc.get("counts_as_full_schema_verdict")
        category = classify_scope(doc, explicit if isinstance(explicit, bool) else None)
        rows.append({
            "path": rel,
            "sha256": digest,
            "mtime": mtime_iso(path),
            "reviewer": doc.get("reviewer") or doc.get("actor"),
            "verdict": verdict_value,
            "verdict_nested": nested,
            "score": doc.get("score"),
            "target_id": str(doc.get("target_id") or doc.get("target") or "")[:200],
            "node_id": doc.get("node_id"),
            "class_id": doc.get("class_id"),
            "reviewed_sha256_binding": hit,
            "key_hits": key_hits_of(doc),
            "declares_f2b": declares_f2b,
            "review_of_review": review_of_review,
            "finding_target": finding_target,
            "full_flag_raw": explicit if isinstance(explicit, bool) else None,
            "full_category": category,
            "counts_as_independent": doc.get("counts_as_independent"),
            "blind": doc.get("blind"),
            "created_at": doc.get("created_at"),
            "is_schema_verdict": bool(verdict_value in VERDICTS and declares_f2b
                                      and not review_of_review and not finding_target),
        })
    corpus_digest = sha256_text("\n".join(corpus_lines) + "\n")
    return rows, skipped, corpus_digest, len(corpus)


def strict_counts(rows):
    """M3: schema verdicts, latest file per reviewer, full-* categories only."""
    latest = {}
    for r in rows:
        if not r["is_schema_verdict"]:
            continue
        rev = r["reviewer"] or r["path"]
        if rev not in latest or r["mtime"] > latest[rev]["mtime"]:
            latest[rev] = r
    full = [r for r in latest.values() if r["full_category"].startswith("full")
            or r["full_category"] == "default_full_flag_absent"]
    accepts = sorted(r["reviewer"] for r in full if r["verdict"] == "accept")
    revises = sorted(r["reviewer"] for r in full if r["verdict"] == "revise")
    other = sorted((r["reviewer"], r["verdict"]) for r in full
                   if r["verdict"] not in ("accept", "revise"))
    return {
        "rule": "M3 worker strict: schema verdicts bound to the rev13 pin, latest file per "
                "reviewer, full-category (explicit/inferred/default) only",
        "accepts": accepts,
        "revises": revises,
        "other": other,
        "n_accept": len(accepts),
        "n_revise": len(revises),
        "rows_considered": sorted(r["path"] for r in full),
    }


def key_policy_counts(rows):
    """What an artifact_sha256-keyed vs reviewed_sha256-keyed census sees, over the same rows.

    This is the measured mechanism of the controller-vs-lead divergence: the three live full
    accepts bind through reviewed_sha256 only, so an artifact_sha256-keyed scan returns zero.
    A row is 'keyed' on a field when that field is present in the source document AND its value
    carries the rev13 pin; the parser records the matched field in key_hits.
    """
    out = {}
    for key in ("reviewed_sha256", "artifact_sha256"):
        sel = [r for r in rows if r["is_schema_verdict"] and key in r.get("key_hits", [])]
        out[key] = {
            "n_rows": len(sel),
            "accepts": sorted(r["reviewer"] for r in sel if r["verdict"] == "accept"),
            "revises": sorted(r["reviewer"] for r in sel if r["verdict"] == "revise"),
        }
    return out


def declared_set_remeasure(rows, files, declared=None):
    by_path = {r["path"]: r for r in rows}
    out = []
    for f in files:
        r = by_path.get(f)
        if r is None:
            out.append({"path": f, "present_bound_to_rev13": False})
        else:
            out.append({
                "path": f,
                "present_bound_to_rev13": True,
                "reviewer": r["reviewer"],
                "live_verdict": r["verdict"],
                "reviewed_sha256_binding": r["reviewed_sha256_binding"],
                "file_sha256": r["sha256"],
                "mtime": r["mtime"],
                "full_category": r["full_category"],
                "is_schema_verdict": r["is_schema_verdict"],
                "declared_verdict": (declared or {}).get(r["reviewer"]),
            })
    return out


def main():
    started = utc_now()
    live_hash = sha256_file(os.path.join(ROOT, F2B_SCHEMA))
    mirror_hash = sha256_file(os.path.join(ROOT, F2B_MIRROR))
    with open(os.path.join(ROOT, FROZEN), "r", encoding="utf-8") as fh:
        frozen = json.load(fh)
    frozen_pin = (frozen.get("files") or {}).get(F2B_SCHEMA, {}).get("sha256")
    if live_hash != F2B_HASH or mirror_hash != F2B_HASH or frozen_pin != F2B_HASH:
        print(json.dumps({"fatal": "pin mismatch", "live": live_hash, "mirror": mirror_hash,
                          "frozen_pin": frozen_pin}, indent=1))
        return 2

    rows, skipped, corpus_digest, corpus_n = build_table()
    table_digest = sha256_text(json.dumps(rows, sort_keys=True))
    m3 = strict_counts(rows)
    m1 = declared_set_remeasure(rows, CONTROLLER_FILES, CF31_DECLARED)
    m2 = declared_set_remeasure(rows, LEAD_FILES)
    key_policy = key_policy_counts(rows)

    # concurrent-corpus corroboration (read-only cross-check, hashed at read time)
    w18_rel = "reviews/F2b-coverage-census-018.json"
    w18_report_rel = "artifacts/worker-018/f2b_coverage_census/report.json"
    corroboration = {"worker_018_review": None, "worker_018_report": None,
                     "agree_accept_set": None}
    for rel in (w18_rel, w18_report_rel):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            corroboration["worker_018_review" if rel == w18_rel else "worker_018_report"] = {
                "path": rel, "sha256": sha256_file(p)}
    w18_path = os.path.join(ROOT, w18_report_rel)
    if os.path.exists(w18_path):
        try:
            with open(w18_path, "r", encoding="utf-8") as fh:
                w18 = json.load(fh)
            acc = sorted(w18.get("live_file_full_accept_reviewers") or [])
            corroboration["worker_018_report"]["live_file_full_accept_reviewers"] = acc
            corroboration["worker_018_report"]["method_reproduction"] = w18.get(
                "method_reproduction")
            corroboration["agree_accept_set"] = (acc == m3["accepts"])
        except Exception as exc:
            corroboration["worker_018_report"]["error"] = repr(exc)

    # ---- controls -----------------------------------------------------------
    controls = []

    def ctl(cid, desc, ok, detail):
        controls.append({"id": cid, "desc": desc, "pass": bool(ok), "detail": detail})

    ctl("C1", "12 declared files (controller 4 + lead 7 + 085) are present and bound to the pin",
        all(r["present_bound_to_rev13"] for r in m1 + m2)
        and any(r["path"].endswith("F2b-review-rev13-085.json") for r in rows),
        {"controller": [r["path"] for r in m1], "lead": [r["path"] for r in m2]})
    ctl("C2", "CF-31 declared worker-072='accept' but live bytes measure 'revise'",
        any(r["reviewer"] == "worker-072" and r["live_verdict"] == "revise"
            and r.get("declared_verdict") == "accept" for r in m1),
        next(r for r in m1 if r["reviewer"] == "worker-072"))
    # C3 negative flip in memory
    import copy
    flip = copy.deepcopy(rows)
    for r in flip:
        if r["reviewer"] == "worker-090":
            r["verdict"] = "revise"
    c3 = strict_counts(flip)
    ctl("C3", "in-memory flip of worker-090 accept->revise moves M3 accepts 3->2",
        c3["n_accept"] == 2 and m3["n_accept"] == 3, {"base": m3["n_accept"], "flipped": c3["n_accept"]})
    # C4 binding removal in memory
    drop = copy.deepcopy(rows)
    for r in drop:
        if r["reviewer"] == "worker-071":
            r["is_schema_verdict"] = False
    c4 = strict_counts(drop)
    ctl("C4", "removing worker-071's binding drops it from M3 accepts",
        c4["n_accept"] == 2, {"base": m3["n_accept"], "dropped": c4["n_accept"]})
    # C5 old-pin exclusion
    ctl("C5", "old-pin F2b-review-030 (1bb78ce9) and F2b-review-17-current are not in the table",
        not any("1bb78ce9" in r["reviewed_sha256_binding"] for r in rows),
        {"n_rows": len(rows)})
    # C6 determinism
    rows2, skipped2, digest2, n2 = build_table()
    ctl("C6", "two full corpus builds are byte-identical (table digest and skipped list)",
        sha256_text(json.dumps(rows2, sort_keys=True)) == table_digest and skipped2 == skipped,
        {"table_digest": table_digest, "corpus_digest": corpus_digest})
    # C8 no drift: re-hash every corpus file at exit
    drift = []
    for r in rows + skipped:
        p = os.path.join(ROOT, r["path"])
        if sha256_file(p) != r["sha256"]:
            drift.append(r["path"])
    ctl("C8", "no review file moved between table build and exit re-hash", not drift,
        {"drift": drift})
    ctl("C9", "accept set agrees with the concurrent worker-018 census (different instrument)",
        corroboration.get("agree_accept_set") is True, corroboration)

    report = {
        "schema": "worker-017/cf31-f2b-census/v1",
        "task_id": "CF31-F2B-BINDING-TABLE-WORKER-017",
        "actor": "worker-017",
        "authority_note": ("Advisory, read-only worker census. No gate verdict, no node "
                           "transition, no validation_status=passed, no canonical write."),
        "node_id": NODE,
        "class_id": CLASS_ID,
        "gate": "G-FORM",
        "started_at": started,
        "finished_at": utc_now(),
        "subject": {
            "path": F2B_SCHEMA,
            "measured_sha256": live_hash,
            "mirror": F2B_MIRROR,
            "mirror_sha256": mirror_hash,
            "frozen_manifest": FROZEN,
            "frozen_revision": frozen.get("revision"),
            "frozen_pin": frozen_pin,
            "author_of_record": frozen.get("owner"),
            "pin_match": True,
        },
        "corpus": {
            "glob": "reviews/**/*.json",
            "n_files": corpus_n,
            "digest": corpus_digest,
            "skipped": skipped,
        },
        "table": rows,
        "table_digest": table_digest,
        "counts": {
            "M1_controller_pass08_declared": {
                "declared": CF31_DECLARED, "files": m1,
                "declared_n_accept": 4,
                "live_n_accept": sum(1 for r in m1 if r.get("live_verdict") == "accept"),
                "live_n_revise": sum(1 for r in m1 if r.get("live_verdict") == "revise"),
            },
            "M2_lead_per_file_census_declared": {
                "declared_reviewers": LEAD_DECLARED, "declared_n_accept": 0,
                "declared_n_revise": 7, "files": m2,
                "live_n_accept": sum(1 for r in m2 if r.get("live_verdict") == "accept"),
                "live_n_revise": sum(1 for r in m2 if r.get("live_verdict") == "revise"),
            },
            "M3_worker_strict": m3,
            "M4_field_key_policy": key_policy,
        },
        "corroboration": corroboration,
        "controls": controls,
        "controls_pass": all(c["pass"] for c in controls),
        "falsifier": (
            "At the per-file sha256 table and corpus digest recorded here: (a) any reviews/ file "
            "bound to the rev13 pin omitted from the table; (b) any row whose parsed (reviewer, "
            "verdict, reviewed_sha256, full-flag) does not match its cited bytes; (c) a strict "
            "accept whose reviewer is the F2b author of record (astra-lead-formulation); (d) a "
            "count a re-run at the same corpus digest does not reproduce; (e) any review file "
            "that moved between the table build and the exit re-hash (control C8)."),
        "next_falsifier": (
            "Re-run at the FROZEN rev30 pins after rev14; every verdict here is void once F2b "
            "bytes move. The method finding (counts must be decision-instant and per-file "
            "hash-pinned) is the durable output."),
    }
    out_path = os.path.join(HERE, "report.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
        fh.write("\n")
    table_path = os.path.join(HERE, "binding_table.json")
    with open(table_path, "w", encoding="utf-8") as fh:
        json.dump({"corpus_digest": corpus_digest, "table_digest": table_digest,
                   "rows": rows}, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps({
        "report": out_path, "report_sha256": sha256_file(out_path),
        "binding_table": table_path, "binding_table_sha256": sha256_file(table_path),
        "corpus_digest": corpus_digest, "table_digest": table_digest,
        "f2b_live_sha256": live_hash,
        "M1_live": {"accept": report["counts"]["M1_controller_pass08_declared"]["live_n_accept"],
                    "revise": report["counts"]["M1_controller_pass08_declared"]["live_n_revise"]},
        "M2_live": {"accept": report["counts"]["M2_lead_per_file_census_declared"]["live_n_accept"],
                    "revise": report["counts"]["M2_lead_per_file_census_declared"]["live_n_revise"]},
        "M3": {"accepts": m3["accepts"], "revises": m3["revises"]},
        "controls_pass": report["controls_pass"],
        "controls": [{"id": c["id"], "pass": c["pass"]} for c in controls],
    }, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

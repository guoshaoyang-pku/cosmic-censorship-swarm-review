#!/usr/bin/env python3
"""W086-GFORM-R3-COVERAGE-VERIFY-01 — independent read-only verification of
reviews/G-FORM-final-verify-r3.json (astra-lead-audit, assignment astra-life05-verify-gform-r3).

Question: does the r3 coverage adjudication's counted accept list actually bind, at the live
F1/F2a/F2b pins, under the conditions the artifact's own falsifiers name, and does it carry the
REC-39 minimum content?

Read-only on every canonical path. Writes only its own report. Deterministic: no wall-clock
value enters the digest basis. Mutation controls run on in-memory deep copies only.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "reviews/G-FORM-final-verify-r3.json"
MAP = ROOT / "research_map/research_map.json"
EVENTS = ROOT / "research_map/events.jsonl"
OUTBOX = ROOT / "comms/outbox"
OUT = Path(__file__).resolve().parent / "report.json"

PINS = {
    "F1": {"path": "schemas/af_wcc_vacuum.yaml",
           "sha256": "d9cebb9404b2e79ef9dab7df7b13113dd3fbd9900848a810eb8d78bd357c5d3d"},
    "F2a": {"path": "schemas/af_scc_c2_vacuum.yaml",
            "sha256": "e9a27996dfd308bd6d057076787eb7f514f9ac4ba78997d6bfb77774169d82fe"},
    "F2b": {"path": "schemas/af_scc_c0_vacuum.yaml",
            "sha256": "b2ab6acb2bbe7f86903e4d41082a4aa4ff19149d5d6fc7206aad5aa861b4501c"},
}
FROZEN = {"path": "artifacts/formulation/FROZEN.json",
          "sha256": "815e08079aefbc168f156d7c15b304aaa3df7674bbd591aa4ec9195bc5188ae0"}
AUTHOR = {"F1": "astra-lead-formulation", "F2a": "astra-lead-formulation", "F2b": "astra-lead-formulation"}
TARGET_AUTHOR = "astra-lead-audit"
PIN_BY_CLASS = {"AF-WCC-VAC-GEN": "F1", "AF-SCC-C2-VAC-GEN": "F2a", "AF-SCC-C0-VAC-GEN": "F2b"}
DECLARED_HASH_KEYS = ("reviewed_sha256", "artifact_sha256", "artifact_sha256_verdict",
                      "reviewed_frozen_sha256", "reviewed_hash", "sha256", "pin")
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")
HEX12 = re.compile(r"\b[0-9a-f]{12}\b")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def load_jsonl(p: Path):
    rows = []
    for ln in p.read_text(errors="replace").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except Exception:
            continue
    return rows


def norm_ts(v) -> str:
    s = str(v or "")
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:{m.group(6)}"
    m = re.match(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:{m.group(6)}"
    return ""


def registry(map_obj, events_rows, outbox_rows):
    """event_id -> record. Map record wins; events fill gaps; outbox adds un-ingested reviews."""
    reg = {}
    for e in outbox_rows:
        if e.get("event_type") == "review" and e.get("event_id"):
            reg[e["event_id"]] = e
    for e in events_rows:
        if e.get("event_type") == "review" and e.get("event_id"):
            reg[e["event_id"]] = e
    for r in map_obj.get("reviews", []):
        eid = r.get("event_id") or r.get("id")
        if eid:
            reg[eid] = r
    return reg


def hash_tokens(rec) -> set:
    txt = json.dumps(rec)
    return set(HEX64.findall(txt)) | set(HEX12.findall(txt))


def bound_pin(rec, reg):
    """Return F1/F2a/F2b from the record's own declared hash fields.

    Declared fields are authoritative: if any are present but none match a pin, the record is
    unbound (None). Token-scan fallback is used only when no declared hash field exists at all.
    """
    cand = []
    for k in DECLARED_HASH_KEYS:
        v = rec.get(k)
        if isinstance(v, str):
            cand.append(v)
    tgt = rec.get("target_id")
    if isinstance(tgt, str):
        cand.append(tgt)
    if cand:
        for node, meta in PINS.items():
            pin = meta["sha256"]
            if any((pin == c) or (pin[:12] in c) or (c in pin and len(c) >= 12) for c in cand):
                return node
        return None
    toks = hash_tokens(rec)
    for node, meta in PINS.items():
        if meta["sha256"] in toks or meta["sha256"][:12] in toks:
            return node
    return None


def declared_node(rec):
    """The node a verdict declares as its target, from declared fields only (never prose)."""
    for k in ("node_id", "node_ids", "class_id", "class_ids"):
        v = rec.get(k)
        if isinstance(v, list):
            v = ";".join(str(x) for x in v)
        s = str(v or "")
        for node, cls in PIN_BY_CLASS.items():
            if node in s or cls in s:
                return node
    tid = str(rec.get("target_id", ""))
    for node in PINS:
        if tid.startswith(node):
            return node
    return None


def is_accept(rec):
    return str(rec.get("verdict", "")).lower() == "accept"


def full_schema(rec):
    return rec.get("counts_as_full_schema_verdict") is True


def hard_empty(rec):
    hf = rec.get("hard_failures")
    return hf is None or (isinstance(hf, list) and len(hf) == 0)


def analyse(target, reg, snap):
    counted = []
    for row in target.get("coverage_table", []):
        for acc in row.get("non_author_accepts_full", []):
            counted.append({"node": row.get("class"), "table_row": acc})

    h2_fail, h3_fail, h4_fail, per_accept = [], [], [], []
    for item in counted:
        node, row = item["node"], item["table_row"]
        eid = row.get("event_id")
        rec = reg.get(eid)
        pin = PINS.get(node, {}).get("sha256")
        detail = {"node": node, "event_id": eid, "table_reviewer": row.get("reviewer"),
                  "table_verdict": row.get("verdict")}
        checks = {"event_id_present": bool(eid), "record_found": rec is not None}
        if rec is None:
            h2_fail.append({"node": node, "event_id": eid, "reason": "record_not_found"})
            checks.update({"verdict_accept": False, "full_schema": False, "hard_empty": False,
                           "bound_to_pin": False})
            per_accept.append({**detail, "checks": checks, "failures": ["record_not_found"]})
            continue
        fails = []
        checks["verdict_accept"] = is_accept(rec)
        if not checks["verdict_accept"]:
            fails.append(f"verdict={rec.get('verdict')}")
        checks["full_schema"] = full_schema(rec)
        if not checks["full_schema"]:
            fails.append("counts_as_full_schema_verdict!=true")
        checks["hard_empty"] = hard_empty(rec)
        if not checks["hard_empty"]:
            fails.append(f"hard_failures={rec.get('hard_failures')}")
        bnode = bound_pin(rec, reg)
        checks["bound_node"] = bnode
        checks["bound_to_pin"] = (bnode == node)
        if not checks["bound_to_pin"]:
            fails.append(f"bound_node={bnode} expected={node}")
        if fails:
            h2_fail.append({"node": node, "event_id": eid, "reason": ";".join(fails)})
        reviewer = rec.get("reviewer") or rec.get("actor")
        checks["reviewer"] = reviewer
        author_hit = [a for a in (AUTHOR.get(node), "astra-lead-formulation", TARGET_AUTHOR)
                      if a and reviewer == a]
        checks["reviewer_is_author"] = bool(author_hit)
        if author_hit:
            h3_fail.append({"node": node, "event_id": eid, "reviewer": reviewer, "author_match": author_hit})
        t0 = norm_ts(rec.get("created_at"))
        flips = []
        for other in reg.values():
            if other.get("event_id") == eid:
                continue
            if (other.get("reviewer") or other.get("actor")) != reviewer:
                continue
            if str(other.get("verdict", "")).lower() not in ("revise", "reject"):
                continue
            t1 = norm_ts(other.get("created_at"))
            if not (t0 and t1 and t1 > t0):
                continue
            if not (pin in hash_tokens(other) or pin[:12] in hash_tokens(other)):
                continue
            if declared_node(other) != node:
                continue
            flips.append({"event_id": other.get("event_id"), "created_at": t1,
                          "verdict": other.get("verdict")})
        checks["later_flips"] = flips
        if flips:
            h4_fail.append({"node": node, "event_id": eid, "reviewer": reviewer, "flips": flips})
        per_accept.append({**detail, "checks": checks, "failures": fails})

    # windowed census: as-of the target's own measured_at vs all-time (CF-31 mutability)
    cutoff = norm_ts(target.get("measured_at")) or "9999-99-99T99:99:99"
    census, census_all = {}, {}
    for node, meta in PINS.items():
        acc = rev = inc = 0
        acc_a = rev_a = inc_a = 0
        for rec in reg.values():
            if bound_pin(rec, reg) != node:
                continue
            v = str(rec.get("verdict", "")).lower()
            in_window = norm_ts(rec.get("created_at")) <= cutoff if norm_ts(rec.get("created_at")) else False
            if v == "accept" and full_schema(rec):
                acc += 1
                acc_a += 1 if in_window else 0
            elif v == "revise":
                rev += 1
                rev_a += 1 if in_window else 0
            elif v == "inconclusive":
                inc += 1
                inc_a += 1 if in_window else 0
        census[node] = {"accepts_full": acc_a, "revises": rev_a, "inconclusive": inc_a}
        census_all[node] = {"accepts_full": acc, "revises": rev, "inconclusive": inc}
    drift = {n: {k: census_all[n][k] - census[n][k] for k in census[n]} for n in PINS}

    target_text = json.dumps(target).lower()
    rec39_terms = {t: (t.lower() in target_text) for t in
                   ("census", "scan", "CF-31", "controller_gate_audit", "which count",
                    "independence basis", "verdict mtime", "per-file")}
    reconciliation = bool(rec39_terms["CF-31"] or rec39_terms["which count"]
                          or rec39_terms["controller_gate_audit"]
                          or (rec39_terms["scan"] and rec39_terms["census"]))
    rows_all, counts_mismatch = {}, []
    target_counts = {row.get("class"): {"full": len(row.get("non_author_accepts_full", [])),
                                        "all": row.get("non_author_accepts_all"),
                                        "revises": row.get("revises")}
                     for row in target.get("coverage_table", [])}
    cols = ("filename", "reviewer", "verdict", "reviewed_sha256", "mtime", "full_schema", "independence")
    for node, meta in PINS.items():
        bound = [r for r in reg.values() if bound_pin(r, reg) == node]
        rows_all[node] = {"verdicts_bound": len(bound)}
        covered = 0
        for r in bound:
            eid = r.get("event_id")
            blob = None
            for row in target.get("coverage_table", []):
                if row.get("class") != node:
                    continue
                for a in row.get("non_author_accepts_full", []):
                    if a.get("event_id") == eid:
                        blob = a
            if blob is None:
                continue
            low = json.dumps(blob).lower()
            present = 0
            for c in cols:
                if c == "filename" and ("file" in low or "path" in low):
                    present += 1
                elif c == "reviewed_sha256" and ("sha256" in low or "pin" in low):
                    present += 1
                elif c == "mtime" and ("created_at" in low or "mtime" in low):
                    present += 1
                elif c == "independence" and ("independ" in low or "blind" in low):
                    present += 1
                elif c in low:
                    present += 1
            if present == len(cols):
                covered += 1
        rows_all[node]["full_7col_rows"] = covered
        tc = target_counts.get(node, {})
        if tc.get("full") != census[node]["accepts_full"]:
            counts_mismatch.append({"node": node, "field": "non_author_accepts_full",
                                    "target": tc.get("full"), "measured": census[node]["accepts_full"]})
        if tc.get("revises") != census[node]["revises"]:
            counts_mismatch.append({"node": node, "field": "revises",
                                    "target": tc.get("revises"), "measured": census[node]["revises"]})
    h5 = {"rec39_terms_present": rec39_terms, "rows": rows_all,
          "statement_of_which_count": reconciliation,
          "counts_mismatch_vs_registry_asof_target": counts_mismatch,
          "census_window": "verdicts with created_at <= target.measured_at (%s)" % (target.get("measured_at"),)}
    # per-column presence across the target's counted rows, and full-7-col coverage of the 8 counted accepts
    def col_present(low, c):
        if c == "filename":
            return ("file" in low or "path" in low)
        if c == "reviewed_sha256":
            return ("sha256" in low or "pin" in low)
        if c == "mtime":
            return ("created_at" in low or "mtime" in low)
        if c == "independence":
            return ("independ" in low or "blind" in low)
        return c in low

    all_blobs = [a for row in target.get("coverage_table", []) for a in row.get("non_author_accepts_full", [])]
    low_all = json.dumps(all_blobs).lower()
    h5["column_global_presence"] = {c: col_present(low_all, c) for c in cols}
    h5["counted_rows_full_7col"] = sum(1 for b in all_blobs
                                       if all(col_present(json.dumps(b).lower(), c) for c in cols))
    h5["counted_rows"] = len(all_blobs)
    if reconciliation and all(v["full_7col_rows"] >= v["verdicts_bound"] for v in rows_all.values()):
        h5["verdict"] = "PRESENT"
    elif any(h5["column_global_presence"].values()) or any(rec39_terms.values()):
        h5["verdict"] = "PARTIAL"
    else:
        h5["verdict"] = "ABSENT"

    findings = []
    for f in h2_fail:
        findings.append({"id": f"W086-R3V-H2-{f['node']}", "severity": "major",
                         "status": "measured", "statement": f"counted accept fails binding: {f}"})
    for f in h3_fail:
        findings.append({"id": f"W086-R3V-H3-{f['node']}", "severity": "major",
                         "status": "measured", "statement": f"counted accept reviewer is an author: {f}"})
    for f in h4_fail:
        findings.append({"id": f"W086-R3V-H4-{f['node']}", "severity": "major",
                         "status": "measured", "statement": f"counted accept self-superseded: {f}"})
    for m in counts_mismatch:
        findings.append({"id": f"W086-R3V-CENSUS-{m['node']}-{m['field']}", "severity": "minor",
                         "status": "measured",
                         "statement": f"target count != registry census at live pin: {m}"})
    if h5["verdict"] != "PRESENT":
        findings.append({"id": "W086-R3V-REC39", "severity": "major", "status": "measured",
                         "statement": (f"REC-39 minimum content {h5['verdict']}: reconciliation_statement="
                                       f"{h5['statement_of_which_count']}, 7-col rows={rows_all}, "
                                       f"terms={rec39_terms}")})
    post_window = {n: drift[n] for n in drift if any(drift[n].values())}
    if post_window:
        findings.append({"id": "W086-R3V-DRIFT", "severity": "minor", "status": "measured",
                         "statement": (f"coverage keeps moving at the same pins after the target's measured_at: "
                                       f"post-window drift {post_window} (census_all - census_asof)")})

    return {
        "counted_accepts": len(counted),
        "per_accept": per_accept,
        "H1_pins_stable": snap["pins_match"],
        "H2_counted_accepts_bind": len(h2_fail) == 0,
        "H2_failures": h2_fail,
        "H3_non_author": len(h3_fail) == 0,
        "H3_failures": h3_fail,
        "H4_no_post_verdict_flip": len(h4_fail) == 0,
        "H4_failures": h4_fail,
        "H5_rec39_content": h5,
        "target_table_counts": target_counts,
        "census_asof_target": census,
        "census_all_time": census_all,
        "census_drift_after_target": drift,
        "target_hash": snap["target_hash"],
        "frozen_match": snap["frozen_match"],
        "schema_hashes": snap["schema_hashes"],
        "registry_size": len(reg),
        "findings": findings,
    }


def mutate(reg, eid, **kw):
    reg2 = copy.deepcopy(reg)
    reg2[eid].update(kw)
    return reg2


def main():
    map_hash_t0 = sha256_file(MAP)
    map_obj = json.loads(MAP.read_text())
    events_rows = load_jsonl(EVENTS)
    outbox_rows = []
    for p in sorted(OUTBOX.glob("*.jsonl")):
        outbox_rows.extend(load_jsonl(p))
    target = json.loads(TARGET.read_text())
    reg = registry(map_obj, events_rows, outbox_rows)

    schema_hashes = {n: sha256_file(ROOT / m["path"]) for n, m in PINS.items()}
    pins_match = all(schema_hashes[n] == m["sha256"] for n, m in PINS.items())
    frozen_hash = sha256_file(ROOT / FROZEN["path"])
    snap = {"pins_match": pins_match, "schema_hashes": schema_hashes,
            "frozen_match": frozen_hash == FROZEN["sha256"], "target_hash": sha256_file(TARGET)}

    r1 = analyse(target, reg, snap)
    r2 = analyse(target, reg, snap)
    d1, d2 = sha256_text(json.dumps(r1, sort_keys=True)), sha256_text(json.dumps(r2, sort_keys=True))

    counted = [a for row in target.get("coverage_table", []) for a in row.get("non_author_accepts_full", [])]
    eid0 = counted[0]["event_id"] if counted else None
    node0 = next((row.get("class") for row in target.get("coverage_table", [])
                  if counted and row.get("non_author_accepts_full")
                  and row["non_author_accepts_full"][0]["event_id"] == eid0), None)

    def flagged(mut_reg):
        return not analyse(target, mut_reg, snap)["H2_counted_accepts_bind"]

    controls = {
        "K1_null_target_parses": bool(target.get("coverage_table")),
        "K2_hash_mutant": flagged(mutate(reg, eid0, reviewed_sha256="0" * 64,
                                         artifact_sha256="0" * 64, target_id="F2b", evidence_refs=[])),
        "K3_flag_mutant": flagged(mutate(reg, eid0, counts_as_full_schema_verdict=False)),
        "K4_hard_mutant": flagged(mutate(reg, eid0, hard_failures=["W086-CONTROL-MUTANT"])),
        "K5_verdict_mutant": flagged(mutate(reg, eid0, verdict="revise")),
    }
    known_revise = next((r for r in reg.values()
                         if str(r.get("verdict", "")).lower() == "revise" and bound_pin(r, reg) == "F2b"
                         and (r.get("reviewer") or r.get("actor")) == "worker-072"), None)
    controls["K6_positive_revise"] = known_revise is not None
    controls["K7_determinism"] = d1 == d2
    after = {n: sha256_file(ROOT / m["path"]) for n, m in PINS.items()}
    controls["K8_read_only"] = (all(after[n] == schema_hashes[n] for n in PINS)
                                and sha256_file(TARGET) == snap["target_hash"]
                                and sha256_file(MAP) == map_hash_t0
                                and sha256_file(ROOT / FROZEN["path"]) == frozen_hash)

    run_valid = all(bool(v) for v in controls.values()) and pins_match and snap["frozen_match"]
    out = {
        "schema_version": "0.1",
        "task_id": "W086-GFORM-R3-COVERAGE-VERIFY-01",
        "actor": "worker-086",
        "target": {"path": "reviews/G-FORM-final-verify-r3.json", "sha256": snap["target_hash"],
                   "declared_event_id": target.get("event_id"), "declared_actor": target.get("actor"),
                   "declared_measured_at": target.get("measured_at"),
                   "declared_adjudicated_verdict": target.get("adjudicated_verdict")},
        "result_digest": d1,
        "run_valid": run_valid,
        "controls": controls,
        "measurements": r1,
        "k6_known_revise_event_id": known_revise.get("event_id") if known_revise else None,
        "limitations": [
            "worker evidence only: not a gate verdict, not a node status, not an adoption, not a claim about schema semantics",
            "H3 author rule is name equality against authored_by / FROZEN owner / target author; it does not run a full authorship graph",
            "H4 flip rule is strict: a later revise/reject by the same reviewer voids a counted accept only when it declares the same node (node_id/class_id/target_id) and carries the same pin token; a merel mention of the pin in another target's evidence does not void it. An unrecorded edit of a review file under a fixed name is out of reach of a read-only pass and is exactly what CF-31 flags",
            "timestamp comparison normalizes the two observed formats to second precision and ignores timezone offsets; sub-second and cross-offset ordering is not resolved",
            "registry union depends on this run's ingest state; un-ingested outbox lines are included, malformed lines are skipped",
            "REC-39 content is a structural field-presence measurement, not an adequacy judgement; the controller rules on adequacy"
        ],
        "falsifier": ("Any counted accept failing H2 at the live pin, an author-reviewer hit, a strict same-target later flip by the "
                      "accept's own reviewer, a pin mismatch, or an escaped K2-K6 mutant / K7 digest split."),
        "next_falsifier": ("Re-run verify_r3_coverage.py (same path) after any target/target-pin/review-file move; "
                           "a fresh accept or revise at the same pin changes the census and voids this snapshot."),
    }
    OUT.write_text(json.dumps(out, indent=1, sort_keys=False) + "\n")
    print(json.dumps({"run_valid": run_valid, "result_digest": d1,
                      "counted_accepts": r1["counted_accepts"],
                      "H1": r1["H1_pins_stable"], "H2": r1["H2_counted_accepts_bind"],
                      "H3": r1["H3_non_author"], "H4": r1["H4_no_post_verdict_flip"],
                      "H5": r1["H5_rec39_content"]["verdict"],
                      "controls": controls, "census_asof_target": r1["census_asof_target"],
                      "census_all_time": r1["census_all_time"],
                      "census_drift_after_target": r1["census_drift_after_target"],
                      "counts_mismatch_asof": r1["H5_rec39_content"]["counts_mismatch_vs_registry_asof_target"]}, indent=1))
    return 0 if run_valid else 3


if __name__ == "__main__":
    sys.exit(main())

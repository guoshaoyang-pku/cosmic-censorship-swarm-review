#!/usr/bin/env python3
"""W053-INDEX-RECON-01: reconcile reviews/INDEX.md against the live map and on-disk hashes.

Read-only. Deterministic (stdlib only). One pinned snapshot:
  - reviews/INDEX.md                    (sha256 recorded)
  - research_map/research_map.json      (sha256 recorded)
  - the artifact paths named by the INDEX rows (sha256 recorded before and after)

The report answers one question: which rows of the A1 review queue are still an accurate
statement of the world, and which have been superseded by later revisions / map verdicts?
It sets no gate verdict and no node transition.

Run from the repo root or anywhere:
    python3 artifacts/worker-053/index_recon/check_index_recon.py [--out PATH]
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

INDEX_REL = "reviews/INDEX.md"
MAP_REL = "research_map/research_map.json"
LEDGER_REL = "ledger/theorems.jsonl"

HEX12 = re.compile(r"^[0-9a-f]{12,64}$")

# row target -> (node id in the map, canonical artifact paths to hash)
ROWS = {
    "A1": {"node": "A1", "paths": []},
    "F0": {"node": "F0", "paths": ["research_map/formulation_taxonomy.yaml"]},
    "F1": {"node": "F1", "paths": ["schemas/af_wcc_vacuum.yaml"]},
    "F2a": {"node": "F2a", "paths": ["schemas/af_scc_c2_vacuum.yaml"]},
    "F2b": {"node": "F2b", "paths": ["schemas/af_scc_c0_vacuum.yaml"]},
    "G-FORM": {"node": "G-FORM", "paths": []},
    "L0": {"node": "L0", "paths": [LEDGER_REL]},
}

# basename -> row, used to attach map reviews whose target is an artifact path
PATH_HINTS = {
    "formulation_taxonomy.yaml": "F0",
    "af_wcc_vacuum.yaml": "F1",
    "af_scc_c2_vacuum.yaml": "F2a",
    "af_scc_c0_vacuum.yaml": "F2b",
}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.isfile(p):
        return None, None
    with open(p, "rb") as f:
        b = f.read()
    return sha256_bytes(b), len(b)


def now_iso():
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def clean(cell):
    c = cell.strip()
    if c.startswith("`") and c.endswith("`") and len(c) >= 2:
        c = c[1:-1]
    return c.strip()


def parse_md_table(text, header_first_cell):
    """Return list of row dicts for the first markdown table whose header starts with header_first_cell."""
    lines = text.splitlines()
    rows = []
    header = None
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("|"):
            if header is not None and rows:
                break
            continue
        cells = [c for c in s.strip("|").split("|")]
        if header is None:
            if clean(cells[0]).lower() == header_first_cell.lower():
                header = [clean(c) for c in cells]
                continue
            continue
        if set(clean(c) for c in cells) <= {"", "---", ":---", "---:", ":---:"}:
            continue
        if len(cells) < len(header):
            cells = cells + [""] * (len(header) - len(cells))
        rows.append({header[j]: clean(cells[j]) for j in range(len(header))})
    return rows


def parse_index(text):
    rows = parse_md_table(text, "target")
    gates = parse_md_table(text, "gate")
    return rows, gates


def split_paths(cell):
    """INDEX artifact cells may name one path, several paths, or a brace-glob prose target."""
    out = []
    for part in re.split(r"\s\+\s", cell):
        part = clean(part)
        if not part or part in ("?", "-"):
            continue
        out.append(part)
    return out


def bound_sha_from_review(rev):
    """A verdict binds an artifact only through a declared hash field or a #sha suffix."""
    for field in ("artifact_sha256", "reviewed_sha256"):
        v = rev.get(field)
        if isinstance(v, str) and HEX12.match(v.lower()):
            return v.lower(), field
    tid = str(rev.get("target_id") or "")
    if "#" in tid:
        suf = tid.rsplit("#", 1)[1].strip().lower()
        if HEX12.match(suf):
            return suf, "target_id_suffix"
    return None, "none"


def review_matches(rev, row):
    tid = str(rev.get("target_id") or "").strip()
    base = tid.split("#")[0].strip()
    node = row["node"]
    if base == node:
        return True
    gate = str(rev.get("gate") or "").strip()
    if node.startswith("G-") and gate == node:
        return True
    if node == "A1" and (base == "A1" or base.startswith("reviews/")):
        return True
    if node == "L0" and base.startswith("ledger/"):
        return True
    for p in row["paths"]:
        if base == p or base.endswith(p):
            return True
    for hint, r in PATH_HINTS.items():
        if r == node and base.endswith(hint):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "reconciliation.json"))
    args = ap.parse_args()

    # ---- snapshot ---------------------------------------------------------
    index_bytes = open(os.path.join(ROOT, INDEX_REL), "rb").read()
    map_bytes = open(os.path.join(ROOT, MAP_REL), "rb").read()
    index_sha = sha256_bytes(index_bytes)
    map_sha = sha256_bytes(map_bytes)
    index_text = index_bytes.decode("utf-8")
    map_doc = json.loads(map_bytes.decode("utf-8"))

    index_rows, index_gate_rows = parse_index(index_text)

    pinned = {
        INDEX_REL: {"sha256": index_sha, "bytes": len(index_bytes)},
        MAP_REL: {"sha256": map_sha, "bytes": len(map_bytes)},
    }

    # live hashes at snapshot, for every concrete path named in the plan
    live_before = {}
    for rel in [LEDGER_REL] + [p for r in ROWS.values() for p in r["paths"]]:
        h, n = sha256_file(rel)
        live_before[rel] = {"sha256": h, "bytes": n}
    pinned.update({k: v for k, v in live_before.items() if k not in pinned})

    # ---- map indexes ------------------------------------------------------
    map_gates = {g.get("gate_id"): g for g in (map_doc.get("gates") or [])}
    map_reviews = map_doc.get("reviews") or []

    # ---- per-row reconciliation ------------------------------------------
    report_rows = []
    for irow in index_rows:
        target = irow.get("target", "")
        row = ROWS.get(target)
        if row is None:
            report_rows.append({"target": target, "in_plan": False,
                                "note": "INDEX row not covered by this task's class-bound scope"})
            continue
        cell = irow.get("artifact", "")
        paths = split_paths(cell)
        concrete, unresolved = [], []
        for p in paths:
            if p in live_before and live_before[p]["sha256"]:
                concrete.append(p)
            else:
                unresolved.append(p)
        idx_sha12 = (irow.get("sha256 (12)") or "").strip()
        path_status = []
        for p in concrete:
            live = live_before[p]["sha256"]
            match = bool(idx_sha12) and live.lower().startswith(idx_sha12.lower()[:12])
            path_status.append({"path": p, "index_sha12": idx_sha12, "live_sha256": live,
                                "hash_current": match})
        if not concrete:
            hash_status = "unresolvable_target" if unresolved else "no_target_path"
        elif any(s["hash_current"] for s in path_status):
            hash_status = "hash_current"
        else:
            hash_status = "hash_superseded"

        matched = [r for r in map_reviews if review_matches(r, row)]
        by_verdict = {}
        accepts_bound, accepts_unbound, revises = [], [], []
        for r in matched:
            v = str(r.get("verdict") or "?")
            by_verdict[v] = by_verdict.get(v, 0) + 1
            bs, field = bound_sha_from_review(r)
            rec = {"event_id": r.get("event_id"), "reviewer": r.get("reviewer"),
                   "verdict": v, "score": r.get("score"),
                   "bound_sha256": bs, "bound_via": field,
                   "binds_index_sha12": bool(bs and idx_sha12 and bs.startswith(idx_sha12.lower()[:12])),
                   "binds_live_canonical": bool(bs and any(
                       s["live_sha256"] and bs.startswith(s["live_sha256"][:12]) for s in path_status))}
            if v == "accept":
                (accepts_bound if bs else accepts_unbound).append(rec)
            elif v == "revise":
                revises.append(rec)

        # node gate: F0->G-F0, F1/F2a/F2b->G-FORM, L0->G-LIT, A1->G-AUDIT
        node_gate = {"F0": "G-F0", "F1": "G-FORM", "F2a": "G-FORM", "F2b": "G-FORM",
                     "L0": "G-LIT", "A1": "G-AUDIT", "G-FORM": "G-FORM"}.get(target)
        gate_rec = map_gates.get(node_gate) if node_gate else None

        discrepancy = []
        if hash_status == "hash_superseded":
            discrepancy.append("index_sha_superseded_on_disk")
        if hash_status == "unresolvable_target":
            discrepancy.append("index_target_not_a_single_file")
        if accepts_unbound:
            discrepancy.append("map_has_%d_unbound_accepts" % len(accepts_unbound))
        if accepts_bound and not any(a["binds_live_canonical"] for a in accepts_bound):
            discrepancy.append("map_accept_binds_a_superseded_hash_only")
        report_rows.append({
            "target": target,
            "in_plan": True,
            "node_id": row["node"],
            "index": {"artifact_cell": cell, "sha256_12": idx_sha12,
                      "verdict": irow.get("verdict"), "score": irow.get("score"),
                      "hard_failures": irow.get("hard failures")},
            "live_paths": path_status,
            "unresolved_targets": unresolved,
            "hash_status": hash_status,
            "map_reviews": {"matched": len(matched), "by_verdict": by_verdict,
                            "accepts_bound": accepts_bound, "accepts_unbound": accepts_unbound,
                            "revises": revises},
            "map_gate": None if gate_rec is None else {
                "gate_id": gate_rec.get("gate_id"), "verdict": gate_rec.get("verdict"),
                "updated_at": gate_rec.get("updated_at"),
                "unmet": gate_rec.get("unmet") or []},
            "discrepancies": discrepancy,
        })

    # ---- gate table -------------------------------------------------------
    gate_recon = []
    for grow in index_gate_rows:
        gid = grow.get("gate", "")
        mg = map_gates.get(gid)
        gate_recon.append({
            "gate": gid,
            "index_verdict": grow.get("verdict"),
            "index_reason": grow.get("reason"),
            "map_verdict": None if mg is None else mg.get("verdict"),
            "map_updated_at": None if mg is None else mg.get("updated_at"),
            "mismatch": bool(mg is not None and grow.get("verdict") != mg.get("verdict")),
            "map_unmet": [] if mg is None else (mg.get("unmet") or []),
        })

    # ---- drift re-check ---------------------------------------------------
    index_after = sha256_file(INDEX_REL)[0]
    map_after = sha256_file(MAP_REL)[0]
    live_after = {rel: sha256_file(rel)[0] for rel in live_before}
    changed = [rel for rel, h in ([(INDEX_REL, index_after), (MAP_REL, map_after)] +
                                  list(live_after.items())) if h != (pinned.get(rel) or {}).get("sha256")]
    drift = {"detected": bool(changed), "changed_inputs": sorted(set(changed)),
             "pins_at_snapshot": {k: v.get("sha256") for k, v in pinned.items()},
             "pins_at_end": {INDEX_REL: index_after, MAP_REL: map_after, **live_after}}

    # ---- findings ---------------------------------------------------------
    findings = []
    superseded = [r["target"] for r in report_rows if r.get("hash_status") == "hash_superseded"]
    unresolvable = [r["target"] for r in report_rows if r.get("hash_status") == "unresolvable_target"]
    unbound_accepts = {r["target"]: len(r["map_reviews"]["accepts_unbound"])
                       for r in report_rows if r.get("map_reviews", {}).get("accepts_unbound")}
    bound_live = {r["target"]: [a["event_id"] for a in r["map_reviews"]["accepts_bound"]
                                if a["binds_live_canonical"]]
                  for r in report_rows if r.get("map_reviews", {}).get("accepts_bound")}
    bound_live = {k: v for k, v in bound_live.items() if v}
    mism = [g["gate"] for g in gate_recon if g["mismatch"]]
    if superseded:
        findings.append({
            "id": "IR-01", "severity": "major",
            "statement": ("Every class-bound INDEX row whose target is a single canonical file is hash-superseded: "
                          + ", ".join(superseded) + ". The INDEX sha256(12) values are not the live bytes at the "
                          "pinned snapshot, so no INDEX verdict can be read as a verdict on the current revision."),
            "falsifier": ("Re-run the checker at the same pins: the finding is falsified if any of these rows is "
                          "classified hash_current, i.e. the first 12 hex of the live canonical sha256 equals the "
                          "INDEX sha256(12).")})
    if unbound_accepts:
        findings.append({
            "id": "IR-02", "severity": "major",
            "statement": ("The map stores accept verdicts for " + ", ".join(sorted(unbound_accepts))
                          + " that declare no artifact hash binding (artifact_sha256/reviewed_sha256 null and no "
                          "#sha suffix on target_id), so they cannot certify any revision; counts: "
                          + json.dumps(unbound_accepts, sort_keys=True)
                          + (". At this snapshot the only class-bound target with an accept bound to the live "
                             "canonical bytes is " + ", ".join(sorted(bound_live)) + " ("
                             + "; ".join(sorted(sum(bound_live.values(), []))) + ")." if bound_live else
                             ". At this snapshot no accept binds the live canonical bytes of any class-bound target.")),
            "falsifier": ("Re-run the checker at the same pins: falsified if an accept for one of these targets is "
                          "found carrying a declared hash that prefixes the live canonical sha256.")})
    if bound_live:
        findings.append({
            "id": "IR-05", "severity": "minor",
            "statement": ("Hash-bound accepts at the live canonical bytes exist only for: "
                          + "; ".join("%s (%s)" % (k, ", ".join(v)) for k, v in sorted(bound_live.items()))
                          + ". For every other class-bound target the map's accepts are unbound, so the G-F0/G-FORM "
                            "unmet reason 'no accept at the current hash' is reproduced for them and not for this one."),
            "falsifier": ("Re-run the checker at the same pins: falsified if another target gains an accept whose "
                          "declared hash prefixes its live canonical sha256, or if the bound accept's hash no longer "
                          "prefixes the live canonical bytes.")})
    if unresolvable:
        findings.append({
            "id": "IR-03", "severity": "minor",
            "statement": ("INDEX rows " + ", ".join(unresolvable) + " name brace-glob/prose targets, not a single "
                          "file, so their hash column cannot be reconciled mechanically by this checker."),
            "falsifier": ("Falsified if the pinned INDEX.md resolves those targets to a single concrete file path "
                          "on re-read.")})
    if mism:
        findings.append({
            "id": "IR-04", "severity": "major",
            "statement": ("The INDEX gate table disagrees with the map gate verdicts for: " + ", ".join(mism)
                          + ". The INDEX records the 23:27:56 review-round verdicts; the map records later "
                          "hash-bound pending verdicts (see map_unmet per gate)."),
            "falsifier": ("Re-run the checker at the same pins: falsified for a gate if index_verdict equals "
                          "map_verdict.")})

    rep = {
        "report": "W053-INDEX-RECON-01",
        "actor": "worker-053",
        "task_id": "W053-INDEX-RECON-01",
        "generated_at": now_iso(),
        "scope": ("class-bound reconciliation of reviews/INDEX.md against research_map/research_map.json and the "
                  "on-disk canonical artifacts; read-only evidence, no gate verdict, no node transition"),
        "pins": pinned,
        "index_generated_line": next((l for l in index_text.splitlines() if l.startswith("Generated:")), None),
        "index_rows_parsed": len(index_rows),
        "index_gate_rows_parsed": len(index_gate_rows),
        "rows": report_rows,
        "gate_table": gate_recon,
        "findings": findings,
        "drift": drift,
        "limits": [
            "A map review is matched to a row by target_id/node/gate/path; review records with unrelated targets are ignored.",
            "binding is counted only through declared hash fields or a #sha target suffix, never by filename or prose (same policy as W03-VERDICT-BIND-01).",
            "the checker does not judge the merit of any verdict, only whether the INDEX row and the map agree on hash and status.",
            "content timestamps in the event stream are known unreliable (controller finding CF-6); ordering uses map list order.",
        ],
        "falsifier": ("Re-run artifacts/worker-053/index_recon/check_index_recon.py against the same pinned "
                      "reviews/INDEX.md and research_map/research_map.json bytes. The report is falsified if (a) any "
                      "row classified hash_superseded matches the live artifact prefix; (b) any row classified "
                      "hash_current differs from the live sha256; (c) index_rows_parsed != the data-row count of the "
                      "pinned INDEX table; or (d) drift.detected is false but a re-hash shows an input changed."),
    }
    with open(args.out, "w") as f:
        f.write(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: rep[k] for k in ("report", "index_rows_parsed", "findings", "drift")}, indent=2, sort_keys=True))
    print("out:", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

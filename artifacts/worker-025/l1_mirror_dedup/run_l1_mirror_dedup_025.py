#!/usr/bin/env python3
"""W025-L1-MIRROR-DEDUP-01: reconcile the declared mirror_of graph with the
identifier-keyed work graph at the frozen L1 citation audit.

Read-only. No network. No clock input in report.json (deterministic).
Fail-closed on the frozen pin.

Rules R1-R6 are those pre-registered in PREREGISTRATION.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import defaultdict

PIN = "315c19145065a5f9c95d64461eae760b4c296b06d1f2f09bc5847ac1a7064ce9"

VERIFICATION_RANK = {
    "primary-page-fetch": 4,
    "crossref-api": 3,
    "inspirehep-api": 2,
    "openalex": 1,
    "openalex-api": 1,
}
EVIDENCE_RANK = {"abstract": 3, "metadata": 2}
RECORD_HOSTS_PUBLISHED = ("crossref.org", "openalex.org", "doi.org")
INSPIRE_RECORD_RE = re.compile(r"inspirehep\.net/api/literature/\d+")
PROVENANCE_PAREN = re.compile(
    r"\(([^)]*(?:record|version|reconstruction|preprint|arxiv|crossref|openalex|journal ref)[^)]*)\)",
    re.IGNORECASE,
)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def doi_norm(value: str) -> str:
    v = (value or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "http://dx.doi.org/",
                   "https://dx.doi.org/", "doi:"):
        if v.startswith(prefix):
            v = v[len(prefix):]
    return v.strip()


def arxiv_norm(value: str) -> str:
    v = (value or "").strip().lower()
    if v.startswith("arxiv:"):
        v = v[len("arxiv:"):]
    v = re.sub(r"v\d+$", "", v.strip())
    return v.strip()


def arxiv_aliases(value: str) -> set:
    """Legacy ids 'subj/NNNNNNN' also match their bare numeric form."""
    v = arxiv_norm(value)
    if not v:
        return set()
    aliases = {v}
    m = re.match(r"^[a-z-]+(?:\.[a-z]{2})?/(\d{7})$", v)
    if m:
        aliases.add(m.group(1))
    return aliases


def title_norm(title: str) -> str:
    t = (title or "").lower()
    t = PROVENANCE_PAREN.sub(" ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def compact_norm(title: str) -> str:
    """All non-alphanumerics removed, so 'space-times' == 'spacetimes'."""
    t = (title or "").lower()
    t = PROVENANCE_PAREN.sub(" ", t)
    return re.sub(r"[^a-z0-9]+", "", t)


def token_jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def title_agree(t1: str, t2: str) -> bool:
    """R4 title test, amendment 1 (see AMENDMENT-01.json).

    equality | compact-form equality | Jaccard >= 0.90 | (both >= 8 tokens and
    the shorter token sequence is a contiguous prefix of the longer).
    """
    n1, n2 = title_norm(t1), title_norm(t2)
    if n1 == n2 or compact_norm(t1) == compact_norm(t2):
        return True
    if token_jaccard(n1, n2) >= 0.90:
        return True
    a, b = n1.split(), n2.split()
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) >= 8 and len(short) < len(long_) and long_[:len(short)] == short:
        return True
    return False


def as_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def artifact_class(url: str) -> str:
    u = (url or "").strip().lower()
    host = u.split("//", 1)[-1].split("/", 1)[0]
    if host.endswith("arxiv.org") or "export.arxiv.org" in host:
        return "PREPRINT"
    if any(h in host for h in RECORD_HOSTS_PUBLISHED) or INSPIRE_RECORD_RE.search(u):
        return "PUBLISHED"
    return "UNKNOWN"


class UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if rb < ra:
                ra, rb = rb, ra
            self.parent[rb] = ra


def load_rows(csv_text: str):
    return [dict(r) for r in csv.DictReader(io.StringIO(csv_text))]


def identifier_edges(rows):
    edges = []
    groups = defaultdict(list)
    for r in rows:
        d = doi_norm(r.get("doi", ""))
        if d:
            groups[("doi", d)].append(r["citation_id"])
        for a in arxiv_aliases(r.get("arxiv_id", "")):
            groups[("arxiv", a)].append(r["citation_id"])
    for key, members in sorted(groups.items()):
        members = sorted(set(members))
        for other in members[1:]:
            edges.append((members[0], other, "identifier:" + key[0] + ":" + key[1]))
    return edges


def identifier_pairs(rows):
    return sorted({tuple(sorted((a, b))) for a, b, _ in identifier_edges(rows)})


def mirror_edges(rows):
    byid = {r["citation_id"]: r for r in rows}
    declared, suspect = [], []
    for r in rows:
        src = r["citation_id"]
        dst = (r.get("mirror_of") or "").strip()
        if not dst:
            continue
        if dst not in byid:
            suspect.append({"from": src, "to": dst, "reason": "MIRROR_TARGET_ABSENT"})
            continue
        tgt = byid[dst]
        reasons = []
        if not title_agree(r.get("title", ""), tgt.get("title", "")):
            reasons.append("TITLE_DISAGREEMENT")
        y1, y2 = as_int(r.get("year", "")), as_int(tgt.get("year", ""))
        if y1 is not None and y2 is not None and abs(y1 - y2) > 4:
            reasons.append("YEAR_GAP_GT_4")
        if reasons:
            suspect.append({"from": src, "to": dst, "reason": "+".join(reasons)})
        else:
            declared.append({"from": src, "to": dst})
    return declared, suspect


def canonical_choice(members, byid):
    def key(cid):
        r = byid[cid]
        resolved = 1 if (r.get("resolver_result") or "").strip() == "resolved" else 0
        vrank = VERIFICATION_RANK.get((r.get("verification_method") or "").strip(), 0)
        erank = EVIDENCE_RANK.get((r.get("evidence_type") or "").strip(), 0)
        return (resolved, vrank, erank, [-ord(c) for c in cid])
    return max(sorted(members), key=key)


def union_citation_edges(members, byid):
    theorems, classes = set(), set()
    for cid in members:
        for t in (byid[cid].get("used_by_theorems") or "").split(";"):
            if t.strip():
                theorems.add(t.strip())
        for c in (byid[cid].get("class_mapping") or "").split(";"):
            c = c.strip()
            if c and not c.startswith("("):
                classes.add(c)
    return sorted(theorems), sorted(classes)


def build_record(csv_text: str):
    rows = load_rows(csv_text)
    byid = {r["citation_id"]: r for r in rows}
    ids = sorted(byid)

    ident_edges = identifier_edges(rows)
    mir_declared, mir_suspect = mirror_edges(rows)

    uf = UnionFind(ids)
    for a, b, _ in ident_edges:
        uf.union(a, b)
    for e in mir_declared:
        uf.union(e["from"], e["to"])

    comps = defaultdict(list)
    for cid in ids:
        comps[uf.find(cid)].append(cid)

    ident_set = {tuple(sorted((a, b))) for a, b, _ in ident_edges}
    mirror_set = {tuple(sorted((e["from"], e["to"]))) for e in mir_declared}

    components, merges, links, mirror_only, suspects = [], [], [], [], []
    for root in sorted(comps):
        members = sorted(comps[root])
        mset = set(members)
        classes = {cid: artifact_class(byid[cid].get("url", "")) for cid in members}
        same_identifier = any(set(p) <= mset for p in ident_set)
        has_mirror = any(set(p) <= mset for p in mirror_set)
        title_ok = all(
            title_agree(byid[members[0]].get("title", ""), byid[cid].get("title", ""))
            for cid in members[1:]
        )
        rec = {
            "component_id": members[0],
            "members": members,
            "artifact_class": classes,
            "identifier_linked": same_identifier,
            "mirror_linked": has_mirror,
            "title_agreement": title_ok,
            "disposition": None,
        }
        if len(members) == 1:
            rec["disposition"] = "SINGLETON"
        elif len(set(classes.values())) == 1 and title_ok:
            canon = canonical_choice(members, byid)
            superseded = [c for c in members if c != canon]
            theorems, cls = union_citation_edges(members, byid)
            own_theorems = sorted(t.strip() for t in (byid[canon].get("used_by_theorems") or "").split(";") if t.strip())
            own_classes = sorted(c.strip() for c in (byid[canon].get("class_mapping") or "").split(";") if c.strip() and not c.strip().startswith("("))
            rec.update({
                "disposition": "MERGE_DUPLICATE",
                "canonical": canon,
                "superseded": superseded,
                "canonical_own_used_by_theorems": own_theorems,
                "canonical_own_class_mapping": own_classes,
                "citation_edge_union": {
                    "used_by_theorems": theorems,
                    "class_mapping": cls,
                    "added_theorems_vs_canonical": sorted(set(theorems) - set(own_theorems)),
                    "added_classes_vs_canonical": sorted(set(cls) - set(own_classes)),
                    "edge_union_differs_from_canonical": theorems != own_theorems or cls != own_classes,
                },
            })
            merges.append(rec)
        elif not same_identifier and has_mirror:
            rec["disposition"] = "MIRROR_ONLY_LINK"
            mirror_only.append(rec)
        elif title_ok:
            rec["disposition"] = "LINK_ONLY"
            links.append(rec)
        else:
            rec["disposition"] = "TITLE_CONFLICT"
            suspects.append(rec)
        components.append(rec)

    for s in mir_suspect:
        if s["reason"] == "MIRROR_TARGET_ABSENT":
            suspects.append(dict(s, disposition="SUSPECT_MIRROR"))
        else:
            suspects.append({"component_id": s["from"], "members": [s["from"], s["to"]],
                             "disposition": "SUSPECT_MIRROR", "reason": s["reason"]})

    return {
        "rows": rows, "byid": byid, "ids": ids,
        "ident_edges": ident_edges, "ident_pairs": sorted(ident_set),
        "mirror_declared": mir_declared, "mirror_suspect": mir_suspect,
        "components": components, "merges": merges, "links": links,
        "mirror_only": mirror_only, "suspects": suspects,
    }


def analyse(csv_text: str):
    b = build_record(csv_text)
    findings = []
    susp = [s for s in b["suspects"] if s.get("reason")]
    if susp:
        findings.append({
            "id": "F1",
            "severity": "major",
            "label": "declared mirror_of edge contradicted by the record fields",
            "detail": susp,
        })
    # F2: a component with rows reachable only through mirror_of
    f2 = [
        {"component": m["component_id"], "members": m["members"],
         "mirror_only_rows": [c for c in m["members"] if not b["byid"][c].get("doi") and not b["byid"][c].get("arxiv_id")]}
        for m in b["components"]
        if m["mirror_linked"] and any(not b["byid"][c].get("doi") and not b["byid"][c].get("arxiv_id") for c in m["members"])
    ]
    if f2:
        findings.append({
            "id": "F2",
            "severity": "major",
            "label": "rows reachable only through mirror_of, invisible to identifier-keyed dedup",
            "detail": f2,
        })
    if b["mirror_only"]:
        findings.append({
            "id": "F3",
            "severity": "info",
            "label": "components with no shared identifier at all (mirror-only)",
            "detail": [m["members"] for m in b["mirror_only"]],
        })
    changed = [m for m in b["merges"] if m["citation_edge_union"]["edge_union_differs_from_canonical"]]
    if changed:
        findings.append({
            "id": "F4",
            "severity": "major",
            "label": "merging without unioning citation edges would drop used_by_theorems/class_mapping",
            "detail": [{"component": m["component_id"], "canonical": m["canonical"],
                        "added_theorems": m["citation_edge_union"]["added_theorems_vs_canonical"],
                        "added_classes": m["citation_edge_union"]["added_classes_vs_canonical"]} for m in changed],
        })
    return b, findings


def controls(csv_text: str, base, b):
    results = []

    def rec(cid, ok, detail):
        results.append({"control": cid, "fired": bool(ok), "detail": detail})

    # C2: with mirror edges removed, only the 9 identifier groups remain.
    rows = b["rows"]
    uf = UnionFind(b["ids"])
    for a, bb, _ in b["ident_edges"]:
        uf.union(a, bb)
    comps = defaultdict(list)
    for cid in b["ids"]:
        comps[uf.find(cid)].append(cid)
    multi = [sorted(v) for v in comps.values() if len(v) > 1]
    rec("C2_no_mirror_components", len(comps) == 88 and len(multi) == 9,
        f"identifier-only components={len(comps)} (expected 88), multi={len(multi)} (expected 9)")

    # C3: rewriting the SRC-072 title must flip its component out of MERGE_DUPLICATE.
    rows2 = [dict(r) for r in rows]
    for r in rows2:
        if r["citation_id"] == "SRC-072":
            r["title"] = "A completely different work on cosmic censorship"
    b2, _ = analyse(rows_to_csv_text(rows2))
    grp = [c for c in b2["components"] if "SRC-072" in c["members"]]
    rec("C3_title_conflict_flips_group",
        bool(grp) and grp[0]["disposition"] in ("TITLE_CONFLICT", "SUSPECT_MIRROR"),
        f"SRC-072 component disposition with rewritten title = {grp[0]['disposition'] if grp else 'ABSENT'}")

    # C4: reversed row order -> identical merge signature.
    rev = "\n".join([csv_text.splitlines()[0]] + list(reversed(csv_text.splitlines()[1:]))) + "\n"
    b3, _ = analyse(rev)

    def sig(ms):
        return sorted((m["component_id"], m["canonical"], tuple(m["superseded"])) for m in ms)
    rec("C4_order_independent", sig(b3["merges"]) == sig(b["merges"]),
        f"reversed-order merge signature match={sig(b3['merges']) == sig(b['merges'])}")

    # C5: swapping the two citation-edge lists leaves the union unchanged.
    rows3 = [dict(r) for r in rows]
    r60 = next(r for r in rows3 if r["citation_id"] == "SRC-060")
    r72 = next(r for r in rows3 if r["citation_id"] == "SRC-072")
    r60["used_by_theorems"], r72["used_by_theorems"] = r72["used_by_theorems"], r60["used_by_theorems"]
    b4, _ = analyse(rows_to_csv_text(rows3))
    m = next((x for x in b4["merges"] if x["component_id"] == "SRC-020"), None)
    rec("C5_union_order_independent",
        bool(m) and m["citation_edge_union"]["used_by_theorems"] == ["D-002", "T-501", "T-521"],
        f"swapped union={m['citation_edge_union']['used_by_theorems'] if m else 'NO_MERGE'}")

    # C6: never propose a merge across PREPRINT/PUBLISHED classes.
    cross = [m for m in b["merges"] if len(set(m["artifact_class"].values())) != 1]
    rec("C6_no_cross_class_merge", not cross, f"cross-class merges={len(cross)}")

    # C7: legacy arXiv ids alias their bare numeric form.
    alias_ok = "0307013" in arxiv_aliases("gr-qc/0307013") and arxiv_aliases("1702.05715") == {"1702.05715"}
    synth = [dict(rows[0]), dict(rows[1])]
    synth[0]["citation_id"], synth[0]["doi"], synth[0]["arxiv_id"] = "SRC-A", "", "gr-qc/0307013"
    synth[1]["citation_id"], synth[1]["doi"], synth[1]["arxiv_id"] = "SRC-B", "", "0307013"
    b5, _ = analyse(rows_to_csv_text(synth))
    grp = [c for c in b5["components"] if "SRC-B" in c["members"]]
    synth_ok = bool(grp) and set(grp[0]["members"]) == {"SRC-A", "SRC-B"}
    rec("C7_legacy_arxiv_alias", alias_ok and synth_ok,
        f"alias_ok={alias_ok}, synthetic component={grp[0]['members'] if grp else 'ABSENT'}")

    return results


def rows_to_csv_text(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="ledger/citation_audit.csv")
    ap.add_argument("--expected-pin", default=PIN)
    ap.add_argument("--out", default="artifacts/worker-025/l1_mirror_dedup/report.json")
    ap.add_argument("--emit-stdout", action="store_true")
    args = ap.parse_args()

    pin = sha256_file(args.csv)
    if pin != args.expected_pin:
        print(json.dumps({"error": "PIN_MISMATCH", "measured": pin, "expected": args.expected_pin}))
        return 2

    csv_text = open(args.csv, "r", newline="").read()
    b, findings = analyse(csv_text)
    ctrl = controls(csv_text, None, b)

    pred = {
        "P1_pin_and_rows": {"pass": len(b["rows"]) == 97 and len(set(b["ids"])) == 97,
                            "rows": len(b["rows"]), "unique_ids": len(set(b["ids"]))},
        "P2_ident_groups": {"pass": len(b["ident_edges"]) == 10 and len(b["ident_pairs"]) == 9,
                            "identifier_edges": len(b["ident_edges"]), "unique_pairs": len(b["ident_pairs"]),
                            "pairs": [list(p) for p in b["ident_pairs"]]},
        "P3_mirror_only_additions": {
            "pass": any(set(m["members"]) == {"SRC-020", "SRC-060", "SRC-072"} for m in b["components"])
                    and any(set(m["members"]) == {"SRC-041", "SRC-054"} for m in b["components"])
                    and any(set(m["members"]) == {"SRC-044", "SRC-067"} for m in b["components"]),
            "mirror_only_components": [m["members"] for m in b["mirror_only"]]},
        "P4_src093_suspect": {"pass": any(s.get("from") == "SRC-093" for s in b["mirror_suspect"]),
                              "suspect_edges": b["mirror_suspect"]},
        "P5_three_merges_four_superseded": {
            "pass": len(b["merges"]) == 3 and sum(len(m["superseded"]) for m in b["merges"]) == 4,
            "merges": [{"component": m["component_id"], "canonical": m["canonical"],
                        "superseded": m["superseded"]} for m in b["merges"]]},
        "P6_edge_union_changes": {
            "pass": any(m["citation_edge_union"]["edge_union_differs_from_canonical"] for m in b["merges"]),
            "details": [{"component": m["component_id"],
                         "differs": m["citation_edge_union"]["edge_union_differs_from_canonical"],
                         "added_theorems": m["citation_edge_union"]["added_theorems_vs_canonical"]}
                        for m in b["merges"]]},
        "P7_seven_link_only": {"pass": len(b["links"]) == 7, "link_only": [m["members"] for m in b["links"]]},
        "P8_deterministic": {"pass": None, "note": "verified by the second run recorded in run2.stdout.txt"},
    }
    failed = [k for k, v in pred.items() if v.get("pass") is False]
    report = {
        "schema": "w025-l1-mirror-dedup-report/v1",
        "task_id": "W025-L1-MIRROR-DEDUP-01",
        "actor": "worker-025",
        "node_id": "L1",
        "gate": "G-LIT",
        "class_ids": ["AF-WCC-VAC-GEN", "AF-SCC-C2-VAC-GEN", "AF-SCC-C0-VAC-GEN", "AF-WCC-SCALAR-SPH"],
        "frozen_input": {"path": args.csv, "sha256": pin, "rows": len(b["rows"])},
        "rule": "R1-R6 as pre-registered in PREREGISTRATION.json",
        "identifier_pairs": [list(p) for p in b["ident_pairs"]],
        "mirror_declared": b["mirror_declared"],
        "mirror_suspect": b["mirror_suspect"],
        "components": b["components"],
        "merges": b["merges"],
        "findings": findings,
        "summary": {
            "components": len(b["components"]),
            "merge_duplicate_components": len(b["merges"]),
            "link_only_components": len(b["links"]),
            "mirror_only_link_components": len(b["mirror_only"]),
            "suspect_mirror_edges": len(b["mirror_suspect"]),
            "rows_superseded_proposed": sum(len(m["superseded"]) for m in b["merges"]),
            "net_row_reduction_proposed": sum(len(m["superseded"]) for m in b["merges"]),
        },
        "controls": ctrl,
        "predictions": pred,
        "failed_predictions": failed,
        "verdict": "MEASURED" if not failed and all(c["fired"] for c in ctrl) else "PARTIAL_OR_FALSIFIED",
        "falsifier": "Re-run twice; falsified if the pin differs, a pre-registered prediction fails unrecorded, the two report.json files differ, or a disposition is not derivable from R1-R5 on the pinned bytes.",
        "non_claims": [
            "not a mathematical or physics claim",
            "not a gate verdict",
            "no ledger/map/schema/detector write; merge map is an unfrozen proposal",
            "title agreement is a normalization heuristic, not an identity proof",
        ],
        "generated_at": None,
    }
    out = json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    with open(args.out, "w") as f:
        f.write(out)
    if args.emit_stdout:
        sys.stdout.write(out)
    return 0 if report["verdict"] == "MEASURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
